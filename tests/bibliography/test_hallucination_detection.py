"""Tests for LLM hallucination detection in bibliographies."""

import pytest
from src.bibliography import (
    Bibliography,
    BibliographyEntry,
    LLMCitationValidator,
)


class TestHallucinationDetection:
    """Test detection of common LLM hallucinations in citations."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return LLMCitationValidator()

    def test_detect_et_al_abuse(self, validator):
        """Test detection of 'et al.' used to hide hallucinated authors."""
        bib = Bibliography()

        # Entry with et al. in author field (common LLM hallucination)
        entry = BibliographyEntry(
            "article",
            "suspicious2023",
            {
                "author": "Smith, John et al.",
                "title": "Some Paper",
                "year": "2023",
            },
        )
        bib.add_entry(entry)

        issues = validator.process(bib)
        assert len(issues) > 0
        assert any("et al." in issue for issue in issues)

    def test_detect_generic_titles(self, validator):
        """Test detection of generic/placeholder titles."""
        bib = Bibliography()

        generic_titles = [
            "A Study of Machine Learning",
            "Research on Neural Networks",
            "Investigation of Deep Learning",
            "Analysis of Artificial Intelligence",
            "Overview of Computer Vision",
        ]

        for i, title in enumerate(generic_titles):
            entry = BibliographyEntry(
                "article",
                f"generic{i}",
                {"author": "Author, Generic", "title": title, "year": "2023"},
            )
            bib.add_entry(entry)

        issues = validator.process(bib)
        assert len(issues) >= len(generic_titles)

    def test_detect_suspicious_page_numbers(self, validator):
        """Test detection of suspicious page numbers."""
        bib = Bibliography()

        suspicious_pages = [
            "1-1000",  # Too many pages
            "12345-12346",  # Suspiciously high
            "1-2",  # Too few for a full paper
            "123-122",  # End before start
        ]

        for i, pages in enumerate(suspicious_pages):
            entry = BibliographyEntry(
                "article",
                f"pages{i}",
                {
                    "author": "Author, Test",
                    "title": "Test Paper",
                    "year": "2023",
                    "pages": pages,
                },
            )
            bib.add_entry(entry)

        issues = validator.process(bib)
        assert len(issues) >= len(suspicious_pages)

    def test_detect_future_years(self, validator):
        """Test detection of papers from too far in the future."""
        bib = Bibliography()

        import datetime

        current_year = datetime.datetime.now().year

        # Entry from far future
        entry = BibliographyEntry(
            "article",
            "future",
            {
                "author": "Future, Author",
                "title": "Future Paper",
                "year": str(current_year + 5),  # Too far in future
            },
        )
        bib.add_entry(entry)

        issues = validator.process(bib)
        assert len(issues) > 0
        assert any("future" in issue.lower() for issue in issues)

    def test_detect_generic_conference_names(self, validator):
        """Test detection of generic conference names."""
        bib = Bibliography()

        generic_conferences = [
            "International Conference on Machine Learning",
            "Conference on Artificial Intelligence",
            "Symposium on Neural Networks",
            "Workshop on Deep Learning",
        ]

        for i, conf in enumerate(generic_conferences):
            entry = BibliographyEntry(
                "inproceedings",
                f"conf{i}",
                {
                    "author": "Author, Conference",
                    "title": "Conference Paper",
                    "booktitle": conf,
                    "year": "2023",
                },
            )
            bib.add_entry(entry)

        issues = validator.process(bib)
        assert len(issues) > 0

    def test_detect_generic_journal_names(self, validator):
        """Test detection of generic journal names."""
        bib = Bibliography()

        generic_journals = [
            "Journal of Machine Learning",
            "International Journal of AI",
            "Transactions on Neural Networks",
            "Journal of Computer Science",
        ]

        for i, journal in enumerate(generic_journals):
            entry = BibliographyEntry(
                "article",
                f"journal{i}",
                {
                    "author": "Author, Journal",
                    "title": "Journal Paper",
                    "journal": journal,
                    "year": "2023",
                },
            )
            bib.add_entry(entry)

        issues = validator.process(bib)
        assert len(issues) > 0

    def test_detect_repetitive_author_patterns(self, validator):
        """Test detection of repetitive author name patterns."""
        bib = Bibliography()

        # Multiple papers by suspiciously similar authors
        similar_authors = [
            "Smith, John A.",
            "Smith, John B.",
            "Smith, John C.",
            "Smith, John D.",
        ]

        for i, author in enumerate(similar_authors):
            entry = BibliographyEntry(
                "article",
                f"smith{i}",
                {"author": author, "title": f"Paper {i}", "year": "2023"},
            )
            bib.add_entry(entry)

        issues = validator.process(bib)
        # Should detect the suspicious pattern
        assert len(issues) > 0

    def test_detect_missing_critical_fields(self, validator):
        """Test detection of entries missing critical fields for verification."""
        bib = Bibliography()

        # Entry with no DOI, URL, or other identifiers
        entry = BibliographyEntry(
            "article",
            "unverifiable",
            {
                "author": "Mystery, Author",
                "title": "Unverifiable Paper",
                "journal": "Unknown Journal",
                "year": "2023",
                # No DOI, URL, arXiv ID, etc.
            },
        )
        bib.add_entry(entry)

        issues = validator.process(bib)
        assert len(issues) > 0
        assert any(
            "identifier" in issue.lower() or "verify" in issue.lower()
            for issue in issues
        )

    def test_detect_inconsistent_publication_info(self, validator):
        """Test detection of inconsistent publication information."""
        bib = Bibliography()

        # Conference paper with journal field (inconsistent)
        entry1 = BibliographyEntry(
            "inproceedings",
            "inconsistent1",
            {
                "author": "Author, Test",
                "title": "Conference Paper",
                "booktitle": "ICML 2023",
                "journal": "Nature",  # Should not have journal
                "year": "2023",
            },
        )

        # Article with booktitle (inconsistent)
        entry2 = BibliographyEntry(
            "article",
            "inconsistent2",
            {
                "author": "Author, Test",
                "title": "Journal Article",
                "journal": "Nature",
                "booktitle": "NeurIPS 2023",  # Should not have booktitle
                "year": "2023",
            },
        )

        bib.add_entry(entry1)
        bib.add_entry(entry2)

        issues = validator.process(bib)
        assert len(issues) >= 2

    def test_detect_common_llm_artifacts(self, validator):
        """Test detection of common LLM response artifacts."""
        bib = Bibliography()

        # Entry with markdown formatting in fields
        entry = BibliographyEntry(
            "article",
            "markdown",
            {
                "author": "**Smith, John**",  # Markdown bold
                "title": "[Important Paper](http://example.com)",  # Markdown link
                "journal": "_Nature_",  # Markdown italic
                "year": "2023",
            },
        )
        bib.add_entry(entry)

        issues = validator.process(bib)
        assert len(issues) > 0

    def test_valid_entries_pass(self):
        """Test that valid entries don't trigger false positives."""
        # Use validator without URL checking for this test since we use fake URLs
        validator = LLMCitationValidator(check_urls=False)
        bib = Bibliography()

        # Well-formed entry with all expected fields
        entry = BibliographyEntry(
            "article",
            "mildenberger2023neurips",
            {
                "author": "Mildenberger, Thorsten and Smith, John and Doe, Jane",
                "title": "NeRFs: A Comprehensive Study of Neural Radiance Fields",
                "journal": "Advances in Neural Information Processing Systems",
                "volume": "36",
                "pages": "12345--12367",
                "year": "2023",
                "doi": "10.5555/3495724.3496371",
                "url": "https://proceedings.neurips.cc/paper/2023/hash/...",
            },
        )
        bib.add_entry(entry)

        issues = validator.process(bib)
        # Valid entry should have no issues
        assert len(issues) == 0

    def test_detect_duplicated_citations(self, validator):
        """Test detection of duplicated citations with slight variations."""
        bib = Bibliography()

        # Same paper cited twice with slight variations
        entry1 = BibliographyEntry(
            "article",
            "smith2023a",
            {
                "author": "Smith, John and Doe, Jane",
                "title": "Deep Learning for Computer Vision",
                "journal": "CVPR",
                "year": "2023",
            },
        )

        entry2 = BibliographyEntry(
            "inproceedings",  # Different type
            "smith2023b",
            {
                "author": "Smith, J. and Doe, J.",  # Abbreviated
                "title": "Deep Learning for Computer Vision",  # Same title
                "booktitle": "CVPR 2023",  # Similar venue
                "year": "2023",
            },
        )

        bib.add_entry(entry1)
        bib.add_entry(entry2)

        issues = validator.process(bib)
        assert len(issues) > 0
        assert any("duplicate" in issue.lower() for issue in issues)
