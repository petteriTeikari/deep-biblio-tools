"""Tests for markdown to LaTeX utility functions."""

from src.converters.md_to_latex.utils import (
    clean_pandoc_output,
    extract_abstract_from_markdown,
    extract_doi_from_url,
    extract_title_from_markdown,
    extract_url_from_link,
    generate_citation_key,
    parse_citation_text,
    sanitize_latex,
)


class TestSanitizeLatex:
    """Test LaTeX sanitization."""

    def test_special_characters(self):
        """Test sanitization of special LaTeX characters."""
        text = "This has $ and & and # and % characters"
        expected = r"This has \$ and \& and \# and \% characters"
        assert sanitize_latex(text) == expected

    def test_braces(self):
        """Test sanitization of braces."""
        text = "Function {foo} with {bar}"
        expected = r"Function \{foo\} with \{bar\}"
        assert sanitize_latex(text) == expected

    def test_underscores(self):
        """Test sanitization of underscores."""
        text = "variable_name and another_var"
        expected = r"variable\_name and another\_var"
        assert sanitize_latex(text) == expected


class TestGenerateCitationKey:
    """Test citation key generation."""

    def test_single_author(self):
        """Test key generation for single author."""
        key = generate_citation_key("Smith", "2023")
        assert key == "smith2023"

    def test_multiple_authors(self):
        """Test key generation for multiple authors."""
        key = generate_citation_key("Smith, Jones, and Brown", "2023")
        assert key == "smith2023"

    def test_et_al(self):
        """Test key generation with et al."""
        # With Better BibTeX as default, without title we get simple key
        key = generate_citation_key("Smith et al.", "2023")
        assert key == "smith2023"


class TestExtractUrlFromLink:
    """Test URL extraction from markdown links."""

    def test_valid_link(self):
        """Test extraction from valid markdown link."""
        link = "[Smith et al. (2023)](https://example.com/paper)"
        url = extract_url_from_link(link)
        assert url == "https://example.com/paper"

    def test_no_link(self):
        """Test extraction when no link present."""
        text = "Just plain text"
        url = extract_url_from_link(text)
        assert url is None


class TestExtractDoiFromUrl:
    """Test DOI extraction from URLs."""

    def test_doi_org_url(self):
        """Test extraction from doi.org URL."""
        url = "https://doi.org/10.1234/example.doi"
        doi = extract_doi_from_url(url)
        assert doi == "10.1234/example.doi"

    def test_doi_in_path(self):
        """Test extraction from URL with DOI in path."""
        url = "https://journal.com/doi/10.1234/example"
        doi = extract_doi_from_url(url)
        assert doi == "10.1234/example"

    def test_no_doi(self):
        """Test extraction when no DOI present."""
        url = "https://example.com/paper"
        doi = extract_doi_from_url(url)
        assert doi is None


class TestParseCitationText:
    """Test citation text parsing."""

    def test_valid_citation(self):
        """Test parsing valid citation format."""
        citation = "[Smith et al. (2023)](https://example.com)"
        authors, year, url = parse_citation_text(citation)
        assert authors == "Smith et al."
        assert year == "2023"
        assert url == "https://example.com"

    def test_invalid_citation(self):
        """Test parsing invalid citation format."""
        citation = "Not a citation"
        authors, year, url = parse_citation_text(citation)
        assert authors is None
        assert year is None
        assert url is None


class TestCleanPandocOutput:
    """Test pandoc output cleaning."""

    def test_remove_tightlist(self):
        """Test removal of tightlist commands."""
        latex = "\\begin{itemize}\\tightlist\n\\item One\n\\end{itemize}"
        cleaned = clean_pandoc_output(latex)
        assert "\\tightlist" not in cleaned

    def test_remove_empty_hypertarget(self):
        """Test removal of empty hypertarget commands."""
        latex = "\\hypertarget{sec:intro}{} Introduction"
        cleaned = clean_pandoc_output(latex)
        assert "\\hypertarget" not in cleaned

    def test_clean_excessive_blank_lines(self):
        """Test cleaning of excessive blank lines."""
        latex = "Line 1\n\n\n\n\nLine 2"
        cleaned = clean_pandoc_output(latex)
        assert cleaned == "Line 1\n\nLine 2"


class TestExtractTitleFromMarkdown:
    """Test title extraction from markdown."""

    def test_h1_title(self):
        """Test extraction of H1 title."""
        content = "# My Research Paper\n\n## Introduction\n\nContent here."
        title = extract_title_from_markdown(content)
        assert title == "My Research Paper"

    def test_no_title(self):
        """Test extraction when no title present."""
        content = "## Introduction\n\nNo H1 title here."
        title = extract_title_from_markdown(content)
        assert title is None


class TestExtractAbstractFromMarkdown:
    """Test abstract extraction from markdown."""

    def test_h2_abstract(self):
        """Test extraction of H2 abstract."""
        content = """# Title

## Abstract

This is the abstract content.
It has multiple lines.

## Introduction

Other content."""
        abstract = extract_abstract_from_markdown(content)
        assert (
            abstract == "This is the abstract content.\nIt has multiple lines."
        )

    def test_bold_abstract(self):
        """Test extraction of bold abstract."""
        content = """# Title

**Abstract**

This is the abstract.

## Introduction"""
        abstract = extract_abstract_from_markdown(content)
        assert abstract == "This is the abstract."

    def test_no_abstract(self):
        """Test extraction when no abstract present."""
        content = "# Title\n\n## Introduction\n\nNo abstract here."
        abstract = extract_abstract_from_markdown(content)
        assert abstract is None
