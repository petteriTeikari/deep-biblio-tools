"""Document analysis utilities."""

import re
from pathlib import Path
from typing import Any


class DocumentAnalyzer:
    """Analyze documents to detect format and extract information."""

    def detect_format(self, path: Path) -> str:
        """Detect document format from file."""
        # First try by extension
        ext = path.suffix.lower()

        ext_map = {
            ".md": "markdown",
            ".markdown": "markdown",
            ".tex": "latex",
            ".bib": "bibtex",
            ".html": "html",
            ".htm": "html",
            ".docx": "docx",
            ".rst": "rst",
            ".txt": "text",
        }

        if ext in ext_map:
            return ext_map[ext]

        # Try content-based detection
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            return self._detect_format_from_content(content)
        except Exception:
            return "unknown"

    def _detect_format_from_content(self, content: str) -> str:
        """Detect format from content."""
        # Check for LaTeX
        if "\\documentclass" in content or "\\begin{document}" in content:
            return "latex"

        # Check for BibTeX
        if (
            "@article{" in content
            or "@book{" in content
            or "@inproceedings{" in content
        ):
            return "bibtex"

        # Check for HTML
        if "<html" in content.lower() or "<!doctype html" in content.lower():
            return "html"

        # Check for Markdown
        if re.search(r"^#+\s", content, re.MULTILINE) or "```" in content:
            return "markdown"

        # Check for reStructuredText
        if re.search(r"^={3,}$", content, re.MULTILINE) or ".. " in content:
            return "rst"

        return "text"

    def analyze(self, path: Path) -> dict[str, Any]:
        """Analyze document and extract information."""
        info = {
            "format": self.detect_format(path),
            "size": path.stat().st_size,
            "name": path.name,
        }

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")

            # Count citations
            citation_patterns = [
                r"\[[^\]]+\]\([^)]+\)",  # Markdown links that might be citations
                r"\([\w\s,]+\d{4}\)",  # (Author, Year)
                r"\\cite\{[^}]+\}",  # LaTeX citations
                r"@[\w]+\{[\w]+,",  # BibTeX entries
            ]

            citation_count = 0
            for pattern in citation_patterns:
                citation_count += len(re.findall(pattern, content))

            info["citation_count"] = citation_count

            # Count references
            ref_section = re.search(
                r"(?:references|bibliography)", content, re.IGNORECASE
            )
            if ref_section:
                # Count items after references section
                after_ref = content[ref_section.end() :]
                # Simple heuristic: count lines starting with number or bullet
                ref_count = len(
                    re.findall(
                        r"^\s*(?:\d+\.|-|\*|\[)", after_ref, re.MULTILINE
                    )
                )
                info["reference_count"] = ref_count
            else:
                info["reference_count"] = 0

            # Extract metadata
            metadata = {}

            # Try to extract title
            title_patterns = [
                r"^#\s+(.+)$",  # Markdown
                r"\\title\{([^}]+)\}",  # LaTeX
                r"<title>([^<]+)</title>",  # HTML
            ]

            for pattern in title_patterns:
                match = re.search(
                    pattern, content, re.MULTILINE | re.IGNORECASE
                )
                if match:
                    metadata["title"] = match.group(1).strip()
                    break

            # Extract sections
            sections = []

            if info["format"] == "markdown":
                sections = re.findall(r"^#{1,6}\s+(.+)$", content, re.MULTILINE)
            elif info["format"] == "latex":
                sections = re.findall(r"\\(?:sub)*section\{([^}]+)\}", content)

            info["metadata"] = metadata
            info["sections"] = sections[:20]  # Limit to first 20

        except Exception as e:
            info["error"] = str(e)

        return info
