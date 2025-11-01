# Emergency Mode Specification

**Purpose**: Complete specification for RDF-only conversion mode with zero network activity.

**Last Updated**: 2025-11-01
**Status**: Active requirement

---

## What is Emergency Mode?

**Emergency Mode** is a deterministic, reproducible conversion mode that uses ONLY data from Zotero RDF export with ZERO network activity.

**Key Principle**: Same RDF input → Same output, every time.

---

## Why Emergency Mode Exists

**Problem Solved**:
- Non-deterministic conversions (different output each time)
- Network failures causing conversion errors
- API rate limits blocking conversions
- Inconsistent results due to changing external data
- Inability to reproduce exact outputs

**User Requirement** (from planning docs):
> "Emergency mode should have ZERO network fetching, NO auto-add, NO cache. If citation not in RDF → temp key ONLY, no bibliographic data."

---

## Core Requirements (NON-NEGOTIABLE)

### 1. RDF File is MANDATORY

**MUST Hard Crash if**:
- ❌ RDF file path not provided
- ❌ RDF file doesn't exist
- ❌ RDF file is empty (0 bytes)
- ❌ RDF file can't be parsed

**Error Message Format**:
```
🚨 EMERGENCY MODE VIOLATION: No Zotero source configured!
Emergency mode requires RDF file - cannot proceed without bibliography source.
```

**Implementation**: `converter.py:1095-1100`

### 2. ZERO Network Activity

**BANNED Operations**:
- ❌ HTTP/HTTPS requests to ANY external service
- ❌ DOI resolution (doi.org, crossref.org)
- ❌ arXiv API calls
- ❌ CrossRef API calls
- ❌ Zotero Web API calls
- ❌ ISBN lookups
- ❌ Any metadata fetching

**Verification**:
```bash
# Monitor network during conversion
sudo tcpdump -i any 'port 80 or port 443' &
python scripts/deterministic_convert.py --rdf file.rdf input.md

# Should see ZERO HTTP traffic from Python process
```

### 3. NO Cache Use

**BANNED**:
- ❌ Reading from cache files
- ❌ Writing to cache files
- ❌ Using cached API responses
- ❌ Any persistent storage of fetched data

**Reason**: Cache may contain fetched data from previous non-emergency runs, violating RDF-only requirement.

**Flag**: Always use `--no-cache` in emergency mode

### 4. NO Auto-Add to Zotero

**BANNED**:
- ❌ Attempting to add missing citations to Zotero
- ❌ Calling Zotero translation server
- ❌ Modifying Zotero collection
- ❌ Any writes to Zotero database/API

