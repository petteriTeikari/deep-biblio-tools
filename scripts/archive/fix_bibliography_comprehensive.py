#!/usr/bin/env python3
"""Comprehensive bibliography fixing combining all improvements."""

# import re  # Banned - using string methods instead
import sys
from pathlib import Path

import bibtexparser
from bibtexparser.bwriter import BibTexWriter


def extract_doi_from_url(url: str) -> str | None:
    """Extract DOI from various academic publisher URLs."""
    if not url:
        return None

    url_lower = url.lower()

    # Springer
    if "link.springer.com/article/" in url_lower:
        idx = url.find("/article/")
        if idx >= 0:
            doi = url[idx + 9 :]
            # Clean up DOI
            doi = doi.replace("%2F", "/")
            # Remove trailing characters
            if "?" in doi:
                doi = doi[: doi.find("?")]
            if "#" in doi:
                doi = doi[: doi.find("#")]
            return doi

    # Nature
    elif "nature.com/articles/" in url_lower:
        idx = url.find("/articles/")
        if idx >= 0:
            doi = url[idx + 10 :]
            doi = doi.replace("%2F", "/")
            if "?" in doi:
                doi = doi[: doi.find("?")]
            if "#" in doi:
                doi = doi[: doi.find("#")]
            return doi

    # Wiley
    elif "onlinelibrary.wiley.com/doi/" in url_lower:
        idx = url.find("/doi/")
        if idx >= 0:
            doi = url[idx + 5 :]
            # Remove full/ or abs/ prefix
            if doi.startswith("full/"):
                doi = doi[5:]
            elif doi.startswith("abs/"):
                doi = doi[4:]
            doi = doi.replace("%2F", "/")
            if "?" in doi:
                doi = doi[: doi.find("?")]
            if "#" in doi:
                doi = doi[: doi.find("#")]
            return doi

    # Direct DOI
    elif "doi.org/" in url_lower:
        idx = url.lower().find("doi.org/")
        if idx >= 0:
            doi = url[idx + 8 :]
            doi = doi.replace("%2F", "/")
            if "?" in doi:
                doi = doi[: doi.find("?")]
            if "#" in doi:
                doi = doi[: doi.find("#")]
            return doi

    # Generic DOI pattern - look for 10.xxxx/ pattern
    elif "/10." in url:
        idx = url.find("/10.")
        if idx >= 0:
            # Check if followed by digits
            start = idx + 1
            end = start + 3  # "10."
            # Look for at least 4 digits after "10."
            if end + 4 <= len(url):
                digits_part = url[end : end + 4]
                if digits_part.isdigit():
                    # Found potential DOI, extract until end or invalid char
                    doi_start = start
                    doi_end = end + 4
                    # Continue until we hit invalid character
                    while doi_end < len(url):
                        ch = url[doi_end]
                        if ch in ".-_()/:" or ch.isalnum():
                            doi_end += 1
                        else:
                            break
                    doi = url[doi_start:doi_end]
                    doi = doi.replace("%2F", "/")
                    return doi

    return None


def fix_et_al_catastrophe(
    author_string: str, title: str = ""
) -> tuple[str, list[str]]:
    """Fix entries where 'et al' was parsed as a name."""
    fixes = []

    # Check for the catastrophic "al, Author et" pattern
    if author_string.startswith("al, ") and " et" in author_string:
        # Extract the actual author name
        if "al, " in author_string and " et" in author_string:
            start = 4  # After "al, "
            end = author_string.find(" et", start)
            if end > start:
                # Extract word between "al, " and " et"
                actual_author = author_string[start:end]
                # Keep only word characters
                if actual_author and all(
                    c.isalnum() or c.isspace() for c in actual_author
                ):
                    actual_author = actual_author.strip()
                    if actual_author:
                        fixes.append("et_al_catastrophe_fixed")

                        # Try to extract more authors from title if it contains "et al"
                        if title and "et al" in title:
                            # Extract author from title like "Zheng et al"
                            words = title.split()
                            if (
                                len(words) >= 3
                                and words[1] == "et"
                                and words[2] == "al"
                            ):
                                if words[0].isalpha():
                                    actual_author = words[0]

                        return actual_author, fixes

    return author_string, []


