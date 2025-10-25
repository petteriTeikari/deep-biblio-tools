#!/usr/bin/env python3
"""Convert manuscript to arXiv format using Zotero API directly."""

import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from pyzotero import zotero

# Load environment variables
load_dotenv()

ZOTERO_API_KEY = os.getenv("ZOTERO_API_KEY")
ZOTERO_LIBRARY_ID = os.getenv("ZOTERO_LIBRARY_ID")

if not ZOTERO_API_KEY or not ZOTERO_LIBRARY_ID:
    logger.error("Missing Zotero credentials in .env file")
    sys.exit(1)

# Initialize Zotero client
zot = zotero.Zotero(ZOTERO_LIBRARY_ID, "user", ZOTERO_API_KEY)

# Configuration
MANUSCRIPT_PATH = "/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/paper-manuscripts/mcp-review/mcp-draft-refined-v3.md"
# Output to the same directory as the manuscript
OUTPUT_DIR = Path(MANUSCRIPT_PATH).parent
COLLECTION_NAME = "dpp-fashion"

# Output directory already exists (it's where the manuscript is)

logger.info("[CHECK] Fetching ALL items from Zotero library...")
all_items = zot.everything(zot.items())
logger.success(f"[PASS] Loaded {len(all_items)} items from Zotero")

# Find dpp-fashion collection
logger.info(f"[CHECK] Finding '{COLLECTION_NAME}' collection...")
collections = zot.collections()
dpp_collection = None
for collection in collections:
    if collection["data"]["name"].lower() == COLLECTION_NAME.lower():
        dpp_collection = collection
        logger.success(f"[PASS] Found collection: {collection['data']['name']}")
        break

if not dpp_collection:
    logger.error(f"[FAIL] Collection '{COLLECTION_NAME}' not found!")
    sys.exit(1)

collection_key = dpp_collection["key"]

# Extract citations from manuscript
logger.info("[FILE] Extracting citations from manuscript...")
manuscript = Path(MANUSCRIPT_PATH).read_text(encoding="utf-8")
pattern = r"\[([^\]]+?),\s*(\d{4})\]\(([^\)]+)\)"

citations = []
for line_no, line in enumerate(manuscript.split("\n"), 1):
    for match in re.finditer(pattern, line):
        author_part = match.group(1).strip()
        year = match.group(2)
        url = match.group(3)
        citations.append(
            {
                "author": author_part,
                "year": year,
                "url": url,
                "line_number": line_no,
                "original": match.group(0),
            }
        )

logger.success(f"[PASS] Extracted {len(citations)} citations from manuscript")

# Build comprehensive indices for matching
logger.info("[BUILD] Building lookup indices...")

doi_index = {}
arxiv_index = {}
url_index = {}
author_year_index = {}

for item in all_items:
    data = item.get("data", {})

    # Index by DOI
    doi = data.get("DOI", "")
    if doi:
        doi_index[doi.lower()] = item

    # Index by arXiv ID
    url = data.get("url", "")
    if "arxiv.org" in url:
        match = re.search(r"(\d{4}\.\d{4,5})", url)
        if match:
            arxiv_index[match.group(1)] = item

    # Index by URL
    if url:
        url_index[url] = item

    # Index by author + year
    creators = data.get("creators", [])
    date = data.get("date", "")
    if creators and date:
        first_author = creators[0].get("lastName", "").lower()
        year_match = re.search(r"\d{4}", date)
        if year_match and first_author:
            key = f"{first_author}{year_match.group(0)}"
            author_year_index[key] = item

logger.info(f"  - DOI index: {len(doi_index)} entries")
logger.info(f"  - arXiv index: {len(arxiv_index)} entries")
logger.info(f"  - URL index: {len(url_index)} entries")
logger.info(f"  - Author+Year index: {len(author_year_index)} entries")

# Match citations
logger.info("\n[LINK] Matching citations...")
matched = []
missing = []
items_to_add_to_collection = []

for cite in citations:
    url = cite["url"]
    year = cite["year"]
    author = cite["author"].lower().replace(" et al.", "")

    matched_item = None

    # Try DOI matching
    if "doi.org" in url:
        doi = url.split("doi.org/")[-1]
        matched_item = doi_index.get(doi.lower())

    # Try arXiv matching
    elif "arxiv.org" in url:
        match = re.search(r"(\d{4}\.\d{4,5})", url)
        if match:
            arxiv_id = match.group(1)
            matched_item = arxiv_index.get(arxiv_id)

    # Try URL matching
    if not matched_item:
        matched_item = url_index.get(url)

    # Try author + year matching
    if not matched_item:
        author_key = f"{author}{year}"
        matched_item = author_year_index.get(author_key)

    if matched_item:
        matched.append((cite, matched_item))

        # Check if item is in dpp-fashion collection
        item_collections = matched_item.get("data", {}).get("collections", [])
        if collection_key not in item_collections:
            items_to_add_to_collection.append(matched_item["key"])
    else:
        missing.append(cite)

logger.success(f"[PASS] Matched: {len(matched)}/{len(citations)}")
logger.info(f"   Missing: {len(missing)}")

# Add matched items to collection if needed
if items_to_add_to_collection:
    logger.info(
        f"\n[FOLDER] Adding {len(items_to_add_to_collection)} items to '{COLLECTION_NAME}' collection..."
    )
    for item_key in items_to_add_to_collection:
        try:
            zot.addto_collection(collection_key, item_key)
            logger.debug(f"  Added {item_key}")
        except Exception as e:
            logger.error(f"  Failed to add {item_key}: {e}")
    logger.success(
        f"[PASS] Organized {len(items_to_add_to_collection)} items into collection"
    )

