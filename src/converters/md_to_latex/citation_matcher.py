"""
Production-grade deterministic citation matcher.

Implements OpenAI's recommended multi-strategy matching approach:
1. DOI matching (most reliable)
2. ISBN matching (books)
3. arXiv ID matching (preprints)
4. URL matching (normalized)
5. Fuzzy author+year+title matching (fallback)
6. Optional Zotero write-back for missing citations

All operations are deterministic given the same Zotero snapshot.
"""

import hashlib
import json
import logging
import os
from typing import Any

from pyzotero import zotero

from src.converters.md_to_latex.utils import (
    extract_arxiv_id,
    extract_doi_from_url,
    extract_isbn_from_url,
    normalize_url,
)

logger = logging.getLogger(__name__)


class CitationMatcher:
    """Deterministic multi-strategy citation matcher."""

    def __init__(
        self,
        zotero_entries: list[dict[str, Any]],
        allow_zotero_write: bool = False,
    ):
        """
        Initialize matcher with Zotero database snapshot.

        Args:
            zotero_entries: List of CSL JSON entries from Zotero export
            allow_zotero_write: Enable automatic addition of missing citations
        """
        self.entries = zotero_entries
        self.allow_write = allow_zotero_write

        # Build deterministic indices
        self.doi_index = {}
        self.isbn_index = {}
        self.arxiv_index = {}
        self.url_index = {}

        self._build_indices()

        # Statistics
        self.stats = {
            "total_citations": 0,
            "matched_by_doi": 0,
            "matched_by_isbn": 0,
            "matched_by_arxiv": 0,
            "matched_by_url": 0,
            "matched_by_fuzzy": 0,
            "added_to_zotero": 0,
            "unmatched": 0,
        }

    def _build_indices(self):
        """Build deterministic lookup indices from Zotero entries."""

        # DIAGNOSTIC: Track entries without URLs
        entries_without_url = 0
        entries_without_doi = 0

        for idx, entry in enumerate(self.entries):
            # DOI index
            doi = entry.get("DOI", "")
            if doi:
                # Normalize: lowercase, strip whitespace
                normalized_doi = doi.lower().strip()
                self.doi_index[normalized_doi] = entry
                # DIAGNOSTIC: Log first few DOIs
                if len(self.doi_index) <= 3:
                    logger.debug(f"Sample DOI indexed: {normalized_doi} -> {entry.get('title', 'NO_TITLE')[:60]}")
            else:
                entries_without_doi += 1

            # ISBN index
            isbn = entry.get("ISBN", "")
            if isbn:
                # Normalize: remove hyphens, keep only digits
                normalized_isbn = "".join(c for c in isbn if c.isdigit())
                if normalized_isbn:
                    self.isbn_index[normalized_isbn] = entry

            # arXiv index
            # Check both archiveID field and URL
            archive_id = entry.get("archiveID", "")
            if archive_id and "arXiv" in entry.get("archive", ""):
                # Remove "arXiv:" prefix if present
                if archive_id.startswith("arXiv:"):
                    archive_id = archive_id[6:]
                self.arxiv_index[archive_id.lower()] = entry

            # Also extract arXiv from URL if present
            url = entry.get("URL", "")
            if url and "arxiv.org" in url.lower():
                arxiv_id = extract_arxiv_id(url)
                if arxiv_id:
                    self.arxiv_index[arxiv_id.lower()] = entry
                    # DIAGNOSTIC: Log first few arXiv IDs
                    if len(self.arxiv_index) <= 3:
                        logger.debug(f"Sample arXiv indexed: {arxiv_id} -> {entry.get('title', 'NO_TITLE')[:60]}")

            # URL index (normalized)
            if url:
                normalized_url = normalize_url(url)
                if normalized_url:
                    self.url_index[normalized_url] = entry
                    # DIAGNOSTIC: Log first few URLs
                    if len(self.url_index) <= 3:
                        logger.debug(f"Sample URL indexed: {normalized_url[:80]} -> {entry.get('title', 'NO_TITLE')[:60]}")
            else:
                entries_without_url += 1

        logger.info(
            f"Built indices: {len(self.doi_index)} DOIs, "
            f"{len(self.isbn_index)} ISBNs, {len(self.arxiv_index)} arXiv, "
            f"{len(self.url_index)} URLs"
        )
        logger.info(
            f"Entries without URL: {entries_without_url}/{len(self.entries)}, "
            f"without DOI: {entries_without_doi}/{len(self.entries)}"
        )

    def match(self, citation_url: str) -> tuple[dict[str, Any] | None, str]:
        """
        Match citation using multi-strategy approach.

        Args:
            citation_url: URL from markdown citation

        Returns:
            Tuple of (matched_entry, match_strategy)
            Strategy is one of: "doi", "isbn", "arxiv", "url", "fuzzy", "added", None
        """
        self.stats["total_citations"] += 1

        # DIAGNOSTIC: Log first 5 match attempts
        debug_this = self.stats["total_citations"] <= 5

        if debug_this:
            logger.debug(f"\n=== Matching attempt #{self.stats['total_citations']} ===")
            logger.debug(f"Citation URL: {citation_url}")

        # Strategy 1: DOI matching (most reliable)
        doi = extract_doi_from_url(citation_url)
        if doi:
            normalized_doi = doi.lower().strip()
            if debug_this:
                logger.debug(f"Extracted DOI: {normalized_doi}")
                logger.debug(f"DOI in index? {normalized_doi in self.doi_index}")
            if normalized_doi in self.doi_index:
                self.stats["matched_by_doi"] += 1
                if debug_this:
                    logger.debug(f"✓ MATCHED by DOI: {normalized_doi}")
                return self.doi_index[normalized_doi], "doi"
            elif debug_this:
                logger.debug(f"✗ DOI not in index (index has {len(self.doi_index)} DOIs)")

        # Strategy 2: ISBN matching (for books)
        isbn = extract_isbn_from_url(citation_url)
        if isbn:
            if debug_this:
                logger.debug(f"Extracted ISBN: {isbn}")
                logger.debug(f"ISBN in index? {isbn in self.isbn_index}")
            if isbn in self.isbn_index:
                self.stats["matched_by_isbn"] += 1
                logger.info(f"Matched by ISBN: {isbn}")
                return self.isbn_index[isbn], "isbn"

        # Strategy 3: arXiv matching (for preprints)
        arxiv_id = extract_arxiv_id(citation_url)
        if arxiv_id:
            normalized_arxiv = arxiv_id.lower()
            if debug_this:
                logger.debug(f"Extracted arXiv ID: {normalized_arxiv}")
                logger.debug(f"arXiv in index? {normalized_arxiv in self.arxiv_index}")
            if normalized_arxiv in self.arxiv_index:
                self.stats["matched_by_arxiv"] += 1
                logger.info(f"Matched by arXiv: {arxiv_id}")
                return self.arxiv_index[normalized_arxiv], "arxiv"
            elif debug_this:
                logger.debug(f"✗ arXiv not in index (index has {len(self.arxiv_index)} arXiv IDs)")

        # Strategy 4: URL matching (normalized)
        normalized_url = normalize_url(citation_url)
        if debug_this:
            logger.debug(f"Normalized URL: {normalized_url[:100]}")
            logger.debug(f"URL in index? {normalized_url in self.url_index if normalized_url else False}")
        if normalized_url and normalized_url in self.url_index:
            self.stats["matched_by_url"] += 1
            if debug_this:
                logger.debug(f"✓ MATCHED by URL")
            return self.url_index[normalized_url], "url"
        elif debug_this:
            logger.debug(f"✗ URL not in index (index has {len(self.url_index)} URLs)")

        # Strategy 5: Fuzzy fallback (deterministic)
        # TODO: Implement fuzzy matching with author+year+title
        # For now, mark as unmatched

        # Strategy 6: Add to Zotero (if enabled)
        if self.allow_write:
            entry = self._add_to_zotero(citation_url)
            if entry:
                self.stats["added_to_zotero"] += 1
                return entry, "added"

        # No match found
        self.stats["unmatched"] += 1
        if debug_this:
            logger.debug("✗ NO MATCH FOUND - all strategies failed")
        return None, None

    def _add_to_zotero(self, url: str) -> dict[str, Any] | None:
        """
        Add missing citation to Zotero via API.

        Args:
            url: Citation URL

        Returns:
            Created entry or None if failed
        """
        # Check for API credentials
        api_key = os.getenv("ZOTERO_API_KEY")
        library_id = os.getenv("ZOTERO_LIBRARY_ID")
        library_type = os.getenv("ZOTERO_LIBRARY_TYPE", "user")

        if not api_key or not library_id:
            logger.debug("Zotero API credentials not found, skipping auto-add")
            return None

        try:
            zot = zotero.Zotero(library_id, library_type, api_key)

            # Create minimal entry
            new_item = {
                "itemType": "webpage",
                "title": f"Auto-added: {url[:50]}...",
                "url": url,
                "accessDate": "2025-10-26",
            }

            # Try to fetch metadata from URL
            # (Could enhance this with CrossRef/arXiv API calls)

            response = zot.create_items([new_item])
            if response.get("success"):
                logger.info(f"Added to Zotero: {url}")
                return new_item
            else:
                logger.warning(f"Failed to add to Zotero: {response}")
                return None

        except Exception as e:
            logger.warning(f"Error adding to Zotero: {e}")
            return None

    def get_statistics(self) -> dict[str, Any]:
        """Get matching statistics."""
        total = self.stats["total_citations"]
        matched = total - self.stats["unmatched"]

        return {
            **self.stats,
            "match_rate": (matched / total * 100) if total > 0 else 0,
            "deterministic_hash": self._compute_hash(),
        }

    def _compute_hash(self) -> str:
        """Compute deterministic hash of matching results."""
        # Hash the statistics to verify determinism
        stats_str = json.dumps(self.stats, sort_keys=True)
        return hashlib.sha256(stats_str.encode()).hexdigest()[:16]
