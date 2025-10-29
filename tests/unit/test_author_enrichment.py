"""Unit tests for author enrichment functionality.

Tests automatic fetching of complete author lists from CrossRef and arXiv APIs.
"""

import pytest
from unittest.mock import Mock, patch
from src.converters.md_to_latex.author_enrichment import AuthorEnricher


@pytest.fixture
def enricher():
    """Create an AuthorEnricher instance for testing."""
    return AuthorEnricher()


@pytest.fixture
def entry_with_truncated_authors():
    """Sample BibTeX entry with truncated authors."""
    return {
        "ID": "duan_uprop_2025",
        "ENTRYTYPE": "misc",
        "author": "Duan and others",
        "title": "UProp: Uncertainty-Aware Prompt Selection",
        "year": "2025",
        "doi": "10.48550/arXiv.2506.17419",
    }


@pytest.fixture
def entry_with_complete_authors():
    """Sample BibTeX entry with complete author list."""
    return {
        "ID": "smith_test_2024",
        "ENTRYTYPE": "article",
        "author": "Smith, John and Doe, Jane and Brown, Alice",
        "title": "Test Article",
        "year": "2024",
        "doi": "10.1234/test",
    }


@pytest.fixture
def crossref_response_mock():
    """Mock CrossRef API response with complete authors."""
    return {
        "message": {
            "author": [
                {"family": "Duan", "given": "Jinhao"},
                {"family": "Diffenderfer", "given": "James"},
                {"family": "Kurtic", "given": "Eldar"},
                {"family": "Gusak", "given": "Julia"},
                {"family": "Hooper", "given": "Daniel"},
                {"family": "Kailkhura", "given": "Bhavya"},
            ]
        }
    }


# ----------------------
# Detection Tests
# ----------------------

def test_has_truncated_authors_with_and_others(enricher):
    """Test detection of 'and others' truncation."""
    author = "Duan and others"
    assert enricher._has_truncated_authors(author) is True


def test_has_truncated_authors_with_et_al(enricher):
    """Test detection of 'et al' truncation."""
    author = "Smith, John et al."
    assert enricher._has_truncated_authors(author) is True


def test_has_truncated_authors_complete(enricher):
    """Test that complete author lists are not flagged."""
    author = "Smith, John and Doe, Jane and Brown, Alice"
    assert enricher._has_truncated_authors(author) is False


def test_has_truncated_authors_empty(enricher):
    """Test that empty author fields are not flagged."""
    assert enricher._has_truncated_authors("") is False
    assert enricher._has_truncated_authors("   ") is False


# ----------------------
# arXiv ID Extraction Tests
# ----------------------

def test_extract_arxiv_id_from_eprint(enricher):
    """Test extraction from eprint field."""
    entry = {"eprint": "2401.13178"}
    assert enricher._extract_arxiv_id(entry) == "2401.13178"


def test_extract_arxiv_id_from_doi(enricher):
    """Test extraction from arXiv DOI."""
    entry = {"doi": "10.48550/arXiv.2506.17419"}
    assert enricher._extract_arxiv_id(entry) == "2506.17419"


def test_extract_arxiv_id_from_url_abs(enricher):
    """Test extraction from arXiv abs URL."""
    entry = {"url": "https://arxiv.org/abs/2401.13178"}
    assert enricher._extract_arxiv_id(entry) == "2401.13178"


def test_extract_arxiv_id_from_url_pdf(enricher):
    """Test extraction from arXiv PDF URL."""
    entry = {"url": "https://arxiv.org/pdf/2401.13178.pdf"}
    assert enricher._extract_arxiv_id(entry) == "2401.13178"


def test_extract_arxiv_id_not_found(enricher):
    """Test when no arXiv ID is present."""
    entry = {"doi": "10.1234/regular.doi"}
    assert enricher._extract_arxiv_id(entry) is None


# ----------------------
# CrossRef Fetching Tests
# ----------------------

def test_fetch_authors_from_crossref_success(enricher, crossref_response_mock):
    """Test successful author fetching from CrossRef."""
    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = crossref_response_mock
        mock_get.return_value = mock_response

        authors = enricher._fetch_authors_from_crossref("10.48550/arXiv.2506.17419")

        assert authors is not None
        assert "Duan, Jinhao" in authors
        assert "Diffenderfer, James" in authors
        assert " and " in authors  # BibTeX format
        assert authors.count(" and ") == 5  # 6 authors = 5 "and"s


def test_fetch_authors_from_crossref_404(enricher):
    """Test CrossRef fetch with invalid DOI."""
    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        authors = enricher._fetch_authors_from_crossref("10.1234/invalid")

        assert authors is None