def parse_authors_properly(
    author_string: str, title: str = ""
) -> tuple[str, list[str]]:
    """Parse authors with proper et al handling and formatting."""
    fixes = []
    original = author_string

    # First check for et al catastrophe
    fixed_author, et_al_fixes = fix_et_al_catastrophe(author_string, title)
    if et_al_fixes:
        author_string = fixed_author
        fixes.extend(et_al_fixes)

    # Remove quotes if present
    if author_string.startswith('"') and author_string.endswith('"'):
        author_string = author_string[1:-1]
        fixes.append("removed_quotes")

    # Handle "et al" properly
    author_lower = author_string.lower()
    if " et al" in author_lower:
        # Find position of " et al"
        idx = author_lower.find(" et al")
        if idx >= 0:
            author_string = author_string[:idx].strip()
            fixes.append("removed_et_al_properly")

    # Handle trailing ampersand
    if author_string.endswith(" &"):
        author_string = author_string[:-2].strip()
        fixes.append("trailing_ampersand")

    # Split by & or and
    if " & " in author_string:
        authors = [a.strip() for a in author_string.split(" & ")]
    elif " and " in author_string:
        authors = [a.strip() for a in author_string.split(" and ")]
    else:
        authors = [author_string]

    formatted_authors = []
    for author in authors:
        if not author or author.lower() in ["et al", "et al.", "al"]:
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
                # Single name - keep as is
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

    result = " and ".join(formatted_authors)

    if result != original and result:
        return result, fixes
    else:
        return original, []


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


def fix_entry_comprehensive(
    entry: dict, known_authors: dict[str, str]
) -> tuple[dict, list[str]]:
    """Apply all fixes to a bibliography entry."""
    fixes = []

    # Check for known authors first
    entry_id = entry.get("ID", "")
    doi = entry.get("doi", "")

    if entry_id in known_authors:
        entry["author"] = known_authors[entry_id]
        fixes.append("author_from_known")
    elif doi and doi in known_authors:
        entry["author"] = known_authors[doi]
        fixes.append("author_from_known")
    elif "author" in entry:
        # Apply comprehensive author fixes
        title = entry.get("title", "")
        fixed_author, author_fixes = parse_authors_properly(
            entry["author"], title
        )
        if author_fixes:
            entry["author"] = fixed_author
            fixes.extend([f"author_{fix}" for fix in author_fixes])

    # Fix title if it's just "Author et al"
    if "title" in entry:
        title = entry["title"]
        # Check if title is same as author or just "X et al"
        if title == entry.get("author", ""):
            entry["title"] = "Title not available - manual verification needed"
            fixes.append("title_placeholder")
        else:
            # Check for "X et al" pattern
            words = title.split()
            if (
                len(words) == 3
                and words[1] == "et"
                and words[2].startswith("al")
            ):
                if words[0].isalpha():
                    entry["title"] = (
                        "Title not available - manual verification needed"
                    )
                    fixes.append("title_placeholder")

    # Extract DOI from URL if not present
    if "doi" not in entry and "url" in entry:
        doi = extract_doi_from_url(entry["url"])
        if doi:
            entry["doi"] = doi
            fixes.append("doi_extracted_from_url")

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
        if "note" not in entry:
            entry["note"] = "Commercial/non-academic source - verify metadata"

    # Fix entry type
    if entry.get("ENTRYTYPE") == "misc" and "journal" in entry:
        entry["ENTRYTYPE"] = "article"
        fixes.append("entry_type")

    # Fix BibTeX key
    if "ID" in entry and "author" in entry:
        current_key = entry["ID"]
        should_fix_key = False

        # Check if key needs fixing
        if (
            current_key.startswith("al") and len(current_key) < 10
        ):  # et al catastrophe
            should_fix_key = True
        elif "&" in entry["author"] and not any(
            current_key.startswith(a.split(",")[0].strip().lower()[:4])
            for a in entry["author"].split(" and ")
        ):
            should_fix_key = True

        if should_fix_key:
            # Generate new key from corrected author
            authors = entry["author"].split(" and ")
            if authors:
                first_author = authors[0]
                if "," in first_author:
                    last_name = first_author.split(",")[0].strip()
                else:
                    parts = first_author.split()
                    last_name = parts[-1] if parts else "unknown"

                clean_last_name = "".join(
                    c for c in last_name if c.isalpha()
                ).lower()
                year = entry.get("year", "2025")
                new_key = f"{clean_last_name}{year}"

                # Handle duplicates
                if new_key != current_key:
                    entry["ID"] = new_key
                    fixes.append("bibtex_key_fixed")

    return entry, fixes


