# Repository Reorganization Summary

## Overview

The deep-biblio-tools repository has been reorganized to improve maintainability, clarity, and scalability. The changes group related files together and create a cleaner, more intuitive structure.

## Key Changes

### 1. Source Code Organization (`src/`)

All Python source code is now under the `src/` directory with three main components:

- **`src/deep_biblio_tools/`** - The main package for citation validation and format conversion
- **`src/parsers/`** - Specialized parsers for extracting content from academic papers
- **`src/processors/`** - Batch processing modules for handling multiple papers

### 2. Data Files (`data/`)

All data files are consolidated under `data/`:
- `data/extracted/` - Extracted content and processed files
- `data/elsevier_manual_scrape/` - Scraped HTML papers
- `data/markdown_parse/` - Parsed markdown papers
- `data/error_analysis/` - Analysis results and error reports

### 3. Prompts (`prompts/`)

All LLM prompt templates (`.prompt` files) are now in a dedicated `prompts/` directory for easy access and management.

### 4. Documentation (`docs/`)

Enhanced documentation structure with:
- Usage guides
- API documentation
- Migration guide
- Architecture overview

## Benefits

1. **Improved Modularity** - Clear separation between parsers, processors, and the main package
2. **Better Discoverability** - Related files are grouped together
3. **Cleaner Repository Root** - Less clutter in the main directory
4. **Easier Maintenance** - Clear structure makes it easier to add new features
5. **Professional Organization** - Follows Python packaging best practices

## File Mapping

| Component | Old Location | New Location |
|-----------|--------------|--------------|
| Paper parsers | Root directory | `src/parsers/` |
| Batch processors | Root directory | `src/processors/` |
| Prompt templates | Root directory | `prompts/` |
| Extracted data | Root directory | `data/extracted/` |
| Documentation | Mixed locations | `docs/` |

## Usage Examples

### Before Reorganization
```bash
python extract_complete_paper.py paper.html
python process_papers_with_cache.py /papers/
```

### After Reorganization
```bash
python src/parsers/extract_complete_paper.py paper.html
python src/processors/process_papers_with_cache.py /papers/
```

### Python Imports
```python
# New import structure
from src.parsers.extract_complete_paper import extract_complete_paper
from src.processors.process_papers_with_cache import PaperProcessor
```

## Migration Support

- See `MIGRATION.md` for detailed migration instructions
- Check `examples/process_papers_example.py` for usage examples
- The main `deep_biblio_tools` package remains unchanged

## Future Additions

The new structure makes it easy to add:
- New parsers in `src/parsers/`
- New processors in `src/processors/`
- Additional data types in `data/`
- More prompt templates in `prompts/`

This reorganization sets a solid foundation for the continued growth and maintenance of the deep-biblio-tools project.
