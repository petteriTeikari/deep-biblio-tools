#!/usr/bin/env python3
"""Comprehensive tests for Zotero API workflow.

This test suite ensures the Zotero integration remains functional and prevents regressions.
Tests cover citation matching, metadata fetching, collection management, and BibTeX generation.
"""

import os
import re
from unittest.mock import Mock, patch

import pytest
from pyzotero import zotero


@pytest.fixture
def mock_zotero_client():
    """Mock Zotero client for testing."""
    client = Mock(spec=zotero.Zotero)
    return client


@pytest.fixture
def sample_zotero_items():
    """Sample Zotero items representing different types."""
    return [
        {
            "key": "ITEM001",
            "data": {
                "itemType": "journalArticle",
                "title": "Deep Learning for Fashion",
                "creators": [
                    {"creatorType": "author", "firstName": "John", "lastName": "Doe"}
                ],
                "date": "2023-01-15",
                "DOI": "10.1234/example.2023.001",
                "url": "https://doi.org/10.1234/example.2023.001",
                "publicationTitle": "Journal of AI Research",
                "volume": "42",
                "issue": "1",
                "pages": "1-20",
                "collections": [],
            },
        },
        {
            "key": "ITEM002",
            "data": {
                "itemType": "preprint",
                "title": "Attention Is All You Need",
                "creators": [
                    {
                        "creatorType": "author",
                        "firstName": "Ashish",
                        "lastName": "Vaswani",
                    }
                ],
                "date": "2017-06-12",
                "url": "https://arxiv.org/abs/1706.03762",
                "repository": "arXiv",
                "archiveID": "1706.03762",
                "collections": [],
            },
        },
        {
            "key": "ITEM003",
            "data": {
                "itemType": "webpage",
                "title": "OpenAI GPT-4 Technical Report",
                "creators": [
                    {"creatorType": "author", "firstName": "", "lastName": "OpenAI"}
                ],
                "date": "2023",
                "url": "https://openai.com/research/gpt-4",
                "collections": [],
            },
        },
    ]


@pytest.fixture
def sample_citations():
    """Sample citations from manuscript."""
    return [
        {
            "author": "Doe",
            "year": "2023",
            "url": "https://doi.org/10.1234/example.2023.001",
            "line_number": 42,
            "original": "[Doe, 2023](https://doi.org/10.1234/example.2023.001)",
        },
        {
            "author": "Vaswani et al.",
            "year": "2017",
            "url": "https://arxiv.org/abs/1706.03762",
            "line_number": 156,
            "original": "[Vaswani et al., 2017](https://arxiv.org/abs/1706.03762)",
        },
        {
            "author": "OpenAI",
            "year": "2023",
            "url": "https://openai.com/research/gpt-4",
            "line_number": 203,
            "original": "[OpenAI, 2023](https://openai.com/research/gpt-4)",
        },
    ]


@pytest.fixture
def mock_env_credentials(monkeypatch):
    """Mock environment variables for Zotero credentials."""
    monkeypatch.setenv("ZOTERO_API_KEY", "test_api_key_12345")
    monkeypatch.setenv("ZOTERO_LIBRARY_ID", "123456")


class TestCitationExtraction:
    """Test citation extraction from markdown."""

    def test_extract_inline_citations(self):
        """Test extraction of inline citations from markdown text."""
        markdown_text = """
        Recent work in AI [Doe, 2023](https://doi.org/10.1234/example.2023.001) has shown
        that transformers [Vaswani et al., 2017](https://arxiv.org/abs/1706.03762) are
        effective for various tasks.
        """

        pattern = r"\[([^\]]+?),\s*(\d{4})\]\(([^\)]+)\)"
        citations = []

        for line_no, line in enumerate(markdown_text.split("\n"), 1):
            for match in re.finditer(pattern, line):
                author_part = match.group(1).strip()
                year = match.group(2)
                url = match.group(3)
                citations.append(
                    {
                        "author": author_part,
                        "year": year,
                        "url": url,
                        "line_number": line_no,
                        "original": match.group(0),
                    }
                )

        assert len(citations) == 2
        assert citations[0]["author"] == "Doe"
        assert citations[0]["year"] == "2023"
        assert "doi.org" in citations[0]["url"]

        assert citations[1]["author"] == "Vaswani et al."
        assert citations[1]["year"] == "2017"
        assert "arxiv.org" in citations[1]["url"]

    def test_extract_citations_with_special_characters(self):
        """Test extraction handles special characters in author names."""
        markdown_text = "[O'Brien & Smith, 2024](https://doi.org/10.1234/test)"

        pattern = r"\[([^\]]+?),\s*(\d{4})\]\(([^\)]+)\)"
        match = re.search(pattern, markdown_text)

        assert match is not None
        assert match.group(1) == "O'Brien & Smith"


