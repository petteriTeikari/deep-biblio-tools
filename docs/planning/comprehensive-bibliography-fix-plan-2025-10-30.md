# Comprehensive Bibliography Fix Plan - 2025-10-30

## Executive Summary

This document provides a **systematic, multi-layered analysis** of why bibliography conversion keeps failing, synthesizing:
- All user requests from current session
- Existing documentation (`bibliography-extraction-issues.md`, `bibliography-quality-analysis.md`)
- CLAUDE.md guardrails and success criteria
- Code analysis (`CitationMatcher`, `bibliography_sources.py`, `citation_manager.py`)

**The pattern**: We keep finding "the issue", fixing it, yet problems persist. This suggests **multiple simultaneous failure points**, not a single bug.

**User's core insight**: "This should be easy - I have almost all entries in Zotero, max 1-2 missing citations expected."

## The User's Journey (This Session)

### User Requests in Chronological Order

1. **Initial request**: Review recent commits from last 6 hours (VSCode crashed mid-session)
2. **Emergency conversion**: Create tool that matches citations from markdown to local `dpp-fashion.json` file (manual Zotero export) - bypass API
3. **Architectural clarification**: "The emergency part is just the SOURCE of ground truth, otherwise the code should be the same right?" - reuse existing matching logic
4. **Identifier-based matching**: Match by extracting DOI/arXiv ID/ISBN from URLs, not naive URL strings
5. **Recurring Fletcher frustration**: "Fletcher issues have been reoccurring multiple times... I keep getting tired having to explain them"
6. **Systematic analysis request**: "Systematic means systematic.. no shallow work... explore multiple points of failure"
7. **Final meta-request**: "Pause for a moment, and do a proper plan instead of this whac-a-moling"

### User's Explicit Frustrations

> "This is getting so ridiculous this session with you, this is now taking a week already to convert a fucking markdown to .tex"

> "It is the same fucking Niinimäki et al. (2020) that you seem to struggle, why is it always that you fail to match it?"

> "Can you go through some old docs again for Fletcher issue... I already documented the Fletcher there which I have pasted you multiple times"

> "People have been creating latex documents successfully for centuries before any AI, and now it somehow is problematic when you are being reactive ;)"

**Key insight**: User is tired of explaining same issues repeatedly. Documentation exists but isn't being leveraged.

## What We Know (From Existing Documentation)

### From `docs/known-issues/bibliography-extraction-issues.md`

**Documented recurring issues** (lines 246-393):

1. **Fletcher/Amazon book issue** (documented multiple times)
   - Missing ISBN in Zotero export despite book having ISBN
   - Amazon URL in markdown instead of DOI
   - CitationMatcher CAN extract ISBN from Amazon URLs (has utility function)
   - But Zotero export has no ISBN to match against
   - **Root cause**: Zotero export quality, not matching logic

2. **"et al" parsing catastrophe**
   - System treats "al" as last name: `al A.`
   - Creates nonsensical author entries
   - Results in "et, al." with comma before "al"

3. **Missing entry types**
   - Many entries have `@misc` instead of proper types
   - Affects formatting in bibliography

4. **arXiv HTML URLs**
   - Markdown has `arxiv.org/html/2508.02765`
   - Should normalize to abstract: `arxiv.org/abs/2508.02765`
   - CitationMatcher has `extract_arxiv_id()` that strips versions and formats

5. **ResearchGate blocking**
   - API calls to ResearchGate get blocked
   - Need alternative metadata sources

### From `docs/troubleshooting/bibliography-quality-analysis.md`

**Seven hypotheses with confidence levels** (lines 89-453):

1. **Auto-add was in dry-run mode** (95% confidence) - **PRIMARY ROOT CAUSE**
   - Default setting doesn't actually add missing citations
   - Creates stub entries with temp keys
   - Fix: Use `--auto-add-real` flag

