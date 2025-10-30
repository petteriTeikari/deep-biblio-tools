"""Unit tests for CitationManager.validate_no_temp_keys() method.

Tests the CRITICAL validation that blocks conversion when citations
are missing from Zotero (have temporary keys).
"""

import pytest
from src.converters.md_to_latex.citation_manager import (
    Citation,
    CitationManager,
)


def create_citation(key, authors, year, url, title="Test Title"):
    """Helper to create Citation with title (title not in __init__)."""
    c = Citation(key=key, authors=authors, year=year, url=url)
    c.title = title
    return c


@pytest.fixture
def citation_manager(tmp_path):
    """Create CitationManager instance for testing."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return CitationManager(
        cache_dir=cache_dir,
        zotero_api_key="test_key",  # Fake credentials for testing
        zotero_library_id="test_library",
        zotero_collection=None,
        enable_auto_add=False,
        use_cache=False,  # Disable cache for faster tests
        use_better_bibtex_keys=True,  # Test Better BibTeX mode
    )


class TestValidateNoTempKeys:
    """Test temporary key detection and validation."""

    def test_no_temp_keys_passes(self, citation_manager):
        """Test that validation passes with all proper Better BibTeX keys."""
        # Add citations with proper Better BibTeX keys
        c1 = Citation(
            key="adisornDigitalProductPassport2021",
            authors="Adisorn, Travis",
            year="2021",
            url="https://doi.org/10.1234/example",
        )
        c1.title = "Digital Product Passport"

        c2 = Citation(
            key="niinimaekiEnvironmentalSustainability2020",
            authors="Niinimäki, Kirsi",
            year="2020",
            url="https://doi.org/10.5678/example",
        )
        c2.title = "Environmental Sustainability"

        citation_manager.citations = {
            "adisornDigitalProductPassport2021": c1,
            "niinimaekiEnvironmentalSustainability2020": c2,
        }

        # Should not raise
        temp_keys = citation_manager.validate_no_temp_keys(fail_on_temp=True)
        assert temp_keys == []

    def test_temp_key_detected_and_fails(self, citation_manager):
        """Test that Temp keys are detected and cause failure."""
        citation_manager.citations = {
            "smithTemp2024": create_citation(
                key="smithTemp2024",
                authors="Smith, John",
                year="2024",
                url="https://example.com/paper",
                title="Some Paper",
            )
        }

        # Should raise RuntimeError
        with pytest.raises(
            RuntimeError, match="VALIDATION FAILED.*missing from Zotero"
        ):
            citation_manager.validate_no_temp_keys(fail_on_temp=True)

    def test_dryrun_key_detected_and_fails(self, citation_manager):
        """Test that dryrun_ keys are detected and cause failure."""
        citation_manager.citations = {
            "dryrun_1761780981742": create_citation(
                key="dryrun_1761780981742",
                authors="European Commission",
                year="2024",
                url="https://commission.europa.eu/...",
                title="Some Document",
            )
        }

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="dryrun_"):
            citation_manager.validate_no_temp_keys(fail_on_temp=True)

    def test_multiple_temp_keys_counted(self, citation_manager):
        """Test that multiple temp keys are all detected."""
        citation_manager.citations = {
            "smithTemp2024": create_citation(
                key="smithTemp2024",
                authors="Smith",
                year="2024",
                url="https://example.com/1",
                title="Paper 1",
            ),
            "axiosTemp2025": create_citation(
                key="axiosTemp2025",
                authors="Axios",
                year="2025",
                url="https://axios.com/article",
                title="Paper 2",
            ),
            "dryrun_123": create_citation(
                key="dryrun_123",
                authors="BBC",
                year="2024",
                url="https://bbc.com/news",
                title="Paper 3",
            ),
        }

        with pytest.raises(RuntimeError, match="3 citations missing"):
            citation_manager.validate_no_temp_keys(fail_on_temp=True)

    def test_fail_on_temp_false_returns_list(self, citation_manager):
        """Test that fail_on_temp=False returns list without raising."""
        citation_manager.citations = {
            "smithTemp2024": create_citation(
                key="smithTemp2024",
                authors="Smith",
                year="2024",
                url="https://example.com",
                title="Paper",
            ),
            "goodKey2024": create_citation(
                key="goodDescriptiveLongKey2024",
                authors="Good",
                year="2024",
                url="https://doi.org/10.1234/good",
                title="Good Paper",
            ),
        }

        # Should NOT raise, but return list of temp keys
        temp_keys = citation_manager.validate_no_temp_keys(fail_on_temp=False)

        assert len(temp_keys) == 1
        assert temp_keys[0]["key"] == "smithTemp2024"
        assert temp_keys[0]["url"] == "https://example.com"
        assert temp_keys[0]["authors"] == "Smith"

    def test_include_dryrun_false_skips_dryrun_keys(self, citation_manager):
        """Test that include_dryrun=False only checks Temp keys."""
        citation_manager.citations = {
            "dryrun_123": create_citation(
                key="dryrun_123",
                authors="Test",
                year="2024",
                url="https://example.com",
                title="Dry Run Entry",
            )
        }

        # Should NOT fail when include_dryrun=False
        temp_keys = citation_manager.validate_no_temp_keys(
            fail_on_temp=True, include_dryrun=False
        )
        assert temp_keys == []

    def test_temp_prefix_variant_detected(self, citation_manager):
        """Test that temp_ prefix variant is also detected."""
        citation_manager.citations = {
            "temp_generated_key": create_citation(
                key="temp_generated_key",
                authors="Author",
                year="2024",
                url="https://example.com",
                title="Paper",
            )
        }

        with pytest.raises(RuntimeError):
            citation_manager.validate_no_temp_keys(fail_on_temp=True)

    def test_error_message_contains_helpful_info(self, citation_manager):
        """Test that error message contains actionable information."""
        citation_manager.citations = {
            "axiosTemp2025": create_citation(
                key="axiosTemp2025",
                authors="Axios",
                year="2025",
                url="https://axios.com/article",
                title="Article",
            )
        }

        with pytest.raises(RuntimeError) as exc_info:
            citation_manager.validate_no_temp_keys(fail_on_temp=True)

        error_msg = str(exc_info.value)
        # Should contain helpful information
        assert "VALIDATION FAILED" in error_msg
        assert "--auto-add-real" in error_msg
        assert "manually add" in error_msg.lower()
        assert "axiosTemp2025" in error_msg
        assert "https://axios.com/article" in error_msg

    def test_more_than_10_keys_shows_ellipsis(self, citation_manager):
        """Test that >10 temp keys shows truncated list."""
        # Create 15 temp keys
        citation_manager.citations = {
            f"temp{i}": create_citation(
                key=f"temp{i}",
                authors=f"Author{i}",
                year="2024",
                url=f"https://example.com/{i}",
                title=f"Paper {i}",
            )
            for i in range(15)
        }

        with pytest.raises(RuntimeError) as exc_info:
            citation_manager.validate_no_temp_keys(fail_on_temp=True)

        error_msg = str(exc_info.value)
        assert (
            "... and 5 more" in error_msg
        )  # Shows ellipsis for 15-10=5 hidden

    def test_mixed_valid_and_temp_keys(self, citation_manager):
        """Test validation with mix of valid and temp keys."""
        citation_manager.citations = {
            "validBetterBibTeXKey2024": create_citation(
                key="validBetterBibTeXKey2024",
                authors="Smith, John",
                year="2024",
                url="https://doi.org/10.1234/valid",
                title="Valid Paper",
            ),
            "anotherValidKey2023": create_citation(
                key="anotherValidKey2023",
                authors="Doe, Jane",
                year="2023",
                url="https://doi.org/10.5678/valid",
                title="Another Valid",
            ),
            "problemTemp2024": create_citation(
                key="problemTemp2024",
                authors="Problem",
                year="2024",
                url="https://example.com/problem",
                title="Problem Paper",
            ),
        }

        # Should detect the 1 temp key among 3 total
        with pytest.raises(RuntimeError, match="1 citations missing"):
            citation_manager.validate_no_temp_keys(fail_on_temp=True)

        # Also check non-raising mode
        temp_keys = citation_manager.validate_no_temp_keys(fail_on_temp=False)
        assert len(temp_keys) == 1
        assert temp_keys[0]["key"] == "problemTemp2024"


class TestRealWorldScenarios:
    """Test based on actual scenarios from troubleshooting doc."""

    def test_axios_example_scenario(self, citation_manager):
        """Test Axios example from bibliography-quality-analysis.md."""
        citation_manager.citations = {
            "axiosTemp2025": create_citation(
                key="axiosTemp2025",
                authors="Axios",
                year="2025",
                url="https://www.axios.com/2025/02/20/ai-agi-timeline-promises-openai-anthropic-deepmind",
                title="Web page by Axios",
            )
        }

        with pytest.raises(RuntimeError) as exc_info:
            citation_manager.validate_no_temp_keys(fail_on_temp=True)

        assert "axiosTemp2025" in str(exc_info.value)
        assert "axios.com" in str(exc_info.value)

    def test_dryrun_european_commission_scenario(self, citation_manager):
        """Test dry-run entry from troubleshooting doc."""
        citation_manager.citations = {
            "dryrun_1761780981742": create_citation(
                key="dryrun_1761780981742",
                authors="European Commission",
                year="2024",
                url="https://commission.europa.eu/energy-climate-change-environment/...",
                title="",
            )
        }

        with pytest.raises(RuntimeError) as exc_info:
            citation_manager.validate_no_temp_keys(fail_on_temp=True)

        assert "dryrun_1761780981742" in str(exc_info.value)

    def test_266_matched_but_22_temp_keys_scenario(self, citation_manager):
        """Test scenario from doc: 266 matched, 22 temp keys."""
        # Simulate 266 good citations + 22 temp keys
        good_citations = {
            f"validKey{i}2024": create_citation(
                key=f"validKey{i}2024",
                authors=f"Author{i}",
                year="2024",
                url=f"https://doi.org/10.1234/{i}",
                title=f"Paper {i}",
            )
            for i in range(266)
        }

        temp_citations = {
            f"temp{i}": create_citation(
                key=f"temp{i}",
                authors=f"TempAuthor{i}",
                year="2024",
                url=f"https://example.com/{i}",
                title=f"Temp Paper {i}",
            )
            for i in range(22)
        }

        citation_manager.citations = {**good_citations, **temp_citations}

        # Should detect 22 temp keys
        with pytest.raises(RuntimeError, match="22 citations missing"):
            citation_manager.validate_no_temp_keys(fail_on_temp=True)
