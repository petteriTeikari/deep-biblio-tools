"""Unit tests for BibTeXEntryValidator - final BibTeX quality gate.

Tests validate that generated BibTeX entries meet quality standards
BEFORE LaTeX compilation.
"""

from pathlib import Path

import pytest
from src.converters.md_to_latex.bibtex_entry_validator import (
    BibTeXEntryValidator,
)


@pytest.fixture
def validator():
    """Create BibTeXEntryValidator instance."""
    return BibTeXEntryValidator()


@pytest.fixture
def tmp_bib_file(tmp_path):
    """Create a temporary BibTeX file for testing."""

    def _create_bib(entries: list[dict]) -> Path:
        """Helper to create BibTeX file from entry dicts."""
        bib_path = tmp_path / "test_references.bib"

        # Convert entries to BibTeX format
        bib_lines = []
        for entry in entries:
            entry_type = entry.get("ENTRYTYPE", "misc")
            entry_id = entry.get("ID", "unknown")

            bib_lines.append(f"@{entry_type}{{{entry_id},")
            for key, value in entry.items():
                if key not in ["ENTRYTYPE", "ID"]:
                    # Simple escaping for BibTeX values
                    safe_value = str(value).replace("{", "(").replace("}", ")")
                    bib_lines.append(f'  {key} = "{safe_value}",')
            bib_lines.append("}")
            bib_lines.append("")

        bib_path.write_text("\n".join(bib_lines))
        return bib_path

    return _create_bib


class TestTemporaryKeyDetection:
    """Test detection of temporary citation keys."""

    def test_temp_key_detected(self, validator, tmp_bib_file):
        """Test that 'Temp' keys are flagged as CRITICAL."""
        entries = [
            {
                "ID": "axiosTemp2025",
                "title": "Some Article Title",
                "author": "Axios",
                "year": "2025",
            }
        ]
        bib_path = tmp_bib_file(entries)

        results = validator.validate_file(bib_path)

        assert results["critical_count"] > 0
        assert "axiosTemp2025" in results["issues_by_entry"]
        issues = results["issues_by_entry"]["axiosTemp2025"]
        assert any("temporary" in i.lower() and "CRITICAL" in i for i in issues)

    def test_dryrun_key_detected(self, validator, tmp_bib_file):
        """Test that 'dryrun_' keys are flagged as CRITICAL."""
        entries = [
            {
                "ID": "dryrun_1761780981742",
                "title": "European Commission Document",
                "author": "European Commission",
                "year": "2024",
            }
        ]
        bib_path = tmp_bib_file(entries)

        results = validator.validate_file(bib_path)

        assert results["critical_count"] > 0
        issues = results["issues_by_entry"]["dryrun_1761780981742"]
        assert any("temporary" in i.lower() for i in issues)

    def test_valid_better_bibtex_key_passes(self, validator, tmp_bib_file):
        """Test that proper Better BibTeX keys pass validation."""
        entries = [
            {
                "ID": "adisornDigitalProductPassport2021",
                "title": "Digital Product Passport: The Ticket to Achieving a Circular Economy",
                "author": "Adisorn, Travis and Thabet, Lara and Pagoropoulos, Alexis",
                "year": "2021",
            }
        ]
        bib_path = tmp_bib_file(entries)

        results = validator.validate_file(bib_path)

        # Should have no CRITICAL issues (may have warnings about key length if <15 chars)
        assert results["critical_count"] == 0


class TestStubTitleDetection:
    """Test detection of stub titles from failed metadata extraction."""

    def test_web_page_by_detected(self, validator, tmp_bib_file):
        """Test that 'Web page by X' is flagged as CRITICAL."""
        entries = [
            {
                "ID": "axios2025",
                "title": "Web page by Axios",
                "author": "Axios",
                "year": "2025",
            }
        ]
        bib_path = tmp_bib_file(entries)

        results = validator.validate_file(bib_path)

        assert results["critical_count"] > 0
        issues = results["issues_by_entry"]["axios2025"]
        assert any(
            "stub title" in i.lower() and "CRITICAL" in i for i in issues
        )

    def test_webpage_by_variant_detected(self, validator, tmp_bib_file):
        """Test that 'Webpage by X' variant is also detected."""
        entries = [
            {
                "ID": "example2024",
                "title": "Webpage by European Parliament",
                "author": "European Parliament",
                "year": "2024",
            }
        ]
        bib_path = tmp_bib_file(entries)

        results = validator.validate_file(bib_path)

        assert results["critical_count"] > 0
        issues = results["issues_by_entry"]["example2024"]
        assert any("stub" in i.lower() for i in issues)


