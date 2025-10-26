#!/usr/bin/env python3
"""Test Zotero API collection loading."""

import logging
import sys
import traceback
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.converters.md_to_latex.zotero_integration import ZoteroClient

load_dotenv()

logging.basicConfig(level=logging.INFO)


def main():
    """Test loading dpp-fashion collection from Zotero API."""
    print("Initializing Zotero client...")
    client = ZoteroClient()

    print(
        f"API Key: {client.api_key[:10]}..." if client.api_key else "No API key"
    )
    print(f"Library ID: {client.library_id}")
    print(f"Library Type: {client.library_type}")

    collection_name = "dpp-fashion"
    print(f"\nLoading collection: {collection_name}")

    try:
        items = client.get_collection_items(collection_name)
        print(f"\nSuccess! Loaded {len(items)} items")

        if items:
            print("\nFirst 3 items:")
            for i, item in enumerate(items[:3], 1):
                title = item.get("title", "No title")[:60]
                authors = item.get("author", [])
                author_names = []
                for author in authors[:2]:
                    if isinstance(author, dict):
                        family = author.get("family", "")
                        given = author.get("given", "")
                        if family:
                            author_names.append(f"{given} {family}".strip())
                author_str = (
                    ", ".join(author_names) if author_names else "No authors"
                )
                print(f"{i}. {title}")
                print(f"   Authors: {author_str}")
                print(f"   Type: {item.get('type', 'unknown')}")
                print(f"   URL: {item.get('URL', 'No URL')[:50]}")
                print()

    except Exception as e:
        print(f"\nERROR: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