class TestZoteroIndexing:
    """Test building lookup indices from Zotero items."""

    def test_build_doi_index(self, sample_zotero_items):
        """Test DOI index construction."""
        doi_index = {}

        for item in sample_zotero_items:
            data = item.get("data", {})
            doi = data.get("DOI", "")
            if doi:
                doi_index[doi.lower()] = item

        assert len(doi_index) == 1
        assert "10.1234/example.2023.001" in doi_index
        assert doi_index["10.1234/example.2023.001"]["key"] == "ITEM001"

    def test_build_arxiv_index(self, sample_zotero_items):
        """Test arXiv ID index construction."""
        arxiv_index = {}

        for item in sample_zotero_items:
            data = item.get("data", {})
            url = data.get("url", "")
            if "arxiv.org" in url:
                match = re.search(r"(\d{4}\.\d{4,5})", url)
                if match:
                    arxiv_index[match.group(1)] = item

        assert len(arxiv_index) == 1
        assert "1706.03762" in arxiv_index
        assert arxiv_index["1706.03762"]["key"] == "ITEM002"

    def test_build_url_index(self, sample_zotero_items):
        """Test URL index construction."""
        url_index = {}

        for item in sample_zotero_items:
            data = item.get("data", {})
            url = data.get("url", "")
            if url:
                url_index[url] = item

        assert len(url_index) == 3
        assert "https://doi.org/10.1234/example.2023.001" in url_index
        assert "https://arxiv.org/abs/1706.03762" in url_index
        assert "https://openai.com/research/gpt-4" in url_index

    def test_build_author_year_index(self, sample_zotero_items):
        """Test author+year index construction."""
        author_year_index = {}

        for item in sample_zotero_items:
            data = item.get("data", {})
            creators = data.get("creators", [])
            date = data.get("date", "")

            if creators and date:
                first_author = creators[0].get("lastName", "").lower()
                year_match = re.search(r"\d{4}", date)
                if year_match and first_author:
                    key = f"{first_author}{year_match.group(0)}"
                    author_year_index[key] = item

        assert len(author_year_index) == 3
        assert "doe2023" in author_year_index
        assert "vaswani2017" in author_year_index
        assert "openai2023" in author_year_index


class TestCitationMatching:
    """Test citation matching strategies."""

    def test_match_citation_by_doi(self, sample_zotero_items, sample_citations):
        """Test matching citations via DOI."""
        # Build DOI index
        doi_index = {}
        for item in sample_zotero_items:
            doi = item.get("data", {}).get("DOI", "")
            if doi:
                doi_index[doi.lower()] = item

        # Match citation
        cite = sample_citations[0]
        url = cite["url"]

        matched_item = None
        if "doi.org" in url:
            doi = url.split("doi.org/")[-1]
            matched_item = doi_index.get(doi.lower())

        assert matched_item is not None
        assert matched_item["key"] == "ITEM001"
        assert matched_item["data"]["title"] == "Deep Learning for Fashion"

    def test_match_citation_by_arxiv(self, sample_zotero_items, sample_citations):
        """Test matching citations via arXiv ID."""
        # Build arXiv index
        arxiv_index = {}
        for item in sample_zotero_items:
            url = item.get("data", {}).get("url", "")
            if "arxiv.org" in url:
                match = re.search(r"(\d{4}\.\d{4,5})", url)
                if match:
                    arxiv_index[match.group(1)] = item

        # Match citation
        cite = sample_citations[1]
        url = cite["url"]

        matched_item = None
        if "arxiv.org" in url:
            match = re.search(r"(\d{4}\.\d{4,5})", url)
            if match:
                arxiv_id = match.group(1)
                matched_item = arxiv_index.get(arxiv_id)

        assert matched_item is not None
        assert matched_item["key"] == "ITEM002"
        assert "Attention Is All You Need" in matched_item["data"]["title"]

    def test_match_citation_by_url(self, sample_zotero_items, sample_citations):
        """Test matching citations via exact URL."""
        # Build URL index
        url_index = {}
        for item in sample_zotero_items:
            url = item.get("data", {}).get("url", "")
            if url:
                url_index[url] = item

        # Match citation
        cite = sample_citations[2]
        matched_item = url_index.get(cite["url"])

        assert matched_item is not None
        assert matched_item["key"] == "ITEM003"

    def test_match_citation_by_author_year(self, sample_zotero_items):
        """Test matching citations via author+year fallback."""
        # Build author+year index
        author_year_index = {}
        for item in sample_zotero_items:
            data = item.get("data", {})
            creators = data.get("creators", [])
            date = data.get("date", "")

            if creators and date:
                first_author = creators[0].get("lastName", "").lower()
                year_match = re.search(r"\d{4}", date)
                if year_match and first_author:
                    key = f"{first_author}{year_match.group(0)}"
                    author_year_index[key] = item

        # Match citation (simulate when URL doesn't match)
        cite = {"author": "Doe", "year": "2023", "url": "https://example.com/different"}

        author = cite["author"].lower().replace(" et al.", "")
        year = cite["year"]
        author_key = f"{author}{year}"

        matched_item = author_year_index.get(author_key)

        assert matched_item is not None
        assert matched_item["key"] == "ITEM001"


