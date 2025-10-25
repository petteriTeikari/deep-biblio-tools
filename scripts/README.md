# Scripts Directory

This directory contains utility scripts for the Deep Biblio Tools project.

## Main Scripts

### 📄 `convert_markdown_to_latex.py`
**Main conversion script** - Converts markdown files to LaTeX with bibliography extraction.

```bash
# Basic usage
./convert_markdown_to_latex.py document.md

# Fast mode (no metadata fetching)
./convert_markdown_to_latex.py document.md --mode minimal

# With validation (for LLM-generated content)
./convert_markdown_to_latex.py document.md --validate

# Limited mode (only DOI/arXiv metadata)
./convert_markdown_to_latex.py document.md --mode limited
```

Features:
- Multiple conversion modes (minimal, limited, full)
- Citation validation for LLM-generated content
- Automatic PDF compilation
- Progress tracking and debug output

### 🔧 `fix_bibliography.py`
**Main bibliography fixing script** - Fixes common issues in bibliography files.

```bash
# Basic fixing
./fix_bibliography.py references.bib

# With validation against real sources
./fix_bibliography.py references.bib --validate

# Without adding explanatory notes
./fix_bibliography.py references.bib --no-notes -o fixed.bib
```

Features:
- Author name formatting (LastName, FirstName)
- "et al" parsing catastrophe fixes
- DOI extraction from URLs
- arXiv URL normalization
- Entry type detection
- Metadata enhancement from CrossRef
- Citation validation

### 🔍 `validate_llm_citations.py`
**Citation validation script** - Validates citations against real academic sources.

```bash
# Validate a bibliography file
./validate_llm_citations.py references.bib

# Validate citations in markdown
./validate_llm_citations.py document.md

# Specify output file
./validate_llm_citations.py references.bib -o validated.bib
```

Features:
- Assumes all author names may be hallucinated
- Validates against CrossRef, arXiv APIs
- Calculates confidence scores
- Caches results to minimize API calls
- Generates detailed validation reports

### 🐛 `debug_bibliography.py`
**Bibliography debugging script** - Analyzes bibliography files for issues.

```bash
./debug_bibliography.py references.bib
```

Features:
- Identifies incomplete author names
- Checks URL accessibility
- Suggests entries that can be enhanced with DOI
- Provides detailed analysis of problem entries

### 🔗 `enhance_github_citations.py`
**GitHub citation enhancement script** - Finds academic papers associated with GitHub repositories.

```bash
# Enhance GitHub citations in a bibliography
./enhance_github_citations.py references.bib

# Specify output file
./enhance_github_citations.py references.bib -o enhanced.bib
```

Features:
- Identifies GitHub repository citations
- Searches for associated academic papers
- Fetches repository metadata from GitHub API
- Searches CrossRef for related publications
- Validates authors when papers are found
- Preserves GitHub URL in notes

## Other Utility Scripts

### LaTeX Post-Processing

- `fix_latex_citations.py` - Fix LaTeX citation commands (`\cite` vs `\citep`)
  ```bash
  # Fix citations in place
  python scripts/fix_latex_citations.py document.tex

  # Preview changes
  python scripts/fix_latex_citations.py --dry-run document.tex
  ```

### Testing & Validation

- `test_citation_validity.py` - Test citation validity in generated PDFs
  ```bash
  python scripts/test_citation_validity.py output_directory/
  ```

### Bibliography Utilities

- `extract_bibliography_with_metadata.py` - Extract bibliography with full metadata
- `check_bibliography_quality.py` - Quality checks for bibliography files
- `test_zotero_connection.py` - Test Zotero API connectivity

### Development Tools

- `validate_claude_constraints.py` - Validate codebase against Claude constraints

## Archived Scripts

Older/redundant scripts have been moved to `scripts/archive/`. These include:
- Multiple `convert_drone_*.py` variants
- Multiple `fix_bibliography_*.py` variants

Use the main consolidated scripts above instead of the archived versions.

## Usage Notes

1. **For LLM-generated content**: Always use the `--validate` flag to verify author names
2. **For large files**: Use `--mode minimal` or `--mode limited` to speed up processing
3. **API Rate Limits**: Scripts automatically handle rate limiting with delays
4. **Caching**: Validation results are cached in `.cache/` to avoid repeated API calls