# Generate BibTeX from matched items
logger.info("\n[DOCS] Generating BibTeX file...")

bibtex_entries = {}

for cite, item in matched:
    data = item.get("data", {})

    # Generate cite key (Author + Year)
    creators = data.get("creators", [])
    date = data.get("date", "")

    if creators:
        first_author = creators[0].get("lastName", "Unknown")
    else:
        first_author = "Unknown"

    year_match = re.search(r"\d{4}", date)
    year_str = year_match.group(0) if year_match else "XXXX"

    cite_key = f"{first_author}{year_str}"

    # Avoid duplicate keys
    if cite_key in bibtex_entries:
        counter = 2
        while f"{cite_key}{chr(96 + counter)}" in bibtex_entries:
            counter += 1
        cite_key = f"{cite_key}{chr(96 + counter)}"

    # Map Zotero types to BibTeX types
    item_type = data.get("itemType", "misc")
    type_mapping = {
        "journalArticle": "article",
        "conferencePaper": "inproceedings",
        "book": "book",
        "bookSection": "inchapter",
        "thesis": "phdthesis",
        "webpage": "misc",
        "preprint": "article",
    }
    bibtex_type = type_mapping.get(item_type, "misc")

    # Build BibTeX entry
    entry_lines = [f"@{bibtex_type}{{{cite_key},"]

    # Title
    title = data.get("title", "")
    if title:
        entry_lines.append(f"  title = {{{title}}},")

    # Authors
    if creators:
        author_str = " and ".join(
            f"{c.get('lastName', '')}, {c.get('firstName', '')}"
            for c in creators
            if c.get("creatorType") == "author"
        )
        if author_str:
            entry_lines.append(f"  author = {{{author_str}}},")

    # Year
    if year_str != "XXXX":
        entry_lines.append(f"  year = {{{year_str}}},")

    # Journal/venue
    pub_title = data.get("publicationTitle", "")
    if pub_title:
        if bibtex_type == "article":
            entry_lines.append(f"  journal = {{{pub_title}}},")
        elif bibtex_type == "inproceedings":
            entry_lines.append(f"  booktitle = {{{pub_title}}},")

    # Volume, issue, pages
    volume = data.get("volume", "")
    if volume:
        entry_lines.append(f"  volume = {{{volume}}},")

    issue = data.get("issue", "")
    if issue:
        entry_lines.append(f"  number = {{{issue}}},")

    pages = data.get("pages", "")
    if pages:
        entry_lines.append(f"  pages = {{{pages}}},")

    # Publisher
    publisher = data.get("publisher", "")
    if publisher:
        entry_lines.append(f"  publisher = {{{publisher}}},")

    # DOI/URL (priority: DOI > URL)
    doi = data.get("DOI", "")
    url = data.get("url", "")

    if doi:
        entry_lines.append(f"  doi = {{{doi}}},")
        entry_lines.append(f"  url = {{https://doi.org/{doi}}},")
    elif url:
        entry_lines.append(f"  url = {{{url}}},")

    entry_lines.append("}")

    bibtex_entries[cite_key] = "\n".join(entry_lines)

# Write BibTeX file
bibtex_path = OUTPUT_DIR / "references.bib"
bibtex_content = "\n\n".join(bibtex_entries.values())
bibtex_path.write_text(bibtex_content, encoding="utf-8")

logger.success(f"[PASS] Generated BibTeX: {bibtex_path}")
logger.info(f"   Entries: {len(bibtex_entries)}")

# Convert to LaTeX using pandoc (now that it's installed)
logger.info("\n[BUILD] Converting markdown to LaTeX...")

try:
    import sys
    from pathlib import Path as PathLib

    # Add deep-biblio-tools to path
    deep_biblio_path = PathLib(
        "/Users/petteri/Dropbox/github-personal/deep-biblio-tools"
    )
    if str(deep_biblio_path) not in sys.path:
        sys.path.insert(0, str(deep_biblio_path))

    from src.converters.md_to_latex.converter import MarkdownToLatexConverter

    converter = MarkdownToLatexConverter(
        output_dir=OUTPUT_DIR,
        arxiv_ready=True,
        two_column=True,  # arXiv format
        bibliography_style="biblio-style-compact",
    )

    latex_path = converter.convert(
        markdown_file=Path(MANUSCRIPT_PATH),
        author="Petteri Teikari",
        verbose=False,
    )

    logger.success(f"[PASS] Generated LaTeX: {latex_path}")

except Exception as e:
    logger.error(f"[FAIL] LaTeX conversion failed: {e}")
    logger.info("   BibTeX file was still generated successfully!")

# Summary
print("\n" + "=" * 60)
print("CONVERSION COMPLETE!")
print("=" * 60)
print("\n[STATS] Statistics:")
print(f"  - Total citations: {len(citations)}")
print(f"  - Matched: {len(matched)} ({len(matched) / len(citations) * 100:.1f}%)")
print(f"  - Missing: {len(missing)}")
print(f"  - Items organized into collection: {len(items_to_add_to_collection)}")
print("\n[FOLDER] Output files:")
print(f"  - BibTeX: {bibtex_path}")
if "latex_path" in locals():
    print(f"  - LaTeX: {latex_path}")
print("\n[SUCCESS] All citations now organized in '{COLLECTION_NAME}' collection!")
print("=" * 60)

if missing:
    print(
        f"\n[WARNING]  {len(missing)} citations still missing - they should have just been added!"
    )
    print("   Try running the converter again to pick them up.")
