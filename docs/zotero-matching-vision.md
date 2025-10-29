# Zotero Matching Vision: Robust Citation Resolution

**Date**: 2025-10-29
**Status**: **Critical - Multiple Re-Explanations Required**
**Branch**: `fix/verify-md-to-latex-conversion`

---

## Executive Summary

**THE FUNDAMENTAL PRINCIPLE**: Citation keys are **IDENTITY**, not **MATCH CRITERIA**.

- **Match** citations by: URL, DOI, arXiv ID, ISBN
- **Use** whatever citation key Zotero provides (never regenerate locally)
- **Never** try to match citation keys themselves - they are outputs, not inputs

---

## The Recurring Bug Pattern

### What Keeps Happening

1. Claude Code attempts to match citations during extraction
2. Zotero entries are not loaded at that time (initialization bug)
3. All citations fail to match → create Temp entries
4. Later, a SECOND matching pass runs successfully
5. But by then, Temp keys are already assigned → still broken

### Root Cause (This Session)

**Bug Location**: `src/converters/md_to_latex/converter.py:116`

```python
# BEFORE (BROKEN):
self.collection_name = collection_name  # Could be None!

# AFTER (FIXED):
self.collection_name = collection_name or os.getenv("ZOTERO_COLLECTION", "dpp-fashion")
```

**What Happened**:
1. Converter.__init__ gets `collection_name=None` (default parameter)
2. CitationManager initialized with `zotero_collection=None`
3. In CitationManager.__init__:288, condition `if zotero_collection:` is FALSE
4. **`load_collection_with_keys()` is NEVER called**
5. `self.zotero_entries = {}` remains EMPTY
6. Citation extraction tries to match against empty dict → all citations become Temp
7. Later at converter.py:899 (old code), collection_name read from env (too late!)

**Symptoms**:
- Log shows: `Initialized Zotero client with library_id: 4953359` ✅
- Log MISSING: `Loaded X entries from Zotero collection 'dpp-fashion'` ❌
- Result: 260/381 citations matched from converter's SECOND pass
- But 121 citations still have Temp keys from the FIRST (failed) pass

---

## Correct Matching Strategy

### NEVER Do This ❌

```python
# DON'T: Try to match citation keys
if citation_key in zotero_entries:
    return zotero_entries[citation_key]

# DON'T: Generate keys locally
def generate_citation_key(author, year):
    return f"{author.lower()}{year}"  # WRONG!

# DON'T: Validate key format
if not re.match(r'^[a-z]+[A-Z][a-z]+\d{4}$', key):
    raise ValueError("Invalid Better BibTeX key")
```

**Why This Fails**:
- Keys change (Web API: `niinimaki_environmental_2020` vs Better BibTeX: `niinimakiEnvironmentalPriceFast2020`)
- Diacritics stripped (Niinimäki → niinimaki)
- Keys are deterministic FROM ZOTERO, but not predictable by us
- Matching keys = trying to match identity, not content

### ALWAYS Do This ✅

```python
def _lookup_zotero_entry_by_url(self, url: str) -> tuple[str, dict] | None:
    """Look up Zotero entry by URL or DOI."""
    if not self.zotero_entries:
        return None

    # Extract DOI if present in URL
    doi = extract_doi_from_url(url)

    # Search through Zotero entries for matching URL or DOI
    for cite_key, entry in self.zotero_entries.items():
        entry_url = entry.get("url", "")
        entry_doi = entry.get("doi", "")

        # Match by DOI (most reliable)
        if doi and entry_doi and doi == entry_doi:
            logger.debug(f"Found Zotero entry by DOI match: {cite_key} (DOI: {doi})")
            return (cite_key, entry)  # ← USE whatever key Zotero provided

        # Match by URL (normalized)
        if url and entry_url:
            if normalize_url(url) == normalize_url(entry_url):
                logger.debug(f"Found Zotero entry by URL match: {cite_key}")
                return (cite_key, entry)

        # Match by arXiv ID
        if "arxiv.org" in url:
            arxiv_id = extract_arxiv_id(url)
            entry_arxiv = entry.get("arxiv_id", "")
            if arxiv_id and entry_arxiv and arxiv_id == entry_arxiv:
                logger.debug(f"Found Zotero entry by arXiv match: {cite_key}")
                return (cite_key, entry)

    return None  # Not in Zotero → create Temp entry
```

