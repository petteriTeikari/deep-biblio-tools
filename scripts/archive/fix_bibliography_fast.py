#!/usr/bin/env python3
"""Fast bibliography fixing script focusing on author format and basic issues."""

# import re  # Banned - using string methods instead
import sys
from pathlib import Path

import bibtexparser
from bibtexparser.bwriter import BibTexWriter


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
                # Single name - keep as is for now
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


def fix_entry(
    entry: dict, known_authors: dict[str, str]
) -> tuple[dict, list[str]]:
    """
    Fix a single bibliography entry.
    Returns: (entry, list_of_fixes_applied)
    """
    fixes = []

    # Fix author format
    if "author" in entry:
        # First check if we have known full names for this entry
        entry_id = entry.get("ID", "")
        doi = entry.get("doi", "")

        # Check known authors mapping
        if entry_id in known_authors:
            entry["author"] = known_authors[entry_id]
            fixes.append("author_from_known")
        elif doi and doi in known_authors:
            entry["author"] = known_authors[doi]
            fixes.append("author_from_known")
        else:
            # Apply general fixes
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

    # Fix entry type based on available fields
    if entry.get("ENTRYTYPE") == "misc" and "journal" in entry:
        entry["ENTRYTYPE"] = "article"
        fixes.append("entry_type")

    # Fix BibTeX key if it uses wrong author
    if "ID" in entry and "author" in entry:
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
            if (
                not current_key.startswith(clean_last_name)
                and clean_last_name != "unknown"
            ):
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


def get_known_authors() -> dict[str, str]:
    """Return mapping of known author corrections."""
    return {
        # By entry ID
        "alqudsi2025": "Alqudsi, Yunes and Makaraci, Murat",
        "amin2014": "Amin, Moeness G. and Ahmad, Fauzia",
        "arteaga2014": "Arteaga, M. and Kahr, B.",
        "botton2019": "Chatzidakis, M. and Botton, G. A.",
        "chatzidakis2019": "Chatzidakis, M. and Botton, G. A.",
        # By DOI
        "10.1177/09544062241275359": "Alqudsi, Yunes and Makaraci, Murat",
        "10.1016/B978-0-12-396500-4.00017-X": "Amin, Moeness G. and Ahmad, Fauzia",
        "10.1107/S2053273314007791": "Arteaga, M. and Kahr, B.",
        "10.1038/s41598-019-38482-1": "Chatzidakis, M. and Botton, G. A.",
    }


def fix_bibliography_file(
    input_file: Path, output_file: Path | None = None
) -> Path:
    """Fix common issues in a bibliography file."""
    print(f"Reading bibliography from: {input_file}")

    with open(input_file, encoding="utf-8") as f:
        bib_database = bibtexparser.load(f)

    entries = bib_database.entries
    print(f"Total entries: {len(entries)}")

    # Get known author corrections
    known_authors = get_known_authors()

    # Track all keys to handle duplicates
    all_keys = {entry["ID"] for entry in entries}

    # Track statistics
    stats = {
        "author_format": 0,
        "arxiv_url": 0,
        "et_al": 0,
        "entry_type": 0,
        "commercial_source": 0,
        "bibtex_key": 0,
        "known_authors": 0,
        "total_fixed": 0,
    }

    # Fix each entry
    for entry in entries:
        # Add reference to all keys for duplicate checking
        entry["_all_keys"] = all_keys

        entry, fixes = fix_entry(entry, known_authors)

        if fixes:
            stats["total_fixed"] += 1
            for fix in fixes:
                # Map specific fixes to stat categories
                if "author" in fix:
                    if "known" in fix:
                        stats["known_authors"] += 1
                    else:
                        stats["author_format"] += 1
                elif fix == "arxiv_url":
                    stats["arxiv_url"] += 1
                elif fix == "removed_et_al" in fix:
                    stats["et_al"] += 1
                elif fix == "entry_type":
                    stats["entry_type"] += 1
                elif fix == "commercial_source_flagged":
                    stats["commercial_source"] += 1
                elif fix == "bibtex_key":
                    stats["bibtex_key"] += 1

        # Clean up temporary field
        if "_all_keys" in entry:
            del entry["_all_keys"]

    # Write output
    if output_file is None:
        output_file = input_file.parent / f"{input_file.stem}_fixed_fast.bib"

    writer = BibTexWriter()
    writer.indent = "  "
    writer.order_entries_by = "ID"
    writer.align_values = True

    with open(output_file, "w", encoding="utf-8") as f:
        bibtexparser.dump(bib_database, f, writer)

    print(f"\nFixed bibliography written to: {output_file}")
    print("\nFixes applied:")
    print(f"  Author format corrected: {stats['author_format']}")
    print(f"  Known authors applied: {stats['known_authors']}")
    print(f"  arXiv URLs fixed: {stats['arxiv_url']}")
    print(f"  'et al' removed: {stats['et_al']}")
    print(f"  Entry types corrected: {stats['entry_type']}")
    print(f"  Commercial sources flagged: {stats['commercial_source']}")
    print(f"  BibTeX keys fixed: {stats['bibtex_key']}")
    print(f"  Total entries modified: {stats['total_fixed']}")

    # Show specific examples that still need attention
    print("\nExamples of entries that may need manual review:")
    examples_shown = 0
    for entry in entries:
        if examples_shown >= 5:
            break

        # Check for single-name authors
        if "author" in entry:
            authors = parse_ampersand_authors(entry["author"])
            for author in authors:
                if author and "," not in author and " " not in author:
                    print(f"  - {entry.get('ID')}: Single name '{author}'")
                    examples_shown += 1
                    break

        # Check for commercial sources
        if "note" in entry and "Commercial" in entry["note"]:
            print(f"  - {entry.get('ID')}: {entry.get('url', 'No URL')}")
            examples_shown += 1

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
            "\nUsage: python fix_bibliography_fast.py [input.bib] [output.bib]"
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
