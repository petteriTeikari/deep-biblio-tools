# Source Code Organization

This directory contains all the source code for the deep-biblio-tools project, organized into logical modules.

## Directory Structure

### `deep_biblio_tools/`
The main package containing the core functionality:
- **Citation validation** - Extract and validate academic citations
- **Format conversion** - Convert between Markdown, LaTeX, and LyX
- **Web interface** - Interactive proofreading tool

### `parsers/`
Specialized parsers for extracting content from academic papers:
- `extract_complete_paper.py` - Main entry point for paper extraction
- `extract_sciencedirect_paper.py` - ScienceDirect-specific HTML parsing
- `extract_html.py` - General HTML paper extraction
- `extract_paper_content.py` - Content extraction utilities

### `processors/`
Batch processing modules for handling multiple papers:
- `process_papers_with_cache.py` - Process papers with MD5-based caching
- `create_comprehensive_summary.py` - Generate literature reviews from summaries

## Usage Examples

### Using Parsers

```python
from src.parsers.extract_complete_paper import extract_complete_paper

# Extract content from a ScienceDirect HTML file
content = extract_complete_paper("path/to/paper.html")
print(f"Extracted {len(content)} characters")
```

### Using Processors

```python
from src.processors.process_papers_with_cache import PaperProcessor, PaperCache

# Initialize cache
cache = PaperCache("my_cache.json")

# Process directory of papers
processor = PaperProcessor(cache)
processor.process_directory("path/to/papers/", force_reprocess=[])
```

### Integration with Main Package

The parser and processor modules can be imported and used alongside the main deep_biblio_tools package:

```python
# Use citation validation
from deep_biblio_tools.core.biblio_checker import BiblioChecker

# Use paper extraction
from src.parsers.extract_sciencedirect_paper import extract_sciencedirect_content

# Combine both for comprehensive processing
checker = BiblioChecker()
content = extract_sciencedirect_content("paper.html")
validated = checker.validate_content(content)
```

## Module Dependencies

- **parsers**: BeautifulSoup4 for HTML parsing
- **processors**: Standard library only (json, hashlib, pathlib)
- **deep_biblio_tools**: See main package requirements

## Development

When adding new parsers or processors:
1. Follow the existing naming conventions
2. Add proper docstrings and type hints
3. Update the `__init__.py` files
4. Add corresponding tests in the tests/ directory
