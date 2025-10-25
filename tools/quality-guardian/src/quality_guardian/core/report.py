"""Quality report generation."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class QualityReport:
    """Represents a quality check report."""

    file_path: str
    timestamp: datetime = field(default_factory=datetime.now)
    issues: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    metrics: dict[str, dict[str, Any]] = field(default_factory=dict)
    scores: dict[str, float] = field(default_factory=dict)
    overall_score: float = 0.0
    fixes_applied: int = 0

    def add_issues(self, category: str, issues: list[dict[str, Any]]):
        """Add issues to report."""
        self.issues[category] = issues

    def add_metrics(self, category: str, metrics: dict[str, Any]):
        """Add metrics to report."""
        self.metrics[category] = metrics

    def add_detailed_analysis(self, category: str, analysis: dict[str, Any]):
        """Add detailed analysis results."""
        if "issues" in analysis:
            self.issues[category] = analysis["issues"]
        if "metrics" in analysis:
            self.metrics[category] = analysis["metrics"]

    def calculate_scores(self):
        """Calculate quality scores."""
        # Grammar score
        grammar_issues = len(self.issues.get("grammar", []))
        self.scores["grammar"] = max(0, 100 - grammar_issues * 5)

        # Style score
        style_issues = len(self.issues.get("style", []))
        self.scores["style"] = max(0, 100 - style_issues * 3)

        # Readability score
        if "readability" in self.metrics:
            flesch_score = self.metrics["readability"].get(
                "flesch_reading_ease", 50
            )
            self.scores["readability"] = min(100, flesch_score * 1.5)
        else:
            self.scores["readability"] = 75

        # Consistency score
        consistency_issues = len(self.issues.get("consistency", []))
        self.scores["consistency"] = max(0, 100 - consistency_issues * 4)

        # Overall score (weighted average)
        weights = {
            "grammar": 0.3,
            "style": 0.25,
            "readability": 0.25,
            "consistency": 0.2,
        }

        total_score = 0
        total_weight = 0

        for category, weight in weights.items():
            if category in self.scores:
                total_score += self.scores[category] * weight
                total_weight += weight

        self.overall_score = (
            total_score / total_weight if total_weight > 0 else 0
        )

    @property
    def issue_counts(self) -> dict[str, int]:
        """Get issue counts by category."""
        return {
            category: len(issues) for category, issues in self.issues.items()
        }

    @property
    def total_issues(self) -> int:
        """Get total number of issues."""
        return sum(len(issues) for issues in self.issues.values())

    @property
    def top_issues(self) -> list[str]:
        """Get top issues across all categories."""
        all_issues = []
        for category, issues in self.issues.items():
            for issue in issues:
                all_issues.append(
                    f"[{category}] {issue.get('description', 'Unknown issue')}"
                )

        # Sort by priority if available
        all_issues.sort(key=lambda x: x.get("priority", 0), reverse=True)

        return all_issues[:10]

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "file_path": self.file_path,
            "timestamp": self.timestamp.isoformat(),
            "overall_score": self.overall_score,
            "scores": self.scores,
            "issue_counts": self.issue_counts,
            "total_issues": self.total_issues,
            "issues": self.issues,
            "metrics": self.metrics,
            "fixes_applied": self.fixes_applied,
        }

    def to_markdown(self) -> str:
        """Generate markdown report."""
        lines = [
            "# Quality Report",
            "",
            f"**File:** `{self.file_path}`",
            f"**Generated:** {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"## Overall Score: {self.overall_score:.0f}/100",
            "",
        ]

        # Scores by category
        lines.extend(["## Category Scores", ""])

        for category, score in self.scores.items():
            lines.append(f"- **{category.capitalize()}:** {score:.0f}/100")

        lines.append("")

        # Issues summary
        if self.total_issues > 0:
            lines.extend([f"## Issues Found ({self.total_issues} total)", ""])

            for category, issues in self.issues.items():
                if issues:
                    lines.append(
                        f"### {category.capitalize()} ({len(issues)} issues)"
                    )
                    lines.append("")

                    for issue in issues[:5]:  # Show first 5
                        lines.append(
                            f"- {issue.get('description', 'Unknown issue')}"
                        )

                    if len(issues) > 5:
                        lines.append(f"- ... and {len(issues) - 5} more")

                    lines.append("")

        # Metrics
        if self.metrics:
            lines.extend(["## Document Metrics", ""])

            for category, metrics in self.metrics.items():
                lines.append(f"### {category.capitalize()}")
                lines.append("")

                for key, value in metrics.items():
                    if isinstance(value, float):
                        lines.append(
                            f"- **{key.replace('_', ' ').title()}:** {value:.2f}"
                        )
                    else:
                        lines.append(
                            f"- **{key.replace('_', ' ').title()}:** {value}"
                        )

                lines.append("")

        return "\n".join(lines)

    def to_html(self) -> str:
        """Generate HTML report."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Quality Report - {self.file_path}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        .header {{ background: #f4f4f4; padding: 20px; border-radius: 5px; }}
        .score {{ font-size: 48px; font-weight: bold; }}
        .score.good {{ color: #27ae60; }}
        .score.fair {{ color: #f39c12; }}
        .score.poor {{ color: #e74c3c; }}
        .category {{ margin: 20px 0; padding: 15px; border-left: 4px solid #3498db; }}
        .issue {{ margin: 10px 0; padding: 10px; background: #ecf0f1; }}
        .metric {{ margin: 5px 0; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Quality Report</h1>
        <p><strong>File:</strong> {self.file_path}</p>
        <p><strong>Generated:</strong> {self.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</p>
        <div class="score {"good" if self.overall_score >= 80 else "fair" if self.overall_score >= 60 else "poor"}">
            Overall Score: {self.overall_score:.0f}/100
        </div>
    </div>
"""

        # Category scores
        html += """
    <h2>Category Scores</h2>
    <table>
        <tr>
            <th>Category</th>
            <th>Score</th>
            <th>Issues</th>
        </tr>
"""

        for category, score in self.scores.items():
            issue_count = len(self.issues.get(category, []))
            html += f"""
        <tr>
            <td>{category.capitalize()}</td>
            <td>{score:.0f}/100</td>
            <td>{issue_count}</td>
        </tr>
"""

        html += "    </table>\n"

        # Issues
        if self.total_issues > 0:
            html += f"\n    <h2>Issues Found ({self.total_issues} total)</h2>\n"

            for category, issues in self.issues.items():
                if issues:
                    html += f"""
    <div class="category">
        <h3>{category.capitalize()} ({len(issues)} issues)</h3>
"""
                    for issue in issues[:10]:
                        html += f"""
        <div class="issue">
            {issue.get("description", "Unknown issue")}
        </div>
"""
                    if len(issues) > 10:
                        html += (
                            f"        <p>... and {len(issues) - 10} more</p>\n"
                        )

                    html += "    </div>\n"

        html += """
</body>
</html>"""

        return html
