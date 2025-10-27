"""Tests for BBL transformer that creates hyperlinked author names."""

import tempfile
from pathlib import Path

import pytest
from src.converters.md_to_latex.bbl_transformer import BblTransformer


@pytest.fixture
def sample_bib_content():
    """Sample BibTeX content with URLs."""
    return """@article{smith2023,
  author = "John Smith and Jane Doe",
  title = "Sample Paper Title",
  year = "2023",
  journal = "Test Journal",
  doi = "10.1234/example",
  url = "https://doi.org/10.1234/example",
}

@article{jones2024,
  author = "Alice Jones and Bob Wilson",
  title = "Another Paper",
  year = "2024",
  journal = "Another Journal",
  doi = "10.5678/test",
  url = "https://doi.org/10.5678/test",
}

@article{nourl2023,
  author = "No URL Author",
  title = "Paper Without URL",
  year = "2023",
  journal = "Journal",
}
"""


@pytest.fixture
def sample_bbl_content():
    """Sample BBL content in standard format."""
    return r"""\begin{thebibliography}{99}

\bibitem[Jones et~al.(2024)Jones and Wilson]{jones2024}
Jones A, Wilson B (2024) Another paper. Another Journal 10(2):100--110

\bibitem[No URL Author(2023)]{nourl2023}
No URL Author (2023) Paper without url. Journal 5:50--60

\bibitem[Smith and Doe(2023)]{smith2023}
Smith J, Doe J (2023) Sample paper title. Test Journal 12(3):45--67

\end{thebibliography}
"""


def test_url_extraction_from_bib(sample_bib_content):
    """Test that URLs are correctly extracted from .bib file."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".bib", delete=False
    ) as bib:
        bib.write(sample_bib_content)
        bib.flush()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".bbl", delete=False
        ) as bbl:
            bbl.write("")  # Empty BBL for now
            bbl.flush()

            try:
                transformer = BblTransformer(Path(bib.name), Path(bbl.name))

                assert "smith2023" in transformer.url_map
                assert "jones2024" in transformer.url_map
                assert "nourl2023" in transformer.url_map

                # Check URL extraction
                url_smith, authors_smith, year_smith = transformer.url_map[
                    "smith2023"
                ]
                assert url_smith == "https://doi.org/10.1234/example"
                assert year_smith == "2023"

                url_jones, authors_jones, year_jones = transformer.url_map[
                    "jones2024"
                ]
                assert url_jones == "https://doi.org/10.5678/test"
                assert year_jones == "2024"

                # Entry without URL should have None
                url_nourl, _, _ = transformer.url_map["nourl2023"]
                assert url_nourl is None
            finally:
                Path(bib.name).unlink()
                Path(bbl.name).unlink()


def test_bbl_transformation_with_urls(sample_bib_content, sample_bbl_content):
    """Test that BBL entries are transformed with href commands."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".bib", delete=False
    ) as bib:
        bib.write(sample_bib_content)
        bib.flush()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".bbl", delete=False
        ) as bbl:
            bbl.write(sample_bbl_content)
            bbl.flush()

            try:
                transformer = BblTransformer(Path(bib.name), Path(bbl.name))
                transformed = transformer.transform()

                # Check that href commands are present for entries with URLs
                assert "\\href{https://doi.org/10.1234/example}" in transformed
                assert "\\href{https://doi.org/10.5678/test}" in transformed

                # Check that author names are wrapped
                assert (
                    "\\href{https://doi.org/10.1234/example}{Smith J, Doe J (2023)}"
                    in transformed
                )
                assert (
                    "\\href{https://doi.org/10.5678/test}{Jones A, Wilson B (2024)}"
                    in transformed
                )

                # Entry without URL should NOT have href
                assert "No URL Author (2023)" in transformed
                assert (
                    "\\href"
                    not in transformed.split("nourl2023")[1].split("\\bibitem")[
                        0
                    ]
                )
            finally:
                Path(bib.name).unlink()
                Path(bbl.name).unlink()


