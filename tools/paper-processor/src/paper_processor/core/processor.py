"""Core paper processing functionality."""

from pathlib import Path
from typing import Any

from ..extractors.html_extractor import HTMLExtractor
from ..extractors.latex_extractor import LaTeXExtractor
from ..extractors.pdf_extractor import PDFExtractor
from ..extractors.xml_extractor import XMLExtractor
from ..models.paper import Paper
from ..utils.config import get_default_config

# Import summarization from literature-reviewer
try:
    from literature_reviewer.models.summary import Citation, Summary
    from literature_reviewer.processors.ai_summarizer import AISummarizer

    SUMMARIZATION_AVAILABLE = True
except ImportError:
    Summary = None
    Citation = None
    AISummarizer = None
    SUMMARIZATION_AVAILABLE = False


class PaperProcessor:
    """Main paper processing class."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or get_default_config()

        # Initialize extractors
        self.extractors = {
            ".html": HTMLExtractor(config),
            ".htm": HTMLExtractor(config),
            ".pdf": PDFExtractor(config),
            ".tex": LaTeXExtractor(config),
            ".xml": XMLExtractor(config),
        }

        # Initialize summarizer if available
        if SUMMARIZATION_AVAILABLE:
            self.ai_summarizer = AISummarizer(config)
        else:
            self.ai_summarizer = None

    def process_file(
        self, file_path: Path, sections: list[str] | None = None
    ) -> Paper:
        """Process a paper file and extract content."""
        # Determine file type
        suffix = file_path.suffix.lower()

        if suffix not in self.extractors:
            raise ValueError(f"Unsupported file type: {suffix}")

        # Extract content using appropriate extractor
        extractor = self.extractors[suffix]
        paper = extractor.extract(file_path)

        # Filter sections if specified
        if sections:
            filtered_sections = []
            for section in paper.sections:
                if any(s.lower() in section.title.lower() for s in sections):
                    filtered_sections.append(section)
            paper.sections = filtered_sections

        # Post-process if configured
        if self.config.get("processing", {}).get("clean_text", True):
            paper = self._clean_paper(paper)

        return paper

    def _clean_paper(self, paper: Paper) -> Paper:
        """Clean and normalize paper content."""
        # Clean abstract
        if paper.abstract:
            paper.abstract = self._clean_text(paper.abstract)

        # Clean sections
        for section in paper.sections:
            section.content = self._clean_text(section.content)
            for subsection in section.subsections:
                subsection.content = self._clean_text(subsection.content)

        # Clean references
        for ref in paper.references:
            ref.text = self._clean_text(ref.text)

        return paper

    def _clean_text(self, text: str) -> str:
        """Clean text content."""
        if not text:
            return ""

        # Remove multiple spaces
        while "  " in text:
            text = text.replace("  ", " ")

        # Remove multiple newlines
        while "\n\n\n" in text:
            text = text.replace("\n\n\n", "\n\n")

        # Remove download links and similar artifacts
        if "Download:" in text:
            parts = text.split("Download:")
            cleaned_parts = []
            for i, part in enumerate(parts):
                if i == 0:
                    cleaned_parts.append(part)
                else:
                    # Find next space or punctuation after download link
                    space_idx = part.find(" ")
                    if space_idx > 0:
                        cleaned_parts.append(part[space_idx:])
            text = "".join(cleaned_parts)

        return text.strip()

    def create_summary(
        self, paper: Paper, compression_ratio: float = 0.25
    ) -> "Summary":
        """Create a summary from an extracted paper."""
        if not SUMMARIZATION_AVAILABLE:
            raise RuntimeError(
                "Summarization not available. Install literature-reviewer package."
            )

        if not self.ai_summarizer:
            raise RuntimeError("AI summarizer not initialized.")

        # Convert paper to markdown content for summarization
        content = paper.to_markdown()

        # Extract citations from paper
        citations = []
        for ref in paper.references:
            citation = Citation(
                text=ref.text, url=ref.url if hasattr(ref, "url") else None
            )
            citations.append(citation)

        # Prepare sections for AI summarizer as list of dicts
        sections_list = []

        # Add abstract with high importance
        if paper.abstract:
            sections_list.append(
                {
                    "title": "Abstract",
                    "content": paper.abstract,
                    "importance": 10,  # Highest importance
                }
            )

        # Add main sections
        for i, section in enumerate(paper.sections):
            # Determine importance based on common section names
            importance = 5  # Default
            title_lower = section.title.lower()
            if any(
                keyword in title_lower
                for keyword in [
                    "introduction",
                    "conclusion",
                    "results",
                    "abstract",
                ]
            ):
                importance = 8
            elif any(
                keyword in title_lower
                for keyword in ["methodology", "methods", "discussion"]
            ):
                importance = 7

            sections_list.append(
                {
                    "title": section.title,
                    "content": section.content,
                    "importance": importance,
                }
            )

            # Add subsections with slightly lower importance
            for subsection in section.subsections:
                sections_list.append(
                    {
                        "title": f"{section.title} - {subsection.title}",
                        "content": subsection.content,
                        "importance": importance - 1,
                    }
                )

        # Create summary using AI summarizer
        summary_content = self.ai_summarizer.create_summary(
            sections=sections_list,
            metadata={
                "title": paper.title,
                "authors": paper.authors,
                "abstract": paper.abstract,
                "word_count": paper.word_count,  # Pass word count for accurate compression
            },
            target_compression=compression_ratio,
        )

        # Create and return Summary object
        return Summary(
            title=paper.title or "Untitled",
            authors=paper.authors or [],
            original_content=content,
            summary_content=summary_content,
            citations=citations,
            references=[ref.text for ref in paper.references],
            compression_ratio=compression_ratio,
            metadata={
                "source": "paper-processor",
                "sections": len(paper.sections),
                "word_count": paper.word_count,
            },
        )
