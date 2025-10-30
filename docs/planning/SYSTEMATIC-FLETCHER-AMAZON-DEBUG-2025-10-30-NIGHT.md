# SYSTEMATIC DEBUGGING PLAN: Fletcher Amazon.de Title Issue
**Date**: 2025-10-30 Night Session
**Priority**: CRITICAL - Blocks manuscript submission TONIGHT
**Issue**: Fletcher (2016) shows "Amazon.de" instead of "Craft of Use: Post-Growth Fashion"

---

## HISTORICAL CONTEXT: Previous Failed Attempts to Fix This

**This is NOT the first time we've tried to fix citation quality issues.** This document is part of a multi-day debugging saga where Claude repeatedly claimed success without verification.

### Related Debugging Sessions (October 30, 2025)

1. **[honest-assessment-2025-10-30.md](./honest-assessment-2025-10-30.md)** - Self-reflection on pattern of failure
   - **Key finding**: "Never once read the actual PDF output to verify citations"
   - **Pattern identified**: Claiming "conversion successful" without checking for garbage citations
   - **What I promised**: "Never claim success without PDF verification"
   - **What actually happened**: Still failing to verify

2. **[comprehensive-citation-fix-analysis-2025-10-30.md](./comprehensive-citation-fix-analysis-2025-10-30.md)** - Analysis of temp/stub citations
   - **Issue**: System producing `zhangTemp2024`, stub titles like "Web page by X"
   - **6 days of work**: Validators, auto-add, Better BibTeX integration - all implemented
   - **Still broken**: Default CLI settings create dry-run entries, validators run too late

3. **[SYSTEMATIC-FIX-PLAN-2025-10-30-EVENING.md](./SYSTEMATIC-FIX-PLAN-2025-10-30-EVENING.md)** - Better BibTeX ban decision
   - **User decision**: "Better BibTeX should be banned altogether from this repo!"
   - **Why**: Too problematic, validation warnings flooding output (1000+ lines)
   - **Solution**: RDF-only emergency mode - NO web fetching, NO Better BibTeX
   - **My behavior**: "I acted like a junior engineer" - fixing symptoms, not causes

4. **[root-cause-analysis-comprehensive-2025-10-30.md](./root-cause-analysis-comprehensive-2025-10-30.md)** - Deep dive into citation/heading bugs

5. **[comprehensive-bibliography-fix-plan-2025-10-30.md](./comprehensive-bibliography-fix-plan-2025-10-30.md)** - Bibliography source architecture refactor

### Why This Matters

**User frustration**: "Fletcher we have been trying to fix for days, and you still always get it wrong while it is available on the local RDF"

**The pattern**:
1. User reports issue (e.g., Fletcher shows "Amazon.de")
2. Claude claims to fix it
3. Claude says "conversion successful" without checking PDF
4. User opens PDF - same issue still there
5. Repeat

**This time MUST be different**:
- ✅ Check .bbl file for garbage titles BEFORE claiming success
- ✅ Read actual PDF output to verify citations
- ✅ Test against ALL known failure modes (not just Fletcher)
- ✅ Run quality verification script and show results

---

## CRITICAL USER FEEDBACK

1. "never fetch anything now online, fetch all the citations from local RDF"
2. "Fletcher we have been trying to fix for days, and you still always get it wrong while it is available on the local RDF"
3. "improve then your matching logic for fuck sake"
4. "there should be even some flag that disables [online fetching] as we have the local RDF on disk, with maximum of 5 missing citations"
5. "if you find more [than 5 missing], there is some problem with your matching logic"

## VERIFIED FACTS

1. ✅ Fletcher book IS in RDF file with CORRECT title: "Craft of Use: Post-Growth Fashion"
2. ✅ RDF file location: `dpp-fashion-zotero.rdf`
3. ✅ Fletcher URL in markdown: `https://www.amazon.de/.../dp/1138021016`
4. ❌ references.bib has WRONG title: "Amazon.de"
5. ❌ .bbl file has WRONG title: "Amazon.de"
6. ❌ Logs show: "Cache entry for [Fletcher URL] has no key - invalidating cache"

## ROOT CAUSE HYPOTHESIS

**The Problem**: RDF parser loads Fletcher entry but does NOT generate/preserve citation key, causing:
1. RDF entry loaded with correct data
2. Citation key is missing or empty
3. Cache invalidation: "has no key - invalidating cache"
4. Entry discarded from cache
5. System falls back to web scraping
6. Web scraper extracts "Amazon.de" as title
7. Wrong data written to references.bib and .bbl

