#!/usr/bin/env python3
"""Convert DronePosition.md with limited citation fetching to avoid timeouts."""

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
    """Convert DronePosition.md with limited citation fetching."""
    # Input file
    input_file = project_root.parent / "drone_data" / "DronePosition.md"

    if not input_file.exists():
        print(f"Error: {input_file} not found")
        return 1

    # Output directory
    output_dir = project_root.parent / "drone_data" / "latex_output_limited"

    print("Converting DronePosition.md to LaTeX with LIMITED citation fetching")
    print("Will only fetch metadata for DOI-based citations (arXiv, CrossRef)")
    print("This avoids timeouts and 403 errors from general websites")
    print("")

    # Create converter without Zotero
    converter = MarkdownToLatexConverter(
        output_dir=output_dir,
        cache_dir=project_root.parent / "cache",
        concept_box_style=ConceptBoxStyle.PROFESSIONAL_BLUE,
        arxiv_ready=True,
        two_column=True,
        bibliography_style="spbasic_pt",
        use_cache=True,
        use_better_bibtex_keys=True,
        font_size="11pt",
        zotero_api_key=None,
        zotero_library_id=None,
    )

    # Statistics
    citations_processed = 0
    citations_fetched = 0
    citations_skipped = 0

    # Patch the fetch method to only fetch DOI-based citations
    original_fetch = converter.citation_manager.fetch_citation_metadata

    def selective_fetch(citation):
        nonlocal citations_processed, citations_fetched, citations_skipped

        citations_processed += 1

        # Only fetch if it has a DOI or is from arxiv
        url = citation.url.lower()
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
                # Check for rate limiting
                if "429" in str(e):
                    print(
                        f"\nWARNING: Rate limited after {citations_fetched} citations!"
                    )
                    raise Exception("Rate limited - aborting")
                # Skip on other errors
                pass

        # For non-DOI citations, just use basic info
        citations_skipped += 1
        citation.title = citation.authors or "Reference"
        citation.bibtex_type = "misc"

        if citations_processed % 50 == 0:
            print(
                f"  Progress: {citations_processed} citations processed "
                + f"({citations_fetched} fetched, {citations_skipped} skipped)"
            )

        return citation

    converter.citation_manager.fetch_citation_metadata = selective_fetch

    try:
        print("Starting conversion...")
        print("Will only fetch metadata for citations with DOIs or from arXiv")
        print("")

        output_path = converter.convert(
            markdown_file=input_file,
            output_name="DronePosition",
            author="Petteri Teikari, Mike Jarrell, Irene Bandera Moreno, Harri Pesola",
            verbose=True,
        )

        print("\nConversion successful!")
        print(f"Output: {output_path}")
        print(f"Bibliography: {output_dir / 'references.bib'}")
        print("\nStatistics:")
        print(f"  Total citations: {citations_processed}")
        print(f"  Metadata fetched: {citations_fetched} (DOI/arXiv only)")
        print(f"  Basic entries: {citations_skipped} (websites, books, etc.)")

        return 0

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        print(f"Processed {citations_processed} citations")
        return 1

    except Exception as e:
        print(f"\nError: {e}")
        if citations_processed > 0:
            print(f"Processed {citations_processed} citations before error")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
