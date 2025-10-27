"""Audit Zotero collection for data quality issues.

Checks for:
- Entries with missing titles
- Entries with generic/placeholder authors
- Duplicate entries (same title/DOI)
- Web page entries without proper metadata
- Organizational authors incorrectly formatted
"""

import os
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from pyzotero import zotero

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

load_dotenv()


def audit_collection(collection_name: str = "dpp-fashion") -> dict:
    """Audit Zotero collection for quality issues.

    Returns:
        Dictionary with lists of problematic entries
    """
    # Initialize Zotero client
    library_id = os.getenv("ZOTERO_LIBRARY_ID")
    api_key = os.getenv("ZOTERO_API_KEY")
    library_type = os.getenv("ZOTERO_LIBRARY_TYPE", "user")

    if not library_id or not api_key:
        print("ERROR: Missing ZOTERO_LIBRARY_ID or ZOTERO_API_KEY")
        sys.exit(1)

    zot = zotero.Zotero(library_id, library_type, api_key)

    # Get collection
    collections = zot.collections()
    collection_id = None
    for coll in collections:
        if coll["data"]["name"] == collection_name:
            collection_id = coll["key"]
            break

    if not collection_id:
        print(f"ERROR: Collection '{collection_name}' not found")
        sys.exit(1)

    # Fetch all items
    items = zot.collection_items(collection_id)

    print(f"\n{'=' * 80}")
    print(f"ZOTERO COLLECTION AUDIT: {collection_name}")
    print(f"{'=' * 80}\n")
    print(f"Total items: {len(items)}\n")

    # Track issues
    issues = {
        "missing_title": [],
        "missing_author": [],
        "web_page_no_title": [],
        "generic_author": [],
        "duplicates": [],
        "org_author_issues": [],
    }

    # Track for duplicates
    titles_seen = defaultdict(list)
    dois_seen = defaultdict(list)

    for item in items:
        data = item["data"]
        item_type = data.get("itemType", "")
        title = data.get("title", "").strip()
        doi = data.get("DOI", "").strip()
        url = data.get("url", "").strip()

        # Get authors/creators
        creators = data.get("creators", [])
        author_names = []
        for creator in creators:
            if "lastName" in creator:
                author_names.append(
                    f"{creator.get('firstName', '')} {creator['lastName']}"
                )
            elif "name" in creator:
                author_names.append(creator["name"])

        # Issue 1: Missing title
        if not title or title.lower() in ["untitled", "no title", "n/a"]:
            issues["missing_title"].append(
                {
                    "key": item["key"],
                    "type": item_type,
                    "title": title,
                    "url": url,
                    "authors": author_names,
                }
            )

        # Issue 2: Missing author
        if not author_names:
            issues["missing_author"].append(
                {
                    "key": item["key"],
                    "type": item_type,
                    "title": title,
                    "url": url,
                }
            )

        # Issue 3: Web page with no title
        if item_type == "webpage" and not title:
            issues["web_page_no_title"].append(
                {
                    "key": item["key"],
                    "url": url,
                    "authors": author_names,
                }
            )

        # Issue 4: Generic/placeholder authors
        generic_patterns = ["et al", "unknown", "anonymous", "various", "n/a"]
        for author in author_names:
            author_lower = author.lower()
            if any(pattern in author_lower for pattern in generic_patterns):
                issues["generic_author"].append(
                    {
                        "key": item["key"],
                        "title": title,
                        "author": author,
                    }
                )

        # Issue 5: Check for duplicates by title
        if title:
            titles_seen[title.lower()].append(
                {
                    "key": item["key"],
                    "title": title,
                    "authors": author_names,
                    "year": data.get("date", "")[:4],
                }
            )

        # Issue 6: Check for duplicates by DOI
        if doi:
            dois_seen[doi.lower()].append(
                {
                    "key": item["key"],
                    "title": title,
                    "doi": doi,
                }
            )

        # Issue 7: Organizational authors that might be mis-parsed
        org_keywords = [
            "commission",
            "regulation",
            "directive",
            "agency",
            "parliament",
            "council",
        ]
        for author in author_names:
            if any(keyword in author.lower() for keyword in org_keywords):
                issues["org_author_issues"].append(
                    {
                        "key": item["key"],
                        "title": title,
                        "author": author,
                        "type": item_type,
                    }
                )

    # Find duplicates
    for title, entries in titles_seen.items():
        if len(entries) > 1:
            issues["duplicates"].append(
                {
                    "title": title,
                    "entries": entries,
                }
            )

    # Print report
    print(f"\n{'=' * 80}")
    print("ISSUES FOUND")
    print(f"{'=' * 80}\n")

    if issues["missing_title"]:
        print(f"\nMISSING TITLE ({len(issues['missing_title'])} items):")
        for item in issues["missing_title"]:
            print(f"  - Key: {item['key']}")
            print(f"    Type: {item['type']}")
            print(f"    Title: '{item['title']}'")
            print(
                f"    Authors: {', '.join(item['authors']) if item['authors'] else 'NONE'}"
            )
            print(f"    URL: {item['url'][:80] if item['url'] else 'NONE'}")
            print()

    if issues["web_page_no_title"]:
        print(
            f"\nWEB PAGE WITH NO TITLE ({len(issues['web_page_no_title'])} items):"
        )
        for item in issues["web_page_no_title"]:
            print(f"  - Key: {item['key']}")
            print(
                f"    Authors: {', '.join(item['authors']) if item['authors'] else 'NONE'}"
            )
            print(f"    URL: {item['url'][:80]}")
            print()

    if issues["missing_author"]:
        print(f"\nMISSING AUTHOR ({len(issues['missing_author'])} items):")
        for item in issues["missing_author"]:
            print(f"  - Key: {item['key']}")
            print(f"    Title: {item['title'][:60]}")
            print()

    if issues["generic_author"]:
        print(
            f"\nGENERIC/PLACEHOLDER AUTHOR ({len(issues['generic_author'])} items):"
        )
        for item in issues["generic_author"]:
            print(f"  - Key: {item['key']}")
            print(f"    Title: {item['title'][:60]}")
            print(f"    Author: {item['author']}")
            print()

    if issues["duplicates"]:
        print(f"\nDUPLICATE ENTRIES ({len(issues['duplicates'])} sets):")
        for dup in issues["duplicates"]:
            print(f"\n  Title: {dup['title'][:60]}")
            for entry in dup["entries"]:
                print(
                    f"    - Key: {entry['key']}, Year: {entry['year']}, Authors: {', '.join(entry['authors'][:2])}"
                )
            print()

    if issues["org_author_issues"]:
        print(
            f"\nORGANIZATIONAL AUTHOR ISSUES ({len(issues['org_author_issues'])} items):"
        )
        for item in issues["org_author_issues"]:
            print(f"  - Key: {item['key']}")
            print(f"    Title: {item['title'][:60]}")
            print(f"    Author: {item['author']}")
            print(f"    Type: {item['type']}")
            print()

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}\n")
    total_issues = sum(
        len(v) if not k == "duplicates" else len(v) for k, v in issues.items()
    )
    print(f"Total issues found: {total_issues}")
    print(f"  - Missing titles: {len(issues['missing_title'])}")
    print(f"  - Web pages without titles: {len(issues['web_page_no_title'])}")
    print(f"  - Missing authors: {len(issues['missing_author'])}")
    print(f"  - Generic authors: {len(issues['generic_author'])}")
    print(f"  - Duplicate entries: {len(issues['duplicates'])}")
    print(
        f"  - Organizational author issues: {len(issues['org_author_issues'])}"
    )
    print()

    return issues


if __name__ == "__main__":
    audit_collection()
