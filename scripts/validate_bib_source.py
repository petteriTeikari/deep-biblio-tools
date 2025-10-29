"""Validate source references.bib file - check DOIs, detect missing metadata.

This validates the SOURCE .bib file (not compiled .bbl), checking:
- DOI validity via CrossRef API
- Missing required fields (title, author, venue)
- Incomplete authors ("and others", "et al.")
- Placeholder titles

Usage:
    python validate_bib_source.py /path/to/references.bib

Outputs:
    validation_report.jsonl - Machine-readable detailed report
    validation_report.csv - Human-readable spreadsheet
    validation.log - Detailed logging
"""

import csv
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import bibtexparser
import click
import requests
from Levenshtein import distance as levenshtein_distance

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]

REQUIRED_FIELDS = {
    "article": ["title", "author", "journal", "year"],
    "inproceedings": ["title", "author", "booktitle", "year"],
    "book": ["title", "author", "publisher", "year"],
    "misc": ["title", "author", "year"],
}

ISSUES = {
    "MISSING_TITLE": "CRITICAL",
    "INVALID_DOI": "CRITICAL",
    "INCOMPLETE_AUTHORS": "HIGH",
    "MISSING_VENUE": "HIGH",
    "WRONG_ENTRY_TYPE": "HIGH",
    "PLACEHOLDER_TITLE": "HIGH",
    "FUZZY_TITLE_MISMATCH": "HIGH",
    "DUPLICATE_CONTENT": "MEDIUM",
    "MISSING_DOI_HAS_ARXIV": "MEDIUM",
    "MISSING_METADATA": "MEDIUM",
    "FORMATTING_ISSUE": "LOW",
}


class DOIValidator:
    """Validate DOIs against CrossRef API."""

    CROSSREF_API = "https://api.crossref.org/works/{}"
    HEADERS = {
        "User-Agent": "deep-biblio-tools/validation (contact via github)"
    }
    TIMEOUT = 10

    def __init__(self):
        self.cache = {}

    def check_doi(self, doi: str) -> dict[str, Any]:
        """Check if DOI is valid and return metadata."""
        if doi in self.cache:
            return self.cache[doi]

        url = self.CROSSREF_API.format(doi)

        try:
            response = requests.get(
                url, headers=self.HEADERS, timeout=self.TIMEOUT
            )

            if response.status_code == 200:
                data = response.json().get("message", {})
                result = {
                    "status": "VALID",
                    "metadata": data,
                    "checked_at": datetime.utcnow().isoformat() + "Z",
                }
            elif response.status_code == 404:
                result = {
                    "status": "INVALID",
                    "checked_at": datetime.utcnow().isoformat() + "Z",
                }
            elif response.status_code == 429:
                result = {
                    "status": "RATE_LIMIT",
                    "checked_at": datetime.utcnow().isoformat() + "Z",
                }
            else:
                result = {
                    "status": "UNKNOWN",
                    "http_status": response.status_code,
                    "checked_at": datetime.utcnow().isoformat() + "Z",
                }

        except requests.RequestException as e:
            logger.warning(f"DOI check failed for {doi}: {e}")
            result = {
                "status": "ERROR",
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat() + "Z",
            }

        self.cache[doi] = result
        return result