def fix_bibliography_file(
    input_file: Path, output_file: Path | None = None
) -> Path:
    """Apply comprehensive fixes to bibliography."""
    print(f"Reading bibliography from: {input_file}")

    with open(input_file, encoding="utf-8") as f:
        bib_database = bibtexparser.load(f)

    entries = bib_database.entries
    print(f"Total entries: {len(entries)}")

    # Get known author corrections
    known_authors = get_known_authors()

    # Track statistics
    stats = {
        "author_format": 0,
        "et_al_catastrophe": 0,
        "doi_extracted": 0,
        "arxiv_url": 0,
        "entry_type": 0,
        "commercial_source": 0,
        "bibtex_key": 0,
        "known_authors": 0,
        "title_fixed": 0,
        "total_fixed": 0,
    }

    # Track all keys for duplicate detection
    all_keys = {entry["ID"] for entry in entries}

    # Fix each entry
    et_al_examples = []
    for entry in entries:
        original_id = entry.get("ID", "")
        entry["_all_keys"] = all_keys  # For duplicate detection

        entry, fixes = fix_entry_comprehensive(entry, known_authors)

        # Clean up temporary field
        if "_all_keys" in entry:
            del entry["_all_keys"]

        if fixes:
            stats["total_fixed"] += 1
            for fix in fixes:
                if "et_al_catastrophe" in fix:
                    stats["et_al_catastrophe"] += 1
                    et_al_examples.append(
                        {
                            "original_id": original_id,
                            "new_id": entry.get("ID"),
                            "author": entry.get("author", "N/A"),
                        }
                    )
                elif "known" in fix:
                    stats["known_authors"] += 1
                elif "author" in fix:
                    stats["author_format"] += 1
                elif "doi" in fix:
                    stats["doi_extracted"] += 1
                elif fix == "arxiv_url":
                    stats["arxiv_url"] += 1
                elif fix == "entry_type":
                    stats["entry_type"] += 1
                elif fix == "commercial_source_flagged":
                    stats["commercial_source"] += 1
                elif "bibtex_key" in fix:
                    stats["bibtex_key"] += 1
                elif fix == "title_placeholder":
                    stats["title_fixed"] += 1

    # Write output
    if output_file is None:
        output_file = input_file.parent / f"{input_file.stem}_comprehensive.bib"

    writer = BibTexWriter()
    writer.indent = "  "
    writer.order_entries_by = "ID"
    writer.align_values = True

    with open(output_file, "w", encoding="utf-8") as f:
        bibtexparser.dump(bib_database, f, writer)

    print(f"\nFixed bibliography written to: {output_file}")
    print("\nFixes applied:")
    print(f"  'et al' catastrophes fixed: {stats['et_al_catastrophe']}")
    print(f"  Known authors applied: {stats['known_authors']}")
    print(f"  Author format corrected: {stats['author_format']}")
    print(f"  DOIs extracted from URLs: {stats['doi_extracted']}")
    print(f"  arXiv URLs fixed: {stats['arxiv_url']}")
    print(f"  Entry types corrected: {stats['entry_type']}")
    print(f"  Commercial sources flagged: {stats['commercial_source']}")
    print(f"  BibTeX keys fixed: {stats['bibtex_key']}")
    print(f"  Title placeholders added: {stats['title_fixed']}")
    print(f"  Total entries modified: {stats['total_fixed']}")

    # Show et al fixes
    if et_al_examples:
        print("\nExamples of 'et al' catastrophes fixed:")
        for ex in et_al_examples[:5]:
            print(f"  - {ex['original_id']} → {ex['new_id']}: {ex['author']}")

    # Show remaining issues
    print("\nQuality check - entries that may need manual review:")
    issues_shown = 0
    for entry in entries:
        if issues_shown >= 5:
            break

        # Check for single-name authors
        if "author" in entry:
            authors = entry["author"].split(" and ")
            for author in authors:
                if author and "," not in author and " " not in author:
                    print(
                        f"  - {entry.get('ID')}: Single name author '{author}'"
                    )
                    issues_shown += 1
                    break

        # Check for placeholder titles
        if (
            entry.get("title")
            == "Title not available - manual verification needed"
        ):
            print(f"  - {entry.get('ID')}: Needs manual title verification")
            issues_shown += 1

    return output_file


def main():
    """Main function."""
    if len(sys.argv) > 1:
        input_file = Path(sys.argv[1])
    else:
        print(
            "Usage: python fix_bibliography_comprehensive.py <input.bib> [output.bib]"
        )
        return 1

    if not input_file.exists():
        print(f"Error: File not found: {input_file}")
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
