#!/usr/bin/env python3
"""Test Better BibTeX key integration with real conversion."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from src.converters.md_to_latex import MarkdownToLatexConverter

# Input and output paths
INPUT_FILE = Path(
    "/home/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/mcp-draft-refined-v4.md"
)
OUTPUT_DIR = Path(
    "/home/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/latex_output"
)

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("Testing Better BibTeX Key Integration")
print("=" * 80)

# Check if Zotero credentials are configured
zotero_key = os.getenv("ZOTERO_API_KEY")
zotero_lib = os.getenv("ZOTERO_LIBRARY_ID")

if not zotero_key or not zotero_lib:
    print("⚠️  WARNING: Zotero credentials not configured")
    print("   Set ZOTERO_API_KEY and ZOTERO_LIBRARY_ID in .env")
    print("   Conversion will use temporary keys only")
else:
    print(f"✅ Zotero API configured (library: {zotero_lib})")

# Run conversion
print(f"\nInput file: {INPUT_FILE}")
print(f"Output dir: {OUTPUT_DIR}")

converter = MarkdownToLatexConverter(
    output_dir=OUTPUT_DIR,
    zotero_api_key=zotero_key,
    zotero_library_id=zotero_lib,
    collection_name="dpp-fashion",  # Use existing Zotero collection
)

print("\nRunning conversion...")
try:
    converter.convert(markdown_file=INPUT_FILE, verbose=True)
    print("\n✅ Conversion completed successfully!")
except Exception as e:
    print(f"\n❌ Conversion failed: {e}")
    import traceback

    traceback.print_exc()
    exit(1)

# Check the bibliography
bib_file = OUTPUT_DIR / "references.bib"
if not bib_file.exists():
    print(f"\n❌ Bibliography file not found: {bib_file}")
    exit(1)

print(f"\n📖 Checking bibliography: {bib_file}")
bib_content = bib_file.read_text()

# Count citation keys
import re

# No regex! Use string methods
lines = bib_content.split("\n")
citation_keys = []
for line in lines:
    if line.startswith("@"):
        # Extract key from @article{key,
        start = line.find("{")
        end = line.find(",", start)
        if start > 0 and end > start:
            key = line[start + 1 : end]
            citation_keys.append(key)

print(f"\nFound {len(citation_keys)} citation entries")

# Check key formats
better_bibtex_keys = []
short_keys = []
temp_keys = []

for key in citation_keys:
    if "Temp" in key:
        temp_keys.append(key)
    elif len(key) >= 15 and any(c.isupper() for c in key[:-4]):
        better_bibtex_keys.append(key)
    else:
        short_keys.append(key)

print("\n" + "=" * 80)
print("Key Format Analysis")
print("=" * 80)
print(f"✅ Better BibTeX keys: {len(better_bibtex_keys)}")
print(f"⚠️  Temporary keys: {len(temp_keys)}")
print(f"❌ Short keys (old format): {len(short_keys)}")

if better_bibtex_keys:
    print("\nSample Better BibTeX keys (first 5):")
    for key in better_bibtex_keys[:5]:
        print(f"  ✅ {key}")

if temp_keys:
    print("\nSample temporary keys (first 5):")
    for key in temp_keys[:5]:
        print(f"  ⚠️  {key}")

if short_keys:
    print("\nSample short keys (first 5):")
    for key in short_keys[:5]:
        print(f"  ❌ {key}")

# Final verdict
print("\n" + "=" * 80)
if better_bibtex_keys and not short_keys:
    print("✅ SUCCESS: All keys are Better BibTeX format!")
    print(
        f"   {len(better_bibtex_keys)} from Zotero, {len(temp_keys)} temporary"
    )
elif short_keys:
    print("❌ FAILURE: Found short keys (old format)")
    print("   Better BibTeX integration not working correctly")
else:
    print(
        "⚠️  PARTIAL: Only temporary keys (Zotero not configured or citations not in collection)"
    )
print("=" * 80)