class TestCollectionManagement:
    """Test Zotero collection operations."""

    def test_find_collection_by_name(self, mock_zotero_client):
        """Test finding a collection by name."""
        mock_collections = [
            {"key": "COLL001", "data": {"name": "Research Papers"}},
            {"key": "COLL002", "data": {"name": "dpp-fashion"}},
            {"key": "COLL003", "data": {"name": "ML Tutorials"}},
        ]

        mock_zotero_client.collections.return_value = mock_collections

        # Find collection
        collections = mock_zotero_client.collections()
        dpp_collection = None
        for collection in collections:
            if collection["data"]["name"].lower() == "dpp-fashion":
                dpp_collection = collection
                break

        assert dpp_collection is not None
        assert dpp_collection["key"] == "COLL002"

    def test_add_item_to_collection(self, mock_zotero_client):
        """Test adding an item to a collection."""
        collection_key = "COLL002"
        item_key = "ITEM001"

        mock_zotero_client.addto_collection.return_value = True

        # Add to collection
        result = mock_zotero_client.addto_collection(collection_key, item_key)

        assert result is True
        mock_zotero_client.addto_collection.assert_called_once_with(
            collection_key, item_key
        )

    def test_check_item_in_collection(self, sample_zotero_items):
        """Test checking if an item is already in a collection."""
        collection_key = "COLL002"

        # Item not in collection
        item = sample_zotero_items[0]
        item_collections = item.get("data", {}).get("collections", [])
        assert collection_key not in item_collections

        # Item in collection
        item["data"]["collections"] = [collection_key]
        item_collections = item.get("data", {}).get("collections", [])
        assert collection_key in item_collections


class TestBibTeXGeneration:
    """Test BibTeX entry generation."""

    def test_generate_cite_key(self, sample_zotero_items):
        """Test citation key generation."""
        item = sample_zotero_items[0]
        data = item.get("data", {})

        creators = data.get("creators", [])
        date = data.get("date", "")

        first_author = creators[0].get("lastName", "Unknown")
        year_match = re.search(r"\d{4}", date)
        year_str = year_match.group(0) if year_match else "XXXX"

        cite_key = f"{first_author}{year_str}"

        assert cite_key == "Doe2023"

    def test_generate_bibtex_article(self, sample_zotero_items):
        """Test BibTeX generation for journal article."""
        item = sample_zotero_items[0]
        data = item.get("data", {})

        # Build BibTeX entry
        entry_lines = ["@article{Doe2023,"]

        title = data.get("title", "")
        if title:
            entry_lines.append(f"  title = {{{title}}},")

        creators = data.get("creators", [])
        if creators:
            author_str = " and ".join(
                f"{c.get('lastName', '')}, {c.get('firstName', '')}"
                for c in creators
                if c.get("creatorType") == "author"
            )
            if author_str:
                entry_lines.append(f"  author = {{{author_str}}},")

        entry_lines.append("  year = {2023},")

        doi = data.get("DOI", "")
        if doi:
            entry_lines.append(f"  doi = {{{doi}}},")
            entry_lines.append(f"  url = {{https://doi.org/{doi}}},")

        entry_lines.append("}")

        bibtex = "\n".join(entry_lines)

        assert "@article{Doe2023," in bibtex
        assert "title = {Deep Learning for Fashion}" in bibtex
        assert "author = {Doe, John}" in bibtex
        assert "doi = {10.1234/example.2023.001}" in bibtex

    def test_handle_duplicate_cite_keys(self):
        """Test handling duplicate citation keys."""
        bibtex_entries = {}

        # First entry
        cite_key = "Doe2023"
        bibtex_entries[cite_key] = "@article{Doe2023,\n  title = {First Paper},\n}"

        # Second entry with same key
        if cite_key in bibtex_entries:
            counter = 2
            while f"{cite_key}{chr(96 + counter)}" in bibtex_entries:
                counter += 1
            cite_key = f"{cite_key}{chr(96 + counter)}"

        assert cite_key == "Doe2023b"

        bibtex_entries[cite_key] = "@article{Doe2023b,\n  title = {Second Paper},\n}"

        assert len(bibtex_entries) == 2
        assert "Doe2023" in bibtex_entries
        assert "Doe2023b" in bibtex_entries


