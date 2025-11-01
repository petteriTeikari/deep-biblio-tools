# Citation Management Requirements - READ THIS FIRST

**Last Updated**: 2025-11-01
**Purpose**: Quick reference for ALL citation management requirements. Read this before ANY work on citations.

---

## Current State (as of 2025-11-01)

### Working Correctly
- ✅ 308 citations extracted from mcp-draft-refined-v5.md
- ✅ 210 matched to Zotero RDF (appear with full author names in PDF)
- ✅ 98 missing citations (not in RDF) - **appear as (?) in PDF - THIS IS CORRECT**
- ✅ failedAutoAdd keys: 71 in .tex, 0 in .bib (CORRECT - filtered out)
- ✅ Missing citations reports auto-generated: missing-citations-report.json and .csv
- ✅ PDF shows (?) for missing citations - **this is EXPECTED and CORRECT**
- ✅ Non-academic links (GitHub, news, company sites) filtered: 123 filtered during extraction
- ✅ Conversion uses CORRECT output directory: input_dir/output/

### Understanding (?) Citations - CRITICAL

**(?) in PDF is a FEATURE, not a bug.**

- Paper in Zotero RDF → Full citation with author names (e.g., "Smith et al., 2020")
- Paper NOT in Zotero RDF → (?) in PDF showing what needs manual addition
- **Goal**: Accurate citations, NOT zero (?)
- **Success**: If 98 missing citations → see ~98 (?) in PDF ✅

**The goal is NOT to eliminate (?) at all costs. The goal is NO hallucinated/phantom citations.**

### Implementation Files
- Citation extraction: `src/converters/md_to_latex/citation_extractor_unified.py`
- Citation management: `src/converters/md_to_latex/citation_manager.py`
- Conversion pipeline: `src/converters/md_to_latex/converter.py`
- Missing reports generation: `converter.py:1171-1244`
- failedAutoAdd filtering: `citation_manager.py:1792-1805`
- .bbl hardcoding scripts: `scripts/hardcode_bibliography.py`, `scripts/create_hardcoded_bibliography_uadreview.py`

---

## Core Requirements (NON-NEGOTIABLE)

### 1. Emergency Mode (RDF-Only)

**Requirement**: When `emergency_mode=True`, ONLY use Zotero RDF export. NO network activity.

**What This Means**:
- ❌ NEVER fetch from web (DOI, arXiv, CrossRef, etc.)
- ❌ NEVER use Zotero API
- ❌ NEVER use cache (could contain fetched data)
- ❌ NEVER auto-add missing citations to Zotero
- ✅ ONLY use data already in RDF file
- ✅ HARD CRASH if RDF file missing or empty

**Why**: Deterministic, reproducible builds. Same RDF → same output, every time.

**Implementation**: `citation_manager.py:681-696` (emergency mode path)

**Verification**:
```bash
# Check logs for ZERO web fetches
grep -i "fetch\|http request\|api call" conversion.log
# Should find ZERO results
```

### 2. failedAutoAdd Keys - BANNED from .bib

**Requirement**: `failedAutoAdd_*` keys MUST NOT appear in references.bib or final .bbl file.

**Current Behavior** (CORRECT):
- ✅ .tex file contains: `\citep{failedAutoAdd_011964}` (71 instances)
- ✅ references.bib contains: 0 failedAutoAdd entries (filtered out)
- ✅ Result: PDF shows (?) for missing citations

**Why Banned**:
- failedAutoAdd entries historically contained FETCHED data (authors, titles, years)
- This violated RDF-only requirement
- User quote: "not hallucinating some weird temp citations to the list!"
- Correct behavior: Missing citations show as (?) in PDF so user knows what to add to Zotero

**Implementation**:
- Generation: `citation_manager.py:684` (creates temp key)
- Filtering: `citation_manager.py:1792-1805` (excludes from .bib)
- Tracking: `citation_manager.py:687` (adds to failed_citations list)

**Historical Context**: See `docs/planning/EMERGENCY-MODE-VIOLATION-MEA-CULPA.md` for why this was banned.

**Verification**:
```bash
# Count failedAutoAdd in .tex (should be > 0 if there are missing citations)
grep -c "failedAutoAdd" output/file.tex

# Count failedAutoAdd in .bib (MUST be 0)
grep -c "failedAutoAdd" output/references.bib  # → 0
```

### 3. Missing Citations Report - MUST Auto-Generate

