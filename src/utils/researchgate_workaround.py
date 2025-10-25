"""
ResearchGate workaround utilities.

Handles ResearchGate links that are blocked from robotic crawling by:
1. Extracting paper titles from ResearchGate URLs
2. Searching for alternative sources via Google Scholar
3. Finding DOI-enabled versions from publishers
"""

import logging

# import re  # Banned - using string methods instead
import time
from urllib.parse import quote_plus, unquote, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ResearchGateWorkaround:
    """Workaround for blocked ResearchGate links."""

    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def process_researchgate_url(self, url: str) -> dict | None:
        """
        Process a ResearchGate URL to find alternative sources.

        Args:
            url: ResearchGate URL

        Returns:
            Dictionary with alternative source information or None
        """
        if not self._is_researchgate_url(url):
            return None

        # Extract title from URL
        title = self._extract_title_from_url(url)
        if not title:
            logger.warning(
                f"Could not extract title from ResearchGate URL: {url}"
            )
            return None

        logger.info(f"Extracted title from ResearchGate URL: {title}")

        # Search for alternative sources
        alternative_info = self._search_for_alternatives(title)

        if alternative_info:
            alternative_info["original_url"] = url
            alternative_info["extracted_title"] = title
            alternative_info["guessed"] = True  # Mark as guessed

        return alternative_info

    def _is_researchgate_url(self, url: str) -> bool:
        """Check if URL is from ResearchGate."""
        return "researchgate.net" in url.lower()

    def _extract_title_from_url(self, url: str) -> str | None:
        """
        Extract paper title from ResearchGate URL.

        ResearchGate URLs typically have format:
        https://www.researchgate.net/publication/NUMBER_Title_With_Underscores
        """
        try:
            # Parse URL to get path
            parsed = urlparse(url)
            path = parsed.path

            # Extract the part after publication number using string methods
            # Pattern: /publication/NUMBER_Title_With_Underscores
            if "/publication/" not in path:
                return None

            # Find the position after /publication/
            pub_pos = path.find("/publication/") + len("/publication/")
            if pub_pos >= len(path):
                return None

            # Find the underscore after the number
            underscore_pos = path.find("_", pub_pos)
            if underscore_pos == -1:
                return None

            # Extract everything after the underscore until ? or end
            title_start = underscore_pos + 1
            title_end = path.find("?", title_start)
            if title_end == -1:
                title_end = len(path)

            title_part = path[title_start:title_end]

            # Replace underscores with spaces and decode URL encoding
            title = unquote(title_part).replace("_", " ")

            # Clean up title using string methods instead of regex
            title = " ".join(title.split()).strip()

            # Capitalize properly
            title = title.title()

            return title if len(title) > 10 else None

        except Exception as e:
            logger.debug(f"Error extracting title from ResearchGate URL: {e}")
            return None

    def _search_for_alternatives(self, title: str) -> dict | None:
        """
        Search for alternative sources using the extracted title.

        Args:
            title: Paper title to search for

        Returns:
            Dictionary with alternative source info or None
        """
        # Try Google Scholar search
        scholar_result = self._search_google_scholar(title)
        if scholar_result:
            return scholar_result

        # Could add other search methods here (Semantic Scholar, etc.)

        return None

    def _search_google_scholar(self, title: str) -> dict | None:
        """
        Search Google Scholar for the paper and extract information.

        Args:
            title: Paper title to search

        Returns:
            Dictionary with paper information or None
        """
        try:
            # Be respectful with delays
            time.sleep(self.delay)

            # Construct Google Scholar search URL
            query = quote_plus(title)
            scholar_url = f"https://scholar.google.com/scholar?q={query}"

            logger.debug(f"Searching Google Scholar: {scholar_url}")

            response = self.session.get(scholar_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Find first search result
            results = soup.find_all("div", class_="gs_r")
            if not results:
                logger.warning("No Google Scholar results found")
                return None

            first_result = results[0]

            # Extract information from first result
            info = self._parse_scholar_result(first_result)

            if info:
                logger.info(
                    f"Found Google Scholar result: {info.get('title', 'Unknown')[:50]}..."
                )

            return info

        except requests.RequestException as e:
            logger.warning(f"Google Scholar search failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error searching Google Scholar: {e}")
            return None

    def _parse_scholar_result(self, result_div) -> dict | None:
        """
        Parse a Google Scholar search result.

        Args:
            result_div: BeautifulSoup div element for a scholar result

        Returns:
            Dictionary with extracted information or None
        """
        try:
            info = {}

            # Extract title
            title_elem = result_div.find("h3", class_="gs_rt")
            if title_elem:
                # Remove citation links and get clean title
                for link in title_elem.find_all("a"):
                    link.extract()
                title = title_elem.get_text().strip()
                if title:
                    info["title"] = title

            # Extract authors and year from the citation line
            citation_elem = result_div.find("div", class_="gs_a")
            if citation_elem:
                citation_text = citation_elem.get_text()

                # Extract authors (before first dash or year) using string methods
                authors_str = self._extract_authors_from_citation_text(
                    citation_text
                )
                if authors_str:
                    # Parse authors
                    authors = self._parse_authors_from_citation(authors_str)
                    if authors:
                        info["authors"] = authors

                # Extract year using string methods instead of regex
                year = self._extract_year_from_text(citation_text)
                if year:
                    info["year"] = year

            # Look for DOI or alternative URLs in the result
            links = result_div.find_all("a")
            for link in links:
                href = link.get("href", "")
                if "doi.org" in href:
                    info["doi_url"] = href
                    # Extract DOI using string methods
                    doi = self._extract_doi_from_url(href)
                    if doi:
                        info["doi"] = doi
                        break
                elif any(
                    domain in href
                    for domain in [
                        "mdpi.com",
                        "ieee.org",
                        "acm.org",
                        "springer.com",
                    ]
                ):
                    info["publisher_url"] = href

            # Look for "Cited by" information for credibility using string methods
            citations = self._extract_citation_count(result_div)
            if citations is not None:
                info["citations"] = citations

            return info if info else None

        except Exception as e:
            logger.debug(f"Error parsing Scholar result: {e}")
            return None

    def _parse_authors_from_citation(self, authors_str: str) -> list[str]:
        """
        Parse authors from Google Scholar citation format.

        Args:
            authors_str: Author string from citation

        Returns:
            List of author surnames
        """
        try:
            # Clean up the string using string methods instead of regex
            authors_str = " ".join(authors_str.strip().split())

            # Handle different formats
            if "," in authors_str:
                # "A Author, B Author, C Author" format
                parts = [part.strip() for part in authors_str.split(",")]
            else:
                # "A Author B Author C Author" format (less reliable)
                parts = authors_str.split()
                # Try to group into pairs (FirstName LastName)
                if len(parts) % 2 == 0:
                    parts = [
                        f"{parts[i]} {parts[i + 1]}"
                        for i in range(0, len(parts), 2)
                    ]
                else:
                    # Fallback: just return the string as is
                    return [authors_str]

            surnames = []
            for part in parts:
                # Extract surname (last word)
                words = part.strip().split()
                if words:
                    surname = words[-1]
                    # Basic validation using string methods instead of regex
                    if self._is_valid_surname(surname):
                        surnames.append(surname.capitalize())

            return surnames[:10]  # Limit to reasonable number

        except Exception as e:
            logger.debug(f"Error parsing authors: {e}")
            return []

    def _extract_year_from_text(self, text: str) -> str | None:
        """Extract 4-digit year from text using string methods instead of regex."""
        words = text.split()
        for word in words:
            # Clean word of punctuation
            clean_word = word.strip(".,;:()[]")
            if len(clean_word) == 4 and clean_word.isdigit():
                year = int(clean_word)
                # Check if it's a reasonable year range
                if 1900 <= year <= 2100:
                    return clean_word
        return None

    def _extract_doi_from_url(self, url: str) -> str | None:
        """Extract DOI from a doi.org URL using string methods."""
        if "doi.org/" not in url:
            return None

        # Find the position after "doi.org/"
        doi_start = url.find("doi.org/") + len("doi.org/")
        if doi_start >= len(url):
            return None

        # Extract everything after "doi.org/"
        doi = url[doi_start:]

        # Clean up any URL parameters or fragments
        if "?" in doi:
            doi = doi.split("?")[0]
        if "#" in doi:
            doi = doi.split("#")[0]

        return doi.strip() if doi else None

    def _is_valid_surname(self, surname: str) -> bool:
        """Check if a string is a valid surname using string methods."""
        if not surname or len(surname) <= 1:
            return False

        # Check if contains only letters (no numbers or special chars)
        if not surname.isalpha():
            return False

        # Additional checks could be added here
        return True

    def _extract_authors_from_citation_text(
        self, citation_text: str
    ) -> str | None:
        """Extract authors from citation text using string methods."""
        # Find the first dash or digit, which usually separates authors from publication info
        words = citation_text.split()
        authors_words = []

        for word in words:
            # Stop at dash or when we find a 4-digit year
            if word.startswith("-") or (len(word) == 4 and word.isdigit()):
                break
            authors_words.append(word)

        if authors_words:
            authors_str = " ".join(authors_words).strip()
            # Remove trailing comma
            if authors_str.endswith(","):
                authors_str = authors_str[:-1]
            return authors_str

        return None

    def _extract_citation_count(self, result_div) -> int | None:
        """Extract citation count from Scholar result using string methods."""
        try:
            # Find all links and check their text
            links = result_div.find_all("a")
            for link in links:
                text = link.get_text().strip()
                if text.startswith("Cited by "):
                    # Extract number after "Cited by "
                    cited_part = text[len("Cited by ") :].strip()
                    # Remove any non-digit characters and get the number
                    number_str = ""
                    for char in cited_part:
                        if char.isdigit():
                            number_str += char
                        else:
                            break
                    if number_str:
                        return int(number_str)
            return None
        except Exception as e:
            logger.debug(f"Error extracting citation count: {e}")
            return None


def process_researchgate_link(url: str) -> dict | None:
    """
    Convenience function to process a ResearchGate link.

    Args:
        url: ResearchGate URL

    Returns:
        Dictionary with alternative source information or None
    """
    workaround = ResearchGateWorkaround()
    return workaround.process_researchgate_url(url)


def extract_title_from_researchgate_url(url: str) -> str | None:
    """
    Extract title from ResearchGate URL without making network requests.

    Args:
        url: ResearchGate URL

    Returns:
        Extracted title or None
    """
    workaround = ResearchGateWorkaround()
    return workaround._extract_title_from_url(url)
