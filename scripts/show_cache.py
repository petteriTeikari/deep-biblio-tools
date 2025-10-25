#!/usr/bin/env python3
"""
Display cache database contents in human-readable format
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path


def format_timestamp(timestamp):
    """Convert Unix timestamp to readable format"""
    try:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError, OverflowError):
        return str(timestamp)


def format_json_data(json_str):
    """Format JSON data for readable display"""
    if not json_str:
        return "None"
    try:
        data = json.loads(json_str)
        return json.dumps(data, indent=2)
    except (json.JSONDecodeError, TypeError):
        return json_str


def show_cache_contents():
    """Display all cache entries"""
    cache_path = Path.home() / ".deep-biblio-cache" / "biblio_cache.db"

    if not cache_path.exists():
        print("Cache database not found at:", cache_path)
        return

    print(f"Cache Database: {cache_path}")
    print(f"File Size: {cache_path.stat().st_size:,} bytes")
    print("=" * 80)

    with sqlite3.connect(cache_path) as conn:
        conn.row_factory = sqlite3.Row

        # Get basic stats
        cursor = conn.execute("SELECT COUNT(*) as total FROM cache_entries")
        total_entries = cursor.fetchone()[0]

        cursor = conn.execute("""
            SELECT COUNT(*) as successful
            FROM cache_entries
            WHERE bibtex_data IS NOT NULL
        """)
        successful_entries = cursor.fetchone()[0]

        cursor = conn.execute("""
            SELECT COUNT(*) as errors
            FROM cache_entries
            WHERE error_message IS NOT NULL
        """)
        error_entries = cursor.fetchone()[0]

        cursor = conn.execute("""
            SELECT COUNT(*) as with_doi
            FROM cache_entries
            WHERE doi IS NOT NULL
        """)
        doi_entries = cursor.fetchone()[0]

        print("CACHE STATISTICS:")
        print(f"  Total entries: {total_entries}")
        print(f"  Successful extractions: {successful_entries}")
        print(f"  Failed extractions: {error_entries}")
        print(f"  Entries with DOI: {doi_entries}")
        print()

        # Show all entries
        cursor = conn.execute("""
            SELECT * FROM cache_entries
            ORDER BY timestamp DESC
        """)

        for i, row in enumerate(cursor.fetchall(), 1):
            print(f"ENTRY {i}:")
            print(f"  ID: {row['id']}")
            print(f"  Original URL: {row['url']}")
            print(f"  Normalized URL: {row['normalized_url']}")
            print(f"  URL Hash: {row['url_hash']}")
            print(f"  DOI: {row['doi'] or 'None'}")
            print(f"  Timestamp: {format_timestamp(row['timestamp'])}")
            print(f"  Created: {row['created_at']}")

            if row["bibtex_data"]:
                print("  BibTeX Data:")
                bibtex_formatted = format_json_data(row["bibtex_data"])
                for line in bibtex_formatted.split("\n"):
                    print(f"    {line}")

            if row["error_message"]:
                print(f"  Error: {row['error_message']}")

            if row["response_headers"]:
                print("  Response Headers:")
                headers_formatted = format_json_data(row["response_headers"])
                for line in headers_formatted.split("\n"):
                    print(f"    {line}")

            print("-" * 80)


if __name__ == "__main__":
    show_cache_contents()
