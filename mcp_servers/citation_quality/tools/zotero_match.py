"""MCP tool for verifying Zotero matches."""

import logging
import os
from typing import Any

from src.converters.md_to_latex.zotero_integration import ZoteroClient

logger = logging.getLogger(__name__)


async def verify_zotero_match(
    url: str, citation_text: str, collection: str | None = None
) -> dict[str, Any]:
    """Check if a citation exists in Zotero and validate metadata.

    Args:
        url: The citation URL
        citation_text: The citation text (e.g., "Cao et al., 2024")
        collection: Zotero collection name (defaults to ZOTERO_COLLECTION env var)

    Returns:
        Dictionary with Zotero match results including:
        - found_in_zotero: Whether the citation exists in Zotero
        - better_bibtex_key: The Better BibTeX key if found
        - metadata: Full metadata from Zotero
        - validation: Validation results (author/year match, encoding issues)
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
                "found_in_zotero": False,
                "better_bibtex_key": None,
                "metadata": {},
                "validation": {
                    "author_match": None,
                    "year_match": None,
                    "encoding_issues": [],
                },
                "error": "ZOTERO_API_KEY and ZOTERO_LIBRARY_ID must be set in environment",
            }

        # Initialize Zotero client
        client = ZoteroClient(
            api_key=api_key, library_id=library_id, library_type=library_type
        )

        # Get all items from the collection
        items = client.get_collection_items(collection)

        # Search for matching URL or DOI
        normalized_url = url.lower().strip()
        found_item = None

        for item in items:
            # Check URL field
            item_url = item.get("URL", "").lower().strip()
            if item_url and item_url == normalized_url:
                found_item = item
                break

            # Check DOI
            item_doi = item.get("DOI", "").lower().strip()
            if item_doi and ("doi.org/" + item_doi) in normalized_url:
                found_item = item
                break

        if not found_item:
            return {
                "found_in_zotero": False,
                "better_bibtex_key": None,
                "metadata": {},
                "validation": {
                    "author_match": None,
                    "year_match": None,
                    "encoding_issues": [],
                },
                "message": f"URL not found in Zotero collection '{collection}'",
            }

        # Extract author and year from citation text for validation
        # Simple extraction: look for year pattern (4 digits)
        year_from_text = None
        for part in citation_text.split():
            if len(part) == 4 and part.isdigit():
                year_from_text = part
                break

        # Get year from Zotero metadata
        year_from_zotero = found_item.get("issued", {}).get(
            "date-parts", [[None]]
        )[0][0]
        year_match = (
            year_from_text == str(year_from_zotero)
            if year_from_text and year_from_zotero
            else None
        )

        # Get Better BibTeX key if available
        better_bibtex_key = found_item.get("citation-key") or found_item.get(
            "id"
        )

        return {
            "found_in_zotero": True,
            "better_bibtex_key": better_bibtex_key,
            "metadata": {
                "title": found_item.get("title"),
                "author": found_item.get("author", []),
                "year": year_from_zotero,
                "doi": found_item.get("DOI"),
                "url": found_item.get("URL"),
            },
            "validation": {
                "author_match": None,  # Would need more complex parsing
                "year_match": year_match,
                "encoding_issues": [],  # Would need character encoding check
            },
        }

    except Exception as e:
        logger.exception(f"Error verifying Zotero match: {url}")
        return {
            "found_in_zotero": False,
            "better_bibtex_key": None,
            "metadata": {},
            "validation": {
                "author_match": None,
                "year_match": None,
                "encoding_issues": [],
            },
            "error": f"Error verifying Zotero match: {e!s}",
        }
