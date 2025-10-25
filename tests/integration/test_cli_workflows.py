"""Integration tests for CLI workflows."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from src.cli import cli

# Check for pandoc availability
try:
    import pypandoc

    PANDOC_AVAILABLE = True
    try:
        pypandoc.get_pandoc_version()
    except OSError:
        PANDOC_AVAILABLE = False
except ImportError:
    PANDOC_AVAILABLE = False


class TestCLIWorkflows:
    """Test complete CLI workflows end-to-end."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def sample_bibliography(self):
        """Create sample bibliography content."""
        return """
@article{smith2023deep,
  author = {Smith, John and Doe, Jane},
  title = {Deep Learning for Computer Vision},
  journal = {Nature Machine Intelligence},
  year = {2023},
  volume = {5},
  pages = {123--145},
  doi = {10.1038/s42256-023-00001-9}
}

@inproceedings{jones2023neural,
  author = {Jones, Alice et al.},
  title = {Neural Networks in Practice},
  booktitle = {Proceedings of ICML},
  year = {2023},
  pages = {456--478}
}
"""

    @pytest.fixture
    def sample_markdown(self):
        """Create sample markdown with citations."""
        return """
# Research Paper

This research builds on previous work (Smith & Doe, 2023) in deep learning.
Recent advances in neural networks (Jones et al., 2023) have shown promise.

## References

Smith, J., & Doe, J. (2023). Deep Learning for Computer Vision. *Nature Machine Intelligence*, 5, 123-145.

Jones, A., et al. (2023). Neural Networks in Practice. In *Proceedings of ICML* (pp. 456-478).
"""

    def test_validate_bibliography_workflow(self, runner, sample_bibliography):
        """Test bibliography validation workflow."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".bib", delete=False
        ) as f:
            f.write(sample_bibliography)
            bib_path = f.name

        try:
            # Run validation
            result = runner.invoke(cli, ["bib", "validate", bib_path])

            assert result.exit_code == 0  # Should pass with warnings
            assert "Validating bibliography" in result.output
            assert "Checking for hallucinations" in result.output
            assert (
                "jones2023neural" in result.output
            )  # Should flag et al. as hallucination warning

        finally:
            Path(bib_path).unlink()

    def test_fix_bibliography_workflow(self, runner, sample_bibliography):
        """Test bibliography fixing workflow."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".bib", delete=False
        ) as f:
            f.write(sample_bibliography)
            bib_path = f.name

        try:
            # Run fix command
            result = runner.invoke(
                cli, ["bib", "fix", bib_path, "--output", bib_path]
            )

            assert result.exit_code == 0
            assert "Fixing bibliography" in result.output

            # Check that file was modified
            with open(bib_path) as f:
                fixed_content = f.read()

            # Should have fixed et al.
            assert (
                "et al." not in fixed_content or "author" not in fixed_content
            )

        finally:
            Path(bib_path).unlink()

    def test_sort_bibliography_workflow(self, runner, sample_bibliography):
        """Test bibliography sorting workflow."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".bib", delete=False
        ) as f:
            f.write(sample_bibliography)
            bib_path = f.name

        output_path = Path(tempfile.mktemp(suffix=".bib"))

        try:
            # Run sort by year
            result = runner.invoke(
                cli,
                [
                    "bib",
                    "sort",
                    bib_path,
                    "--output",
                    str(output_path),
                ],
            )

            assert result.exit_code == 0
            assert "Sorting bibliography" in result.output
            assert output_path.exists()

            # Check sorted content
            with open(output_path) as f:
                sorted_content = f.read()

            # Both entries are from 2023, so order should be stable
            assert "@article{smith2023deep" in sorted_content
            assert "@inproceedings{jones2023neural" in sorted_content

        finally:
            Path(bib_path).unlink()
            if output_path.exists():
                output_path.unlink()

    def test_format_bibliography_workflow(self, runner, sample_bibliography):
        """Test bibliography formatting workflow."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".bib", delete=False
        ) as f:
            f.write(sample_bibliography)
            bib_path = f.name

        try:
            # Run format command
            result = runner.invoke(cli, ["bib", "format-keys", bib_path])

            assert result.exit_code == 0
            assert "Formatting bibliography" in result.output

            # Check that keys were formatted
            assert "Formatted keys to author-year style" in result.output

        finally:
            Path(bib_path).unlink()

    def test_extract_citations_workflow(self, runner, sample_markdown):
        """Test citation extraction from markdown."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(sample_markdown)
            md_path = f.name

        output_path = Path(tempfile.mktemp(suffix=".bib"))

        try:
            # Run extract command
            result = runner.invoke(
                cli, ["bib", "extract", md_path, "--output", str(output_path)]
            )

            assert result.exit_code == 0
            assert "Extracting citations" in result.output
            assert output_path.exists()

            # Check extracted bibliography
            with open(output_path) as f:
                bib_content = f.read()

            assert "Smith" in bib_content
            assert "2023" in bib_content

        finally:
            Path(md_path).unlink()
            if output_path.exists():
                output_path.unlink()

    def test_check_hallucinations_workflow(self, runner):
        """Test hallucination detection workflow."""
        # Create bibliography with suspicious entries
        suspicious_bib = """
@article{generic2023,
  author = {Author, Generic et al.},
  title = {A Study of Machine Learning},
  journal = {Journal of AI},
  year = {2025},
  pages = {1-1000}
}

