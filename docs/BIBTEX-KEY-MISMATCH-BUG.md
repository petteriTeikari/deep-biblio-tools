# BibTeX Key Mismatch Bug: Citations vs Generated Keys

**Status**: ✅ FIXED - Zotero BibTeX key integration complete
**Date Identified**: 2025-10-26
**Date Fixed (Part 1)**: 2025-10-26 (arXiv URL deduplication)
**Date Fixed (Part 2)**: 2025-10-27 (Zotero BibTeX key integration)
**Impact**: Reduced undefined citations from 3 to 1 (remaining is user typo in markdown)

---

## The Problem

LaTeX compilation shows undefined citation warnings:
```
Package natbib Warning: Citation `moore2025' on page 13 undefined
Package natbib Warning: Citation `beigi2024' on page 15 undefined
```

**However**: Both papers ARE in Zotero collection and ARE in `references.bib`!

---

## Root Cause: BibTeX Key Generation Mismatch

### What the Markdown Contains (LLM-generated citations)

```markdown
[Moore 2025](https://arxiv.org/abs/2508.12683v1)
[Moore et al. 2025](https://arxiv.org/abs/2508.08204)
[Beigi et al., 2024](https://arxiv.org/abs/2410.20199)
```

### What Citation Extractor Generates (LaTeX cite keys)

```latex
\citep{moore2025}    % Line 307 - expects "moore2025"
\citep{moore2025}    % Line 340 - expects "moore2025" (second Moore paper!)
\citep{beigi2024}    % Lines 351, 377, 381 - expects "beigi2024"
```

**Key assumption**: Citation extractor creates keys as `{first_author_lowercase}{year}`

### What Zotero API Generates (Actual BibTeX keys in references.bib)

```bibtex
@article{moorePreprintPdf2025,      # arXiv 2508.12683
  author = "...",
  url = "https://arxiv.org/abs/2508.12683",
}

@article{mooreHumanAlignmentCalibration2025,  # arXiv 2508.08204
  author = "...",
  doi = "10.48550/arXiv.2508.08204",
  url = "https://arxiv.org/abs/2508.08204",
}

@misc{beigiRethinkingUncertaintyCritical2024,
  doi = "10.48550/arXiv.2410.20199",
  url = "https://arxiv.org/html/2410.20199",
}
```

**Actual keys**: `moorePreprintPdf2025`, `mooreHumanAlignmentCalibration2025`, `beigiRethinkingUncertaintyCritical2024`

---

## The Mismatch

| Markdown Citation | Expected LaTeX Key | Actual Zotero Key | Match? |
|------------------|-------------------|-------------------|--------|
| `[Moore 2025](2508.12683)` | `moore2025` | `moorePreprintPdf2025` | ❌ |
| `[Moore et al. 2025](2508.08204)` | `moore2025` | `mooreHumanAlignmentCalibration2025` | ❌ |
| `[Beigi et al., 2024](2410.20199)` | `beigi2024` | `beigiRethinkingUncertaintyCritical2024` | ❌ |

**Additional problem**: Both Moore papers map to same key `moore2025` but are different papers!

---

## Why This Happens

### Zotero BibTeX Key Generation

Zotero's default BibTeX export uses this pattern:
```
{first_author}{TitleFirstWord}{year}
```

Examples:
- `moorePreprintPdf2025` = Moore + "Preprint" + 2025
- `mooreHumanAlignmentCalibration2025` = Moore + "HumanAlignmentCalibration" + 2025
- `beigiRethinkingUncertaintyCritical2024` = Beigi + "RethinkingUncertaintyCritical" + 2024

### Our Citation Extractor Key Generation

See `src/converters/md_to_latex/citation_manager.py`:
```python
def generate_bibtex_key(self, citation: Citation) -> str:
    """Generate a BibTeX key from citation metadata."""
    # Simplified: {first_author}{year}
    return f"{first_author.lower()}{year}"
```

**The problem**: We generate simple `author+year` keys, but Zotero generates `author+title+year` keys.

---

## Better BibTeX Solution (Planned)

**Better BibTeX plugin** allows pinning stable, customizable citation keys:

### BBT Configuration
```
citation key format: [auth:lower][year]
```

This would generate:
- `moore2025` (but collision issue for multiple Moore 2025 papers!)
- `beigi2024`

**Even better approach** (recommended):
```
citation key format: [auth:lower][year][veryshorttitle:lower]
or
citation key format: [auth:lower][shortyear][0][>0]
```

Generates:
- `moore2025a`, `moore2025b` (for multiple papers)
- `beigi2024`

---

## Current Workaround: None

**User correctly noted**: "those entries are found from the Zotero but there was the bibtex key mismatch that we wanted to address with Better BibTeX"

The citations ARE in Zotero. The problem is:
1. **Key generation mismatch**: Zotero uses title-based keys, we generate simple keys
2. **No key resolution**: We don't look up what key Zotero actually assigned
3. **Collision issue**: Multiple papers by same author+year map to same key in our system

