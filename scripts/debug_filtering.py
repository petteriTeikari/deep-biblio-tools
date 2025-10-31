#!/usr/bin/env python3
"""Debug why bib:Article entries are being filtered out."""

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

# Find first bib:Article entry
bib_articles = root.findall("bib:Article", namespaces)
if bib_articles:
    article = bib_articles[0]
    print("Testing first bib:Article entry:")
    print(f"  Tag: {article.tag}")
    print()

    # Test all filters
    tag_name = article.tag.split("}")[-1]
    print(f"1. Tag name: {tag_name}")
    print(f"   Is excluded? {tag_name in excluded_bib_tags}")
    print()

    title_elem = article.find("dc:title", namespaces)
    title_text = title_elem.text if title_elem is not None else None
    print(f"2. Title: {title_text[:60] if title_text else 'NONE'}...")
    print(f"   Has title elem? {title_elem is not None}")
    print(f"   Has title text? {bool(title_text)}")
    print()

    item_type_elem = article.find("z:itemType", namespaces)
    item_type = item_type_elem.text if item_type_elem is not None else None
    print(f"3. Item type: {item_type}")
    print(f"   In valid types? {item_type in valid_item_types if item_type else 'N/A'}")
    has_valid_item_type = item_type in valid_item_types if item_type else False
    print(f"   has_valid_item_type = {has_valid_item_type}")
    print()

    has_authors = article.find("bib:authors", namespaces) is not None
    print(f"4. has_authors = {has_authors}")

    is_bib_typed = article.tag.startswith(f"{{{namespaces['bib']}}}")
    print(f"5. is_bib_typed = {is_bib_typed}")
    print(f"   Tag starts with: {article.tag[:50]}...")
    print(f"   Expected prefix: {namespaces['bib']}")
    print()

    passes_check3 = has_authors or has_valid_item_type or is_bib_typed
    print(f"6. Passes check #3? {passes_check3}")
    print(f"   (has_authors={has_authors} OR has_valid_item_type={has_valid_item_type} OR is_bib_typed={is_bib_typed})")
    print()

    url = article.get(f"{{{namespaces['rdf']}}}about", "")
    print(f"7. URL: {url}")
    print()

    print("=" * 60)
    print(f"SHOULD THIS ENTRY BE PARSED? {not tag_name in excluded_bib_tags and title_text and passes_check3}")
