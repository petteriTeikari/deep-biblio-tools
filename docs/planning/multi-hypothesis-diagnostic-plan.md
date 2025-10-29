# Multi-Hypothesis Diagnostic Plan for Citation Replacement Failure

**Date**: 2025-10-27
**Approach**: Systematically test ALL plausible hypotheses, assuming multiple bugs may co-occur
**Status**: 🔬 READY FOR SYSTEMATIC TESTING

---

## Overview: 5 Competing Hypotheses

Based on comprehensive codebase analysis, we have identified **5 distinct failure modes** that could be occurring independently or simultaneously:

| ID | Hypothesis | Likelihood | Test Complexity |
|----|-----------|------------|-----------------|
| H1 | `self.citations` dict empty/wrong keys at replacement time | 70% | Easy |
| H2 | URL normalization mismatch (arxiv vs general) | 85% | Medium |
| H3 | Token rendering loses replacements after mutation | 95% | Medium |
| H4 | Citation key lookup fails silently (confirmed happening) | 100% | Easy |
| H5 | Better BibTeX key regeneration timing issue | 30% | Medium |

**Strategy**: Test each hypothesis independently with targeted logging, then test combined fixes.

---

## Test Suite: One Test Per Hypothesis

### Test H1: Is `self.citations` Dict Populated?

**File to Modify**: `src/converters/md_to_latex/citation_manager.py`

**Add at line 1204 (inside `replace_citations_in_text_ast()`):**

```python
def replace_citations_in_text_ast(self, content: str) -> tuple[str, int]:
    """Replace markdown citations with LaTeX cite commands using AST parsing."""

    # H1 TEST: Check if self.citations is populated
    logger.error(f"[H1-TEST] self.citations dict has {len(self.citations)} entries")
    if len(self.citations) == 0:
        logger.error("[H1-TEST] CRITICAL: self.citations is EMPTY - no replacements possible")
    else:
        sample_keys = list(self.citations.keys())[:5]
        logger.error(f"[H1-TEST] Sample keys: {sample_keys}")
        sample_urls = [self.citations[k].url for k in sample_keys]
        logger.error(f"[H1-TEST] Sample URLs: {sample_urls}")

    # Continue with existing code...
    url_to_key = self._build_normalized_url_lookup()
```

**Expected Outcomes**:
- ✅ **PASS**: Dict has 40+ entries with valid keys and URLs
- ❌ **FAIL**: Dict is empty (0 entries)
- ⚠️ **PARTIAL**: Dict has entries but URLs don't look right

**Action if Failed**: Add population code before calling replacement in converter.py:1141

---

### Test H2: URL Normalization Consistency

**File to Modify**: `src/converters/md_to_latex/citation_manager.py`

**Add at line 1183 (inside `_build_normalized_url_lookup()`):**

```python
def _build_normalized_url_lookup(self) -> dict[str, str]:
    """Build a lookup map from normalized URLs to citation keys."""
    lookup = {}

    # H2 TEST: Track normalization inconsistencies
    normalization_log = []

    for key, citation in self.citations.items():
        if not citation.url.startswith("#orphan-"):
            original_url = citation.url

            # Test BOTH normalization paths
            arxiv_normalized = normalize_arxiv_url(original_url)
            general_normalized = normalize_url(original_url)

            # Log if they differ
            if arxiv_normalized != general_normalized:
                normalization_log.append({
                    "key": key,
                    "original": original_url,
                    "arxiv_norm": arxiv_normalized,
                    "general_norm": general_normalized,
                    "stored_in_citation": citation.url
                })

            # Use the same logic as extraction (arxiv first, then general)
            normalized = normalize_url(normalize_arxiv_url(original_url))

            if normalized in lookup:
                logger.warning(
                    f"URL collision: {normalized} maps to both {key} and {lookup[normalized]}"
                )
            lookup[normalized] = key

    if normalization_log:
        logger.error(f"[H2-TEST] Found {len(normalization_log)} URLs with different normalizations")
        for item in normalization_log[:3]:
            logger.error(f"[H2-TEST] {item}")
    else:
        logger.error("[H2-TEST] All URLs normalize consistently")

    logger.info(f"Built normalized URL lookup with {len(lookup)} entries")
    return lookup
```

**Expected Outcomes**:
- ✅ **PASS**: No URLs with different normalizations
- ❌ **FAIL**: arXiv URLs normalize differently, causing lookup mismatches
- ⚠️ **PARTIAL**: Some URLs affected but not all

**Action if Failed**: Apply consistent normalization (arxiv → general) in lookup building

---

### Test H3: Token Rendering Completeness

**File to Modify**: `src/converters/md_to_latex/citation_manager.py`

**Replace lines 1286-1315 with instrumented version:**

