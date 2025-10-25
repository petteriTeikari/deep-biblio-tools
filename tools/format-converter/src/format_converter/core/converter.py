"""Core format conversion functionality."""

from pathlib import Path
from typing import Any

from ..converters.bibtex_handler import BibtexHandler
from ..converters.latex_to_markdown import LatexToMarkdownConverter
from ..converters.markdown_to_latex import MarkdownToLatexConverter
from ..converters.pandoc_converter import PandocConverter
from ..utils.document_analyzer import DocumentAnalyzer


class FormatConverter:
    """Main format conversion class."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}

        # Initialize converters
        self.converters = {
            ("markdown", "latex"): MarkdownToLatexConverter(config),
            ("latex", "markdown"): LatexToMarkdownConverter(config),
        }

        # Pandoc for other conversions
        self.pandoc = PandocConverter(config)
        self.bibtex_handler = BibtexHandler(config)
        self.analyzer = DocumentAnalyzer()

    def convert_file(
        self,
        input_path: Path,
        output_path: Path,
        to_format: str,
        template: str | None = None,
        citation_style: str = "author-year",
        bibliography: Path | None = None,
    ) -> None:
        """Convert a file from one format to another."""
        # Detect input format
        from_format = self.analyzer.detect_format(input_path)

        # Check if we have a direct converter
        converter_key = (from_format, to_format)

        if converter_key in self.converters:
            # Use specialized converter
            converter = self.converters[converter_key]
            converter.convert(
                input_path,
                output_path,
                template=template,
                citation_style=citation_style,
                bibliography=bibliography,
            )
        else:
            # Use pandoc for general conversions
            self.pandoc.convert(
                input_path,
                output_path,
                from_format=from_format,
                to_format=to_format,
                citation_style=citation_style,
                bibliography=bibliography,
            )

    def extract_bibliography(self, input_path: Path) -> list[dict[str, Any]]:
        """Extract bibliography from a document."""
        format = self.analyzer.detect_format(input_path)

        if format == "bibtex":
            # Already a bibliography file
            return self.bibtex_handler.parse_bibtex(input_path)

        # Extract references based on format
        if format == "markdown":
            return self._extract_markdown_references(input_path)
        elif format == "latex":
            return self._extract_latex_references(input_path)
        else:
            # Try pandoc extraction
            return self.pandoc.extract_references(input_path)

    def format_bibliography(
        self, references: list[dict[str, Any]], format: str = "bibtex"
    ) -> str:
        """Format references as bibliography."""
        if format in ["bibtex", "biblatex"]:
            return self.bibtex_handler.format_bibtex(references)
        else:
            raise ValueError(f"Unsupported bibliography format: {format}")

    def analyze_document(self, input_path: Path) -> dict[str, Any]:
        """Analyze document and return information."""
        return self.analyzer.analyze(input_path)

    def _extract_markdown_references(self, path: Path) -> list[dict[str, Any]]:
        """Extract references from markdown."""
        content = path.read_text(encoding="utf-8")
        references = []

        # Look for reference section
        lines = content.split("\n")
        in_references = False

        for line in lines:
            if line.strip().lower() in [
                "references",
                "## references",
                "### references",
            ]:
                in_references = True
                continue

            if in_references and line.strip():
                # Parse reference line
                ref = self._parse_reference_line(line)
                if ref:
                    references.append(ref)

        return references

    def _extract_latex_references(self, path: Path) -> list[dict[str, Any]]:
        """Extract references from LaTeX."""
        content = path.read_text(encoding="utf-8")
        references = []

        # Look for bibliography entries
        import re

        # Pattern for bibitem
        bibitem_pattern = r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}(.*?)(?=\\bibitem|\\end\{thebibliography\})"

        for match in re.finditer(bibitem_pattern, content, re.DOTALL):
            key = match.group(1)
            text = match.group(2).strip()

            ref = self._parse_reference_line(text)
            if ref:
                ref["key"] = key
                references.append(ref)

        # Also check for \bibliography command
        bib_match = re.search(r"\\bibliography\{([^}]+)\}", content)
        if bib_match:
            bib_files = bib_match.group(1).split(",")
            for bib_file in bib_files:
                bib_path = path.parent / f"{bib_file.strip()}.bib"
                if bib_path.exists():
                    references.extend(
                        self.bibtex_handler.parse_bibtex(bib_path)
                    )

        return references

    def _parse_reference_line(self, line: str) -> dict[str, Any] | None:
        """Parse a reference line into structured data."""
        # Remove leading numbers/bullets
        import re

        line = re.sub(r"^[\d\.\-\•\[\]]+\s*", "", line.strip())

        if not line:
            return None

        ref = {"raw": line}

        # Try to extract components
        # Pattern: Author(s) (Year). Title. Journal/Publisher.

        # Extract year
        year_match = re.search(r"\((\d{4})\)", line)
        if year_match:
            ref["year"] = year_match.group(1)

            # Author is typically before year
            author_end = line.find("(")
            if author_end > 0:
                ref["author"] = line[:author_end].strip().rstrip(",.")

        # Extract DOI if present
        doi_match = re.search(r"10\.\d{4,}/[^\s]+", line)
        if doi_match:
            ref["doi"] = doi_match.group(0)

        # Extract title (typically after year, before journal)
        if year_match:
            after_year = line[year_match.end() :].strip()
            # Title often ends with a period before journal
            title_match = re.match(r"([^.]+)\.", after_year)
            if title_match:
                ref["title"] = title_match.group(1).strip()

        return ref
