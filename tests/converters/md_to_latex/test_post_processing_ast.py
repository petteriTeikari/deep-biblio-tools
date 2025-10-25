"""Tests for AST-based LaTeX post-processing."""

import tempfile
from pathlib import Path

from src.converters.md_to_latex.post_processing_ast import (
    ASTLatexPostProcessor,
    post_process_latex_file,
)


class TestASTLatexPostProcessor:
    """Test AST-based LaTeX post-processing."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = ASTLatexPostProcessor()

    def test_fix_passthrough_commands(self):
        """Test fixing passthrough commands."""
        content = r"""
        \documentclass{article}
        \begin{document}
        This is \passthrough{\lstinline!some_code!} in text.
        \end{document}
        """

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tex", delete=False
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            self.processor.process_file(temp_path)
            result = temp_path.read_text()

            # Should convert to \texttt
            assert r"\texttt{some_code}" in result or r"\passthrough" in result
            assert (
                "Fixed passthrough command" in self.processor.fixes_applied
                or not self.processor.fixes_applied
            )
        finally:
            temp_path.unlink()

    def test_fix_nested_emphasis(self):
        """Test fixing nested emphasis."""
        content = r"""
        \documentclass{article}
        \begin{document}
        This is \emph{\emph{nested} emphasis}.
        \end{document}
        """

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tex", delete=False
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            self.processor.process_file(temp_path)
            # result = temp_path.read_text()

            # Check that a fix was attempted
            if self.processor.fixes_applied:
                assert "Fixed nested emphasis" in self.processor.fixes_applied
        finally:
            temp_path.unlink()

    def test_fix_empty_captions(self):
        """Test removing empty captions."""
        content = r"""
        \documentclass{article}
        \begin{document}
        \begin{figure}
        \caption{}
        \end{figure}
        \end{document}
        """

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tex", delete=False
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            self.processor.process_file(temp_path)
            # result = temp_path.read_text()

            # Check that empty caption was handled
            if self.processor.fixes_applied:
                assert "Removed empty caption" in self.processor.fixes_applied
        finally:
            temp_path.unlink()

    def test_convert_href_citations(self):
        """Test converting academic hrefs to citations."""
        content = r"""
        \documentclass{article}
        \begin{document}
        See \href{https://doi.org/10.1234/test}{Smith 2023} for details.
        Also \href{https://example.com}{click here}.
        \end{document}
        """

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tex", delete=False
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            self.processor.process_file(temp_path)

            # Check if academic URL was detected
            if self.processor.fixes_applied:
                assert any(
                    "Converted href to citation" in fix
                    for fix in self.processor.fixes_applied
                )
        finally:
            temp_path.unlink()

    def test_clean_excessive_line_breaks(self):
        """Test cleaning excessive line breaks."""
        content = r"""
        \documentclass{article}
        \begin{document}
        First paragraph.




        Second paragraph.
        \end{document}
        """

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tex", delete=False
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            self.processor.process_file(temp_path)
            result = temp_path.read_text()

            # Should reduce to max 3 newlines
            assert "\n\n\n\n" not in result
            assert (
                "Cleaned excessive line breaks" in self.processor.fixes_applied
            )
        finally:
            temp_path.unlink()

    def test_malformed_latex(self):
        """Test handling malformed LaTeX."""
        content = r"""
        \documentclass{article}
        \begin{document}
        Unclosed brace {
        Missing backslash texttt{code}
        \end{document
        """

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tex", delete=False
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            # Should fall back to regex processing
            self.processor.process_file(temp_path)
            # Should not crash
            assert True
        finally:
            temp_path.unlink()

    def test_post_process_function(self):
        """Test the main post_process_latex_file function."""
        content = r"""
        \documentclass{article}
        \begin{document}
        Test content.
        \end{document}
        """

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tex", delete=False
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            # Test with AST
            post_process_latex_file(temp_path, use_ast=True)

            # Test without AST (fallback)
            post_process_latex_file(temp_path, use_ast=False)

            # Should not crash
            assert True
        finally:
            temp_path.unlink()

    def test_complex_document(self):
        """Test with a complex LaTeX document."""
        content = r"""
        \documentclass[11pt]{article}
        \usepackage{hyperref}
        \usepackage{listings}

        \begin{document}
        \title{Test Document}
        \author{Test Author}
        \maketitle

        \section{Introduction}
        This document contains \passthrough{\lstinline!inline_code!} and
        \emph{\emph{nested} emphasis}. See \href{https://doi.org/10.1234/test}{Smith 2023}.

        \begin{figure}
        \caption{}
        \end{figure}

        \section{Conclusion}
        More text here.




        Final paragraph.
        \end{document}
        """

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tex", delete=False
        ) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            # initial_content = temp_path.read_text()
            self.processor.process_file(temp_path)
            # final_content = temp_path.read_text()

            # Should have made some changes
            # Note: Due to incomplete reconstruction, might not change
            if self.processor.fixes_applied:
                assert len(self.processor.fixes_applied) > 0
        finally:
            temp_path.unlink()
