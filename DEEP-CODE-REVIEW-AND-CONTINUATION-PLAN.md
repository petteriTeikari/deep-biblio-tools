# Deep Code Review & Continuation Plan
**Date:** 2025-10-27
**Branch:** `fix/verify-md-to-latex-conversion`
**Context:** Last 6 hours of development work

---

## Executive Summary

### ✅ Recent Achievements (Last 6 Hours)
1. **Regression Test Suite** - 16/16 tests passing for 4 papers with zero missing citations
2. **MCP Citation Quality Server** - Full audit tool with URL categorization
3. **Golden Dataset** - Deterministic test fixtures (384 KB manuscripts + 25.4 KB bibliography)
4. **Better BibTeX Integration** - Verified working correctly from Zotero exports
5. **--audit Flag** - Pre-conversion citation quality checking in CLI

### 🔍 Code Health Status
- **Linting:** ✅ Zero ruff errors
- **Tests:** ✅ 398 tests collected, regression suite passing
- **Type Safety:** ⚠️ Not systematically enforced (no mypy)
- **Documentation:** ⚠️ Inconsistent docstrings
- **Technical Debt:** ⚠️ 50+ TODOs, debug code in production

---

## 🐛 Critical Issues Found

### 1. Debug Code in Production (HIGH PRIORITY)
**Location:** `src/converters/md_to_latex/citation_manager.py:1272-1372`

```python
# H4 DEBUG: Log token structure to understand nesting
logger.error(f"[H4-DEBUG] Token structure: {token_types_found}")
logger.error(f"[H4-DEBUG] Links processed: {links_processed}")
```

**Problem:** Using `logger.error()` for debug messages pollutes error logs.

**Fix Required:**
```python
# Change to logger.debug() and remove H4 prefix
logger.debug(f"Token structure: {token_types_found}")
logger.debug(f"Links processed: {links_processed}")
```

**Impact:** Medium - Makes actual errors harder to find in logs.

---

### 2. Incomplete MCP Tool Implementations (MEDIUM PRIORITY)
**Locations:**
- `mcp_servers/citation_quality/tools/zotero_match.py:32`
- `mcp_servers/citation_quality/tools/bibtex_keys.py:31`
- `mcp_servers/zotero/src/zotero/server.py:170,179,221`

**Problem:** Stub implementations with TODO comments.

```python
# TODO: Import and use CitationManager from src/
return {
    "found_in_zotero": False,
    "better_bibtex_key": None,
    "metadata": {},
    "message": "Zotero integration not yet implemented",
}
```

**Fix Required:**
1. Import `CitationManager` from `src/converters/md_to_latex/citation_manager.py`
2. Implement actual Zotero matching logic
3. Add tests for MCP tools

**Impact:** Medium - MCP tools partially functional but incomplete.

---

### 3. Inconsistent Error Handling
**Location:** Multiple files use different error patterns

**Examples:**
```python
# Pattern 1: sys.exit(1)
if not valid:
    click.echo("Error!", err=True)
    sys.exit(1)

# Pattern 2: raise exceptions
if not valid:
    raise ValueError("Error!")

# Pattern 3: return error codes
if not valid:
    return 1
```

**Fix Required:** Standardize on exceptions with proper error hierarchy:
```python
class DeepBiblioError(Exception):
    """Base exception for deep-biblio-tools."""

class ValidationError(DeepBiblioError):
    """Raised when validation fails."""

class ConversionError(DeepBiblioError):
    """Raised when conversion fails."""
```

**Impact:** Low - Works but inconsistent developer experience.

---

### 4. Missing Type Annotations
**Location:** Many functions lack type hints

**Example from `src/converters/md_to_latex/utils.py`:
```python
# Current
def parse_bibtex_entries(bibtex_content):
    """Parse BibTeX content."""

# Should be
def parse_bibtex_entries(bibtex_content: str) -> dict[str, dict]:
    """Parse BibTeX content and return entry dict."""
```

**Fix Required:**
1. Add type annotations to all public functions
2. Enable `mypy` in pre-commit hooks
3. Add `py.typed` marker for library usage

**Impact:** Low - Runtime works but IDE support suffers.

---

### 5. Golden Dataset Missing Expected Outputs
**Location:** `tests/fixtures/golden/expected_outputs/` (empty)

**Problem:** User noted expected outputs should include:
- `.tex` files
- `.pdf` files
- `.bbl` files (BibTeX processed bibliography)
- `_refs.bib` files (subset of references actually cited)

**Fix Required:**
1. Run conversion for all 4 papers
2. Manually verify PDFs have zero (?) citations
3. Copy outputs to `expected_outputs/`
4. Update tests to use golden fixtures instead of live files

