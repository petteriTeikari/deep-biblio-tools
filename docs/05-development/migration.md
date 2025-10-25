# Repository Reorganization - Migration Guide

The deep-biblio-tools repository has been reorganized for better maintainability and clarity. This guide helps you migrate from the old structure to the new one.

## What Changed

### File Moves

| Old Location | New Location | Purpose |
|-------------|--------------|---------|
| `extract_complete_paper.py` | `src/parsers/extract_complete_paper.py` | Paper extraction |
| `extract_sciencedirect_paper.py` | `src/parsers/extract_sciencedirect_paper.py` | ScienceDirect parsing |
| `extract_html.py` | `src/parsers/extract_html.py` | HTML extraction |
| `extract_paper_content.py` | `src/parsers/extract_paper_content.py` | Content utilities |
| `parse_omni_scan2bim.py` | `src/parsers/parse_omni_scan2bim.py` | Omni-Scan2BIM parser |
| `process_papers_with_cache.py` | `src/processors/process_papers_with_cache.py` | Batch processing |
| `create_comprehensive_summary.py` | `src/processors/create_comprehensive_summary.py` | Summary generation |
| `*.prompt` | `prompts/` | All prompt templates |
| `extracted_content.md` | `data/extracted/` | Extracted data |

### New Directory Structure

```
deep-biblio-tools/
├── src/                    # All source code
│   ├── deep_biblio_tools/  # Main package
│   ├── parsers/           # Paper parsing modules
│   └── processors/        # Batch processing modules
├── data/                  # All data files
├── prompts/              # LLM prompt templates
├── scripts/              # Utility scripts
├── tools/                # Standalone tools
└── docs/                 # Documentation
```

## Updating Your Code

### If you were importing modules directly:

**Old way:**
```python
from extract_complete_paper import extract_complete_paper
from process_papers_with_cache import PaperProcessor
```

**New way:**
```python
from src.parsers.extract_complete_paper import extract_complete_paper
from src.processors.process_papers_with_cache import PaperProcessor
```

### If you were running scripts:

**Old way:**
```bash
python extract_complete_paper.py paper.html
python process_papers_with_cache.py /path/to/papers/
```

**New way:**
```bash
python src/parsers/extract_complete_paper.py paper.html
python src/processors/process_papers_with_cache.py /path/to/papers/
```

### For package imports:

The main `deep_biblio_tools` package remains unchanged:
```python
# These still work the same
from deep_biblio_tools import BiblioChecker
deep-biblio-md2latex paper.md
```

## Benefits of the New Structure

1. **Better Organization** - Related files are grouped together
2. **Cleaner Root** - Repository root is less cluttered
3. **Easier Navigation** - Clear separation of concerns
4. **Import Clarity** - Module paths indicate their purpose
5. **Scalability** - Easy to add new parsers or processors

## Quick Start with New Structure

1. **For paper processing:**
   ```bash
   cd deep-biblio-tools
   python src/processors/process_papers_with_cache.py /path/to/papers/
   ```

2. **For single paper extraction:**
   ```bash
   python src/parsers/extract_complete_paper.py paper.html
   ```

3. **For development:**
   ```python
   # Add src to path if needed
   import sys
   sys.path.append('path/to/deep-biblio-tools')

   # Then import normally
   from src.parsers.extract_complete_paper import extract_complete_paper
   ```

## Examples

See the `examples/` directory for updated usage examples:
- `examples/process_papers_example.py` - Shows how to use the reorganized modules

## Questions?

If you encounter any issues with the migration, please:
1. Check this guide first
2. Look at the examples in `examples/`
3. Open an issue on GitHub if needed
