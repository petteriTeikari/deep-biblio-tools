#!/usr/bin/env python3
"""
Extract bibliography entries with incomplete author names for manual checking.
Creates a separate .bib file with only those entries that need manual verification.
"""

import argparse

# import re  # Banned - using string methods instead
from pathlib import Path

import bibtexparser
from bibtexparser.bwriter import BibTexWriter


def has_incomplete_authors(entry):
    """Check if an entry has incomplete author information."""
    author = entry.get("author", "")

    # Check for validation notes indicating incomplete authors
    note = entry.get("note", "")
    if any(
        phrase in note.lower()
        for phrase in [
            "incomplete author",
            "needs manual fix",
            "needs manual verification",
        ]
    ):
        return True

    # Single-word authors (except known organizations)
    # Check if author contains only letters and hyphens
    is_single_word = True
    for char in author:
        if not (char.isalpha() or char == "-"):
            is_single_word = False
            break

    if is_single_word:
        # Skip if it looks like an organization
        if not (author.isupper() or author in ["CFPB", "FHFA", "MBA", "ACSR"]):
            return True

    # "LastName and others" pattern
    if " and others" in author:
        return True

    # Authors without commas (likely missing first names)
    authors = author.split(" and ")
    for auth in authors:
        auth = auth.strip()
        # Skip organizations
        # Check if contains digits, ampersands, or dots
        has_special = False
        for char in auth:
            if char.isdigit() or char in "&.":
                has_special = True
                break

        if auth.isupper() or has_special:
            continue
        # If no comma and it's not a single-word org name
        if "," not in auth and len(auth.split()) == 1:
            return True

    return False


def extract_incomplete_entries(input_file, output_file):
    """Extract entries with incomplete authors to a separate file."""

    # Read the bibliography
    with open(input_file, encoding="utf-8") as f:
        bib_db = bibtexparser.load(f)

    # Filter entries with incomplete authors
    incomplete_entries = []
    complete_entries = []

    for entry in bib_db.entries:
        if has_incomplete_authors(entry):
            incomplete_entries.append(entry)
        else:
            complete_entries.append(entry)

    # Write incomplete entries to output file
    if incomplete_entries:
        incomplete_db = bibtexparser.bibdatabase.BibDatabase()
        incomplete_db.entries = incomplete_entries

        writer = BibTexWriter()
        writer.indent = "  "
        writer.align_values = True

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(writer.write(incomplete_db))

        print(
            f"Extracted {len(incomplete_entries)} entries with incomplete authors to: {output_file}"
        )
    else:
        print("No entries with incomplete authors found.")

    # Update the original file to remove incomplete entries
    if complete_entries:
        clean_db = bibtexparser.bibdatabase.BibDatabase()
        clean_db.entries = complete_entries

        clean_file = input_file.with_stem(input_file.stem + "_clean")
        with open(clean_file, "w", encoding="utf-8") as f:
            f.write(writer.write(clean_db))

        print(
            f"Created clean bibliography with {len(complete_entries)} complete entries: {clean_file}"
        )

    # Generate summary report
    print("\n" + "=" * 60)
    print("Summary Report")
    print("=" * 60)
    print(f"Total entries: {len(bib_db.entries)}")
    print(f"Incomplete author entries: {len(incomplete_entries)}")
    print(f"Complete entries: {len(complete_entries)}")

    if incomplete_entries:
        print("\nIncomplete author entries (first 10):")
        for entry in incomplete_entries[:10]:
            print(
                f"  - {entry.get('ID', 'unknown')}: {entry.get('author', 'NO AUTHOR')}"
            )
            if "title" in entry:
                print(f"    Title: {entry['title'][:60]}...")

    return len(incomplete_entries), len(complete_entries)


def main():
    parser = argparse.ArgumentParser(
        description="Extract bibliography entries with incomplete authors for manual checking"
    )
    parser.add_argument("input", type=Path, help="Input bibliography file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output file for incomplete entries (default: input_incomplete.bib)",
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        return 1

    # Set default output filename if not provided
    if not args.output:
        args.output = args.input.with_stem(args.input.stem + "_incomplete")

    extract_incomplete_entries(args.input, args.output)

    return 0


if __name__ == "__main__":
    exit(main())