**Impact:** Medium - Can't use golden dataset for deterministic testing yet.

---

## 🔧 Technical Debt Items

### Priority 1 (Do Next)
1. **Populate Golden Dataset Outputs** - Complete the dataset for deterministic testing
2. **Clean Up Debug Code** - Remove H4-DEBUG and switch to proper logging
3. **Implement MCP Tool Stubs** - Complete Zotero matching functionality

### Priority 2 (Within 1-2 Weeks)
4. **Add Type Annotations** - Start with most-used modules
5. **Standardize Error Handling** - Create exception hierarchy
6. **Document Citation Pipeline** - Add architecture diagram
7. **Add Coverage Reporting** - Know what's tested vs untested

### Priority 3 (Nice to Have)
8. **Remove Archive Scripts** - Clean up `scripts/archive/` (13 old scripts)
9. **Add Performance Benchmarks** - Track conversion speed over time
10. **CI/CD Pipeline** - Auto-run regression tests on PRs

---

## 📋 Continuation Plan (Next Session)

### Phase 1: Complete Golden Dataset (1-2 hours)
**Goal:** Make golden dataset fully functional for deterministic testing

**Steps:**
1. ✅ **Already Done:**
   - 4 manuscripts copied to `tests/fixtures/golden/manuscripts/`
   - Zotero snapshot exported to `bibliography/dpp-fashion-snapshot.bib`
   - Comprehensive README written

2. 🔲 **To Do:**
   - Run conversion for all 4 papers:
     ```bash
     for paper in fashion_4DGS fashion_3D_CAD fashion_LCA mcp_review; do
       uv run python -m src.cli md2latex \
         tests/fixtures/golden/manuscripts/${paper}.md \
         -o tests/fixtures/golden/expected_outputs/${paper}.tex
     done
     ```

   - Verify each PDF manually:
     ```bash
     # Use Read tool to check for (?) citations
     # Look for Unknown/Anonymous in references
     ```

   - Extract subset BibTeX for each paper:
     ```python
     # Create script to extract only cited entries
     # Input: references.bib (full), paper.tex
     # Output: paper_refs.bib (subset)
     ```

   - Copy `.bbl` files from LaTeX output

   - Update test suite to use golden fixtures:
     ```python
     # Change from live paths to:
     PAPERS = [
         "tests/fixtures/golden/manuscripts/fashion_4DGS.md",
         ...
     ]
     ```

**Acceptance Criteria:**
- [ ] All 4 papers in `expected_outputs/` with `.tex`, `.pdf`, `.bbl`, `_refs.bib`
- [ ] Manual verification confirms zero (?) citations
- [ ] Test suite runs without network/Zotero API access
- [ ] README updated with "Dataset Complete" status

**Why Important:** Enables truly deterministic regression testing without external dependencies.

---

### Phase 2: Clean Production Code (1 hour)
**Goal:** Remove debug code and improve code quality

**Steps:**
1. 🔲 **Fix Debug Logging:**
   ```bash
   # Find all H4-DEBUG lines
   grep -r "H4-DEBUG" src/

   # Replace with proper debug logging
   sed -i '' 's/logger.error.*H4-DEBUG/logger.debug/g' \
     src/converters/md_to_latex/citation_manager.py
   ```

2. 🔲 **Review All TODOs:**
   ```bash
   # List all TODOs by priority
   grep -rn "TODO" src/ mcp_servers/ | \
     grep -v "test" | \
     sort > TODO-AUDIT.txt
   ```

   - Mark critical TODOs for immediate action
   - Create GitHub issues for non-critical items
   - Remove stale/obsolete TODOs

3. 🔲 **Standardize Error Handling:**
   - Create `src/exceptions.py` with exception hierarchy
   - Replace `sys.exit(1)` with proper exceptions in library code
   - Keep `sys.exit()` only in CLI entry points

**Acceptance Criteria:**
- [ ] Zero `logger.error()` calls for debug messages
- [ ] All critical TODOs resolved or have GitHub issues
- [ ] Exception hierarchy documented in `docs/EXCEPTIONS.md`

---

### Phase 3: Complete MCP Tools (2-3 hours)
**Goal:** Finish incomplete MCP tool implementations

**Steps:**
1. 🔲 **Implement `verify_zotero_match` Tool:**
   ```python
   # mcp_servers/citation_quality/tools/zotero_match.py

   from src.converters.md_to_latex.citation_manager import CitationManager
   from src.converters.md_to_latex.zotero_integration import ZoteroClient

   async def verify_zotero_match(
       url: str, citation_text: str, collection: str | None = None
   ) -> dict[str, Any]:
       """Check if citation exists in Zotero."""

       # 1. Parse citation text to extract author/year
       # 2. Search Zotero collection for matching entry
       # 3. Compare metadata (author names, year, title)
       # 4. Return validation result
   ```

