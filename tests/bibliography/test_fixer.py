"""Tests for bibliography fixer module."""

from src.bibliography import Bibliography, BibliographyEntry, BibliographyFixer


class TestBibliographyFixer:
    """Test BibliographyFixer class."""

    def test_fix_empty_bibliography(self):
        """Test fixing empty bibliography."""
        bib = Bibliography()
        fixer = BibliographyFixer()

        fixes_applied = fixer.process(bib)
        assert fixes_applied == 0
        assert len(bib) == 0

    def test_fix_author_format(self):
        """Test fixing author field formatting."""
        bib = Bibliography()

        # Entry with improperly formatted authors
        entry = BibliographyEntry(
            "article",
            "test2023",
            {
                "author": "John Smith and Jane Doe and Bob Johnson",
                "title": "Test Article",
                "year": "2023",
            },
        )
        bib.add_entry(entry)

        fixer = BibliographyFixer()
        fixer.process(bib)

        fixed_entry = bib.get_entry("test2023")
        assert fixed_entry is not None
        # The fixer should convert to proper BibTeX format
        assert " and " in fixed_entry.get_field("author")

    def test_fix_missing_doi(self):
        """Test adding DOI when URL contains one."""
        bib = Bibliography()

        # Entry with DOI in URL but not in doi field
        entry = BibliographyEntry(
            "article",
            "test2023",
            {
                "author": "Smith, John",
                "title": "Test Article",
                "year": "2023",
                "url": "https://doi.org/10.1234/example.doi",
            },
        )
        bib.add_entry(entry)

        fixer = BibliographyFixer()
        fixer.process(bib)

        fixed_entry = bib.get_entry("test2023")
        assert fixed_entry is not None
        assert fixed_entry.get_field("doi") == "10.1234/example.doi"

    def test_fix_arxiv_format(self):
        """Test fixing arXiv entries."""
        bib = Bibliography()

        # Entry with arXiv URL
        entry = BibliographyEntry(
            "misc",
            "test2023",
            {
                "author": "Smith, John",
                "title": "Test Preprint",
                "year": "2023",
                "url": "https://arxiv.org/abs/2301.12345",
            },
        )
        bib.add_entry(entry)

        fixer = BibliographyFixer()
        fixer.process(bib)

        fixed_entry = bib.get_entry("test2023")
        assert fixed_entry is not None
        assert fixed_entry.get_field("eprint") == "2301.12345"
        assert fixed_entry.get_field("archivePrefix") == "arXiv"

    def test_fix_page_numbers(self):
        """Test fixing page number formats."""
        bib = Bibliography()

        # Entry with single dash in pages
        entry = BibliographyEntry(
            "article",
            "test2023",
            {
                "author": "Smith, John",
                "title": "Test Article",
                "year": "2023",
                "pages": "123-456",  # Should be double dash
            },
        )
        bib.add_entry(entry)

        fixer = BibliographyFixer()
        fixer.process(bib)

        fixed_entry = bib.get_entry("test2023")
        assert fixed_entry is not None
        assert fixed_entry.get_field("pages") == "123--456"

    def test_fix_duplicate_fields(self):
        """Test handling of duplicate information."""
        bib = Bibliography()

        # Entry with URL that duplicates DOI
        entry = BibliographyEntry(
            "article",
            "test2023",
            {
                "author": "Smith, John",
                "title": "Test Article",
                "year": "2023",
                "doi": "10.1234/example",
                "url": "https://doi.org/10.1234/example",  # Redundant
            },
        )
        bib.add_entry(entry)

        fixer = BibliographyFixer()
        fixer.process(bib)

        fixed_entry = bib.get_entry("test2023")
        assert fixed_entry is not None
        assert fixed_entry.get_field("doi") == "10.1234/example"
        # URL should be removed if it's just the DOI URL
        assert fixed_entry.get_field("url") is None

    def test_fix_title_capitalization(self):
        """Test fixing title capitalization."""
        bib = Bibliography()

        # Entry with improper title capitalization
        entry = BibliographyEntry(
            "article",
            "test2023",
            {
                "author": "Smith, John",
                "title": "test article with improper capitalization",
                "year": "2023",
            },
        )
        bib.add_entry(entry)

        fixer = BibliographyFixer()
        fixer.process(bib)

        fixed_entry = bib.get_entry("test2023")
        assert fixed_entry is not None
        # Should preserve BibTeX capitalization
        title = fixed_entry.get_field("title")
        assert title[0].isupper()  # First letter should be capitalized

    def test_fix_journal_abbreviations(self):
        """Test expanding common journal abbreviations."""
        bib = Bibliography()

        # Entry with abbreviated journal name
        entry = BibliographyEntry(
            "article",
            "test2023",
            {
                "author": "Smith, John",
                "title": "Test Article",
                "journal": "Phys. Rev. Lett.",
                "year": "2023",
            },
        )
        bib.add_entry(entry)

        fixer = BibliographyFixer()
        fixer.process(bib)

        fixed_entry = bib.get_entry("test2023")
        assert fixed_entry is not None
        # Should expand to full name if configured
        journal = fixed_entry.get_field("journal")
        assert journal in ["Phys. Rev. Lett.", "Physical Review Letters"]

    def test_fix_et_al_in_authors(self):
        """Test handling 'et al.' in author fields."""
        bib = Bibliography()

        # Entry with et al. in authors (common LLM error)
        entry = BibliographyEntry(
            "article",
            "test2023",
            {
                "author": "Smith, John et al.",
                "title": "Test Article",
                "year": "2023",
            },
        )
        bib.add_entry(entry)

        fixer = BibliographyFixer()
        fixer.process(bib)

        fixed_entry = bib.get_entry("test2023")
        assert fixed_entry is not None
        # Should remove et al. from author field
        assert "et al." not in fixed_entry.get_field("author")

    def test_preserve_valid_entries(self):
        """Test that valid entries are preserved unchanged."""
        bib = Bibliography()

        # Well-formatted entry
        entry = BibliographyEntry(
            "article",
            "test2023",
            {
                "author": "Smith, John and Doe, Jane",
                "title": "A Well-Formatted Article",
                "journal": "Nature",
                "year": "2023",
                "volume": "123",
                "pages": "45--67",
                "doi": "10.1234/nature.2023",
            },
        )
        bib.add_entry(entry)

        fixer = BibliographyFixer()
        fixer.process(bib)

        fixed_entry = bib.get_entry("test2023")
        assert fixed_entry is not None

        # All fields should be preserved
        for field in [
            "author",
            "title",
            "journal",
            "year",
            "volume",
            "pages",
            "doi",
        ]:
            assert fixed_entry.get_field(field) == entry.get_field(field)
