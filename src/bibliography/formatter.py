"""Citation key formatting for bibliography entries."""

# import re  # Banned - using string methods instead

from .core import Bibliography, BibliographyEntry, BibliographyProcessor


class CitationKeyFormatter(BibliographyProcessor):
    """Format citation keys in various styles.

    This class consolidates functionality from:
    - bib_key_fixes.py
    - convert_bib_keys_to_authoryear.py
    - convert_arxiv_citekey_authoryear.py
    """

    def __init__(self):
        """Initialize formatter."""
        self.processed_keys = set()

    def process(self, bibliography: Bibliography) -> None:
        """Process all entries in bibliography.

        Args:
            bibliography: Bibliography to process
        """
        # Clear processed keys for new bibliography
        self.processed_keys.clear()

        for entry in bibliography:
            self.process_entry(entry)

    def process_entry(self, entry: BibliographyEntry) -> None:
        """Process a single entry (required by base class).

        Args:
            entry: Entry to process
        """
        # Default implementation does nothing
        # Specific formatting is done by individual methods
        pass

    def to_authoryear(self, entry: BibliographyEntry) -> str:
        """Convert entry to Author2023 format.

        Args:
            entry: Bibliography entry

        Returns:
            Formatted citation key
        """
        # Get author information
        author = entry.get_field("author", "")
        if not author:
            # Try editor if no author
            author = entry.get_field("editor", "Unknown")

        # Extract first author's last name
        # Handle "Last, First" and "First Last" formats
        if "," in author:
            # "Last, First" format
            first_author = author.split("and")[0].strip()
            last_name = first_author.split(",")[0].strip()
        else:
            # "First Last" format
            first_author = author.split("and")[0].strip()
            parts = first_author.split()
            last_name = parts[-1] if parts else "Unknown"

        # Remove special characters from name without regex
        # Only keep ASCII letters
        cleaned_chars = []
        for char in last_name:
            if char.isalpha() and ord(char) < 128:
                cleaned_chars.append(char)
        last_name = "".join(cleaned_chars)

        # Get year
        year = entry.get_field("year", "")
        if not year:
            # Try to extract from date field
            date = entry.get_field("date", "")
            if date and len(date) >= 4:
                year = date[:4]
            else:
                year = "NoYear"

        # Create base key
        base_key = f"{last_name}{year}"

        # Handle duplicates
        if base_key in self.processed_keys:
            suffix = "a"
            while f"{base_key}{suffix}" in self.processed_keys:
                suffix = chr(ord(suffix) + 1)
            key = f"{base_key}{suffix}"
        else:
            key = base_key

        self.processed_keys.add(key)
        return key

    def to_numeric(self, entries: list[BibliographyEntry]) -> dict[str, str]:
        """Convert entries to numeric format [1], [2], etc.

        Args:
            entries: List of bibliography entries

        Returns:
            Mapping of old keys to numeric keys
        """
        key_mapping = {}
        for i, entry in enumerate(entries, 1):
            key_mapping[entry.key] = str(i)
        return key_mapping

    def fix_arxiv_keys(self, bibliography: Bibliography) -> None:
        """Fix arXiv-specific citation keys.

        Converts keys like "2023arXiv230112345S" to "Smith2023arxiv"

        Args:
            bibliography: Bibliography to process
        """
        updates = []

        for entry in bibliography:
            if self._is_arxiv_entry(entry):
                old_key = entry.key
                new_key = self._format_arxiv_key(entry)

                if old_key != new_key:
                    # Create new entry with updated key
                    new_entry = BibliographyEntry(
                        entry.entry_type, new_key, entry.fields.copy()
                    )
                    updates.append((old_key, new_entry))

        # Apply updates
        for old_key, new_entry in updates:
            bibliography.remove_entry(old_key)
            bibliography.add_entry(new_entry)

    def _is_arxiv_entry(self, entry: BibliographyEntry) -> bool:
        """Check if entry is from arXiv.

        Args:
            entry: Bibliography entry

        Returns:
            True if arXiv entry
        """
        # Check various fields that indicate arXiv
        eprint = entry.get_field("eprint", "")
        journal = entry.get_field("journal", "")
        archiveprefix = entry.get_field("archiveprefix", "")

        return (
            "arxiv" in eprint.lower()
            or "arxiv" in journal.lower()
            or archiveprefix.lower() == "arxiv"
        )

    def _format_arxiv_key(self, entry: BibliographyEntry) -> str:
        """Format arXiv entry key as AuthorYYYYarxiv.

        Args:
            entry: arXiv bibliography entry

        Returns:
            Formatted key
        """
        # Get base authoryear key
        base_key = self.to_authoryear(entry)

        # Append 'arxiv' if not already present
        if not base_key.lower().endswith("arxiv"):
            return f"{base_key}arxiv"
        return base_key

    def standardize_keys(
        self, bibliography: Bibliography, style: str = "authoryear"
    ) -> None:
        """Standardize all citation keys in bibliography.

        Args:
            bibliography: Bibliography to process
            style: Citation style ('authoryear' or 'numeric')
        """
        if style == "authoryear":
            updates = []

            for entry in bibliography:
                old_key = entry.key
                new_key = self.to_authoryear(entry)

                if old_key != new_key:
                    new_entry = BibliographyEntry(
                        entry.entry_type, new_key, entry.fields.copy()
                    )
                    updates.append((old_key, new_entry))

            # Apply updates
            for old_key, new_entry in updates:
                bibliography.remove_entry(old_key)
                bibliography.add_entry(new_entry)

        elif style == "numeric":
            # Numeric style requires updating all entries at once
            raise NotImplementedError("Numeric style not yet implemented")
        else:
            raise ValueError(f"Unknown citation style: {style}")
