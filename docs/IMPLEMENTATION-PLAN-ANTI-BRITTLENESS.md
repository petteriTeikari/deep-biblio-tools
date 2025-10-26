# Implementation Plan: Anti-Brittleness Infrastructure

**Date**: 2025-10-26
**Goal**: Make citation pipeline robust, debuggable, and regression-proof
**Priority**: CRITICAL - Required before any future BBT work

---

## Critical Analysis: OpenAI vs Our Current State

### Claude's Implementation (What We Built)
- ✅ **Good**: Comprehensive failure documentation
- ✅ **Good**: Fast reversion to working state
- ✅ **Good**: Identified exact failure mechanisms
- ❌ **Bad**: No validation before deployment
- ❌ **Bad**: Zero debug instrumentation
- ❌ **Bad**: No regression tests
- ❌ **Bad**: Didn't research BBT architecture first

### OpenAI's Approach (What We Should Have Done)
- ✅ **Research first**: Check BBT documentation before coding
- ✅ **Log everything**: Add instrumentation BEFORE changes
- ✅ **Establish baseline**: Golden files as reference
- ✅ **Incremental validation**: Keep old method while testing new
- ✅ **Automated safety**: Regression tests + CI/CD

### Synthesis: Why We Failed
1. **Skipped research phase**: Assumed Zotero API includes BBT keys (wrong)
2. **No safety net**: Changed critical code without logging/tests
3. **All-or-nothing deployment**: Replaced working method entirely
4. **Silent failures**: 0 matches logged but didn't stop pipeline
5. **No baseline**: Couldn't detect regression automatically

---

## Three-Phase Implementation Plan

### Phase 1: Safety Infrastructure (THIS SESSION)
**Goal**: Add logging + baseline before touching BBT again
**Time**: ~2 hours
**Risk**: Low (no logic changes)

#### Task 1.1: Add Debug Logging Helper
**File**: `src/converters/md_to_latex/debug_logger.py` (NEW)
```python
"""Debug logging utilities for citation pipeline."""
import json
import logging
from pathlib import Path
from typing import Any

class PipelineDebugger:
    """Manages debug artifacts for each pipeline stage."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("pipeline_debug")

    def log_stage(self, stage_num: int, stage_name: str):
        """Log start of pipeline stage."""
        self.logger.info("=" * 80)
        self.logger.info(f"STAGE {stage_num}: {stage_name}")
        self.logger.info("=" * 80)

    def dump_json(self, data: Any, filename: str):
        """Save debug data as JSON."""
        path = self.output_dir / filename
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.logger.info(f"Saved debug: {path}")

    def dump_text(self, content: str, filename: str):
        """Save debug data as text."""
        path = self.output_dir / filename
        path.write_text(content, encoding='utf-8')
        self.logger.info(f"Saved debug: {path}")
```

#### Task 1.2: Instrument converter.py with 6-Stage Logging
**File**: `src/converters/md_to_latex/converter.py`
**Changes**: Add debug calls at each critical point
- Import `PipelineDebugger`
- Initialize in `convert()` method
- Add Stage 1-6 logging (see APPENDIX-OPENAI for details)

#### Task 1.3: Create Debug CLI Harness
**File**: `scripts/run_debug_conversion.py` (NEW)
- Copy from OpenAI's template
- Adapt to our repo structure
- Add environment validation
- Add timestamped output directories

#### Task 1.4: Run Baseline Capture
```bash
# Generate golden baseline
uv run python scripts/run_debug_conversion.py \
    --markdown /path/to/mcp-draft-refined-v4.md \
    --collection dpp-fashion \
    --update-baseline

# Verify artifacts created
ls -la debug_runs/YYYYMMDD_HHMMSS_*/debug-*.json
```

#### Task 1.5: Commit Golden Baseline
```bash
git add tests/fixtures/golden-matching-results.json
git add tests/fixtures/debug-baseline/
git commit -m "Add golden baseline for regression testing"
```

---

### Phase 2: Regression Test Suite (NEXT SESSION)
**Goal**: Automated detection of citation pipeline breaks
**Time**: ~3 hours
**Risk**: Low (test-only changes)

