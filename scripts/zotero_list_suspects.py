#!/usr/bin/env python3
"""
List suspect/garbage entries in Zotero collection.

Identifies entries that were likely added by broken script:
- Title starts with "Added from URL"
- Title is truncated
- Added recently (last 3 days)
"""

import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from pyzotero import zotero

# Load environment
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def is_suspect(item):
    """Check if item looks like garbage entry."""
    data = item.get("data", {})
    title = data.get("title", "") or ""

    # Pattern 1: Explicit garbage marker
    if title.startswith("Added from URL"):
        return True, "starts with 'Added from URL'"

    # Pattern 2: Very short truncated titles with URL-like content
    if len(title) < 20 and ("http" in title.lower() or "..." in title):
        return True, "truncated URL-like title"

    # Pattern 3: No authors (but allow organizational items)
    creators = data.get("creators", [])
    if not creators and data.get("itemType") in ["webpage", "document"]:
        # Check if recently added
        date_added = item.get("meta", {}).get("dateAdded")
        if date_added:
            try:
                dt = datetime.fromisoformat(date_added.replace("Z", "+00:00"))
                if datetime.utcnow().replace(tzinfo=dt.tzinfo) - dt < timedelta(
                    days=3
                ):
                    return True, "no authors, recently added"
            except (ValueError, AttributeError):
                pass

    return False, None


def main():
    # Get credentials
    api_key = os.getenv("ZOTERO_API_KEY")
    library_id = os.getenv("ZOTERO_LIBRARY_ID")
    collection_name = "dpp-fashion"

    if not api_key or not library_id:
        logger.error("Missing ZOTERO_API_KEY or ZOTERO_LIBRARY_ID in .env")
        sys.exit(1)

    # Connect
    zot = zotero.Zotero(library_id, "user", api_key)

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

    logger.info(f"Scanning collection '{collection_name}'...")

    # Get all items
    items = zot.collection_items(collection_key)
    logger.info(f"Total items in collection: {len(items)}")

    # Find suspects
    suspects = []
    for item in items:
        is_bad, reason = is_suspect(item)
        if is_bad:
            data = item.get("data", {})
            suspects.append(
                {
                    "key": data.get("key"),
                    "version": data.get("version"),
                    "title": data.get("title", ""),
                    "url": data.get("url", ""),
                    "itemType": data.get("itemType", ""),
                    "dateAdded": item.get("meta", {}).get("dateAdded", ""),
                    "reason": reason,
                }
            )

    # Report
    logger.info(f"\n{'=' * 80}")
    logger.info(f"SUSPECT ENTRIES FOUND: {len(suspects)}")
    logger.info(f"{'=' * 80}\n")

    if suspects:
        for i, s in enumerate(suspects, 1):
            logger.info(f"[{i}] {s['title'][:70]}")
            logger.info(f"    Key: {s['key']}")
            logger.info(f"    Type: {s['itemType']}")
            logger.info(f"    Reason: {s['reason']}")
            logger.info(f"    Added: {s['dateAdded']}")
            if s["url"]:
                logger.info(f"    URL: {s['url'][:70]}")
            logger.info("")

        # Save to file
        output_file = Path("zotero_suspects.json")
        with open(output_file, "w") as f:
            json.dump(suspects, f, indent=2)
        logger.info(f"Suspect list saved to: {output_file}")
        logger.info("\nTo delete these, run:")
        logger.info(
            f"  python3 scripts/zotero_delete_items.py --file {output_file} --dry-run"
        )
    else:
        logger.info("No suspect entries found.")


if __name__ == "__main__":
    main()