2. **Translation-server metadata extraction failed** (85% confidence)
   - Amazon URLs don't provide proper metadata
   - Web pages return generic titles
   - Fix: Enhance metadata extraction or require better source URLs

3. **Validation logic has blind spots** (95% confidence)
   - Validator checks for "Unknown"/"Anonymous" but not stub titles
   - Allows "Amazon.de" or "Web page by axios" to pass
   - Fix: Enhance `EntryValidator` to catch stub titles

4. **Markdown source insufficient** (70% confidence)
   - Amazon URLs instead of DOIs
   - YouTube links instead of proper citations
   - Fix: Improve markdown quality (long-term)

5. **Zotero collection missing recent additions** (60% confidence)
   - Entries added to Zotero but not in specified collection
   - Fix: Verify collection sync

6. **Better BibTeX keys not generated** (50% confidence)
   - Entries in Zotero but without Better BibTeX keys
   - Fix: Re-trigger Better BibTeX key generation

7. **Stale output files validated** (80% confidence)
   - Reading old PDF/BibTeX from previous run
   - Fix: Delete outputs before conversion

**Priority-ranked fixes** (lines 455-511):
1. Run with --auto-add-real (HIGHEST - 80% impact)
2. Enhance EntryValidator (HIGH)
3. Verify translation-server (MEDIUM)
4. Improve markdown source quality (LONG-TERM)
5. Create standalone markdown validator (STRATEGIC)

### From `.claude/CLAUDE.md` (Guardrails)

**Success criteria** (lines 291-318):

**BEFORE claiming conversion success, verify ALL:**
1. ✅ PDF generates without LaTeX errors
2. ✅ PDF has ZERO (?) citations
3. ✅ PDF has ZERO (Unknown) or (Anonymous) citations
4. ✅ All citations show proper author names and years
5. ✅ references.bib has ZERO "Unknown" or "Anonymous" entries
6. ✅ LaTeX log has ZERO compilation errors
7. ✅ BibTeX log has ZERO fatal errors (warnings OK)

**Forbidden intermediate "success" claims:**
- ❌ "citations extracted" - meaningless without verification
- ❌ "BibTeX generated" - meaningless if it contains Unknown entries
- ❌ "PDF compiled" - meaningless if citations show as (?)

