#!/usr/bin/env python3
"""Convert markdown to LaTeX with real-time citation validation.

This script assumes ALL citations from LLM-generated markdown contain
potentially hallucinated author names and validates each one during extraction.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import time

import pypandoc
from scripts.validate_llm_citations import CitationValidator, ValidationResult
from src.deep_biblio_tools.converters.md_to_latex.citation_manager import (
    CitationManager,
)
from src.deep_biblio_tools.converters.md_to_latex.citation_pattern import (
    extract_citation_text,
)
from src.deep_biblio_tools.converters.md_to_latex.latex_formatter import (
    LaTeXFormatter,
)
from tqdm import tqdm


class ValidatingCitationManager(CitationManager):
    """Citation manager that validates all citations during extraction."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validator = CitationValidator()
        self.validation_results: dict[str, ValidationResult] = {}
        self.validation_stats = {
            "total": 0,
            "validated": 0,
            "partial": 0,
            "failed": 0,
            "unvalidated": 0,
        }

    def extract_citations(self, text: str) -> None:
        """Extract citations with validation."""
        citations = []
        citation_pattern = self.citation_pattern

        for match in citation_pattern.finditer(text):
            citation_dict = match.groupdict()
            if citation_dict:
                author_text = citation_dict.get("author", "")
                # Extract authors assuming "et al" means incomplete
                if " et al" in author_text:
                    authors = [author_text.replace(" et al", "").strip()]
                else:
                    authors = [
                        a.strip()
                        for a in author_text.replace(" & ", " and ").split(
                            " and "
                        )
                    ]

                citation_dict["original_authors"] = authors
                citations.append(citation_dict)

        print(
            f"\nFound {len(citations)} citations to validate during extraction"
        )
        print("WARNING: Assuming ALL author names may be hallucinated!\n")

        # Process with progress bar
        with tqdm(total=len(citations), desc="Validating citations") as pbar:
            for citation in citations:
                self.validation_stats["total"] += 1

                # Create citation text for reference
                author = citation.get("author", "")
                year = citation.get("year", "")
                citation_text = extract_citation_text(author, year)
                url = citation.get("url", "")

                # Validate citation
                validation_result = self.validator.validate_citation(
                    citation_text=citation_text,
                    url=url,
                    original_authors=citation.get("original_authors", []),
                )

                self.validation_results[citation_text] = validation_result

                # Update stats
                self.validation_stats[validation_result.validation_status] += 1

                # If validation successful, update citation with validated data
                if (
                    validation_result.validated_authors
                    and validation_result.validation_status
                    in ["validated", "partial"]
                ):
                    # Update authors with validated names
                    citation["author"] = " and ".join(
                        validation_result.validated_authors
                    )
                    citation["validation_source"] = (
                        validation_result.validation_source
                    )
                    citation["validation_status"] = (
                        validation_result.validation_status
                    )

                    # Add other metadata if available
                    if validation_result.metadata:
                        for field in [
                            "title",
                            "journal",
                            "year",
                            "volume",
                            "pages",
                            "doi",
                        ]:
                            if (
                                field in validation_result.metadata
                                and validation_result.metadata[field]
                            ):
                                citation[field] = validation_result.metadata[
                                    field
                                ]
                else:
                    # Mark as needing manual verification
                    citation["validation_status"] = (
                        validation_result.validation_status
                    )
                    citation["validation_issues"] = "; ".join(
                        validation_result.issues[:3]
                    )

                # Add to citations
                self.citations[citation_text] = citation

                # Update progress with current stats
                pbar.set_postfix(
                    {
                        "OK": self.validation_stats["validated"],
                        "Partial": self.validation_stats["partial"],
                        "Failed": self.validation_stats["failed"],
                    }
                )
                pbar.update(1)

        print(
            f"\nValidation complete: {self.validation_stats['validated']} validated, "
            f"{self.validation_stats['failed']} failed/suspicious"
        )

    def fetch_metadata(self, citation: dict) -> dict:
        """Override to skip fetching if already validated."""
        if citation.get("validation_status") == "validated":
            # Already have good metadata from validation
            return citation

        # For non-validated entries, try regular metadata fetch
        # but add warning notes
        result = super().fetch_metadata(citation)

        if citation.get("validation_status") == "failed":
            if "note" not in result:
                result["note"] = ""
            result["note"] += (
                "; VALIDATION FAILED - authors may be hallucinated!"
            )
        elif citation.get("validation_status") == "unvalidated":
            if "note" not in result:
                result["note"] = ""
            result["note"] += (
                "; Could not validate - manual verification needed"
            )

        if citation.get("validation_issues"):
            if "note" not in result:
                result["note"] = ""
            result["note"] += f"; Issues: {citation['validation_issues']}"

        return result

    def get_validation_summary(self) -> str:
        """Get a summary of validation results."""
        total = self.validation_stats["total"]
        if total == 0:
            return "No citations validated"

        lines = [
            "\n" + "=" * 60,
            "CITATION VALIDATION SUMMARY",
            "=" * 60,
            f"Total citations:        {total}",
            f"Validated:             {self.validation_stats['validated']} ({self.validation_stats['validated'] / total * 100:.1f}%)",
            f"Partially validated:   {self.validation_stats['partial']} ({self.validation_stats['partial'] / total * 100:.1f}%)",
            f"Failed validation:     {self.validation_stats['failed']} ({self.validation_stats['failed'] / total * 100:.1f}%)",
            f"Could not validate:    {self.validation_stats['unvalidated']} ({self.validation_stats['unvalidated'] / total * 100:.1f}%)",
            "=" * 60,
        ]

        # Add examples of problematic citations
        problematic = [
            (k, v)
            for k, v in self.validation_results.items()
            if v.confidence_score < 0.5 and v.validated_authors
        ]

        if problematic:
            lines.extend(["\nLIKELY HALLUCINATED CITATIONS:", "-" * 40])

            for citation_key, result in problematic[:5]:
                lines.append(f"\n{citation_key}:")
                if result.original_authors:
                    lines.append(
                        f"  Markdown had:    {', '.join(result.original_authors)}"
                    )
                if result.validated_authors:
                    lines.append(
                        f"  Should be:       {', '.join(result.validated_authors)}"
                    )
                if result.issues:
                    lines.append(
                        f"  Issues:          {'; '.join(result.issues[:2])}"
                    )

        return "\n".join(lines)


