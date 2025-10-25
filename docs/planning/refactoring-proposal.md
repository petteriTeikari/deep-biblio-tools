# Deep-Biblio-Tools Refactoring Proposal

## Executive Summary

This proposal outlines a comprehensive refactoring of the deep-biblio-tools repository to improve maintainability, determinism, and integration with Claude Code. The refactoring focuses on modularization, clear workflows, and better testing infrastructure.

## Current Architecture Issues

### 1. Script Proliferation
- 81 scripts in `/scripts/` with overlapping functionality
- Multiple versions of similar scripts (e.g., fix_bibliography variants)
- Lack of clear entry points for common workflows

### 2. Documentation Fragmentation
- Documentation spread across 76 markdown files
- Multiple README files at different levels
- Claude-specific documentation mixed with general docs

### 3. Testing Gaps
- Many scripts without corresponding tests
- Integration tests not covering full workflows
- No clear testing strategy for bibliography validation

### 4. Configuration Complexity
- Multiple configuration approaches
- Settings scattered across files
- No centralized configuration management

## Proposed New Architecture

### 1. Core Library Structure

```
src/deep_biblio_tools/
├── api/                    # High-level API for common workflows
│   ├── __init__.py
│   ├── workflows.py       # Complete workflow implementations
│   └── pipeline.py        # Pipeline orchestration
├── bibliography/          # All bibliography-related functionality
│   ├── __init__.py
│   ├── extractors/       # Extract from various sources
│   │   ├── markdown.py
│   │   ├── latex.py
│   │   └── pdf.py
│   ├── validators/       # Validation logic
│   │   ├── authors.py
│   │   ├── citations.py
│   │   └── metadata.py
│   ├── fixers/          # Fix common issues
│   │   ├── authors.py
│   │   ├── formatting.py
│   │   └── encoding.py
│   ├── enrichers/       # Add metadata
│   │   ├── doi.py
│   │   ├── arxiv.py
│   │   └── crossref.py
│   └── formats/         # Format conversions
│       ├── bibtex.py
│       ├── biblatex.py
│       └── hardcoded.py
├── converters/           # Document conversion
│   ├── __init__.py
│   ├── markdown/        # Markdown processing
│   │   ├── parser.py
│   │   ├── ast_visitor.py
│   │   └── renderer.py
│   ├── latex/           # LaTeX generation
│   │   ├── builder.py
│   │   ├── templates.py
│   │   └── commands.py
│   └── pipeline.py      # Conversion pipeline
├── utils/               # Shared utilities
│   ├── __init__.py
│   ├── cache.py        # Citation caching
│   ├── config.py       # Configuration management
│   ├── logging.py      # Centralized logging
│   └── errors.py       # Custom exceptions
└── cli/                # Command-line interface
    ├── __init__.py
    ├── main.py         # Main entry point
    └── commands/       # CLI commands
        ├── convert.py
        ├── validate.py
        ├── fix.py
        └── extract.py
```

### 2. Simplified Script Structure

```
scripts/
├── workflows/           # High-level workflow scripts
│   ├── convert_markdown_to_latex.py
│   ├── validate_bibliography.py
│   └── fix_all_issues.py
├── utilities/          # Standalone utilities
│   ├── check_cache.py
│   ├── clean_temp_files.py
│   └── export_statistics.py
└── dev/               # Development tools
    ├── run_tests.py
    ├── update_docs.py
    └── check_constraints.py
```

### 3. Test Architecture

```
tests/
├── unit/              # Unit tests for each module
│   ├── bibliography/
│   ├── converters/
│   └── utils/
├── integration/       # End-to-end workflow tests
│   ├── test_markdown_to_latex.py
│   ├── test_bibliography_validation.py
│   └── test_complete_pipeline.py
├── fixtures/          # Test data
│   ├── markdown/
│   ├── latex/
│   └── bibliographies/
└── conftest.py       # Shared test configuration
```

### 4. Documentation Structure

```
docs/
├── README.md         # Main documentation
├── user-guide/       # End-user documentation
│   ├── quickstart.md
│   ├── workflows.md
│   └── troubleshooting.md
├── developer/        # Developer documentation
│   ├── architecture.md
│   ├── contributing.md
│   └── testing.md
├── claude/          # Claude-specific docs
│   ├── integration.md
│   ├── constraints.md
│   └── best-practices.md
└── api/             # API documentation
    └── reference.md
```

### 5. Configuration Management

```yaml
# config/default.yaml
bibliography:
  validation:
    check_authors: true
    check_dois: true
    check_urls: true
  enrichment:
    sources:
      - crossref
      - arxiv
    timeout: 30
  fixing:
    auto_fix_authors: true
    auto_fix_encoding: true

conversion:
  markdown:
    parser: markdown-it-py
    extensions:
      - tables
      - footnotes
  latex:
    template: academic
    bibliography_style: spbasic_pt

logging:
  level: INFO
  format: structured
  output: file
```