def test_bbl_transformation_preserves_structure(
    sample_bib_content, sample_bbl_content
):
    """Test that transformation preserves BBL structure."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".bib", delete=False
    ) as bib:
        bib.write(sample_bib_content)
        bib.flush()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".bbl", delete=False
        ) as bbl:
            bbl.write(sample_bbl_content)
            bbl.flush()

            try:
                transformer = BblTransformer(Path(bib.name), Path(bbl.name))
                transformed = transformer.transform()

                # Check preamble is preserved
                assert "\\begin{thebibliography}" in transformed
                assert "\\end{thebibliography}" in transformed

                # Check all bibitem entries are present
                assert (
                    "\\bibitem[Jones et~al.(2024)Jones and Wilson]{jones2024}"
                    in transformed
                )
                assert (
                    "\\bibitem[No URL Author(2023)]{nourl2023}" in transformed
                )
                assert (
                    "\\bibitem[Smith and Doe(2023)]{smith2023}" in transformed
                )

                # Check content after author-year is preserved
                assert (
                    "Another paper. Another Journal 10(2):100--110"
                    in transformed
                )
                assert "Paper without url. Journal 5:50--60" in transformed
                assert (
                    "Sample paper title. Test Journal 12(3):45--67"
                    in transformed
                )
            finally:
                Path(bib.name).unlink()
                Path(bbl.name).unlink()


def test_malformed_bbl_entry_handling():
    """Test that malformed BBL entries are returned unchanged."""
    malformed_bbl = r"""\begin{thebibliography}{99}

\bibitem[MalformedEntry]{badkey}
This entry has no year in parentheses and should be returned as-is

\end{thebibliography}
"""

    bib_content = """@article{badkey,
  author = "Bad Author",
  title = "Malformed Entry",
  year = "2023",
  url = "https://example.com",
}
"""

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".bib", delete=False
    ) as bib:
        bib.write(bib_content)
        bib.flush()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".bbl", delete=False
        ) as bbl:
            bbl.write(malformed_bbl)
            bbl.flush()

            try:
                transformer = BblTransformer(Path(bib.name), Path(bbl.name))
                transformed = transformer.transform()

                # Entry should be unchanged (no year in parentheses means no transformation)
                assert "This entry has no year in parentheses" in transformed
                # Should NOT have href since transformation couldn't happen
                assert "\\href" not in transformed
            finally:
                Path(bib.name).unlink()
                Path(bbl.name).unlink()


def test_url_removal_from_bbl():
    """Test that urlprefix and url commands are removed from bibliography."""
    bbl_with_url = r"""\begin{thebibliography}{99}

\bibitem[Smith(2023)]{smith2023}
Smith J (2023) Sample paper title. Test Journal 12(3):45--67
\urlprefix\url{https://doi.org/10.1234/example}

\end{thebibliography}
"""

    bib_content = """@article{smith2023,
  author = "John Smith",
  title = "Sample Paper Title",
  year = "2023",
  url = "https://doi.org/10.1234/example",
}
"""

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".bib", delete=False
    ) as bib:
        bib.write(bib_content)
        bib.flush()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".bbl", delete=False
        ) as bbl:
            bbl.write(bbl_with_url)
            bbl.flush()

            try:
                transformer = BblTransformer(Path(bib.name), Path(bbl.name))
                transformed = transformer.transform()

                # URL commands should be removed
                assert "\\urlprefix" not in transformed
                assert (
                    "\\url{https://doi.org/10.1234/example}" not in transformed
                )

                # But href should be present
                assert "\\href{https://doi.org/10.1234/example}" in transformed
            finally:
                Path(bib.name).unlink()
                Path(bbl.name).unlink()


def test_doi_formatting():
    """Test that DOI-only entries get proper https:// prefix."""
    bib_with_doi = """@article{smith2023,
  author = "John Smith",
  title = "Paper",
  year = "2023",
  doi = "10.1234/example",
}
"""

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".bib", delete=False
    ) as bib:
        bib.write(bib_with_doi)
        bib.flush()

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".bbl", delete=False
        ) as bbl:
            bbl.write("")
            bbl.flush()

            try:
                transformer = BblTransformer(Path(bib.name), Path(bbl.name))

                url, _, _ = transformer.url_map["smith2023"]
                assert url == "https://doi.org/10.1234/example"
            finally:
                Path(bib.name).unlink()
                Path(bbl.name).unlink()
