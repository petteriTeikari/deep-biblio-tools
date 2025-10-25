"""CrossRef API client for deterministic DOI validation."""

import logging
from urllib.parse import quote

from .base import APIClient


class CrossRefClient(APIClient):
    """Client for CrossRef API with deterministic behavior."""

    BASE_URL = "https://api.crossref.org"

    def __init__(self, email: str | None = None, delay: float = 0.5):
        """
        Initialize CrossRef client.

        Args:
            email: Email for polite use of API (gets better rate limits)
            delay: Delay between requests in seconds
        """
        super().__init__(delay=delay)
        self.logger = logging.getLogger(__name__)

        # Set user agent with email for polite use
        if email:
            self.session.headers["User-Agent"] = (
                f"DeepBiblioTools/1.0 (mailto:{email})"
            )
        else:
            self.session.headers["User-Agent"] = "DeepBiblioTools/1.0"

        # CrossRef prefers these headers
        self.session.headers["Accept"] = "application/json"

    def get_by_doi(self, doi: str) -> dict[str, any] | None:
        """
        Get citation data by DOI.

        Args:
            doi: The DOI to look up

        Returns:
            Parsed citation data or None if not found
        """
        # Clean DOI
        doi = doi.strip()
        if doi.startswith("doi:"):
            doi = doi[4:]
        if doi.startswith("https://doi.org/"):
            doi = doi[16:]
        if doi.startswith("http://doi.org/"):
            doi = doi[15:]

        url = f"{self.BASE_URL}/works/{quote(doi, safe='')}"

        try:
            data = self._make_request(url)
            if data and "message" in data:
                return self._parse_work(data["message"])
        except Exception as e:
            self.logger.error(f"Error fetching DOI {doi}: {e}")

        return None

    def search_by_title(
        self, title: str, author: str | None = None, limit: int = 5
    ) -> list[dict[str, any]]:
        """
        Search for works by title and optionally author.

        Args:
            title: Title to search for
            author: Optional author name to refine search
            limit: Maximum number of results

        Returns:
            List of parsed citation data
        """
        params = {
            "query.title": title,
            "rows": limit,
            "select": "DOI,title,author,published-print,published-online,container-title,volume,issue,page,publisher",
        }

        if author:
            params["query.author"] = author

        url = f"{self.BASE_URL}/works"

        try:
            data = self._make_request(url, params=params)
            if data and "message" in data and "items" in data["message"]:
                return [
                    self._parse_work(item) for item in data["message"]["items"]
                ]
        except Exception as e:
            self.logger.error(f"Error searching title '{title}': {e}")

        return []

    def get_bibtex(self, doi: str) -> str | None:
        """
        Get BibTeX entry directly from CrossRef.

        Args:
            doi: The DOI to get BibTeX for

        Returns:
            BibTeX string or None
        """
        # Clean DOI
        doi = doi.strip()
        if doi.startswith("doi:"):
            doi = doi[4:]

        url = f"https://doi.org/{quote(doi, safe='')}"
        headers = {
            "Accept": "application/x-bibtex",
            "User-Agent": self.session.headers["User-Agent"],
        }

        try:
            response = self._rate_limited_request(
                self.session.get,
                url,
                headers=headers,
                timeout=10,
                allow_redirects=True,
            )

            if response.status_code == 200:
                return response.text

        except Exception as e:
            self.logger.error(f"Error fetching BibTeX for {doi}: {e}")

        return None

    def _parse_work(self, work_data: dict) -> dict[str, any]:
        """Parse CrossRef work data into standard format."""
        result = {
            "doi": work_data.get("DOI"),
            "title": self._extract_title(work_data),
            "authors": self._extract_authors(work_data),
            "year": self._extract_year(work_data),
            "journal": self._extract_journal(work_data),
            "volume": work_data.get("volume"),
            "issue": work_data.get("issue"),
            "pages": work_data.get("page"),
            "publisher": work_data.get("publisher"),
            "type": work_data.get("type", "journal-article"),
        }

        # Add URL
        if result["doi"]:
            result["url"] = f"https://doi.org/{result['doi']}"

        return result

    def _extract_title(self, work_data: dict) -> str | None:
        """Extract title from CrossRef data."""
        title = work_data.get("title", [])
        if isinstance(title, list) and title:
            return title[0]
        return title if isinstance(title, str) else None

    def _extract_authors(self, work_data: dict) -> list[dict[str, str]]:
        """Extract and format authors from CrossRef data."""
        authors = []

        for author in work_data.get("author", []):
            parsed_author = {
                "given": author.get("given", ""),
                "family": author.get("family", ""),
                "name": author.get("name", ""),
            }

            # Add ORCID if available
            if author.get("ORCID"):
                parsed_author["orcid"] = author["ORCID"]

            # Add affiliation if available
            if author.get("affiliation"):
                affiliations = []
                for aff in author["affiliation"]:
                    if aff.get("name"):
                        affiliations.append(aff["name"])
                if affiliations:
                    parsed_author["affiliation"] = "; ".join(affiliations)

            authors.append(parsed_author)

        return authors

    def _extract_year(self, work_data: dict) -> int | None:
        """Extract publication year from CrossRef data."""
        # Try published-print first
        if date_parts := work_data.get("published-print", {}).get("date-parts"):
            if date_parts and date_parts[0] and date_parts[0][0]:
                return int(date_parts[0][0])

        # Try published-online
        if date_parts := work_data.get("published-online", {}).get(
            "date-parts"
        ):
            if date_parts and date_parts[0] and date_parts[0][0]:
                return int(date_parts[0][0])

        # Try issued date
        if date_parts := work_data.get("issued", {}).get("date-parts"):
            if date_parts and date_parts[0] and date_parts[0][0]:
                return int(date_parts[0][0])

        return None

    def _extract_journal(self, work_data: dict) -> str | None:
        """Extract journal/container title from CrossRef data."""
        container = work_data.get("container-title", [])
        if isinstance(container, list) and container:
            return container[0]
        return container if isinstance(container, str) else None
