"""Paper models for paper-processor."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Reference:
    """Represents a reference in a paper."""

    key: str
    text: str
    authors: list[str] | None = None
    title: str | None = None
    year: str | None = None
    journal: str | None = None
    doi: str | None = None
    url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "text": self.text,
            "authors": self.authors,
            "title": self.title,
            "year": self.year,
            "journal": self.journal,
            "doi": self.doi,
            "url": self.url,
        }


@dataclass
class Section:
    """Represents a section in a paper."""

    title: str
    content: str
    level: int = 1
    subsections: list["Section"] = field(default_factory=list)

    @property
    def word_count(self) -> int:
        """Count words in section including subsections."""
        count = len(self.content.split())
        for subsection in self.subsections:
            count += subsection.word_count
        return count

    def to_markdown(self, base_level: int = 1) -> str:
        """Convert section to markdown."""
        lines = []

        # Add heading
        heading_level = base_level + self.level - 1
        lines.append(f"{'#' * heading_level} {self.title}")
        lines.append("")

        # Add content
        if self.content:
            lines.append(self.content)
            lines.append("")

        # Add subsections
        for subsection in self.subsections:
            lines.append(subsection.to_markdown(base_level))

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "content": self.content,
            "level": self.level,
            "word_count": self.word_count,
            "subsections": [s.to_dict() for s in self.subsections],
        }


@dataclass
class Paper:
    """Represents an academic paper."""

    title: str | None = None
    authors: list[str] = field(default_factory=list)
    abstract: str | None = None
    keywords: list[str] = field(default_factory=list)
    doi: str | None = None
    journal: str | None = None
    year: str | None = None
    volume: str | None = None
    pages: str | None = None
    sections: list[Section] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    source_path: str | None = None
    extracted_at: datetime = field(default_factory=datetime.now)

    @property
    def word_count(self) -> int:
        """Total word count of the paper."""
        count = 0
        if self.abstract:
            count += len(self.abstract.split())
        for section in self.sections:
            count += section.word_count
        return count

    def get_section(self, title: str) -> Section | None:
        """Get section by title."""
        for section in self.sections:
            if section.title.lower() == title.lower():
                return section
            # Check subsections
            for subsection in section.subsections:
                if subsection.title.lower() == title.lower():
                    return subsection
        return None

    def to_markdown(self) -> str:
        """Convert paper to markdown format."""
        lines = []

        # Title
        if self.title:
            lines.append(f"# {self.title}")
            lines.append("")

        # Authors
        if self.authors:
            lines.append(f"**Authors:** {', '.join(self.authors)}")
            lines.append("")

        # Publication info
        pub_info = []
        if self.journal:
            pub_info.append(self.journal)
        if self.year:
            pub_info.append(self.year)
        if self.volume:
            pub_info.append(f"Vol. {self.volume}")
        if self.pages:
            pub_info.append(f"pp. {self.pages}")

        if pub_info:
            lines.append(f"**Published in:** {', '.join(pub_info)}")
            lines.append("")

        # DOI
        if self.doi:
            lines.append(f"**DOI:** [{self.doi}](https://doi.org/{self.doi})")
            lines.append("")

        # Keywords
        if self.keywords:
            lines.append(f"**Keywords:** {', '.join(self.keywords)}")
            lines.append("")

        # Abstract
        if self.abstract:
            lines.append("## Abstract")
            lines.append("")
            lines.append(self.abstract)
            lines.append("")

        # Main content
        for section in self.sections:
            lines.append(section.to_markdown(base_level=2))

        # References
        if self.references:
            lines.append("## References")
            lines.append("")
            for i, ref in enumerate(self.references, 1):
                lines.append(f"{i}. {ref.text}")
            lines.append("")

        return "\n".join(lines)

    def to_text(self) -> str:
        """Convert paper to plain text."""
        lines = []

        if self.title:
            lines.append(self.title)
            lines.append("=" * len(self.title))
            lines.append("")

        if self.authors:
            lines.append(f"Authors: {', '.join(self.authors)}")
            lines.append("")

        if self.abstract:
            lines.append("ABSTRACT")
            lines.append(self.abstract)
            lines.append("")

        # Sections
        for section in self.sections:
            lines.append(section.title.upper())
            lines.append(section.content)
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "keywords": self.keywords,
            "doi": self.doi,
            "journal": self.journal,
            "year": self.year,
            "volume": self.volume,
            "pages": self.pages,
            "sections": [s.to_dict() for s in self.sections],
            "references": [r.to_dict() for r in self.references],
            "metadata": self.metadata,
            "source_path": self.source_path,
            "extracted_at": self.extracted_at.isoformat(),
            "word_count": self.word_count,
        }

    def to_latex(self) -> str:
        """Convert paper to LaTeX format."""
        lines = [
            r"\documentclass{article}",
            r"\usepackage[utf8]{inputenc}",
            r"\usepackage{hyperref}",
            "",
            r"\begin{document}",
            "",
        ]

        if self.title:
            lines.append(r"\title{" + self.title + "}")

        if self.authors:
            lines.append(r"\author{" + r" \and ".join(self.authors) + "}")

        lines.extend([r"\date{}", r"\maketitle", ""])

        if self.abstract:
            lines.extend(
                [r"\begin{abstract}", self.abstract, r"\end{abstract}", ""]
            )

        # Sections
        for section in self.sections:
            lines.append(r"\section{" + section.title + "}")
            lines.append(section.content)
            lines.append("")

        # References
        if self.references:
            lines.extend([r"\begin{thebibliography}{99}", ""])
            for ref in self.references:
                lines.append(r"\bibitem{" + ref.key + "} " + ref.text)
            lines.extend(["", r"\end{thebibliography}"])

        lines.extend(["", r"\end{document}"])

        return "\n".join(lines)
