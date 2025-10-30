"""Validates final BibTeX entries for quality issues.

This validator runs AFTER BibTeX generation to catch issues in the final output.
It complements EntryValidator which validates Zotero metadata BEFORE adding.

Uses bibtexparser (AST-based, NO regex) per CLAUDE.md requirements.
"""

import logging
from pathlib import Path
from typing import Any

# Use bibtexparser for AST-based parsing (CLAUDE.md requirement)
from bibtexparser.bparser import BibTexParser

logger = logging.getLogger(__name__)


class BibTeXEntryValidator:
    """Validate generated BibTeX entries for quality issues.

    This validator checks the FINAL BibTeX output (references.bib) for:
    - Temporary citation keys (Temp, dryrun_)
    - Stub titles ("Web page by X")
    - Domain names as titles ("Amazon.de")
    - Missing or empty required fields
    - Unknown/Anonymous authors
    - Short keys (likely not Better BibTeX format)

    This is the LAST validation gate before LaTeX compilation.
    """

    def __init__(self):
        """Initialize validator with check patterns."""
        # Stub title patterns (NO REGEX - string methods only)
        self.stub_prefixes = ["Web page by ", "Webpage by ", "Web site by "]

        # Domain extensions indicating domain-as-title
        self.domain_extensions = [
            ".com",
            ".org",
            ".de",
            ".co.uk",
            ".eu",
            ".net",
        ]

        # Known domain titles
        self.known_domain_titles = [
            "Amazon.de",
            "Amazon.com",
            "Amazon.co.uk",
            "BBC.com",
            "Bloomberg.com",
            "Reuters.com",
        ]

        # Minimum Better BibTeX key length
        self.min_key_length = 15

    def validate_file(self, bib_path: Path | str) -> dict[str, Any]:
        """Parse and validate all entries in BibTeX file.

        Args:
            bib_path: Path to references.bib file

        Returns:
            dict with:
                - total_entries: int
                - issues_by_entry: dict[key -> list[issues]]
                - critical_count: int
                - warning_count: int

        Raises:
            FileNotFoundError: If bib_path doesn't exist
        """
        bib_path = Path(bib_path)
        if not bib_path.exists():
            raise FileNotFoundError(f"BibTeX file not found: {bib_path}")

        # Parse with bibtexparser (AST-based, no regex)
        with open(bib_path, encoding="utf8") as f:
            parser = BibTexParser(common_strings=True)
            bib_db = parser.parse_file(f)

        results = {
            "total_entries": len(bib_db.entries),
            "issues_by_entry": {},
            "critical_count": 0,
            "warning_count": 0,
        }

        # Validate each entry
        for entry in bib_db.entries:
            issues = self._validate_entry(entry)
            if issues:
                key = entry.get("ID", "unknown")
                results["issues_by_entry"][key] = issues

                # Count severity
                critical = [i for i in issues if i.startswith("CRITICAL")]
                warnings = [i for i in issues if i.startswith("WARNING")]
                results["critical_count"] += len(critical)
                results["warning_count"] += len(warnings)

        logger.info(
            f"BibTeX validation: {results['total_entries']} entries, "
            f"{results['critical_count']} CRITICAL, "
            f"{results['warning_count']} WARNING"
        )

        return results

    def _validate_entry(self, entry: dict[str, Any]) -> list[str]:
        """Validate single BibTeX entry.

        Args:
            entry: Dict from bibtexparser with keys: ID, author, title, year, etc.

        Returns:
            List of issue strings with CRITICAL or WARNING prefix
        """
        issues: list[str] = []

        # Extract fields
        key = entry.get("ID", "")
        title = entry.get("title", "").strip()
        author = entry.get("author", "").strip()
        year = entry.get("year", entry.get("date", "")).strip()

        # Check 1: Temporary keys (CRITICAL)
        # NO REGEX - use simple string checks
        if "Temp" in key or "dryrun_" in key or key.startswith("temp_"):
            issues.append(
                f"CRITICAL: Temporary citation key '{key}' - not from Zotero Better BibTeX"
            )

        # Check 2: Stub titles (CRITICAL)
        for prefix in self.stub_prefixes:
            if title.startswith(prefix):
                issues.append(
                    f"CRITICAL: Stub title '{title}' - metadata extraction failed"
                )
                break

        # Check 3: Domain extensions as title endings (CRITICAL)
        for ext in self.domain_extensions:
            if title.endswith(ext):
                issues.append(
                    f"CRITICAL: Domain name as title '{title}' - should be actual content title"
                )
                break

        # Check 4: Exact domain name matches (CRITICAL)
        if title in self.known_domain_titles:
            issues.append(
                f"CRITICAL: Title is domain name '{title}' instead of content title"
            )

        # Check 5: Empty or very short title (CRITICAL)
        if not title:
            issues.append("CRITICAL: Title field is empty")
        elif len(title) < 5:
            issues.append(
                f"CRITICAL: Title too short ({len(title)} chars): '{title}'"
            )

        # Check 6: Unknown/Anonymous author (WARNING)
        if author in ["Unknown", "Anonymous", ""]:
            issues.append(f"WARNING: Invalid author '{author or 'EMPTY'}'")

        # Check 7: Better BibTeX key format (WARNING)
        # Better BibTeX keys are typically ≥15 chars with camelCase
        if len(key) < self.min_key_length:
            issues.append(
                f"WARNING: Suspiciously short key '{key}' "
                f"({len(key)} chars, expect ≥{self.min_key_length} for Better BibTeX)"
            )

        # Check 8: Missing year (WARNING)
        if not year:
            issues.append("WARNING: Missing year/date field")

        # Check 9: Year format validation (WARNING)
        # NO REGEX - check if year contains any digits
        if year and not any(c.isdigit() for c in year):
            issues.append(f"WARNING: Year '{year}' contains no digits")

        return issues

    def has_critical_issues(self, bib_path: Path | str) -> bool:
        """Quick check if BibTeX file has any CRITICAL issues.

        Args:
            bib_path: Path to references.bib

        Returns:
            True if CRITICAL issues found, False otherwise
        """
        results = self.validate_file(bib_path)
        return results["critical_count"] > 0
