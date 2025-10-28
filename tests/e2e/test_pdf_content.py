"""End-to-end tests for PDF content validation.

Tests the core requirement: MD→LaTeX→PDF pipeline produces PDFs with
properly resolved citations (NO "(?)", "Unknown", or "Anonymous" markers).

This is the ZERO TOLERANCE test - these failures are showstoppers.
"""

import tempfile
from pathlib import Path

import pytest
from src.converters.md_to_latex import MarkdownToLatexConverter
from tests.e2e.helpers_pdf import (
    count_citations_in_text,
    extract_text_from_pdf,
    get_page_count,
    normalize_pdf_text,
)


@pytest.mark.e2e
@pytest.mark.slow
class TestPDFContentValidation:
    """Critical PDF content validation tests."""

    def _convert_markdown_to_pdf(
        self, markdown_content: str, temp_dir: Path
    ) -> Path:
        """Helper to convert markdown to PDF.

        Args:
            markdown_content: Markdown text with citations
            temp_dir: Temporary directory for test files

        Returns:
            Path to generated PDF
        """
        # Write markdown to temp file (in temp_dir, NOT in output)
        md_file = temp_dir / "test.md"
        md_file.write_text(markdown_content, encoding="utf-8")

        # Output goes to subdirectory
        output_dir = temp_dir / "output"

        # Convert
        converter = MarkdownToLatexConverter(output_dir=output_dir)
        converter.convert(markdown_file=md_file, verbose=False)

        # Return PDF path
        pdf_file = output_dir / "test.pdf"
        return pdf_file

    def test_zero_unresolved_citations(self):
        """CRITICAL: PDF must have ZERO (?) citation markers.

        This is the primary quality gate. If this fails, the pipeline is broken.
        """
        markdown_content = """
# Test Paper

Citation 1: [Smith (2020)](https://doi.org/10.1000/test.12345)

Citation 2: [Zhang et al. (2021)](https://arxiv.org/abs/2101.00001)

## References
Bibliography generated automatically.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            pdf_file = self._convert_markdown_to_pdf(markdown_content, temp_dir)

            # Verify PDF exists
            assert pdf_file.exists(), "PDF was not generated"

            # Extract text
            pdf_text = extract_text_from_pdf(pdf_file)

            # ZERO TOLERANCE checks
            assert "(?)" not in pdf_text, (
                "Found unresolved citation (?). Pipeline BROKEN."
            )
            assert "(Unknown)" not in pdf_text, (
                "Found Unknown author. Citation extraction FAILED."
            )
            assert "(Anonymous)" not in pdf_text, (
                "Found Anonymous author. Citation extraction FAILED."
            )

    def test_author_names_present_in_pdf(self):
        """Verify actual author names appear in PDF (not just checking absence of errors)."""
        markdown_content = """
# Test Paper

