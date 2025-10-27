"""End-to-end tests for PDF structural validation.

Tests PDF structure and compliance requirements:
- Hyperlink extraction and validation
- Font embedding (arXiv compliance)
- Metadata presence
- Multi-page handling

These tests ensure the generated PDFs meet submission requirements.
"""

import tempfile
from pathlib import Path

import pytest
from src.converters.md_to_latex import MarkdownToLatexConverter
from tests.e2e.helpers_pdf import (
    extract_links,
    extract_text_from_pdf,
    get_font_info,
    get_metadata,
    get_page_count,
)


@pytest.mark.e2e
@pytest.mark.slow
class TestPDFStructure:
    """PDF structural validation tests."""

    def _convert_markdown_to_pdf(
        self, markdown_content: str, temp_dir: Path
    ) -> Path:
        """Helper to convert markdown to PDF.

        Args:
            markdown_content: Markdown text with citations
            output_dir: Where to write output files

        Returns:
            Path to generated PDF
        """
        # Write markdown to temp file
        md_file = temp_dir / "test.md"
        md_file.write_text(markdown_content, encoding="utf-8")

        # Convert
        output_dir = temp_dir / "output"
        converter = MarkdownToLatexConverter(output_dir=output_dir)
        converter.convert(markdown_file=md_file, verbose=False)

        # Return PDF path
        pdf_file = output_dir / "test.pdf"
        return pdf_file

    def test_hyperlinks_preserved_in_pdf(self):
        """Verify citation URLs are embedded as clickable links in PDF."""
        markdown_content = """
# Test Paper

Citation with DOI: [Smith (2020)](https://doi.org/10.1000/test.001)

Citation with arXiv: [Jones (2021)](https://arxiv.org/abs/2101.00001)
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            pdf_file = self._convert_markdown_to_pdf(markdown_content, temp_dir)

            # Extract all hyperlinks
            links = extract_links(pdf_file)

            # Should have at least 2 external links
            uri_links = [url for _, url, kind in links if kind == "uri"]

            # Check for DOI link
            doi_links = [url for url in uri_links if "doi.org" in url]
            assert len(doi_links) >= 1, "DOI link not found in PDF"

            # Check for arXiv link
            arxiv_links = [url for url in uri_links if "arxiv.org" in url]
            assert len(arxiv_links) >= 1, "arXiv link not found in PDF"

    def test_fonts_embedded_arxiv_compliance(self):
        """Verify all fonts are embedded (arXiv requirement).

        arXiv rejects PDFs with non-embedded fonts. This is a critical check.
        """
        markdown_content = """
# Test Paper with Various Fonts

Regular text, **bold text**, *italic text*, and `code text`.

