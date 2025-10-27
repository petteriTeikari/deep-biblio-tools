# Fashion Papers Tonight: 4-Hour Conversion Plan

**Created**: 2025-10-27 Evening
**Deadline**: Tonight (4 hours max)
**Goal**: Get all 3 fashion papers converting to PDF with working citations

---

## Reality Check: What We Already Have

✅ **Working MD→LaTeX→PDF pipeline** (mcp-review paper converts perfectly)
✅ **E2E test suite** (22 tests passing, catches (?) citations)
✅ **Zotero integration** (pyzotero with auto-add missing citations)
✅ **Citation extraction** (handles author-year and et al. formats)
✅ **Output cleanup** (prevents stale artifacts)
✅ **Known glitches documented** (in docs/ folder - dollar signs, special chars, etc.)

## What's Actually New

- 3 different papers (but same markdown→PDF workflow)
- Different citation patterns (but extractor should handle)
- Possible math equations ($ might be math, not currency)
- Some table formatting (Pandoc handles this)
- ~300 citations total (but auto-add to Zotero should work)

## 4-Hour Timeline (Realistic)

### Hour 1: Run Conversions & Identify Issues (30 min per paper)

```bash
# Paper 1: fashion-lca-draft-v3.md
cd /Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/fashion_LCA
uv run --project /Users/petteri/Dropbox/github-personal/deep-biblio-tools \
  python -m src.cli md2latex fashion-lca-draft-v3.md \
  --collection dpp-fashion --verbose

# Check output/fashion-lca-draft-v3.pdf for (?) citations
# Note any errors in conversion log

# Paper 2: 4dgs-fashion-comprehensive-v2.md
cd /Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/fashion_4DGS
uv run --project /Users/petteri/Dropbox/github-personal/deep-biblio-tools \
  python -m src.cli md2latex 4dgs-fashion-comprehensive-v2.md \
  --collection dpp-fashion --verbose

# Paper 3: fashion-cad-review-v3.md
cd /Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/fashion_3D_CAD
uv run --project /Users/petteri/Dropbox/github-personal/deep-biblio-tools \
  python -m src.cli md2latex fashion-cad-review-v3.md \
  --collection dpp-fashion --verbose
```

**Expected issues** (from your hints):
1. Some (?) citations (auto-add might not catch all)
2. Math equations breaking ($ interpreted as currency)
3. Table formatting issues (minor, cosmetic)
4. Special characters in citations

**Actions during Hour 1**:
- Count (?) citations in each PDF
- Check LaTeX compilation logs for errors
- Identify patterns in failures (math? tables? citations?)

### Hour 2: Fix Known Glitches (Based on docs/)

**Glitch 1: Dollar Signs** (currency vs math)

From `CLAUDE.md`: "NEVER convert $50-200 to LaTeX math mode"

**Problem**: Converter escapes ALL $ as `\$`, breaking math equations
**Solution**: Detect math context (inline: `$E=mc^2$`, block: `$$...$$`)

```python
# Quick fix in converter.py
def escape_dollar_signs(text: str) -> str:
    """Escape currency dollars but preserve math dollars"""
    # Regex to detect math: $...$ (inline) or $$...$$ (block)
    # For tonight: Simple heuristic - if $ followed by letter/backslash, it's math
    # If followed by digit, it's currency

    import re

    # Block math: $$...$$ - don't escape
    text = re.sub(r'\$\$(.*?)\$\$', r'BLOCKMATH\1BLOCKMATH', text, flags=re.DOTALL)

    # Inline math: $...$ with LaTeX commands or symbols - don't escape
    text = re.sub(r'\$([^$]*?\\[a-zA-Z]+.*?)\$', r'INLINEMATH\1INLINEMATH', text)

    # Now escape remaining $ (currency)
    text = text.replace('$', '\\$')

    # Restore math
    text = text.replace('BLOCKMATH', '$$')
    text = text.replace('INLINEMATH', '$')

    return text
```

**Glitch 2: Special Characters in Author Names**

From docs: "Author names with accents (ü, é, etc.)"

**Solution**: Already handled by BibTeX encoding, verify it works

**Glitch 3: Et al. Citations**

From `CLAUDE.md`: "TREAT all 'et al' as requiring full author lookup"

**Solution**: Already implemented, should work. If not, check logs.

### Hour 3: Iteration & Citation Resolution

**For each paper with (?) citations**:

