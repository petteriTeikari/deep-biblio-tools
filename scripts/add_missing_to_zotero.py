#!/usr/bin/env python3
"""Add missing citations to Zotero library using conversion_results.json."""

import json
import logging
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from pyzotero import zotero

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

ZOTERO_API_KEY = os.getenv("ZOTERO_API_KEY")
ZOTERO_LIBRARY_ID = os.getenv("ZOTERO_LIBRARY_ID")
ZOTERO_LIBRARY_TYPE = os.getenv("ZOTERO_LIBRARY_TYPE", "user")

if not ZOTERO_API_KEY or not ZOTERO_LIBRARY_ID:
    logger.error("Missing Zotero credentials in .env file")
    logger.error("Required: ZOTERO_API_KEY, ZOTERO_LIBRARY_ID")
    sys.exit(1)


def extract_arxiv_id(url: str) -> str | None:
    """Extract arXiv ID from URL using string methods."""
    if "arxiv.org" not in url.lower():
        return None

    # Look for pattern like 2410.10762 or 2304.03442
    # Format: YYMM.NNNNN or YYMM.NNNN
    parts = url.split("/")
    for part in parts:
        # Check if part looks like an arXiv ID
        if "." in part:
            left, right = part.split(".", 1)
            # Check if left part is 4 digits starting with 19-25 (years)
            if (
                len(left) == 4
                and left.isdigit()
                and left.startswith(("19", "20", "21", "22", "23", "24", "25"))
            ):
                # Check if right part is 4-5 digits
                # Remove any trailing characters (like 'v1')
                right_clean = ""
                for char in right:
                    if char.isdigit():
                        right_clean += char
                    else:
                        break

                if len(right_clean) in [4, 5]:
                    return f"{left}.{right_clean}"

    return None


def extract_doi(url: str) -> str | None:
    """Extract DOI from URL using string methods."""
    if "doi.org" not in url.lower():
        return None

    # Find "doi.org/" and extract everything after it
    parts = url.split("doi.org/")
    if len(parts) >= 2:
        doi = parts[1]
        # Remove any trailing fragments or query params
        if "#" in doi:
            doi = doi.split("#")[0]
        if "?" in doi:
            doi = doi.split("?")[0]
        return doi

    return None


