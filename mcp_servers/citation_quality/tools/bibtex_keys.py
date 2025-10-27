"""MCP tool for validating BibTeX keys."""

import logging
import os
from typing import Any

from src.converters.md_to_latex.zotero_integration import ZoteroClient

logger = logging.getLogger(__name__)


async def validate_bibtex_keys(
    citations: list[dict[str, str]], collection: str | None = None
) -> dict[str, Any]:
    """Check if BibTeX keys match Better BibTeX format from Zotero.

    Args:
        citations: List of citations with 'url' and 'current_key' fields
        collection: Zotero collection name (defaults to ZOTERO_COLLECTION env var)

    Returns:
        Dictionary with mismatches:
        - url: Citation URL
        - current_key: Current BibTeX key being used
        - correct_key: Correct Better BibTeX key from Zotero
        - source: Where the correct key comes from
    """
    try:
        # Use collection from env if not provided
        if collection is None:
            collection = os.getenv("ZOTERO_COLLECTION", "dpp-fashion")

        # Get Zotero credentials from environment
        api_key = os.getenv("ZOTERO_API_KEY")
        library_id = os.getenv("ZOTERO_LIBRARY_ID")
        library_type = os.getenv("ZOTERO_LIBRARY_TYPE", "user")

        if not api_key or not library_id:
            return {
                "mismatches": [],
                "error": "ZOTERO_API_KEY and ZOTERO_LIBRARY_ID must be set in environment",
            }

        # Initialize Zotero client
        client = ZoteroClient(
            api_key=api_key, library_id=library_id, library_type=library_type
        )

        # Get all items from the collection
        items = client.get_collection_items(collection)

        # Build URL to citation-key mapping
        url_to_key = {}
        for item in items:
            item_url = item.get("URL", "").lower().strip()
            citation_key = item.get("citation-key") or item.get("id")
            if item_url and citation_key:
                url_to_key[item_url] = citation_key

            # Also map DOI if available
            item_doi = item.get("DOI", "").strip()
            if item_doi and citation_key:
                doi_url = f"https://doi.org/{item_doi}".lower()
                url_to_key[doi_url] = citation_key

        # Check each citation for mismatches
        mismatches = []
        for citation in citations:
            url = citation.get("url", "").lower().strip()
            current_key = citation.get("current_key", "")

            if url in url_to_key:
                correct_key = url_to_key[url]
                if current_key != correct_key:
                    mismatches.append(
                        {
                            "url": citation.get("url"),  # Original case
                            "current_key": current_key,
                            "correct_key": correct_key,
                            "source": "Zotero Better BibTeX",
                        }
                    )

        return {
            "mismatches": mismatches,
            "total_checked": len(citations),
            "mismatches_found": len(mismatches),
        }

    except Exception as e:
        logger.exception("Error validating BibTeX keys")
        return {
            "mismatches": [],
            "error": f"Error validating BibTeX keys: {e!s}",
        }
