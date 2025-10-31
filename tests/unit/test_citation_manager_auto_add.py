"""Unit tests for citation manager auto-add and policy enforcement.

Tests the core functionality for:
- DOI validation with HEAD requests
- Auto-add integration with Zotero API
- Policy enforcement (no Temp keys for valid DOIs)
- Error reporting and caching

All external services (Zotero, CrossRef) are mocked for fast, deterministic tests.
"""

from unittest.mock import patch

import pytest
from src.converters.md_to_latex.citation_manager import (
    Citation,
    CitationManager,
)

# ----------------------
# Fixtures
# ----------------------


@pytest.fixture
def citation_manager():
    """Create a CitationManager instance for testing."""
    # Create with minimal config for testing (no Zotero credentials needed)
    return CitationManager(
        use_better_bibtex_keys=False,
        zotero_api_key="test_key",
        zotero_library_id="test_id",
        zotero_collection=None,  # No collection loading needed for unit tests
    )


@pytest.fixture
def sample_citation_valid():
    """Sample citation with valid DOI."""
    return Citation(
        authors="Duan, Jinhao and Diffenderfer, James",
        year="2025",
        url="https://doi.org/10.48550/arXiv.2506.17419",
        key="duan_uprop_2025",
    )


@pytest.fixture
def sample_citation_invalid_doi():
    """Sample citation with invalid/hallucinated DOI."""
    return Citation(
        authors="Agrawal, A",
        year="2021",
        url="https://doi.org/10.1016/j.compind.2021.107130",
        key="agrawalTemp2021",
    )


@pytest.fixture
def sample_citation_no_doi():
    """Sample citation without DOI (web page)."""
    return Citation(
        authors="Google",
        year="2024",
        url="https://example.com/article",
        key="googleTemp2024",
    )


# ----------------------
# DOI Validation Tests
# ----------------------


def test_validate_doi_success(citation_manager):
    """Test DOI validation with valid DOI returns True."""
    with patch("requests.head") as mock_head:
        mock_head.return_value.status_code = 200

        result = citation_manager._validate_doi("10.48550/arXiv.2506.17419")

        assert result is True
        mock_head.assert_called_once()
        assert (
            "10.48550/arXiv.2506.17419"
            in citation_manager._doi_validation_cache
        )


def test_validate_doi_failure_404(citation_manager):
    """Test DOI validation with invalid DOI (404) returns False."""
    with patch("requests.head") as mock_head:
        mock_head.return_value.status_code = 404

        result = citation_manager._validate_doi("10.1016/j.compind.2021.107130")

        assert result is False
        mock_head.assert_called_once()
        # Check that 404 is cached
        assert (
            citation_manager._doi_validation_cache[
                "10.1016/j.compind.2021.107130"
            ]
            is False
        )


def test_validate_doi_caching(citation_manager):
    """Test that DOI validation results are cached."""
    with patch("requests.head") as mock_head:
        mock_head.return_value.status_code = 404

        # First call - should hit API
        result1 = citation_manager._validate_doi("10.1234/invalid")
        assert result1 is False
        assert mock_head.call_count == 1

        # Second call - should use cache, no additional API call
        result2 = citation_manager._validate_doi("10.1234/invalid")
        assert result2 is False
        assert mock_head.call_count == 1  # Still only 1 call


def test_validate_doi_network_error(citation_manager):
    """Test DOI validation with network error returns False."""
    with patch("requests.head") as mock_head:
        mock_head.side_effect = Exception("Network timeout")

        result = citation_manager._validate_doi("10.1234/any")

        assert result is False
        # Network errors are NOT cached (might be transient)
        assert "10.1234/any" not in citation_manager._doi_validation_cache


# ----------------------
# Extract DOI from URL Tests
# ----------------------


def test_extract_doi_from_doi_url(citation_manager):
    """Test extracting DOI from doi.org URL."""
    doi = citation_manager._extract_doi_from_url(
        "https://doi.org/10.1234/example"
    )
    assert doi == "10.1234/example"


def test_extract_doi_from_dx_doi_url(citation_manager):
    """Test extracting DOI from dx.doi.org URL."""
    doi = citation_manager._extract_doi_from_url(
        "https://dx.doi.org/10.1234/example"
    )
    assert doi == "10.1234/example"


def test_extract_doi_from_arxiv_url(citation_manager):
    """Test extracting DOI from arXiv URL."""
    doi = citation_manager._extract_doi_from_url(
        "https://doi.org/10.48550/arXiv.2506.17419"
    )
    assert doi == "10.48550/arXiv.2506.17419"


def test_extract_doi_from_non_doi_url(citation_manager):
    """Test that non-DOI URLs return None."""
    doi = citation_manager._extract_doi_from_url("https://example.com/article")
    assert doi is None


