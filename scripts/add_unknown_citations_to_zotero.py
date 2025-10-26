#!/usr/bin/env python3
"""
Add Unknown citations from conversion_results.json to Zotero library.

This script:
1. Reads conversion_results.json to get Unknown citation URLs
2. Fetches metadata from DOI/arXiv/CrossRef APIs where possible
3. Adds each citation to the specified Zotero collection
4. Reports success/failure for each citation
"""

import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pyzotero import zotero

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def get_metadata_from_url(url: str) -> dict | None:
    """
    Fetch metadata for a URL from appropriate API.

    Returns metadata dict or None if unable to fetch.
    """
    import requests

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
                return {
                    "itemType": "journalArticle",
                    "title": data.get("title", [""])[0],
                    "DOI": data.get("DOI", ""),
                    "url": url,
                    "abstractNote": data.get("abstract", ""),
                }
        except Exception as e:
            logger.warning(f"Failed to fetch DOI metadata for {doi}: {e}")

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
                            "abstractNote": summary.text.strip()
                            if summary is not None
                            else "",
                            "url": url,
                            "archiveID": arxiv_id,
                            "date": published.text[:10]
                            if published is not None
                            else "",
                            "repository": "arXiv",
                        }
            except Exception as e:
                logger.warning(
                    f"Failed to fetch arXiv metadata for {arxiv_id}: {e}"
                )

    # Fallback: generic webpage
    return {
        "itemType": "webpage",
        "title": f"Added from URL: {url[:80]}",
        "url": url,
    }


def add_citations_to_zotero(
    results_path: Path,
    collection_name: str,
    library_id: str | None = None,
    api_key: str | None = None,
    library_type: str = "user",
) -> None:
    """Add Unknown citations to Zotero."""
    # Load results
    with open(results_path) as f:
        data = json.load(f)

    # Handle both author-verification.json and conversion_results.json formats
    if "issues" in data:
        # author-verification.json format
        not_in_zotero = [
            issue
            for issue in data["issues"]
            if issue["issue"] == "Not found in Zotero library"
        ]
        # Get unique URLs, filter out internal references and empty URLs
        urls_to_add = list(
            set(
                issue["url"]
                for issue in not_in_zotero
                if issue["url"] and not issue["url"].startswith("#")
            )
        )
    else:
        # conversion_results.json format (fallback)
        unknown_citations = data.get("unknown_authors", [])
        urls_to_add = [
            c["url"] for c in unknown_citations if not c["url"].startswith("#")
        ]

    logger.info(f"Found {len(urls_to_add)} citations to add to Zotero")

    # Get credentials
    api_key = api_key or os.getenv("ZOTERO_API_KEY")
    library_id = library_id or os.getenv("ZOTERO_LIBRARY_ID")

    if not api_key or not library_id:
        logger.error(
            "Missing Zotero credentials. Set ZOTERO_API_KEY and ZOTERO_LIBRARY_ID"
        )
        sys.exit(1)

    # Connect to Zotero
    zot = zotero.Zotero(library_id, library_type, api_key)

    # Find collection
    collections = zot.collections()
    collection_key = None
    for coll in collections:
        if coll["data"]["name"] == collection_name:
            collection_key = coll["key"]
            logger.info(
                f"Found collection '{collection_name}' (key: {collection_key})"
            )
            break

    if not collection_key:
        logger.error(f"Collection '{collection_name}' not found")
        sys.exit(1)

    # Add each citation
    added = 0
    failed = 0

    for i, url in enumerate(urls_to_add, 1):
        logger.info(f"[{i}/{len(urls_to_add)}] Processing: {url}")

        try:
            # Get metadata
            metadata = get_metadata_from_url(url)
            if not metadata:
                metadata = {
                    "itemType": "webpage",
                    "title": f"Added from URL: {url[:80]}",
                    "url": url,
                }

            # Add to collection
            metadata["collections"] = [collection_key]

            # Create item
            response = zot.create_items([metadata])

            if response.get("success"):
                logger.info(
                    f"  SUCCESS: Added '{metadata.get('title', url)[:60]}'"
                )
                added += 1
            else:
                logger.error(f"  FAILED: {response}")
                failed += 1

        except Exception as e:
            logger.error(f"  ERROR: {e}")
            failed += 1

    logger.info(f"\nSummary: {added} added, {failed} failed")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Add Unknown citations to Zotero"
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("conversion_results.json"),
        help="Path to conversion_results.json",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="dpp-fashion",
        help="Zotero collection name",
    )
    parser.add_argument(
        "--library-id",
        type=str,
        help="Zotero library ID (or set ZOTERO_LIBRARY_ID)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="Zotero API key (or set ZOTERO_API_KEY)",
    )

    args = parser.parse_args()

    add_citations_to_zotero(
        results_path=args.results,
        collection_name=args.collection,
        library_id=args.library_id,
        api_key=args.api_key,
    )
