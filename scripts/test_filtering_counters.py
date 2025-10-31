#!/usr/bin/env python3
"""Track exactly where entries are being filtered."""

import xml.etree.ElementTree as ET
from pathlib import Path

rdf_path = Path.home() / "Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/dpp-fashion-zotero.rdf"

tree = ET.parse(rdf_path)
root = tree.getroot()

namespaces = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "bib": "http://purl.org/net/biblio#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "z": "http://www.zotero.org/namespaces/export#",
}

valid_item_types = {
    "journalArticle", "book", "bookSection", "conferencePaper",
    "thesis", "report", "webpage", "preprint", "article",
    "patent", "document", "recording",
}

excluded_bib_tags = {"Journal", "Series", "Periodical"}

total_children = 0
filtered_by_metadata = 0
filtered_by_no_title = 0
filtered_by_invalid_itemtype = 0
filtered_by_check3 = 0
would_be_parsed = 0

for child in root:
    total_children += 1

    # Check metadata exclusion
    if child.tag.startswith(f"{{{namespaces['bib']}}}"):
        tag_name = child.tag.split("}")[-1]
        if tag_name in excluded_bib_tags:
            filtered_by_metadata += 1
            continue

    # Check title
    title_elem = child.find("dc:title", namespaces)
    if title_elem is None or not title_elem.text:
        filtered_by_no_title += 1
        continue

    # Check item type
    item_type_elem = child.find("z:itemType", namespaces)
    has_valid_item_type = False
    if item_type_elem is not None:
        item_type = item_type_elem.text or ""
        if item_type.lower() not in valid_item_types:
            filtered_by_invalid_itemtype += 1
            continue
        has_valid_item_type = True

    # Check #3
    has_authors = child.find("bib:authors", namespaces) is not None
    is_bib_typed = child.tag.startswith(f"{{{namespaces['bib']}}}")

    if not (has_authors or has_valid_item_type or is_bib_typed):
        filtered_by_check3 += 1
        continue

    would_be_parsed += 1

print(f"Total children in root: {total_children}")
print(f"Filtered by metadata (Journal, etc.): {filtered_by_metadata}")
print(f"Filtered by no/empty title: {filtered_by_no_title}")
print(f"Filtered by invalid itemType: {filtered_by_invalid_itemtype}")
print(f"Filtered by check #3 (no authors/itemtype/bibtyped): {filtered_by_check3}")
print(f"Would be parsed: {would_be_parsed}")
print()
print(f"Total filtered: {filtered_by_metadata + filtered_by_no_title + filtered_by_invalid_itemtype + filtered_by_check3}")
print(f"Expected: {total_children - would_be_parsed}")
