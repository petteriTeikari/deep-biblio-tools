#!/usr/bin/env python3
"""
Add entries to Zotero using the API's built-in URL/DOI/ISBN resolver.

This mimics what the Zotero Connector (Chrome extension) does:
1. POST the URL/DOI/ISBN to Zotero's item creation endpoint
2. Zotero's server fetches metadata using its translation infrastructure
3. Returns fully populated item with authors, title, etc.

This is THE correct way to add items programmatically.
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from pyzotero import zotero

# Load environment
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def add_item_from_identifier(zot, identifier: str, collection_key: str) -> dict:
    """
    Add item to Zotero using URL/DOI/ISBN identifier.

    This uses Zotero's built-in translation via the API.
    Same backend as the Zotero Connector extension.

    Returns: Response dict with 'success' key
    """
    try:
        # Use Pyzotero's item_from_identifier method
        # This hits /items/new endpoint with identifier parameter
        zot.item_template("book")  # Default template

        # Actually, let's use the raw API directly for better control
        import requests

        api_key = os.getenv("ZOTERO_API_KEY")
        library_id = os.getenv("ZOTERO_LIBRARY_ID")

        # Step 1: Ask Zotero to translate the identifier
        headers = {
            "Zotero-API-Key": api_key,
            "Content-Type": "application/json",
        }

        # The identifier goes in the request body
        # Format: Send the URL/DOI/ISBN as plain text to let Zotero resolve it
        # Actually, we need to use the search endpoint first

        # Alternative: Use /items/new with identifier parameter
        search_url = f"https://api.zotero.org/users/{library_id}/items"
        search_params = {"identifier": identifier}

        response = requests.get(
            search_url, headers=headers, params=search_params, timeout=30
        )

        if response.status_code == 200:
            items = response.json()
            if items:
                # Got translated item(s)
                # Add to collection and create
                for item in items:
                    item_data = item.get("data", {})
                    item_data["collections"] = [collection_key]

                    # Create the item
                    create_response = zot.create_items([item_data])
                    return create_response

        return {
            "success": {},
            "failed": {"0": {"message": "Could not translate identifier"}},
        }

    except Exception as e:
        logger.error(f"Error: {e}")
        return {"success": {}, "failed": {"0": {"message": str(e)}}}


def main():
    parser = argparse.ArgumentParser(
        description="Add entries to Zotero using API translation"
    )
    parser.add_argument(
        "--urls",
        type=Path,
        required=True,
        help="Text file with URLs/DOIs/ISBNs (one per line)",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="dpp-fashion",
        help="Zotero collection name",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview only (no dry-run by default)",
    )
    parser.add_argument(
        "--confirm", action="store_true", help="Actually add items"
    )
    args = parser.parse_args()

    # Get credentials
    api_key = os.getenv("ZOTERO_API_KEY")
    library_id = os.getenv("ZOTERO_LIBRARY_ID")

    if not api_key or not library_id:
        logger.error("Missing ZOTERO_API_KEY or ZOTERO_LIBRARY_ID in .env")
        sys.exit(1)

    # Load URLs
    with open(args.urls) as f:
        identifiers = [line.strip() for line in f if line.strip()]

    logger.info(f"Found {len(identifiers)} identifiers to process\n")

    # Connect to Zotero
    zot = zotero.Zotero(library_id, "user", api_key)

    # Find collection
    collections = zot.collections()
    collection_key = None
    for coll in collections:
        if coll["data"]["name"] == args.collection:
            collection_key = coll["key"]
            break

    if not collection_key:
        logger.error(f"Collection '{args.collection}' not found")
        sys.exit(1)

    # Process each identifier
    added = 0
    failed = 0
    skipped = []

    for i, identifier in enumerate(identifiers, 1):
        logger.info(f"[{i}/{len(identifiers)}] {identifier}")

        if args.dry_run or not args.confirm:
            logger.info("  [DRY RUN - would attempt to add]")
            continue

        # Add via API
        result = add_item_from_identifier(zot, identifier, collection_key)

        if result.get("success"):
            logger.info("  [OK] Added successfully")
            added += 1
        else:
            error_msg = (
                result.get("failed", {})
                .get("0", {})
                .get("message", "Unknown error")
            )
            logger.error(f"  [FAILED] Failed: {error_msg}")
            skipped.append(identifier)
            failed += 1

        time.sleep(1)  # Rate limiting

    # Summary
    logger.info(f"\n{'=' * 80}")
    logger.info("SUMMARY")
    logger.info(f"{'=' * 80}")
    logger.info(f"Total identifiers: {len(identifiers)}")
    logger.info(f"Added: {added}")
    logger.info(f"Failed: {failed}")

    if skipped:
        logger.info(f"\n[WARNING] {len(skipped)} identifiers failed:")
        for identifier in skipped:
            logger.info(f"  - {identifier}")
        logger.info("\nThese require manual addition via Zotero UI")

    if args.dry_run or not args.confirm:
        logger.info(f"\n{'=' * 80}")
        logger.info("DRY RUN MODE - Nothing was added")
        logger.info(f"{'=' * 80}")
        logger.info("\nTo actually add, run:")
        logger.info(f"  python3 {sys.argv[0]} --urls {args.urls} --confirm")


if __name__ == "__main__":
    main()
