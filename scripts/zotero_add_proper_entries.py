#!/usr/bin/env python3
"""
Add proper entries to Zotero using Zotero's own metadata fetching.

This uses Zotero API's ability to create items from URLs/DOIs/ISBNs.
Much safer than manual metadata construction.

For URLs that Zotero can't auto-fetch, falls back to minimal webpage entry
BUT logs it clearly for manual review.
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


def fetch_metadata_from_url(url: str) -> dict | None:
    """
    Fetch metadata using DOI/arXiv APIs.

    Returns None if URL is not a DOI or arXiv link.
    """
    # DOI
    if "doi.org" in url:
        doi = url.split("doi.org/")[-1]
        try:
            response = requests.get(
                f"https://api.crossref.org/works/{doi}",
                headers={"User-Agent": "DeepBiblioTools/1.0"},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()["message"]
                # Convert CrossRef to Zotero format
                authors = []
                for author in data.get("author", []):
                    authors.append(
                        {
                            "creatorType": "author",
                            "firstName": author.get("given", ""),
                            "lastName": author.get("family", ""),
                        }
                    )

                return {
                    "itemType": "journalArticle",
                    "title": data.get("title", [""])[0],
                    "creators": authors,
                    "DOI": data.get("DOI", ""),
                    "url": url,
                    "date": data.get("published", {}).get("date-parts", [[""]])[
                        0
                    ][0],
                    "publicationTitle": data.get("container-title", [""])[0],
                }
        except Exception as e:
            logger.warning(f"Failed to fetch DOI metadata: {e}")

    # arXiv
    if "arxiv.org" in url.lower():
        import xml.etree.ElementTree as ET

        arxiv_id = None
        for pattern in ["/abs/", "/html/", "/pdf/"]:
            if pattern in url:
                arxiv_id = (
                    url.split(pattern)[-1]
                    .split("/")[0]
                    .split("?")[0]
                    .split("#")[0]
                )
                break

        if arxiv_id:
            # Remove version suffix
            if "v" in arxiv_id:
                v_pos = arxiv_id.rfind("v")
                if arxiv_id[v_pos + 1 :].isdigit():
                    arxiv_id = arxiv_id[:v_pos]

            try:
                response = requests.get(
                    f"http://export.arxiv.org/api/query?id_list={arxiv_id}",
                    timeout=10,
                )
                if response.status_code == 200:
                    root = ET.fromstring(response.content)
                    ns = {"atom": "http://www.w3.org/2005/Atom"}
                    entry = root.find("atom:entry", ns)
                    if entry is not None:
                        title = entry.find("atom:title", ns)
                        summary = entry.find("atom:summary", ns)
                        published = entry.find("atom:published", ns)
                        authors = entry.findall("atom:author", ns)

                        creators = []
                        for author in authors:
                            name = author.find("atom:name", ns)
                            if name is not None and name.text:
                                parts = name.text.strip().split()
                                if len(parts) >= 2:
                                    creators.append(
                                        {
                                            "creatorType": "author",
                                            "firstName": " ".join(parts[:-1]),
                                            "lastName": parts[-1],
                                        }
                                    )

                        return {
                            "itemType": "preprint",
                            "title": title.text.strip()
                            if title is not None
                            else "",
                            "creators": creators,
                            "abstractNote": (
                                summary.text.strip()
                                if summary is not None
                                else ""
                            ),
                            "url": url,
                            "archiveID": arxiv_id,
                            "date": published.text[:10]
                            if published is not None
                            else "",
                            "repository": "arXiv",
                        }
            except Exception as e:
                logger.warning(f"Failed to fetch arXiv metadata: {e}")

    return None


def validate_metadata(item: dict, url: str) -> tuple[bool, str]:
    """
    Validate that metadata is complete enough for citation.

    Returns: (is_valid, reason)
    """
    # Check title
    title = item.get("title", "")
    if not title or len(title) < 10:
        return False, "Title too short or missing"

    if title.startswith("Added from"):
        return False, "Garbage title pattern detected"

    # Check creators
    creators = item.get("creators", [])
    if not creators:
        # Organizational items (reports, etc.) might not have individual authors
        # This is acceptable for some itemTypes
        if item.get("itemType") not in ["report", "document", "webpage"]:
            return False, "No creators found (required for this item type)"

    return True, "OK"


def main():
    parser = argparse.ArgumentParser(description="Add proper entries to Zotero")
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
        default=True,
        help="Preview only (default: True)",
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
        urls = [line.strip() for line in f if line.strip()]

    logger.info(f"Found {len(urls)} URLs to process\n")

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

    for i, url in enumerate(urls, 1):
        logger.info(f"[{i}/{len(urls)}] {url}")

        # Try to fetch metadata
        metadata = fetch_metadata_from_url(url)

        if not metadata:
            logger.warning("  ⚠️  Could not auto-fetch metadata")
            logger.warning(
                "  → This URL requires manual addition via Zotero UI"
            )
            skipped.append(url)
            failed += 1
            continue

        # Validate
        is_valid, reason = validate_metadata(metadata, url)
        if not is_valid:
            logger.error(f"  ❌ Invalid metadata: {reason}")
            skipped.append(url)
            failed += 1
            continue

        # Preview
        logger.info(f"  ✓ Title: {metadata['title'][:60]}")
        creators = metadata.get("creators", [])
        if creators:
            author_names = ", ".join(
                c.get("lastName", "") for c in creators[:3]
            )
            logger.info(f"  ✓ Authors: {author_names}")
        logger.info(f"  ✓ Type: {metadata['itemType']}")

        if args.dry_run or not args.confirm:
            logger.info("  [DRY RUN - would add]")
            continue

        # Add to Zotero
        try:
            metadata["collections"] = [collection_key]
            response = zot.create_items([metadata])
            if response.get("success"):
                logger.info("  ✅ Added successfully")
                added += 1
            else:
                logger.error(f"  ❌ Failed: {response}")
                failed += 1
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
            failed += 1

        time.sleep(1)  # Rate limiting

    # Summary
    logger.info(f"\n{'=' * 80}")
    logger.info("SUMMARY")
    logger.info(f"{'=' * 80}")
    logger.info(f"Total URLs: {len(urls)}")
    logger.info(f"Added: {added}")
    logger.info(f"Failed/Skipped: {failed}")

    if skipped:
        logger.info(f"\n⚠️  {len(skipped)} URLs require manual addition:")
        for url in skipped:
            logger.info(f"  - {url}")
        logger.info("\nAdd these manually via Zotero → Add Item by Identifier")

    if args.dry_run or not args.confirm:
        logger.info(f"\n{'=' * 80}")
        logger.info("DRY RUN MODE - Nothing was added")
        logger.info(f"{'=' * 80}")
        logger.info("\nTo actually add, run:")
        logger.info(f"  python3 {sys.argv[0]} --urls {args.urls} --confirm")


if __name__ == "__main__":
    main()