```python
# H3 TEST: Track which rendering path is used
logger.error("[H3-TEST] Starting token rendering")

# Manual token extraction
output_parts = []
token_types_seen = set()
citations_in_tokens = 0

for token in tokens:
    token_types_seen.add(token.type)

    if token.type == "text":
        output_parts.append(token.content)
        # Check if this is a citation we inserted
        if "\\citep{" in token.content:
            citations_in_tokens += 1
    elif token.type == "inline" and token.children:
        for child in token.children:
            token_types_seen.add(child.type)
            if child.type == "text":
                output_parts.append(child.content)
                if "\\citep{" in child.content:
                    citations_in_tokens += 1
    elif hasattr(token, "content") and token.content:
        output_parts.append(token.content)

manual_output = "".join(output_parts)
manual_length = len(manual_output.strip())
original_length = len(content)

logger.error(f"[H3-TEST] Token types encountered: {token_types_seen}")
logger.error(f"[H3-TEST] Citations in extracted tokens: {citations_in_tokens}")
logger.error(f"[H3-TEST] Manual extraction: {manual_length} chars (original: {original_length})")
logger.error(f"[H3-TEST] Extraction ratio: {manual_length/original_length:.2%}")

# CRITICAL: Check if we should use fallback
use_fallback = not output_parts or manual_length < original_length // 2

if use_fallback:
    logger.error(f"[H3-TEST] USING FALLBACK RENDERER (manual extraction insufficient)")
    output = md.renderer.render(tokens, md.options, {})
    logger.error(f"[H3-TEST] Fallback output length: {len(output)} chars")
    # Check if citations survived
    fallback_citations = output.count("\\citep{")
    logger.error(f"[H3-TEST] Citations in fallback output: {fallback_citations}")
else:
    logger.error(f"[H3-TEST] USING MANUAL EXTRACTION (sufficient)")
    output = manual_output
```

**Expected Outcomes**:
- ✅ **PASS**: Manual extraction works, citations preserved
- ❌ **FAIL H3a**: Fallback renderer used, citations lost
- ❌ **FAIL H3b**: Manual extraction incomplete (many token types missing)
- ❌ **FAIL H3c**: Citations inserted but then lost during rendering

**Action if Failed**:
- If H3a: Fix renderer to preserve LaTeX citations
- If H3b: Use renderer always, don't do manual extraction
- If H3c: Check token insertion logic

---

### Test H4: Citation Key Lookup Success Rate

**File to Modify**: `src/converters/md_to_latex/citation_manager.py`

**Add comprehensive logging at lines 1220-1280:**

```python
# H4 TEST: Track all lookup attempts
logger.error(f"[H4-TEST] Starting citation replacement with {len(url_to_key)} URLs in lookup")

replaced_count = 0
failed_urls = []
lookup_attempts = []

# Walk tokens...
i = 0
while i < len(tokens):
    token = tokens[i]
    if token.type == "link_open":
        # Extract href
        href = None
        for attr in token.attrs or []:
            if attr[0] == "href":
                href = attr[1]
                break

        if href:
            # H4 TEST: Log every lookup attempt
            original_href = href
            normalized_href = normalize_url(href)
            key = url_to_key.get(normalized_href)

            lookup_attempts.append({
                "original": original_href,
                "normalized": normalized_href,
                "found_key": key,
                "success": key is not None
            })

            if key:
                # SUCCESS - log and replace
                logger.debug(f"[H4-TEST] ✓ Match: {original_href} → {key}")
                # ... replacement code ...
                replaced_count += 1
            else:
                # FAILURE - log details
                logger.warning(f"[H4-TEST] ✗ No match: {original_href}")
                logger.warning(f"[H4-TEST]   Normalized to: {normalized_href}")
                logger.warning(f"[H4-TEST]   Available keys: {list(url_to_key.keys())[:5]}...")
                failed_urls.append(href)

# Summary
logger.error(f"[H4-TEST] Lookup attempts: {len(lookup_attempts)}")
logger.error(f"[H4-TEST] Successful: {replaced_count}")
logger.error(f"[H4-TEST] Failed: {len(failed_urls)}")

if failed_urls:
    logger.error(f"[H4-TEST] First 3 failed URLs:")
    for url in failed_urls[:3]:
        logger.error(f"[H4-TEST]   - {url}")
```

**Expected Outcomes**:
- ✅ **PASS**: 100% lookup success rate
- ❌ **FAIL H4a**: 0% success - lookup table empty or wrong
- ❌ **FAIL H4b**: Partial success - some URLs match, some don't
- ❌ **FAIL H4c**: Normalized URLs don't match lookup table keys