**Why This Works**:
- DOI/URL/arXiv are stable identifiers (persistent)
- Keys are whatever Zotero provides (we just use them)
- No local key generation or validation
- Clear separation: MATCH by identifier, USE the key

---

## The Two-Pass Matching Bug

### Current Architecture (BROKEN)

```
┌─────────────────────────────────────────────────────────────┐
│ PASS 1: Citation Extraction (citation_manager.py)          │
├─────────────────────────────────────────────────────────────┤
│ 1. extract_citations() called                               │
│ 2. For each citation, _lookup_zotero_entry_by_url()        │
│ 3. self.zotero_entries = {} (EMPTY! Bug!)                  │
│ 4. All lookups return None                                  │
│ 5. All citations get Temp keys                              │
└─────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────┐
│ PASS 2: Zotero Matching (converter.py:910)                 │
├─────────────────────────────────────────────────────────────┤
│ 1. _populate_from_zotero_bibtex() called                   │
│ 2. Loads 658 BibTeX entries from Zotero API                │
│ 3. Builds lookup maps (url_to_key, doi_to_key, etc.)       │
│ 4. Matches 260/381 citations successfully                   │
│ 5. But 121 citations ALREADY have Temp keys (from Pass 1)  │
│ 6. Those Temp keys stick → still broken!                    │
└─────────────────────────────────────────────────────────────┘
```

### Fixed Architecture (CORRECT)

```
┌─────────────────────────────────────────────────────────────┐
│ INITIALIZATION: Load Zotero Entries FIRST                  │
├─────────────────────────────────────────────────────────────┤
│ 1. Converter.__init__ sets collection_name from env         │
│ 2. CitationManager.__init__(zotero_collection="dpp-fashion")│
│ 3. load_collection_with_keys() called                       │
│ 4. self.zotero_entries = {658 entries loaded}              │
│ 5. Log: "Loaded 658 entries with Better BibTeX keys"       │
└─────────────────────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────────────────────┐
│ SINGLE PASS: Citation Extraction with Loaded Entries       │
├─────────────────────────────────────────────────────────────┤
│ 1. extract_citations() called                               │
│ 2. For each citation, _lookup_zotero_entry_by_url()        │
│ 3. self.zotero_entries has 658 entries (LOADED!)           │
│ 4. DOI/URL/arXiv matching succeeds                          │
│ 5. ~380/381 citations matched on first pass                 │
│ 6. Only genuinely missing citations get Temp keys           │
└─────────────────────────────────────────────────────────────┘
```

---

## What NOT to Do (Lessons Learned)

### ❌ Don't Validate Citation Key Format

```python
# WRONG - Keys are identity, not validation targets
if key and not key.startswith("temp"):
    if "_" in key:  # Web API format
        if not re.match(r'^[a-z]+_[a-z]+_\d{4}$', key):
            logger.warning(f"Invalid Web API key: {key}")
    else:  # Better BibTeX format
        if not re.match(r'^[a-z][a-zA-Z]*\d{4}[a-z]*$', key):
            logger.warning(f"Invalid Better BibTeX key: {key}")
```

**Why This Is Wrong**:
- Keys can be in ANY format Zotero generates
- We have NO authority to validate them
- Warning about "invalid" keys implies we know the "right" format
- Better BibTeX keys are user-configurable in Zotero!

### ❌ Don't Have Local Key Databases

```python
# WRONG - Creates parallel sources of truth
self.local_keys = {}
self.zotero_entries = {}

# Now we have to reconcile two sources:
if key in self.local_keys:
    # Use local
elif key in self.zotero_entries:
    # Use Zotero
else:
    # Create new? Conflict!
```

