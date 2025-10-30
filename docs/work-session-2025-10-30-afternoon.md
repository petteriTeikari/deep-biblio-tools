# Work Session: 2025-10-30 Afternoon - PDF Quality Fix

## Session Goal
Fix MD→LaTeX→PDF conversion to produce zero garbage citations. Iterate until perfect.

## Actions Taken

###  1. Updated CLAUDE.md
Added CRITICAL RULE #1: `references.bib` is EPHEMERAL - never static, always regenerated.
- Commit: fdb74c3

### 2. Fixed click.Exit Bug
- **Issue**: `click.Exit(1)` raised `AttributeError` in exception handler
- **Fix**: Added `import sys` and replaced with `sys.exit(1)`
- **Commit**: 491c561

### 3. Conversion Strategy Change
**Problem**: `--auto-add-real` mode too slow - calls translation server for every missing citation
- First attempt with `--auto-add-real`: Ran 10+ minutes, hung at 25% (extracting citations)
- Multiple competing processes were running, killed all

**Current Approach**: Running with `--auto-add-dry-run`
- Started: 14:50 UTC (process ID: 380811)
- Status: Running 2+ minutes, still in citation extraction phase
- Progress: Extracted 578 links, matching against 663 Zotero entries
- Observation: Even dry-run calls translation server for missing citations (slow)

### 4. Translation Server Issues Found
From logs:
- Server running on localhost:1969 (404 on root is expected) ✓
- Many citations failing with HTTP 400 errors:
  - `https://doi.org/10.1016/j.spc.2025.03.020`
  - `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023R1542`
  - `https://cirpassproject.eu/results`
- Each failed URL retried multiple times → significant slowdown

## Current Status (14:52 UTC)

**Conversion Progress**: Running (380811) - still extracting/matching citations
- Loaded 663 entries from Zotero successfully ✓
- Extracted 578 total links from markdown ✓
- Calling translation server for missing citations (slow even in dry-run)
- No PDF or references.bib generated yet

**Files Generated**:
- `mcp-draft-refined-v4-TABLES.md` only (table stripping worked)

## Known Issues from Previous Session

1. **Garbage BibTeX Entries** (user-reported):
   ```bibtex
   @article{david_m_rothschild_agentic_2025,
     author = "David M. Rothschild...",
     title = "On the momentum of gluons in Lattice Gauge Theory",  # WRONG TITLE!
   }
   ```

2. **Fletcher Rendering**: "Fletcher K (2016) Amazon.de" instead of full book title

3. **Organization Names**: "Commission E" vs "European Commission"

4. **Missing Hyperlinks**: Citations not clickable in PDF

5. **Dryrun Keys**: `dryrun_1761780981742` appearing in old output

## Next Steps (Once Conversion Completes)

1. Wait for process 380811 to complete (may take 10-30 more minutes)
2. Check generated `references.bib` for garbage entries
3. Inspect PDF for (?) citations
4. If issues found:
   - Analyze root cause (Zotero data vs code bug vs LaTeX style)
   - Fix code/data
   - Re-run conversion
5. Iterate until PDF has ZERO issues

## Performance Observations

**Problem**: Auto-add (even dry-run) is bottleneck
- Translation server calls: ~2 seconds per URL (with retries)
- Estimated missing citations: 100-200 based on past runs
- Total time for auto-add phase: 3-10 minutes minimum

**Possible Optimization** (for future):
- Skip translation server calls entirely in dry-run
- Generate temp keys immediately for missing citations
- Only call translation server when `--auto-add-real` is used

## Files Modified This Session
- `.claude/CLAUDE.md`: Added references.bib ephemeral warning (fdb74c3)
- `src/cli_md_to_latex.py`: Fixed click.Exit bug (491c561)
- `docs/work-session-2025-10-30-afternoon.md`: This document

## Commits This Session
1. `fdb74c3`: docs: Add critical rule about references.bib being ephemeral
2. `4fbb8c6`: docs: Add work session 2025-10-30 afternoon progress
3. `491c561`: fix: Replace click.Exit with sys.exit for proper error handling

## Time Spent
- Documentation updates: 15 min
- Bug fixes: 10 min
- Conversion attempts and monitoring: 40 min+ (ongoing)
- **Total**: 65+ minutes (process still running)

## Expected Completion
- Conversion should complete: 15:05-15:20 UTC (another 15-30 min)
- Will update this document when PDF is ready to inspect
