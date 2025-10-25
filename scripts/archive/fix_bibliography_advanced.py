#!/usr/bin/env python3
"""Advanced bibliography fixing script with et al handling and DOI extraction."""

# import re  # Banned - using string methods instead
import sys
from pathlib import Path

import bibtexparser
import requests
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


def fetch_doi_from_pmc(pmc_id: str) -> str | None:
    """Fetch DOI from PMC ID using NCBI API."""
    # Extract PMC ID number
    if "PMC" not in pmc_id:
        return None

    idx = pmc_id.find("PMC")
    if idx >= 0:
        # Extract digits after PMC
        start = idx + 3
        end = start
        while end < len(pmc_id) and pmc_id[end].isdigit():
            end += 1

        if end > start:
            pmc_num = pmc_id[start:end]
            url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids=PMC{pmc_num}&format=json"

    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "records" in data and data["records"]:
                record = data["records"][0]
                return record.get("doi")
    except Exception:
        pass

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


def parse_authors_properly(author_string: str) -> tuple[str, list[str]]:
    """Parse authors with proper et al handling."""
    fixes = []
    original = author_string

    # First check for et al catastrophe
    fixed_author, et_al_fixes = fix_et_al_catastrophe(author_string)
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


def check_url_validity(url: str) -> tuple[bool, str | None]:
    """Check if URL is valid and accessible."""
    if not url:
        return True, None

    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        if response.status_code == 404:
            return False, "URL returns 404 - Not Found"
        elif response.status_code >= 500:
            return False, f"Server error: {response.status_code}"
        elif response.status_code >= 400:
            return False, f"Client error: {response.status_code}"
        return True, None
    except requests.exceptions.Timeout:
        return False, "URL timeout - may be inaccessible"
    except Exception as e:
        return False, f"URL check failed: {str(e)}"


def enhance_entry(entry: dict) -> tuple[dict, list[str]]:
    """Enhance a bibliography entry with all fixes."""
    fixes = []

    # Fix author format including et al catastrophe
    if "author" in entry:
        fixed_author, author_fixes = parse_authors_properly(entry["author"])
        if author_fixes:
            entry["author"] = fixed_author
            fixes.extend([f"author_{fix}" for fix in author_fixes])

    # Fix title if it's just "Author et al"
    if "title" in entry and entry["title"] == entry.get("author", ""):
        # Title is same as author - likely a parsing error
        entry["title"] = "Title not available - manual verification needed"
        fixes.append("title_placeholder")

    # Extract DOI from URL if not present
    if "doi" not in entry and "url" in entry:
        doi = extract_doi_from_url(entry["url"])
        if doi:
            entry["doi"] = doi
            fixes.append("doi_extracted_from_url")
        elif "pmc.ncbi.nlm.nih.gov" in entry["url"]:
            # Try to get DOI from PMC
            if "PMC" in entry["url"]:
                idx = entry["url"].find("PMC")
                if idx >= 0:
                    # Extract PMC ID
                    start = idx
                    end = idx + 3
                    while (
                        end < len(entry["url"]) and entry["url"][end].isdigit()
                    ):
                        end += 1
                    if end > idx + 3:
                        pmc_id = entry["url"][start:end]
                        doi = fetch_doi_from_pmc(pmc_id)
                        if doi:
                            entry["doi"] = doi
                            fixes.append("doi_from_pmc")

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

    # Check URL validity (disabled by default to avoid too many requests)
    # valid_url, error_msg = check_url_validity(entry.get('url'))
    # if not valid_url:
    #     if 'note' in entry:
    #         entry['note'] += f"; {error_msg}"
    #     else:
    #         entry['note'] = error_msg
    #     fixes.append('broken_url_flagged')

    # Fix entry type
    if entry.get("ENTRYTYPE") == "misc" and "journal" in entry:
        entry["ENTRYTYPE"] = "article"
        fixes.append("entry_type")

    # Fix BibTeX key for et al catastrophes
    if "ID" in entry and entry["ID"].startswith("al"):
        # Generate new key from corrected author
        if "author" in entry:
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

                entry["ID"] = new_key
                fixes.append("bibtex_key_from_et_al")

    return entry, fixes


def fix_bibliography_file(
    input_file: Path, output_file: Path | None = None
) -> Path:
    """Fix bibliography with advanced et al and DOI handling."""
    print(f"Reading bibliography from: {input_file}")

    with open(input_file, encoding="utf-8") as f:
        bib_database = bibtexparser.load(f)

    entries = bib_database.entries
    print(f"Total entries: {len(entries)}")

    # Track statistics
    stats = {
        "author_format": 0,
        "et_al_catastrophe": 0,
        "doi_extracted": 0,
        "arxiv_url": 0,
        "entry_type": 0,
        "bibtex_key": 0,
        "title_fixed": 0,
        "total_fixed": 0,
    }

    # Fix each entry
    et_al_examples = []
    for entry in entries:
        original_id = entry.get("ID", "")
        entry, fixes = enhance_entry(entry)

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
                elif "author" in fix:
                    stats["author_format"] += 1
                elif "doi" in fix:
                    stats["doi_extracted"] += 1
                elif fix == "arxiv_url":
                    stats["arxiv_url"] += 1
                elif fix == "entry_type":
                    stats["entry_type"] += 1
                elif "bibtex_key" in fix:
                    stats["bibtex_key"] += 1
                elif fix == "title_placeholder":
                    stats["title_fixed"] += 1

    # Write output
    if output_file is None:
        output_file = input_file.parent / f"{input_file.stem}_advanced.bib"

    writer = BibTexWriter()
    writer.indent = "  "
    writer.order_entries_by = "ID"
    writer.align_values = True

    with open(output_file, "w", encoding="utf-8") as f:
        bibtexparser.dump(bib_database, f, writer)

    print(f"\nFixed bibliography written to: {output_file}")
    print("\nFixes applied:")
    print(f"  'et al' catastrophes fixed: {stats['et_al_catastrophe']}")
    print(f"  Author format corrected: {stats['author_format']}")
    print(f"  DOIs extracted from URLs: {stats['doi_extracted']}")
    print(f"  arXiv URLs fixed: {stats['arxiv_url']}")
    print(f"  Entry types corrected: {stats['entry_type']}")
    print(f"  BibTeX keys fixed: {stats['bibtex_key']}")
    print(f"  Titles placeholders added: {stats['title_fixed']}")
    print(f"  Total entries modified: {stats['total_fixed']}")

    # Show et al fixes
    if et_al_examples:
        print("\nExamples of 'et al' catastrophes fixed:")
        for ex in et_al_examples[:5]:
            print(f"  - {ex['original_id']} → {ex['new_id']}: {ex['author']}")

    # Show remaining issues
    remaining_issues = []
    for entry in entries:
        if "author" in entry and entry["author"].lower().startswith("al,"):
            remaining_issues.append(
                f"{entry.get('ID')}: Still has 'al,' pattern"
            )

    if remaining_issues:
        print("\nRemaining issues to investigate:")
        for issue in remaining_issues[:5]:
            print(f"  - {issue}")

    return output_file


def main():
    """Main function."""
    if len(sys.argv) > 1:
        input_file = Path(sys.argv[1])
    else:
        input_file = Path("drone_data/latex_output_final/references.bib")

    if not input_file.exists():
        print(f"Error: File not found: {input_file}")
        print(
            "\nUsage: python fix_bibliography_advanced.py [input.bib] [output.bib]"
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
