#!/usr/bin/env python3
"""
Delete items from Zotero collection.

SAFETY:
- Requires explicit --confirm flag to actually delete
- Default mode is --dry-run (safe)
- Deletes in chunks of 50 (Zotero API limit)
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pyzotero import zotero

# Load environment
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Delete items from Zotero")
    parser.add_argument(
        "--file",
        type=Path,
        required=True,
        help="JSON file with suspect entries",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview only (default: True)",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually delete (must be explicitly set)",
    )
    args = parser.parse_args()

    # Get credentials
    api_key = os.getenv("ZOTERO_API_KEY")
    library_id = os.getenv("ZOTERO_LIBRARY_ID")

    if not api_key or not library_id:
        logger.error("Missing ZOTERO_API_KEY or ZOTERO_LIBRARY_ID in .env")
        sys.exit(1)

    # Load suspects
    with open(args.file) as f:
        suspects = json.load(f)

    if not suspects:
        logger.info("No items to delete.")
        return

    keys = [s["key"] for s in suspects if s.get("key")]

    logger.info(f"{'=' * 80}")
    logger.info(f"DELETE PREVIEW: {len(keys)} items")
    logger.info(f"{'=' * 80}\n")

    for s in suspects:
        logger.info(f"  - {s.get('title', 'Untitled')[:70]}")
        logger.info(f"    Key: {s['key']}")
        logger.info("")

    if args.dry_run or not args.confirm:
        logger.info(f"{'=' * 80}")
        logger.info("DRY RUN MODE - Nothing will be deleted")
        logger.info(f"{'=' * 80}")
        logger.info("\nTo actually delete, run:")
        logger.info(f"  python3 {sys.argv[0]} --file {args.file} --confirm")
        logger.info(
            "\n⚠️  This will permanently delete these items from Zotero!"
        )
        return

    # Confirm deletion
    logger.info(f"{'=' * 80}")
    logger.info("⚠️  DELETION CONFIRMED")
    logger.info(f"{'=' * 80}")

    # Connect
    zot = zotero.Zotero(library_id, "user", api_key)

    # Delete in chunks
    deleted = 0
    failed = 0

    for i in range(0, len(keys), 50):
        chunk = keys[i : i + 50]
        logger.info(f"Deleting chunk {i // 50 + 1} ({len(chunk)} items)...")

        try:
            # Zotero API: delete multiple items
            for key in chunk:
                try:
                    zot.delete_item(zot.item(key))
                    deleted += 1
                except Exception as e:
                    logger.error(f"  Failed to delete {key}: {e}")
                    failed += 1
        except Exception as e:
            logger.error(f"Chunk deletion failed: {e}")
            failed += len(chunk)

    logger.info(f"\n{'=' * 80}")
    logger.info("DELETION COMPLETE")
    logger.info(f"{'=' * 80}")
    logger.info(f"Deleted: {deleted}")
    logger.info(f"Failed: {failed}")


if __name__ == "__main__":
    main()