---

## Solutions (In Priority Order)

### Solution 1: Better BibTeX Integration (PLANNED - Phase 3)

See `docs/IMPLEMENTATION-PLAN-ANTI-BRITTLENESS.md` Phase 3.

**Benefits**:
- Stable, predictable keys
- Customizable format
- Can pin keys to avoid changes
- Industry standard for academic workflows

**Implementation**: See `docs/SESSION-END-SUMMARY.md` - DO NOT START until Phase 1 & 2 complete

### Solution 2: Fetch Keys from Zotero API (Short-term fix)

Modify `citation_manager.py` to:
1. Extract citation URL/DOI
2. Query Zotero API for matching entry
3. Extract the actual BibTeX key Zotero assigned
4. Use that key in LaTeX

**Pros**: Works immediately, no Zotero plugin required
**Cons**: API overhead, requires URL/DOI matching logic

### Solution 3: Post-process BibTeX File (Hacky workaround)

After Zotero generates `references.bib`:
1. Parse all entries
2. Create alias entries with simplified keys:
```bibtex
@article{moore2025,  % Alias
  crossref = {moorePreprintPdf2025}
}
```

**Pros**: Zero code changes to converter
**Cons**: Hacky, doesn't solve collision issue

---

## Testing Strategy

### Regression Test (when fixing)

```python
def test_bibtex_key_matching():
    """Ensure generated LaTeX keys match Zotero BibTeX keys."""

    # Test case: Moore 2025 papers
    citations = [
        Citation(url="https://arxiv.org/abs/2508.12683", authors=["Moore"], year=2025),
        Citation(url="https://arxiv.org/abs/2508.08204", authors=["Moore"], year=2025),
    ]

    # Fetch Zotero entries
    zotero_entries = fetch_zotero_bibtex("dpp-fashion")

    # Generate keys
    for citation in citations:
        our_key = generate_bibtex_key(citation)
        zotero_key = find_matching_zotero_key(citation, zotero_entries)

        assert our_key == zotero_key, \
            f"Key mismatch for {citation.url}: {our_key} != {zotero_key}"
```

### Example Debug Artifacts (when logging added)

`debug-04-matching-results.json` should show:
```json
{
  "citation": {
    "markdown": "[Moore 2025](https://arxiv.org/abs/2508.12683)",
    "url": "https://arxiv.org/abs/2508.12683",
    "authors": ["Moore"],
    "year": 2025
  },
  "generated_key": "moore2025",
  "zotero_key": "moorePreprintPdf2025",
  "match_status": "KEY_MISMATCH",
  "resolution": "FAILED - undefined citation in LaTeX"
}
```

---

## Related Documentation

- **SESSION-END-SUMMARY.md** - Phase 3 BBT integration plan
- **CRITICAL-REGRESSION-ANALYSIS.md** - Original 0/366 regression analysis
- **APPENDIX-OPENAI-RECOMMENDATIONS.md** - BBT plugin architecture notes
- **IMPLEMENTATION-PLAN-ANTI-BRITTLENESS.md** - Full 3-phase roadmap

---

## Action Items

1. **IMMEDIATE**: Document this bug (✅ DONE - this file)
2. **Phase 1**: Add debug logging to capture key mismatches
3. **Phase 2**: Add regression test for key matching
4. **Phase 3**: Implement Better BibTeX integration
5. **Future**: Consider Solution 2 (API-based key lookup) as fallback

---

## Key Takeaway

**This is NOT a "missing citations" problem.**
**This IS a "citation key mismatch" problem.**

The citations exist in Zotero. The BibTeX entries exist in `references.bib`.
But the LaTeX `\citep{moore2025}` command doesn't match the actual key `@article{moorePreprintPdf2025}`.

**Better BibTeX** is the correct long-term solution, but requires:
1. Debug logging infrastructure (Phase 1)
2. Regression testing (Phase 2)
3. Careful BBT integration (Phase 3)

DO NOT attempt quick fixes without safety nets in place.

---

## Phase 3 Progress: Part 1 - arXiv URL Normalization (COMPLETED)

**Date**: 2025-10-26
**Commit**: feat: Fix arXiv URL deduplication in citation extractor

### Problem Found

The citation extractor was creating DUPLICATE citations for the same arXiv paper when the markdown contained URLs with and without version specifiers:

```markdown
[Moore 2025](https://arxiv.org/abs/2508.12683v1)  → moore2025
[Moore, 2025](https://arxiv.org/abs/2508.12683)   → moore2025b
```

Same paper, two different citation keys!

### Solution Implemented

Added arXiv URL normalization to `citation_extractor_unified.py`:

```python
# Import normalize_arxiv_url from utils
from src.converters.md_to_latex.utils import normalize_arxiv_url

# In extract_citations():
# Normalize arXiv URLs to remove version specifiers (v1, v2, etc.)
# This prevents duplicate citations for the same paper
url = normalize_arxiv_url(url)
```

