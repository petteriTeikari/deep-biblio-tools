"""BibTeX parser using bibtexparser."""

import logging

# import re  # Banned - using string methods instead
from typing import Any

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode

from .base import ParsedDocument, ParsedNode, StructuredParser

logger = logging.getLogger(__name__)


class BibtexParser(StructuredParser):
    """Parser for BibTeX files using bibtexparser."""

    def __init__(self):
        """Initialize BibTeX parser."""
        self.parser = BibTexParser(common_strings=True)
        self.parser.customization = convert_to_unicode
        self.parser.ignore_nonstandard_types = False

    def parse(self, text: str) -> ParsedDocument:
        """Parse BibTeX text into structured document."""
        try:
            # Check for entries with empty IDs before parsing without regex
            if self._has_empty_id_entries(text):
                logger.warning("Found entry with empty ID")

            bib_database = bibtexparser.loads(text, parser=self.parser)
        except Exception as e:
            logger.error(f"BibTeX parsing error: {e}")
            return ParsedDocument(
                raw_text=text, nodes=[], metadata={"parse_error": str(e)}
            )

        # Convert BibTeX entries to ParsedNodes
        nodes = []
        for entry in bib_database.entries:
            node = self._entry_to_node(entry, text)
            if node:
                nodes.append(node)

        # Extract metadata
        metadata = {
            "num_entries": len(bib_database.entries),
            "num_comments": len(bib_database.comments),
            "num_strings": len(bib_database.strings),
            "entry_types": list(
                set(
                    e.get("ENTRYTYPE", "").lower() for e in bib_database.entries
                )
            ),
        }

        # Check for entries with empty IDs in raw text without regex
        empty_id_types = self._find_empty_id_entries(text)
        if empty_id_types:
            metadata["has_empty_ids"] = True
            metadata["empty_id_count"] = len(empty_id_types)

        return ParsedDocument(raw_text=text, nodes=nodes, metadata=metadata)

    def _entry_to_node(
        self, entry: dict[str, str], text: str
    ) -> ParsedNode | None:
        """Convert BibTeX entry to ParsedNode."""
        entry_type = entry.get("ENTRYTYPE", "unknown").lower()
        entry_id = entry.get("ID", "")

        # Try to find position in text (approximate)
        search_pattern = f"@{entry_type}{{{entry_id},"
        start_pos = text.find(search_pattern)
        if start_pos == -1:
            # Try case-insensitive search
            search_pattern_lower = search_pattern.lower()
            text_lower = text.lower()
            start_pos = text_lower.find(search_pattern_lower)

        if start_pos == -1:
            start_pos = 0
            end_pos = len(text)
        else:
            # Find the closing brace
            brace_count = 0
            end_pos = start_pos
            for i in range(start_pos, len(text)):
                if text[i] == "{":
                    brace_count += 1
                elif text[i] == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        end_pos = i + 1
                        break

        line_no = text[:start_pos].count("\n") + 1
        col_no = start_pos - text.rfind("\n", 0, start_pos) - 1

        # Create metadata
        metadata = {
            "entry_type": entry_type,
            "entry_id": entry_id,
            "fields": {
                k: v for k, v in entry.items() if k not in ["ENTRYTYPE", "ID"]
            },
        }

        # Create child nodes for each field
        children = []
        for field_name, field_value in entry.items():
            if field_name not in ["ENTRYTYPE", "ID"]:
                field_node = ParsedNode(
                    type="field",
                    content=field_value,
                    start_pos=start_pos,  # Approximate
                    end_pos=end_pos,  # Approximate
                    line_no=line_no,
                    col_no=col_no,
                    metadata={"field_name": field_name},
                    children=[],
                )
                children.append(field_node)

        return ParsedNode(
            type="entry",
            content=entry_id,
            start_pos=start_pos,
            end_pos=end_pos,
            line_no=line_no,
            col_no=col_no,
            metadata=metadata,
            children=children,
        )

    def validate(self, text: str) -> list[str]:
        """Validate BibTeX text and return errors."""
        errors = []

        try:
            doc = self.parse(text)

            # Check for parse errors
            if "parse_error" in doc.metadata:
                errors.append(f"Parse error: {doc.metadata['parse_error']}")
                return errors

            # Check for empty IDs that parser might have missed
            if doc.metadata.get("has_empty_ids", False):
                errors.append(
                    f"Found {doc.metadata.get('empty_id_count', 0)} entries with empty ID"
                )

            # Check entries
            for node in doc.nodes:
                if node.type == "entry":
                    # Check for missing required fields
                    entry_type = node.metadata.get("entry_type", "")
                    fields = node.metadata.get("fields", {})

                    # Check for empty ID
                    if not node.content or node.content.strip() == "":
                        errors.append(
                            f"Entry at line {node.line_no} has empty ID"
                        )

                    # Check required fields based on entry type
                    required_fields = self._get_required_fields(entry_type)
                    for field in required_fields:
                        if field not in fields:
                            errors.append(
                                f"Entry '{node.content}' missing required field: {field}"
                            )

                    # Check for duplicate IDs (simple check)
                    all_ids = [
                        n.content for n in doc.nodes if n.type == "entry"
                    ]
                    if all_ids.count(node.content) > 1:
                        errors.append(f"Duplicate entry ID: {node.content}")

        except Exception as e:
            errors.append(f"Validation error: {str(e)}")

        return errors

    def _get_required_fields(self, entry_type: str) -> list[str]:
        """Get required fields for entry type."""
        required = {
            "article": ["author", "title", "journal", "year"],
            "book": ["author", "title", "publisher", "year"],
            "inproceedings": ["author", "title", "booktitle", "year"],
            "incollection": ["author", "title", "booktitle", "year"],
            "phdthesis": ["author", "title", "school", "year"],
            "mastersthesis": ["author", "title", "school", "year"],
            "techreport": ["author", "title", "institution", "year"],
            "unpublished": ["author", "title", "note"],
        }
        return required.get(entry_type.lower(), ["author", "title", "year"])

    def extract_entries(self, text: str) -> list[dict[str, Any]]:
        """Extract all entries from BibTeX text."""
        doc = self.parse(text)
        entries = []

        for node in doc.nodes:
            if node.type == "entry":
                entry_info = {
                    "id": node.content,
                    "type": node.metadata.get("entry_type", ""),
                    "fields": node.metadata.get("fields", {}),
                    "position": (node.start_pos, node.end_pos),
                    "line": node.line_no,
                    "column": node.col_no,
                }
                entries.append(entry_info)

        return entries

    def get_entry_by_id(
        self, text: str, entry_id: str
    ) -> dict[str, Any] | None:
        """Get specific entry by ID."""
        entries = self.extract_entries(text)
        for entry in entries:
            if entry["id"] == entry_id:
                return entry
        return None

    def extract_field(
        self, text: str, entry_id: str, field_name: str
    ) -> str | None:
        """Extract specific field from entry."""
        entry = self.get_entry_by_id(text, entry_id)
        if entry:
            return entry["fields"].get(field_name)
        return None

    def update_field(
        self, text: str, entry_id: str, field_name: str, new_value: str
    ) -> str:
        """Update field value in BibTeX entry."""
        # Parse the text
        bib_database = bibtexparser.loads(text, parser=self.parser)

        # Find and update the entry
        for entry in bib_database.entries:
            if entry.get("ID") == entry_id:
                entry[field_name] = new_value
                break

        # Convert back to string
        return bibtexparser.dumps(bib_database)

    def _has_empty_id_entries(self, text: str) -> bool:
        """Check if text contains entries with empty IDs."""
        # Look for pattern @type{, without regex
        i = 0
        while i < len(text):
            if text[i] == "@":
                # Found @, check if it's followed by entry type
                j = i + 1
                # Skip entry type (alphanumeric)
                while j < len(text) and (text[j].isalnum() or text[j] == "_"):
                    j += 1
                # Skip whitespace
                while j < len(text) and text[j].isspace():
                    j += 1
                # Check if followed by {
                if j < len(text) and text[j] == "{":
                    # Skip whitespace after {
                    k = j + 1
                    while k < len(text) and text[k].isspace():
                        k += 1
                    # Check if followed by comma (empty ID)
                    if k < len(text) and text[k] == ",":
                        return True
            i += 1
        return False

    def _find_empty_id_entries(self, text: str) -> list[str]:
        """Find all entry types that have empty IDs."""
        empty_types = []
        i = 0
        while i < len(text):
            if text[i] == "@":
                # Found @, extract entry type
                j = i + 1
                entry_type = []
                while j < len(text) and (text[j].isalnum() or text[j] == "_"):
                    entry_type.append(text[j])
                    j += 1
                entry_type_str = "".join(entry_type)

                # Skip whitespace
                while j < len(text) and text[j].isspace():
                    j += 1
                # Check if followed by {
                if j < len(text) and text[j] == "{":
                    # Skip whitespace after {
                    k = j + 1
                    while k < len(text) and text[k].isspace():
                        k += 1
                    # Check if followed by comma (empty ID)
                    if k < len(text) and text[k] == ",":
                        empty_types.append(entry_type_str)
            i += 1
        return empty_types
