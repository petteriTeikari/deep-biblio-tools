"""Test Zotero integration functionality."""

from unittest.mock import MagicMock, patch

import pytest
from src.converters.md_to_latex.zotero_integration import (
    ZoteroClient,
)


@pytest.fixture(autouse=True)
def clear_zotero_env_vars(monkeypatch):
    """Clear Zotero environment variables to prevent test pollution."""
    monkeypatch.delenv("ZOTERO_API_KEY", raising=False)
    monkeypatch.delenv("ZOTERO_LIBRARY_ID", raising=False)
    monkeypatch.delenv("ZOTERO_LIBRARY_TYPE", raising=False)


class TestZoteroClient:
    """Test ZoteroClient functionality."""

    def test_initialization(self):
        """Test client initialization."""
        # Without credentials
        client = ZoteroClient()
        assert client.api_key is None
        assert client.library_id is None

        # With credentials
        client = ZoteroClient(api_key="test_key", library_id="12345")
        assert client.api_key == "test_key"
        assert client.library_id == "12345"

    @patch("requests.post")
    def test_search_by_identifier_translation_server(self, mock_post):
        """Test searching via translation server."""
        client = ZoteroClient()

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "itemType": "journalArticle",
                "title": "NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis",
                "creators": [
                    {
                        "firstName": "Ben",
                        "lastName": "Mildenhall",
                        "creatorType": "author",
                    }
                ],
                "date": "2020",
                "DOI": "10.1145/3503250",
            }
        ]
        mock_post.return_value = mock_response

        result = client.search_by_identifier("10.1145/3503250")

        assert result is not None
        assert (
            result["title"]
            == "NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis"
        )
        assert result["DOI"] == "10.1145/3503250"

        # Verify the request was made correctly
        mock_post.assert_called_once_with(
            "https://translate.zotero.org/search",
            data="10.1145/3503250",
            headers={
                "Content-Type": "text/plain",
                "Accept": "application/json",
            },
            timeout=10,
        )

    @patch("requests.post")
    def test_search_by_identifier_translation_server_failure(self, mock_post):
        """Test fallback when translation server fails."""
        client = ZoteroClient()

        # Mock failed response
        mock_post.side_effect = Exception("Connection error")

        result = client.search_by_identifier("10.1145/3503250")

        # Should return None when no library configured
        assert result is None

    @patch("requests.get")
    def test_search_library(self, mock_get):
        """Test searching user's library."""
        client = ZoteroClient(api_key="test_key", library_id="12345")

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "data": {
                    "itemType": "journalArticle",
                    "title": "Test Article",
                    "creators": [
                        {
                            "firstName": "John",
                            "lastName": "Doe",
                            "creatorType": "author",
                        }
                    ],
                    "date": "2023",
                }
            }
        ]
        mock_get.return_value = mock_response

        result = client._search_library("test query")

        assert result is not None
        assert result["title"] == "Test Article"

        # Verify the request
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "users/12345/items" in call_args[0][0]
        assert call_args[1]["params"]["q"] == "test query"
        assert call_args[1]["headers"]["Zotero-API-Key"] == "test_key"

    def test_format_bibtex(self):
        """Test BibTeX formatting."""
        client = ZoteroClient()

        item_data = {
            "itemType": "journalArticle",
            "title": "NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis",
            "creators": [
                {
                    "firstName": "Ben",
                    "lastName": "Mildenhall",
                    "creatorType": "author",
                },
                {
                    "firstName": "Pratul P.",
                    "lastName": "Srinivasan",
                    "creatorType": "author",
                },
            ],
            "date": "2020",
            "publicationTitle": "European Conference on Computer Vision",
            "volume": "65",
            "issue": "1",
            "pages": "405-421",
            "DOI": "10.1145/3503250",
            "url": "https://doi.org/10.1145/3503250",
            "abstractNote": "We present a method that achieves state-of-the-art results...",
        }

        bibtex = client.format_bibtex(item_data)

        # Check key generation
        assert "@article{mildenhall2020Nerf," in bibtex

        # Check required fields
        assert 'author = "Ben Mildenhall and Pratul P. Srinivasan"' in bibtex
        assert (
            'title = "NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis"'
            in bibtex
        )
        assert 'year = "2020"' in bibtex
        assert 'journal = "European Conference on Computer Vision"' in bibtex
        assert 'volume = "65"' in bibtex
        assert 'number = "1"' in bibtex
        assert 'pages = "405-421"' in bibtex
        assert 'doi = "10.1145/3503250"' in bibtex

    def test_format_bibtex_minimal(self):
        """Test BibTeX formatting with minimal data."""
        client = ZoteroClient()

        item_data = {"itemType": "misc", "title": "Some Title"}

        bibtex = client.format_bibtex(item_data)

        # Should still generate valid BibTeX
        assert "@misc{" in bibtex
        assert 'title = "Some Title"' in bibtex

    def test_extract_year(self):
        """Test year extraction from various date formats."""
        client = ZoteroClient()

        assert client._extract_year("2023") == "2023"
        assert client._extract_year("2023-05-15") == "2023"
        assert client._extract_year("May 15, 2023") == "2023"
        assert client._extract_year("Published in 2023") == "2023"
        assert client._extract_year("") == ""
        assert client._extract_year("no year here") == ""

    def test_get_first_title_word(self):
        """Test extraction of first significant word from title."""
        client = ZoteroClient()

        assert client._get_first_title_word("The NeRF Revolution") == "Nerf"
        assert (
            client._get_first_title_word("A Study of Neural Networks")
            == "Study"
        )
        assert client._get_first_title_word("In the Beginning") == "Beginning"
        assert client._get_first_title_word("On AI") == ""  # Too short
        assert client._get_first_title_word("") == ""


@pytest.mark.integration
class TestZoteroIntegration:
    """Integration tests with actual Zotero translation server."""

    def test_real_translation_server(self):
        """Test with real Zotero translation server."""
        client = ZoteroClient()

        # Test with a known DOI
        result = client.search_by_identifier("10.1145/3503250")

        if result:
            assert "title" in result
            assert "NeRF" in result["title"]
