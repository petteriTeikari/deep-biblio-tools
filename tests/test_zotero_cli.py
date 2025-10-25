"""Test Zotero CLI integration."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner
from src.cli_md_to_latex import convert_markdown_to_latex

try:
    import pypandoc

    PANDOC_AVAILABLE = True
    try:
        pypandoc.get_pandoc_version()
    except OSError:
        PANDOC_AVAILABLE = False
except ImportError:
    PANDOC_AVAILABLE = False


class TestZoteroCLI:
    """Test Zotero functionality via CLI."""

    def test_zotero_options_in_cli(self):
        """Test that Zotero options are available in CLI."""
        runner = CliRunner()
        result = runner.invoke(convert_markdown_to_latex, ["--help"])

        assert result.exit_code == 0
        assert "--zotero-api-key" in result.output
        assert "--zotero-library-id" in result.output
        assert "ZOTERO_API_KEY" in result.output
        assert "ZOTERO_LIBRARY_ID" in result.output

    @patch("src.converters.md_to_latex.zotero_integration.requests.post")
    @pytest.mark.skipif(not PANDOC_AVAILABLE, reason="pandoc not available")
    def test_zotero_citation_fetch(self, mock_post):
        """Test that Zotero is used when credentials are provided."""
        runner = CliRunner()

        # Mock Zotero translation server response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "itemType": "journalArticle",
                "title": "NeRF: Complete Title from Zotero",
                "creators": [
                    {
                        "firstName": "Ben",
                        "lastName": "Mildenhall",
                        "creatorType": "author",
                    }
                ],
                "date": "2020",
                "DOI": "10.1145/3503250",
            }
        ]
        mock_post.return_value = mock_response

        with runner.isolated_filesystem():
            # Remove any existing cache to ensure clean test
            import shutil

            cache_dir = Path(".cache")
            if cache_dir.exists():
                shutil.rmtree(cache_dir)

            # Create test markdown with citation
            test_md = Path("test.md")
            test_md.write_text("""# Test Document

Here's a citation: [Mildenhall et al. (2020)](https://doi.org/10.1145/3503250)
""")

            # Run with Zotero options and temporary cache
            import tempfile

            with tempfile.TemporaryDirectory() as temp_cache:
                result = runner.invoke(
                    convert_markdown_to_latex,
                    [
                        str(test_md),
                        "--zotero-api-key",
                        "test_key",
                        "--zotero-library-id",
                        "12345",
                        "--cache-dir",
                        temp_cache,
                    ],
                )

            assert result.exit_code == 0

            # Check that bibliography was created with Zotero data
            # Default behavior: output in same directory as input
            bib_file = Path("references.bib")
            assert bib_file.exists()

            bib_content = bib_file.read_text()

            # Debug: check if Zotero was actually called
            assert mock_post.called, "Zotero translation server was not called"

            # Should have the title from Zotero, not from CrossRef
            assert "Complete Title from Zotero" in bib_content

    @pytest.mark.skipif(not PANDOC_AVAILABLE, reason="pandoc not available")
    def test_zotero_env_vars(self):
        """Test that Zotero credentials can be set via environment variables."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create test markdown
            test_md = Path("test.md")
            test_md.write_text("# Test Document\n\nNo citations here.")

            # Run with environment variables
            result = runner.invoke(
                convert_markdown_to_latex,
                [str(test_md)],
                env={
                    "ZOTERO_API_KEY": "env_key",
                    "ZOTERO_LIBRARY_ID": "env_12345",
                },
            )

            assert result.exit_code == 0
