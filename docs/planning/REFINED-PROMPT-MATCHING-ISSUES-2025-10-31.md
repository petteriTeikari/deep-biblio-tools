# Refined Comprehensive Prompt: Bibliography Matching System Overhaul

**Date**: 2025-10-31
**Context**: Critical matching failure - RDF has 1,751 entries but converter reports hundreds missing
**Root Cause Hypothesis**: Matching logic bugs, NOT missing data

---

## Executive Summary

This is a **comprehensive, systematic overhaul** of the bibliography matching system to fix recurring matching failures that have persisted across multiple debugging sessions. The approach emphasizes:

1. **Scientific Rigour**: Hypothesis-driven development with comprehensive testing
2. **Deterministic Behavior**: Following CLAUDE.md principles for reproducible results
3. **Evidence-Based Solutions**: Fix proven bugs, not speculative issues
4. **No Rush to Implementation**: Thorough analysis before code changes

---

## Problem Statement

### Current State (Verified)
- **RDF Database**: 1,751 entries (very complete, local Zotero export)
- **Converter Reports**: HUNDREDS of citations "not found"
- **Expected Missing**: Maximum 5 citations (user's realistic estimate)
- **Actual Result**: Catastrophic matching failure

### Evidence of Matching Bug
```bash
# Citation EXISTS in RDF:
<dc:identifier>
  <dcterms:URI>
    <rdf:value>https://doi.org/10.1007/978-3-031-70262-4_5</rdf:value>
  </dcterms:URI>
</dc:identifier>

# But converter reports: "Citation not found in Zotero collection"
```

**Conclusion**: Matching logic is broken, NOT missing RDF data.

---

## CLAUDE.md Principles to Follow

### 1. Deterministic Behavior (CRITICAL)
- **ALWAYS** produce same output for same input
- **NEVER** rely on non-deterministic factors without explicit caching
- **ALWAYS** provide audit trails for validation decisions

### 2. Emergency Mode Requirements (ADDED 2025-10-30)
From `.claude/CLAUDE.md` lines 29-34:
- **NEVER** allow web fetching when `emergency_mode=True`
- **NEVER** proceed if RDF file is missing (MUST HARD CRASH)
- **NEVER** proceed if RDF file is empty (MUST HARD CRASH)
- **NEVER** auto-merge duplicate citations (FLAG only, require manual review)
- **NEVER** allow >5 missing citations without WARNING (likely indicates matching bug)

### 3. Conversion Success Criteria (LINES 322-348)
The ONLY measure of success: **Working PDF with ALL citations resolved**

**BEFORE claiming conversion success, verify ALL of these**:
1. ✅ PDF generates without LaTeX errors
2. ✅ PDF has ZERO (?) citations (use Read tool to check PDF visually)
3. ✅ PDF has ZERO (Unknown) or (Anonymous) citations
4. ✅ All citations show proper author names and years
5. ✅ references.bib has ZERO "Unknown" or "Anonymous" entries
6. ✅ LaTeX log has ZERO compilation errors
7. ✅ BibTeX log has ZERO fatal errors (warnings OK)

**Intermediate steps do NOT count as success.**

### 4. No Directory Cleaning (LINES 14-18)
- **NEVER** implement directory cleaning operations
- **ONLY** remove specific, known output files (e.g., `output.pdf`)
- **NEVER** use `shutil.rmtree()`, `rm -rf`, or loop deletions
- If cleaning needed: **ONLY** delete files with explicit extensions

---

## Historical Context: Recurring Matching Failures

This is **NOT the first time** matching has failed. We have 4 documented previous debugging sessions:

### 1. plea-to-openai-robust-matching.md (2025-10-26)
- URL-only matching fails 12% of time (46/376 citations)
- Proposed multi-strategy matching (DOI, arXiv, ISBN, URL, fuzzy)
- **Never implemented**

### 2. zotero-matching-vision.md (2025-10-29)
- **Core Principle**: "Citation keys are IDENTITY, not MATCH CRITERIA"
- **The One Rule**: "Match by DOI/URL/arXiv, USE whatever key Zotero provides"
- Critical bug pattern: Collection not initialized → entries never loaded → temp keys created
- **Never fully fixed**

### 3. SYSTEMATIC-FLETCHER-AMAZON-DEBUG (2025-10-30 Night)
- Fletcher book available in RDF but reported missing
- Days of failed attempts to fix
- 7 root causes identified (URL normalization, cache, web fetching)
- **Never comprehensively fixed**

### 4. Tonight's RDF Parser Bug Discovery (2025-10-31)
- Parser only looked at `rdf:about` attribute
- Ignored nested `<dcterms:URI><rdf:value>` structure
- **Fixed tonight** in bibliography_sources.py lines 387-402
- But hundreds of citations STILL failing

---

## Comprehensive Root Cause Analysis

### Category 1: Identifier Extraction Not Implemented
**Status**: Proposed Oct 26, never implemented

**Problem**: System matches by FULL URLs, not identifiers
- Citation has: `https://doi.org/10.1007/978-3-031-70262-4_5`
- RDF has: `https://doi.org/10.1007/978-3-031-70262-4_5`
- **Should match by DOI**: `10.1007/978-3-031-70262-4_5`

**Impact**:
- arXiv URL format variations fail to match
- DOI HTTP vs HTTPS fails to match
- Amazon URL path variations fail to match

**Solution**: Extract stable identifiers FIRST:
```python
def extract_identifiers(url: str) -> Dict[str, str]:
    """Extract stable identifiers from URLs."""
    identifiers = {}

    # DOI extraction (most authoritative)
    if "doi.org/" in url:
        identifiers["doi"] = url.split("doi.org/")[-1].strip("/")

    # arXiv ID extraction
    if "arxiv.org/abs/" in url:
        identifiers["arxiv"] = url.split("arxiv.org/abs/")[-1].strip("/")

    # Amazon ISBN extraction
    if "amazon." in url and "/dp/" in url:
        identifiers["isbn"] = url.split("/dp/")[-1].split("/")[0]

    # PubMed ID extraction
    if "pubmed.ncbi.nlm.nih.gov" in url or "ncbi.nlm.nih.gov/pubmed" in url:
        identifiers["pmid"] = url.rstrip("/").split("/")[-1]

    return identifiers
```

### Category 2: True Emergency Mode Not Implemented
**Status**: Requirements added Oct 30, never implemented

**Problem**: System still fetches from web in "emergency mode"
- Log shows: `Failed to fetch https://www.fda.gov/... HTTP 404`
- CLAUDE.md line 30: **NEVER** allow web fetching in emergency mode

**Impact**:
- Mixing RDF data with web data (non-deterministic)
- Slow performance (waiting for HTTP timeouts)
- Cache pollution from failed web fetches

**Solution**: Add `--no-web-fetch` flag
```python
if emergency_mode and not args.no_web_fetch:
    raise ValueError(
        "Emergency mode requires --no-web-fetch flag. "
        "Cannot fetch from web in emergency mode."
    )

if args.no_web_fetch and citation not in rdf_entries:
    # Fail immediately, don't try web
    raise CitationNotFoundError(
        f"Citation {url} not in RDF and web fetch disabled"
    )
```

### Category 3: Cache Contamination Risk
**Status**: User identified tonight, not implemented

**Problem**: Cache may contain stale data from previous runs
- Cache entry from run WITH web access
- Now running in emergency mode
- Cache returns web-fetched data (not RDF data)

**Impact**: Non-deterministic results, impossible to debug

**Solution**: Add `--no-cache` flag
```python
if args.no_cache:
    # Disable all caches
    translation_client.cache = None
    author_enrichment.cache = None
    # Don't write new cache entries
    os.environ["DISABLE_CACHING"] = "1"
```

### Category 4: URL Normalization Insufficient
**Status**: Partially implemented, still failing

**Problem**: URLs have many valid variations
- `https://arxiv.org/abs/2401.12345` vs `https://www.arxiv.org/abs/2401.12345`
- `https://doi.org/10.1234/example` vs `http://dx.doi.org/10.1234/example`
- `https://amazon.de/dp/ISBN` vs `https://amazon.de/-/en/Title/dp/ISBN`

**Impact**: Same paper with slightly different URL fails to match

**Solution**: Normalize BEFORE matching
```python
def normalize_url(url: str) -> str:
    """Normalize URL for matching."""
    url = url.lower().strip()

    # Remove protocol
    url = url.replace("https://", "").replace("http://", "")

    # Remove www prefix
    url = url.replace("www.", "")

    # DOI normalization
    if "doi.org/" in url:
        return "doi.org/" + url.split("doi.org/")[-1]

    # arXiv normalization
    if "arxiv.org/abs/" in url:
        return "arxiv.org/abs/" + url.split("arxiv.org/abs/")[-1]

    # Amazon normalization (keep only domain + /dp/ISBN)
    if "amazon." in url and "/dp/" in url:
        domain = url.split("/")[0]  # amazon.de or amazon.com
        isbn = url.split("/dp/")[-1].split("/")[0]
        return f"{domain}/dp/{isbn}"

    return url
```

### Category 5: No Multi-Strategy Fallback
**Status**: Proposed Oct 26, never implemented

**Problem**: Single matching strategy (URL-only) fails completely

**Solution**: Try multiple strategies in priority order:
1. Match by DOI (if extracted)
2. Match by arXiv ID (if extracted)
3. Match by ISBN (if extracted)
4. Match by PubMed ID (if extracted)
5. Match by normalized URL
6. Match by fuzzy title + first author

---

## Implementation Plan: Systematic Approach

### Phase 0: Analysis and Documentation (CURRENT)
**Goal**: Comprehensive understanding before code changes
**Duration**: Take all time needed (user sleeping)

**Tasks**:
- [x] Read all historical matching failure documents
- [x] Read CLAUDE.md for project principles
- [x] Create comprehensive analysis document
- [x] Create refined prompt (this document)
- [ ] Develop detailed implementation plan with tests
- [ ] Get evidence from current conversion attempt

**Output**: Complete understanding of problem space

### Phase 1: Core Identifier Matching (HIGHEST PRIORITY)
**Goal**: Match by stable identifiers, not full URLs

**Tasks**:
1. Implement `extract_identifiers()` function with tests
2. Implement `normalize_url()` function with tests
3. Update matching logic to use identifiers first
4. Add comprehensive logging of matching attempts
5. Add real-time statistics (matched by DOI, arXiv, URL, etc.)

**Success Criteria**:
- DOI-based matching works 100% for DOI citations
- arXiv-based matching works 100% for arXiv citations
- ISBN-based matching works 100% for Amazon books
- Comprehensive test coverage (>20 test cases)

**Tests to Write**:
```python
def test_doi_matching_http_vs_https():
    """DOI should match regardless of protocol."""
    assert match("https://doi.org/10.1234/example") == \
           match("http://doi.org/10.1234/example")

def test_arxiv_matching_with_without_www():
    """arXiv should match with/without www."""
    assert match("https://arxiv.org/abs/2401.12345") == \
           match("https://www.arxiv.org/abs/2401.12345")

def test_amazon_isbn_different_paths():
    """Amazon should match by ISBN regardless of path."""
    assert match("https://amazon.de/dp/0470519460") == \
           match("https://amazon.de/-/en/Multi-Agent-Systems/dp/0470519460")
```

### Phase 2: True Emergency Mode Implementation
**Goal**: RDF-only operation, zero web access, zero cache use

**Tasks**:
1. Add `--no-web-fetch` flag to deterministic_convert.py
2. Add `--no-cache` flag to deterministic_convert.py
3. Implement hard crash if RDF missing or empty
4. Implement warning if >5 citations missing (likely bug)
5. Update tests for emergency mode

**Success Criteria**:
- Zero HTTP requests in emergency mode (verify with network monitoring)
- Zero cache reads/writes with --no-cache flag
- Hard crash with clear error if RDF missing
- Warning logged if >5 citations missing

**Tests to Write**:
```python
def test_emergency_mode_no_web_access(monkeypatch):
    """Emergency mode must not make HTTP requests."""
    requests_made = []

    def mock_request(*args, **kwargs):
        requests_made.append(args[0])
        raise AssertionError("HTTP request in emergency mode!")

    monkeypatch.setattr(requests, "get", mock_request)

    # Should succeed without any HTTP requests
    convert(input_md, rdf=rdf_path, no_web_fetch=True)
    assert len(requests_made) == 0

def test_no_cache_flag_disables_all_caches():
    """--no-cache should disable ALL caching."""
    convert(input_md, rdf=rdf_path, no_cache=True)

    # Verify no cache files written
    assert not Path(".cache").exists()
    assert not any(Path(".").glob("**/*.cache"))
```

### Phase 3: Output File Management
**Goal**: Clean only specific output files before conversion

**Tasks**:
1. Implement explicit file deletion (NOT directory cleaning)
2. Delete specific files: `output.pdf`, `*.aux`, `*.log`, `*.bbl`, `references.bib`
3. NEVER use `shutil.rmtree()` or `rm -rf` (CLAUDE.md violation)
4. Add `--clean-output` flag (explicit opt-in)

**Success Criteria**:
- Only specified files deleted
- Never deletes directories
- Never deletes input files
- Explicit user opt-in required

**Implementation**:
```python
def clean_output_files(output_dir: Path, base_name: str):
    """Delete specific output files only."""
    # NEVER delete directories
    if not output_dir.is_dir():
        return

    # Delete ONLY these specific files
    files_to_delete = [
        output_dir / f"{base_name}.pdf",
        output_dir / f"{base_name}.aux",
        output_dir / f"{base_name}.log",
        output_dir / f"{base_name}.bbl",
        output_dir / "references.bib",
    ]

    for file_path in files_to_delete:
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            logger.info(f"Deleted: {file_path}")
```

### Phase 4: Comprehensive Testing and Verification
**Goal**: Prove the system works on actual paper

**Tasks**:
1. Run full conversion on actual file (mcp-draft-refined-v4.md)
2. Verify with bib_sanitizer.py in emergency mode
3. Verify with verify_bbl_quality.py
4. Read actual PDF with Read tool
5. Verify ZERO (?) citations in PDF
6. Document all matching statistics

**Success Criteria** (from CLAUDE.md):
- ✅ PDF generates without LaTeX errors
- ✅ PDF has ZERO (?) citations
- ✅ PDF has ZERO (Unknown) or (Anonymous) citations
- ✅ All citations show proper author names and years
- ✅ references.bib has ZERO "Unknown" or "Anonymous" entries
- ✅ ≤5 citations missing (user's realistic estimate)

### Phase 5: Pre-Commit Checks and Real-Time Monitoring
**Goal**: Prevent regression of matching bugs

**Tasks**:
1. Add pre-commit hook to check for Temp keys
2. Add pre-commit hook to run verify_bbl_quality.py
3. Add real-time matching statistics logging
4. Add GitHub Actions CI check
5. Update documentation

**Success Criteria**:
- Pre-commit fails if Temp keys detected
- Pre-commit fails if quality checks fail
- Real-time logging shows matching method for each citation
- CI prevents merging broken matching code

---

## Verification Strategy: Multi-Layered Testing

### Layer 1: Unit Tests (Test Each Component)
```python
# Test identifier extraction
test_extract_doi_from_url()
test_extract_arxiv_from_url()
test_extract_isbn_from_amazon_url()

# Test URL normalization
test_normalize_doi_url()
test_normalize_arxiv_url()
test_normalize_amazon_url()

# Test matching strategies
test_match_by_doi()
test_match_by_arxiv()
test_match_by_isbn()
test_fallback_to_url_matching()
```

### Layer 2: Integration Tests (Test Full Pipeline)
```python
# Test on small RDF subset
test_conversion_with_10_citations()
test_conversion_with_mixed_sources()  # DOI + arXiv + Amazon + web URLs

# Test emergency mode
test_emergency_mode_no_web()
test_emergency_mode_no_cache()
test_emergency_mode_warns_on_many_missing()
```

### Layer 3: Actual Paper Conversion (Real-World Test)
```bash
# The ACTUAL test that matters
uv run python scripts/deterministic_convert.py \
  /path/to/mcp-draft-refined-v4.md \
  --rdf /path/to/dpp-fashion-zotero.rdf \
  --output-dir /path/to/output \
  --no-web-fetch \
  --no-cache \
  --clean-output \
  --verbose

# Then verify PDF has zero (?) citations
```

### Layer 4: Quality Verification Tools
```bash
# Run bib_sanitizer.py
uv run python scripts/bib_sanitizer.py \
  --rdf /path/to/dpp-fashion-zotero.rdf \
  --emergency-mode

# Run verify_bbl_quality.py
uv run python scripts/verify_bbl_quality.py \
  /path/to/output/mcp-draft-refined-v4.bbl
```

### Layer 5: Manual PDF Inspection
- Read PDF with Read tool
- Search for "(?" in PDF (should be zero)
- Search for "Unknown" in PDF (should be zero)
- Spot-check 10 random citations (should have author names)

---

## Success Metrics: Objective Verification

### Quantitative Metrics
1. **Match Rate**: ≥99% (max 5 missing from 383 citations)
2. **Temp Keys**: 0 (zero tolerance)
3. **(?) Citations in PDF**: 0 (zero tolerance)
4. **Unknown Authors**: 0 (zero tolerance)
5. **Conversion Time**: <5 minutes (with RDF, no web access)

### Qualitative Metrics
1. **Determinism**: Same input → same output (100% reproducible)
2. **Auditability**: Clear logs showing why each citation matched/failed
3. **Debuggability**: Easy to identify root cause of any failures
4. **Maintainability**: Code follows CLAUDE.md principles

### User Satisfaction Metrics
1. **Can submit paper**: PDF is ready for submission
2. **Can verify manually**: Easy to spot-check citations
3. **Can trust results**: Confident all citations are correct
4. **Can debug issues**: Clear logs if something goes wrong

---

## Fallback Strategies: What If Something Fails?

### Fallback 1: If Identifier Matching Fails for Specific Citation
1. Try normalized URL matching
2. Try fuzzy title + first author matching
3. Generate temp key with clear warning
4. Log detailed diagnostics for manual review

### Fallback 2: If >5 Citations Missing
1. Log WARNING (likely indicates bug, not missing data)
2. Generate detailed matching report
3. Show which matching strategies were tried for each
4. Suggest running with --verbose for debugging

### Fallback 3: If Emergency Mode Cannot Complete
1. Clear error message explaining why
2. Suggest checking RDF file exists and is valid
3. Suggest trying without --no-web-fetch (but warn about non-determinism)
4. Provide path to matching diagnostics

### Fallback 4: If PDF Has (?) Citations
1. Run verify_bbl_quality.py automatically
2. Generate report of all (?) citations
3. Check if they're in RDF (matching bug) or missing (data issue)
4. Provide actionable next steps

---

## Commit Strategy: Incremental, Testable Progress

Following user directive: "commit after each phase with push"

### Commit 1: Analysis and Planning
```bash
git add docs/planning/COMPREHENSIVE-MATCHING-ANALYSIS-2025-10-31.md
git add docs/planning/USER-PROMPT-MATCHING-ISSUES-2025-10-31.md
git add docs/planning/REFINED-PROMPT-MATCHING-ISSUES-2025-10-31.md
git commit -m "docs: Comprehensive matching failure analysis and refined implementation plan"
git push
```

### Commit 2: Identifier Extraction (Phase 1)
```bash
git add src/converters/md_to_latex/identifier_extraction.py
git add tests/test_identifier_extraction.py
git commit -m "feat: Add identifier extraction for DOI/arXiv/ISBN/PubMed"
git push
```

### Commit 3: Multi-Strategy Matching (Phase 1)
```bash
git add src/converters/md_to_latex/citation_matcher.py
git add tests/test_citation_matcher.py
git commit -m "feat: Implement multi-strategy citation matching with fallback"
git push
```

### Commit 4: Emergency Mode Flags (Phase 2)
```bash
git add scripts/deterministic_convert.py
git add src/converters/md_to_latex/bibliography_sources.py
git add tests/test_emergency_mode.py
git commit -m "feat: Add --no-web-fetch and --no-cache flags for emergency mode"
git push
```

### Commit 5: Output Cleaning (Phase 3)
```bash
git add scripts/deterministic_convert.py
git add tests/test_output_cleaning.py
git commit -m "feat: Add --clean-output flag for explicit file deletion"
git push
```

### Commit 6: Pre-Commit Checks (Phase 5)
```bash
git add .pre-commit-config.yaml
git add scripts/check_temp_keys.py
git commit -m "feat: Add pre-commit checks for temp keys and quality"
git push
```

### Commit 7: Final Verification and Documentation
```bash
git add docs/planning/COMPLETION-REPORT-2025-10-31.md
git commit -m "docs: Matching system overhaul completion report with verification"
git push
```

---

## References: Related Documents

1. **USER-PROMPT-MATCHING-ISSUES-2025-10-31.md** - Original user prompt (verbatim)
2. **COMPREHENSIVE-MATCHING-ANALYSIS-2025-10-31.md** - Historical context and synthesis
3. **.claude/CLAUDE.md** - Project behavioral contract and principles
4. **plea-to-openai-robust-matching.md** (2025-10-26) - First matching failure proposal
5. **zotero-matching-vision.md** (2025-10-29) - Core principles and recurring bugs
6. **SYSTEMATIC-FLETCHER-AMAZON-DEBUG-2025-10-30-NIGHT.md** - Recent debugging session

---

## Key Differences from Original Prompt

This refined prompt improves on the user's original by:

1. **Explicit CLAUDE.md Integration**: References specific lines and principles
2. **Evidence-Based Approach**: Uses actual RDF parsing bug as proof
3. **Phased Implementation**: Clear phases with success criteria
4. **Test-First Mindset**: Unit tests → integration tests → real paper
5. **Quantitative Metrics**: Objective verification (≤5 missing, 0 temp keys)
6. **Fallback Strategies**: What to do when things don't work perfectly
7. **No Rush Emphasis**: "Take all time needed" incorporated throughout
8. **Commit Strategy**: Incremental progress with pushes

---

## Expected Timeline

**IMPORTANT**: User said "take all the tokens and time needed" - no rush!

- **Phase 0** (Analysis): Already mostly complete
- **Phase 1** (Identifier matching): ~2-3 hours (tests + implementation)
- **Phase 2** (Emergency mode): ~1-2 hours (flags + tests)
- **Phase 3** (Output cleaning): ~1 hour (simple implementation)
- **Phase 4** (Verification): ~1-2 hours (run actual conversion + verify)
- **Phase 5** (Pre-commit): ~1 hour (hooks + CI)

**Total**: ~7-10 hours of systematic work while user sleeps

**Priority**: Correctness > Speed. Better to take 10 hours and get it right than rush in 2 hours and still have bugs.

---

## Final Notes for Implementation

1. **Follow CLAUDE.md rigorously** - It exists to prevent mistakes
2. **Write tests FIRST** - Prove the bug, then fix it
3. **Commit after each phase** - Incremental progress
4. **No directory cleaning** - CLAUDE.md lines 14-18 forbid this
5. **Verify PDF with Read tool** - Don't trust intermediate steps
6. **Write markdown status files** - User requested this instead of summaries
7. **Work continuously until complete** - User is sleeping

**User's words**: "execute without breaks until the end"

Let's do this right. 🎯