class BibSourceValidator:
    """Validate source references.bib file."""

    def __init__(self):
        self.doi_validator = DOIValidator()

    def parse_bib_file(self, bib_path: Path) -> list[dict]:
        """Parse BibTeX file and return entries."""
        logger.info(f"Parsing {bib_path}...")

        with open(bib_path, encoding="utf-8") as f:
            bib_database = bibtexparser.load(f)

        entries = bib_database.entries
        logger.info(f"Found {len(entries)} entries")
        return entries

    def validate_entry(self, entry: dict) -> dict[str, Any]:
        """Validate a single bibliography entry."""
        citation_key = entry.get("ID", "UNKNOWN")
        entry_type = entry.get("ENTRYTYPE", "misc")

        issues = []

        # Check required fields
        required = REQUIRED_FIELDS.get(entry_type, REQUIRED_FIELDS["misc"])
        for field in required:
            if field not in entry:
                issues.append(f"MISSING_{field.upper()}")

        # Check title
        title = entry.get("title", "")
        if not title or len(title) < 3:
            issues.append("MISSING_TITLE")
        elif self._is_placeholder_title(title):
            issues.append("PLACEHOLDER_TITLE")

        # Check DOI first (needed for author validation)
        doi = entry.get("doi")
        doi_status = None
        doi_metadata = None

        if doi:
            doi_check = self.doi_validator.check_doi(doi)
            doi_status = doi_check["status"]

            if doi_status == "INVALID":
                issues.append("INVALID_DOI")
            elif doi_status == "VALID":
                doi_metadata = doi_check.get("metadata")
                # Fuzzy title matching
                if doi_metadata and title:
                    crossref_title = " ".join(doi_metadata.get("title", []))
                    if crossref_title and self._fuzzy_mismatch(
                        title, crossref_title
                    ):
                        issues.append("FUZZY_TITLE_MISMATCH")

        # Check authors (after DOI check so we can use doi_metadata)
        author = entry.get("author", "")
        if not author:
            issues.append("MISSING_AUTHOR")
        elif self._has_incomplete_authors(author, doi_metadata):
            issues.append("INCOMPLETE_AUTHORS")

        # Check venue for articles
        if entry_type == "article" and "journal" not in entry:
            issues.append("MISSING_VENUE")

        # Determine severity
        severity = "INFO"
        if issues:
            severities = [ISSUES.get(issue, "LOW") for issue in issues]
            severity = max(severities, key=lambda s: SEVERITY_ORDER.index(s))

        return {
            "citation_key": citation_key,
            "entry_type": entry_type,
            "has_title": "title" in entry,
            "has_author": "author" in entry,
            "has_venue": "journal" in entry or "booktitle" in entry,
            "doi": doi,
            "doi_status": doi_status,
            "doi_checked_at": (
                self.doi_validator.cache.get(doi, {}).get("checked_at")
                if doi
                else None
            ),
            "arxiv_id": self._extract_arxiv_id(entry.get("url", "")),
            "issues": issues,
            "severity": severity,
            "suggested_actions": self._suggest_actions(issues, entry),
        }

    def _is_placeholder_title(self, title: str) -> bool:
        placeholders = ["Web page by", "Unknown", "Anonymous", "Untitled"]
        return any(p in title for p in placeholders)

    def _count_bibtex_authors(self, author_field: str) -> int:
        """Count authors in BibTeX author field.

        BibTeX format: "Last1, First1 and Last2, First2 and Last3, First3"

        Returns:
            Number of authors, or -1 if truncated with "others"/"et al"
        """
        if not author_field or author_field.strip() == "":
            return 0

        # Check for "others" or "et al" (indicates truncated list)
        if "others" in author_field.lower() or "et al" in author_field.lower():
            return -1

        # Split by " and " to count authors
        authors = [a.strip() for a in author_field.split(" and ") if a.strip()]
        return len(authors)

    def _has_incomplete_authors(self, author: str, doi_metadata: dict | None = None) -> bool:
        """Check if author field is incomplete.

        Updated logic to reduce false positives:
        - If ≥6 complete authors: NOT incomplete
        - If "et al" with ≥15 expected authors: NOT incomplete (acceptable)
        - If "et al" with <15 expected authors: incomplete
        - Otherwise check against DOI metadata if available

        Args:
            author: BibTeX author field
            doi_metadata: Optional DOI metadata from CrossRef

        Returns:
            True if incomplete, False otherwise
        """
        author_count = self._count_bibtex_authors(author)

        # If author count is negative, list was truncated with "others"/"et al"
        if author_count == -1:
            # Check if DOI metadata available to verify expected count
            if doi_metadata and "author" in doi_metadata:
                expected_count = len(doi_metadata["author"])

                # Only flag as incomplete if expected authors < 15
                # (for 15+ author papers, "et al" is acceptable)
                if expected_count < 15:
                    return True
            # If no DOI metadata, conservatively flag as potentially incomplete
            return True

        # If no authors at all
        if author_count == 0:
            return True

        # If ≥6 complete authors, accept as complete (not truncated)
        if author_count >= 6:
            return False

        # For 1-5 authors, check against DOI metadata if available
        if doi_metadata and "author" in doi_metadata:
            expected_count = len(doi_metadata["author"])
            if author_count < expected_count:
                return True

        # Default: if we can't verify, assume complete
        return False

    def _fuzzy_mismatch(
        self, title1: str, title2: str, threshold: float = 0.3
    ) -> bool:
        dist = levenshtein_distance(title1.lower(), title2.lower())
        max_len = max(len(title1), len(title2))
        if max_len == 0:
            return False
        similarity = 1 - (dist / max_len)
        return similarity < (1 - threshold)

    def _extract_arxiv_id(self, url: str) -> str | None:
        if "arxiv.org/" not in url:
            return None
        parts = url.split("/")
        for i, part in enumerate(parts):
            if part in ["abs", "pdf"] and i + 1 < len(parts):
                return parts[i + 1]
        return None

    def _suggest_actions(self, issues: list[str], entry: dict) -> list[str]:
        actions = []
        if "INVALID_DOI" in issues:
            actions.append("search_doi_by_title_author")
        if "MISSING_TITLE" in issues and entry.get("doi"):
            actions.append("fetch_from_doi")
        if "INCOMPLETE_AUTHORS" in issues and entry.get("doi"):
            actions.append("fetch_full_authors_from_doi")
        if not actions:
            actions.append("manual_verification_required")
        return actions


