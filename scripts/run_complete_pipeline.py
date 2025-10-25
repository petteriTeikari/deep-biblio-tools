#!/usr/bin/env python3
"""Run complete pipeline from DronePosition.md to PDF."""

import os

# import re  # Banned - using string methods instead
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).resolve().parent
sys.path.insert(0, str(src_path))

from src.converters.md_to_latex.concept_boxes import (  # noqa: E402
    ConceptBoxStyle,
)
from src.converters.md_to_latex.converter import (  # noqa: E402
    MarkdownToLatexConverter,
)


def main():
    """Run the complete conversion pipeline."""
    # Configuration
    input_file = Path("drone_data/DronePosition.md")
    output_dir = Path("drone_data/DronePosition_complete")

    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        return 1

    # Create output directory
    output_dir.mkdir(exist_ok=True)

    print("Starting complete pipeline conversion...")
    print(f"Input: {input_file}")
    print(f"Output directory: {output_dir}")
    print("Bibliography style: spbasic_pt")
    print("-" * 60)

    # Step 1: Convert markdown to LaTeX
    print("\nStep 1: Converting markdown to LaTeX...")
    converter = MarkdownToLatexConverter(
        output_dir=output_dir,
        concept_box_style=ConceptBoxStyle.PROFESSIONAL_BLUE,
        arxiv_ready=True,
        two_column=True,  # Enable two-column format
        prefer_arxiv=True,
        use_cache=True,
        bibliography_style="spbasic_pt",  # Using spbasic_pt style
        font_size="10pt",  # Even smaller font for two-column as requested
        use_better_bibtex_keys=True,
    )

    try:
        tex_file = converter.convert(
            input_file,
            output_name="DronePosition",
            author="Author Name",
            verbose=True,
        )
        print(f"\n[SUCCESS] LaTeX file created: {tex_file}")

        # Step 2: Copy bibliography style file
        print("\nStep 2: Copying bibliography style file...")
        bst_source = Path("drone_data/spbasic_pt.bst")
        bst_dest = output_dir / "spbasic_pt.bst"
        if bst_source.exists():
            shutil.copy2(bst_source, bst_dest)
            print(f"[SUCCESS] Copied {bst_source} to {bst_dest}")
        else:
            print(f"[WARNING] {bst_source} not found")

        # Step 3: Compile to PDF with proper BibTeX processing
        print("\nStep 3: Compiling to PDF...")
        pdf_file = compile_with_bibtex(tex_file, output_dir)

        if pdf_file and pdf_file.exists():
            print(f"\n[SUCCESS] PDF created successfully: {pdf_file}")
            print(f"  Size: {pdf_file.stat().st_size / 1024:.1f} KB")

            # Validate PDF quality
            print("\nValidating PDF quality...")
            validate_pdf_citations(pdf_file, tex_file)
        else:
            print("\n[WARNING] PDF compilation had issues")

        # Step 4: Analyze bibliography for placeholder entries
        print("\nStep 4: Analyzing bibliography for placeholder entries...")
        bib_file = output_dir / "references.bib"
        if bib_file.exists():
            analyze_bibliography(bib_file)

        print("\n" + "=" * 60)
        print("Pipeline complete!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError during conversion: {e}")
        traceback.print_exc()
        return 1

    return 0


def compile_with_bibtex(tex_file: Path, output_dir: Path) -> Path | None:
    """Compile LaTeX to PDF with proper BibTeX processing."""

    # Save current directory
    original_dir = Path.cwd()
    pdf_file = tex_file.with_suffix(".pdf")

    try:
        # Change to output directory
        os.chdir(output_dir)

        # Compilation sequence: XeLaTeX -> BibTeX -> XeLaTeX -> XeLaTeX
        commands = [
            ["xelatex", "-interaction=nonstopmode", tex_file.name],
            ["bibtex", tex_file.stem],
            ["xelatex", "-interaction=nonstopmode", tex_file.name],
            ["xelatex", "-interaction=nonstopmode", tex_file.name],
        ]

        for i, cmd in enumerate(commands):
            print(f"  Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60
            )

            if result.returncode != 0:
                print(f"  [WARNING] {cmd[0]} returned code {result.returncode}")
                if i == 1:  # BibTeX warnings are often not critical
                    continue
                # Check if PDF exists anyway
                if pdf_file.exists():
                    print("  [INFO] PDF exists despite warning")
                else:
                    print(f"  [ERROR] {cmd[0]} failed")
                    # Print last part of output for debugging
                    if result.stdout:
                        print("  Last output:")
                        print(
                            "  " + "\n  ".join(result.stdout.split("\n")[-10:])
                        )
                    return None

        return pdf_file if pdf_file.exists() else None

    except Exception as e:
        print(f"  [ERROR] Compilation error: {e}")
        return None
    finally:
        # Return to original directory
        os.chdir(original_dir)


