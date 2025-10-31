"""Phase 1 MVP: Format validation tests.

CRITICAL: October 26 regression tests must pass to prevent garbage entries.

Test coverage:
- October 26 hallucination patterns (MUST catch)
- arXiv format validation (numeric IDs only)
- DOI format validation
- URL scheme validation
- Performance benchmarks (<100ms per file)
- CLI integration (exit codes, reports)
"""

import tempfile
import time
from pathlib import Path

import pytest
from click.testing import CliRunner
from src.kb_quality.cli import validate
from src.kb_quality.url_validator import (
    CitationIssue,
    MarkdownKBValidator,
    ValidationIssue,
    generate_report,
)

# ============================================================================
# October 26 Regression Tests - CRITICAL
# ============================================================================


class TestOctober26Regression:
    """CRITICAL: Tests that prevent the October 26 incident from recurring.

    October 26 incident: Three hallucinated arXiv URLs with non-numeric IDs
    entered the knowledge base:
    - https://arxiv.org/abs/2025.mcp.taxonomy
    - https://arxiv.org/abs/2025.mcp.privilege
    - https://arxiv.org/abs/2025.mpma

    These MUST be caught by format validation.
    """

    def test_october26_pattern_taxonomy(self):
        """Catch arXiv ID with non-numeric suffix: 2025.mcp.taxonomy"""
        validator = MarkdownKBValidator()

        markdown = (
            "[Zhao et al., 2025](https://arxiv.org/abs/2025.mcp.taxonomy)"
        )
        citations = validator._extract_citations(markdown)
        assert len(citations) == 1

        citation_text, url = citations[0]
        issue = validator._validate_url(url, citation_text, 1)

        assert issue is not None, "October 26 pattern MUST be caught"
        assert issue.severity == "CRITICAL"
        assert issue.issue_type == ValidationIssue.INVALID_ARXIV_FORMAT
        assert "non-numeric" in issue.message.lower()
        assert "2025.mcp.taxonomy" in issue.message

    def test_october26_pattern_privilege(self):
        """Catch arXiv ID with non-numeric suffix: 2025.mcp.privilege"""
        validator = MarkdownKBValidator()

        markdown = "[Li et al., 2025](https://arxiv.org/abs/2025.mcp.privilege)"
        citations = validator._extract_citations(markdown)
        citation_text, url = citations[0]
        issue = validator._validate_url(url, citation_text, 1)

        assert issue is not None, "October 26 pattern MUST be caught"
        assert issue.severity == "CRITICAL"
        assert "2025.mcp.privilege" in issue.message

    def test_october26_pattern_mpma(self):
        """Catch arXiv ID with non-numeric suffix: 2025.mpma"""
        validator = MarkdownKBValidator()

        markdown = "[Wang et al., 2025](https://arxiv.org/abs/2025.mpma)"
        citations = validator._extract_citations(markdown)
        citation_text, url = citations[0]
        issue = validator._validate_url(url, citation_text, 1)

        assert issue is not None, "October 26 pattern MUST be caught"
        assert issue.severity == "CRITICAL"
        assert "2025.mpma" in issue.message

    def test_october26_suggested_fixes(self):
        """Verify suggested fixes mention hallucination checking"""
        validator = MarkdownKBValidator()

        markdown = "[Test](https://arxiv.org/abs/2025.hallucinated)"
        citations = validator._extract_citations(markdown)
        citation_text, url = citations[0]
        issue = validator._validate_url(url, citation_text, 1)

        assert issue.suggested_fix is not None
        assert "hallucinated" in issue.suggested_fix.lower()

    def test_october26_all_patterns_in_file(self):
        """Validate file with all 3 October 26 patterns"""
        validator = MarkdownKBValidator()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(
                """# Test
[Zhao et al., 2025](https://arxiv.org/abs/2025.mcp.taxonomy)
[Li et al., 2025](https://arxiv.org/abs/2025.mcp.privilege)
[Wang et al., 2025](https://arxiv.org/abs/2025.mpma)
[Good (2024)](https://arxiv.org/abs/2412.02646)
"""
            )
            temp_path = Path(f.name)

        try:
            issues = validator.validate_file(temp_path)

            # MUST find exactly 3 issues (the bad ones)
            assert len(issues) == 3, f"Expected 3 issues, found {len(issues)}"

            # All must be CRITICAL
            assert all(i.severity == "CRITICAL" for i in issues)

            # Check specific IDs are caught
            bad_ids = {"2025.mcp.taxonomy", "2025.mcp.privilege", "2025.mpma"}
            found_ids = {
                i.url.split("/abs/")[-1] for i in issues if "/abs/" in i.url
            }
            assert found_ids == bad_ids

        finally:
            temp_path.unlink()


