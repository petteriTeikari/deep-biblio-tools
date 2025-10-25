"""Pandoc-based converter for various formats."""

import json
import subprocess
from pathlib import Path
from typing import Any


class PandocConverter:
    """Use pandoc for general format conversions."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}
        self._check_pandoc()

    def _check_pandoc(self):
        """Check if pandoc is available."""
        try:
            subprocess.run(
                ["pandoc", "--version"], capture_output=True, check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "Pandoc is not installed. Please install pandoc to use this converter."
            )

    def convert(
        self,
        input_path: Path,
        output_path: Path,
        from_format: str,
        to_format: str,
        citation_style: str = "author-year",
        bibliography: Path | None = None,
    ) -> None:
        """Convert file using pandoc."""
        cmd = [
            "pandoc",
            str(input_path),
            "-f",
            self._get_pandoc_format(from_format),
            "-t",
            self._get_pandoc_format(to_format),
            "-o",
            str(output_path),
            "--standalone",
        ]

        # Add citation processing if bibliography provided
        if bibliography:
            cmd.extend(["--bibliography", str(bibliography)])

            # Set citation style
            if citation_style == "numeric":
                cmd.extend(["--csl", "ieee.csl"])
            # Default is author-year

        # Add format-specific options
        if to_format == "latex":
            cmd.extend(["--pdf-engine", "xelatex"])
        elif to_format == "html":
            cmd.extend(["--mathjax"])

        # Run conversion
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Pandoc conversion failed: {e.stderr}")

    def extract_references(self, input_path: Path) -> list[dict[str, Any]]:
        """Extract references using pandoc."""
        # Use pandoc to extract citations
        cmd = ["pandoc", str(input_path), "--to", "json"]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True
            )
            doc = json.loads(result.stdout)

            # Extract citations from AST
            references = []
            self._extract_citations_from_ast(doc, references)

            return references

        except subprocess.CalledProcessError:
            # Fallback to empty list
            return []

    def _get_pandoc_format(self, format: str) -> str:
        """Map format names to pandoc format strings."""
        format_map = {
            "markdown": "markdown",
            "latex": "latex",
            "html": "html",
            "docx": "docx",
            "rst": "rst",
            "org": "org",
            "mediawiki": "mediawiki",
            "asciidoc": "asciidoc",
        }

        return format_map.get(format, format)

    def _extract_citations_from_ast(
        self, ast: dict[str, Any], references: list[dict[str, Any]]
    ):
        """Recursively extract citations from pandoc AST."""
        if isinstance(ast, dict):
            if ast.get("t") == "Cite":
                # Extract citation info
                citations = ast.get("c", [])
                if isinstance(citations, list) and len(citations) > 0:
                    for cite in citations[
                        0
                    ]:  # First element contains citations
                        if isinstance(cite, dict):
                            ref = {
                                "key": cite.get("citationId", ""),
                                "raw": str(cite),
                            }
                            references.append(ref)

            # Recurse into children
            for value in ast.values():
                self._extract_citations_from_ast(value, references)

        elif isinstance(ast, list):
            for item in ast:
                self._extract_citations_from_ast(item, references)
