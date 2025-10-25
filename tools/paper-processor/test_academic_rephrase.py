#!/usr/bin/env python3
"""Test script for academic rephrasing functionality."""

import sys
from datetime import datetime
from pathlib import Path

# Add the literature-reviewer module to Python path
lit_reviewer_path = Path(__file__).parent.parent / "literature-reviewer" / "src"
sys.path.insert(0, str(lit_reviewer_path))

# Import the necessary modules
from literature_reviewer.processors.academic_rephraser import (  # noqa: E402
    AcademicRephraser,
)
from literature_reviewer.processors.content_processor import (  # noqa: E402
    ContentProcessor,
)
from literature_reviewer.utils.config import get_default_config  # noqa: E402


def test_rephrase_airvista():
    """Test rephrasing on the AirVista-II paper."""

    # File paths
    input_file = Path(
        "/home/petteri/Dropbox/LABs/KusiKasa/papers/scan2bim/biblio/drones/extracted/AirVista-II_ An Agentic System for Embodied UAVs Toward Dynamic Scene Semantic Understanding.md"
    )
    output_dir = Path(
        "/home/petteri/Dropbox/LABs/KusiKasa/papers/scan2bim/biblio/drones/rephrased"
    )
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / "AirVista-II_rephrased_bim_context.md"

    # Check if input file exists
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        return

    print(f"Processing: {input_file.name}")
    print(f"Output will be saved to: {output_file}")

    # Initialize processors
    config = get_default_config()
    content_processor = ContentProcessor(config)
    rephraser = AcademicRephraser(config)

    # Read the content
    content = input_file.read_text(encoding="utf-8")
    original_word_count = len(content.split())

    print(f"Original word count: {original_word_count:,}")

    # Extract metadata
    metadata = content_processor.extract_metadata(content)
    print(f"Title: {metadata.get('title', 'Unknown')}")
    print(f"Authors: {', '.join(metadata.get('authors', []))}")

    # Extract citations and references
    citations, references = content_processor.extract_citations_and_references(
        content
    )
    print(f"Found {len(citations)} inline citations")
    print(f"Found {len(references)} references")

    # Parse sections
    sections = content_processor.parse_sections(content)
    print(f"Found {len(sections)} sections")

    # Print section breakdown
    print("\nSection breakdown:")
    for section in sections:
        word_count = len(section["content"].split())
        print(f"  - {section['title']}: {word_count:,} words")

    # Perform rephrasing with comprehensive approach
    print("\nStarting comprehensive rephrasing process...")
    print(
        "This will preserve 85-95% of content with BIM/scan-to-BIM contextualization"
    )

    start_time = datetime.now()

    try:
        # Use the comprehensive rephrasing method
        rephrased_content = rephraser.create_comprehensive_rephrase(
            sections=sections,
            metadata=metadata,
            citations=list(citations.items()),
            references=references,
        )

        # Calculate statistics
        rephrased_word_count = len(rephrased_content.split())
        preservation_ratio = rephrased_word_count / original_word_count
        processing_time = (datetime.now() - start_time).total_seconds()

        # Add statistics header
        stats_header = f"""**Rephrasing Info:**
- Original length: {original_word_count:,} words
- Rephrased length: {rephrased_word_count:,} words
- Content preservation: {preservation_ratio:.1%}
- Processing time: {processing_time:.1f} seconds
- Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
- Method: Academic rephrasing with BIM/scan-to-BIM contextualization

---

"""

        # Save the rephrased content
        final_content = stats_header + rephrased_content
        output_file.write_text(final_content, encoding="utf-8")

        print("\nRephrasing completed successfully!")
        print(f"Rephrased word count: {rephrased_word_count:,}")
        print(f"Content preservation: {preservation_ratio:.1%}")
        print(f"Processing time: {processing_time:.1f} seconds")
        print(f"Output saved to: {output_file}")

        # Print a sample of the rephrased content
        print("\nFirst 500 characters of rephrased content:")
        print("-" * 50)
        print(rephrased_content[:500])
        print("-" * 50)

    except Exception as e:
        print(f"\nError during rephrasing: {e}")
        import traceback

        traceback.print_exc()

        # Try fallback approach
        print("\nAttempting fallback section-by-section rephrasing...")
        try:
            rephrased_content = rephraser.rephrase_for_bim_context(
                sections=sections, metadata=metadata, preserve_ratio=0.85
            )

            # Save with fallback note
            stats_header = f"""**Rephrasing Info (Fallback Method):**
- Original length: {original_word_count:,} words
- Method: Section-by-section rephrasing
- Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}

---

"""
            final_content = stats_header + rephrased_content
            output_file.write_text(final_content, encoding="utf-8")
            print("Fallback rephrasing completed successfully!")

        except Exception as e2:
            print(f"Fallback also failed: {e2}")


if __name__ == "__main__":
    print("Academic Rephrasing Test - AirVista-II Paper")
    print("=" * 60)
    test_rephrase_airvista()
    print("\nTest completed!")