def test_fetch_authors_from_crossref_network_error(enricher):
    """Test CrossRef fetch with network error."""
    with patch("requests.get") as mock_get:
        mock_get.side_effect = Exception("Network error")

        authors = enricher._fetch_authors_from_crossref("10.1234/any")

        assert authors is None


def test_fetch_authors_from_crossref_caching(enricher, crossref_response_mock):
    """Test that CrossRef results are cached."""
    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = crossref_response_mock
        mock_get.return_value = mock_response

        # First call - should hit API
        authors1 = enricher._fetch_authors_from_crossref("10.48550/arXiv.2506.17419")
        assert mock_get.call_count == 1

        # Second call - should use cache
        authors2 = enricher._fetch_authors_from_crossref("10.48550/arXiv.2506.17419")
        assert mock_get.call_count == 1  # Still only 1 call

        # Results should be the same
        assert authors1 == authors2


# ----------------------
# arXiv Fetching Tests
# ----------------------

def test_fetch_authors_from_arxiv_success(enricher):
    """Test successful author fetching from arXiv."""
    arxiv_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <author><name>John Smith</name></author>
        <author><name>Jane Doe</name></author>
        <author><name>Alice Brown</name></author>
      </entry>
    </feed>"""

    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = arxiv_xml
        mock_get.return_value = mock_response

        authors = enricher._fetch_authors_from_arxiv("2401.13178")

        assert authors is not None
        assert "Smith, John" in authors
        assert "Doe, Jane" in authors
        assert "Brown, Alice" in authors
        assert " and " in authors


def test_parse_arxiv_authors(enricher):
    """Test parsing authors from arXiv XML."""
    xml = """
    <author><name>John Smith</name></author>
    <author><name>Jane M. Doe</name></author>
    """

    authors = enricher._parse_arxiv_authors(xml)

    assert len(authors) == 2
    assert "Smith, John" in authors
    assert "Doe, Jane M." in authors


# ----------------------
# Entry Enrichment Tests
# ----------------------

def test_enrich_entry_with_crossref(enricher, entry_with_truncated_authors, crossref_response_mock):
    """Test enriching an entry using CrossRef."""
    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = crossref_response_mock
        mock_get.return_value = mock_response

        enriched = enricher._enrich_entry(entry_with_truncated_authors)

        assert enriched is not None
        assert enriched["author"] != entry_with_truncated_authors["author"]
        assert "Duan, Jinhao" in enriched["author"]
        assert "and others" not in enriched["author"]


def test_enrich_entry_no_doi(enricher):
    """Test enriching an entry without DOI or arXiv ID."""
    entry = {
        "ID": "test_2024",
        "author": "Smith and others",
        "title": "Test",
        "year": "2024",
    }

    enriched = enricher._enrich_entry(entry)

    assert enriched is None  # Can't enrich without identifier


def test_enrich_bibtex_entries_mixed(enricher, crossref_response_mock):
    """Test enriching a collection with mixed entries."""
    entries = {
        "truncated": {
            "author": "Duan and others",
            "doi": "10.48550/arXiv.2506.17419",
        },
        "complete": {
            "author": "Smith, John and Doe, Jane",
            "doi": "10.1234/test",
        },
    }

    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = crossref_response_mock
        mock_get.return_value = mock_response

        enriched_dict = enricher.enrich_bibtex_entries(entries)

        # Check statistics
        stats = enricher.get_stats()
        assert stats["total_entries"] == 2
        assert stats["truncated_detected"] == 1  # Only "truncated" entry
        assert stats["enriched_success"] == 1


def test_enrich_bibtex_entries_empty(enricher):
    """Test enriching an empty collection."""
    entries = {}
    enriched = enricher.enrich_bibtex_entries(entries)

    assert enriched == {}
    stats = enricher.get_stats()
    assert stats["total_entries"] == 0


# ----------------------
# Statistics Tests
# ----------------------

def test_get_stats_initial(enricher):
    """Test initial statistics are zero."""
    stats = enricher.get_stats()

    assert stats["total_entries"] == 0
    assert stats["truncated_detected"] == 0
    assert stats["enriched_success"] == 0
    assert stats["enriched_failed"] == 0


def test_get_stats_after_enrichment(enricher):
    """Test statistics are updated after enrichment."""
    entries = {
        "test1": {"author": "Smith and others", "doi": "10.1234/invalid"},
        "test2": {"author": "Doe, Jane"},
    }

    with patch("requests.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 404  # Simulate failure
        mock_get.return_value = mock_response

        enricher.enrich_bibtex_entries(entries)

        stats = enricher.get_stats()
        assert stats["total_entries"] == 2
        assert stats["truncated_detected"] == 1
        assert stats["enriched_failed"] == 1  # Failed due to 404
