#!/usr/bin/env python3
"""
Rename Priority Files Script

Focuses on renaming only the most important source files first:
- Python source files in src/, scripts/, tests/, tools/
- Configuration files
- Documentation files in docs/

This is a safer approach than renaming everything at once.
"""

import sys
from pathlib import Path

PRIORITY_DIRS = ["src", "scripts", "tests", "tools", "docs", ".claude"]

PRIORITY_EXTENSIONS = [".py", ".sh", ".md", ".yml", ".yaml", ".json", ".toml"]


def should_rename_priority(filepath: Path) -> bool:
    """Check if a priority file should be renamed."""
    # Skip these directories
    skip_dirs = {
        ".git",
        ".venv",
        "__pycache__",
        ".mypy_cache",
        "node_modules",
        "data",
        ".pytest_cache",
        ".ruff_cache",
        ".cache",
    }
    for parent in filepath.parents:
        if parent.name in skip_dirs:
            return False

    # Check if in priority directory
    try:
        rel_path = filepath.relative_to(
            Path("/home/petteri/Dropbox/LABs/KusiKasa/github/deep-biblio-tools")
        )
        first_dir = str(rel_path).split("/")[0]
        if first_dir not in PRIORITY_DIRS:
            return False
    except ValueError:
        return False

    # Check extension
    if filepath.suffix not in PRIORITY_EXTENSIONS:
        return False

    filename = filepath.name

    # Skip special files
    if filename in [
        "__init__.py",
        "__main__.py",
        "README.md",
        "CHANGELOG.md",
        "CLAUDE.md",
        "LICENSE",
        "Makefile",
    ]:
        return False

    # Check if needs renaming
    has_underscore = "_" in filename
    has_uppercase = filename != filename.lower()

    return has_underscore or has_uppercase


def get_new_filename(filename: str) -> str:
    """Convert filename to follow conventions."""
    # Special cases
    if filename in [
        "__init__.py",
        "__main__.py",
        "README.md",
        "CHANGELOG.md",
        "CLAUDE.md",
        "LICENSE",
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


def update_python_imports(file_path: Path, renames: dict[Path, Path]) -> bool:
    """Update imports in a Python file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        updated = content

        for old_path, new_path in renames.items():
            if not old_path.suffix == ".py":
                continue

            # Get module names
            old_parts = old_path.stem.replace("-", "_")
            new_parts = new_path.stem.replace("-", "_")

            # Update imports
            patterns = [
                (f"from {old_parts} import", f"from {new_parts} import"),
                (f"import {old_parts}", f"import {new_parts}"),
                (f"from .{old_parts} import", f"from .{new_parts} import"),
                (f"import .{old_parts}", f"import .{new_parts}"),
            ]

            for old_pattern, new_pattern in patterns:
                updated = updated.replace(old_pattern, new_pattern)

        if content != updated:
            file_path.write_text(updated, encoding="utf-8")
            return True

    except Exception as e:
        print(f"Error updating {file_path}: {e}")

    return False


def rename_priority_files(dry_run: bool = True):
    """Rename priority files only."""
    root = Path("/home/petteri/Dropbox/LABs/KusiKasa/github/deep-biblio-tools")

    # Collect priority files to rename
    renames = {}

    print("Scanning for priority files to rename...")
    print(f"Looking in: {', '.join(PRIORITY_DIRS)}")
    print(f"Extensions: {', '.join(PRIORITY_EXTENSIONS)}")
    print()

    for dir_name in PRIORITY_DIRS:
        dir_path = root / dir_name
        if not dir_path.exists():
            continue

        for filepath in dir_path.rglob("*"):
            if filepath.is_file() and should_rename_priority(filepath):
                old_name = filepath.name
                new_name = get_new_filename(old_name)

                if old_name != new_name:
                    new_path = filepath.parent / new_name
                    renames[filepath] = new_path

    if not renames:
        print("No priority files need renaming!")
        return

    print(f"Found {len(renames)} priority files to rename\n")

    # Group by directory
    by_dir = {}
    for old_path, new_path in renames.items():
        dir_name = old_path.relative_to(root).parts[0]
        by_dir.setdefault(dir_name, []).append((old_path, new_path))

    # Show summary
    for dir_name, items in sorted(by_dir.items()):
        print(f"{dir_name}/: {len(items)} files")

    if dry_run:
        print("\nDRY RUN - Preview of changes:")
        print("-" * 80)

        # Show sample from each directory
        for dir_name, items in sorted(by_dir.items()):
            print(f"\n{dir_name}/:")
            for old_path, new_path in items[:3]:
                old_rel = old_path.relative_to(root)
                new_rel = new_path.relative_to(root)
                print(f"  {old_rel} → {new_rel}")
            if len(items) > 3:
                print(f"  ... and {len(items) - 3} more files")

        print("-" * 80)
        print("\nRun with --execute to perform the renaming")
        return

    # Perform renaming
    print("\nRenaming files...")
    renamed_count = 0
    errors = []

    for old_path, new_path in sorted(renames.items()):
        try:
            if new_path.exists():
                errors.append(f"Target exists: {new_path.name}")
                continue

            old_path.rename(new_path)
            renamed_count += 1
            print(f" {old_path.relative_to(root)} → {new_path.name}")

        except Exception as e:
            errors.append(f"{old_path.name}: {e}")

    print(f"\nRenamed {renamed_count} files successfully")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for err in errors[:10]:
            print(f"  - {err}")

    # Update imports
    print("\nUpdating imports in Python files...")
    python_files = []
    for dir_name in PRIORITY_DIRS:
        dir_path = root / dir_name
        if dir_path.exists():
            python_files.extend(dir_path.rglob("*.py"))

    updated_count = 0
    for pyfile in python_files:
        if update_python_imports(pyfile, renames):
            updated_count += 1

    print(f"Updated imports in {updated_count} files")
    print("\nPriority renaming complete!")


if __name__ == "__main__":
    dry_run = "--execute" not in sys.argv
    rename_priority_files(dry_run)
