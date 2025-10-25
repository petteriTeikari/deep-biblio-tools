#!/usr/bin/env python3
"""Audit ALL regex usage in deep-biblio-tools source files."""

from pathlib import Path


def audit_regex():
    """Find all Python files with ACTIVE regex usage."""
    src_dir = Path("src")
    results = {
        "active_imports": [],
        "active_usage": [],
        "commented": [],
        "clean": [],
    }

    for py_file in src_dir.rglob("*.py"):
        with open(py_file, encoding="utf-8") as f:
            lines = f.readlines()

        has_active_import = False
        has_active_usage = False
        has_commented = False

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Check for ACTIVE regex imports (not commented)
            if not stripped.startswith("#"):
                if "import re" in line or "from re import" in line:
                    has_active_import = True
                    results["active_imports"].append(
                        (str(py_file), i, line.strip())
                    )

                # Check for re. usage (but not "re" as part of other words)
                if (
                    " re." in line
                    or "\tre." in line
                    or "(re." in line
                    or "=re." in line
                ):
                    has_active_usage = True
                    results["active_usage"].append(
                        (str(py_file), i, line.strip())
                    )

            # Check for commented regex
            if stripped.startswith("#") and (
                "import re" in stripped or "Banned" in stripped
            ):
                has_commented = True

        if has_active_import or has_active_usage:
            pass  # Recorded above
        elif has_commented:
            results["commented"].append(str(py_file))
        else:
            results["clean"].append(str(py_file))

    # Print results
    print("=" * 80)
    print("REGEX AUDIT RESULTS")
    print("=" * 80)

    if results["active_imports"]:
        print("\nFAIL FILES WITH ACTIVE REGEX IMPORTS:")
        for file, line_no, line in results["active_imports"]:
            print(f"  {file}:{line_no}")
            print(f"    {line}")

    if results["active_usage"]:
        print("\nFAIL FILES WITH ACTIVE REGEX USAGE (re. calls):")
        seen_files = set()
        for file, line_no, line in results["active_usage"]:
            if file not in seen_files:
                print(f"  {file}")
                seen_files.add(file)

    if results["commented"]:
        print(
            f"\nPASS FILES WITH REGEX BANNED (commented out): {len(results['commented'])}"
        )

    if results["clean"]:
        print(f"\nPASS FILES WITH NO REGEX: {len(results['clean'])}")

    print("\n" + "=" * 80)
    print("SUMMARY:")
    print(f"  Active imports: {len(results['active_imports'])}")
    print(f"  Active usage: {len(results['active_usage'])}")
    print(f"  Regex banned: {len(results['commented'])}")
    print(f"  Clean files: {len(results['clean'])}")
    print("=" * 80)


if __name__ == "__main__":
    audit_regex()
