# Literature Review Generation Instructions

## Overview
This document provides detailed instructions for generating comprehensive academic literature reviews from collections of papers using Claude Code.

## Requirements for Paper Summaries

### 1. Summary Length
- **Target: EXACTLY 25% of original document size**
- For a 68KB input → 17KB output (NOT 4.8KB)
- Minimum summary size: 15KB to ensure comprehensiveness

### 2. Citation Format
Convert all numeric citations to author-year format:
- ❌ Wrong: "using SMPL model [64]"
- ✅ Correct: "using SMPL model ([Loper et al., 2015](https://doi.org/...))"

### 3. Reference Section
Each summary MUST end with a complete bibliography containing:
- Full author names (not just initials)
- Complete paper title
- Publication venue, volume, pages
- Year
- DOI or URL when available

Example:
```
## References

Loper, M., Mahmood, N., Romero, J., Pons-Moll, G., & Black, M. J. (2015). SMPL: A skinned multi-person linear model. ACM Transactions on Graphics (Proceedings of SIGGRAPH Asia), 34(6), 248:1–248:16. https://doi.org/10.1145/2816795.2818013
```

### 4. Content Structure
Each summary must include:
1. **Header Information**
   - Full paper title
   - All authors with affiliations
   - Publication venue and date
   - Link to paper/project page

2. **Comprehensive Abstract** (300-500 words)
   - Preserve original if under 500 words
   - Otherwise create detailed summary

3. **Key Contributions** (20-30% of summary)
   - List each contribution with technical details
   - Include specific innovations and novelty claims

4. **Methodology** (25-35% of summary)
   - Detailed algorithm descriptions
   - Architecture diagrams (describe if visual)
   - Mathematical formulations
   - Implementation specifics

5. **Results and Evaluation** (20-30% of summary)
   - All quantitative results with numbers
   - Comparison tables
   - Performance metrics
   - Statistical significance

6. **Technical Details**
   - Datasets used
   - Hyperparameters
   - Computational requirements
   - Code availability

7. **Limitations and Future Work**
   - Acknowledged limitations
   - Proposed extensions

8. **Complete References**
   - All cited works in full format

## Literature Review Requirements

### Target Specifications
- Length: 12-15 pages (8000-10000 words)
- Style: Formal academic writing
- Citations: Author-year format with markdown links

### Structure
1. **Abstract** (300-400 words)
2. **Introduction** (800-1000 words)
3. **Historical Development** (1500-2000 words)
4. **Current State-of-the-Art** (1500-2000 words)
5. **Knowledge Gaps** (1000-1500 words)
6. **Recent Solutions** (1500-2000 words)
7. **Future Directions** (1000-1500 words)
8. **Conclusions** (500-700 words)
9. **Context-Specific Application** (1500-2000 words)
10. **References** (all papers cited)

### Writing Guidelines
- Synthesize across papers, don't just summarize sequentially
- Identify trends, patterns, and contradictions
- Critical analysis, not just description
- Group related work thematically
- Highlight seminal contributions
- Discuss methodological evolution

## Processing Steps

### Step 1: Analyze Input Papers
```bash
# Check file sizes
ls -lh *.html *.md | grep -v "_summary\|review"

# Count papers
find . -name "*.html" -o -name "*.md" | grep -v "_summary\|review" | wc -l
```

### Step 2: Create Output Directories
```bash
mkdir -p summaries review
```

### Step 3: Process Each Paper
For each paper:
1. Read the full content
2. Calculate target summary size (25% of original)
3. Extract all citations and references
4. Create comprehensive summary maintaining target size
5. Convert all citations to author-year format
6. Add complete bibliography at end
7. Save to summaries/ directory

### Step 4: Generate Literature Review
1. Read all summaries
2. Extract key themes and contributions
3. Organize chronologically and thematically
4. Write comprehensive review following structure
5. Ensure all citations are properly formatted
6. Add complete merged bibliography
7. Save to review/ directory

## Quality Checks

### For Summaries
- [ ] File size is ~25% of original (±10%)
- [ ] All citations in author-year format
- [ ] Complete reference list at end
- [ ] All sections properly covered
- [ ] Technical details preserved

### For Literature Review
- [ ] Meets word count (8000-10000)
- [ ] All sections properly sized
- [ ] Citations properly formatted
- [ ] Synthesis across papers evident
- [ ] Critical analysis included
- [ ] Complete bibliography

## Example Commands for Claude Code

```
# Process all papers in directory
"Please process all HTML and MD files in /path/to/papers/ following the literature review instructions. Create 25% summaries with full citations and then generate a comprehensive literature review."

# Check summary quality
"Please verify that the summaries in /path/to/summaries/ meet the 25% size requirement and have proper author-year citations with complete reference lists."

# Generate review only
"Using the summaries in /path/to/summaries/, create a comprehensive 12-page literature review following the specified structure."
```

## Common Issues and Solutions

### Issue: Summary too short (e.g., 4.8KB instead of 17KB)
**Solution**: Explicitly calculate and state target size. Include more direct quotes, detailed methodology, and comprehensive results.

### Issue: Citations as numbers [1], [2]
**Solution**: Extract reference list first, create mapping, then convert all citations during summary generation.

### Issue: Missing reference list
**Solution**: Always append complete bibliography even if it seems redundant with inline citations.

### Issue: Review too superficial
**Solution**: Ensure summaries are comprehensive first. Review should synthesize, not just list.

## Reusable Script Usage

```bash
# Make script executable
chmod +x process_papers_to_review.py

# Run on a directory
python process_papers_to_review.py /path/to/papers/

# Specify custom output directories
python process_papers_to_review.py /path/to/papers/ \
  --summaries-dir /path/to/summaries/ \
  --review-dir /path/to/review/
```
