#!/usr/bin/env python3
"""Validate import structure according to guardrails."""

import ast
import sys
from pathlib import Path


def check_imports(filepath: Path) -> list[str]:
    """Check import ordering and location."""
    errors = []

    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError):
        return errors  # Skip files with errors

    # Collect all imports with their line numbers
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import | ast.ImportFrom):
            imports.append((node.lineno, node))

    if not imports:
        return errors

    # Sort imports by line number
    imports.sort(key=lambda x: x[0])

    # Check if imports are at the top
    # Allow for module docstrings and comments
    first_non_import_line = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.ClassDef | ast.Assign):
            if (
                first_non_import_line is None
                or node.lineno < first_non_import_line
            ):
                first_non_import_line = node.lineno

    # Check for imports after code
    if first_non_import_line:
        for line_no, import_node in imports:
            if line_no > first_non_import_line:
                # Check if there's a comment about circular imports on the previous line
                lines = content.split("\n")
                if line_no > 1 and (
                    "circular" in lines[line_no - 2].lower()
                    or "avoid circular" in lines[line_no - 2].lower()
                ):
                    continue  # Skip this violation if it's marked as avoiding circular imports

                import_str = _format_import(import_node)
                errors.append(
                    f"{filepath}:{line_no}: Import after code: {import_str}"
                )

    # Check import ordering (stdlib → third-party → local)
    import_groups = _categorize_imports(imports, filepath)
    errors.extend(_check_import_order(import_groups, filepath))

    return errors


def _format_import(node):
    """Format import node as string."""
    if isinstance(node, ast.Import):
        names = [alias.name for alias in node.names]
        return f"import {', '.join(names)}"
    else:  # ImportFrom
        module = node.module or ""
        names = [alias.name for alias in node.names]
        return f"from {module} import {', '.join(names)}"


def _categorize_imports(imports, filepath):
    """Categorize imports into stdlib, third-party, and local."""
    stdlib = []
    third_party = []
    local = []

    # Common stdlib modules
    stdlib_modules = {
        "os",
        "sys",
        "re",
        "json",
        "time",
        "datetime",
        "pathlib",
        "collections",
        "itertools",
        "functools",
        "typing",
        "enum",
        "logging",
        "subprocess",
        "tempfile",
        "shutil",
        "glob",
        "ast",
        "inspect",
        "importlib",
        "abc",
        "copy",
        "math",
        "random",
        "string",
        "io",
        "csv",
        "xml",
        "urllib",
        "http",
        "html",
        "webbrowser",
        "argparse",
        "dataclasses",
        "hashlib",
        "sqlite3",
        "asyncio",
        "concurrent",
        "traceback",
    }

    # Local modules for this project
    local_modules = {
        "utils",
        "core",
        "parsers",
        "citations",
        "converters",
        "bibliography",
        "src",
    }

    for line_no, node in imports:
        if isinstance(node, ast.Import):
            module_name = node.names[0].name.split(".")[0]
        else:  # ImportFrom
            if node.level > 0:  # Relative import
                local.append((line_no, node))
                continue
            module_name = (node.module or "").split(".")[0]

        if module_name in stdlib_modules:
            stdlib.append((line_no, node))
        elif module_name.startswith("."):
            local.append((line_no, node))
        elif module_name in local_modules:
            local.append((line_no, node))
        else:
            # Assume third-party if not stdlib or local
            third_party.append((line_no, node))

    return {"stdlib": stdlib, "third_party": third_party, "local": local}


def _check_import_order(import_groups, filepath):
    """Check if imports follow stdlib → third-party → local order."""
    errors = []

    # Get the last line number of each group
    stdlib_last = max([imp[0] for imp in import_groups["stdlib"]], default=0)
    third_party_last = max(
        [imp[0] for imp in import_groups["third_party"]], default=0
    )
    max([imp[0] for imp in import_groups["local"]], default=0)

    # Check order violations
    for line_no, node in import_groups["third_party"]:
        if stdlib_last > 0 and line_no < stdlib_last:
            errors.append(
                f"{filepath}:{line_no}: Third-party import before stdlib imports"
            )

    for line_no, node in import_groups["local"]:
        if third_party_last > 0 and line_no < third_party_last:
            errors.append(
                f"{filepath}:{line_no}: Local import before third-party imports"
            )
        if stdlib_last > 0 and line_no < stdlib_last:
            errors.append(
                f"{filepath}:{line_no}: Local import before stdlib imports"
            )

    return errors


def main():
    """Run import validation on all Python files."""
    errors = []
    project_root = Path(__file__).parent.parent

    for py_file in (project_root / "src").rglob("*.py"):
        file_errors = check_imports(py_file)
        errors.extend(file_errors)

    if errors:
        print("[FAIL] Import violations found:")
        for error in errors:
            print(f"  - {error}")
        print("\nImports should be:")
        print("  1. At the top of the file")
        print("  2. Ordered: stdlib → third-party → local")
        sys.exit(1)
    else:
        print("[PASS] All imports properly structured!")


if __name__ == "__main__":
    main()
