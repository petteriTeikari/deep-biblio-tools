"""Unit tests for site author mapping functionality."""

import pytest
from src.converters.md_to_latex.site_author_mapping import (
    SITE_AUTHOR_MAPPINGS,
    add_site_mapping,
    augment_metadata_with_site_author,
    extract_author_from_url,
    extract_domain,
    get_known_domains,
)


class TestExtractDomain:
    """Tests for domain extraction from URLs."""

    def test_extract_domain_simple(self):
        """Test basic domain extraction."""
        assert extract_domain("https://www.bbc.com/news/article") == "bbc.com"
        assert (
            extract_domain("https://bloomberg.com/economy") == "bloomberg.com"
        )

    def test_extract_domain_removes_www(self):
        """Test that www. prefix is removed."""
        assert extract_domain("https://www.bbc.com/news") == "bbc.com"
        assert extract_domain("https://www.europa.eu/policy") == "europa.eu"

    def test_extract_domain_preserves_subdomain(self):
        """Test that non-www subdomains are preserved."""
        assert extract_domain("https://ec.europa.eu/policy") == "ec.europa.eu"
        assert (
            extract_domain("https://news.bbc.co.uk/article") == "news.bbc.co.uk"
        )

    def test_extract_domain_handles_query_params(self):
        """Test domain extraction ignores query parameters."""
        assert (
            extract_domain("https://www.bbc.com/news?id=123&ref=abc")
            == "bbc.com"
        )

    def test_extract_domain_handles_fragments(self):
        """Test domain extraction ignores URL fragments."""
        assert extract_domain("https://www.bbc.com/news#section") == "bbc.com"

    def test_extract_domain_invalid_url(self):
        """Test that invalid URLs return None."""
        assert extract_domain("not-a-url") is None
        assert extract_domain("") is None

    def test_extract_domain_case_insensitive(self):
        """Test that domain is returned in lowercase."""
        assert extract_domain("https://WWW.BBC.COM/news") == "bbc.com"


class TestExtractAuthorFromUrl:
    """Tests for author extraction from URLs."""

    def test_known_site_direct_match(self):
        """Test direct mapping for known sites."""
        assert (
            extract_author_from_url(
                "https://www.bbc.com/news/business-44885983"
            )
            == "BBC"
        )
        assert (
            extract_author_from_url("https://bloomberg.com/article")
            == "Bloomberg"
        )
        assert (
            extract_author_from_url("https://reuters.com/article") == "Reuters"
        )

    def test_known_site_subdomain(self):
        """Test subdomain handling for known sites."""
        # ec.europa.eu should map to "European Commission"
        assert (
            extract_author_from_url("https://ec.europa.eu/environment")
            == "European Commission"
        )

        # europarl.europa.eu should map to "European Parliament"
        assert (
            extract_author_from_url("https://europarl.europa.eu/news")
            == "European Parliament"
        )

    def test_unknown_site(self):
        """Test that unknown sites return None."""
        assert (
            extract_author_from_url("https://unknown-site-12345.com/article")
            is None
        )
        assert (
            extract_author_from_url("https://random-blog.example.org/post")
            is None
        )

    def test_industry_sites(self):
        """Test industry-specific site mappings."""
        assert (
            extract_author_from_url("https://hmfoundation.com/about")
            == "H&M Foundation"
        )
        assert (
            extract_author_from_url("https://gs1.eu/standards") == "GS1 Europe"
        )
        assert (
            extract_author_from_url("https://wbcsd.org/sustainability")
            == "World Business Council for Sustainable Development"
        )

    def test_government_sites(self):
        """Test government site mappings."""
        assert (
            extract_author_from_url("https://gov.uk/policy") == "UK Government"
        )
        assert (
            extract_author_from_url("https://epa.gov/environment")
            == "US Environmental Protection Agency"
        )

    def test_news_sites(self):
        """Test news outlet mappings."""
        assert (
            extract_author_from_url("https://theguardian.com/world")
            == "The Guardian"
        )
        assert (
            extract_author_from_url("https://nytimes.com/section/world")
            == "The New York Times"
        )


