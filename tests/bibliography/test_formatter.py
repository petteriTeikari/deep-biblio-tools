"""Tests for bibliography formatter module."""

from src.bibliography import (
    Bibliography,
    BibliographyEntry,
    CitationKeyFormatter,
)


class TestCitationKeyFormatter:
    """Test CitationKeyFormatter class."""

    def test_to_authoryear_simple(self):
        """Test basic author-year formatting."""
        formatter = CitationKeyFormatter()

        entry = BibliographyEntry(
            "article",
            "oldkey",
            {"author": "Smith, John", "year": "2023", "title": "A Great Paper"},
        )

        key = formatter.to_authoryear(entry)
        assert key == "Smith2023"

    def test_to_authoryear_multiple_authors(self):
        """Test formatting with multiple authors."""
        formatter = CitationKeyFormatter()

        entry = BibliographyEntry(
            "article",
            "oldkey",
            {"author": "Smith, John and Jones, Jane", "year": "2023"},
        )

        key = formatter.to_authoryear(entry)
        assert key == "Smith2023"  # Should use first author

    def test_to_authoryear_no_comma(self):
        """Test formatting with 'First Last' format."""
        formatter = CitationKeyFormatter()

        entry = BibliographyEntry(
            "article", "oldkey", {"author": "John Smith", "year": "2023"}
        )

        key = formatter.to_authoryear(entry)
        assert key == "Smith2023"

    def test_to_authoryear_special_chars(self):
        """Test formatting with special characters in names."""
        formatter = CitationKeyFormatter()

        entry = BibliographyEntry(
            "article", "oldkey", {"author": "Müller, Hans", "year": "2023"}
        )

        key = formatter.to_authoryear(entry)
        assert key == "Mller2023"  # Special chars removed

    def test_to_authoryear_duplicates(self):
        """Test handling of duplicate keys."""
        formatter = CitationKeyFormatter()

        entry1 = BibliographyEntry(
            "article", "key1", {"author": "Smith, John", "year": "2023"}
        )
        entry2 = BibliographyEntry(
            "article", "key2", {"author": "Smith, Jane", "year": "2023"}
        )

        key1 = formatter.to_authoryear(entry1)
        key2 = formatter.to_authoryear(entry2)

        assert key1 == "Smith2023"
        assert key2 == "Smith2023a"  # Should add suffix

    def test_to_authoryear_no_year(self):
        """Test formatting without year."""
        formatter = CitationKeyFormatter()

        entry = BibliographyEntry(
            "article", "oldkey", {"author": "Smith, John"}
        )

        key = formatter.to_authoryear(entry)
        assert key == "SmithNoYear"

    def test_to_authoryear_editor_fallback(self):
        """Test using editor when no author."""
        formatter = CitationKeyFormatter()

        entry = BibliographyEntry(
            "book", "oldkey", {"editor": "Jones, Jane", "year": "2023"}
        )

        key = formatter.to_authoryear(entry)
        assert key == "Jones2023"

    def test_fix_arxiv_keys(self):
        """Test arXiv key fixing."""
        bib = Bibliography()

        # Add arXiv entry with old-style key
        entry = BibliographyEntry(
            "article",
            "2023arXiv230112345S",
            {
                "author": "Smith, John",
                "year": "2023",
                "eprint": "2301.12345",
                "archiveprefix": "arXiv",
            },
        )
        bib.add_entry(entry)

        formatter = CitationKeyFormatter()
        formatter.fix_arxiv_keys(bib)

        # Check that key was updated
        assert bib.get_entry("2023arXiv230112345S") is None
        assert bib.get_entry("Smith2023arxiv") is not None

    def test_standardize_keys(self):
        """Test standardizing all keys in bibliography."""
        bib = Bibliography()

        # Add entries with various key formats
        entries = [
            BibliographyEntry(
                "article",
                "smith:2023",
                {"author": "Smith, John", "year": "2023", "title": "Paper A"},
            ),
            BibliographyEntry(
                "article",
                "jones_2022",
                {"author": "Jones, Jane", "year": "2022", "title": "Paper B"},
            ),
            BibliographyEntry(
                "article",
                "doe23",
                {"author": "Doe, John", "year": "2023", "title": "Paper C"},
            ),
        ]

        for entry in entries:
            bib.add_entry(entry)

        formatter = CitationKeyFormatter()
        formatter.standardize_keys(bib)

        # Check all keys are now in author-year format
        assert bib.get_entry("Smith2023") is not None
        assert bib.get_entry("Jones2022") is not None
        assert bib.get_entry("Doe2023") is not None

        # Old keys should be gone
        assert bib.get_entry("smith:2023") is None
        assert bib.get_entry("jones_2022") is None
        assert bib.get_entry("doe23") is None
