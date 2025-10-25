#!/usr/bin/env python3
"""
Fix bibliography entries to resolve BibTeX compilation issues.
"""

# import re  # Banned - using string methods instead
import sys
from pathlib import Path

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.customization import convert_to_unicode


class BibliographyCompilationFixer:
    def __init__(self, bib_file: Path):
        self.bib_file = bib_file
        self.fixes_applied = []

    def fix_entry_types(self, entry):
        """Convert non-standard entry types to standard ones."""
        entry_type = entry.get("ENTRYTYPE", "").lower()

        # Map non-standard types to standard ones
        type_mapping = {
            "online": "misc",
            "report": "techreport",
            "software": "misc",
            "webpage": "misc",
            "website": "misc",
        }

        if entry_type in type_mapping:
            old_type = entry["ENTRYTYPE"]
            entry["ENTRYTYPE"] = type_mapping[entry_type]
            self.fixes_applied.append(
                f"Changed {entry['ID']}: @{old_type} → @{entry['ENTRYTYPE']}"
            )

        return entry

    def fix_missing_years(self, entry):
        """Extract year from date field or URL if year is missing."""
        if "year" not in entry or not entry["year"].strip():
            # Try to extract from date field
            if "date" in entry and entry["date"]:
                # Look for 4 consecutive digits
                date_str = entry["date"]
                for i in range(len(date_str) - 3):
                    if date_str[i : i + 4].isdigit():
                        entry["year"] = date_str[i : i + 4]
                        self.fixes_applied.append(
                            f"Added year to {entry['ID']}: {entry['year']}"
                        )
                        return entry

            # Try to extract from URL or urldate
            for field in ["url", "urldate"]:
                if field in entry and entry[field]:
                    # Look for 4 consecutive digits
                    field_str = entry[field]
                    for i in range(len(field_str) - 3):
                        if field_str[i : i + 4].isdigit():
                            entry["year"] = field_str[i : i + 4]
                            self.fixes_applied.append(
                                f"Added year to {entry['ID']} from {field}: {entry['year']}"
                            )
                            return entry

            # Default year if none found
            entry["year"] = "2024"
            self.fixes_applied.append(
                f"Added default year to {entry['ID']}: 2024"
            )

        return entry

    def fix_missing_journals(self, entry):
        """Add journal field for articles that are missing it."""
        entry_type = entry.get("ENTRYTYPE", "").lower()

        if entry_type == "article" and (
            "journal" not in entry or not entry["journal"].strip()
        ):
            # Try to infer from other fields
            if "url" in entry and entry["url"]:
                url = entry["url"].lower()
                if "arxiv.org" in url:
                    entry["journal"] = "arXiv preprint"
                elif "github.com" in url:
                    entry["journal"] = "GitHub repository"
                elif "blog" in url or "medium.com" in url:
                    entry["journal"] = "Blog post"
                else:
                    entry["journal"] = "Online resource"

                self.fixes_applied.append(
                    f"Added journal to {entry['ID']}: {entry['journal']}"
                )
            else:
                entry["journal"] = "Unpublished"
                self.fixes_applied.append(
                    f"Added default journal to {entry['ID']}: Unpublished"
                )

        return entry

    def fix_author_formatting(self, entry):
        """Fix complex author name formatting that causes BibTeX errors."""
        if "author" in entry and entry["author"]:
            original_author = entry["author"]
            author = original_author

            # Fix complex family/given/prefix patterns
            # Look for family=Name, given=First, prefix=de, useprefix=true patterns
            if "family=" in author and "given=" in author:
                # Parse the complex format manually
                parts = {}
                current_pos = 0
                while current_pos < len(author):
                    for field_name in [
                        "family",
                        "given",
                        "prefix",
                        "useprefix",
                    ]:
                        field_start = author.find(field_name + "=", current_pos)
                        if field_start != -1:
                            field_start += len(field_name) + 1
                            # Find the end of this field value
                            field_end = field_start
                            while (
                                field_end < len(author)
                                and author[field_end] not in ",;"
                            ):
                                field_end += 1
                            parts[field_name] = author[
                                field_start:field_end
                            ].strip()
                            current_pos = field_end
                    else:
                        current_pos += 1

                # Reconstruct author if we found the needed parts
                if "family" in parts and "given" in parts:
                    if "prefix" in parts:
                        author = f"{parts['prefix']} {parts['family']}, {parts['given']}".strip()
                    else:
                        author = f"{parts['family']}, {parts['given']}".strip()

            # Fix patterns where there are too many commas
            # Remove extra metadata that BibTeX can't handle
            for metadata_field in [
                "prefix=",
                "useprefix=",
                "family=",
                "given=",
            ]:
                while metadata_field in author:
                    start_pos = author.find(", " + metadata_field)
                    if start_pos == -1:
                        start_pos = author.find("," + metadata_field)
                    if start_pos == -1:
                        break
                    # Find the end of this metadata
                    end_pos = start_pos + len(metadata_field) + 2
                    while end_pos < len(author) and author[end_pos] not in ",;":
                        end_pos += 1
                    author = author[:start_pos] + author[end_pos:]

            if author != original_author:
                entry["author"] = author
                self.fixes_applied.append(
                    f"Fixed author formatting for {entry['ID']}: {author[:50]}..."
                )

        return entry

    def fix_special_characters(self, entry):
        """Fix special characters that cause issues."""
        for field in ["title", "author", "journal"]:
            if field in entry and entry[field]:
                original = entry[field]
                # Fix specific character issues
                fixed = original.replace("", "ä")  # Common encoding issue

                if fixed != original:
                    entry[field] = fixed
                    self.fixes_applied.append(
                        f"Fixed special characters in {entry['ID']}.{field}"
                    )

        return entry

    def remove_duplicates(self, entries):
        """Remove duplicate entries."""
        seen_ids = set()
        unique_entries = []

        for entry in entries:
            entry_id = entry.get("ID", "")
            if entry_id not in seen_ids:
                seen_ids.add(entry_id)
                unique_entries.append(entry)
            else:
                self.fixes_applied.append(
                    f"Removed duplicate entry: {entry_id}"
                )

        return unique_entries

    def fix_bibliography(self):
        """Apply all fixes to the bibliography."""
        print(f"Fixing bibliography compilation issues: {self.bib_file}")

        # Create parser that accepts all entry types
        parser = BibTexParser()
        parser.ignore_nonstandard_types = False
        parser.homogenize_fields = False
        parser.customization = convert_to_unicode

        # Load bibliography
        with open(self.bib_file, encoding="utf-8") as f:
            bib_database = bibtexparser.load(f, parser=parser)

        print(f"Original entries: {len(bib_database.entries)}")

        # Apply fixes to each entry
        fixed_entries = []
        for entry in bib_database.entries:
            # Apply all fixes
            entry = self.fix_entry_types(entry)
            entry = self.fix_missing_years(entry)
            entry = self.fix_missing_journals(entry)
            entry = self.fix_author_formatting(entry)
            entry = self.fix_special_characters(entry)
            fixed_entries.append(entry)

        # Remove duplicates
        fixed_entries = self.remove_duplicates(fixed_entries)

        # Update database
        bib_database.entries = fixed_entries

        # Create backup
        backup_file = self.bib_file.with_suffix(".bib.compilation_backup")
        print(f"Creating backup: {backup_file}")
        backup_file.write_text(
            self.bib_file.read_text(encoding="utf-8"), encoding="utf-8"
        )

        # Write fixed bibliography
        writer = BibTexWriter()
        writer.indent = "  "
        writer.align_values = True
        writer.order_entries_by = "ID"
        writer.add_trailing_comma = True

        fixed_content = writer.write(bib_database)

        # Save fixed file
        self.bib_file.write_text(fixed_content, encoding="utf-8")

        print("\nFixes applied:")
        for fix in self.fixes_applied:
            print(f"  - {fix}")

        print(f"\nFixed bibliography saved to: {self.bib_file}")
        print(f"Backup saved to: {backup_file}")
        print(f"Final entries: {len(bib_database.entries)}")

        return len(self.fixes_applied)


def main():
    bib_file = Path("uadReview/references.bib")

    if len(sys.argv) > 1:
        bib_file = Path(sys.argv[1])

    if not bib_file.exists():
        print(f"Error: Bibliography file not found: {bib_file}")
        sys.exit(1)

    fixer = BibliographyCompilationFixer(bib_file)
    fixes_count = fixer.fix_bibliography()

    print(f"\nApplied {fixes_count} fixes to resolve compilation issues!")
    print("\nNow try running the LaTeX compilation sequence:")
    print("1. pdflatex main.tex")
    print("2. bibtex main")
    print("3. pdflatex main.tex")
    print("4. pdflatex main.tex")


if __name__ == "__main__":
    main()