**Right Approach**:
- ONE source of truth: `self.zotero_entries` from Zotero API
- NO local key generation
- NO local key database
- If not in Zotero → add to Zotero via API → reload

### ❌ Don't Match During Extraction

```python
# WRONG - Extraction should not depend on matching
def extract_citations(self, content: str) -> list[Citation]:
    citations = []
    for url, text in find_citation_links(content):
        # DON'T: Try to match now
        cite_key = self._lookup_zotero_entry_by_url(url)
        if not cite_key:
            cite_key = self._generate_temp_key(text)  # BAD!
        citations.append(Citation(url=url, key=cite_key))
    return citations
```

**Right Approach**:
- Extract citations WITHOUT keys
- Match against Zotero AFTER extraction
- Assign keys only after successful matching
- One-pass, one source of truth

---

## The Correct Workflow

### 1. Initialization (FIXED)

```python
# converter.py:116
self.collection_name = collection_name or os.getenv("ZOTERO_COLLECTION", "dpp-fashion")

# converter.py:119-123
self.citation_manager = CitationManager(
    zotero_collection=self.collection_name,  # ← Now guaranteed to have value
    # ...
)

# citation_manager.py:288-296
if zotero_collection:  # ← Now TRUE!
    try:
        self.zotero_entries = self.zotero_client.load_collection_with_keys(
            zotero_collection
        )
        logger.info(f"Loaded {len(self.zotero_entries)} entries from Zotero collection")
```

### 2. Citation Extraction (SINGLE PASS)

```python
# converter.py:867
citations = self.citation_manager.extract_citations(content)

# citation_manager.py (during extraction)
def extract_citations(self, content: str) -> list[Citation]:
    for url, text in find_citation_links(content):
        # Match against loaded Zotero entries
        match = self._lookup_zotero_entry_by_url(url)  # ← Works now!
        if match:
            cite_key, entry = match
            citations.append(Citation(url=url, key=cite_key, ...))
        else:
            # Not in Zotero → add via API
            cite_key = self._handle_missing_citation(url, text)
            citations.append(Citation(url=url, key=cite_key, ...))
```

### 3. No Second Pass Needed

```python
# converter.py:910 (THIS SHOULD BE REMOVED OR BECOME NO-OP)
# The old _populate_from_zotero_bibtex() is redundant now
# All matching already happened during extraction
```

---

## References to Existing Documentation

### Related Documents

1. **[plea-to-openai-robust-matching.md](plea-to-openai-robust-matching.md)**
   - Multi-strategy matching (URL, DOI, ISBN, arXiv)
   - Fallback to fuzzy title matching
   - Expected 90%+ success rate

2. **[phase-5-author-enrichment-solution.md](retrospectives/phase-5-author-enrichment-solution.md)**
   - Automatic author enrichment from CrossRef/arXiv
   - Integration with Zotero loading
   - Expected to fix truncated author lists

3. **[better-bibtex-key-strategy.md](better-bibtex-key-strategy.md)**
   - Citation key format requirements
   - Why keys must come from Zotero only
   - No local key generation allowed

4. **CLAUDE.md (Bibliography Workflow)**
   - Zotero Web API only (SINGLE SOURCE OF TRUTH)
   - No manual CSL JSON exports
   - Auto-add missing citations to Zotero
   - Regenerate references.bib from Zotero every time

---

## Success Criteria

### Immediate (This Fix)

- ✅ Syntax errors fixed (f-strings with raw strings)
- ✅ collection_name initialized from environment variable
- ✅ CitationManager loads Zotero entries during __init__
- ⏳ Test conversion: Verify 658 entries loaded (not 0)
- ⏳ Test conversion: Verify ~380/381 citations matched (not 260)

### Short Term (Next Session)