**Requirement**: EVERY conversion MUST generate missing citations reports if there are failed citations.

**Files Generated**:
- `output/missing-citations-report.json` - Machine-readable format
- `output/missing-citations-review.csv` - Human-reviewable with supervision columns

**Report Contents**:
- Citation text from markdown (e.g., `[Author (Year)](URL)`)
- URL
- Authors (from markdown)
- Year (from markdown)
- Reason (e.g., "Not found in RDF export")
- Action (e.g., "Add this paper to your Zotero collection and re-export RDF")
- Empty supervision columns for manual review

**Implementation**: `converter.py:1171-1244`

**CSV Format**:
```csv
Citation Text,URL,Current Authors,Current Year,Reason,Is Real Problem? (YES/NO),Should Be In Zotero? (YES/NO),Notes
[Zhang et al (2025)](https://arxiv.org/abs/2510.04618),https://arxiv.org/abs/2510.04618,Zhang et al,2025,Not found in RDF export,,,
```

**Verification**:
```bash
# Check reports exist
ls -lh output/missing-citations-report.json output/missing-citations-review.csv

# Check count matches
jq '.missing_count' output/missing-citations-report.json
wc -l output/missing-citations-review.csv
```

**Bug Fixed** (2025-11-01): Reports were checking for `citation.authors == "Unknown"` but emergency mode extracts authors from markdown text, so they're never "Unknown". Fixed to use `self.citation_manager.failed_citations` list instead.

### 4. .bbl Hardcoding (Final Submission Workflow)

**Purpose**: Convert .bib → hardcoded .bbl with hyperlinked authors for final submission.

**When to Use**:
- Final journal/conference submission
- Archival versions
- When you want clickable author-year links in PDF

**What It Does**:
- Converts `\bibliography{references}` → inline `\begin{thebibliography}...\end{thebibliography}`
- Hyperlinks author-year: `\href{https://doi.org/...}{Author (Year)}`
- Standalone bibliography (no external .bib file needed)
- Preserves citation order or sorts alphabetically

**Scripts Available**:
1. `scripts/hardcode_bibliography.py` - Standard formatting
2. `scripts/create_hardcoded_bibliography_uadreview.py` - With natbib label support

**Example Output**:
```latex
\begin{thebibliography}{99}
\bibitem{niinimaki_environmental_2020}
\href{https://doi.org/10.1038/s43017-020-0039-9}{Niinimäki K, Peters G, Dahlbo H, Perry P, Rissanen T, Gwilt A (2020)} The environmental price of fast fashion. {\em Nature Reviews Earth \& Environment 1}(4):189--200.
\end{thebibliography}
```

**User's Workflow**:
1. Run markdown → LaTeX conversion (generates references.bib)
2. Compile with BibTeX (generates .bbl)
3. Optionally modify .bbl by hand (e.g., fix formatting)
4. Use hardcoding script OR manually copy .bbl into .tex
5. Final .tex has embedded bibliography, no external .bib needed

**Key Detail**: User copies modified .bbl into .tex file, so references.bib is ephemeral (deleted before each conversion).

**For More Details**: See `.claude/bbl-hardcoding-guide.md`

### 5. Output Directory - ALWAYS input_dir/output/

**Requirement**: ALL conversion outputs MUST go to `output/` subdirectory next to input markdown.

**Pattern**:
- Input: `/path/to/paper/file.md`
- Output: `/path/to/paper/output/file.tex`, `output/file.pdf`, `output/references.bib`, etc.

**Examples**:
```bash
# CORRECT
Input:  /home/petteri/Dropbox/.../mcp-review/mcp-draft-refined-v5.md
Output: /home/petteri/Dropbox/.../mcp-review/output/mcp-draft-refined-v5.tex
Output: /home/petteri/Dropbox/.../mcp-review/output/mcp-draft-refined-v5.pdf

# WRONG
Output: /tmp/test/mcp-draft-refined-v5.tex  # ❌ /tmp is BANNED
Output: /home/petteri/Dropbox/github-personal/deep-biblio-tools/output/file.tex  # ❌ Inside repo
```

**Why**: User needs to find outputs next to source files. /tmp is invisible and temporary.

**Implementation**: Check `self.output_dir` in converter

**Verification**:
```bash
# After conversion, check output directory
ls -lh "$(dirname "$INPUT_MARKDOWN")/output/"
```

### 6. Citation Classification (Academic vs Non-Academic)