def convert_markdown_with_validation(
    input_file: Path,
    output_dir: Path | None = None,
    style: str = "spbasic_pt",
    skip_metadata_fetch: bool = False,
) -> Path:
    """Convert markdown to LaTeX with citation validation."""

    # Setup output directory
    if output_dir is None:
        output_dir = (
            input_file.parent / f"latex_output_validated_{input_file.stem}"
        )
    output_dir.mkdir(exist_ok=True)

    print(f"Converting {input_file.name} with citation validation...")
    print(f"Output directory: {output_dir}")

    # Read input file
    with open(input_file, encoding="utf-8") as f:
        content = f.read()

    # Create citation manager with validation
    citation_manager = ValidatingCitationManager()

    # Extract and validate citations
    print("\nStep 1: Extracting and validating citations...")
    citation_manager.extract_citations(content)

    # Generate bibliography (with validated data)
    print("\nStep 2: Generating bibliography...")
    if not skip_metadata_fetch:
        # This will use already validated data where available
        bib_entries = citation_manager.generate_bibliography()
    else:
        bib_entries = citation_manager.generate_bibliography_minimal()

    # Save bibliography
    bib_file = output_dir / "references.bib"
    citation_manager.save_bibliography(bib_entries, bib_file)
    print(f"Bibliography saved to: {bib_file}")

    # Print validation summary
    print(citation_manager.get_validation_summary())

    # Convert to LaTeX
    print("\nStep 3: Converting to LaTeX...")

    # Pre-process content
    formatter = LaTeXFormatter()
    processed_content = formatter.preprocess_markdown(content)

    # Use pypandoc for conversion
    latex_content = pypandoc.convert_text(
        processed_content,
        "latex",
        format="markdown",
        extra_args=[
            "--standalone",
            "--biblatex",
            f"--biblio={bib_file}",
            "--top-level-division=chapter",
            "--wrap=preserve",
        ],
    )

    # Post-process LaTeX
    latex_content = formatter.postprocess_latex(latex_content, style=style)

    # Save LaTeX file
    tex_file = output_dir / f"{input_file.stem}.tex"
    with open(tex_file, "w", encoding="utf-8") as f:
        f.write(latex_content)

    print(f"\nLaTeX file saved to: {tex_file}")

    # Save validation report
    report_file = output_dir / "validation_report.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("CITATION VALIDATION REPORT\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Source file: {input_file}\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(citation_manager.get_validation_summary())

        # Add detailed results
        f.write("\n\nDETAILED VALIDATION RESULTS:\n")
        f.write("=" * 60 + "\n")

        for citation_key, result in citation_manager.validation_results.items():
            f.write(f"\n{citation_key}:\n")
            f.write(f"  Status: {result.validation_status}\n")
            f.write(f"  Source: {result.validation_source}\n")
            f.write(f"  Confidence: {result.confidence_score:.2f}\n")
            if result.original_authors:
                f.write(f"  Original: {', '.join(result.original_authors)}\n")
            if result.validated_authors:
                f.write(f"  Validated: {', '.join(result.validated_authors)}\n")
            if result.issues:
                f.write(f"  Issues: {'; '.join(result.issues)}\n")

    print(f"Validation report saved to: {report_file}")

    # Also save validation cache info
    print(
        f"\nValidation cache saved to: {citation_manager.validator.cache_file}"
    )
    print(f"API calls made: {citation_manager.validator.api_calls}")

    return tex_file


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert markdown to LaTeX with citation validation"
    )
    parser.add_argument("input", type=Path, help="Input markdown file")
    parser.add_argument(
        "-o", "--output-dir", type=Path, help="Output directory for LaTeX files"
    )
    parser.add_argument(
        "--style",
        default="spbasic_pt",
        help="Bibliography style (default: spbasic_pt)",
    )
    parser.add_argument(
        "--skip-metadata",
        action="store_true",
        help="Skip additional metadata fetching (use validation data only)",
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: File not found: {args.input}")
        return 1

    try:
        tex_file = convert_markdown_with_validation(
            args.input, args.output_dir, args.style, args.skip_metadata
        )

        print("\nConversion complete!")
        print(f"LaTeX file: {tex_file}")

        # Compile to PDF
        print("\nCompiling to PDF...")
        from src.deep_biblio_tools.converters.md_to_latex.pdf_compiler import (
            compile_latex_to_pdf,
        )

        pdf_path = compile_latex_to_pdf(tex_file)
        if pdf_path and pdf_path.exists():
            print(f"PDF generated: {pdf_path}")
        else:
            print("PDF compilation failed - check the .log file for errors")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
