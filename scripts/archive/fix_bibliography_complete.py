#!/usr/bin/env python3
"""
Complete bibliography fix - matches existing entries and creates placeholders for missing ones.

This script:
1. Extracts all citation keys from a LaTeX document
2. Matches existing bibliography entries to the correct keys
3. Creates placeholder entries for citations that couldn't be matched
4. Generates a complete bibliography file ready for use
"""

import logging

# import re  # Banned - using string methods instead
import sys
from pathlib import Path

import bibtexparser
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bwriter import BibTexWriter

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def extract_latex_citations(latex_file: Path) -> set[str]:
    """Extract all citation keys from a LaTeX file."""
    citations = set()

    with open(latex_file, encoding="utf-8") as f:
        content = f.read()

    # Find all citations - look for \cite, \citep, \citet commands
    i = 0
    while i < len(content):
        # Look for \cite
        if content[i : i + 5] == "\\cite":
            # Check if it's \citep or \citet
            j = i + 5
            if j < len(content) and content[j] in "pt":
                j += 1

            # Skip whitespace
            while j < len(content) and content[j] in " \t\n":
                j += 1

            # Check for opening brace
            if j < len(content) and content[j] == "{":
                # Find closing brace
                k = j + 1
                brace_count = 1
                while k < len(content) and brace_count > 0:
                    if content[k] == "{":
                        brace_count += 1
                    elif content[k] == "}":
                        brace_count -= 1
                    k += 1

                if brace_count == 0:
                    # Extract citation keys
                    cite_text = content[j + 1 : k - 1]
                    # Split by comma and semicolon
                    cite_text = cite_text.replace(";", ",")
                    cite_keys = cite_text.split(",")
                    for key in cite_keys:
                        key = key.strip()
                        if key:
                            citations.add(key)

                i = k
                continue

        i += 1

    return citations


def parse_author_year_from_key(key: str) -> tuple[str, str]:
    """Extract author and year from a citation key."""
    # Most keys follow pattern: author2023 or author_2023

    # Find the year (4 digits, possibly followed by a letter)
    year_start = -1
    for i in range(len(key) - 3):
        if key[i : i + 4].isdigit():
            # Check if it's a valid year
            year_num = int(key[i : i + 4])
            if 1900 <= year_num <= 2100:
                year_start = i
                break

    if year_start >= 0:
        # Extract year with possible suffix letter
        year_end = year_start + 4
        if (
            year_end < len(key)
            and key[year_end].isalpha()
            and key[year_end].islower()
        ):
            year_end += 1

        year = key[year_start:year_end]

        # Extract author (everything before year, excluding underscore or space)
        author = key[:year_start]
        if author and author[-1] in "_":
            author = author[:-1]

        # Keep only letters
        author = "".join(c for c in author if c.isalpha()).lower()

        return author, year

    return "", ""


def normalize_author_name(author: str) -> str:
    """Normalize author name for comparison."""
    # Remove et al.
    author = author.replace(" et al.", "").strip()

    # Extract last name
    if "," in author:
        # Handle "Last, First" format
        author = author.split(",")[0].strip()
    elif " and " in author:
        # Handle "Author1 and Author2" - take first author
        author = author.split(" and ")[0].strip()
        if " " in author:
            # Take last word as surname
            author = author.split()[-1].strip()
    elif " " in author:
        # Handle "First Last" format - take last word
        author = author.split()[-1].strip()

    return author.lower()


def find_entries_by_year(entries: list[dict], year: str) -> list[dict]:
    """Find all entries with a specific year."""
    matches = []
    for entry in entries:
        if entry.get("year", "") == year:
            matches.append(entry)
    return matches


def match_citation_to_entry(
    citation_key: str, entries: list[dict]
) -> dict | None:
    """Find the best matching entry for a citation key."""
    target_author, target_year = parse_author_year_from_key(citation_key)

    if not target_year:
        return None

    # First, find all entries with matching year
    year_matches = find_entries_by_year(entries, target_year)

    if not year_matches:
        return None

    # If only one match for the year, return it
    if len(year_matches) == 1:
        return year_matches[0]

    # Try to match by author
    best_match = None
    best_score = 0.0

    for entry in year_matches:
        author = normalize_author_name(entry.get("author", ""))

        # Calculate match score
        score = 0.0
        if target_author and author:
            if target_author == author:
                score = 1.0
            elif target_author in author or author in target_author:
                score = 0.7
            elif (
                len(target_author) >= 3
                and len(author) >= 3
                and target_author[:3] == author[:3]
            ):
                score = 0.5

        if score > best_score:
            best_score = score
            best_match = entry

    # Only return if we have a reasonable match
    if best_score >= 0.5:
        return best_match

    # If no good author match but only one entry for the year, return it
    if len(year_matches) == 1:
        return year_matches[0]

    return None


