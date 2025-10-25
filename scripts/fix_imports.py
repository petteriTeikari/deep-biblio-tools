#!/usr/bin/env python3
"""Fix imports after moving deep_biblio_tools contents to src."""

# import re  # Banned - using string methods instead
from pathlib import Path


def fix_imports_in_file(file_path: Path) -> bool:
    """Fix imports in a single file."""
    try:
        content = file_path.read_text()
        original_content = content

        # Replace deep_biblio_tools imports with src imports
        # Handle various import patterns using string methods
        replacements = [
            ("from deep_biblio_tools.", "from src."),
            ("import src.", "import src."),
            ("from src import", "from src import"),
            ("import src", "import src"),  # This handles the word boundary case
        ]

        for old_str, new_str in replacements:
            content = content.replace(old_str, new_str)

        if content != original_content:
            file_path.write_text(content)
            print(f"Fixed imports in: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Fix all imports in the project."""
    project_root = Path(__file__).parent.parent

    # Find all Python files
    python_files = []
    for pattern in ["*.py"]:
        python_files.extend(project_root.rglob(pattern))

    # Filter out __pycache__ and .git directories
    python_files = [
        f
        for f in python_files
        if "__pycache__" not in str(f) and ".git" not in str(f)
    ]

    fixed_count = 0
    for file_path in python_files:
        if fix_imports_in_file(file_path):
            fixed_count += 1

    print(f"\nTotal files fixed: {fixed_count}")

    # Also need to update pyproject.toml
    pyproject_path = project_root / "pyproject.toml"
    if pyproject_path.exists():
        content = pyproject_path.read_text()
        original = content
        content = content.replace('"deep_biblio_tools"', '"src"')
        content = content.replace("deep_biblio_tools = ", "src = ")
        if content != original:
            pyproject_path.write_text(content)
            print("Fixed pyproject.toml")


if __name__ == "__main__":
    main()
