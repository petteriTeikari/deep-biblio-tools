#!/usr/bin/env python3
"""
Analyze and export unresolved/failed links from the cache database.
"""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.deep_biblio_tools.utils.cache import BiblioCache  # noqa: E402


def analyze_unresolved_links(
    export_format: str = None,
    output_file: str = None,
    domain_filter: str = None,
    error_filter: str = None,
):
    """
    Analyze unresolved links with filtering and export options.

    Args:
        export_format: Export format ('json', 'csv', or None for console)
        output_file: Output filename for export
        domain_filter: Filter by domain (e.g., 'arxiv.org')
        error_filter: Filter by error type keyword
    """
    cache = BiblioCache()
    failed_entries = cache.get_failed_entries()

    if not failed_entries:
        print("No unresolved links found in cache.")
        return

    # Apply filters
    filtered_entries = []
    for entry in failed_entries:
        # Domain filter
        if domain_filter:
            parsed_url = urlparse(entry["url"])
            if domain_filter not in parsed_url.netloc:
                continue

        # Error filter
        if error_filter:
            if error_filter.lower() not in entry["error_message"].lower():
                continue

        filtered_entries.append(entry)

    if not filtered_entries:
        print("No entries match the specified filters.")
        return

    # Analyze domains
    domain_counts = {}
    error_counts = {}

    for entry in filtered_entries:
        # Count domains
        parsed_url = urlparse(entry["url"])
        domain = parsed_url.netloc
        domain_counts[domain] = domain_counts.get(domain, 0) + 1

        # Count error types
        error_msg = entry["error_message"]
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

        error_counts[error_type] = error_counts.get(error_type, 0) + 1

    # Export if requested
    if export_format and output_file:
        if export_format == "json":
            export_data = {
                "summary": {
                    "total_unresolved": len(filtered_entries),
                    "domains": dict(
                        sorted(
                            domain_counts.items(),
                            key=lambda x: x[1],
                            reverse=True,
                        )
                    ),
                    "error_types": dict(
                        sorted(
                            error_counts.items(),
                            key=lambda x: x[1],
                            reverse=True,
                        )
                    ),
                    "export_date": datetime.now().isoformat(),
                },
                "entries": [
                    {
                        "url": entry["url"],
                        "normalized_url": entry["normalized_url"],
                        "doi": entry["doi"],
                        "error_message": entry["error_message"],
                        "timestamp": entry["timestamp"].isoformat(),
                        "domain": urlparse(entry["url"]).netloc,
                    }
                    for entry in filtered_entries
                ],
            }

            with open(output_file, "w") as f:
                json.dump(export_data, f, indent=2)

            print(f"Exported {len(filtered_entries)} entries to {output_file}")

        elif export_format == "csv":
            with open(output_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "URL",
                        "Normalized URL",
                        "DOI",
                        "Domain",
                        "Error Message",
                        "Timestamp",
                    ]
                )

                for entry in filtered_entries:
                    writer.writerow(
                        [
                            entry["url"],
                            entry["normalized_url"],
                            entry["doi"] or "",
                            urlparse(entry["url"]).netloc,
                            entry["error_message"],
                            entry["timestamp"].strftime("%Y-%m-%d %H:%M:%S"),
                        ]
                    )

            print(f"Exported {len(filtered_entries)} entries to {output_file}")

    else:
        # Console output
        print(f"\nUNRESOLVED LINKS ANALYSIS ({len(filtered_entries)} entries)")
        print("=" * 80)

        # Show domain statistics
        print("\nTOP DOMAINS WITH ERRORS:")
        print("-" * 40)
        for domain, count in sorted(
            domain_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]:
            print(f"  {domain:40} {count:5} errors")

        # Show error type statistics
        print("\nERROR TYPE DISTRIBUTION:")
        print("-" * 40)
        for error_type, count in sorted(
            error_counts.items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (count / len(filtered_entries)) * 100
            print(f"  {error_type:30} {count:5} ({percentage:5.1f}%)")

        # Show recent failures
        print("\nMOST RECENT FAILURES (last 10):")
        print("-" * 40)
        recent_entries = sorted(
            filtered_entries, key=lambda x: x["timestamp"], reverse=True
        )[:10]
        for i, entry in enumerate(recent_entries, 1):
            print(f"\n  {i}. URL: {entry['url']}")
            print(f"     Error: {entry['error_message']}")
            print(
                f"     Time: {entry['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}"
            )

        # Suggest actions
        print("\n" + "=" * 80)
        print("SUGGESTED ACTIONS:")
        print("  1. Review domain-specific errors for patterns")
        print("  2. Check if certain domains need special handling")
        print("  3. Run the proofreader to manually correct failed entries:")
        print("     streamlit run src/deep_biblio_tools/proofreader.py")
        print("  4. Export full list for detailed analysis:")
        print(
            "     python scripts/analyze_unresolved_links.py --export json -o unresolved.json"
        )


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Analyze and export unresolved/failed links from the cache"
    )
    parser.add_argument(
        "--export", choices=["json", "csv"], help="Export format"
    )
    parser.add_argument("-o", "--output", help="Output file for export")
    parser.add_argument("--domain", help="Filter by domain (e.g., arxiv.org)")
    parser.add_argument(
        "--error", help="Filter by error type keyword (e.g., '404', 'timeout')"
    )

    args = parser.parse_args()

    if args.export and not args.output:
        parser.error("--export requires --output/-o")

    analyze_unresolved_links(
        export_format=args.export,
        output_file=args.output,
        domain_filter=args.domain,
        error_filter=args.error,
    )


if __name__ == "__main__":
    main()