**This is NOT**:
- ❌ Bibliography style issue (earlier hypothesis was WRONG)
- ❌ LaTeX formatting issue
- ❌ Zotero data issue
- ❌ Missing data in RDF

**This IS**:
- ✅ Citation key generation/preservation issue in RDF parser
- ✅ URL matching issue in citation lookup
- ✅ Improper fallback to web scraping when RDF entry exists

---

## ALL POSSIBLE ROOT CAUSES (Systematic Analysis)

### Cause 1: RDF Parser Doesn't Generate Keys
**Location**: `src/converters/md_to_latex/bibliography_sources.py:_parse_rdf_item()`
**Hypothesis**: Parser extracts title, authors, URL but doesn't create citation key
**How to test**: Add logging in _parse_rdf_item to show keys generated
**Expected fix**: Call `_extract_citation_key_from_url()` for entries with URLs

### Cause 2: Citation Key Not Stored in CSL Entry
**Location**: `src/converters/md_to_latex/bibliography_sources.py:_parse_rdf_item()`
**Hypothesis**: Key is generated but not added to CSL entry dictionary
**How to test**: Check if CSL entry has 'id' or 'citation-key' field
**Expected fix**: Add `csl_entry['id'] = citation_key` before returning

### Cause 3: URL Normalization Mismatch
**Location**: `src/converters/md_to_latex/citation_manager.py:_normalize_url()`
**Hypothesis**: Fletcher URL in markdown normalized differently than in RDF
**Examples**:
- Markdown: `https://www.amazon.de/.../dp/1138021016`
- RDF: `https://www.amazon.de/-/en/Craft-Use-Post-Growth-Kate-Fletcher/dp/1138021016`
**How to test**: Log both normalized URLs side by side
**Expected fix**: Strip Amazon path variations before comparing

### Cause 4: Citation Lookup Uses Wrong Key
**Location**: `src/converters/md_to_latex/citation_manager.py:_lookup_entry_by_url()`
**Hypothesis**: Lookup function searches by wrong field (key vs URL)
**How to test**: Check what field is used for matching
**Expected fix**: Ensure lookup checks URL field, not just citation key

### Cause 5: Cache Structure Issue
**Location**: `src/converters/md_to_latex/bibliography_sources.py:get_bibliography()`
**Hypothesis**: Cache stores entries with URL as key, but lookup expects citation key
**How to test**: Print cache.keys() and see what keys exist
**Expected fix**: Support both URL-based and key-based lookup

### Cause 6: RDF Attachment vs Book Entry
**Location**: `src/converters/md_to_latex/bibliography_sources.py:_load_rdf()`
**Hypothesis**: RDF has BOTH `bib:Book` and `z:Attachment` for same URL, parser picks attachment
**Evidence from RDF**: Attachment has title "Amazon.com Link" (wrong)
**How to test**: Check if parser processes z:Attachment nodes
**Expected fix**: Skip z:Attachment nodes, only parse bib:Book, bib:Article, etc.

### Cause 7: Web Fetching Not Disabled
**Location**: `src/converters/md_to_latex/citation_manager.py`
**Hypothesis**: No flag to disable online fetching, always falls back to web
**User requirement**: "never fetch anything now online"
**How to test**: Check for --no-web-fetching flag or similar
**Expected fix**: Add flag to disable web fetching fallback

---

## INVESTIGATION PLAN (Step by Step)

### Phase 1: Examine RDF File (10 minutes)
**Goal**: Verify Fletcher entry format and identify any issues

**Steps**:
1. Search RDF for Fletcher Amazon URL
2. Check if multiple entries exist for same URL (Book vs Attachment)
3. Note exact XML structure of Fletcher entry
4. Check if entry has citation-key attribute

**Files to check**:
- `/home/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/dpp-fashion-zotero.rdf`

**What to look for**:
```xml
<!-- CORRECT FORMAT -->
<bib:Book rdf:about="[AMAZON_URL]">
    <dc:title>Craft of Use: Post-Growth Fashion</dc:title>
    <!-- Citation key might be here or needs to be generated -->
</bib:Book>

<!-- WRONG FORMAT (if this exists, it's the problem) -->
<z:Attachment>
    <dc:title>Amazon.com Link</dc:title>
    <dc:identifier>[AMAZON_URL]</dc:identifier>
</z:Attachment>
```

