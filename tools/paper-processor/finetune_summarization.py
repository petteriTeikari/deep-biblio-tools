#!/usr/bin/env python3
"""
Fine-tune summarization parameters by testing different prompt variations
and compression settings on sample papers.
"""

import json
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from paper_processor.core.processor import PaperProcessor  # noqa: E402
from rich.console import Console  # noqa: E402
from rich.table import Table  # noqa: E402

console = Console()


def analyze_existing_summaries(base_dir: Path) -> list[dict]:
    """Analyze existing good summaries to understand target compression ratios."""
    results = []

    # Known good examples from user feedback
    good_examples = [
        {
            "original": "Automated process for generating an air conditioning duct model using the CAD-to-BIM approach - ScienceDirect.md",
            "summary": "AC_duct_CAD_to_BIM_comprehensive_summary.md",
            "original_size": 169.7 * 1024,  # KB to bytes
            "summary_size": 15.6 * 1024,
            "compression_ratio": 9.2,  # ~10% which user said was good
        }
    ]

    # Also analyze any existing summaries
    extracted_dir = base_dir / "extracted"
    summaries_dir = base_dir / "summaries"

    if extracted_dir.exists() and summaries_dir.exists():
        for summary_file in summaries_dir.glob("*_summary.md"):
            # Find corresponding extracted file
            original_name = summary_file.stem.replace("_summary", "")
            extracted_file = extracted_dir / f"{original_name}.md"

            if extracted_file.exists():
                original_size = extracted_file.stat().st_size
                summary_size = summary_file.stat().st_size
                compression_ratio = (summary_size / original_size) * 100

                # Count words for more accurate comparison
                original_text = extracted_file.read_text(encoding="utf-8")
                summary_text = summary_file.read_text(encoding="utf-8")
                original_words = len(original_text.split())
                summary_words = len(summary_text.split())
                word_compression = (summary_words / original_words) * 100

                results.append(
                    {
                        "original": extracted_file.name,
                        "summary": summary_file.name,
                        "original_size": original_size,
                        "summary_size": summary_size,
                        "compression_ratio": compression_ratio,
                        "original_words": original_words,
                        "summary_words": summary_words,
                        "word_compression": word_compression,
                    }
                )

    return good_examples + results


def test_compression_variations(
    processor: PaperProcessor,
    test_file: Path,
    variations: list[
        tuple[float, float]
    ],  # (compression_ratio, adjustment_factor)
) -> list[dict]:
    """Test different compression settings on a sample file."""
    results = []

    # First, extract the paper
    paper = processor.process_file(test_file)
    original_words = paper.word_count

    for compression_ratio, adjustment_factor in variations:
        try:
            # Temporarily modify the summarizer's adjustment factor
            processor.ai_summarizer._test_adjustment = adjustment_factor

            # Create summary
            summary = processor.create_summary(
                paper, compression_ratio=compression_ratio
            )

            # Analyze results
            summary_words = len(summary.summary_content.split())
            actual_compression = (summary_words / original_words) * 100

            results.append(
                {
                    "compression_ratio": compression_ratio,
                    "adjustment_factor": adjustment_factor,
                    "original_words": original_words,
                    "summary_words": summary_words,
                    "actual_compression": actual_compression,
                    "target_range": (10, 25),  # User's desired range
                    "in_target": 10 <= actual_compression <= 25,
                }
            )

            console.print(
                f"[cyan]Test: compression={compression_ratio}, adjustment={adjustment_factor}[/cyan]"
            )
            console.print(f"  Original: {original_words} words")
            console.print(f"  Summary: {summary_words} words")
            console.print(f"  Actual compression: {actual_compression:.1f}%")
            console.print(
                f"  In target range: {'Yes' if results[-1]['in_target'] else 'No'}"
            )
            console.print()

        except Exception as e:
            console.print(
                f"[red]Error testing {compression_ratio}/{adjustment_factor}: {e}[/red]"
            )

    return results


def find_optimal_settings(results: list[dict]) -> dict:
    """Analyze results to find optimal settings."""
    # Filter results that are in target range
    good_results = [r for r in results if r["in_target"]]

    if not good_results:
        # Find closest to target
        target_center = 17.5  # Middle of 10-25%
        results.sort(key=lambda x: abs(x["actual_compression"] - target_center))
        best = results[0]
    else:
        # Find result closest to center of target range
        target_center = 17.5
        good_results.sort(
            key=lambda x: abs(x["actual_compression"] - target_center)
        )
        best = good_results[0]

    return {
        "recommended_compression": best["compression_ratio"],
        "recommended_adjustment": best["adjustment_factor"],
        "expected_compression": best["actual_compression"],
        "all_results": results,
    }


