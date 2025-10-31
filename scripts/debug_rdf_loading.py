#!/usr/bin/env python3
"""
Debug script to verify RDF loading and CitationMatcher indexing.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.converters.md_to_latex.bibliography_sources import LocalFileSource
from src.converters.md_to_latex.citation_matcher import CitationMatcher

# Load RDF
rdf_path = Path("/home/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/dpp-fashion-zotero.rdf")

print(f"Loading RDF from: {rdf_path}")
source = LocalFileSource(rdf_path)
entries = source.load_entries()

print(f"\n✓ Loaded {len(entries)} entries from RDF")

# Check how many have 'id' fields
entries_with_id = [e for e in entries if e.get("id")]
print(f"✓ Entries with 'id' field: {len(entries_with_id)}/{len(entries)}")

# Check how many have URL fields
entries_with_url = [e for e in entries if e.get("URL")]
print(f"✓ Entries with 'URL' field: {len(entries_with_url)}/{len(entries)}")

# Check how many have DOI fields
entries_with_doi = [e for e in entries if e.get("DOI")]
print(f"✓ Entries with 'DOI' field: {len(entries_with_doi)}/{len(entries)}")

# Show first 3 entries
print(f"\n📋 Sample entries:")
for i, entry in enumerate(entries[:3]):
    print(f"\nEntry {i+1}:")
    print(f"  id: {entry.get('id', 'MISSING')}")
    print(f"  title: {entry.get('title', 'MISSING')[:60]}")
    print(f"  URL: {entry.get('URL', 'MISSING')[:80]}")
    print(f"  DOI: {entry.get('DOI', 'MISSING')}")
    print(f"  type: {entry.get('type', 'MISSING')}")

# Initialize CitationMatcher
print(f"\n🔍 Initializing CitationMatcher...")
matcher = CitationMatcher(entries, allow_zotero_write=False)

# Print index statistics
print(f"\n📊 Index Statistics:")
print(f"  DOI index: {len(matcher.doi_index)} entries")
print(f"  ISBN index: {len(matcher.isbn_index)} entries")
print(f"  arXiv index: {len(matcher.arxiv_index)} entries")
print(f"  URL index: {len(matcher.url_index)} entries")

# Test matching a known arXiv paper
test_urls = [
    "https://arxiv.org/abs/2509.25370",
    "https://arxiv.org/abs/2503.13657",
    "https://doi.org/10.1007/978-3-031-70262-4_5",
]

print(f"\n🧪 Testing matches:")
for url in test_urls:
    entry, strategy = matcher.match(url)
    if entry:
        print(f"  ✓ {url}")
        print(f"    Strategy: {strategy}")
        print(f"    Title: {entry.get('title', 'NO_TITLE')[:60]}")
        print(f"    Has 'id': {bool(entry.get('id'))}")
    else:
        print(f"  ✗ {url} - NO MATCH")
