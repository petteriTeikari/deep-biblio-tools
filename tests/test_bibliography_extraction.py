"""
Test suite for bibliography extraction with metadata fetching.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from extract_bibliography_with_metadata import (
    Citation,
    enrich_citation_metadata,
    extract_arxiv_id_from_url,
    extract_citations,
    extract_doi_from_url,
    fetch_arxiv_metadata,
    fetch_crossref_metadata,
    fetch_webpage_title,
    process_markdown_file,
)


class TestCitation:
    """Test Citation class functionality."""

    def test_citation_initialization(self):
        """Test creating a citation object."""
        citation = Citation(
            raw_text="[Smith et al. (2023)](https://doi.org/10.1234/test)",
            authors="Smith et al.",
            year="2023",
            url="https://doi.org/10.1234/test",
        )

        assert citation.authors == "Smith et al."
        assert citation.year == "2023"
        assert citation.url == "https://doi.org/10.1234/test"
        assert citation.title is None
        assert citation.metadata_source is None

    def test_bibtex_key_generation(self):
        """Test BibTeX key generation."""
        citation = Citation("", "Smith et al.", "2023", "")
        assert citation.to_bibtex_key() == "smith2023"

        citation = Citation("", "García-López", "2022", "")
        assert citation.to_bibtex_key() == "garcalpez2022"

        citation = Citation("", "O'Brien", "2021", "")
        assert citation.to_bibtex_key() == "obrien2021"

    def test_bibtex_generation_article(self):
        """Test BibTeX generation for journal article."""
        citation = Citation(
            "", "Smith et al.", "2023", "https://doi.org/10.1234/test"
        )
        citation.title = "Test Article"
        citation.journal = "Journal of Testing"
        citation.volume = "42"
        citation.pages = "123-456"
        citation.doi = "10.1234/test"

        bibtex = citation.to_bibtex()
        assert "@article{smith2023," in bibtex
        assert 'title = "Test Article",' in bibtex
        assert 'journal = "Journal of Testing",' in bibtex
        assert 'volume = "42",' in bibtex
        assert 'pages = "123-456",' in bibtex
        assert 'doi = "10.1234/test",' in bibtex

    def test_bibtex_generation_arxiv(self):
        """Test BibTeX generation for arXiv paper."""
        citation = Citation(
            "", "Johnson", "2024", "https://arxiv.org/abs/2401.12345"
        )
        citation.title = "Machine Learning Paper"
        citation.arxiv_id = "2401.12345"
        citation.metadata_source = "arXiv"

        bibtex = citation.to_bibtex()
        assert "@misc{johnson2024," in bibtex
        assert 'arxivId = "2401.12345",' in bibtex
        assert 'eprint = "2401.12345",' in bibtex
        assert 'archivePrefix = "arXiv",' in bibtex

    def test_bibtex_generation_missing_title(self):
        """Test BibTeX generation when title is missing."""
        citation = Citation("", "Unknown", "2020", "https://example.com")
        citation.fetch_error = "Could not fetch metadata"

        bibtex = citation.to_bibtex()
        assert (
            'title = "[Title not available - manual entry needed]",' in bibtex
        )
        assert (
            'note = "Metadata fetch error: Could not fetch metadata",' in bibtex
        )


class TestCitationExtraction:
    """Test citation extraction from markdown."""

    def test_extract_simple_citations(self):
        """Test extracting simple citations."""
        content = """
        This is a test document with a citation [Smith et al. (2023)](https://doi.org/10.1234/test).
        Another citation here [Johnson (2024)](https://arxiv.org/abs/2401.12345).
        """

        citations = extract_citations(content)
        assert len(citations) == 2

        assert citations[0].authors == "Smith et al."
        assert citations[0].year == "2023"
        assert citations[0].url == "https://doi.org/10.1234/test"

        assert citations[1].authors == "Johnson"
        assert citations[1].year == "2024"
        assert citations[1].url == "https://arxiv.org/abs/2401.12345"

    def test_extract_citations_with_spaces(self):
        """Test extracting citations with various spacing."""
        content = """
        Citation with extra spaces [Smith (2023)](https://example.com).
        Normal citation [Johnson (2024)](https://test.com).
        """

        citations = extract_citations(content)
        assert len(citations) == 2
        assert citations[0].authors == "Smith"
        assert citations[0].url == "https://example.com"

    def test_skip_duplicate_urls(self):
        """Test that duplicate URLs are skipped."""
        content = """
        First citation [Smith (2023)](https://example.com).
        Same URL different author [Johnson (2023)](https://example.com).
        Different URL [Brown (2023)](https://different.com).
        """

        citations = extract_citations(content)
        assert len(citations) == 2
        assert citations[0].authors == "Smith"
        assert citations[1].authors == "Brown"

    def test_complex_author_names(self):
        """Test extraction with complex author names."""
        content = """
        Complex names [García-López and O'Brien (2023)](https://doi.org/10.1234/test).
        Multiple authors [Smith, Johnson, and Brown (2022)](https://example.com).
        """

        citations = extract_citations(content)
        assert len(citations) == 2
        assert citations[0].authors == "García-López and O'Brien"
        assert citations[1].authors == "Smith, Johnson, and Brown"


class TestURLParsing:
    """Test URL parsing for DOIs and arXiv IDs."""

    def test_extract_doi_from_url(self):
        """Test DOI extraction from various URL formats."""
        # Standard DOI URLs
        assert (
            extract_doi_from_url("https://doi.org/10.1234/test")
            == "10.1234/test"
        )
        assert (
            extract_doi_from_url("http://dx.doi.org/10.1234/test")
            == "10.1234/test"
        )
        assert (
            extract_doi_from_url("https://doi.org/10.1234/test?param=value")
            == "10.1234/test"
        )

        # DOI with special characters
        assert (
            extract_doi_from_url("https://doi.org/10.1007/s11146-019-09716-w")
            == "10.1007/s11146-019-09716-w"
        )

        # Non-DOI URLs
        assert extract_doi_from_url("https://example.com") is None
        assert extract_doi_from_url("https://arxiv.org/abs/2401.12345") is None

    def test_extract_arxiv_id_from_url(self):
        """Test arXiv ID extraction from various URL formats."""
        # Standard arXiv URLs
        assert (
            extract_arxiv_id_from_url("https://arxiv.org/abs/2401.12345")
            == "2401.12345"
        )
        assert (
            extract_arxiv_id_from_url("https://arxiv.org/pdf/2401.12345.pdf")
            == "2401.12345"
        )
        assert (
            extract_arxiv_id_from_url("https://arxiv.org/pdf/2401.12345")
            == "2401.12345"
        )

        # With version numbers
        assert (
            extract_arxiv_id_from_url("https://arxiv.org/abs/2401.12345v2")
            == "2401.12345"
        )

        # Old-style arXiv IDs
        assert (
            extract_arxiv_id_from_url("https://arxiv.org/abs/cs.AI/0301023")
            == "cs.AI/0301023"
        )

        # Non-arXiv URLs
        assert extract_arxiv_id_from_url("https://example.com") is None
        assert extract_arxiv_id_from_url("https://doi.org/10.1234/test") is None


class TestMetadataFetching:
    """Test metadata fetching functionality."""

    @patch("extract_bibliography_with_metadata.requests.get")
    def test_fetch_crossref_metadata_success(self, mock_get):
        """Test successful CrossRef metadata fetching."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "title": ["Test Article Title"],
                "container-title": ["Journal of Testing"],
                "volume": "42",
                "page": "123-456",
                "publisher": "Test Publisher",
                "author": [
                    {"given": "John", "family": "Smith"},
                    {"given": "Jane", "family": "Doe"},
                ],
            }
        }
        mock_get.return_value = mock_response

        metadata = fetch_crossref_metadata("10.1234/test")

        assert metadata is not None
        assert metadata["title"] == ["Test Article Title"]
        assert metadata["container-title"] == ["Journal of Testing"]
        assert metadata["volume"] == "42"

    @patch("extract_bibliography_with_metadata.requests.get")
    def test_fetch_crossref_metadata_not_found(self, mock_get):
        """Test CrossRef metadata fetching when DOI not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        metadata = fetch_crossref_metadata("10.1234/notfound")
        assert metadata is None

    @patch("extract_bibliography_with_metadata.requests.get")
    def test_fetch_arxiv_metadata_success(self, mock_get):
        """Test successful arXiv metadata fetching."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title>Test arXiv Paper</title>
                <author><name>John Doe</name></author>
                <author><name>Jane Smith</name></author>
                <published>2024-01-15T00:00:00Z</published>
                <summary>This is the abstract.</summary>
            </entry>
        </feed>"""
        mock_get.return_value = mock_response

        metadata = fetch_arxiv_metadata("2401.12345")

        assert metadata is not None
        assert metadata["title"] == "Test arXiv Paper"
        assert metadata["authors"] == ["John Doe", "Jane Smith"]

    @patch("extract_bibliography_with_metadata.requests.get")
    def test_fetch_webpage_title_success(self, mock_get):
        """Test successful webpage title fetching."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head>
                <title>Test Page Title | Website Name</title>
            </head>
        </html>
        """
        mock_get.return_value = mock_response

        title = fetch_webpage_title("https://example.com")
        assert title == "Test Page Title"

    @patch("extract_bibliography_with_metadata.requests.get")
    def test_enrich_citation_with_doi(self, mock_get):
        """Test enriching citation with DOI metadata."""
        citation = Citation(
            "", "Smith et al.", "2023", "https://doi.org/10.1234/test"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "title": ["Real Paper Title"],
                "container-title": ["Nature"],
                "volume": "600",
                "page": "100-105",
                "author": [
                    {"given": "John", "family": "Smith"},
                    {"given": "Jane", "family": "Doe"},
                ],
            }
        }
        mock_get.return_value = mock_response

        enrich_citation_metadata(citation)

        assert citation.title == "Real Paper Title"
        assert citation.journal == "Nature"
        assert citation.volume == "600"
        assert citation.pages == "100-105"
        assert citation.metadata_source == "CrossRef"
        assert citation.doi == "10.1234/test"


class TestEndToEnd:
    """Test end-to-end processing."""

    @patch("extract_bibliography_with_metadata.fetch_crossref_metadata")
    @patch("extract_bibliography_with_metadata.fetch_arxiv_metadata")
    @patch("extract_bibliography_with_metadata.fetch_webpage_title")
    def test_process_markdown_file(
        self, mock_webpage, mock_arxiv, mock_crossref
    ):
        """Test processing a complete markdown file."""
        # Create test markdown content
        test_content = """
# Test Document

This document cites several papers:

1. A CrossRef paper [Smith et al. (2023)](https://doi.org/10.1234/test)
2. An arXiv paper [Johnson (2024)](https://arxiv.org/abs/2401.12345)
3. A regular webpage [Brown (2022)](https://example.com/paper)
"""

        # Mock API responses
        mock_crossref.return_value = {
            "title": ["CrossRef Paper Title"],
            "container-title": ["Journal Name"],
            "volume": "10",
        }

        mock_arxiv.return_value = {
            "title": "arXiv Paper Title",
            "authors": ["A. Johnson", "B. Smith"],
        }

        mock_webpage.return_value = "Webpage Title"

        # Create temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(test_content)
            temp_file = Path(f.name)

        try:
            # Process the file
            output_file = temp_file.with_suffix(".bib")
            json_file = temp_file.with_suffix(".json")

            process_markdown_file(temp_file)

            # Check that output files were created
            assert output_file.exists()
            assert json_file.exists()

            # Check BibTeX content
            bibtex_content = output_file.read_text()
            assert "@article{smith2023," in bibtex_content
            assert 'title = "CrossRef Paper Title",' in bibtex_content
            # arXiv papers are classified as @misc
            assert "@misc{" in bibtex_content
            assert 'title = "arXiv Paper Title",' in bibtex_content
            assert "@misc{brown2022," in bibtex_content
            assert 'title = "Webpage Title",' in bibtex_content

            # Check JSON summary
            with open(json_file) as f:
                summary = json.load(f)

            assert summary["total_citations"] == 3
            assert "CrossRef" in summary["metadata_sources"]
            assert "arXiv" in summary["metadata_sources"]
            assert "webpage" in summary["metadata_sources"]

        finally:
            # Clean up
            temp_file.unlink(missing_ok=True)
            output_file.unlink(missing_ok=True)
            json_file.unlink(missing_ok=True)
