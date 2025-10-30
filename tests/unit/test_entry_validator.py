"""Unit tests for EntryValidator - preventing garbage entries.

These tests verify that the validator catches the same issues that
caused the October 26 garbage entry incident.
"""

import pytest
from src.converters.md_to_latex.entry_validator import EntryValidator


@pytest.fixture
def validator():
    """Create EntryValidator instance for testing."""
    return EntryValidator()


class TestValidateTitle:
    """Tests for title validation (most critical for preventing garbage)."""

    def test_valid_title(self, validator):
        """Test that a normal title passes validation."""
        metadata = {
            "title": "Burberry burns bags, clothes and perfume worth millions",
            "creators": [{"lastName": "BBC"}],
            "date": "2018",
        }
        is_valid, issues = validator.validate(metadata)

        assert is_valid
        # May have warnings but no CRITICAL issues
        critical = [i for i in issues if "CRITICAL" in i]
        assert len(critical) == 0

    def test_missing_title(self, validator):
        """Test that missing title is CRITICAL."""
        metadata = {"creators": [], "date": "2023"}
        is_valid, issues = validator.validate(metadata)

        assert not is_valid
        assert any("CRITICAL" in i and "missing" in i.lower() for i in issues)

    def test_truncated_title_added_from_url(self, validator):
        """Test October 26 pattern: 'Added from URL:' - MUST BLOCK!"""
        metadata = {
            "title": "Added from URL: https://cris.vtt.fi/en/publications/implemen...",
            "creators": [],
            "date": "",
        }
        is_valid, issues = validator.validate(metadata)

        assert not is_valid, "Should BLOCK 'Added from URL' pattern"
        assert any("CRITICAL" in i and "Added from URL" in i for i in issues), (
            f"Should detect 'Added from URL' marker. Issues: {issues}"
        )

    def test_truncated_title_implementation_plan(self, validator):
        """Test October 26 pattern: 'Implementation plan' garbage - MUST BLOCK!"""
        metadata = {
            "title": "Implementation plan for fashion industry DPP",
            "creators": [],
            "date": "2024",
        }
        is_valid, issues = validator.validate(metadata)

        assert not is_valid, "Should BLOCK 'Implementation plan' pattern"
        assert any(
            "CRITICAL" in i and "Implementation plan" in i for i in issues
        )

    def test_truncated_title_ellipsis(self, validator):
        """Test that ellipsis in title is flagged as truncation."""
        metadata = {
            "title": "Some article title that was truncated...",
            "creators": [{"lastName": "Author"}],
            "date": "2023",
        }
        is_valid, issues = validator.validate(metadata)

        assert not is_valid
        assert any("CRITICAL" in i and "..." in i for i in issues)

    def test_suspiciously_short_title(self, validator):
        """Test that very short titles are blocked."""
        metadata = {
            "title": "Fashion",
            "creators": [{"lastName": "Someone"}],
            "date": "2023",
        }
        is_valid, issues = validator.validate(metadata)

        assert not is_valid
        assert any("CRITICAL" in i and "short" in i.lower() for i in issues)

    def test_all_uppercase_title_warning(self, validator):
        """Test that all-caps titles get WARNING (poor metadata quality)."""
        metadata = {
            "title": "THIS IS ALL UPPERCASE AND LOOKS LIKE POOR METADATA",
            "creators": [{"lastName": "Author"}],
            "date": "2023",
        }
        is_valid, issues = validator.validate(metadata)

        # Should pass but with warning
        assert is_valid
        assert any("WARNING" in i and "uppercase" in i.lower() for i in issues)

    def test_stub_title_web_page_by(self, validator):
        """Test that 'Web page by X' stub titles are BLOCKED."""
        metadata = {
            "title": "Web page by Axios",
            "creators": [{"lastName": "Axios"}],
            "date": "2025",
        }
        is_valid, issues = validator.validate(metadata)

        assert not is_valid, "Should BLOCK 'Web page by' stub title"
        assert any(
            "CRITICAL" in i and "stub title" in i.lower() for i in issues
        ), f"Should detect stub title. Issues: {issues}"

    def test_stub_title_webpage_by(self, validator):
        """Test that 'Webpage by X' variant is also BLOCKED."""
        metadata = {
            "title": "Webpage by European Parliament",
            "creators": [{"lastName": "European Parliament"}],
            "date": "2024",
        }
        is_valid, issues = validator.validate(metadata)

        assert not is_valid
        assert any("CRITICAL" in i and "stub" in i.lower() for i in issues)

    def test_domain_as_title_amazon_de(self, validator):
        """Test that 'Amazon.de' as title is BLOCKED."""
        metadata = {
            "title": "Amazon.de",
            "creators": [{"lastName": "Fletcher"}],
            "date": "2016",
        }
        is_valid, issues = validator.validate(metadata)

        assert not is_valid, "Should BLOCK domain name as title"
        assert any("CRITICAL" in i and "domain" in i.lower() for i in issues), (
            f"Should detect domain as title. Issues: {issues}"
        )

    def test_domain_extension_as_title_ending(self, validator):
        """Test that titles ending with .com/.org are BLOCKED."""
        metadata = {
            "title": "example.com",
            "creators": [{"lastName": "Someone"}],
            "date": "2024",
        }
        is_valid, issues = validator.validate(metadata)

        assert not is_valid
        assert any("CRITICAL" in i and "domain" in i.lower() for i in issues)

    def test_bbc_com_as_title(self, validator):
        """Test that BBC.com as exact title is BLOCKED."""
        metadata = {
            "title": "BBC.com",
            "creators": [{"lastName": "BBC"}],
            "date": "2023",
        }
        is_valid, issues = validator.validate(metadata)

        assert not is_valid
        assert any("CRITICAL" in i and "domain" in i.lower() for i in issues)


