#!/usr/bin/env python3
"""
Remove unused bibliography entries from a BibTeX file.
"""

# import re  # Banned - using string methods instead
import sys
from pathlib import Path

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.customization import convert_to_unicode


class UnusedEntryRemover:
    def __init__(self, tex_file: Path, bib_file: Path):
        self.tex_file = tex_file
        self.bib_file = bib_file
        self.tex_citations = set()

    def extract_tex_citations(self) -> set[str]:
        """Extract all citation keys from LaTeX file."""
        print(f"Extracting citations from {self.tex_file}...")

        content = self.tex_file.read_text(encoding="utf-8")

        # Find all \cite commands and their variants
        i = 0
        while i < len(content):
            if content[i : i + 5] == "\\cite":
                # Check for optional suffix (like p, t, author, etc.)
                j = i + 5
                while j < len(content) and content[j].islower():
                    j += 1
                # Check for optional asterisk
                if j < len(content) and content[j] == "*":
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
                        keys_str = content[j + 1 : k - 1]
                        # Split by comma
                        keys = keys_str.split(",")
                        for key in keys:
                            key = key.strip()
                            if key:
                                self.tex_citations.add(key)
                        i = k
                        continue
            i += 1

        print(f"Found {len(self.tex_citations)} unique citations in LaTeX")
        return self.tex_citations

    def remove_unused_entries(self):
        """Remove unused entries from bibliography and save cleaned version."""
        print(f"Processing bibliography file: {self.bib_file}")

        # Create parser that accepts all entry types
        parser = BibTexParser()
        parser.ignore_nonstandard_types = False
        parser.homogenize_fields = False
        parser.customization = convert_to_unicode

        # Load bibliography
        with open(self.bib_file, encoding="utf-8") as f:
            bib_database = bibtexparser.load(f, parser=parser)

        print(f"Original bibliography has {len(bib_database.entries)} entries")

        # Get citations used in LaTeX
        used_citations = self.extract_tex_citations()

        # Filter entries - keep only those cited in LaTeX
        original_count = len(bib_database.entries)
        unused_entries = []
        used_entries = []

        for entry in bib_database.entries:
            entry_key = entry.get("ID", "")
            if entry_key in used_citations:
                used_entries.append(entry)
            else:
                unused_entries.append(entry_key)

        # Update database with only used entries
        bib_database.entries = used_entries

        print("\nRemoval summary:")
        print(f"- Original entries: {original_count}")
        print(f"- Used entries: {len(used_entries)}")
        print(f"- Removed entries: {len(unused_entries)}")

        if unused_entries:
            print("\nRemoved entries:")
            for key in sorted(unused_entries):
                print(f"  - {key}")

        # Create backup
        backup_file = self.bib_file.with_suffix(".bib.backup")
        print(f"\nCreating backup: {backup_file}")
        backup_file.write_text(
            self.bib_file.read_text(encoding="utf-8"), encoding="utf-8"
        )

        # Write cleaned bibliography
        writer = BibTexWriter()
        writer.indent = "  "  # 2 spaces
        writer.align_values = True
        writer.order_entries_by = "ID"
        writer.add_trailing_comma = True

        cleaned_content = writer.write(bib_database)

        # Save cleaned file
        self.bib_file.write_text(cleaned_content, encoding="utf-8")
        print(f"Cleaned bibliography saved to: {self.bib_file}")

        return len(unused_entries)


def main():
    # Default paths
    tex_file = Path("uadReview/main.tex")
    bib_file = Path("uadReview/references.bib")

    # Allow command line override
    if len(sys.argv) > 1:
        tex_file = Path(sys.argv[1])
    if len(sys.argv) > 2:
        bib_file = Path(sys.argv[2])

    # Check files exist
    if not tex_file.exists():
        print(f"Error: LaTeX file not found: {tex_file}")
        sys.exit(1)
    if not bib_file.exists():
        print(f"Error: Bibliography file not found: {bib_file}")
        sys.exit(1)

    # Show action
    print("Removing unused bibliography entries from your .bib file.")
    print(f"LaTeX file: {tex_file}")
    print(f"Bibliography file: {bib_file}")
    print("(A backup will be created automatically)")

    # Remove unused entries
    remover = UnusedEntryRemover(tex_file, bib_file)
    removed_count = remover.remove_unused_entries()

    print(f"\nSuccessfully removed {removed_count} unused entries!")
    print(f"Backup created at {bib_file.with_suffix('.bib.backup')}")
    print(f"Cleaned bibliography saved to {bib_file}")


if __name__ == "__main__":
    main()
