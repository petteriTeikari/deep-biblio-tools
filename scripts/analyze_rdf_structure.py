#!/usr/bin/env python3
"""
Analyze RDF structure to understand why only 313/665 entries are loading.
"""

import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

rdf_path = Path(
    "/home/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/dpp-fashion-zotero.rdf"
)

print(f"Analyzing RDF: {rdf_path}\n")

tree = ET.parse(rdf_path)
root = tree.getroot()

# Namespaces
ns = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "bib": "http://purl.org/net/biblio#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "z": "http://www.zotero.org/namespaces/export#",
}

# Count all bibliographic item types
print("📊 Counting all bib:* elements in RDF...")
all_bib_elements = root.findall(
    ".//*[@{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about]", ns
)
print(f"Total elements with rdf:about: {len(all_bib_elements)}\n")

# Count by tag name
tag_counter = Counter()
for elem in all_bib_elements:
    tag_name = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
    tag_counter[tag_name] += 1

print("Element types found:")
for tag, count in sorted(tag_counter.items(), key=lambda x: -x[1]):
    print(f"  {tag}: {count}")

# Check what the parser is looking for
parser_types = [
    "Book",
    "Article",
    "ArticleJournal",
    "ConferencePaper",
    "Thesis",
    "Report",
    "WebPage",
    "Document",
]
print("\n📋 Parser looks for these types:")
for t in parser_types:
    print(f"  bib:{t}")

# Count what parser would find
parser_would_find = 0
for t in parser_types:
    count = len(root.findall(f"bib:{t}", ns))
    if count > 0:
        print(f"    ✓ Found {count} bib:{t}")
        parser_would_find += count
    else:
        print(f"    ✗ Found 0 bib:{t}")

print(f"\n Total parser would find: {parser_would_find}")

# Check for entries without titles
print("\n🔍 Checking for entries without titles...")
entries_without_title = 0
for t in parser_types:
    for item in root.findall(f"bib:{t}", ns):
        title_elem = item.find("dc:title", ns)
        if title_elem is None or not title_elem.text:
            entries_without_title += 1
            url = item.get(f"{{{ns['rdf']}}}about", "NO_URL")[:80]
            print(f"  ✗ No title: {url}")

print(f"\nEntries without title (would be skipped): {entries_without_title}")
print(f"Expected loaded: {parser_would_find - entries_without_title}")

# Look for other common Zotero types that might be missing
print("\n🔍 Looking for other possible bibliographic types...")
other_possible_types = [
    "BookSection",
    "JournalArticle",
    "Preprint",
    "BlogPost",
    "ForumPost",
    "Presentation",
    "Patent",
]
for t in other_possible_types:
    count = len(root.findall(f"bib:{t}", ns))
    if count > 0:
        print(f"  ! Found {count} bib:{t} (NOT in parser list!)")
