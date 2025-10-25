"""AI-powered literature review generation."""

from typing import Any

from ..models.summary import Summary


class AIReviewer:
    """Generate literature reviews using AI."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}

    def generate_synthesis(
        self, summaries: list[Summary], theme: str, context: str
    ) -> str:
        """Generate a synthesis of multiple paper summaries."""
        # For now, implement a simple rule-based synthesis
        synthesis_parts = []

        # Introduction
        synthesis_parts.append(
            f"This literature review examines {len(summaries)} papers related to {theme}. "
            f"{context}"
        )

        # Group papers by common topics
        topic_groups = self._group_by_topics(summaries)

        # Synthesize each topic group
        for topic, papers in topic_groups.items():
            if len(papers) > 1:
                synthesis_parts.append(
                    f"\n\nSeveral studies ({len(papers)} papers) address {topic}. "
                )
                # Add key insights from each
                for paper in papers[:3]:  # Limit to avoid too long synthesis
                    key_point = self._extract_key_point(paper)
                    if key_point:
                        synthesis_parts.append(
                            f"{paper.authors[0] if paper.authors else 'Authors'} "
                            f"({paper.metadata.get('year', 'n.d.')}) {key_point}. "
                        )

        # Add conclusion
        synthesis_parts.append(
            f"\n\nOverall, the literature on {theme} reveals diverse approaches and findings, "
            "highlighting the complexity and ongoing evolution of this research area."
        )

        return "".join(synthesis_parts)

    def extract_key_findings(self, summaries: list[Summary]) -> list[str]:
        """Extract key findings from summaries."""
        findings = []

        for summary in summaries:
            # Extract sentences containing key finding indicators
            sentences = summary.summary_content.split(".")
            for sentence in sentences:
                sentence_lower = sentence.lower()
                if any(
                    indicator in sentence_lower
                    for indicator in [
                        "found that",
                        "results show",
                        "demonstrate",
                        "indicate",
                        "reveal",
                        "suggest that",
                        "concluded that",
                        "evidence that",
                    ]
                ):
                    finding = sentence.strip()
                    if (
                        finding and len(finding) > 20
                    ):  # Avoid very short fragments
                        # Add citation
                        if summary.authors:
                            finding = f"{summary.authors[0]} et al. ({summary.metadata.get('year', 'n.d.')}): {finding}"
                        findings.append(finding)

        # Deduplicate similar findings
        unique_findings = []
        for finding in findings:
            is_duplicate = False
            for existing in unique_findings:
                # Simple similarity check
                if self._similarity_ratio(finding, existing) > 0.8:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_findings.append(finding)

        return unique_findings[:10]  # Limit to top 10 findings

    def identify_research_gaps(
        self, summaries: list[Summary], theme: str
    ) -> list[str]:
        """Identify research gaps from the literature."""
        gaps = []

        # Common gap indicators
        gap_phrases = [
            "future research",
            "further investigation",
            "remains unclear",
            "limited evidence",
            "more research needed",
            "gap in",
            "understudied",
            "lacking",
            "insufficient",
        ]

        for summary in summaries:
            sentences = summary.summary_content.split(".")
            for sentence in sentences:
                sentence_lower = sentence.lower()
                if any(phrase in sentence_lower for phrase in gap_phrases):
                    gap = sentence.strip()
                    if gap and len(gap) > 20:
                        gaps.append(gap)

        # Add general gaps based on coverage analysis
        topics_covered = set()
        for summary in summaries:
            if "keywords" in summary.metadata:
                topics_covered.update(summary.metadata["keywords"])

        # Suggest general gaps
        if len(summaries) < 5:
            gaps.append(f"Limited number of studies available on {theme}")

        if not any(
            "longitudinal" in s.summary_content.lower() for s in summaries
        ):
            gaps.append(
                "Lack of longitudinal studies to assess long-term impacts"
            )

        if not any(
            "meta-analysis" in s.summary_content.lower() for s in summaries
        ):
            gaps.append(
                "Need for systematic reviews and meta-analyses to synthesize findings"
            )

        return list(set(gaps))[:8]  # Deduplicate and limit

    def suggest_future_directions(
        self, summaries: list[Summary], theme: str
    ) -> list[str]:
        """Suggest future research directions."""
        directions = []

        # Extract explicit future directions mentioned
        for summary in summaries:
            if "future" in summary.summary_content.lower():
                sentences = summary.summary_content.split(".")
                for sentence in sentences:
                    if (
                        "future" in sentence.lower()
                        or "should" in sentence.lower()
                    ):
                        direction = sentence.strip()
                        if direction and len(direction) > 20:
                            directions.append(direction)

        # Add general recommendations based on gaps
        gaps = self.identify_research_gaps(summaries, theme)
        for gap in gaps[:3]:
            if "lack of" in gap.lower():
                topic = gap.lower().split("lack of")[-1].strip()
                directions.append(f"Conduct comprehensive studies on {topic}")
            elif "limited" in gap.lower():
                topic = gap.lower().split("limited")[-1].strip()
                directions.append(f"Expand research to include {topic}")

        # Technology-related suggestions
        if not any(
            "ai" in s.summary_content.lower()
            or "artificial intelligence" in s.summary_content.lower()
            for s in summaries
        ):
            directions.append(
                f"Explore the application of AI and machine learning techniques in {theme}"
            )

        return list(set(directions))[:6]  # Deduplicate and limit

    def _group_by_topics(
        self, summaries: list[Summary]
    ) -> dict[str, list[Summary]]:
        """Group summaries by common topics."""
        topic_groups = {}

        # Simple keyword-based grouping
        for summary in summaries:
            keywords = summary.metadata.get("keywords", [])
            if not keywords:
                # Extract from title
                if summary.title:
                    keywords = [
                        w for w in summary.title.lower().split() if len(w) > 4
                    ]

            for keyword in keywords:
                if keyword not in topic_groups:
                    topic_groups[keyword] = []
                topic_groups[keyword].append(summary)

        # Filter out small groups
        return {k: v for k, v in topic_groups.items() if len(v) > 1}

    def _extract_key_point(self, summary: Summary) -> str:
        """Extract a key point from a summary."""
        # Look for the most important sentence
        sentences = summary.summary_content.split(".")

        # Prioritize sentences with results/findings
        for sentence in sentences:
            if any(
                word in sentence.lower()
                for word in ["found", "showed", "demonstrated", "revealed"]
            ):
                return sentence.strip()

        # Return first substantial sentence
        for sentence in sentences:
            if len(sentence.strip()) > 50:
                return sentence.strip()

        return ""

    def _similarity_ratio(self, text1: str, text2: str) -> float:
        """Calculate simple similarity ratio between two texts."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union)
