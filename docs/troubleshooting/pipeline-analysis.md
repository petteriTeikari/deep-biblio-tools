# Citation Pipeline Root Cause Analysis

## Executive Summary

**Status**: Pipeline is partially working but has multiple critical issues
**Impact**: 121 out of 381 citations (32%) have incomplete metadata
**Root Causes**: Invalid DOIs from LLM, auto-add not integrated into main flow, validation bugs

---

## Current State (October 29, 2025)

### What's Working ✅
1. **Zotero Integration**: 260 citations (68%) successfully loaded from Zotero
   - 247 Web API keys
   - 13 Legacy Zotero keys
   - Pagination working (658/659 entries fetched)
   - Patents now included

2. **Better BibTeX Principle**: No keys being generated - all keys from Zotero as-is

3. **Auto-add Functionality EXISTS**: `citation_matcher.py:add_to_zotero_library()` implemented

### What's Broken ❌

1. **Auto-add NOT Integrated into Main Pipeline**
   - Function exists in `citation_matcher.py`
   - NOT called from `citation_manager.py`
   - Result: 121 temporary citations created but never added to Zotero

2. **Invalid/Hallucinated DOIs from LLM**
   - Example: `agrawal2021` has DOI `10.1016/j.compind.2021.107130`
   - CrossRef API returns 404 - DOI doesn't exist
   - Pipeline creates stub entry: "Agrawal and others" with no title
   - Should be flagged as CRITICAL error, not hidden with Temp key

3. **Validation False Positives**
   - Entries with complete authors flagged as "INCOMPLETE_AUTHORS"
   - Example: `duan_uprop_2025` has all 6 authors but flagged as incomplete
   - Example: `beigi_rethinking_2024` has all 12 authors but flagged as incomplete
   - Impact: 62 false positives out of 72 "HIGH" severity issues

4. **Poor Error Reporting**
   - Temporary keys hide the real problem
   - Invalid DOIs not reported as CRITICAL
   - No clear signal to user that citations are incomplete

---

## Data Analysis

### Test File: mcp-draft-refined-v4.md
- **Total citations**: 381
- **From Zotero**: 260 (68%)
- **Temporary/incomplete**: 121 (32%)

###Validation Results
- **INFO (good)**: 289 (76%)
- **HIGH severity**: 72 (19%) - **MOSTLY FALSE POSITIVES**
  - Real incomplete authors: ~10
  - False positives: ~62
- **CRITICAL**: 1 (0.3%)

### Example Failures

| Citation | Issue | Root Cause |
|----------|-------|------------|
| agrawal2021 | No title, "Agrawal and others" | Invalid DOI (404 from CrossRef) |
| axios2025 | Placeholder title | Web page, no proper metadata |
| google2024 | Placeholder title | Web page, no proper metadata |
| duan_uprop_2025 | Flagged "incomplete authors" | **FALSE POSITIVE** - has all 6 authors |
| beigi_rethinking_2024 | Flagged "incomplete authors" | **FALSE POSITIVE** - has all 12 authors |

---

## Code Flow Analysis

### Current Flow for Missing Citations

```
1. extract_citations() finds citation in markdown
   └─> NOT in Zotero collection
       └─> Creates temporary key (e.g., "agrawalTemp2021")
           └─> fetch_citation_metadata()
               ├─> Try Zotero translation server
               ├─> Try CrossRef (DOI)
               ├─> Try arXiv
               └─> If all fail: stub entry with minimal data
           └─> ❌ NEVER calls add_to_zotero_library()
```

### Where Auto-Add Should Be Called

The `add_to_zotero_library()` function exists but is never invoked. It should be called:
- **After** successful metadata fetch from CrossRef/arXiv
- **Before** creating temporary key
- **With** full metadata (title, authors, DOI, etc.)

---

## Priority Fixes

### P0 - Critical (Must Fix)
1. **Integrate auto-add into main pipeline**
   - Call `add_to_zotero_library()` from `citation_manager.py`
   - Only after successful metadata fetch
   - Return proper Zotero key, not Temp key

2. **Validate DOIs before fetch**
   - HEAD request to CrossRef before full fetch
   - Fail fast on 404
   - Report as CRITICAL error to user

3. **Fix validation false positives**
   - Update author validation logic
   - Don't flag entries with 6+ complete authors as incomplete

### P1 - High (Should Fix)
4. **Improve error reporting**
   - Log invalid DOIs with citation context (markdown line number)
   - Report count of failed auto-adds at end
   - Clear distinction between "not in Zotero" vs "invalid DOI"

5. **Better CrossRef/arXiv fetching**
   - Retry on transient failures
   - Better error messages
   - Cache negative results (404s)

### P2 - Medium (Nice to Have)
6. **Validation improvements**
   - Accept "et al" for papers with >15 authors
   - Better detection of placeholder titles
   - Distinguish web pages from academic papers

---

## Next Steps

1. ✅ Complete this analysis
2. [ ] Get user approval for priority fixes
3. [ ] Implement P0 fixes one by one
4. [ ] Test with mcp-draft-refined-v4.md
5. [ ] Verify all Temp citations resolved

---

## Questions for User

1. Should we auto-add ALL missing citations to Zotero, or only those with valid DOIs?
2. For invalid DOIs (404s), should we:
   - Skip them entirely and show as (?) in PDF
   - Try to find correct DOI via title/author search
   - Add to Zotero anyway with incomplete metadata as placeholder
3. For web pages (axios, google, etc.), should we auto-add them as "webpage" items in Zotero?

---

Generated: 2025-10-29
