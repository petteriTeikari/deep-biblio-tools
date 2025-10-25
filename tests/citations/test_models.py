"""Tests for citation data models."""

from datetime import datetime

from src.citations.models import (
    AuthorData,
    CitationData,
    DataSource,
    ValidationResult,
)


class TestDataSource:
    """Test DataSource enum."""

    def test_trust_scores(self):
        """Test that trust scores are ordered correctly."""
        assert DataSource.CROSSREF.trust_score == 1.0
        assert DataSource.ARXIV.trust_score == 0.95
        assert DataSource.LLM_OUTPUT.trust_score == 0.1

        # CrossRef should be most trusted
        assert DataSource.CROSSREF.trust_score > DataSource.ZOTERO.trust_score
        assert DataSource.ZOTERO.trust_score > DataSource.LLM_OUTPUT.trust_score


class TestAuthorData:
    """Test AuthorData model."""

    def test_author_creation(self):
        """Test creating author with automatic confidence."""
        author = AuthorData(
            given_name="John", family_name="Smith", source=DataSource.CROSSREF
        )

        assert author.full_name == "John Smith"
        assert author.confidence == 1.0  # From CROSSREF trust score
        assert author.to_bibtex_name() == "Smith, John"

    def test_author_bibtex_formatting(self):
        """Test BibTeX name formatting."""
        # Normal case
        author = AuthorData(given_name="Jane", family_name="Doe")
        assert author.to_bibtex_name() == "Doe, Jane"

        # Only full name
        author = AuthorData(
            given_name="", family_name="", full_name="John Smith"
        )
        assert author.to_bibtex_name() == "John Smith"

        # Missing data
        author = AuthorData(given_name="", family_name="")
        assert author.to_bibtex_name() == "Unknown"


class TestCitationData:
    """Test CitationData model."""

    def test_citation_creation(self):
        """Test creating citation with defaults."""
        citation = CitationData(
            doi="10.1234/example",
            title="Test Paper",
            year=2023,
            source=DataSource.CROSSREF,
        )

        assert citation.confidence == 1.0
        assert citation.get_primary_identifier() == "doi:10.1234/example"
        assert len(citation.validation_log) == 0
        assert len(citation.issues) == 0

    def test_primary_identifier_priority(self):
        """Test identifier priority order."""
        # DOI takes precedence
        citation = CitationData(
            doi="10.1234/example", arxiv_id="2301.12345", pmid="12345"
        )
        assert citation.get_primary_identifier() == "doi:10.1234/example"

        # ArXiv if no DOI
        citation = CitationData(arxiv_id="2301.12345", pmid="12345")
        assert citation.get_primary_identifier() == "arxiv:2301.12345"

        # PMID if no DOI/ArXiv
        citation = CitationData(pmid="12345")
        assert citation.get_primary_identifier() == "pmid:12345"

    def test_validation_tracking(self):
        """Test validation log and issues."""
        citation = CitationData(title="Test")

        # Add validation step
        citation.add_validation_step(
            action="validate_doi",
            source=DataSource.CROSSREF,
            success=True,
            message="DOI validated successfully",
            data={"doi": "10.1234/example"},
        )

        assert len(citation.validation_log) == 1
        assert citation.validation_log[0].action == "validate_doi"
        assert citation.validation_log[0].success is True

        # Add issue
        citation.add_issue(
            field="author",
            severity="warning",
            message="Author name might be incomplete",
            expected="John Smith",
            actual="J. Smith",
        )

        assert len(citation.issues) == 1
        assert citation.issues[0].severity == "warning"

    def test_to_dict_serialization(self):
        """Test dictionary serialization."""
        citation = CitationData(
            doi="10.1234/example",
            title="Test Paper",
            authors=[
                AuthorData(
                    given_name="John",
                    family_name="Smith",
                    source=DataSource.CROSSREF,
                )
            ],
            year=2023,
            source=DataSource.CROSSREF,
        )

        result = citation.to_dict()

        assert result["identifiers"]["doi"] == "10.1234/example"
        assert result["metadata"]["title"] == "Test Paper"
        assert result["metadata"]["year"] == 2023
        assert len(result["metadata"]["authors"]) == 1
        assert result["metadata"]["authors"][0]["given"] == "John"
        assert result["validation"]["source"] == "crossref"
        assert result["validation"]["confidence"] == 1.0


class TestValidationResult:
    """Test ValidationResult model."""

    def test_empty_result(self):
        """Test empty validation result."""
        result = ValidationResult()

        assert result.total_citations == 0
        assert result.success_rate == 0.0
        assert result.duration_seconds is None

    def test_add_citations(self):
        """Test adding citations to result."""
        result = ValidationResult(start_time=datetime.now())

        # Add successful citation
        citation1 = CitationData(
            doi="10.1234/example", source=DataSource.CROSSREF, confidence=1.0
        )
        result.add_citation(citation1)

        # Add citation with issues
        citation2 = CitationData(
            title="Test", source=DataSource.LLM_OUTPUT, confidence=0.1
        )
        citation2.add_issue("author", "error", "Missing authors")
        result.add_citation(citation2)

        assert result.total_citations == 2
        assert result.validated_citations == 1  # Only high confidence
        assert result.citations_with_issues == 1
        assert result.success_rate == 0.5

        # Check source tracking
        assert result.sources_used["crossref"] == 1
        assert result.sources_used["llm"] == 1

        # Check issue tracking
        assert result.issue_types["author"] == 1

    def test_duration_calculation(self):
        """Test duration calculation."""
        start = datetime.now()
        result = ValidationResult(start_time=start)

        # No end time yet
        assert result.duration_seconds is None

        # Set end time
        result.end_time = datetime.now()
        assert result.duration_seconds is not None
        assert result.duration_seconds >= 0
