"""Bibliography entry validation."""

import datetime
from urllib.parse import urlparse

# import re  # Banned - using string methods instead
import requests

from .core import Bibliography, BibliographyEntry, BibliographyProcessor


class BibliographyValidator(BibliographyProcessor):
    """Validate bibliography entries.

    This class consolidates functionality from:
    - validate_citations.py
    - validate_bibliography_entries.py
    - check_bibliography_quality.py
    - validate_llm_citations.py
    """

    # Required fields by entry type
    REQUIRED_FIELDS = {
        "article": {"author", "title", "journal", "year"},
        "book": {"author", "title", "publisher", "year"},
        "inproceedings": {"author", "title", "booktitle", "year"},
        "inbook": {"author", "title", "booktitle", "publisher", "year"},
        "incollection": {"author", "title", "booktitle", "publisher", "year"},
        "manual": {"title"},
        "mastersthesis": {"author", "title", "school", "year"},
        "misc": {},
        "phdthesis": {"author", "title", "school", "year"},
        "proceedings": {"title", "year"},
        "techreport": {"author", "title", "institution", "year"},
        "unpublished": {"author", "title", "note"},
    }

    # Common suspicious patterns in LLM-generated citations (converted from regex)
    SUSPICIOUS_PATTERNS = [
        "et al",  # "et al." in author field
        "Unknown",  # Placeholder values
        "TBD",
        "TODO",
        "Author",  # Field names as values
        "Title",
        "Year",
    ]

    def __init__(self, check_urls: bool = False, timeout: int = 5):
        """Initialize validator.

        Args:
            check_urls: Whether to validate URLs by making requests
            timeout: Timeout for URL validation requests
        """
        self.check_urls = check_urls
        self.timeout = timeout
        self.errors: list[str] = []

    def process(self, bibliography: Bibliography) -> list[str]:
        """Validate all entries in bibliography.

        Args:
            bibliography: Bibliography to validate

        Returns:
            List of validation errors
        """
        self.errors = []

        # Check for duplicate keys
        self._check_duplicate_keys(bibliography)

        # Check for duplicate content (for LLMCitationValidator)
        if isinstance(self, LLMCitationValidator):
            self._check_duplicate_content(bibliography)

        # Validate each entry
        for entry in bibliography:
            entry_errors = self.validate_entry(entry)
            if entry_errors:
                self.errors.extend(entry_errors)

        return self.errors

    def process_entry(self, entry: BibliographyEntry) -> None:
        """Process a single entry (required by base class).

        Args:
            entry: Entry to process
        """
        errors = self.validate_entry(entry)
        if errors:
            self.errors.extend(errors)

    def validate_entry(self, entry: BibliographyEntry) -> list[str]:
        """Validate a single bibliography entry.

        Args:
            entry: Bibliography entry to validate

        Returns:
            List of validation errors for this entry
        """
        errors = []

        # Check required fields
        missing_fields = self.check_required_fields(entry)
        if missing_fields:
            errors.append(
                f"Entry '{entry.key}' ({entry.entry_type}) missing required fields: "
                f"{', '.join(missing_fields)}"
            )

        # Check for suspicious patterns
        suspicious = self._check_suspicious_patterns(entry)
        if suspicious:
            errors.extend(suspicious)

        # Validate specific fields
        if entry.has_field("year"):
            year_error = self._validate_year(entry.key, entry.get_field("year"))
            if year_error:
                errors.append(year_error)

        if entry.has_field("author"):
            author_errors = self._validate_authors(
                entry.key, entry.get_field("author")
            )
            errors.extend(author_errors)

        # Validate URLs if enabled
        if self.check_urls:
            url_errors = self.validate_urls(entry)
            errors.extend(url_errors)

        return errors

    def check_required_fields(self, entry: BibliographyEntry) -> set[str]:
        """Check if entry has all required fields.

        Args:
            entry: Bibliography entry

        Returns:
            Set of missing required fields
        """
        required = self.REQUIRED_FIELDS.get(entry.entry_type, set())
        present = set(entry.fields.keys())

        # Special handling for author/editor
        if (
            "author" in required
            and "author" not in present
            and "editor" in present
        ):
            required = required - {"author"}

        return required - present

    def validate_urls(self, entry: BibliographyEntry) -> list[str]:
        """Validate URLs in bibliography entry.

        Args:
            entry: Bibliography entry

        Returns:
            List of URL validation errors
        """
        errors = []
        url_fields = ["url", "doi", "eprint", "arxiv"]

        for field in url_fields:
            if not entry.has_field(field):
                continue

            value = entry.get_field(field)

            # Construct full URL based on field type
            if field == "doi":
                url = f"https://doi.org/{value}"
            elif field == "arxiv" or (
                field == "eprint" and "arxiv" in value.lower()
            ):
                # Handle various arXiv formats
                arxiv_id = value.replace("arXiv:", "").replace("arxiv:", "")
                url = f"https://arxiv.org/abs/{arxiv_id}"
            else:
                url = value

            # Validate URL format
            try:
                result = urlparse(url)
                if not all([result.scheme, result.netloc]):
                    errors.append(
                        f"Entry '{entry.key}': Invalid URL format in {field}: {value}"
                    )
                    continue
            except Exception:
                errors.append(
                    f"Entry '{entry.key}': Malformed URL in {field}: {value}"
                )
                continue

            # Check if URL is accessible
            if self.check_urls and result.scheme in ["http", "https"]:
                try:
                    response = requests.head(
                        url, timeout=self.timeout, allow_redirects=True
                    )
                    if response.status_code >= 400:
                        errors.append(
                            f"Entry '{entry.key}': URL in {field} returned "
                            f"{response.status_code}: {url}"
                        )
                except requests.RequestException as e:
                    errors.append(
                        f"Entry '{entry.key}': Failed to validate URL in {field}: "
                        f"{url} ({str(e)})"
                    )

        return errors

    def _check_duplicate_keys(self, bibliography: Bibliography) -> None:
        """Check for duplicate citation keys.

        Args:
            bibliography: Bibliography to check
        """
        seen_keys = set()
        for entry in bibliography:
            if entry.key in seen_keys:
                self.errors.append(f"Duplicate citation key: '{entry.key}'")
            seen_keys.add(entry.key)

    def _check_suspicious_patterns(self, entry: BibliographyEntry) -> list[str]:
        """Check for suspicious patterns that indicate LLM hallucination.

        Args:
            entry: Bibliography entry

        Returns:
            List of suspicious pattern warnings
        """
        warnings = []

        for field_name, value in entry.fields.items():
            if not isinstance(value, str):
                continue

            value_lower = value.lower().strip()

            # Check for suspicious patterns
            for pattern in self.SUSPICIOUS_PATTERNS:
                pattern_lower = pattern.lower()

                # Check for exact match or contained pattern
                if (
                    pattern_lower == value_lower
                    or pattern_lower in value_lower
                    or (pattern_lower == "et al" and "et al" in value_lower)
                ):
                    warnings.append(
                        f"Entry '{entry.key}': Suspicious pattern in {field_name}: '{value}'"
                    )

        # Special check for "et al" in author field
        author = entry.get_field("author", "")
        if "et al" in author.lower():
            warnings.append(
                f"Entry '{entry.key}': 'et al' found in author field - "
                "should list all authors explicitly"
            )

        return warnings

    def _validate_year(self, key: str, year: str) -> str | None:
        """Validate year field.

        Args:
            key: Citation key
            year: Year value

        Returns:
            Error message if invalid, None otherwise
        """
        # Clean year value
        year = str(year).strip()

        # Check if it's a valid 4-digit year
        # Check year format without regex
        if not (len(year) == 4 and year.isdigit()):
            return f"Entry '{key}': Invalid year format: '{year}'"

        # Check if year is reasonable (not too far in future)
        current_year = datetime.datetime.now().year
        year_int = int(year)

        if year_int > current_year + 2:  # Allow 2 years in future for preprints
            return f"Entry '{key}': Year {year} is too far in the future"

        if year_int < 1800:  # Reasonable lower bound
            return f"Entry '{key}': Year {year} seems too old"

        return None

    def _validate_authors(self, key: str, authors: str) -> list[str]:
        """Validate author field.

        Args:
            key: Citation key
            authors: Author string

        Returns:
            List of validation errors
        """
        errors = []

        # Check for empty authors
        if not authors or authors.strip() == "":
            errors.append(f"Entry '{key}': Empty author field")
            return errors

        # Split authors (handle both "and" and "&")
        # Split authors without regex
        # First replace & with and
        authors_normalized = authors.replace(" & ", " and ").replace(
            "&", " and "
        )
        author_list = authors_normalized.split(" and ")

        for i, author in enumerate(author_list):
            author = author.strip()

            # Check for single-word authors (likely incomplete)
            if author and " " not in author and "," not in author:
                errors.append(
                    f"Entry '{key}': Author {i + 1} appears incomplete: '{author}'"
                )

            # Check for reversed names without comma
            # Check for reversed names without regex
            parts = author.strip().split()
            if len(parts) == 2 and "," not in author:
                if (
                    parts[0]
                    and parts[0][0].isupper()
                    and parts[0][1:].islower()
                    and parts[1]
                    and parts[1][0].isupper()
                    and parts[1][1:].islower()
                ):
                    errors.append(
                        f"Entry '{key}': Author {i + 1} may need comma: '{author}'"
                    )

        return errors


