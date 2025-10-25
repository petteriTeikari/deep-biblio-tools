"""Test the citation context finder functionality."""

import tempfile
from pathlib import Path

from src.utils.citation_context_finder import (
    CitationContext,
    CitationContextFinder,
)


class TestCitationContextFinder:
    """Test citation context finder."""

    def test_citation_context_creation(self):
        """Test creating a citation context object."""
        ctx = CitationContext(
            file_path="/path/to/file.md",
            line_number=42,
            text_before="Some text before ",
            citation_text="Smith et al. (2023)",
            text_after=" and some text after",
            full_line="Some text before [Smith et al. (2023)](https://example.com) and some text after",
        )

        assert ctx.file_path == "/path/to/file.md"
        assert ctx.line_number == 42
        assert ctx.citation_text == "Smith et al. (2023)"
        assert "file.md" in repr(ctx)
        assert "line=42" in repr(ctx)

    def test_normalize_url(self):
        """Test URL normalization."""
        finder = CitationContextFinder()

        # Test trailing slash removal
        assert (
            finder._normalize_url("https://example.com/")
            == "https://example.com"
        )

        # Test escaped characters
        assert (
            finder._normalize_url("https://doi.org/10.1016/0167-2789\\(90\\)")
            == "https://doi.org/10.1016/0167-2789(90)"
        )

        # Test lowercase conversion
        assert (
            finder._normalize_url("HTTPS://EXAMPLE.COM")
            == "https://example.com"
        )

    def test_find_citation_contexts(self):
        """Test finding citation contexts in markdown files."""
        # Create a temporary directory with test markdown files
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create test markdown file
            test_md = tmpdir_path / "test.md"
            test_md.write_text("""# Test Document

This is a test with a citation to [Smith et al. (2023)](https://example.com/paper1).

Another paragraph with [Jones (2022)](https://example.com/paper2) citation.

And here's the same paper again: [Smith and colleagues (2023)](https://example.com/paper1).
""")

            # Create finder with temp directory
            finder = CitationContextFinder(search_dirs=[str(tmpdir_path)])

            # Find contexts for paper1
            contexts = finder.find_citation_contexts(
                "https://example.com/paper1"
            )

            assert len(contexts) == 2
            assert contexts[0].citation_text == "Smith et al. (2023)"
            assert contexts[0].line_number == 3
            assert contexts[1].citation_text == "Smith and colleagues (2023)"
            assert contexts[1].line_number == 7

    def test_find_all_citation_contexts(self):
        """Test finding contexts for multiple URLs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create test markdown file
            test_md = tmpdir_path / "test.md"
            test_md.write_text("""# Test Document

Citation to [Paper A](https://example.com/a).
Citation to [Paper B](https://example.com/b).
Another [Paper A](https://example.com/a) reference.
""")

            finder = CitationContextFinder(search_dirs=[str(tmpdir_path)])

            # Find contexts for multiple URLs
            urls = [
                "https://example.com/a",
                "https://example.com/b",
                "https://example.com/c",
            ]
            all_contexts = finder.find_all_citation_contexts(urls)

            assert len(all_contexts["https://example.com/a"]) == 2
            assert len(all_contexts["https://example.com/b"]) == 1
            assert len(all_contexts["https://example.com/c"]) == 0

    def test_context_extraction(self):
        """Test context extraction with character limits."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            test_md = tmpdir_path / "test.md"
            # Create a long line to test context truncation
            long_text = "A" * 150
            test_md.write_text(f"{long_text}[Citation]({long_text}){long_text}")

            finder = CitationContextFinder(search_dirs=[str(tmpdir_path)])
            contexts = finder.find_citation_contexts(
                long_text, context_chars=50
            )

            assert len(contexts) == 1
            ctx = contexts[0]

            # Check that context is truncated
            assert ctx.text_before.startswith("...")
            assert ctx.text_after.endswith("...")
            assert len(ctx.text_before) <= 53  # 50 chars + "..."
            assert len(ctx.text_after) <= 53  # 50 chars + "..."

    def test_find_markdown_files(self):
        """Test finding markdown files in directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create nested structure with markdown files
            (tmpdir_path / "dir1").mkdir()
            (tmpdir_path / "dir1" / "file1.md").touch()
            (tmpdir_path / "dir1" / "file2.txt").touch()  # Not markdown
            (tmpdir_path / "dir2").mkdir()
            (tmpdir_path / "dir2" / "file3.md").touch()
            (tmpdir_path / "root.md").touch()

            finder = CitationContextFinder(search_dirs=[str(tmpdir_path)])
            md_files = finder.find_markdown_files()

            # Filter to only files in our temp directory
            test_md_files = [f for f in md_files if str(tmpdir_path) in str(f)]

            # Should find 3 markdown files in our temp directory
            assert len(test_md_files) == 3
            md_names = {f.name for f in test_md_files}
            assert md_names == {"file1.md", "file3.md", "root.md"}

    def test_format_context_display(self):
        """Test formatting context for display."""
        ctx = CitationContext(
            file_path="/path/to/document.md",
            line_number=10,
            text_before="Before text ",
            citation_text="Citation",
            text_after=" after text",
            full_line="Full line content",
        )

        finder = CitationContextFinder()
        display = finder.format_context_display(ctx)

        assert "document.md" in display
        assert "line 10" in display
        assert "Before text [Citation]( after text)" in display
