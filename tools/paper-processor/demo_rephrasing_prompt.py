#!/usr/bin/env python3
"""Demonstrate the rephrasing prompts and approach."""

import sys
from pathlib import Path

# Add the literature-reviewer module to Python path
lit_reviewer_path = Path(__file__).parent.parent / "literature-reviewer" / "src"
sys.path.insert(0, str(lit_reviewer_path))

from literature_reviewer.processors.content_processor import (  # noqa: E402
    ContentProcessor,
)
from literature_reviewer.utils.config import get_default_config  # noqa: E402


def demonstrate_rephrasing_prompt():
    """Demonstrate the rephrasing prompt generation."""

    # File path
    input_file = Path(
        "/home/petteri/Dropbox/LABs/github-personal/papers/scan2bim/biblio/drones/extracted/AirVista-II_ An Agentic System for Embodied UAVs Toward Dynamic Scene Semantic Understanding.md"
    )

    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        return

    print("Academic Rephrasing Demonstration")
    print("=" * 80)
    print(f"\nInput file: {input_file.name}")

    # Initialize content processor
    config = get_default_config()
    content_processor = ContentProcessor(config)

    # Read content
    content = input_file.read_text(encoding="utf-8")

    # Extract metadata
    metadata = content_processor.extract_metadata(content)
    print(f"\nTitle: {metadata.get('title', 'Unknown')}")

    # Parse sections
    sections = content_processor.parse_sections(content)

    # Find critical sections (future work, research gaps, limitations)
    critical_sections = []
    for section in sections:
        title_lower = section["title"].lower()
        if any(
            term in title_lower
            for term in [
                "future",
                "gap",
                "limitation",
                "challenge",
                "conclusion",
            ]
        ):
            critical_sections.append(section)

    print(
        f"\nFound {len(critical_sections)} critical sections to preserve at 95-100%:"
    )
    for section in critical_sections:
        print(
            f"  - {section['title']} ({len(section['content'].split())} words)"
        )

    # Demonstrate the prompt for a critical section
    if critical_sections:
        section = critical_sections[0]
        print(f"\n\nDemonstration: Rephrasing prompt for '{section['title']}'")
        print("-" * 80)

        prompt = f"""Rephrase this section from an academic paper for a Building Information Modeling (BIM) and scan-to-BIM research context. This is a CRITICAL section containing research gaps, future directions, or limitations - preserve ALL content with enhanced clarity.

Section: {section["title"]}

CRITICAL PRESERVATION REQUIREMENTS:
- Preserve 95-100% of the original content and ideas
- Maintain ALL specific research gaps, challenges, and future directions mentioned
- Keep EVERY limitation, constraint, or unresolved issue
- Preserve the authors' exact terminology for technical concepts
- Maintain all temporal references (e.g., "currently", "at present", "future work")
- Keep all conditional statements (e.g., "could", "might", "potentially")

REPHRASING GUIDELINES:
1. Academic Writing Style:
   - Maintain formal, scholarly tone
   - Use complete sentences and paragraphs (avoid excessive bullet points)
   - Ensure logical flow between ideas
   - Use appropriate academic transitions

2. BIM/Scan-to-BIM Contextualization:
   - Draw connections to building modeling, point cloud processing, or construction workflows where relevant
   - Highlight implications for digital twin creation, as-built modeling, or facility management
   - Note potential applications in architectural, engineering, and construction (AEC) domains
   - Connect UAV/drone capabilities to building inspection or site monitoring

3. Citation Preservation:
   - Keep ALL inline citations in (Author, Year) format
   - Maintain citation context and relationships
   - Preserve direct quotes with proper attribution

4. Technical Detail Preservation:
   - Keep ALL numerical values, percentages, metrics
   - Maintain technical specifications and parameters
   - Preserve algorithm names, system components, and methodologies
   - Keep all comparisons and benchmarks

5. Research Gap and Future Work Emphasis:
   - Use clear topic sentences to highlight each gap or future direction
   - Expand on implications of each limitation
   - Connect gaps to BIM/scan-to-BIM challenges
   - Preserve priority or timeline information if mentioned

Original Content:
{section["content"][:1000]}... [truncated for demonstration]

Provide the rephrased section that preserves ALL original insights while enhancing clarity and BIM/scan-to-BIM relevance:"""

        print(prompt)

    # Show the comprehensive rephrasing approach
    print("\n\n" + "=" * 80)
    print("COMPREHENSIVE REPHRASING APPROACH")
    print("=" * 80)

    print("""
Key Features of the New Rephrasing Method:

1. CONTENT PRESERVATION (85-95%):
   - Much higher retention than traditional summarization
   - Preserves technical details, methodologies, and results
   - Maintains all citations and references
   - Keeps numerical data and comparisons

2. SPECIAL HANDLING FOR CRITICAL SECTIONS:
   - Future Work: 95% preservation
   - Research Gaps: 95% preservation
   - Limitations: 90% preservation
   - Discussion: 90% preservation
   - Methodology: 85% preservation

3. BIM/SCAN-TO-BIM CONTEXTUALIZATION:
   - Connects UAV capabilities to building inspection
   - Links computer vision to point cloud processing
   - Relates semantic understanding to BIM classification
   - Highlights applications in AEC domains

4. ACADEMIC WRITING ENHANCEMENT:
   - Formal scholarly prose (not bullet lists)
   - Logical flow and transitions
   - Clear topic sentences
   - Proper citation formatting

5. USE CASES:
   - Creating context for LLM analysis
   - Building academic review articles
   - Knowledge preservation for research
   - Cross-domain knowledge transfer

COMPARISON WITH PREVIOUS SUMMARIZATION:
- Previous: 10-25% compression (lost 75-90% of content)
- New: 85-95% preservation (loses only 5-15% of redundancy)
- Previous: Brief bullet points
- New: Full academic paragraphs with flow
- Previous: Lost many technical details
- New: Preserves all technical content
""")

    # Show sample output structure
    print("\nEXPECTED OUTPUT STRUCTURE:")
    print("-" * 40)
    print("""
# [Paper Title]

**Authors:** [Full author list]
**Year:** [Publication year]
**Venue:** [Conference/Journal]
**DOI:** [If available]

---

## Abstract
[Rephrased abstract with BIM/scan-to-BIM context, preserving all key findings]

## Introduction
[Comprehensive introduction connecting the work to BIM/scan-to-BIM challenges...]

## Related Work
[Literature review with preserved citations (Author, Year) and BIM connections...]

## Methodology
[Detailed technical approach with all algorithms and parameters preserved...]

## Results
[All numerical results, tables, and comparisons maintained...]

## Discussion
[Full analysis with BIM/scan-to-BIM implications highlighted...]

## Future Work and Research Gaps
[95-100% preservation of all mentioned gaps, challenges, and future directions...]

## Conclusion
[Rephrased conclusions with enhanced clarity...]

## References
[Complete reference list in proper format]
""")


if __name__ == "__main__":
    demonstrate_rephrasing_prompt()
