"""Tests for the main markdown to LaTeX converter."""

from pathlib import Path
from unittest.mock import patch

import pytest
from src.converters.md_to_latex import MarkdownToLatexConverter
from src.converters.md_to_latex.concept_boxes import (
    ConceptBoxStyle,
)


class TestMarkdownToLatexConverter:
    """Test MarkdownToLatexConverter class."""

    @pytest.fixture
    def temp_output_dir(self, tmp_path):
        """Create temporary output directory."""
        output_dir = tmp_path / "latex_output"
        output_dir.mkdir()
        return output_dir

    @pytest.fixture
    def sample_markdown_file(self, tmp_path):
        """Create a sample markdown file for testing."""
        md_file = tmp_path / "test_document.md"
        content = """# Test Document

## Abstract

This is the abstract of the test document.

## Introduction

This document contains [Smith et al. (2023)](https://doi.org/10.1234/example) citation.

*Technical Concept Box: Important Concept*

This is an important concept that needs highlighting.

## Conclusion

The end.
"""
        md_file.write_text(content)
        return md_file

    def test_converter_initialization(self, temp_output_dir):
        """Test converter initialization."""
        converter = MarkdownToLatexConverter(
            output_dir=temp_output_dir,
            concept_box_style=ConceptBoxStyle.MODERN_GRADIENT,
            arxiv_ready=True,
        )
        assert converter.output_dir == temp_output_dir
        assert converter.concept_box_style == ConceptBoxStyle.MODERN_GRADIENT
        assert converter.arxiv_ready is True

    def test_converter_default_initialization(self):
        """Test converter with default parameters."""
        converter = MarkdownToLatexConverter()
        assert (
            converter.output_dir is None
        )  # Default is None, gets set during conversion
        assert converter.concept_box_style == ConceptBoxStyle.PROFESSIONAL_BLUE
        assert converter.arxiv_ready is True

    @patch("pypandoc.convert_text")
    def test_convert_basic(
        self, mock_pandoc, sample_markdown_file, temp_output_dir
    ):
        """Test basic conversion process."""
        # Mock pandoc conversion
        mock_pandoc.return_value = "\\section{Introduction}\nConverted content."

        converter = MarkdownToLatexConverter(output_dir=temp_output_dir)
        output_file = converter.convert(
            markdown_file=sample_markdown_file,
            author="Test Author",
            verbose=False,
        )

        # Check output file exists
        assert output_file.exists()
        assert output_file.suffix == ".tex"

        # Check other files created
        assert (temp_output_dir / "references.bib").exists()
        assert (temp_output_dir / "Makefile").exists()
        assert (temp_output_dir / "README.md").exists()

        # Check LaTeX content
        latex_content = output_file.read_text()
        assert "\\documentclass" in latex_content
        assert "\\title{Test Document}" in latex_content
        assert "\\author{Test Author}" in latex_content
        assert "\\begin{document}" in latex_content
        assert "\\end{document}" in latex_content

    def test_convert_nonexistent_file(self, temp_output_dir):
        """Test conversion with nonexistent file."""
        converter = MarkdownToLatexConverter(output_dir=temp_output_dir)

        with pytest.raises(FileNotFoundError):
            converter.convert(Path("nonexistent.md"))

    @patch("pypandoc.convert_text")
    def test_convert_with_custom_output_name(
        self, mock_pandoc, sample_markdown_file, temp_output_dir
    ):
        """Test conversion with custom output name."""
        mock_pandoc.return_value = "Content"

        converter = MarkdownToLatexConverter(output_dir=temp_output_dir)
        output_file = converter.convert(
            markdown_file=sample_markdown_file,
            output_name="custom_name",
            verbose=False,
        )

        assert output_file.name == "custom_name.tex"

    @patch("pypandoc.convert_text")
    def test_citation_extraction(
        self, mock_pandoc, sample_markdown_file, temp_output_dir
    ):
        """Test that citations are properly extracted."""
        mock_pandoc.return_value = "Content with \\cite{smith2023}"

        converter = MarkdownToLatexConverter(output_dir=temp_output_dir)
        converter.convert(sample_markdown_file, verbose=False)

        # Check BibTeX file
        bib_file = temp_output_dir / "references.bib"
        bib_content = bib_file.read_text()
        assert (
            "@misc{smith2023," in bib_content
            or "@article{smith2023," in bib_content
        )
        assert (
            'author = "Smith and others",' in bib_content
        )  # Note: mistletoe removes the period

    @patch("pypandoc.convert_text")
    def test_concept_box_conversion(
        self, mock_pandoc, sample_markdown_file, temp_output_dir
    ):
        """Test that concept boxes are converted."""
        mock_pandoc.return_value = "Content"

        converter = MarkdownToLatexConverter(output_dir=temp_output_dir)
        output_file = converter.convert(sample_markdown_file, verbose=False)

        latex_content = output_file.read_text()
        # Should have tcolorbox package
        assert (
            "\\usepackage{tcolorbox}" in latex_content
            or "\\usepackage[most]{tcolorbox}" in latex_content
        )

    def test_set_concept_box_style(self):
        """Test changing concept box style."""
        converter = MarkdownToLatexConverter()
        converter.set_concept_box_style(ConceptBoxStyle.TECHNICAL_DARK)
        assert converter.concept_box_style == ConceptBoxStyle.TECHNICAL_DARK
        assert (
            converter.concept_box_converter.default_style
            == ConceptBoxStyle.TECHNICAL_DARK
        )

    def test_get_available_styles(self):
        """Test getting available styles."""
        converter = MarkdownToLatexConverter()
        styles = converter.get_available_styles()
        assert "professional_blue" in styles
        assert "modern_gradient" in styles
        assert "technical_dark" in styles
        assert len(styles) == 5

    @patch("pypandoc.convert_text")
    def test_verbose_mode(
        self, mock_pandoc, sample_markdown_file, temp_output_dir, capsys
    ):
        """Test verbose mode output."""
        mock_pandoc.return_value = "Content"

        converter = MarkdownToLatexConverter(output_dir=temp_output_dir)
        converter.convert(sample_markdown_file, verbose=True)

        captured = capsys.readouterr()
        assert "CONVERSION SUMMARY" in captured.out
        assert "Citations extracted:" in captured.out
        assert "Concept boxes found:" in captured.out

    @patch("pypandoc.convert_text", side_effect=Exception("Pandoc error"))
    def test_pandoc_failure(
        self, mock_pandoc, sample_markdown_file, temp_output_dir
    ):
        """Test handling of pandoc conversion failure."""
        converter = MarkdownToLatexConverter(output_dir=temp_output_dir)

        with pytest.raises(Exception) as exc_info:
            converter.convert(sample_markdown_file, verbose=False)
        assert "Pandoc error" in str(exc_info.value)
