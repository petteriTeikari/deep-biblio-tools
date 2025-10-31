# Emergency Mode: Zero Internet Fetch Plan - 2025-10-31

## Executive Summary

**Problem**: Emergency mode is still fetching metadata from CrossRef/arXiv APIs despite `enable_auto_add=False` and `use_cache=False`.

**Impact**: Violates emergency mode guarantee of zero internet use, wastes time fetching data that won't be used.

**Root Cause**: `fetch_citation_metadata()` is called for ALL citations in `generate_bibtex_file()`, regardless of emergency mode setting.

**Solution**: Skip metadata fetching entirely in emergency mode - use only RDF data.

---

## Current State (After failedAutoAdd Fix)

### What's Working ✅

1. **failedAutoAdd filtering**: 0 failedAutoAdd entries in references.bib (filtering successful!)
2. **RDF parser**: Finds 664/664 entries from RDF
3. **Amazon book URLs**: Finds 2/2 books with nested URL structure
4. **Conversion completes**: Generates .tex, .bib, and .pdf files

### What's Broken ❌

1. **Metadata fetching in emergency mode**: System fetches from CrossRef/arXiv even though it shouldn't
2. **Log spam**: 133 "Citation not found" + "Fetching metadata from CrossRef" messages
3. **Performance**: Wastes time on network calls that don't help emergency mode
4. **Conceptual violation**: Emergency mode should be 100% offline

### Evidence from Conversion Log

```
Citation not found in Zotero collection: https://arxiv.org/abs/2510.04618 - attempting auto-add
⚠️  Allow-failures enabled - generating temp key and continuing
  Temporary key: failedAutoAdd_510621
...
Fetching metadata from CrossRef: https://doi.org/10.1016/j.procir.2024.12.030
Fetching metadata from arXiv: https://arxiv.org/abs/2510.01499
...
Excluding 133 failedAutoAdd entries from .bib (will appear as (?) in PDF)
```

**Analysis**:
- 133 citations not in RDF → Generated failedAutoAdd_* keys ✓
- System attempted to fetch metadata for these from CrossRef/arXiv ✗
- Filter excluded them from .bib file ✓
- But fetching still happened (wasted network calls) ✗

---

## User Requirements (from User Messages)

> "there was supposed to be zero internet use in the emergency mode!"

> "there was a separate markdown quality pipeline that needed to verify that all the hyperlinks are correct, author names are correct and the contents of the links actually match what we are saying about them."

**Clear separation of concerns**:
1. **Emergency mode (MD→LaTeX)**: ZERO internet, use ONLY RDF data, fast conversion
2. **Quality pipeline (separate)**: Validate links, verify author names, check content accuracy

---

## The Problem: Metadata Fetching in generate_bibtex_file()

**File**: `src/converters/md_to_latex/citation_manager.py:1720-1776`

**Current code**:
```python
def generate_bibtex_file(self, output_path: Path, show_progress: bool = False) -> None:
    """Generate BibTeX file with all citations."""

    # Filter out failedAutoAdd entries ✓ (FIXED)
    filtered_citations = [
        (key, citation) for key, citation in citations_list
        if not key.startswith("failedAutoAdd_")
    ]

    for key, citation in filtered_citations:
        # Fetch metadata if not already done ✗ (PROBLEM!)
        self.fetch_citation_metadata(citation)  # <-- FETCHES FROM INTERNET
        bibtex_entries.append(citation.to_bibtex())
```

**Problem**: `fetch_citation_metadata(citation)` makes CrossRef/arXiv API calls even though:
- We're in emergency mode
- We only want RDF data
- These citations are already matched to RDF entries

---

## Solution Design

### Principle: Emergency Mode = RDF Data Only

**Emergency mode workflow**:
1. Load 664 entries from RDF → CSL JSON format
2. Extract citations from markdown → URLs
3. Match citations to RDF entries by URL/DOI/arXiv ID
4. For matched citations → Use RDF metadata AS-IS (no fetching)
5. For missing citations → Generate failedAutoAdd_* key, exclude from .bib
6. Generate .bib file with ONLY RDF data
7. Compile LaTeX → missing citations show as (?)

**No fetching at any stage.**

### Implementation: Add emergency_mode flag

