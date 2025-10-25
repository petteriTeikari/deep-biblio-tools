"""Markdown to LaTeX converter."""

import re
from pathlib import Path
from typing import Any


class MarkdownToLatexConverter:
    """Convert Markdown to LaTeX with citation preservation."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}

    def convert(
        self,
        input_path: Path,
        output_path: Path,
        template: str | None = None,
        citation_style: str = "author-year",
        bibliography: Path | None = None,
    ) -> None:
        """Convert markdown file to LaTeX."""
        # Read markdown content
        content = input_path.read_text(encoding="utf-8")

        # Extract metadata
        metadata = self._extract_metadata(content)

        # Convert content
        latex_body = self._convert_content(content)

        # Build complete document
        latex_doc = self._build_document(
            latex_body,
            metadata,
            template=template,
            citation_style=citation_style,
            bibliography=bibliography,
        )

        # Write output
        output_path.write_text(latex_doc, encoding="utf-8")

    def _extract_metadata(self, content: str) -> dict[str, Any]:
        """Extract metadata from markdown."""
        metadata = {}

        # Extract title (first # heading)
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match:
            metadata["title"] = title_match.group(1)

        # Extract author if in frontmatter
        if content.startswith("---"):
            frontmatter_end = content.find("---", 3)
            if frontmatter_end > 0:
                frontmatter = content[3:frontmatter_end]
                # Simple YAML parsing
                for line in frontmatter.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        metadata[key.strip()] = value.strip()

        return metadata

    def _convert_content(self, content: str) -> str:
        """Convert markdown content to LaTeX."""
        latex = content

        # Convert headings
        latex = re.sub(
            r"^######\s+(.+)$", r"\\subparagraph{\1}", latex, flags=re.MULTILINE
        )
        latex = re.sub(
            r"^#####\s+(.+)$", r"\\paragraph{\1}", latex, flags=re.MULTILINE
        )
        latex = re.sub(
            r"^####\s+(.+)$", r"\\subsubsection{\1}", latex, flags=re.MULTILINE
        )
        latex = re.sub(
            r"^###\s+(.+)$", r"\\subsection{\1}", latex, flags=re.MULTILINE
        )
        latex = re.sub(
            r"^##\s+(.+)$", r"\\section{\1}", latex, flags=re.MULTILINE
        )
        latex = re.sub(r"^#\s+(.+)$", r"\\title{\1}", latex, flags=re.MULTILINE)

        # Convert emphasis
        latex = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", latex)
        latex = re.sub(r"\*(.+?)\*", r"\\textit{\1}", latex)
        latex = re.sub(r"`(.+?)`", r"\\texttt{\1}", latex)

        # Convert lists
        latex = self._convert_lists(latex)

        # Convert links and citations
        latex = self._convert_links_and_citations(latex)

        # Convert code blocks
        latex = self._convert_code_blocks(latex)

        # Escape special characters
        latex = self._escape_latex(latex)

        return latex

    def _convert_lists(self, text: str) -> str:
        """Convert markdown lists to LaTeX."""
        lines = text.split("\n")
        result = []
        in_list = False
        list_stack = []

        for line in lines:
            # Check for unordered list
            if re.match(r"^\s*[-*+]\s+", line):
                if not in_list:
                    result.append("\\begin{itemize}")
                    in_list = True
                    list_stack.append("itemize")

                item_text = re.sub(r"^\s*[-*+]\s+", "", line)
                result.append(f"\\item {item_text}")

            # Check for ordered list
            elif re.match(r"^\s*\d+\.\s+", line):
                if not in_list or list_stack[-1] != "enumerate":
                    result.append("\\begin{enumerate}")
                    in_list = True
                    list_stack.append("enumerate")

                item_text = re.sub(r"^\s*\d+\.\s+", "", line)
                result.append(f"\\item {item_text}")

            else:
                # End lists if needed
                while list_stack:
                    list_type = list_stack.pop()
                    result.append(f"\\end{{{list_type}}}")
                in_list = False
                result.append(line)

        # Close any remaining lists
        while list_stack:
            list_type = list_stack.pop()
            result.append(f"\\end{{{list_type}}}")

        return "\n".join(result)

    def _convert_links_and_citations(self, text: str) -> str:
        """Convert markdown links and citations to LaTeX."""

        # Convert citations [Author, Year](url) to \cite{AuthorYear}
        def citation_replace(match):
            text = match.group(1)
            url = match.group(2)

            # Extract author and year
            author_year_match = re.search(r"([A-Za-z]+).*?(\d{4})", text)
            if author_year_match:
                author = author_year_match.group(1)
                year = author_year_match.group(2)
                cite_key = f"{author}{year}"
                return f"\\cite{{{cite_key}}}"
            else:
                # Regular link
                return f"\\href{{{url}}}{{{text}}}"

        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", citation_replace, text)

        # Convert simple citations (Author, Year) to \cite{AuthorYear}
        text = re.sub(
            r"\(([A-Za-z]+)(?:\s+et\s+al\.)?,?\s*(\d{4})\)",
            lambda m: f"\\cite{{{m.group(1)}{m.group(2)}}}",
            text,
        )

        return text

    def _convert_code_blocks(self, text: str) -> str:
        """Convert markdown code blocks to LaTeX."""
        # Fenced code blocks
        text = re.sub(
            r"```(\w*)\n(.*?)\n```",
            lambda m: f"\\begin{{lstlisting}}[language={m.group(1)}]\n{m.group(2)}\n\\end{{lstlisting}}",
            text,
            flags=re.DOTALL,
        )

        # Inline code
        text = re.sub(r"`([^`]+)`", r"\\texttt{\1}", text)

        return text

    def _escape_latex(self, text: str) -> str:
        """Escape special LaTeX characters."""
        # Skip already converted LaTeX commands
        parts = re.split(r"(\\[a-zA-Z]+(?:\{[^}]*\})*)", text)

        for i in range(len(parts)):
            if i % 2 == 0:  # Not a LaTeX command
                parts[i] = parts[i].replace("$", r"\$")
                parts[i] = parts[i].replace("%", r"\%")
                parts[i] = parts[i].replace("&", r"\&")
                parts[i] = parts[i].replace("#", r"\#")
                parts[i] = parts[i].replace("_", r"\_")
                parts[i] = parts[i].replace("^", r"\^")
                parts[i] = parts[i].replace("~", r"\~")

        return "".join(parts)

    def _build_document(
        self,
        body: str,
        metadata: dict[str, Any],
        template: str | None = None,
        citation_style: str = "author-year",
        bibliography: Path | None = None,
    ) -> str:
        """Build complete LaTeX document."""
        # Extract title from body if present
        title_match = re.search(r"\\title\{([^}]+)\}", body)
        if title_match:
            title = title_match.group(1)
            body = body.replace(title_match.group(0), "")
        else:
            title = metadata.get("title", "Untitled")

        author = metadata.get("author", "")

        # Basic document template
        doc = [
            "\\documentclass[11pt]{article}",
            "\\usepackage[utf8]{inputenc}",
            "\\usepackage[T1]{fontenc}",
            "\\usepackage{hyperref}",
            "\\usepackage{graphicx}",
            "\\usepackage{listings}",
            "\\usepackage{amsmath}",
            "\\usepackage{amssymb}",
        ]

        # Add citation package based on style
        if citation_style == "numeric":
            doc.append("\\usepackage[numbers]{natbib}")
        else:
            doc.append("\\usepackage{natbib}")

        doc.extend(
            [
                "",
                f"\\title{{{title}}}",
                f"\\author{{{author}}}" if author else "",
                "\\date{\\today}",
                "",
                "\\begin{document}",
                "",
                "\\maketitle",
                "",
                body,
                "",
            ]
        )

        # Add bibliography if specified
        if bibliography:
            bib_name = bibliography.stem
            doc.extend(
                [
                    "",
                    "\\bibliographystyle{plainnat}",
                    f"\\bibliography{{{bib_name}}}",
                ]
            )

        doc.extend(["", "\\end{document}"])

        return "\n".join(line for line in doc if line is not None)
