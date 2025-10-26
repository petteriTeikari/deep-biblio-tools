# Bibliography Workflow - The Complete Truth

**Status**: DEFINITIVE DOCUMENTATION
**Last Updated**: 2025-10-26
**Purpose**: Explain EXACTLY how bibliography files work in deep-biblio-tools

---

## Executive Summary

**THERE IS ONLY ONE SOURCE OF TRUTH: The CSL JSON file exported from Zotero**

Everything else is GENERATED and should be deleted before each conversion.

---

## The Single Source of Truth

### Zotero Collection → CSL JSON Export

1. **Zotero Desktop App** contains the "dpp-fashion" collection with ~100 entries
2. **User exports** this collection as CSL JSON format
3. **File saved to**: Same directory as the markdown, same base name
   - Markdown: `mcp-draft-refined-v3.md`
   - CSL JSON: `mcp-draft-refined-v3.json` (in SAME directory!)

**This CSL JSON is the ONLY source of bibliography data**

---

## What Happens During Conversion

### Step 1: Extract Citations from Markdown
- Parser reads `mcp-draft-refined-v3.md`
- Finds all `[Author, Year](URL)` citations
- Extracts 376 citation instances → ~290 unique URLs

### Step 2: Match Citations to Zotero
- Citation manager loads `mcp-draft-refined-v3.json` (CSL JSON)
- For each URL in markdown, tries to find matching entry in CSL JSON
- Matching is done by:
  - Exact URL match (after normalization)
  - arXiv ID extraction and match
  - DOI extraction and match

### Step 3: Generate BibTeX from Matched Citations
- For EACH citation found in CSL JSON:
  - Convert CSL JSON format → BibTeX format
  - Generate citation key (e.g., `angelopoulos2021`)
  - Create `@article{...}` entry with all fields
- **Write to**: `references.bib` in output directory
- **This file is GENERATED** - it's a conversion artifact, NOT source data

### Step 4: Build LaTeX Document
- LaTeX template includes `\\addbibresource{references.bib}`
- When compiled, LaTeX reads `references.bib` to resolve `\\citep{...}` commands

---

## Common Files and What They Mean

| File | Purpose | Source | Should Delete? |
|------|---------|--------|----------------|
| `mcp-draft-refined-v3.json` | CSL JSON from Zotero | **SOURCE OF TRUTH** | ❌ NEVER |
| `references.bib` | Generated BibTeX | Converted from JSON | ✅ YES, before each conversion |
| `dpp-fashion.bib` | OLD/obsolete BibTeX | Manual/old export | ✅ YES, delete entirely |
| `context/dpp-fashion.bib` | OLD/obsolete | Manual/old export | ✅ YES, delete entirely |

---

## What About `LOCAL_BIBTEX_PATH`?

**OBSOLETE AND SHOULD BE REMOVED**

The environment variable:
```bash
LOCAL_BIBTEX_PATH=/Users/petteri/Dropbox/.../dpp-fashion.bib
```

This was used in an OLD workflow where BibTeX was manually exported from Zotero. **This is no longer used** because:

1. CSL JSON is more complete and accurate
2. CSL JSON preserves all metadata properly
3. BibTeX export loses information
4. Manual exports get stale

**Action Required**:
1. Remove `LOCAL_BIBTEX_PATH` from `.env`
2. Delete all `dpp-fashion.bib` files
3. Update all documentation to reference ONLY CSL JSON

---

## Why Are Citations Missing?

### Problem: 9 missing citations in `references.bib`

**Root Causes**:

1. **Citation not in Zotero** → Need to add to Zotero, re-export JSON
2. **URL mismatch** → Citation URL in markdown doesn't match Zotero URL
3. **arXiv HTML internal refs** → `https://arxiv.org/html/2510.05566v1#bib.bib2` (not a real paper!)

### Solution Flow:

