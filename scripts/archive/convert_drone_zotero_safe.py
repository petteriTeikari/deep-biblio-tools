#!/usr/bin/env python3
"""Convert DronePosition.md to LaTeX with Zotero integration and rate limit protection."""

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


class RateLimitError(Exception):
    """Raised when Zotero rate limits are hit."""

    pass


def main():
    """Convert DronePosition.md to LaTeX with Zotero."""
    # Get Zotero credentials from environment
    zotero_api_key = os.getenv("ZOTERO_API_KEY")
    zotero_library_id = os.getenv("ZOTERO_LIBRARY_ID")

    if not zotero_api_key or not zotero_library_id:
        print("ERROR: Zotero credentials not found in .env file")
        print("Please add ZOTERO_API_KEY and ZOTERO_LIBRARY_ID to .env file")
        return 1

    print(f"Using Zotero integration (Library ID: {zotero_library_id})")
    print("Will abort if rate limiting is detected.")

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

    # Patch the citation manager to detect rate limiting
    original_fetch = converter.citation_manager._fetch_from_crossref
    citations_processed = 0
    rate_limited = False

    def fetch_with_rate_limit_check(*args, **kwargs):
        nonlocal citations_processed, rate_limited

        # Check if we've been rate limited
        if rate_limited:
            raise RateLimitError("Aborting due to rate limiting")

        try:
            # Call the original method
            result = original_fetch(*args, **kwargs)
            citations_processed += 1

            # Print progress every 10 citations
            if citations_processed % 10 == 0:
                print(f"  Processed {citations_processed} citations...")

            return result

        except Exception as e:
            # Check for rate limiting indicators
            error_msg = str(e).lower()
            if any(
                indicator in error_msg
                for indicator in ["429", "rate limit", "too many"]
            ):
                rate_limited = True
                print(
                    "\nWARNING: RATE LIMITING DETECTED! Aborting metadata fetching."
                )
                raise RateLimitError(
                    f"Rate limited after {citations_processed} citations"
                )
            raise

    # Replace the method
    converter.citation_manager._fetch_from_crossref = (
        fetch_with_rate_limit_check
    )

    # Also monitor Zotero API responses
    if hasattr(converter.citation_manager, "zotero_client"):
        original_zotero_search = (
            converter.citation_manager.zotero_client.search_by_identifier
        )

        def zotero_search_with_monitoring(*args, **kwargs):
            nonlocal rate_limited
            import requests

            # Make the request but check for rate limiting
            try:
                # Get the original method's internals to check response
                result = original_zotero_search(*args, **kwargs)
                return result
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    rate_limited = True
                    print("\nWARNING: ZOTERO RATE LIMITING DETECTED! Aborting.")
                    raise RateLimitError("Zotero API rate limit hit")
                raise

        converter.citation_manager.zotero_client.search_by_identifier = (
            zotero_search_with_monitoring
        )

    try:
        # Convert the file
        print("Converting DronePosition.md to LaTeX with Zotero integration...")
        print("This will process 545+ citations. Will abort if rate limited.")
        print("")

        output_path = converter.convert(
            markdown_file=input_file,
            output_name="DronePosition",
            author="Petteri Teikari, Mike Jarrell, Irene Bandera Moreno, Harri Pesola",
            verbose=True,
        )

        print(f"\nConversion successful! Output written to: {output_path}")
        print(f"Bibliography file: {output_dir / 'references.bib'}")
        print(f"Processed {citations_processed} citations successfully")

        return 0

    except RateLimitError as e:
        print(f"\nConversion aborted: {e}")
        print(f"Processed {citations_processed} citations before rate limiting")
        print("\nTo continue:")
        print("1. Wait a few minutes for rate limits to reset")
        print("2. Run the script again (cached citations will be used)")
        return 1

    except KeyboardInterrupt:
        print("\nConversion interrupted by user")
        print(f"Processed {citations_processed} citations")
        return 1

    except Exception as e:
        print(f"\nError during conversion: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
