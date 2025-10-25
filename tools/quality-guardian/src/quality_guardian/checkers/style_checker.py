"""Style checking functionality."""

import re
from typing import Any


class StyleChecker:
    """Check for style issues."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}

    def check(
        self, content: str, style_guide: str | None = None
    ) -> list[dict[str, Any]]:
        """Check style issues."""
        issues = []

        # Check for contractions (not academic)
        contractions = {
            "don't": "do not",
            "won't": "will not",
            "can't": "cannot",
            "shouldn't": "should not",
            "wouldn't": "would not",
            "couldn't": "could not",
            "isn't": "is not",
            "aren't": "are not",
            "wasn't": "was not",
            "weren't": "were not",
            "haven't": "have not",
            "hasn't": "has not",
            "hadn't": "had not",
            "it's": "it is",
            "that's": "that is",
            "what's": "what is",
            "there's": "there is",
        }

        lines = content.split("\n")

        for i, line in enumerate(lines):
            # Check contractions
            for contraction, expansion in contractions.items():
                if contraction in line.lower():
                    issues.append(
                        {
                            "line": i + 1,
                            "description": f'Contraction "{contraction}" found (not academic style)',
                            "original": contraction,
                            "replacement": expansion,
                            "suggestion": f'Replace with "{expansion}"',
                            "priority": 2,
                        }
                    )

            # Check for first person (I, we, our)
            first_person = re.findall(
                r"\b(I|we|our|my|me)\b", line, re.IGNORECASE
            )
            if first_person and not line.startswith("#"):  # Not in headings
                issues.append(
                    {
                        "line": i + 1,
                        "description": "First person pronoun found (consider third person)",
                        "original": line,
                        "suggestion": "Consider using third person perspective",
                        "priority": 1,
                    }
                )

            # Check for informal words
            informal_words = [
                "really",
                "very",
                "quite",
                "basically",
                "actually",
                "just",
            ]
            for word in informal_words:
                if re.search(rf"\b{word}\b", line, re.IGNORECASE):
                    issues.append(
                        {
                            "line": i + 1,
                            "description": f'Informal word "{word}" found',
                            "original": word,
                            "suggestion": f'Consider removing or replacing "{word}"',
                            "priority": 1,
                        }
                    )

            # Check sentence length
            sentences = re.split(r"[.!?]+", line)
            for sentence in sentences:
                word_count = len(sentence.split())
                if word_count > 35:  # Long sentence
                    issues.append(
                        {
                            "line": i + 1,
                            "description": f"Long sentence ({word_count} words)",
                            "original": sentence.strip(),
                            "suggestion": "Consider breaking into shorter sentences",
                            "priority": 2,
                        }
                    )

        return issues

    def detailed_check(self, content: str) -> dict[str, Any]:
        """Detailed style analysis."""
        issues = self.check(content)

        # Calculate style metrics
        sentences = re.split(r"[.!?]+", content)
        sentences = [s.strip() for s in sentences if s.strip()]

        # Passive voice detection (simplified)
        passive_count = 0
        for sentence in sentences:
            if re.search(
                r"\b(was|were|been|being|is|are|am)\s+\w+ed\b", sentence
            ):
                passive_count += 1

        metrics = {
            "total_sentences": len(sentences),
            "style_issues": len(issues),
            "passive_voice_count": passive_count,
            "passive_voice_percentage": (passive_count / len(sentences) * 100)
            if sentences
            else 0,
            "avg_sentence_length": sum(len(s.split()) for s in sentences)
            / len(sentences)
            if sentences
            else 0,
        }

        return {"issues": issues, "metrics": metrics}

    def apply_fixes(self, content: str, issues: list[dict[str, Any]]) -> str:
        """Apply style fixes."""
        for issue in issues:
            if "replacement" in issue and "original" in issue:
                content = content.replace(
                    issue["original"], issue["replacement"]
                )

        return content

    def generate_suggestions(
        self, content: str, focus: str | None = None
    ) -> list[dict[str, Any]]:
        """Generate style improvement suggestions."""
        suggestions = []

        # Analyze paragraph structure
        paragraphs = content.split("\n\n")
        for i, para in enumerate(paragraphs):
            if len(para.split()) < 30 and para.strip():
                suggestions.append(
                    {
                        "type": "structure",
                        "location": f"Paragraph {i + 1}",
                        "issue": "Very short paragraph",
                        "suggestion": "Consider expanding or combining with adjacent paragraph",
                        "priority": 1,
                    }
                )

        # Check for repetitive sentence starts
        sentences = re.split(r"[.!?]+", content)
        sentence_starts = [
            s.split()[0].lower() for s in sentences if s.strip() and s.split()
        ]

        start_counts = {}
        for start in sentence_starts:
            start_counts[start] = start_counts.get(start, 0) + 1

        for word, count in start_counts.items():
            if count > 3:
                suggestions.append(
                    {
                        "type": "variety",
                        "location": "Throughout document",
                        "issue": f'Multiple sentences start with "{word}" ({count} times)',
                        "suggestion": "Vary sentence beginnings for better flow",
                        "priority": 2,
                    }
                )

        return suggestions
