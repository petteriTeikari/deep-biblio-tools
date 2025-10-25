# Implementation Roadmap

## Immediate Actions (This Week)

### 1. Create Script Index
Create a comprehensive index of all scripts with their purpose and usage:

```markdown
# scripts/SCRIPT_INDEX.md

## Bibliography Processing
- `fix_bibliography.py` - Main bibliography fixer (KEEP)
- `fix_bibliography_enhanced.py` - Enhanced version (DEPRECATE → merge into main)
- `fix_bibliography_ampersands.py` - Specific fix (DEPRECATE → add as option)
...
```

### 2. Consolidate Core Scripts
Start with the most-used functionality:

```python
# scripts/refactor/consolidate_bibliography_fixers.py
"""Consolidate all bibliography fixing scripts into one"""

def consolidate():
    # 1. Identify all fix_bibliography* scripts
    # 2. Extract unique functionality from each
    # 3. Create unified fix_bibliography.py with options
    # 4. Move old scripts to archive/deprecated/
```

### 3. Create Workflow Scripts
Replace complex script chains with simple workflows:

```python
# workflows/process_markdown_paper.py
#!/usr/bin/env python3
"""Complete workflow: Markdown → LaTeX with validated bibliography"""

import click
from deep_biblio_tools import Pipeline

@click.command()
@click.argument('input_file')
@click.option('--output', '-o', help='Output LaTeX file')
@click.option('--validate/--no-validate', default=True)
@click.option('--fix-authors/--no-fix-authors', default=True)
def process_paper(input_file, output, validate, fix_authors):
    """Process markdown paper to LaTeX with bibliography fixes"""

    pipeline = Pipeline()

    # Step 1: Extract bibliography
    pipeline.add("extract_bibliography")

    # Step 2: Validate if requested
    if validate:
        pipeline.add("validate_citations")

    # Step 3: Fix issues
    if fix_authors:
        pipeline.add("fix_incomplete_authors")

    # Step 4: Convert to LaTeX
    pipeline.add("convert_to_latex")

    # Run pipeline
    result = pipeline.run(input_file, output)

    # Report results
    click.echo(f"✓ Processed {input_file}")
    click.echo(f"✓ Fixed {result.fixes_count} issues")
    click.echo(f"✓ Output: {result.output_file}")

if __name__ == "__main__":
    process_paper()
```

## Phase 1: Core Consolidation (Week 1-2)

### Step 1: Module Organization
```bash
# Create new structure
mkdir -p src/deep_biblio_tools/{bibliography,converters,utils,cli}
mkdir -p src/deep_biblio_tools/bibliography/{extractors,validators,fixers,enrichers}
```

### Step 2: Move Core Functionality
```python
# Move and refactor scripts
# FROM: scripts/fix_bibliography.py
# TO: src/deep_biblio_tools/bibliography/fixers/comprehensive.py

# FROM: scripts/validate_llm_citations.py
# TO: src/deep_biblio_tools/bibliography/validators/llm_citations.py
```

### Step 3: Create Unified API
```python
# src/deep_biblio_tools/api.py
from .bibliography import fix_bibliography, validate_citations
from .converters import markdown_to_latex

__all__ = ['fix_bibliography', 'validate_citations', 'markdown_to_latex']

# Simple API for common tasks
def process_document(input_file, output_file=None, **options):
    """One-stop document processing"""
    # Implementation
```

## Phase 2: Testing Infrastructure (Week 3)

### Step 1: Create Test Structure
```bash
# Organize tests by functionality
mkdir -p tests/{unit,integration,fixtures,regression}
mkdir -p tests/unit/{bibliography,converters,utils}
```

### Step 2: Add Test Coverage
```python
# tests/unit/bibliography/test_author_fixer.py
import pytest
from deep_biblio_tools.bibliography.fixers import AuthorFixer

class TestAuthorFixer:
    @pytest.fixture
    def fixer(self):
        return AuthorFixer()

    def test_fix_et_al_catastrophe(self, fixer):
        """Test the infamous 'et al' bug"""
        assert fixer.fix("al, Smith et") == "Smith"

    def test_incomplete_single_name(self, fixer):
        """Test single name completion"""
        assert fixer.fix("Moss") == "Moss, Adam"  # with metadata lookup
```