#### Task 2.1: Create Test Fixtures
**Structure**:
```
tests/
├── fixtures/
│   ├── sample-paper.md           # Minimal test document
│   ├── golden-matching-results.json
│   └── debug-baseline/
│       ├── debug-01-extracted-citations.json
│       ├── debug-02-zotero-bibtex-raw.bib
│       ├── debug-03-parsed-bibtex-entries.json
│       ├── debug-04-matching-results.json
│       ├── debug-05-bibtex-validation.json
│       ├── debug-06-latex-citations.json
│       └── debug-07-pdf-validation.json
```

#### Task 2.2: Implement Regression Tests
**File**: `tests/test_citation_pipeline.py` (NEW)
```python
def test_citation_extraction_stability():
    """Ensure extraction is deterministic."""
    # Run twice, compare results

def test_zotero_matching_baseline():
    """Ensure matching doesn't regress."""
    # Compare against golden baseline

def test_bibtex_generation_completeness():
    """Ensure all citations get BibTeX entries."""
    # Check entry count, no Unknown/Anonymous

def test_latex_citation_consistency():
    """Ensure LaTeX citations match BibTeX keys."""
    # Extract keys from both, compare sets

def test_pdf_compilation_success():
    """Ensure PDF compiles with zero unresolved citations."""
    # Check .blg for "didn't find" warnings
```

#### Task 2.3: Add Pre-Commit Hooks
**File**: `.pre-commit-config.yaml`
```yaml
repos:
  - repo: local
    hooks:
      - id: citation-regression-test
        name: Citation Pipeline Regression Test
        entry: pytest tests/test_citation_pipeline.py -v
        language: python
        pass_filenames: false
        files: '(converter.py|citation_manager.py|zotero_integration.py)$'
```

#### Task 2.4: Add GitHub Actions CI
**File**: `.github/workflows/test-citations.yml` (NEW)
```yaml
name: Citation Pipeline Tests
on:
  pull_request:
    paths:
      - 'src/converters/**'
      - 'tests/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: uv sync
      - name: Run regression tests
        env:
          ZOTERO_API_KEY: ${{ secrets.ZOTERO_API_KEY }}
          ZOTERO_USER_ID: ${{ secrets.ZOTERO_USER_ID }}
        run: pytest tests/test_citation_pipeline.py -v
```

---

### Phase 3: Better BibTeX Integration (FUTURE)
**Goal**: Integrate BBT properly with safety nets in place
**Time**: ~4 hours
**Risk**: Medium (but now safe to attempt)

#### Task 3.1: Configure BBT Auto-Export
**Manual step**: Configure Zotero Better BibTeX
1. Open Zotero preferences → Better BibTeX → Automatic Export
2. Add collection: `dpp-fashion`
3. Export format: BibTeX
4. Output path: `~/Dropbox/zotero-exports/dpp-fashion.bib`
5. Auto-export on: Collection change

#### Task 3.2: Implement BBT File Reader
**File**: `src/converters/md_to_latex/bbt_integration.py` (NEW)
```python
"""Better BibTeX integration via auto-exported .bib file."""
from pathlib import Path
from typing import Dict

def load_bbt_export(path: Path) -> Dict[str, Dict]:
    """Load BBT auto-exported .bib file and build indices."""
    content = path.read_text(encoding='utf-8')
    entries = parse_bibtex_entries(content)  # Reuse existing parser

    # Build lookup indices
    url_to_key = {}
    doi_to_key = {}
    arxiv_to_key = {}

    for key, metadata in entries.items():
        if metadata['url']:
            normalized = normalize_identifier(metadata['url'])
            url_to_key[normalized] = key
        if metadata['doi']:
            doi_to_key[f"doi:{metadata['doi']}"] = key
        if metadata['arxiv_id']:
            arxiv_to_key[f"arxiv:{metadata['arxiv_id']}"] = key

    return {
        'url_to_key': url_to_key,
        'doi_to_key': doi_to_key,
        'arxiv_to_key': arxiv_to_key,
        'raw_entries': entries
    }
```

