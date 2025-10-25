"""Bibliography sorting functionality."""

from collections.abc import Callable
from typing import Any

from .core import Bibliography, BibliographyEntry, BibliographyProcessor


class BibliographySorter(BibliographyProcessor):
    """Sort bibliography entries in various ways.

    This class consolidates functionality from:
    - sort_bibliography.py
    - debug_bibliography_sorting.py
    """

    def __init__(
        self,
        sort_method: str = "author_year",
        sort_by: str = None,
        reverse: bool = False,
    ):
        """Initialize sorter.

        Args:
            sort_method: Sorting method to use ('author', 'year', 'key', 'author_year', 'type')
            sort_by: Alternative way to specify sort method (for compatibility)
            reverse: Whether to sort in reverse order
        """
        # Handle both parameter names for compatibility
        if sort_by is not None:
            sort_method = sort_by
        self.sort_method = sort_method
        self.reverse = reverse

    def process(self, bibliography: Bibliography) -> Bibliography:
        """Process bibliography by sorting entries and return sorted bibliography.

        Args:
            bibliography: Bibliography to sort

        Returns:
            New Bibliography with sorted entries
        """
        if self.sort_method == "author":
            sorted_entries = self.sort_by_author(
                bibliography, reverse=self.reverse
            )
        elif self.sort_method == "year":
            sorted_entries = self.sort_by_year(
                bibliography, reverse=self.reverse
            )
        elif self.sort_method == "key":
            sorted_entries = self.sort_by_key(
                bibliography, reverse=self.reverse
            )
        elif self.sort_method == "type":
            sorted_entries = self.sort_by_type(
                bibliography, reverse=self.reverse
            )
        elif self.sort_method == "author_year":
            sorted_entries = self.sort_by_author_year(
                bibliography, reverse=self.reverse
            )
        elif self.sort_method == "title":
            sorted_entries = self.sort_by_title(
                bibliography, reverse=self.reverse
            )
        else:
            raise ValueError(f"Unknown sort method: {self.sort_method}")

        # Create new bibliography with sorted entries
        sorted_bib = Bibliography()
        for entry in sorted_entries:
            sorted_bib.add_entry(entry)
        return sorted_bib

    def process_entry(self, entry: BibliographyEntry) -> None:
        """Process a single entry (no-op for sorting)."""
        pass

    @staticmethod
    def sort_by_title(
        bibliography: Bibliography, reverse: bool = False
    ) -> list[BibliographyEntry]:
        """Sort bibliography entries by title.

        Args:
            bibliography: Bibliography to sort
            reverse: Whether to sort in reverse order

        Returns:
            Sorted list of entries
        """

        def get_title_sort_key(entry: BibliographyEntry) -> str:
            """Extract sort key from title field."""
            title = entry.get_field("title", "")
            if not title:
                return "zzz"  # Sort entries without title to end
            return title.lower()

        return sorted(
            bibliography.entries, key=get_title_sort_key, reverse=reverse
        )

    @staticmethod
    def sort_by_key(
        bibliography: Bibliography, reverse: bool = False
    ) -> list[BibliographyEntry]:
        """Sort bibliography entries by citation key.

        Args:
            bibliography: Bibliography to sort
            reverse: Whether to sort in reverse order

        Returns:
            Sorted list of entries
        """
        return sorted(
            bibliography.entries, key=lambda e: e.key.lower(), reverse=reverse
        )

    @staticmethod
    def sort_by_author(
        bibliography: Bibliography, reverse: bool = False
    ) -> list[BibliographyEntry]:
        """Sort bibliography entries by first author's last name.

        Args:
            bibliography: Bibliography to sort
            reverse: Whether to sort in reverse order

        Returns:
            Sorted list of entries
        """

        def get_author_sort_key(entry: BibliographyEntry) -> str:
            """Extract sort key from author field."""
            author = entry.get_field("author", entry.get_field("editor", ""))
            if not author:
                return "zzz"  # Sort entries without authors to end

            # Get first author
            first_author = author.split(" and ")[0].strip()

            # Handle "Last, First" format
            if "," in first_author:
                last_name = first_author.split(",")[0].strip()
            else:
                # Handle "First Last" format
                parts = first_author.split()
                last_name = parts[-1] if parts else ""

            return last_name.lower()

        return sorted(
            bibliography.entries, key=get_author_sort_key, reverse=reverse
        )

    @staticmethod
    def sort_by_year(
        bibliography: Bibliography, reverse: bool = False
    ) -> list[BibliographyEntry]:
        """Sort bibliography entries by year.

        Args:
            bibliography: Bibliography to sort
            reverse: Whether to sort in reverse order (newest first)

        Returns:
            Sorted list of entries
        """

        def get_year_sort_key(entry: BibliographyEntry) -> str:
            """Extract sort key from year field."""
            year = entry.get_field("year", "")
            if not year:
                # Try to extract from date field
                date = entry.get_field("date", "")
                if date and len(date) >= 4:
                    year = date[:4]
                else:
                    year = "9999"  # Sort entries without year to end

            # Ensure it's a string for consistent sorting
            return str(year)

        return sorted(
            bibliography.entries, key=get_year_sort_key, reverse=reverse
        )

    @staticmethod
    def sort_by_type(
        bibliography: Bibliography, reverse: bool = False
    ) -> list[BibliographyEntry]:
        """Sort bibliography entries by entry type.

        Args:
            bibliography: Bibliography to sort
            reverse: Whether to sort in reverse order

        Returns:
            Sorted list of entries
        """
        return sorted(
            bibliography.entries, key=lambda e: e.entry_type, reverse=reverse
        )

    @staticmethod
    def sort_by_author_year(
        bibliography: Bibliography, reverse: bool = False
    ) -> list[BibliographyEntry]:
        """Sort bibliography entries by author then year.

        This is the most common sorting for bibliographies.

        Args:
            bibliography: Bibliography to sort
            reverse: Whether to sort in reverse order

        Returns:
            Sorted list of entries
        """

        def get_author_year_key(entry: BibliographyEntry) -> tuple:
            """Extract compound sort key."""
            # Get author key
            author = entry.get_field("author", entry.get_field("editor", ""))
            if not author:
                author_key = "zzz"
            else:
                first_author = author.split(" and ")[0].strip()
                if "," in first_author:
                    author_key = first_author.split(",")[0].strip().lower()
                else:
                    parts = first_author.split()
                    author_key = parts[-1].lower() if parts else "zzz"

            # Get year key
            year = entry.get_field("year", "")
            if not year:
                date = entry.get_field("date", "")
                year = date[:4] if date and len(date) >= 4 else "9999"

            # Add title as third sort key for stable sorting
            title = entry.get_field("title", "").lower()

            return (author_key, str(year), title)

        return sorted(
            bibliography.entries, key=get_author_year_key, reverse=reverse
        )

    @staticmethod
    def sort_by_custom(
        bibliography: Bibliography,
        key_func: Callable[[BibliographyEntry], Any],
        reverse: bool = False,
    ) -> list[BibliographyEntry]:
        """Sort bibliography entries using a custom key function.

        Args:
            bibliography: Bibliography to sort
            key_func: Function that extracts sort key from entry
            reverse: Whether to sort in reverse order

        Returns:
            Sorted list of entries
        """
        return sorted(bibliography.entries, key=key_func, reverse=reverse)

    @staticmethod
    def group_by_type(
        bibliography: Bibliography,
    ) -> dict[str, list[BibliographyEntry]]:
        """Group bibliography entries by type.

        Args:
            bibliography: Bibliography to group

        Returns:
            Dictionary mapping entry types to lists of entries
        """
        groups = {}
        for entry in bibliography:
            entry_type = entry.entry_type
            if entry_type not in groups:
                groups[entry_type] = []
            groups[entry_type].append(entry)

        # Sort entries within each group by author-year
        for entry_type in groups:
            groups[entry_type] = BibliographySorter.sort_by_author_year(
                Bibliography()  # Create temporary bibliography
            )

        return groups

    @staticmethod
    def apply_sort(
        bibliography: Bibliography, sorted_entries: list[BibliographyEntry]
    ) -> None:
        """Apply a sort order to bibliography in-place.

        Args:
            bibliography: Bibliography to modify
            sorted_entries: Entries in desired order
        """
        # Verify all entries are accounted for
        if len(sorted_entries) != len(bibliography.entries):
            raise ValueError(
                "Sorted entries must contain all bibliography entries"
            )

        # Clear and rebuild
        bibliography.entries.clear()
        bibliography._key_index.clear()

        for i, entry in enumerate(sorted_entries):
            bibliography.entries.append(entry)
            bibliography._key_index[entry.key] = i
