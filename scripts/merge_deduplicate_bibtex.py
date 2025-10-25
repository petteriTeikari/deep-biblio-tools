#!/usr/bin/env python3
"""Merge and deduplicate BibTeX files with different key formats.

This script handles the common case where:
- One file uses Better BibTeX keys (e.g., held3DConvexSplatting2024)
- Another file uses standard keys (e.g., held2024)
- Both files contain the same entries with different keys
"""

# import re  # Banned - using string methods instead
from pathlib import Path

import bibtexparser
from bibtexparser.bibdatabase import BibDatabase


def extract_standard_key(better_key: str, author: str, year: str) -> str:
    """Convert Better BibTeX key to standard format.

    Args:
        better_key: Better BibTeX key like 'held3DConvexSplatting2024'
        author: First author's last name
        year: Publication year

    Returns:
        Standard key like 'held2024'
    """
    # Extract first author's last name (lowercase)
    if author:
        # Handle author formats like "Held, Jan" or "Jan Held"
        if "," in author:
            last_name = author.split(",")[0].strip().lower()
        else:
            # Assume last word is last name
            last_name = author.split()[-1].strip().lower()
    else:
        # Fall back to extracting from Better BibTeX key
        # Look for lowercase letters followed by uppercase
        last_name = ""
        for i, char in enumerate(better_key):
            if char.isupper():
                break
            if char.islower():
                last_name += char

        if not last_name:
            last_name = better_key[:4].lower()

    return f"{last_name}{year}"


def normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    # Remove LaTeX formatting (braces)
    result = ""
    i = 0
    while i < len(title):
        if title[i] == "{":
            # Find matching close brace
            brace_count = 1
            i += 1
            while i < len(title) and brace_count > 0:
                if title[i] == "{":
                    brace_count += 1
                elif title[i] == "}":
                    brace_count -= 1
                else:
                    result += title[i]
                i += 1
        elif title[i] != "}":
            result += title[i]
            i += 1
        else:
            i += 1

    # Remove punctuation and convert to lowercase
    cleaned = ""
    for char in result.lower():
        if char.isalnum() or char.isspace():
            cleaned += char

    # Normalize whitespace
    return " ".join(cleaned.split())


def extract_identifiers(entry: dict) -> tuple[str | None, str | None, str]:
    """Extract DOI, URL, and normalized title from entry."""
    doi = entry.get("doi", "").strip()
    url = entry.get("url", "").strip()

    # Also check for DOI in URL
    if not doi and url:
        doi_prefix = "doi.org/"
        doi_start = url.find(doi_prefix)
        if doi_start != -1:
            doi_start += len(doi_prefix)
            # Find the end of DOI (space or end of string)
            doi_end = doi_start
            while doi_end < len(url) and not url[doi_end].isspace():
                doi_end += 1
            doi = url[doi_start:doi_end]

    # Normalize title
    title = normalize_title(entry.get("title", ""))

    return doi, url, title


def find_duplicates(
    entries1: dict[str, dict], entries2: dict[str, dict]
) -> dict[str, list[str]]:
    """Find duplicate entries between two sets based on DOI, URL, or title.

    Returns:
        Dict mapping keys from entries1 to list of duplicate keys in entries2
    """
    duplicates = {}

    # Build lookup indices for entries2
    doi_index = {}
    url_index = {}
    title_index = {}

    for key2, entry2 in entries2.items():
        doi, url, title = extract_identifiers(entry2)
        if doi:
            doi_index[doi] = key2
        if url:
            url_index[url] = key2
        if title:
            title_index[title] = key2

    # Find duplicates
    for key1, entry1 in entries1.items():
        doi, url, title = extract_identifiers(entry1)
        duplicate_keys = []

        # Check DOI match (highest confidence)
        if doi and doi in doi_index:
            duplicate_keys.append(doi_index[doi])
        # Check URL match
        elif url and url in url_index:
            duplicate_keys.append(url_index[url])
        # Check title match (lowest confidence)
        elif title and title in title_index:
            duplicate_keys.append(title_index[title])

        if duplicate_keys:
            duplicates[key1] = duplicate_keys

    return duplicates