# ----------------------
# Handle Missing Citation Tests
# ----------------------


def test_handle_missing_citation_valid_doi_auto_adds(
    citation_manager, sample_citation_valid
):
    """Test that valid DOI triggers auto-add and returns Zotero key."""
    with (
        patch("requests.head") as mock_head,
        patch.object(citation_manager, "_fetch_metadata") as mock_fetch,
        patch.object(citation_manager, "citation_matcher") as mock_matcher,
        patch.object(
            citation_manager, "_fetch_newly_added_entry"
        ) as mock_fetch_new,
    ):
        # Setup mocks
        mock_head.return_value.status_code = 200  # Valid DOI
        mock_fetch.return_value = {
            "title": "Sample Paper",
            "authors": ["Duan, Jinhao", "Diffenderfer, James"],
        }
        mock_matcher.add_to_zotero_library.return_value = {"success": True}
        mock_fetch_new.return_value = {"key": "ZOT123"}

        # Call function
        key = citation_manager._handle_missing_citation(
            sample_citation_valid, sample_citation_valid.url
        )

        # Assertions
        assert key == "ZOT123"
        mock_matcher.add_to_zotero_library.assert_called_once_with(
            sample_citation_valid.url
        )
        # Should not have any CRITICAL errors
        critical_errors = [
            e
            for e in citation_manager._citation_errors
            if e["severity"] == "CRITICAL"
        ]
        assert len(critical_errors) == 0


def test_handle_missing_citation_invalid_doi_returns_temp_key(
    citation_manager, sample_citation_invalid_doi
):
    """Test that invalid DOI (404) returns Temp key and logs CRITICAL."""
    with patch("requests.head") as mock_head:
        mock_head.return_value.status_code = 404  # Invalid DOI

        # Call function
        key = citation_manager._handle_missing_citation(
            sample_citation_invalid_doi, sample_citation_invalid_doi.url
        )

        # Assertions
        assert "Temp" in key
        # Should have CRITICAL error logged
        critical_errors = [
            e
            for e in citation_manager._citation_errors
            if e["severity"] == "CRITICAL"
        ]
        assert len(critical_errors) == 1
        assert critical_errors[0]["issue"] == "INVALID_DOI"
        assert "10.1016/j.compind.2021.107130" in critical_errors[0]["doi"]


def test_handle_missing_citation_no_doi_returns_temp_key(
    citation_manager, sample_citation_no_doi
):
    """Test that citation without DOI returns Temp key and logs WARNING."""
    # Call function (no mocking needed - no DOI means no API calls)
    key = citation_manager._handle_missing_citation(
        sample_citation_no_doi, sample_citation_no_doi.url
    )

    # Assertions
    assert "Temp" in key
    # Should have WARNING logged
    warnings = [
        e
        for e in citation_manager._citation_errors
        if e["severity"] == "WARNING"
    ]
    assert len(warnings) == 1
    assert warnings[0]["issue"] == "NO_DOI_OR_FAILED_ADD"


def test_handle_missing_citation_incomplete_metadata(
    citation_manager, sample_citation_valid
):
    """Test that valid DOI with incomplete metadata returns Temp key."""
    with (
        patch("requests.head") as mock_head,
        patch.object(citation_manager, "_fetch_metadata") as mock_fetch,
    ):
        mock_head.return_value.status_code = 200  # Valid DOI
        mock_fetch.return_value = {"title": ""}  # Empty title = incomplete

        # Call function
        key = citation_manager._handle_missing_citation(
            sample_citation_valid, sample_citation_valid.url
        )

        # Assertions
        assert "Temp" in key
        # Should have ERROR logged
        errors = [
            e
            for e in citation_manager._citation_errors
            if e["severity"] == "ERROR"
        ]
        assert len(errors) == 1
        assert errors[0]["issue"] == "INCOMPLETE_METADATA"


def test_handle_missing_citation_zotero_add_fails(
    citation_manager, sample_citation_valid
):
    """Test that failed Zotero add falls back to Temp key."""
    with (
        patch("requests.head") as mock_head,
        patch.object(citation_manager, "_fetch_metadata") as mock_fetch,
        patch.object(citation_manager, "citation_matcher") as mock_matcher,
    ):
        mock_head.return_value.status_code = 200  # Valid DOI
        mock_fetch.return_value = {"title": "Sample", "authors": ["Author"]}
        mock_matcher.add_to_zotero_library.return_value = None  # Add failed

        # Call function
        key = citation_manager._handle_missing_citation(
            sample_citation_valid, sample_citation_valid.url
        )

        # Assertions
        assert "Temp" in key


# ----------------------
# Policy Enforcement Tests
# ----------------------


