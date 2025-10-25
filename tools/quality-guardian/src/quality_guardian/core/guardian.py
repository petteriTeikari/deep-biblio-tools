"""Core quality checking functionality."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..analyzers.readability_analyzer import ReadabilityAnalyzer
from ..analyzers.structure_analyzer import StructureAnalyzer
from ..checkers.consistency_checker import ConsistencyChecker
from ..checkers.grammar_checker import GrammarChecker
from ..checkers.style_checker import StyleChecker
from .report import QualityReport


class QualityGuardian:
    """Main quality checking class."""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or {}

        # Initialize checkers
        self.grammar_checker = GrammarChecker(config)
        self.style_checker = StyleChecker(config)
        self.consistency_checker = ConsistencyChecker(config)

        # Initialize analyzers
        self.readability_analyzer = ReadabilityAnalyzer(config)
        self.structure_analyzer = StructureAnalyzer(config)

    def check_document(
        self, file_path: Path, style_guide: str | None = None
    ) -> QualityReport:
        """Run all quality checks on a document."""
        # Read document
        content = file_path.read_text(encoding="utf-8")

        # Create report
        report = QualityReport(file_path=str(file_path))

        # Run grammar check
        grammar_issues = self.grammar_checker.check(content)
        report.add_issues("grammar", grammar_issues)

        # Run style check
        style_issues = self.style_checker.check(
            content, style_guide=style_guide
        )
        report.add_issues("style", style_issues)

        # Run consistency check
        consistency_issues = self.consistency_checker.check(content)
        report.add_issues("consistency", consistency_issues)

        # Run readability analysis
        readability_metrics = self.readability_analyzer.analyze(content)
        report.add_metrics("readability", readability_metrics)

        # Run structure analysis
        structure_metrics = self.structure_analyzer.analyze(content)
        report.add_metrics("structure", structure_metrics)

        # Calculate scores
        report.calculate_scores()

        return report

    def analyze_document(
        self,
        file_path: Path,
        focus: str = "all",
        progress_callback: Callable | None = None,
    ) -> QualityReport:
        """Perform detailed analysis of document."""
        content = file_path.read_text(encoding="utf-8")
        report = QualityReport(file_path=str(file_path))

        analyses = {
            "grammar": lambda: self.grammar_checker.detailed_check(content),
            "style": lambda: self.style_checker.detailed_check(content),
            "readability": lambda: self.readability_analyzer.detailed_analyze(
                content
            ),
            "consistency": lambda: self.consistency_checker.detailed_check(
                content
            ),
            "structure": lambda: self.structure_analyzer.detailed_analyze(
                content
            ),
        }

        if focus == "all":
            for name, analyzer in analyses.items():
                result = analyzer()
                report.add_detailed_analysis(name, result)
                if progress_callback:
                    progress_callback()
        else:
            if focus in analyses:
                result = analyses[focus]()
                report.add_detailed_analysis(focus, result)

        report.calculate_scores()
        return report

    def apply_fixes(self, file_path: Path, report: QualityReport) -> str:
        """Apply automatic fixes to document."""
        content = file_path.read_text(encoding="utf-8")

        # Apply grammar fixes
        if "grammar" in report.issues:
            content = self.grammar_checker.apply_fixes(
                content, report.issues["grammar"]
            )

        # Apply style fixes
        if "style" in report.issues:
            content = self.style_checker.apply_fixes(
                content, report.issues["style"]
            )

        # Apply consistency fixes
        if "consistency" in report.issues:
            content = self.consistency_checker.apply_fixes(
                content, report.issues["consistency"]
            )

        report.fixes_applied = sum(
            len(issues) for issues in report.issues.values()
        )

        return content

    def apply_fixes_interactive(
        self, file_path: Path, report: QualityReport, console
    ) -> str:
        """Apply fixes interactively with user approval."""
        content = file_path.read_text(encoding="utf-8")
        fixes_applied = 0

        # Group all issues
        all_issues = []
        for category, issues in report.issues.items():
            for issue in issues:
                issue["category"] = category
                all_issues.append(issue)

        # Sort by position in document
        all_issues.sort(key=lambda x: x.get("position", 0))

        # Apply fixes interactively
        for issue in all_issues:
            console.print(f"\n[yellow]Issue:[/yellow] {issue['description']}")
            console.print(f"[dim]Category: {issue['category']}[/dim]")

            if "suggestion" in issue:
                console.print(
                    f"[green]Suggestion:[/green] {issue['suggestion']}"
                )

                response = console.input("Apply this fix? (y/n/q): ").lower()
                if response == "y":
                    content = self._apply_single_fix(content, issue)
                    fixes_applied += 1
                elif response == "q":
                    break

        report.fixes_applied = fixes_applied
        return content

    def _apply_single_fix(self, content: str, issue: dict[str, Any]) -> str:
        """Apply a single fix to content."""
        if "replacement" in issue:
            # Simple replacement
            return content.replace(issue["original"], issue["replacement"])
        elif "position" in issue and "suggestion" in issue:
            # Position-based replacement
            # Implementation would depend on specific issue format
            pass

        return content

    def generate_suggestions(
        self, file_path: Path, use_ai: bool = False, focus: str | None = None
    ) -> list[dict[str, Any]]:
        """Generate improvement suggestions."""
        content = file_path.read_text(encoding="utf-8")
        suggestions = []

        # Style suggestions
        style_suggestions = self.style_checker.generate_suggestions(
            content, focus
        )
        suggestions.extend(style_suggestions)

        # Readability suggestions
        readability_suggestions = (
            self.readability_analyzer.generate_suggestions(content)
        )
        suggestions.extend(readability_suggestions)

        # Structure suggestions
        structure_suggestions = self.structure_analyzer.generate_suggestions(
            content
        )
        suggestions.extend(structure_suggestions)

        if use_ai:
            # Would integrate with AI service for advanced suggestions
            pass

        # Sort by priority
        suggestions.sort(key=lambda x: x.get("priority", 0), reverse=True)

        return suggestions

    def filter_issues(
        self, report: QualityReport, types: list[str]
    ) -> QualityReport:
        """Filter report to only include specified issue types."""
        filtered_report = QualityReport(file_path=report.file_path)

        for issue_type in types:
            if issue_type in report.issues:
                filtered_report.issues[issue_type] = report.issues[issue_type]

        filtered_report.calculate_scores()
        return filtered_report
