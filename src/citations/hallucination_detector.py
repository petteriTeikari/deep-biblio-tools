"""Detect LLM hallucinations in citations."""

import logging

# import re  # Banned - using string methods instead
from difflib import SequenceMatcher

from .models import CitationData, DataSource, ValidationIssue


class HallucinationDetector:
    """Detect potential hallucinations in LLM-generated citations."""

    # Suspicious patterns in author fields
    AUTHOR_PATTERNS = [
        (r"\bet al\.?\b", "Contains 'et al.' which should be expanded"),
        (r"^\s*$", "Empty author field"),
        (r"^[A-Z]\.$", "Single letter author name"),
        (r"^(Author|Unknown|TBD|TODO)$", "Placeholder author name"),
        (r"^Anonymous$", "Anonymous author (verify if intentional)"),
        (r"^\W+$", "Non-alphanumeric author name"),
        (r"^(First|Last)name$", "Template author name"),
    ]

    # Suspicious patterns in titles (using string methods instead of regex)
    TITLE_PATTERNS = [
        (
            "generic_single_word",
            "Generic title like 'Title', 'Paper', 'Article', 'Study'",
        ),
        ("ellipsis_ending", "Truncated title ending with ellipsis (...)"),
        ("bracketed_placeholder", "Bracketed placeholder title [...]"),
        (
            "placeholder_prefix",
            "Placeholder title starting with TODO/TBD/FIXME",
        ),
        ("untitled_prefix", "Untitled document"),
    ]

    # Suspicious patterns in journal names (using string methods instead of regex)
    JOURNAL_PATTERNS = [
        (
            "generic_journal",
            "Generic journal name like 'Journal', 'Conference', 'Proceedings'",
        ),
        (
            "international_generic",
            "Too generic journal name like 'International Journal'",
        ),
        ("bracketed_journal", "Bracketed placeholder journal [...]"),
        ("placeholder_journal", "Placeholder journal starting with TODO/TBD"),
    ]

    # Common hallucinated author name patterns
    HALLUCINATED_AUTHORS = {
        "Smith et al",
        "Jones et al",
        "Johnson et al",
        "Williams et al",
        "Brown et al",
        "Davis et al",
        "Miller et al",
        "Wilson et al",
        "Moore et al",
        "Taylor et al",
        "Anderson et al",
        "Thomas et al",
        "Jackson et al",
        "White et al",
        "Harris et al",
        "Martin et al",
        "Thompson et al",
        "Garcia et al",
        "Martinez et al",
        "Robinson et al",
        "Bhat et al",
        "Kumar et al",
        "Singh et al",
        "Patel et al",
        "Wang et al",
        "Li et al",
        "Zhang et al",
        "Chen et al",
        "Liu et al",
        "Yang et al",
        "Huang et al",
        "Zhao et al",
    }

    def __init__(self):
        """Initialize detector."""
        self.logger = logging.getLogger(__name__)

    def check_citation(
        self, original: dict[str, any], validated: CitationData
    ) -> list[ValidationIssue]:
        """
        Check for hallucinations by comparing original vs validated data.

        Args:
            original: Original citation data (from LLM)
            validated: Validated citation data (from authoritative source)

        Returns:
            List of detected issues
        """
        issues = []

        # Only check if we have validated data from a trusted source
        if validated.source == DataSource.LLM_OUTPUT:
            # Can't compare, but check for obvious issues
            issues.extend(self._check_standalone_issues(original))
        else:
            # Compare original vs validated
            issues.extend(
                self._check_author_hallucinations(original, validated)
            )
            issues.extend(self._check_title_hallucinations(original, validated))
            issues.extend(self._check_year_hallucinations(original, validated))
            issues.extend(
                self._check_journal_hallucinations(original, validated)
            )

        return issues

    def _check_standalone_issues(
        self, citation: dict[str, any]
    ) -> list[ValidationIssue]:
        """Check for obvious issues in unvalidated citations."""
        issues = []

        # Check authors
        if authors := citation.get("author", ""):
            # Check patterns without regex
            authors_lower = authors.lower().strip()

            # Pattern checks based on original AUTHOR_PATTERNS
            # Check for 'et al'
            if "et al." in authors_lower or " et al" in authors_lower:
                issues.append(
                    ValidationIssue(
                        field="author",
                        severity="warning",
                        message="Contains 'et al.' which should be expanded",
                        actual=authors,
                    )
                )

            # Check for empty
            elif not authors_lower:
                issues.append(
                    ValidationIssue(
                        field="author",
                        severity="warning",
                        message="Empty author field",
                        actual=authors,
                    )
                )

            # Check for single letter like "A."
            elif (
                len(authors.strip()) == 2
                and authors.strip()[0].isupper()
                and authors.strip()[1] == "."
            ):
                issues.append(
                    ValidationIssue(
                        field="author",
                        severity="warning",
                        message="Single letter author name",
                        actual=authors,
                    )
                )

            # Check for placeholder names
            elif authors_lower in ["author", "unknown", "tbd", "todo"]:
                issues.append(
                    ValidationIssue(
                        field="author",
                        severity="warning",
                        message="Placeholder author name",
                        actual=authors,
                    )
                )

            # Check for anonymous
            elif authors_lower == "anonymous":
                issues.append(
                    ValidationIssue(
                        field="author",
                        severity="warning",
                        message="Anonymous author (verify if intentional)",
                        actual=authors,
                    )
                )

            # Check for non-alphanumeric only
            elif not any(c.isalnum() for c in authors):
                issues.append(
                    ValidationIssue(
                        field="author",
                        severity="warning",
                        message="Non-alphanumeric author name",
                        actual=authors,
                    )
                )

            # Check for template names
            elif authors_lower in ["firstname", "lastname"]:
                issues.append(
                    ValidationIssue(
                        field="author",
                        severity="warning",
                        message="Template author name",
                        actual=authors,
                    )
                )

            # Check for common hallucinated patterns
            if authors in self.HALLUCINATED_AUTHORS:
                issues.append(
                    ValidationIssue(
                        field="author",
                        severity="error",
                        message="Common hallucinated author pattern detected",
                        actual=authors,
                    )
                )

        # Check title
        if title := citation.get("title", ""):
            # Check title patterns without regex
            title_lower = title.lower().strip()

            # Check for generic titles
            if title_lower in ["title", "paper", "article", "study"]:
                issues.append(
                    ValidationIssue(
                        field="title",
                        severity="warning",
                        message="Generic title",
                        actual=title,
                    )
                )

            # Check for truncated (ellipsis)
            elif title.endswith("..."):
                issues.append(
                    ValidationIssue(
                        field="title",
                        severity="warning",
                        message="Truncated title (ellipsis)",
                        actual=title,
                    )
                )

            # Check for bracketed placeholder
            elif title.startswith("[") and title.endswith("]"):
                issues.append(
                    ValidationIssue(
                        field="title",
                        severity="warning",
                        message="Bracketed placeholder title",
                        actual=title,
                    )
                )

            # Check for TODO/TBD/FIXME
            elif title_lower.startswith(("todo", "tbd", "fixme")):
                issues.append(
                    ValidationIssue(
                        field="title",
                        severity="warning",
                        message="Placeholder title",
                        actual=title,
                    )
                )

            # Check for untitled
            elif title_lower.startswith("untitled"):
                issues.append(
                    ValidationIssue(
                        field="title",
                        severity="warning",
                        message="Untitled document",
                        actual=title,
                    )
                )

        # Check journal
        if journal := citation.get("journal", ""):
            # Check journal patterns without regex
            journal_lower = journal.lower().strip()

            # Check for generic journal names
            if journal_lower in [
                "journal",
                "conference",
                "proceedings",
                "international journal",
                "international conference",
            ]:
                issues.append(
                    ValidationIssue(
                        field="journal",
                        severity="warning",
                        message="Generic or too generic journal name",
                        actual=journal,
                    )
                )

            # Check for bracketed placeholder
            elif journal.startswith("[") and journal.endswith("]"):
                issues.append(
                    ValidationIssue(
                        field="journal",
                        severity="warning",
                        message="Bracketed placeholder journal",
                        actual=journal,
                    )
                )

            # Check for TODO/TBD
            elif journal_lower.startswith(("todo", "tbd")):
                issues.append(
                    ValidationIssue(
                        field="journal",
                        severity="warning",
                        message="Placeholder journal",
                        actual=journal,
                    )
                )

        return issues

    def _check_author_hallucinations(
        self, original: dict[str, any], validated: CitationData
    ) -> list[ValidationIssue]:
        """Check for author name hallucinations."""
        issues = []

        original_authors = original.get("author", "")
        if not original_authors or not validated.authors:
            return issues

        # Format validated authors for comparison
        validated_names = []
        for author in validated.authors:
            if author.family_name and author.given_name:
                validated_names.append(
                    f"{author.given_name} {author.family_name}"
                )
            elif author.full_name:
                validated_names.append(author.full_name)

        validated_author_str = ", ".join(validated_names)

        # Check for "et al" when we have full author list
        if "et al" in original_authors.lower() and len(validated.authors) > 1:
            issues.append(
                ValidationIssue(
                    field="author",
                    severity="error",
                    message="LLM used 'et al' but full author list is available",
                    expected=validated_author_str,
                    actual=original_authors,
                )
            )

        # Check for completely different authors (likely hallucination)
        similarity = SequenceMatcher(
            None, original_authors.lower(), validated_author_str.lower()
        ).ratio()

        if similarity < 0.3:  # Very low similarity
            issues.append(
                ValidationIssue(
                    field="author",
                    severity="error",
                    message="Author names appear to be hallucinated",
                    expected=validated_author_str,
                    actual=original_authors,
                )
            )
        elif similarity < 0.7:  # Moderate similarity
            issues.append(
                ValidationIssue(
                    field="author",
                    severity="warning",
                    message="Author names differ significantly from validated data",
                    expected=validated_author_str,
                    actual=original_authors,
                )
            )

        return issues

    def _check_title_hallucinations(
        self, original: dict[str, any], validated: CitationData
    ) -> list[ValidationIssue]:
        """Check for title hallucinations."""
        issues = []

        original_title = original.get("title", "")
        validated_title = validated.title

        if not original_title or not validated_title:
            return issues

        # Normalize for comparison
        orig_normalized = self._normalize_text(original_title)
        valid_normalized = self._normalize_text(validated_title)

        similarity = SequenceMatcher(
            None, orig_normalized, valid_normalized
        ).ratio()

        if similarity < 0.5:  # Significantly different
            issues.append(
                ValidationIssue(
                    field="title",
                    severity="error",
                    message="Title appears to be incorrect",
                    expected=validated_title,
                    actual=original_title,
                )
            )
        elif similarity < 0.8:  # Somewhat different
            issues.append(
                ValidationIssue(
                    field="title",
                    severity="warning",
                    message="Title differs from validated source",
                    expected=validated_title,
                    actual=original_title,
                )
            )

        return issues

    def _check_year_hallucinations(
        self, original: dict[str, any], validated: CitationData
    ) -> list[ValidationIssue]:
        """Check for year hallucinations."""
        issues = []

        original_year = str(original.get("year", "")).strip()
        validated_year = validated.year

        if not original_year or not validated_year:
            return issues

        try:
            orig_year_int = int(original_year)
            if orig_year_int != validated_year:
                issues.append(
                    ValidationIssue(
                        field="year",
                        severity="error",
                        message="Publication year is incorrect",
                        expected=str(validated_year),
                        actual=original_year,
                    )
                )
        except ValueError:
            issues.append(
                ValidationIssue(
                    field="year",
                    severity="error",
                    message="Invalid year format",
                    expected=str(validated_year),
                    actual=original_year,
                )
            )

        return issues

    def _check_journal_hallucinations(
        self, original: dict[str, any], validated: CitationData
    ) -> list[ValidationIssue]:
        """Check for journal name hallucinations."""
        issues = []

        original_journal = original.get("journal", "")
        validated_journal = validated.journal

        if not original_journal or not validated_journal:
            return issues

        # Normalize for comparison
        orig_normalized = self._normalize_text(original_journal)
        valid_normalized = self._normalize_text(validated_journal)

        similarity = SequenceMatcher(
            None, orig_normalized, valid_normalized
        ).ratio()

        if similarity < 0.5:  # Very different
            issues.append(
                ValidationIssue(
                    field="journal",
                    severity="error",
                    message="Journal name appears to be incorrect",
                    expected=validated_journal,
                    actual=original_journal,
                )
            )

        return issues

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Remove punctuation, lowercase, collapse whitespace without regex
        chars = []
        for char in text.lower():
            if char.isalnum() or char.isspace() or char == "_":
                chars.append(char)
            else:
                chars.append(" ")

        text = "".join(chars)
        # Collapse whitespace
        text = " ".join(text.split())
        return text

    def get_hallucination_score(self, issues: list[ValidationIssue]) -> float:
        """
        Calculate overall hallucination score.

        Returns:
            Score from 0.0 (no hallucinations) to 1.0 (severe hallucinations)
        """
        if not issues:
            return 0.0

        error_count = sum(1 for issue in issues if issue.severity == "error")
        warning_count = sum(
            1 for issue in issues if issue.severity == "warning"
        )

        # Weight errors more heavily
        score = (error_count * 1.0 + warning_count * 0.5) / 10.0

        return min(score, 1.0)  # Cap at 1.0
