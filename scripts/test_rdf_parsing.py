#!/usr/bin/env python3
"""
Test harness to verify RDF parsing correctness.

Expected: 339 entries (as counted by grep)
Actual: ??? (what the parser actually finds)

This will prove whether the RDF parser works or not.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from converters.md_to_latex.bibliography_sources import LocalFileSource


def test_rdf_parsing():
    """Test RDF parsing against actual file."""

    rdf_path = Path.home() / "Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/dpp-fashion-zotero.rdf"

    print(f"Testing RDF parser with file: {rdf_path}")
    print(f"File size: {rdf_path.stat().st_size / 1024 / 1024:.1f} MB")
    print()

    # Count expected entries using grep
    import subprocess
    result = subprocess.run(
        ["grep", "-c", '<rdf:Description rdf:about=', str(rdf_path)],
        capture_output=True,
        text=True
    )
    expected_count = int(result.stdout.strip())
    print(f"Expected entries (grep count): {expected_count}")
    print()

    # Test the parser
    try:
        source = LocalFileSource(rdf_path)
        entries = source.load_entries()

        print(f"Actual entries parsed: {len(entries)}")
        print(f"Success rate: {len(entries)}/{expected_count} ({len(entries)/expected_count*100:.1f}%)")
        print()

        if len(entries) < expected_count:
            print(f"❌ PARSER IS BROKEN!")
            print(f"   Missing {expected_count - len(entries)} entries ({(expected_count - len(entries))/expected_count*100:.1f}% failure rate)")
            print()
            print("First 5 entries found:")
            for i, entry in enumerate(entries[:5], 1):
                print(f"  {i}. {entry.get('id', 'NO_ID')}: {entry.get('title', 'NO_TITLE')[:60]}...")

            # Now let's check what structure the RDF actually uses
            print()
            print("Checking actual RDF structure...")
            import xml.etree.ElementTree as ET
            tree = ET.parse(rdf_path)
            root = tree.getroot()

            # Count rdf:Description entries
            namespaces = {
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "z": "http://www.zotero.org/namespaces/export#",
                "bib": "http://purl.org/net/biblio#",
                "dc": "http://purl.org/dc/elements/1.1/",
            }

            desc_entries = root.findall("rdf:Description", namespaces)
            print(f"rdf:Description entries: {len(desc_entries)}")

            # Check for bib:* entries (what parser looks for)
            bib_entries_count = 0
            for item_type in ["Book", "Article", "ArticleJournal", "ConferencePaper", "Thesis", "Report", "WebPage", "Document", "BookSection", "Recording", "Patent"]:
                count = len(root.findall(f"bib:{item_type}", namespaces))
                if count > 0:
                    print(f"bib:{item_type} entries: {count}")
                    bib_entries_count += count

            print(f"Total bib:* entries (what parser looks for): {bib_entries_count}")
            print()

            # Check what entries are being filtered out
            print("Analyzing filtered entries...")
            filtered_count = 0
            filtered_examples = []

            for child in root:
                title_elem = child.find("dc:title", namespaces)
                if title_elem is None or title_elem.text is None:
                    continue

                # Check if this would be filtered by our logic
                item_type_elem = child.find("z:itemType", namespaces)
                has_authors = child.find("bib:authors", namespaces) is not None
                is_bib_typed = child.tag.startswith(f"{{{namespaces['bib']}}}")

                if item_type_elem is not None:
                    item_type = item_type_elem.text or ""
                else:
                    item_type = "NONE"

                # Would this be filtered?
                is_filtered = not (has_authors or is_bib_typed or item_type in ["journalArticle", "book", "bookSection", "conferencePaper", "thesis", "report", "webpage", "preprint", "article", "patent", "document", "recording"])

                if is_filtered and len(filtered_examples) < 5:
                    filtered_examples.append({
                        "title": title_elem.text[:60],
                        "type": item_type,
                        "has_authors": has_authors,
                        "is_bib_typed": is_bib_typed,
                        "tag": child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    })
                    filtered_count += 1

            print(f"Entries being filtered out: {filtered_count}")
            if filtered_examples:
                print("Examples of filtered entries:")
                for i, ex in enumerate(filtered_examples, 1):
                    print(f"  {i}. [{ex['tag']}] {ex['title']}...")
                    print(f"     itemType={ex['type']}, has_authors={ex['has_authors']}, is_bib_typed={ex['is_bib_typed']}")

            print()
            print("DIAGNOSIS:")
            print(f"  - Parser found: {len(entries)} entries")
            print(f"  - Expected: {expected_count} entries")
            print(f"  - Filtered out: {filtered_count} entries")
            print(f"  - bib:* entries in RDF: {bib_entries_count}")

        else:
            print("✅ Parser working correctly!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_rdf_parsing()
