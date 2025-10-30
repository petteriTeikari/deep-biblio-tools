"""Validates Zotero item metadata quality before adding to library.

This module prevents garbage entries (like the October 26 incident) by
checking for truncated titles, missing authors, invalid years, etc.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class EntryValidator:
    """Validates Zotero item metadata quality.

    Checks for common issues that indicate garbage or incomplete metadata:
    - Truncated titles (e.g., "Added from URL: ...")
    - Missing or incomplete authors
    - Invalid years (outside 1900-2030 range)
    - Suspiciously short titles

    Returns validation results as (is_valid, issues) where issues
    are classified as CRITICAL (prevent add) or WARNING (allow but log).
    """

    def __init__(self):
        """Initialize validator with default settings."""
        # Patterns that indicate truncated or garbage titles
        self.truncation_markers = [
            "Added from URL:",
            "...",
            "[truncated]",
            "Implementation plan",  # Specific to CRIS garbage from Oct 26
            "Abstract only",
            "Full text unavailable",
        ]

        # Minimum acceptable title length
        self.min_title_length = 10

        # Valid year range for publications
        self.min_year = 1900
        self.max_year = 2030

    def validate(self, metadata: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate entry metadata and return (is_valid, issues).

        Args:
            metadata: Zotero item JSON (from translation server or API)

        Returns:
            (is_valid, issues) where:
                - is_valid: False if entry should NOT be added (critical issues)
                - issues: List of issue descriptions (CRITICAL or WARNING prefix)

        Example:
            >>> validator = EntryValidator()
            >>> metadata = {"title": "Added from URL: https://...", ...}
            >>> is_valid, issues = validator.validate(metadata)
            >>> print(is_valid)
            False
            >>> print(issues)
            ['CRITICAL: Title contains truncation marker "Added from URL:"']
        """
        issues: list[str] = []

        # 1. Title validation (CRITICAL)
        title_valid = self._validate_title(metadata, issues)
        if not title_valid:
            return False, issues

        # 2. Creator/Author validation (WARNING only, can augment)
        self._validate_creators(metadata, issues)

        # 3. Date/Year validation (WARNING)
        self._validate_date(metadata, issues)

        # 4. DOI format validation (WARNING, non-blocking)
        self._validate_doi_format(metadata, issues)

        # 5. Item type specific checks (WARNING)
        self._validate_item_type_specific(metadata, issues)

        # If we got here, entry is valid (no critical issues)
        # There may be warnings but they don't prevent addition
        return True, issues

    def _validate_title(
        self, metadata: dict[str, Any], issues: list[str]
    ) -> bool:
        """Validate title field. Returns False if critical issues found."""
        title = metadata.get("title", "").strip()

        # Check 1: Title presence
        if not title:
            issues.append("CRITICAL: Title missing")
            return False

        # Check 2: Stub titles (check BEFORE length check)
        # These indicate translation server failed to extract proper title
        stub_prefixes = ["Web page by ", "Webpage by ", "Web site by "]
        for prefix in stub_prefixes:
            if title.startswith(prefix):
                issues.append(
                    f"CRITICAL: Stub title detected: '{title}' - indicates metadata extraction failure"
                )
                return False

        # Check 3: Domain names as titles (check BEFORE length check)
        # Translation server sometimes returns domain instead of page title
        domain_extensions = [".com", ".org", ".de", ".co.uk", ".eu", ".net"]
        for ext in domain_extensions:
            if title.endswith(ext):
                issues.append(
                    f"CRITICAL: Domain name as title: '{title}' - should be actual content title"
                )
                return False

        # Check 4: Exact domain name matches (check BEFORE length check)
        # Common cases where domain is used as title
        known_domain_titles = [
            "Amazon.de",
            "Amazon.com",
            "Amazon.co.uk",
            "BBC.com",
            "Bloomberg.com",
            "Reuters.com",
        ]
        if title in known_domain_titles:
            issues.append(
                f"CRITICAL: Title is domain name '{title}' instead of content title"
            )
            return False

        # Check 5: Minimum length
        if len(title) < self.min_title_length:
            issues.append(
                f"CRITICAL: Title suspiciously short ({len(title)} chars): '{title}'"
            )
            return False

        # Check 6: Truncation markers
        for marker in self.truncation_markers:
            if marker in title:
                issues.append(
                    f"CRITICAL: Title contains truncation marker '{marker}'"
                )
                return False

        # Check 7: All uppercase (often indicates poor metadata)
        if title.isupper() and len(title) > 20:
            issues.append(
                "WARNING: Title is all uppercase (may indicate poor metadata)"
            )

        return True

    def _validate_creators(self, metadata: dict[str, Any], issues: list[str]):
        """Validate creators/authors. Only adds warnings."""
        creators = metadata.get("creators", [])

        if not creators or len(creators) == 0:
            issues.append("WARNING: No creators/authors present")
            return

        # Check for incomplete creator objects
        for i, creator in enumerate(creators):
            if not isinstance(creator, dict):
                issues.append(f"WARNING: Creator {i} is not a dict: {creator}")
                continue

            # Check for required fields
            last_name = creator.get("lastName", "").strip()
            creator_type = creator.get("creatorType", "")

            if not last_name:
                issues.append(f"WARNING: Creator {i} missing lastName field")

            if not creator_type:
                issues.append(f"WARNING: Creator {i} missing creatorType field")

            # Check for suspiciously short names
            if last_name and len(last_name) < 2:
                issues.append(
                    f"WARNING: Creator {i} has suspiciously short lastName: '{last_name}'"
                )

    def _validate_date(self, metadata: dict[str, Any], issues: list[str]):
        """Validate date/year field. Only adds warnings."""
        date = metadata.get("date", "").strip()

        if not date:
            issues.append("WARNING: No date field present")
            return

        # Try to extract 4-digit year
        year = self._extract_year(date)

        if not year:
            issues.append(
                f"WARNING: No valid 4-digit year found in date: '{date}'"
            )
            return

        # Check if year is in reasonable range
        if year < self.min_year or year > self.max_year:
            issues.append(
                f"WARNING: Year {year} outside expected range ({self.min_year}-{self.max_year})"
            )

    def _extract_year(self, date_str: str) -> int | None:
        """Extract 4-digit year from date string without regex.

        Args:
            date_str: Date string in various formats (e.g., "2018-07-19", "July 2018")

        Returns:
            Integer year if found, None otherwise
        """
        if not date_str:
            return None

        # Split by common separators and whitespace
        # Replace separators with spaces, then split
        normalized = date_str
        for sep in ["-", "/", ",", "."]:
            normalized = normalized.replace(sep, " ")

        tokens = normalized.split()

        # Look for 4-digit tokens that are years
        for token in tokens:
            if len(token) == 4 and token.isdigit():
                return int(token)

        return None

    def _validate_doi_format(self, metadata: dict[str, Any], issues: list[str]):
        """Validate DOI format if present. Only adds warnings.

        Note: We don't do network validation (HEAD request) because
        it's too slow for batch processing. Just check format.
        """
        # Check multiple possible fields (translation server inconsistent)
        doi = (
            metadata.get("DOI")
            or metadata.get("doi")
            or metadata.get("Doi")
            or ""
        ).strip()

        if not doi:
            return  # No DOI is fine

        # Basic format check: should start with "10."
        if not doi.startswith("10."):
            issues.append(
                f"WARNING: DOI '{doi}' has unusual format (expected '10.XXXX/...')"
            )

        # Check for suspiciously short DOI
        if len(doi) < 7:  # Minimum realistic DOI like "10.1/x"
            issues.append(f"WARNING: DOI '{doi}' is suspiciously short")

    def _validate_item_type_specific(
        self, metadata: dict[str, Any], issues: list[str]
    ):
        """Validate based on specific item types."""
        item_type = metadata.get("itemType", "")

        if item_type == "webpage":
            # Web pages should have authors (can be organization)
            creators = metadata.get("creators", [])
            if not creators:
                issues.append(
                    "WARNING: Webpage entry without author "
                    "(consider extracting from site name)"
                )

            # Web pages should have access date
            access_date = metadata.get("accessDate", "")
            if not access_date:
                issues.append("WARNING: Webpage without accessDate")

        elif item_type == "journalArticle":
            # Journal articles should have publication name
            publication = metadata.get("publicationTitle", "")
            if not publication:
                issues.append(
                    "WARNING: Journal article without publication name"
                )

            # Should have DOI
            doi = metadata.get("DOI") or metadata.get("doi")
            if not doi:
                issues.append("WARNING: Journal article without DOI")

        elif item_type == "conferencePaper":
            # Conference papers should have proceedings name
            proceedings = metadata.get("proceedingsTitle", "")
            if not proceedings:
                issues.append(
                    "WARNING: Conference paper without proceedings title"
                )