# ============================================================================
# arXiv Format Validation
# ============================================================================


class TestArxivFormatValidation:
    """Test arXiv URL format validation (numeric IDs only)."""

    @pytest.mark.parametrize(
        "arxiv_id",
        [
            "2412.02646",  # Standard format YYMM.NNNNN
            "2412.02646v1",  # With version
            "2412.02646v2",  # Different version
            "1207.5678",  # Old format YYMM.NNNN (2012, July)
            "0704.0001",  # First arXiv paper (new format)
            "2501.12345",  # Future date (valid range)
        ],
    )
    def test_valid_arxiv_ids(self, arxiv_id):
        """Valid numeric arXiv IDs should pass"""
        validator = MarkdownKBValidator()
        url = f"https://arxiv.org/abs/{arxiv_id}"
        issue = validator._validate_arxiv_url(url, "Test", 1)
        assert issue is None, f"{arxiv_id} should be valid"

    @pytest.mark.parametrize(
        "arxiv_id,expected_in_message",
        [
            ("2025.mcp.taxonomy", "non-numeric"),  # October 26 pattern
            ("2025.hallucinated", "non-numeric"),  # Generic hallucination
            ("abc123.def456", "non-numeric"),  # Completely invalid
            ("2025.test.paper", "non-numeric"),  # Multiple dots
            ("paper.2025", "non-numeric"),  # Reversed format
        ],
    )
    def test_invalid_arxiv_ids_non_numeric(self, arxiv_id, expected_in_message):
        """Non-numeric arXiv IDs MUST be caught"""
        validator = MarkdownKBValidator()
        url = f"https://arxiv.org/abs/{arxiv_id}"
        issue = validator._validate_arxiv_url(url, "Test", 1)

        assert issue is not None, f"{arxiv_id} MUST be caught"
        assert issue.severity == "CRITICAL"
        assert expected_in_message in issue.message.lower()

    @pytest.mark.parametrize(
        "arxiv_id",
        [
            "9912.12345",  # Year too far in past
            "3101.12345",  # Year too far in future
            "2413.12345",  # Invalid month (13)
            "2400.12345",  # Invalid month (00)
        ],
    )
    def test_invalid_arxiv_year_month_range(self, arxiv_id):
        """Invalid year/month ranges should be caught"""
        validator = MarkdownKBValidator()
        url = f"https://arxiv.org/abs/{arxiv_id}"
        issue = validator._validate_arxiv_url(url, "Test", 1)

        assert issue is not None, f"{arxiv_id} has invalid year/month"
        assert issue.severity == "CRITICAL"


# ============================================================================
# DOI Format Validation
# ============================================================================