class TestValidateCreators:
    """Tests for creator/author validation."""

    def test_missing_creators_warning(self, validator):
        """Test that missing creators generates WARNING (not blocking)."""
        metadata = {
            "title": "Some Valid Article Title Here",
            "creators": [],
            "date": "2023",
        }
        is_valid, issues = validator.validate(metadata)

        # Should pass with warning (can be augmented with site author)
        assert is_valid
        assert any(
            "WARNING" in i and ("author" in i.lower() or "creator" in i.lower())
            for i in issues
        )

    def test_valid_creators(self, validator):
        """Test that proper creators pass validation."""
        metadata = {
            "title": "Article Title",
            "creators": [
                {
                    "creatorType": "author",
                    "lastName": "Smith",
                    "firstName": "John",
                },
                {
                    "creatorType": "author",
                    "lastName": "Doe",
                    "firstName": "Jane",
                },
            ],
            "date": "2023",
        }
        is_valid, issues = validator.validate(metadata)

        assert is_valid
        # No creator-related warnings
        creator_issues = [
            i for i in issues if "creator" in i.lower() or "author" in i.lower()
        ]
        assert len(creator_issues) == 0

    def test_creator_missing_lastname(self, validator):
        """Test that creators without lastName get WARNING."""
        metadata = {
            "title": "Article Title",
            "creators": [
                {
                    "creatorType": "author",
                    "firstName": "John",
                }  # Missing lastName
            ],
            "date": "2023",
        }
        is_valid, issues = validator.validate(metadata)

        assert is_valid  # Not blocking, but warns
        assert any("WARNING" in i and "lastName" in i for i in issues)

    def test_creator_suspiciously_short_name(self, validator):
        """Test that single-letter names get WARNING."""
        metadata = {
            "title": "Article Title",
            "creators": [{"creatorType": "author", "lastName": "X"}],
            "date": "2023",
        }
        is_valid, issues = validator.validate(metadata)

        assert is_valid
        assert any("WARNING" in i and "short" in i.lower() for i in issues)


