# Academic Rephrasing Requirements for BIM/Scan-to-BIM Papers

## Overview
This document outlines the requirements for creating academic rephrases of research papers with a focus on BIM and scan-to-BIM applications. The goal is to create high-quality academic reviews that preserve critical content while contextualizing findings for the construction industry.

## 1. Length Requirements

### Target Length
- **Exactly ~24.3% of original length** (following the AirVista-II example)
- For example:
  - 10,000 word paper → ~2,430 words
  - 34,000 word paper → ~8,262 words
  - 50,000 word paper → ~12,150 words

### What to Avoid
- ❌ Extreme compression (1-5% retention)
- ❌ Minimal reduction (50-70% retention)
- ❌ Taking shortcuts or bullet-point summaries

## 2. Content Processing Strategy

### Approach
- **Section-by-section rephrasing** - Process each section individually
- Maintain academic prose style throughout
- Preserve logical flow and transitions between sections
- No bullet points unless specifically listing items

### Section-Specific Retention Guidelines
- Abstract/Executive Summary: 50-60% retention
- Introduction: 30-40% retention
- Related Work/Background: 15-20% retention
- Methodology: 25-30% retention
- Results/Experiments: 25-30% retention
- Discussion: 35-40% retention
- Limitations: 90-95% retention
- Future Work: 100% retention
- Conclusion: 80-90% retention

## 3. Critical Content Preservation

### Must Preserve 100%
- ✅ All future work statements
- ✅ All research gaps identified
- ✅ All limitations mentioned
- ✅ Key quantitative results (percentages, metrics)

### High Priority Preservation (90%+)
- Conclusion statements
- Novel contributions
- Critical findings

## 4. Citation Format Requirements ⚠️

### Format
- **Hyperlinked inline citations in (Author, Year) format**
- Every citation must be clickable
- Format: `[(Author et al., Year)](link)`

### Examples
- ✅ Correct: "Recent advances in 3D scene understanding [(Chen et al., 2021)](link) demonstrate..."
- ❌ Wrong: "Recent advances in 3D scene understanding [1] demonstrate..."
- ❌ Wrong: "Recent advances in 3D scene understanding (Chen et al., 2021) demonstrate..."

### Implementation
```markdown
[(Chen et al., 2021)](https://arxiv.org/abs/2104.00000)
[(Smith and Jones, 2023)](https://doi.org/10.1109/CVPR.2023.00123)
```

## 5. Reference List Requirements

### Extraction
- Extract ALL references from the HTML source file
- Use multiple methods to ensure completeness:
  - Look for bibliography/references sections
  - Search for citation class names (ltx_bibitem, reference, citation)
  - Pattern matching for numbered references

### Format
- Complete bibliographic information
- Present as numbered list in appendix
- Include statement: "The following is the complete list of [N] references from the original paper:"

## 6. BIM/Scan-to-BIM Contextualization

### Throughout the Document
- Connect findings to construction industry applications
- Highlight relevance for building documentation
- Emphasize scan-to-BIM workflow implications
- Link to BIM software integration possibilities

### Dedicated Sections
Include these sections with consistent formatting:

```markdown
## BIM-Specific Research Opportunities

Based on the contributions, key research directions for BIM applications include:

1. **Automated As-Built Documentation**: [specific adaptations]
2. **Semantic Enhancement**: [BIM-specific applications]
3. **Quality Assurance**: [construction monitoring aspects]
4. **Workflow Integration**: [scan-to-BIM processes]

## Implementation Considerations

Adoption in construction workflows requires:
- Hardware integration with existing scanning equipment
- APIs for major BIM platforms (Revit, ArchiCAD)
- Construction-specific training datasets
- Industry-standard validation protocols
```

## 7. Document Structure

### Required Structure
```markdown
# [Paper Title]
*Academic Review for BIM/Scan-to-BIM Applications*

**Document Type**: Academic Review
**Original Length**: [N] words
**Review Length**: ~[N] words (24.3%)
**Future Work Preservation**: 100%
**Generated**: [Date]

---

## Executive Summary
[Rephrased abstract with BIM context]

## Key Motivation / Introduction
[Core problem and relevance to construction]

## Technical Approach / Methodology
[Key methods with BIM relevance]

## Key Results
[Critical findings and metrics]

## Limitations and Challenges [PRESERVED]
[Nearly complete preservation of limitations]

## Future Work and Research Directions [100% PRESERVED]
[Complete preservation of future work]

## BIM-Specific Research Opportunities
[Construction-specific research directions]

## Implementation Considerations
[Practical deployment requirements]

## Appendix: Original Paper References
[Complete reference list]

---

*This academic review maintains 24.3% of the original content while preserving 100% of stated future research directions. All citations are hyperlinked in (Author, Year) format with complete references provided. The review emphasizes practical implications for BIM and scan-to-BIM applications.*
```

## 8. Quality Checks

Before finalizing each rephrasing:
1. ✓ Verify word count is ~24.3% of original
2. ✓ Check all citations are hyperlinked in (Author, Year) format
3. ✓ Confirm 100% future work preservation
4. ✓ Ensure complete reference list is included
5. ✓ Verify BIM contextualization throughout
6. ✓ Check academic prose style is maintained
7. ✓ Ensure logical flow between sections

## 9. Common Mistakes to Avoid

1. ❌ Forgetting hyperlinked citations
2. ❌ Extreme compression or over-retention
3. ❌ Bullet-point style instead of prose
4. ❌ Missing reference appendix
5. ❌ Losing critical quantitative results
6. ❌ Generic summaries without BIM context
7. ❌ Not preserving future work completely

## 10. Example Reference

The AirVista-II_academic_rephrase_50percent_with_appendix.md file serves as the gold standard example, demonstrating:
- Proper 24.3% length retention
- Hyperlinked (Author, Year) citations
- Complete reference preservation
- Strong BIM contextualization
- Academic prose throughout
- 100% future work preservation
