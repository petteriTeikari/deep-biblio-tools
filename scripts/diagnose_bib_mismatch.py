"""Diagnostic script to detect citation key mismatches in .bib file.

This script reads a .bib file and checks if the citation keys match the actual
author names and titles in the entries.
"""

from pathlib import Path

import bibtexparser


def diagnose_bib_file(bib_path: Path) -> None:
    """Diagnose citation key mismatches in BibTeX file."""

    with open(bib_path) as bib_file:
        bib_database = bibtexparser.load(bib_file)

    print(f"Analyzing {len(bib_database.entries)} BibTeX entries...\n")

    mismatches = []

    for entry in bib_database.entries:
        cite_key = entry.get("ID", "")
        author = entry.get("author", "")
        title = entry.get("title", "")
        year = entry.get("year", "")

        # Extract first author's last name
        if author:
            # Simple extraction - first word before space or comma
            first_author = author.split()[0].split(",")[0].lower()
        else:
            first_author = "unknown"

        # Extract first word from key (before underscore or number)
        key_parts = cite_key.replace("_", " ").split()
        key_parts[0].lower() if key_parts else ""

        # Check if first author appears in citation key
        if (
            first_author not in cite_key.lower()
            and "dryrun" not in cite_key.lower()
        ):
            mismatches.append(
                {
                    "key": cite_key,
                    "author": author[:80],
                    "title": title[:60] if title else "No title",
                    "year": year,
                    "expected_author": first_author,
                }
            )

    print(f"Found {len(mismatches)} potential mismatches:\n")
    print("=" * 100)

    for i, mismatch in enumerate(mismatches[:50], 1):  # Show first 50
        print(f"\n{i}. Key: {mismatch['key']}")
        print(f"   Expected author: {mismatch['expected_author']}")
        print(f"   Actual author:   {mismatch['author']}")
        print(f"   Title:           {mismatch['title']}")
        print(f"   Year:            {mismatch['year']}")

    if len(mismatches) > 50:
        print(f"\n... and {len(mismatches) - 50} more mismatches")

    print("\n" + "=" * 100)
    print(
        f"\nSummary: {len(mismatches)} / {len(bib_database.entries)} entries have mismatched keys"
    )
    print(
        f"Success rate: {100 * (len(bib_database.entries) - len(mismatches)) / len(bib_database.entries):.1f}%"
    )


if __name__ == "__main__":
    bib_path = Path(
        "/home/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/output/references.bib"
    )
    diagnose_bib_file(bib_path)