**Requirement**: NOT every hyperlink is a citation. Distinguish academic from non-academic.

**Academic Citations** (→ Bibliography):
- Has DOI: `https://doi.org/10.1234/example`
- Has arXiv ID: `https://arxiv.org/abs/2401.12345`
- Has ISBN (book): `https://www.amazon.com/.../1234567890`
- Academic publisher domain: springer.com, ieee.org, acm.org, nature.com, etc.

**Non-Academic Links** (→ Should be footnotes or inline hyperlinks):
- News sites: bbc.com, bloomberg.com, reuters.com, theguardian.com
- Company blogs: anthropic.com, openai.com, google.com
- Social media: x.com, youtube.com, linkedin.com
- Code repositories: github.com, gitlab.com
- Government: europa.eu, .gov, oecd.org

**Current Implementation**: `citation_extractor_unified.py:92-178` (NON_ACADEMIC_DOMAINS filter, 80+ domains)

**Issue Found** (v4.md validation): 73 citations with organization names as authors (BBC, Bloomberg, Google, Anthropic). These should likely be footnotes, not bibliography entries.

**For More Details**: See `.claude/citation-classification-rules.md`

### 7. Quality Checks Before Claiming Success

**NEVER claim conversion success without verifying ALL of these**:

1. ✅ **references.bib quality**:
   ```bash
   grep -c "failedAutoAdd" output/references.bib  # → 0
   grep -c "Unknown" output/references.bib        # → 0
   grep -c "Anonymous" output/references.bib      # → 0
   ```

2. ✅ **Missing citations reports exist**:
   ```bash
   ls output/missing-citations-report.json output/missing-citations-review.csv
   ```

3. ✅ **Count verification**:
   ```bash
   # Total citations = matched + missing
   # Example: 308 total = 210 matched + 98 missing
   ```

4. ✅ **PDF compiles**:
   ```bash
   ls output/file.pdf  # Must exist
   pdfinfo output/file.pdf  # Must show valid PDF
   ```

5. ✅ **PDF shows (?) for missing citations**:
   ```bash
   pdftotext output/file.pdf - | grep -c "(\?)"  # Should match missing count
   ```

6. ✅ **Output directory correct**:
   ```bash
   # Output MUST be in input_dir/output/, NOT /tmp
   ```

7. ✅ **No web fetching in logs** (emergency mode):
   ```bash
   grep -i "fetch\|http request\|api call" logs  # → 0 results
   ```

**For Complete Checklist**: See `.claude/quality-verification-checklist.md`

---

## References for Detailed Context

When you need more details, refer to these documents:

- **failedAutoAdd ban rationale**: `.claude/CLAUDE.md:365-390` + `docs/planning/EMERGENCY-MODE-VIOLATION-MEA-CULPA.md`
- **.bbl hardcoding**: `.claude/bbl-hardcoding-guide.md`
- **Emergency mode specification**: `.claude/emergency-mode-specification.md`
- **Citation classification**: `.claude/citation-classification-rules.md`
- **Quality verification**: `.claude/quality-verification-checklist.md`
- **Complete history**: `docs/planning/CITATION-MANAGEMENT-MASTER-PLAN.md`
- **Code implementation**: Research report from 2025-11-01 session

---

## Common Mistakes to Avoid

Based on past sessions where I forgot requirements:

1. ❌ **Claiming success without reading PDF** - Always verify (?) citations appear
2. ❌ **Using /tmp for output** - Always use input_dir/output/
3. ❌ **Not generating missing reports** - Must auto-generate on every conversion
4. ❌ **Allowing failedAutoAdd in .bib** - Must be filtered out (OK in .tex only)
5. ❌ **Treating all hyperlinks as citations** - Check NON_ACADEMIC_DOMAINS filter
6. ❌ **Forgetting .bbl hardcoding exists** - User wants hyperlinked authors for final submission
7. ❌ **Web fetching in emergency mode** - RDF ONLY, no exceptions
8. ❌ **Not reading this document first** - This is the quick reference, read it every time

---

## When to Read This Document

**ALWAYS read this document FIRST when**:
- Starting work on citation management
- User reports citation issues
- Converting markdown to LaTeX
- Debugging missing citations
- Updating citation-related code
- Creating or updating .bib/.bbl files

**This document prevents forgetting critical requirements between sessions.**

---

Last updated: 2025-11-01 after fixing missing citations report generation bug.
