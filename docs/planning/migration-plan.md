# Script Consolidation Migration Plan

## Overview

This plan details how to migrate 89 scripts into the new module structure while maintaining functionality and ensuring nothing breaks.

## Migration Principles

1. **Test First**: Write tests before migrating functionality
2. **Incremental**: Migrate one script at a time
3. **Backwards Compatible**: Keep scripts working during migration
4. **Document Everything**: Update docs as we go
5. **No Regex**: Use AST parsers per project policy

## Phase-by-Phase Migration

### Phase 2.1: Core Infrastructure (Days 3-4)

#### Day 3: Base Classes and Exceptions

1. Create `src/bibliography/__init__.py`
2. Create `src/bibliography/core.py`:
   ```python
   from pathlib import Path
   from typing import List, Dict, Any, Optional
   from abc import ABC, abstractmethod

   class BibliographyEntry:
       """Represents a single bibliography entry."""
       def __init__(self, entry_type: str, key: str, fields: Dict[str, Any]):
           self.entry_type = entry_type
           self.key = key
           self.fields = fields

   class Bibliography:
       """Collection of bibliography entries."""
       def __init__(self):
           self.entries: List[BibliographyEntry] = []

       @classmethod
       def from_file(cls, filepath: Path) -> "Bibliography":
           """Load from BibTeX file."""
           pass

       def to_file(self, filepath: Path) -> None:
           """Save to BibTeX file."""
           pass
   ```

3. Create `src/core/exceptions.py`:
   ```python
   class BibliographyError(Exception):
       """Base exception for bibliography errors."""
       pass

   class ParsingError(BibliographyError):
       """Error parsing bibliography file."""
       pass

   class ValidationError(BibliographyError):
       """Validation error in bibliography entry."""
       pass
   ```

4. Create tests:
   - `tests/bibliography/test_core.py`
   - `tests/core/test_exceptions.py`

#### Day 4: API Clients Infrastructure

1. Create `src/utils/api_clients/__init__.py`
2. Create base client with rate limiting:
   ```python
   # src/utils/api_clients/base.py
   from abc import ABC, abstractmethod
   import time
   from typing import Optional

   class APIClient(ABC):
       """Base class for API clients with rate limiting."""
       def __init__(self, rate_limit: float = 1.0):
           self.rate_limit = rate_limit
           self._last_request = 0.0

       def _rate_limit_wait(self):
           """Wait if necessary to respect rate limit."""
           elapsed = time.time() - self._last_request
           if elapsed < self.rate_limit:
               time.sleep(self.rate_limit - elapsed)
           self._last_request = time.time()
   ```

3. Implement specific clients:
   - `src/utils/api_clients/crossref.py`
   - `src/utils/api_clients/arxiv.py`
   - `src/utils/api_clients/zotero.py`

### Phase 2.2: Simple Processors Migration (Days 5-6)

#### Day 5: Formatter and Sorter

**Migrate Citation Key Formatting**

Scripts to consolidate:
- `bib_key_fixes.py`
- `convert_bib_keys_to_authoryear.py`
- `convert_arxiv_citekey_authoryear.py`

1. Create `src/bibliography/formatter.py`:
   ```python
   class CitationKeyFormatter:
       def to_authoryear(self, entry: BibliographyEntry) -> str:
           """Convert to Author2023 format."""
           # Migrate logic from convert_bib_keys_to_authoryear.py

       def to_numeric(self, entry: BibliographyEntry) -> str:
           """Convert to numeric format."""

       def fix_arxiv_keys(self, bibliography: Bibliography) -> None:
           """Fix arXiv-specific keys."""
           # Migrate from convert_arxiv_citekey_authoryear.py
   ```

2. Create wrapper script for backwards compatibility:
   ```python
   # scripts/convert_bib_keys_to_authoryear.py
   #!/usr/bin/env python3
   """Backwards compatibility wrapper."""
   import warnings
   from src.bibliography import Bibliography, CitationKeyFormatter

   warnings.warn(
       "This script is deprecated. Use 'deep-biblio bib format' instead.",
       DeprecationWarning
   )

   # Original functionality using new modules
   ```

**Migrate Sorting**

Scripts to consolidate:
- `sort_bibliography.py`
- `debug_bibliography_sorting.py`

1. Create `src/bibliography/sorter.py`
2. Add sorting methods (by key, by year, by author)
3. Create tests and compatibility wrapper

#### Day 6: Deduplicator

Scripts to consolidate:
- `unique_bibentries.py`
- `check_bibliography_duplicates.py`
- `fix_duplicate_bibliography.py`
- `merge_bibliographies.py`

1. Create `src/bibliography/deduplicator.py`
2. Implement duplicate detection algorithms
3. Add merge functionality
4. Create comprehensive tests

### Phase 2.3: Complex Processors (Week 2, Days 7-10)

#### Day 7-8: Parser and Validator

**Parser** - Consolidate all parsing logic:
- Use bibtexparser as base
- Add custom parsing for edge cases
- Implement robust error handling

**Validator** - Consolidate validation scripts:
- `validate_citations.py`
- `validate_bibliography_entries.py`
- `check_bibliography_quality.py`
- `validate_llm_citations.py`

#### Day 9-10: Fixer and Resolver

**Fixer** - Consolidate all fix scripts:
- `fix_bibliography.py`
- `fix_bibliography_errors.py`
- `fix_bibliography_ampersands.py`
- `fix_incomplete_authors.py`
- `fix_unknown_authors.py`
- `fix_unknown_refs.py`

**Resolver** - External data resolution:
- DOI resolution via CrossRef
- ArXiv metadata fetching
- Author disambiguation

### Phase 2.4: Integration (Week 2, Days 11-12)

1. Create unified CLI in `src/cli.py`
2. Update existing converters to use new modules
3. Update documentation
4. Create migration guide for users

## Script Migration Checklist

For each script being migrated:

- [ ] Analyze script functionality
- [ ] Identify target module(s)
- [ ] Write unit tests for the functionality
- [ ] Implement in new module
- [ ] Verify tests pass
- [ ] Create compatibility wrapper
- [ ] Add deprecation warning
- [ ] Update documentation
- [ ] Add to migration log

## Testing Strategy

1. **Unit Tests**: Each new module gets comprehensive tests
2. **Integration Tests**: Test module interactions
3. **Regression Tests**: Ensure scripts still work
4. **Performance Tests**: Ensure no performance degradation

## Rollback Plan

If issues arise:
1. Scripts remain functional via wrappers
2. Can revert module changes without affecting scripts
3. Git branches for each major migration phase

## Success Metrics

- All 89 scripts either migrated or explicitly kept
- Test coverage > 80% for new modules
- No functionality lost
- Performance maintained or improved
- Clear documentation for all changes

## Migration Tracking

Create `docs/planning/migration-log.md` to track:
- Which scripts have been migrated
- Any issues encountered
- Performance comparisons
- User feedback

## Communication Plan

1. Update README with migration status
2. Create CHANGELOG entries
3. Announce deprecations clearly
4. Provide migration guide for users