def detect_key_format(key: str) -> str:
    """Detect if key is standard or Better BibTeX format."""
    # Standard format: author + year + optional suffix
    # Check if it's lowercase letters followed by 4 digits and optional lowercase letter
    if key:
        # Find where digits start
        digit_start = -1
        for i, char in enumerate(key):
            if char.isdigit():
                digit_start = i
                break

        if digit_start > 0:
            # Check if everything before digits is lowercase
            prefix = key[:digit_start]
            if prefix.islower():
                # Check if we have exactly 4 digits
                digit_end = digit_start
                while digit_end < len(key) and key[digit_end].isdigit():
                    digit_end += 1

                if digit_end - digit_start == 4:
                    # Check optional suffix
                    suffix = key[digit_end:]
                    if not suffix or (len(suffix) == 1 and suffix.islower()):
                        return "standard"

        # Better BibTeX format: author + CamelCase + year
        # Look for pattern: lowercase, then uppercase, then mixed case, then 4 digits
        has_lowercase_start = False
        has_uppercase = False
        i = 0

        # Check lowercase start
        while i < len(key) and key[i].islower():
            has_lowercase_start = True
            i += 1

        # Check for uppercase letter
        if i < len(key) and key[i].isupper():
            has_uppercase = True
            i += 1

            # Skip mixed case letters
            while i < len(key) and key[i].isalpha():
                i += 1

            # Check for 4 digits at the end
            if i < len(key):
                digit_count = 0
                digit_start = i
                while i < len(key) and key[i].isdigit():
                    digit_count += 1
                    i += 1

                if digit_count == 4:
                    # Check optional suffix
                    suffix = key[i:]
                    if not suffix or (len(suffix) == 1 and suffix.islower()):
                        if has_lowercase_start and has_uppercase:
                            return "better"

    return "unknown"


def merge_entries(entry1: dict, entry2: dict) -> dict:
    """Merge two entries, preferring non-empty fields."""
    merged = entry1.copy()

    # Add any fields from entry2 that are missing or empty in entry1
    for field, value in entry2.items():
        if field not in merged or not merged[field].strip():
            merged[field] = value

    return merged