def fetch_metadata_from_doi(doi: str) -> dict | None:
    """Fetch metadata from DOI via CrossRef."""
    try:
        response = requests.get(
            f"https://api.crossref.org/works/{doi}",
            headers={
                "User-Agent": "DeepBiblioTools/1.0 (mailto:petteri@example.com)"
            },
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()["message"]

            # Extract authors
            creators = []
            for author in data.get("author", []):
                creators.append(
                    {
                        "creatorType": "author",
                        "firstName": author.get("given", ""),
                        "lastName": author.get("family", ""),
                    }
                )

            # Extract year
            year = ""
            if "published" in data:
                date_parts = data["published"].get("date-parts", [[]])
                if date_parts and date_parts[0]:
                    year = str(date_parts[0][0])

            return {
                "itemType": "journalArticle",
                "title": data.get("title", [""])[0],
                "creators": creators,
                "date": year,
                "DOI": doi,
                "url": f"https://doi.org/{doi}",
                "publicationTitle": data.get("container-title", [""])[0],
                "volume": str(data.get("volume", "")),
                "issue": str(data.get("issue", "")),
                "pages": data.get("page", ""),
            }
    except Exception as e:
        logger.debug(f"DOI fetch failed for {doi}: {e}")

    return None


def fetch_metadata_from_arxiv(arxiv_id: str) -> dict | None:
    """Fetch metadata from arXiv API."""
    try:
        response = requests.get(
            f"http://export.arxiv.org/api/query?id_list={arxiv_id}",
            timeout=10,
        )
        if response.status_code == 200:
            import xml.etree.ElementTree as ET

            root = ET.fromstring(response.content)
            entry = root.find("{http://www.w3.org/2005/Atom}entry")

            if entry is not None:
                title = entry.find(
                    "{http://www.w3.org/2005/Atom}title"
                ).text.strip()
                authors = entry.findall("{http://www.w3.org/2005/Atom}author")
                published = entry.find(
                    "{http://www.w3.org/2005/Atom}published"
                ).text[:4]

                creators = []
                for author in authors:
                    name = author.find("{http://www.w3.org/2005/Atom}name").text
                    # Split name into first/last (simple approach)
                    parts = name.split()
                    if len(parts) > 1:
                        first_name = " ".join(parts[:-1])
                        last_name = parts[-1]
                    else:
                        first_name = ""
                        last_name = name

                    creators.append(
                        {
                            "creatorType": "author",
                            "firstName": first_name,
                            "lastName": last_name,
                        }
                    )

                return {
                    "itemType": "preprint",
                    "title": title,
                    "creators": creators,
                    "date": published,
                    "url": f"https://arxiv.org/abs/{arxiv_id}",
                    "repository": "arXiv",
                    "archiveID": arxiv_id,
                }
    except Exception as e:
        logger.debug(f"arXiv fetch failed for {arxiv_id}: {e}")

    return None


def create_webpage_item(url: str, title: str = "") -> dict:
    """Create a generic webpage item."""
    # Extract domain name for title if not provided
    if not title:
        # Simple domain extraction
        domain = url
        if "://" in domain:
            domain = domain.split("://", 1)[1]
        if "/" in domain:
            domain = domain.split("/", 1)[0]
        title = f"Webpage: {domain}"

    return {
        "itemType": "webpage",
        "title": title,
        "url": url,
        "accessDate": "2025-10-26",
    }


def main():
    """Main entry point."""
    # Find conversion_results.json
    results_file = Path("conversion_results.json")
    if not results_file.exists():
        logger.error(f"conversion_results.json not found in {Path.cwd()}")
        logger.error("Please run the conversion first to generate this file")
        sys.exit(1)

    # Load results
    with open(results_file) as f:
        results = json.load(f)

    unknown_citations = results.get("unknown_authors", [])

    if not unknown_citations:
        logger.info("No unknown citations to add!")
        sys.exit(0)

    logger.info(f"Found {len(unknown_citations)} unknown citations to process")
    logger.info("")

    # Initialize Zotero client
    zot = zotero.Zotero(ZOTERO_LIBRARY_ID, ZOTERO_LIBRARY_TYPE, ZOTERO_API_KEY)

    # Find the dpp-fashion collection
    logger.info("Finding 'dpp-fashion' collection...")
    collections = zot.collections()
    collection_key = None

    for collection in collections:
        if collection["data"]["name"].lower() == "dpp-fashion":
            collection_key = collection["key"]
            logger.info(f" Found collection: {collection['data']['name']}")
            logger.info(f"  Collection ID: {collection_key}")
            logger.info("")
            break

    if not collection_key:
        logger.error(" Collection 'dpp-fashion' not found!")
        logger.error("Available collections:")
        for c in collections[:10]:
            logger.error(f"  - {c['data']['name']}")
        sys.exit(1)

    # Process each citation
    added_count = 0
    failed_count = 0
    skipped_count = 0

    for i, entry in enumerate(unknown_citations, 1):
        url = entry["url"]
        key = entry["key"]

        logger.info(f"[{i}/{len(unknown_citations)}] Processing: {key}")
        logger.info(f"  URL: {url}")

        # Skip internal references
        if url.startswith("#"):
            logger.info("   Skipping (internal reference)")
            skipped_count += 1
            continue

        item_data = None

        # Try DOI first
        doi = extract_doi(url)
        if doi:
            logger.info(f"   Fetching from DOI: {doi}")
            item_data = fetch_metadata_from_doi(doi)
            if item_data:
                logger.info("   Metadata fetched from CrossRef")

        # Try arXiv
        if not item_data:
            arxiv_id = extract_arxiv_id(url)
            if arxiv_id:
                logger.info(f"   Fetching from arXiv: {arxiv_id}")
                item_data = fetch_metadata_from_arxiv(arxiv_id)
                if item_data:
                    logger.info("   Metadata fetched from arXiv")

        # Fallback to generic webpage
        if not item_data:
            logger.info("   Creating generic webpage item")
            item_data = create_webpage_item(url)

        # Add to collection
        item_data["collections"] = [collection_key]

        # Add to Zotero
        try:
            response = zot.create_items([item_data])
            if response.get("success"):
                added_count += 1
                logger.info("   Added to Zotero!")
            else:
                failed_count += 1
                logger.error(f"   Failed: {response}")
        except Exception as e:
            failed_count += 1
            logger.error(f"   Error: {e}")

        logger.info("")

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f" Successfully added: {added_count}")
    print(f" Failed:            {failed_count}")
    print(f" Skipped:           {skipped_count}")
    print(f"  Total processed:   {len(unknown_citations)}")
    print("=" * 60)

    if added_count > 0:
        print("")
        print("Next steps:")
        print("1. Export your Zotero library to update the .json file")
        print("2. Re-run the conversion to pick up the new citations")


if __name__ == "__main__":
    main()
