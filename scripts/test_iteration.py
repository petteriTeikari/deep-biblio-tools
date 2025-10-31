#!/usr/bin/env python3
"""Test if iteration over root finds all elements."""

import xml.etree.ElementTree as ET
from pathlib import Path

rdf_path = Path.home() / "Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/dpp-fashion-zotero.rdf"

tree = ET.parse(rdf_path)
root = tree.getroot()

namespaces = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "bib": "http://purl.org/net/biblio#",
    "dc": "http://purl.org/dc/elements/1.1/",
}

print(f"Total elements in root: {len(root)}")
print()

# Count by tag type
tag_counts = {}
for child in root:
    tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
    tag_counts[tag] = tag_counts.get(tag, 0) + 1

print("Element counts:")
for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1])[:20]:
    print(f"  {tag}: {count}")

print()

# Check specifically for bib:Article entries
bib_article_by_iteration = sum(1 for child in root if child.tag.split("}")[-1] == "Article")
bib_article_by_findall = len(root.findall("bib:Article", namespaces))

print(f"bib:Article found by iteration: {bib_article_by_iteration}")
print(f"bib:Article found by findall: {bib_article_by_findall}")
