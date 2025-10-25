#!/usr/bin/env python3
"""
Fix bibliography keys to match LaTeX citations.

This script:
1. Extracts all citation keys from a LaTeX document
2. Analyzes existing bibliography entries to find matches
3. Updates bibliography keys to match those expected by the LaTeX document
"""

import logging

# import re  # Banned - using string methods instead
import sys
from pathlib import Path

import bibtexparser
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


def parse_author_year_from_entry(entry: dict) -> tuple[str, str]:
    """Extract author and year from a bibliography entry."""
    # Get author field
    author = entry.get("author", "")
    year = entry.get("year", "")

    # Extract first author's last name
    if author:
        # Handle "Author et al." format
        if " et al." in author:
            author = author.replace(" et al.", "").strip()
        # Handle "Last, First" format
        elif "," in author:
            author = author.split(",")[0].strip()
        # Handle "First Last" format - take last word
        elif " " in author:
            author = author.split()[-1].strip()
        # Handle "Author and Other" format
        elif " and " in author:
            author = author.split(" and ")[0].strip()
            if " " in author:
                author = author.split()[-1].strip()

    return author.lower(), year


def find_matching_entry(
    target_key: str, entries: list[dict]
) -> tuple[dict, float]:
    """Find the best matching entry for a target citation key."""
    target_author, target_year = parse_author_year_from_key(target_key)

    best_match = None
    best_score = 0.0

    for entry in entries:
        entry_author, entry_year = parse_author_year_from_entry(entry)

        # Calculate match score
        score = 0.0

        # Exact year match
        if target_year and entry_year == target_year:
            score += 0.5

        # Author name matching
        if target_author and entry_author:
            # Exact match
            if target_author == entry_author:
                score += 0.5
            # Partial match (one contains the other)
            elif target_author in entry_author or entry_author in target_author:
                score += 0.3
            # Similar start
            elif target_author[:3] == entry_author[:3]:
                score += 0.2

        if score > best_score:
            best_score = score
            best_match = entry

    return best_match, best_score


def fix_bibliography_keys(latex_file: Path, bib_file: Path, output_file: Path):
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

    # Track changes and issues
    key_mapping = {}
    unmatched_citations = []
    ambiguous_matches = []

    # For each expected citation, find the best matching entry
    for expected_key in sorted(expected_keys):
        # Check if key already exists correctly
        if expected_key in current_entries:
            logger.debug(f"Key '{expected_key}' already exists correctly")
            continue

        # Find best matching entry
        best_entry, best_score = find_matching_entry(
            expected_key, bib_database.entries
        )

        if best_entry and best_score >= 0.5:
            old_key = best_entry["ID"]
            if old_key != expected_key:
                key_mapping[old_key] = expected_key
                logger.info(
                    f"Mapping '{old_key}' -> '{expected_key}' (score: {best_score:.2f})"
                )

                # Check for ambiguity
                if best_score < 1.0:
                    author, year = parse_author_year_from_entry(best_entry)
                    ambiguous_matches.append(
                        f"{expected_key}: matched to {old_key} ({author}, {year}) with score {best_score:.2f}"
                    )
        else:
            unmatched_citations.append(expected_key)
            logger.warning(f"No match found for citation '{expected_key}'")

    # Apply key changes
    for entry in bib_database.entries:
        if entry["ID"] in key_mapping:
            new_key = key_mapping[entry["ID"]]
            logger.info(
                f"Actually changing key from {entry['ID']} to {new_key}"
            )
            entry["ID"] = new_key

    # Write updated bibliography
    logger.info(f"Writing updated bibliography to {output_file}")
    writer = BibTexWriter()
    writer.indent = "  "
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(writer.write(bib_database))

    # Report summary
    print("\n=== Bibliography Key Fix Summary ===")
    print(f"Total citations in LaTeX: {len(expected_keys)}")
    print(
        f"Keys already correct: {len(expected_keys) - len(key_mapping) - len(unmatched_citations)}"
    )
    print(f"Keys updated: {len(key_mapping)}")
    print(f"Unmatched citations: {len(unmatched_citations)}")

    if unmatched_citations:
        print("\n=== Unmatched Citations ===")
        print(
            "These citations appear in the LaTeX but have no matching bibliography entry:"
        )
        for key in sorted(unmatched_citations):
            print(f"  - {key}")

    if ambiguous_matches:
        print("\n=== Ambiguous Matches ===")
        print("These matches may need manual verification:")
        for match in ambiguous_matches:
            print(f"  - {match}")

    if key_mapping:
        print("\n=== Key Mappings Applied ===")
        for old_key, new_key in sorted(key_mapping.items()):
            print(f"  - {old_key} -> {new_key}")


def main():
    """Main entry point."""
    # Define file paths
    data_dir = Path(__file__).parent.parent / "data"
    latex_file = data_dir / "v6_UAD.tex"
    bib_file = data_dir / "references.bib"
    output_file = data_dir / "references_fixed.bib"

    # Check files exist
    if not latex_file.exists():
        logger.error(f"LaTeX file not found: {latex_file}")
        sys.exit(1)

    if not bib_file.exists():
        logger.error(f"Bibliography file not found: {bib_file}")
        sys.exit(1)

    # Fix bibliography keys
    fix_bibliography_keys(latex_file, bib_file, output_file)

    print(f"\nFixed bibliography written to: {output_file}")
    print("Review the changes and rename to 'references.bib' if satisfactory.")


if __name__ == "__main__":
    main()