### Step 3: Integration Tests
```python
# tests/integration/test_complete_workflow.py
def test_markdown_to_latex_workflow(tmp_path):
    """Test complete conversion workflow"""
    input_file = tmp_path / "paper.md"
    input_file.write_text(SAMPLE_MARKDOWN)

    output_file = tmp_path / "paper.tex"

    result = process_document(
        input_file,
        output_file,
        validate=True,
        fix_authors=True
    )

    assert output_file.exists()
    assert "\\bibliography{references}" in output_file.read_text()
    assert result.success
```

## Phase 3: Documentation (Week 4)

### Step 1: Create User Guide
```markdown
# docs/user-guide/quickstart.md

## Quick Start

### Installation
```bash
pip install deep-biblio-tools
```

### Basic Usage

1. **Fix a bibliography**
   ```bash
   biblio fix references.bib
   ```

2. **Convert markdown to LaTeX**
   ```bash
   biblio convert paper.md -o paper.tex
   ```

3. **Validate citations**
   ```bash
   biblio validate references.bib --check-dois
   ```
```

### Step 2: API Documentation
```python
# Auto-generate from docstrings
# docs/conf.py
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx_click',
]
```

## Phase 4: Claude Integration (Week 5)

### Step 1: Create Claude-Specific Commands
```python
# src/deep_biblio_tools/cli/claude_commands.py
@click.group()
def claude():
    """Commands optimized for Claude Code"""
    pass

@claude.command()
@click.option('--verbose', is_flag=True)
def status():
    """Show current project status"""
    click.echo("Bibliography Database:")
    click.echo(f"  Entries: {count_entries()}")
    click.echo(f"  Validated: {count_validated()}")
    click.echo(f"  Issues: {count_issues()}")
```

### Step 2: Add Progress Indicators
```python
# src/deep_biblio_tools/utils/progress.py
def with_progress(iterable, description):
    """Claude-friendly progress indicator"""
    total = len(iterable)
    for i, item in enumerate(iterable):
        print(f"\r{description}: {i+1}/{total}", end='')
        yield item
    print()  # New line when done
```

## Migration Checklist

### Week 1
- [ ] Create script inventory
- [ ] Identify core functionality
- [ ] Plan consolidation strategy
- [ ] Set up new module structure

### Week 2
- [ ] Consolidate bibliography fixers
- [ ] Consolidate validators
- [ ] Create unified API
- [ ] Archive deprecated scripts

### Week 3
- [ ] Set up test structure
- [ ] Write unit tests for core modules
- [ ] Add integration tests
- [ ] Set up CI/CD

### Week 4
- [ ] Consolidate documentation
- [ ] Write user guide
- [ ] Generate API docs
- [ ] Create examples

### Week 5
- [ ] Add Claude-specific features
- [ ] Test with Claude Code
- [ ] Create workflow templates
- [ ] Final testing

## Success Metrics

### Code Quality
- [ ] Reduce scripts from 81 to <30
- [ ] Test coverage >80%
- [ ] All functions have docstrings
- [ ] Consistent code style (enforced by ruff)

### Usability
- [ ] Single command for common tasks
- [ ] Clear error messages
- [ ] Progress indicators for long operations
- [ ] Comprehensive --help for all commands

### Performance
- [ ] <5s for typical bibliography fix
- [ ] <30s for full document conversion
- [ ] Efficient caching reduces API calls by 90%

### Claude Integration
- [ ] Deterministic outputs
- [ ] Clear task boundaries
- [ ] Structured error reporting
- [ ] Progress visibility

## Rollback Plan

If issues arise:

1. **Keep old scripts available**
   ```bash
   # scripts/legacy/run_old_script.py
   import warnings
   warnings.warn("Using legacy script", DeprecationWarning)
   # Forward to old implementation
   ```

2. **Feature flags**
   ```python
   if os.getenv('USE_LEGACY_FIXER'):
       from ..legacy import fix_bibliography
   else:
       from ..bibliography import fix_bibliography
   ```

3. **Gradual migration**
   - Start with new scripts
   - Migrate one workflow at a time
   - Keep both versions during transition

## Next Immediate Steps

1. **Today**: Create `SCRIPT_INDEX.md` listing all scripts and their purpose
2. **Tomorrow**: Identify top 5 most-used scripts for consolidation
3. **This Week**: Create first unified workflow script
4. **Next Week**: Begin module reorganization

The key is to start small, validate each change, and maintain backward compatibility throughout the transition.
