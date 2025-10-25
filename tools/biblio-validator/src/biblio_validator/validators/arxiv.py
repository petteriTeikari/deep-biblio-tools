"""arXiv validator implementation."""

import re
from typing import Any
from xml.etree import ElementTree

from ..models.citation import Citation, ValidationResult
from .base import BaseValidator


class ArxivValidator(BaseValidator):
    """Validates citations against arXiv database."""

    API_URL = "http://export.arxiv.org/api/query"

    def get_source_name(self) -> str:
        return "arxiv"

    def validate(self, citation: Citation) -> ValidationResult:
        """Validate citation against arXiv."""
        # Check if citation contains arXiv ID
        arxiv_pattern = r"(\d{4}\.\d{4,5}|[a-z\-]+/\d{7})"
        arxiv_match = re.search(arxiv_pattern, citation.text)

        if arxiv_match:
            # Direct ID lookup
            arxiv_id = arxiv_match.group(1)
            return self._validate_by_id(citation, arxiv_id)

        # Extract components for search
        year_match = re.search(r"(19|20)\d{2}", citation.key)
        year = year_match.group(0) if year_match else None
        author = re.sub(r"\d{4}$", "", citation.key).rstrip("EtAl")

        if not author:
            return ValidationResult(
                citation=citation,
                is_valid=False,
                confidence=0.0,
                issues=["Could not extract author from citation key"],
            )

        # Search arXiv
        search_query = f"au:{author}"
        if year:
            # arXiv uses submittedDate for year filtering
            search_query += f" AND submittedDate:[{year}0101 TO {year}1231]"

        params = {
            "search_query": search_query,
            "max_results": 10,
            "sortBy": "relevance",
        }

        try:
            response = self.session.get(
                self.API_URL, params=params, timeout=self.timeout
            )
            response.raise_for_status()

            # Parse XML response
            root = ElementTree.fromstring(response.text)
            # Define namespace
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.findall("atom:entry", ns)

            if not entries:
                return ValidationResult(
                    citation=citation,
                    is_valid=False,
                    confidence=0.0,
                    issues=["No matching entries found in arXiv"],
                )

            # Find best match
            best_match = self._find_best_match(
                citation, entries, author, year, ns
            )

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
                    issues=["No sufficiently confident match found in arXiv"],
                    suggestions=self._generate_suggestions(entries, ns),
                )

        except Exception as e:
            return ValidationResult(
                citation=citation,
                is_valid=False,
                confidence=0.0,
                issues=[f"arXiv API error: {str(e)}"],
            )

    def _validate_by_id(
        self, citation: Citation, arxiv_id: str
    ) -> ValidationResult:
        """Validate citation by arXiv ID."""
        params = {"id_list": arxiv_id}

        try:
            response = self.session.get(
                self.API_URL, params=params, timeout=self.timeout
            )
            response.raise_for_status()

            root = ElementTree.fromstring(response.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entry = root.find("atom:entry", ns)

            if entry is not None:
                entry_data = self._extract_entry_data(entry, ns)
                return ValidationResult(
                    citation=citation,
                    is_valid=True,
                    confidence=1.0,  # Direct ID match
                    source=self.get_source_name(),
                    matched_entry=entry_data,
                )
            else:
                return ValidationResult(
                    citation=citation,
                    is_valid=False,
                    confidence=0.0,
                    issues=[f"arXiv ID {arxiv_id} not found"],
                )

        except Exception as e:
            return ValidationResult(
                citation=citation,
                is_valid=False,
                confidence=0.0,
                issues=[f"arXiv API error: {str(e)}"],
            )

    def _find_best_match(
        self,
        citation: Citation,
        entries: list,
        author: str,
        year: str,
        ns: dict,
    ) -> dict[str, Any]:
        """Find the best matching entry from arXiv results."""
        best_score = 0
        best_entry = None

        for entry in entries:
            score = 0
            entry_data = self._extract_entry_data(entry, ns)

            # Check year match
            if year and entry_data["year"] == year:
                score += 0.5

            # Check author match
            if author and entry_data["authors"]:
                # Check if search author matches any entry author
                for entry_author in entry_data["authors"]:
                    last_name = entry_author.split()[-1]
                    if (
                        author.lower() in last_name.lower()
                        or last_name.lower() in author.lower()
                    ):
                        score += 0.4
                        break

            # Check title similarity
            title = entry_data["title"].lower()
            citation_words = set(citation.text.lower().split())
            title_words = set(title.split())
            common_words = citation_words & title_words
            if len(common_words) > 2:
                score += 0.1 * min(len(common_words) / 10, 0.1)

            if score > best_score:
                best_score = score
                best_entry = entry_data

        if best_score >= 0.7:
            return {"confidence": best_score, "entry": best_entry}

        return None

    def _extract_entry_data(self, entry, ns: dict) -> dict[str, Any]:
        """Extract relevant data from arXiv entry XML."""
        # Extract title
        title_elem = entry.find("atom:title", ns)
        title = title_elem.text.strip() if title_elem is not None else ""

        # Extract authors
        authors = []
        for author_elem in entry.findall("atom:author", ns):
            name_elem = author_elem.find("atom:name", ns)
            if name_elem is not None:
                authors.append(name_elem.text)

        # Extract published date and year
        published_elem = entry.find("atom:published", ns)
        published = published_elem.text if published_elem is not None else ""
        year = published[:4] if published else ""

        # Extract arXiv ID
        id_elem = entry.find("atom:id", ns)
        arxiv_url = id_elem.text if id_elem is not None else ""
        arxiv_id = arxiv_url.split("/")[-1] if arxiv_url else ""

        # Extract abstract
        summary_elem = entry.find("atom:summary", ns)
        abstract = summary_elem.text.strip() if summary_elem is not None else ""

        return {
            "title": title,
            "authors": authors,
            "author": "; ".join(authors),
            "year": year,
            "arxiv_id": arxiv_id,
            "url": arxiv_url,
            "abstract": abstract[:200] + "..."
            if len(abstract) > 200
            else abstract,
        }

    def _generate_suggestions(self, entries: list, ns: dict) -> list:
        """Generate suggestions from arXiv results."""
        suggestions = []
        for entry in entries[:3]:
            data = self._extract_entry_data(entry, ns)
            if data["authors"] and data["year"]:
                first_author = data["authors"][0].split()[-1]
                suggestions.append(
                    f"Did you mean {first_author} ({data['year']}), arXiv:{data['arxiv_id']}?"
                )
        return suggestions
