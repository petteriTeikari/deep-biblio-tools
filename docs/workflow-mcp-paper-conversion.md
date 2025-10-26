# MCP Paper Conversion Workflow - Critical Context

**Last Updated**: 2025-10-26
**Purpose**: Document the complete workflow and critical decisions for converting the MCP paper from Markdown to arXiv-ready LaTeX

## Executive Summary

This document captures the COMPLETE workflow for preparing the MCP (Model Context Protocol) paper for arXiv submission. The key challenge is that **LLMs hallucinate citation details**, especially author names, so we need **deterministic validation against authoritative sources** (Zotero, CrossRef, arXiv APIs).

## Critical File Locations (DO NOT FORGET THESE!)

### Input Paper Location
```
/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/
├── mcp-draft-refined-v3.md          # Source markdown
├── mcp-draft-refined-v3.json        # Zotero library (CSL JSON format)
├── dpp-fashion.bib                  # BibTeX export from Zotero (in context/ subdir)
└── author-verification.json         # Verification results
```

### Tool Repository Location
```
/Users/petteri/Dropbox/github-personal/deep-biblio-tools/
├── .env                            # Zotero credentials (ALWAYS HERE!)
├── scripts/
│   ├── verify_author_names.py     # Verify citations match Zotero
│   ├── fix_anchor_citations.py    # Fix anchor-link citations
│   └── add_unknown_citations_to_zotero.py  # Add missing citations
└── src/converters/md_to_latex/     # Conversion pipeline
```

### Environment Variables (.env)
```bash
# Location: /Users/petteri/Dropbox/github-personal/deep-biblio-tools/.env
ZOTERO_API_KEY=CvF3rPEqyRUPtREz7gGcvOWP
ZOTERO_LIBRARY_ID=4953359
ZOTERO_LIBRARY_TYPE=user
LOCAL_BIBTEX_PATH=/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/context/dpp-fashion.bib
```

**IMPORTANT**: Scripts MUST use `python-dotenv` to load these credentials. Always add at the top of scripts:
```python
from dotenv import load_dotenv
load_dotenv()  # Loads from .env in project root
```

## The Complete Workflow

### Phase 1: Citation Validation (COMPLETED)

#### Step 1.1: Fix Invalid arXiv Citations
**Problem**: Some citations had fake arXiv IDs like `2025.mcp.taxonomy`

**Solution**: Fixed 10 occurrences in `mcp-draft-refined-v3.md`:
- `[Zhao et al., 2025](https://arxiv.org/abs/2025.mcp.taxonomy)` → `https://arxiv.org/abs/2509.24272`
- `[Li et al., 2025](https://arxiv.org/abs/2025.mcp.privilege)` → `https://arxiv.org/abs/2507.06250`
- `[Wang et al., 2025](https://arxiv.org/abs/2025.mpma)` → `https://arxiv.org/abs/2505.11154`

**Status**: ✅ FIXED

#### Step 1.2: Fix Broken Google A2A URLs
**Problem**: 7 citations pointed to 404 URL: `https://developers.google.com/agent-to-agent`

**Solution**: Replaced with correct URL: `https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/`

**Status**: ✅ FIXED

#### Step 1.3: Fix Anchor-Link Citations
**Problem**: Citations were pointing to `https://arxiv.org/html/2510.05566v1#bib.bibXX` (bibliography anchors in another paper) instead of the actual papers

**Solution**:
1. Fetched the source paper's HTML
2. Extracted bibliography entries
3. Found original paper URLs (arXiv/DOI)
4. Created `fix_anchor_citations.py` script with mappings
5. Replaced 9 anchor citations with proper URLs

**Key Papers Fixed**:
- Vovk et al., 2005 → `https://doi.org/10.1007/b106715`
- Angelopoulos et al., 2020 → `https://arxiv.org/abs/2009.14193`
- Romano et al., 2019 → `https://arxiv.org/abs/1905.03222`
- Tibshirani et al., 2019 → `https://arxiv.org/abs/1904.06019`
- Barber et al., 2023 → `https://arxiv.org/abs/2202.13415`
- Kumar et al., 2023 → `https://arxiv.org/abs/2305.18404`
- Ye et al., 2024 → `https://arxiv.org/abs/2401.12794`
- Moreno-Torres et al., 2012 → `https://doi.org/10.1016/j.patcog.2011.06.019`
- Recht et al., 2019 → `https://arxiv.org/abs/1902.10811`