Here is a citation: [Mildenhall et al. (2022)](https://doi.org/10.1145/3503250)
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            pdf_file = self._convert_markdown_to_pdf(markdown_content, temp_dir)

            pdf_text = extract_text_from_pdf(pdf_file)
            normalized_text = normalize_pdf_text(pdf_text)

            # Check for author name
            assert "mildenhall" in normalized_text.lower(), (
                "Author name not found in PDF"
            )

            # Check for year
            assert "2022" in pdf_text, "Year not found in PDF"

    def test_bibliography_section_exists(self):
        """Verify PDF contains bibliography/references section."""
        markdown_content = """
# Test Paper

Citation: [Test Author (2020)](https://doi.org/10.1000/test.001)

## Some content

More text here.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            pdf_file = self._convert_markdown_to_pdf(markdown_content, temp_dir)

            pdf_text = extract_text_from_pdf(pdf_file)
            pdf_text_lower = pdf_text.lower()

            # Check for bibliography section header
            assert (
                "references" in pdf_text_lower
                or "bibliography" in pdf_text_lower
            ), "Bibliography section not found in PDF"

    def test_citation_count_matches_expected(self):
        """Verify number of citations in PDF matches markdown."""
        markdown_content = """
# Test Paper

Citation 1: [Smith (2020)](https://doi.org/10.1000/test.001)
Citation 2: [Jones (2021)](https://doi.org/10.1000/test.002)
Citation 3: [Brown (2022)](https://doi.org/10.1000/test.003)
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            pdf_file = self._convert_markdown_to_pdf(markdown_content, temp_dir)

            pdf_text = extract_text_from_pdf(pdf_file)
            citation_count = count_citations_in_text(pdf_text)

            # Should have at least 3 citations (might have more in bibliography)
            assert citation_count >= 3, (
                f"Expected ≥3 citations, found {citation_count}"
            )

    def test_pdf_not_empty(self):
        """Basic sanity check: PDF has content."""
        markdown_content = """
# Test Paper

Some content here.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            pdf_file = self._convert_markdown_to_pdf(markdown_content, temp_dir)

            # Check page count
            page_count = get_page_count(pdf_file)
            assert page_count > 0, "PDF has no pages"

            # Check text extraction works
            pdf_text = extract_text_from_pdf(pdf_file)
            assert len(pdf_text) > 50, "PDF text too short"

    def test_multiple_citations_from_same_paper(self):
        """Verify duplicate citations are handled correctly."""
        markdown_content = """
# Test Paper

First mention: [Smith (2020)](https://doi.org/10.1000/test.001)

Second mention: [Smith (2020)](https://doi.org/10.1000/test.001)

Third mention: [Smith (2020)](https://doi.org/10.1000/test.001)
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            pdf_file = self._convert_markdown_to_pdf(markdown_content, temp_dir)

            pdf_text = extract_text_from_pdf(pdf_file)

            # Check no unresolved citations
            assert "(?)" not in pdf_text, "Duplicate citations not resolved"

            # Check "Smith" appears multiple times
            smith_count = pdf_text.lower().count("smith")
            assert smith_count >= 3, (
                f"Expected ≥3 'Smith' mentions, found {smith_count}"
            )


@pytest.mark.e2e
@pytest.mark.slow
class TestEdgeCases:
    """Test edge cases and error handling."""

    def _convert_markdown_to_pdf(
        self, markdown_content: str, temp_dir: Path
    ) -> Path:
        """Helper to convert markdown to PDF."""
        md_file = temp_dir / "test.md"
        md_file.write_text(markdown_content, encoding="utf-8")

        output_dir = temp_dir / "output"
        converter = MarkdownToLatexConverter(output_dir=output_dir)
        converter.convert(markdown_file=md_file, verbose=False)

        return output_dir / "test.pdf"

    def test_markdown_without_citations(self):
        """Pipeline should work even without citations."""
        markdown_content = """
# Test Paper

This paper has no citations.

Just plain text content.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            pdf_file = self._convert_markdown_to_pdf(markdown_content, temp_dir)

            assert pdf_file.exists(), (
                "PDF not generated for citation-free markdown"
            )

            pdf_text = extract_text_from_pdf(pdf_file)
            assert len(pdf_text) > 20, (
                "PDF too short for citation-free markdown"
            )

    def test_markdown_with_special_characters(self):
        """Test handling of LaTeX special characters."""
        markdown_content = """
# Test Paper with Dollar Signs

Price range: $50-200 (should be escaped)

Performance: 80 percent accuracy

Citation: [Test (2020)](https://doi.org/10.1000/test.001)
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            pdf_file = self._convert_markdown_to_pdf(markdown_content, temp_dir)

            assert pdf_file.exists(), "PDF not generated with special chars"

            pdf_text = extract_text_from_pdf(pdf_file)

            # Check special chars rendered (not literal LaTeX errors)
            assert "50" in pdf_text, "Dollar sign handling broken"
            assert "200" in pdf_text, "Dollar sign handling broken"