def analyze_bibliography(bib_file: Path):
    """Analyze bibliography for placeholder entries."""
    with open(bib_file, encoding="utf-8") as f:
        content = f.read()

    # Count total entries
    entries = (
        content.count("@article{")
        + content.count("@inproceedings{")
        + content.count("@book{")
        + content.count("@misc{")
        + content.count("@techreport{")
        + content.count("@phdthesis{")
    )
    print(f"\nTotal bibliography entries: {entries}")

    # Check for placeholder entries
    placeholders = []
    lines = content.split("\n")
    current_key = None

    for line in lines:
        if line.strip().startswith("@"):
            # Extract the citation key
            if line.strip().startswith("@") and "{" in line:
                start_idx = line.find("{")
                end_idx = line.find(",", start_idx)
                if start_idx != -1 and end_idx != -1:
                    current_key = line[start_idx + 1 : end_idx].strip()
        elif current_key and "author" in line.lower():
            # Check for placeholder author patterns
            if any(
                pattern in line
                for pattern in [
                    "Unknown",
                    "TODO",
                    "PLACEHOLDER",
                    ", .",
                    "et al.",
                    "Author Name",
                ]
            ):
                placeholders.append(f"{current_key}: {line.strip()}")

    if placeholders:
        print(
            f"\nFound {len(placeholders)} entries that may need manual Zotero handling:"
        )
        for i, entry in enumerate(placeholders[:10]):
            print(f"  {i + 1}. {entry}")
        if len(placeholders) > 10:
            print(f"  ... and {len(placeholders) - 10} more")

        # Save placeholder list
        placeholder_file = bib_file.parent / "placeholder_entries.txt"
        with open(placeholder_file, "w") as f:
            f.write("Bibliography entries that need manual Zotero handling:\n")
            f.write("=" * 60 + "\n\n")
            for entry in placeholders:
                f.write(entry + "\n")
        print(f"\nPlaceholder list saved to: {placeholder_file}")
    else:
        print("\nNo obvious placeholder entries found!")


def validate_pdf_citations(pdf_file: Path, tex_file: Path):
    """Validate that PDF has working citations."""
    try:
        # Check for undefined citations in the PDF
        log_file = tex_file.with_suffix(".log")
        if log_file.exists():
            with open(log_file, encoding="utf-8", errors="ignore") as f:
                log_content = f.read()

            # Count undefined citations
            undefined_count = log_content.count(
                "Citation"
            ) and log_content.count("undefined")
            if undefined_count > 0:
                print(
                    f"[WARNING] Found {undefined_count} undefined citations in PDF"
                )

                # Extract citation keys from log
                undefined_keys = []
                for line in log_content.split("\n"):
                    if "Citation" in line and "undefined" in line:
                        if "Citation `" in line and "' undefined" in line:
                            start_idx = line.find("Citation `") + len(
                                "Citation `"
                            )
                            end_idx = line.find("' undefined", start_idx)
                            if (
                                start_idx > len("Citation `") - 1
                                and end_idx != -1
                            ):
                                undefined_keys.append(line[start_idx:end_idx])

                if undefined_keys:
                    print(f"  First 10 undefined keys: {undefined_keys[:10]}")

                    # Check if these keys exist in the bibliography
                    bib_file = tex_file.parent / "references.bib"
                    if bib_file.exists():
                        with open(bib_file) as f:
                            bib_content = f.read()

                        missing_in_bib = []
                        for key in undefined_keys[:10]:
                            if f"{{{key}," not in bib_content:
                                missing_in_bib.append(key)

                        if missing_in_bib:
                            print(
                                f"  Keys missing from bibliography: {missing_in_bib}"
                            )
                        else:
                            print(
                                "  All checked keys exist in bibliography - may be a compilation issue"
                            )
            else:
                print("[SUCCESS] No undefined citations found in PDF")

    except Exception as e:
        print(f"[ERROR] Failed to validate PDF: {e}")


if __name__ == "__main__":
    sys.exit(main())
