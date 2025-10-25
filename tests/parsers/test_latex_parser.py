"""Tests for LaTeX parser."""

from src.parsers import LatexParser


class TestLatexParser:
    """Test LaTeX parser functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = LatexParser()

    def test_parse_simple_text(self):
        """Test parsing simple LaTeX text."""
        text = "Hello \\textbf{world}!"
        doc = self.parser.parse(text)

        assert doc.raw_text == text
        assert len(doc.nodes) > 0
        assert not doc.metadata.get("parse_error")

    def test_extract_citations(self):
        """Test extracting citations."""
        text = r"""
        This is a citation \cite{Smith2020}.
        Multiple citations \cite{Jones2019, Brown2021}.
        Different types \citep{Davis2018} and \citet{Wilson2022}.
        """

        citations = self.parser.extract_citations(text)

        assert len(citations) == 4
        assert citations[0]["keys"] == ["Smith2020"]
        assert citations[1]["keys"] == ["Jones2019", "Brown2021"]
        assert citations[2]["type"] == "citep"
        assert citations[3]["type"] == "citet"

    def test_extract_labels(self):
        """Test extracting labels."""
        text = r"""
        \section{Introduction}
        \label{sec:intro}

        \begin{equation}
        E = mc^2
        \label{eq:einstein}
        \end{equation}
        """

        labels = self.parser.extract_labels(text)

        assert len(labels) == 2
        assert labels[0]["label"] == "sec:intro"
        assert labels[1]["label"] == "eq:einstein"

    def test_extract_sections(self):
        """Test extracting sections."""
        text = r"""
        \section{Introduction}
        \subsection{Background}
        \subsubsection{Related Work}
        """

        sections = self.parser.extract_sections(text)

        assert len(sections) == 3
        assert sections[0]["type"] == "section"
        assert sections[0]["title"] == "Introduction"
        assert sections[1]["type"] == "subsection"
        assert sections[2]["type"] == "subsubsection"

    def test_validate_valid_latex(self):
        """Test validation of valid LaTeX."""
        text = r"\textbf{Hello} world"
        errors = self.parser.validate(text)

        assert len(errors) == 0

    def test_validate_unmatched_braces(self):
        """Test validation of unmatched braces."""
        text = r"\textbf{Hello world"
        errors = self.parser.validate(text)

        assert len(errors) > 0
        assert any("brace" in error.lower() for error in errors)

    def test_validate_unmatched_math(self):
        """Test validation of unmatched math delimiters."""
        text = r"This is $incomplete math"
        errors = self.parser.validate(text)

        assert len(errors) > 0
        assert any("math" in error.lower() for error in errors)

    def test_parse_with_comments(self):
        """Test parsing with comments."""
        text = r"""
        % This is a comment
        \section{Test} % Another comment
        """

        doc = self.parser.parse(text)
        comment_nodes = [n for n in doc.nodes if n.type == "comment"]

        assert len(comment_nodes) >= 1

    def test_parse_math_environments(self):
        """Test parsing math environments."""
        text = r"""
        Inline math $x + y$ and display math:
        \begin{equation}
        \int_0^1 f(x) dx
        \end{equation}
        """

        doc = self.parser.parse(text)

        assert doc.metadata["has_math"]
        math_nodes = [n for n in doc.nodes if n.type == "math"]
        assert len(math_nodes) > 0