2. 🔲 **Implement `get_bibtex_keys` Tool:**
   ```python
   # mcp_servers/citation_quality/tools/bibtex_keys.py

   async def get_bibtex_keys(collection: str) -> dict[str, Any]:
       """Get all Better BibTeX keys from collection."""

       # 1. Fetch collection from Zotero API
       # 2. Extract citation keys from BibTeX export
       # 3. Return key → metadata mapping
   ```

3. 🔲 **Add Tests for MCP Tools:**
   ```python
   # tests/mcp_servers/test_zotero_match.py

   @pytest.mark.asyncio
   async def test_verify_zotero_match_found():
       result = await verify_zotero_match(
           url="https://arxiv.org/abs/2024.12345",
           citation_text="Smith et al., 2024",
           collection="test-collection"
       )
       assert result["found_in_zotero"] is True
       assert result["better_bibtex_key"] == "smithExamplePaper2024"
   ```

**Acceptance Criteria:**
- [ ] `verify_zotero_match` returns real data, not stubs
- [ ] `get_bibtex_keys` fetches actual keys from Zotero
- [ ] 80%+ test coverage for MCP tools
- [ ] MCP server documented in `mcp_servers/citation_quality/README.md`

---

### Phase 4: Documentation & Type Safety (2 hours)
**Goal:** Improve code maintainability and IDE support

**Steps:**
1. 🔲 **Add Type Annotations (Start with Core):**
   - `src/converters/md_to_latex/converter.py` (main entry point)
   - `src/converters/md_to_latex/citation_manager.py` (core logic)
   - `src/converters/md_to_latex/zotero_integration.py` (API client)

2. 🔲 **Enable Mypy:**
   ```toml
   # pyproject.toml
   [tool.mypy]
   python_version = "3.12"
   warn_return_any = true
   warn_unused_configs = true
   disallow_untyped_defs = true

   [[tool.mypy.overrides]]
   module = "tests.*"
   disallow_untyped_defs = false
   ```

   Add to pre-commit:
   ```yaml
   - repo: https://github.com/pre-commit/mirrors-mypy
     rev: v1.8.0
     hooks:
       - id: mypy
         additional_dependencies: [types-all]
   ```

3. 🔲 **Document Citation Pipeline:**
   Create `docs/ARCHITECTURE.md` with:
   - System architecture diagram
   - Data flow: MD → Citation Extraction → Zotero → BibTeX → LaTeX → PDF
   - Module responsibilities
   - Extension points

**Acceptance Criteria:**
- [ ] Core modules have 90%+ type annotation coverage
- [ ] Mypy passes on core modules
- [ ] Architecture doc explains how everything fits together
- [ ] Contributor guide updated with type annotation requirements

---

## 🎯 Long-Term Roadmap (Beyond Next Session)

### Milestone 1: Production-Ready Golden Dataset (Week 1)
- [ ] Golden dataset fully populated and tested
- [ ] Regression tests use golden fixtures exclusively
- [ ] CI runs regression tests on every PR
- [ ] Add 4 more papers to golden dataset (8 total)

### Milestone 2: MCP Server Feature Complete (Week 2)
- [ ] All MCP tools fully implemented
- [ ] MCP server tested with Claude Desktop
- [ ] Real-time citation quality checking in editor
- [ ] Integration tests with live Zotero API

### Milestone 3: Type Safety & Documentation (Week 3)
- [ ] 100% type annotation coverage in `src/`
- [ ] Mypy strict mode enabled
- [ ] Complete API documentation
- [ ] Video tutorial for common workflows

### Milestone 4: Performance & Scalability (Week 4)
- [ ] Benchmark suite tracking conversion speed
- [ ] Parallel processing for large bibliographies
- [ ] Caching layer for API responses
- [ ] Handle 1000+ citation papers without slowdown

---

## 📊 Metrics & Health Checks

### Current Status
```
Code Quality:
  ✅ Linting: 0 errors (ruff)
  ⚠️  Type Safety: Not enforced (no mypy)
  ✅ Tests: 398 collected, 16/16 regression passing
  ⚠️  Coverage: Unknown (not measured)
  ⚠️  TODOs: 50+ active items

Documentation:
  ✅ README: Comprehensive
  ✅ CLAUDE.md: Detailed guardrails
  ⚠️  API Docs: Inconsistent docstrings
  ⚠️  Architecture: No system diagram
  ✅ Test Coverage: Regression suite documented

Technical Debt:
  🔴 Debug code in production (HIGH)
  🟡 MCP stubs incomplete (MEDIUM)
  🟡 Golden dataset incomplete (MEDIUM)
  🟢 Error handling inconsistent (LOW)
```

