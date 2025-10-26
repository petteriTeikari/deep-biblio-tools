#!/usr/bin/env python3
"""
Add the 2 remaining URLs using DOI extraction.

For ScienceDirect: Extract PII, convert to DOI, fetch from CrossRef
For Ellen MacArthur: Will need manual addition (direct PDF)
"""

import os

import requests
from dotenv import load_dotenv
from pyzotero import zotero

load_dotenv()

api_key = os.getenv("ZOTERO_API_KEY")
library_id = os.getenv("ZOTERO_LIBRARY_ID")

zot = zotero.Zotero(library_id, "user", api_key)

# Get collection
collections = zot.collections()
collection_key = None
for coll in collections:
    if coll["data"]["name"] == "dpp-fashion":
        collection_key = coll["key"]
        break

# 1. ScienceDirect article - has DOI in URL
sciencedirect_url = (
    "https://www.sciencedirect.com/science/article/abs/pii/S1084804523000917"
)
doi = "10.1016/j.jnca.2023.103782"  # Found via CrossRef

print(f"Adding ScienceDirect article via DOI: {doi}")

# Fetch from CrossRef
response = requests.get(
    f"https://api.crossref.org/works/{doi}",
    headers={"User-Agent": "DeepBiblioTools/1.0"},
    timeout=10,
)

if response.status_code == 200:
    data = response.json()["message"]

    # Convert to Zotero format
    authors = []
    for author in data.get("author", []):
        authors.append(
            {
                "creatorType": "author",
                "firstName": author.get("given", ""),
                "lastName": author.get("family", ""),
            }
        )

    item = {
        "itemType": "journalArticle",
        "title": data.get("title", [""])[0],
        "creators": authors,
        "DOI": data.get("DOI", ""),
        "url": sciencedirect_url,  # Original URL
        "date": str(data.get("published", {}).get("date-parts", [[""]])[0][0]),
        "publicationTitle": data.get("container-title", [""])[0],
        "volume": data.get("volume", ""),
        "issue": data.get("issue", ""),
        "pages": data.get("page", ""),
        "collections": [collection_key],
    }

    print(f"  Title: {item['title'][:70]}")
    print(f"  Authors: {', '.join(c['lastName'] for c in authors[:3])}")

    # Add to Zotero
    result = zot.create_items([item])
    if result.get("success"):
        print("  Successfully added to Zotero!")
    else:
        print(f"  Failed: {result}")
else:
    print(f"  CrossRef API error: {response.status_code}")

print("\n" + "=" * 80)
print("Ellen MacArthur PDF - REQUIRES MANUAL ADDITION")
print("=" * 80)
print("This is a direct PDF link that cannot be auto-fetched.")
print("Please add manually via Zotero UI:")
print(
    "  URL: https://content.ellenmacarthurfoundation.org/m/54c053dd73f80168/original/France-s-Anti-waste-and-Circular-Economy-Law.pdf"
)
print("\nSteps:")
print("1. Open Zotero")
print("2. File → New Item → Link to URI")
print("3. Paste the URL above")
print("4. Manually add title: 'France's Anti-waste and Circular Economy Law'")
print("5. Add to 'dpp-fashion' collection")
