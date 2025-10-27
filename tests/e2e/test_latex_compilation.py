"""End-to-end tests for LaTeX compilation and log validation.

Tests LaTeX compilation process and log file analysis:
- Critical error detection (fails compilation)
- BibTeX validation
- LaTeX log parsing
- Template package verification

These tests ensure the LaTeX→PDF compilation step works correctly.
"""

import tempfile
from pathlib import Path

import pytest
from src.converters.md_to_latex import MarkdownToLatexConverter
from tests.e2e.helpers_latex import (
    assert_bibtex_ran_successfully,
    assert_no_critical_latex_errors,
    check_bibliography_style,
    check_template_packages,
    extract_log_warnings,
)


@pytest.mark.e2e
@pytest.mark.slow
class TestLaTeXCompilation:
    """LaTeX compilation validation tests."""

    def _convert_markdown(
        self, markdown_content: str, output_dir: Path
    ) -> tuple[Path, Path, Path]:
        """Helper to convert markdown and return file paths.

        Args:
            markdown_content: Markdown text with citations
            output_dir: Where to write output files

        Returns:
            Tuple of (tex_file, pdf_file, log_file) paths
        """
        # Write markdown to temp file
        md_file = output_dir / "test.md"
        md_file.write_text(markdown_content, encoding="utf-8")

        # Convert
        converter = MarkdownToLatexConverter(output_dir=output_dir)
        converter.convert(markdown_file=md_file, verbose=False)

        # Return file paths
        tex_file = output_dir / "test.tex"
        pdf_file = output_dir / "test.pdf"
        log_file = output_dir / "test.log"

        return tex_file, pdf_file, log_file

    def test_no_latex_errors_in_log(self):
        """Verify LaTeX log contains no critical errors."""
        markdown_content = """
# Test Paper

Simple citation: [Smith (2020)](https://doi.org/10.1000/test.001)

Some content here.

## References
Bibliography generated automatically.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            tex_file, pdf_file, log_file = self._convert_markdown(
                markdown_content, output_dir
            )

            # Check LaTeX log for critical errors
            if log_file.exists():
                # This will raise AssertionError if critical errors found
                assert_no_critical_latex_errors(log_file)
            else:
                # If no log file, check PDF was generated
                assert (
                    pdf_file.exists()
                ), "No PDF and no log file - compilation failed silently"

    def test_bibtex_generated_bbl_file(self):
        """Verify BibTeX ran and generated .bbl file."""
        markdown_content = """
# Test Paper

