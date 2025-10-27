# E2E Test Plan Implementation Summary

**Date**: 2025-10-27
**Status**: Ready for implementation - synthesis complete
**Context**: 2 days of test failure fixes + OpenAI feedback integration

---

## Three Document Set

This directory now contains a complete test planning trilogy:

1. **`COMPREHENSIVE-TEST-PLAN.md`** (~50KB)
   - Detailed implementation guide with full code examples
   - GitHub Actions configuration
   - Helper functions with complete implementations
   - For: Implementation reference, detailed planning

2. **`COMPACT-TEST-PLAN.md`** (~8KB)
   - LLM-optimized condensed version
   - Essential patterns and quick reference
   - Implementation priorities
   - For: LLM context windows, quick review

3. **`OPENAI-FEEDBACK-SYNTHESIS.md`** (this synthesis)
   - Critical assessment of external suggestions
   - Project-specific adaptations
   - What to adopt/adapt/defer and WHY
   - For: Decision rationale, future reference

---

## Key Decisions Made

### ✅ ADOPT (High Value, Project-Aligned)

1. **PDF Structural Checks** (links, fonts, metadata)
   - **Why**: Citation validation requires clickable DOI links
   - **Tool**: PyMuPDF + pikepdf
   - **Timeline**: Week 1

2. **LaTeX Log Parsing**
   - **Why**: Fail fast on compilation errors (no regex!)
   - **Tool**: String methods (`in`, `find()`)
   - **Timeline**: Week 1

3. **Text Normalization**
   - **Why**: Robust comparison despite LaTeX quirks (dashes, ligatures)
   - **Tool**: String replacement chains (no regex!)
   - **Timeline**: Week 1

4. **Pytest Markers** (`@pytest.mark.slow`, `@pytest.mark.e2e`)
   - **Why**: Fast PR feedback, comprehensive nightly builds
   - **Tool**: pytest.ini configuration
   - **Timeline**: Week 1

5. **CI Hardening** (caching, artifacts on failure)
   - **Why**: Faster feedback, better debugging
   - **Tool**: GitHub Actions enhancements
   - **Timeline**: Week 2

---

### ⚠️ ADAPT (Good Ideas, Need Tailoring)

1. **Visual Regression** → **Text-Based Structural Comparison**
   - **Why NOT image-based**: We validate citation *content*, not *design*
   - **Why NOT pixel-perfect**: LaTeX environments vary (font rendering, package versions)
   - **What instead**: Page count + section headers + citation counts + normalized text diffs
   - **Timeline**: Week 3

2. **Golden PDFs** → **Text Snapshots**
   - **Why NOT binary PDFs**: Can't review in Git, environment-dependent
   - **Why NOT Git LFS**: Setup friction, maintenance overhead
   - **What instead**: `tests/snapshots/*.txt` with normalized text
   - **Timeline**: Week 3

---

### ❌ DEFER (Not Now, Maybe Future)

1. **Image-Based RMS Diff**
   - **Why defer**: Wrong tool for citation validation pipeline
   - **Reconsider if**: We need to validate figure rendering in PDFs

2. **Git LFS for Golden Files**
   - **Why defer**: Text snapshots sufficient, adds complexity
   - **Reconsider if**: Binary regression becomes critical

3. **Full Docker Reproducibility**
   - **Why defer**: Already have `ci-docker.yml`, not currently needed
   - **Reconsider if**: Environment drift becomes problematic

---

## Implementation Roadmap

### Week 1: Foundation

**Goal**: Core E2E helpers + test infrastructure

```
✅ Create tests/e2e/helpers_pdf.py
   - extract_links() - verify DOI/arXiv clickability
   - get_font_info() - arXiv compliance (font embedding)
   - get_metadata() - PDF metadata validation
   - normalize_pdf_text() - robust text comparison (NO REGEX)

✅ Create tests/e2e/helpers_latex.py
   - assert_no_critical_latex_errors() - log parsing (NO REGEX)
   - Uses string methods: "LaTeX Error" in log_text

✅ Add pyproject.toml dependencies
   [project.optional-dependencies]
   test = [
       ...existing...
       "PyMuPDF>=1.23.0",  # Link extraction
       "pikepdf>=8.0.0",   # Font/metadata inspection
       "pytest-vcr>=1.0.2", # API response recording
   ]

✅ Create pytest.ini
   [pytest]
   markers =
       slow: marks tests as slow (deselect with '-m "not slow"')
       e2e: end-to-end tests (MD→LaTeX→PDF)
       integration: tests that contact external APIs
       requires_zotero: tests requiring Zotero credentials
```

**Deliverable**: Helper functions ready, pytest markers configured

---

### Week 2: Core E2E Tests

**Goal**: Validate MD→LaTeX→PDF pipeline comprehensively

