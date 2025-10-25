# Markdown → arXiv-Ready PDF: Zero-Glitch Conversion Plan

**Goal:** Convert academic markdown manuscripts to arXiv-ready PDFs with ZERO errors, ZERO warnings, and ZERO missing citations.

## Problem

Academic researchers write manuscripts in markdown with inline citations like `[Author (Year)](DOI_URL)`. These must be converted to LaTeX with proper BibTeX citations and compiled to PDF meeting arXiv standards.

**Success = ZERO tolerance:**
- 0 markdown syntax errors
- 0 (?) or (Unknown) citations in PDF
- 0 LaTeX compilation errors/warnings
- 0 raw URLs in bibliography
- 100% citations resolved from Zotero
- 100% authors hyperlinked in bibliography

## Test Case

**Input:** `/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/mcp-draft-refined-v3.md`

**Reference Standard:** https://arxiv.org/pdf/2508.01965v1
- Successfully submitted arXiv paper
- Shows correct bibliography format with hyperlinked authors
- No raw URLs visible

## Tech Stack

- **Language:** Python 3.12+
- **Parser:** markdown-it-py (AST-based, no regex)
- **LaTeX:** xelatex + bibtex
- **Bibliography:** spbasic_pt.bst (Springer author-year style)
- **Citations:** natbib with `\citep{}` / `\citet{}`
- **Font:** 10pt (arXiv mandatory)

## 7-Phase Workflow

### Phase 1: Validate Markdown (Pre-conversion)

**Check:**
1. **Brackets:** Every `[` has `]`, every `(` has `)`
2. **Tables:** Parse with markdown-it-py, verify column counts
3. **Citations:** Extract all `[Author (Year)](URL)` patterns

**Script:** `scripts/validate_markdown_structure.py`

**Output:**
```json
{
  "brackets": {"errors": 0, "citations": 87},
  "tables": {"count": 3, "errors": []},
  "citations": {"total": 87, "dois": 65, "arxiv": 12}
}
```

### Phase 2: Resolve Citations (100% Required)

**Priority Chain:**
1. **Zotero API** (primary) → Query by DOI/arXiv ID
2. **Local .bib files** (fallback) → Search cached metadata
3. **BLOCK if missing** → Generate report, stop conversion

**Tool:** `mcp-servers/deep-biblio/convert-with-zotero-api.py`

**If citations missing:**
```markdown
# Missing Citations Report
1. Consumer Affairs (2025) - Water Damage
   - URL: https://www.consumeraffairs.com/...
   - Action: Add to Zotero manually
   - Command: zotero-cli add --url "..."
```

### Phase 3: Convert MD→LaTeX

**Process:**
1. Replace citations: `[Abaza et al. (2024)](DOI)` → `\citep{abaza2024managing}`
2. Extract tables (avoid AST duplication bugs)
3. Generate preamble with 10pt font + spbasic_pt.bst
4. Create references.bib with generated BibTeX keys

**Output:** Same directory as input
- `manuscript.tex`
- `references.bib`
- `spbasic_pt.bst` (copied)
- `tables/` (if needed)

### Phase 4: Compile TEX→PDF (Zero Tolerance)

**Build Sequence:**
```bash
xelatex manuscript.tex  # Pass 1: expand refs
bibtex manuscript       # Process bibliography
xelatex manuscript.tex  # Pass 2: insert citations
xelatex manuscript.tex  # Pass 3: resolve cross-refs
```

**Validation:**
```bash
# Check errors (MUST be 0)
grep "^!" manuscript.log

# Check warnings (MUST be 0)
grep "Warning" manuscript.log

# Check PDF for (?) or (Unknown)
pdftotext manuscript.pdf
grep -E "\(\?|Unknown" manuscript.txt  # MUST be empty
```

**Script:** `scripts/compile_latex_with_validation.py`

### Phase 5: Validate Bibliography

**Requirements (from arXiv reference paper):**

**❌ WRONG - Raw URLs:**
```latex
Author (2024) Title. https://doi.org/10.1234/example
```

**✅ CORRECT - Hyperlinked authors:**
```latex
\href{https://doi.org/10.1145/3626091}{Hazem Abaza},
\href{https://doi.org/10.1145/3626091}{Debayan Roy}, ...
(2024) Managing End-to-End Timing Jitters
\textit{Proceedings of...}:229--241.
```

**Key features:**
- Each author individually hyperlinked to DOI
- Journal/conference names italicized
- Page ranges use en-dash (`--`) not hyphen (`-`)
- No visible URLs in final PDF

**Script:** `scripts/hardcode_bibliography.py`

### Phase 6: Create Test Corpus

