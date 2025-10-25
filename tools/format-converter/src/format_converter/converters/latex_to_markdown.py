"""LaTeX to Markdown converter."""

import re
from pathlib import Path
from typing import Any


class LatexToMarkdownConverter:
    """Convert LaTeX to Markdown."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}

    def convert(self, input_path: Path, output_path: Path, **kwargs) -> None:
        """Convert LaTeX file to Markdown."""
        # Read LaTeX content
        content = input_path.read_text(encoding="utf-8")

        # Extract document content
        doc_content = self._extract_document_content(content)

        # Convert to markdown
        markdown = self._convert_content(doc_content)

        # Write output
        output_path.write_text(markdown, encoding="utf-8")

    def _extract_document_content(self, content: str) -> str:
        """Extract content between begin and end document."""
        begin_match = re.search(r"\\begin\{document\}", content)
        end_match = re.search(r"\\end\{document\}", content)

        if begin_match and end_match:
            return content[begin_match.end() : end_match.start()].strip()

        return content

    def _convert_content(self, content: str) -> str:
        """Convert LaTeX content to Markdown."""
        md = content

        # Convert title and author
        title_match = re.search(r"\\title\{([^}]+)\}", md)
        author_match = re.search(r"\\author\{([^}]+)\}", md)

        if title_match:
            title = title_match.group(1)
            md = md.replace(title_match.group(0), "")
            md = f"# {title}\n\n" + md

        if author_match:
            author = author_match.group(1)
            md = md.replace(author_match.group(0), "")
            # Insert after title if exists
            if title_match:
                md = md.replace(
                    f"# {title}\n\n", f"# {title}\n\n**Author:** {author}\n\n"
                )

        # Remove \maketitle
        md = re.sub(r"\\maketitle", "", md)

        # Convert sections
        md = re.sub(r"\\section\{([^}]+)\}", r"\n## \1\n", md)
        md = re.sub(r"\\subsection\{([^}]+)\}", r"\n### \1\n", md)
        md = re.sub(r"\\subsubsection\{([^}]+)\}", r"\n#### \1\n", md)
        md = re.sub(r"\\paragraph\{([^}]+)\}", r"\n##### \1\n", md)
        md = re.sub(r"\\subparagraph\{([^}]+)\}", r"\n###### \1\n", md)

        # Convert emphasis
        md = re.sub(r"\\textbf\{([^}]+)\}", r"**\1**", md)
        md = re.sub(r"\\textit\{([^}]+)\}", r"*\1*", md)
        md = re.sub(r"\\emph\{([^}]+)\}", r"*\1*", md)
        md = re.sub(r"\\texttt\{([^}]+)\}", r"`\1`", md)

        # Convert lists
        md = self._convert_lists(md)

        # Convert citations
        md = self._convert_citations(md)

        # Convert links
        md = re.sub(r"\\href\{([^}]+)\}\{([^}]+)\}", r"[\2](\1)", md)
        md = re.sub(r"\\url\{([^}]+)\}", r"<\1>", md)

        # Convert code listings
        md = self._convert_code_blocks(md)

        # Remove LaTeX comments
        md = re.sub(r"%.*$", "", md, flags=re.MULTILINE)

        # Clean up
        md = self._cleanup(md)

        return md

    def _convert_lists(self, text: str) -> str:
        """Convert LaTeX lists to Markdown."""
        # Convert itemize
        text = re.sub(r"\\begin\{itemize\}", "", text)
        text = re.sub(r"\\end\{itemize\}", "\n", text)
        text = re.sub(r"\\item\s+", "- ", text)

        # Convert enumerate
        text = re.sub(r"\\begin\{enumerate\}", "", text)
        text = re.sub(r"\\end\{enumerate\}", "\n", text)

        # Number enumerated items
        lines = text.split("\n")
        counter = 0
        result = []

        for line in lines:
            if (
                line.strip().startswith("\\item")
                and "\\begin{enumerate}" in text[: text.find(line)]
            ):
                counter += 1
                line = re.sub(r"\\item\s+", f"{counter}. ", line)
            result.append(line)

        return "\n".join(result)

    def _convert_citations(self, text: str) -> str:
        """Convert LaTeX citations to Markdown."""
        # Convert \cite{key} to (Author, Year) format
        # This is a simplification - in practice would need bibliography
        text = re.sub(r"\\cite\{([^}]+)\}", r"(\1)", text)
        text = re.sub(r"\\citep\{([^}]+)\}", r"(\1)", text)
        text = re.sub(r"\\citet\{([^}]+)\}", r"\1", text)

        return text

    def _convert_code_blocks(self, text: str) -> str:
        """Convert LaTeX code blocks to Markdown."""
        # Convert lstlisting
        text = re.sub(
            r"\\begin\{lstlisting\}(?:\[.*?\])?\n?(.*?)\n?\\end\{lstlisting\}",
            r"```\n\1\n```",
            text,
            flags=re.DOTALL,
        )

        # Convert verbatim
        text = re.sub(
            r"\\begin\{verbatim\}\n?(.*?)\n?\\end\{verbatim\}",
            r"```\n\1\n```",
            text,
            flags=re.DOTALL,
        )

        return text

    def _cleanup(self, text: str) -> str:
        """Clean up converted text."""
        # Remove extra blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove leading/trailing whitespace
        text = text.strip()

        # Unescape LaTeX special characters
        text = text.replace(r"\$", "$")
        text = text.replace(r"\%", "%")
        text = text.replace(r"\&", "&")
        text = text.replace(r"\#", "#")
        text = text.replace(r"\_", "_")
        text = text.replace(r"\^", "^")
        text = text.replace(r"\~", "~")

        return text