1. **Check references.bib** for "Unknown" or "Anonymous" entries
2. **Review LaTeX log** for BibTeX warnings
3. **Manually check first 5 (?) citations** - are they in Zotero?
4. **If auto-add failed**: Check why (DOI lookup? arXiv lookup?)
5. **Quick fix**: Add missing citations manually to Zotero web interface
6. **Re-run conversion**

**Optimization**: Don't fix ALL (?) citations tonight
- Goal: Verify pipeline WORKS, not perfect output
- If auto-add catches 80%+ citations → GOOD ENOUGH for tonight
- Remaining (?) can be fixed later (not blocking)

### Hour 4: E2E Tests & Documentation

**Run E2E tests on new papers**:

```bash
# Quick test: Just check (?) count in PDFs
pytest tests/e2e/test_fashion_papers.py -v --tb=short -k "zero_unresolved"
```

**Expected result**: Tests FAIL with some (?) citations (acceptable for tonight)

**Document what worked/didn't**:
```bash
# Create quick summary
cat > conversion-summary-$(date +%Y%m%d).txt <<EOF
Fashion Papers Conversion Summary - $(date)

Paper 1: fashion-lca-draft-v3.md
  Status: PDF generated ✓
  (?) citations: X
  Issues: [list any]

Paper 2: 4dgs-fashion-comprehensive-v2.md
  Status: PDF generated ✓
  (?) citations: Y
  Issues: [list any]

Paper 3: fashion-cad-review-v3.md
  Status: PDF generated ✓
  (?) citations: Z
  Issues: [list any]

Total time: ~4 hours
Next steps: [Fix remaining citations / Math equation handling / Table formatting]
EOF
```

---

## MCP Integration (The "Must-Have")

**Your point**: "MCP is a must for everything as this is also a MCP practice"

**Pragmatic approach for tonight**:

1. **Keep current Zotero integration** (pyzotero direct) - it works!
2. **Create MCP server wrapper TOMORROW** - don't block tonight's conversions
3. **MCP server = thin wrapper around existing code** - should take 2-3 hours max

**Why this makes sense**:
- MCP server doesn't change the LOGIC (that already works)
- MCP server is just a PROTOCOL wrapper (stdio, tools, resources)
- Conversions working tonight → MCP wrapper tomorrow → Done by Week 1

**MCP Server Tomorrow (2-3 hours)**:
```
Hour 1: Create mcp-servers/zotero/ structure
Hour 2: Wrap existing zotero_integration.py methods as MCP tools
Hour 3: Test MCP server with md2latex converter, compare with direct calls
```

---

## Known Glitches from docs/ (Quick Reference)

From reading the docs/ folder history:

### 1. Unicode Citation Keys (FIXED)
- **Issue**: BibTeX keys with special characters broke compilation
- **Fix**: ASCII normalization in citation key generation
- **File**: `docs/fix-plan-unicode-citation-keys.md`

### 2. Dollar Sign Escaping (NEEDS CHECK)
- **Issue**: $50-200 converted to math mode
- **Fix**: Smart detection (currency vs math)
- **CLAUDE.md**: "NEVER convert $50-200 to LaTeX math mode"

### 3. Citation Format Variations (HANDLED)
- **Issue**: Multiple formats: [Author (Year)], [Author et al., Year]
- **Fix**: Unified extractor handles both
- **File**: `citation_extractor_unified.py`

### 4. Hyperlink vs Citation (FIXED)
- **Issue**: Regular hyperlinks treated as citations
- **Fix**: Must have year in brackets to be citation
- **CLAUDE.md**: "Hyperlink vs Citation Format (CRITICAL)"

### 5. Comma-Separated Citations (FIXED)
- **Issue**: [Author1, 2020; Author2, 2021] not parsed
- **Fix**: Semicolon splitting implemented
- **Commit**: `34085cf fix: Support comma format citations`

### 6. Zotero Collection Management (WORKING)
- **Issue**: Items added to wrong collection
- **Fix**: `ZOTERO_COLLECTION` env var
- **Status**: Should work with dpp-fashion collection

---

## Realistic Success Criteria (Tonight)

### Must Have (4-Hour Goal)
1. ✅ All 3 papers generate PDFs (even with some (?))
2. ✅ LaTeX compiles without ERRORS (warnings OK)
3. ✅ Each paper has output/ folder with .tex, .pdf, .bib
4. ✅ ≥80% citations resolved (some (?) acceptable)