**Extract from arXiv paper:**
1. Download https://arxiv.org/pdf/2508.01965v1
2. Extract 3-5 reference examples
3. Create minimal test case: `tests/test-files/test-mcp-conversion.md`

**Test includes:**
- Conference paper
- Journal article
- arXiv preprint
- Web URL
- One table

### Phase 7: MCP Server Integration

**Ensure MCP tool can execute entire workflow:**

```python
# MCP tool: convert_markdown_to_arxiv_latex
{
  "markdown_file": "manuscript.md",
  "zotero_api_key": "...",
  "bibliography_style": "spbasic_pt"
}
```

**Returns:**
```json
{
  "status": "success",
  "pdf_file": "manuscript.pdf",
  "validation": {
    "markdown_errors": 0,
    "missing_citations": 0,
    "latex_errors": 0,
    "latex_warnings": 0
  }
}
```

**OR if errors:**
```json
{
  "status": "error",
  "missing_citations": [...],
  "zotero_import_commands": [...]
}
```

## Sequential Execution Flow

```
INPUT: mcp-draft-refined-v3.md
  ↓
[1] Validate Markdown
  → ✓ 0 errors → Continue
  → ✗ Errors → STOP, report
  ↓
[2] Resolve Citations (Zotero API)
  → ✓ 100% resolved → Continue
  → ✗ Missing → STOP, report
  ↓
[3] Convert to LaTeX
  → Generate .tex + .bib
  ↓
[4] Compile to PDF (3-pass)
  → ✓ 0 errors, 0 warnings → Continue
  → ✗ Issues → STOP, report
  ↓
[5] Validate Bibliography
  → ✓ No raw URLs, authors hyperlinked → Continue
  → ✗ Issues → Generate .bbl, recompile
  ↓
OUTPUT: manuscript.pdf
  ✓ READY FOR ARXIV
```

## Success Metrics (Final Checklist)

**Must ALL be true:**
- [ ] 0 markdown bracket/table errors
- [ ] 87/87 citations resolved (100%)
- [ ] 0 LaTeX compilation errors
- [ ] 0 LaTeX compilation warnings
- [ ] 0 (?) in PDF output
- [ ] 0 (Unknown) in PDF output
- [ ] 0 raw URLs in bibliography
- [ ] 87 references with hyperlinked authors
- [ ] MCP server can execute autonomously

## Key Files

**To Create:**
- `scripts/validate_markdown_structure.py`
- `scripts/compile_latex_with_validation.py`
- `scripts/hardcode_bibliography.py`
- `tests/test-files/test-mcp-conversion.md`

**To Update:**
- `mcp-servers/deep-biblio/src/deep_biblio/server.py` (add arXiv workflow)
- `tests/test_arxiv_workflow.py` (integration tests)

## Common Issues

**Missing Citations:**
- Symptom: `LaTeX Warning: Citation 'key' undefined`
- Fix: Check missing-citations.md, add to Zotero

**Table Errors:**
- Symptom: `! Misplaced \noalign`
- Fix: Validate table structure, fix column count

**Raw URLs:**
- Symptom: Visible URLs in PDF reference list
- Fix: Generate hard-coded .bbl with hyperlinked authors

**Font Size Wrong:**
- Symptom: PDF has 11pt instead of 10pt
- Fix: Verify `\documentclass[10pt,...]` in preamble

## Timeline

**Total:** ~8-12 hours development + testing

**Breakdown:**
- Phase 1-2: Validation + citation (4h)
- Phase 3-4: Conversion + compilation (3h)
- Phase 5-6: Bibliography + tests (4h)
- Phase 7: MCP integration (2h)

## Commands Quick Reference

```bash
# Validate markdown
python scripts/validate_markdown_structure.py manuscript.md

# Convert with Zotero
deep-biblio-md2latex manuscript.md \
  --bibliography-style spbasic_pt \
  --zotero-api-key $ZOTERO_KEY

# Compile with validation
python scripts/compile_latex_with_validation.py manuscript.tex

# Generate hard-coded bibliography
python scripts/hardcode_bibliography.py \
  --bib references.bib \
  --output manuscript.bbl \
  --style arxiv-hyperlinked

# Full workflow via MCP
# (Claude calls convert_markdown_to_arxiv_latex tool)
```

## What Makes This "Zero-Glitch"?

1. **AST parsing** (no regex) → robust structure validation
2. **Zotero-first** → authoritative metadata, full author lists
3. **3-pass compilation** → proper reference resolution
4. **Hard-coded .bbl** → guaranteed formatting control
5. **Comprehensive validation** → catch errors before arXiv submission
6. **MCP automation** → reproducible, no manual intervention

**The key:** Block at each phase if ANY validation fails. No "close enough" - zero means zero.
