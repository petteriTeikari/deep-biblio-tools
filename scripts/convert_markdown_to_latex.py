#!/usr/bin/env python3
"""Main script for converting markdown to LaTeX with bibliography extraction.

This is the consolidated script that combines all conversion functionality:
- Citation extraction and validation (for LLM-generated content)
- Bibliography generation with metadata fetching
- LaTeX formatting and compilation
- Multiple output modes (fast, limited, full)

IMPORTANT: This script assumes markdown may contain LLM-generated citations
with potentially hallucinated author names. Use --validate flag to verify.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import argparse
import shutil
import subprocess
from datetime import datetime

from scripts.fix_bibliography import BibliographyFixer
from scripts.pdf_citation_corrector import PDFCitationCorrector
from src.deep_biblio_tools.converters.md_to_latex.converter import (
    MarkdownToLatexConverter,
)


def write_validation_report(fixer: BibliographyFixer, output_dir: Path) -> None:
    """Write validation report from bibliography fixer."""
    report_file = output_dir / "VALIDATION_REPORT.md"

    with open(report_file, "w") as f:
        f.write("# Bibliography Validation Report\n\n")
        f.write(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        )

        f.write("## Statistics\n\n")
        for key, value in fixer.stats.items():
            f.write(f"- {key}: {value}\n")

        if hasattr(fixer, "validator") and hasattr(
            fixer.validator, "validation_cache"
        ):
            f.write("\n## Validation Details\n\n")
            failed = []
            hallucinated = []

            for key, result in fixer.validator.validation_cache.items():
                if (
                    result.validation_status == "failed"
                    and result.confidence_score < 0.5
                ):
                    hallucinated.append((key, result))
                elif result.validation_status == "failed":
                    failed.append((key, result))

            if hallucinated:
                f.write(f"### Hallucinated Entries ({len(hallucinated)})\n\n")
                for key, result in hallucinated[:10]:  # Show first 10
                    f.write(f"- **{key}**: ")
                    if result.validated_authors:
                        f.write(
                            f"Corrected to: {', '.join(result.validated_authors)}\n"
                        )
                    else:
                        f.write("Could not determine correct authors\n")

            if failed:
                f.write(f"\n### Failed Validations ({len(failed)})\n\n")
                for key, result in failed[:10]:  # Show first 10
                    f.write(
                        f"- **{key}**: {result.error_message or 'Unknown error'}\n"
                    )

    print(f"Validation report written to: {report_file}")


def compile_latex_with_feedback(
    tex_file: Path, bib_file: Path, debug: bool = False, max_iterations: int = 3
) -> tuple[Path | None, dict]:
    """Compile LaTeX to PDF with iterative error fixing.

    Returns:
        Tuple of (pdf_path, compilation_results)
    """
    print("\nCompiling LaTeX to PDF with quality checks...")

    corrector = PDFCitationCorrector(debug=debug)
    pdf_file = None
    all_results = []

    for iteration in range(max_iterations):
        print(f"\nCompilation iteration {iteration + 1}/{max_iterations}...")

        # Compile and analyze
        compilation_results = corrector.compile_latex(
            tex_file, engine="xelatex"
        )
        all_results.append(compilation_results)

        # Check if successful
        if compilation_results["success"]:
            pdf_file = tex_file.with_suffix(".pdf")
            print("PDF compilation successful!")
            break

        # Analyze bibliography issues
        bib_issues = corrector.analyze_bibliography(bib_file)

        # Generate report for this iteration
        corrector.generate_report(tex_file, compilation_results, bib_issues)

        # If we have errors and haven't reached max iterations, try to fix
        if iteration < max_iterations - 1:
            if compilation_results["undefined_citations"] or any(
                bib_issues.values()
            ):
                print(
                    f"\nAttempting to fix {len(compilation_results['undefined_citations'])} undefined citations and bibliography issues..."
                )

                # Fix bibliography
                fixed_bib = corrector.fix_bibliography(
                    bib_file, bib_issues, compilation_results
                )

                # Update the bibliography file for next iteration
                shutil.copy2(fixed_bib, bib_file)
                print(f"Updated bibliography: {bib_file}")
            else:
                # No fixable issues found
                print("No automatic fixes available for remaining errors.")
                break

    # Prepare final results
    final_results = {
        "pdf_created": pdf_file is not None and pdf_file.exists(),
        "iterations": len(all_results),
        "final_status": all_results[-1],
        "all_iterations": all_results,
    }

    return pdf_file, final_results


def compile_latex(tex_file: Path, debug: bool = False) -> Path | None:
    """Legacy compile function for backward compatibility."""
    print("\nCompiling LaTeX to PDF...")

    # Use xelatex for better UTF-8 support
    cmd = ["xelatex", "-interaction=nonstopmode", str(tex_file)]

    # Change to the directory containing the tex file
    original_dir = Path.cwd()
    tex_dir = tex_file.parent

    try:
        import os

        os.chdir(tex_dir)

        # Run twice for references
        for i in range(2):
            if debug:
                print(f"  Pass {i + 1}/2...")

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0 and debug:
                print("LaTeX compilation warnings/errors:")
                print(result.stdout[-2000:])  # Last 2000 chars

        # Check for PDF
        pdf_file = tex_file.with_suffix(".pdf")
        if pdf_file.exists():
            return pdf_file
        else:
            if debug:
                log_file = tex_file.with_suffix(".log")
                if log_file.exists():
                    print(f"Check log file for errors: {log_file}")
            return None

    finally:
        os.chdir(original_dir)


def convert_markdown_to_latex(
    input_file: Path,
    output_dir: Path | None = None,
    mode: str = "full",
    validate: bool = False,
    style: str = "spbasic_pt",
    compile_pdf: bool = True,
    debug: bool = False,
    auto_fix_pdf: bool = True,
    max_fix_iterations: int = 3,
) -> Path:
    """Convert markdown to LaTeX with citation extraction and validation.

    Args:
        input_file: Markdown file to convert
        output_dir: Output directory (default: same as input)
        mode: Conversion mode - 'minimal', 'limited', or 'full'
        validate: Whether to validate citations (for LLM content)
        style: Bibliography style
        compile_pdf: Whether to compile to PDF
        debug: Enable debug output

    Returns:
        Path to generated LaTeX file
    """
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    # Set output directory
    if output_dir is None:
        output_dir = input_path.parent / f"latex_output_{mode}"
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nConverting {input_path.name} using {mode} mode...")
    print(f"Output directory: {output_dir}")

    # Initialize converter
    converter = MarkdownToLatexConverter(
        output_dir=output_dir,
        bibliography_style=style,
        arxiv_ready=True,
        two_column=True,
    )

    # Convert to LaTeX
    latex_file = converter.convert(
        input_path, output_name=input_path.stem + ".tex"
    )

    # Extract bibliography if it exists
    bib_file = output_dir / "references.bib"
    fixer = None  # Initialize fixer for later use

    if converter.citation_manager.citations:
        print(f"\nFound {len(converter.citation_manager.citations)} citations")

        # Fix bibliography formatting
        if mode in ["limited", "full"]:
            print("\nFixing bibliography formatting...")
            fixer = BibliographyFixer(validate=validate, add_notes=True)
            fixed_bib = fixer.fix_bibliography_file(bib_file)

            # Replace original with fixed version
            shutil.move(fixed_bib, bib_file)

            if validate:
                # Write validation report
                write_validation_report(fixer, output_dir)

                # Write list of hallucinated entries
                if hasattr(fixer, "validator") and hasattr(
                    fixer.validator, "validation_cache"
                ):
                    hallucinated = []
                    for key, result in fixer.validator.validation_cache.items():
                        if (
                            result.validation_status == "failed"
                            and result.confidence_score < 0.5
                        ):
                            hallucinated.append(f"@{key}")

                    if hallucinated:
                        hallucinated_file = (
                            output_dir / "hallucinated_entries.txt"
                        )
                        with open(hallucinated_file, "w") as f:
                            f.write("\n".join(sorted(hallucinated)) + "\n")
                        print(
                            f"\nFound {len(hallucinated)} hallucinated entries"
                        )
                        print(f"List saved to: {hallucinated_file}")

    # Compile to PDF if requested
    if compile_pdf:
        if bib_file.exists() and auto_fix_pdf:
            # Use the new feedback system if we have a bibliography
            pdf_file, compilation_results = compile_latex_with_feedback(
                latex_file,
                bib_file,
                debug=debug,
                max_iterations=max_fix_iterations,
            )

            # Write comprehensive compilation report
            compilation_report = output_dir / "PDF_QUALITY_REPORT.md"
            with open(compilation_report, "w") as f:
                f.write("# Comprehensive Quality Report\n\n")
                f.write(
                    f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
                f.write(f"**Input File**: {input_file.name}\n")
                f.write(f"**LaTeX File**: {latex_file.name}\n")
                f.write(f"**Mode**: {mode}\n")
                f.write(
                    f"**Validation**: {'Enabled' if validate else 'Disabled'}\n\n"
                )

                # PDF Compilation Summary
                f.write("## PDF Compilation Summary\n\n")
                f.write(
                    f"**PDF Created**: {'Yes' if compilation_results['pdf_created'] else 'No'}\n"
                )
                f.write(
                    f"**Iterations Required**: {compilation_results['iterations']}\n"
                )
                f.write(
                    f"**Final Status**: {'Success' if compilation_results['final_status']['success'] else 'Failed'}\n\n"
                )

                # Citation Statistics
                if converter.citation_manager.citations:
                    f.write("## Citation Statistics\n\n")
                    f.write(
                        f"**Total Citations Found**: {len(converter.citation_manager.citations)}\n"
                    )
                    if validate and fixer and hasattr(fixer, "stats"):
                        for key, value in fixer.stats.items():
                            f.write(f"**{key}**: {value}\n")
                    f.write("\n")

                # Initialize hallucinated_entries for later use
                hallucinated_entries = []

                # Validation Results (if enabled)
                if (
                    validate
                    and fixer
                    and hasattr(fixer, "validator")
                    and hasattr(fixer.validator, "validation_cache")
                ):
                    f.write("## Citation Validation Results\n\n")

                    # Count validation statuses
                    validated = failed = unknown = 0
                    confidence_scores = []

                    for (
                        result
                    ) in fixer.validator.validation_cache.get_all_results():
                        if result.validation_status == "validated":
                            validated += 1
                        elif result.validation_status == "failed":
                            failed += 1
                        else:
                            unknown += 1
                        if result.confidence_score is not None:
                            confidence_scores.append(result.confidence_score)

                    f.write(f"- **Validated**: {validated}\n")
                    f.write(f"- **Failed**: {failed}\n")
                    f.write(f"- **Unknown**: {unknown}\n")

                    if confidence_scores:
                        avg_confidence = sum(confidence_scores) / len(
                            confidence_scores
                        )
                        f.write(
                            f"- **Average Confidence**: {avg_confidence:.2f}\n"
                        )

                    # List likely hallucinated entries
                    if hasattr(fixer.validator.validation_cache, "cache"):
                        for (
                            key,
                            result,
                        ) in fixer.validator.validation_cache.cache.items():
                            if (
                                result.validation_status == "failed"
                                and result.confidence_score < 0.5
                            ):
                                hallucinated_entries.append((key, result))

                    if hallucinated_entries:
                        f.write(
                            f"\n### Likely Hallucinated Entries ({len(hallucinated_entries)})\n\n"
                        )
                        for key, result in hallucinated_entries[:10]:
                            f.write(f"- `{key}`: {result.validation_message}\n")
                        if len(hallucinated_entries) > 10:
                            f.write(
                                f"- ... and {len(hallucinated_entries) - 10} more\n"
                            )
                    f.write("\n")

                # PDF Compilation Details
                if compilation_results["iterations"] > 1:
                    f.write("## Issues Fixed During Compilation\n\n")
                    for i, iteration in enumerate(
                        compilation_results["all_iterations"][:-1]
                    ):
                        if (
                            iteration["undefined_citations"]
                            or iteration["errors"]
                        ):
                            f.write(f"### Iteration {i + 1}\n")
                            if iteration["undefined_citations"]:
                                f.write(
                                    f"- Fixed {len(iteration['undefined_citations'])} undefined citations\n"
                                )
                            if iteration["errors"]:
                                f.write(
                                    f"- Encountered {len(iteration['errors'])} LaTeX errors\n"
                                )
                    f.write("\n")

                # Final unresolved issues
                final = compilation_results["final_status"]
                if not final["success"]:
                    f.write("## Unresolved Issues\n\n")
                    if final["undefined_citations"]:
                        f.write(
                            f"### Undefined Citations ({len(final['undefined_citations'])})\n"
                        )
                        for cite in final["undefined_citations"][:10]:
                            f.write(f"- `{cite}`\n")
                        if len(final["undefined_citations"]) > 10:
                            f.write(
                                f"- ... and {len(final['undefined_citations']) - 10} more\n"
                            )
                        f.write("\n")
                    if final["errors"]:
                        f.write(f"### LaTeX Errors ({len(final['errors'])})\n")
                        for error in final["errors"][:5]:
                            f.write(f"- {error['message']}\n")
                        if len(final["errors"]) > 5:
                            f.write(
                                f"- ... and {len(final['errors']) - 5} more\n"
                            )
                        f.write("\n")

                # Recommendations
                f.write("## Recommendations\n\n")
                if not compilation_results["pdf_created"]:
                    f.write(
                        "1. **PDF Generation Failed**: Review the unresolved issues above\n"
                    )
                if validate and hallucinated_entries:
                    f.write(
                        "2. **Hallucinated Citations**: Consider removing or manually correcting entries with low confidence\n"
                    )
                if final.get("undefined_citations"):
                    f.write(
                        "3. **Undefined Citations**: Check that all \\cite{} commands match bibliography keys\n"
                    )
                if compilation_results["iterations"] >= max_fix_iterations:
                    f.write(
                        "4. **Max Iterations Reached**: Some issues may require manual intervention\n"
                    )

                # File locations
                f.write("\n## Generated Files\n\n")
                f.write(f"- LaTeX: `{latex_file.relative_to(output_dir)}`\n")
                if bib_file.exists():
                    f.write(
                        f"- Bibliography: `{bib_file.relative_to(output_dir)}`\n"
                    )
                if pdf_file:
                    f.write(f"- PDF: `{pdf_file.relative_to(output_dir)}`\n")

                # List any other reports
                for report in output_dir.glob("*.md"):
                    if report != compilation_report:
                        f.write(
                            f"- Report: `{report.relative_to(output_dir)}`\n"
                        )

            print(f"\nCompilation report: {compilation_report}")

            if pdf_file:
                print(f"\nPDF generated: {pdf_file}")
            else:
                print(
                    "\nPDF compilation failed after all fix attempts - check reports for details"
                )
        else:
            # Fall back to simple compilation if no bibliography
            pdf_file = compile_latex(latex_file, debug=debug)
            if pdf_file:
                print(f"\nPDF generated: {pdf_file}")
            else:
                print("\nPDF compilation failed - check .log file")

    return latex_file


def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Convert markdown to LaTeX with bibliography extraction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Conversion modes:
  minimal   - Fast conversion, no metadata fetching
  limited   - Fetch metadata only for DOI/arXiv
  full      - Fetch metadata from all available sources

Examples:
  # Fast conversion without metadata
  %(prog)s document.md --mode minimal

  # Convert with validation (for LLM content)
  %(prog)s document.md --validate

  # Limited mode with specific output
  %(prog)s document.md --mode limited -o output_dir/
""",
    )

    parser.add_argument("input", type=Path, help="Input markdown file")
    parser.add_argument(
        "-o", "--output-dir", type=Path, help="Output directory"
    )
    parser.add_argument(
        "--mode",
        choices=["minimal", "limited", "full"],
        default="full",
        help="Conversion mode (default: full)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate citations (for LLM-generated content)",
    )
    parser.add_argument(
        "--style",
        default="spbasic_pt",
        help="Bibliography style (default: spbasic_pt)",
    )
    parser.add_argument(
        "--no-pdf", action="store_true", help="Skip PDF compilation"
    )
    parser.add_argument(
        "--no-auto-fix",
        action="store_true",
        help="Disable automatic bibliography fixing during PDF compilation",
    )
    parser.add_argument(
        "--max-fix-iterations",
        type=int,
        default=3,
        help="Maximum iterations for fixing PDF compilation errors (default: 3)",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Save debug information"
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: File not found: {args.input}")
        return 1

    try:
        tex_file = convert_markdown_to_latex(
            input_file=args.input,
            output_dir=args.output_dir,
            mode=args.mode,
            validate=args.validate,
            style=args.style,
            compile_pdf=not args.no_pdf,
            debug=args.debug,
            auto_fix_pdf=not args.no_auto_fix,
            max_fix_iterations=args.max_fix_iterations,
        )

        print(f"\nSuccess! LaTeX file: {tex_file}")
        return 0

    except Exception as e:
        print(f"\nError: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
