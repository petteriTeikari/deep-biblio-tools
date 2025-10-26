#!/usr/bin/env python3
"""Check for entries in Zotero without authors."""

import json
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

# Get all items
items = zot.collection_items(collection_key)

print(f"Total items in collection: {len(items)}\n")

no_author_items = []

for item in items:
    data = item.get("data", {})
    creators = data.get("creators", [])
    title = data.get("title", "Untitled")
    item_type = data.get("itemType", "unknown")
    url = data.get("url", "")
    date_added = item.get("meta", {}).get("dateAdded", "")

    if not creators:
        no_author_items.append(
            {
                "key": item["key"],
                "title": title,
                "type": item_type,
                "url": url,
                "date_added": date_added,
            }
        )

print(f"Found {len(no_author_items)} items without authors:\n")
print("=" * 80)

for i, item in enumerate(no_author_items, 1):
    print(f"[{i}] {item['title'][:70]}")
    print(f"    Key: {item['key']}")
    print(f"    Type: {item['type']}")
    print(f"    URL: {item['url'][:70] if item['url'] else 'None'}")
    print(f"    Added: {item['date_added']}")
    print()

# Save to file
with open("entries_without_authors.json", "w") as f:
    json.dump(no_author_items, f, indent=2)

print("Saved to: entries_without_authors.json")
