#!/usr/bin/env python3
"""Enhanced bibliography fixing script with comprehensive author parsing and DOI metadata fetching."""

# import re  # Banned - using string methods instead
import sys
import time
from pathlib import Path

import bibtexparser
import requests
from bibtexparser.bwriter import BibTexWriter


def fetch_crossref_metadata(doi: str) -> dict | None:
    """Fetch complete metadata from CrossRef API."""
    url = f"https://api.crossref.org/works/{doi}"
    headers = {
        "User-Agent": "DeepBiblioTools/1.0 (mailto:petteri.teikari@gmail.com)"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("message", {})
        elif response.status_code == 429:
            # Rate limited
            print(f"  Rate limited on CrossRef for DOI {doi}")
            return None
    except Exception as e:
        print(f"  Error fetching CrossRef metadata for {doi}: {e}")

    return None


def format_author_name(author_dict: dict) -> str:
    """Format author name from CrossRef metadata."""
    family = author_dict.get("family", "")
    given = author_dict.get("given", "")

    if family and given:
        return f"{family}, {given}"
    elif family:
        return family
    else:
        return author_dict.get("name", "")


def extract_authors_from_crossref(metadata: dict) -> list[str]:
    """Extract properly formatted authors from CrossRef metadata."""
    authors = []

    if "author" in metadata:
        for author in metadata["author"]:
            formatted = format_author_name(author)
            if formatted:
                authors.append(formatted)

    return authors


def parse_ampersand_authors(author_string: str) -> list[str]:
    """Parse authors separated by & or 'and'."""
    # Replace multiple spaces with single space
    result = []
    prev_space = False
    for ch in author_string.strip():
        if ch.isspace():
            if not prev_space:
                result.append(" ")
                prev_space = True
        else:
            result.append(ch)
            prev_space = False
    author_string = "".join(result)

    # Split by & or and
    if " & " in author_string:
        parts = [p.strip() for p in author_string.split(" & ")]
    elif " and " in author_string:
        parts = [p.strip() for p in author_string.split(" and ")]
    else:
        parts = [author_string]

    return parts


def fix_author_format(author_string: str) -> tuple[str, list[str]]:
    """
    Fix author formatting issues.
    Returns: (fixed_string, list_of_fixes_applied)
    """
    fixes = []
    original = author_string

    # Remove quotes if present
    if author_string.startswith('"') and author_string.endswith('"'):
        author_string = author_string[1:-1]
        fixes.append("removed_quotes")

    # Handle special case of "LastName &" format (like "Chatzidakis & Botton")
    if author_string.endswith(" &"):
        author_string = author_string[:-2].strip()
        fixes.append("trailing_ampersand")

    # Parse authors
    authors = parse_ampersand_authors(author_string)
    formatted_authors = []

    for author in authors:
        # Skip empty authors
        if not author or author == "et al" or author == "et al.":
            fixes.append("removed_et_al")
            continue

        # Check if already in "LastName, FirstName" format
        if "," in author:
            formatted_authors.append(author)
        else:
            # Split into parts
            parts = author.split()
            if len(parts) == 0:
                continue
            elif len(parts) == 1:
                # Single name - assume it's last name
                formatted_authors.append(parts[0])
                fixes.append("single_name")
            elif len(parts) == 2:
                # Assume "FirstName LastName" format
                formatted_authors.append(f"{parts[1]}, {parts[0]}")
                fixes.append("reordered_names")
            else:
                # Multiple parts - assume last part is last name
                last_name = parts[-1]
                first_names = " ".join(parts[:-1])
                formatted_authors.append(f"{last_name}, {first_names}")
                fixes.append("complex_name")

    # Join with " and "
    result = " and ".join(formatted_authors)

    # Check if we made meaningful changes
    if result != original and result:
        return result, fixes
    else:
        return original, []


def is_commercial_source(url: str) -> bool:
    """Check if URL is from a commercial/non-academic source."""
    commercial_domains = [
        "biblus.accasoftware.com",
        "bimgym.com",
        "buildingandland.co.uk",
        "consumeraffairs.com",
        "researchgate.net",  # Often blocks scraping
        "medium.com",
        "towardsdatascience.com",
        "linkedin.com",
        "twitter.com",
        "facebook.com",
    ]

    return any(domain in url.lower() for domain in commercial_domains)


def enhance_entry_with_doi(entry: dict, doi: str) -> dict[str, str]:
    """Enhance bibliography entry with CrossRef metadata."""
    enhancements = {}

    # Fetch metadata
    metadata = fetch_crossref_metadata(doi)
    if not metadata:
        return enhancements

    # Extract authors
    authors = extract_authors_from_crossref(metadata)
    if authors:
        enhancements["author_enhanced"] = " and ".join(authors)

    # Extract other fields
    if "title" in metadata and metadata["title"]:
        # Handle title as list (CrossRef format)
        if isinstance(metadata["title"], list):
            enhancements["title_enhanced"] = metadata["title"][0]
        else:
            enhancements["title_enhanced"] = metadata["title"]

    if "container-title" in metadata and metadata["container-title"]:
        # Handle journal as list
        if isinstance(metadata["container-title"], list):
            enhancements["journal_enhanced"] = metadata["container-title"][0]
        else:
            enhancements["journal_enhanced"] = metadata["container-title"]

    if "volume" in metadata:
        enhancements["volume_enhanced"] = str(metadata["volume"])

    if "issue" in metadata:
        enhancements["issue_enhanced"] = str(metadata["issue"])

    if "page" in metadata:
        enhancements["pages_enhanced"] = metadata["page"]

    if "published-print" in metadata:
        date_parts = metadata["published-print"].get("date-parts", [[]])[0]
        if date_parts and len(date_parts) > 0:
            enhancements["year_enhanced"] = str(date_parts[0])

    # Add publisher if available
    if "publisher" in metadata:
        enhancements["publisher_enhanced"] = metadata["publisher"]

    # Add ISSN if available
    if "ISSN" in metadata and metadata["ISSN"]:
        enhancements["issn_enhanced"] = metadata["ISSN"][0]

    return enhancements


def fix_entry(entry: dict) -> tuple[dict, list[str]]:
    """
    Fix a single bibliography entry.
    Returns: (entry, list_of_fixes_applied)
    """
    fixes = []

    # Fix author format
    if "author" in entry:
        fixed_author, author_fixes = fix_author_format(entry["author"])
        if author_fixes:
            entry["author"] = fixed_author
            fixes.extend([f"author_{fix}" for fix in author_fixes])

    # Fix arXiv URLs
    if "url" in entry and "arxiv.org" in entry["url"]:
        url = entry["url"]
        if "/html/" in url:
            idx = url.find("/html/")
            if idx >= 0:
                # Extract arXiv ID (format: XXXX.XXXXX)
                start = idx + 6
                arxiv_id = ""
                # Look for pattern of digits.digits
                i = start
                while i < len(url) and url[i].isdigit():
                    arxiv_id += url[i]
                    i += 1
                if i < len(url) and url[i] == ".":
                    arxiv_id += "."
                    i += 1
                    while i < len(url) and url[i].isdigit():
                        arxiv_id += url[i]
                        i += 1

                if arxiv_id and "." in arxiv_id:
                    entry["url"] = f"https://arxiv.org/abs/{arxiv_id}"
                    fixes.append("arxiv_url")

    # Check for commercial sources
    if "url" in entry and is_commercial_source(entry["url"]):
        fixes.append("commercial_source_flagged")
        # Add note field to flag this
        if "note" not in entry:
            entry["note"] = "Commercial/non-academic source - verify metadata"

    # Try to enhance with DOI metadata if available
    if "doi" in entry and entry["doi"]:
        print(f"  Fetching metadata for DOI: {entry['doi']}")
        enhancements = enhance_entry_with_doi(entry, entry["doi"])

        for field, enhanced_value in enhancements.items():
            base_field = field.replace("_enhanced", "")

            # Special handling for authors
            if base_field == "author":
                # Only replace if current authors are incomplete
                current = entry.get("author", "")
                if "et al" in current.lower() or "," not in current:
                    entry["author"] = enhanced_value
                    fixes.append("author_from_doi")
            elif base_field == "title" and (
                not entry.get("title")
                or entry.get("title") == entry.get("author")
            ):
                # Replace if title is missing or same as author
                entry["title"] = enhanced_value
                fixes.append("title_from_doi")
            elif base_field not in entry or not entry[base_field]:
                # Add missing fields
                entry[base_field] = enhanced_value
                fixes.append(f"{base_field}_from_doi")

        # Add delay to avoid rate limiting
        time.sleep(0.5)

    # Fix entry type based on available fields
    if entry.get("ENTRYTYPE") == "misc" and "journal" in entry:
        entry["ENTRYTYPE"] = "article"
        fixes.append("entry_type")

    # Fix BibTeX key if it uses wrong author
    if "ID" in entry and "&" in entry.get("author", ""):
        # Extract first author's last name
        authors = parse_ampersand_authors(entry["author"])
        if authors:
            first_author = authors[0]
            # Extract last name
            if "," in first_author:
                last_name = first_author.split(",")[0].strip()
            else:
                parts = first_author.split()
                last_name = parts[-1] if parts else "unknown"

            # Clean last name for BibTeX key
            clean_last_name = "".join(
                c for c in last_name if c.isalpha()
            ).lower()
            year = entry.get("year", "2025")

            # Check if current key doesn't match
            current_key = entry["ID"]
            if not current_key.startswith(clean_last_name):
                # Generate new key
                new_key = f"{clean_last_name}{year}"
                # Handle duplicates by adding suffix
                base_key = new_key
                suffix = ord("a")
                while new_key in entry.get("_all_keys", set()):
                    new_key = base_key + chr(suffix)
                    suffix += 1

                entry["ID"] = new_key
                fixes.append("bibtex_key")

    return entry, fixes


def fix_bibliography_file(
    input_file: Path, output_file: Path | None = None
) -> Path:
    """Fix common issues in a bibliography file with enhanced processing."""
    print(f"Reading bibliography from: {input_file}")

    with open(input_file, encoding="utf-8") as f:
        bib_database = bibtexparser.load(f)

    entries = bib_database.entries
    print(f"Total entries: {len(entries)}")

    # Track all keys to handle duplicates
    all_keys = {entry["ID"] for entry in entries}

    # Track statistics
    stats = {
        "author_format": 0,
        "arxiv_url": 0,
        "et_al": 0,
        "entry_type": 0,
        "commercial_source": 0,
        "doi_enhanced": 0,
        "bibtex_key": 0,
        "total_fixed": 0,
    }

    # Fix each entry
    for i, entry in enumerate(entries):
        # Add reference to all keys for duplicate checking
        entry["_all_keys"] = all_keys

        # Show progress
        if (i + 1) % 50 == 0:
            print(f"  Processing entry {i + 1}/{len(entries)}...")

        entry, fixes = fix_entry(entry)

        if fixes:
            stats["total_fixed"] += 1
            for fix in fixes:
                # Map specific fixes to stat categories
                if "author" in fix:
                    stats["author_format"] += 1
                elif fix == "arxiv_url":
                    stats["arxiv_url"] += 1
                elif fix == "removed_et_al" in fix:
                    stats["et_al"] += 1
                elif fix == "entry_type":
                    stats["entry_type"] += 1
                elif fix == "commercial_source_flagged":
                    stats["commercial_source"] += 1
                elif "from_doi" in fix:
                    stats["doi_enhanced"] += 1
                elif fix == "bibtex_key":
                    stats["bibtex_key"] += 1

        # Clean up temporary field
        if "_all_keys" in entry:
            del entry["_all_keys"]

    # Write output
    if output_file is None:
        output_file = input_file.parent / f"{input_file.stem}_enhanced.bib"

    writer = BibTexWriter()
    writer.indent = "  "
    writer.order_entries_by = "ID"
    writer.align_values = True

    with open(output_file, "w", encoding="utf-8") as f:
        bibtexparser.dump(bib_database, f, writer)

    print(f"\nEnhanced bibliography written to: {output_file}")
    print("\nFixes applied:")
    print(f"  Author format corrected: {stats['author_format']}")
    print(f"  arXiv URLs fixed: {stats['arxiv_url']}")
    print(f"  'et al' removed: {stats['et_al']}")
    print(f"  Entry types corrected: {stats['entry_type']}")
    print(f"  Commercial sources flagged: {stats['commercial_source']}")
    print(f"  Enhanced with DOI metadata: {stats['doi_enhanced']}")
    print(f"  BibTeX keys fixed: {stats['bibtex_key']}")
    print(f"  Total entries modified: {stats['total_fixed']}")

    # Show remaining issues
    remaining_issues = []
    for entry in entries:
        if "author" in entry:
            # Check for still missing first names
            authors = parse_ampersand_authors(entry["author"])
            for author in authors:
                if author and "," not in author and " " not in author:
                    remaining_issues.append(
                        f"Single name author in {entry.get('ID')}: {author}"
                    )

    if remaining_issues and len(remaining_issues) <= 10:
        print("\nRemaining issues to fix manually:")
        for issue in remaining_issues[:10]:
            print(f"  - {issue}")

    return output_file


def main():
    """Main function."""
    if len(sys.argv) > 1:
        input_file = Path(sys.argv[1])
    else:
        input_file = Path("drone_data/latex_output_limited/references.bib")

    if not input_file.exists():
        print(f"Error: File not found: {input_file}")
        print(
            "\nUsage: python fix_bibliography_enhanced.py [input.bib] [output.bib]"
        )
        return 1

    output_file = None
    if len(sys.argv) > 2:
        output_file = Path(sys.argv[2])

    try:
        fix_bibliography_file(input_file, output_file)
        return 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
