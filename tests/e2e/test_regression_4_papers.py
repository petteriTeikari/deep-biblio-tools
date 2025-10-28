"""Regression tests for 4 working papers.

Tests that the 4 papers convert successfully with ZERO missing citations.
This ensures that future changes don't break the conversion of these papers.

Papers tested:
1. fashion_4DGS/4dgs-fashion-comprehensive-v2.md
2. fashion_3D_CAD/fashion-cad-review-v3.md
3. fashion_LCA/fashion-lca-draft-v3.md
4. mcp-review/mcp-draft-refined-v4.md
"""

import tempfile
from pathlib import Path

import pytest
from src.converters.md_to_latex import MarkdownToLatexConverter
from tests.e2e.helpers_pdf import (
    assert_no_missing_citations,
    extract_pdf_text,
)

# Test data: (markdown_path, display_name)
PAPERS = [
    (
        "/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/fashion_4DGS/4dgs-fashion-comprehensive-v2.md",
        "fashion_4DGS",
    ),
    (
        "/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/fashion_3D_CAD/fashion-cad-review-v3.md",
        "fashion_3D_CAD",
    ),
    (
        "/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/fashion_LCA/fashion-lca-draft-v3.md",
        "fashion_LCA",
    ),
    (
        "/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/mcp-draft-refined-v4.md",
        "mcp_review",
    ),
]


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.parametrize("markdown_path,paper_name", PAPERS)
class TestRegressionPapers:
    """Regression tests for 4 working papers."""

    def test_paper_converts_successfully(
        self, markdown_path: str, paper_name: str
    ):
        """Test that paper converts to PDF without errors.

        Args:
            markdown_path: Path to markdown file
            paper_name: Display name for test reporting
        """
        md_file = Path(markdown_path)

        # Skip if file doesn't exist (e.g., running on CI without access to Dropbox)
        if not md_file.exists():
            pytest.skip(f"Markdown file not found: {markdown_path}")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"

            # Convert with Zotero API (requires credentials)
            converter = MarkdownToLatexConverter(
                output_dir=output_dir,
                zotero_api_key=None,  # Will use env vars
                zotero_library_id=None,
                collection_name="dpp-fashion",
            )

            try:
                converter.convert(
                    markdown_file=md_file, output_name=paper_name, verbose=False
                )
            except Exception as e:
                pytest.fail(f"Conversion failed for {paper_name}: {e}")

            # Verify PDF was created
            pdf_file = output_dir / f"{paper_name}.pdf"
            assert pdf_file.exists(), f"PDF not generated for {paper_name}"

            # Verify PDF has content
            pdf_text = extract_pdf_text(pdf_file)
            assert len(pdf_text) > 0, f"PDF is empty for {paper_name}"

    def test_paper_has_zero_missing_citations(
        self, markdown_path: str, paper_name: str
    ):
        """Test that paper PDF has ZERO (?) citations.

        This is the CRITICAL regression test - ensures all citations are resolved.

        Args:
            markdown_path: Path to markdown file
            paper_name: Display name for test reporting
        """
        md_file = Path(markdown_path)

        # Skip if file doesn't exist
        if not md_file.exists():
            pytest.skip(f"Markdown file not found: {markdown_path}")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"

            # Convert
            converter = MarkdownToLatexConverter(
                output_dir=output_dir,
                zotero_api_key=None,
                zotero_library_id=None,
                collection_name="dpp-fashion",
            )

            try:
                converter.convert(
                    markdown_file=md_file, output_name=paper_name, verbose=False
                )
            except Exception as e:
                pytest.fail(f"Conversion failed for {paper_name}: {e}")

            pdf_file = output_dir / f"{paper_name}.pdf"
            assert pdf_file.exists(), f"PDF not generated for {paper_name}"

            # CRITICAL CHECK: Verify ZERO (?) citations in PDF
            # This will raise AssertionError if any (?) found
            assert_no_missing_citations(pdf_file)

    def test_paper_has_no_unknown_authors(
        self, markdown_path: str, paper_name: str
    ):
        """Test that paper PDF has no 'Unknown' or 'Anonymous' authors.

        Args:
            markdown_path: Path to markdown file
            paper_name: Display name for test reporting
        """
        md_file = Path(markdown_path)

        # Skip if file doesn't exist
        if not md_file.exists():
            pytest.skip(f"Markdown file not found: {markdown_path}")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"

            # Convert
            converter = MarkdownToLatexConverter(
                output_dir=output_dir,
                zotero_api_key=None,
                zotero_library_id=None,
                collection_name="dpp-fashion",
            )

            try:
                converter.convert(
                    markdown_file=md_file, output_name=paper_name, verbose=False
                )
            except Exception as e:
                pytest.fail(f"Conversion failed for {paper_name}: {e}")

            pdf_file = output_dir / f"{paper_name}.pdf"
            assert pdf_file.exists(), f"PDF not generated for {paper_name}"

            # Check for Unknown/Anonymous in PDF
            pdf_text = extract_pdf_text(pdf_file)

            # Check references section specifically
            if "References" in pdf_text or "Bibliography" in pdf_text:
                # Find references section
                refs_start = max(
                    pdf_text.find("References"), pdf_text.find("Bibliography")
                )
                if refs_start > 0:
                    refs_text = pdf_text[refs_start:]

                    # Check for problematic patterns
                    assert "Unknown" not in refs_text, (
                        f"Found 'Unknown' author in {paper_name} references"
                    )
                    assert "Anonymous" not in refs_text, (
                        f"Found 'Anonymous' author in {paper_name} references"
                    )

    def test_paper_bibtex_file_valid(self, markdown_path: str, paper_name: str):
        """Test that generated references.bib has no Unknown/Anonymous entries.

        Args:
            markdown_path: Path to markdown file
            paper_name: Display name for test reporting
        """
        md_file = Path(markdown_path)

        # Skip if file doesn't exist
        if not md_file.exists():
            pytest.skip(f"Markdown file not found: {markdown_path}")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "output"

            # Convert
            converter = MarkdownToLatexConverter(
                output_dir=output_dir,
                zotero_api_key=None,
                zotero_library_id=None,
                collection_name="dpp-fashion",
            )

            try:
                converter.convert(
                    markdown_file=md_file, output_name=paper_name, verbose=False
                )
            except Exception as e:
                pytest.fail(f"Conversion failed for {paper_name}: {e}")

            # Check references.bib
            bib_file = output_dir / "references.bib"
            if bib_file.exists():
                bib_content = bib_file.read_text(encoding="utf-8")

                # Check for problematic patterns in BibTeX
                assert "author = {Unknown}" not in bib_content, (
                    f"Found 'Unknown' author in {paper_name} BibTeX"
                )
                assert "author = {Anonymous}" not in bib_content, (
                    f"Found 'Anonymous' author in {paper_name} BibTeX"
                )
                assert "author={Unknown}" not in bib_content, (
                    f"Found 'Unknown' author in {paper_name} BibTeX"
                )
                assert "author={Anonymous}" not in bib_content, (
                    f"Found 'Anonymous' author in {paper_name} BibTeX"
                )
