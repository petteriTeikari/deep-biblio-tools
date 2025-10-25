"""Tests for bibliography validator module."""

from src.bibliography import (
    Bibliography,
    BibliographyEntry,
    BibliographyValidator,
    LLMCitationValidator,
)


class TestBibliographyValidator:
    """Test BibliographyValidator class."""

    def test_validate_empty_bibliography(self):
        """Test validating empty bibliography."""
        bib = Bibliography()
        validator = BibliographyValidator()

        errors = validator.process(bib)
        assert len(errors) == 0

    def test_check_required_fields_article(self):
        """Test required fields for article."""
        validator = BibliographyValidator()

        # Complete article
        complete = BibliographyEntry(
            "article",
            "test2023",
            {
                "author": "Test, Author",
                "title": "Test Article",
                "journal": "Test Journal",
                "year": "2023",
            },
        )

        missing = validator.check_required_fields(complete)
        assert len(missing) == 0

        # Missing journal
        incomplete = BibliographyEntry(
            "article",
            "test2023",
            {"author": "Test, Author", "title": "Test Article", "year": "2023"},
        )

        missing = validator.check_required_fields(incomplete)
        assert "journal" in missing

    def test_check_required_fields_editor_fallback(self):
        """Test editor can substitute for author."""
        validator = BibliographyValidator()

        book = BibliographyEntry(
            "book",
            "test2023",
            {
                "editor": "Test, Editor",  # Editor instead of author
                "title": "Test Book",
                "publisher": "Test Publisher",
                "year": "2023",
            },
        )

        missing = validator.check_required_fields(book)
        assert len(missing) == 0  # Should accept editor

    def test_validate_year(self):
        """Test year validation."""
        validator = BibliographyValidator()

        # Valid year
        error = validator._validate_year("test", "2023")
        assert error is None

        # Invalid format
        error = validator._validate_year("test", "23")
        assert "Invalid year format" in error

        # Too far in future
        error = validator._validate_year("test", "2999")
        assert "too far in the future" in error

        # Too old
        error = validator._validate_year("test", "1799")
        assert "too old" in error

    def test_validate_authors(self):
        """Test author validation."""
        validator = BibliographyValidator()

        # Valid authors
        errors = validator._validate_authors(
            "test", "Smith, John and Jones, Jane"
        )
        assert len(errors) == 0

        # Empty authors
        errors = validator._validate_authors("test", "")
        assert any("Empty author field" in e for e in errors)

        # Single-word author
        errors = validator._validate_authors("test", "Smith")
        assert any("appears incomplete" in e for e in errors)

        # Possible reversed name
        errors = validator._validate_authors("test", "John Smith")
        assert any("may need comma" in e for e in errors)

    def test_check_suspicious_patterns(self):
        """Test detection of suspicious patterns."""
        validator = BibliographyValidator()

        # Entry with "et al"
        entry = BibliographyEntry(
            "article", "test", {"author": "Smith et al.", "title": "Test"}
        )

        warnings = validator._check_suspicious_patterns(entry)
        assert any("et al" in w for w in warnings)

        # Entry with placeholder
        entry = BibliographyEntry(
            "article", "test", {"author": "TODO", "title": "Test"}
        )

        warnings = validator._check_suspicious_patterns(entry)
        assert any("Suspicious pattern" in w for w in warnings)

    def test_validate_urls_format(self):
        """Test URL format validation."""
        validator = BibliographyValidator(
            check_urls=False
        )  # Don't make requests

        # Valid URL
        entry = BibliographyEntry(
            "misc", "test", {"url": "https://example.com/paper.pdf"}
        )
        errors = validator.validate_urls(entry)
        assert len(errors) == 0

        # Invalid URL
        entry = BibliographyEntry("misc", "test", {"url": "not-a-url"})
        errors = validator.validate_urls(entry)
        assert any("Invalid URL format" in e for e in errors)

        # DOI field
        entry = BibliographyEntry("article", "test", {"doi": "10.1234/example"})
        errors = validator.validate_urls(entry)
        assert len(errors) == 0  # DOI format is valid


class TestLLMCitationValidator:
    """Test LLMCitationValidator class."""

    def test_check_llm_patterns(self):
        """Test LLM-specific pattern detection."""
        validator = LLMCitationValidator(check_urls=False)

        # Generic conference name
        entry = BibliographyEntry(
            "inproceedings",
            "test",
            {
                "author": "Test, Author",
                "title": "Test Paper",
                "booktitle": "International Conference",
                "year": "2023",
            },
        )

        errors = validator.validate_entry(entry)
        assert any("generic conference name" in e for e in errors)

        # Suspicious page numbers
        entry = BibliographyEntry(
            "article",
            "test",
            {
                "author": "Test, Author",
                "title": "Test",
                "journal": "Test Journal",
                "year": "2023",
                "pages": "100--200",
            },
        )

        errors = validator.validate_entry(entry)
        assert any("Suspicious page numbers" in e for e in errors)

        # Placeholder journal
        entry = BibliographyEntry(
            "article",
            "test",
            {
                "author": "Test, Author",
                "title": "Test",
                "journal": "Journal",
                "year": "2023",
            },
        )

        errors = validator.validate_entry(entry)
        assert any("Generic journal name" in e for e in errors)
