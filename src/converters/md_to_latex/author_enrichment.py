"""Automatic author enrichment for BibTeX entries with truncated author lists.

This module detects and fixes truncated author lists (e.g., "Smith and others")
by fetching complete metadata from CrossRef and arXiv APIs.
"""

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class AuthorEnricher:
    """Enriches BibTeX entries with complete author lists from APIs."""

    CROSSREF_API = "https://api.crossref.org/works/{}"
    ARXIV_API = "https://export.arxiv.org/api/query?id_list={}"
    HEADERS = {
        "User-Agent": "deep-biblio-tools/author-enrichment (mailto:research@example.com)"
    }
    TIMEOUT = 10

    def __init__(self):
        """Initialize author enricher."""
        self.cache = {}  # Cache author lookups to avoid repeated API calls
        self.stats = {
            "total_entries": 0,
            "truncated_detected": 0,
            "enriched_success": 0,
            "enriched_failed": 0,
        }

    def enrich_bibtex_entries(
        self, entries_dict: dict[str, dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        """Enrich all BibTeX entries with complete author lists.

        Args:
            entries_dict: Dict mapping citation keys to BibTeX entry dicts

        Returns:
            Dict with enriched entries (same structure as input)
        """
        logger.info(
            f"Starting author enrichment for {len(entries_dict)} BibTeX entries"
        )

        enriched_dict = {}
        self.stats["total_entries"] = len(entries_dict)

        for cite_key, entry in entries_dict.items():
            # Check if entry has truncated authors
            author_field = entry.get("author", "")

            if self._has_truncated_authors(author_field):
                self.stats["truncated_detected"] += 1
                logger.debug(
                    f"Detected truncated authors in {cite_key}: {author_field[:50]}..."
                )

                # Try to enrich from CrossRef/arXiv
                enriched_entry = self._enrich_entry(entry)

                if enriched_entry:
                    self.stats["enriched_success"] += 1
                    enriched_dict[cite_key] = enriched_entry
                    logger.info(
                        f"✓ Enriched {cite_key}: {len(entry.get('author', ''))} → {len(enriched_entry.get('author', ''))} chars"
                    )
                else:
                    self.stats["enriched_failed"] += 1
                    enriched_dict[cite_key] = entry
                    logger.warning(
                        f"✗ Failed to enrich {cite_key} - keeping original"
                    )
            else:
                # No truncation detected - keep as-is
                enriched_dict[cite_key] = entry

        self._log_stats()
        return enriched_dict

    def _has_truncated_authors(self, author_field: str) -> bool:
        """Check if author field has truncated list indicators.

        Args:
            author_field: BibTeX author field

        Returns:
            True if truncated, False otherwise
        """
        if not author_field or author_field.strip() == "":
            return False

        # Check for common truncation patterns
        author_lower = author_field.lower()
        return "and others" in author_lower or "et al" in author_lower

    def _enrich_entry(self, entry: dict[str, Any]) -> dict[str, Any] | None:
        """Enrich a single entry with complete author list.

        Args:
            entry: BibTeX entry dict

        Returns:
            Enriched entry dict, or None if enrichment failed
        """
        # Extract DOI or arXiv ID
        doi = entry.get("doi", "").strip()
        arxiv_id = self._extract_arxiv_id(entry)

        # Try CrossRef first (if DOI available)
        if doi:
            complete_authors = self._fetch_authors_from_crossref(doi)
            if complete_authors:
                enriched_entry = entry.copy()
                enriched_entry["author"] = complete_authors
                logger.debug(
                    f"Enriched from CrossRef: {complete_authors[:100]}..."
                )
                return enriched_entry

        # Try arXiv if CrossRef failed (if arXiv ID available)
        if arxiv_id:
            complete_authors = self._fetch_authors_from_arxiv(arxiv_id)
            if complete_authors:
                enriched_entry = entry.copy()
                enriched_entry["author"] = complete_authors
                logger.debug(
                    f"Enriched from arXiv: {complete_authors[:100]}..."
                )
                return enriched_entry

        # No DOI or arXiv ID, or both APIs failed
        return None

    def _fetch_authors_from_crossref(self, doi: str) -> str | None:
        """Fetch complete author list from CrossRef API.

        Args:
            doi: DOI identifier

        Returns:
            BibTeX-formatted author string, or None if failed
        """
        # Check cache first
        if doi in self.cache:
            logger.debug(f"Using cached authors for DOI: {doi}")
            return self.cache[doi]

        url = self.CROSSREF_API.format(doi)

        try:
            response = requests.get(
                url, headers=self.HEADERS, timeout=self.TIMEOUT
            )

            if response.status_code != 200:
                logger.debug(
                    f"CrossRef returned status {response.status_code} for DOI: {doi}"
                )
                return None

            data = response.json()
            metadata = data.get("message", {})

            # Extract authors from CrossRef metadata
            authors = metadata.get("author", [])
            if not authors:
                logger.debug(
                    f"No authors found in CrossRef metadata for DOI: {doi}"
                )
                return None

            # Convert to BibTeX format: "Last1, First1 and Last2, First2 and ..."
            author_strings = []
            for author in authors:
                family = author.get("family", "")
                given = author.get("given", "")

                if family:
                    if given:
                        author_strings.append(f"{family}, {given}")
                    else:
                        author_strings.append(family)

            if not author_strings:
                logger.debug(
                    f"Failed to parse author names from CrossRef for DOI: {doi}"
                )
                return None

            bibtex_authors = " and ".join(author_strings)

            # Cache the result
            self.cache[doi] = bibtex_authors

            return bibtex_authors

        except requests.RequestException as e:
            logger.debug(f"CrossRef API error for DOI {doi}: {e}")
            return None
        except Exception as e:
            logger.warning(
                f"Unexpected error fetching from CrossRef for DOI {doi}: {e}"
            )
            return None

    def _fetch_authors_from_arxiv(self, arxiv_id: str) -> str | None:
        """Fetch complete author list from arXiv API.

        Args:
            arxiv_id: arXiv identifier (e.g., "2401.13178")

        Returns:
            BibTeX-formatted author string, or None if failed
        """
        # Check cache first
        cache_key = f"arxiv:{arxiv_id}"
        if cache_key in self.cache:
            logger.debug(f"Using cached authors for arXiv: {arxiv_id}")
            return self.cache[cache_key]

        url = self.ARXIV_API.format(arxiv_id)

        try:
            response = requests.get(
                url, headers=self.HEADERS, timeout=self.TIMEOUT
            )

            if response.status_code != 200:
                logger.debug(
                    f"arXiv returned status {response.status_code} for ID: {arxiv_id}"
                )
                return None

            # arXiv returns Atom XML
            content = response.text

            # Extract author names using string methods (no regex!)
            author_strings = self._parse_arxiv_authors(content)

            if not author_strings:
                logger.debug(
                    f"Failed to parse authors from arXiv for ID: {arxiv_id}"
                )
                return None

            bibtex_authors = " and ".join(author_strings)

            # Cache the result
            self.cache[cache_key] = bibtex_authors

            return bibtex_authors

        except requests.RequestException as e:
            logger.debug(f"arXiv API error for ID {arxiv_id}: {e}")
            return None
        except Exception as e:
            logger.warning(
                f"Unexpected error fetching from arXiv for ID {arxiv_id}: {e}"
            )
            return None

    def _parse_arxiv_authors(self, xml_content: str) -> list[str]:
        """Parse author names from arXiv Atom XML response.

        Uses string methods only (no regex as per project policy).

        Args:
            xml_content: arXiv API XML response

        Returns:
            List of author name strings in "Last, First" format
        """
        authors = []

        # Find all <author> tags
        pos = 0
        while True:
            # Find next <author> tag
            start_tag = "<author>"
            end_tag = "</author>"

            author_start = xml_content.find(start_tag, pos)
            if author_start == -1:
                break

            author_end = xml_content.find(end_tag, author_start)
            if author_end == -1:
                break

            # Extract author block
            author_block = xml_content[
                author_start + len(start_tag) : author_end
            ]

            # Find <name> tag within author block
            name_start = author_block.find("<name>")
            name_end = author_block.find("</name>")

            if name_start != -1 and name_end != -1:
                name = author_block[name_start + 6 : name_end].strip()

                # Convert "First Last" to "Last, First" format
                # Split by last space (assumes last word is family name)
                name_parts = name.split()
                if len(name_parts) >= 2:
                    given_names = " ".join(name_parts[:-1])
                    family_name = name_parts[-1]
                    formatted_name = f"{family_name}, {given_names}"
                else:
                    formatted_name = name

                authors.append(formatted_name)

            # Move position past this author tag
            pos = author_end + len(end_tag)

        return authors

    def _extract_arxiv_id(self, entry: dict[str, Any]) -> str | None:
        """Extract arXiv ID from BibTeX entry.

        Checks both 'eprint' field and DOI field for arXiv identifiers.

        Args:
            entry: BibTeX entry dict

        Returns:
            arXiv ID (e.g., "2401.13178"), or None if not found
        """
        # Check eprint field (standard BibTeX field for arXiv)
        eprint = entry.get("eprint", "").strip()
        if eprint and "arxiv" not in eprint.lower():
            # Assume it's an arXiv ID if it looks like one
            return eprint

        # Check DOI field for arXiv DOI format
        doi = entry.get("doi", "").strip()
        if "arxiv" in doi.lower():
            # Extract ID from DOI like "10.48550/arXiv.2401.13178"
            if "arxiv." in doi.lower():
                parts = doi.split("arXiv.")
                if len(parts) >= 2:
                    return parts[1].strip()

        # Check URL field
        url = entry.get("url", "").strip()
        if "arxiv.org" in url.lower():
            # Extract from URL like "https://arxiv.org/abs/2401.13178"
            if "/abs/" in url:
                parts = url.split("/abs/")
                if len(parts) >= 2:
                    arxiv_id = parts[1].strip().split("/")[0].split("?")[0]
                    return arxiv_id
            elif "/pdf/" in url:
                parts = url.split("/pdf/")
                if len(parts) >= 2:
                    arxiv_id = parts[1].strip().split(".pdf")[0].split("?")[0]
                    return arxiv_id

        return None

    def _log_stats(self):
        """Log enrichment statistics."""
        stats = self.stats
        logger.info("=" * 60)
        logger.info("Author Enrichment Statistics")
        logger.info("=" * 60)
        logger.info(f"Total entries processed: {stats['total_entries']}")
        logger.info(
            f"Truncated authors detected: {stats['truncated_detected']}"
        )
        logger.info(f"Successfully enriched: {stats['enriched_success']}")
        logger.info(f"Failed to enrich: {stats['enriched_failed']}")

        if stats["truncated_detected"] > 0:
            success_rate = (
                stats["enriched_success"] / stats["truncated_detected"]
            ) * 100
            logger.info(f"Success rate: {success_rate:.1f}%")

        logger.info("=" * 60)

    def get_stats(self) -> dict[str, int]:
        """Get enrichment statistics.

        Returns:
            Dict with statistics
        """
        return self.stats.copy()
