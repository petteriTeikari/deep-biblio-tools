"""Tests for citation extractor."""

from src.citations.extractor import CitationExtractor


class TestCitationExtractor:
    """Test citation extraction from various formats."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = CitationExtractor()

    def test_extract_from_markdown_with_doi_link(self):
        """Test extracting citation with DOI link."""
        text = "This is a great paper by [Smith et al. (2023)](https://doi.org/10.1234/example)."

        citations = self.extractor.extract_from_markdown(text)

        assert len(citations) == 1
        assert citations[0].text == "Smith et al. (2023)"
        assert citations[0].url == "https://doi.org/10.1234/example"
        assert citations[0].doi == "10.1234/example"
        assert citations[0].format == "markdown"

    def test_extract_from_markdown_with_arxiv_link(self):
        """Test extracting citation with arXiv link."""
        text = "Check out this paper: [Neural Networks](https://arxiv.org/abs/2301.12345)"

        citations = self.extractor.extract_from_markdown(text)

        assert len(citations) == 1
        assert citations[0].text == "Neural Networks"
        assert citations[0].url == "https://arxiv.org/abs/2301.12345"
        assert citations[0].arxiv_id == "2301.12345"

    def test_extract_from_markdown_multiple_citations(self):
        """Test extracting multiple citations."""
        text = """Here are two papers:
- [Paper One](https://doi.org/10.1111/test1)
- [Paper Two](https://arxiv.org/abs/2302.54321)

And another [Paper Three](https://pubmed.ncbi.nlm.nih.gov/12345)."""

        citations = self.extractor.extract_from_markdown(text)

        assert len(citations) == 3
        assert citations[0].doi == "10.1111/test1"
        assert citations[1].arxiv_id == "2302.54321"
        assert citations[2].pmid == "12345"

    def test_extract_from_latex_href(self):
        """Test extracting from LaTeX \\href command."""
        text = r"""
        \href{https://doi.org/10.1234/example}{Smith et al., 2023}
        """

        citations = self.extractor.extract_from_latex(text)

        assert len(citations) == 1
        assert citations[0].text == "Smith et al., 2023"
        assert citations[0].url == "https://doi.org/10.1234/example"
        assert citations[0].doi == "10.1234/example"

    def test_extract_from_latex_cite(self):
        """Test extracting from LaTeX \\cite command."""
        text = r"""
        As shown in \cite{smith2023neural}, neural networks are effective.
        """

        citations = self.extractor.extract_from_latex(text)

        assert len(citations) == 1
        assert citations[0].text == "smith2023neural"
        assert citations[0].url is None  # Bibliography key, not URL
        assert citations[0].format == "latex"

    def test_extract_identifiers(self):
        """Test identifier extraction from text."""
        text = "Check doi:10.1234/test and arxiv:2301.12345 and PMID: 98765"

        identifiers = self.extractor.extract_identifiers(text)

        assert identifiers["doi"] == "10.1234/test"
        assert identifiers["arxiv"] == "2301.12345"
        assert identifiers["pmid"] == "98765"

    def test_is_academic_url(self):
        """Test academic URL detection."""
        # Academic URLs
        assert self.extractor._is_academic_url("https://doi.org/10.1234/test")
        assert self.extractor._is_academic_url(
            "https://arxiv.org/abs/1234.5678"
        )
        assert self.extractor._is_academic_url("https://example.edu/paper.pdf")
        assert self.extractor._is_academic_url(
            "https://nature.com/articles/123"
        )

        # Non-academic URLs
        assert not self.extractor._is_academic_url("https://google.com")
        assert not self.extractor._is_academic_url(
            "https://twitter.com/post/123"
        )
        assert not self.extractor._is_academic_url("")
        assert not self.extractor._is_academic_url(None)
