# Work Session: 2025-10-30 Afternoon - PDF Quality Fix

## Session Goal
Fix MD→LaTeX→PDF conversion to produce zero garbage citations. Iterate until perfect.

## Actions Taken

###  1. Updated CLAUDE.md
Added CRITICAL RULE #1: `references.bib` is EPHEMERAL - never static, always regenerated.
- Commit: fdb74c3

### 2. Started Conversion with--allow-failures
Running conversion with:
- `--allow-failures`: Continue past citation failures
- `--auto-add-real`: Actually add to Zotero (not dry-run)
- Translation server: Running on localhost:1969 (responds with 404 on root - expected)

### 3. User's Critical Issue: Garbage BibTeX Entries
User showed examples with KEY/CONTENT mismatches:
```bibtex
@article{david_m_rothschild_agentic_2025,
  author = "David M. Rothschild...",
  title = "On the momentum of gluons in Lattice Gauge Theory",  # WRONG TITLE!
}
```

This is CRITICAL - suggests either:
1. Old stale references.bib being read
2. Bug in BibTeX generation
3. Garbage already in Zotero from bad auto-add

### 4. Code Analysis
Verified `generate_bibtex_file()` uses "w" mode (line 1680 in citation_manager.py) - SHOULD overwrite completely.

## Current Status

**Conversion Progress**: Running (6433be) - stuck at 25% (extracting citations)
- Loaded 663 entries from Zotero successfully
- Translation server responding
- Using allow-failures mode

**Old Background Processes**: ALL failed without --allow-failures (crashed on PDF URL)

## Next Steps (Once Conversion Completes)

1. Check generated `references.bib` for garbage entries
2. If garbage found, trace source (Zotero vs code bug)
3. Check generated PDF for (?) citations
4. Fix identified issues
5. Re-run conversion
6. **ITERATE** until PDF has ZERO issues

## Files Modified This Session
- `.claude/CLAUDE.md`: Added references.bib ephemeral warning

## Known Issues to Fix
- Fletcher rendering: "Fletcher K (2016) Amazon.de" instead of full title
- Organization names: "Commission E" vs "European Commission"
- Missing hyperlinks in PDF
- Possible hallucinated arXiv titles

## Time Spent
- Documentation updates: 10 min
- Conversion monitoring: 30 min+ (still running)
