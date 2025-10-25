#!/usr/bin/env python3
"""
Generic pipeline runner for markdown to PDF conversion.
This script runs the entire conversion process from markdown to LaTeX to PDF.

Usage:
    python run_pipeline.py [input_file.md] [options]

Examples:
    python run_pipeline.py drone_data/DronePosition.md
    python run_pipeline.py UAD_data/v6_UAD.md
    python run_pipeline.py paper.md --output-dir output --style plainnat
"""

import argparse
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


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert markdown files to LaTeX and PDF with bibliography support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s drone_data/DronePosition.md
  %(prog)s UAD_data/v6_UAD.md --output-dir UAD_output
  %(prog)s paper.md --style plainnat --font-size 11pt
  %(prog)s paper.md --single-column --no-arxiv
        """,
    )

    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to the input markdown file",
    )

    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        default=None,
        help="Output directory (default: input_dir/input_name_complete)",
    )

    parser.add_argument(
        "--output-name",
        "-n",
        default=None,
        help="Output filename without extension (default: input filename)",
    )

    parser.add_argument(
        "--style",
        "-s",
        default="spbasic_pt",
        help="Bibliography style (default: spbasic_pt)",
    )

    parser.add_argument(
        "--font-size",
        default="10pt",
        choices=["10pt", "11pt", "12pt"],
        help="Font size (default: 10pt)",
    )

    parser.add_argument(
        "--single-column",
        action="store_true",
        help="Use single column layout instead of two columns",
    )

    parser.add_argument(
        "--no-arxiv",
        action="store_true",
        help="Disable arXiv-ready formatting",
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable citation caching",
    )

    parser.add_argument(
        "--author",
        default="Author Name",
        help="Author name for the document",
    )

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress verbose output",
    )

    return parser.parse_args()


def main():
    """Run the complete conversion pipeline."""
    # Parse arguments
    args = parse_arguments()

    # Validate input file
    if not args.input_file.exists():
        print(f"Error: Input file not found: {args.input_file}")
        return 1

    # Set output directory
    if args.output_dir is None:
        args.output_dir = (
            args.input_file.parent / f"{args.input_file.stem}_complete"
        )

    # Set output name
    if args.output_name is None:
        args.output_name = args.input_file.stem

    # Create output directory
    args.output_dir.mkdir(exist_ok=True)

    print("Starting complete pipeline conversion...")
    print(f"Input: {args.input_file}")
    print(f"Output directory: {args.output_dir}")
    print(f"Output name: {args.output_name}")
    print(f"Bibliography style: {args.style}")
    print(f"Font size: {args.font_size}")
    print(f"Layout: {'single-column' if args.single_column else 'two-column'}")
    print(f"ArXiv ready: {'no' if args.no_arxiv else 'yes'}")
    print("-" * 60)

    # Step 1: Convert markdown to LaTeX
    print("\nStep 1: Converting markdown to LaTeX...")
    converter = MarkdownToLatexConverter(
        output_dir=args.output_dir,
        concept_box_style=ConceptBoxStyle.PROFESSIONAL_BLUE,
        arxiv_ready=not args.no_arxiv,
        two_column=not args.single_column,
        prefer_arxiv=True,
        use_cache=not args.no_cache,
        bibliography_style=args.style,
        font_size=args.font_size,
        use_better_bibtex_keys=True,
    )

    try:
        tex_file = converter.convert(
            args.input_file,
            output_name=args.output_name,
            author=args.author,
            verbose=not args.quiet,
        )
        print(f"\n[SUCCESS] LaTeX file created: {tex_file}")

        # Step 2: Copy bibliography style file if it exists
        print("\nStep 2: Checking for bibliography style file...")
        bst_filename = f"{args.style}.bst"

        # Search for .bst file in multiple locations
        search_paths = [
            args.input_file.parent / bst_filename,  # Same dir as input
            Path("templates") / bst_filename,  # Templates directory
            Path(bst_filename),  # Project root
            Path("drone_data") / bst_filename,  # Legacy location
        ]

        bst_source = None
        for path in search_paths:
            if path.exists():
                bst_source = path
                break

        if bst_source:
            bst_dest = args.output_dir / bst_filename
            shutil.copy2(bst_source, bst_dest)
            print(f"[SUCCESS] Copied {bst_source} to {bst_dest}")
        else:
            print(f"[INFO] No custom .bst file found for style '{args.style}'")
            print(
                "       LaTeX will use its built-in style or you'll need to provide the .bst file"
            )

        # Step 3: Compile to PDF with proper BibTeX processing
        print("\nStep 3: Compiling to PDF...")
        pdf_file = compile_with_bibtex(tex_file, args.output_dir)

        if pdf_file and pdf_file.exists():
            print(f"\n[SUCCESS] PDF created successfully: {pdf_file}")
            print(f"  Size: {pdf_file.stat().st_size / 1024:.1f} KB")

            # Validate PDF quality
            if not args.quiet:
                print("\nValidating PDF quality...")
                validate_pdf_citations(pdf_file, tex_file)
        else:
            print("\n[WARNING] PDF compilation had issues")

        # Step 4: Analyze bibliography for placeholder entries
        print("\nStep 4: Analyzing bibliography for placeholder entries...")
        bib_file = args.output_dir / "references.bib"
        if bib_file.exists():
            analyze_bibliography(bib_file)

        # Step 5: Run citation validity test
        print("\nStep 5: Running citation validity test...")
        from scripts.test_citation_validity import (
            analyze_citation_validity,
            print_analysis_report,
        )

        citation_results = analyze_citation_validity(args.output_dir)
        print_analysis_report(citation_results, args.output_dir)

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
                    "et al. )",  # Malformed et al
                    "Author Name",
                    "and others",  # Our fallback
                ]
            ):
                placeholders.append(f"{current_key}: {line.strip()}")

    if placeholders:
        print(
            f"\nFound {len(placeholders)} entries that may need manual handling:"
        )
        for i, entry in enumerate(placeholders[:10]):
            print(f"  {i + 1}. {entry}")
        if len(placeholders) > 10:
            print(f"  ... and {len(placeholders) - 10} more")

        # Save placeholder list
        placeholder_file = bib_file.parent / "placeholder_entries.txt"
        with open(placeholder_file, "w") as f:
            f.write("Bibliography entries that need manual handling:\n")
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
            undefined_matches = []
            for line in log_content.split("\n"):
                if "Citation `" in line and "undefined" in line:
                    start_idx = line.find("Citation `") + len("Citation `")
                    end_idx = line.find("'", start_idx)
                    if start_idx > len("Citation `") - 1 and end_idx != -1:
                        undefined_matches.append(line[start_idx:end_idx])

            undefined_count = len(undefined_matches)

            if undefined_count > 0:
                print(
                    f"[WARNING] Found {undefined_count} undefined citations in PDF"
                )

                # Show first 10 undefined keys
                if undefined_matches:
                    print(
                        f"  First 10 undefined keys: {undefined_matches[:10]}"
                    )

                    # Check if these keys exist in the bibliography
                    bib_file = tex_file.parent / "references.bib"
                    if bib_file.exists():
                        with open(bib_file) as f:
                            bib_content = f.read()

                        missing_in_bib = []
                        for key in undefined_matches[:10]:
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
