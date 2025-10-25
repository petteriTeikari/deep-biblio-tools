"""Citation-bibliography matching functionality."""

import re
from pathlib import Path
from typing import Any

from ..models.bibliography import BibEntry
from ..models.citation import Citation
from ..utils.parsers import parse_bibtex_file, parse_document_citations


class CitationMatcher:
    """Matches citations in documents to bibliography entries."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}

    def match_document_to_bib(
        self, document_path: Path, bibfile_path: Path
    ) -> dict[str, Any]:
        """Match citations in document to entries in bibliography."""
        # Parse document citations
        citations = parse_document_citations(document_path)
        citation_keys = {c.key for c in citations}

        # Parse bibliography entries
        bib_entries = parse_bibtex_file(bibfile_path)
        bib_keys = {e.key for e in bib_entries}

        # Find matches and mismatches
        matched_keys = citation_keys & bib_keys
        unmatched_citations = citation_keys - bib_keys
        unused_entries = bib_keys - citation_keys

        # Build detailed results
        results = {
            "total_citations": len(citation_keys),
            "total_entries": len(bib_keys),
            "matched": len(matched_keys),
            "unmatched_citations": sorted(list(unmatched_citations)),
            "unused_entries": sorted(list(unused_entries)),
            "match_details": self._build_match_details(
                citations, bib_entries, matched_keys
            ),
        }

        return results

    def _build_match_details(
        self,
        citations: list[Citation],
        entries: list[BibEntry],
        matched_keys: set[str],
    ) -> list[dict[str, Any]]:
        """Build detailed match information."""
        # Create lookup dictionaries
        citation_dict = {c.key: c for c in citations}
        entry_dict = {e.key: e for e in entries}

        details = []
        for key in sorted(matched_keys):
            detail = {
                "key": key,
                "citation_text": citation_dict[key].text,
                "entry_title": entry_dict[key].title,
                "entry_author": entry_dict[key].author,
                "entry_year": entry_dict[key].year,
            }
            details.append(detail)

        return details

    def find_potential_matches(
        self, unmatched_citation: str, entries: list[BibEntry]
    ) -> list[BibEntry]:
        """Find potential matches for an unmatched citation using fuzzy matching."""
        potential_matches = []

        # Extract year from citation if present
        year_match = re.search(r"\b(19|20)\d{2}\b", unmatched_citation)
        citation_year = year_match.group(0) if year_match else None

        # Extract author name patterns
        author_patterns = self._extract_author_patterns(unmatched_citation)

        for entry in entries:
            score = 0

            # Check year match
            if citation_year and entry.year == citation_year:
                score += 3

            # Check author match
            if entry.author:
                for pattern in author_patterns:
                    if pattern.lower() in entry.author.lower():
                        score += 2

            # Check title keywords
            if entry.title:
                citation_words = set(unmatched_citation.lower().split())
                title_words = set(entry.title.lower().split())
                common_words = citation_words & title_words
                score += len(common_words)

            if score >= 3:  # Threshold for potential match
                potential_matches.append((score, entry))

        # Sort by score and return top matches
        potential_matches.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in potential_matches[:5]]

    def _extract_author_patterns(self, citation_text: str) -> list[str]:
        """Extract potential author name patterns from citation."""
        patterns = []

        # Look for patterns like "Smith et al." or "Smith and Jones"
        # Pattern 1: Capitalized word followed by "et al" or "and"
        words = citation_text.split()
        for i, word in enumerate(words):
            if word[0].isupper() and len(word) > 2:
                if i + 1 < len(words) and words[i + 1] in ["et", "and"]:
                    patterns.append(word.rstrip(",."))
                elif i > 0 and words[i - 1] in ["and"]:
                    patterns.append(word.rstrip(",."))

        # Pattern 2: First capitalized word (often the first author)
        for word in words:
            if (
                word[0].isupper()
                and len(word) > 2
                and word not in ["The", "In", "On", "At"]
            ):
                patterns.append(word.rstrip(",."))
                break

        return patterns

    def generate_report(self, results: dict[str, Any]) -> str:
        """Generate a detailed matching report."""
        lines = [
            "# Citation-Bibliography Matching Report",
            "",
            f"**Total citations:** {results['total_citations']}",
            f"**Total bibliography entries:** {results['total_entries']}",
            f"**Matched:** {results['matched']}",
            f"**Unmatched citations:** {len(results['unmatched_citations'])}",
            f"**Unused entries:** {len(results['unused_entries'])}",
            "",
        ]

        if results["unmatched_citations"]:
            lines.extend(
                [
                    "## Unmatched Citations",
                    "",
                    "The following citations were not found in the bibliography:",
                    "",
                ]
            )
            for cite in results["unmatched_citations"]:
                lines.append(f"- `{cite}`")
            lines.append("")

        if results["unused_entries"]:
            lines.extend(
                [
                    "## Unused Bibliography Entries",
                    "",
                    "The following bibliography entries are not cited in the document:",
                    "",
                ]
            )
            for entry in results["unused_entries"]:
                lines.append(f"- `{entry}`")
            lines.append("")

        if results.get("match_details"):
            lines.extend(
                [
                    "## Matched Citations",
                    "",
                    "Successfully matched citations:",
                    "",
                ]
            )
            for detail in results["match_details"][:10]:  # Show first 10
                lines.append(
                    f"- **{detail['key']}**: {detail['entry_title']} ({detail['entry_year']})"
                )

        return "\n".join(lines)
