#!/usr/bin/env python3
"""Ensure no regex is used for structured format parsing."""

import ast
import sys
from pathlib import Path

STRUCTURED_FORMATS = {
    "markdown": ["md", "markdown"],
    "latex": ["tex", "latex", "LaTeX"],
    "bibtex": ["bib", "bibtex", "BibTeX"],
    "xml": ["xml", "XML"],
    "json": ["json", "JSON"],
    "yaml": ["yaml", "yml"],
}

# These are simple patterns that are allowed
ALLOWED_PATTERNS = [
    # Year extraction
    r"\d{4}",
    r"^\d{4}$",
    # DOI pattern
    r"10\.\d+/",
    # arXiv ID
    r"\d{4}\.\d{4,5}",
    # Simple email
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
]


def check_file(filepath: Path) -> list[str]:
    """Check for regex parsing of structured formats."""
    errors = []

    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        # Parse AST to find regex usage
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return errors  # Skip files with syntax errors

        for node in ast.walk(tree):
            # Check for re module usage
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "re":
                        errors.extend(
                            check_regex_near_formats(filepath, content)
                        )

            # Check for regex patterns in function calls
            if isinstance(node, ast.Call):
                if hasattr(node.func, "attr") and node.func.attr in [
                    "compile",
                    "match",
                    "search",
                    "findall",
                    "sub",
                ]:
                    if hasattr(node.func, "value") and hasattr(
                        node.func.value, "id"
                    ):
                        if node.func.value.id == "re":
                            # Check if this is near structured format handling
                            line_no = node.lineno
                            if is_near_structured_format(content, line_no):
                                errors.append(
                                    f"{filepath}:{line_no}: "
                                    f"Regex used near structured format parsing"
                                )

    except Exception as e:
        print(f"Error checking {filepath}: {e}")

    return errors


def check_regex_near_formats(filepath: Path, content: str) -> list[str]:
    """Check if regex is used near structured format keywords."""
    errors = []
    lines = content.splitlines()

    for i, line in enumerate(lines, 1):
        # Skip comments
        if line.strip().startswith("#"):
            continue

        # Check if line mentions structured formats
        line_lower = line.lower()
        for fmt, keywords in STRUCTURED_FORMATS.items():
            if any(keyword in line_lower for keyword in keywords):
                # Look for regex patterns in surrounding lines
                start = max(0, i - 5)
                end = min(len(lines), i + 5)
                for j in range(start, end):
                    if "re." in lines[j] or "regex" in lines[j].lower():
                        # Check if it's an allowed pattern
                        if not any(
                            pattern in lines[j] for pattern in ALLOWED_PATTERNS
                        ):
                            errors.append(
                                f"{filepath}:{j + 1}: "
                                f"Possible regex parsing of {fmt} format"
                            )
                            break

    return errors


def is_near_structured_format(content: str, line_no: int) -> bool:
    """Check if a line number is near structured format handling."""
    lines = content.splitlines()
    context_range = 10  # Look within 10 lines

    start = max(0, line_no - context_range - 1)
    end = min(len(lines), line_no + context_range)

    for i in range(start, end):
        line_lower = lines[i].lower()
        for keywords in STRUCTURED_FORMATS.values():
            if any(keyword in line_lower for keyword in keywords):
                return True

    return False


def main():
    """Run checks on all Python files."""
    errors = []
    project_root = Path(__file__).parent.parent

    for py_file in (project_root / "src").rglob("*.py"):
        file_errors = check_file(py_file)
        errors.extend(file_errors)

    if errors:
        print("[FAIL] Regex parsing violations found:")
        for error in errors:
            print(f"  - {error}")
        print("\nUse AST-based parsers instead:")
        print("  - markdown-it-py for Markdown")
        print("  - pylatexenc for LaTeX")
        print("  - bibtexparser for BibTeX")
        sys.exit(1)
    else:
        print("[PASS] No regex parsing violations found!")


if __name__ == "__main__":
    main()
