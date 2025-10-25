#!/usr/bin/env python3
"""Test the manuscript-to-arXiv converter."""

import sys
from pathlib import Path

# Add module to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from deep_biblio.arxiv_converter import create_arxiv_package

# Test with actual files
MANUSCRIPT_PATH = "/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/paper-manuscripts/mcp-review/mcp-draft-refined-v3-1.md"
ZOTERO_JSON_PATH = "/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/paper-manuscripts/mcp-review/dpp-fashion.json"
OUTPUT_DIR = "/Users/petteri/Dropbox/LABs/open-mode/github/dpp-fashion/mcp-servers/deep-biblio/test_output"

print("Testing manuscript-to-arXiv converter...\n")

result = create_arxiv_package(
    markdown_path=MANUSCRIPT_PATH,
    zotero_json_path=ZOTERO_JSON_PATH,
    output_dir=OUTPUT_DIR,
    author="Petteri Teikari",
    single_column=False,
)

print("\n" + "=" * 60)
print("RESULTS")
print("=" * 60)
print("\n[STATS] Citation Statistics:")
print(f"  - Total citations found: {result['total_citations']}")
print(f"  - Matched in Zotero: {result['matched_count']}")
print(f"  - Missing from Zotero: {result['missing_count']}")
print(
    f"  - Match rate: {result['matched_count'] / result['total_citations'] * 100:.1f}%"
)

print("\n[FILE] Generated Files:")
print(f"  - BibTeX: {result['bibtex_path']}")

if result["missing_citations"]:
    print(f"\n[WARNING]  Missing Citations ({len(result['missing_citations'])}):\n")
    for i, cite in enumerate(result["missing_citations"][:10], 1):
        print(f"{i}. {cite['author']}, {cite['year']}")
        print(f"   URL: {cite['url']}")
        print(f"   Line: {cite['line_number']}\n")

    if len(result["missing_citations"]) > 10:
        print(f"... and {len(result['missing_citations']) - 10} more")

print("\n" + "=" * 60)
print("[PASS] Test complete!")
print("=" * 60)
