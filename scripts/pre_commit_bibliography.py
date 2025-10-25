#!/usr/bin/env python3
"""
Pre-commit hook for bibliography integrity validation.

This hook runs the bibliography integrity validator before commits
to ensure that bibliography issues are caught early.
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Main pre-commit hook function."""
    # Find LaTeX and BibTeX files in the repository
    tex_files = list(Path(".").rglob("*.tex"))
    bib_files = list(Path(".").rglob("*.bib"))

    if not tex_files:
        print("No LaTeX files found, skipping bibliography check.")
        return 0

    if not bib_files:
        print("No bibliography files found, skipping bibliography check.")
        return 0

    # Run validation for each tex/bib pair
    exit_code = 0
    for tex_file in tex_files:
        # Find corresponding bib file (assume same directory)
        bib_file = tex_file.parent / "references.bib"
        if not bib_file.exists():
            # Try to find any bib file in the same directory
            local_bibs = list(tex_file.parent.glob("*.bib"))
            if local_bibs:
                bib_file = local_bibs[0]
            else:
                continue

        print(f"Validating bibliography for {tex_file}...")

        # Run the bibliography integrity test
        test_script = (
            Path(__file__).parent / "tests" / "test_bibliography_integrity.py"
        )
        if not test_script.exists():
            print(
                f"Warning: Bibliography test script not found at {test_script}"
            )
            continue

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    str(test_script),
                    str(tex_file),
                    str(bib_file),
                    "--quiet",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                print(f"X Bibliography validation failed for {tex_file}")
                print("Run the following command for details:")
                print(f"  python {test_script} {tex_file} {bib_file}")
                exit_code = 1
            else:
                print(f"+ Bibliography validation passed for {tex_file}")

        except Exception as e:
            print(f"Error running bibliography validation: {e}")
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
