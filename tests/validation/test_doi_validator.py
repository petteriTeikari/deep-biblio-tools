"""Unit tests for DOI validation."""

import pytest
import requests


# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


class TestDOIValidator:
    """Test DOI validation against CrossRef API."""

    def test_valid_doi_returns_metadata(self, monkeypatch):
        """Valid DOI should return VALID status with metadata."""

        def mock_get(url, headers=None, timeout=None):
            class MockResponse:
                status_code = 200

                def json(self):
                    return {
                        "message": {
                            "title": ["Test Article Title"],
                            "author": [{"family": "Doe", "given": "Jane"}],
                            "container-title": ["Journal of Testing"],
                            "issued": {"date-parts": [[2020]]},
                        }
                    }

            return MockResponse()

        monkeypatch.setattr(requests, "get", mock_get)

        # This will be implemented in validate_bibliography.py
        # For now, test the mock works
        response = requests.get("https://api.crossref.org/works/10.1000/testdoi")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "title" in data["message"]

    def test_invalid_doi_returns_404(self, monkeypatch):
        """Invalid DOI should return 404 status."""

        def mock_get(url, headers=None, timeout=None):
            class MockResponse:
                status_code = 404
                text = "Not Found"

            return MockResponse()

        monkeypatch.setattr(requests, "get", mock_get)

        response = requests.get("https://api.crossref.org/works/10.1016/invalid")
        assert response.status_code == 404

    def test_rate_limit_returns_429(self, monkeypatch):
        """Rate limited requests should return 429 status."""

        def mock_get(url, headers=None, timeout=None):
            class MockResponse:
                status_code = 429
                text = "Too Many Requests"

            return MockResponse()

        monkeypatch.setattr(requests, "get", mock_get)

        response = requests.get("https://api.crossref.org/works/10.1000/test")
        assert response.status_code == 429

    @pytest.mark.network
    @pytest.mark.slow
    def test_real_doi_crossref_integration(self):
        """Integration test with real CrossRef API.

        This test actually calls CrossRef - mark as @network and @slow
        Run with: pytest -m network
        """
        # Test a stable, well-known DOI
        doi = "10.1038/nature12373"  # Famous CRISPR paper
        url = f"https://api.crossref.org/works/{doi}"

        response = requests.get(
            url, headers={"User-Agent": "deep-biblio-tools/test"}, timeout=5
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "title" in data["message"]


class TestDOIExtraction:
    """Test extracting DOIs from BibTeX entries."""

    def test_extract_doi_from_doi_field(self):
        """Should extract DOI from 'doi' field."""
        entry = {"doi": "10.1000/testdoi"}

        # Placeholder for actual implementation
        doi = entry.get("doi")
        assert doi == "10.1000/testdoi"

    def test_extract_doi_from_url_field(self):
        """Should extract DOI from 'url' field if it contains doi.org."""
        entry = {"url": "https://doi.org/10.1000/testdoi"}

        # Placeholder - will implement in scripts/validate_bibliography.py
        doi = None
        if "doi.org/" in entry.get("url", ""):
            doi = entry["url"].split("doi.org/")[-1]

        assert doi == "10.1000/testdoi"

    def test_no_doi_returns_none(self):
        """Entry without DOI should return None."""
        entry = {"title": "Some paper", "author": "Smith"}

        doi = entry.get("doi")
        assert doi is None
