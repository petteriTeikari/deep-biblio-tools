#!/usr/bin/env python3
"""
Monitor compression drift over time and generate reports.
"""

import json
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt


class CompressionMonitor:
    """Monitor and visualize compression drift over time."""

    def __init__(self, test_dir: Path = None):
        self.test_dir = test_dir or Path(__file__).parent / "tests"
        self.baseline_file = self.test_dir / "compression_baseline.json"

    def collect_comparisons(self) -> list[dict]:
        """Collect all comparison files."""
        comparisons = []

        for file in self.test_dir.glob("comparison_*.json"):
            with open(file) as f:
                data = json.load(f)
                comparisons.append(
                    {"timestamp": file.stem.split("_", 1)[1], "data": data}
                )

        return sorted(comparisons, key=lambda x: x["timestamp"])

    def generate_report(self) -> str:
        """Generate a markdown report of compression trends."""
        comparisons = self.collect_comparisons()

        if not comparisons:
            return "No comparison data found. Run the regression test first."

        # Load baseline
        with open(self.baseline_file) as f:
            baseline = json.load(f)

        report = f"""# Compression Drift Report

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Baseline Information
- Date: {baseline["test_date"]}
- Paper: {baseline["paper_name"]}
- Original Words: {baseline["original"]["words"]:,}
- Baseline Summary Words: {baseline["summary"]["words"]:,}
- Baseline Compression: {baseline["summary"]["compression_ratio"]:.1f}%

## Test History

| Date | Summary Words | Compression % | Word Change | Drift % |
|------|---------------|---------------|-------------|---------|
"""

        for comp in comparisons[-10:]:  # Last 10 tests
            data = comp["data"]
            current = data["current"]["summary"]
            comparison = data["comparison"]

            report += f"| {comp['timestamp'][:10]} | {current['words']:,} | {current['compression_ratio']:.1f}% | {comparison['word_count_diff']:+,} | {comparison['compression_pct_change']:+.1f}% |\n"

        # Add drift detection
        latest = comparisons[-1]["data"]["comparison"] if comparisons else None
        if latest:
            if abs(latest["compression_pct_change"]) > 25:
                report += "\n**WARNING: Significant drift detected!**\n"
            else:
                report += "\nCompression remains stable.\n"

        # Add recommendations
        report += "\n## Recommendations\n\n"
        if latest and abs(latest["compression_pct_change"]) > 15:
            report += "- Consider reviewing prompt changes\n"
            report += "- Check if model version has changed\n"
            report += "- Verify API parameters are consistent\n"
        else:
            report += "- Continue monitoring for changes\n"
            report += "- Run weekly tests to catch drift early\n"

        return report

    def plot_trends(self, output_file: Path = None):
        """Generate a plot of compression trends."""
        comparisons = self.collect_comparisons()

        if not comparisons:
            print("No comparison data to plot")
            return

        # Extract data for plotting
        dates = [
            datetime.strptime(c["timestamp"][:10], "%Y%m%d")
            for c in comparisons
        ]
        compressions = [
            c["data"]["current"]["summary"]["compression_ratio"]
            for c in comparisons
        ]
        word_counts = [
            c["data"]["current"]["summary"]["words"] for c in comparisons
        ]

        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

        # Plot compression ratio
        ax1.plot(dates, compressions, "b-o", label="Compression Ratio")
        ax1.axhline(y=10, color="g", linestyle="--", label="Target Min (10%)")
        ax1.axhline(y=25, color="r", linestyle="--", label="Target Max (25%)")
        ax1.set_ylabel("Compression Ratio (%)")
        ax1.set_title("Summarization Compression Ratio Over Time")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Plot word count
        ax2.plot(dates, word_counts, "g-o", label="Summary Words")
        ax2.set_ylabel("Word Count")
        ax2.set_xlabel("Date")
        ax2.set_title("Summary Word Count Over Time")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        if output_file:
            plt.savefig(output_file)
        else:
            plt.savefig(self.test_dir / "compression_trends.png")

        print(
            f"Plot saved to: {output_file or self.test_dir / 'compression_trends.png'}"
        )

    def alert_on_drift(self, threshold: float = 25.0) -> bool:
        """Check latest comparison and alert if drift exceeds threshold."""
        comparisons = self.collect_comparisons()

        if not comparisons:
            return False

        latest = comparisons[-1]["data"]["comparison"]

        if abs(latest["compression_pct_change"]) > threshold:
            print(
                f"ALERT: Compression drift of {latest['compression_pct_change']:.1f}% detected!"
            )
            print(
                f"   Current: {comparisons[-1]['data']['current']['summary']['compression_ratio']:.1f}%"
            )
            print(
                f"   Baseline: {comparisons[-1]['data']['baseline']['summary']['compression_ratio']:.1f}%"
            )
            return True

        return False


def main():
    """CLI for monitoring compression drift."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Monitor summarization compression drift"
    )
    parser.add_argument(
        "--report", action="store_true", help="Generate markdown report"
    )
    parser.add_argument(
        "--plot", action="store_true", help="Generate trend plots"
    )
    parser.add_argument(
        "--check", action="store_true", help="Check for drift and alert"
    )
    parser.add_argument(
        "--output", type=Path, help="Output file for report or plot"
    )

    args = parser.parse_args()

    monitor = CompressionMonitor()

    if args.report:
        report = monitor.generate_report()
        if args.output:
            args.output.write_text(report)
            print(f"Report saved to: {args.output}")
        else:
            print(report)

    if args.plot:
        # Only plot if matplotlib is available
        try:
            monitor.plot_trends(args.output)
        except ImportError:
            print("Matplotlib not installed. Run: pip install matplotlib")

    if args.check:
        drift_detected = monitor.alert_on_drift()
        exit(1 if drift_detected else 0)

    if not any([args.report, args.plot, args.check]):
        parser.print_help()


if __name__ == "__main__":
    main()
