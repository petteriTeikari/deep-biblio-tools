# Citation Filtering Fix - Execution Plan
**Date**: 2025-10-31 23:30
**Context**: Programmatic tests show filters NOT working + 117 unknown citations
**Test Results**: `verify_citation_filtering.py` shows 43 issues (15 non-academic not filtered + 28 arXiv normalization failures)

---

## Problem Summary

### Test Results from verify_citation_filtering.py

**❌ Test 1: Non-Academic Domain Exclusions FAILED**
- 15 non-academic links found in missing citations list
- Domains: GitHub (4), Fashion United (3), YouTube (1), X.com (1), Medium (1), company sites (5)
- **Root cause**: Filter code in `citation_extractor_unified.py` NOT being executed during conversion

**❌ Test 2: arXiv URL Normalization FAILED**
- 28 arXiv issues: 15 with version numbers (v1), 13 with /html/ variants
- **Root cause**: `normalize_arxiv_url()` EXISTS but `citation_manager.py:1640` doesn't call it
- Example: `https://arxiv.org/abs/2510.04618v1` → should be `https://arxiv.org/abs/2510.04618`
- Example: `https://arxiv.org/html/2509.10691v1` → should be `https://arxiv.org/abs/2509.10691`

**⚠️ Test 3: Unknown Citations Issue**
- 117 citations classified as "Unknown" (neither academic nor non-academic)
- User concern: "we have 117 citations that you do not even know what they are!? Sounds really bad!"
- **Root cause**: Classification lists incomplete - many legitimate non-academic domains missing

### What This Proves

The user was RIGHT (from FIX-CITATION-MATCHING-ACTIONABLE-PLAN-2025-10-31.md):
> "we struggle so much with this as you try to create stuff from scratch and end up re-implementing the same stuff all over again without re-using old tools :("

I added filter code but it's not integrated into the actual execution pipeline.

---

## What Was Already Done

### 2025-10-31 23:18-23:22 - Background Documentation
**Created**: Three documentation files
1. `docs/reference/bibtex-citation-generation-and-classification.md`
   - Documents citation vs hyperlink patterns
   - Citation format: `[Author (Year)](URL)` with year
   - Inline link format: `[Text](URL)` without year

2. `docs/reference/identifier-matching-strategies.md`
   - Documents existing multi-strategy matching (DOI → arXiv → ISBN → URL)
   - **CRITICAL**: Documents that `extract_arxiv_id()` ALREADY strips versions (utils.py:821-827)
   - **CRITICAL**: Documents that `normalize_arxiv_url()` ALREADY normalizes variants (utils.py:468-507)
   - These functions EXIST but aren't being called during matching!

3. `docs/planning/FIX-CITATION-MATCHING-ACTIONABLE-PLAN-2025-10-31.md`
   - Actionable plan referencing existing code
   - Identified that existing code isn't being used

### 2025-10-31 23:25 - Code Changes
**Modified**: `src/converters/md_to_latex/citation_extractor_unified.py`
1. Added `NON_ACADEMIC_DOMAINS` set (lines 87-113)
2. Updated `_is_academic_url()` to check exclusions FIRST (lines 215-219)
3. Added explicit filter in `extract_citations_from_markdown()` (lines 420-427)

**Result**: Code changes committed but **NOT TESTED** - filters not working in practice

### 2025-10-31 23:30 - Verification Script
**Created**: `scripts/verify_citation_filtering.py`
- Imports NON_ACADEMIC_DOMAINS from production code (no hard-coding)
- Tests that non-academic domains are excluded
- Tests arXiv normalization (versions stripped, /html/ normalized)
- Generates detailed report with specific violations
- **Result**: Confirmed filters NOT working (43 issues found)

---

## Root Cause Analysis

### Issue 1: Filter Code Not Being Used

**Evidence**: No "Skipping non-academic link" messages in logs
**Location**: `citation_extractor_unified.py` lines 420-427
**Problem**: The `extract_citations_from_markdown()` method I modified is likely NOT the code path used during conversion

**Hypothesis**: `citation_manager.py` might use a different method or bypass this filtering

**Search needed**:
```bash
# Find where citations are extracted during conversion
grep -rn "extract.*citation" src/converters/md_to_latex/citation_manager.py
grep -rn "UnifiedCitationExtractor" src/converters/md_to_latex/citation_manager.py
grep -rn "MarkdownParser" src/converters/md_to_latex/citation_manager.py
```

### Issue 2: arXiv Normalization Not Applied