**Status**: ✅ FIXED

### Phase 2: Author Name Verification (IN PROGRESS)

#### Step 2.1: Verify ALL Author Names
**Problem**: LLMs hallucinate author names. Need to verify EVERY citation matches the actual authors in Zotero.

**Method**: Match citation text last names (e.g., "[Wang et al., 2024]") against Zotero JSON authors

**Script**: `scripts/verify_author_names.py`

**Results** (from author-verification.json):
- **Total citations**: 291
- **Verified (correct)**: 177 (61%)
- **Author mismatches**: 52 (18%) ❌ CRITICAL ISSUE
- **Not in Zotero**: 60 (21%) ❌ CRITICAL ISSUE

**Example Mismatch**:
```
Line 191: [Wang et al., 2024](https://arxiv.org/abs/2401.13178)
Citation author(s): Wang
Zotero authors: Chang Ma, Junlei Zhang, Zhihao Zhu
Issue: NO WANG AS AUTHOR! Wrong paper in Zotero!
```

**Status**: ⚠️ IN PROGRESS - Need to fix 52 mismatches + add 60 missing citations

#### Step 2.2: Add Missing Citations to Zotero
**Problem**: 60 citations are NOT in Zotero at all (28 unique URLs after deduplication)

**Solution**: Use `scripts/add_unknown_citations_to_zotero.py` to:
1. Read `author-verification.json`
2. Fetch metadata from DOI/arXiv/CrossRef APIs
3. Add to Zotero collection 'dpp-fashion' via API

**CRITICAL**: This script MUST use python-dotenv to load credentials!

**Command**:
```bash
cd /Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review
uv run --project /Users/petteri/Dropbox/github-personal/deep-biblio-tools \
  python3 /Users/petteri/Dropbox/github-personal/deep-biblio-tools/scripts/add_unknown_citations_to_zotero.py \
  --results author-verification.json \
  --collection dpp-fashion
```

**Status**: ❌ NOT STARTED - Waiting for script update to use dotenv

