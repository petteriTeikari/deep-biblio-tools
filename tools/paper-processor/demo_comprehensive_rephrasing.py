#!/usr/bin/env python3
"""Demonstrate comprehensive rephrasing with research gaps preservation."""

import sys
from pathlib import Path

# Add the literature-reviewer module to Python path
lit_reviewer_path = Path(__file__).parent.parent / "literature-reviewer" / "src"
sys.path.insert(0, str(lit_reviewer_path))


def demonstrate_comprehensive_rephrasing():
    """Demonstrate the comprehensive rephrasing approach."""

    print("Comprehensive Academic Rephrasing Demonstration")
    print("=" * 70)

    # Show the key features
    print("\nKEY FEATURES OF THE REPHRASING APPROACH:\n")

    print("1. CONTENT PRESERVATION STRATEGY:")
    print("   - Standard sections: 85-90% preservation")
    print("   - Critical sections: 95-99% preservation")
    print("   - Future work/Research gaps: 99-100% preservation")
    print("   - All citations and references: 100% preservation\n")

    print("2. RESEARCH GAPS IDENTIFICATION:")
    print("   The system automatically identifies and preserves:")
    print("   - Explicit future work statements")
    print("   - Technical limitations and constraints")
    print("   - Computational challenges")
    print("   - System robustness issues")
    print("   - Scalability concerns")
    print("   - Integration challenges\n")

    print("3. BIM/SCAN-TO-BIM CONTEXTUALIZATION:")
    print("   Each research gap is expanded with:")
    print("   - Building inspection implications")
    print("   - Point cloud processing relevance")
    print("   - As-built documentation impacts")
    print("   - Construction monitoring applications")
    print("   - BIM software integration needs\n")

    # Show example prompt structure
    print("4. EXAMPLE REPHRASING PROMPT FOR RESEARCH GAPS:\n")

    example_prompt = """
When encountering research gaps or future work statements:

1. PRESERVE VERBATIM: Quote the exact statement first
   Example: "Future work will focus on optimizing the pipeline to reduce computational overhead"

2. EXPAND FOR BIM CONTEXT: Add domain-specific implications
   - How does this gap affect building documentation?
   - What are the impacts on scan-to-BIM workflows?
   - How does it limit construction monitoring?

3. CONNECT TO REAL-WORLD CHALLENGES:
   - Large-scale building projects
   - Real-time model updates
   - Multi-stakeholder collaboration
   - Regulatory compliance needs

4. HIGHLIGHT RESEARCH OPPORTUNITIES:
   - Potential solutions in BIM domain
   - Integration with existing tools
   - Standards development needs
   - Performance benchmarks required
"""

    print(example_prompt)

    # Show expected output format
    print("\n5. EXPECTED OUTPUT STRUCTURE FOR RESEARCH GAPS:\n")

    output_example = """
## Research Gaps and Future Directions [99% Preserved]

### Computational Efficiency Challenges
**Original Statement**: "Future work will focus on optimizing the pipeline to reduce computational overhead"

**BIM Context Analysis**:
This computational limitation has critical implications for BIM applications:
- Current processing delays prevent real-time as-built model updates
- High computational overhead limits on-site point cloud processing
- Resource constraints affect multi-building project scalability

**Scan-to-BIM Impact**:
- Extended processing time increases project delivery cycles
- Limited field deployment due to hardware requirements
- Challenges in continuous construction progress monitoring

**Research Opportunities**:
1. GPU-accelerated processing for BIM model generation
2. Distributed computing architectures for large-scale projects
3. Edge computing solutions for on-device processing
4. Optimization algorithms specific to building geometry

### System Robustness Requirements
**Original Statement**: "enhance overall system robustness"

**BIM Context Analysis**:
System robustness is paramount for construction site deployment:
- Variable lighting conditions in indoor/outdoor transitions
- Dust and debris affecting sensor performance
- Weather-related challenges for facade inspections
- Dynamic construction site environments

**Future Research Directions**:
- Sensor fusion techniques for harsh environments
- Adaptive algorithms for varying conditions
- Fail-safe mechanisms for critical inspections
- Validation protocols for BIM accuracy requirements
"""

    print(output_example)

    # Show preservation metrics
    print("\n6. PRESERVATION METRICS:\n")

    metrics_example = """
After rephrasing, the system provides detailed metrics:

Content Preservation Report:
- Future Work Statements: 100% (6/6 preserved)
- Technical Limitations: 100% (8/8 preserved)
- Computational Challenges: 100% (4/4 preserved)
- System Constraints: 95% (19/20 preserved)
- Research Opportunities: 100% (12/12 preserved)

Total Research Gaps Preserved: 49/50 (98%)

BIM Contextualization Added:
- Building inspection connections: 15
- Point cloud processing links: 12
- Construction monitoring applications: 18
- As-built documentation impacts: 10
- Integration opportunities: 8
"""

    print(metrics_example)

    # Implementation guide
    print("\n7. IMPLEMENTATION GUIDE:\n")

    print("To use the academic rephraser with research gaps focus:")
    print("1. Configure API credentials (Anthropic or OpenAI)")
    print("2. Run: python test_academic_rephrase.py")
    print("3. The rephraser will:")
    print("   - Identify all research gaps automatically")
    print("   - Apply preservation ratios based on content type")
    print("   - Add BIM/scan-to-BIM context throughout")
    print("   - Generate comprehensive academic prose")
    print("   - Provide detailed preservation metrics\n")

    print("For papers with significant future work sections,")
    print("consider using test_rephrase_full_paper_gaps.py for")
    print("extreme preservation of research directions.\n")

    # Show benefits
    print("8. BENEFITS FOR RESEARCHERS:\n")

    benefits = """
- Complete preservation of research opportunities
- Enhanced understanding through domain contextualization
- Ready-to-use content for literature reviews
- Identified connections to BIM/construction challenges
- Structured format for systematic analysis
- Academic prose suitable for publication
- Cross-domain knowledge transfer facilitated
- Foundation for grant proposals and research planning
"""

    print(benefits)

    print("\n" + "=" * 70)
    print("End of Demonstration")


if __name__ == "__main__":
    demonstrate_comprehensive_rephrasing()
