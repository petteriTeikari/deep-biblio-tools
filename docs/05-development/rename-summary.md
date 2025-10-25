# Files to Rename Summary

This document summarizes all files that don't follow the naming convention (lowercase with hyphens).

## Categories of Files to Rename

### 1. Python Scripts and Source Files
- All Python files using underscores (`_`) instead of hyphens (`-`)
- Examples:
  - `biblio_checker.py` → `biblio-checker.py`
  - `test_citation_validity.py` → `test-citation-validity.py`
  - `citation_context_finder.py` → `citation-context-finder.py`

### 2. Shell Scripts
- `example_usage.sh` → `example-usage.sh`
- `process_biblio_theme_folder.sh` → `process-biblio-theme-folder.sh`
- `setup_claude_hooks.sh` → `setup-claude-hooks.sh`
- `setup_regex_enforcement.sh` → `setup-regex-enforcement.sh`

### 3. Markdown Files with Uppercase
- `CLEANUP_PLAN.md` → `cleanup-plan.md`
- `UADReview_*.md` → `uadreview-*.md`

### 4. Data Files
- `combined_papers.md` → `combined-papers.md`
- `error_details.csv` → `error-details.csv`
- `extracted_content.md` → `extracted-content.md`
- `full_paper_content.md` → `full-paper-content.md`
- `references_extracted.json` → `references-extracted.json`
- `validation_cache.json` → `validation-cache.json`

### 5. Log Files
- `biblio_checker.log` → `biblio-checker.log`

### 6. Backup Files
- `references_20250801_165234.bib` → `references-20250801-165234.bib`

## Excluded from Renaming
- README files (allowed exception)
- CHANGELOG files (allowed exception)
- CLAUDE files (allowed exception)
- `.git/` directory contents
- `.venv/` virtual environment files
- `.mypy_cache/` cache files
- External scraped data in `data/elsevier_manual_scrape/`

## Recommended Approach

1. **Start with project source files** (highest priority):
   - All Python files in `src/`
   - All Python files in `scripts/`
   - All Python files in `tests/`
   - All Python files in `tools/`

2. **Then handle data files**:
   - Markdown files in `data/`
   - JSON files in `data/`
   - CSV files in `data/`
   - Log files

3. **Finally handle examples and documentation**:
   - Example scripts
   - Shell scripts
   - Other documentation files

## Total Files to Rename
Approximately 3,134 files need renaming (excluding .venv, .git, .mypy_cache, and external data).
