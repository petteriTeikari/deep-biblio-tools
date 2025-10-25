"""Core classes for bibliography processing."""

# Standard library imports
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

# Third-party imports
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.customization import convert_to_unicode

# Local imports
from src.core.exceptions import ParsingError


class BibliographyEntry:
    """Represents a single bibliography entry.

    This class encapsulates a bibliography entry with its type, citation key,
    and field data. It provides methods for validation and manipulation.
    """

    def __init__(self, entry_type: str, key: str, fields: dict[str, Any]):
        """Initialize a bibliography entry.

        Args:
            entry_type: The type of entry (e.g., 'article', 'book', 'inproceedings')
            key: The citation key (e.g., 'Smith2023')
            fields: Dictionary of field names to values
        """
        self.entry_type = entry_type.lower()
        self.key = key
        self.fields = fields

    def get_field(self, field_name: str, default: Any = None) -> Any:
        """Get a field value with optional default.

        Args:
            field_name: Name of the field to retrieve
            default: Default value if field doesn't exist

        Returns:
            Field value or default
        """
        return self.fields.get(field_name, default)

    def set_field(self, field_name: str, value: Any) -> None:
        """Set a field value.

        Args:
            field_name: Name of the field to set
            value: Value to set
        """
        self.fields[field_name] = value

    def has_field(self, field_name: str) -> bool:
        """Check if a field exists.

        Args:
            field_name: Name of the field to check

        Returns:
            True if field exists, False otherwise
        """
        return field_name in self.fields

    def to_bibtex_dict(self) -> dict[str, Any]:
        """Convert to bibtexparser format dictionary.

        Returns:
            Dictionary in bibtexparser format
        """
        result = {
            "ENTRYTYPE": self.entry_type,
            "ID": self.key,
        }
        result.update(self.fields)
        return result

    @classmethod
    def from_bibtex_dict(
        cls, bibtex_dict: dict[str, Any]
    ) -> "BibliographyEntry":
        """Create from bibtexparser format dictionary.

        Args:
            bibtex_dict: Dictionary in bibtexparser format

        Returns:
            BibliographyEntry instance
        """
        entry_type = bibtex_dict.pop("ENTRYTYPE", "misc")
        key = bibtex_dict.pop("ID", "")
        return cls(entry_type, key, bibtex_dict)

    def __repr__(self) -> str:
        """String representation of the entry."""
        return f"BibliographyEntry(type='{self.entry_type}', key='{self.key}')"


class Bibliography:
    """Collection of bibliography entries with operations.

    This class manages a collection of bibliography entries and provides
    methods for loading, saving, and manipulating bibliographies.
    """

    def __init__(self):
        """Initialize an empty bibliography."""
        self.entries: list[BibliographyEntry] = []
        self._key_index: dict[str, int] = {}  # Maps keys to entry indices

    def add_entry(self, entry: BibliographyEntry) -> None:
        """Add an entry to the bibliography.

        Args:
            entry: BibliographyEntry to add

        Raises:
            ValueError: If an entry with the same key already exists
        """
        if entry.key in self._key_index:
            raise ValueError(f"Entry with key '{entry.key}' already exists")
        self._key_index[entry.key] = len(self.entries)
        self.entries.append(entry)

    def get_entry(self, key: str) -> BibliographyEntry | None:
        """Get an entry by its citation key.

        Args:
            key: Citation key to look up

        Returns:
            BibliographyEntry if found, None otherwise
        """
        index = self._key_index.get(key)
        if index is not None:
            return self.entries[index]
        return None

    def remove_entry(self, key: str) -> bool:
        """Remove an entry by its citation key.

        Args:
            key: Citation key of entry to remove

        Returns:
            True if entry was removed, False if not found
        """
        if key not in self._key_index:
            return False

        index = self._key_index[key]
        del self.entries[index]
        del self._key_index[key]

        # Update indices for entries after the removed one
        for k, v in self._key_index.items():
            if v > index:
                self._key_index[k] = v - 1

        return True

    def update_entry(self, entry: BibliographyEntry) -> bool:
        """Update an existing entry.

        Args:
            entry: BibliographyEntry with updated data

        Returns:
            True if entry was updated, False if not found
        """
        index = self._key_index.get(entry.key)
        if index is not None:
            self.entries[index] = entry
            return True
        return False

    @classmethod
    def from_file(cls, filepath: Path) -> "Bibliography":
        """Load bibliography from a BibTeX file.

        Args:
            filepath: Path to the BibTeX file

        Returns:
            Bibliography instance with loaded entries

        Raises:
            FileNotFoundError: If file doesn't exist
            ParsingError: If file cannot be parsed
        """
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        bibliography = cls()

        with open(filepath, encoding="utf-8") as bibtex_file:
            parser = BibTexParser(common_strings=True)
            parser.customization = convert_to_unicode

            try:
                bib_database = bibtexparser.load(bibtex_file, parser=parser)
            except Exception as e:
                raise ParsingError(f"Failed to parse {filepath}: {str(e)}")

        for entry_dict in bib_database.entries:
            entry = BibliographyEntry.from_bibtex_dict(entry_dict.copy())
            bibliography.add_entry(entry)

        return bibliography

    def to_file(self, filepath: Path) -> None:
        """Save bibliography to a BibTeX file.

        Args:
            filepath: Path where to save the BibTeX file
        """
        # Convert entries to bibtexparser format
        entries_dict = [entry.to_bibtex_dict() for entry in self.entries]

        # Create BibTeX database
        db = bibtexparser.bibdatabase.BibDatabase()
        db.entries = entries_dict

        # Configure writer
        writer = BibTexWriter()
        writer.indent = "  "
        writer.order_entries_by = ["author", "year", "title"]

        # Write to file
        with open(filepath, "w", encoding="utf-8") as bibtex_file:
            bibtex_file.write(writer.write(db))

    def __len__(self) -> int:
        """Return the number of entries."""
        return len(self.entries)

    def __iter__(self):
        """Iterate over entries."""
        return iter(self.entries)

    def __repr__(self) -> str:
        """String representation of the bibliography."""
        return f"Bibliography(entries={len(self.entries)})"


class BibliographyProcessor(ABC):
    """Abstract base class for bibliography processors.

    All bibliography processing classes should inherit from this
    to ensure consistent interface.
    """

    @abstractmethod
    def process(self, bibliography: Bibliography) -> None:
        """Process the bibliography in-place.

        Args:
            bibliography: Bibliography to process
        """
        pass

    @abstractmethod
    def process_entry(self, entry: BibliographyEntry) -> None:
        """Process a single entry.

        Args:
            entry: BibliographyEntry to process
        """
        pass
