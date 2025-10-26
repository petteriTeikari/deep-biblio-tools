#!/usr/bin/env python3
"""Debug conversion harness for capturing golden baseline and debugging citation pipeline.

This script runs the markdown-to-LaTeX conversion with comprehensive debug logging enabled,
capturing artifacts at each stage for regression testing and forensic analysis.

Usage:
    # Capture new golden baseline
    uv run python scripts/run_debug_conversion.py \\
        --markdown path/to/file.md \\
        --collection dpp-fashion \\
        --update-baseline

    # Run debug conversion (no baseline update)
    uv run python scripts/run_debug_conversion.py \\
        --markdown path/to/file.md \\
        --collection dpp-fashion

Output:
    Creates timestamped debug directory with 7 debug artifacts:
    - debug-01-extracted-citations.json
    - debug-02-zotero-bibtex-raw.bib
    - debug-03-parsed-bibtex-entries.json
    - debug-04-matching-results.json
    - debug-05-bibtex-validation.json
    - debug-06-latex-citations.json
    - debug-07-pdf-validation.json
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
from dotenv import load_dotenv  # noqa: E402
from src.converters.md_to_latex.converter import (  # noqa: E402
    MarkdownToLatexConverter,
)

load_dotenv(project_root / ".env")


def validate_environment():
    """Ensure required environment variables are set."""
    required_vars = [
        "ZOTERO_API_KEY",
        "ZOTERO_LIBRARY_ID",
        "ZOTERO_LIBRARY_TYPE",
    ]

    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        print("ERROR: Missing required environment variables:")
        for var in missing:
            print(f"  - {var}")
        print("\nPlease configure these in your .env file.")
        sys.exit(1)


def create_debug_output_dir(markdown_file: Path) -> Path:
    """Create timestamped debug output directory.

    Args:
        markdown_file: Input markdown file path

    Returns:
        Path to debug output directory
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    stem = markdown_file.stem
    debug_dir = (
        project_root
        / "tests"
        / "fixtures"
        / "debug-runs"
        / f"{stem}-{timestamp}"
    )
    debug_dir.mkdir(parents=True, exist_ok=True)
    return debug_dir


def run_debug_conversion(
    markdown_file: Path,
    collection_name: str,
    debug_dir: Path,
) -> dict:
    """Run conversion with full debug logging.

    Args:
        markdown_file: Path to input markdown file
        collection_name: Zotero collection name
        debug_dir: Debug output directory

    Returns:
        dict: Conversion statistics and results
    """
    # Configure logging to both console and file
    log_file = debug_dir / "conversion.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )

    logger = logging.getLogger(__name__)

    # Initialize converter with debug output directory
    output_dir = markdown_file.parent / "output"
    converter = MarkdownToLatexConverter(
        output_dir=output_dir,
        collection_name=collection_name,
        debug_output_dir=debug_dir,  # Enable debug mode
    )

    logger.info(f"Starting debug conversion of {markdown_file}")
    logger.info(f"Debug artifacts will be saved to: {debug_dir}")
    logger.info(f"Zotero collection: {collection_name}")

    try:
        # Run conversion (debug logging happens inside converter)
        converter.convert(str(markdown_file))

        # Collect statistics from debug artifacts
        stats = collect_conversion_stats(debug_dir)

        logger.info("=" * 80)
        logger.info("CONVERSION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Total citations: {stats['total_citations']}")
        logger.info(f"Matched from Zotero: {stats['matched_citations']}")
        logger.info(f"Unmatched: {stats['unmatched_citations']}")
        logger.info(f"Unknown/Anonymous entries: {stats['unknown_count']}")
        logger.info(f"BibTeX entries: {stats['bibtex_entries']}")
        logger.info(f"LaTeX \\citep commands: {stats['citep_count']}")
        logger.info(f"Missing from PDF: {len(stats['missing_from_pdf'])}")

        return stats

    except Exception as e:
        logger.error(f"Conversion failed: {e}", exc_info=True)
        raise


