"""Literature review generation functionality."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..models.summary import LiteratureReview, Summary
from ..processors.ai_reviewer import AIReviewer
from ..utils.reference_manager import ReferenceManager
from .summarizer import Summarizer


class LiteratureReviewer:
    """Creates comprehensive literature reviews from multiple papers."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}
        self.summarizer = Summarizer(config)
        self.ai_reviewer = AIReviewer(config)
        self.reference_manager = ReferenceManager()

    def create_review(
        self,
        paper_files: list[Path],
        theme: str,
        context: str,
        progress_callback: Callable | None = None,
    ) -> LiteratureReview:
        """Create a literature review from multiple papers."""

        # Process each paper
        summaries = []
        all_references = []

        for paper_file in paper_files:
            # Create summary if needed
            if paper_file.suffix == ".md" and "summary" in paper_file.name:
                # Already a summary, just parse it
                content = paper_file.read_text(encoding="utf-8")
                summary = self._parse_existing_summary(content)
            else:
                # Create new summary
                summary = self.summarizer.summarize_file(paper_file)

            summaries.append(summary)
            all_references.extend(summary.references)

            if progress_callback:
                progress_callback()

        # Deduplicate references
        unique_references = self.reference_manager.deduplicate_references(
            all_references
        )

        # Generate synthesis and analysis
        synthesis = self.ai_reviewer.generate_synthesis(
            summaries, theme, context
        )
        key_findings = self.ai_reviewer.extract_key_findings(summaries)
        research_gaps = self.ai_reviewer.identify_research_gaps(
            summaries, theme
        )
        future_directions = self.ai_reviewer.suggest_future_directions(
            summaries, theme
        )

        # Create literature review
        review = LiteratureReview(
            theme=theme,
            context=context,
            papers=summaries,
            synthesis=synthesis,
            key_findings=key_findings,
            research_gaps=research_gaps,
            future_directions=future_directions,
            all_references=unique_references,
        )

        return review

    def _parse_existing_summary(self, content: str) -> Summary:
        """Parse an existing summary file."""
        # Extract title
        title = ""
        for line in content.split("\n"):
            if line.startswith("# "):
                title = line[2:].strip()
                break

        # Extract authors
        authors = []
        for line in content.split("\n"):
            if line.startswith("**Authors:**"):
                authors_text = line.replace("**Authors:**", "").strip()
                authors = [a.strip() for a in authors_text.split(",")]
                break

        # Extract summary content
        summary_start = content.find("## Summary")
        ref_start = content.find("## References")

        if summary_start >= 0:
            if ref_start >= 0:
                summary_content = content[summary_start:ref_start].strip()
            else:
                summary_content = content[summary_start:].strip()
            # Remove the heading
            summary_content = "\n".join(summary_content.split("\n")[2:])
        else:
            summary_content = content

        # Extract references
        references = []
        if ref_start >= 0:
            ref_section = content[ref_start:]
            for line in ref_section.split("\n")[2:]:  # Skip heading
                if line.strip() and (
                    line.strip()[0].isdigit() or line.strip().startswith("-")
                ):
                    references.append(line.strip())

        return Summary(
            title=title,
            authors=authors,
            original_content=content,
            summary_content=summary_content,
            references=references,
        )
