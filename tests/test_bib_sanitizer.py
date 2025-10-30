"""test_bib_sanitizer.py
-----------------------
Tests for bib_sanitizer.py

Validates all key sanitation and reporting behavior including:
- Emergency mode RDF validation
- Organization name fixing
- arXiv eprint detection
- Domain-as-title repair
- Duplicate detection (FLAG only, no merge)
- JSON report structure

Run with:
    pytest -v tests/test_bib_sanitizer.py
"""

import json
import tempfile
from pathlib import Path
import pytest
import bibtexparser

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from converters.md_to_latex.bib_sanitizer import (
    sanitize_bib,
    is_domain_title,
    is_stub_title,
    normalize_url,
)

# --------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------

@pytest.fixture
def sample_bib(tmp_path: Path):
    """Creates a small sample .bib file for testing."""
    bib_content = r"""@misc{ec2023,
  author = {European Commission},
  title = {Circular economy report},
  year = {2023}
}

@misc{domain_title,
  author = {Fashion Revolution},
  title = {fashionrevolution.org},
  url = {https://www.fashionrevolution.org},
  year = {2022}
}

@article{arxiv_example,
  author = {Doe, John},
  title = {Quantum cats},
  journal = {arXiv preprint},
  url = {https://arxiv.org/abs/2401.12345},
  year = {2024}
}

@misc{stub_title,
  author = {Axios},
  title = {Web page by axios},
  url = {https://www.axios.com/example},
  year = {2025}
}

@misc{duplicate_a,
  author = {Smith, Alice and Jones, Bob},
  title = {Green textiles: future materials},
  year = {2021}
}

@misc{duplicate_b,
  author = {Alice Smith and Bob Jones},
  title = {Future materials: green textiles},
  year = {2021}
}
"""
    bibfile = tmp_path / "test_refs.bib"
    bibfile.write_text(bib_content)
    return bibfile

@pytest.fixture
def sample_rdf(tmp_path: Path):
    """Minimal RDF file that matches the domain_title entry."""
    rdf_text = """<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns:dc="http://purl.org/dc/elements/1.1/"
         xmlns:bib="http://purl.org/net/biblio#">
  <bib:Webpage rdf:about="https://www.fashionrevolution.org">
    <dc:title>Fashion Revolution Annual Report</dc:title>
    <dc:identifier>https://www.fashionrevolution.org</dc:identifier>
    <dc:creator>
      <rdf:Seq><rdf:li>Fashion Revolution</rdf:li></rdf:Seq>
    </dc:creator>
    <dc:date>2022</dc:date>
  </bib:Webpage>
</rdf:RDF>"""
    rdf_file = tmp_path / "zotero.rdf"
    rdf_file.write_text(rdf_text)
    return rdf_file

# --------------------------------------------------------------------
# Unit Tests
# --------------------------------------------------------------------

def test_is_domain_title():
    assert is_domain_title("example.com")
    assert is_domain_title("https://eco-textiles.org")
    assert is_domain_title("Amazon.de")
    assert not is_domain_title("Nature")
    assert not is_domain_title("Circular economy in Europe")

def test_is_stub_title():
    assert is_stub_title("Web page by axios")
    assert is_stub_title("Web article by bloomberg")
    assert is_stub_title("Added from URL: something")
    assert not is_stub_title("Real Article Title")

def test_normalize_url():
    # Protocol and www removal
    assert normalize_url("https://www.example.com/path") == "example.com/path"
    assert normalize_url("http://example.org/page/") == "example.org/page"

    # Amazon normalization by ASIN
    url1 = "https://www.amazon.de/-/en/Craft-Use/dp/1138021016?ref=xyz"
    url2 = "https://amazon.com/dp/1138021016"
    assert normalize_url(url1) == "amazon.com/dp/1138021016"
    assert normalize_url(url2) == "amazon.com/dp/1138021016"

    # arXiv normalization
    url3 = "https://arxiv.org/abs/2401.12345"
    url4 = "https://arxiv.org/pdf/2401.12345.pdf"
    assert normalize_url(url3) == "arxiv.org/abs/2401.12345"
    assert normalize_url(url4) == "arxiv.org/abs/2401.12345"

# --------------------------------------------------------------------
# Integration Tests
# --------------------------------------------------------------------

def test_sanitize_bib_with_rdf(sample_bib, sample_rdf, tmp_path):
    """Test sanitization with RDF file (normal mode)."""
    out_bib = tmp_path / "clean.bib"
    report_file = tmp_path / "report.json"

    report = sanitize_bib(sample_bib, out_bib, rdf_path=sample_rdf, emergency_mode=False)

    # Write report
    report_file.write_text(json.dumps(report, indent=2))

    # Check report structure
    assert set(report.keys()) == {
        "fixed_orgs", "fixed_arxiv", "domain_titles", "stub_titles",
        "manual_review", "duplicates", "not_found_in_rdf"
    }

    assert report["fixed_orgs"] >= 1  # European Commission
    assert report["fixed_arxiv"] >= 1  # arXiv entry
    assert report["domain_titles"] >= 1  # fashionrevolution.org
    assert report["stub_titles"] >= 1  # "Web page by axios"

    # Load sanitized file
    with open(out_bib, encoding="utf8") as f:
        bib_db = bibtexparser.load(f)

    entries = {e["ID"]: e for e in bib_db.entries}

    # Organization should be double-braced
    assert "{{European Commission}}" in entries["ec2023"]["author"]

    # RDF should have replaced the domain title
    assert "Annual Report" in entries["domain_title"]["title"]

    # arXiv entry should have eprint
    assert "eprint" in entries["arxiv_example"]
    assert entries["arxiv_example"]["eprint"] == "2401.12345"

    # Duplicate entries should be FLAGGED (not merged)
    duplicates = report["duplicates"]
    assert len(duplicates) >= 1
    assert any("duplicate_a" in str(d.values()) and "duplicate_b" in str(d.values())
               for d in duplicates)

    # Ensure duplicates were NOT merged (both should still exist)
    assert "duplicate_a" in entries
    assert "duplicate_b" in entries

