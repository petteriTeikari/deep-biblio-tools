# Comprehensive Testing Plan for MCP-Draft-Refined-v5
**Date**: 2025-10-31
**Test File**: `mcp-draft-refined-v5.md` (249KB, last updated Oct 31 09:28)
**RDF File**: `dpp-fashion-zotero.rdf` (2.9MB, last updated Oct 30 19:56)
**Context**: Multi-session quality improvement and emergency mode implementation

---

## Executive Summary

This testing plan addresses **FIVE QUALITY DIMENSIONS** that have been iteratively improved over multiple sessions:

1. **Emergency Mode Zero-Fetch** (just implemented) - No network calls
2. **RDF Parser Quality** (fixed Oct 30-31) - Parse all 664 entries
3. **Citation Matching Quality** (fixed Oct 30-31) - Multi-strategy matching working
4. **Markdown Input Quality** (partially fixed Oct 31) - Clean up broken URLs, classify citations
5. **Output Quality Verification** (MANDATORY) - Zero (?) citations in PDF

This is **NOT** just about "hyperlink matching" - it's about verifying the entire conversion pipeline produces submission-ready output.

---

## Historical Context (What We've Fixed)

### Session 1: Oct 26, 2025 - Initial Quality Analysis
**Found**:
- 52 author name mismatches
- 10 invalid arXiv citations
- 7 broken Google A2A URLs

**Status**: ❌ Fixes were NEVER applied to markdown source (reports created but not executed)

### Session 2: Oct 30, 2025 Night - Core Technical Fixes
**Fixed**:
1. ✅ CitationMatcher overwritten to None (citation_manager.py:334)
2. ✅ RDF parser missing item types (BookSection, Recording, Patent)
3. ✅ Now parses 664/665 entries (was only 311/665)

**Commits**: 9bcb3e0, 9d2c059

### Session 3: Oct 31, 2025 Morning - Markdown URL Fixes
**Fixed automatically**:
- ✅ Google A2A URLs (6 occurrences) - updated to correct endpoint
- ✅ CIRPASS URLs (2 occurrences) - updated to working URLs
- ✅ Agrawal DOI typo (1 occurrence) - corrected DOI

**Output**: mcp-draft-refined-v4-1.md (intermediate version)

**Status**: Some fixes applied to v4-1, but user moved to v5

### Session 4: Oct 31, 2025 Afternoon - Emergency Mode Implementation
**Implemented**:
- ✅ emergency_mode flag threading (CitationManager → Converter → deterministic_convert.py)
- ✅ Skip fetch_citation_metadata() when emergency_mode=True
- ✅ Startup/completion logging
- ✅ Updated CLAUDE.md with zero-fetch guarantee

**Expected**: 22x performance improvement (11 min → <30 sec)

**Commit**: 6ce52ef

---

## The Five Quality Dimensions

### Dimension 1: Emergency Mode Zero-Fetch ✅ IMPLEMENTED

**Requirement**: ZERO network calls during conversion

**What was fixed**:
```python
# citation_manager.py:1792-1793
if not self.emergency_mode:
    self.fetch_citation_metadata(citation)
```

**Expected behavior**:
- ✅ Log shows: "🚨 Emergency Mode active — skipping all network metadata fetching."
- ✅ Log shows: "✅ Emergency mode complete: Used X RDF entries, no metadata fetched."
- ❌ Log does NOT show: "Fetching metadata from CrossRef"
- ❌ Log does NOT show: "Fetching metadata from arXiv"

**Performance**:
- Before: ~11 minutes (133 citations × 5 sec timeout each)
- After: <30 seconds (zero network calls)

**Verification**:
```bash
# Run conversion and grep logs
grep "Fetching metadata" conversion.log  # Should return ZERO results
grep "CrossRef" conversion.log           # Should return ZERO results
grep "arXiv" conversion.log              # Should return ZERO results (except in URLs)
```

---

### Dimension 2: RDF Parser Quality ✅ FIXED

**Requirement**: Parse ALL bibliographic entries from Zotero RDF

**What was fixed**:
1. Added missing item types (BookSection, Recording, Patent)
2. Fixed CitationMatcher initialization (was overwritten to None)