**Action if Failed**:
- If H4a: Check H1 (dict population)
- If H4b: Check H2 (normalization mismatch)
- If H4c: Log both sides of lookup for comparison

---

### Test H5: Better BibTeX Key Timing

**File to Modify**: `src/converters/md_to_latex/converter.py`

**Add at multiple checkpoints:**

```python
# CHECKPOINT 1: After extraction (line 863)
citations = self.citation_manager.extract_citations(content)
logger.error(f"[H5-TEST-CP1] After extraction: {len(citations)} citations")
logger.error(f"[H5-TEST-CP1] self.citations dict has {len(self.citation_manager.citations)} keys")
sample_keys_cp1 = list(self.citation_manager.citations.keys())[:3]
logger.error(f"[H5-TEST-CP1] Sample keys: {sample_keys_cp1}")

# CHECKPOINT 2: After Zotero matching (line 922)
logger.error(f"[H5-TEST-CP2] After Zotero matching:")
logger.error(f"[H5-TEST-CP2] self.citations dict has {len(self.citation_manager.citations)} keys")
sample_keys_cp2 = list(self.citation_manager.citations.keys())[:3]
logger.error(f"[H5-TEST-CP2] Sample keys: {sample_keys_cp2}")
if sample_keys_cp1 != sample_keys_cp2:
    logger.error("[H5-TEST-CP2] KEYS CHANGED after Zotero matching!")

# CHECKPOINT 3: After metadata fetching (line 1032)
logger.error(f"[H5-TEST-CP3] After metadata fetching:")
logger.error(f"[H5-TEST-CP3] self.citations dict has {len(self.citation_manager.citations)} keys")
sample_keys_cp3 = list(self.citation_manager.citations.keys())[:3]
logger.error(f"[H5-TEST-CP3] Sample keys: {sample_keys_cp3}")
if sample_keys_cp2 != sample_keys_cp3:
    logger.error("[H5-TEST-CP3] KEYS CHANGED after metadata fetching!")

# CHECKPOINT 4: Just before replacement (line 1140)
logger.error(f"[H5-TEST-CP4] Before replacement:")
logger.error(f"[H5-TEST-CP4] self.citations dict has {len(self.citation_manager.citations)} keys")
sample_keys_cp4 = list(self.citation_manager.citations.keys())[:3]
logger.error(f"[H5-TEST-CP4] Sample keys: {sample_keys_cp4}")
if sample_keys_cp3 != sample_keys_cp4:
    logger.error("[H5-TEST-CP4] KEYS CHANGED between metadata and replacement!")
```

**Expected Outcomes**:
- ✅ **PASS**: Keys stay consistent across all checkpoints
- ❌ **FAIL H5a**: Keys change after Zotero matching
- ❌ **FAIL H5b**: Keys change after metadata fetching
- ❌ **FAIL H5c**: Keys change between metadata and replacement
- ⚠️ **PARTIAL**: Dict shrinks (keys deleted but not added)

**Action if Failed**: Fix the timing of lookup table rebuilding

---

## Execution Plan

### Phase 1: Add All Test Instrumentation (30 min)

1. Add H1 test to `citation_manager.py` line 1204
2. Add H2 test to `citation_manager.py` line 1183
3. Add H3 test to `citation_manager.py` lines 1286-1315
4. Add H4 test to `citation_manager.py` lines 1220-1280
5. Add H5 test to `converter.py` at 4 checkpoints
6. Run linters to ensure no syntax errors

### Phase 2: Run Single Test Conversion (15 min)

```bash
cd /Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/fashion_3D_CAD
uv run --project /Users/petteri/Dropbox/github-personal/deep-biblio-tools \
  python -m src.cli md2latex fashion-cad-review-v3.md -c dpp-fashion \
  2>&1 | tee /tmp/multi-hypothesis-test.log
```

### Phase 3: Analyze Results (20 min)

Extract test results:
```bash
grep "\[H1-TEST\]" /tmp/multi-hypothesis-test.log
grep "\[H2-TEST\]" /tmp/multi-hypothesis-test.log
grep "\[H3-TEST\]" /tmp/multi-hypothesis-test.log
grep "\[H4-TEST\]" /tmp/multi-hypothesis-test.log
grep "\[H5-TEST\]" /tmp/multi-hypothesis-test.log
```

Create results matrix:

| Test | Result | Evidence |
|------|--------|----------|
| H1: Dict populated? | PASS/FAIL | # entries, sample keys |
| H2: URL normalization? | PASS/FAIL | # mismatches |
| H3: Token rendering? | PASS/FAIL | Which path used, citations preserved? |
| H4: Lookup success? | PASS/FAIL | Success rate % |
| H5: Key timing? | PASS/FAIL | Keys changed at which checkpoint? |

### Phase 4: Prioritized Fixes (Variable)