class LLMCitationValidator(BibliographyValidator):
    """Specialized validator for LLM-generated citations.

    This validator performs additional checks specific to citations
    that may have been generated or hallucinated by language models.
    """

    def __init__(self, check_urls: bool = True, timeout: int = 5):
        """Initialize LLM citation validator.

        Args:
            check_urls: Whether to validate URLs (recommended for LLM citations)
            timeout: Timeout for URL validation
        """
        super().__init__(check_urls=check_urls, timeout=timeout)

    def validate_entry(self, entry: BibliographyEntry) -> list[str]:
        """Validate entry with additional LLM-specific checks.

        Args:
            entry: Bibliography entry

        Returns:
            List of validation errors
        """
        # Run standard validation
        errors = super().validate_entry(entry)

        # Additional LLM-specific checks
        llm_errors = self._check_llm_patterns(entry)
        errors.extend(llm_errors)

        return errors

    def _check_llm_patterns(self, entry: BibliographyEntry) -> list[str]:
        """Check for patterns specific to LLM hallucinations.

        Args:
            entry: Bibliography entry

        Returns:
            List of LLM-specific warnings
        """
        warnings = []

        # Check for "et al." in author field (common LLM shortcut)
        author = entry.get_field("author", "")
        if author and "et al." in author:
            warnings.append(
                f"Entry '{entry.key}': Found 'et al.' in author field - may be hiding hallucinated authors"
            )

        # Check for generic titles
        title = entry.get_field("title", "")
        if title:
            generic_titles = [
                "A Study of",
                "Research on",
                "Investigation of",
                "Analysis of",
                "Overview of",
            ]
            for generic in generic_titles:
                if title.startswith(generic):
                    warnings.append(
                        f"Entry '{entry.key}': Generic title pattern: '{title}'"
                    )

        # Check for generic conference names
        booktitle = entry.get_field("booktitle", "")
        if booktitle:
            generic_conferences = [
                "International Conference",
                "Proceedings of the Conference",
                "Annual Conference",
                "Workshop on",
            ]
            for generic in generic_conferences:
                if generic in booktitle and len(booktitle) < 50:
                    warnings.append(
                        f"Entry '{entry.key}': Possibly generic conference name: '{booktitle}'"
                    )

        # Check for suspiciously round page numbers
        pages = entry.get_field("pages", "")
        # Check for suspiciously round page numbers without regex
        if pages and "--" in pages:
            parts = pages.split("--")
            if len(parts) == 2:
                start, end = parts[0].strip(), parts[1].strip()
                if (
                    start.endswith("00")
                    and end.endswith("00")
                    and start[:-2].isdigit()
                    and end[:-2].isdigit()
                ):
                    warnings.append(
                        f"Entry '{entry.key}': Suspicious page numbers: '{pages}'"
                    )

        # Check for placeholder journal names
        journal = entry.get_field("journal", "")
        if journal:
            placeholders = ["Journal", "Proceedings", "Transactions"]
            if journal in placeholders:
                warnings.append(
                    f"Entry '{entry.key}': Generic journal name: '{journal}'"
                )

        # Check for missing identifiers (can't verify without DOI, URL, etc)
        has_doi = entry.has_field("doi")
        has_url = entry.has_field("url")
        has_eprint = entry.has_field("eprint")
        has_isbn = entry.has_field("isbn")

        if not (has_doi or has_url or has_eprint or has_isbn):
            warnings.append(
                f"Entry '{entry.key}': No identifier found - difficult to verify authenticity"
            )

        # Check for markdown artifacts in fields
        text_fields = ["author", "title", "journal", "booktitle", "note"]
        for field_name in text_fields:
            field_value = entry.get_field(field_name, "")
            if field_value and isinstance(field_value, str):
                # Check for markdown formatting
                if any(
                    pattern in field_value
                    for pattern in ["**", "__", "_", "[", "](", "`"]
                ):
                    warnings.append(
                        f"Entry '{entry.key}': Markdown formatting found in {field_name}: '{field_value}'"
                    )

        return warnings

    def _check_duplicate_content(self, bibliography: Bibliography) -> None:
        """Check for potentially duplicate content with variations.

        Args:
            bibliography: Bibliography to check for duplicates
        """
        entries = list(bibliography.entries)

        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                entry1, entry2 = entries[i], entries[j]

                # Check if titles are exactly the same
                title1 = entry1.get_field("title", "").lower().strip()
                title2 = entry2.get_field("title", "").lower().strip()

                if title1 and title2 and title1 == title2:
                    # Same title - check if authors are similar
                    # TODO: Implement author similarity check
                    # author1 = entry1.get_field("author", "").lower()
                    # author2 = entry2.get_field("author", "").lower()

                    # Simple similarity check - same year and similar authors
                    year1 = entry1.get_field("year", "")
                    year2 = entry2.get_field("year", "")

                    if year1 == year2:
                        self.errors.append(
                            f"Potential duplicate: '{entry1.key}' and '{entry2.key}' have same title and year"
                        )
