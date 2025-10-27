"""MCP tool for validating BibTeX keys."""

import logging
import os
from typing import Any

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

        # TODO: Import and use CitationManager from src/
        # For now, return a stub response
        return {
            "mismatches": [],
            "message": "BibTeX key validation not yet implemented",
        }

    except Exception as e:
        logger.exception("Error validating BibTeX keys")
        return {
            "mismatches": [],
            "error": f"Error validating BibTeX keys: {e!s}",
        }