class TestDomainAsTitleDetection:
    """Test detection of domain names used as titles."""

    def test_amazon_de_detected(self, validator, tmp_bib_file):
        """Test that 'Amazon.de' as title is flagged."""
        entries = [
            {
                "ID": "fletcher2016",
                "title": "Amazon.de",
                "author": "Fletcher, Kate",
                "year": "2016",
            }
        ]
        bib_path = tmp_bib_file(entries)

        results = validator.validate_file(bib_path)

        assert results["critical_count"] > 0
        issues = results["issues_by_entry"]["fletcher2016"]
        assert any("domain" in i.lower() and "CRITICAL" in i for i in issues)

    def test_domain_extension_ending_detected(self, validator, tmp_bib_file):
        """Test that titles ending with .com/.org are flagged."""
        entries = [
            {
                "ID": "test2024",
                "title": "example.com",
                "author": "Someone",
                "year": "2024",
            }
        ]
        bib_path = tmp_bib_file(entries)

        results = validator.validate_file(bib_path)

        assert results["critical_count"] > 0
        issues = results["issues_by_entry"]["test2024"]
        assert any("domain" in i.lower() for i in issues)

    def test_bbc_com_exact_match_detected(self, validator, tmp_bib_file):
        """Test that exact domain name 'BBC.com' is flagged."""
        entries = [
            {
                "ID": "bbc2023",
                "title": "BBC.com",
                "author": "BBC",
                "year": "2023",
            }
        ]
        bib_path = tmp_bib_file(entries)

        results = validator.validate_file(bib_path)

        assert results["critical_count"] > 0


class TestMissingFieldsDetection:
    """Test detection of missing or empty required fields."""

    def test_empty_title_detected(self, validator, tmp_bib_file):
        """Test that empty title is flagged as CRITICAL."""
        entries = [
            {
                "ID": "notitle2024",
                "title": "",
                "author": "Author",
                "year": "2024",
            }
        ]
        bib_path = tmp_bib_file(entries)

        results = validator.validate_file(bib_path)

        assert results["critical_count"] > 0
        issues = results["issues_by_entry"]["notitle2024"]
        assert any("empty" in i.lower() and "CRITICAL" in i for i in issues)

    def test_very_short_title_detected(self, validator, tmp_bib_file):
        """Test that suspiciously short titles are flagged."""
        entries = [
            {
                "ID": "short2024",
                "title": "AI",
                "author": "Author",
                "year": "2024",
            }
        ]
        bib_path = tmp_bib_file(entries)

        results = validator.validate_file(bib_path)

        assert results["critical_count"] > 0
        issues = results["issues_by_entry"]["short2024"]
        assert any("short" in i.lower() and "CRITICAL" in i for i in issues)

    def test_unknown_author_warning(self, validator, tmp_bib_file):
        """Test that 'Unknown' author generates WARNING."""
        entries = [
            {
                "ID": "unknown2024",
                "title": "Some Valid Title Here",
                "author": "Unknown",
                "year": "2024",
            }
        ]
        bib_path = tmp_bib_file(entries)

        results = validator.validate_file(bib_path)

        # Should be WARNING, not CRITICAL
        assert results["warning_count"] > 0
        issues = results["issues_by_entry"]["unknown2024"]
        assert any("WARNING" in i and "author" in i.lower() for i in issues)

    def test_anonymous_author_warning(self, validator, tmp_bib_file):
        """Test that 'Anonymous' author generates WARNING."""
        entries = [
            {
                "ID": "anon2024",
                "title": "Some Valid Title Here",
                "author": "Anonymous",
                "year": "2024",
            }
        ]
        bib_path = tmp_bib_file(entries)

        results = validator.validate_file(bib_path)

        assert results["warning_count"] > 0


class TestBetterBibTeXKeyValidation:
    """Test Better BibTeX key format validation."""

    def test_short_key_warning(self, validator, tmp_bib_file):
        """Test that short keys (<15 chars) generate WARNING."""
        entries = [
            {
                "ID": "smith2024",  # Only 10 chars - likely not Better BibTeX
                "title": "Valid Article Title Here",
                "author": "Smith, John",
                "year": "2024",
            }
        ]
        bib_path = tmp_bib_file(entries)

        results = validator.validate_file(bib_path)

        # Should be WARNING (short key is suspicious but not blocking)
        assert results["warning_count"] > 0
        issues = results["issues_by_entry"]["smith2024"]
        assert any("WARNING" in i and "short key" in i.lower() for i in issues)

    def test_long_descriptive_key_passes(self, validator, tmp_bib_file):
        """Test that proper Better BibTeX keys don't trigger warnings."""
        entries = [
            {
                "ID": "niinimaekiEnvironmentalSustainabilityTextile2020",
                "title": "Environmental Sustainability of Textile and Clothing Supply Chain",
                "author": "Niinimäki, Kirsi and Peters, Greg",
                "year": "2020",
            }
        ]
        bib_path = tmp_bib_file(entries)

        results = validator.validate_file(bib_path)

        # No warning about key length (≥15 chars)
        if (
            "niinimaekiEnvironmentalSustainabilityTextile2020"
            in results["issues_by_entry"]
        ):
            issues = results["issues_by_entry"][
                "niinimaekiEnvironmentalSustainabilityTextile2020"
            ]
            key_warnings = [i for i in issues if "short key" in i.lower()]
            assert len(key_warnings) == 0


