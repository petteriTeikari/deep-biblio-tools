#!/usr/bin/env python3
"""
Display unresolved/failed links from the cache database.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.deep_biblio_tools.utils.cache import BiblioCache  # noqa: E402


def show_unresolved_links(verbose: bool = False):
    """Display all unresolved links from the cache."""
    cache = BiblioCache()

    # Get cache statistics first
    stats = cache.get_stats()
    print("CACHE STATISTICS:")
    print(f"  Total entries: {stats['total_entries']}")
    print(f"  Valid entries: {stats['valid_entries']}")
    print(f"  Entries with errors: {stats['entries_with_errors']}")
    print(f"  Cache file: {stats['cache_file']}")
    print("=" * 80)

    # Get failed entries
    failed_entries = cache.get_failed_entries()

    if not failed_entries:
        print("\nNo unresolved links found in cache.")
        return

    print(f"\nUNRESOLVED LINKS ({len(failed_entries)} total):")
    print("=" * 80)

    # Group by error type
    error_types = {}
    for entry in failed_entries:
        error_msg = entry["error_message"]
        # Extract error type from message
        if "Request error" in error_msg:
            error_type = "Network/Request Error"
        elif "Parse error" in error_msg:
            error_type = "Parse Error"
        elif "404" in error_msg:
            error_type = "404 Not Found"
        elif "403" in error_msg:
            error_type = "403 Forbidden"
        elif "timeout" in error_msg.lower():
            error_type = "Timeout"
        else:
            error_type = "Other Error"

        if error_type not in error_types:
            error_types[error_type] = []
        error_types[error_type].append(entry)

    # Display by error type
    for error_type, entries in sorted(error_types.items()):
        print(f"\n{error_type} ({len(entries)} entries):")
        print("-" * 40)

        for i, entry in enumerate(entries, 1):
            print(f"\n  {i}. URL: {entry['url']}")
            if entry["normalized_url"] != entry["url"]:
                print(f"     Normalized: {entry['normalized_url']}")
            if entry["doi"]:
                print(f"     DOI: {entry['doi']}")
            print(f"     Error: {entry['error_message']}")
            print(
                f"     Timestamp: {entry['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}"
            )

            if verbose:
                # In verbose mode, show full error details
                print(f"     Full details: {entry}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY BY ERROR TYPE:")
    for error_type, entries in sorted(error_types.items()):
        print(f"  {error_type}: {len(entries)}")

    print("\nTo manually correct these entries, run:")
    print("  streamlit run src/deep_biblio_tools/proofreader.py")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Display unresolved/failed links from the cache"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show verbose output with full error details",
    )

    args = parser.parse_args()
    show_unresolved_links(verbose=args.verbose)


if __name__ == "__main__":
    main()