- ⏳ Remove redundant _populate_from_zotero_bibtex() second pass
- ⏳ Delete references.bib before each conversion
- ⏳ Implement automatic Zotero API addition for missing citations
- ⏳ Verify (?) marks in PDF drop from 372 to ~10-20

### Long Term (Vision)

- Clean architecture: ONE matching pass, ONE source of truth
- Comprehensive matching: DOI > ISBN > arXiv > URL > fuzzy title
- Zero local key generation or validation
- Robust to Zotero key format changes
- Automatic addition of missing citations via API
- 100% reproducible: same input → same output

---

## How We Keep Fucking Up (Root Cause Analysis)

### Pattern 1: Dual Sources of Truth

**Symptom**: CitationManager has empty `self.zotero_entries`, but converter has second matching pass

**Why This Happens**:
1. Someone adds a new matching method without checking existing ones
2. Code grows organically without refactoring
3. Both methods work partially, neither works completely
4. Bug masked by partial success (260/381 matches)

**Prevention**:
- Single matching location in codebase
- Assert ONE source of truth: `self.zotero_entries`
- Remove all secondary matching passes
- Log at startup: "Zotero entries loaded: X"

### Pattern 2: Environment Variable Reading at Wrong Time

**Symptom**: collection_name read AFTER CitationManager initialization

**Why This Happens**:
1. Parameter defaults to None (seems safe)
2. Environment variable read "just in time" (seems DRY)
3. But initialization happens earlier → None propagates
4. Bug manifests as silent failure (no error, just empty dict)

**Prevention**:
- Read environment variables at module init or __init__ only
- Never defer environment reading to "later"
- Default parameters should be VALUES, not None
- Log all config at startup

### Pattern 3: Silent Failures

**Symptom**: No log message "Loaded X entries from Zotero collection"

**Why This Happens**:
1. Try/except catches Exception but continues silently
2. No explicit assertion or check for empty dict
3. Logs show "Initialized client" (partial success)
4. Missing log for "Loaded entries" (actual success)

**Prevention**:
- Loud failures: log.ERROR and raise if critical step fails
- Check postconditions: `assert len(self.zotero_entries) > 0`
- Log every critical milestone explicitly
- Unit test: verify entries loaded during __init__

### Pattern 4: Key Format Confusion

**Symptom**: Warnings about "invalid" citation key format

**Why This Happens**:
1. Confusion between matching (input) vs identity (output)
2. Assumption that keys have "correct" format
3. Validation logic for something we don't control
4. Better BibTeX format is user-configurable!

**Prevention**:
- Never validate citation key format
- Keys are opaque identifiers from Zotero
- Match by DOI/URL/arXiv, USE whatever key Zotero gives
- Document: "Keys are identity, not match criteria"

---

## The Correct Mental Model

### Citation Resolution Flow

```
┌─────────────────┐
│ Markdown File   │
│ [Author, Year]  │
│ (URL)           │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────┐
│ Extract Citation Pattern        │
│ - Author text                   │
│ - Year                          │
│ - URL/DOI/arXiv                 │
└────────┬────────────────────────┘
         │
         ↓
┌─────────────────────────────────┐
│ Match Against Zotero            │
│ - Load entries ONCE at startup  │
│ - Match by DOI (most reliable)  │
│ - Fallback to URL               │
│ - Fallback to arXiv ID          │
└────────┬────────────────────────┘
         │
         ├─ FOUND ────────→ Use Zotero's citation key (e.g., "niinimakiEnvironmentalPriceFast2020")
         │
         └─ NOT FOUND ───→ Add to Zotero via API → Get key → Use it
```

### What We DON'T Do

```
┌─────────────────┐
│ Markdown File   │
└────────┬────────┘
         │
         ↓
❌ Generate local key (smith2024)
❌ Validate key format
❌ Check against local database
❌ Match by key name
❌ Create Temp entries that stick
❌ Have multiple matching passes
```

---

## Implementation Checklist

### Done ✅