def test_sanitize_bib_without_rdf_marks_manual_review(sample_bib, tmp_path):
    """Test that domain titles are flagged for manual review when no RDF."""
    out_bib = tmp_path / "clean_no_rdf.bib"

    report = sanitize_bib(sample_bib, out_bib, rdf_path=None, emergency_mode=False)

    # Domain title should be flagged for manual review
    assert "domain_title" in report["manual_review"]

    # Stub title should also be flagged
    assert "stub_title" in report["manual_review"]

def test_emergency_mode_requires_rdf(sample_bib, tmp_path):
    """Test that emergency mode crashes if RDF not provided."""
    out_bib = tmp_path / "clean_emergency.bib"

    with pytest.raises(RuntimeError, match="EMERGENCY MODE: RDF file path is REQUIRED"):
        sanitize_bib(sample_bib, out_bib, rdf_path=None, emergency_mode=True)

def test_emergency_mode_crashes_if_rdf_missing(sample_bib, tmp_path):
    """Test that emergency mode crashes if RDF file doesn't exist."""
    out_bib = tmp_path / "clean_emergency.bib"
    fake_rdf = tmp_path / "nonexistent.rdf"

    with pytest.raises(FileNotFoundError, match="EMERGENCY MODE: RDF file not found"):
        sanitize_bib(sample_bib, out_bib, rdf_path=fake_rdf, emergency_mode=True)

def test_emergency_mode_crashes_if_rdf_empty(sample_bib, tmp_path):
    """Test that emergency mode crashes if RDF file is empty."""
    out_bib = tmp_path / "clean_emergency.bib"
    empty_rdf = tmp_path / "empty.rdf"
    empty_rdf.write_text("<rdf:RDF></rdf:RDF>")  # Empty but valid XML

    with pytest.raises(RuntimeError, match="EMERGENCY MODE: RDF file contains no entries"):
        sanitize_bib(sample_bib, out_bib, rdf_path=empty_rdf, emergency_mode=True)

def test_emergency_mode_outputs_not_found_list(sample_bib, sample_rdf, tmp_path, capsys):
    """Test that emergency mode outputs list of citations not in RDF."""
    out_bib = tmp_path / "clean_emergency.bib"

    # sample_bib has entries that won't be in sample_rdf
    report = sanitize_bib(sample_bib, out_bib, rdf_path=sample_rdf, emergency_mode=True)

    # Should have not_found_in_rdf entries
    assert len(report["not_found_in_rdf"]) > 0

    # Should print output to console
    captured = capsys.readouterr()
    assert "Citations NOT found in RDF" in captured.out
    assert "MANUAL REVIEW REQUIRED" in captured.out

    # Check structure of not_found items
    for item in report["not_found_in_rdf"]:
        assert "key" in item
        assert "url" in item
        assert "normalized_url" in item
        assert "title" in item

def test_output_files_created(sample_bib, tmp_path, sample_rdf):
    """Test that output files are created correctly."""
    out_bib = tmp_path / "clean2.bib"
    report_path = tmp_path / "report2.json"

    report = sanitize_bib(sample_bib, out_bib, rdf_path=sample_rdf)

    with open(report_path, "w", encoding="utf8") as f:
        json.dump(report, f, indent=2)

    assert out_bib.exists()
    assert report_path.exists()

    loaded_report = json.loads(report_path.read_text())
    assert "fixed_orgs" in loaded_report

def test_duplicates_not_merged(sample_bib, sample_rdf, tmp_path):
    """CRITICAL: Test that duplicates are FLAGGED but NOT auto-merged."""
    out_bib = tmp_path / "clean_dup_test.bib"

    report = sanitize_bib(sample_bib, out_bib, rdf_path=sample_rdf)

    # Load output
    with open(out_bib, encoding="utf8") as f:
        bib_db = bibtexparser.load(f)

    entries = {e["ID"]: e for e in bib_db.entries}

    # Both duplicate entries should still exist (not merged)
    assert "duplicate_a" in entries
    assert "duplicate_b" in entries

    # Both should be in duplicates report
    assert len(report["duplicates"]) >= 1

    # Check that duplicate report has MANUAL_REVIEW_REQUIRED action
    for dup in report["duplicates"]:
        assert dup["action"] == "MANUAL_REVIEW_REQUIRED"