**Required workflow:**
1. Run conversion
2. Check references.bib for Unknown/Anonymous entries
3. If found, FIX the root cause (don't just report it)
4. Re-run conversion
5. Read the PDF with Read tool
6. Verify EVERY citation shows author names (not ?)
7. ONLY THEN claim success

**Bibliography workflow** (lines 155-244):
- `references.bib` is EPHEMERAL (generated output, not source)
- SINGLE SOURCE OF TRUTH: Zotero Web API (long-term) or local export (emergency)
- Better BibTeX keys: ≥15 chars, camelCase, semantic (e.g., `niinimakiEnvironmentalPriceFast2020`)
- NEVER generate keys locally

## What We Have (Existing Code)

### `citation_matcher.py` - Production Matching Logic

**Multi-strategy matching** (lines 117-174):
1. **DOI extraction and matching** (most reliable)
   - Handles doi.org, dx.doi.org, sci-hub
   - Normalizes to lowercase

2. **ISBN extraction and matching** (books)
   - Extracts from Amazon URLs
   - Removes hyphens, normalizes

3. **arXiv ID extraction** (preprints)
   - Extracts from abs/html/pdf URLs
   - Strips version numbers

4. **URL normalization and matching**
   - Protocol normalization (http→https)
   - Trailing slash removal
   - Case normalization

5. **Fuzzy fallback** (TODO - not implemented)
   - Author + year + title matching

6. **Zotero write-back** (if enabled)
   - Auto-add missing citations

**This code is PRODUCTION-GRADE and should be reused, not replaced.**

### `bibliography_sources.py` - Modular Sources

**Already implemented** (lines 1-491):
- `BiblographySource` abstract interface
- `LocalFileSource` - loads from BibTeX/CSL JSON/RDF
- `ZoteroAPISource` - fetches from Zotero Web API
- `create_bibliography_source()` - factory pattern

**BibTeX parsing** (lines 136-219):
- Uses `bibtexparser` (AST-based, no regex - per CLAUDE.md)
- Converts BibTeX → CSL JSON
- Field mapping: ID→id, author→parsed, isbn→ISBN, doi→DOI
- Type mapping: article→article-journal, patent→patent

**This refactor is DONE and committed (fe2d3b6).**

### `converter.py` + `citation_manager.py` - Integration

**Recent changes**:
- `CitationManager` now uses modular sources
- Initializes `CitationMatcher` with loaded entries
- Handles both uppercase (CSL JSON) and lowercase (legacy) field names

## What's Broken (Current Status)

### Immediate Bug: File Format Mismatch

**Error from background process 5e1c41:**
```
Error: Expecting value: line 1 column 1 (char 0)
Sources Attempted:
  - json: /home/petteri/.../dpp-fashion-better-bibtex.bib
```

**Root cause**: User passed `--json` flag pointing to `.bib` file, but code tries to parse as JSON.

**Location**: `scripts/deterministic_convert.py` line 197-199
```python
converter = MarkdownToLatexConverter(
    zotero_json_path=json_path if json_path else None,  # Expects .json
    ...
)
```

**Fix**: Rename parameter to `bibliography_file_path` and let `bibliography_sources.py` detect format from extension.

### Major Issues from Conversion Attempt

**207 citations extracted, MASSIVE matching failures:**

1. **Fletcher book** (Amazon URL)
   - `https://www.amazon.de/.../Kate-Fletcher/dp/1138021016`
   - Not matched (recurring issue documented multiple times)

2. **50+ arXiv papers** not matched
   - `https://arxiv.org/abs/2509.25370`
   - `https://arxiv.org/abs/2503.13657`
   - These should be trivial matches via arXiv ID extraction

3. **Multiple DOI links** not matched
   - `https://doi.org/10.1016/j.jii.2022.100345`
   - `https://doi.org/10.1108/JOCM-09-2020-0299`
   - These should be trivial matches via DOI extraction

4. **Web pages and organizational URLs**
   - `https://commission.europa.eu/...`
   - `https://www.wbcsd.org`
   - Many are NOT citations (regular hyperlinks)
   - Should be filtered out (see CLAUDE.md lines 247-265)

5. **All auto-add attempts failing**
   - Returning "temp" key → validation fails
   - Creating `failedAutoAdd_*` keys
   - This suggests auto-add is not actually working

### The "Validation Theater" Problem

From `bibliography-quality-analysis.md` line 575:

> **The Validation Theater Problem**: Our validation infrastructure is sophisticated, running multiple checks at different stages. But it's optimized for "does it compile?" not "is the data quality good?"

**What this means:**
- We validate that LaTeX compiles
- We DON'T validate that "Amazon.de" is a terrible title
- We DON'T validate that temp keys shouldn't exist
- We DON'T validate that arXiv entries should have hyperlinks

**Result**: System reports "success" with garbage bibliography.

## Root Cause Analysis: Multiple Failure Layers

### Layer 1: File Format Handling (IMMEDIATE BUG)

**Problem**: Code expects `.json` file, user provides `.bib` file, parser fails.

**Impact**: BLOCKS all conversion attempts.

**Fix complexity**: LOW - rename parameter, leverage existing `LocalFileSource` format detection.

**Why it matters**: This is the FIRST failure - nothing else can work until this is fixed.

### Layer 2: CitationMatcher Not Being Used (ARCHITECTURAL)

**Problem**: Even though we have production `CitationMatcher` with sophisticated multi-strategy matching, it's not being properly invoked with local file sources.

**Evidence**:
- 50+ arXiv papers not matching (should be trivial via `extract_arxiv_id()`)
- Multiple DOIs not matching (should be trivial via `extract_doi_from_url()`)
- This suggests CitationMatcher indices not built from BibTeX entries

**Impact**: MASSIVE match failure rate (possibly 0% for current conversion).

**Fix complexity**: MEDIUM - ensure `CitationManager` initializes `CitationMatcher` with entries from `LocalFileSource`.

**Code location**: `citation_manager.py` lines 268-305 (already partially fixed in refactor, needs verification)

### Layer 3: Hyperlink vs Citation Filtering (DESIGN)

**Problem**: Code treats ALL markdown links as citations, creating false positives.

**From CLAUDE.md (lines 247-265):**
- Citations: `[Author (Year)](URL)` or `[Author et al., Year](URL)`
- Regular links: `[Text](URL)` - NO year in brackets

**Examples from conversion attempt:**
- `[European Commission](https://commission.europa.eu/...)` - NOT a citation
- `[WBCSD](https://www.wbcsd.org)` - NOT a citation
- `[YouTube video](https://www.youtube.com/watch?v=...)` - NOT a citation

**Impact**: Creates dozens of false "missing citations", pollutes bibliography.

**Fix complexity**: LOW - add year pattern detection in citation extraction.

**Code location**: `citation_extractor_unified.py` (mentioned in CLAUDE.md line 265)

### Layer 4: Zotero Export Quality (DATA QUALITY)

**Problem**: Even when matching works, Zotero export may lack critical fields.

**Fletcher book example**:
- Book has ISBN: 978-1138021013
- BibTeX export missing `isbn` field
- CitationMatcher can extract ISBN from Amazon URL
- But nothing to match against

**Impact**: Some citations will NEVER match without fixing Zotero data.

**Fix complexity**: HIGH - requires manual Zotero data curation OR enhanced export.

**Why it matters**: This explains why "Fletcher keeps failing" - it's not a code bug, it's data quality.

### Layer 5: Auto-Add Failure (FEATURE NOT WORKING)

**Problem**: When citations don't match, auto-add should add them to Zotero. Instead, it's returning "temp" keys and failing.

**Evidence from conversion log:**
```
Citation key 'temp' does not match Zotero format
⚠️  Allow-failures enabled - generating temp key and continuing
  Temporary key: failedAutoAdd_986951
```

**Impact**: No recovery mechanism for missing citations.

**Fix complexity**: MEDIUM - debug why auto-add returns "temp" instead of proper keys.

**Code location**: `citation_matcher.py` lines 176-219 `_add_to_zotero()`

### Layer 6: Validation Blind Spots (QUALITY ASSURANCE)

**Problem**: Validator doesn't catch stub titles, temp keys, missing hyperlinks.

**From `bibliography-quality-analysis.md`:**
- Allows "Amazon.de" as title
- Allows "Web page by axios" as title
- Doesn't check for temp keys
- Doesn't verify arXiv entries have URLs

**Impact**: Garbage passes validation, users see bad bibliography.

**Fix complexity**: MEDIUM - enhance `EntryValidator` with stricter rules.

**Code location**: Need to find `EntryValidator` class.

## The Systematic Fix Plan

### Phase 1: EMERGENCY - Get PDF Today (1-2 hours)

**Goal**: User submits manuscript with working citations.

**Assumption**: User's Zotero export contains 95%+ of citations (max 1-2 missing).

**Strategy**: Fix ONLY Layer 1 and Layer 2 - get matching working with local BibTeX file.

#### Task 1.1: Fix File Format Handling

**File**: `scripts/deterministic_convert.py`

**Changes**:
```python
# Line 197-199: BEFORE
converter = MarkdownToLatexConverter(
    zotero_json_path=json_path if json_path else None,
    ...
)

# AFTER
converter = MarkdownToLatexConverter(
    bibliography_file_path=json_path if json_path else None,  # Rename param
    ...
)
```

**File**: `src/converters/md_to_latex/converter.py`

**Changes**:
```python
# Constructor: rename zotero_json_path → bibliography_file_path
def __init__(
    self,
    bibliography_file_path: Path | str | None = None,  # Renamed
    ...
):
    self.bibliography_file_path = bibliography_file_path  # Store path
```

**Verification**: Run `deterministic_convert.py` with `.bib` file, should not crash with JSON parse error.

#### Task 1.2: Verify CitationMatcher Integration

**File**: `src/converters/md_to_latex/citation_manager.py`

**Check lines 268-305**: Ensure CitationMatcher is initialized with entries from LocalFileSource.

**Expected behavior**:
1. `LocalFileSource` loads `.bib` file
2. Converts BibTeX → CSL JSON (already implemented)
3. CSL entries passed to `CitationMatcher.__init__()`
4. CitationMatcher builds indices (DOI, ISBN, arXiv, URL)
5. Matching uses indices

**Verification**: Add logging to see index sizes:
```python
logger.info(f"CitationMatcher indices: {len(self.citation_matcher.doi_index)} DOIs, "
            f"{len(self.citation_matcher.arxiv_index)} arXiv")
```

#### Task 1.3: Test Conversion with BibTeX

**Command**:
```bash
uv run python scripts/deterministic_convert.py \
  "/path/to/mcp-draft-refined-v4.md" \
  --json "/path/to/dpp-fashion-better-bibtex.bib" \  # Will auto-detect .bib format
  --output-dir "/path/to/output" \
  --allow-failures  # For first test
```

**Expected result**:
- High match rate (>90%) via DOI, arXiv, ISBN indices
- Few unmatched citations (web pages, organizational links)
- PDF generates with minimal (?) citations

**Verification per CLAUDE.md**:
1. Check `references.bib` for Unknown/Anonymous entries
2. Read PDF to verify citations show author names
3. Count (?) citations - should be <10 out of 207

#### Task 1.4: Handle Remaining Mismatches

**For unmatched citations**:
1. Check if they're regular hyperlinks (no year in brackets) - filter out
2. Check if missing from BibTeX - add manually to Zotero
3. Check if data quality issue (Fletcher) - manual BibTeX entry

**Goal**: Get to ZERO (?) citations in PDF.

**Success criteria**: User can submit manuscript TODAY.

---

### Phase 2: SHORT-TERM - Fix Recurring Issues (This Week)

**Goal**: Stop Fletcher, Niinimäki, etc. from failing repeatedly.

#### Task 2.1: Implement Hyperlink Filtering

**File**: `citation_extractor_unified.py` (find this file)

**Add year pattern detection**:
```python
def is_citation_link(text: str) -> bool:
    """
    Check if markdown link is a citation vs regular hyperlink.

    Citations have author + year: [Smith (2020)](URL) or [Wang et al., 2023](URL)
    Regular links don't: [Google Docs](URL)
    """
    # Check for year pattern: (YYYY) or , YYYY
    has_year_parens = any(f"({year})" in text for year in range(1900, 2030))
    has_year_comma = any(f", {year}" in text for year in range(1900, 2030))

    return has_year_parens or has_year_comma
```

**Impact**: Eliminates false positives (European Commission, WBCSD, YouTube links).

#### Task 2.2: Enhance ISBN Matching for Books

**File**: `citation_manager.py`

**For Fletcher and other books**:
1. Check if Zotero export has ISBN field
2. If missing but book type: flag for manual review
3. Document pattern: "Books without ISBN in export require manual addition"

**Also check**: Does `bibtexparser` preserve ISBN field from BibTeX? Verify field mapping.

#### Task 2.3: Fix Auto-Add "temp" Key Issue

**File**: `citation_matcher.py` lines 176-219

**Debug why auto-add returns "temp"**:
- Check if API credentials are actually loaded
- Check if API call succeeds but returns temp key
- Check Better BibTeX plugin interaction

**Add better logging**:
```python
logger.info(f"Auto-add attempt for {url}: API credentials present: {bool(api_key)}")
logger.info(f"Zotero API response: {response}")
```

**Goal**: Auto-add should either work properly OR fail explicitly (not return temp keys).

#### Task 2.4: Document Zotero Export Best Practices

**File**: `docs/user-guides/zotero-export-guide.md` (NEW)

**Content**:
- Export format: Better BibTeX (.bib) preferred
- Required fields: DOI, ISBN, URL, author, year, title
- Better BibTeX plugin configuration
- How to verify export quality
- How to re-trigger Better BibTeX key generation
- Fletcher book case study: "Add ISBN manually in Zotero before export"

---

### Phase 3: LONG-TERM - Systematic Quality (Next Month)

**Goal**: Make this robust for hundreds of papers, not just one manuscript.

#### Task 3.1: Enhanced EntryValidator

**File**: Create `src/converters/md_to_latex/entry_validator_enhanced.py`

**Validation rules**:
1. **Stub title detection**: Flag "Amazon.de", "Web page by", generic titles
2. **Temp key detection**: Fail if any citation keys contain "temp", "failed", "unknown"
3. **Required field checks**: DOI/URL for articles, ISBN for books
4. **arXiv hyperlink check**: arXiv entries must have URL field
5. **Organization name check**: "Commission E" → "European Commission"

**Integration**: Run validator BEFORE writing BibTeX, fail early if quality issues.

#### Task 3.2: Fuzzy Matching Implementation

**File**: `citation_matcher.py` line 161-163 (currently TODO)

**Implement author + year + title fuzzy matching**:
- Use `rapidfuzz` library (already in dependencies?)
- Match on: first author last name + year + first 3 words of title
- Threshold: 85% similarity
- ONLY as fallback when DOI/ISBN/arXiv/URL fail

**Goal**: Catch cases where URL changed but metadata is same.

#### Task 3.3: Translation-Server Enhancement

**Investigate why metadata extraction fails**:
- Amazon URLs return generic titles
- Web pages return "Web page by..." placeholders
- Check if translation-server is even running

**Options**:
1. Use CrossRef API for DOI metadata
2. Use arXiv API for preprint metadata
3. Require users provide better source URLs in markdown

#### Task 3.4: Markdown Pre-Validation Tool

**File**: `scripts/validate_markdown_citations.py` (NEW)

**Features**:
- Parse markdown citations BEFORE conversion
- Check for common issues:
  - Amazon URLs instead of DOIs
  - YouTube links as citations
  - Missing years in citation text
  - "et al" without full author list
- Generate report: "Fix these 10 citations before converting"

**Goal**: Catch issues early, improve markdown quality.

#### Task 3.5: Automated Testing

**File**: `tests/test_citation_matching.py`

**Test cases**:
1. Fletcher book with Amazon URL (known failure case)
2. Niinimäki with DOI (should match)
3. arXiv papers with various URL formats (abs/html/pdf)
4. Regular hyperlinks (should be filtered)
5. "et al" citations (should expand)

**Use golden outputs**: Store expected BibTeX for each test case.

**Goal**: Prevent regressions, document expected behavior.

---

## Decision Log: Why This Plan Is Different

### Previous Attempts (What Didn't Work)

1. **Created new scripts** (`simple_local_converter.py`, `emergency_md_converter.py`)
   - Reinvented wheel
   - Got 3.4% match rate (7/207 citations)
   - Violated "reuse existing code" principle

2. **Shallow quick-fixes** (field name case sensitivity, patent type)
   - Fixed one bug, didn't solve systemic issue
   - Niinimäki still failing after "fix"
   - Fletcher still failing after "fix"

3. **Reactive debugging** (whac-a-mole)
   - Fixed bugs as they appeared
   - Didn't understand root causes
   - Same issues kept recurring

### This Plan (What's Different)

1. **Multi-layer analysis**: Identified 6 distinct failure layers, not 1 bug
2. **Leverage existing code**: Reuse `CitationMatcher`, `bibliography_sources.py`
3. **Phase-based approach**: Emergency fix (hours) → Short-term (week) → Long-term (month)
4. **User-centric**: Acknowledges recurring frustrations (Fletcher, Niinimäki), addresses them specifically
5. **Documentation-driven**: Built on existing docs (`bibliography-extraction-issues.md`, `bibliography-quality-analysis.md`)
6. **Success criteria from CLAUDE.md**: Zero (?) citations in PDF, not "conversion ran"

### Why Fletcher Keeps Failing

**NOT a code bug** - it's a **data quality issue**:
- Fletcher book exists in Zotero
- Zotero export missing ISBN field (should have 978-1138021013)
- Markdown has Amazon URL (no DOI exists for this book)
- CitationMatcher can extract ISBN from Amazon URL
- But BibTeX has nothing to match against

**Solution**: Either fix Zotero export OR manually add BibTeX entry for Fletcher.

**Why this wasn't obvious**: We kept looking at matching logic, not at export quality.

### Why So Many arXiv Papers Fail

**Hypothesis**: CitationMatcher indices not being built from BibTeX entries.

**Evidence**:
- CitationMatcher has sophisticated `extract_arxiv_id()` function
- Should trivially match `arxiv.org/abs/2509.25370`
- Yet 50+ arXiv papers unmatched in conversion attempt

**Root cause**: Likely Layer 1 bug (file format mismatch) preventing CitationMatcher from initializing.

**Verification needed**: Check if `self.arxiv_index` is empty during matching.

---

## Implementation Priority Matrix

| Layer | Issue | Impact | Effort | Priority | Phase |
|-------|-------|--------|--------|----------|-------|
| 1 | File format mismatch | BLOCKS conversion | LOW | **P0** | Emergency |
| 2 | CitationMatcher not used | 0% match rate | MEDIUM | **P0** | Emergency |
| 3 | Hyperlink filtering | False positives | LOW | P1 | Short-term |
| 4 | Zotero export quality | Fletcher, etc. | HIGH | P1 | Short-term |
| 5 | Auto-add failure | No recovery | MEDIUM | P1 | Short-term |
| 6 | Validation blind spots | Garbage passes | MEDIUM | P2 | Long-term |

**P0 (Emergency - TODAY)**: Blocks all progress, must fix immediately.
**P1 (Short-term - THIS WEEK)**: Recurring pain points, high user impact.
**P2 (Long-term - THIS MONTH)**: Quality improvements, robustness.

---

## Success Metrics

### Phase 1 (Emergency)

- [ ] Conversion runs without JSON parse error
- [ ] Match rate >90% (should be ~190/207 citations)
- [ ] PDF generates with <10 (?) citations
- [ ] references.bib has <5 "Unknown" entries
- [ ] User submits manuscript TODAY

### Phase 2 (Short-term)

- [ ] Fletcher book matches (manually if needed)
- [ ] Niinimäki et al. (2020) matches automatically (DOI-based)
- [ ] Zero false positives from regular hyperlinks
- [ ] Auto-add works OR explicitly disabled
- [ ] Documented Zotero export best practices

### Phase 3 (Long-term)

- [ ] Fuzzy matching implemented and tested
- [ ] Enhanced validator catches stub titles
- [ ] Automated tests prevent regressions
- [ ] Markdown pre-validator available
- [ ] Zero (?) citations in PDF for test corpus

---

## Key Files Reference

### Must Read
- `.claude/CLAUDE.md` - Guardrails and success criteria
- `docs/known-issues/bibliography-extraction-issues.md` - Documented recurring issues
- `docs/troubleshooting/bibliography-quality-analysis.md` - Seven hypotheses

### Code to Leverage (Don't Reinvent)
- `src/converters/md_to_latex/citation_matcher.py` - Production matching logic
- `src/converters/md_to_latex/bibliography_sources.py` - Modular sources (already done)
- `src/converters/md_to_latex/utils.py` - Identifier extraction utilities

### Code to Modify
- `scripts/deterministic_convert.py` - Rename parameter (Task 1.1)
- `src/converters/md_to_latex/converter.py` - Update constructor (Task 1.1)
- `src/converters/md_to_latex/citation_manager.py` - Verify CitationMatcher init (Task 1.2)
- `citation_extractor_unified.py` - Add hyperlink filtering (Task 2.1)

### Code to Create
- `docs/user-guides/zotero-export-guide.md` - Export best practices (Task 2.4)
- `src/converters/md_to_latex/entry_validator_enhanced.py` - Quality checks (Task 3.1)
- `scripts/validate_markdown_citations.py` - Pre-conversion validator (Task 3.4)
- `tests/test_citation_matching.py` - Automated tests (Task 3.5)

---

## Lessons Learned

### What Went Wrong

1. **Assumed single root cause**: Looked for "the bug" instead of systemic issues
2. **Didn't leverage documentation**: Fletcher was documented multiple times, kept re-explaining
3. **Reactive mode**: Fixed bugs as they appeared, didn't prevent recurrence
4. **Didn't verify CitationMatcher integration**: Assumed it worked, didn't check indices
5. **Trusted "conversion ran" as success**: Should have checked PDF for (?) citations

### What to Do Differently

1. **Check documentation first**: Before asking user to explain, search existing docs
2. **Multi-layer thinking**: When fix doesn't work, assume multiple failures
3. **Verify success per CLAUDE.md**: Zero (?) citations in PDF, not "no errors"
4. **Test with known cases**: Fletcher, Niinimäki should be in every test run
5. **Build on existing code**: Reuse CitationMatcher, don't write new matching logic

### User's Wisdom

> "People have been creating latex documents successfully for centuries before any AI, and now it somehow is problematic when you are being reactive ;)"

**Translation**: Stop overthinking. The tools exist. The code exists. Just wire them together properly.

---

## Next Immediate Actions

1. **Start Phase 1, Task 1.1**: Fix file format parameter mismatch (15 minutes)
2. **Task 1.2**: Verify CitationMatcher indices are built (10 minutes logging)
3. **Task 1.3**: Test conversion with BibTeX file (5 minutes to run)
4. **Task 1.4**: Manually handle any remaining mismatches (30 minutes max)
5. **Verify per CLAUDE.md**: Read PDF, count (?) citations, confirm zero

**Total estimated time**: 1-2 hours

**Expected outcome**: User has working PDF and can submit manuscript TODAY.

---

## Appendix A: Technical Debt Identified

1. **Fuzzy matching not implemented** (citation_matcher.py line 161-163)
2. **RDF loading not implemented** (bibliography_sources.py line 260-266)
3. **EntryValidator doesn't check stub titles** (mentioned in analysis)
4. **citation_extractor_unified.py doesn't filter hyperlinks** (mentioned in CLAUDE.md)
5. **No automated tests for matching logic** (prevents regression detection)

## Appendix B: Questions for User (After Emergency Fix)

1. Does your Zotero export include ISBN fields for books like Fletcher?
2. Would you prefer we require DOIs in markdown instead of Amazon URLs?
3. Should organizational URLs (European Commission, WBCSD) be filtered entirely?
4. What's your preferred workflow: manual Zotero curation OR auto-add missing citations?

## Appendix C: File Format Decision

**User asked**: "Do you preference some other format for Zotero export?"

**Answer based on code analysis**:

| Format | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Better BibTeX (.bib)** | Standard LaTeX format, preserves citation keys, widely supported | Need to parse and convert | ✅ **PREFERRED** |
| CSL JSON (.json) | Already in CSL format, no conversion | Not standard LaTeX, less common | ✅ Acceptable |
| RDF (.rdf) | Zotero native | Parser not implemented | ❌ Not supported yet |

**Current code supports**: Better BibTeX and CSL JSON.

**Best practice**: Export as Better BibTeX (.bib) from Zotero with Better BibTeX plugin enabled.
