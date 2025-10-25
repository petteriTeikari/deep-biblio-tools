"""ArXiv API client for deterministic paper validation."""

import logging

# import re  # Banned - using string methods instead
import xml.etree.ElementTree as ET
from datetime import datetime
from xml.etree.ElementTree import XMLParser

from .base import APIClient


class ArXivClient(APIClient):
    """Client for arXiv API with deterministic behavior."""

    BASE_URL = "http://export.arxiv.org/api/query"

    # Namespaces used in arXiv responses
    NAMESPACES = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

    def __init__(self, delay: float = 0.5):
        """
        Initialize arXiv client.

        Args:
            delay: Delay between requests in seconds (be nice to arXiv)
        """
        super().__init__(delay=delay)
        self.logger = logging.getLogger(__name__)

    def get_by_id(self, arxiv_id: str) -> dict[str, any] | None:
        """
        Get paper data by arXiv ID.

        Args:
            arxiv_id: The arXiv ID (e.g., "2301.12345" or "math.GT/0309136")

        Returns:
            Parsed paper data or None if not found
        """
        # Clean arXiv ID
        arxiv_id = arxiv_id.strip()
        if arxiv_id.startswith("arxiv:"):
            arxiv_id = arxiv_id[6:]
        if "arxiv.org/abs/" in arxiv_id:
            arxiv_id = arxiv_id.split("arxiv.org/abs/")[-1]

        # Remove version if present (e.g., "2301.12345v2" -> "2301.12345")
        # Remove version if present without regex
        if "v" in arxiv_id:
            v_pos = arxiv_id.rfind("v")
            if v_pos > 0 and arxiv_id[v_pos + 1 :].isdigit():
                arxiv_id = arxiv_id[:v_pos]

        params = {"id_list": arxiv_id, "max_results": 1}

        try:
            response = self._make_request(
                self.BASE_URL, params=params, json_response=False
            )
            if response and response.text:
                entries = self._parse_arxiv_response(response.text)
                if entries:
                    return entries[0]
        except Exception as e:
            self.logger.error(f"Error fetching arXiv ID {arxiv_id}: {e}")

        return None

    def search_by_title(
        self, title: str, author: str | None = None, limit: int = 5
    ) -> list[dict[str, any]]:
        """
        Search for papers by title and optionally author.

        Args:
            title: Title to search for
            author: Optional author name to refine search
            limit: Maximum number of results

        Returns:
            List of parsed paper data
        """
        # Build search query
        query_parts = [f'ti:"{title}"']
        if author:
            query_parts.append(f'au:"{author}"')

        params = {
            "search_query": " AND ".join(query_parts),
            "max_results": limit,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        try:
            response = self._make_request(
                self.BASE_URL, params=params, json_response=False
            )
            if response and response.text:
                return self._parse_arxiv_response(response.text)
        except Exception as e:
            self.logger.error(f"Error searching arXiv for '{title}': {e}")

        return []

    def _parse_arxiv_response(self, xml_text: str) -> list[dict[str, any]]:
        """Parse arXiv XML response into standard format."""
        try:
            # Create a secure parser that prevents XXE attacks
            parser = XMLParser(target=ET.TreeBuilder())
            parser.entity = {}  # Disable entity resolution
            parser.default = lambda x: None  # Ignore DTD

            root = ET.fromstring(xml_text, parser=parser)
            entries = []

            for entry in root.findall("atom:entry", self.NAMESPACES):
                parsed = self._parse_entry(entry)
                if parsed:
                    entries.append(parsed)

            return entries

        except ET.ParseError as e:
            self.logger.error(f"Error parsing arXiv XML: {e}")
            return []

    def _parse_entry(self, entry: ET.Element) -> dict[str, any] | None:
        """Parse single arXiv entry."""
        try:
            # Extract arXiv ID
            id_elem = entry.find("atom:id", self.NAMESPACES)
            if id_elem is None:
                return None

            arxiv_id = id_elem.text.split("/abs/")[-1]

            # Extract basic metadata
            result = {
                "arxiv_id": arxiv_id,
                "title": self._get_text(entry, "atom:title"),
                "abstract": self._get_text(entry, "atom:summary"),
                "authors": self._extract_authors(entry),
                "categories": self._extract_categories(entry),
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}.pdf",
            }

            # Extract dates
            published = self._get_text(entry, "atom:published")
            if published:
                result["published_date"] = published
                # Extract year
                try:
                    year = datetime.fromisoformat(
                        published.replace("Z", "+00:00")
                    ).year
                    result["year"] = year
                except Exception:
                    pass

            updated = self._get_text(entry, "atom:updated")
            if updated:
                result["updated_date"] = updated

            # Extract DOI if present
            doi_elem = entry.find("arxiv:doi", self.NAMESPACES)
            if doi_elem is not None and doi_elem.text:
                result["doi"] = doi_elem.text

            # Extract journal reference if present
            journal_ref = entry.find("arxiv:journal_ref", self.NAMESPACES)
            if journal_ref is not None and journal_ref.text:
                result["journal_ref"] = journal_ref.text
                # Try to extract journal name
                result["journal"] = self._parse_journal_ref(journal_ref.text)

            # Extract comment (often contains conference info)
            comment = entry.find("arxiv:comment", self.NAMESPACES)
            if comment is not None and comment.text:
                result["comment"] = comment.text

            return result

        except Exception as e:
            self.logger.error(f"Error parsing arXiv entry: {e}")
            return None

    def _get_text(self, parent: ET.Element, tag: str) -> str | None:
        """Get text content of a child element."""
        elem = parent.find(tag, self.NAMESPACES)
        if elem is not None and elem.text:
            # Clean up whitespace
            return " ".join(elem.text.split())
        return None

    def _extract_authors(self, entry: ET.Element) -> list[dict[str, str]]:
        """Extract author information."""
        authors = []

        for author_elem in entry.findall("atom:author", self.NAMESPACES):
            name_elem = author_elem.find("atom:name", self.NAMESPACES)
            if name_elem is not None and name_elem.text:
                name = name_elem.text.strip()

                # Try to split into given/family names
                # This is heuristic - arXiv doesn't provide structured names
                author_dict = {"name": name}

                parts = name.split()
                if len(parts) >= 2:
                    # Assume last part is family name
                    author_dict["family"] = parts[-1]
                    author_dict["given"] = " ".join(parts[:-1])

                # Check for affiliation
                affil_elem = author_elem.find(
                    "arxiv:affiliation", self.NAMESPACES
                )
                if affil_elem is not None and affil_elem.text:
                    author_dict["affiliation"] = affil_elem.text.strip()

                authors.append(author_dict)

        return authors

    def _extract_categories(self, entry: ET.Element) -> list[str]:
        """Extract arXiv categories."""
        categories = []

        for cat_elem in entry.findall("atom:category", self.NAMESPACES):
            term = cat_elem.get("term")
            if term:
                categories.append(term)

        return categories

    def _parse_journal_ref(self, journal_ref: str) -> str | None:
        """Try to extract journal name from reference string."""
        # Common patterns in arXiv journal references
        # Examples:
        # "Phys. Rev. Lett. 123, 456789 (2019)"
        # "Nature 500, 123-126 (2013)"
        # "Proceedings of ICML 2020"

        # Remove year and page numbers
        # Remove year and page numbers without regex
        cleaned = journal_ref

        # Remove year in parentheses (2024) or at end
        if "(" in cleaned and ")" in cleaned:
            start = cleaned.rfind("(")
            end = cleaned.find(")", start)
            if start > 0 and end > start:
                year_part = cleaned[start + 1 : end]
                if len(year_part) == 4 and year_part.isdigit():
                    cleaned = cleaned[:start] + cleaned[end + 1 :]

        # Remove trailing year
        parts = cleaned.rstrip().split()
        if parts and len(parts[-1]) == 4 and parts[-1].isdigit():
            cleaned = " ".join(parts[:-1])

        # Remove page ranges (123-456 or 123, 456)
        result_parts = []
        skip_next = False
        for i, part in enumerate(cleaned.split()):
            if skip_next:
                skip_next = False
                continue

            # Check for page range with dash
            if "-" in part or "–" in part:
                segments = part.replace("–", "-").split("-")
                if len(segments) == 2 and all(
                    s.strip().isdigit() for s in segments if s.strip()
                ):
                    continue

            # Check for comma-separated pages
            if part.rstrip(",").isdigit():
                if (
                    i + 1 < len(cleaned.split())
                    and cleaned.split()[i + 1].strip().isdigit()
                ):
                    skip_next = True
                    continue

            result_parts.append(part)

        cleaned = " ".join(result_parts)

        # Remove trailing punctuation and whitespace
        cleaned = cleaned.rstrip()
        while cleaned and cleaned[-1] in ",.":
            cleaned = cleaned[:-1].rstrip()

        # Remove trailing volume numbers
        parts = cleaned.split()
        if parts and parts[-1].isdigit():
            cleaned = " ".join(parts[:-1])

        return cleaned.strip() if cleaned.strip() else None
