#!/usr/bin/env python3
"""
Example of using the reorganized deep-biblio-tools modules for paper processing
"""

import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the parsers
from src.parsers.extract_complete_paper import extract_complete_paper

# Import the processors
from src.processors.process_papers_with_cache import PaperCache, PaperProcessor


def main():
    """Example of processing papers with the reorganized structure"""

    # Example 1: Extract content from a single ScienceDirect HTML file
    print("=== Example 1: Extracting from ScienceDirect HTML ===")
    html_file = Path("../data/elsevier_manual_scrape/example_paper.html")

    if html_file.exists():
        content = extract_complete_paper(str(html_file))
        print(f"Extracted {len(content)} characters from {html_file.name}")
        print(f"First 200 characters: {content[:200]}...")
    else:
        print(f"Example file not found: {html_file}")

    # Example 2: Process multiple papers with caching
    print("\n=== Example 2: Batch processing with cache ===")
    papers_dir = Path("../data/elsevier_manual_scrape/")

    if papers_dir.exists():
        # Initialize cache
        cache = PaperCache("example_cache.json")

        # Process papers
        processor = PaperProcessor(cache)
        processor.process_directory(papers_dir, force_reprocess=[])

        print("Processed papers are cached in: example_cache.json")
    else:
        print(f"Papers directory not found: {papers_dir}")

    # Example 3: Create comprehensive summaries
    print("\n=== Example 3: Creating summaries ===")
    print("Use the generated prompts with Claude/GPT to create 25% summaries")
    print(
        "Then use create_comprehensive_summary.py to generate the literature review"
    )


if __name__ == "__main__":
    main()
