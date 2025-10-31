#!/usr/bin/env python3
"""Test _parse_rdf_item on bib:Article vs rdf:Description."""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from converters.md_to_latex.bibliography_sources import LocalFileSource

rdf_path = (
    Path.home()
    / "Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/dpp-fashion-zotero.rdf"
)

tree = ET.parse(rdf_path)
root = tree.getroot()

namespaces = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "bib": "http://purl.org/net/biblio#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "z": "http://www.zotero.org/namespaces/export#",
    "dcterms": "http://purl.org/dc/terms/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "link": "http://purl.org/rss/1.0/modules/link/",
}

# Create a LocalFileSource instance to access _parse_rdf_item
source = LocalFileSource(rdf_path)

# Test bib:Article
print("=" * 60)
print("Testing bib:Article entry:")
print("=" * 60)
bib_articles = root.findall("bib:Article", namespaces)
if bib_articles:
    article = bib_articles[0]
    title_elem = article.find("dc:title", namespaces)
    print(
        f"Title: {title_elem.text[:60] if title_elem is not None and title_elem.text else 'NONE'}..."
    )
    rdf_about_key = f"{{{namespaces['rdf']}}}about"
    print(f"URL: {article.get(rdf_about_key, 'NO_URL')}")
    print()

    result = source._parse_rdf_item(article, namespaces)
    if result:
        print("✅ PARSED SUCCESSFULLY!")
        print(f"   ID: {result.get('id', 'NO_ID')}")
        print(f"   Title: {result.get('title', 'NO_TITLE')[:60]}...")
        print(f"   URL: {result.get('URL', 'NO_URL')}")
        print(f"   Type: {result.get('type', 'NO_TYPE')}")
        print(f"   Authors: {len(result.get('author', []))} authors")
    else:
        print("❌ RETURNED NONE!")

print()
print("=" * 60)
print("Testing rdf:Description entry:")
print("=" * 60)
descriptions = root.findall("rdf:Description", namespaces)
if descriptions:
    desc = descriptions[0]
    title_elem = desc.find("dc:title", namespaces)
    print(
        f"Title: {title_elem.text[:60] if title_elem is not None and title_elem.text else 'NONE'}..."
    )
    print(f"URL: {desc.get(rdf_about_key, 'NO_URL')}")
    print()

    result = source._parse_rdf_item(desc, namespaces)
    if result:
        print("✅ PARSED SUCCESSFULLY!")
        print(f"   ID: {result.get('id', 'NO_ID')}")
        print(f"   Title: {result.get('title', 'NO_TITLE')[:60]}...")
        print(f"   URL: {result.get('URL', 'NO_URL')}")
        print(f"   Type: {result.get('type', 'NO_TYPE')}")
        print(f"   Authors: {len(result.get('author', []))} authors")
    else:
        print("❌ RETURNED NONE!")