Based on test results, apply fixes in priority order:

1. **If H3 fails** (token rendering): Fix first - this loses data even if everything else works
2. **If H2 fails** (URL normalization): Fix second - this prevents lookups from working
3. **If H1 fails** (dict empty): Fix third - nothing works without data
4. **If H5 fails** (key timing): Fix fourth - causes intermittent failures
5. **H4 should pass** once H1-H3 are fixed

### Phase 5: Verify Each Fix Independently (15 min per fix)

After each fix:
1. Re-run test conversion
2. Check if that specific hypothesis now passes
3. Verify other tests still pass (no regressions)
4. Commit the specific fix with evidence

### Phase 6: Final Integration Test (30 min)

Run all 4 markdown files through conversion:
1. fashion-cad-review-v3.md
2. 4dgs-fashion-comprehensive-v2.md
3. fashion-lca-draft-v3.md
4. mcp-draft-refined-v4.md

For each, verify:
- .tex file has `\citep{}` commands
- .tex file has NO markdown links `[...](...)`
- .aux file has `\citation{key}` entries
- PDF compiles without errors
- PDF has ZERO (?) citations

---

## Test Results Template

```markdown
## Test Execution Results: [DATE/TIME]

### H1: Dict Population
- **Status**: PASS / FAIL / PARTIAL
- **Evidence**:
  - Dict size: [N] entries
  - Sample keys: [...]
  - Sample URLs: [...]
- **Conclusion**: [WORKING / BROKEN / NEEDS FIX]

### H2: URL Normalization
- **Status**: PASS / FAIL / PARTIAL
- **Evidence**:
  - Inconsistencies found: [N]
  - Example mismatches: [...]
- **Conclusion**: [WORKING / BROKEN / NEEDS FIX]

### H3: Token Rendering
- **Status**: PASS / FAIL / PARTIAL
- **Evidence**:
  - Rendering path used: MANUAL / FALLBACK
  - Citations in tokens: [N]
  - Citations in output: [N]
  - Token types seen: [...]
- **Conclusion**: [WORKING / BROKEN / NEEDS FIX]

### H4: Lookup Success Rate
- **Status**: PASS / FAIL / PARTIAL
- **Evidence**:
  - Total attempts: [N]
  - Successful: [N] ([X]%)
  - Failed: [N] ([X]%)
  - Failed URLs: [...]
- **Conclusion**: [WORKING / BROKEN / NEEDS FIX]

### H5: Key Timing
- **Status**: PASS / FAIL / PARTIAL
- **Evidence**:
  - CP1 keys: [...]
  - CP2 keys: [...]
  - CP3 keys: [...]
  - CP4 keys: [...]
  - Changes detected at: [checkpoint]
- **Conclusion**: [WORKING / BROKEN / NEEDS FIX]

### Overall Assessment
- **Root Causes Identified**: [list]
- **Fixes Required**: [prioritized list]
- **Estimated Fix Time**: [hours]
- **Risk Level**: [LOW / MEDIUM / HIGH]
```

---

## Next Steps

1. **Get User Approval**: Confirm this systematic approach before adding instrumentation
2. **Add All Tests**: Implement all 5 hypothesis tests in one go
3. **Run Single Conversion**: Get comprehensive diagnostic output
4. **Analyze Results**: Fill out results template
5. **Fix Issues**: Address root causes in priority order
6. **Verify**: Confirm all 4 test files convert correctly

**Estimated Total Time**: 3-4 hours for complete diagnosis and fixes

---

## Notes

### Why Test All Hypotheses Together?

1. **Multiple bugs may co-occur**: Fixing one won't help if others are also broken
2. **Interaction effects**: Some bugs may mask others
3. **Efficient debugging**: Get all evidence in one test run
4. **No false confidence**: Don't claim success after fixing just one issue

### Why This Approach is Better

- ✅ **Evidence-based**: Every conclusion backed by logged data
- ✅ **Systematic**: All possibilities tested, not just first guess
- ✅ **Reproducible**: Clear test protocol anyone can follow
- ✅ **Comprehensive**: Won't miss co-occurring bugs
- ✅ **Auditable**: Full diagnostic log for future reference

---

## Success Criteria (Unchanged from CLAUDE.md)

The ONLY measure of success:

1. ✅ PDF generates without LaTeX errors
2. ✅ PDF has ZERO (?) citations
3. ✅ PDF has ZERO (Unknown) citations
4. ✅ All citations show proper author names and years
5. ✅ references.bib has ZERO "Unknown" entries
6. ✅ LaTeX log has ZERO compilation errors
7. ✅ BibTeX log has ZERO fatal errors

**Process**: Run conversion → Read PDF → Verify EVERY citation → ONLY THEN claim success