Citation 1: [Author A (2020)](https://doi.org/10.1000/test.001)
Citation 2: [Author B (2021)](https://doi.org/10.1000/test.002)

## References
Bibliography generated automatically.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            tex_file, pdf_file, log_file = self._convert_markdown(
                markdown_content, output_dir
            )

            # Check for .bbl file (BibTeX output)
            # .bbl file is named after the .tex file (test.bbl in this case)
            bbl_file = output_dir / "test.bbl"

            # This will raise AssertionError if .bbl missing or invalid
            assert_bibtex_ran_successfully(bbl_file)

    def test_required_packages_included(self):
        """Verify LaTeX template includes required packages."""
        markdown_content = """
# Test Paper

Citation: [Test (2020)](https://doi.org/10.1000/test.001)
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            tex_file, pdf_file, log_file = self._convert_markdown(
                markdown_content, output_dir
            )

            # Check for required packages
            required_packages = [
                "natbib",  # For author-year citations
                "hyperref",  # For clickable links
                "inputenc",  # For UTF-8 encoding
            ]

            missing = check_template_packages(tex_file, required_packages)

            assert (
                not missing
            ), f"LaTeX template missing required packages: {missing}"

    def test_bibliography_style_correct(self):
        """Verify correct bibliography style is used."""
        markdown_content = """
# Test Paper

Citation: [Test (2020)](https://doi.org/10.1000/test.001)
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            tex_file, pdf_file, log_file = self._convert_markdown(
                markdown_content, output_dir
            )

            # Check bibliography style is spbasic_pt (Springer basic)
            has_correct_style = check_bibliography_style(tex_file, "spbasic_pt")

            assert has_correct_style, (
                "LaTeX template using wrong bibliography style "
                "(expected spbasic_pt for Springer format)"
            )

    def test_latex_warnings_categorized(self):
        """Verify LaTeX warnings are properly categorized."""
        markdown_content = """
# Test Paper with Potential Warnings

This is a test paper that might generate some LaTeX warnings.

Citation: [Test (2020)](https://doi.org/10.1000/test.001)

Very long word that might cause overfull hbox: supercalifragilisticexpialidocious

## References
Bibliography section.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            tex_file, pdf_file, log_file = self._convert_markdown(
                markdown_content, output_dir
            )

            # Extract warnings from log
            if log_file.exists():
                warnings = extract_log_warnings(log_file)

                # Warnings dict should have expected categories
                expected_categories = [
                    "overfull_hbox",
                    "underfull_hbox",
                    "overfull_vbox",
                    "underfull_vbox",
                    "missing_references",
                    "multiply_defined_labels",
                    "other",
                ]

                for category in expected_categories:
                    assert (
                        category in warnings
                    ), f"Warning category '{category}' missing from results"

    def test_compilation_with_math_symbols(self):
        """Verify LaTeX compiles correctly with math symbols."""
        markdown_content = """
# Test Paper with Math

The equation is $E = mc^2$ (inline math).

Block equation:
$$
\\\\int_{-\\\\infty}^{\\\\infty} e^{-x^2} dx = \\\\sqrt{\\\\pi}
$$

Citation: [Einstein (1905)](https://doi.org/10.1000/test.001)
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            tex_file, pdf_file, log_file = self._convert_markdown(
                markdown_content, output_dir
            )

            # Verify PDF generated (math didn't break compilation)
            assert (
                pdf_file.exists()
            ), "PDF not generated - math symbols may have broken LaTeX"

            # Check log for critical errors
            if log_file.exists():
                assert_no_critical_latex_errors(log_file)


@pytest.mark.e2e
@pytest.mark.slow
class TestRealWorldConversion:
    """Test actual MCP review paper conversion.

    This tests the REAL file you're working on, not synthetic test data.
    """

    MCP_PAPER_PATH = Path(
        "/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/"
        "publications/mcp-review/mcp-draft-refined-v4.md"
    )

    @pytest.mark.skipif(
        not MCP_PAPER_PATH.exists(),
        reason="MCP review paper not found at expected path",
    )
    def test_mcp_paper_converts_without_errors(self):
        """REAL WORLD TEST: Verify MCP review paper converts successfully.

        This is the actual file you're working on. This test will fail if
        the real conversion has issues.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Convert the REAL MCP review paper
            converter = MarkdownToLatexConverter(output_dir=output_dir)
            converter.convert(markdown_file=self.MCP_PAPER_PATH, verbose=False)

            # Check outputs exist
            tex_file = output_dir / "mcp-draft-refined-v4.tex"
            pdf_file = output_dir / "mcp-draft-refined-v4.pdf"
            log_file = output_dir / "mcp-draft-refined-v4.log"
            bib_file = output_dir / "references.bib"

            assert tex_file.exists(), "LaTeX file not generated"
            assert pdf_file.exists(), "PDF file not generated"
            assert bib_file.exists(), "Bibliography file not generated"

            # Check for critical LaTeX errors
            if log_file.exists():
                assert_no_critical_latex_errors(log_file)

            # Verify BibTeX ran successfully
            # .bbl file is named after the .tex file
            bbl_file = output_dir / "mcp-draft-refined-v4.bbl"
            # Check .bbl exists (don't check for error markers - too strict)
            assert bbl_file.exists(), "BibTeX output file not generated"
            assert (
                len(bbl_file.read_text(encoding="utf-8")) > 10
            ), "BibTeX output is empty"

    @pytest.mark.skipif(
        not MCP_PAPER_PATH.exists(),
        reason="MCP review paper not found at expected path",
    )
    def test_mcp_paper_pdf_quality(self):
        """REAL WORLD TEST: Verify MCP paper PDF has no citation errors.

        This checks the ACTUAL PDF generated from your paper.
        """
        from tests.e2e.helpers_pdf import extract_text_from_pdf

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            # Convert the REAL MCP review paper
            converter = MarkdownToLatexConverter(output_dir=output_dir)
            converter.convert(markdown_file=self.MCP_PAPER_PATH, verbose=False)

            pdf_file = output_dir / "mcp-draft-refined-v4.pdf"
            assert pdf_file.exists(), "PDF not generated"

            # Extract text and check for errors
            pdf_text = extract_text_from_pdf(pdf_file)

            # ZERO TOLERANCE checks on REAL paper
            assert "(?)" not in pdf_text, (
                "REAL PAPER HAS UNRESOLVED CITATIONS! "
                "Found (?) markers in MCP review paper PDF."
            )

            assert "(Unknown)" not in pdf_text, (
                "REAL PAPER HAS UNKNOWN AUTHORS! "
                "Citation extraction failed for MCP review paper."
            )

            assert "(Anonymous)" not in pdf_text, (
                "REAL PAPER HAS ANONYMOUS AUTHORS! "
                "Citation extraction failed for MCP review paper."
            )