def collect_conversion_stats(debug_dir: Path) -> dict:
    """Collect statistics from debug artifacts.

    Args:
        debug_dir: Debug output directory

    Returns:
        dict: Statistics collected from debug files
    """
    stats = {
        "total_citations": 0,
        "matched_citations": 0,
        "unmatched_citations": 0,
        "unknown_count": 0,
        "anonymous_count": 0,
        "bibtex_entries": 0,
        "citep_count": 0,
        "missing_from_pdf": [],
    }

    # Read debug-04-matching-results.json
    matching_file = debug_dir / "debug-04-matching-results.json"
    if matching_file.exists():
        matching_data = json.loads(matching_file.read_text())
        stats["total_citations"] = matching_data.get("total", 0)
        stats["matched_citations"] = matching_data.get("matched", 0)
        stats["unmatched_citations"] = matching_data.get("unmatched", 0)

    # Read debug-05-bibtex-validation.json
    bibtex_file = debug_dir / "debug-05-bibtex-validation.json"
    if bibtex_file.exists():
        bibtex_data = json.loads(bibtex_file.read_text())
        stats["bibtex_entries"] = bibtex_data.get("entry_count", 0)
        stats["unknown_count"] = bibtex_data.get("unknown_count", 0)
        stats["anonymous_count"] = bibtex_data.get("anonymous_count", 0)

    # Read debug-06-latex-citations.json
    latex_file = debug_dir / "debug-06-latex-citations.json"
    if latex_file.exists():
        latex_data = json.loads(latex_file.read_text())
        stats["citep_count"] = latex_data.get("citep_count", 0)

    # Read debug-07-pdf-validation.json
    pdf_file = debug_dir / "debug-07-pdf-validation.json"
    if pdf_file.exists():
        pdf_data = json.loads(pdf_file.read_text())
        stats["missing_from_pdf"] = pdf_data.get("missing_entries", [])

    return stats


def update_golden_baseline(
    stats: dict, markdown_file: Path, collection_name: str
):
    """Update golden baseline with current statistics.

    Args:
        stats: Conversion statistics
        markdown_file: Input markdown file
        collection_name: Zotero collection name
    """
    baseline_file = (
        project_root / "tests" / "fixtures" / "golden-matching-results.json"
    )
    baseline_file.parent.mkdir(parents=True, exist_ok=True)

    baseline_data = {
        "collection_name": collection_name,
        "markdown_file": str(markdown_file),
        "total_citations": stats["total_citations"],
        "last_matched": stats["matched_citations"],
        "last_unmatched": stats["unmatched_citations"],
        "min_matched": stats["matched_citations"],  # Initial baseline
        "max_missing": stats["unmatched_citations"],  # Initial baseline
        "unknown_count": stats["unknown_count"],
        "anonymous_count": stats["anonymous_count"],
        "timestamp": datetime.now().isoformat(),
        "notes": f"Baseline established from working conversion ({stats['matched_citations']}/{stats['total_citations']} citations matched)",
    }

    baseline_file.write_text(json.dumps(baseline_data, indent=2))
    print(f"\nGolden baseline updated: {baseline_file}")
    print(
        f"   Matched: {stats['matched_citations']}/{stats['total_citations']}"
    )
    print(f"   Unknown/Anonymous: {stats['unknown_count']}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run debug conversion and optionally update golden baseline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--markdown",
        required=True,
        type=Path,
        help="Path to input markdown file",
    )

    parser.add_argument(
        "--collection",
        default="dpp-fashion",
        help="Zotero collection name (default: dpp-fashion)",
    )

    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Update golden baseline with current results",
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.markdown.exists():
        print(f"ERROR: Markdown file not found: {args.markdown}")
        sys.exit(1)

    validate_environment()

    # Create debug output directory
    debug_dir = create_debug_output_dir(args.markdown)

    print("=" * 80)
    print("DEBUG CONVERSION HARNESS")
    print("=" * 80)
    print(f"Input: {args.markdown}")
    print(f"Collection: {args.collection}")
    print(f"Debug output: {debug_dir}")
    print(f"Update baseline: {args.update_baseline}")
    print("=" * 80)

    # Run conversion
    stats = run_debug_conversion(args.markdown, args.collection, debug_dir)

    # Update golden baseline if requested
    if args.update_baseline:
        update_golden_baseline(stats, args.markdown, args.collection)

    print("\nDebug conversion complete!")
    print(f"   Debug artifacts: {debug_dir}")

    # Exit with error if there are unknown/anonymous entries
    if stats["unknown_count"] > 0 or stats["anonymous_count"] > 0:
        print(
            f"\nWARNING: {stats['unknown_count']} Unknown/Anonymous entries found"
        )
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