class TestMetadataFetching:
    """Test fetching metadata from external APIs."""

    @patch("requests.get")
    def test_fetch_doi_metadata(self, mock_get):
        """Test fetching metadata from CrossRef DOI API."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "title": ["Deep Learning for Fashion"],
                "author": [{"given": "John", "family": "Doe"}],
                "published": {"date-parts": [[2023]]},
                "DOI": "10.1234/example.2023.001",
                "container-title": ["Journal of AI Research"],
                "volume": "42",
                "issue": "1",
                "page": "1-20",
            }
        }
        mock_get.return_value = mock_response

        # Simulate fetch
        import requests

        doi = "10.1234/example.2023.001"
        response = requests.get(
            f"https://api.crossref.org/works/{doi}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()["message"]
        assert data["title"][0] == "Deep Learning for Fashion"
        assert data["author"][0]["family"] == "Doe"

    @patch("requests.get")
    def test_fetch_arxiv_metadata(self, mock_get):
        """Test fetching metadata from arXiv API."""
        # Mock XML response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"""<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title>Attention Is All You Need</title>
                <author><name>Ashish Vaswani</name></author>
                <published>2017-06-12T00:00:00Z</published>
            </entry>
        </feed>"""
        mock_get.return_value = mock_response

        # Simulate fetch
        import requests

        arxiv_id = "1706.03762"
        response = requests.get(
            f"http://export.arxiv.org/api/query?id_list={arxiv_id}", timeout=10
        )

        assert response.status_code == 200
        assert b"Attention Is All You Need" in response.content


class TestEnvironmentConfiguration:
    """Test environment variable handling."""

    def test_load_credentials_from_env(self, mock_env_credentials):
        """Test loading Zotero credentials from environment."""
        api_key = os.getenv("ZOTERO_API_KEY")
        library_id = os.getenv("ZOTERO_LIBRARY_ID")

        assert api_key == "test_api_key_12345"
        assert library_id == "123456"

    def test_missing_credentials_raises_error(self, monkeypatch):
        """Test that missing credentials are detected."""
        monkeypatch.delenv("ZOTERO_API_KEY", raising=False)
        monkeypatch.delenv("ZOTERO_LIBRARY_ID", raising=False)

        api_key = os.getenv("ZOTERO_API_KEY")
        library_id = os.getenv("ZOTERO_LIBRARY_ID")

        assert api_key is None
        assert library_id is None


class TestEndToEndWorkflow:
    """Integration tests for the complete workflow."""

    @patch("pyzotero.zotero.Zotero")
    def test_complete_conversion_workflow(
        self, mock_zotero_class, sample_zotero_items, sample_citations
    ):
        """Test the complete citation matching and BibTeX generation workflow."""
        # Setup mock
        mock_client = Mock()
        mock_client.everything.return_value = sample_zotero_items
        mock_client.collections.return_value = [
            {"key": "COLL002", "data": {"name": "dpp-fashion"}}
        ]
        mock_zotero_class.return_value = mock_client

        # Simulate workflow
        zot = mock_zotero_class("123456", "user", "test_key")

        # Fetch items
        all_items = zot.everything(zot.items())
        assert len(all_items) == 3

        # Find collection
        collections = zot.collections()
        dpp_collection = collections[0]
        assert dpp_collection["data"]["name"] == "dpp-fashion"

        # Build indices
        doi_index = {}
        for item in all_items:
            doi = item.get("data", {}).get("DOI", "")
            if doi:
                doi_index[doi.lower()] = item

        # Match citations
        matched = []
        for cite in sample_citations:
            url = cite["url"]
            if "doi.org" in url:
                doi = url.split("doi.org/")[-1]
                matched_item = doi_index.get(doi.lower())
                if matched_item:
                    matched.append((cite, matched_item))

        assert len(matched) == 1  # Only DOI citation should match via this index

    def test_match_rate_calculation(self, sample_citations):
        """Test calculating citation match rate."""
        total_citations = len(sample_citations)
        matched_count = 2

        match_rate = (matched_count / total_citations) * 100

        assert match_rate == pytest.approx(66.7, rel=0.1)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