Citation: [Test (2020)](https://doi.org/10.1000/test.001)

## Math Example

Inline math: The equation is important.

## References
Bibliography section here.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            pdf_file = self._convert_markdown_to_pdf(markdown_content, temp_dir)

            # Get font information
            fonts = get_font_info(pdf_file)

            # Flatten all fonts across pages
            all_fonts = []
            for page_fonts in fonts.values():
                all_fonts.extend(page_fonts)

            # Check that fonts exist
            assert len(all_fonts) > 0, "No fonts found in PDF"

            # Find any non-embedded fonts
            unembedded_fonts = [f for f in all_fonts if not f["embedded"]]

            # arXiv CRITICAL: All fonts must be embedded
            assert not unembedded_fonts, (
                f"arXiv compliance FAILED: {len(unembedded_fonts)} "
                f"non-embedded fonts found: {unembedded_fonts}"
            )

    def test_pdf_metadata_present(self):
        """Verify PDF has metadata (title, producer, etc.)."""
        markdown_content = """
# Research Paper Title

Some content here.

Citation: [Author (2020)](https://doi.org/10.1000/test.001)
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            pdf_file = self._convert_markdown_to_pdf(markdown_content, temp_dir)

            # Get metadata
            metadata = get_metadata(pdf_file)

            # Check for producer/creator (indicates PDF generation tool)
            # Keys may have / prefix like '/Producer'
            has_producer = any(
                "producer" in str(key).lower() for key in metadata.keys()
            )
            has_creator = any(
                "creator" in str(key).lower() for key in metadata.keys()
            )

            assert (
                has_producer or has_creator
            ), "PDF missing producer/creator metadata"

    def test_multi_page_pdf_handling(self):
        """Verify pipeline handles multi-page PDFs correctly."""
        # Create content that will span multiple pages
        markdown_content = """
# Multi-Page Test Paper

## Introduction

Citation 1: [Author A (2020)](https://doi.org/10.1000/test.001)

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod
tempor incididunt ut labore et dolore magna aliqua.

## Section 1

Citation 2: [Author B (2021)](https://doi.org/10.1000/test.002)

Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi
ut aliquip ex ea commodo consequat.

## Section 2

Citation 3: [Author C (2022)](https://doi.org/10.1000/test.003)

Duis aute irure dolor in reprehenderit in voluptate velit esse cillum
dolore eu fugiat nulla pariatur.

## Section 3

Citation 4: [Author D (2023)](https://doi.org/10.1000/test.004)

Excepteur sint occaecat cupidatat non proident, sunt in culpa qui
officia deserunt mollit anim id est laborum.

## Conclusion

Final thoughts with Citation 5: [Author E (2024)](https://doi.org/10.1000/test.005)

## References

Bibliography generated automatically.
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            pdf_file = self._convert_markdown_to_pdf(markdown_content, temp_dir)

            # Check page count (may be 1 or more pages depending on template)
            page_count = get_page_count(pdf_file)
            assert (
                page_count >= 1
            ), f"Expected at least 1 page, got {page_count} page(s)"

            # Extract text to verify content across pages
            pdf_text = extract_text_from_pdf(pdf_file)

            # Check that all sections appear
            assert "Introduction" in pdf_text, "Section missing in PDF"
            assert "Conclusion" in pdf_text, "Section missing in PDF"

            # Check citations span pages (uses abbreviated author names)
            # Citations show as (A, 2020), (E, 2024), etc.
            assert "(A, 2020)" in pdf_text, "Citation missing in multi-page PDF"
            assert "(E, 2024)" in pdf_text, "Citation missing in multi-page PDF"


@pytest.mark.e2e
@pytest.mark.slow
class TestHyperlinkStyling:
    """Test hyperlink appearance and styling in PDFs."""

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
        md_file = temp_dir / "test.md"
        md_file.write_text(markdown_content, encoding="utf-8")

        output_dir = temp_dir / "output"
        converter = MarkdownToLatexConverter(output_dir=output_dir)
        converter.convert(markdown_file=md_file, verbose=False)

        return output_dir / "test.pdf"

    def test_citation_links_are_clickable(self):
        """Verify citations become clickable hyperlinks, not plain text."""
        markdown_content = """
# Test Paper

This paper cites [Important Work (2020)](https://doi.org/10.1145/example).

Another citation: [Another Work (2021)](https://arxiv.org/abs/2101.00001)
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            pdf_file = self._convert_markdown_to_pdf(markdown_content, temp_dir)

            # Extract links
            links = extract_links(pdf_file)
            uri_links = [url for _, url, kind in links if kind == "uri"]

            # Should have clickable links
            assert (
                len(uri_links) >= 2
            ), f"Expected ≥2 clickable links, found {len(uri_links)}"

            # Check links are external URLs (not internal references)
            external_links = [
                url for url in uri_links if url.startswith("http")
            ]
            assert (
                len(external_links) >= 2
            ), "Citations not converted to external hyperlinks"

    def test_regular_hyperlinks_preserved(self):
        """Verify non-citation hyperlinks are also preserved."""
        markdown_content = """
# Test Paper

Check out [this website](https://example.com) for more information.

Documentation available at [docs](https://docs.example.org/guide).

Citation: [Smith (2020)](https://doi.org/10.1000/test.001)
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            pdf_file = self._convert_markdown_to_pdf(markdown_content, temp_dir)

            # Extract links
            links = extract_links(pdf_file)
            uri_links = [url for _, url, kind in links if kind == "uri"]

            # Check for example.com link
            example_links = [url for url in uri_links if "example.com" in url]
            assert (
                len(example_links) >= 1
            ), "Regular hyperlink not preserved in PDF"

            # Check for docs link
            docs_links = [url for url in uri_links if "docs.example.org" in url]
            assert (
                len(docs_links) >= 1
            ), "Documentation link not preserved in PDF"
