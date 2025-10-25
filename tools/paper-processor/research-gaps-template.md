# Research Gap Analysis Template

## Purpose
This template guides the creation of research-gap-focused paper analyses for identifying business opportunities in BIM/Scan-to-BIM applications.

## Core Questions to Answer

### 1. What Wasn't Known Before This Paper?
- What specific knowledge gaps did the authors identify?
- What problems were unsolved in the field?
- What limitations existed in prior approaches?

### 2. What This Paper Achieved
- What novel contributions were made?
- What problems were solved?
- What new capabilities were demonstrated?
- *Note: Focus on capabilities, not specific metrics (e.g., "achieved real-time processing" not "achieved 95.3% accuracy")*

### 3. What Knowledge Gaps Remain
- What couldn't be solved?
- What new questions arose?
- What practical challenges weren't addressed?
- What would be needed for real-world deployment?

## Section Priorities for Preservation

### HIGH Priority (>60% preservation)
- **Introduction**: Problem statements and gap identification
- **Discussion**: Implications and insights
- **Conclusion**: What was achieved
- **Future Work**: Complete preservation (100%)
- **Limitations**: Near-complete preservation (95%)
- **Abstract**: Novel contributions

### MEDIUM Priority (30-50% preservation)
- **Related Work**: Context of what was known
- **Novel Contributions**: Any explicitly stated contributions

### LOW Priority (<30% preservation)
- **Methodology**: Brief overview only
- **Experiments**: Setup basics, not detailed protocols
- **Results**: Key outcomes only, minimal metrics
- **Implementation Details**: Only if relevant to gaps

## Output Structure

```markdown
# [Paper Title]
*Research Gap Analysis for BIM/Scan-to-BIM Applications*

## Key Contributions & Novel Aspects
[What makes this paper unique and valuable]

## Problem Context & Research Gaps Addressed
[What problems existed and which ones this paper tackled]

## Prior Knowledge & Remaining Gaps
[What was already known and what stayed unsolved]

## Approach Overview
[Brief description of their solution approach]

## Key Achievements
[What they accomplished - capabilities not metrics]

## Implications & New Insights
[What this means for the field]

## Limitations & Unresolved Issues [PRESERVED]
[What they couldn't solve - nearly verbatim]

## Future Research Directions [FULLY PRESERVED]
[Complete preservation of future work]

## Research Opportunities for BIM/Scan-to-BIM

### Knowledge Gaps This Opens:
[New questions and challenges]

### Business Opportunities:
[Potential startup/product ideas]

### Unresolved Technical Challenges:
[What still needs solving for practical deployment]

## References
[Complete bibliography preserved]
```

## Key Principles

1. **Focus on Evolution**: Track how knowledge progressed
2. **Minimize Metrics**: "Improved performance" not "achieved 87.3% mAP"
3. **Preserve Gaps**: Keep all mentions of limitations, challenges, future work
4. **Business Lens**: Always consider startup/product opportunities
5. **Generic Solution**: Same approach for all papers, no paper-specific handling

## Example Transformations

### Instead of:
"Our method achieves 92.5% accuracy on the ScanNet benchmark, outperforming the baseline by 3.2%"

### Write:
"The method demonstrates improved performance on indoor scene understanding tasks"

### Instead of:
"Table 3 shows detailed ablation results across 15 different configurations..."

### Write:
"Ablation studies confirmed the importance of the key architectural choices"

### Always Preserve:
- "However, our method cannot handle..."
- "Future work should address..."
- "A limitation of this approach is..."
- "This opens new questions about..."
- "We were unable to solve..."
