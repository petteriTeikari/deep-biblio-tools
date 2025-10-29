"""Markdown knowledge base URL validator.

Validates citation URLs for format correctness BEFORE any consumption.
Independent of conversion processes - validates the knowledge base itself.

Core principle: Markdown is the knowledge base for LLM context engineering,
not just input to a conversion pipeline. Quality must be ensured at source.

Primary focus: Format validation (fast, suitable for pre-commit hooks).
Network validation is optional and expensive (Phase 3).
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List
import logging
import re

logger = logging.getLogger(__name__)


class ValidationIssue(str, Enum):
    """Types of validation issues."""
    INVALID_ARXIV_FORMAT = "invalid_arxiv_format"
    INVALID_DOI_FORMAT = "invalid_doi_format"
    INVALID_URL_SCHEME = "invalid_url_scheme"
    URL_NOT_FOUND = "url_not_found"  # Optional network check


@dataclass
class CitationIssue:
    """Single citation validation issue."""
    line_number: int
    url: str
    citation_text: str  # Full [Author (Year)](URL)
    issue_type: ValidationIssue
    severity: str  # CRITICAL, WARNING, INFO
    message: str
    suggested_fix: str = None


class MarkdownKBValidator:
    """Validates markdown knowledge base quality.

    Focus: Format validation (arXiv, DOI, URL schemes).
    Default: NO network checks (fast for pre-commit hooks).
    """

    def __init__(self, enable_network_checks: bool = False):
        """Initialize validator.

        Args:
            enable_network_checks: Enable expensive network validation.
                                  Default False for pre-commit speed.
        """
        self.enable_network_checks = enable_network_checks

    def validate_file(self, path: Path) -> List[CitationIssue]:
        """Validate all citations in a markdown file.

        Returns list of issues found (empty if all valid).
        """
        issues = []

        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, start=1):
                    # Extract citations: [text](url)
                    citations = self._extract_citations(line)

                    for citation_text, url in citations:
                        # Validate URL format
                        issue = self._validate_url(url, citation_text, line_num)
                        if issue:
                            issues.append(issue)
        except Exception as e:
            logger.error(f"Error reading {path}: {e}")
            # Return error as issue
            issues.append(CitationIssue(
                line_number=0,
                url="",
                citation_text="",
                issue_type=ValidationIssue.INVALID_URL_SCHEME,
                severity="CRITICAL",
                message=f"Failed to read file: {e}"
            ))

        return issues

    def _extract_citations(self, line: str) -> List[tuple]:
        """Extract all [text](url) patterns from line.

        Returns list of (citation_text, url) tuples.
        """
        # Pattern: [text](url)
        pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
        matches = re.findall(pattern, line)
        return matches

    def _validate_url(
        self, url: str, citation_text: str, line_num: int
    ) -> CitationIssue | None:
        """Validate single URL.

        Returns CitationIssue if invalid, None if valid.
        """
        # Check basic URL scheme
        if not url.startswith(('http://', 'https://')):
            return CitationIssue(
                line_number=line_num,
                url=url,
                citation_text=f"[{citation_text}]({url})",
                issue_type=ValidationIssue.INVALID_URL_SCHEME,
                severity="CRITICAL",
                message="URL must start with http:// or https://"
            )

        # Check arXiv format
        if 'arxiv.org/abs/' in url:
            return self._validate_arxiv_url(url, citation_text, line_num)

        # Check DOI format
        elif 'doi.org/' in url:
            return self._validate_doi_url(url, citation_text, line_num)

        # Other URLs - basic validation passed
        return None

    def _validate_arxiv_url(
        self, url: str, citation_text: str, line_num: int
    ) -> CitationIssue | None:
        """Validate arXiv URL format.

        Valid formats:
        - https://arxiv.org/abs/2412.02646 (YYMM.NNNNN)
        - https://arxiv.org/abs/2412.02646v1 (with version)
        - https://arxiv.org/abs/1234.5678 (old format YYMM.NNNN)

        Invalid formats (October 26 patterns):
        - https://arxiv.org/abs/2025.mcp.taxonomy (non-numeric)
        - https://arxiv.org/abs/2025.mpma (too short)
        """
        # Extract arXiv ID (numeric only)
        match = re.search(r'arxiv\.org/abs/([0-9]+\.[0-9]+(?:v[0-9]+)?)', url)

        if not match:
            # Has arxiv.org/abs/ but no valid numeric ID
            # This catches October 26 patterns like "2025.mcp.taxonomy"
            arxiv_id = url.split('arxiv.org/abs/')[-1] if '/abs/' in url else 'unknown'
            return CitationIssue(
                line_number=line_num,
                url=url,
                citation_text=f"[{citation_text}]({url})",
                issue_type=ValidationIssue.INVALID_ARXIV_FORMAT,
                severity="CRITICAL",
                message=f"Invalid arXiv ID format: '{arxiv_id}'. Expected: YYMM.NNNNN (e.g., 2412.02646). Contains non-numeric characters.",
                suggested_fix="Check if this is a hallucinated URL. Search arXiv for the actual paper."
            )

        # Validate year/month range
        arxiv_id = match.group(1).rstrip('v0123456789')  # Remove version
        year_month = arxiv_id.split('.')[0]

        try:
            year = int(year_month[:2])
            month = int(year_month[2:])

            # Valid range: 07 (2007) to 30 (2030)
            # arXiv started in 1991, but new format started in 2007
            if not (7 <= year <= 30 and 1 <= month <= 12):
                return CitationIssue(
                    line_number=line_num,
                    url=url,
                    citation_text=f"[{citation_text}]({url})",
                    issue_type=ValidationIssue.INVALID_ARXIV_FORMAT,
                    severity="CRITICAL",
                    message=f"Invalid year/month in arXiv ID: {year_month}. Year should be 07-30 (2007-2030), month 01-12."
                )
        except (ValueError, IndexError):
            return CitationIssue(
                line_number=line_num,
                url=url,
                citation_text=f"[{citation_text}]({url})",
                issue_type=ValidationIssue.INVALID_ARXIV_FORMAT,
                severity="CRITICAL",
                message=f"Malformed arXiv ID: {arxiv_id}"
            )

        return None  # Valid

    def _validate_doi_url(
        self, url: str, citation_text: str, line_num: int
    ) -> CitationIssue | None:
        """Validate DOI URL format.

        Valid: https://doi.org/10.XXXX/...
        """
        # DOI format: 10.XXXX/...
        if not re.search(r'doi\.org/(10\.[0-9]+/[^\s]+)', url):
            return CitationIssue(
                line_number=line_num,
                url=url,
                citation_text=f"[{citation_text}]({url})",
                issue_type=ValidationIssue.INVALID_DOI_FORMAT,
                severity="CRITICAL",
                message="Invalid DOI format. Expected: https://doi.org/10.XXXX/..."
            )

        return None  # Valid


def generate_report(issues: List[CitationIssue], total_citations: int) -> str:
    """Generate human-readable quality report.

    Args:
        issues: List of validation issues
        total_citations: Total number of citations checked

    Returns:
        Formatted report string
    """
    report = []
    report.append("=" * 80)
    report.append("MARKDOWN KNOWLEDGE BASE QUALITY REPORT")
    report.append("=" * 80)
    report.append(f"Total citations checked: {total_citations}")
    report.append(f"Issues found: {len(issues)}")
    report.append("")

    if not issues:
        report.append("✅ All citations validated successfully!")
        report.append("✅ Knowledge base is clean and ready for LLM context engineering.")
        report.append("=" * 80)
        return "\n".join(report)

    # Group by severity
    critical = [i for i in issues if i.severity == "CRITICAL"]
    warnings = [i for i in issues if i.severity == "WARNING"]
    info = [i for i in issues if i.severity == "INFO"]

    if critical:
        report.append(f"❌ CRITICAL ISSUES ({len(critical)}) - Likely hallucinations or format errors:")
        report.append("-" * 80)
        for issue in critical:
            report.append(f"\nLine {issue.line_number}:")
            report.append(f"  Citation: {issue.citation_text}")
            report.append(f"  URL: {issue.url}")
            report.append(f"  Issue: {issue.message}")
            if issue.suggested_fix:
                report.append(f"  💡 Fix: {issue.suggested_fix}")
        report.append("")

    if warnings:
        report.append(f"⚠️  WARNINGS ({len(warnings)}) - Need attention:")
        report.append("-" * 80)
        for issue in warnings:
            report.append(f"Line {issue.line_number}: {issue.message}")
        report.append("")

    if info:
        report.append(f"ℹ️  INFO ({len(info)}):")
        report.append("-" * 80)
        for issue in info:
            report.append(f"Line {issue.line_number}: {issue.message}")
        report.append("")

    report.append("=" * 80)
    report.append("NEXT STEPS:")
    report.append("1. Fix CRITICAL issues before committing")
    report.append("2. Review WARNINGS for potential problems")
    report.append("3. Re-run validation after fixes")
    report.append("=" * 80)

    return "\n".join(report)
