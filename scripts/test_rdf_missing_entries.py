#!/usr/bin/env python3
"""
Find which specific entries the RDF parser is missing.
Compare what ElementTree iteration finds vs what the parser returns.
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from converters.md_to_latex.bibliography_sources import LocalFileSource


def test_missing_entries():
    """Find which entries are being missed."""

    rdf_path = (
        Path.home()
        / "Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/dpp-fashion-zotero.rdf"
    )

    print("Analyzing missing RDF entries...")
    print()

    # Parse with our parser
    source = LocalFileSource(rdf_path)
    parsed_entries = source.load_entries()
    parsed_urls = {
        entry.get("URL", "") for entry in parsed_entries if entry.get("URL")
    }

    print(f"Parser found: {len(parsed_entries)} entries")
    print(f"With URLs: {len(parsed_urls)}")
    print()

    # Parse directly with ElementTree to find all bib:* entries
    tree = ET.parse(rdf_path)
    root = tree.getroot()

    namespaces = {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "bib": "http://purl.org/net/biblio#",
        "dc": "http://purl.org/dc/elements/1.1/",
        "z": "http://www.zotero.org/namespaces/export#",
    }

    # Find all bib:* entries
    all_bib_entries = []
    for item_type in [
        "Book",
        "Article",
        "Thesis",
        "Report",
        "Document",
        "BookSection",
        "Recording",
        "Patent",
    ]:
        for item in root.findall(f"bib:{item_type}", namespaces):
            item_url = item.get(f"{{{namespaces['rdf']}}}about", "")
            title_elem = item.find("dc:title", namespaces)
            title = title_elem.text if title_elem is not None else ""

            all_bib_entries.append(
                {
                    "url": item_url,
                    "title": title,
                    "type": item_type,
                }
            )

    print(f"Total bib:* entries in RDF: {len(all_bib_entries)}")
    print()

    # Find missing entries
    missing = []
    for entry in all_bib_entries:
        if entry["url"] not in parsed_urls:
            missing.append(entry)

    if missing:
        print(f"❌ Missing {len(missing)} bib:* entries:")
        for i, entry in enumerate(missing[:10], 1):
            print(f"  {i}. [{entry['type']}] {entry['title'][:60]}...")
            print(f"     URL: {entry['url'][:80]}...")
    else:
        print("✅ All bib:* entries parsed successfully!")

    # Also check rdf:Description entries
    all_desc_entries = []
    for desc in root.findall("rdf:Description", namespaces):
        item_url = desc.get(f"{{{namespaces['rdf']}}}about", "")
        title_elem = desc.find("dc:title", namespaces)
        title = title_elem.text if title_elem is not None else ""

        if title:  # Only count those with titles
            all_desc_entries.append(
                {
                    "url": item_url,
                    "title": title,
                }
            )

    print()
    print(f"rdf:Description entries with titles: {len(all_desc_entries)}")

    # Find rdf:Description entries NOT in bib:* set
    bib_urls = {e["url"] for e in all_bib_entries}
    desc_only = [e for e in all_desc_entries if e["url"] not in bib_urls]

    if desc_only:
        print(f"rdf:Description ONLY entries (not in bib:*): {len(desc_only)}")
        for i, entry in enumerate(desc_only[:5], 1):
            print(f"  {i}. {entry['title'][:60]}...")
            print(f"     URL: {entry['url'][:80]}...")


if __name__ == "__main__":
    test_missing_entries()
