# Core Library Module Structure Design

## Overview

This document outlines the target module structure for consolidating 89 scripts into a well-organized library.

## Proposed Module Structure

```
src/
├── __init__.py
├── __main__.py
├── cli.py                    # Unified CLI entry point
│
├── bibliography/             # Core bibliography processing
│   ├── __init__.py
│   ├── core.py              # Base classes and interfaces
│   ├── parser.py            # BibTeX parsing with AST
│   ├── formatter.py         # Citation key formatting
│   ├── validator.py         # Entry validation
│   ├── fixer.py            # Error correction
│   ├── merger.py           # Merge bibliographies
│   ├── deduplicator.py     # Remove duplicates
│   ├── sorter.py           # Sort entries
│   ├── extractor.py        # Extract citations from text
│   ├── resolver.py         # Resolve missing data
│   └── llm/                # LLM-specific handling
│       ├── __init__.py
│       ├── validator.py    # Validate LLM citations
│       └── corrector.py    # Fix hallucinated entries
│
├── converters/              # Document converters (existing)
│   ├── __init__.py
│   ├── md_to_latex/        # Markdown to LaTeX (existing)
│   ├── to_lyx/             # LaTeX/MD to LyX (existing)
│   ├── latex_to_bibtex/    # NEW: Hardcoded bib extraction
│   │   ├── __init__.py
│   │   ├── extractor.py
│   │   └── formatter.py
│   └── preprocessor.py     # Common preprocessing
│
├── utils/                   # Utilities (enhance existing)
│   ├── __init__.py
│   ├── cache.py            # (existing)
│   ├── validators.py       # (existing)
│   ├── extractors.py       # (existing)
│   ├── link_cleaner.py     # NEW: Clean broken links
│   ├── ai_artifacts.py     # NEW: Remove AI artifacts
│   └── api_clients/        # NEW: External API clients
│       ├── __init__.py
│       ├── crossref.py
│       ├── arxiv.py
│       └── zotero.py
│
├── core/                    # Core functionality (existing)
│   ├── __init__.py
│   ├── biblio_checker.py   # (existing)
│   └── exceptions.py       # NEW: Custom exceptions
│
└── config/                  # Configuration (existing)
    ├── __init__.py
    └── settings.py
```

## Module Descriptions

### 1. Bibliography Module (`src/bibliography/`)

The heart of the consolidation effort. This module will absorb ~39 scripts.

#### Core Components

**`core.py`** - Base classes and interfaces
```python
class BibliographyEntry:
    """Single bibliography entry with validation."""

class Bibliography:
    """Collection of entries with operations."""

class BibliographyProcessor(ABC):
    """Base class for all processors."""
```

**`parser.py`** - AST-based parsing (no regex!)
```python
class BibtexParser:
    """Parse BibTeX using bibtexparser library."""

    def parse_file(self, filepath: Path) -> Bibliography
    def parse_string(self, content: str) -> Bibliography
```

**`formatter.py`** - Citation key formatting
```python
class CitationKeyFormatter:
    """Format citation keys in various styles."""

    def to_authoryear(self, entry: BibliographyEntry) -> str
    def to_numeric(self, entry: BibliographyEntry) -> str
    def fix_arxiv_keys(self, bibliography: Bibliography) -> None
```

**`validator.py`** - Entry validation
```python
class BibliographyValidator:
    """Validate bibliography entries."""

    def validate_entry(self, entry: BibliographyEntry) -> List[str]
    def validate_urls(self, entry: BibliographyEntry) -> bool
    def check_required_fields(self, entry: BibliographyEntry) -> bool
```

**`fixer.py`** - Error correction
```python
class BibliographyFixer:
    """Fix common errors in bibliographies."""

    def fix_encoding(self, bibliography: Bibliography) -> None
    def fix_author_names(self, bibliography: Bibliography) -> None
    def fix_ampersands(self, bibliography: Bibliography) -> None
```