- [x] Fix syntax errors (f-strings with raw strings)
- [x] Fix collection_name initialization (read from env during __init__)
- [x] Update converter.py:116 to read ZOTERO_COLLECTION
- [x] Remove redundant line 900 (reading env again)
- [x] Document root cause in this file

### Next Steps ⏳

- [ ] Run test conversion with fixed code
- [ ] Verify log: "Loaded 658 entries from Zotero collection 'dpp-fashion'"
- [ ] Verify citations matched: ~380/381 (not 260/381)
- [ ] Count (?) marks in PDF: expect ~10-20 (down from 372)
- [ ] Remove redundant _populate_from_zotero_bibtex() second pass
- [ ] Add unit test: CitationManager.__init__ loads entries
- [ ] Add unit test: Conversion with env var works
- [ ] Update CLAUDE.md with lessons learned

---

## Actionable Plan (Incorporating External Review)

### What We Should Do ✅

Based on external review and codebase reality, here's the prioritized action plan:

#### 1. Immediate (This Session) - DONE

- [x] Fix collection_name initialization bug (converter.py:116)
- [x] Fix syntax errors (f-strings with raw strings)
- [x] Document root cause and patterns

#### 2. Validation (Next Session)

**Goal**: Verify the fix works

- [ ] Run test conversion with fixed code
- [ ] Check logs for: `"Loaded 658 entries from Zotero collection 'dpp-fashion'"`
- [ ] Verify matching rate: expect ~380/381 (not 260/381)
- [ ] Count (?) marks in PDF: expect ~10-20 (down from 372)

#### 3. Architecture Cleanup (After Validation)

**Goal**: Remove dual-pass pathology

- [ ] Make `_populate_from_zotero_bibtex()` a NO-OP or remove entirely
  - It's redundant now that entries load during __init__
  - Keep the method signature for backward compatibility
  - Log warning if called: "Second-pass matching is deprecated"

- [ ] Add assertion in `extract_citations()`:
  ```python
  if not self.zotero_entries:
      raise RuntimeError("Zotero entries not loaded - check initialization")
  ```

#### 4. Test Coverage (After Cleanup)

**Goal**: Prevent regression

- [ ] Unit test: `test_citation_manager_init_loads_entries()`
  - Mock ZoteroClient that returns known entries
  - Assert `len(citation_manager.zotero_entries) > 0`
  - Assert log message contains "Loaded X entries"

- [ ] Unit test: `test_citation_manager_matches_by_doi()`
  - Mock entry with DOI "10.1000/test"
  - Create citation with URL "https://doi.org/10.1000/test"
  - Assert match found, key returned

- [ ] Integration test: `test_conversion_with_env_var()`
  - Set ZOTERO_COLLECTION="test-collection"
  - Run conversion
  - Verify entries loaded from correct collection

#### 5. Optional Tooling (Nice to Have)

**Goal**: Developer experience improvements

- [ ] CLI tool: `scripts/check_missing_citations.py`
  - Scans markdown file
  - Reports citations NOT in Zotero collection
  - Does NOT auto-add (manual review required)
  - Exit code 1 if missing citations found (for CI)

- [ ] Pre-commit hook: Check no Temp keys in committed .tex files
  ```bash
  if grep -r "Temp[0-9]" output/*.tex; then
    echo "ERROR: Temporary citation keys found"
    exit 1
  fi
  ```

### What We Should NOT Do ❌

Based on codebase architecture and existing working components:

#### 1. Don't Rewrite Working Components

- ❌ **Don't rewrite CitationManager from scratch**
  - Current architecture is correct
  - Only had initialization order bug (now fixed)
  - Extractors already use AST (markdown-it-py)
  - DOI/arXiv extraction already regex-free (uses string methods)

#### 2. Don't Add Automatic Zotero Addition During Conversion

- ❌ **Don't call `zotero_client.add_item_to_collection()` automatically**
  - Conversions should be read-only operations
  - Adding to Zotero requires review (metadata quality)
  - User may not have write permissions
  - Creates race conditions (parallel conversions)