**Step 1**: Add `emergency_mode` parameter to `CitationManager.__init__()`:

```python
def __init__(
    self,
    # ... existing params ...
    emergency_mode: bool = False,  # NEW: Disable all fetching
):
    self.emergency_mode = emergency_mode
```

**Step 2**: Skip fetching in `generate_bibtex_file()`:

```python
def generate_bibtex_file(self, output_path: Path, show_progress: bool = False) -> None:
    """Generate BibTeX file with all citations."""

    filtered_citations = [
        (key, citation) for key, citation in citations_list
        if not key.startswith("failedAutoAdd_")
    ]

    for key, citation in filtered_citations:
        # EMERGENCY MODE: Use RDF data only, no fetching
        if not self.emergency_mode:
            self.fetch_citation_metadata(citation)

        bibtex_entries.append(citation.to_bibtex())
```

**Step 3**: Pass `emergency_mode=True` from converter:

```python
# File: scripts/deterministic_convert.py
converter = MarkdownToLatexConverter(
    bibliography_rdf_file_path=rdf_path,
    output_dir=output_dir,
    allow_failures=allow_failures,
    enable_auto_add=False,
    use_cache=False,
    emergency_mode=True,  # NEW: ZERO internet use
)
```

**Step 4**: Thread through to CitationManager:

```python
# File: src/converters/md_to_latex/converter.py
self.citation_manager = CitationManager(
    # ... existing params ...
    emergency_mode=self.emergency_mode,  # NEW
)
```

---

## Expected Results After Fix

### Conversion Log (Expected)

```
Starting conversion...
Loading 664 entries from RDF...
Extracting citations from markdown...
Found 383 citations
Matching citations to RDF entries...
  - Matched: 250 citations
  - Missing: 133 citations (will appear as (?) in PDF)
Generating references.bib...
  - Included: 250 RDF entries
  - Excluded: 133 failedAutoAdd entries
Writing LaTeX files...
Compiling PDF...
Done!
```

