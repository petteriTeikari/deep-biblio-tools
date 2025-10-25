"""CrossRef validator implementation."""

import re
from typing import Any

from ..models.citation import Citation, ValidationResult
from .base import BaseValidator


class CrossRefValidator(BaseValidator):
    """Validates citations against CrossRef database."""

    API_URL = "https://api.crossref.org/works"

    def get_source_name(self) -> str:
        return "crossref"

    def validate(self, citation: Citation) -> ValidationResult:
        """Validate citation against CrossRef."""
        # Extract year from citation if present
        year_match = re.search(r"(19|20)\d{2}", citation.key)
        year = year_match.group(0) if year_match else None

        # Extract author name
        author = re.sub(r"\d{4}$", "", citation.key).rstrip("EtAl")

        # Build query
        query_parts = []
        if author:
            query_parts.append(f"author:{author}")
        if year:
            query_parts.append(f"published:{year}")

        if not query_parts:
            return ValidationResult(
                citation=citation,
                is_valid=False,
                confidence=0.0,
                issues=["Could not extract author or year from citation key"],
            )

        # Search CrossRef
        params = {"query": " ".join(query_parts), "rows": 5}

        try:
            data = self._make_request(self.API_URL, params)
            items = data.get("message", {}).get("items", [])

            if not items:
                return ValidationResult(
                    citation=citation,
                    is_valid=False,
                    confidence=0.0,
                    issues=["No matching entries found in CrossRef"],
                )

            # Find best match
            best_match = self._find_best_match(citation, items, author, year)

            if best_match:
                return ValidationResult(
                    citation=citation,
                    is_valid=True,
                    confidence=best_match["confidence"],
                    source=self.get_source_name(),
                    matched_entry=best_match["entry"],
                )
            else:
                return ValidationResult(
                    citation=citation,
                    is_valid=False,
                    confidence=0.3,
                    issues=["No sufficiently confident match found"],
                    suggestions=self._generate_suggestions(items),
                )

        except Exception as e:
            return ValidationResult(
                citation=citation,
                is_valid=False,
                confidence=0.0,
                issues=[f"CrossRef API error: {str(e)}"],
            )

    def _find_best_match(
        self, citation: Citation, items: list, author: str, year: str
    ) -> dict[str, Any]:
        """Find the best matching entry from search results."""
        best_score = 0
        best_entry = None

        for item in items:
            score = 0

            # Check year match
            published = item.get("published-print") or item.get(
                "published-online"
            )
            if published and year:
                item_year = str(published.get("date-parts", [[None]])[0][0])
                if item_year == year:
                    score += 0.5

            # Check author match
            authors = item.get("author", [])
            if authors and author:
                first_author = authors[0]
                family_name = first_author.get("family", "").lower()
                if (
                    author.lower() in family_name
                    or family_name in author.lower()
                ):
                    score += 0.4

            # Check title similarity (basic keyword matching)
            title = item.get("title", [""])[0].lower()
            citation_words = set(citation.text.lower().split())
            title_words = set(title.split())
            common_words = citation_words & title_words
            if len(common_words) > 2:
                score += 0.1 * min(len(common_words) / 10, 0.1)

            if score > best_score:
                best_score = score
                best_entry = item

        if best_score >= 0.7:  # Confidence threshold
            return {
                "confidence": best_score,
                "entry": self._format_entry(best_entry),
            }

        return None

    def _format_entry(self, item: dict[str, Any]) -> dict[str, Any]:
        """Format CrossRef entry for storage."""
        authors = item.get("author", [])
        author_str = "; ".join(
            [
                f"{a.get('given', '')} {a.get('family', '')}".strip()
                for a in authors
            ]
        )

        return {
            "title": item.get("title", [""])[0],
            "author": author_str,
            "year": self._extract_year(item),
            "journal": item.get("container-title", [""])[0],
            "doi": item.get("DOI"),
            "url": item.get("URL"),
            "type": item.get("type"),
        }

    def _extract_year(self, item: dict[str, Any]) -> str:
        """Extract year from CrossRef item."""
        published = item.get("published-print") or item.get("published-online")
        if published:
            date_parts = published.get("date-parts", [[None]])
            if date_parts and date_parts[0]:
                return str(date_parts[0][0])
        return ""

    def _generate_suggestions(self, items: list) -> list:
        """Generate suggestions from search results."""
        suggestions = []
        for item in items[:3]:  # Top 3 results
            authors = item.get("author", [])
            if authors:
                first_author = authors[0].get("family", "Unknown")
                year = self._extract_year(item)
                if year:
                    suggestions.append(f"Did you mean {first_author} ({year})?")
        return suggestions