def main():
    """Run the fine-tuning process."""
    # Configuration
    base_dir = Path(
        "/home/petteri/Dropbox/LABs/github-personal/papers/scan2bim/biblio/bim"
    )
    test_file = (
        base_dir
        / "2D–3D fusion approach for improved point cloud segmentation - ScienceDirect.html"
    )

    console.print("[bold blue]Summarization Fine-Tuning Tool[/bold blue]")
    console.print()

    # Step 1: Analyze existing summaries
    console.print("[yellow]Step 1: Analyzing existing summaries...[/yellow]")
    existing_analysis = analyze_existing_summaries(base_dir)

    if existing_analysis:
        table = Table(title="Existing Summary Analysis")
        table.add_column("File", style="cyan")
        table.add_column("Size Compression", style="green")
        table.add_column("Word Compression", style="green")

        for item in existing_analysis[:5]:  # Show first 5
            if "word_compression" in item:
                table.add_row(
                    item["original"][:40] + "...",
                    f"{item['compression_ratio']:.1f}%",
                    f"{item.get('word_compression', 'N/A'):.1f}%",
                )

        console.print(table)
        console.print()

    # Step 2: Test variations
    console.print("[yellow]Step 2: Testing compression variations...[/yellow]")

    # Test different combinations
    variations = [
        # (compression_ratio, adjustment_factor)
        (0.25, 0.4),  # Less aggressive adjustment
        (0.25, 0.5),
        (0.25, 0.6),
        (0.25, 0.7),  # Current default
        (0.25, 0.8),
        (0.25, 0.9),
        (0.25, 1.0),  # No adjustment
        (0.30, 0.6),  # Higher base compression
        (0.30, 0.7),
        (0.35, 0.5),  # Even higher base
        (0.35, 0.6),
    ]

    # Initialize processor
    processor = PaperProcessor()

    # Temporarily patch the AI summarizer for testing
    import types

    def patched_create_summary(sections, metadata, target_compression):
        # Use test adjustment factor if available
        if hasattr(processor.ai_summarizer, "_test_adjustment"):
            adjustment = processor.ai_summarizer._test_adjustment
        else:
            adjustment = 0.7

        # Temporarily modify the method

        def temp_calc_target(self):
            if metadata.get("word_count"):
                original_words = metadata["word_count"]
                adjusted_compression = target_compression * adjustment
                target_words = int(original_words * adjusted_compression)
                target_chars = target_words * 6
            else:
                total_chars = sum(len(s["content"]) for s in sections)
                adjusted_compression = target_compression * adjustment
                target_chars = int(total_chars * adjusted_compression)
                target_words = int(target_chars / 6)

            # Ensure minimum
            min_words = 2000
            if target_words < min_words:
                target_words = min_words
                target_chars = target_words * 6

            return target_words, target_chars, adjusted_compression

        # Store original target calculation
        target_words, target_chars, adjusted_compression = temp_calc_target(
            processor.ai_summarizer
        )

        # Update the prompt with calculated values
        prompt = f"""Please provide a detailed and comprehensive summary of the following academic paper.

CRITICAL LENGTH REQUIREMENT:
- You MUST write EXACTLY {target_words} words (approximately {target_chars} characters)
- This represents {int(adjusted_compression * 100)}% of the original paper
- The summary should be comprehensive and detailed, not brief
- Aim for the exact word count - not significantly more or less

Content Requirements:
1. Write a THOROUGH, DETAILED summary that preserves the paper's substance
2. Include comprehensive coverage of ALL major sections
3. Preserve important numerical data, findings, and technical details
4. Maintain clear section structure
5. Include methodology, results, discussion, and conclusions
6. Keep technical terminology and academic rigor

FORMAT: Write in clear paragraphs with good flow. Cover all major aspects of the paper.

Paper content:
{processor.ai_summarizer._build_content_for_summary(sections, metadata)}

IMPORTANT: Your summary must be EXACTLY {target_words} words. Count carefully."""

        # Call the AI service with modified prompt
        if processor.ai_summarizer.provider == "anthropic":
            response = processor.ai_summarizer.client.messages.create(
                model=processor.ai_summarizer.model,
                max_tokens=processor.ai_summarizer.max_tokens,
                temperature=processor.ai_summarizer.temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        else:
            raise NotImplementedError(
                "Only Anthropic provider supported for testing"
            )

    # Monkey patch for testing
    processor.ai_summarizer.create_summary = types.MethodType(
        patched_create_summary, processor.ai_summarizer
    )

    # Run tests
    results = test_compression_variations(processor, test_file, variations)

    # Step 3: Find optimal settings
    console.print("[yellow]Step 3: Finding optimal settings...[/yellow]")
    optimal = find_optimal_settings(results)

    # Display results
    console.print()
    console.print("[bold green]Optimal Settings Found:[/bold green]")
    console.print(f"Compression Ratio: {optimal['recommended_compression']}")
    console.print(f"Adjustment Factor: {optimal['recommended_adjustment']}")
    console.print(
        f"Expected Compression: {optimal['expected_compression']:.1f}%"
    )

    # Save results
    results_file = Path("summarization_tuning_results.json")
    with open(results_file, "w") as f:
        json.dump(optimal, f, indent=2)

    console.print(f"\n[green]Results saved to {results_file}[/green]")

    # Provide implementation recommendation
    console.print("\n[bold yellow]Recommended Implementation:[/bold yellow]")
    console.print(f"""
Update literature_reviewer/processors/ai_summarizer.py:
- Change adjustment factor from 0.7 to {optimal["recommended_adjustment"]}
- Consider using compression ratio of {optimal["recommended_compression"]} instead of 0.25

This should produce summaries that are approximately {optimal["expected_compression"]:.1f}% of the original,
which falls within your target range of 10-25%.
""")


if __name__ == "__main__":
    main()