def test_policy_enforcement_raises_for_temp_key_with_valid_doi(
    citation_manager, sample_citation_invalid_doi
):
    """Test that policy enforcement raises RuntimeError for Temp key + valid DOI."""
    # Modify citation to have Temp key but valid DOI
    sample_citation_invalid_doi.key = "agrawalTemp2021"

    with patch("requests.head") as mock_head:
        mock_head.return_value.status_code = 200  # Valid DOI

        # Should raise RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            citation_manager._enforce_no_temp_key_for_valid_doi(
                sample_citation_invalid_doi
            )

        assert "Policy violation" in str(exc_info.value)
        assert "agrawalTemp2021" in str(exc_info.value)


def test_policy_enforcement_allows_temp_key_with_invalid_doi(
    citation_manager, sample_citation_invalid_doi
):
    """Test that policy enforcement allows Temp key for invalid DOI."""
    sample_citation_invalid_doi.key = "agrawalTemp2021"

    with patch("requests.head") as mock_head:
        mock_head.return_value.status_code = 404  # Invalid DOI

        # Should NOT raise
        try:
            citation_manager._enforce_no_temp_key_for_valid_doi(
                sample_citation_invalid_doi
            )
        except RuntimeError:
            pytest.fail(
                "Policy enforcement should allow Temp key for invalid DOI"
            )


def test_policy_enforcement_allows_temp_key_without_doi(
    citation_manager, sample_citation_no_doi
):
    """Test that policy enforcement allows Temp key for citations without DOI."""
    sample_citation_no_doi.key = "googleTemp2024"

    # Should NOT raise (no DOI means no validation)
    try:
        citation_manager._enforce_no_temp_key_for_valid_doi(
            sample_citation_no_doi
        )
    except RuntimeError:
        pytest.fail(
            "Policy enforcement should allow Temp key for citations without DOI"
        )


def test_policy_enforcement_allows_non_temp_keys(
    citation_manager, sample_citation_valid
):
    """Test that policy enforcement allows non-Temp keys regardless of DOI."""
    sample_citation_valid.key = "duan_uprop_2025"  # Valid Zotero key

    # Should NOT raise
    try:
        citation_manager._enforce_no_temp_key_for_valid_doi(
            sample_citation_valid
        )
    except RuntimeError:
        pytest.fail("Policy enforcement should allow non-Temp keys")


# ----------------------
# Error Reporting Tests
# ----------------------


def test_error_reporting_empty(citation_manager):
    """Test error report with no errors."""
    report = citation_manager.generate_error_report()
    assert "successfully" in report.lower()
    assert "no errors" in report.lower()


def test_error_reporting_with_critical_errors(citation_manager):
    """Test error report includes CRITICAL errors."""
    citation_manager._citation_errors.append(
        {
            "severity": "CRITICAL",
            "issue": "INVALID_DOI",
            "doi": "10.1234/invalid",
            "citation": "Agrawal et al.",
        }
    )

    report = citation_manager.generate_error_report()
    assert "CRITICAL" in report
    assert "10.1234/invalid" in report
    assert "INVALID_DOI" in report


def test_error_reporting_groups_by_severity(citation_manager):
    """Test that error report groups by severity."""
    citation_manager._citation_errors.extend(
        [
            {
                "severity": "CRITICAL",
                "issue": "INVALID_DOI",
                "doi": "10.1234/invalid",
            },
            {
                "severity": "ERROR",
                "issue": "INCOMPLETE_METADATA",
                "doi": "10.5678/incomplete",
            },
            {
                "severity": "WARNING",
                "issue": "NO_DOI",
                "url": "https://example.com",
            },
        ]
    )

    report = citation_manager.generate_error_report()

    # Check that all severity levels appear in order (search for emoji markers)
    critical_pos = report.find("🔴 CRITICAL")
    error_pos = report.find("⚠️  ERROR")
    warning_pos = report.find("ℹ️  WARNING")

    assert critical_pos > 0
    assert error_pos > critical_pos
    assert warning_pos > error_pos


# ----------------------
# Generate Temp Key Tests
# ----------------------


def test_generate_temp_key_format(citation_manager, sample_citation_valid):
    """Test that generated Temp keys follow expected format."""
    key = citation_manager._generate_temp_key(sample_citation_valid)

    assert "Temp" in key
    assert "2025" in key
    # Should include author info
    assert len(key) > 8  # More than just "Temp2025"


def test_generate_temp_key_handles_duplicates(
    citation_manager, sample_citation_valid
):
    """Test that duplicate Temp keys get unique suffixes."""
    key1 = citation_manager._generate_temp_key(sample_citation_valid)

    # Add first key to citations dict to simulate collision
    citation_manager.citations[key1] = sample_citation_valid

    # Generate second key - should have suffix
    key2 = citation_manager._generate_temp_key(sample_citation_valid)

    assert key1 != key2
    assert key2.startswith(
        key1.rstrip("a")
    )  # Should have 'a' suffix or similar
