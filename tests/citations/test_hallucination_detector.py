"""Tests for hallucination detector."""

from src.citations.hallucination_detector import HallucinationDetector
from src.citations.models import (
    AuthorData,
    CitationData,
    DataSource,
    ValidationIssue,
)


class TestHallucinationDetector:
    """Test hallucination detection."""

    def setup_method(self):
        """Set up test fixtures."""
        self.detector = HallucinationDetector()

    def test_detect_et_al_hallucination(self):
        """Test detection of 'et al' when full author list is available."""
        original = {
            "author": "Smith et al",
            "title": "Neural Networks",
            "year": "2023",
        }

        validated = CitationData(
            title="Neural Networks",
            authors=[
                AuthorData(given_name="John", family_name="Smith"),
                AuthorData(given_name="Jane", family_name="Doe"),
                AuthorData(given_name="Bob", family_name="Johnson"),
            ],
            year=2023,
            source=DataSource.CROSSREF,
        )

        issues = self.detector.check_citation(original, validated)

        assert len(issues) > 0
        assert any(
            issue.field == "author" and "et al" in issue.message
            for issue in issues
        )

    def test_detect_wrong_authors(self):
        """Test detection of completely wrong author names."""
        original = {"author": "Bhat et al", "title": "Machine Learning Study"}

        validated = CitationData(
            title="Machine Learning Study",
            authors=[
                AuthorData(given_name="Pierre", family_name="Marsal"),
                AuthorData(given_name="Anna", family_name="Chen"),
            ],
            source=DataSource.ARXIV,
        )

        issues = self.detector.check_citation(original, validated)

        assert len(issues) > 0
        author_issues = [i for i in issues if i.field == "author"]
        assert any(
            "hallucinated" in issue.message.lower() for issue in author_issues
        )

    def test_detect_wrong_year(self):
        """Test detection of wrong publication year."""
        original = {
            "author": "Smith, J.",
            "title": "Test Paper",
            "year": "2021",
        }

        validated = CitationData(
            title="Test Paper",
            authors=[AuthorData(given_name="John", family_name="Smith")],
            year=2023,
            source=DataSource.CROSSREF,
        )

        issues = self.detector.check_citation(original, validated)

        year_issues = [i for i in issues if i.field == "year"]
        assert len(year_issues) > 0
        assert year_issues[0].expected == "2023"
        assert year_issues[0].actual == "2021"

    def test_standalone_suspicious_patterns(self):
        """Test detection of suspicious patterns without validation."""
        citations = [
            {"author": "Author et al"},
            {"author": "TODO"},
            {"author": "Unknown"},
            {"title": "Title"},
            {"title": "[PLACEHOLDER]"},
            {"journal": "Journal"},
            {"journal": "International Conference"},
        ]

        for citation in citations:
            issues = self.detector._check_standalone_issues(citation)
            assert len(issues) > 0

    def test_common_hallucinated_authors(self):
        """Test detection of common hallucinated author patterns."""
        original = {"author": "Kumar et al"}

        issues = self.detector._check_standalone_issues(original)

        assert any(
            issue.field == "author" and "hallucinated" in issue.message
            for issue in issues
        )

    def test_hallucination_score_calculation(self):
        """Test hallucination score calculation."""
        # No issues
        assert self.detector.get_hallucination_score([]) == 0.0

        # One warning
        issues = [
            ValidationIssue(
                field="author", severity="warning", message="Test warning"
            )
        ]
        score = self.detector.get_hallucination_score(issues)
        assert 0 < score < 0.5

        # Multiple errors
        issues = [
            ValidationIssue(field="author", severity="error", message="Test"),
            ValidationIssue(field="title", severity="error", message="Test"),
            ValidationIssue(field="year", severity="error", message="Test"),
        ]
        score = self.detector.get_hallucination_score(issues)
        assert score > 0.2

    def test_text_normalization(self):
        """Test text normalization for comparison."""
        cases = [
            ("Hello, World!", "hello world"),
            ("The   Quick   Brown   Fox", "the quick brown fox"),
            (
                "Test-Case_Example",
                "test case_example",
            ),  # underscore is part of \w
            ("", ""),
        ]

        for input_text, expected in cases:
            assert self.detector._normalize_text(input_text) == expected