def create_placeholder_entry(citation_key: str) -> dict:
    """Create a placeholder bibliography entry for an unmatched citation."""
    author, year = parse_author_year_from_key(citation_key)

    # Create a basic entry
    entry = {
        "ID": citation_key,
        "ENTRYTYPE": "misc",
        "author": author.capitalize() if author else "Unknown",
        "year": year if year else "2025",
        "title": f"[PLACEHOLDER - Please update: {citation_key}]",
        "note": "This is a placeholder entry generated to match a LaTeX citation. Please update with correct bibliographic information.",
    }

    # Handle special known patterns
    if citation_key == "akerlof1970":
        entry.update(
            {
                "author": "Akerlof, George A.",
                "title": 'The Market for "Lemons": Quality Uncertainty and the Market Mechanism',
                "journal": "The Quarterly Journal of Economics",
                "volume": "84",
                "number": "3",
                "pages": "488-500",
                "year": "1970",
                "ENTRYTYPE": "article",
            }
        )
    elif citation_key == "stiglitz2000":
        entry.update(
            {
                "author": "Stiglitz, Joseph E.",
                "title": "The Contributions of the Economics of Information to Twentieth Century Economics",
                "journal": "The Quarterly Journal of Economics",
                "volume": "115",
                "number": "4",
                "pages": "1441-1478",
                "year": "2000",
                "ENTRYTYPE": "article",
            }
        )
    elif citation_key == "lusht1996":
        entry.update(
            {
                "author": "Lusht, Kenneth M.",
                "title": "Real Estate Valuation: Principles and Applications",
                "publisher": "McGraw-Hill",
                "year": "1996",
                "ENTRYTYPE": "book",
            }
        )
    elif citation_key == "susskind2015":
        entry.update(
            {
                "author": "Susskind, Richard and Susskind, Daniel",
                "title": "The Future of the Professions: How Technology Will Transform the Work of Human Experts",
                "publisher": "Oxford University Press",
                "year": "2015",
                "ENTRYTYPE": "book",
            }
        )
    elif citation_key == "mae2022":
        entry.update(
            {
                "author": "Fannie Mae",
                "title": "Appraiser Update: Appraisal Bias and Appraisal Quality",
                "year": "2022",
                "url": "https://singlefamily.fanniemae.com/media/30751/display",
            }
        )
    elif citation_key == "mae2024":
        entry.update(
            {
                "author": "Fannie Mae",
                "title": "Uniform Appraisal Dataset (UAD) and Forms Redesign Update",
                "year": "2024",
                "url": "https://singlefamily.fanniemae.com/originating-underwriting/uniform-appraisal-dataset-uad",
            }
        )
    elif citation_key == "mac2024":
        entry.update(
            {
                "author": "Freddie Mac",
                "title": "Uniform Appraisal Dataset (UAD) Version 3.6",
                "year": "2024",
                "url": "https://sf.freddiemac.com/working-with-us/origination-underwriting/mortgage-products/uad",
            }
        )

    return entry


