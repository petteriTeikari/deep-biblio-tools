#!/usr/bin/env python3
"""Extract citations from DronePosition.md and save them to a JSON file."""

import json
import sys
from pathlib import Path

# Add the src directory to the Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from src.converters.md_to_latex.citation_extractor_unified import (
    UnifiedCitationExtractor,
)  # noqa: E402, I001


def main():
    """Extract citations from DronePosition.md."""
    # Input file
    input_file = project_root / "drone_data" / "DronePosition.md"

    if not input_file.exists():
        print(f"Error: {input_file} not found")
        return 1

    # Read markdown content
    print("Reading markdown file...")
    with open(input_file, encoding="utf-8") as f:
        content = f.read()

    # Extract citations
    print("Extracting citations...")
    extractor = UnifiedCitationExtractor()
    citations = extractor.extract_citations(content)

    print(f"Found {len(citations)} citations")

    # Citations are already in dictionary format
    citation_data = []
    for i, citation in enumerate(citations):
        citation_dict = {
            "index": i + 1,
            "authors": citation.get("authors", ""),
            "year": citation.get("year", ""),
            "url": citation.get("url", ""),
            "text": citation.get("text", ""),
            "raw_markdown": citation.get("raw_markdown", ""),
        }
        citation_data.append(citation_dict)

    # Save to JSON file
    output_file = project_root / "drone_data" / "extracted_citations.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(citation_data, f, indent=2, ensure_ascii=False)

    print(f"Citations saved to: {output_file}")

    # Print first 10 citations as sample
    print("\nFirst 10 citations:")
    for i, cite in enumerate(citation_data[:10]):
        print(
            f"{i + 1}. {cite['authors']} ({cite['year']}) - {cite['url'][:60]}..."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
