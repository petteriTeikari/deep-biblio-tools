"""Tests for bibliography core module."""

import tempfile
from pathlib import Path

import pytest
from src.bibliography import Bibliography, BibliographyEntry


class TestBibliographyEntry:
    """Test BibliographyEntry class."""

    def test_create_entry(self):
        """Test creating a bibliography entry."""
        entry = BibliographyEntry(
            entry_type="article",
            key="Smith2023",
            fields={
                "author": "Smith, John",
                "title": "A Great Paper",
                "year": "2023",
                "journal": "Nature",
            },
        )

        assert entry.entry_type == "article"
        assert entry.key == "Smith2023"
        assert entry.get_field("author") == "Smith, John"
        assert entry.get_field("title") == "A Great Paper"

    def test_entry_field_operations(self):
        """Test field operations on entry."""
        entry = BibliographyEntry("article", "Test2023", {})

        # Test get with default
        assert entry.get_field("missing") is None
        assert entry.get_field("missing", "default") == "default"

        # Test set and has
        assert not entry.has_field("author")
        entry.set_field("author", "Test Author")
        assert entry.has_field("author")
        assert entry.get_field("author") == "Test Author"

    def test_bibtex_conversion(self):
        """Test conversion to/from bibtex format."""
        original = {
            "ENTRYTYPE": "article",
            "ID": "Smith2023",
            "author": "Smith, John",
            "title": "A Great Paper",
            "year": "2023",
        }

        # From bibtex dict
        entry = BibliographyEntry.from_bibtex_dict(original.copy())
        assert entry.entry_type == "article"
        assert entry.key == "Smith2023"
        assert entry.get_field("author") == "Smith, John"

        # To bibtex dict
        converted = entry.to_bibtex_dict()
        assert converted == original


class TestBibliography:
    """Test Bibliography class."""

    def test_create_empty_bibliography(self):
        """Test creating an empty bibliography."""
        bib = Bibliography()
        assert len(bib) == 0
        assert list(bib) == []

    def test_add_entry(self):
        """Test adding entries to bibliography."""
        bib = Bibliography()
        entry1 = BibliographyEntry("article", "Smith2023", {"title": "Paper 1"})
        entry2 = BibliographyEntry("book", "Jones2022", {"title": "Book 1"})

        bib.add_entry(entry1)
        assert len(bib) == 1
        assert bib.get_entry("Smith2023") == entry1

        bib.add_entry(entry2)
        assert len(bib) == 2
        assert bib.get_entry("Jones2022") == entry2

    def test_duplicate_key_error(self):
        """Test that duplicate keys raise error."""
        bib = Bibliography()
        entry1 = BibliographyEntry("article", "Smith2023", {"title": "Paper 1"})
        entry2 = BibliographyEntry("article", "Smith2023", {"title": "Paper 2"})

        bib.add_entry(entry1)
        with pytest.raises(ValueError, match="already exists"):
            bib.add_entry(entry2)

    def test_get_entry(self):
        """Test getting entries by key."""
        bib = Bibliography()
        entry = BibliographyEntry("article", "Smith2023", {"title": "Paper"})
        bib.add_entry(entry)

        assert bib.get_entry("Smith2023") == entry
        assert bib.get_entry("NonExistent") is None

    def test_remove_entry(self):
        """Test removing entries."""
        bib = Bibliography()
        entry1 = BibliographyEntry("article", "Smith2023", {"title": "Paper 1"})
        entry2 = BibliographyEntry("book", "Jones2022", {"title": "Book 1"})
        entry3 = BibliographyEntry("misc", "Doe2021", {"title": "Misc 1"})

        bib.add_entry(entry1)
        bib.add_entry(entry2)
        bib.add_entry(entry3)

        assert len(bib) == 3

        # Remove middle entry
        assert bib.remove_entry("Jones2022")
        assert len(bib) == 2
        assert bib.get_entry("Jones2022") is None
        assert bib.get_entry("Smith2023") == entry1
        assert bib.get_entry("Doe2021") == entry3

        # Try to remove non-existent
        assert not bib.remove_entry("NonExistent")

    def test_update_entry(self):
        """Test updating entries."""
        bib = Bibliography()
        entry = BibliographyEntry("article", "Smith2023", {"title": "Original"})
        bib.add_entry(entry)

        # Update existing
        updated = BibliographyEntry(
            "article", "Smith2023", {"title": "Updated"}
        )
        assert bib.update_entry(updated)
        assert bib.get_entry("Smith2023").get_field("title") == "Updated"

        # Update non-existent
        new_entry = BibliographyEntry("book", "New2023", {"title": "New"})
        assert not bib.update_entry(new_entry)

    def test_iterate_entries(self):
        """Test iterating over entries."""
        bib = Bibliography()
        entries = [
            BibliographyEntry("article", f"Entry{i}", {"title": f"Title {i}"})
            for i in range(3)
        ]

        for entry in entries:
            bib.add_entry(entry)

        # Test iteration
        collected = list(bib)
        assert len(collected) == 3
        assert all(e in entries for e in collected)

    def test_file_operations(self):
        """Test loading and saving bibliography files."""
        # Create test bibliography
        bib = Bibliography()
        bib.add_entry(
            BibliographyEntry(
                "article",
                "Smith2023",
                {
                    "author": "Smith, John",
                    "title": "A Great Paper",
                    "year": "2023",
                    "journal": "Nature",
                },
            )
        )
        bib.add_entry(
            BibliographyEntry(
                "book",
                "Jones2022",
                {
                    "author": "Jones, Jane",
                    "title": "Comprehensive Guide",
                    "year": "2022",
                    "publisher": "Academic Press",
                },
            )
        )

        # Save to temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".bib", delete=False
        ) as f:
            temp_path = Path(f.name)

        try:
            bib.to_file(temp_path)

            # Load back
            loaded = Bibliography.from_file(temp_path)
            assert len(loaded) == 2

            # Check entries
            smith = loaded.get_entry("Smith2023")
            assert smith is not None
            assert smith.entry_type == "article"
            assert smith.get_field("author") == "Smith, John"
            assert smith.get_field("title") == "A Great Paper"

            jones = loaded.get_entry("Jones2022")
            assert jones is not None
            assert jones.entry_type == "book"
            assert jones.get_field("author") == "Jones, Jane"

        finally:
            temp_path.unlink()

    def test_file_not_found(self):
        """Test loading non-existent file."""
        with pytest.raises(FileNotFoundError):
            Bibliography.from_file(Path("/nonexistent/file.bib"))

    def test_empty_bibtex_file(self):
        """Test loading empty BibTeX file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".bib", delete=False
        ) as f:
            f.write("")  # Empty file
            temp_path = Path(f.name)

        try:
            bib = Bibliography.from_file(temp_path)
            assert (
                len(bib) == 0
            )  # Empty file should result in empty bibliography
        finally:
            temp_path.unlink()
