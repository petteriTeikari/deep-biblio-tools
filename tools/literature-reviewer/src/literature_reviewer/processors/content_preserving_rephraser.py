"""
Content-Preserving Academic Rephraser

A new approach that focuses on preserving content quality while achieving target retention.
Instead of aggressive compression, this approach:
1. Starts with full content and selectively condenses
2. Uses importance scoring rather than random selection
3. Preserves all critical technical information
4. Maintains academic prose style
"""

import re
from dataclasses import dataclass


@dataclass
class ContentSegment:
    """Represents a segment of content with importance scoring."""

    text: str
    importance_score: float
    segment_type: str  # 'critical', 'supporting', 'redundant'
    word_count: int
    is_technical: bool = False
    contains_metrics: bool = False
    contains_citations: bool = False


class ContentPreservingRephraser:
    """Academic rephraser that preserves content quality while achieving target retention."""

    def __init__(self):
        self.critical_keywords = {
            "methodology": [
                "method",
                "approach",
                "algorithm",
                "framework",
                "system",
                "model",
                "architecture",
                "pipeline",
                "process",
                "technique",
                "protocol",
            ],
            "results": [
                "result",
                "performance",
                "accuracy",
                "precision",
                "recall",
                "f1",
                "improve",
                "achieve",
                "demonstrate",
                "show",
                "outperform",
                "exceed",
            ],
            "metrics": [
                r"\d+\.?\d*\s*%",
                r"\d+\.?\d*x\s",
                r"table\s+\d+",
                r"figure\s+\d+",
            ],
            "future_work": [
                "future",
                "limitation",
                "challenge",
                "remain",
                "opportunity",
                "potential",
                "direction",
                "next",
                "further",
                "extend",
            ],
            "contributions": [
                "contribute",
                "propose",
                "present",
                "introduce",
                "develop",
                "novel",
                "new",
                "first",
                "unique",
                "main",
            ],
        }

    def analyze_content_importance(
        self, text: str, section_title: str = ""
    ) -> list[ContentSegment]:
        """Analyze content and assign importance scores to each segment."""
        # Split into sentences
        sentences = self._split_into_sentences(text)
        segments = []

        for sent in sentences:
            segment = ContentSegment(
                text=sent,
                importance_score=0.0,
                segment_type="supporting",
                word_count=len(sent.split()),
                contains_metrics=bool(
                    re.search(r"\d+\.?\d*\s*%|\d+\.?\d*x\s", sent)
                ),
                contains_citations=bool(
                    re.search(r"\[[\d,\s]+\]|\([^)]*\d{4}[^)]*\)", sent)
                ),
            )

            # Score the segment
            segment.importance_score = self._calculate_importance_score(
                sent, section_title
            )

            # Classify segment type
            if segment.importance_score >= 0.8:
                segment.segment_type = "critical"
            elif segment.importance_score <= 0.3:
                segment.segment_type = "redundant"

            segments.append(segment)

        return segments

    def _calculate_importance_score(
        self, sentence: str, section_title: str
    ) -> float:
        """Calculate importance score for a sentence."""
        score = 0.5  # Base score
        sent_lower = sentence.lower()

        # Section-specific scoring
        if "abstract" in section_title.lower():
            score += 0.2
        elif "conclusion" in section_title.lower():
            score += 0.3
        elif (
            "future" in section_title.lower()
            or "limitation" in section_title.lower()
        ):
            score = 0.95  # Almost always preserve

        # Keyword-based scoring
        for category, keywords in self.critical_keywords.items():
            for keyword in keywords:
                if isinstance(keyword, str) and keyword in sent_lower:
                    score += 0.15
                elif isinstance(keyword, str) and re.search(keyword, sentence):
                    score += 0.2

        # Technical content scoring
        if re.search(r"\d+\.?\d*\s*%", sentence):  # Percentages
            score += 0.3
        if re.search(r"[A-Z]{2,}", sentence):  # Acronyms
            score += 0.1
        if len(re.findall(r"\[[\d,\s]+\]", sentence)) > 2:  # Multiple citations
            score += 0.15

        # First and last sentence bonus
        if sentence == sentence:  # Placeholder for position check
            score += 0.1

        return min(score, 1.0)

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences while preserving abbreviations."""
        # Handle common abbreviations
        text = re.sub(r"(?<!\w)e\.g\.", "e.g.", text)
        text = re.sub(r"(?<!\w)i\.e\.", "i.e.", text)
        text = re.sub(r"(?<!\w)et al\.", "et al.", text)

        # Split on sentence boundaries
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)

        # Clean and filter
        sentences = [
            s.strip() for s in sentences if s.strip() and len(s.split()) > 3
        ]

        return sentences

    def preserve_and_condense(
        self, segments: list[ContentSegment], target_word_count: int
    ) -> str:
        """Preserve content while achieving target word count."""
        # Sort by importance
        sorted_segments = sorted(
            segments, key=lambda x: x.importance_score, reverse=True
        )

        # Always include critical segments
        selected_segments = []
        current_word_count = 0

        # First pass: Add all critical segments
        for segment in sorted_segments:
            if segment.segment_type == "critical":
                selected_segments.append(segment)
                current_word_count += segment.word_count

        # Second pass: Add supporting segments until target
        for segment in sorted_segments:
            if segment.segment_type == "supporting":
                if current_word_count + segment.word_count <= target_word_count:
                    selected_segments.append(segment)
                    current_word_count += segment.word_count

        # Sort selected segments back to original order
        selected_segments.sort(key=lambda x: segments.index(x))

        # Reconstruct text
        return self._reconstruct_text(selected_segments)

    def _reconstruct_text(self, segments: list[ContentSegment]) -> str:
        """Reconstruct text from segments maintaining flow."""
        if not segments:
            return ""

        # Group consecutive segments
        paragraphs = []
        current_para = []

        for i, segment in enumerate(segments):
            current_para.append(segment.text)

            # Start new paragraph after 3-5 sentences or at natural breaks
            if len(current_para) >= 3 and (
                i == len(segments) - 1 or segments[i].importance_score < 0.5
            ):
                paragraphs.append(" ".join(current_para))
                current_para = []

        if current_para:
            paragraphs.append(" ".join(current_para))

        return "\n\n".join(paragraphs)

    def rephrase_academic_content(
        self,
        content: str,
        section_title: str,
        preservation_ratio: float,
        references: list[str] = None,
    ) -> str:
        """Main method to rephrase academic content."""
        if not content.strip():
            return ""

        # Analyze content importance
        segments = self.analyze_content_importance(content, section_title)

        # Calculate target word count
        original_words = sum(s.word_count for s in segments)
        target_words = int(original_words * preservation_ratio)

        # Special handling for critical sections
        if any(
            keyword in section_title.lower()
            for keyword in ["future", "limitation", "conclusion"]
        ):
            # For critical sections, ensure minimum 90% preservation
            target_words = max(target_words, int(original_words * 0.9))

        # Preserve and condense
        rephrased = self.preserve_and_condense(segments, target_words)

        # Apply citation conversion if references provided
        if references and rephrased:
            rephrased = self._convert_citations(rephrased, references)

        return rephrased

    def _convert_citations(self, text: str, references: list[str]) -> str:
        """Convert citations to hyperlinked format."""
        # Build citation mapping
        ref_mapping = {}

        for i, ref in enumerate(references, 1):
            # Extract author and year
            year_match = re.search(r"\b(19[0-9]{2}|20[0-2][0-9])\b", ref)
            year = year_match.group() if year_match else ""

            # Extract first author
            author_match = re.match(r"^[^,]+", ref.strip())
            if author_match:
                author = author_match.group().strip()
                # Check for et al.
                if " et al" in ref:
                    author += " et al."

                ref_mapping[str(i)] = (
                    f"({author}, {year})" if year else f"({author})"
                )

        # Convert numbered citations
        def replace_citation(match):
            nums = match.group(1).split(",")
            links = []
            for num in nums:
                num = num.strip()
                if num in ref_mapping:
                    author_year = ref_mapping[num]
                    links.append(f"[{author_year}](#ref{num})")
            return " ".join(links) if links else match.group(0)

        text = re.sub(r"\[([0-9, ]+)\]", replace_citation, text)

        return text