```
✅ tests/e2e/test_pdf_structure.py
   - test_citations_are_hyperlinked()
     * Extract links with PyMuPDF
     * Verify DOI/arXiv URLs present
   - test_all_fonts_embedded()
     * Use pikepdf to check font embedding
     * Fail if any fonts missing (arXiv violation)
   - test_pdf_metadata_present()
     * Verify Title, Author, Producer fields

✅ tests/e2e/test_pdf_content.py
   - test_zero_unresolved_citations()
     * Extract PDF text
     * Assert NO "(?)", "(Unknown)", "(Anonymous)"
   - test_author_names_present()
     * Verify actual author names in text
   - test_bibliography_section_exists()
     * Check "References" heading present

✅ tests/e2e/test_latex_compilation.py
   - test_no_critical_latex_errors()
     * Parse .log file with string methods (NO REGEX!)
     * Fail on: "LaTeX Error", "Undefined citation", "No file references.bbl"
   - test_bibtex_ran_successfully()
     * Check .bbl file exists and non-empty
   - test_correct_template_used()
     * Verify spbasic_pt, authoryear in preamble
```

**Deliverable**: Full E2E coverage, catches all regressions

---

### Week 3: Styling & Regression

**Goal**: Publication quality + safe refactoring

```
✅ tests/e2e/test_hyperlink_styling.py
   - test_hyperref_navy_blue()
     * Parse LaTeX preamble
     * Verify urlcolor=NavyBlue, colorlinks=true

✅ tests/e2e/test_regression.py
   - test_citation_count_regression()
     * Compare to baseline citation count
   - test_text_content_regression()
     * Compare normalized PDF text to snapshot
   - test_structural_similarity()
     * Page count + section headers match baseline

✅ scripts/update_snapshots.py
   - Helper to regenerate text baselines
   - Interactive approve/reject workflow
```

**Deliverable**: Design system compliance + regression detection

---

### Week 4: CI Enhancement

**Goal**: Fast feedback, better debugging

```
✅ .github/workflows/ci.yml updates
   - Install poppler-utils (pdfinfo, pdftotext)
   - Cache LaTeX packages (~/.texlive*)
     key: texlive-${{ runner.os }}-${{ hashFiles('**/pyproject.toml') }}
   - Upload PDF artifacts on failure
     path: tests/output/**/*.pdf, tests/output/**/*.log

✅ .github/workflows/e2e-nightly.yml (NEW)
   - Run full E2E suite on main branch only
   - Run integration tests with real APIs (with secrets)
   - Schedule: nightly at 2am UTC
```

**Deliverable**: Faster CI, artifact-driven debugging

---

## Critical Constraints Applied

### 1. NO REGEX (Project Policy)

**All pattern matching uses string methods**:

```python
# ❌ FORBIDDEN
if re.search(r"LaTeX Error", log_text):
    raise AssertionError("LaTeX failed")

# ✅ REQUIRED
if "LaTeX Error" in log_text:
    raise AssertionError("LaTeX failed")
```

**Rationale**: `.claude/CLAUDE.md` forbids regex for predictability and AST-based parsing.

---

### 2. Text-First, Not Pixel-First

**Our project validates citation CONTENT, not visual DESIGN**:

```python
# ❌ NOT NEEDED (visual regression)
rms_diff = compare_images(golden_pdf, current_pdf)
assert rms_diff < 6.0

# ✅ SUFFICIENT (text-based structural check)
text_similarity = compare_normalized_text(golden, current)
assert text_similarity > 0.95  # Allow minor whitespace drift
```

**Rationale**: LaTeX environments vary (fonts, package versions). Text stays consistent.

---

### 3. Git-Friendly Snapshots

**Text snapshots, not binary PDFs**:

```python
# ❌ NOT ADOPTED (binary golden PDFs)
assert pdf_matches_golden("tests/golden/paper.pdf")

# ✅ ADOPTED (text snapshots)
normalized = normalize_pdf_text(extract_text(pdf))
snapshot_path = Path("tests/snapshots/paper.txt")
assert normalized == snapshot_path.read_text()
```

**Rationale**: Text diffs are human-reviewable in Git. No Git LFS needed.

---

### 4. Deterministic Behavior

**Core project principle from `.claude/CLAUDE.md`**:

```python
def normalize_pdf_text(text: str) -> str:
    """Make text comparison deterministic."""
    # Unicode normalization
    text = text.replace('\u2013', '-')  # en-dash
    text = text.replace('\u2014', '-')  # em-dash
    text = text.replace('\u00a0', ' ')  # nbsp
    text = text.replace('\ufb01', 'fi') # ligature

    # Whitespace normalization (NO REGEX!)
    while '  ' in text:
        text = text.replace('  ', ' ')

    return text.strip()
```

**Rationale**: Same input → same output. Critical for regression detection.