class TestDOIFormatValidation:
    """Test DOI URL format validation."""

    @pytest.mark.parametrize(
        "doi",
        [
            "10.1234/example",
            "10.1109/CVPR.2024.12345",
            "10.48550/arXiv.2412.02646",  # arXiv DOI
            "10.1038/s41586-024-12345-6",  # Nature format
        ],
    )
    def test_valid_dois(self, doi):
        """Valid DOI formats should pass"""
        validator = MarkdownKBValidator()
        url = f"https://doi.org/{doi}"
        issue = validator._validate_doi_url(url, "Test", 1)
        assert issue is None, f"{doi} should be valid"

    @pytest.mark.parametrize(
        "invalid_doi",
        [
            "doi.org/example",  # Missing 10. prefix
            "10/example",  # Missing registry code
            "example/paper",  # No DOI structure
        ],
    )
    def test_invalid_dois(self, invalid_doi):
        """Invalid DOI formats should be caught"""
        validator = MarkdownKBValidator()
        url = f"https://doi.org/{invalid_doi}"
        issue = validator._validate_doi_url(url, "Test", 1)

        assert issue is not None, f"{invalid_doi} should be invalid"
        assert issue.severity == "CRITICAL"


# ============================================================================
# URL Scheme Validation
# ============================================================================


class TestURLSchemeValidation:
    """Test basic URL scheme validation."""

    @pytest.mark.parametrize(
        "url",
        [
            "https://arxiv.org/abs/2412.02646",
            "http://arxiv.org/abs/2412.02646",
            "https://doi.org/10.1234/example",
            "https://example.com/paper",
        ],
    )
    def test_valid_url_schemes(self, url):
        """Valid URL schemes should pass"""
        validator = MarkdownKBValidator()
        issue = validator._validate_url(url, "Test", 1)
        assert (
            issue is None
            or issue.issue_type != ValidationIssue.INVALID_URL_SCHEME
        )

    @pytest.mark.parametrize(
        "url",
        [
            "arxiv.org/abs/2412.02646",  # Missing scheme
            "ftp://example.com/paper",  # Wrong scheme
            "file:///local/paper.pdf",  # Local file
            "javascript:alert(1)",  # XSS attempt
        ],
    )
    def test_invalid_url_schemes(self, url):
        """Invalid URL schemes should be caught"""
        validator = MarkdownKBValidator()
        issue = validator._validate_url(url, "Test", 1)

        assert issue is not None
        assert issue.severity == "CRITICAL"
        assert issue.issue_type == ValidationIssue.INVALID_URL_SCHEME


# ============================================================================
# Citation Extraction
# ============================================================================


class TestCitationExtraction:
    """Test markdown citation extraction."""

    def test_extract_single_citation(self):
        """Extract single [text](url) citation"""
        validator = MarkdownKBValidator()
        line = (
            "See [Smith (2020)](https://arxiv.org/abs/2012.12345) for details"
        )
        citations = validator._extract_citations(line)

        assert len(citations) == 1
        assert citations[0][0] == "Smith (2020)"
        assert citations[0][1] == "https://arxiv.org/abs/2012.12345"

    def test_extract_multiple_citations(self):
        """Extract multiple citations from one line"""
        validator = MarkdownKBValidator()
        line = "[A (2020)](url1) and [B (2021)](url2) show"
        citations = validator._extract_citations(line)

        assert len(citations) == 2
        assert citations[0][0] == "A (2020)"
        assert citations[1][0] == "B (2021)"

    def test_no_citations_in_line(self):
        """Handle lines with no citations"""
        validator = MarkdownKBValidator()
        line = "This is just regular text"
        citations = validator._extract_citations(line)

        assert len(citations) == 0


# ============================================================================
# Performance Tests
# ============================================================================


class TestPerformance:
    """Performance benchmarks for pre-commit speed."""

    def test_single_file_performance(self):
        """Single file validation should be <100ms"""
        validator = MarkdownKBValidator()

        # Create test file with 50 citations
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            for i in range(50):
                f.write(
                    f"[Author {i} (2024)](https://arxiv.org/abs/2412.{i:05d})\n"
                )
            temp_path = Path(f.name)

        try:
            start = time.time()
            validator.validate_file(temp_path)
            elapsed = (time.time() - start) * 1000  # Convert to ms

            assert elapsed < 100, (
                f"Validation took {elapsed:.2f}ms (target: <100ms)"
            )
        finally:
            temp_path.unlink()

    def test_no_network_calls_by_default(self):
        """Default validator should NOT make network calls"""
        validator = MarkdownKBValidator()
        assert validator.enable_network_checks is False