**`resolver.py`** - Resolve missing data
```python
class DataResolver:
    """Resolve missing bibliography data from external sources."""

    def resolve_doi(self, doi: str) -> BibliographyEntry
    def resolve_arxiv(self, arxiv_id: str) -> BibliographyEntry
    def resolve_authors(self, entry: BibliographyEntry) -> None
```

### 2. Converters Module Enhancements

Add `latex_to_bibtex` submodule for hardcoded bibliography extraction:

**`converters/latex_to_bibtex/extractor.py`**
```python
class HardcodedBibliographyExtractor:
    """Extract hardcoded bibliographies from LaTeX."""

    def extract_from_file(self, tex_file: Path) -> Bibliography
    def extract_from_string(self, content: str) -> Bibliography
```

### 3. Utils Module Enhancements

**`utils/link_cleaner.py`**
```python
class LinkCleaner:
    """Remove or fix broken links in documents."""

    def clean_markdown(self, content: str) -> str
    def validate_urls(self, urls: List[str]) -> Dict[str, bool]
```

**`utils/ai_artifacts.py`**
```python
class AIArtifactCleaner:
    """Remove AI-generated artifacts from text."""

    def remove_thinking_tags(self, content: str) -> str
    def clean_llm_artifacts(self, content: str) -> str
```

**`utils/api_clients/`** - Centralized API access
- Rate limiting
- Caching
- Error handling
- Retry logic

### 4. CLI Module (`src/cli.py`)

Unified command-line interface consolidating all script functionality:

```python
@click.group()
def cli():
    """Deep Biblio Tools - Bibliography and document processing."""
    pass

@cli.group()
def bib():
    """Bibliography processing commands."""
    pass

@bib.command()
def validate():
    """Validate bibliography entries."""

@bib.command()
def fix():
    """Fix bibliography errors."""

@bib.command()
def merge():
    """Merge multiple bibliography files."""

@cli.group()
def convert():
    """Document conversion commands."""
    pass
```

## Migration Strategy

### Phase 2.1: Create Core Infrastructure (Days 3-4)
1. Create `bibliography/core.py` with base classes
2. Create `core/exceptions.py` for custom exceptions
3. Set up `utils/api_clients/` with rate limiting

### Phase 2.2: Migrate Simple Processors (Days 5-6)
1. Start with `formatter.py` - migrate key formatting scripts
2. Move to `sorter.py` - simple, well-defined functionality
3. Implement `deduplicator.py` - consolidate duplicate removal

### Phase 2.3: Migrate Complex Processors (Week 2)
1. Implement `parser.py` with robust error handling
2. Create `validator.py` combining all validation scripts
3. Build `fixer.py` consolidating all fix scripts
4. Develop `resolver.py` for external data resolution

### Phase 2.4: Update Existing Modules (Week 2)
1. Enhance converters with new latex_to_bibtex
2. Update utils with new functionality
3. Create unified CLI

## Benefits

1. **Reduced Duplication**: 39 scripts → 10 modules
2. **Better Organization**: Clear separation of concerns
3. **Easier Testing**: Modular structure enables unit testing
4. **API Access**: Can be used as library, not just CLI
5. **Maintainability**: Related functionality grouped together
6. **Extensibility**: Easy to add new processors/validators

## Example Usage

```python
from src.bibliography import Bibliography, BibliographyFixer, BibliographyValidator

# Load and fix a bibliography
bib = Bibliography.from_file("references.bib")
fixer = BibliographyFixer()
fixer.fix_encoding(bib)
fixer.fix_author_names(bib)

# Validate entries
validator = BibliographyValidator()
for entry in bib.entries:
    errors = validator.validate_entry(entry)
    if errors:
        print(f"Entry {entry.key}: {errors}")

# Save fixed bibliography
bib.to_file("references_fixed.bib")
```

## Testing Strategy

Each module will have comprehensive tests:
- `tests/bibliography/test_parser.py`
- `tests/bibliography/test_formatter.py`
- `tests/bibliography/test_validator.py`
- etc.

This ensures functionality is preserved during migration.
