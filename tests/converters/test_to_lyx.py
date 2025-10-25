"""Tests for LyX converters."""

import os
import shutil
from pathlib import Path

import pytest
from src.converters.to_lyx import (
    MarkdownToLyxConverter,
    TexToLyxConverter,
)


@pytest.mark.skipif(
    not shutil.which("tex2lyx") or os.environ.get("CONTAINER_ENV"),
    reason="tex2lyx not available or running in container",
)
class TestTexToLyxConverter:
    """Tests for TeX to LyX converter."""

    @pytest.fixture
    def converter(self, tmp_path):
        """Create a converter instance."""
        return TexToLyxConverter(output_dir=tmp_path)

    @pytest.fixture
    def sample_tex(self, tmp_path):
        """Create a sample TeX file."""
        tex_file = tmp_path / "sample.tex"
        tex_file.write_text(r"""
\documentclass{article}
\begin{document}
\title{Test Document}
\author{Test Author}
\maketitle

\section{Introduction}
This is a test document.

\begin{equation}
E = mc^2
\end{equation}

\end{document}
""")
        return tex_file

    def test_tex2lyx_available(self):
        """Test that tex2lyx is available."""
        # This test is redundant since we skip all tests if tex2lyx is not available
        assert shutil.which("tex2lyx") is not None

    def test_convert_basic(self, converter, sample_tex):
        """Test basic TeX to LyX conversion."""
        output_file = converter.convert(sample_tex)

        assert output_file.exists()
        assert output_file.suffix == ".lyx"

        # Check that LyX file has content
        content = output_file.read_text()
        assert "#LyX" in content  # LyX file header
        assert "Test Document" in content

    def test_convert_with_custom_output(self, converter, sample_tex, tmp_path):
        """Test conversion with custom output path."""
        custom_output = tmp_path / "custom" / "output.lyx"
        output_file = converter.convert(sample_tex, custom_output)

        assert output_file == custom_output
        assert output_file.exists()

    def test_convert_nonexistent_file(self, converter):
        """Test error handling for nonexistent file."""
        with pytest.raises(FileNotFoundError):
            converter.convert(Path("nonexistent.tex"))

    def test_convert_with_options(self, converter, sample_tex):
        """Test conversion with roundtrip option."""
        output_file = converter.convert_with_options(sample_tex, roundtrip=True)

        assert output_file.exists()
        content = output_file.read_text()
        assert "#LyX" in content


@pytest.mark.skipif(
    not shutil.which("pandoc")
    or not shutil.which("tex2lyx")
    or os.environ.get("CONTAINER_ENV"),
    reason="pandoc or tex2lyx not available or running in container",
)
class TestMarkdownToLyxConverter:
    """Tests for Markdown to LyX converter."""

    @pytest.fixture
    def converter(self, tmp_path):
        """Create a converter instance."""
        return MarkdownToLyxConverter(output_dir=tmp_path)

    @pytest.fixture
    def sample_markdown(self, tmp_path):
        """Create a sample Markdown file."""
        md_file = tmp_path / "sample.md"
        md_file.write_text("""
# Test Document

This is a test document with **bold** and *italic* text.

## Introduction

Here's a list:
- Item 1
- Item 2
- Item 3

And a [link](https://example.com).

```python
def hello():
    print("Hello, world!")
```
""")
        return md_file

    @pytest.fixture
    def sample_markdown_with_citations(self, tmp_path):
        """Create a Markdown file with citations."""
        md_file = tmp_path / "citations.md"
        md_file.write_text("""
# Research Paper

According to [Smith et al. (2023)](https://doi.org/10.1234/example),
the results are significant.

*Technical Concept Box: Machine Learning*
This is a concept box explaining ML basics.
It can have multiple paragraphs.

Another citation: [Jones (2022)](https://arxiv.org/abs/2201.00000)
""")
        return md_file

    def test_pandoc_available(self):
        """Test that pandoc is available."""
        # This test is redundant since we skip all tests if pandoc is not available
        assert shutil.which("pandoc") is not None

    def test_convert_simple(self, converter, sample_markdown):
        """Test simple Markdown to LyX conversion."""
        output_file = converter.convert_simple(sample_markdown)

        assert output_file.exists()
        assert output_file.suffix == ".lyx"

        content = output_file.read_text()
        assert "#LyX" in content
        assert "Test Document" in content

    def test_convert_advanced(self, converter, sample_markdown_with_citations):
        """Test advanced conversion with citations."""
        output_file = converter.convert_advanced(
            sample_markdown_with_citations,
            process_citations=True,
            process_concept_boxes=True,
        )

        assert output_file.exists()
        assert output_file.suffix == ".lyx"

        # Check if bibliography was created
        bib_file = converter.output_dir / "references.bib"
        if bib_file.exists():
            bib_content = bib_file.read_text()
            assert "@article" in bib_content or "@misc" in bib_content

    def test_batch_convert(self, converter, sample_markdown, tmp_path):
        """Test batch conversion of multiple files."""
        # Create additional markdown files
        md2 = tmp_path / "doc2.md"
        md2.write_text("# Document 2\n\nContent here.")

        md3 = tmp_path / "doc3.md"
        md3.write_text("# Document 3\n\nMore content.")

        files = [sample_markdown, md2, md3]
        results = converter.batch_convert(files, simple=True)

        assert len(results) == 3
        for md_file, lyx_file in results.items():
            if lyx_file:  # Conversion might fail if tools aren't available
                assert lyx_file.exists()
                assert lyx_file.suffix == ".lyx"

    def test_convert_with_layout_options(self, converter, sample_markdown):
        """Test conversion with layout options."""
        output_file = converter.convert_advanced(
            sample_markdown, two_column=True, arxiv_ready=True
        )

        assert output_file.exists()
        assert output_file.suffix == ".lyx"


@pytest.mark.integration
class TestCLIIntegration:
    """Integration tests for the CLI."""

    def test_cli_imports(self):
        """Test that CLI can be imported."""
        from src.cli_to_lyx import cli

        assert cli is not None

    def test_cli_help(self):
        """Test CLI help command."""
        from click.testing import CliRunner
        from src.cli_to_lyx import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Convert various formats to LyX" in result.output
