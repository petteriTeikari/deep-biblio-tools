#!/usr/bin/env python3
"""Add Ellen MacArthur Foundation PDF to Zotero with minimal metadata."""

import os

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

# Create minimal report entry
item = {
    "itemType": "report",
    "title": "France's Anti-waste and Circular Economy Law",
    "creators": [
        {"creatorType": "author", "name": "Ellen MacArthur Foundation"}
    ],
    "url": "https://content.ellenmacarthurfoundation.org/m/54c053dd73f80168/original/France-s-Anti-waste-and-Circular-Economy-Law.pdf",
    "institution": "Ellen MacArthur Foundation",
    "date": "2020",  # Approximate based on context
    "abstractNote": "Overview of France's Anti-waste and Circular Economy Law (AGEC Law)",
    "collections": [collection_key],
}

print("Adding Ellen MacArthur Foundation PDF...")
print(f"  Title: {item['title']}")
print(f"  Type: {item['itemType']}")
print(f"  Organization: {item['institution']}")

result = zot.create_items([item])

if result.get("success"):
    print("  Successfully added to Zotero!")
else:
    print(f"  Failed: {result}")