**Expected behavior**:
- ✅ Loaded 664/665 entries from RDF (user said 665 in Zotero)
- ✅ DOI index: ~152 entries
- ✅ ISBN index: Working (Amazon book URLs)
- ✅ arXiv index: ~3-5 entries
- ✅ URL index: 664 entries

**Verification**:
```bash
# Check logs for RDF loading
grep "Loaded.*entries from RDF" conversion.log
# Should show: "Loaded 664 entries from RDF: ..."
```

---

### Dimension 3: Citation Matching Quality ✅ FIXED

**Requirement**: Multi-strategy matching (DOI → ISBN → arXiv → URL)

**What was fixed**:
1. CitationMatcher no longer overwritten to None
2. All matching strategies now active

**Expected behavior**:
- ✅ DOI citations match via DOI index
- ✅ Amazon book citations match via ISBN extraction
- ✅ arXiv citations match via arXiv ID normalization
- ✅ Generic URLs match via URL normalization

**Known limitation**: ~50-150 citations NOT in Zotero yet (new 2024-2025 papers)
- These should generate temp keys but NOT appear in references.bib
- Should show as (?) in PDF

**Verification**:
```bash
# Count failedAutoAdd in references.bib (should be ZERO due to filtering)
grep "failedAutoAdd" output/references.bib | wc -l
# Should return: 0
```

---

### Dimension 4: Markdown Input Quality ⚠️ PARTIALLY FIXED

**Requirement**: Clean, accurate citations in markdown source

**What we know from previous analysis**:

#### 4.1 Broken URLs (PARTIALLY FIXED)
From CITATION-VERIFICATION-REPORT-2025-10-31.md:
- 163 broken/inaccessible URLs found in v4
- Many are HTTP 403 (paywalled but valid): DOIs, Bloomberg, etc.
- Some are real 404s that need fixing

**Fixed so far**:
- ✅ Google A2A URLs (6→0)
- ✅ CIRPASS URLs (2→0)
- ✅ Agrawal DOI (1→0)

**Still broken** (from v4 analysis - need to verify in v5):
- ⚠️ HTTP 403s: DOI.org, Bloomberg, Emerald, Taylor & Francis (paywalled but valid)
- ⚠️ HTTP 404s: Old URLs that moved/removed
- ⚠️ Timeouts: asiagarmenthub.net, bangladeshworkersafety.org

#### 4.2 Non-Academic Citations (NOT ADDRESSED)
From COMPREHENSIVE-QUALITY-ANALYSIS-2025-10-31.md:
~50-100 citations that should be **footnotes**, not bibliography entries:

**Organization homepages**:
- wbcsd.org
- commission.europa.eu
- standardsmap.org

