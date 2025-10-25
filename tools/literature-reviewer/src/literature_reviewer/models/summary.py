"""Summary models for literature-reviewer."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Citation:
    """Represents a citation with preserved hyperlink."""

    text: str
    url: str | None = None
    authors: list[str] | None = None
    year: str | None = None

    def to_markdown(self) -> str:
        """Convert to markdown with hyperlink."""
        if self.url:
            return f"[{self.text}]({self.url})"
        return self.text


@dataclass
class Summary:
    """Represents a paper summary."""

    title: str
    authors: list[str]
    original_content: str
    summary_content: str
    citations: list[Citation] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    compression_ratio: float = 0.25
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def word_count_original(self) -> int:
        """Word count of original content."""
        return len(self.original_content.split())

    @property
    def word_count_summary(self) -> int:
        """Word count of summary."""
        return len(self.summary_content.split())

    @property
    def actual_compression(self) -> float:
        """Actual compression ratio achieved."""
        if self.word_count_original == 0:
            return 0.0
        return self.word_count_summary / self.word_count_original

    def to_markdown(self) -> str:
        """Convert summary to markdown format."""
        lines = []

        # Title
        lines.append(f"# {self.title}")
        lines.append("")

        # Authors
        if self.authors:
            lines.append(f"**Authors:** {', '.join(self.authors)}")
            lines.append("")

        # Metadata
        lines.append("**Summary Info:**")
        lines.append(f"- Original length: {self.word_count_original:,} words")
        lines.append(f"- Summary length: {self.word_count_summary:,} words")
        lines.append(f"- Compression: {self.actual_compression:.1%}")
        lines.append(
            f"- Generated: {self.created_at.strftime('%Y-%m-%d %H:%M')}"
        )
        lines.append("")

        # Summary content
        lines.append("## Summary")
        lines.append("")
        lines.append(self.summary_content)
        lines.append("")

        # References
        if self.references:
            lines.append("## References")
            lines.append("")
            for i, ref in enumerate(self.references, 1):
                lines.append(f"{i}. {ref}")
            lines.append("")

        return "\n".join(lines)

    def to_latex(self) -> str:
        """Convert summary to LaTeX format."""
        lines = [
            r"\section{" + self.title + "}",
            "",
            r"\textbf{Authors:} " + ", ".join(self.authors),
            "",
            r"\subsection{Summary}",
            "",
            self.summary_content.replace("_", r"\_").replace("&", r"\&"),
            "",
        ]

        if self.references:
            lines.extend([r"\subsection{References}", r"\begin{enumerate}"])
            for ref in self.references:
                lines.append(
                    r"\item " + ref.replace("_", r"\_").replace("&", r"\&")
                )
            lines.append(r"\end{enumerate}")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "title": self.title,
            "authors": self.authors,
            "summary_content": self.summary_content,
            "citations": [
                {"text": c.text, "url": c.url} for c in self.citations
            ],
            "references": self.references,
            "metadata": self.metadata,
            "compression_ratio": self.compression_ratio,
            "actual_compression": self.actual_compression,
            "word_count_original": self.word_count_original,
            "word_count_summary": self.word_count_summary,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class LiteratureReview:
    """Represents a comprehensive literature review."""

    theme: str
    context: str
    papers: list[Summary] = field(default_factory=list)
    synthesis: str = ""
    key_findings: list[str] = field(default_factory=list)
    research_gaps: list[str] = field(default_factory=list)
    future_directions: list[str] = field(default_factory=list)
    all_references: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def paper_count(self) -> int:
        """Number of papers in the review."""
        return len(self.papers)

    @property
    def total_citations(self) -> int:
        """Total number of unique citations."""
        unique_citations = set()
        for paper in self.papers:
            for citation in paper.citations:
                unique_citations.add(citation.text)
        return len(unique_citations)

    def to_markdown(self) -> str:
        """Convert literature review to markdown."""
        lines = []

        # Title
        lines.append(f"# Literature Review: {self.theme}")
        lines.append("")

        # Context
        lines.append("## Context")
        lines.append(self.context)
        lines.append("")

        # Summary statistics
        lines.append("## Overview")
        lines.append(f"- Papers reviewed: {self.paper_count}")
        lines.append(f"- Total citations: {self.total_citations}")
        lines.append(f"- Generated: {self.created_at.strftime('%Y-%m-%d')}")
        lines.append("")

        # Synthesis
        if self.synthesis:
            lines.append("## Synthesis")
            lines.append(self.synthesis)
            lines.append("")

        # Key findings
        if self.key_findings:
            lines.append("## Key Findings")
            for finding in self.key_findings:
                lines.append(f"- {finding}")
            lines.append("")

        # Research gaps
        if self.research_gaps:
            lines.append("## Research Gaps")
            for gap in self.research_gaps:
                lines.append(f"- {gap}")
            lines.append("")

        # Future directions
        if self.future_directions:
            lines.append("## Future Research Directions")
            for direction in self.future_directions:
                lines.append(f"- {direction}")
            lines.append("")

        # Individual paper summaries
        lines.append("## Paper Summaries")
        lines.append("")
        for i, paper in enumerate(self.papers, 1):
            lines.append(f"### {i}. {paper.title}")
            lines.append(f"**Authors:** {', '.join(paper.authors)}")
            lines.append("")
            lines.append(paper.summary_content)
            lines.append("")

        # All references
        if self.all_references:
            lines.append("## References")
            lines.append("")
            for i, ref in enumerate(self.all_references, 1):
                lines.append(f"{i}. {ref}")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "theme": self.theme,
            "context": self.context,
            "paper_count": self.paper_count,
            "total_citations": self.total_citations,
            "synthesis": self.synthesis,
            "key_findings": self.key_findings,
            "research_gaps": self.research_gaps,
            "future_directions": self.future_directions,
            "papers": [p.to_dict() for p in self.papers],
            "all_references": self.all_references,
            "created_at": self.created_at.isoformat(),
        }
