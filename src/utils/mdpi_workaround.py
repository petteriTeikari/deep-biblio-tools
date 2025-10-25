"""
MDPI workaround utilities.

Handles MDPI links that are blocked from robotic crawling by:
1. Extracting paper information from MDPI URLs
2. Searching for alternative sources via DOI and Google Scholar
3. Finding open access versions when possible
"""

import logging

# import re  # Banned - using string methods instead
import time
from urllib.parse import quote_plus, urlparse

import requests
from bs4 import BeautifulSoup

from src.parsers import BibtexParser

logger = logging.getLogger(__name__)


class MDPIWorkaround:
    """Workaround for blocked MDPI links."""

    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def process_mdpi_url(self, url: str) -> dict | None:
        """
        Process an MDPI URL to find alternative sources.

        Args:
            url: MDPI URL

        Returns:
            Dictionary with alternative source information or None
        """
        if not self._is_mdpi_url(url):
            return None

        # Extract DOI and journal info from URL
        url_info = self._extract_info_from_url(url)
        if not url_info:
            logger.warning(f"Could not extract info from MDPI URL: {url}")
            return None

        logger.info(f"Extracted MDPI info: {url_info}")

        # Try to get info via DOI
        if url_info.get("doi"):
            doi_info = self._search_via_doi(url_info["doi"])
            if doi_info:
                doi_info["original_url"] = url
                doi_info["guessed"] = True
                return doi_info

        # Search for alternatives via Google Scholar
        if url_info.get("search_terms"):
            alternative_info = self._search_for_alternatives(
                url_info["search_terms"]
            )
            if alternative_info:
                alternative_info["original_url"] = url
                alternative_info["guessed"] = True
                return alternative_info

        return None

    def _is_mdpi_url(self, url: str) -> bool:
        """Check if URL is from MDPI."""
        return "mdpi.com" in url.lower()

    def _extract_info_from_url(self, url: str) -> dict | None:
        """
        Extract paper information from MDPI URL.

        MDPI URLs typically have format:
        https://www.mdpi.com/ISSN/volume/issue/article_number
        Example: https://www.mdpi.com/1996-1073/17/2/436
        """
        try:
            # Parse URL to get path
            parsed = urlparse(url)
            path = parsed.path.strip("/")

            # Extract ISSN, volume, issue, article number
            # Pattern: ISSN/volume/issue/article_number
            parts = path.split("/")
            if len(parts) >= 4:
                issn = parts[0]
                volume = parts[1]
                issue = parts[2]
                article_num = parts[3]

                # Construct DOI (MDPI DOIs follow pattern: 10.3390/journalabbrev{volume}{issue:0>2}{article_num:0>4})
                # This is approximate - we'll try different formats

                # Get journal info from ISSN
                journal_info = self._get_journal_from_issn(issn)

                info = {
                    "issn": issn,
                    "volume": volume,
                    "issue": issue,
                    "article_number": article_num,
                    "journal": journal_info.get(
                        "name", f"MDPI Journal ({issn})"
                    ),
                    "journal_abbrev": journal_info.get("abbrev", "mdpi"),
                }

                # Try to construct DOI
                if journal_info.get("abbrev"):
                    # MDPI DOI format: 10.3390/abbreviation{volume}{issue:0>2}{article_num:0>4}
                    try:
                        doi_suffix = f"{journal_info['abbrev']}{volume}{int(issue):02d}{int(article_num):04d}"
                        info["doi"] = f"10.3390/{doi_suffix}"
                    except ValueError:
                        # Fallback DOI format
                        info["doi"] = (
                            f"10.3390/{journal_info['abbrev']}{volume}{issue}{article_num}"
                        )

                # Create search terms
                info["search_terms"] = (
                    f"{info['journal']} volume {volume} issue {issue}"
                )

                return info

            return None

        except Exception as e:
            logger.debug(f"Error extracting info from MDPI URL: {e}")
            return None

    def _get_journal_from_issn(self, issn: str) -> dict:
        """Get journal information from ISSN."""
        # Common MDPI journals and their abbreviations
        mdpi_journals = {
            "1996-1073": {"name": "Energies", "abbrev": "en"},
            "1424-8220": {"name": "Sensors", "abbrev": "sensors"},
            "2076-3417": {"name": "Applied Sciences", "abbrev": "app"},
            "2073-4395": {"name": "Water", "abbrev": "w"},
            "2072-4292": {"name": "Remote Sensing", "abbrev": "rs"},
            "2071-1050": {"name": "Sustainability", "abbrev": "su"},
            "1660-4601": {
                "name": "International Journal of Environmental Research and Public Health",
                "abbrev": "ijerph",
            },
            "2079-9292": {"name": "Electronics", "abbrev": "electronics"},
            "2073-8994": {"name": "Symmetry", "abbrev": "sym"},
            "2227-9032": {"name": "Mathematics", "abbrev": "math"},
            "2076-2615": {"name": "Animals", "abbrev": "ani"},
            "2304-8158": {"name": "Foods", "abbrev": "foods"},
            "2072-6643": {"name": "Nutrients", "abbrev": "nu"},
            "1422-0067": {
                "name": "International Journal of Molecular Sciences",
                "abbrev": "ijms",
            },
            "2073-4409": {"name": "Pharmaceuticals", "abbrev": "ph"},
            "2075-163X": {"name": "Antioxidants", "abbrev": "antiox"},
        }

        return mdpi_journals.get(
            issn,
            {"name": f"MDPI Journal ({issn})", "abbrev": issn.replace("-", "")},
        )

    def _search_via_doi(self, doi: str) -> dict | None:
        """
        Search for paper information via DOI.

        Args:
            doi: DOI string

        Returns:
            Dictionary with paper information or None
        """
        try:
            # Be respectful with delays
            time.sleep(self.delay)

            # Try DOI content negotiation for BibTeX
            doi_url = f"https://doi.org/{doi}"
            headers = self.headers.copy()
            headers["Accept"] = "application/x-bibtex; charset=utf-8"

            logger.debug(f"Trying DOI lookup: {doi_url}")

            response = self.session.get(doi_url, headers=headers, timeout=10)
            if response.status_code == 200 and response.content:
                bibtex_text = response.content.decode("utf-8")

                # Parse basic info from BibTeX
                info = self._parse_bibtex_for_info(bibtex_text)
                if info:
                    info["doi"] = doi
                    info["doi_url"] = doi_url
                    info["raw_bibtex"] = bibtex_text
                    logger.info(f"Successfully retrieved info via DOI: {doi}")
                    return info

        except Exception as e:
            logger.debug(f"DOI lookup failed for {doi}: {e}")

        return None

    def _parse_bibtex_for_info(self, bibtex_text: str) -> dict | None:
        """Parse BibTeX text to extract basic information using AST parser."""
        try:
            parser = BibtexParser()
            doc = parser.parse(bibtex_text)

            if not doc.nodes:
                logger.debug("No BibTeX entries found in text")
                return None

            # Get the first entry
            entry = doc.nodes[0]
            if entry.type != "entry":
                logger.debug("First node is not a BibTeX entry")
                return None

            fields = entry.metadata.get("fields", {})
            info = {}

            # Extract standard fields
            if "title" in fields:
                info["title"] = fields["title"].strip()

            if "author" in fields:
                authors_str = fields["author"].strip()
                # Split authors by "and" - AST parser gives us clean field values
                authors = [
                    author.strip()
                    for author in authors_str.split(" and ")
                    if author.strip()
                ]
                info["authors"] = authors

            if "year" in fields:
                info["year"] = fields["year"].strip()

            if "journal" in fields:
                info["journal"] = fields["journal"].strip()

            # Also extract other useful fields that might be present
            for field_name in ["volume", "issue", "pages", "publisher", "doi"]:
                if field_name in fields:
                    info[field_name] = fields[field_name].strip()

            return info if info else None

        except Exception as e:
            logger.debug(f"Error parsing BibTeX with AST: {e}")
            # Fallback to regex parsing for malformed BibTeX
            return self._parse_bibtex_for_info_fallback(bibtex_text)

    def _parse_bibtex_for_info_fallback(self, bibtex_text: str) -> dict | None:
        """Fallback string-based BibTeX parsing for malformed entries."""
        try:
            info = {}
            text_lower = bibtex_text.lower()

            # Helper function to extract field value
            def extract_field(field_name: str) -> str | None:
                # Look for field_name = { ... }
                field_lower = field_name.lower()
                field_lower + r"\s*="

                # Find field start
                idx = 0
                while idx < len(text_lower):
                    pos = text_lower.find(field_lower, idx)
                    if pos == -1:
                        break

                    # Skip whitespace after field name
                    i = pos + len(field_lower)
                    while i < len(text_lower) and text_lower[i].isspace():
                        i += 1

                    # Check for = sign
                    if i < len(text_lower) and text_lower[i] == "=":
                        # Skip whitespace after =
                        i += 1
                        while i < len(text_lower) and text_lower[i].isspace():
                            i += 1

                        # Check for opening brace
                        if i < len(text_lower) and text_lower[i] == "{":
                            # Find matching closing brace
                            brace_count = 1
                            start = i + 1
                            i += 1
                            while i < len(text_lower) and brace_count > 0:
                                if text_lower[i] == "{":
                                    brace_count += 1
                                elif text_lower[i] == "}":
                                    brace_count -= 1
                                i += 1

                            if brace_count == 0:
                                # Extract value from original text (preserve case)
                                return bibtex_text[start : i - 1].strip()

                    idx = pos + 1

                return None

            # Extract title
            title = extract_field("title")
            if title:
                info["title"] = title

            # Extract authors
            authors_str = extract_field("author")
            if authors_str:
                # Split by "and" with whitespace
                authors = []
                parts = authors_str.split(" and ")
                for part in parts:
                    author = part.strip()
                    if author:
                        authors.append(author)
                if authors:
                    info["authors"] = authors

            # Extract year
            year = extract_field("year")
            if year:
                info["year"] = year

            # Extract journal
            journal = extract_field("journal")
            if journal:
                info["journal"] = journal

            logger.debug("Used fallback string parsing for malformed BibTeX")
            return info if info else None

        except Exception as e:
            logger.debug(f"Error in fallback BibTeX parsing: {e}")
            return None

    def _search_for_alternatives(self, search_terms: str) -> dict | None:
        """
        Search for alternative sources using the search terms.

        Args:
            search_terms: Terms to search for

        Returns:
            Dictionary with alternative source info or None
        """
        # Try Google Scholar search
        scholar_result = self._search_google_scholar(search_terms)
        if scholar_result:
            return scholar_result

        return None

    def _search_google_scholar(self, search_terms: str) -> dict | None:
        """
        Search Google Scholar for the paper and extract information.

        Args:
            search_terms: Terms to search for

        Returns:
            Dictionary with paper information or None
        """
        try:
            # Be respectful with delays
            time.sleep(self.delay)

            # Construct Google Scholar search URL
            query = quote_plus(search_terms)
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


def process_mdpi_link(url: str) -> dict | None:
    """
    Convenience function to process an MDPI link.

    Args:
        url: MDPI URL

    Returns:
        Dictionary with alternative source information or None
    """
    workaround = MDPIWorkaround()
    return workaround.process_mdpi_url(url)


def extract_doi_from_mdpi_url(url: str) -> str | None:
    """
    Extract likely DOI from MDPI URL.

    Args:
        url: MDPI URL

    Returns:
        Extracted DOI or None
    """
    workaround = MDPIWorkaround()
    info = workaround._extract_info_from_url(url)
    return info.get("doi") if info else None
