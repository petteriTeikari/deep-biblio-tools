"""Readability analysis functionality."""

import re
from typing import Any


class ReadabilityAnalyzer:
    """Analyze document readability."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}

    def analyze(self, content: str) -> dict[str, Any]:
        """Analyze readability metrics."""
        # Basic text statistics
        sentences = self._split_sentences(content)
        words = content.split()
        syllables = sum(self._count_syllables(word) for word in words)

        # Calculate metrics
        metrics = {
            "word_count": len(words),
            "sentence_count": len(sentences),
            "syllable_count": syllables,
            "avg_sentence_length": len(words) / len(sentences)
            if sentences
            else 0,
            "avg_syllables_per_word": syllables / len(words) if words else 0,
        }

        # Flesch Reading Ease
        if len(sentences) > 0 and len(words) > 0:
            metrics["flesch_reading_ease"] = (
                206.835
                - 1.015 * (len(words) / len(sentences))
                - 84.6 * (syllables / len(words))
            )
        else:
            metrics["flesch_reading_ease"] = 0

        # Flesch-Kincaid Grade Level
        if len(sentences) > 0 and len(words) > 0:
            metrics["flesch_kincaid_grade"] = (
                0.39 * (len(words) / len(sentences))
                + 11.8 * (syllables / len(words))
                - 15.59
            )
        else:
            metrics["flesch_kincaid_grade"] = 0

        return metrics

    def detailed_analyze(self, content: str) -> dict[str, Any]:
        """Detailed readability analysis."""
        basic_metrics = self.analyze(content)

        # Additional analysis
        sentences = self._split_sentences(content)
        paragraphs = content.split("\n\n")

        # Sentence complexity
        complex_sentences = 0
        very_long_sentences = 0

        for sentence in sentences:
            word_count = len(sentence.split())
            if word_count > 25:
                complex_sentences += 1
            if word_count > 40:
                very_long_sentences += 1

        # Paragraph analysis
        paragraph_lengths = [len(p.split()) for p in paragraphs if p.strip()]

        detailed_metrics = {
            **basic_metrics,
            "paragraph_count": len(paragraphs),
            "avg_paragraph_length": sum(paragraph_lengths)
            / len(paragraph_lengths)
            if paragraph_lengths
            else 0,
            "complex_sentence_count": complex_sentences,
            "complex_sentence_percentage": (
                complex_sentences / len(sentences) * 100
            )
            if sentences
            else 0,
            "very_long_sentence_count": very_long_sentences,
        }

        return {
            "metrics": detailed_metrics,
            "issues": self._identify_readability_issues(detailed_metrics),
        }

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r"[.!?]+", text)
        return [
            s.strip() for s in sentences if s.strip() and len(s.strip()) > 10
        ]

    def _count_syllables(self, word: str) -> int:
        """Count syllables in a word (simplified)."""
        word = word.lower()
        vowels = "aeiou"
        syllable_count = 0
        previous_was_vowel = False

        for char in word:
            is_vowel = char in vowels
            if is_vowel and not previous_was_vowel:
                syllable_count += 1
            previous_was_vowel = is_vowel

        # Adjust for silent e
        if word.endswith("e"):
            syllable_count -= 1

        # Ensure at least one syllable
        return max(1, syllable_count)

    def _identify_readability_issues(
        self, metrics: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Identify readability issues based on metrics."""
        issues = []

        # Check Flesch Reading Ease
        fre = metrics.get("flesch_reading_ease", 50)
        if fre < 30:
            issues.append(
                {
                    "description": f"Very difficult to read (Flesch score: {fre:.1f})",
                    "suggestion": "Simplify sentences and use shorter words",
                    "priority": 3,
                }
            )
        elif fre < 50:
            issues.append(
                {
                    "description": f"Difficult to read (Flesch score: {fre:.1f})",
                    "suggestion": "Consider simplifying complex sentences",
                    "priority": 2,
                }
            )

        # Check sentence length
        avg_sentence_length = metrics.get("avg_sentence_length", 0)
        if avg_sentence_length > 25:
            issues.append(
                {
                    "description": f"Long average sentence length ({avg_sentence_length:.1f} words)",
                    "suggestion": "Break long sentences into shorter ones",
                    "priority": 2,
                }
            )

        # Check very long sentences
        very_long = metrics.get("very_long_sentence_count", 0)
        if very_long > 0:
            issues.append(
                {
                    "description": f"{very_long} very long sentences (40+ words)",
                    "suggestion": "Break these sentences into multiple shorter sentences",
                    "priority": 3,
                }
            )

        return issues

    def generate_suggestions(self, content: str) -> list[dict[str, Any]]:
        """Generate readability improvement suggestions."""
        metrics = self.detailed_analyze(content)["metrics"]
        suggestions = []

        # Suggest based on grade level
        grade_level = metrics.get("flesch_kincaid_grade", 12)
        if grade_level > 16:
            suggestions.append(
                {
                    "type": "readability",
                    "location": "Throughout document",
                    "issue": f"Very high reading level (grade {grade_level:.1f})",
                    "suggestion": "Use simpler vocabulary and shorter sentences for broader accessibility",
                    "priority": 3,
                }
            )
        elif grade_level > 14:
            suggestions.append(
                {
                    "type": "readability",
                    "location": "Throughout document",
                    "issue": f"High reading level (grade {grade_level:.1f})",
                    "suggestion": "Consider your target audience - simplify if needed",
                    "priority": 2,
                }
            )

        # Suggest paragraph improvements
        avg_para_length = metrics.get("avg_paragraph_length", 0)
        if avg_para_length > 150:
            suggestions.append(
                {
                    "type": "structure",
                    "location": "Paragraphs",
                    "issue": f"Long paragraphs (average {avg_para_length:.0f} words)",
                    "suggestion": "Break long paragraphs into smaller, focused paragraphs",
                    "priority": 2,
                }
            )

        return suggestions