### Should Have (If Time Permits)
1. ⚠️ Math equations render correctly (might need fix)
2. ⚠️ Tables look decent (Pandoc usually handles this)
3. ⚠️ ≥90% citations resolved

### Don't Need Tonight (Future Work)
1. ❌ 100% citation resolution (can fix manually later)
2. ❌ Perfect table formatting (cosmetic)
3. ❌ MCP server wrapper (tomorrow's 2-hour task)
4. ❌ Publication-ready content (separate task)

---

## Potential Surprises & Quick Fixes

### Surprise 1: Math Equations Break Compilation

**Symptom**: LaTeX error: "Missing $ inserted"
**Cause**: Inline math $E=mc^2$ got escaped to \$E=mc^2\$

**Quick Fix**:
```python
# In converter.py, improve escape_special_chars()
# Check if $ is followed by backslash or letter → likely math
# Only escape $ followed by digit → likely currency
```

### Surprise 2: Citation Extraction Misses New Pattern

**Symptom**: Many (?) citations, but citations look correct in markdown
**Cause**: New citation format not recognized by extractor

**Quick Fix**:
```python
# Check markdown for actual citation pattern
# Update citation_extractor_unified.py regex if needed
# Example: [Author, A., Author, B. (2020)] might need handling
```

### Surprise 3: Zotero API Rate Limiting

**Symptom**: "429 Too Many Requests" error
**Cause**: Auto-adding 100+ citations hits rate limit

**Quick Fix**:
```python
# Add sleep between API calls
import time
time.sleep(0.5)  # 500ms between requests
```

### Surprise 4: Table Markdown Not Converting

**Symptom**: Tables appear as raw markdown in PDF
**Cause**: Pandoc needs specific table syntax

**Quick Fix**:
```bash
# Check if tables use correct markdown syntax
# If not, might need to fix in markdown source
# For tonight: Skip table fixes, focus on citations
```

---

## Execution Checklist

- [ ] **Hour 1**: Run all 3 conversions, collect logs
- [ ] **Hour 1**: Count (?) citations in each PDF
- [ ] **Hour 1**: Check LaTeX logs for ERRORS (not warnings)
- [ ] **Hour 2**: Fix math equation escaping if broken
- [ ] **Hour 2**: Check if citation extraction missed patterns
- [ ] **Hour 2**: Re-run conversions with fixes
- [ ] **Hour 3**: Review top 10 (?) citations per paper
- [ ] **Hour 3**: Quick Zotero additions if auto-add failed
- [ ] **Hour 3**: Final conversion run
- [ ] **Hour 4**: Run E2E tests (expect some failures - OK)
- [ ] **Hour 4**: Document results and next steps
- [ ] **Hour 4**: Commit working conversions

---

## Quick Command Reference

```bash
# Convert single paper
uv run python -m src.cli md2latex <file.md> --collection dpp-fashion --verbose

# Check PDF for (?) citations
fdfind "\(\?\)" output/<paper>.pdf  # Should return count

# Count citations in markdown
grep -oP '\[.*?\]\(http' <file.md> | wc -l

# Check LaTeX log for errors
grep -i "error" output/<paper>.log

# Run E2E tests
pytest tests/e2e/ -v --tb=short -k "fashion"

# Check references.bib for Unknown
grep -i "unknown\|anonymous" output/references.bib
```

---

## Tomorrow's 2-Hour MCP Wrapper Task

**Don't do tonight** - conversions are priority

```
Hour 1: Create mcp-servers/zotero/__main__.py
  - stdio_server setup
  - Register tools from existing zotero_integration.py

Hour 2: Update md2latex converter to use MCP client
  - Replace direct pyzotero calls with MCP tool calls
  - Test: conversion results should be identical
```

**MCP is just a protocol wrapper** - doesn't change the working logic!

---

## Let's Go! Start with Paper 1

Ready to start Hour 1? Let's run the first conversion and see what happens!

```bash
cd /Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/fashion_LCA
uv run --project /Users/petteri/Dropbox/github-personal/deep-biblio-tools \
  python -m src.cli md2latex fashion-lca-draft-v3.md \
  --collection dpp-fashion --verbose 2>&1 | tee conversion-lca.log
```

**This should work!** The infrastructure is solid. Let's find out what (if anything) breaks and fix it fast.