**Reason**: Auto-add requires network (violates requirement #2)

### 5. Missing Citations Handling

**When citation NOT found in RDF**:

1. ✅ **Generate temp key**: `failedAutoAdd_{hash(url)}`
2. ✅ **Add to .tex file**: `\citep{failedAutoAdd_011964}`
3. ✅ **Track in failed_citations list**: `(url, ["Not found in RDF export"])`
4. ❌ **NEVER add to references.bib** (must be filtered out)
5. ✅ **Result**: Shows as (?) in PDF

**Implementation**:
- Key generation: `citation_manager.py:684`
- Tracking: `citation_manager.py:687`
- Filtering: `citation_manager.py:1792-1805`

### 6. failedAutoAdd BANNED from .bib

**CRITICAL**: failedAutoAdd keys MUST be filtered out of references.bib

**Why**: In the past, failedAutoAdd entries contained FETCHED metadata (authors, titles, years), violating RDF-only requirement.

**Current Behavior** (CORRECT):
```python
# citation_manager.py:1792-1805
filtered_citations = [
    (key, citation)
    for key, citation in citations_list
    if not key.startswith("failedAutoAdd_")
]
```

**Result**:
- 71 failedAutoAdd keys in .tex ✅
- 0 failedAutoAdd keys in .bib ✅
- (?) appears in PDF for missing ✅

---

## Workflow Diagram

```
┌─────────────────────┐
│  Markdown Input     │
│  mcp-draft-v5.md    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Extract Citations  │
│  (308 total)        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Filter Non-Academic│
│  (123 filtered)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Load Zotero RDF    │
│  (665 entries)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Match Citations    │
│  URL → RDF Entry    │
└──────────┬──────────┘
           │
           ├─────────────┐
           │             │
    FOUND in RDF    NOT FOUND
           │             │
           ▼             ▼
  ┌────────────┐  ┌─────────────────┐
  │Use RDF Data│  │Generate temp key│
  │(210 matched)│  │failedAutoAdd_*  │
  └─────┬──────┘  └────────┬────────┘
        │                  │
        │                  │
        ▼                  ▼
  ┌────────────────────────────┐
  │   Generate references.bib   │
  │   (FILTER OUT failedAutoAdd)│
  └──────────┬─────────────────┘
             │
             ▼
  ┌───────────────────┐
  │  Compile LaTeX    │
  │  + BibTeX         │
  └─────────┬─────────┘
            │
            ▼
  ┌─────────────────────┐
  │     PDF Output      │
  │  210 with authors   │
  │  98 with (?)        │
  └─────────────────────┘
```

---

## Command Line Usage

### Correct Emergency Mode Invocation:
```bash
uv run python scripts/deterministic_convert.py \
    "/path/to/input.md" \
    --rdf "/path/to/zotero-export.rdf" \
    --output-dir "/path/to/input/output" \
    --allow-failures \
    --no-cache
```

**Flags Explained**:
- `--rdf PATH`: REQUIRED - path to Zotero RDF export
- `--output-dir PATH`: Where to save outputs (NOT /tmp)
- `--allow-failures`: Continue despite missing citations (don't crash)
- `--no-cache`: Don't use cached API responses

### What Happens:
1. Loads RDF file
2. Extracts citations from markdown
3. Matches citations to RDF entries (URL-based matching)
4. For matches: Uses full RDF metadata
5. For misses: Generates failedAutoAdd temp key
6. Generates references.bib (filters out failedAutoAdd)
7. Compiles LaTeX + BibTeX
8. Generates PDF with (?) for missing citations
9. Auto-generates missing citations reports

---

## Success Criteria

**ALL of these must be true**:

1. ✅ **Conversion completes** without crashing
2. ✅ **PDF generated** and compilable
3. ✅ **Citation counts match**: Total = Matched + Missing
   - Example: 308 total = 210 matched + 98 missing
4. ✅ **references.bib has ZERO**:
   - failedAutoAdd_* entries
   - Unknown authors
   - Anonymous authors
5. ✅ **Missing citations reports generated**:
   - `output/missing-citations-report.json`
   - `output/missing-citations-review.csv`
6. ✅ **PDF shows (?) for missing** citations (expected behavior)
7. ✅ **Matched citations show proper** author names (not ?)
8. ✅ **Zero network activity** (verify with tcpdump/wireshark)
9. ✅ **Output directory correct** (input_dir/output/, NOT /tmp)

**NOT Failures**:
- ⚠️ (?) in PDF for papers not in RDF (this is correct)
- ⚠️ 98 missing citations reported (user needs to add to Zotero)
- ⚠️ BibTeX warnings about missing citations (expected)

---

## Verification Commands

### 1. Check Citation Counts Match:
```bash
# From conversion output
grep "Citations extracted:" output.log
grep "Missing:" output.log

# Should see: Total = Matched + Missing
```

### 2. Verify ZERO failedAutoAdd in .bib:
```bash
grep -c "failedAutoAdd" output/references.bib
# Must return: 0
```

### 3. Verify Missing Reports Exist:
```bash
ls -lh output/missing-citations-report.json output/missing-citations-review.csv
# Both files must exist
```

### 4. Count (?) in PDF:
```bash
pdftotext output/file.pdf - | grep -o "(\?)" | wc -l
# Should approximately match missing count
```

### 5. Verify No Network Activity:
```bash
# During conversion, monitor network
strace -e trace=network python scripts/deterministic_convert.py ... 2>&1 | grep -i "connect\|socket"
# Should see only local connections, NO external
```

---

## Common Violations and Fixes

### Violation 1: Web Fetching Detected

**Symptom**: Seeing HTTP requests in logs
```
INFO: Fetching metadata from doi.org...
INFO: Querying CrossRef API...
```

**Fix**: Check for code that bypasses emergency mode checks
```bash
grep -rn "requests.get\|urllib.request" src/converters/md_to_latex/
```

**Hard-code ban**: All fetching must check `if self.emergency_mode: return` first

### Violation 2: failedAutoAdd in .bib

**Symptom**: `grep -c "failedAutoAdd" references.bib` returns > 0

**Fix**: Check filtering in `citation_manager.py:1792-1805`
```python
# MUST filter out failedAutoAdd
if not key.startswith("failedAutoAdd_"):
    # Only add to filtered_citations if NOT failedAutoAdd
```

### Violation 3: Cache Being Used

**Symptom**: Conversion too fast (< 5 seconds for 300 citations)

**Fix**: Ensure `--no-cache` flag passed and cache code respects it

### Violation 4: Missing Reports Not Generated

**Symptom**: `missing-citations-report.json` doesn't exist

**Fix**: Check `converter.py:1171-1244` - reports should auto-generate if `failed_citations` list not empty

**Bug Fixed** (2025-11-01): Was checking for `citation.authors == "Unknown"` but emergency mode extracts authors from markdown, so never "Unknown". Now uses `self.citation_manager.failed_citations` list.

---

## Historical Context

### Why Emergency Mode Was Created

**Problem History** (from planning docs):
1. Oct 26: Validation reports claimed "FIXED" but never applied fixes
2. Oct 31: User discovered URLs still broken (Google A2A, CIRPASS)
3. Discovery: Fetched data was being used, causing non-deterministic builds
4. Solution: Ban ALL fetching, use ONLY RDF data

### The failedAutoAdd Ban Saga

**Timeline**:
- Pre-2025-10-30: failedAutoAdd entries had FETCHED metadata
- 2025-10-30: User repeatedly asked to ban failedAutoAdd
- 2025-10-30 23:59: Finally banned from .bib (commit c7d0803)
- 2025-11-01: Bug fixed - reports now track all failed citations

**Key Learning**: failedAutoAdd keys are OK in .tex (LaTeX needs some key), but BANNED from .bib (would contain phantom entries).

---

## Related Documents

- **Quick Reference**: `.claude/CITATION-REQUIREMENTS.md` section 1
- **Success Criteria**: `.claude/CLAUDE.md:463-523`
- **Missing Citations**: `.claude/CLAUDE.md:361-390`
- **Planning History**: `docs/planning/EMERGENCY-MODE-ZERO-FETCH-PLAN-2025-10-31.md`
- **Consolidated Plan**: `docs/planning/CONSOLIDATED-EMERGENCY-MODE-PLAN-2025-10-31.md`
- **Violation Report**: `docs/planning/EMERGENCY-MODE-VIOLATION-MEA-CULPA.md`

---

## Summary

**Emergency Mode in 3 Rules**:

1. **RDF ONLY** - No network, no cache, no auto-add
2. **failedAutoAdd in .tex, NOT in .bib** - Missing citations show as (?)
3. **Reports MUST auto-generate** - User needs list of what to add to Zotero

**Remember**: (?) in PDF is CORRECT behavior for missing citations. The goal is accurate citations, not zero (?).
