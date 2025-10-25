#!/usr/bin/env python3
"""Convert DronePosition.md to LaTeX with Zotero integration."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

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

# Load environment variables from .env file
load_dotenv(project_root / ".env")


def main():
    """Convert DronePosition.md to LaTeX with Zotero."""
    # Get Zotero credentials from environment
    zotero_api_key = os.getenv("ZOTERO_API_KEY")
    zotero_library_id = os.getenv("ZOTERO_LIBRARY_ID")

    if not zotero_api_key or not zotero_library_id:
        print("WARNING: Zotero credentials not found in .env file")
        print("Please add ZOTERO_API_KEY and ZOTERO_LIBRARY_ID to .env file")
        print("Continuing without Zotero integration...")
    else:
        print(f"Using Zotero integration (Library ID: {zotero_library_id})")

    # Input file
    input_file = project_root / "drone_data" / "DronePosition.md"

    if not input_file.exists():
        print(f"Error: {input_file} not found")
        return 1

    # Output directory
    output_dir = project_root / "drone_data" / "latex_output_zotero"

    # Create converter with Zotero integration
    converter = MarkdownToLatexConverter(
        output_dir=output_dir,
        cache_dir=project_root / "cache",
        concept_box_style=ConceptBoxStyle.PROFESSIONAL_BLUE,
        arxiv_ready=True,
        two_column=True,
        bibliography_style="spbasic_pt",  # As per CLAUDE.md policy
        use_cache=True,
        use_better_bibtex_keys=True,
        font_size="11pt",
        zotero_api_key=zotero_api_key,
        zotero_library_id=zotero_library_id,
    )

    try:
        # Convert the file
        print("Converting DronePosition.md to LaTeX with Zotero integration...")
        print(
            "This may take several minutes due to the large number of citations..."
        )
        output_path = converter.convert(
            markdown_file=input_file,
            output_name="DronePosition",
            author="Petteri Teikari, Mike Jarrell, Irene Bandera Moreno, Harri Pesola",
            verbose=True,
        )

        print(f"\nConversion successful! Output written to: {output_path}")
        print(f"Bibliography file: {output_dir / 'references.bib'}")
        print("\nWith Zotero integration, the bibliography should contain:")
        print(
            "- Entries from your Zotero library (if matching citations found)"
        )
        print("- Metadata fetched via Zotero's translation server")
        print("- Fallback to CrossRef/arXiv for citations not in Zotero")

        return 0

    except Exception as e:
        print(f"Error during conversion: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
