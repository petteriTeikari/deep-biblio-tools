#!/usr/bin/env python3
"""Check bibliography issues in uadReview manuscript."""

# import re  # Banned - using string methods instead
from collections import Counter
from pathlib import Path


def extract_citations_from_tex(tex_path):
    """Extract all citations from the tex file."""
    content = tex_path.read_text(encoding="utf-8")
    citations = []

    # Find all \cite{...} and \citep{...} commands
    i = 0
    while i < len(content):
        # Look for \cite or \citep
        if content[i : i + 5] == "\\cite":
            # Check if it's \cite{ or \citep{
            start_idx = i + 5
            if start_idx < len(content) and content[start_idx] == "p":
                start_idx += 1

            if start_idx < len(content) and content[start_idx] == "{":
                # Find closing brace
                brace_count = 1
                j = start_idx + 1
                while j < len(content) and brace_count > 0:
                    if content[j] == "{":
                        brace_count += 1
                    elif content[j] == "}":
                        brace_count -= 1
                    j += 1

                if brace_count == 0:
                    # Extract citation keys
                    cite_content = content[start_idx + 1 : j - 1]
                    # Split by comma for multiple citations
                    keys = [k.strip() for k in cite_content.split(",")]
                    citations.extend(keys)
                    i = j
                    continue

        i += 1

    return citations


def extract_entries_from_bib(bib_path):
    """Extract all entry keys from a bib file."""
    content = bib_path.read_text(encoding="utf-8")
    entries = []

    # Match @type{key,
    i = 0
    while i < len(content):
        if content[i] == "@":
            # Extract entry type
            j = i + 1
            while j < len(content) and (
                content[j].isalnum() or content[j] == "_"
            ):
                j += 1

            if j > i + 1:
                entry_type = content[i + 1 : j].lower()

                # Skip whitespace
                while j < len(content) and content[j] in " \t\n\r":
                    j += 1

                # Check for opening brace
                if j < len(content) and content[j] == "{":
                    # Extract key (everything until comma or whitespace)
                    k = j + 1
                    while k < len(content) and content[k] not in ",\\s\t\n\r}":
                        k += 1

                    if k > j + 1:
                        key = content[j + 1 : k].strip()
                        if key:
                            entries.append((key, entry_type))

                    i = k
                    continue

        i += 1

    return entries


def check_duplicate_entries(entries):
    """Find duplicate entries in bibliography."""
    key_counts = Counter(key for key, _ in entries)
    duplicates = {key: count for key, count in key_counts.items() if count > 1}
    return duplicates


def main():
    # Paths
    tex_path = Path("uadReview/main.tex")
    ref_bib_path = Path("uadReview/references.bib")
    uad_bib_path = Path("uadReview/uad_1st.bib")

    print("=== uadReview Bibliography Analysis ===\n")

    # Extract citations from tex
    print("1. Extracting citations from main.tex...")
    citations = extract_citations_from_tex(tex_path)
    unique_citations = set(citations)
    print(
        f"   Found {len(citations)} total citations ({len(unique_citations)} unique)"
    )

    # Extract entries from references.bib
    print("\n2. Checking references.bib...")
    ref_entries = extract_entries_from_bib(ref_bib_path)
    ref_keys = {key for key, _ in ref_entries}
    print(f"   Found {len(ref_entries)} entries")

    # Check for duplicates in references.bib
    ref_duplicates = check_duplicate_entries(ref_entries)
    if ref_duplicates:
        print("   DUPLICATES FOUND:")
        for key, count in ref_duplicates.items():
            print(f"     - {key}: appears {count} times")
    else:
        print("   No duplicates found")

    # Extract entries from uad_1st.bib
    print("\n3. Checking uad_1st.bib...")
    uad_entries = extract_entries_from_bib(uad_bib_path)
    uad_keys = {key for key, _ in uad_entries}
    print(f"   Found {len(uad_entries)} entries")

    # Check for duplicates in uad_1st.bib
    uad_duplicates = check_duplicate_entries(uad_entries)
    if uad_duplicates:
        print("   DUPLICATES FOUND:")
        for key, count in uad_duplicates.items():
            print(f"     - {key}: appears {count} times")

    # Check overlap between the two bib files
    print("\n4. Checking overlap between references.bib and uad_1st.bib...")
    overlap = ref_keys & uad_keys
    if overlap:
        print(f"   Found {len(overlap)} entries that appear in both files:")
        for key in sorted(overlap)[:10]:  # Show first 10
            print(f"     - {key}")
        if len(overlap) > 10:
            print(f"     ... and {len(overlap) - 10} more")

    # Find missing citations
    print("\n5. Finding missing citations...")
    missing_from_ref = unique_citations - ref_keys
    if missing_from_ref:
        print(
            f"   {len(missing_from_ref)} citations not found in references.bib:"
        )
        for key in sorted(missing_from_ref)[:20]:
            # Check if it's in uad_1st.bib
            if key in uad_keys:
                print(f"     - {key} (found in uad_1st.bib)")
            else:
                print(f"     - {key} (NOT FOUND in either bib file)")
        if len(missing_from_ref) > 20:
            print(f"     ... and {len(missing_from_ref) - 20} more")

    # Check specific problematic entries mentioned in errors
    print("\n6. Checking specific problematic entries from error messages...")
    problematic = [
        "williamson1975",
        "nonaka1995",
        "eriksen2019",
        "kroll2016",
        "hosta2025",
        "pearl2018",
        "hjort2024",
        "mucsnyi2024",
        "kirilenko2017",
        "hllermeier2021",
    ]

    for key in problematic:
        ref_count = sum(1 for k, _ in ref_entries if k == key)
        uad_count = sum(1 for k, _ in uad_entries if k == key)
        print(f"   {key}: references.bib={ref_count}, uad_1st.bib={uad_count}")


if __name__ == "__main__":
    main()
