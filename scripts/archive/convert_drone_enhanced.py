#!/usr/bin/env python3
"""Enhanced DronePosition.md to LaTeX converter with improved citation handling."""

import sys
from pathlib import Path

# Add the src directory to the Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from src.converters.md_to_latex.citation_manager import (
    Citation,  # noqa: E402, I001
)
from src.converters.md_to_latex.concept_boxes import (
    ConceptBoxStyle,
)  # noqa: E402, I001
from src.converters.md_to_latex.converter import (
    MarkdownToLatexConverter,
)  # noqa: E402, I001


def patch_citation_parsing(converter):
    """Patch the citation manager to better handle author names."""
    original_add = converter.citation_manager.add_citation

    def enhanced_add_citation(
        authors: str, year: str, url: str, key: str | None = None
    ) -> Citation:
        """Enhanced citation adding with better author parsing."""
        # Clean up authors - handle & separator
        if " & " in authors:
            # Don't modify the display format, but ensure it's clean
            authors = authors.strip()

        # Call original method
        citation = original_add(authors, year, url, key)

        # Additional processing for specific known issues
        if "Chatzidakis & Botton" in authors:
            citation.full_authors = "Chatzidakis, M. and Botton, G. A."
        elif "Alqudsi & Makaraci" in authors:
            citation.full_authors = "Alqudsi, Yunes and Makaraci, Murat"
        elif "Amin & Ahmad" in authors:
            citation.full_authors = "Amin, Moeness G. and Ahmad, Fauzia"
        elif "Arteaga & Kahr" in authors:
            citation.full_authors = "Arteaga, M. and Kahr, B."

        return citation

    converter.citation_manager.add_citation = enhanced_add_citation


def main():
    """Convert DronePosition.md to LaTeX with enhanced citation handling."""
    # Input file
    input_file = project_root / "drone_data" / "DronePosition.md"

    if not input_file.exists():
        print(f"Error: {input_file} not found")
        return 1

    # Output directory
    output_dir = project_root / "drone_data" / "latex_output_enhanced"

    # Create converter with limited metadata fetching
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

    # Apply patches
    patch_citation_parsing(converter)

    # Patch fetch method to be selective
    original_fetch = converter.citation_manager.fetch_citation_metadata

    def selective_fetch(citation):
        """Only fetch for DOI/arXiv citations to avoid timeouts."""
        url = citation.url.lower() if citation.url else ""

        # Check if it's a commercial source
        commercial_domains = [
            "biblus.accasoftware.com",
            "bimgym.com",
            "buildingandland.co.uk",
            "consumeraffairs.com",
            "researchgate.net",
            "medium.com",
            "linkedin.com",
        ]

        if any(domain in url for domain in commercial_domains):
            # Skip fetching for commercial sources
            citation.title = citation.authors or "Reference"
            citation.bibtex_type = "misc"
            return citation

        # Only fetch if it has DOI or is from arxiv
        should_fetch = (
            citation.doi
            or "arxiv.org" in url
            or "doi.org" in url
            or "dx.doi.org" in url
        )

        if should_fetch:
            return original_fetch(citation)
        else:
            # Basic info only
            citation.title = citation.authors or "Reference"
            citation.bibtex_type = "misc"
            return citation

    converter.citation_manager.fetch_citation_metadata = selective_fetch

    try:
        print("Converting DronePosition.md with enhanced citation handling...")
        print("- Better author name parsing")
        print("- Selective metadata fetching (DOI/arXiv only)")
        print("- Commercial source detection")
        print("")

        output_path = converter.convert(
            markdown_file=input_file,
            output_name="DronePosition",
            author="Petteri Teikari, Mike Jarrell, Irene Bandera Moreno, Harri Pesola",
            verbose=True,
        )

        print(f"\nConversion successful! Output written to: {output_path}")
        print(f"Bibliography file: {output_dir / 'references.bib'}")

        # Apply post-processing fixes
        print("\nApplying bibliography fixes...")
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                str(project_root / "scripts" / "fix_bibliography_fast.py"),
                str(output_dir / "references.bib"),
                str(output_dir / "references_final.bib"),
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("Bibliography fixes applied successfully!")
            print(f"Final bibliography: {output_dir / 'references_final.bib'}")
        else:
            print("Error applying bibliography fixes:")
            print(result.stderr)

        return 0

    except Exception as e:
        print(f"Error during conversion: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
