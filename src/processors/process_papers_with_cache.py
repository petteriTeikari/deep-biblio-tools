#!/usr/bin/env python3
"""
Academic Literature Review Generator with Caching
Processes academic papers (HTML/MD) to create comprehensive summaries and literature review
Includes caching to avoid reprocessing files

Usage: python process_papers_with_cache.py [--force-reprocess FILE1 FILE2...]
"""

import argparse
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

# Configuration
TARGET_SUMMARY_PERCENTAGE = 0.25  # 25% of original
MIN_SUMMARY_SIZE_KB = 15  # Minimum summary size
CACHE_FILE = "paper_processing_cache.json"


class PaperCache:
    """Manages cache of processed papers"""

    def __init__(self, cache_file: str):
        self.cache_file = cache_file
        self.cache = self._load_cache()

    def _load_cache(self) -> dict:
        """Load cache from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(
                    f"Warning: Could not load cache from {self.cache_file}: {e}"
                )
                return {}
        return {}

    def _save_cache(self):
        """Save cache to file"""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f, indent=2, sort_keys=True)
        except Exception as e:
            print(f"Warning: Could not save cache: {e}")

    def _get_file_hash(self, filepath: Path) -> str:
        """Calculate MD5 hash of file content"""
        md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)
        return md5.hexdigest()

    def _get_file_info(self, filepath: Path) -> dict:
        """Get file information"""
        stat = filepath.stat()
        return {
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "hash": self._get_file_hash(filepath),
        }

    def is_processed(self, input_file: Path, output_file: Path) -> bool:
        """Check if file has been processed and is up to date"""
        input_str = str(input_file.absolute())

        # Check if in cache
        if input_str not in self.cache:
            return False

        cached_info = self.cache[input_str]

        # Check if output file exists
        if not output_file.exists():
            return False

        # Check if input file has changed
        current_info = self._get_file_info(input_file)
        if current_info["hash"] != cached_info["input_hash"]:
            return False

        # Check if output file size is reasonable (at least 10KB)
        if output_file.stat().st_size < 10240:
            return False

        return True

    def mark_processed(
        self, input_file: Path, output_file: Path, metadata: dict = None
    ):
        """Mark file as processed"""
        input_str = str(input_file.absolute())
        file_info = self._get_file_info(input_file)

        self.cache[input_str] = {
            "input_hash": file_info["hash"],
            "input_size": file_info["size"],
            "input_modified": file_info["modified"],
            "output_file": str(output_file.absolute()),
            "output_size": output_file.stat().st_size,
            "processed_at": datetime.now().isoformat(),
            "target_size": metadata.get("target_size", 0) if metadata else 0,
            "summary_percentage": metadata.get("percentage", 25)
            if metadata
            else 25,
        }
        self._save_cache()

    def get_unprocessed_files(
        self, input_files: list[Path], output_dir: Path
    ) -> list[dict]:
        """Get list of files that need processing"""
        unprocessed = []

        for input_file in input_files:
            output_name = (
                input_file.stem.replace(" ", "_").replace(":", "")
                + "_comprehensive_summary.md"
            )
            output_file = output_dir / output_name

            if not self.is_processed(input_file, output_file):
                unprocessed.append(
                    {
                        "input": input_file,
                        "output": output_file,
                        "reason": "new"
                        if str(input_file.absolute()) not in self.cache
                        else "updated",
                    }
                )

        return unprocessed

    def get_statistics(self) -> dict:
        """Get cache statistics"""
        total_files = len(self.cache)
        total_input_size = sum(
            info["input_size"] for info in self.cache.values()
        )
        total_output_size = sum(
            info["output_size"] for info in self.cache.values()
        )

        return {
            "total_files": total_files,
            "total_input_size_mb": total_input_size / (1024 * 1024),
            "total_output_size_mb": total_output_size / (1024 * 1024),
            "average_compression": total_output_size / total_input_size
            if total_input_size > 0
            else 0,
        }


def create_summary_prompt(paper_path: Path, target_size_kb: float) -> str:
    """Create prompt for summarizing a paper"""

    original_size_kb = paper_path.stat().st_size / 1024

    return f"""
Create a COMPREHENSIVE summary of this academic paper that is EXACTLY {target_size_kb:.1f}KB in size (25% of the original {original_size_kb:.1f}KB).

CRITICAL REQUIREMENTS:

1. TARGET SIZE: The summary MUST be approximately {target_size_kb:.1f}KB

2. CITATION FORMAT: Convert ALL citations from [X] to author-year format
   - Original: "using SMPL model [64]"
   - Converted: "using SMPL model ([Loper et al., 2015])"

3. STRUCTURE (with approximate sizes):
   - Title, Authors, Affiliations (0.5KB)
   - Comprehensive Abstract (10-15% of summary)
   - Detailed Key Contributions (20-25% of summary)
   - Extensive Methodology (30-35% of summary)
   - Complete Results with numbers (20-25% of summary)
   - Technical Implementation (10-15% of summary)
   - Limitations and Future Work (5% of summary)
   - COMPLETE References (10-15% of summary)