### Success Criteria (Next Session)
- [ ] Golden dataset complete with expected outputs
- [ ] Zero debug code in production
- [ ] MCP tools fully functional
- [ ] Type annotations on core modules
- [ ] Architecture documented

---

## 🔗 Context from Last 6 Hours

### Key Files Modified
1. **src/cli.py** - Added `--audit` flag for pre-conversion checks
2. **tests/e2e/test_regression_4_papers.py** - New regression test suite
3. **tests/e2e/helpers_pdf.py** - Added `assert_no_missing_citations()`
4. **tests/fixtures/golden/** - Created golden dataset structure
5. **scripts/export_zotero_snapshot.py** - Tool for exporting Zotero snapshots

### Recent Commits (Branch: fix/verify-md-to-latex-conversion)
```
7ec9836 feat: Add golden dataset for MD→LaTeX→PDF regression testing
3069711 test: Add assert_no_missing_citations helper for regression tests
c3fc177 feat: Add --audit flag and MCP citation quality integration
```

### Known Working State
- All 4 papers convert with **zero (?) citations**:
  1. fashion_4DGS (47 KB) - 4D Gaussian Splatting
  2. fashion_3D_CAD (70 KB) - 3D CAD Review
  3. fashion_LCA (52 KB) - Life Cycle Assessment
  4. mcp_review (215 KB) - Model Context Protocol

- Zotero collection: `dpp-fashion` (12 entries, 25.4 KB snapshot)
- Better BibTeX keys working correctly
- Test suite: 16/16 passing

### User's Manual Fixes Applied
- Fixed 14 problematic citations in `fashion-cad-review-v3.md`:
  - Personal website citations → Proper paper URLs
  - Project pages → arXiv links
  - GitHub repos → Conference proceedings
  - Amazon links → Publisher URLs

---

## 🚀 Quick Start (Resuming Work)

### 1. Pull Latest & Check Status
```bash
cd /Users/petteri/Dropbox/github-personal/deep-biblio-tools
git pull
git status
```

### 2. Run Regression Tests
```bash
uv run python -m pytest tests/e2e/test_regression_4_papers.py -v
```

### 3. Review This Document
```bash
# Read this file for complete context
cat DEEP-CODE-REVIEW-AND-CONTINUATION-PLAN.md
```

### 4. Start with Priority 1 Tasks
- [ ] Populate golden dataset expected outputs
- [ ] Clean up debug code in citation_manager.py
- [ ] Implement MCP tool stubs

---

## 📝 Notes for Future Sessions

### What's Working Well
- **Regression test suite** - Caught issues early, 16/16 tests passing
- **Golden dataset approach** - Smart way to ensure deterministic testing
- **MCP integration** - Good architecture for real-time citation checking
- **Pre-commit hooks** - Catching issues before commits

### Pain Points to Address
- **Debug code in production** - Makes logs noisy
- **Incomplete MCP tools** - Return stubs instead of real data
- **No type safety** - Missing mypy enforcement
- **Golden dataset incomplete** - Can't use for deterministic tests yet

### Developer Experience Improvements
1. Add `make` targets for common tasks:
   ```makefile
   test:           # Run all tests
   test-regression: # Run just regression suite
   lint:           # Run ruff + mypy
   golden-update:  # Regenerate golden dataset
   ```

2. Add quick verification script:
   ```bash
   scripts/verify-setup.sh
   # Checks: env vars, dependencies, Zotero access, test data
   ```

3. Improve error messages:
   ```python
   # Current
   raise ValueError("Invalid")

   # Better
   raise ValidationError(
       "Citation 'Smith 2020' not found in Zotero collection 'dpp-fashion'. "
       "Did you forget to add it to Zotero? "
       "Run: uv run python -m src.cli bib validate"
   )
   ```

---

## 📚 References

### Key Documentation Files
- `.claude/CLAUDE.md` - Behavioral contract and guardrails
- `.claude/golden-paths.md` - Common workflows
- `tests/fixtures/golden/README.md` - Golden dataset documentation
- `mcp_servers/citation_quality/README.md` - MCP server guide

### Important Code Locations
- **Citation Pipeline:** `src/converters/md_to_latex/`
- **MCP Server:** `mcp_servers/citation_quality/`
- **Tests:** `tests/e2e/test_regression_4_papers.py`
- **Golden Dataset:** `tests/fixtures/golden/`

### Related Issues & PRs
- Branch: `fix/verify-md-to-latex-conversion`
- Previous work: 3 days of intensive development
- See `REPOSITORY-VISION.md` for 3-day synthesis

---

**Last Updated:** 2025-10-27 23:30
**Next Review:** After Phase 1 completion
**Status:** Ready for continuation
