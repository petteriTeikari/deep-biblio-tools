"""Export Zotero collection to BibTeX snapshot for golden dataset.

This script exports a frozen snapshot of the dpp-fashion Zotero collection
for use in deterministic testing. The snapshot ensures tests don't depend
on live Zotero API access.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv  # noqa: E402
from src.converters.md_to_latex.zotero_integration import (  # noqa: E402
    ZoteroClient,
)

# Load environment variables
load_dotenv()


def export_zotero_snapshot(
    collection_name: str = "dpp-fashion",
    output_path: Path | None = None,
) -> Path:
    """Export Zotero collection to BibTeX file.

    Args:
        collection_name: Name of Zotero collection to export
        output_path: Path to write BibTeX file (default: tests/fixtures/golden/bibliography/)

    Returns:
        Path to exported BibTeX file
    """
    if output_path is None:
        output_path = (
            project_root
            / "tests"
            / "fixtures"
            / "golden"
            / "bibliography"
            / f"{collection_name}-snapshot.bib"
        )

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Get Zotero credentials from environment
    api_key = os.getenv("ZOTERO_API_KEY")
    library_id = os.getenv("ZOTERO_LIBRARY_ID")
    library_type = os.getenv("ZOTERO_LIBRARY_TYPE", "user")

    if not api_key or not library_id:
        raise ValueError(
            "ZOTERO_API_KEY and ZOTERO_LIBRARY_ID must be set in environment"
        )

    print(f"Connecting to Zotero library: {library_id} ({library_type})")
    print(f"Exporting collection: {collection_name}")

    # Create client and fetch BibTeX
    client = ZoteroClient(
        api_key=api_key, library_id=library_id, library_type=library_type
    )

    bibtex_content = client.get_collection_bibtex(collection_name)

    # Count entries (simple count of @article, @book, etc.)
    entry_count = bibtex_content.count("@")

    print(f"Exported {entry_count} entries")

    # Write to file
    output_path.write_text(bibtex_content, encoding="utf-8")

    print(f"Saved snapshot to: {output_path}")
    print(f"Snapshot size: {output_path.stat().st_size / 1024:.1f} KB")

    return output_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Export Zotero collection to BibTeX snapshot"
    )
    parser.add_argument(
        "--collection",
        default="dpp-fashion",
        help="Zotero collection name (default: dpp-fashion)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output path (default: tests/fixtures/golden/...)",
    )

    args = parser.parse_args()

    try:
        export_zotero_snapshot(
            collection_name=args.collection, output_path=args.output
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
