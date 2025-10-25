#!/usr/bin/env python3
"""Analyze all Python scripts in the repository."""

import ast
from collections import defaultdict
from pathlib import Path


def analyze_script(file_path: Path) -> dict:
    """Analyze a single Python script."""
    try:
        content = file_path.read_text()
        tree = ast.parse(content)

        # Extract imports
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        # Count functions and classes
        functions = sum(
            1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        )
        classes = sum(
            1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
        )

        # Check for main block
        has_main = any(
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and node.test.left.id == "__name__"
            for node in ast.walk(tree)
        )

        return {
            "imports": sorted(set(imports)),
            "functions": functions,
            "classes": classes,
            "has_main": has_main,
            "lines": len(content.splitlines()),
        }
    except Exception as e:
        return {"error": str(e)}


def main():
    """Analyze all scripts."""
    scripts_dir = Path(__file__).parent
    archive_dir = scripts_dir / "archive"

    # Categorize scripts
    categories = defaultdict(list)

    # Bibliography-related keywords
    bib_keywords = ["bib", "citation", "reference", "bibliography", "ref"]

    # Conversion-related keywords
    conv_keywords = ["convert", "md_to", "to_latex", "to_lyx", "markdown"]

    # Get all Python files
    all_scripts = list(scripts_dir.glob("*.py"))
    archive_scripts = list(archive_dir.glob("*.py"))

    print(f"Total scripts in scripts/: {len(all_scripts)}")
    print(f"Total scripts in archive/: {len(archive_scripts)}")
    print(f"Grand total: {len(all_scripts) + len(archive_scripts)}")

    # Analyze active scripts
    print("\n## Active Scripts Analysis")
    print("-" * 80)

    for script in sorted(all_scripts):
        if script.name == "analyze_scripts.py":
            continue

        analysis = analyze_script(script)

        # Categorize
        name_lower = script.name.lower()
        if any(kw in name_lower for kw in bib_keywords):
            categories["bibliography"].append(script.name)
        elif any(kw in name_lower for kw in conv_keywords):
            categories["conversion"].append(script.name)
        elif "test_" in name_lower:
            categories["testing"].append(script.name)
        elif "drone" in name_lower:
            categories["domain-specific"].append(script.name)
        else:
            categories["utility"].append(script.name)

        if "error" not in analysis:
            print(f"\n{script.name}:")
            print(f"  Lines: {analysis['lines']}")
            print(f"  Functions: {analysis['functions']}")
            print(f"  Classes: {analysis['classes']}")
            print(f"  Has main: {analysis['has_main']}")
            if analysis["imports"]:
                key_imports = [
                    imp
                    for imp in analysis["imports"]
                    if imp.startswith(("bibtex", "src", "deep_biblio"))
                ]
                if key_imports:
                    print(f"  Key imports: {', '.join(key_imports[:5])}")

    print("\n## Category Summary")
    print("-" * 80)
    for category, scripts in sorted(categories.items()):
        print(f"{category.capitalize()}: {len(scripts)} scripts")
        for script in sorted(scripts)[:5]:
            print(f"  - {script}")
        if len(scripts) > 5:
            print(f"  ... and {len(scripts) - 5} more")


if __name__ == "__main__":
    main()
