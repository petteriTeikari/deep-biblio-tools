#!/usr/bin/env python3
"""
Check Dropbox file version history programmatically.

This script lists all file revisions for files in the repository
that were modified on a specific date (default: today).

Usage:
    python check_dropbox_versions.py --token YOUR_DROPBOX_TOKEN [--date 2025-10-28]

To get a Dropbox API token:
1. Go to https://www.dropbox.com/developers/apps
2. Create a new app or use existing app
3. Generate an access token
4. Use the token with this script
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import dropbox
from dropbox.exceptions import ApiError


def list_file_revisions(dbx, file_path, target_date=None):
    """
    List all revisions of a file, optionally filtered by date.

    Args:
        dbx: Dropbox client instance
        file_path: Path to file in Dropbox (must start with /)
        target_date: datetime.date object to filter by (optional)

    Returns:
        List of revision metadata dictionaries
    """
    try:
        revisions = dbx.files_list_revisions(file_path, limit=100).entries

        if target_date:
            revisions = [
                r for r in revisions
                if r.client_modified.date() == target_date
            ]

        return revisions
    except ApiError as e:
        if e.error.is_path() and e.error.get_path().is_not_found():
            return []
        raise


def find_files_with_date_revisions(dbx, repo_path, target_date):
    """
    Find all files in repository that have revisions from target_date.

    Args:
        dbx: Dropbox client instance
        repo_path: Path to repository root in Dropbox (e.g., /github-personal/deep-biblio-tools)
        target_date: datetime.date object

    Returns:
        Dict mapping file paths to list of revisions from target_date
    """
    results = {}

    try:
        # List all files recursively
        result = dbx.files_list_folder(repo_path, recursive=True)

        while True:
            for entry in result.entries:
                if isinstance(entry, dropbox.files.FileMetadata):
                    # Check revisions for this file
                    revisions = list_file_revisions(dbx, entry.path_display, target_date)
                    if revisions:
                        results[entry.path_display] = revisions

            if not result.has_more:
                break

            result = dbx.files_list_folder_continue(result.cursor)

    except ApiError as e:
        print(f"Error listing folder: {e}")
        sys.exit(1)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Check Dropbox file version history for repository files"
    )
    parser.add_argument(
        "--token",
        required=True,
        help="Dropbox API access token"
    )
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Date to check for file versions (YYYY-MM-DD, default: today)"
    )
    parser.add_argument(
        "--repo-path",
        default="/github-personal/deep-biblio-tools",
        help="Path to repository in Dropbox (default: /github-personal/deep-biblio-tools)"
    )

    args = parser.parse_args()

    # Parse target date
    try:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    except ValueError:
        print(f"Error: Invalid date format '{args.date}'. Use YYYY-MM-DD")
        sys.exit(1)

    # Initialize Dropbox client
    dbx = dropbox.Dropbox(args.token)

    # Verify connection
    try:
        account = dbx.users_get_current_account()
        print(f"Connected to Dropbox account: {account.name.display_name}")
        print(f"Checking for file versions from: {target_date}")
        print(f"Repository path: {args.repo_path}")
        print("-" * 80)
    except ApiError as e:
        print(f"Error connecting to Dropbox: {e}")
        sys.exit(1)

    # Find files with revisions from target date
    print(f"\nSearching for files with revisions from {target_date}...")
    files_with_revisions = find_files_with_date_revisions(
        dbx, args.repo_path, target_date
    )

    if not files_with_revisions:
        print(f"\nNo files found with revisions from {target_date}")
        print("\nThis could mean:")
        print("  1. No files were modified on that date")
        print("  2. The repository path is incorrect")
        print("  3. The Dropbox API token doesn't have access to this path")
        sys.exit(0)

    # Display results
    print(f"\nFound {len(files_with_revisions)} file(s) with revisions from {target_date}:")
    print("=" * 80)

    for file_path, revisions in sorted(files_with_revisions.items()):
        print(f"\n{file_path}")
        print(f"  {len(revisions)} revision(s) from {target_date}:")

        for rev in revisions:
            timestamp = rev.client_modified.strftime("%Y-%m-%d %H:%M:%S")
            size_kb = rev.size / 1024
            print(f"    - {timestamp} | {size_kb:.1f} KB | Rev: {rev.rev}")

    print("\n" + "=" * 80)
    print(f"\nTo restore a specific revision:")
    print(f"  dbx.files_restore(path='/path/to/file', rev='revision_id')")


if __name__ == "__main__":
    main()
