"""BibTeX handling functionality."""

from pathlib import Path
from typing import Any

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter


class BibtexHandler:
    """Handle BibTeX parsing and formatting."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}

    def parse_bibtex(self, path: Path) -> list[dict[str, Any]]:
        """Parse a BibTeX file."""
        content = path.read_text(encoding="utf-8")

        parser = BibTexParser(common_strings=True)
        parser.ignore_nonstandard_types = False
        parser.homogenize_fields = False

        try:
            bib_database = bibtexparser.loads(content, parser=parser)
        except Exception as e:
            raise ValueError(f"Failed to parse BibTeX: {str(e)}")

        references = []
        for entry in bib_database.entries:
            ref = {
                "key": entry.get("ID", ""),
                "type": entry.get("ENTRYTYPE", "misc"),
                "raw": entry.get("raw", ""),
            }

            # Copy all fields
            for field, value in entry.items():
                if field not in ["ID", "ENTRYTYPE", "raw"]:
                    ref[field.lower()] = value

            references.append(ref)

        return references

    def format_bibtex(self, references: list[dict[str, Any]]) -> str:
        """Format references as BibTeX."""
        bib_database = bibtexparser.bibdatabase.BibDatabase()

        for ref in references:
            entry = {
                "ID": ref.get("key", self._generate_key(ref)),
                "ENTRYTYPE": ref.get("type", "misc"),
            }

            # Map common fields
            field_mapping = {
                "author": "author",
                "title": "title",
                "year": "year",
                "journal": "journal",
                "volume": "volume",
                "number": "number",
                "pages": "pages",
                "publisher": "publisher",
                "doi": "doi",
                "url": "url",
                "isbn": "isbn",
                "booktitle": "booktitle",
                "editor": "editor",
                "series": "series",
                "address": "address",
                "month": "month",
                "note": "note",
            }

            for bib_field, ref_field in field_mapping.items():
                if ref_field in ref and ref[ref_field]:
                    entry[bib_field] = str(ref[ref_field])

            bib_database.entries.append(entry)

        # Write to string
        writer = BibTexWriter()
        writer.indent = "  "
        writer.order_entries_by = None
        writer.align_values = True

        return bibtexparser.dumps(bib_database, writer)

    def _generate_key(self, ref: dict[str, Any]) -> str:
        """Generate a BibTeX key from reference data."""
        # Try to extract author last name
        author = ref.get("author", "")
        if author:
            # Simple extraction of first author's last name
            if "," in author:
                last_name = author.split(",")[0].strip()
            else:
                words = author.split()
                last_name = words[-1] if words else "Unknown"
        else:
            last_name = "Unknown"

        # Get year
        year = ref.get("year", "0000")

        # Clean last name
        last_name = "".join(c for c in last_name if c.isalnum())

        return f"{last_name}{year}"

    def merge_bibliographies(self, bib_files: list[Path]) -> str:
        """Merge multiple BibTeX files."""
        all_entries = {}

        for bib_file in bib_files:
            references = self.parse_bibtex(bib_file)
            for ref in references:
                key = ref.get("key", "")
                if key:
                    # Keep the most complete entry
                    if key not in all_entries or len(str(ref)) > len(
                        str(all_entries[key])
                    ):
                        all_entries[key] = ref

        # Format merged bibliography
        return self.format_bibtex(list(all_entries.values()))
