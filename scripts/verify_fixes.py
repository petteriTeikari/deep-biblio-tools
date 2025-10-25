#!/usr/bin/env python3
"""Verify all fixes are in place."""

from pathlib import Path


def check_fixes():
    """Check if all fixes are properly implemented."""
    base_dir = Path(
        "/home/petteri/Dropbox/LABs/KusiKasa/github/deep-biblio-tools"
    )

    print("Checking implemented fixes...")

    # Check 1: Currency dollar escaping
    converter_file = (
        base_dir / "src/deep_biblio_tools/converters/md_to_latex/converter.py"
    )
    with open(converter_file) as f:
        content = f.read()
        if (
            "_escape_currency_dollars" in content
            and "ESCAPED_DOLLAR_PLACEHOLDER" in content
        ):
            print("[OK] Currency dollar escaping implemented")
        else:
            print("[FAIL] Currency dollar escaping NOT found")

    # Check 2: Unicode symbol handling
    latex_builder = (
        base_dir
        / "src/deep_biblio_tools/converters/md_to_latex/latex_builder.py"
    )
    with open(latex_builder) as f:
        content = f.read()
        if (
            "_restore_unicode_symbols" in content
            and "MULTIPLICATION_SIGN_PLACEHOLDER" in content
        ):
            print("[OK] Unicode symbol restoration implemented")
        else:
            print("[FAIL] Unicode symbol restoration NOT found")

    # Check 3: Better BibTeX keys
    utils_file = (
        base_dir / "src/deep_biblio_tools/converters/md_to_latex/utils.py"
    )
    with open(utils_file) as f:
        content = f.read()
        if (
            "use_better_bibtex" in content
            and "generate_citation_key" in content
        ):
            print("[OK] Better BibTeX key generation available")
        else:
            print("[FAIL] Better BibTeX key generation NOT found")

    # Check 4: Bibliography style in LaTeX builder
    with open(latex_builder) as f:
        content = f.read()
        if "bibliographystyle{spbasic_pt}" in content:
            print("[OK] spbasic_pt bibliography style is set")
        else:
            print("[FAIL] spbasic_pt bibliography style NOT set")
            # Let's check what style is used
            if "bibliographystyle" in content:
                # import re  # Banned - using string methods instead

                # Find \bibliographystyle{...} using string methods
                pos = content.find("\\bibliographystyle{")
                if pos != -1:
                    start = pos + 19  # len("\\bibliographystyle{")
                    end = content.find("}", start)
                    if end != -1:
                        style = content[start:end]
                        print(f"  Current style: {style}")

    print("\nAll checks complete.")


if __name__ == "__main__":
    check_fixes()