## Implementation Plan

### Phase 1: Core Refactoring (Week 1-2)

1. **Create new module structure**
   ```bash
   # Move core functionality to proper modules
   python scripts/refactor/reorganize_modules.py
   ```

2. **Consolidate duplicate functionality**
   - Merge all bibliography fixing scripts
   - Combine validation logic
   - Unify extraction methods

3. **Implement configuration system**
   - Create ConfigManager class
   - Migrate all hardcoded settings
   - Add environment variable support

### Phase 2: API Development (Week 3)

1. **Create high-level API**
   ```python
   from deep_biblio_tools import convert_document

   result = convert_document(
       input_file="paper.md",
       output_file="paper.tex",
       validate_citations=True,
       fix_authors=True
   )
   ```

2. **Implement workflow pipelines**
   ```python
   from deep_biblio_tools.api import Pipeline

   pipeline = Pipeline()
   pipeline.add_step("extract", ExtractBibliography())
   pipeline.add_step("validate", ValidateCitations())
   pipeline.add_step("fix", FixAuthors())
   pipeline.add_step("convert", ConvertToLaTeX())

   result = pipeline.run(input_file)
   ```

### Phase 3: Testing Infrastructure (Week 4)

1. **Create comprehensive test suite**
   - Unit tests for each module
   - Integration tests for workflows
   - Property-based tests for parsers

2. **Add test automation**
   ```yaml
   # .github/workflows/test.yml
   name: Test Suite
   on: [push, pull_request]
   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - name: Run tests
           run: |
             uv sync
             uv run pytest --cov
   ```

### Phase 4: Documentation (Week 5)

1. **Consolidate documentation**
   - Move all docs to structured format
   - Generate API docs from docstrings
   - Create interactive examples

2. **Claude Code integration guide**
   - Best practices for Claude Code
   - Example workflows
   - Troubleshooting guide

## Benefits of Refactoring

### 1. Improved Maintainability
- Clear module boundaries
- Single responsibility principle
- Reduced code duplication

### 2. Better Testing
- Comprehensive test coverage
- Automated testing pipeline
- Easier to test individual components

### 3. Enhanced Usability
- Simple high-level API
- Clear documentation
- Predictable behavior

### 4. Claude Code Integration
- Deterministic workflows
- Clear entry points
- Better error handling

### 5. Reproducibility
- Configuration-driven behavior
- Versioned dependencies
- Consistent output

## Migration Strategy

### 1. Backward Compatibility
```python
# scripts/legacy_wrapper.py
import warnings
from deep_biblio_tools.api import convert_document

def fix_bibliography(input_file, output_file):
    """Legacy wrapper for fix_bibliography.py"""
    warnings.warn(
        "fix_bibliography.py is deprecated. Use deep_biblio_tools.api",
        DeprecationWarning
    )
    return convert_document(
        input_file,
        output_file,
        steps=["fix_bibliography"]
    )
```

### 2. Gradual Migration
- Keep old scripts working during transition
- Provide migration guide
- Update documentation incrementally

### 3. Testing Migration
- Test old vs new implementation
- Ensure identical output
- Performance comparison

## Metrics for Success

1. **Code Quality**
   - Reduce script count from 81 to ~20
   - Increase test coverage to >90%
   - Eliminate duplicate code

2. **Performance**
   - Faster execution through caching
   - Parallel processing support
   - Reduced memory usage

3. **Usability**
   - Time to first successful conversion <5 minutes
   - Clear error messages
   - Comprehensive documentation

4. **Maintainability**
   - Average module size <300 lines
   - Clear dependency graph
   - Consistent coding style

## Next Steps

1. **Review and approve proposal**
2. **Create refactoring branch**
3. **Begin Phase 1 implementation**
4. **Regular progress reviews**
5. **Incremental rollout**

## Appendix: Example Workflows

### Simple Bibliography Fix
```python
from deep_biblio_tools import fix_bibliography

# One-line fix
fix_bibliography("references.bib", fix_authors=True, validate_dois=True)
```

### Complete Document Conversion
```python
from deep_biblio_tools import Pipeline, steps

pipeline = Pipeline([
    steps.ExtractBibliography(),
    steps.ValidateCitations(),
    steps.FixAuthors(),
    steps.EnrichMetadata(),
    steps.ConvertToLaTeX(),
    steps.GeneratePDF()
])

result = pipeline.run("manuscript.md")
print(f"Converted {result.input} to {result.output}")
print(f"Fixed {result.fixes_applied} issues")
```

### Custom Validation
```python
from deep_biblio_tools.bibliography import Validator

validator = Validator()
validator.add_rule("author_format", check_lastname_firstname)
validator.add_rule("doi_valid", check_doi_exists)

issues = validator.validate("references.bib")
for issue in issues:
    print(f"{issue.entry}: {issue.message}")
```