class TestValidateDate:
    """Tests for date/year validation."""

    def test_valid_year(self, validator):
        """Test that valid year passes."""
        metadata = {
            "title": "Article Title",
            "creators": [{"lastName": "Author"}],
            "date": "2023-05-15",
        }
        is_valid, issues = validator.validate(metadata)

        assert is_valid
        # No date-related warnings
        date_issues = [
            i for i in issues if "year" in i.lower() or "date" in i.lower()
        ]
        assert len(date_issues) == 0

    def test_missing_date(self, validator):
        """Test that missing date generates WARNING."""
        metadata = {
            "title": "Article Title",
            "creators": [{"lastName": "Author"}],
            "date": "",
        }
        is_valid, issues = validator.validate(metadata)

        assert is_valid  # Not blocking
        assert any("WARNING" in i and "date" in i.lower() for i in issues)

    def test_year_outside_range(self, validator):
        """Test that unrealistic years generate WARNING."""
        metadata = {
            "title": "Article Title",
            "creators": [{"lastName": "Author"}],
            "date": "1850",  # Too old
        }
        is_valid, issues = validator.validate(metadata)

        assert is_valid
        assert any("WARNING" in i and "1850" in str(i) for i in issues)

        # Test future year
        metadata["date"] = "2050"
        is_valid, issues = validator.validate(metadata)
        assert is_valid
        assert any("WARNING" in i and "2050" in str(i) for i in issues)

    def test_extract_year_various_formats(self, validator):
        """Test year extraction from various date formats."""
        test_cases = [
            ("2023-05-15", 2023),
            ("May 15, 2023", 2023),
            ("15/05/2023", 2023),
            ("2023", 2023),
            ("Published in 2022", 2022),
            ("No year here", None),
            ("", None),
        ]

        for date_str, expected_year in test_cases:
            year = validator._extract_year(date_str)
            assert year == expected_year, (
                f"Failed for '{date_str}': expected {expected_year}, got {year}"
            )


class TestValidateDOI:
    """Tests for DOI format validation."""

    def test_valid_doi_format(self, validator):
        """Test that valid DOI format passes."""
        metadata = {
            "title": "Article Title",
            "creators": [{"lastName": "Author"}],
            "date": "2023",
            "DOI": "10.1234/example.2023.0001",
        }
        is_valid, issues = validator.validate(metadata)

        assert is_valid
        # No DOI-related warnings
        doi_issues = [i for i in issues if "DOI" in i or "doi" in i.lower()]
        assert len(doi_issues) == 0

    def test_invalid_doi_format(self, validator):
        """Test that invalid DOI format generates WARNING."""
        metadata = {
            "title": "Article Title",
            "creators": [{"lastName": "Author"}],
            "date": "2023",
            "DOI": "invalid-doi-format",  # Should start with "10."
        }
        is_valid, issues = validator.validate(metadata)

        assert is_valid  # Not blocking
        assert any("WARNING" in i and "DOI" in i for i in issues)

    def test_suspiciously_short_doi(self, validator):
        """Test that very short DOIs generate WARNING."""
        metadata = {
            "title": "Article Title",
            "creators": [{"lastName": "Author"}],
            "date": "2023",
            "DOI": "10.1/x",  # Technically valid but suspiciously short
        }
        is_valid, issues = validator.validate(metadata)

        assert is_valid
        assert any("WARNING" in i and "short" in i.lower() for i in issues)