---

## Success Metrics

### Short-Term (Week 1-2)

- ✅ **Zero `(?)` citations**: Tests fail if any unresolved citations in PDF
- ✅ **All fonts embedded**: arXiv compliance enforced
- ✅ **Hyperlinks clickable**: DOI/arXiv links are actual hyperlinks, not text
- ✅ **LaTeX errors fail tests**: No silent compilation failures

### Medium-Term (Week 3-4)

- ✅ **Structural regression**: Detect page count changes, missing sections
- ✅ **E2E on every PR**: CI runs smoke tests automatically
- ✅ **PDF artifacts on failure**: Debug with actual PDFs, not just logs

### Long-Term (Month 2+)

- ✅ **Text snapshot regression**: Safe refactoring with baseline comparisons
- ✅ **Nightly comprehensive suite**: Full integration tests on main branch
- ✅ **Golden snapshot process**: Documented update/approval workflow

---

## Dependencies Added

### pyproject.toml

```toml
[project.optional-dependencies]
test = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.0",

    # NEW - PDF inspection
    "PyMuPDF>=1.23.0",    # fitz - link extraction, rendering
    "pikepdf>=8.0.0",     # Font embedding, metadata

    # NEW - API mocking
    "pytest-vcr>=1.0.2",  # Record/replay HTTP interactions

    # OPTIONAL - Text snapshot management
    "pytest-snapshot>=0.9.0",
]
```

### GitHub Actions (ci.yml)

```yaml
- name: Install system dependencies
  run: |
    sudo apt-get update
    sudo apt-get install -y \
      pandoc lyx \
      texlive-xetex texlive-latex-extra texlive-fonts-recommended \
      poppler-utils  # NEW: pdfinfo, pdftotext, pdftoppm

- name: Cache LaTeX packages  # NEW
  uses: actions/cache@v4
  with:
    path: ~/.texlive*
    key: texlive-${{ runner.os }}-${{ hashFiles('**/pyproject.toml') }}
```

---

## Risks & Mitigations

### Risk 1: PyMuPDF / pikepdf Size

**Impact**: MEDIUM (~50MB installed)
**Mitigation**:
- Keep in `test` optional dependencies (not required for CLI users)
- CI caching amortizes download cost
- Alternative: Fallback to pdfplumber (already dependency)

### Risk 2: LaTeX Environment Variability

**Impact**: MEDIUM (tests pass locally, fail in CI)
**Mitigation**:
- Text normalization handles rendering differences
- Document LaTeX version in test output
- Future: Docker if variability becomes problematic

### Risk 3: External API Flakiness

**Impact**: LOW (already mitigated with caching)
**Mitigation**:
- pytest-vcr records API responses
- `@pytest.mark.integration` opt-in
- Skip by default, run with `--run-integration`

---

## Next Steps (Actionable)

### Immediate (This Week)

1. ✅ **Review this synthesis** - User approval needed
2. ✅ **Create helpers_pdf.py** - Link extraction, font checks
3. ✅ **Add pytest.ini** - Configure markers
4. ✅ **Update pyproject.toml** - Add PyMuPDF, pikepdf

### Week 1 Sprint

1. **Implement core E2E helpers** (helpers_pdf.py, helpers_latex.py)
2. **Write first E2E test** (test_zero_unresolved_citations)
3. **Verify it catches known issues** (run on broken conversion)
4. **Document helper usage** (docstrings, examples)

### Week 2 Sprint

1. **Complete E2E test suite** (PDF structure, content, LaTeX logs)
2. **Add CI enhancements** (caching, artifacts)
3. **Run full suite on main branch** (verify no regressions)
4. **Update test documentation** (README, examples)

---

## Related Documents

- **`COMPREHENSIVE-TEST-PLAN.md`**: Full implementation guide (50KB)
- **`COMPACT-TEST-PLAN.md`**: LLM-optimized quick reference (8KB)
- **`OPENAI-FEEDBACK-SYNTHESIS.md`**: Critical assessment + rationale
- **`PLAYWRIGHT-TESTING-GUIDE.md`**: Visual testing guide (for intern, different project)
- **`test-failure-resolution-plan.md`**: Recent 9 test fixes (completed)

---

## Conclusion

We now have a **clear, actionable, project-aligned test plan** that:

1. ✅ **Adopts best practices** from OpenAI suggestions (PDF inspection, log parsing)
2. ✅ **Respects project constraints** (no regex, deterministic, text-first)
3. ✅ **Solves actual problems** (catches `(?)` citations, verifies hyperlinks)
4. ✅ **Is implementation-ready** (phased roadmap, dependencies specified)
5. ✅ **Balances rigor and pragmatism** (no overkill, no shortcuts)

**Status**: Ready for user approval and Week 1 implementation kickoff.
