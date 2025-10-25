#!/usr/bin/env python3
"""Convert DronePosition.md to LaTeX without fetching metadata (fast mode)."""

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
    """Convert DronePosition.md to LaTeX in fast mode."""
    # Input file
    input_file = project_root / "drone_data" / "DronePosition.md"

    if not input_file.exists():
        print(f"Error: {input_file} not found")
        return 1

    # Output directory
    output_dir = project_root / "drone_data" / "latex_output"

    # Create converter with caching disabled to avoid metadata fetching
    converter = MarkdownToLatexConverter(
        output_dir=output_dir,
        cache_dir=None,  # Disable caching
        concept_box_style=ConceptBoxStyle.PROFESSIONAL_BLUE,
        arxiv_ready=True,
        two_column=True,
        bibliography_style="spbasic_pt",  # As per CLAUDE.md policy
        use_cache=False,  # Disable cache to skip metadata fetching
        use_better_bibtex_keys=False,  # Use simple keys
        font_size="11pt",
    )

    # Patch the citation manager to skip metadata fetching

    def skip_fetch(citation):
        """Skip metadata fetching and just return basic info."""
        # Just create a basic entry without fetching
        citation.title = citation.authors or f"Reference {citation.key}"
        citation.metadata = {
            "title": citation.title,
            "year": citation.year or "2025",
            "author": citation.authors or "Author",
        }
        citation.bibtex_type = "misc"
        return citation

    # Replace the fetch method
    converter.citation_manager.fetch_citation_metadata = skip_fetch

    try:
        # Convert the file
        print(
            "Converting DronePosition.md to LaTeX (fast mode - no metadata fetching)..."
        )
        output_path = converter.convert(
            markdown_file=input_file,
            output_name="DronePosition",
            author="Petteri Teikari, Mike Jarrell, Irene Bandera Moreno, Harri Pesola",
            verbose=True,
        )

        print(f"\nConversion successful! Output written to: {output_path}")
        print(f"Bibliography file: {output_dir / 'references.bib'}")
        print(
            "\nNote: Bibliography entries are placeholders. Run full conversion with metadata fetching for complete bibliography."
        )

        return 0

    except Exception as e:
        print(f"Error during conversion: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