**Blog posts**:
- anthropic.com/engineering/*
- developers.googleblog.com
- developer.okta.com/blog

**News articles**:
- bbc.com/news
- bloomberg.com/news
- fashionunited.com

**Videos**:
- youtube.com/watch?v=*

**Problem**: Markdown uses `[Author, Year](URL)` for EVERYTHING
**Solution needed**: Convert non-academic citations to footnotes

#### 4.3 Missing Zotero Entries (NOT ADDRESSED)
~100-150 **legitimate academic papers** not in Zotero yet:
- 60+ arXiv preprints from 2024-2025
- Recent conference papers
- New journal articles

**Expected behavior**:
- These should show as (?) in PDF
- User needs list to add manually to Zotero
- Then re-run conversion to eliminate (?)

#### 4.4 Author Name Mismatches (NOT VERIFIED)
From Oct 26 analysis: 52 mismatches found

**Status**: Unknown if still present in v5
**Needs**: Manual verification

---

### Dimension 5: Output Quality Verification ⚠️ MANDATORY

**Requirement**: Submission-ready PDF with ZERO (?) citations

**Critical checks** (from CLAUDE.md):
1. ✅ PDF generates without LaTeX errors
2. ✅ PDF has ZERO (?) citations
3. ✅ PDF has ZERO (Unknown) or (Anonymous) citations
4. ✅ All citations show proper author names and years
5. ✅ references.bib has ZERO "Unknown" or "Anonymous" entries
6. ✅ references.bib has ZERO failedAutoAdd entries
7. ✅ LaTeX log has ZERO compilation errors
8. ✅ BibTeX log has ZERO fatal errors (warnings OK)

**Files to check**:
```bash
output/references.bib          # Bibliography database
output/mcp-draft-refined-v5.bbl # Compiled bibliography
output/mcp-draft-refined-v5.tex # LaTeX source
output/mcp-draft-refined-v5.pdf # Final PDF
output/mcp-draft-refined-v5.log # LaTeX compilation log
```

**Verification commands**:
```bash
# Check for failedAutoAdd in .bib
grep -c "failedAutoAdd" output/references.bib
# Expected: 0

# Check for Unknown/Anonymous in .bbl
grep -c "Unknown\|Anonymous" output/mcp-draft-refined-v5.bbl
# Expected: 0

# Check for (?) in PDF (requires PDF text extraction)
pdftotext output/mcp-draft-refined-v5.pdf - | grep -c "(?"
# Expected: 0 (or small number with explanation)

# Count total bibliography entries
grep -c "@" output/references.bib
# Expected: ~250-350 (matched from RDF)
```

---

## Testing Workflow

### Pre-Test Setup

```bash
cd /home/petteri/Dropbox/github-personal/deep-biblio-tools

# Ensure we're on the correct branch with latest code
git status
git log -1 --oneline
# Should show: 6ce52ef feat: Implement emergency mode zero-fetch guarantee

# Define paths
MARKDOWN="/home/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/mcp-draft-refined-v5.md"
RDF="/home/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/dpp-fashion-zotero.rdf"
OUTPUT="/home/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/output"

# Verify input files exist
ls -lh "$MARKDOWN"
ls -lh "$RDF"
```

### Test 1: Emergency Mode Zero-Fetch

**Purpose**: Verify no network calls during conversion

```bash
# Run conversion with time tracking
time uv run python scripts/deterministic_convert.py \
  "$MARKDOWN" \
  --rdf "$RDF" \
  --output-dir "$OUTPUT" \
  --allow-failures \
  2>&1 | tee conversion.log

# Verification checks
echo "=== EMERGENCY MODE VERIFICATION ==="

# Check for emergency mode activation
grep "Emergency Mode active" conversion.log
# Expected: "🚨 Emergency Mode active — skipping all network metadata fetching."

# Check for fetching messages (should be ZERO)
echo "Fetching metadata count:"
grep -c "Fetching metadata" conversion.log || echo "0 ✅"

echo "CrossRef count:"
grep -c "CrossRef" conversion.log || echo "0 ✅"

echo "arXiv API calls:"
grep -c "Fetching.*from arXiv" conversion.log || echo "0 ✅"

# Check for completion message
grep "Emergency mode complete" conversion.log
# Expected: "✅ Emergency mode complete: Used X RDF entries, no metadata fetched."

echo "=== PERFORMANCE CHECK ==="
# Time should be < 30 seconds (check terminal output from 'time' command)
```

**Expected results**:
- ✅ Conversion completes in <30 seconds
- ✅ Log shows emergency mode activation
- ✅ Log shows emergency mode completion
- ✅ ZERO "Fetching metadata" messages
- ✅ ZERO network-related errors

---

### Test 2: RDF Parser Quality

**Purpose**: Verify all RDF entries loaded

```bash
echo "=== RDF PARSER VERIFICATION ==="

# Check RDF loading count
grep "Loaded.*entries from RDF" conversion.log

# Expected: "Loaded 664 entries from RDF: ..."
# User said 665 in Zotero, but parser might exclude 1 duplicate or invalid entry

# Check index statistics (if logged)
grep "DOI index" conversion.log
grep "ISBN index" conversion.log
grep "arXiv index" conversion.log
grep "URL index" conversion.log
```

**Expected results**:
- ✅ Loaded 664/665 entries (tolerance: ±5)
- ✅ DOI index: ~150+ entries
- ✅ ISBN index: >0 entries
- ✅ arXiv index: >0 entries
- ✅ URL index: 664 entries

---

### Test 3: Citation Matching Quality

**Purpose**: Verify multi-strategy matching working

```bash
echo "=== CITATION MATCHING VERIFICATION ==="

# Check matching statistics
grep "Matched.*citations" conversion.log
grep "Missing.*citations" conversion.log

# Expected patterns:
# "Matched: 250-350 citations" (from RDF)
# "Missing: 50-150 citations (will appear as (?) in PDF)"

# Verify failedAutoAdd filtering
echo "failedAutoAdd count in references.bib:"
grep -c "failedAutoAdd" "$OUTPUT/references.bib" || echo "0 ✅"

# Count actual bibliography entries
echo "Total entries in references.bib:"
grep -c "^@" "$OUTPUT/references.bib"
```

**Expected results**:
- ✅ 250-350 citations matched from RDF
- ✅ 50-150 citations missing (not in Zotero yet)
- ✅ ZERO failedAutoAdd entries in references.bib
- ✅ Bibliography count matches "matched" count

---

### Test 4: Markdown Input Quality

**Purpose**: Check for known issues in markdown source

```bash
echo "=== MARKDOWN INPUT QUALITY CHECK ==="

# Check if we're testing v5 (current) or v4-1 (intermediate)
basename "$MARKDOWN"

# Run URL validation (if tool exists)
uv run python scripts/verify_citations.py "$MARKDOWN" > url-check-v5.txt 2>&1

# Analyze results
echo "Broken URLs found:"
grep -c "HTTP 404\|HTTP 403\|Timeout\|Connection failed" url-check-v5.txt || echo "0"

echo "Total citations:"
grep "Total citations:" url-check-v5.txt

# Manual review needed for:
# 1. HTTP 403 (paywalled but valid DOIs)
# 2. Real 404s (need fixing)
# 3. Non-academic citations (should be footnotes)
```

**Expected results**:
- ⚠️ Some HTTP 403 (paywalled - acceptable)
- ⚠️ Some HTTP 404 (real issues - need fixing)
- ⚠️ Classification needed: academic vs non-academic

**Action items** (if issues found):
1. Generate list of broken URLs needing fixes
2. Generate list of non-academic citations → convert to footnotes
3. Generate list of missing academic papers → add to Zotero

---

### Test 5: Output Quality Verification (MANDATORY)

**Purpose**: Verify submission-ready output

```bash
echo "=== OUTPUT QUALITY VERIFICATION ==="

# Check compilation success
if [ -f "$OUTPUT/mcp-draft-refined-v5.pdf" ]; then
    echo "✅ PDF generated successfully"
    ls -lh "$OUTPUT/mcp-draft-refined-v5.pdf"
else
    echo "❌ PDF generation FAILED"
    exit 1
fi

# Check references.bib quality
echo "--- references.bib checks ---"

echo "failedAutoAdd entries:"
grep -c "failedAutoAdd" "$OUTPUT/references.bib" || echo "0 ✅"

echo "Unknown authors:"
grep -c "author.*Unknown" "$OUTPUT/references.bib" || echo "0 ✅"

echo "Anonymous authors:"
grep -c "author.*Anonymous" "$OUTPUT/references.bib" || echo "0 ✅"

echo "Total bibliography entries:"
grep -c "^@" "$OUTPUT/references.bib"

# Check .bbl file quality (if exists)
if [ -f "$OUTPUT/mcp-draft-refined-v5.bbl" ]; then
    echo "--- .bbl file checks ---"

    echo "Unknown authors in .bbl:"
    grep -c "Unknown" "$OUTPUT/mcp-draft-refined-v5.bbl" || echo "0 ✅"

    echo "Anonymous authors in .bbl:"
    grep -c "Anonymous" "$OUTPUT/mcp-draft-refined-v5.bbl" || echo "0 ✅"

    echo "Total .bbl entries:"
    grep -c "\\\\bibitem" "$OUTPUT/mcp-draft-refined-v5.bbl"
fi

# Check LaTeX compilation log
echo "--- LaTeX log checks ---"

if [ -f "$OUTPUT/mcp-draft-refined-v5.log" ]; then
    echo "LaTeX errors:"
    grep -c "^!" "$OUTPUT/mcp-draft-refined-v5.log" || echo "0 ✅"

    echo "Undefined citations:"
    grep -c "Citation.*undefined" "$OUTPUT/mcp-draft-refined-v5.log" || echo "0 ✅"
fi

# PDF text extraction and (?) check
echo "--- PDF content checks ---"

if command -v pdftotext &> /dev/null; then
    echo "(?) citations in PDF:"
    pdftotext "$OUTPUT/mcp-draft-refined-v5.pdf" - | grep -c "(?" || echo "0 ✅"

    echo "Unknown citations in PDF:"
    pdftotext "$OUTPUT/mcp-draft-refined-v5.pdf" - | grep -c "(Unknown)" || echo "0 ✅"
else
    echo "⚠️ pdftotext not installed - manual PDF review required"
fi
```

**Expected results**:
- ✅ PDF generated successfully
- ✅ ZERO failedAutoAdd in references.bib
- ✅ ZERO Unknown/Anonymous authors
- ✅ ZERO LaTeX compilation errors
- ✅ ZERO (?) citations in PDF (or small number with explanation)
- ✅ Bibliography count ~250-350 entries

**If ANY check fails**:
- ❌ DO NOT claim success
- ❌ DO NOT submit for publication
- ✅ Document which checks failed
- ✅ Root cause analysis
- ✅ Fix and re-test

---

## Success Criteria (All Must Pass)

### Critical Requirements ✅
1. ✅ Conversion completes in <30 seconds
2. ✅ ZERO "Fetching metadata" messages in log
3. ✅ ZERO failedAutoAdd entries in references.bib
4. ✅ ZERO Unknown/Anonymous authors in bibliography
5. ✅ ZERO LaTeX compilation errors
6. ✅ PDF generates successfully

### Quality Requirements ⚠️
7. ⚠️ ZERO (?) citations in PDF (or documented exceptions)
8. ⚠️ All DOI links accessible (excluding paywalled)
9. ⚠️ Non-academic citations converted to footnotes
10. ⚠️ Author names match source papers

### Documentation Requirements 📝
11. 📝 List of missing papers to add to Zotero
12. 📝 List of non-academic citations to convert
13. 📝 List of broken URLs needing fixes
14. 📝 Performance metrics (time, entry counts)

---

## Known Acceptable Issues

### HTTP 403 on DOIs ✅
**Issue**: Many DOI links return HTTP 403
**Reason**: Publisher paywalls (e.g., Emerald, Taylor & Francis)
**Acceptable**: YES - DOIs are valid, just paywalled
**Action**: No fix needed

### Paywalled News Articles ✅
**Issue**: Bloomberg, BBC articles may be paywalled
**Reason**: Subscription required
**Acceptable**: YES - URLs are valid
**Action**: No fix needed

### Missing Recent Papers ⚠️
**Issue**: 50-150 citations not in Zotero (2024-2025 papers)
**Reason**: User hasn't added them yet
**Acceptable**: YES if listed for manual addition
**Action**: Generate list → user adds to Zotero → re-run conversion

---

## Post-Test Actions

### If All Critical Tests Pass ✅
1. Generate missing papers list
2. Generate non-academic citations list
3. Generate broken URLs list
4. Provide to user for manual review
5. User adds missing papers to Zotero
6. Re-run conversion
7. Verify ZERO (?) citations in final PDF

### If Any Critical Test Fails ❌
1. Document which test(s) failed
2. Capture relevant log excerpts
3. Root cause analysis
4. Create fix plan
5. Implement fix
6. Re-run ALL tests
7. Do NOT claim success until ALL pass

---

## Difference from Previous Testing

### What's New in This Plan:
1. **Comprehensive** - Tests all 5 quality dimensions, not just matching
2. **Evidence-based** - Based on actual issues found across multiple sessions
3. **Automated** - Provides bash commands for verification
4. **Clear criteria** - Defines what "success" means (not just "compiled")
5. **Honest** - Acknowledges known issues and acceptable failures

### What Was Wrong Before:
1. ❌ Claimed success based on "compilation succeeded"
2. ❌ Never checked PDF content for (?)
3. ❌ Never verified emergency mode actually worked
4. ❌ Never counted bibliography entries
5. ❌ Never classified citation types (academic vs web)

---

## Timeline

**Total estimated time**: 30-45 minutes

1. Pre-test setup: 5 min
2. Test 1 (Emergency mode): 5 min
3. Test 2 (RDF parser): 2 min
4. Test 3 (Citation matching): 3 min
5. Test 4 (Markdown quality): 10 min
6. Test 5 (Output verification): 10 min
7. Analysis and reporting: 10 min

---

## Next Steps

After user approval of this plan:
1. Execute tests in sequence
2. Document results for each test
3. Generate actionable lists (missing papers, broken URLs, etc.)
4. Provide clear pass/fail status
5. If all critical tests pass → provide lists for user action
6. If any critical test fails → root cause analysis and fix

**Ready to begin testing whenever you are!**
