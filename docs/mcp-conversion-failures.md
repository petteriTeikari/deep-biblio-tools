# MCP Conversion Failures and Fixes

## Document Purpose
Track ALL failures in mcp-draft-refined-v3.md conversion and systematically fix them.
DO NOT claim success until ALL tests pass.

## Test Suite Location
`scripts/test_mcp_conversion.py` - deterministic test that checks for:
1. Zero Unknown authors in BibTeX
2. Zero internal cross-references treated as citations
3. PDF generates successfully
4. Zero LaTeX errors
5. Zero BibTeX warnings

## Current Status

### Baseline (Before Fixes)
```
❌ FAIL | No Unknown authors: 201 found (expected: 0)
❌ FAIL | No internal refs as citations: 79 found (expected: 0)
✅ PASS | PDF generated: 229 KB
❌ FAIL | LaTeX errors: 1, warnings: 0
```

**Breakdown of 201 Unknown Citations:**
- 79 internal cross-references (URLs like #abstract, #1.-introduction)
- 105 external URLs failing to fetch metadata
- 17 other

## Fixes Applied

### Fix #1: Filter Internal Cross-References
**File**: `src/converters/md_to_latex/citation_extractor_unified.py`
**Line**: 104-113
**Status**: APPLIED, NOT TESTED YET

**Problem**: Internal document references like `[Abstract](#abstract)` were being treated as citations requiring BibTeX entries.

**Solution**: Added filter in `extract_citations()` to skip URLs starting with `#`:
```python
# Skip internal cross-references (URLs starting with #)
if url.startswith("#"):
    logger.debug(f"Skipping internal cross-reference: {link_info['text']} -> {url}")
    continue
```

**Expected Impact**: Should reduce Unknown citations from 201 to ~122 (201 - 79 = 122)

**Test Command**: `python3 scripts/test_mcp_conversion.py`

**Result**: PENDING

---

## Remaining Issues to Fix

### Issue #2: External URL Metadata Fetching (105 failing)
**Status**: NOT STARTED

**Examples of Failing URLs:**
- DOIs: `https://doi.org/10.1007/978-3-031-70262-4_5`
- News: `https://www.bbc.com/news/business-44885983`
- Bloomberg: `https://www.bloomberg.com/news/articles/...`
- EU Parliament: `https://www.europarl.europa.eu/thinktank/en/document/...`
- Academic: `https://studenttheses.uu.nl/handle/20.500.12932/48177`

**Investigation Needed:**
1. Check which URL fetcher is being used
2. Check if APIs are being called correctly
3. Check if cache is interfering
4. Check error logs for why fetches are failing

**Files to Examine:**
- `src/converters/md_to_latex/citation_manager.py` - handles metadata fetching
- Citation fetcher implementation (need to find)

### Issue #3: 1 LaTeX Error
**Status**: NOT INVESTIGATED

**Need to check**: `/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/mcp-draft-refined-v3.log` for error details

### Issue #4: 17 Other Unknown Citations
**Status**: NOT INVESTIGATED

Need to examine what these 17 are (201 - 79 internal - 105 external = 17)

---

## Success Criteria

ALL of these must be TRUE:
- [ ] Zero Unknown authors in references.bib
- [ ] Zero internal cross-references treated as citations
- [ ] PDF generates (>200KB)
- [ ] Zero LaTeX errors
- [ ] Zero BibTeX warnings

---

## Next Steps

1. **Test Fix #1**: Run `python3 scripts/test_mcp_conversion.py`
2. **If Fix #1 Works**: Move to Issue #2 (external URL fetching)
3. **If Fix #1 Fails**: Debug why internal refs still appearing
4. **Document ALL Results**: Update this file after EVERY test run
5. **NO BLIND FIXES**: Always investigate first, then fix, then test

---

## Test Results Log

### Test Run #1 - PARTIAL SUCCESS ✅
**Date**: 2025-10-26 ~9:00 AM
**Changes**: Fix #1 applied (filter internal cross-refs)
**Command**: `python3 scripts/test_mcp_conversion.py`
**Result**:
```
❌ FAIL | No Unknown authors: 124 found (expected: 0) [was 201, reduced by 77]
❌ FAIL | No internal refs as citations: 1 found (expected: 0) [was 79, reduced by 78]
✅ PASS | PDF generated: 222 KB
❌ FAIL | LaTeX errors: 1, warnings: 0
```

**Analysis**:
- ✅ Fix #1 mostly works: Eliminated 78 out of 79 internal cross-references
- ❌ 1 internal ref still remains (need to investigate which one)
- ❌ Still have 124 Unknown authors (need to fix external URL fetching)
- ❌ 1 LaTeX error persists (need to check log file)

### Test Run #2 - With Improved Test Suite
**Date**: 2025-10-26 ~9:30 AM
**Changes**: Upgraded test suite with JSON output and offender extraction
**Command**: `python3 scripts/test_mcp_conversion.py`
**Result**:
```
❌ FAIL (124) | No Unknown authors (expected: 0)
❌ FAIL (1) | No internal refs as citations (expected: 0)
✅ PASS | PDF generated (size: 212 KB)
❌ FAIL (1 errors, 458 warnings) | LaTeX compilation clean
```

**Top 10 Offending Citations**:
1. Amazon link (craft book)
2. arXiv:2309.07864
3. modelcontextprotocol.io docs
4. Google developer docs
5. Okta developer blog
6. arXiv:2410.10762
7. arXiv:2304.03442
8. Anthropic engineering blog
9. DOI:10.1002/sd.2474
10. EU legal document

**ROOT CAUSE FOUND**:
The citation extractor does NOT fetch metadata from URLs. Instead, it parses author/year from the citation text using heuristics in `citation_extractor_unified.py:318-350`.

**The Heuristic Only Recognizes**:
- `[Author (2020)](url)` - with parentheses around year

**But Manuscript Uses**:
- `[Xi et al., 2023](url)` - WITHOUT parentheses (comma-separated)

**Example**:
- Markdown: `[Xi et al., 2023](https://arxiv.org/abs/2309.07864)`
- Extractor looks for: `(2023)` with parentheses
- Doesn't find it → sets author="Unknown", year="Unknown"

**Solution Options**:
1. Fix text parsing heuristic to handle "Author et al., YEAR" format
2. Implement actual URL metadata fetching from arXiv/CrossRef/DOI APIs
3. Both (parse text as fallback, fetch URLs as primary)

---

## Notes

- User correctly pointed out: "can't you have some proper deterministic test suite written"
- User correctly pointed out: I claimed success with 63% citation failure rate
- User correctly pointed out: I violated "no blind fixes" rule
- This document is to prevent those failures from recurring
- **RULE**: Update this document after EVERY test run
- **RULE**: Do NOT claim success unless test passes
