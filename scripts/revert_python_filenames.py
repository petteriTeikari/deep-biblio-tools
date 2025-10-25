#!/usr/bin/env python3
"""
Revert Python filenames back to underscore convention.

Python module names cannot contain hyphens, so we need to keep Python files
with underscores while other files can use hyphens.
"""

import sys
from pathlib import Path


def should_revert(filepath: Path) -> bool:
    """Check if a Python file should be reverted to underscore naming."""
    if not filepath.suffix == ".py":
        return False

    # Skip special files that should keep underscores
    if filepath.name in ["__init__.py", "__main__.py"]:
        return False

    # Check if file has hyphens
    return "-" in filepath.name


def revert_to_underscore(filename: str) -> str:
    """Convert hyphenated filename back to underscores."""
    return filename.replace("-", "_")


def revert_python_files(dry_run: bool = True):
    """Revert Python files back to underscore naming."""
    root = Path("/home/petteri/Dropbox/LABs/KusiKasa/github/deep-biblio-tools")

    # Find all Python files with hyphens
    files_to_revert = []

    print("Scanning for Python files to revert...")

    for filepath in root.rglob("*.py"):
        # Skip cache directories
        if any(
            skip in str(filepath)
            for skip in [".venv", "__pycache__", ".pytest_cache"]
        ):
            continue

        if should_revert(filepath):
            new_name = revert_to_underscore(filepath.name)
            new_path = filepath.parent / new_name
            files_to_revert.append((filepath, new_path))

    if not files_to_revert:
        print("No Python files need reverting!")
        return

    print(f"\nFound {len(files_to_revert)} Python files to revert")

    if dry_run:
        print("\nDRY RUN - Preview of changes:")
        print("-" * 80)
        for old_path, new_path in files_to_revert[:20]:
            print(f"{old_path.relative_to(root)} → {new_path.name}")
        if len(files_to_revert) > 20:
            print(f"... and {len(files_to_revert) - 20} more files")
        print("-" * 80)
        print("\nRun with --execute to perform the reverting")
        return

    # Perform reverting
    print("\nReverting Python files...")
    reverted_count = 0
    errors = []

    for old_path, new_path in files_to_revert:
        try:
            if new_path.exists():
                errors.append(f"Target exists: {new_path.name}")
                continue

            old_path.rename(new_path)
            reverted_count += 1
            print(f" {old_path.name} → {new_path.name}")

        except Exception as e:
            errors.append(f"{old_path.name}: {e}")

    print(f"\nReverted {reverted_count} Python files successfully")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for err in errors[:10]:
            print(f"  - {err}")

    # Update guardrails to reflect this exception
    print("\nNote: Python files must use underscores for valid module names")
    print("Other files (.md, .sh, .yml, etc.) should still use hyphens")


if __name__ == "__main__":
    dry_run = "--execute" not in sys.argv
    revert_python_files(dry_run)
