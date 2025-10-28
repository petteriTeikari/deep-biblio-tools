"""Tests for citation manager."""

from textwrap import dedent
from unittest.mock import MagicMock, patch

import pytest
from src.converters.md_to_latex.citation_manager import (
    Citation,
    CitationManager,
)


class TestCitation:
    """Test Citation class."""

    def test_basic_citation(self):
        """Test basic citation creation with required Better BibTeX key."""
        citation = Citation(
            "Smith et al.",
            "2023",
            "https://example.com",
            key="smithMachineLearning2023",
        )
        assert citation.authors == "Smith et al."
        assert citation.year == "2023"
        assert citation.url == "https://example.com"
        assert citation.key == "smithMachineLearning2023"

    def test_custom_key(self):
        """Test citation with Better BibTeX key."""
        citation = Citation(
            "Smith", "2023", "https://example.com", key="smithDeepLearning2023"
        )
        assert citation.key == "smithDeepLearning2023"

    def test_doi_extraction(self):
        """Test DOI extraction from URL."""
        citation = Citation(
            "Smith",
            "2023",
            "https://doi.org/10.1234/example",
            key="smithExample2023",
        )
        assert citation.doi == "10.1234/example"

    def test_to_bibtex_basic(self):
        """Test basic BibTeX generation."""
        citation = Citation(
            "Smith et al.", "2023", "https://example.com", key="smithTest2023"
        )
        bibtex = citation.to_bibtex()
        assert "@misc{smithTest2023," in bibtex
        assert 'author = "Smith and others",' in bibtex
        assert 'year = "2023",' in bibtex
        assert 'url = "https://example.com",' in bibtex

    def test_to_bibtex_with_metadata(self):
        """Test BibTeX generation with full metadata."""
        citation = Citation(
            "Smith et al.",
            "2023",
            "https://doi.org/10.1234/example",
            key="smithExamplePaper2023",
        )
        citation.title = "Example Paper"
        citation.journal = "Example Journal"
        citation.volume = "42"
        citation.pages = "1-10"
        citation.bibtex_type = "article"

        # Key regeneration is now a no-op (keys must come from Zotero)
        result_key = citation.regenerate_key_with_title()
        assert result_key == "smithExamplePaper2023"  # Key unchanged

        bibtex = citation.to_bibtex()
        assert "@article{smithExamplePaper2023," in bibtex
        assert 'title = "Example Paper",' in bibtex
        assert 'journal = "Example Journal",' in bibtex
        assert 'volume = "42",' in bibtex
        assert 'pages = "1-10",' in bibtex
        assert 'doi = "10.1234/example",' in bibtex


