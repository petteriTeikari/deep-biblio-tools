# Systematic Fix Plan - 2025-10-30 Evening
## Principal Engineer Root Cause Analysis & Systematic Solution

**Date**: 2025-10-30 19:30 UTC
**Author**: Claude (acting as Principal Engineer)
**Context**: Emergency conversion for manuscript submission TONIGHT
**User Frustration Level**: CRITICAL - "stop being like a junior engineer"

---

## ROOT CAUSE ANALYSIS

### What Actually Went Wrong Tonight

1. **Better BibTeX is BANNED** (user's final decision after trying to make it work)
   - Too problematic to get working from all sources
   - Validation warnings flooding output (1000+ lines)
   - User quote: "they should be banned altogether from this repo!"

2. **.bib Format DROPS Critical Fields**
   - Fletcher book: Amazon URL in RDF → MISSING in .bib export
   - ISBNs missing from .bib but present in RDF
   - DOIs sometimes stripped
   - **Discovery**: .bib/.bibtex exports are LOSSY

3. **RDF is the ONLY Acceptable Format for Emergency Mode**
   - Preserves ALL metadata fields
   - Complete data including URLs, ISBNs, DOIs
   - Already implemented RDF parser in `bibliography_sources.py`

4. **Code Inconsistency from Partial Refactoring**
   - Some places use `zotero_json_path` (old)
   - Some places use `bibliography_rdf_file_path` (new)
   - Method named `_populate_from_zotero_json` but loads RDF
   - Result: AttributeError crashes

5. **I Acted Like a Junior Engineer**
   - Fixed symptoms (warnings) instead of causes (architecture)
   - Made incremental changes without committing
   - No systematic plan before coding
   - Whac-a-mole approach instead of root cause fixing

---

## THE SYSTEMATIC FIX (Principal Engineer Approach)

### PHASE 1: Document & Commit Current State ✅

**Actions**:
1. Write this systematic plan document
2. Commit ALL current changes with clear message
3. Push to remote for clean checkpoint
4. Creates rollback point if needed

**Changes to Commit**:
- `comprehensive-bibliography-fix-plan-2025-10-30.md` (794 lines) - context
- `deterministic_convert.py` - RDF parameter rename (incomplete)
- `bibliography_sources.py` - RDF parser implementation (COMPLETE ✅)
- `citation_manager.py` - Better BibTeX validation removed (COMPLETE ✅)
- `converter.py` - Parameter renames (INCOMPLETE)

**Commit Message**:
```
WIP: Ban Better BibTeX, implement RDF-only emergency mode

- Remove Better BibTeX key validation (too problematic)
- Implement complete RDF parser in bibliography_sources.py
- Rename bibliography_file_path → bibliography_rdf_file_path
- Make --rdf flag required in deterministic_convert.py

INCOMPLETE: Still has use_better_bibtex_keys references in converter.py
Next: Complete systematic cleanup per SYSTEMATIC-FIX-PLAN

Ref: User request - "Better BibTeX should be banned from repo"
```

### PHASE 2: Complete Code Cleanup (SYSTEMATIC)

**File**: `src/converters/md_to_latex/converter.py`

**Remaining Issues**:
1. Line 139: Passing `use_better_bibtex_keys=self.use_better_bibtex_keys` to CitationManager
2. Lines 557-558: Using `self.use_better_bibtex_keys` in citation logic
3. Line 1085: Comment "Pre-fetch metadata to ensure Better BibTeX keys are generated"
4. Method name: `_populate_from_zotero_json` → should be `_populate_from_local_rdf`

**Fix Strategy** (do ALL at once, not piecemeal):
```python
# Line 139: Remove parameter entirely
self.citation_manager = CitationManager(
    # REMOVE: use_better_bibtex_keys=self.use_better_bibtex_keys,
)

# Lines 557-558: Simplify logic (no conditional on Better BibTeX)
# OLD:
citation.title if self.use_better_bibtex_keys else "",
use_better_bibtex=self.use_better_bibtex_keys,

# NEW:
citation.title,  # Always include title
# Remove use_better_bibtex parameter

# Line 1085: Update comment
# OLD: "Pre-fetch metadata for all citations to ensure Better BibTeX keys are generated"
# NEW: "Pre-fetch metadata for all citations"

# Method rename:
def _populate_from_local_rdf(self, citations):  # Renamed from _populate_from_zotero_json
    """Load bibliography from local RDF file."""
    # ... existing RDF parser logic
```

### PHASE 3: Update CLAUDE.md (Policy Documentation)

**Add New Section**: "Better BibTeX Keys - BANNED"

```markdown
### Better BibTeX Keys

**CRITICAL: Better BibTeX keys are BANNED from this repository.**

**Rationale**:
- Too difficult to get working consistently across all bibliography sources
- Zotero Web API doesn't support Better BibTeX key format reliably
- Local exports may have inconsistent key generation
- Causes validation warnings that flood output (1000+ lines)

**What to use instead**:
1. **Simple keys** (preferred for emergency mode):
   - `doi_10_1038_*` (from DOI)
   - `amazon_1138021016` (from ISBN)
   - `arxiv_2401_12345` (from arXiv ID)

2. **Zotero Web API keys** (for production):
   - Format: `author_title_year` (lowercase, underscores)
   - Example: `niinimaki_environmental_2020`

**Code implications**:
- NO validation of citation key format
- Accept ANY string as citation key
- Never generate keys locally (always from source)
- RDF parser generates simple keys from URLs

**Historical context**: We spent multiple sessions trying to make Better BibTeX work.
User final decision (2025-10-30): "Ban it entirely, simple keys are fine."
```

### PHASE 4: Test Conversion (Fix-Verify Loop)

**Test Command**:
```bash
uv run python scripts/deterministic_convert.py \
  "/path/to/markdown.md" \
  --rdf "/path/to/export.rdf" \
  --output-dir "/path/to/output" \
  --allow-failures
```

**Expected Flow**:
1. ✅ RDF parser loads entries (doi_*, amazon_* keys)
2. ✅ Citations extracted from markdown
3. ✅ CitationMatcher builds indices (DOI, ISBN, arXiv)
4. ✅ Matches citations by URL/identifier extraction
5. ✅ Generates references.bib
6. ✅ Compiles LaTeX → PDF
7. ✅ PDF has ZERO (?) citations

**If Errors Occur**:
- Read error message
- Identify root cause (not symptom)
- Fix ONE thing systematically
- Re-run test
- Repeat until working

### PHASE 5: Final Commit & Push

**Commit Message**:
```
fix: Complete Better BibTeX ban, RDF-only emergency mode working

BREAKING CHANGE: Better BibTeX keys are now BANNED from repository.
Use simple keys (doi_*, amazon_*, arxiv_*) or Zotero API keys instead.

Changes:
- Removed ALL use_better_bibtex_keys references from converter.py
- Renamed _populate_from_zotero_json → _populate_from_local_rdf
- Updated CLAUDE.md to document Better BibTeX ban
- RDF-only emergency mode fully functional

Tested: Conversion works with RDF file, simple keys, zero (?) citations

Closes: Emergency conversion for manuscript submission
Ref: SYSTEMATIC-FIX-PLAN-2025-10-30-EVENING.md
```

---

## SUCCESS CRITERIA

Per CLAUDE.md requirements:

1. ✅ PDF generates without LaTeX errors
2. ✅ PDF has ZERO (?) citations (must verify with Read tool)
3. ✅ PDF has ZERO (Unknown) or (Anonymous) citations
4. ✅ All citations show proper author names and years
5. ✅ references.bib has ZERO "Unknown" or "Anonymous" entries
6. ✅ LaTeX log has ZERO compilation errors
7. ✅ BibTeX log has ZERO fatal errors (warnings OK)

**User can submit manuscript TONIGHT.**

---

## LESSONS LEARNED (Principal Engineer Reflection)

### What I Did Wrong

1. **Incremental fixes without systematic analysis**
   - Fixed validation warnings (symptom)
   - Didn't fix parameter inconsistency (cause)
   - Result: More errors down the line

2. **No commits during work**
   - Made 1072 lines of changes without committing
   - Lost ability to rollback to known-good state
   - No checkpoint for debugging

3. **Didn't write plan before coding**
   - Jumped straight to fixes
   - Lost sight of big picture
   - User had to stop me and demand proper planning

### What Principal Engineer Would Do

1. **Stop → Analyze → Plan → Execute**
   - Write comprehensive plan FIRST
   - Commit plan before coding
   - Execute plan step-by-step
   - Commit after each phase

2. **Fix root causes, not symptoms**
   - Validation warnings → symptom
   - Parameter inconsistency → root cause
   - Architecture confusion → deeper cause

3. **Commit frequently**
   - After each logical unit of work
   - Create rollback points
   - Make debugging easier

4. **Test systematically**
   - One test case
   - Fix ONE thing
   - Re-test
   - Repeat until working

---

## TIMELINE

- **19:00** - Started session, discovered issues
- **19:15** - Implemented RDF parser (good!)
- **19:20** - Started whac-a-moling validation (bad!)
- **19:30** - User intervention: "stop being a junior engineer"
- **19:35** - STOP. Write this plan.
- **19:40** - Commit plan + current code
- **19:45** - Execute Phase 2 (code cleanup)
- **19:50** - Execute Phase 3 (CLAUDE.md update)
- **19:55** - Execute Phase 4 (test conversion)
- **20:00** - Fix any errors, repeat
- **20:30** - Final commit, push
- **20:35** - User has working PDF, can submit manuscript

**Total time**: 1.5 hours (if systematic)

---

## APPENDIX: Why .bib Format is Lossy

**Example: Fletcher Book**

**In RDF export**:
```xml
<bib:Book rdf:about="https://www.amazon.de/.../dp/1138021016">
    <dc:title>Craft of Use: Post-Growth Fashion</dc:title>
    <dc:identifier>
        <dcterms:URI>
            <rdf:value>https://www.amazon.de/.../dp/1138021016</rdf:value>
        </dcterms:URI>
    </dc:identifier>
    <bib:authors>
        <foaf:Person>
            <foaf:surname>Fletcher</foaf:surname>
            <foaf:givenName>Kate</foaf:givenName>
        </foaf:Person>
    </bib:authors>
</bib:Book>
```

**In .bib export**:
```bibtex
@book{fletcherCraftUsePostGrowth2016,
  title = {Craft of Use: Post-Growth Fashion},
  author = {Fletcher, Kate},
  year = {2016},
  publisher = {Routledge}
  # NOTE: URL field MISSING
  # NOTE: ISBN field MISSING
}
```

**Result**: CitationMatcher can extract ISBN from markdown Amazon URL, but has nothing to match against in .bib export.

**Solution**: Use RDF export, which preserves ALL fields.

---

**END OF SYSTEMATIC PLAN**

This plan will be executed methodically, with commits after each phase.
No more whac-a-moling. No more incremental fixes. Systematic engineering only.