def main():
    # File paths
    ref_path = Path("uadReview/references.bib")
    uad_path = Path("uadReview/uad_1st.bib")
    output_path = Path("uadReview/references_deduplicated.bib")

    print("=== BibTeX Merge and Deduplication ===\n")

    # Load both files
    print(f"Loading {ref_path}...")
    with open(ref_path, encoding="utf-8") as f:
        ref_bib = bibtexparser.load(f)

    print(f"Loading {uad_path}...")
    with open(uad_path, encoding="utf-8") as f:
        uad_bib = bibtexparser.load(f)

    print(f"\nEntries in {ref_path.name}: {len(ref_bib.entries)}")
    print(f"Entries in {uad_path.name}: {len(uad_bib.entries)}")

    # Convert to dict format for easier manipulation
    ref_entries = {entry["ID"]: entry for entry in ref_bib.entries}
    uad_entries = {entry["ID"]: entry for entry in uad_bib.entries}

    # Analyze key formats
    ref_formats = {}
    uad_formats = {}

    for key in ref_entries:
        format_type = detect_key_format(key)
        ref_formats[format_type] = ref_formats.get(format_type, 0) + 1

    for key in uad_entries:
        format_type = detect_key_format(key)
        uad_formats[format_type] = uad_formats.get(format_type, 0) + 1

    print(f"\nKey formats in {ref_path.name}: {ref_formats}")
    print(f"Key formats in {uad_path.name}: {uad_formats}")

    # Find duplicates
    print("\nFinding duplicates...")
    duplicates_ref_to_uad = find_duplicates(ref_entries, uad_entries)
    duplicates_uad_to_ref = find_duplicates(uad_entries, ref_entries)

    print(
        f"Found {len(duplicates_ref_to_uad)} entries in {ref_path.name} that exist in {uad_path.name}"
    )
    print(
        f"Found {len(duplicates_uad_to_ref)} entries in {uad_path.name} that exist in {ref_path.name}"
    )

    # Build merged database
    merged_entries = {}
    used_uad_keys = set()

    # First, add all entries from references.bib (standard keys preferred)
    for ref_key, ref_entry in ref_entries.items():
        if ref_key in duplicates_ref_to_uad:
            # This entry has a duplicate in uad_1st.bib
            uad_keys = duplicates_ref_to_uad[ref_key]
            print(f"\nMerging: {ref_key} <- {', '.join(uad_keys)}")

            # Merge information from both entries
            merged_entry = ref_entry.copy()
            for uad_key in uad_keys:
                if uad_key in uad_entries:
                    merged_entry = merge_entries(
                        merged_entry, uad_entries[uad_key]
                    )
                    used_uad_keys.add(uad_key)

            merged_entries[ref_key] = merged_entry
        else:
            # No duplicate, just use the entry as-is
            merged_entries[ref_key] = ref_entry

    # Then, add unique entries from uad_1st.bib
    unique_uad_count = 0
    for uad_key, uad_entry in uad_entries.items():
        if (
            uad_key not in used_uad_keys
            and uad_key not in duplicates_uad_to_ref
        ):
            # This is a unique entry, convert key if it's Better BibTeX format
            if detect_key_format(uad_key) == "better":
                # Convert to standard format
                # Find 4 consecutive digits for year
                year = "0000"
                for i in range(len(uad_key) - 3):
                    if uad_key[i : i + 4].isdigit():
                        year = uad_key[i : i + 4]
                        break

                author = uad_entry.get("author", "")

                new_key = extract_standard_key(uad_key, author, year)

                # Handle collisions
                suffix = ""
                original_new_key = new_key
                while new_key in merged_entries:
                    suffix = (
                        chr(ord("a") + (ord(suffix) - ord("a") + 1))
                        if suffix
                        else "a"
                    )
                    new_key = original_new_key + suffix

                print(f"\nConverting key: {uad_key} -> {new_key}")
                uad_entry["ID"] = new_key
                merged_entries[new_key] = uad_entry
            else:
                merged_entries[uad_key] = uad_entry
            unique_uad_count += 1

    print(f"\nAdded {unique_uad_count} unique entries from {uad_path.name}")

    # Create output database
    output_db = BibDatabase()
    output_db.entries = list(merged_entries.values())

    # Sort by key for consistency
    output_db.entries.sort(key=lambda x: x["ID"])

    # Write output
    print(
        f"\nWriting {len(output_db.entries)} deduplicated entries to {output_path}..."
    )
    with open(output_path, "w", encoding="utf-8") as f:
        bibtexparser.dump(output_db, f)

    print(f"\nSuccessfully created {output_path}")
    print(f"   Total entries: {len(output_db.entries)}")
    print(
        f"   Removed duplicates: {len(ref_entries) + len(uad_entries) - len(output_db.entries)}"
    )

    # Show some examples of merged entries
    print("\n=== Sample Merged Entries ===")
    sample_count = 0
    for ref_key in list(duplicates_ref_to_uad.keys())[:5]:
        if ref_key in merged_entries:
            entry = merged_entries[ref_key]
            print(f"\nKey: {ref_key}")
            print(f"Title: {entry.get('title', 'N/A')[:60]}...")
            print(f"Authors: {entry.get('author', 'N/A')[:60]}...")
            if "doi" in entry:
                print(f"DOI: {entry['doi']}")
            sample_count += 1


if __name__ == "__main__":
    main()
