#!/usr/bin/env python3
"""Remove unresolved links from the cache."""

import argparse
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.utils.cache import BiblioCache


def remove_unresolved_links(dry_run=False, yes=False):
    """Remove all unresolved links from the cache."""
    cache = BiblioCache()

    # Get all failed entries
    failed_entries = cache.get_failed_entries()

    if not failed_entries:
        print("No unresolved links found in cache.")
        return

    print(f"Found {len(failed_entries)} unresolved links to remove:")
    print("=" * 80)

    for entry in failed_entries:
        print(f"  - {entry.get('url')}")
        if entry.get("error_message"):
            print(f"    Error: {entry['error_message']}")

    print("=" * 80)

    if dry_run:
        print("\nDRY RUN: No changes made to cache.")
        return

    # Confirm removal
    if not yes:
        try:
            response = input(
                f"\nRemove all {len(failed_entries)} unresolved links? (y/N): "
            )
            if response.lower() != "y":
                print("Cancelled.")
                return
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return

    # Remove each failed entry
    removed_count = 0
    for entry in failed_entries:
        url = entry.get("url")
        if url and cache.remove(url):
            removed_count += 1
            print(f"Removed: {url}")

    print(
        f"\nSuccessfully removed {removed_count} unresolved links from cache."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Remove unresolved links from the cache"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be removed without actually removing",
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Automatically confirm removal without prompting",
    )

    args = parser.parse_args()
    remove_unresolved_links(dry_run=args.dry_run, yes=args.yes)


if __name__ == "__main__":
    main()