class TestItemTypeSpecificValidation:
    """Tests for item-type specific validation rules."""

    def test_webpage_without_author_warning(self, validator):
        """Test that webpage without author generates WARNING."""
        metadata = {
            "title": "Web Page Title",
            "creators": [],
            "date": "2023",
            "itemType": "webpage",
        }
        is_valid, issues = validator.validate(metadata)

        assert is_valid
        assert any(
            "WARNING" in i and "webpage" in i.lower() and "author" in i.lower()
            for i in issues
        )

    def test_webpage_without_access_date(self, validator):
        """Test that webpage without accessDate generates WARNING."""
        metadata = {
            "title": "Web Page Title",
            "creators": [{"lastName": "BBC"}],
            "date": "2023",
            "itemType": "webpage",
            "accessDate": "",
        }
        is_valid, issues = validator.validate(metadata)

        assert is_valid
        assert any("WARNING" in i and "accessDate" in i for i in issues)

    def test_journal_article_without_publication(self, validator):
        """Test that journal article without publication generates WARNING."""
        metadata = {
            "title": "Article Title",
            "creators": [{"lastName": "Smith"}],
            "date": "2023",
            "itemType": "journalArticle",
            "publicationTitle": "",
        }
        is_valid, issues = validator.validate(metadata)

        assert is_valid
        assert any(
            "WARNING" in i and "publication" in i.lower() for i in issues
        )

    def test_journal_article_without_doi(self, validator):
        """Test that journal article without DOI generates WARNING."""
        metadata = {
            "title": "Article Title",
            "creators": [{"lastName": "Smith"}],
            "date": "2023",
            "itemType": "journalArticle",
            "publicationTitle": "Journal Name",
        }
        is_valid, issues = validator.validate(metadata)

        assert is_valid
        assert any("WARNING" in i and "DOI" in i for i in issues)

    def test_conference_paper_without_proceedings(self, validator):
        """Test that conference paper without proceedings generates WARNING."""
        metadata = {
            "title": "Paper Title",
            "creators": [{"lastName": "Author"}],
            "date": "2023",
            "itemType": "conferencePaper",
            "proceedingsTitle": "",
        }
        is_valid, issues = validator.validate(metadata)

        assert is_valid
        assert any(
            "WARNING" in i and "proceedings" in i.lower() for i in issues
        )


class TestRealWorldGarbageExamples:
    """Tests based on actual garbage entries from October 26 incident."""

    def test_october_26_cris_garbage(self, validator):
        """Test actual garbage entry from CRIS system (October 26)."""
        # This is an ACTUAL garbage entry that was added
        metadata = {
            "title": "Implementation plan for fashion industry DPP",
            "creators": [],
            "date": "",
            "itemType": "document",
        }
        is_valid, issues = validator.validate(metadata)

        # MUST be blocked!
        assert not is_valid, "FAILED: Should block October 26 CRIS garbage"
        critical = [i for i in issues if "CRITICAL" in i]
        assert len(critical) > 0, "Should have CRITICAL issues"

    def test_october_26_truncated_url_title(self, validator):
        """Test another October 26 pattern."""
        metadata = {
            "title": "Added from URL: https://cris.vtt.fi/en/publications/implemen",
            "creators": [],
            "date": "",
        }
        is_valid, issues = validator.validate(metadata)

        assert not is_valid
        assert any("Added from URL" in i for i in issues)

    def test_good_bbc_entry(self, validator):
        """Test that a GOOD entry (like BBC article) passes."""
        metadata = {
            "title": "Burberry burns bags, clothes and perfume worth millions",
            "creators": [{"creatorType": "author", "lastName": "BBC"}],
            "date": "2018-07-19",
            "itemType": "webpage",
            "url": "https://www.bbc.com/news/business-44885983",
        }
        is_valid, issues = validator.validate(metadata)

        assert is_valid, "Good BBC entry should pass"
        # May have warnings but no CRITICAL
        critical = [i for i in issues if "CRITICAL" in i]
        assert len(critical) == 0


class TestValidatorConfiguration:
    """Tests for validator configuration and customization."""

    def test_truncation_markers_list(self, validator):
        """Test that all truncation markers are checked."""
        assert len(validator.truncation_markers) > 0
        assert "Added from URL:" in validator.truncation_markers
        assert "Implementation plan" in validator.truncation_markers

    def test_year_range(self, validator):
        """Test year range configuration."""
        assert validator.min_year == 1900
        assert validator.max_year == 2030

    def test_min_title_length(self, validator):
        """Test minimum title length."""
        assert validator.min_title_length > 0
        assert validator.min_title_length == 10