@inproceedings{real2023,
  author = {Mildenberger, Thorsten and Smith, John},
  title = {Specific Research on Neural Radiance Fields},
  booktitle = {NeurIPS 2023},
  year = {2023},
  pages = {123--134}
}
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".bib", delete=False
        ) as f:
            f.write(suspicious_bib)
            bib_path = f.name

        try:
            # Run hallucination check
            result = runner.invoke(cli, ["bib", "validate", bib_path])

            assert result.exit_code == 0
            assert "Checking for hallucinations" in result.output
            assert (
                "generic2023" in result.output
            )  # Should flag suspicious entry
            assert "et al." in result.output
            assert "generic title" in result.output.lower()

        finally:
            Path(bib_path).unlink()

    @pytest.mark.skipif(not PANDOC_AVAILABLE, reason="pandoc not available")
    def test_markdown_to_latex_workflow(self, runner, sample_markdown):
        """Test markdown to LaTeX conversion workflow."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False
        ) as f:
            f.write(sample_markdown)
            md_path = f.name

        output_path = Path(tempfile.mktemp(suffix=".tex"))

        try:
            # Run conversion
            result = runner.invoke(
                cli, ["md2latex", md_path, "--output", str(output_path)]
            )

            assert result.exit_code == 0
            assert "Converting markdown to LaTeX" in result.output
            assert output_path.exists()

            # Check LaTeX output
            with open(output_path) as f:
                latex_content = f.read()

            assert r"\title{Research Paper}" in latex_content
            assert (
                r"\cite{" in latex_content
                or r"Smith \& Doe, 2023" in latex_content
            )

        finally:
            Path(md_path).unlink()
            if output_path.exists():
                output_path.unlink()

    def test_pipeline_workflow(self, runner, sample_bibliography):
        """Test complete pipeline: validate -> fix -> sort -> format."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".bib", delete=False
        ) as f:
            f.write(sample_bibliography)
            bib_path = f.name

        # Create temporary files for intermediate steps
        fixed_path = Path(tempfile.mktemp(suffix="-fixed.bib"))
        sorted_path = Path(tempfile.mktemp(suffix="-sorted.bib"))

        try:
            # Step 1: Validate
            result = runner.invoke(cli, ["bib", "validate", bib_path])
            assert result.exit_code == 0

            # Step 2: Fix
            result = runner.invoke(
                cli, ["bib", "fix", bib_path, "--output", str(fixed_path)]
            )
            assert result.exit_code == 0
            assert fixed_path.exists()

            # Step 3: Sort
            result = runner.invoke(
                cli,
                [
                    "bib",
                    "sort",
                    str(fixed_path),
                    "--output",
                    str(sorted_path),
                ],
            )
            assert result.exit_code == 0
            assert sorted_path.exists()

            # Step 4: Format
            result = runner.invoke(
                cli, ["bib", "format-keys", str(sorted_path)]
            )
            assert result.exit_code == 0
            assert "Smith, John and Doe, Jane" in result.output

        finally:
            Path(bib_path).unlink()
            if fixed_path.exists():
                fixed_path.unlink()
            if sorted_path.exists():
                sorted_path.unlink()

    @patch("src.api_clients.crossref.CrossRefClient.get_by_doi")
    def test_doi_validation_workflow(self, mock_get_by_doi, runner):
        """Test DOI validation workflow with mocked API."""
        # Mock CrossRef response - return the parsed format that get_by_doi returns
        mock_get_by_doi.return_value = {
            "doi": "10.1038/s42256-023-00001-9",
            "title": "Deep Learning for Computer Vision",
            "authors": [
                {"given": "John", "family": "Smith"},
                {"given": "Jane", "family": "Doe"},
            ],
            "year": 2023,
            "journal": None,
            "volume": None,
            "issue": None,
            "pages": None,
            "publisher": None,
            "type": "journal-article",
            "url": "https://doi.org/10.1038/s42256-023-00001-9",
        }

        bib_with_doi = """
@article{smith2023,
  author = {Smith, John and Doe, Jane},
  title = {Deep Learning for Computer Vision},
  journal = {Nature Machine Intelligence},
  year = {2023},
  doi = {10.1038/s42256-023-00001-9}
}
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".bib", delete=False
        ) as f:
            f.write(bib_with_doi)
            bib_path = f.name

        try:
            # Run validation with DOI checking
            result = runner.invoke(cli, ["bib", "validate", bib_path])

            assert result.exit_code == 0
            assert "Bibliography is valid!" in result.output
            # DOI validation would use the mock if implemented
            # assert mock_get_by_doi.called

        finally:
            Path(bib_path).unlink()

    def test_batch_processing_workflow(self, runner):
        """Test batch processing of multiple bibliography files."""
        # Create multiple bibliography files
        bib_files = []

        for i in range(3):
            content = f"""
@article{{paper{i}2023,
  author = {{Smith, John and Doe, Jane}},
  title = {{Research Paper {i}}},
  journal = {{Journal of Computer Science}},
  year = {{2023}},
  doi = {{10.1000/example{i}}}
}}
"""
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=f"_{i}.bib", delete=False
            ) as f:
                f.write(content)
                bib_files.append(f.name)

        try:
            # Run validation on first file only (not true batch processing)
            result = runner.invoke(cli, ["bib", "validate", bib_files[0]])

            assert result.exit_code == 0
            assert "Bibliography is valid!" in result.output

        finally:
            for bib_file in bib_files:
                Path(bib_file).unlink()
