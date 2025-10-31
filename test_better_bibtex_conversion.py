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
    print("❌ ERROR: Zotero credentials not configured")
    print("   Set ZOTERO_API_KEY and ZOTERO_LIBRARY_ID in .env")
    print("   Better BibTeX mode requires Zotero API access")
    exit(1)

print(f"✅ Zotero API configured (library: {zotero_lib})")

# Run conversion
print(f"\nInput file: {INPUT_FILE}")
print(f"Output dir: {OUTPUT_DIR}")

converter = MarkdownToLatexConverter(
    output_dir=OUTPUT_DIR,
    zotero_api_key=zotero_key,
    zotero_library_id=zotero_lib,
    collection_name="dpp-fashion",  # Use existing Zotero collection
    use_better_bibtex_keys=True,  # CRITICAL: Enable Web API key mode
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

# Check key formats using the actual validation function
from src.converters.md_to_latex.utils import is_valid_zotero_key

web_api_keys = []  # Zotero Web API format: author_title_year
better_bibtex_keys = []  # Better BibTeX plugin format: authorTitleYear
legacy_zotero_keys = []  # Legacy Zotero format: authoryear or authoryearsuffix
temp_keys = []  # Temporary format: authorTempYear
invalid_keys = []  # Keys that don't match any Zotero format

for key in citation_keys:
    if "Temp" in key:
        temp_keys.append(key)
    elif not is_valid_zotero_key(key):
        invalid_keys.append(key)
    elif "_" in key:
        # Web API format has underscores
        web_api_keys.append(key)
    elif any(c.isupper() for c in key) and any(c.islower() for c in key):
        # Better BibTeX plugin format (CamelCase)
        better_bibtex_keys.append(key)
    else:
        # Legacy Zotero format (alphanumeric with year)
        legacy_zotero_keys.append(key)

print("\n" + "=" * 80)
print("Key Format Analysis")
print("=" * 80)
print(f"✅ Zotero Web API keys: {len(web_api_keys)}")
print(f"✅ Better BibTeX plugin keys: {len(better_bibtex_keys)}")
print(f"✅ Legacy Zotero keys: {len(legacy_zotero_keys)}")
print(f"⚠️  Temporary keys: {len(temp_keys)}")
print(f"❌ Invalid keys: {len(invalid_keys)}")

if web_api_keys:
    print("\nSample Web API keys (first 5):")
    for key in web_api_keys[:5]:
        print(f"  ✅ {key}")

if better_bibtex_keys:
    print("\nSample Better BibTeX plugin keys (first 5):")
    for key in better_bibtex_keys[:5]:
        print(f"  ✅ {key}")

if legacy_zotero_keys:
    print("\nSample Legacy Zotero keys (first 5):")
    for key in legacy_zotero_keys[:5]:
        print(f"  ✅ {key}")

if temp_keys:
    print("\nSample temporary keys (first 5):")
    for key in temp_keys[:5]:
        print(f"  ⚠️  {key}")

if invalid_keys:
    print("\nSample invalid keys (first 5):")
    for key in invalid_keys[:5]:
        print(f"  ❌ {key}")

# Final verdict
print("\n" + "=" * 80)
total_zotero_keys = (
    len(web_api_keys) + len(better_bibtex_keys) + len(legacy_zotero_keys)
)
if total_zotero_keys > 0 and not invalid_keys:
    print("✅ SUCCESS: All keys are from Zotero!")
    print(
        f"   {len(web_api_keys)} Web API, {len(better_bibtex_keys)} Better BibTeX, "
        f"{len(legacy_zotero_keys)} Legacy, {len(temp_keys)} temporary"
    )
elif invalid_keys:
    print("❌ FAILURE: Found invalid keys (not from Zotero)")
    print("   Zotero integration not working correctly")
else:
    print(
        "⚠️  PARTIAL: Only temporary keys (citations not in Zotero collection)"
    )
print("=" * 80)