**Evidence**: `https://arxiv.org/abs/2510.04618v1` in missing citations
**Location**: `citation_manager.py:1640`
**Problem**: Uses `normalize_url(href)` but NOT `normalize_arxiv_url()`

**Current code** (citation_manager.py:1640):
```python
normalized_href = normalize_url(href)
```

**Should be**:
```python
normalized_href = normalize_arxiv_url(normalize_url(href))
```

**Verification**:
- Read citation_manager.py around line 1640
- Check if `normalize_arxiv_url()` is imported
- Check if it's called anywhere in the matching pipeline

### Issue 3: 117 Unknown Citations

**Evidence**: Verification report shows 117 links neither academic nor non-academic
**Location**: `citation_extractor_unified.py` lines 89-113 (NON_ACADEMIC_DOMAINS)
**Problem**: Classification lists incomplete

**Examples of likely "unknown" domains**:
- News sites: bbc.com, bloomberg.com, reuters.com
- Government: europa.eu, commission.europa.eu, gov.uk
- Organizations: wbcsd.org, oecd.org, un.org
- Blogs: towards datascience.com, hackernoon.com
- Documentation: docs.python.org, developer.mozilla.org

**Solution**: Expand NON_ACADEMIC_DOMAINS to cover these categories

---

## Execution Plan

### Phase 1: Comprehensive Search (10 minutes)

#### Step 1.1: Find ALL Citation Extraction Locations
```bash
# Find where citations are extracted
grep -rn "extract_citations" src/converters/md_to_latex/*.py

# Find where MarkdownParser is used
grep -rn "MarkdownParser" src/converters/md_to_latex/*.py

# Find where links are processed
grep -rn "extract_links" src/converters/md_to_latex/*.py
```

**Output**: Table of all locations

| File | Line | Function | Purpose |
|------|------|----------|---------|
| ... | ... | ... | ... |

#### Step 1.2: Find ALL Matching Locations
```bash
# Find where URLs are normalized
grep -rn "normalize_url" src/converters/md_to_latex/*.py

# Find where arXiv normalization is called
grep -rn "normalize_arxiv_url" src/converters/md_to_latex/*.py

# Find URL matching logic
grep -rn "url_to_key" src/converters/md_to_latex/*.py
```

**Output**: Table of all locations

| File | Line | Function | Normalizes arXiv? |
|------|------|----------|-------------------|
| ... | ... | ... | Yes/No |

#### Step 1.3: Analyze "Unknown" Citations
```bash
# Extract all "unknown" citation URLs
grep "Unknown" /tmp/test-exclusions-verification-report.txt

# Manually classify top 20 by domain
# Add appropriate categories to NON_ACADEMIC_DOMAINS
```

**Output**: List of domains to add to NON_ACADEMIC_DOMAINS

### Phase 2: Fix Filter Integration (15 minutes)

#### Step 2.1: Trace Citation Extraction Path
**Task**: Understand which code path is actually used during conversion

**Files to read**:
1. `src/converters/md_to_latex/citation_manager.py` - Where citations are matched
2. `src/converters/md_to_latex/converter.py` - Where conversion happens
3. `src/converters/md_to_latex/citation_extractor_unified.py` - Where filtering is

**Questions to answer**:
- Does citation_manager.py use UnifiedCitationExtractor?
- Which method does it call?
- Is my filter code in the right place?

#### Step 2.2: Add Filtering at Correct Location
**Based on findings from 2.1**, add filtering where citations are ACTUALLY extracted

**Options**:
- Option A: citation_manager.py needs to call `extract_academic_citations()` instead of `extract_citations()`
- Option B: Filtering needs to happen in citation_manager.py directly
- Option C: Current location is correct but method isn't being called

**Implementation**: TBD after analysis

#### Step 2.3: Add Debug Logging
```python
# At citation extraction point
logger.info(f"Extracting citations using UnifiedCitationExtractor")
logger.info(f"Found {len(all_links)} total links")
logger.info(f"Classified: {academic_count} academic, {non_academic_count} non-academic")

# At filtering point
if not citation.is_academic:
    logger.info(f"Skipping non-academic link: [{citation.text}]({citation.url})")
```

### Phase 3: Fix arXiv Normalization (5 minutes)

#### Step 3.1: Verify normalize_arxiv_url Import
**File**: `src/converters/md_to_latex/citation_manager.py`

Check if `normalize_arxiv_url` is imported:
```python
from src.converters.md_to_latex.utils import normalize_arxiv_url, normalize_url
```

If not imported, add it.

#### Step 3.2: Update Normalization Call
**Location**: `citation_manager.py` around line 1640

**Current**:
```python
normalized_href = normalize_url(href)
```

