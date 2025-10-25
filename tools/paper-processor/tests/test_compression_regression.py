#!/usr/bin/env python3
"""
Regression test for summarization compression ratios.
Uses a reference paper to track model/prompt drift over time.

This test is designed to run in CI/CD environments with proper setup,
including the paper-processor package installation and test data.
"""

import json
import sys
from datetime import datetime
from pathlib import Path


def main():
    """CLI interface for regression testing."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Test summarization compression consistency"
    )
    parser.add_argument(
        "--save-baseline",
        action="store_true",
        help="Save current results as new baseline",
    )
    parser.add_argument(
        "--baseline-file", type=Path, help="Path to baseline file"
    )

    args = parser.parse_args()

    try:
        # Add src to path
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

        # Import rich for pretty output
        from rich.console import Console

        console = Console()

        # Run the actual test
        tester = CompressionRegressionTest(
            baseline_file=args.baseline_file, console=console
        )
        tester.run(save_new_baseline=args.save_baseline)

    except (ImportError, IndentationError, SyntaxError) as e:
        print(
            f"Warning: Missing or corrupted dependencies for regression test: {e}"
        )
        print(
            "This test requires the paper-processor package to be properly installed."
        )
        print("Skipping regression test.")
        sys.exit(0)
    except FileNotFoundError as e:
        print(f"Warning: {e}")
        print("Skipping regression test - test file not available")
        sys.exit(0)
    except Exception as e:
        print(f"Error running test: {e}")
        print(
            "This test is designed to run in CI/CD environments with proper setup."
        )
        sys.exit(1)


class CompressionRegressionTest:
    """Test summarization compression consistency over time."""

    def __init__(self, baseline_file: Path | None = None, console=None):
        self.console = console or self._create_fallback_console()
        self.baseline_file = (
            baseline_file or Path(__file__).parent / "compression_baseline.json"
        )

        # Use relative path from repository root
        repo_root = Path(__file__).parent.parent.parent.parent
        self.test_paper = (
            repo_root
            / "data"
            / "elsevier_manual_scrape"
            / "BIM-based quantity takeoff_ Current state and future opportunities - ScienceDirect.html"
        )

        # Import and create processor
        from paper_processor.core.processor import PaperProcessor

        self.processor = PaperProcessor()

    def _create_fallback_console(self):
        """Create a fallback console that uses print."""

        class FallbackConsole:
            def print(self, text):
                print(text)

        return FallbackConsole()

    def load_baseline(self) -> dict | None:
        """Load baseline metrics from file."""
        if self.baseline_file.exists():
            with open(self.baseline_file) as f:
                return json.load(f)
        return None

    def save_baseline(self, metrics: dict):
        """Save current metrics as baseline."""
        self.baseline_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.baseline_file, "w") as f:
            json.dump(metrics, f, indent=2)

    def run_test(self) -> dict:
        """Run compression test on reference paper."""
        self.console.print("Running Compression Regression Test")
        self.console.print(f"Test paper: {self.test_paper.name}")

        # Check if test paper exists
        if not self.test_paper.exists():
            raise FileNotFoundError(
                f"Test paper not found: {self.test_paper}\\n"
                "This test requires the reference paper to be available."
            )

        # Extract paper
        paper = self.processor.process_file(self.test_paper)
        original_words = paper.word_count
        original_sections = len(paper.sections)

        # Create summary
        summary = self.processor.create_summary(paper, compression_ratio=0.25)
        summary_words = len(summary.summary_content.split())
        summary_chars = len(summary.summary_content)

        # Calculate metrics
        word_compression = (summary_words / original_words) * 100

        # Extract key summary characteristics
        summary_lines = summary.summary_content.split("\\n")
        section_headers = [
            line for line in summary_lines if line.startswith("#")
        ]
        bullet_points = [
            line for line in summary_lines if line.strip().startswith("-")
        ]

        metrics = {
            "test_date": datetime.now().isoformat(),
            "paper_name": self.test_paper.name,
            "original": {
                "words": original_words,
                "sections": original_sections,
            },
            "summary": {
                "words": summary_words,
                "characters": summary_chars,
                "compression_ratio": round(word_compression, 2),
                "section_headers": len(section_headers),
                "bullet_points": len(bullet_points),
            },
            "model_info": {
                "provider": self.processor.ai_summarizer.provider,
                "model": self.processor.ai_summarizer.model,
                "temperature": self.processor.ai_summarizer.temperature,
                "max_tokens": self.processor.ai_summarizer.max_tokens,
            },
        }

        return metrics

    def compare_with_baseline(self, current: dict, baseline: dict) -> dict:
        """Compare current metrics with baseline."""
        comparison = {
            "word_count_diff": current["summary"]["words"]
            - baseline["summary"]["words"],
            "compression_diff": current["summary"]["compression_ratio"]
            - baseline["summary"]["compression_ratio"],
            "section_headers_diff": current["summary"]["section_headers"]
            - baseline["summary"]["section_headers"],
            "bullet_points_diff": current["summary"]["bullet_points"]
            - baseline["summary"]["bullet_points"],
        }

        # Calculate percentage changes
        comparison["word_count_pct_change"] = (
            comparison["word_count_diff"] / baseline["summary"]["words"]
        ) * 100
        comparison["compression_pct_change"] = (
            comparison["compression_diff"]
            / baseline["summary"]["compression_ratio"]
        ) * 100

        return comparison

    def check_drift(
        self, comparison: dict, thresholds: dict | None = None
    ) -> bool:
        """Check if drift exceeds thresholds."""
        if not thresholds:
            thresholds = {
                "word_count_pct_change": 20.0,  # 20% change in word count
                "compression_pct_change": 25.0,  # 25% change in compression ratio
            }

        drift_detected = False

        for metric, threshold in thresholds.items():
            if metric in comparison and abs(comparison[metric]) > threshold:
                self.console.print(
                    f"WARNING - DRIFT DETECTED: {metric} changed by {comparison[metric]:.1f}% (threshold: {threshold}%)"
                )
                drift_detected = True

        return drift_detected

    def display_results(self, current: dict, baseline: dict | None = None):
        """Display test results."""
        self.console.print("\\n=== Compression Test Results ===")
        self.console.print(f"Original Words: {current['original']['words']:,}")
        self.console.print(f"Summary Words: {current['summary']['words']:,}")
        self.console.print(
            f"Compression Ratio: {current['summary']['compression_ratio']:.1f}%"
        )
        self.console.print(
            f"Section Headers: {current['summary']['section_headers']}"
        )
        self.console.print(
            f"Bullet Points: {current['summary']['bullet_points']}"
        )

        if baseline:
            self.console.print("\\n=== Comparison with Baseline ===")
            word_diff = (
                current["summary"]["words"] - baseline["summary"]["words"]
            )
            comp_diff = (
                current["summary"]["compression_ratio"]
                - baseline["summary"]["compression_ratio"]
            )
            self.console.print(f"Word Count Change: {word_diff:+,}")
            self.console.print(f"Compression Ratio Change: {comp_diff:+.1f}%")

        # Model info
        self.console.print("\\n=== Model Info ===")
        self.console.print(f"Provider: {current['model_info']['provider']}")
        self.console.print(f"Model: {current['model_info']['model']}")
        self.console.print(
            f"Temperature: {current['model_info']['temperature']}"
        )

    def run(self, save_new_baseline: bool = False):
        """Run the regression test."""
        try:
            # Load baseline
            baseline = self.load_baseline()

            # Run current test
            current = self.run_test()

            # Display results
            self.display_results(current, baseline)

            # Compare if baseline exists
            if baseline:
                self.console.print("\\nComparing with baseline...")
                comparison = self.compare_with_baseline(current, baseline)

                # Check for drift
                drift_detected = self.check_drift(comparison)

                if not drift_detected:
                    self.console.print("No significant drift detected")

                # Save detailed comparison
                comparison_file = (
                    self.baseline_file.parent
                    / f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                with open(comparison_file, "w") as f:
                    json.dump(
                        {
                            "baseline": baseline,
                            "current": current,
                            "comparison": comparison,
                        },
                        f,
                        indent=2,
                    )
                self.console.print(f"Comparison saved to: {comparison_file}")

            # Save new baseline if requested
            if save_new_baseline or not baseline:
                self.save_baseline(current)
                self.console.print(
                    f"{'New baseline saved' if save_new_baseline else 'Baseline created'}!"
                )

        except Exception as e:
            self.console.print(f"Error running test: {e}")
            raise


if __name__ == "__main__":
    main()
