#!/usr/bin/env python3
"""Convert DronePosition.md and apply bibliography fixes."""

import subprocess
import sys
from pathlib import Path

# Add the src directory to the Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from src.converters.md_to_latex.concept_boxes import (
    ConceptBoxStyle,
)  # noqa: E402, I001
from src.converters.md_to_latex.converter import (
    MarkdownToLatexConverter,
)  # noqa: E402, I001


def main():
    """Convert DronePosition.md and fix bibliography."""
    # Input file
    input_file = project_root / "drone_data" / "DronePosition.md"

    if not input_file.exists():
        print(f"Error: {input_file} not found")
        return 1

    # Output directory
    output_dir = project_root / "drone_data" / "latex_output_final"

    print(
        "Step 1: Converting DronePosition.md to LaTeX with limited fetching..."
    )
    print("(Only fetching metadata for DOI/arXiv citations)")
    print("")

    # Create converter
    converter = MarkdownToLatexConverter(
        output_dir=output_dir,
        cache_dir=project_root / "cache",
        concept_box_style=ConceptBoxStyle.PROFESSIONAL_BLUE,
        arxiv_ready=True,
        two_column=True,
        bibliography_style="spbasic_pt",
        use_cache=True,
        use_better_bibtex_keys=True,
        font_size="11pt",
    )

    # Patch fetch to be selective
    original_fetch = converter.citation_manager.fetch_citation_metadata
    citations_processed = 0
    citations_fetched = 0
    citations_skipped = 0

    def selective_fetch(citation):
        nonlocal citations_processed, citations_fetched, citations_skipped

        citations_processed += 1
        url = citation.url.lower() if citation.url else ""

        # Only fetch if it has DOI or is from arxiv
        should_fetch = (
            citation.doi
            or "arxiv.org" in url
            or "doi.org" in url
            or "dx.doi.org" in url
        )

        if should_fetch:
            try:
                result = original_fetch(citation)
                citations_fetched += 1

                if citations_fetched % 10 == 0:
                    print(
                        f"  Fetched metadata for {citations_fetched} DOI/arXiv citations..."
                    )

                return result
            except Exception as e:
                if "429" in str(e):
                    print(
                        f"\nRate limited after {citations_fetched} citations!"
                    )
                    raise Exception("Rate limited - aborting")
                pass

        # For non-DOI citations, just use basic info
        citations_skipped += 1
        citation.title = citation.authors or "Reference"
        citation.bibtex_type = "misc"

        if citations_processed % 50 == 0:
            print(
                f"  Progress: {citations_processed} citations ({citations_fetched} fetched, {citations_skipped} skipped)"
            )

        return citation

    converter.citation_manager.fetch_citation_metadata = selective_fetch

    try:
        output_path = converter.convert(
            markdown_file=input_file,
            output_name="DronePosition",
            author="Petteri Teikari, Mike Jarrell, Irene Bandera Moreno, Harri Pesola",
            verbose=True,
        )

        print("\nConversion complete!")
        print(f"  Total citations: {citations_processed}")
        print(f"  Metadata fetched: {citations_fetched}")
        print(f"  Basic entries: {citations_skipped}")
        print(f"\nLaTeX file: {output_path}")
        print(f"Bibliography: {output_dir / 'references.bib'}")

    except Exception as e:
        print(f"Error during conversion: {e}")
        return 1

    # Step 2: Fix bibliography
    print("\n" + "=" * 60)
    print("Step 2: Applying bibliography fixes...")
    print("=" * 60 + "\n")

    bib_file = output_dir / "references.bib"
    fixed_file = output_dir / "references_fixed.bib"

    result = subprocess.run(
        [
            sys.executable,
            str(project_root / "scripts" / "fix_bibliography_fast.py"),
            str(bib_file),
            str(fixed_file),
        ],
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)

    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("SUCCESS! Conversion and fixes complete.")
        print("=" * 60)
        print("\nFinal files:")
        print(f"  LaTeX: {output_path}")
        print(f"  Original bibliography: {bib_file}")
        print(f"  Fixed bibliography: {fixed_file}")
        print(
            "\nTo use the fixed bibliography, update the LaTeX file to use 'references_fixed.bib'"
        )
        print("or copy the fixed file over the original:")
        print(f"  cp {fixed_file} {bib_file}")

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