**Change to**:
```python
# Normalize arXiv URLs first (strip versions, normalize /html/ → /abs/)
# Then apply general URL normalization (http/https, trailing slash)
normalized_href = normalize_url(normalize_arxiv_url(href))
```

**Add logging**:
```python
if href != normalized_href:
    logger.debug(f"URL normalized: {href} → {normalized_href}")
```

#### Step 3.3: Apply Same Fix to All Matching Locations
**Based on grep results from Phase 1**, apply arXiv normalization to ALL URL matching locations

### Phase 4: Expand Classification Lists (10 minutes)

#### Step 4.1: Analyze Unknown Citations
**From verification report**, extract domains of "unknown" citations

**Categories to add**:

1. **News and Media**:
   - `bbc.com`, `bloomberg.com`, `reuters.com`, `theguardian.com`
   - `wsj.com`, `ft.com`, `economist.com`

2. **Government and International Organizations**:
   - `europa.eu`, `ec.europa.eu`, `commission.europa.eu`
   - `gov.uk`, `gov`, `.gov.`  (various government domains)
   - `un.org`, `oecd.org`, `who.int`

3. **Industry Organizations and Standards Bodies**:
   - `wbcsd.org`, `iso.org`, `w3.org`
   - `ietf.org`, `opengroup.org`

4. **Tech Blogs and Documentation**:
   - `towardsdatascience.com`, `hackernoon.com`
   - `docs.`, `developer.` (documentation sites)

5. **Company Blogs**:
   - `anthropic.com/`, `openai.com/blog`
   - `blog.`, `/blog/` in path

#### Step 4.2: Update NON_ACADEMIC_DOMAINS
**File**: `src/converters/md_to_latex/citation_extractor_unified.py`

Add comprehensive list with comments:
```python
NON_ACADEMIC_DOMAINS = {
    # === Code Repositories ===
    "github.com",
    "gitlab.com",
    "bitbucket.org",

    # === Social Media ===
    "x.com",
    "twitter.com",
    "facebook.com",
    "linkedin.com",
    "instagram.com",
    "youtube.com",
    "reddit.com",

    # === Tech Blogs and Developer Sites ===
    "medium.com",
    "substack.com",
    "dev.to",
    "towardsdatascience.com",
    "hackernoon.com",

    # === Q&A Sites ===
    "stackoverflow.com",
    "stackexchange.com",

    # === News and Media ===
    "bbc.com",
    "bloomberg.com",
    "reuters.com",
    "theguardian.com",
    "wsj.com",
    "ft.com",
    "economist.com",

    # === Government and International Orgs ===
    "europa.eu",
    "ec.europa.eu",
    "commission.europa.eu",
    ".gov.uk",
    ".gov",
    "un.org",
    "oecd.org",
    "who.int",

    # === Industry Organizations ===
    "wbcsd.org",
    "iso.org",
    "w3.org",
    "ietf.org",

    # === Company Websites ===
    "haelixa.com",
    "oritain.com",
    "entrupy.com",
    "eon.xyz",
    ".xyz",  # Startup TLD
    "fashionunited.com",
    "sigmatechnology.com",
}
```

**Goal**: Reduce "unknown" classifications from 117 to <10

### Phase 5: Developer Smoke Test (10 minutes)

#### Step 5.1: Run Test Conversion
```bash
rm -f /tmp/dev-smoke-test-final.log

time uv run python scripts/deterministic_convert.py \
  "/home/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/mcp-draft-refined-v5.md" \
  --rdf "/home/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/dpp-fashion-zotero.rdf" \
  --output-dir "/tmp/dev-smoke-final" \
  --allow-failures \
  2>&1 | tee /tmp/dev-smoke-test-final.log
```

#### Step 5.2: Run Verification Script
```bash
uv run python scripts/verify_citation_filtering.py \
  "/home/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/mcp-draft-refined-v5.md" \
  "/tmp/dev-smoke-test-final.log"
```

**Expected results**:
- ✅ Test 1: Non-academic exclusions PASS (0 violations)
- ✅ Test 2: arXiv normalization PASS (0 issues)
- ✅ Unknown citations reduced from 117 to <10

#### Step 5.3: Check Debug Logging
```bash
# Verify filter messages appear
grep -c "Skipping non-academic link" /tmp/dev-smoke-test-final.log
# Should be > 0 (at least 15 based on test results)

# Verify URL normalization messages
grep -c "URL normalized.*arxiv" /tmp/dev-smoke-test-final.log
# Should be > 0 (at least 28 based on test results)
```

