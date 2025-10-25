"""Tests for LaTeX builder."""

from src.converters.md_to_latex.latex_builder import LatexBuilder


class TestLatexBuilder:
    """Test LatexBuilder class."""

    def test_basic_builder(self):
        """Test basic LaTeX builder creation."""
        builder = LatexBuilder(
            title="Test Paper", author="John Doe", abstract="Test abstract"
        )
        assert builder.title == "Test Paper"
        assert builder.author == "John Doe"
        assert builder.abstract == "Test abstract"
        assert builder.document_class == "article"
        assert builder.arxiv_ready is True

    def test_custom_document_class(self):
        """Test custom document class."""
        builder = LatexBuilder(document_class="report")
        assert builder.document_class == "report"

    def test_build_preamble_basic(self):
        """Test basic preamble building."""
        builder = LatexBuilder(title="Test", author="Author")
        preamble = builder.build_preamble()

        assert "\\documentclass[10pt,a4paper,twocolumn]{article}" in preamble
        assert "\\usepackage[utf8]{inputenc}" in preamble
        assert "\\usepackage{hyperref}" in preamble
        assert "\\title{Test}" in preamble
        assert "\\author{Author}" in preamble
        assert "\\date{\\today}" in preamble

    def test_build_preamble_non_arxiv(self):
        """Test preamble for non-arXiv document."""
        builder = LatexBuilder(arxiv_ready=False)
        preamble = builder.build_preamble()

        assert "\\documentclass[twocolumn]{article}" in preamble
        assert "\\geometry{" not in preamble

    def test_build_preamble_single_column(self):
        """Test preamble for single-column layout."""
        builder = LatexBuilder(two_column=False)
        preamble = builder.build_preamble()

        assert "\\documentclass[10pt,a4paper]{article}" in preamble
        assert "twocolumn" not in preamble
        assert "\\usepackage{balance}" not in preamble

    def test_add_packages(self):
        """Test adding additional packages."""
        builder = LatexBuilder()
        builder.add_packages(
            ["\\usepackage{algorithm}", "\\usepackage{algorithmic}"]
        )
        preamble = builder.build_preamble()

        assert "\\usepackage{algorithm}" in preamble
        assert "\\usepackage{algorithmic}" in preamble

    def test_add_custom_commands(self):
        """Test adding custom commands."""
        builder = LatexBuilder()
        builder.add_custom_commands(
            ["\\newcommand{\\R}{\\mathbb{R}}", "\\newcommand{\\Z}{\\mathbb{Z}}"]
        )
        preamble = builder.build_preamble()

        assert "% Additional custom commands" in preamble
        assert "\\newcommand{\\R}{\\mathbb{R}}" in preamble
        assert "\\newcommand{\\Z}{\\mathbb{Z}}" in preamble

    def test_build_document(self):
        """Test building complete document."""
        builder = LatexBuilder(
            title="Test Paper",
            author="Author",
            abstract="This is the abstract.",
        )
        content = "This is the main content."
        document = builder.build_document(content)

        assert "\\begin{document}" in document
        assert "\\maketitle" in document
        assert "\\begin{abstract}" in document
        assert "This is the abstract." in document
        assert "\\end{abstract}" in document
        assert "This is the main content." in document
        assert "\\printbibliography" in document
        assert "\\end{document}" in document

    def test_build_document_no_title(self):
        """Test building document without title."""
        builder = LatexBuilder()
        content = "Content only."
        document = builder.build_document(content)

        assert "\\maketitle" not in document
        assert "\\begin{abstract}" not in document
        assert "Content only." in document

    def test_process_pandoc_output(self):
        """Test processing pandoc output."""
        builder = LatexBuilder()
        pandoc_output = """\\documentclass{article}
\\usepackage{hyperref}
\\begin{document}
\\tightlist
Some content here.
\\hypertarget{sec:intro}{}
\\end{document}"""

        processed = builder.process_pandoc_output(pandoc_output)

        assert "\\documentclass" not in processed
        assert "\\begin{document}" not in processed
        assert "\\end{document}" not in processed
        assert "\\tightlist" not in processed
        assert "\\hypertarget" not in processed
        assert "Some content here." in processed

    def test_create_makefile(self, tmp_path):
        """Test Makefile creation."""
        builder = LatexBuilder()
        builder.create_makefile(tmp_path, "main.tex")

        makefile = tmp_path / "Makefile"
        assert makefile.exists()

        content = makefile.read_text()
        assert "MAIN = main" in content
        assert "LATEX = xelatex" in content
        assert "BIBTEX = biber" in content
        assert "$(LATEX) $(MAIN)" in content
        assert "$(BIBTEX) $(MAIN)" in content

    def test_create_readme(self, tmp_path):
        """Test README creation."""
        builder = LatexBuilder()
        builder.create_readme(tmp_path)

        readme = tmp_path / "README.md"
        assert readme.exists()

        content = readme.read_text()
        assert "# LaTeX Document Compilation Instructions" in content
        assert "xelatex main" in content
        assert "biber main" in content
        assert "make" in content
        assert "arXiv Submission" in content