4. CONTENT PRESERVATION:
   - Include extensive quotes from important sections
   - Preserve ALL quantitative results and comparisons
   - Keep all algorithm names and technical details
   - Maintain equations and mathematical notation
   - Include all dataset names and evaluation metrics

5. REFERENCES: End with a complete bibliography containing:
   - Full author names (not just initials)
   - Complete paper titles
   - Publication venue, volume, pages
   - Year and DOI/URL when available

Input file: {paper_path}
Target size: {target_size_kb:.1f}KB
"""


def process_directory(input_dir: Path, force_reprocess: set[str] = None):
    """Process all papers in directory with caching"""

    # Setup directories
    summaries_dir = input_dir / "summaries"
    review_dir = input_dir / "review"
    summaries_dir.mkdir(exist_ok=True)
    review_dir.mkdir(exist_ok=True)

    # Initialize cache
    cache = PaperCache(input_dir / CACHE_FILE)

    # Find all papers
    paper_files = list(input_dir.glob("*.html")) + list(input_dir.glob("*.md"))
    paper_files = [
        f
        for f in paper_files
        if "_summary" not in f.name and "Literature_Review" not in f.name
    ]

    print(f"Found {len(paper_files)} papers in {input_dir}")

    # Check which need processing
    unprocessed = cache.get_unprocessed_files(paper_files, summaries_dir)

    # Add force-reprocess files
    if force_reprocess:
        for paper in paper_files:
            if any(forced in str(paper) for forced in force_reprocess):
                output_name = (
                    paper.stem.replace(" ", "_").replace(":", "")
                    + "_comprehensive_summary.md"
                )
                output_file = summaries_dir / output_name

                # Add to unprocessed if not already there
                if not any(u["input"] == paper for u in unprocessed):
                    unprocessed.append(
                        {
                            "input": paper,
                            "output": output_file,
                            "reason": "forced",
                        }
                    )

    # Show statistics
    stats = cache.get_statistics()
    print("\nCache Statistics:")
    print(f"  Total processed: {stats['total_files']} files")
    print(f"  Total input size: {stats['total_input_size_mb']:.1f} MB")
    print(f"  Total output size: {stats['total_output_size_mb']:.1f} MB")
    print(f"  Average compression: {stats['average_compression']:.1%}")

    print(f"\nNeed to process: {len(unprocessed)} files")
    for item in unprocessed:
        print(f"  - {item['input'].name} ({item['reason']})")

    # Process each unprocessed file
    for i, item in enumerate(unprocessed, 1):
        input_file = item["input"]
        output_file = item["output"]

        print(f"\n[{i}/{len(unprocessed)}] Processing: {input_file.name}")

        # Calculate target size
        input_size = input_file.stat().st_size
        target_size = max(
            int(input_size * TARGET_SUMMARY_PERCENTAGE),
            MIN_SUMMARY_SIZE_KB * 1024,
        )
        target_size_kb = target_size / 1024

        print(f"  Input size: {input_size / 1024:.1f} KB")
        print(f"  Target size: {target_size_kb:.1f} KB")

        # Create prompt
        prompt = create_summary_prompt(input_file, target_size_kb)

        # Save prompt for manual processing
        prompt_file = input_file.parent / f"{input_file.stem}.prompt"
        with open(prompt_file, "w") as f:
            f.write(prompt)

        print(f"  Created prompt: {prompt_file.name}")
        print(f"  Output will be: {output_file.name}")

        # NOTE: Here you would call Claude to process the file
        # For now, we just create the prompt file

    print(f"\n{'=' * 60}")
    print("Summary prompts created. Use Claude to process each prompt.")
    print("After processing, run this script again to update the cache.")
    print(f"{'=' * 60}")

    return cache, unprocessed


def main():
    parser = argparse.ArgumentParser(
        description="Process papers with caching support"
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory containing papers (default: current directory)",
    )
    parser.add_argument(
        "--force-reprocess",
        nargs="*",
        help="Force reprocess specific files (partial name match)",
    )
    parser.add_argument(
        "--show-cache", action="store_true", help="Show cache contents and exit"
    )

    args = parser.parse_args()

    input_dir = Path(args.directory).absolute()

    if args.show_cache:
        cache = PaperCache(input_dir / CACHE_FILE)
        print(f"Cache contents for {input_dir}:")
        for file, info in cache.cache.items():
            print(f"\n{Path(file).name}:")
            print(f"  Processed: {info['processed_at']}")
            print(f"  Output: {Path(info['output_file']).name}")
            print(
                f"  Size: {info['input_size'] / 1024:.1f}KB → {info['output_size'] / 1024:.1f}KB"
            )
        return

    # Process directory
    cache, unprocessed = process_directory(
        input_dir, set(args.force_reprocess) if args.force_reprocess else None
    )

    # After papers are processed, update cache
    # This part would be called after Claude processes the files
    print("\nTo mark a file as processed after using Claude:")
    print(
        "python process_papers_with_cache.py --mark-processed INPUT_FILE OUTPUT_FILE"
    )


if __name__ == "__main__":
    main()
