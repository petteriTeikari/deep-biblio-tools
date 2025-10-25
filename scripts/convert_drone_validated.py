#!/usr/bin/env python3
"""Convert DronePosition.md with citation validation."""

import sys
from pathlib import Path

# Add the src directory to Python path
src_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(src_path))

from scripts.validate_llm_citations import CitationValidator
from src.converters.md_to_latex.concept_boxes import (
    ConceptBoxStyle,
)
from src.converters.md_to_latex.converter import (
    MarkdownToLatexConverter,
)


def main():
    """Convert DronePosition.md with validation."""
    # Input and output paths
    input_file = Path("drone_data/DronePosition.md")
    output_dir = Path("drone_data/latex_output_validated")

    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        return 1

    print(f"Converting: {input_file}")
    print(f"Output directory: {output_dir}")
    print("\nIMPORTANT: Validating all citations for LLM hallucinations!\n")

    # Create converter
    converter = MarkdownToLatexConverter(
        output_dir=output_dir,
        concept_box_style=ConceptBoxStyle.PROFESSIONAL_BLUE,
        arxiv_ready=True,
        two_column=False,
        prefer_arxiv=True,
        use_cache=True,
        bibliography_style="spbasic_pt",
        font_size="12pt",
    )

    # Convert the file
    try:
        # First convert
        output_file = converter.convert(input_file)
        print(f"\nConversion complete: {output_file}")

        # Now validate the bibliography
        bib_file = output_dir / "references.bib"
        if bib_file.exists():
            print("\n" + "=" * 60)
            print("VALIDATING CITATIONS")
            print("=" * 60)

            validator = CitationValidator()
            results = validator.validate_bibliography_file(bib_file)

            # Generate validated bibliography
            validated_bib = validator.generate_validated_bibliography(
                bib_file, results
            )
            print(f"\nValidated bibliography: {validated_bib}")

            # Check for critical issues
            hallucinated = sum(
                1
                for r in results.values()
                if r.confidence_score < 0.5 and r.validated_authors
            )
            if hallucinated > 0:
                print(
                    f"\nWARNING: Found {hallucinated} likely hallucinated citations!"
                )
                print(
                    "Check the validated bibliography for entries marked with LOW CONFIDENCE"
                )

        return 0

    except Exception as e:
        print(f"Error during conversion: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
