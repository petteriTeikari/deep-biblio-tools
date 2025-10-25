#!/usr/bin/env python3
"""Add verified 4DGS citations to Zotero collection."""

import os
import sys
import xml.etree.ElementTree as ET

import requests
from pyzotero import zotero

# Zotero credentials from environment
ZOTERO_API_KEY = os.getenv("ZOTERO_API_KEY")
ZOTERO_LIBRARY_ID = os.getenv("ZOTERO_LIBRARY_ID")

if not ZOTERO_API_KEY or not ZOTERO_LIBRARY_ID:
    # Try loading from deep-biblio-tools .env (centralized credentials)
    env_path = "/Users/petteri/Dropbox/github-personal/deep-biblio-tools/.env"

    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("ZOTERO_API_KEY=") and not ZOTERO_API_KEY:
                    ZOTERO_API_KEY = line.split("=", 1)[1]
                elif (
                    line.startswith("ZOTERO_LIBRARY_ID=")
                    and not ZOTERO_LIBRARY_ID
                ):
                    ZOTERO_LIBRARY_ID = line.split("=", 1)[1]

if not ZOTERO_API_KEY or not ZOTERO_LIBRARY_ID:
    print("[FAIL] Error: Missing Zotero credentials")
    print("Set ZOTERO_API_KEY and ZOTERO_LIBRARY_ID environment variables")
    sys.exit(1)

# Initialize Zotero
zot = zotero.Zotero(ZOTERO_LIBRARY_ID, "user", ZOTERO_API_KEY)

# 4DGS Citations to add
CITATIONS = [
    ("Gaussian Garments", "2409.08189", "arxiv"),
    ("ClothingTwin", "10.1111/cgf.70240", "doi"),
    ("D3GA", "2311.08581", "arxiv"),
    ("3DGS-Avatar", "2312.09228", "arxiv"),
    ("MPMAvatar", "2510.01619", "arxiv"),
    ("Offset Geometric Contact", "10.1145/3731205", "doi"),
]


def find_collection(name="dpp-fashion"):
    """Find collection by name."""
    print(f"Finding '{name}' collection...")
    collections = zot.collections()

    for c in collections:
        if c["data"]["name"].lower() == name.lower():
            print(f"[PASS] Found: {c['data']['name']} ({c['key']})")
            return c["key"]

    print(f"[FAIL] Collection '{name}' not found")
    print("Available collections:")
    for c in collections[:10]:
        print(f"  - {c['data']['name']}")
    return None


def fetch_arxiv(arxiv_id, collection_key):
    """Fetch metadata from arXiv."""
    print(f"  Fetching arXiv {arxiv_id}...")
    response = requests.get(
        f"http://export.arxiv.org/api/query?id_list={arxiv_id}", timeout=10
    )
    root = ET.fromstring(response.content)
    entry = root.find("{http://www.w3.org/2005/Atom}entry")

    if entry is None:
        return None

    title = entry.find("{http://www.w3.org/2005/Atom}title").text.strip()
    authors = entry.findall("{http://www.w3.org/2005/Atom}author")
    year = entry.find("{http://www.w3.org/2005/Atom}published").text[:4]

    return {
        "itemType": "preprint",
        "title": title,
        "creators": [
            {
                "creatorType": "author",
                "firstName": "",
                "lastName": a.find("{http://www.w3.org/2005/Atom}name").text,
            }
            for a in authors
        ],
        "date": year,
        "url": f"https://arxiv.org/abs/{arxiv_id}",
        "repository": "arXiv",
        "archiveID": arxiv_id,
        "collections": [collection_key],
    }


def fetch_doi(doi, collection_key):
    """Fetch metadata from DOI."""
    print(f"  Fetching DOI {doi}...")
    response = requests.get(
        f"https://api.crossref.org/works/{doi}",
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    )
    data = response.json()["message"]

    return {
        "itemType": "journalArticle",
        "title": data.get("title", [""])[0],
        "creators": [
            {
                "creatorType": "author",
                "firstName": a.get("given", ""),
                "lastName": a.get("family", ""),
            }
            for a in data.get("author", [])
        ],
        "date": str(data.get("published", {}).get("date-parts", [[""]])[0][0]),
        "DOI": doi,
        "url": f"https://doi.org/{doi}",
        "publicationTitle": data.get("container-title", [""])[0],
        "collections": [collection_key],
    }


def exists(title, collection_key):
    """Check if citation exists in collection."""
    items = zot.collection_items(collection_key)
    return any(
        i["data"].get("title", "").lower() == title.lower() for i in items
    )


def main():
    """Add 4DGS citations to Zotero."""
    collection_key = find_collection("dpp-fashion")
    if not collection_key:
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print(f"ADDING {len(CITATIONS)} 4DGS CITATIONS TO ZOTERO")
    print(f"{'=' * 60}\n")

    added = 0
    skipped = 0
    failed = 0

    for name, identifier, type_ in CITATIONS:
        print(f"{name}:")

        try:
            # Fetch metadata
            if type_ == "arxiv":
                item = fetch_arxiv(identifier, collection_key)
            else:
                item = fetch_doi(identifier, collection_key)

            if not item:
                print("  [FAIL] Failed to fetch metadata")
                failed += 1
                continue

            # Check if exists
            if exists(item["title"], collection_key):
                print("  [NEXT]  Already exists")
                skipped += 1
                continue

            # Add to Zotero
            response = zot.create_items([item])
            if response.get("success"):
                print("  [PASS] Added!")
                added += 1
            else:
                print(f"  [FAIL] Failed: {response}")
                failed += 1

        except Exception as e:
            print(f"  [FAIL] Error: {e}")
            failed += 1

        print()

    print(f"{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"[PASS] Added:   {added}")
    print(f"[NEXT]  Skipped: {skipped}")
    print(f"[FAIL] Failed:  {failed}")
    print(f"[DOCS] Total:   {len(CITATIONS)}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
