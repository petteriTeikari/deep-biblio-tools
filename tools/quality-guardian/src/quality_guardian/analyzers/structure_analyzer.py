"""Document structure analysis functionality."""

import re
from typing import Any


class StructureAnalyzer:
    """Analyze document structure."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}

    def analyze(self, content: str) -> dict[str, Any]:
        """Analyze document structure."""
        lines = content.split("\n")

        # Find sections
        sections = []

        for i, line in enumerate(lines):
            if line.startswith("#"):
                level = len(re.match(r"^#+", line).group())
                title = line.lstrip("#").strip()
                sections.append({"level": level, "title": title, "line": i + 1})

        # Analyze structure
        metrics = {
            "total_sections": len(sections),
            "max_heading_level": max((s["level"] for s in sections), default=0),
            "has_introduction": any(
                "introduction" in s["title"].lower() for s in sections
            ),
            "has_conclusion": any(
                "conclusion" in s["title"].lower() for s in sections
            ),
            "has_references": any(
                "reference" in s["title"].lower()
                or "bibliography" in s["title"].lower()
                for s in sections
            ),
        }

        # Check for abstract
        content_lower = content.lower()
        metrics["has_abstract"] = (
            "abstract" in content_lower[:1000]
        )  # Check first 1000 chars

        return metrics

    def detailed_analyze(self, content: str) -> dict[str, Any]:
        """Detailed structure analysis."""
        basic_metrics = self.analyze(content)
        lines = content.split("\n")

        # Analyze section balance
        sections = []
        current_section = None

        for i, line in enumerate(lines):
            if line.startswith("#"):
                if current_section:
                    current_section["end_line"] = i
                    current_section["content_lines"] = (
                        i - current_section["start_line"]
                    )
                    sections.append(current_section)

                level = len(re.match(r"^#+", line).group())
                title = line.lstrip("#").strip()
                current_section = {
                    "level": level,
                    "title": title,
                    "start_line": i + 1,
                    "content_lines": 0,
                }

        if current_section:
            current_section["end_line"] = len(lines)
            current_section["content_lines"] = (
                len(lines) - current_section["start_line"]
            )
            sections.append(current_section)

        # Calculate section balance
        if sections:
            section_lengths = [s["content_lines"] for s in sections]
            avg_section_length = sum(section_lengths) / len(section_lengths)

            detailed_metrics = {
                **basic_metrics,
                "sections": sections,
                "avg_section_length": avg_section_length,
                "shortest_section": min(section_lengths),
                "longest_section": max(section_lengths),
                "section_balance_ratio": min(section_lengths)
                / max(section_lengths)
                if max(section_lengths) > 0
                else 0,
            }
        else:
            detailed_metrics = basic_metrics

        return {
            "metrics": detailed_metrics,
            "issues": self._identify_structure_issues(detailed_metrics),
        }

    def _identify_structure_issues(
        self, metrics: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Identify structure issues."""
        issues = []

        # Check for missing sections
        if not metrics.get("has_abstract"):
            issues.append(
                {
                    "description": "Missing abstract",
                    "suggestion": "Add an abstract at the beginning of the document",
                    "priority": 2,
                }
            )

        if not metrics.get("has_introduction"):
            issues.append(
                {
                    "description": "Missing introduction section",
                    "suggestion": "Add an introduction section",
                    "priority": 2,
                }
            )

        if not metrics.get("has_conclusion"):
            issues.append(
                {
                    "description": "Missing conclusion section",
                    "suggestion": "Add a conclusion section",
                    "priority": 2,
                }
            )

        # Check section balance
        if (
            "section_balance_ratio" in metrics
            and metrics["section_balance_ratio"] < 0.2
        ):
            issues.append(
                {
                    "description": "Unbalanced sections (some very short, others very long)",
                    "suggestion": "Balance content across sections more evenly",
                    "priority": 1,
                }
            )

        # Check heading hierarchy
        if "sections" in metrics:
            sections = metrics["sections"]
            for i in range(1, len(sections)):
                if sections[i]["level"] > sections[i - 1]["level"] + 1:
                    issues.append(
                        {
                            "description": f"Skipped heading level at line {sections[i]['start_line']}",
                            "suggestion": "Use sequential heading levels (e.g., ## after #, not ### after #)",
                            "priority": 1,
                        }
                    )

        return issues

    def generate_suggestions(self, content: str) -> list[dict[str, Any]]:
        """Generate structure improvement suggestions."""
        analysis = self.detailed_analyze(content)
        metrics = analysis["metrics"]
        suggestions = []

        # Suggest section additions
        if not metrics.get("has_abstract"):
            suggestions.append(
                {
                    "type": "structure",
                    "location": "Beginning of document",
                    "issue": "No abstract found",
                    "suggestion": "Add a 150-250 word abstract summarizing the key points",
                    "priority": 3,
                }
            )

        # Check section length variance
        if "sections" in metrics and len(metrics["sections"]) > 3:
            sections = metrics["sections"]
            very_short = [s for s in sections if s["content_lines"] < 10]
            very_long = [s for s in sections if s["content_lines"] > 100]

            if very_short:
                suggestions.append(
                    {
                        "type": "structure",
                        "location": f"Sections: {', '.join(s['title'] for s in very_short[:3])}",
                        "issue": "Very short sections",
                        "suggestion": "Expand these sections or combine with related sections",
                        "priority": 2,
                    }
                )

            if very_long:
                suggestions.append(
                    {
                        "type": "structure",
                        "location": f"Sections: {', '.join(s['title'] for s in very_long[:3])}",
                        "issue": "Very long sections",
                        "suggestion": "Break these sections into subsections for better organization",
                        "priority": 2,
                    }
                )

        return suggestions
