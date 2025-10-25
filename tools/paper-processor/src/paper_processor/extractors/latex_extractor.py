"""LaTeX paper extractor."""

import re
from pathlib import Path

from ..models.paper import Paper, Reference, Section
from .base import BaseExtractor


class LaTeXExtractor(BaseExtractor):
    """Extract content from LaTeX papers."""

    def extract(self, file_path: Path) -> Paper:
        """Extract paper content from LaTeX file."""
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            content = f.read()

        paper = Paper(source_path=str(file_path))

        # Extract metadata
        self._extract_metadata(content, paper)

        # Extract abstract
        paper.abstract = self._extract_abstract(content)

        # Extract sections
        paper.sections = self._extract_sections(content)

        # Extract references
        paper.references = self._extract_references(content)

        return paper

    def _extract_metadata(self, content: str, paper: Paper):
        """Extract metadata from LaTeX content."""
        # Title
        title_match = re.search(r"\\title\{([^}]+)\}", content)
        if title_match:
            paper.title = self._clean_latex(title_match.group(1))

        # Authors
        author_match = re.search(r"\\author\{([^}]+)\}", content)
        if author_match:
            authors_text = author_match.group(1)
            # Split by \and
            authors = authors_text.split(r"\and")
            paper.authors = [self._clean_latex(a.strip()) for a in authors]

    def _extract_abstract(self, content: str) -> str:
        """Extract abstract from LaTeX."""
        # Look for abstract environment
        abstract_match = re.search(
            r"\\begin\{abstract\}(.*?)\\end\{abstract\}", content, re.DOTALL
        )

        if abstract_match:
            return self._clean_latex(abstract_match.group(1))

        return ""

    def _extract_sections(self, content: str) -> list[Section]:
        """Extract sections from LaTeX content."""
        sections = []

        # Find all section commands
        section_pattern = r"\\(section|subsection|subsubsection)\{([^}]+)\}"
        matches = list(re.finditer(section_pattern, content))

        for i, match in enumerate(matches):
            section_type = match.group(1)
            section_title = self._clean_latex(match.group(2))

            # Determine level
            level_map = {"section": 1, "subsection": 2, "subsubsection": 3}
            level = level_map.get(section_type, 1)

            # Extract content until next section
            start_pos = match.end()
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                # Until references or end of document
                ref_match = re.search(
                    r"\\begin\{thebibliography\}", content[start_pos:]
                )
                if ref_match:
                    end_pos = start_pos + ref_match.start()
                else:
                    end_match = re.search(
                        r"\\end\{document\}", content[start_pos:]
                    )
                    if end_match:
                        end_pos = start_pos + end_match.start()
                    else:
                        end_pos = len(content)

            section_content = content[start_pos:end_pos]
            cleaned_content = self._clean_latex(section_content)

            section = Section(
                title=section_title, content=cleaned_content, level=level
            )
            sections.append(section)

        return self._organize_sections(sections)

    def _organize_sections(self, flat_sections: list[Section]) -> list[Section]:
        """Organize flat sections into hierarchy."""
        if not flat_sections:
            return []

        organized = []
        stack = []

        for section in flat_sections:
            # Find parent
            while stack and stack[-1].level >= section.level:
                stack.pop()

            if stack:
                # Add as subsection
                stack[-1].subsections.append(section)
            else:
                # Top-level section
                organized.append(section)

            stack.append(section)

        return organized

    def _extract_references(self, content: str) -> list[Reference]:
        """Extract references from LaTeX bibliography."""
        references = []

        # Look for thebibliography environment
        bib_match = re.search(
            r"\\begin\{thebibliography\}.*?(.*?)\\end\{thebibliography\}",
            content,
            re.DOTALL,
        )

        if bib_match:
            bib_content = bib_match.group(1)

            # Extract bibitem entries
            bibitem_pattern = r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}(.*?)(?=\\bibitem|\\end\{thebibliography\})"

            for match in re.finditer(bibitem_pattern, bib_content, re.DOTALL):
                key = match.group(1)
                ref_text = self._clean_latex(match.group(2))

                reference = Reference(key=key, text=ref_text)
                references.append(reference)

        # Also check for BibTeX file references
        biblio_match = re.search(r"\\bibliography\{([^}]+)\}", content)
        if biblio_match and not references:
            # Note: Would need to read external .bib file
            # Bibliography file found but not processed: biblio_match.group(1)
            pass

        return references

    def _clean_latex(self, text: str) -> str:
        """Clean LaTeX markup from text."""
        if not text:
            return ""

        # Remove comments
        text = re.sub(r"%.*?\n", " ", text)

        # Remove common LaTeX commands
        commands_to_remove = [
            r"\\textbf\{([^}]+)\}",  # Bold
            r"\\textit\{([^}]+)\}",  # Italic
            r"\\emph\{([^}]+)\}",  # Emphasis
            r"\\cite\{[^}]+\}",  # Citations (remove)
            r"\\ref\{[^}]+\}",  # References
            r"\\label\{[^}]+\}",  # Labels
        ]

        for cmd in commands_to_remove[:3]:  # Keep content for text formatting
            text = re.sub(cmd, r"\1", text)

        for cmd in commands_to_remove[3:]:  # Remove entirely
            text = re.sub(cmd, "", text)

        # Remove other backslash commands
        text = re.sub(r"\\[a-zA-Z]+", " ", text)

        # Clean up whitespace
        text = re.sub(r"\s+", " ", text)

        return text.strip()
