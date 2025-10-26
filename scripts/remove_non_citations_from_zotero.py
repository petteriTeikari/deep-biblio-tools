#!/usr/bin/env python3
"""
Remove items that are not real citations (hyperlinks, invalid arXiv IDs).
"""

import logging
import os
import sys

from pyzotero import zotero

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# URLs that should NOT be citations (they're just hyperlinks)
NON_CITATION_URLS = [
    "https://www.eon.xyz/",
    "https://github.com/rednote-hilab/dots.ocr",
    "https://docs.google.com/presentation/d/1acexbPG2b39_DYkr7TJ0EyKuysmEBorGmWkvThatgPw",
    "https://arxiv.org/abs/2025.mcp.taxonomy",  # Invalid arXiv ID
    "https://arxiv.org/abs/2025.mcp.privilege",  # Invalid arXiv ID
    "https://arxiv.org/abs/2025.mpma",  # Invalid arXiv ID
]


def remove_non_citations(
    collection_name: str,
    library_id: str | None = None,
    api_key: str | None = None,
    library_type: str = "user",
) -> None:
    """Remove non-citation items from Zotero."""
    api_key = api_key or os.getenv("ZOTERO_API_KEY")
    library_id = library_id or os.getenv("ZOTERO_LIBRARY_ID")

    if not api_key or not library_id:
        logger.error("Missing Zotero credentials")
        sys.exit(1)

    zot = zotero.Zotero(library_id, library_type, api_key)

    # Find collection
    collections = zot.collections()
    collection_key = None
    for coll in collections:
        if coll["data"]["name"] == collection_name:
            collection_key = coll["key"]
            break

    if not collection_key:
        logger.error(f"Collection '{collection_name}' not found")
        sys.exit(1)

    # Get all items in collection
    items = zot.collection_items(collection_key)

    removed = 0
    for item in items:
        url = item["data"].get("url", "")
        title = item["data"].get("title", "")

        # Check if this URL should be removed
        should_remove = False
        for non_citation_url in NON_CITATION_URLS:
            if url.startswith(non_citation_url):
                should_remove = True
                break

        if should_remove:
            logger.info(f"Removing: {title[:60]}")
            logger.info(f"  URL: {url}")
            zot.delete_item(item)
            removed += 1

    logger.info(f"\nRemoved {removed} non-citation items")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--collection", default="dpp-fashion")
    args = parser.parse_args()

    remove_non_citations(collection_name=args.collection)
