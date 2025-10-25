"""Tests for LaTeX post-processing module."""

from src.converters.md_to_latex.post_processing import LatexPostProcessor


class TestLatexPostProcessor:
    """Test LaTeX post-processing functionality."""

    def test_fix_passthrough_commands(self):
        """Test fixing passthrough commands."""
        processor = LatexPostProcessor()

        # Test basic passthrough fix
        content = r"\passthrough{\lstinline!some code!}"
        result = processor._fix_passthrough_commands(content)
        assert result == r"\texttt{some code}"

        # Test multiple passthrough commands
        content = r"""
        \passthrough{\lstinline!first code!} and
        \passthrough{\lstinline!second code!}
        """
        result = processor._fix_passthrough_commands(content)
        assert r"\texttt{first code}" in result
        assert r"\texttt{second code}" in result
        assert r"\passthrough" not in result

    def test_fix_table_alignment_issues(self):
        """Test fixing table alignment issues."""
        processor = LatexPostProcessor()

        # Test table with extra columns
        content = r"""
        \begin{tabular}{ll}
        \toprule
        Col1 & Col2 \\
        \midrule
        A & B & C & D \\
        E & F \\
        \bottomrule
        \end{tabular}
        """
        result = processor._fix_table_alignment_issues(content)
        # The row with 4 cells should be fixed to have only 2
        assert "A & B & C & D" not in result
        assert "E & F" in result  # This row should remain unchanged

    def test_fix_strut_commands(self):
        """Test fixing strut commands."""
        processor = LatexPostProcessor()

        content = r"""
        Some text \strut \\
        More text \strut &
        """
        result = processor._fix_strut_commands(content)
        assert r"\strut \\" not in result
        assert r"\strut &" not in result

    def test_fix_empty_captions(self):
        """Test fixing empty captions."""
        processor = LatexPostProcessor()

        # Test empty caption
        content = r"\caption{}"
        result = processor._fix_empty_captions(content)
        assert result == r"\caption{~}"

        # Test caption with only label
        content = r"\caption{\label{fig:test}}"
        result = processor._fix_empty_captions(content)
        assert result == r"\caption{~\label{fig:test}}"

    def test_fix_nested_emphasis(self):
        """Test fixing nested emphasis."""
        processor = LatexPostProcessor()

        content = r"\emph{\emph{nested text}}"
        result = processor._fix_nested_emphasis(content)
        assert result == r"\emph{nested text}"

    def test_fix_href_in_tables(self):
        """Test fixing long hrefs in tables."""
        processor = LatexPostProcessor()

        long_url = "https://www.example.com/very/long/path/that/causes/overfull/hbox/issues"
        content = f"""
        \\begin{{tabular}}{{ll}}
        Title & \\href{{{long_url}}}{{{long_url}}} \\\\
        \\end{{tabular}}
        """
        result = processor._fix_href_in_tables(content)
        # The display text should be shortened
        assert "..." in result
        # But the actual URL should remain intact
        assert f"\\href{{{long_url}}}" in result

    def test_process_file(self, tmp_path):
        """Test processing a complete file."""
        processor = LatexPostProcessor()

        # Create a test file with various issues
        test_file = tmp_path / "test.tex"
        content = r"""
        \documentclass{article}
        \begin{document}

        \passthrough{\lstinline!inline code!}

        \begin{tabular}{ll}
        A & B & C \\
        D & E \\
        \end{tabular}

        \caption{}

        \emph{\emph{nested}}

        \end{document}
        """
        test_file.write_text(content)

        # Process the file
        processor.process_file(test_file)

        # Check that fixes were applied
        result = test_file.read_text()
        assert r"\texttt{inline code}" in result
        assert r"\passthrough" not in result
        assert r"\caption{~}" in result
        assert len(processor.fixes_applied) > 0
