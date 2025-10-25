"""Consistency checking functionality."""

import re
from collections import defaultdict
from typing import Any


class ConsistencyChecker:
    """Check for consistency issues."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}

    def check(self, content: str) -> list[dict[str, Any]]:
        """Check consistency issues."""
        issues = []

        # Check spelling variations
        variations = {
            "analyze": "analyse",
            "organize": "organise",
            "recognize": "recognise",
            "behavior": "behaviour",
            "color": "colour",
            "center": "centre",
        }

        # Count occurrences of each variant

        for us_spelling, uk_spelling in variations.items():
            us_count = len(
                re.findall(rf"\b{us_spelling}\b", content, re.IGNORECASE)
            )
            uk_count = len(
                re.findall(rf"\b{uk_spelling}\b", content, re.IGNORECASE)
            )

            if us_count > 0 and uk_count > 0:
                issues.append(
                    {
                        "description": f'Mixed spelling: "{us_spelling}" ({us_count}x) and "{uk_spelling}" ({uk_count}x)',
                        "suggestion": "Use consistent spelling throughout",
                        "priority": 2,
                    }
                )

        # Check capitalization consistency
        words = re.findall(r"\b[A-Za-z]+\b", content)
        word_cases = defaultdict(list)

        for word in words:
            word_lower = word.lower()
            if word_lower not in ["i", "a", "an", "the"]:  # Skip common words
                word_cases[word_lower].append(word)

        for word_lower, cases in word_cases.items():
            unique_cases = set(cases)
            if (
                len(unique_cases) > 1 and len(cases) > 2
            ):  # Multiple casings used
                case_counts = {case: cases.count(case) for case in unique_cases}
                issues.append(
                    {
                        "description": f"Inconsistent capitalization: {', '.join(f'{case} ({count}x)' for case, count in case_counts.items())}",
                        "suggestion": f'Use consistent capitalization for "{word_lower}"',
                        "priority": 1,
                    }
                )

        # Check abbreviation consistency
        abbrev_patterns = [
            (r"\be\.g\.", r"\beg\b", "e.g."),
            (r"\bi\.e\.", r"\bie\b", "i.e."),
            (r"\betc\.", r"\betc\b", "etc."),
            (r"\bvs\.", r"\bvs\b", "vs."),
        ]

        for with_periods, without_periods, standard in abbrev_patterns:
            with_count = len(re.findall(with_periods, content))
            without_count = len(re.findall(without_periods, content))

            if with_count > 0 and without_count > 0:
                issues.append(
                    {
                        "description": f'Mixed abbreviation style: "{standard}" and without periods',
                        "suggestion": "Use consistent abbreviation style",
                        "priority": 1,
                    }
                )

        # Check citation style consistency
        # Look for different citation patterns
        author_year_paren = len(
            re.findall(r"\([A-Z][a-z]+(?:\s+et\s+al\.)?,?\s*\d{4}\)", content)
        )
        author_year_inline = len(
            re.findall(r"[A-Z][a-z]+(?:\s+et\s+al\.)?\s+\(\d{4}\)", content)
        )
        numbered = len(re.findall(r"\[\d+\]", content))

        citation_styles = []
        if author_year_paren > 2:
            citation_styles.append(("(Author, Year)", author_year_paren))
        if author_year_inline > 2:
            citation_styles.append(("Author (Year)", author_year_inline))
        if numbered > 2:
            citation_styles.append(("[1]", numbered))

        if len(citation_styles) > 1:
            issues.append(
                {
                    "description": f"Mixed citation styles: {', '.join(f'{style} ({count}x)' for style, count in citation_styles)}",
                    "suggestion": "Use consistent citation style throughout",
                    "priority": 3,
                }
            )

        return issues

    def detailed_check(self, content: str) -> dict[str, Any]:
        """Detailed consistency analysis."""
        issues = self.check(content)

        # Additional metrics
        metrics = {
            "consistency_issues": len(issues),
            "spelling_variations": sum(
                1 for i in issues if "spelling" in i["description"]
            ),
            "capitalization_issues": sum(
                1 for i in issues if "capitalization" in i["description"]
            ),
            "abbreviation_issues": sum(
                1 for i in issues if "abbreviation" in i["description"]
            ),
            "citation_style_issues": sum(
                1 for i in issues if "citation" in i["description"]
            ),
        }

        return {"issues": issues, "metrics": metrics}

    def apply_fixes(self, content: str, issues: list[dict[str, Any]]) -> str:
        """Apply consistency fixes."""
        # For consistency issues, we would need user input to decide which variant to use
        # For now, just return content unchanged
        return content
