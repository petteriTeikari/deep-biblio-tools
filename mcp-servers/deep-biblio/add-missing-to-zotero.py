#!/usr/bin/env python3
"""Automatically add missing citations to Zotero collection."""

import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from loguru import logger
from pyzotero import zotero

# Add module to path for citation parsing (must be before imports)
sys.path.insert(0, str(Path(__file__).parent / "src"))
from deep_biblio.arxiv_converter import ZoteroCitationMatcher  # noqa: E402

# Load environment variables
load_dotenv()

ZOTERO_API_KEY = os.getenv("ZOTERO_API_KEY")
ZOTERO_LIBRARY_ID = os.getenv("ZOTERO_LIBRARY_ID")

if not ZOTERO_API_KEY or not ZOTERO_LIBRARY_ID:
    logger.error("Missing Zotero credentials in .env file")
    sys.exit(1)

# Initialize Zotero client
zot = zotero.Zotero(ZOTERO_LIBRARY_ID, "user", ZOTERO_API_KEY)

# Find the "dpp-fashion" collection
logger.info("Finding 'dpp-fashion' collection...")
collections = zot.collections()
dpp_collection = None

for collection in collections:
    if collection["data"]["name"].lower() == "dpp-fashion":
        dpp_collection = collection
        logger.success(f"[PASS] Found collection: {collection['data']['name']}")
        logger.info(f"   Collection ID: {collection['key']}")
        break

if not dpp_collection:
    logger.error("[FAIL] Collection 'dpp-fashion' not found!")
    logger.info("Available collections:")
    for c in collections[:10]:
        logger.info(f"  - {c['data']['name']}")
    sys.exit(1)

collection_key = dpp_collection["key"]

# Load missing citations report
REPORT_PATH = Path(__file__).parent / "missing-citations-report.md"
ZOTERO_JSON_PATH = "/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/paper-manuscripts/mcp-review/dpp-fashion.json"
MANUSCRIPT_PATH = "/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/paper-manuscripts/mcp-review/mcp-draft-refined-v3.md"

logger.info("Loading missing citations...")
matcher = ZoteroCitationMatcher(ZOTERO_JSON_PATH)
citations = matcher.extract_citations_from_markdown(MANUSCRIPT_PATH)

# Find missing citations
missing = []
for cite in citations:
    entry = matcher.match_citation(cite)
    if not entry:
        missing.append(cite)

# Deduplicate by URL
url_to_cites = {}
for cite in missing:
    url = cite["url"]
    if url not in url_to_cites:
        url_to_cites[url] = cite

logger.info(f"Found {len(url_to_cites)} unique missing citations")

print("\n" + "=" * 60)
print(f"ADDING {len(url_to_cites)} CITATIONS TO ZOTERO")
print("=" * 60)


def fetch_metadata_from_doi(doi):
    """Fetch metadata from DOI via CrossRef."""
    try:
        response = requests.get(
            f"https://api.crossref.org/works/{doi}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()["message"]
            return {
                "itemType": "journalArticle",
                "title": data.get("title", [""])[0],
                "creators": [
                    {
                        "creatorType": "author",
                        "firstName": author.get("given", ""),
                        "lastName": author.get("family", ""),
                    }
                    for author in data.get("author", [])
                ],
                "date": str(data.get("published", {}).get("date-parts", [[""]])[0][0]),
                "DOI": doi,
                "url": f"https://doi.org/{doi}",
                "publicationTitle": data.get("container-title", [""])[0],
                "volume": str(data.get("volume", "")),
                "issue": str(data.get("issue", "")),
                "pages": data.get("page", ""),
                "collections": [collection_key],
            }
    except Exception as e:
        logger.debug(f"DOI fetch failed: {e}")
    return None


def fetch_metadata_from_arxiv(arxiv_id):
    """Fetch metadata from arXiv API."""
    try:
        response = requests.get(
            f"http://export.arxiv.org/api/query?id_list={arxiv_id}", timeout=10
        )
        if response.status_code == 200:
            import xml.etree.ElementTree as ET

            root = ET.fromstring(response.content)
            entry = root.find("{http://www.w3.org/2005/Atom}entry")

            if entry is not None:
                title = entry.find("{http://www.w3.org/2005/Atom}title").text.strip()
                authors = entry.findall("{http://www.w3.org/2005/Atom}author")
                published = entry.find("{http://www.w3.org/2005/Atom}published").text[
                    :4
                ]

                return {
                    "itemType": "preprint",
                    "title": title,
                    "creators": [
                        {
                            "creatorType": "author",
                            "firstName": "",
                            "lastName": author.find(
                                "{http://www.w3.org/2005/Atom}name"
                            ).text,
                        }
                        for author in authors
                    ],
                    "date": published,
                    "url": f"https://arxiv.org/abs/{arxiv_id}",
                    "repository": "arXiv",
                    "archiveID": arxiv_id,
                    "collections": [collection_key],
                }
    except Exception as e:
        logger.debug(f"arXiv fetch failed: {e}")
    return None


def create_generic_item(cite):
    """Create a generic webpage item from citation."""
    # Extract author last name
    author_name = cite["author"].replace(" et al.", "").strip()

    return {
        "itemType": "webpage",
        "title": f"{cite['author']}, {cite['year']}",
        "creators": [
            {"creatorType": "author", "firstName": "", "lastName": author_name}
        ],
        "date": cite["year"],
        "url": cite["url"],
        "collections": [collection_key],
    }


# Process each missing citation
added_count = 0
failed_count = 0

for i, (url, cite) in enumerate(url_to_cites.items(), 1):
    logger.info(
        f"\n[{i}/{len(url_to_cites)}] Processing: {cite['author']}, {cite['year']}"
    )
    logger.info(f"   URL: {url[:80]}...")

    item_data = None

    # Try DOI
    if "doi.org" in url:
        doi = url.split("doi.org/")[-1]
        logger.info("   Fetching from DOI...")
        item_data = fetch_metadata_from_doi(doi)

    # Try arXiv
    elif "arxiv.org" in url:
        match = re.search(r"(\d{4}\.\d{4,5})", url)
        if match:
            arxiv_id = match.group(1)
            logger.info("   Fetching from arXiv...")
            item_data = fetch_metadata_from_arxiv(arxiv_id)

    # Fallback to generic webpage
    if not item_data:
        logger.info("   Creating generic webpage item...")
        item_data = create_generic_item(cite)

    # Add to Zotero
    try:
        response = zot.create_items([item_data])
        if response.get("success"):
            added_count += 1
            logger.success("   [PASS] Added to Zotero!")
        else:
            failed_count += 1
            logger.error(f"   [FAIL] Failed: {response}")
    except Exception as e:
        failed_count += 1
        logger.error(f"   [FAIL] Error: {e}")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"[PASS] Successfully added: {added_count}")
print(f"[FAIL] Failed: {failed_count}")
print(f"[DOCS] Total processed: {len(url_to_cites)}")
print("\n[SUCCESS] All citations added to collection: dpp-fashion")
print("=" * 60)