class TestMixedQualityFile:
    """Test validation of files with both valid and invalid entries."""

    def test_mixed_entries_counted_correctly(self, validator, tmp_bib_file):
        """Test that valid and invalid entries are counted separately."""
        entries = [
            # Good entry
            {
                "ID": "goodEntryWithLongDescriptiveKey2024",
                "title": "A Proper Academic Paper Title That Is Descriptive",
                "author": "Smith, John and Doe, Jane",
                "year": "2024",
            },
            # Bad entry - stub title
            {
                "ID": "badEntry2024",
                "title": "Web page by BBC",
                "author": "BBC",
                "year": "2024",
            },
            # Bad entry - temp key
            {
                "ID": "axiosTemp2025",
                "title": "Valid Title But Temp Key",
                "author": "Axios",
                "year": "2025",
            },
            # Warning-level entry - Unknown author
            {
                "ID": "warningEntry2024",
                "title": "Valid Title But No Author",
                "author": "Unknown",
                "year": "2024",
            },
        ]
        bib_path = tmp_bib_file(entries)

        results = validator.validate_file(bib_path)

        assert results["total_entries"] == 4
        assert results["critical_count"] >= 2  # stub title + temp key
        assert results["warning_count"] >= 1  # Unknown author
        assert len(results["issues_by_entry"]) == 3  # 3 problematic entries


class TestFileOperations:
    """Test file handling and error conditions."""

    def test_nonexistent_file_raises_error(self, validator):
        """Test that nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            validator.validate_file("/nonexistent/path/to/file.bib")

    def test_has_critical_issues_method(self, validator, tmp_bib_file):
        """Test has_critical_issues convenience method."""
        # File with CRITICAL issue
        bad_entries = [
            {
                "ID": "temp2024",
                "title": "Web page by Test",
                "author": "Test",
                "year": "2024",
            }
        ]
        bad_path = tmp_bib_file(bad_entries)
        assert validator.has_critical_issues(bad_path) is True

        # File without CRITICAL issues
        good_entries = [
            {
                "ID": "goodEntryWithDescriptiveLongKey2024",
                "title": "Proper Academic Title",
                "author": "Author, Name",
                "year": "2024",
            }
        ]
        good_path = tmp_bib_file(good_entries)
        assert validator.has_critical_issues(good_path) is False


class TestRealWorldScenarios:
    """Test based on actual problematic entries from troubleshooting doc."""

    def test_axios_example_from_doc(self, validator, tmp_bib_file):
        """Test actual Axios example from bibliography-quality-analysis.md."""
        entries = [
            {
                "ID": "axiosTemp2025",
                "title": "Web page by Axios",
                "author": "Axios",
                "year": "2025",
                "journal": "Web page",
                "url": "https://www.axios.com/2025/02/20/ai-agi-timeline-promises-openai-anthropic-deepmind",
            }
        ]
        bib_path = tmp_bib_file(entries)

        results = validator.validate_file(bib_path)

        # Should have multiple CRITICAL issues
        assert results["critical_count"] >= 2  # Temp key + stub title
        issues = results["issues_by_entry"]["axiosTemp2025"]
        assert any("temporary" in i.lower() for i in issues)
        assert any("stub title" in i.lower() for i in issues)

    def test_fletcher_amazon_example_from_doc(self, validator, tmp_bib_file):
        """Test actual Fletcher/Amazon example from troubleshooting doc."""
        entries = [
            {
                "ID": "fletcher_craft_2016",
                "title": "Amazon.de",
                "author": "Fletcher, Kate",
                "year": "2016",
                "journal": "Web page",
                "url": "https://www.amazon.de/-/en/Craft-Use-Post-Growth-Kate-Fletcher/dp/1138021016",
            }
        ]
        bib_path = tmp_bib_file(entries)

        results = validator.validate_file(bib_path)

        # Should flag domain-as-title
        assert results["critical_count"] > 0
        issues = results["issues_by_entry"]["fletcher_craft_2016"]
        assert any("domain" in i.lower() and "CRITICAL" in i for i in issues)

    def test_dryrun_european_commission_example(self, validator, tmp_bib_file):
        """Test actual dry-run entry from troubleshooting doc."""
        entries = [
            {
                "ID": "dryrun_1761780981742",
                "title": "",  # Empty title
                "author": "European Commission",
                "year": "2024",
                "journal": "Web page",
                "url": "https://commission.europa.eu/energy-climate-change-environment/...",
            }
        ]
        bib_path = tmp_bib_file(entries)

        results = validator.validate_file(bib_path)

        # Should have CRITICAL issues: temp key + empty title
        assert results["critical_count"] >= 2
        issues = results["issues_by_entry"]["dryrun_1761780981742"]
        assert any("temporary" in i.lower() for i in issues)
        assert any("empty" in i.lower() for i in issues)
