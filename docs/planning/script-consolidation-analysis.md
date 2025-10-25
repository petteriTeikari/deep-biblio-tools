# Script Consolidation Analysis

## Overview
This document analyzes all Python scripts in the repository to identify patterns, duplicates, and consolidation opportunities.

## Script Categories

### 1. Bibliography Processing Scripts (Core Functionality)
Scripts that handle bibliography extraction, validation, fixing, and formatting.

#### BibTeX Processing
- `scripts/bib_key_fixes.py` - Fix BibTeX key formats
- `scripts/fix_bibliography.py` - General bibliography fixing
- `scripts/fix_bibliography_errors.py` - Error correction in bibliographies
- `scripts/sort_bibliography.py` - Sort bibliography entries
- `scripts/debug_bibliography_sorting.py` - Debug sorting issues
- `scripts/convert_bib_keys_to_authoryear.py` - Convert keys to author-year format
- `scripts/convert_arxiv_citekey_authoryear.py` - ArXiv specific key conversion
- `scripts/merge_bibliographies.py` - Merge multiple .bib files
- `scripts/unique_bibentries.py` - Remove duplicate entries
- `scripts/check_bibliography_duplicates.py` - Check for duplicates

#### Citation Extraction & Validation
- `scripts/extract_citations.py` - Extract citations from documents
- `scripts/extract_drone_citations.py` - Domain-specific extraction
- `scripts/extract_refs_from_tex.py` - Extract from LaTeX
- `scripts/extract_missing_citations.py` - Find missing citations
- `scripts/validate_citations.py` - Validate citation format
- `scripts/validate_llm_citations.py` - Validate LLM-generated citations
- `scripts/validate_bibliography_entries.py` - Validate bib entries
- `scripts/fix_unknown_authors.py` - Fix missing author data
- `scripts/fix_unknown_refs.py` - Fix missing references

#### LaTeX to BibTeX Conversion
- `scripts/convert_latex_hardcoded_bibliography.py` - Convert hardcoded bibliographies
- `scripts/extract_hardcoded_bibliography.py` - Extract hardcoded entries
- `scripts/hardcode_biblio_authoryear_hyperlinks.py` - Add hyperlinks to hardcoded entries

### 2. Document Conversion Scripts
Scripts that convert between different document formats.

#### Markdown to LaTeX
- `scripts/convert_markdown_to_latex.py` - Main conversion script
- `scripts/md_to_latex.py` - Alternative implementation
- `scripts/convert_markdown_to_latex_full.py` - Full pipeline

#### Domain-Specific Converters (Drone Project)
- `scripts/convert_drone_validated.py` - Active converter
- `scripts/archive/convert_drone_*.py` - Multiple archived versions (10+ files)

#### Other Conversions
- `scripts/run_pipeline.py` - Run conversion pipeline
- `scripts/run_complete_pipeline.py` - Complete pipeline with all steps
- `scripts/clean_markdown_before_conversion.py` - Pre-process markdown

### 3. Utility Scripts
Helper scripts for various tasks.

#### Text Processing
- `scripts/remove_unresolved_links.py` - Clean up broken links
- `scripts/test_thinking_tag_removal.py` - Remove AI thinking tags
- `scripts/test_abbreviation_checker.py` - Check abbreviations
- `scripts/test_citation_style_fixer.py` - Fix citation styles

#### Development Tools
- `scripts/fix_imports.py` - Fix import statements
- `scripts/install-git-hooks.sh` - Install git hooks
- `scripts/validate_claude_constraints.py` - Validate project constraints

### 4. Archive Directory
Contains 26 scripts, mostly older versions of converters and experiments.

## Consolidation Opportunities

### Immediate Consolidation Targets

1. **Bibliography Module** (`src/bibliography/`)
   - Merge all bibliography processing scripts into cohesive modules
   - Create `BibtexProcessor`, `CitationExtractor`, `BibliographyValidator` classes
   - Estimated scripts to consolidate: 19

2. **Converter Module** (`src/converters/`)
   - Already partially exists
   - Integrate standalone conversion scripts
   - Archive drone-specific converters or create plugin system
   - Estimated scripts to consolidate: 15

3. **Utils Module** (`src/utils/`)
   - Already exists with good structure
   - Move utility scripts into existing modules
   - Estimated scripts to consolidate: 5

### Keep as Scripts
- `install-git-hooks.sh` - Shell script, not Python
- `validate_claude_constraints.py` - Development tool
- `fix_imports.py` - One-time migration tool (can be deleted after use)

### Archive/Delete Candidates
- All scripts in `scripts/archive/` - Already archived
- Test scripts that duplicate pytest tests
- One-off migration scripts after completion

## Implementation Priority

1. **High Priority**: Bibliography processing consolidation
   - Most duplicated functionality
   - Core to the project's purpose
   - Clear module structure possible

2. **Medium Priority**: Converter consolidation
   - Some already in src/converters
   - Need to preserve working converters while archiving experiments

3. **Low Priority**: Utility consolidation
   - Many are one-off tools
   - Some may be better as CLI commands

## Next Steps

1. Create detailed module structure for bibliography processing
2. Write migration plan for each script category
3. Implement consolidation in phases with tests
4. Update documentation and CLI commands