# ============================================================================
# CLI Integration Tests
# ============================================================================


class TestCLIIntegration:
    """Test CLI interface and exit codes."""

    def test_cli_exit_code_on_failure(self):
        """CLI should exit with code 1 when issues found"""
        runner = CliRunner()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write("[Bad](https://arxiv.org/abs/2025.hallucinated)")
            temp_path = Path(f.name)

        try:
            result = runner.invoke(validate, [str(temp_path)])
            assert result.exit_code == 1
            assert "CRITICAL" in result.output
        finally:
            temp_path.unlink()

    def test_cli_exit_code_on_success(self):
        """CLI should exit with code 0 when no issues"""
        runner = CliRunner()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write("[Good (2024)](https://arxiv.org/abs/2412.02646)")
            temp_path = Path(f.name)

        try:
            result = runner.invoke(validate, [str(temp_path)])
            assert result.exit_code == 0
            assert "✅" in result.output
        finally:
            temp_path.unlink()

    def test_cli_verbose_mode(self):
        """Verbose mode should show progress"""
        runner = CliRunner()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write("[Test (2024)](https://arxiv.org/abs/2412.02646)")
            temp_path = Path(f.name)

        try:
            result = runner.invoke(validate, [str(temp_path), "-v"])
            assert "Validating" in result.output
            assert "file(s)" in result.output
        finally:
            temp_path.unlink()

    def test_cli_no_fail_option(self):
        """--no-fail should return exit code 0 even with issues"""
        runner = CliRunner()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write("[Bad](https://arxiv.org/abs/2025.hallucinated)")
            temp_path = Path(f.name)

        try:
            result = runner.invoke(validate, [str(temp_path), "--no-fail"])
            assert result.exit_code == 0
            assert "not failing due to --no-fail" in result.output
        finally:
            temp_path.unlink()


# ============================================================================
# Report Generation
# ============================================================================


class TestReportGeneration:
    """Test report formatting."""

    def test_report_with_no_issues(self):
        """Report should show success when no issues"""
        issues = []
        report = generate_report(issues, total_citations=10)

        assert "✅ All citations validated successfully" in report
        assert "Total citations checked: 10" in report

    def test_report_with_critical_issues(self):
        """Report should highlight CRITICAL issues"""
        issues = [
            CitationIssue(
                line_number=5,
                url="https://arxiv.org/abs/2025.bad",
                citation_text="[Test](url)",
                issue_type=ValidationIssue.INVALID_ARXIV_FORMAT,
                severity="CRITICAL",
                message="Bad format",
                suggested_fix="Fix it",
            )
        ]
        report = generate_report(issues, total_citations=10)

        assert "❌ CRITICAL ISSUES (1)" in report
        assert "Line 5:" in report
        assert "Bad format" in report
        assert "💡 Fix: Fix it" in report

    def test_report_grouping_by_severity(self):
        """Report should group issues by severity"""
        issues = [
            CitationIssue(
                line_number=1,
                url="url1",
                citation_text="[Test1](url1)",
                issue_type=ValidationIssue.INVALID_ARXIV_FORMAT,
                severity="CRITICAL",
                message="Critical issue",
            ),
            CitationIssue(
                line_number=2,
                url="url2",
                citation_text="[Test2](url2)",
                issue_type=ValidationIssue.INVALID_DOI_FORMAT,
                severity="WARNING",
                message="Warning issue",
            ),
        ]
        report = generate_report(issues, total_citations=10)

        # Check CRITICAL section appears before WARNING
        critical_idx = report.find("❌ CRITICAL")
        warning_idx = report.find("⚠️  WARNINGS")
        assert critical_idx < warning_idx
