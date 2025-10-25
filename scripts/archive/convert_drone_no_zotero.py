#!/usr/bin/env python3
"""Convert DronePosition.md to LaTeX without Zotero credentials (guest mode)."""

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
    """Convert DronePosition.md to LaTeX without Zotero credentials."""
    # Input file
    input_file = project_root / "drone_data" / "DronePosition.md"

    if not input_file.exists():
        print(f"Error: {input_file} not found")
        return 1

    # Output directory
    output_dir = project_root / "drone_data" / "latex_output_guest"

    print(
        "Converting DronePosition.md to LaTeX WITHOUT Zotero credentials (guest mode)"
    )
    print("This will use CrossRef, arXiv, and other public sources")
    print("Will abort if rate limiting is detected")
    print("")

    # Create converter WITHOUT Zotero integration
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
        zotero_api_key=None,  # No Zotero API key
        zotero_library_id=None,  # No Zotero library ID
    )

    # Monitor for rate limiting
    citations_processed = 0

    # Patch the fetch method to monitor progress and detect rate limiting
    original_fetch = converter.citation_manager.fetch_citation_metadata

    def fetch_with_monitoring(citation):
        nonlocal citations_processed

        try:
            result = original_fetch(citation)
            citations_processed += 1

            # Print progress every 25 citations
            if citations_processed % 25 == 0:
                print(f"  Processed {citations_processed} citations...")

            return result

        except Exception as e:
            error_msg = str(e).lower()
            # Check for rate limiting indicators
            if any(
                indicator in error_msg
                for indicator in ["429", "rate limit", "too many"]
            ):
                print(
                    f"\nWARNING: RATE LIMITING DETECTED after {citations_processed} citations!"
                )
                print(
                    "WARNING: Aborting metadata fetching to avoid being blocked."
                )
                raise Exception("Rate limited - aborting")

            # For other errors, just log and continue
            if citations_processed % 10 == 0:
                print(
                    f"  Warning: Failed to fetch metadata for citation {citations_processed}: {e}"
                )

            return citation

    converter.citation_manager.fetch_citation_metadata = fetch_with_monitoring

    try:
        # Convert the file
        print("Starting conversion...")
        print("Processing 642 citations without Zotero credentials...")
        print("")

        output_path = converter.convert(
            markdown_file=input_file,
            output_name="DronePosition",
            author="Petteri Teikari, Mike Jarrell, Irene Bandera Moreno, Harri Pesola",
            verbose=True,
        )

        print(f"\nConversion successful! Output written to: {output_path}")
        print(f"Bibliography file: {output_dir / 'references.bib'}")
        print(f"Processed {citations_processed} citations")

        return 0

    except KeyboardInterrupt:
        print("\nConversion interrupted by user")
        print(f"Processed {citations_processed} citations before interruption")
        return 1

    except Exception as e:
        if "rate limit" in str(e).lower():
            print("\nConversion aborted due to rate limiting")
            print(
                f"Successfully processed {citations_processed} citations before hitting limits"
            )
            print("\nThe partial output has been saved. To continue:")
            print("1. Wait 15-30 minutes for rate limits to reset")
            print("2. Run the script again (cached citations will be reused)")
        else:
            print(f"\nError during conversion: {e}")
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