#### Step 2.3: Fix Author Mismatches in Zotero
**Problem**: 52 citations have WRONG papers in Zotero (author names don't match)

**Solution**: Manual review required
1. Review each mismatch in `author-verification.json`
2. Search for correct paper in Zotero or add if missing
3. Update Zotero entry to match the correct paper

**Status**: ❌ NOT STARTED

### Phase 3: Zotero Library Update (PENDING)

#### Step 3.1: Add Missing Papers
Use `add_unknown_citations_to_zotero.py` to add 28 unique missing papers

**Status**: ❌ PENDING

#### Step 3.2: Export Updated Zotero JSON
After adding/fixing papers:
1. Go to Zotero desktop app
2. Right-click 'dpp-fashion' collection
3. Export Collection → CSL JSON format
4. Save to: `/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/mcp-draft-refined-v3.json`

**Status**: ❌ PENDING

#### Step 3.3: Re-run Author Verification
After updating Zotero, re-verify ALL authors:
```bash
cd /Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review
uv run --project /Users/petteri/Dropbox/github-personal/deep-biblio-tools \
  python3 /Users/petteri/Dropbox/github-personal/deep-biblio-tools/scripts/verify_author_names.py \
  mcp-draft-refined-v3.md \
  mcp-draft-refined-v3.json \
  --output author-verification-FINAL.json
```

**Target**: 0 mismatches, 0 missing

**Status**: ❌ PENDING

### Phase 4: Markdown to LaTeX Conversion (PARTIALLY WORKING)

#### Step 4.1: Run Conversion
```bash
cd /Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review
export LOCAL_BIBTEX_PATH=/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/dpp-fashion.bib
uv run --project /Users/petteri/Dropbox/github-personal/deep-biblio-tools \
  deep-biblio md2latex mcp-draft-refined-v3.md
```

**Current Issue**: LaTeX compilation fails with invalid character `^^?` in:
```latex
\citep{unknownUnknown^^?}
```

This happens when citations are NOT found in Zotero → creates `unknownUnknown` entries

**Status**: ⚠️ BLOCKED - Need to fix Zotero library first

### Phase 5: LaTeX Validation and PDF Compilation (NOT STARTED)

#### Step 5.1: Validate LaTeX
- Check all citations resolve
- No `unknownUnknown` entries
- No invalid characters
- All BibTeX entries valid

#### Step 5.2: Compile PDF
```bash
cd /Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review
make  # Uses xelatex + bibtex
```

**Status**: ❌ NOT STARTED

## Critical Decisions and Principles

### 1. Zotero is the Single Source of Truth
- **ALL** citations MUST be in Zotero
- **ALL** author names MUST match Zotero exactly
- No manual BibTeX editing - fix Zotero, then re-export

### 2. CSL JSON Format
The `mcp-draft-refined-v3.json` file is **CSL JSON**, NOT Zotero's internal format:
- Authors: `author` array with `family` and `given` fields (NOT `creators` with `lastName`)
- URL: Uppercase `URL` (NOT lowercase `url`)
- No `data` wrapper

**Scripts MUST handle both formats!**

### 3. Environment Variables via .env
**NEVER** rely on shell environment variables. **ALWAYS** use python-dotenv:
```python
from dotenv import load_dotenv
load_dotenv()  # Loads .env from project root

import os
api_key = os.getenv("ZOTERO_API_KEY")
library_id = os.getenv("ZOTERO_LIBRARY_ID")
```

### 4. URL Normalization for Matching
When matching citations to Zotero entries:
- Remove `http://` and `https://`
- Remove `www.`
- Remove trailing `/`
- For arXiv: normalize to just ID (remove version suffix `v1`, `v2`)
- For DOI: extract just the DOI part

Example:
```python
https://arxiv.org/abs/2509.24272v1 → arxiv:2509.24272
https://doi.org/10.1007/s10479-023-05477-1 → doi:10.1007/s10479-023-05477-1
```

### 5. Never Remove or Ignore Problems
**WRONG**: "Citation not found, removing..."
**RIGHT**: "Citation not found, adding to Zotero via API..."

**WRONG**: "Author mismatch, skipping..."
**RIGHT**: "Author mismatch, need to fix Zotero entry..."

When errors are found, **FIX THEM**, don't work around them!

## Common Issues and Solutions

### Issue: "VIRTUAL_ENV points to old KusiKasa path"
**Problem**: Shell environment has stale `VIRTUAL_ENV=/Users/petteri/Dropbox/LABs/KusiKasa/github/deep-biblio-tools/.venv`

**Solution**: Clear from shell profile:
```bash
# Add to ~/.zshrc or ~/.bashrc
unset VIRTUAL_ENV
# Remove KusiKasa path from PATH
```

### Issue: "Scripts can't find Zotero credentials"
**Problem**: Scripts don't load .env file

**Solution**: Add to top of ALL scripts:
```python
from dotenv import load_dotenv
load_dotenv()
```

### Issue: "Loaded 0 entries from Zotero"
**Problem**: Script expects Zotero internal JSON format, but file is CSL JSON

**Solution**: Handle both formats:
```python
# CSL JSON: Direct access
item_data = item
url = item_data.get("URL", "")  # Uppercase
authors = item_data.get("author", [])
last_name = author.get("family", "")

# Zotero JSON: Wrapped in "data"
item_data = item.get("data", item)
url = item_data.get("url", "")  # Lowercase
creators = item_data.get("creators", [])
last_name = creator.get("lastName", "")
```

### Issue: "unknownUnknown entries in LaTeX"
**Problem**: Citations not found in Zotero during conversion

**Solution**:
1. Add missing citations to Zotero via API
2. Fix wrong papers in Zotero
3. Re-export Zotero JSON
4. Re-run conversion

### Issue: "Invalid character ^^? in LaTeX"
**Problem**: Unicode or encoding issues in citation keys

**Solution**: Fix at source (Zotero) before conversion

## What User Has Repeatedly Asked For

### 1. "Stop forgetting the file locations!"
- Input paper: `/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/mcp-draft-refined-v3.md`
- Zotero JSON: **SAME DIRECTORY**, same name: `mcp-draft-refined-v3.json`
- .env file: **ALWAYS** at `/Users/petteri/Dropbox/github-personal/deep-biblio-tools/.env`

### 2. "Why aren't scripts using dotenv?"
ALL scripts should load .env automatically. No excuses.

### 3. "If citations are missing, ADD THEM to Zotero!"
Don't report and stop. Use the Zotero API to add them programmatically.

### 4. "If authors don't match, FIX IT!"
Don't skip or ignore. Fix the Zotero entry.

### 5. "Don't remove anchor citations, find the original papers!"
Anchor links like `#bib.bib31` reference real papers. Fetch the source HTML, extract the bibliography, find the original URLs.

## Current Status Summary

### ✅ Completed
1. Fixed 10 invalid arXiv citations
2. Fixed 7 broken Google A2A URLs
3. Fixed 9 anchor-link citations
4. Created author verification system
5. Identified 52 author mismatches
6. Identified 28 unique missing citations

### ⚠️ In Progress
1. Update scripts to use python-dotenv

### ❌ Blocked/Pending
1. Add 28 missing citations to Zotero via API (waiting for dotenv)
2. Fix 52 author name mismatches in Zotero (manual review)
3. Export updated Zotero JSON
4. Re-run author verification (target: 0 errors)
5. Re-run LaTeX conversion (target: no unknownUnknown entries)
6. Compile PDF successfully

## Next Immediate Actions

1. **Update `add_unknown_citations_to_zotero.py`** to use dotenv
2. **Run script** to add 28 missing citations
3. **User exports** updated Zotero JSON
4. **Re-run** author verification
5. **Review and fix** remaining mismatches
6. **Re-export** Zotero JSON
7. **Re-run** conversion → should succeed with 0 unknownUnknown entries

## Files to Reference

### Reports Generated
```
/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/
├── author-verification.json          # Current verification results
├── citation-validation.json          # URL validation results
├── citation-validation.log           # Validation execution log
└── CITATION-VALIDATION-FINAL-REPORT.md  # Human-readable summary
```

### Scripts to Use
```
/Users/petteri/Dropbox/github-personal/deep-biblio-tools/scripts/
├── verify_author_names.py            # Verify citations match Zotero
├── fix_anchor_citations.py           # Fix bibliography anchor links
├── add_unknown_citations_to_zotero.py  # Add missing citations via API
└── validate_all_citations.py         # Validate all citation URLs
```

## User's Zotero Workflow

### Adding Papers Manually
User manually added 3 MCP security papers to Zotero:
- Zhao et al., 2025 (2509.24272)
- Li et al., 2025 (2507.06250)
- Wang et al., 2025 (2505.11154)

### Exporting Zotero Collection
1. Open Zotero desktop
2. Right-click collection "dpp-fashion"
3. Export Collection
4. Format: CSL JSON
5. Save to: `/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/mcp-draft-refined-v3.json`

## Key Insight: Why This Matters

The entire purpose of `deep-biblio-tools` is to solve the **LLM citation hallucination problem**. LLMs make up author names, years, titles, and even entire papers. The ONLY way to ensure correctness is:

1. **Deterministic validation** against authoritative APIs (CrossRef, arXiv)
2. **Zotero as single source of truth** for all citation metadata
3. **Automated verification** that EVERY citation matches its Zotero entry exactly
4. **No manual intervention** in the conversion process - fix Zotero, re-export, re-convert

This is NOT just about converting Markdown to LaTeX. It's about **provably correct citations** that won't embarrass the author or get rejected by arXiv reviewers.

---

**End of Document**

If you're an AI assistant reading this in the future: READ THIS ENTIRE DOCUMENT CAREFULLY before asking the user for file locations or credentials. Everything you need to know is documented here.