class TestAugmentMetadataWithSiteAuthor:
    """Tests for augmenting metadata with site-derived authors."""

    def test_augment_missing_author(self):
        """Test adding author when creators field is empty."""
        metadata = {
            "title": "Burberry burns bags",
            "creators": [],
            "date": "2018-07-19",
        }

        result = augment_metadata_with_site_author(
            metadata, "https://www.bbc.com/news/business-44885983"
        )

        assert len(result["creators"]) == 1
        assert result["creators"][0]["lastName"] == "BBC"
        assert result["creators"][0]["creatorType"] == "author"

    def test_augment_no_override_existing_author(self):
        """Test that existing authors are not overridden."""
        metadata = {
            "title": "Some Article",
            "creators": [
                {
                    "creatorType": "author",
                    "lastName": "Smith",
                    "firstName": "John",
                }
            ],
        }

        result = augment_metadata_with_site_author(
            metadata, "https://www.bbc.com/news/article"
        )

        # Should not override existing author
        assert len(result["creators"]) == 1
        assert result["creators"][0]["lastName"] == "Smith"

    def test_augment_unknown_site(self):
        """Test behavior with unknown site (no mapping)."""
        metadata = {"title": "Article Title", "creators": []}

        result = augment_metadata_with_site_author(
            metadata, "https://unknown-site.com/article"
        )

        # Should leave creators empty if no mapping found
        assert result["creators"] == []

    def test_augment_preserves_other_fields(self):
        """Test that other metadata fields are preserved."""
        metadata = {
            "title": "Test Article",
            "creators": [],
            "date": "2023-01-01",
            "itemType": "webpage",
            "url": "https://www.bbc.com/news/test",
        }

        result = augment_metadata_with_site_author(
            metadata, "https://www.bbc.com/news/test"
        )

        # Check that all original fields are preserved
        assert result["title"] == "Test Article"
        assert result["date"] == "2023-01-01"
        assert result["itemType"] == "webpage"
        assert result["url"] == "https://www.bbc.com/news/test"

        # And author was added
        assert len(result["creators"]) == 1
        assert result["creators"][0]["lastName"] == "BBC"


class TestMappingManagement:
    """Tests for mapping management functions."""

    def test_get_known_domains(self):
        """Test getting list of known domains."""
        domains = get_known_domains()

        assert isinstance(domains, list)
        assert len(domains) > 0
        assert "bbc.com" in domains
        assert "bloomberg.com" in domains

        # Should be sorted
        assert domains == sorted(domains)

    def test_add_site_mapping(self):
        """Test adding a new site mapping at runtime."""
        # Count before
        initial_count = len(SITE_AUTHOR_MAPPINGS)

        # Add new mapping
        add_site_mapping("example-test.com", "Example Test Organization")

        # Check it was added
        assert (
            SITE_AUTHOR_MAPPINGS["example-test.com"]
            == "Example Test Organization"
        )
        assert len(SITE_AUTHOR_MAPPINGS) == initial_count + 1

        # Check it works in extraction
        author = extract_author_from_url("https://example-test.com/article")
        assert author == "Example Test Organization"

        # Clean up
        del SITE_AUTHOR_MAPPINGS["example-test.com"]

    def test_add_site_mapping_validation(self):
        """Test that add_site_mapping validates inputs."""
        with pytest.raises(ValueError):
            add_site_mapping("", "Some Author")

        with pytest.raises(ValueError):
            add_site_mapping("domain.com", "")

    def test_add_site_mapping_normalizes_domain(self):
        """Test that domain is normalized (lowercase, trimmed)."""
        add_site_mapping("  EXAMPLE-TEST2.COM  ", "Example Test2")

        assert "example-test2.com" in SITE_AUTHOR_MAPPINGS
        assert SITE_AUTHOR_MAPPINGS["example-test2.com"] == "Example Test2"

        # Clean up
        del SITE_AUTHOR_MAPPINGS["example-test2.com"]


class TestMappingCompleteness:
    """Tests for mapping table quality."""

    def test_no_duplicate_domains(self):
        """Test that mapping table has no duplicate keys."""
        domains = list(SITE_AUTHOR_MAPPINGS.keys())
        assert len(domains) == len(set(domains))

    def test_minimum_coverage(self):
        """Test that mapping table has reasonable coverage."""
        # Should have at least major news outlets and organizations
        required_domains = [
            "bbc.com",
            "bloomberg.com",
            "reuters.com",
            "europa.eu",
        ]

        for domain in required_domains:
            assert domain in SITE_AUTHOR_MAPPINGS, (
                f"Missing required domain: {domain}"
            )

    def test_no_empty_authors(self):
        """Test that all mappings have non-empty author names."""
        for domain, author in SITE_AUTHOR_MAPPINGS.items():
            assert author, f"Empty author for domain: {domain}"
            assert len(author.strip()) > 0, (
                f"Whitespace-only author for domain: {domain}"
            )

    def test_author_name_quality(self):
        """Test that author names are properly formatted."""
        for domain, author in SITE_AUTHOR_MAPPINGS.items():
            # Should not be all lowercase (except acronyms)
            if len(author) > 5:  # Skip short acronyms like "BBC"
                assert not author.islower(), (
                    f"All-lowercase author for {domain}: {author}"
                )

            # Should not have leading/trailing whitespace
            assert author == author.strip(), (
                f"Whitespace in author for {domain}: '{author}'"
            )
