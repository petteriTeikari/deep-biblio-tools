#!/usr/bin/env python3
"""Debug script to check bibliography sorting."""

from pathlib import Path

from hardcode_bibliography import BibliographyHardcoder

# Create hardcoder instance
hardcoder = BibliographyHardcoder()

# Parse bibliography
bib_path = Path("Drone_Position/references.bib")
entries = hardcoder.parse_bib_file(bib_path)

# Get sort keys for first 20 entries
sorted_entries = sorted(
    entries.items(), key=lambda x: hardcoder._get_sort_key(x[1])
)

print("First 20 entries with their sort keys:")
print("-" * 80)
for i, (key, entry) in enumerate(sorted_entries[:20]):
    sort_key = hardcoder._get_sort_key(entry)
    # Extract just the surname part from sort_key (before underscore)
    surname_part = sort_key.split("_")[0]
    # Debug: also show the first author split
    first_author = (
        entry.authors.split(" and ")[0].strip()
        if " and " in entry.authors
        else entry.authors.strip()
    )
    parts = first_author.split()
    print(
        f"{i + 1:2d}. {surname_part:20s} <- {entry.authors[:60]}... (parts: {parts})"
    )

print("\n" + "-" * 80)
print("Full sort keys for first 10:")
for i, (key, entry) in enumerate(sorted_entries[:10]):
    sort_key = hardcoder._get_sort_key(entry)
    print(f"{i + 1:2d}. {sort_key[:80]}...")