### Results

- **Before**: 368 citations extracted (including 3 duplicates)
- **After**: 365 citations extracted (duplicates eliminated)
- **Test case**: Moore 2025 paper no longer appears twice

### Remaining Work (Phase 3 Part 2)

The key mismatch problem still exists but is now CLEARER:

```
LaTeX uses:        \citep{moore2025}
BibTeX has:        @article{moorePreprintPdf2025,
```

This requires mapping Zotero's generated keys to our simpler keys. Options:
1. Use Zotero's keys directly in LaTeX (replace our key generation)
2. Create alias entries in BibTeX (@article{moore2025, crossref={moorePreprintPdf2025}})
3. Implement Better BibTeX integration for stable, simple keys

**Recommendation**: Option 1 is simplest and most robust. Extract the actual key from Zotero's BibTeX output and use that in the LaTeX \citep commands.

---

## Phase 3 Part 2: FIXED - Zotero BibTeX Key Integration (2025-10-27)

**Date**: 2025-10-27
**Commit**: fix: Use Zotero BibTeX keys instead of generated keys

### The One-Line Fix

Changed converter.py line 896:
```python
# BEFORE (WRONG):
matched, missing = self._populate_from_zotero_api(citations, collection_name)

# AFTER (CORRECT):
matched, missing = self._populate_from_zotero_bibtex(citations, collection_name)
```

### Why This Worked

The infrastructure to use Zotero's Better BibTeX keys **already existed** at line 277-419!
The `_populate_from_zotero_bibtex()` method:
1. Fetches BibTeX export from Zotero (includes actual citation keys)
2. Parses BibTeX entries to extract `cite_key` (e.g., `moorePreprintPdf2025`)
3. Builds lookup maps (URL→key, DOI→key, arXiv→key)
4. Matches citations and sets `citation.key = matched_key`

This method was **written but never called**. We were calling `_populate_from_zotero_api()` instead, which generates simple keys.

### Results

**Before (using _populate_from_zotero_api)**:
- Missing entries: `song2024`, `beigl2024`, `nafar2025` (3 total)
- LaTeX: `\citep{moore2025}`
- BibTeX: `@article{moorePreprintPdf2025,`
- Result: ❌ Undefined citations

**After (using _populate_from_zotero_bibtex)**:
- Missing entries: `beigl2024` (1 total - user typo in markdown)
- LaTeX: `\citep{moorePreprintPdf2025}`
- BibTeX: `@article{moorePreprintPdf2025,`
- Result: ✅ Citations resolve correctly

### Remaining Issue: User Typo (Not a Bug)

The markdown file has inconsistent spelling of the same author:
- Lines 314, 340, 344: `[Beigi et al., 2024]` ✅ Correct
- Lines 336, 538 (twice): `[Beigl et al., 2024]` ❌ Typo (extra 'l')

The converter correctly generated two different keys:
- `beigi2024` → matches Zotero entry ✅
- `beigl2024` → no matching entry in Zotero ❌

**This is not a converter bug** - it's working exactly as designed. The user needs to fix the markdown typo.

### Test Coverage

Regression test in `tests/test_citation_pipeline.py::test_pdf_validation_artifact` now uses:
- Debug artifact: `tests/fixtures/debug-runs/mcp-draft-refined-v4-20251027-000434/`
- Shows 1 missing entry (beigl2024) which is expected user typo
- Test will fail if missing entries increase (regression detection working!)

### Verification

PDF validation from debug-06-pdf-validation.json:
```json
{
  "pdf_exists": true,
  "pdf_size": 376058,
  "missing_entries": ["beigl2024"],
  "has_unresolved": true
}
```

Success metrics:
- ✅ PDF generated successfully (376KB)
- ✅ 365 citations extracted
- ✅ Only 1 missing entry (known user typo)
- ✅ All Zotero-matched citations resolve correctly
- ✅ No undefined (?) citations except for the typo

### User Action Required

Fix the markdown typo by changing all "Beigl" to "Beigi" in lines 336 and 538:
```bash
# In the mcp-draft-refined-v4.md file:
s/Beigl et al., 2024/Beigi et al., 2024/g
```

After this fix, the PDF will have **ZERO** missing citations.

---

## Summary: Bug Status

| Phase | Date | Action | Missing Citations |
|-------|------|--------|-------------------|
| Initial | 2025-10-26 | Discovered bug | 3 (song2024, beigl2024, nafar2025) |
| Part 1 | 2025-10-26 | arXiv URL normalization | Still 3 |
| Part 2 | 2025-10-27 | Zotero BibTeX key integration | 1 (beigl2024 - user typo) |
| Future | TBD | User fixes markdown typo | 0 ✅ |

**Conclusion**: The BibTeX key mismatch bug is **FIXED**. The converter now correctly uses Zotero's Better BibTeX keys. The remaining missing entry is a user typo in the source markdown, not a converter issue.