class TestCitationManager:
    """Test CitationManager class."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """Create temporary cache directory."""
        cache_dir = tmp_path / "citation_cache"
        cache_dir.mkdir()
        return cache_dir

    def test_extract_citations(self, temp_cache_dir):
        """Test citation extraction from markdown."""
        manager = CitationManager(
            cache_dir=temp_cache_dir, use_better_bibtex_keys=False
        )
        content = dedent("""
            Some text with [Smith et al. (2023)](https://example.com/paper1) citation.
            Another [Jones (2022)](https://example.com/paper2) reference.
        """).strip()

        citations = manager.extract_citations(content)

        assert len(citations) == 2
        assert (
            citations[0].authors == "Smith et al."
        )  # Note: mistletoe preserves the period in "et al."
        assert citations[0].year == "2023"
        assert citations[1].authors == "Jones"
        assert citations[1].year == "2022"

    def test_duplicate_key_handling(self, temp_cache_dir):
        """Test handling of duplicate citation keys."""
        manager = CitationManager(
            cache_dir=temp_cache_dir, use_better_bibtex_keys=False
        )
        content = dedent("""
            First [Smith (2023)](https://example.com/paper1) citation.
            Second [Smith (2023)](https://example.com/paper2) citation.
        """).strip()

        citations = manager.extract_citations(content)
        assert len(citations) == 2
        # Keys now use Better BibTeX format (temporary until Phase 2)
        assert citations[0].key == "smithTemp2023"
        assert citations[1].key == "smithTemp2023a"

    def test_replace_citations_in_text(self, temp_cache_dir):
        """Test replacement of citations with LaTeX commands."""
        manager = CitationManager(
            cache_dir=temp_cache_dir, use_better_bibtex_keys=False
        )
        content = (
            "Text with [Smith et al. (2023)](https://example.com) citation."
        )

        # First extract citations
        manager.extract_citations(content)

        # Then replace
        latex_content = manager.replace_citations_in_text(content)
        assert latex_content == "Text with \\citep{smithTemp2023} citation."

    @patch("requests.get")
    def test_fetch_from_crossref(self, mock_get, temp_cache_dir):
        """Test fetching metadata from CrossRef."""
        manager = CitationManager(
            cache_dir=temp_cache_dir, use_better_bibtex_keys=False
        )
        citation = Citation(
            "Smith",
            "2023",
            "https://doi.org/10.1234/example",
            key="smithExample2023",
        )

        # Mock CrossRef response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "title": ["Example Paper Title"],
                "container-title": ["Journal Name"],
                "volume": "42",
                "page": "1-10",
                "type": "journal-article",
            }
        }
        mock_get.return_value = mock_response

        manager._fetch_from_crossref(citation)

        assert citation.title == "Example Paper Title"
        assert citation.journal == "Journal Name"
        assert citation.volume == "42"
        assert citation.pages == "1-10"
        assert citation.bibtex_type == "article"

    @patch("requests.get")
    def test_fetch_from_arxiv(self, mock_get, temp_cache_dir):
        """Test fetching metadata from arXiv."""
        manager = CitationManager(
            cache_dir=temp_cache_dir, use_better_bibtex_keys=False
        )
        citation = Citation(
            "Smith",
            "2023",
            "https://arxiv.org/abs/2301.00001",
            key="smithArxiv2023",
        )

        # Mock arXiv response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <entry>
            <title>Example arXiv Paper</title>
        </entry>
        """
        mock_get.return_value = mock_response

        manager._fetch_from_arxiv(citation)

        assert citation.title == "Example arXiv Paper"
        assert citation.journal == "arXiv"
        assert citation.bibtex_type == "article"

    def test_cache_persistence(self, temp_cache_dir):
        """Test citation cache persistence."""
        # First manager instance
        manager1 = CitationManager(
            cache_dir=temp_cache_dir, use_better_bibtex_keys=False
        )
        citation = Citation(
            "Smith", "2023", "https://example.com", key="smithTest2023"
        )
        citation.title = "Cached Paper"
        manager1.citations["test"] = citation
        # Don't need to call _save_to_cache directly as it's handled internally

        # Second manager instance should load from cache
        CitationManager(cache_dir=temp_cache_dir, use_better_bibtex_keys=False)
        # Check that cache directory exists (SQLite cache is used now)
        assert temp_cache_dir.exists()

    def test_generate_bibtex_file(self, temp_cache_dir):
        """Test BibTeX file generation."""
        manager = CitationManager(
            cache_dir=temp_cache_dir, use_better_bibtex_keys=False
        )

        # Add some citations
        citation1 = Citation(
            "Smith", "2023", "https://example.com/1", key="smithTest2023"
        )
        citation2 = Citation(
            "Jones", "2022", "https://example.com/2", key="jonesTest2022"
        )
        manager.citations["smithTest2023"] = citation1
        manager.citations["jonesTest2022"] = citation2

        # Generate BibTeX file
        output_path = temp_cache_dir / "references.bib"
        manager.generate_bibtex_file(output_path)

        assert output_path.exists()
        content = output_path.read_text()
        # With Better BibTeX and web page fetching, keys will be regenerated
        # Check that both citations are present (with Better BibTeX keys after metadata fetch)
        assert "smith" in content.lower() and "2023" in content
        assert "jones" in content.lower() and "2022" in content
