#!/usr/bin/env python3
"""Analyze Zotero JSON to find issues."""

import json
import sys

json_path = "/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/mcp-draft-refined-v3.json"

try:
    with open(json_path) as f:
        data = json.load(f)

    print("Successfully loaded JSON")
    print(f"Type: {type(data)}")

    if isinstance(data, list):
        print(f"Number of items: {len(data)}")

        # Check first few items
        for i, item in enumerate(data[:5]):
            print(f"\n[{i}] Item keys: {list(item.keys())[:10]}")
            if "title" in item:
                print(f"    Title: {item.get('title', 'N/A')[:70]}")
            if "author" in item:
                authors = item.get("author", [])
                if authors:
                    first_author = authors[0]
                    print(f"    First author: {first_author}")
            if "URL" in item:
                print(f"    URL: {item.get('URL', 'N/A')[:70]}")

        # Count items without authors
        no_author = [item for item in data if not item.get("author")]
        print(f"\nItems without authors: {len(no_author)}/{len(data)}")

        # Show first no-author item
        if no_author:
            print("\nFirst item without authors:")
            print(json.dumps(no_author[0], indent=2)[:500])

except json.JSONDecodeError as e:
    print(f"JSON decode error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
