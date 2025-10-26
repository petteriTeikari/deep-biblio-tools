#!/usr/bin/env python3
"""
Rename Files Script

Renames all files in the repository to follow the naming convention:
- All lowercase (except README, CHANGELOG, CLAUDE)
- Hyphens instead of underscores to separate words
- Updates import statements and references
"""

import sys
from pathlib import Path


def should_rename(filepath: Path) -> bool:
    """Check if a file should be renamed according to conventions."""
    # Skip these directories entirely
    skip_dirs = {".git", ".venv", "__pycache__", ".mypy_cache", "node_modules"}
    for parent in filepath.parents:
        if parent.name in skip_dirs:
            return False

    filename = filepath.name

    # Skip special Python files
    if filename in ["__init__.py", "__main__.py"]:
        return False

    # Skip allowed uppercase files
    if filename in [
        "README.md",
        "README",
        "CHANGELOG.md",
        "CHANGELOG",
        "CLAUDE.md",
        "LICENSE",
        "LICENSE.md",
        "Makefile",
    ]:
        return False

    # Check if file needs renaming
    has_underscore = "_" in filename
    has_uppercase = filename != filename.lower()

    return has_underscore or has_uppercase


def get_new_filename(filename: str) -> str:
    """Convert filename to follow conventions."""
    # Special cases that should keep their format
    if filename in [
        "__init__.py",
        "__main__.py",
        "README.md",
        "README",
        "CHANGELOG.md",
        "CHANGELOG",
        "CLAUDE.md",
        "LICENSE",
        "LICENSE.md",
        "Makefile",
    ]:
        return filename

    # Convert to lowercase and replace underscores
    new_name = filename.lower().replace("_", "-")

    # Handle camelCase without regex
    result = []
    for i, char in enumerate(new_name):
        if i > 0 and char.isupper() and new_name[i - 1].islower():
            result.append("-")
        result.append(char.lower())
    new_name = "".join(result)

    # Remove duplicate hyphens
    while "--" in new_name:
        new_name = new_name.replace("--", "-")

    return new_name


def update_python_imports(content: str, renames: dict[str, str]) -> str:
    """Update Python import statements for renamed modules."""
    updated = content

    for old_path, new_path in renames.items():
        # Skip if not a Python file
        if not old_path.endswith(".py"):
            continue

        # Convert file paths to module names
        old_module = old_path.replace("/", ".").replace(".py", "")
        new_module = new_path.replace("/", ".").replace(".py", "")

        # Update various import patterns
        patterns = [
            (f"from {old_module}", f"from {new_module}"),
            (f"import {old_module}", f"import {new_module}"),
            (f'"{old_module}"', f'"{new_module}"'),
            (f"'{old_module}'", f"'{new_module}'"),
        ]

        for old_pattern, new_pattern in patterns:
            updated = updated.replace(old_pattern, new_pattern)

    return updated


def rename_files(dry_run: bool = True):
    """Rename files in the repository."""
    root = Path(
        "/home/petteri/Dropbox/LABs/github-personal/github/deep-biblio-tools"
    )

    # Collect all files to rename
    renames = {}

    print("Scanning for files to rename...")
    for filepath in root.rglob("*"):
        if filepath.is_file() and should_rename(filepath):
            old_name = filepath.name
            new_name = get_new_filename(old_name)

            if old_name != new_name:
                new_path = filepath.parent / new_name
                renames[str(filepath.relative_to(root))] = str(
                    new_path.relative_to(root)
                )

    if not renames:
        print("No files need renaming!")
        return

    print(f"\nFound {len(renames)} files to rename")

    if dry_run:
        print("\nDRY RUN - No files will be renamed. Preview of changes:")
        print("-" * 80)
        for old, new in sorted(renames.items())[:20]:  # Show first 20
            print(f"{old} → {new}")
        if len(renames) > 20:
            print(f"... and {len(renames) - 20} more files")
        print("-" * 80)
        print("\nRun with --execute to perform the renaming")
        return

    # Perform the renaming
    print("\nRenaming files...")
    renamed_count = 0

    for old_rel, new_rel in sorted(renames.items()):
        old_path = root / old_rel
        new_path = root / new_rel

        try:
            # Check if target exists
            if new_path.exists():
                print(f"SKIP: {old_rel} - target already exists")
                continue

            # Rename the file
            old_path.rename(new_path)
            renamed_count += 1
            print(f" {old_rel} → {new_rel}")

        except Exception as e:
            print(f"ERROR: Failed to rename {old_rel}: {e}")

    print(f"\nRenamed {renamed_count} files")

    # Update imports in Python files
    print("\nUpdating import statements...")
    python_files = list(root.rglob("*.py"))

    for pyfile in python_files:
        try:
            content = pyfile.read_text(encoding="utf-8")
            updated = update_python_imports(content, renames)

            if content != updated:
                pyfile.write_text(updated, encoding="utf-8")
                print(f" Updated imports in {pyfile.relative_to(root)}")

        except Exception as e:
            print(f"ERROR: Failed to update {pyfile}: {e}")

    print("\nRenaming complete!")


if __name__ == "__main__":
    dry_run = "--execute" not in sys.argv
    rename_files(dry_run)
