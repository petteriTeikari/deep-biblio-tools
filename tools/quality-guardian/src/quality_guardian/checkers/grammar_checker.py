"""Grammar checking functionality."""

import re
from typing import Any


class GrammarChecker:
    """Check for grammar issues."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}

    def check(self, content: str) -> list[dict[str, Any]]:
        """Basic grammar check."""
        issues = []

        # Check for common grammar issues
        lines = content.split("\n")

        for i, line in enumerate(lines):
            # Double spaces
            if "  " in line:
                issues.append(
                    {
                        "line": i + 1,
                        "description": "Double space found",
                        "original": line,
                        "suggestion": "Remove extra spaces",
                        "priority": 1,
                    }
                )

            # Missing period at end of sentence
            if line.strip() and line.strip()[-1] not in ".!?:":
                # Check if it's not a heading
                if not line.startswith("#") and len(line.strip()) > 20:
                    issues.append(
                        {
                            "line": i + 1,
                            "description": "Missing punctuation at end of sentence",
                            "original": line,
                            "suggestion": "Add period at end",
                            "priority": 2,
                        }
                    )

            # Common typos
            typos = {
                "teh": "the",
                "adn": "and",
                "taht": "that",
                "wiht": "with",
                "recieve": "receive",
                "occured": "occurred",
            }

            for typo, correction in typos.items():
                if typo in line.lower():
                    issues.append(
                        {
                            "line": i + 1,
                            "description": f'Possible typo: "{typo}"',
                            "original": typo,
                            "replacement": correction,
                            "suggestion": f'Change "{typo}" to "{correction}"',
                            "priority": 3,
                        }
                    )

        return issues

    def detailed_check(self, content: str) -> dict[str, Any]:
        """Detailed grammar analysis."""
        issues = self.check(content)

        # Additional metrics
        sentences = re.split(r"[.!?]+", content)
        sentences = [s.strip() for s in sentences if s.strip()]

        metrics = {
            "total_sentences": len(sentences),
            "grammar_issues": len(issues),
            "sentences_with_issues": len(set(i["line"] for i in issues)),
        }

        return {"issues": issues, "metrics": metrics}

    def apply_fixes(self, content: str, issues: list[dict[str, Any]]) -> str:
        """Apply grammar fixes."""
        lines = content.split("\n")

        for issue in issues:
            if "replacement" in issue and "original" in issue:
                # Apply replacement
                line_num = issue.get("line", 0) - 1
                if 0 <= line_num < len(lines):
                    lines[line_num] = lines[line_num].replace(
                        issue["original"], issue["replacement"]
                    )

        return "\n".join(lines)