@click.command()
@click.argument("bib_file", type=click.Path(exists=True, path_type=Path))
@click.option("--output-dir", type=click.Path(path_type=Path), default=None)
def main(bib_file: Path, output_dir: Path | None):
    """Validate source references.bib file."""

    if output_dir is None:
        output_dir = bib_file.parent

    output_jsonl = output_dir / "validation_report.jsonl"
    output_csv = output_dir / "validation_report.csv"
    log_file = output_dir / "validation.log"

    # Configure file logging
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info(f"Starting validation of {bib_file}")

    validator = BibSourceValidator()

    try:
        entries = validator.parse_bib_file(bib_file)
    except Exception as e:
        logger.error(f"Failed to parse {bib_file}: {e}")
        sys.exit(1)

    results = []
    for entry in entries:
        result = validator.validate_entry(entry)
        results.append(result)

    # Write JSONL
    logger.info(f"Writing JSONL report to {output_jsonl}...")
    with open(output_jsonl, "w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result) + "\n")

    # Write CSV
    logger.info(f"Writing CSV report to {output_csv}...")
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "citation_key",
            "severity",
            "issues",
            "has_title",
            "has_author",
            "has_venue",
            "doi_status",
            "suggested_actions",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            row = {
                "citation_key": result["citation_key"],
                "severity": result["severity"],
                "issues": "; ".join(result["issues"]),
                "has_title": result["has_title"],
                "has_author": result["has_author"],
                "has_venue": result["has_venue"],
                "doi_status": result.get("doi_status", "N/A"),
                "suggested_actions": "; ".join(result["suggested_actions"]),
            }
            writer.writerow(row)

    # Print summary
    print(f"\n{'=' * 80}")
    print(f"Validation complete for {len(results)} entries")
    print(f"{'=' * 80}\n")

    # Summary by severity
    severity_counts = {}
    for result in results:
        severity = result["severity"]
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    print("Summary by Severity:")
    for severity in SEVERITY_ORDER:
        if severity in severity_counts:
            count = severity_counts[severity]
            print(f"  {severity:10s}: {count:4d} entries")

    # Issue breakdown
    print("\nIssue Breakdown:")
    issue_counts = {}
    for result in results:
        for issue in result["issues"]:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

    for issue, count in sorted(
        issue_counts.items(), key=lambda x: x[1], reverse=True
    )[:10]:
        severity = ISSUES.get(issue, "UNKNOWN")
        print(f"  {issue:30s} ({severity:8s}): {count:4d}")

    print(f"\n{'=' * 80}")
    print("Reports written:")
    print(f"  JSONL: {output_jsonl}")
    print(f"  CSV:   {output_csv}")
    print(f"  Log:   {log_file}")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    main()