**Instead**: Report missing citations clearly, let user add manually or via separate script

#### 3. Don't Hardcode Collection Name

- ❌ **Don't hardcode "dpp-fashion" in code**
  - Use environment variable: `ZOTERO_COLLECTION`
  - Default can be "dpp-fashion" for convenience
  - But must be configurable for other projects

#### 4. Don't Add New Dependencies Unless Necessary

- ❌ **Don't add `idutils` library**
  - We already have working DOI/arXiv extraction
  - Uses string methods (no regex)
  - One more dependency = one more failure point
  - Current code: `extract_doi_from_url()` in utils.py works fine

#### 5. Don't Create Migration Scripts for Temp Keys

- ❌ **Don't write scripts to replace Temp keys in existing .tex**
  - We're fixing the root cause (no more Temp keys generated)
  - Old outputs should be regenerated, not patched
  - Patching creates technical debt
  - References.bib is GENERATED (deleted every run)

### Priority Order

1. **Validate the fix** (this week)
   - Run test conversion
   - Verify logs and metrics
   - Document results

2. **Remove second pass** (this week)
   - Make `_populate_from_zotero_bibtex()` deprecated
   - Add runtime assertion if entries not loaded

3. **Add unit tests** (next week)
   - Mock Zotero client
   - Test initialization
   - Test matching by DOI/URL/arXiv

4. **Optional tooling** (when needed)
   - CLI checker for missing citations
   - Pre-commit hook for Temp keys

---

## Why This Plan is Minimal and Correct

### We Already Have Most of What We Need

| Component | Status | Notes |
|-----------|--------|-------|
| AST-based Markdown parsing | ✅ Working | Uses markdown-it-py |
| DOI extraction | ✅ Working | `extract_doi_from_url()` in utils.py (no regex) |
| arXiv extraction | ✅ Working | `extract_arxiv_id()` in utils.py (no regex) |
| URL normalization | ✅ Working | `normalize_url()` in utils.py |
| Zotero client | ✅ Working | `ZoteroClient` in zotero_integration.py |
| Zotero loading | ✅ Fixed | Now loads during __init__ |
| DOI/URL matching | ✅ Working | `_lookup_zotero_entry_by_url()` in citation_manager.py |

### What Was Actually Broken

**Only one thing**: Collection name not initialized before CitationManager.__init__

**Fix applied**: Read `ZOTERO_COLLECTION` env var at converter.py:116

**Impact**: ~120 citations will now match on first pass instead of becoming Temp entries

### What We're Removing

**Only one thing**: Redundant second-pass matching at converter.py:910

**Why remove**: Entries now loaded during __init__, so first pass works. Second pass is redundant and confusing.

### Total Code Changes Required

- ✅ **1 line changed**: converter.py:116 (already done)
- ✅ **1 line removed**: converter.py:900 (already done)
- ⏳ **1 method deprecated**: _populate_from_zotero_bibtex() (make NO-OP)
- ⏳ **3 unit tests added**: initialization, matching, env var

**Total**: ~20 lines of code changed, ~100 lines of tests added

This is a **minimal, surgical fix** that solves the root cause without rewriting working components.

---

## Conclusion

**The One Rule**: **Match by DOI/URL/arXiv, USE whatever key Zotero provides.**

Every bug in this session stemmed from violating this rule:
- Trying to validate keys (keys are identity, not validation targets)
- Trying to match during extraction (entries not loaded yet)
- Trying to have dual sources of truth (empty dict vs second pass)
- Reading config at wrong time (after initialization)

**The Fix**: **Load Zotero entries ONCE at startup, match ONCE during extraction.**

If we follow this principle consistently:
- No key format validation needed
- No local key generation needed
- No dual matching passes needed
- No silent failures possible
- 100% reproducible conversions

---

**Author**: Claude Code (with regret and determination)
**Date**: 2025-10-29
**Next Review**: After successful test conversion
**Status**: Ready for validation