**No "Fetching metadata from CrossRef" messages.**
**No "attempting auto-add" messages (that's for auto-add, which is disabled).**

### Performance Improvement

- **Before**: ~5-10 seconds per missing citation (network timeout)
- **After**: Instant (no network calls)
- **Total time saved**: 133 citations × 5 sec = ~11 minutes!

### Correctness Guarantee

- **RDF entries**: Use metadata exactly as exported from Zotero (author names, titles, years, DOIs)
- **Missing citations**: Show as (?) in PDF, clearly indicating what needs to be added to Zotero
- **No hallucination**: System cannot invent author names or titles

---

## Quality Pipeline (Separate Tool, Future Work)

**Purpose**: Validate that citations in markdown are accurate

**NOT part of emergency mode conversion!**

**Features** (to be implemented separately):
1. **Link validation**: Check that URLs are accessible
2. **Author name verification**: Fetch from CrossRef/arXiv and compare to markdown
3. **Content verification**: Check that linked paper matches description
4. **Report generation**: List all discrepancies for manual review

**Key difference**: This runs BEFORE conversion, as a quality check. Emergency mode conversion then uses pre-verified citations.

---

## Implementation Checklist

### Phase 1: Add emergency_mode Flag (10 minutes)

- [ ] Add `emergency_mode: bool = False` parameter to `CitationManager.__init__()`
- [ ] Store as `self.emergency_mode`
- [ ] Add to `MarkdownToLatexConverter.__init__()`
- [ ] Pass through from `converter.py` to `citation_manager.py`
- [ ] Update `scripts/deterministic_convert.py` to pass `emergency_mode=True`

### Phase 2: Skip Fetching in Emergency Mode (5 minutes)

- [ ] Update `generate_bibtex_file()` to check `self.emergency_mode`
- [ ] Skip `fetch_citation_metadata()` call if emergency mode
- [ ] Update docstring to document emergency mode behavior

### Phase 3: Clean Up Logging (5 minutes)

- [ ] Remove "attempting auto-add" message (confusing in emergency mode)
- [ ] Change "Citation not found" to "Citation not in RDF" (clearer)
- [ ] Add summary at end: "X citations from RDF, Y missing (will show as ?)"

### Phase 4: Test and Verify (10 minutes)

- [ ] Run conversion on actual paper
- [ ] Verify NO "Fetching metadata" messages in log
- [ ] Verify 0 failedAutoAdd entries in references.bib
- [ ] Count entries in references.bib (should match RDF matched count)
- [ ] Check PDF for (?) citations where expected
- [ ] Verify conversion is much faster

### Phase 5: Update Documentation (5 minutes)

- [ ] Update `.claude/CLAUDE.md` with emergency mode = zero fetching
- [ ] Document that quality pipeline is separate tool
- [ ] Add this plan to docs/planning/ for future reference

---

## Success Criteria

**Before claiming success, verify ALL of these**:

1. ✅ Conversion log has ZERO "Fetching metadata from CrossRef" messages
2. ✅ Conversion log has ZERO "Fetching metadata from arXiv" messages
3. ✅ Conversion completes in < 30 seconds (was ~11 minutes with fetching)
4. ✅ references.bib has 0 failedAutoAdd entries
5. ✅ references.bib has ~250 entries (matched from RDF)
6. ✅ PDF compiles successfully
7. ✅ PDF has ~133 (?) citations (missing from RDF)
8. ✅ All (?) citations are ones we expect to be missing
9. ✅ Monitor network activity: Should be ZERO

---

## Questions for User / OpenAI Review

1. **Is this plan correct?** Does it address the emergency mode violation properly?

2. **Quality pipeline scope**: Should we implement the quality pipeline now or later?

3. **Missing citations**: How should we present the list of 133 missing citations to the user?
   - Option A: Log each one during conversion
   - Option B: Write to separate file (missing_citations.txt)
   - Option C: Add as comment section at end of .tex file

4. **Verification**: What additional tests should we run to ensure zero fetching?

5. **Edge cases**: Are there any scenarios where emergency mode SHOULD fetch metadata?
   - My answer: NO. Emergency mode should never fetch. Ever.

---

## Timeline

**Total estimated time**: 35 minutes

1. Phase 1 (flag): 10 min
2. Phase 2 (skip fetch): 5 min
3. Phase 3 (logging): 5 min
4. Phase 4 (test): 10 min
5. Phase 5 (docs): 5 min

**Can start immediately upon user approval.**

---

## Risk Assessment

### Low Risk ✅

- Changes are isolated to emergency mode path
- Normal mode (Zotero API) unaffected
- Backward compatible (emergency_mode defaults to False)

### No Risk of Breaking Existing Functionality ✅

- Only adds new parameter
- Only changes behavior when emergency_mode=True
- Default behavior unchanged

### High Confidence in Solution ✅

- Problem is clear: fetching when we shouldn't
- Solution is simple: add flag to skip fetching
- Easy to verify: check logs for "Fetching" messages

---

---

## OpenAI Review Feedback (Integrated 2025-10-31)

### Mental Model: The Robot Librarian Analogy

Think of the converter like a robot librarian:

- **Normal mode**: When it sees a citation it doesn't know, it runs to the internet to ask CrossRef or arXiv for help
- **Emergency mode**: The library doors are locked. The robot should only use what's already on the local shelf (RDF file)

**Current bug**: The robot still tries to run to the door for help — even though it can't leave.

**Fix**: Tell it "When the door's locked, don't even try to run out!" (the `emergency_mode=True` flag)

### Exact Implementation (OpenAI-Approved Diff)

#### File 1: `src/converters/md_to_latex/citation_manager.py`

```python
def __init__(
    self,
    # ... existing params ...
    emergency_mode: bool = False,  # NEW: Zero-fetch mode flag
):
    self.emergency_mode = emergency_mode

    if self.emergency_mode:
        logger.info("🚨 Emergency Mode active — skipping all network metadata fetching.")
```

```python
def generate_bibtex_file(self, output_path: Path, show_progress: bool = False) -> None:
    """Generate BibTeX file with all citations.

    In emergency mode, uses only RDF metadata and skips all fetching.
    """
    filtered_citations = [
        (key, citation) for key, citation in self.citations.items()
        if not key.startswith("failedAutoAdd_")
    ]

    bibtex_entries = []

    for key, citation in filtered_citations:
        # In emergency mode, use only RDF metadata and skip fetching
        if not self.emergency_mode:
            self.fetch_citation_metadata(citation)

        bibtex_entries.append(citation.to_bibtex())

    # Write all BibTeX entries to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(bibtex_entries))

    if self.emergency_mode:
        logger.info(f"✅ Emergency mode complete: Used {len(bibtex_entries)} RDF entries, no metadata fetched.")
```

#### File 2: `src/converters/md_to_latex/converter.py`

```python
def __init__(
    self,
    # ... existing params ...
    emergency_mode: bool = False,
):
    self.emergency_mode = emergency_mode

    # Init citation manager
    self.citation_manager = CitationManager(
        # ... existing params ...
        emergency_mode=self.emergency_mode,
    )
```

#### File 3: `scripts/deterministic_convert.py`

```python
parser.add_argument(
    "--emergency",
    action="store_true",
    help="Enable zero-internet emergency mode (RDF only)"
)

# ... later in main() ...

converter = MarkdownToLatexConverter(
    bibliography_rdf_file_path=rdf_path,
    output_dir=output_dir,
    allow_failures=args.allow_failures,
    enable_auto_add=False,
    use_cache=False,
    emergency_mode=True,  # ALWAYS True in deterministic_convert.py
)
```

### Safety Checks (OpenAI Recommendation)

**Add startup warning**:
```python
if self.emergency_mode:
    logger.warning("🚨 Emergency mode active: Skipping ALL metadata fetching!")
```

**"Silence Detector" Test** (to verify no fetching):
```python
log_text = open("conversion.log").read()
assert "Fetching metadata" not in log_text
assert "CrossRef" not in log_text
assert "arXiv" not in log_text
```

If any of these appear → the flag threading is broken.

### Optional Enhancement: Missing Citations Report

**Add `--missing-report` flag**:
```python
parser.add_argument(
    "--missing-report",
    type=Path,
    help="Write missing citations to this file for quality pipeline"
)
```

**Generate report**:
```python
if args.missing_report and self.failed_citations:
    with open(args.missing_report, "w") as f:
        f.write("Missing Citations (not in RDF)\n")
        f.write("=" * 80 + "\n\n")
        for url, reasons in self.failed_citations:
            f.write(f"{url}\n")
            for reason in reasons:
                f.write(f"  - {reason}\n")
            f.write("\n")
```

### Expected Log Output (After Fix)

```
🚨 Emergency Mode active — skipping all network metadata fetching.
Loading 664 entries from RDF...
Extracting 383 citations from markdown...
Matching citations to RDF entries...
  - Matched: 250 citations
  - Missing: 133 citations (will appear as (?) in PDF)
Generating references.bib...
Excluding 133 failedAutoAdd entries from .bib (will appear as (?) in PDF)
✅ Emergency mode complete: Used 250 RDF entries, no metadata fetched.
Compiling LaTeX...
Done! (28.3 seconds)
```

**No "Fetching metadata from CrossRef" messages.**
**No "attempting auto-add" messages.**

### Performance Verification

- **Before**: ~11 minutes (133 citations × ~5 seconds each)
- **After**: ~30 seconds
- **Speedup**: 22x faster

### Quality Pipeline (Future, Separate Tool)

**Clear separation**:

| Mode | Internet? | Purpose | Example Output |
|------|-----------|---------|----------------|
| 🧩 Emergency Mode | ❌ No | Deterministic offline build | `patterns_for_api` shows as (?) |
| 🔍 Quality Pipeline | ✅ Yes | Validate citations and links | amazon.com link unreachable |

The quality pipeline will:
1. Run **before** emergency mode conversion
2. Fetch from CrossRef/arXiv to verify author names match
3. Check that URLs are accessible
4. Generate quality report for manual review

**Emergency mode just uses the RDF data** — no validation, no fetching.

---

## Next Steps

**Plan approved by OpenAI** ✅

**Ready to implement** — will follow the exact diff provided by OpenAI, systematically, one phase at a time.

**Estimated time**: 35 minutes total
- Phase 1 (flag threading): 10 min
- Phase 2 (skip fetching): 5 min
- Phase 3 (logging cleanup): 5 min
- Phase 4 (testing): 10 min
- Phase 5 (documentation): 5 min