#### Step 5.4: Create Evidence Document
```markdown
# Developer Smoke Test Evidence

## Test Results
- Time: X seconds
- Total links: 605
- Academic: X
- Non-academic (filtered): Y
- Unknown: Z (target: <10)

## Verification Script Results
- Test 1 (Non-academic exclusions): PASS/FAIL
- Test 2 (arXiv normalization): PASS/FAIL
- Missing citations: X (down from 141)

## Log Analysis
- "Skipping non-academic" count: X
- "URL normalized" count: X
- No errors/warnings: Yes/No

## Status
- Ready for user testing: Yes/No
- Issues found: [list if any]
```

### Phase 6: Commit with Evidence (5 minutes)

```bash
# Format and lint
uv run ruff check --fix
uv run ruff format

# Commit CLAUDE.md update
git add .claude/CLAUDE.md
git commit -m "docs: Add TDD and verification requirements to CLAUDE.md

- Ban blind fixes without comprehensive search
- Require developer smoke tests before commits
- Require test-driven development with debug logging
- Require programmatic tests that import from production code

Addresses user feedback about shallow fixes and lack of verification."

# Commit plan
git add docs/planning/FIX-CITATION-FILTERING-EXECUTION-PLAN-2025-10-31.md
git commit -m "docs: Citation filtering fix execution plan

Based on verify_citation_filtering.py results:
- 15 non-academic links not filtered
- 28 arXiv normalization failures
- 117 unknown citations

Plan includes comprehensive search, proper integration, and expanded classification."

# Commit code fixes (after Phase 2-4 complete)
git add src/converters/md_to_latex/citation_extractor_unified.py
git add src/converters/md_to_latex/citation_manager.py
git commit -m "fix: Integrate citation filtering and arXiv normalization

VERIFIED with developer smoke test:
- Filters now execute during conversion
- arXiv URLs normalized (versions stripped, /html/ → /abs/)
- Unknown citations reduced from 117 to X

Evidence: /tmp/dev-smoke-test-final.log
Tests: verify_citation_filtering.py shows 0 issues"

# Push
git push origin fix/verify-md-to-latex-conversion
```

---

## Success Criteria

### Critical (Must Pass)
1. ✅ `verify_citation_filtering.py` reports 0 issues
2. ✅ "Skipping non-academic link" messages appear in logs
3. ✅ arXiv URLs normalized in matching pipeline
4. ✅ Unknown citations < 10 (down from 117)

### Quality (Should Pass)
5. ✅ Missing citations reduced from 141 to ~50-80 (legitimate academic papers)
6. ✅ Debug logging shows filtering decisions
7. ✅ Conversion time still <30 seconds

### Documentation (Must Have)
8. ✅ Evidence document with test results
9. ✅ Commit messages reference verification
10. ✅ CLAUDE.md updated with TDD requirements

---

## Files to Modify

### DONE
- ✅ `.claude/CLAUDE.md` - Add TDD requirements
- ✅ `docs/planning/FIX-CITATION-FILTERING-EXECUTION-PLAN-2025-10-31.md` - This file

### TODO (Phase 2-4)
- ⏳ `src/converters/md_to_latex/citation_manager.py` - Add arXiv normalization to matching
- ⏳ `src/converters/md_to_latex/citation_extractor_unified.py` - Expand NON_ACADEMIC_DOMAINS
- ⏳ Possibly other files based on comprehensive search results

### CREATED (Already)
- ✅ `scripts/verify_citation_filtering.py` - Programmatic test
- ✅ `docs/reference/bibtex-citation-generation-and-classification.md`
- ✅ `docs/reference/identifier-matching-strategies.md`
- ✅ `docs/planning/FIX-CITATION-MATCHING-ACTIONABLE-PLAN-2025-10-31.md`

---

## Timeline

- **Phase 1** (Comprehensive search): 10 min
- **Phase 2** (Fix filter integration): 15 min
- **Phase 3** (Fix arXiv normalization): 5 min
- **Phase 4** (Expand classification): 10 min
- **Phase 5** (Developer smoke test): 10 min
- **Phase 6** (Commit with evidence): 5 min

**Total**: ~55 minutes

---

## Next Steps

1. ✅ Update CLAUDE.md (DONE)
2. ✅ Create this execution plan (DONE)
3. ⏳ Commit both
4. ⏳ Execute Phase 1 (Comprehensive search)
5. ⏳ Execute Phase 2-4 (Fixes)
6. ⏳ Execute Phase 5 (Smoke test)
7. ⏳ Execute Phase 6 (Commit with evidence)

**Status**: Ready to commit and start execution