#### Task 3.3: Implement Hybrid Matching Strategy
**File**: `src/converters/md_to_latex/citation_matcher.py` (MODIFY)
```python
def match_citation_with_fallback(
    citation: Citation,
    bbt_indices: Dict,
    zotero_api_data: Dict
) -> Optional[str]:
    """Match using hierarchy: DOI → arXiv → URL → API fallback."""

    # Try DOI first (most stable)
    if citation.doi:
        doi_key = f"doi:{citation.doi}"
        if doi_key in bbt_indices['doi_to_key']:
            return bbt_indices['doi_to_key'][doi_key]

    # Try arXiv ID (very stable)
    if 'arxiv.org' in citation.url:
        arxiv_id = extract_arxiv_id(citation.url)
        if arxiv_id:
            arxiv_key = f"arxiv:{arxiv_id}"
            if arxiv_key in bbt_indices['arxiv_to_key']:
                return bbt_indices['arxiv_to_key'][arxiv_key]

    # Try normalized URL (fragile but common)
    norm_url = normalize_identifier(citation.url)
    if norm_url in bbt_indices['url_to_key']:
        return bbt_indices['url_to_key'][norm_url]

    # Fallback to API-based matching
    return match_via_zotero_api(citation, zotero_api_data)
```

#### Task 3.4: Add Comparison Mode
**File**: `scripts/compare_bbt_vs_api.py` (NEW)
```python
"""Compare BBT file matching vs Zotero API matching."""

def main():
    citations = extract_citations(markdown_file)

    # Method 1: BBT file
    bbt_data = load_bbt_export(bbt_path)
    bbt_matched, bbt_missing = match_with_bbt(citations, bbt_data)

    # Method 2: Zotero API
    api_matched, api_missing = match_with_api(citations, collection)

    # Report differences
    print(f"BBT matched: {bbt_matched}/{len(citations)}")
    print(f"API matched: {api_matched}/{len(citations)}")
    print(f"Diff: {abs(bbt_matched - api_matched)}")

    # Only switch if BBT >= API
    if bbt_matched >= api_matched:
        print("✅ BBT method equal or better - safe to switch")
    else:
        print("⚠️ BBT method worse - keep as auxiliary only")
```

#### Task 3.5: Gradual Rollout
```bash
# Step 1: Run comparison (don't change primary yet)
python scripts/compare_bbt_vs_api.py

# Step 2: If BBT >= API, add BBT as auxiliary
# Modify converter to try BBT first, fall back to API

# Step 3: Monitor for one week
# Check debug logs for any BBT failures

# Step 4: If stable, make BBT primary
# Keep API as fallback for missing citations
```

---

## Implementation Order (This Session)

### Priority 1: Logging Infrastructure (Critical)
1. ✅ Create `debug_logger.py`
2. ✅ Add Stage 1-6 logging to `converter.py`
3. ✅ Create `run_debug_conversion.py` script

### Priority 2: Baseline Capture (Critical)
1. ✅ Run debug conversion on MCP paper
2. ✅ Save all debug-*.json files
3. ✅ Commit as golden baseline

### Priority 3: Quick Validation (Optional if time)
1. ✅ Add minimal regression test
2. ✅ Run test to verify baseline works

---

## Success Criteria

### Phase 1 Complete When:
- [  ] All 7 debug JSON files generated for MCP paper
- [  ] Golden baseline committed to repo
- [  ] Debug harness runs without errors
- [  ] Can re-run and get identical baseline

### Phase 2 Complete When:
- [  ] Regression tests pass in CI
- [  ] Pre-commit hooks catch citation changes
- [  ] Golden baseline auto-validates on PR

### Phase 3 Complete When:
- [  ] BBT matching >= API matching (comparison mode)
- [  ] Hybrid strategy implemented with DOI-first
- [  ] One week of stable operation
- [  ] Documentation updated with BBT setup guide

---

## Risks & Mitigation

### Risk 1: Logging overhead slows pipeline
**Mitigation**: Make debug mode optional (`--debug` flag)

### Risk 2: Golden baseline becomes stale
**Mitigation**: Auto-update workflow + baseline versioning

### Risk 3: BBT auto-export path issues
**Mitigation**: Config file for BBT path, clear error if missing

### Risk 4: Regression tests flaky in CI
**Mitigation**: Use cached Zotero data, mock API calls

---

## Documentation Updates Required

1. **README.md**: Add debugging section
2. **CONTRIBUTING.md**: Explain regression test workflow
3. **docs/DEBUGGING.md** (NEW): Debug pipeline guide
4. **docs/BBT-SETUP.md** (NEW): Better BibTeX configuration

---

**Let's start implementing Phase 1 NOW.**
