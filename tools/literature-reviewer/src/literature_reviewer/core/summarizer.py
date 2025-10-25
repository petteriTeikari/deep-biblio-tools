"""Core summarization functionality."""

import re
from pathlib import Path
from typing import Any

from ..models.summary import Citation, Summary
from ..processors.ai_summarizer import AISummarizer
from ..processors.content_processor import ContentProcessor
from ..utils.config import get_default_config


class Summarizer:
    """Main summarization class."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or get_default_config()
        self.content_processor = ContentProcessor(config)
        self.ai_summarizer = AISummarizer(config)

    def summarize_file(
        self,
        file_path: Path,
        compression_ratio: float = 0.25,
        section_based: bool = False,
    ) -> Summary:
        """Summarize a single paper file."""
        # Read content
        content = file_path.read_text(encoding="utf-8")

        # Extract metadata
        metadata = self.content_processor.extract_metadata(content)

        # Extract citations and references
        citations, references = (
            self.content_processor.extract_citations_and_references(content)
        )

        # Parse sections
        sections = self.content_processor.parse_sections(content)

        # Create summary content
        summary_content = self.ai_summarizer.create_summary(
            sections=sections,
            metadata=metadata,
            target_compression=compression_ratio,
            section_based=section_based,
        )

        # Create Summary object
        summary = Summary(
            title=metadata.get("title", "Untitled"),
            authors=metadata.get("authors", []),
            original_content=content,
            summary_content=summary_content,
            citations=[
                Citation(text=text, url=url) for text, url in citations.items()
            ],
            references=references,
            metadata=metadata,
            compression_ratio=compression_ratio,
        )

        return summary

    def analyze_summary(self, content: str) -> dict[str, Any]:
        """Analyze a summary for quality metrics."""
        lines = content.split("\n")
        sentences = [
            s.strip() for s in re.split(r"[.!?]+", content) if s.strip()
        ]

        # Basic metrics
        word_count = len(content.split())
        sentence_count = len(sentences)
        avg_sentence_length = (
            word_count / sentence_count if sentence_count > 0 else 0
        )

        # Count citations (look for year patterns)
        citation_pattern = r"\b(19|20)\d{2}\b"
        citations = re.findall(citation_pattern, content)
        citation_count = len(citations)

        # Count references
        reference_count = 0
        in_references = False
        for line in lines:
            if line.strip().lower() in [
                "references",
                "## references",
                "### references",
            ]:
                in_references = True
                continue
            if (
                in_references
                and line.strip()
                and (
                    line.strip()[0].isdigit()
                    or line.strip().startswith("-")
                    or line.strip().startswith("•")
                )
            ):
                reference_count += 1

        # Extract key topics (simple frequency analysis)
        words = content.lower().split()
        word_freq = {}
        stopwords = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "as",
            "is",
            "was",
            "are",
            "were",
            "been",
            "be",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "can",
            "this",
            "that",
            "these",
            "those",
            "it",
            "its",
            "they",
            "their",
            "them",
        }

        for word in words:
            word = word.strip('.,!?;:"')
            if len(word) > 4 and word not in stopwords:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Get top topics
        key_topics = sorted(
            word_freq.items(), key=lambda x: x[1], reverse=True
        )[:20]
        key_topics = [word for word, _ in key_topics]

        return {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_sentence_length": avg_sentence_length,
            "citation_count": citation_count,
            "reference_count": reference_count,
            "key_topics": key_topics,
        }
