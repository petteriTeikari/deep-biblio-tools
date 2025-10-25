"""Tests for Deep Biblio Tools."""

from src.core import BiblioChecker
from src.utils import (
    extract_dois_from_text,
    is_academic_domain,
    validate_doi,
)


class TestBiblioChecker:
    """Test suite for BiblioChecker."""

    def test_initialization(self):
        """Test BiblioChecker initialization."""
        checker = BiblioChecker()
        assert checker is not None
        assert checker.academic_domains is not None
        assert len(checker.academic_domains) > 0

    def test_academic_domain_detection(self):
        """Test academic domain detection."""
        checker = BiblioChecker()

        # Test academic domains
        assert checker._is_academic_url("https://doi.org/10.1000/test")
        assert checker._is_academic_url("https://arxiv.org/abs/1234.5678")
        assert checker._is_academic_url("https://ieee.org/document/123456")
        assert checker._is_academic_url("https://example.edu/paper.pdf")

        # Test non-academic domains
        assert not checker._is_academic_url("https://google.com")
        assert not checker._is_academic_url("https://facebook.com")


class TestUtilityFunctions:
    """Test suite for utility functions."""

    def test_extract_dois_from_text(self):
        """Test DOI extraction from text."""
        text = "This paper (doi:10.1000/123456) is interesting. Also see 10.5678/abcdef."
        dois = extract_dois_from_text(text)
        assert len(dois) == 2
        assert "10.1000/123456" in dois
        assert "10.5678/abcdef" in dois

    def test_validate_doi(self):
        """Test DOI validation."""
        # Valid DOIs
        assert validate_doi("10.1000/123456")
        assert validate_doi("10.5678/journal.2023.123")

        # Invalid DOIs
        assert not validate_doi("invalid-doi")
        assert not validate_doi("10.1000")
        assert not validate_doi("")

    def test_is_academic_domain(self):
        """Test academic domain detection utility."""
        # Academic domains
        assert is_academic_domain("https://doi.org/10.1000/test")
        assert is_academic_domain("https://arxiv.org/abs/1234.5678")
        assert is_academic_domain("https://pubmed.ncbi.nlm.nih.gov/12345")

        # Non-academic domains
        assert not is_academic_domain("https://google.com")
        assert not is_academic_domain("https://twitter.com")