def fix_bibliography_keys(
    latex_file: Path,
    bib_file: Path,
    output_file: Path,
    create_placeholders: bool = True,
):
    """Fix bibliography keys to match LaTeX citations."""

    # Extract expected citation keys from LaTeX
    logger.info(f"Extracting citations from {latex_file}")
    expected_keys = extract_latex_citations(latex_file)
    logger.info(
        f"Found {len(expected_keys)} unique citations in LaTeX document"
    )

    # Parse bibliography
    logger.info(f"Parsing bibliography from {bib_file}")
    with open(bib_file, encoding="utf-8") as f:
        bib_database = bibtexparser.load(f)

    logger.info(f"Found {len(bib_database.entries)} entries in bibliography")

    # Create mapping of current keys
    current_entries = {entry["ID"]: entry for entry in bib_database.entries}

    # Create new database for output
    new_database = BibDatabase()

    # Track what we've processed
    processed_entries = set()
    unmatched_citations = []
    matched_citations = {}
    placeholder_entries = []

    # First pass: Process citations that need matching
    for citation_key in sorted(expected_keys):
        # Check if key already exists correctly
        if citation_key in current_entries:
            entry = current_entries[citation_key]
            new_database.entries.append(entry)
            processed_entries.add(entry["ID"])
            matched_citations[citation_key] = entry["ID"]
            continue

        # Try to find a matching entry
        match = match_citation_to_entry(citation_key, bib_database.entries)

        if match:
            # Create a copy with the new key
            new_entry = match.copy()
            old_key = new_entry["ID"]
            new_entry["ID"] = citation_key
            new_database.entries.append(new_entry)
            processed_entries.add(old_key)
            matched_citations[citation_key] = old_key
            logger.info(
                f"Matched '{citation_key}' to entry '{old_key}' ({match.get('author', 'Unknown')}, {match.get('year', 'Unknown')})"
            )
        else:
            unmatched_citations.append(citation_key)
            if create_placeholders:
                # Create placeholder entry
                placeholder = create_placeholder_entry(citation_key)
                new_database.entries.append(placeholder)
                placeholder_entries.append(citation_key)
                logger.info(f"Created placeholder for '{citation_key}'")
            else:
                logger.warning(f"No match found for citation '{citation_key}'")

    # Second pass: Add any unprocessed entries (not referenced in LaTeX)
    unreferenced_entries = []
    for entry in bib_database.entries:
        if entry["ID"] not in processed_entries:
            new_database.entries.append(entry)
            unreferenced_entries.append(entry["ID"])

    # Write updated bibliography
    logger.info(f"Writing updated bibliography to {output_file}")
    writer = BibTexWriter()
    writer.indent = "  "
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(writer.write(new_database))

    # Report summary
    print("\n=== Bibliography Fix Summary ===")
    print(f"Total citations in LaTeX: {len(expected_keys)}")
    print(f"Successfully matched: {len(matched_citations)}")
    if create_placeholders:
        print(f"Placeholders created: {len(placeholder_entries)}")
    else:
        print(f"Unmatched citations: {len(unmatched_citations)}")
    print(f"Unreferenced entries kept: {len(unreferenced_entries)}")

    if unmatched_citations and not create_placeholders:
        print("\n=== Unmatched Citations ===")
        print(
            "These citations appear in the LaTeX but have no matching bibliography entry:"
        )
        for key in sorted(unmatched_citations):
            print(f"  - {key}")

    if placeholder_entries:
        print("\n=== Placeholder Entries Created ===")
        print(
            "These entries need to be updated with correct bibliographic information:"
        )
        for key in sorted(placeholder_entries):
            print(f"  - {key}")

    if matched_citations:
        print("\n=== Successful Matches ===")
        changed = {k: v for k, v in matched_citations.items() if k != v}
        unchanged = {k: v for k, v in matched_citations.items() if k == v}

        if changed:
            print(f"\nKeys updated ({len(changed)}):")
            for new_key, old_key in sorted(changed.items()):
                print(f"  - {old_key} -> {new_key}")

        if unchanged:
            print(f"\nKeys already correct ({len(unchanged)}):")
            for key in sorted(unchanged.keys())[:10]:  # Show first 10
                print(f"  - {key}")
            if len(unchanged) > 10:
                print(f"  ... and {len(unchanged) - 10} more")


def main():
    """Main entry point."""
    # Define file paths
    data_dir = Path(__file__).parent.parent / "data"
    latex_file = data_dir / "v6_UAD.tex"
    bib_file = data_dir / "references.bib"
    output_file = data_dir / "references_complete.bib"

    # Check files exist
    if not latex_file.exists():
        logger.error(f"LaTeX file not found: {latex_file}")
        sys.exit(1)

    if not bib_file.exists():
        logger.error(f"Bibliography file not found: {bib_file}")
        sys.exit(1)

    # Fix bibliography keys with placeholders
    fix_bibliography_keys(
        latex_file, bib_file, output_file, create_placeholders=True
    )

    print(f"\nComplete bibliography written to: {output_file}")
    print("This file includes placeholders for missing citations.")
    print("Review and update placeholder entries before use.")


if __name__ == "__main__":
    main()