```
Missing citation detected
  ↓
Is it in Zotero JSON? NO
  ↓
Is it a real paper? YES
  ↓
Add to Zotero via API
  ↓
Re-export Zotero → CSL JSON
  ↓
Re-run conversion
  ↓
Citation now appears in references.bib ✓
```

---

## The Correct Conversion Workflow

### Prerequisites
```bash
# Ensure Zotero collection is up to date
# Export collection as CSL JSON
# Save to same directory as markdown, same base name
```

### Run Conversion
```bash
cd /path/to/markdown/directory

# Delete old generated files to avoid confusion
rm -f references.bib *.aux *.bbl *.blg *.log *.bcf *.run.xml

# Run conversion (looks for .json file automatically)
uv run --project /path/to/deep-biblio-tools \
  deep-biblio md2latex mcp-draft-refined-v3.md
```

### What Gets Created
```
mcp-draft-refined-v3.tex    # LaTeX document
references.bib               # Generated BibTeX (from CSL JSON)
Makefile                     # Build instructions
README.md                    # Usage instructions
```

### Compile PDF
```bash
make  # or xelatex + bibtex manually
```

---

## Why `references.bib` Should Be Deleted Before Each Conversion

**Problem**: If `references.bib` exists from a previous conversion:
- It may have STALE data (old Zotero export)
- It may have INCOMPLETE data (missing newly added citations)
- It causes CONFUSION about source of truth

**Solution**: ALWAYS delete `references.bib` before conversion

**Implementation**:
- Converter should delete `references.bib` at START of conversion
- User can manually delete before running
- Background bash commands already do this: `rm -f references.bib`

---

## Updating CLAUDE.md

Add to `.claude/CLAUDE.md`:

```markdown
## Bibliography Workflow

### Single Source of Truth: CSL JSON from Zotero

**NEVER** use manual BibTeX files. **ALWAYS** use CSL JSON exported from Zotero.

**File naming**: CSL JSON must be in SAME directory as markdown, with SAME base name:
- Markdown: `paper.md`
- CSL JSON: `paper.json`

**Workflow**:
1. Update Zotero collection
2. Export collection → CSL JSON format
3. Save to same directory as markdown
4. Delete old `references.bib`
5. Run conversion
6. `references.bib` is GENERATED from CSL JSON

**DO NOT**:
- ❌ Use `LOCAL_BIBTEX_PATH` environment variable (obsolete)
- ❌ Manually edit `references.bib` (it's generated)
- ❌ Keep `dpp-fashion.bib` or other manual BibTeX files
- ❌ Trust `references.bib` as source data

**DO**:
- ✅ Export fresh CSL JSON from Zotero for each conversion
- ✅ Delete `references.bib` before each conversion
- ✅ Add missing citations to Zotero, not to BibTeX manually
- ✅ Trust only CSL JSON as source of truth
```

---

## Common Errors and Solutions

### Error: "9 citations missing from .bib"

**Diagnosis**: Run `scripts/find_missing_bibtex.py`

**Solutions**:
1. If citation is real paper → Add to Zotero → Re-export JSON → Re-convert
2. If citation is arXiv HTML internal ref → Find parent paper → Add that to Zotero
3. If citation URL doesn't match Zotero → Fix URL in markdown OR Zotero

### Error: "unknownUnknown in LaTeX"

**Cause**: Citation not found in CSL JSON during conversion

**Solution**: Same as above - add missing citations to Zotero

### Error: "150+ Unknown authors"

**Cause**: Citation matching failed - URLs in markdown don't match URLs in Zotero

**Diagnosis**: Check URL normalization logic in citation manager

**Solution**: Fix URL matching algorithm OR update URLs in Zotero to match markdown

---

## Key Insight

The confusion comes from having MULTIPLE bibliography files:
- `references.bib` (generated)
- `dpp-fashion.bib` (manual/obsolete)
- `context/references.bib` (copy?)
- Environment variable pointing to wrong file

**Simple Rule**: ONE source (CSL JSON), ONE generated file (`references.bib`), DELETE before each conversion.

---

**End of Document**