### Phase 2: Examine RDF Parser Code (15 minutes)
**Goal**: Understand how parser processes RDF and generates keys

**Files to check**:
1. `src/converters/md_to_latex/bibliography_sources.py:_load_rdf()` (lines 259-297)
   - Does it process z:Attachment nodes? (it shouldn't)
   - What node types does it process?

2. `src/converters/md_to_latex/bibliography_sources.py:_parse_rdf_item()` (lines 302-400)
   - Does it call `_extract_citation_key_from_url()`?
   - Does it add citation key to CSL entry?
   - What fields are extracted?

3. `src/converters/md_to_latex/bibliography_sources.py:_extract_citation_key_from_url()` (lines ~450-500)
   - What format does it generate for Amazon URLs?
   - Is it called at all?

**What to look for**:
- Missing citation key assignment
- Attachment node processing (should be skipped)
- URL extraction logic

### Phase 3: Examine Citation Matching Logic (15 minutes)
**Goal**: Understand how markdown citations are matched to RDF entries

**Files to check**:
1. `src/converters/md_to_latex/citation_manager.py:_lookup_entry_by_url()` (lines ~600-650)
   - How does it normalize URLs?
   - What field does it match against?
   - What happens if no match found?

2. `src/converters/md_to_latex/citation_manager.py:_normalize_url()` (lines ~550-600)
   - How does it handle Amazon URLs?
   - Does it strip path variations?

**What to look for**:
- URL normalization differences between markdown and RDF
- Fallback logic to web scraping
- Missing NO_WEB_FETCHING flag

### Phase 4: Add Debug Logging (20 minutes)
**Goal**: Instrument code to show exactly what's happening

**Add logging to**:
1. `bibliography_sources.py:_parse_rdf_item()`:
   ```python
   logger.debug(f"RDF: Parsed entry - Title: {title}, URL: {url}, Key: {citation_key}")
   ```

2. `bibliography_sources.py:get_bibliography()`:
   ```python
   logger.debug(f"RDF: Loaded {len(entries)} entries")
   logger.debug(f"RDF: Sample keys: {list(entries.keys())[:5]}")
   ```

3. `citation_manager.py:_lookup_entry_by_url()`:
   ```python
   logger.debug(f"LOOKUP: Searching for URL: {normalized_url}")
   logger.debug(f"LOOKUP: Available keys: {len(self.bibliography_cache)}")
   logger.debug(f"LOOKUP: Match found: {found}")
   ```

### Phase 5: Create Test Harness (30 minutes)
**Goal**: Verify .bbl output before claiming success

**Create**: `scripts/verify_bbl_quality.py`

**Features**:
1. Parse .bbl file
2. Extract all citations
3. Check for quality issues:
   - Domain names as titles ("Amazon.de", "Arxiv.org")
   - Missing titles (empty or "Unknown")
   - Stub titles ("Web page by X")
   - Temp keys ("Temp", "dryrun_")
4. Report specific entries with issues
5. Exit code 0 = success, 1 = issues found

**Usage**:
```bash
python scripts/verify_bbl_quality.py output.bbl
# Output:
# ✅ All 383 citations verified
# OR
# ❌ Found 2 issues:
#   - fletcher_craft_2016: Title is domain name "Amazon.de"
#   - wooldridge_2009: Title is domain name "Amazon.de"
```

### Phase 6: Run Test Conversion with Debug Logging (15 minutes)
**Goal**: Capture actual behavior with Fletcher citation

**Command**:
```bash
# Set debug logging
export LOG_LEVEL=DEBUG

# Run conversion
uv run python scripts/deterministic_convert.py \
  "/home/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/mcp-draft-refined-v4.md" \
  --rdf "/home/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/dpp-fashion-zotero.rdf" \
  --output-dir "/tmp/debug_output" \
  --allow-failures \
  2>&1 | tee /tmp/conversion_debug.log

# Search log for Fletcher
grep -i "fletcher\|amazon" /tmp/conversion_debug.log

# Check references.bib
grep -A5 "fletcher" /tmp/debug_output/references.bib

# Check .bbl file
grep "Fletcher" /tmp/debug_output/*.bbl
```

**What to look for in logs**:
- "RDF: Parsed entry - Title: Craft of Use... URL: amazon.de... Key: ?"
- "LOOKUP: Searching for URL: [Fletcher URL]"
- "LOOKUP: Match found: True/False"
- "Cache entry for [Fletcher URL] has no key - invalidating cache"

---

## FIX STRATEGY (Priority Order)

### FIX 1: Skip z:Attachment Nodes (If Applicable)
**IF**: RDF parser is processing z:Attachment nodes
**File**: `bibliography_sources.py:_load_rdf()`
**Change**:
```python
# Current (if this is the issue):
for item in root.findall(f"z:Attachment", namespaces):
    entry = self._parse_rdf_item(item, namespaces)  # WRONG

# Fixed:
# Just remove z:Attachment from list of types to process
# Only process: Book, Article, ArticleJournal, etc.
```

### FIX 2: Ensure Citation Key Generation
**IF**: Keys are not being generated for RDF entries
**File**: `bibliography_sources.py:_parse_rdf_item()`
**Change**:
```python
# After extracting URL, before returning CSL entry:
if url:
    citation_key = self._extract_citation_key_from_url(url)
    if citation_key:
        csl_entry['id'] = citation_key
        logger.debug(f"RDF: Generated key '{citation_key}' for {title}")
```

### FIX 3: Improve URL Normalization for Amazon
**IF**: Amazon URLs are normalized differently
**File**: `citation_manager.py:_normalize_url()`
**Change**:
```python
def _normalize_url(self, url: str) -> str:
    # Existing normalization...

    # Amazon-specific normalization
    if 'amazon.' in url:
        # Extract just the ASIN/ISBN: dp/XXXXXXXXXX
        match = url.find('/dp/')
        if match != -1:
            asin = url[match+4:match+14]  # Extract 10-char ASIN
            # Normalize to standard format
            return f"https://www.amazon.com/dp/{asin}"

    return normalized_url
```

### FIX 4: Add NO_WEB_FETCHING Flag
**User requirement**: "never fetch anything now online"
**File**: `citation_manager.py` + `cli_md_to_latex.py`

**Add CLI flag**:
```python
# cli_md_to_latex.py
@click.option(
    "--no-web-fetching",
    is_flag=True,
    default=False,
    help="Disable online fetching - use only local RDF data",
)
```

**Use in citation_manager**:
```python
def _handle_missing_citation(self, citation, url):
    if self.no_web_fetching:
        raise RuntimeError(
            f"Citation not found in RDF and web fetching is DISABLED: {url}\n"
            f"Add this entry to Zotero and re-export RDF."
        )

    # Otherwise proceed with web fetching...
```

### FIX 5: Add Citation Key Validation
**Prevent entries without keys from entering cache**
**File**: `bibliography_sources.py:get_bibliography()`
```python
for entry in csl_entries:
    # VALIDATE: Entry must have citation key
    if 'id' not in entry or not entry['id']:
        logger.warning(f"RDF entry missing citation key: {entry.get('title', 'Unknown')}")
        continue  # Skip entries without keys

    self.cache[entry['id']] = entry
```

---

## SUCCESS CRITERIA (Zero Tolerance)

### Test 1: Fletcher Title is Correct ✅
```bash
grep "fletcher" /tmp/output/references.bib
# Expected: title = "Craft of Use: Post-Growth Fashion"
# NOT: title = "Amazon.de"
```

### Test 2: No Domain Names as Titles ✅
```bash
python scripts/verify_bbl_quality.py /tmp/output/*.bbl
# Expected: ✅ All 383 citations verified
# No entries with ".com", ".de", ".org" as titles
```

### Test 3: Maximum 5 Missing Citations ✅
```bash
# Run conversion
# Should NOT fetch more than 5 citations from web
grep "Fetching:" /tmp/conversion.log | wc -l
# Expected: <= 5
```

### Test 4: No Cache Invalidation Messages ✅
```bash
grep "has no key - invalidating cache" /tmp/conversion.log
# Expected: ZERO matches
```

### Test 5: PDF Shows Correct Title ✅
```bash
# Read the PDF and verify Fletcher citation
pdftotext /tmp/output/*.pdf - | grep -A1 "Fletcher"
# Expected: "Fletcher K (2016) Craft of Use: Post-Growth Fashion"
# NOT: "Fletcher K (2016) Amazon.de"
```

---

## WHAT NOT TO DO (Lessons Learned)

1. ❌ **Don't claim success without running verify_bbl_quality.py**
2. ❌ **Don't assume the first fix will work - test each hypothesis**
3. ❌ **Don't skip the debug logging phase - we need visibility**
4. ❌ **Don't reinvent matching logic - fix the existing code**
5. ❌ **Don't add more web fetching - user wants LESS, not more**
6. ❌ **Don't modify multiple files at once - fix one thing at a time**
7. ❌ **Don't commit without testing - run full conversion first**

---

## EXECUTION TIMELINE

| Phase | Time | Deliverable |
|-------|------|-------------|
| 1. RDF Examination | 10 min | Fletcher entry format documented |
| 2. Code Review | 15 min | Root cause identified |
| 3. Matching Logic Review | 15 min | URL normalization issues found |
| 4. Debug Logging | 20 min | Instrumented code ready |
| 5. Test Harness | 30 min | verify_bbl_quality.py working |
| 6. Test Conversion | 15 min | Debug logs captured |
| 7. Implement Fix | 30 min | Code fixed |
| 8. Verify Fix | 15 min | All tests pass |
| **TOTAL** | **2.5 hours** | Working conversion with correct Fletcher title |

---

## OPEN QUESTIONS FOR USER (If Needed)

1. Is there a reason the markdown uses `.de` URL while RDF might have `.com` URL?
2. Should we strip ALL Amazon path variations and match by ASIN only?
3. What's the preferred behavior when citation truly not in RDF? Error or warning?

---

## ALL KNOWN FAILURE MODES (User-Reported from Latest PDF)

**Context**: These are REAL examples from user's actual PDF output. Each represents a systematic failure that MUST be tested and fixed.

### Failure Mode 1: Domain Names as Titles
**Examples from PDF**:
```
Fletcher K (2016) Amazon.de
Wooldridge (2009) Amazon.de
```

**Root cause**: Web scraper extracts domain instead of actual book title
**Why this happens**:
1. Citation in markdown has Amazon URL
2. RDF has correct entry but URL doesn't match (normalization issue)
3. System falls back to web scraping
4. Amazon pages don't have clear title metadata
5. Scraper extracts "Amazon.de" from page
6. Gets written to references.bib and .bbl

**Test**: Any .bbl entry with title matching pattern `*.com|*.de|*.org` should FAIL
**Fix needed**: Improve URL normalization for Amazon, eBay, other shopping sites

### Failure Mode 2: Missing Hyperlinks in Citations
**Examples from PDF**:
```
Beigi M, Wang S, Shen Y, Lin Z, Kulkarni A, He J, Chen F, Jin M,
Cho JH, Zhou D, Lu CT, Huang L (2024) A note on abelian envelopes. arXiv
```

**What's wrong**: No clickable link to arXiv paper (should be hyperlinked)
**Root cause**: Bibliography style doesn't include URL field or hyperref not configured
**Test**: PDF should have clickable URLs for all web sources
**Fix needed**: Update LaTeX template or bibliography style to include hyperlinks

### Failure Mode 3: Missing arXiv Identifiers
**Examples from PDF**:
```
Chen, et al. (2025a) A note on the cross matrices. arXiv
Ibrahim, et al. (2025a) Revisiting ostrowski's inequality. arXiv
```

**What's wrong**: Says "arXiv" but doesn't show the arXiv ID (e.g., arXiv:2501.12345)
**Root cause**: Bibliography style doesn't format arXiv IDs properly
**Test**: All arXiv citations should show identifier in format "arXiv:YYMM.NNNNN"
**Fix needed**: Customize bibliography style or use eprint field

### Failure Mode 4: Hallucinated Titles (Potentially)
**Examples from PDF**:
```
Beigi M, Wang S, ... (2024) A note on abelian envelopes. arXiv
Manca N, Tarsi G, ... (2023) Strain, young's modulus, and structural
transition of eutio3 thin films probed by micro-mechanical methods. arXiv
```

**Question**: Are these real titles or hallucinated?
**Root cause**: If hallucinated, likely from:
1. CrossRef returning wrong metadata
2. arXiv API returning incomplete data
3. Title extraction parsing issues

**Test**: Sample 5 arXiv citations, verify titles match actual papers
**Fix needed**: If systematic, improve arXiv metadata fetching

### Failure Mode 5: Incorrect Organization Name Parsing
**Examples from PDF**:
```
Commission E (2023) Regulation - 2023/1542 - en - eur-lex
    ↑ Should be: European Commission

Foundation EM (2024) The fashion remodel | scaling circular fashion business models
    ↑ Should be: Ellen MacArthur Foundation

Revolution F (2024) What fuels fashion? 2024 : Fashion revolution
    ↑ Should be: Fashion Revolution
```

**Root cause**: BibTeX author field parsing treats organization names as "First Last"
- Input: `{European Commission}` (single braces)
- BibTeX parsing: "European" = first name, "Commission" = last name
- LaTeX output: "Commission E" (last name + initial)

**Fix**: Organization names MUST use double braces: `{{European Commission}}`
**Test**: Check .bib file for all organization authors, ensure double-braced
**Where to fix**: Either in Zotero export or in our RDF parser

### Failure Mode 6: Duplicate Entries with Different Years
**Examples from PDF**:
```
Revolution F (2023) What fuels fashion? 2025 : Fashion revolution
Revolution F (2024) What fuels fashion? 2024 : Fashion revolution
```

**Root cause**: Same report, accessed on different dates, treated as separate publications
**Why this happens**:
1. Markdown has two citations to same URL
2. Zotero has two entries (different access dates)
3. No deduplication logic
4. Both appear in bibliography

**Test**: Check for duplicate titles with same author, flag for review
**Fix needed**: Deduplication logic in citation extraction or Zotero cleanup

### Failure Mode 7: Stub Titles
**Examples from PDF**:
```
Axios (2025) Web page by axios
Arner, et al. (2016) Web page by arner et al
Bloomberg News (2018) Web article by bloomberg
Borkey B (2024) Web page by brown & borkey
CIRPASS (2024b) Web page by cirpass
```

**Root cause**: Translation server or web scraper generates placeholder titles
**Why this happens**:
1. URL has no clear title metadata
2. System generates stub: "Web page by {author}"
3. EntryValidator has "Web page by" in truncation markers
4. But validation runs AFTER entry created (too late)

**Test**: .bbl file should have ZERO entries matching "Web page by|Web article by"
**Fix needed**: Block these at extraction time, not validation time

### Failure Mode 8: Missing Titles / No Info
**Examples from PDF**:
```
Arab, et al. (2025)  [nothing else]
Google (2024) Web page by google
Newman (2021) Web page by newman
```

**Root cause**: Web page with no extractable metadata
**Why this happens**: Some sites (Google, OECD, etc.) don't provide citation metadata
**Test**: .bbl should have no entries with empty titles or single-word domain titles
**Fix needed**:
- Option A: Require manual Zotero entry before conversion
- Option B: Generate footnote instead of bibliography entry
- Option C: Use wayback machine snapshot for better metadata

### Failure Mode 9: Generic Titles from URL Scrapers
**Examples from PDF**:
```
GS1 (2024) Epcis & cbv | gs1
ITC (2024a) Standardsmap
Parliament E (2024) Web page by european parliament
```

**Root cause**: Web scraper extracts page title literally (includes site chrome)
**Why this happens**: `<title>` tag includes site name, separators, etc.
**Test**: Check for titles with pipe symbols "|", site names in title
**Fix needed**: Title cleaning heuristics (remove site name suffixes, etc.)

---

## COMPREHENSIVE TEST PLAN REQUIREMENTS

Based on the above failure modes, any quality verification MUST check:

1. ✅ **No domain-as-title**: `.bbl` has no titles like "Amazon.de", "Arxiv.org"
2. ✅ **No stub titles**: `.bbl` has no "Web page by" or "Web article by"
3. ✅ **No missing titles**: All entries have non-empty title fields
4. ✅ **No temp keys**: `.bbl` has no keys containing "Temp", "dryrun_", "Unknown"
5. ✅ **Organization names correct**: No "Commission E", "Foundation EM", etc.
6. ✅ **arXiv IDs present**: All arXiv citations show "arXiv:YYMM.NNNNN" format
7. ✅ **Hyperlinks working**: All web citations have clickable URLs in PDF
8. ✅ **No duplicates**: No two entries with same title/author
9. ✅ **Title quality**: No generic titles like "Standardsmap", titles with "|"

**CRITICAL**: Test script MUST parse .bbl file (not just .bib) because that's what actually appears in PDF.

---

## NEXT IMMEDIATE ACTION

**START**: Phase 1 - Examine RDF file for Fletcher entry format (10 minutes)

**Command**:
```bash
# Search for Fletcher in RDF
grep -A20 -B2 "Fletcher\|1138021016" dpp-fashion-zotero.rdf

# Look for Attachment nodes
grep -A10 "z:Attachment" dpp-fashion-zotero.rdf | grep -A10 "amazon"
```

---

**CRITICAL REMINDER**: User needs this working TONIGHT for manuscript submission. No hallucinated verification. No claiming success without running verify_bbl_quality.py and checking the actual .bbl output.
