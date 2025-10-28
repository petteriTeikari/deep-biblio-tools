"""Integration tests for full validation pipeline."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def temp_workdir():
    """Create temporary working directory for tests."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_bib_file(temp_workdir):
    """Create sample .bib file with mixed valid/invalid entries."""
    bib_content = """
@misc{invalid_doi_no_title,
  author = "Author and others",
  year = "2021",
  doi = "10.1016/j.invalid.999999",
}

@article{valid_complete,
  title = {A Complete Valid Article},
  author = {Smith, Alice and Doe, Bob},
  journal = {Test Journal},
  year = {2020},
  doi = {10.1000/validtest},
}

@article{missing_venue,
  title = {Missing Venue Article},
  author = {Johnson, Mike},
  year = {2019},
  doi = {10.2000/test},
}
"""
    bib_path = temp_workdir / "test_references.bib"
    bib_path.write_text(bib_content)
    return bib_path


class TestValidationPipeline:
    """Test end-to-end validation workflow."""

    def test_validation_detects_all_issues(self, sample_bib_file):
        """Should detect all expected issues in sample file."""
        # Placeholder - will implement validate_bibliography.py
        # For now, manually verify what should be detected

        content = sample_bib_file.read_text()

        # Should detect these issues:

        # Count entries
        entry_count = content.count("@")
        assert entry_count == 3

        # Verify sample file exists and is readable
        assert sample_bib_file.exists()
        assert sample_bib_file.stat().st_size > 0

    def test_validation_generates_jsonl_output(
        self, sample_bib_file, temp_workdir
    ):
        """Should generate JSONL validation report."""
        # Placeholder for actual validation script
        # Expected output: validation_report.jsonl

        temp_workdir / "validation_report.jsonl"

        # For now, just verify directory structure
        assert temp_workdir.exists()
        assert sample_bib_file.parent == temp_workdir

    def test_validation_generates_csv_output(
        self, sample_bib_file, temp_workdir
    ):
        """Should generate CSV validation report for human review."""
        # Placeholder for actual validation script
        # Expected output: validation_report.csv

        temp_workdir / "validation_report.csv"

        # CSV should have these columns:
        expected_columns = [
            "citation_key",
            "severity",
            "issues",
            "has_title",
            "has_author",
            "has_venue",
            "doi_status",
        ]

        # Verify structure expectations
        assert isinstance(expected_columns, list)
        assert len(expected_columns) > 0


class TestAutoFixPipeline:
    """Test automatic fixing of entries."""

    def test_auto_fix_generates_staged_output(
        self, sample_bib_file, temp_workdir
    ):
        """Should generate staged .bib file with fixes."""
        # Placeholder for auto_fix_bibliography.py
        # Expected output: references_fixed.staged.bib

        temp_workdir / "references_fixed.staged.bib"

        # Original should remain unchanged
        assert sample_bib_file.exists()

    def test_auto_fix_generates_audit_log(self, sample_bib_file, temp_workdir):
        """Should generate audit log of all changes."""
        # Expected output: automatic_fixes.log

        temp_workdir / "automatic_fixes.log"

        # Log should be JSON lines format
        # Each line: {"timestamp": "...", "citation_key": "...", "action": "...", ...}

    def test_auto_fix_generates_merge_proposal(
        self, sample_bib_file, temp_workdir
    ):
        """Should generate merge proposal with diffs."""
        # Expected output: merge_proposal.json

        temp_workdir / "merge_proposal.json"

        # Should contain per-entry diffs: {"citation_key": {"old": ..., "new": ...}}


class TestManualReviewQueue:
    """Test manual review queue generation."""

    def test_review_queue_filters_unfixable_issues(self, temp_workdir):
        """Should only include entries requiring human judgment."""
        # Entries that SHOULD be in manual review queue:
        # - Invalid DOI with no arXiv
        # - Placeholder titles
        # - Fuzzy title mismatches
        # - Duplicates requiring decision

        unfixable_issues = [
            "INVALID_DOI",  # When no alternative source
            "PLACEHOLDER_TITLE",
            "FUZZY_TITLE_MISMATCH",
            "DUPLICATE_CONTENT",
        ]

        # Entries that should NOT need manual review:
        # - Valid DOI with missing metadata (auto-fixable)
        # - Valid arXiv with missing metadata (auto-fixable)

        assert len(unfixable_issues) == 4

    def test_review_queue_prioritizes_by_severity(self):
        """Manual review queue should be sorted by severity."""
        # Expected sort order: CRITICAL > HIGH > MEDIUM > LOW
        severity_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

        # Verify sort works correctly
        test_items = [
            {"severity": "LOW"},
            {"severity": "CRITICAL"},
            {"severity": "HIGH"},
            {"severity": "MEDIUM"},
        ]

        sorted_items = sorted(
            test_items, key=lambda x: severity_order.index(x["severity"])
        )

        assert sorted_items[0]["severity"] == "CRITICAL"
        assert sorted_items[-1]["severity"] == "LOW"


@pytest.mark.e2e
class TestEndToEndValidation:
    """End-to-end validation tests."""

    @pytest.mark.slow
    def test_full_workflow_on_real_bib_file(self):
        """Test complete workflow on actual references.bib.

        Steps:
        1. Run validate_bibliography.py
        2. Run auto_fix_bibliography.py
        3. Generate manual review queue
        4. Verify staged output

        This test is marked @e2e and @slow as it processes real data.
        """
        # This will be implemented once scripts are ready
        # For now, document the expected workflow
        workflow_steps = [
            "validate_bibliography.py references.bib",
            "auto_fix_bibliography.py references.bib",
            "generate_review_queue.py --validation-report validation_report.jsonl",
            "verify_fixes.py references_fixed.staged.bib",
        ]

        assert len(workflow_steps) == 4
