#!/usr/bin/env python3
"""
Fix imports after renaming - simple version without regex.

This script updates Python import statements to use the original underscore
convention for module names, even though the files now use hyphens.
"""

from pathlib import Path


def fix_python_imports(file_path: Path) -> bool:
    """Fix imports in a Python file to use underscores for module names."""
    try:
        content = file_path.read_text(encoding="utf-8")
        updated = content
        changed = False

        # Simple replacements for common module names that were renamed
        replacements = [
            ("from biblio-checker import", "from biblio_checker import"),
            ("import biblio-checker", "import biblio_checker"),
            ("from .biblio-checker import", "from .biblio_checker import"),
            ("from batch-validator import", "from batch_validator import"),
            ("import batch-validator", "import batch_validator"),
            (
                "from hallucination-detector import",
                "from hallucination_detector import",
            ),
            ("import hallucination-detector", "import hallucination_detector"),
            # Add more as needed
        ]

        for old_text, new_text in replacements:
            if old_text in updated:
                updated = updated.replace(old_text, new_text)
                changed = True

        if changed:
            file_path.write_text(updated, encoding="utf-8")
            return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

    return False


def main():
    """Fix imports in all Python files."""
    root = Path("/home/petteri/Dropbox/LABs/KusiKasa/github/deep-biblio-tools")

    # Priority directories
    priority_dirs = ["src", "scripts", "tests", "tools"]

    print("Fixing Python imports after file renaming...")

    fixed_count = 0

    for dir_name in priority_dirs:
        dir_path = root / dir_name
        if not dir_path.exists():
            continue

        print(f"\nProcessing {dir_name}/...")

        for py_file in dir_path.rglob("*.py"):
            # Skip __pycache__
            if "__pycache__" in str(py_file):
                continue

            if fix_python_imports(py_file):
                fixed_count += 1
                print(f"  Fixed imports in {py_file.relative_to(root)}")

    print(f"\nFixed imports in {fixed_count} files")


if __name__ == "__main__":
    main()
