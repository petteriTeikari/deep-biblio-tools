#!/usr/bin/env python3
"""
Add entries to Zotero using translation-server.

Uses the local Zotero translation-server (Docker) to convert URLs to metadata.
This is the same technology the Zotero Connector uses.

Prerequisites:
  docker run -d -p 1969:1969 --name zotero-translation-server zotero/translation-server

Usage:
  python3 scripts/zotero_add_with_translator.py --urls urls.txt --dry-run
  python3 scripts/zotero_add_with_translator.py --urls urls.txt --confirm
"""

import argparse
import logging
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from pyzotero import zotero

# Load environment
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

TRANSLATOR_URL = "http://localhost:1969/web"


def fetch_metadata_from_translator(url: str) -> dict | None:
    """
    Fetch metadata using local translation-server.

    Returns Zotero JSON dict or None if translation fails.
    """
    try:
        response = requests.post(
            TRANSLATOR_URL,
            data=url,
            headers={"Content-Type": "text/plain"},
            timeout=30,
        )

        if response.status_code == 200:
            items = response.json()
            if items and len(items) > 0:
                # Return first item (usually the main one)
                return items[0]
            else:
                logger.warning("  Translation returned empty result")
                return None
        else:
            logger.warning(
                f"  Translation server error: {response.status_code}"
            )
            return None

    except requests.exceptions.ConnectionError:
        logger.error("  Translation server not running!")
        logger.error(
            "  Start it with: docker run -d -p 1969:1969 zotero/translation-server"
        )
        return None
    except Exception as e:
        logger.warning(f"  Translation failed: {e}")
        return None


def validate_metadata(item: dict, url: str) -> tuple[bool, str, list[str]]:
    """
    Validate metadata completeness.

    Returns: (is_valid, reason, warnings)
    """
    warnings = []

    # Check title
    title = item.get("title", "")
    if not title or len(title) < 5:
        return False, "Title missing or too short", warnings

    # Check for generic titles
    generic_titles = [
        "Added from URL",
        "Untitled",
        "Document",
        "Webpage",
    ]
    if any(gen in title for gen in generic_titles):
        return False, f"Generic title detected: {title}", warnings

    # Check creators
    creators = item.get("creators", [])
    if not creators:
        # Some item types (reports, webpages) might not have individual authors
        # This is acceptable but should be flagged
        if item.get("itemType") in ["report", "document", "webpage"]:
            warnings.append("No individual authors (organizational content)")
        else:
            return (
                False,
                "No creators found (required for this item type)",
                warnings,
            )

    # Check URL matches
    item_url = item.get("url", "")
    if item_url != url:
        warnings.append(f"URL mismatch: {item_url} != {url}")

    return True, "OK", warnings


def main():
    parser = argparse.ArgumentParser(
        description="Add entries to Zotero using translation-server"
    )
    parser.add_argument(
        "--urls",
        type=Path,
        required=True,
        help="Text file with URLs (one per line)",
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
        help="Preview only (no changes)",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually add items to Zotero",
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
        urls = [line.strip() for line in f if line.strip()]

    logger.info(f"Found {len(urls)} URLs to process\n")

    # Test translation server
    logger.info("Testing translation server...")
    try:
        # Test the /web endpoint with a simple request
        requests.post(
            TRANSLATOR_URL,
            data="https://www.example.com",
            headers={"Content-Type": "text/plain"},
            timeout=5,
        )
        # Any response (even error) means server is running
        logger.info("  Translation server is running\n")
    except requests.exceptions.ConnectionError:
        logger.error("  Translation server not running!")
        logger.error("  Start it with:")
        logger.error("    docker run -d -p 1969:1969 zotero/translation-server")
        sys.exit(1)

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

    # Process each URL
    added = 0
    failed = 0
    skipped = []
    warnings_list = []

    for i, url in enumerate(urls, 1):
        logger.info(f"[{i}/{len(urls)}] {url}")

        # Fetch metadata via translation server
        metadata = fetch_metadata_from_translator(url)

        if not metadata:
            logger.error("  Could not fetch metadata")
            skipped.append(url)
            failed += 1
            continue

        # Validate
        is_valid, reason, warnings = validate_metadata(metadata, url)

        if not is_valid:
            logger.error(f"  Invalid metadata: {reason}")
            skipped.append(url)
            failed += 1
            continue

        # Show preview
        logger.info(f"  Title: {metadata.get('title', 'N/A')[:70]}")
        logger.info(f"  Type: {metadata.get('itemType', 'N/A')}")

        creators = metadata.get("creators", [])
        if creators:
            # Format creator names
            names = []
            for c in creators[:3]:
                if "lastName" in c:
                    names.append(c["lastName"])
                elif "name" in c:
                    names.append(c["name"])
            logger.info(f"  Creators: {', '.join(names)}")
        else:
            logger.warning("  No creators found")

        # Show warnings
        for warning in warnings:
            logger.warning(f"  {warning}")
            warnings_list.append((url, warning))

        if args.dry_run or not args.confirm:
            logger.info("  [DRY RUN - would add]")
            continue

        # Add to Zotero
        try:
            # Remove translation-server specific fields
            metadata.pop("key", None)
            metadata.pop("version", None)

            # Add to collection
            metadata["collections"] = [collection_key]

            # Create item
            response = zot.create_items([metadata])

            if response.get("success"):
                logger.info("  Added successfully")
                added += 1
            else:
                error = (
                    response.get("failed", {})
                    .get("0", {})
                    .get("message", "Unknown error")
                )
                logger.error(f"  Failed: {error}")
                skipped.append(url)
                failed += 1

        except Exception as e:
            logger.error(f"  Error adding to Zotero: {e}")
            skipped.append(url)
            failed += 1

        time.sleep(1)  # Rate limiting

    # Summary
    logger.info(f"\n{'=' * 80}")
    logger.info("SUMMARY")
    logger.info(f"{'=' * 80}")
    logger.info(f"Total URLs: {len(urls)}")
    logger.info(f"Added: {added}")
    logger.info(f"Failed: {failed}")

    if warnings_list:
        logger.info(f"\nWarnings ({len(warnings_list)}):")
        for url, warning in warnings_list:
            logger.info(f"  {url[:50]}: {warning}")

    if skipped:
        logger.info(f"\n{len(skipped)} URLs failed:")
        for url in skipped:
            logger.info(f"  - {url}")
        logger.info("\nThese may require manual addition via Zotero UI")

    if args.dry_run or not args.confirm:
        logger.info(f"\n{'=' * 80}")
        logger.info("DRY RUN MODE - Nothing was added")
        logger.info(f"{'=' * 80}")
        logger.info("\nTo actually add, run:")
        logger.info(f"  python3 {sys.argv[0]} --urls {args.urls} --confirm")


if __name__ == "__main__":
    main()
