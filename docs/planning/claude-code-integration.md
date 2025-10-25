# Claude Code Integration Strategy

## Making Deep-Biblio-Tools Deterministic with Claude Code

### 1. Deterministic Workflows

#### Current Issues
- Scripts have side effects (modifying files in place)
- Inconsistent output depending on external API availability
- No clear state management
- Unpredictable error handling

#### Solutions

**A. Pure Functions Approach**
```python
# Instead of:
def fix_bibliography(filename):
    """Modifies file in place - non-deterministic"""
    with open(filename, 'r') as f:
        content = f.read()
    fixed = do_fixes(content)
    with open(filename, 'w') as f:
        f.write(fixed)

# Use:
def fix_bibliography(content: str, config: dict) -> tuple[str, list[str]]:
    """Pure function - deterministic"""
    fixes_applied = []
    fixed_content = content

    for fixer in get_fixers(config):
        fixed_content, fixes = fixer.apply(fixed_content)
        fixes_applied.extend(fixes)

    return fixed_content, fixes_applied
```

**B. Explicit State Management**
```python
@dataclass
class WorkflowState:
    """Explicit state for bibliography processing"""
    input_content: str
    current_content: str
    fixes_applied: list[str]
    validation_errors: list[str]
    metadata_cache: dict
    config: dict

    def snapshot(self) -> dict:
        """Create reproducible snapshot"""
        return {
            'content_hash': hashlib.sha256(self.current_content.encode()).hexdigest(),
            'fixes_count': len(self.fixes_applied),
            'errors_count': len(self.validation_errors),
            'timestamp': datetime.utcnow().isoformat()
        }
```

### 2. Claude Code Best Practices

#### A. Clear Task Boundaries
```python
# tasks.py - Define clear, atomic tasks for Claude
class BibliographyTasks:
    """Tasks that Claude can execute independently"""

    @staticmethod
    def extract_citations(markdown_content: str) -> list[Citation]:
        """Extract all citations from markdown - single responsibility"""
        pass

    @staticmethod
    def validate_authors(citations: list[Citation]) -> list[ValidationIssue]:
        """Validate author format - single responsibility"""
        pass

    @staticmethod
    def fix_single_author(author: str, metadata: dict) -> str:
        """Fix one author entry - atomic operation"""
        pass
```

#### B. Structured Commands
```python
# cli/commands.py - Claude-friendly command structure
@click.group()
def cli():
    """Deep Biblio Tools - Bibliography Processing Suite"""
    pass

@cli.command()
@click.option('--input', '-i', required=True, help='Input file')
@click.option('--output', '-o', help='Output file (default: stdout)')
@click.option('--fixes', '-f', multiple=True,
              type=click.Choice(['authors', 'encoding', 'urls', 'all']),
              help='Fixes to apply')
@click.option('--dry-run', is_flag=True, help='Show what would be done')
def fix(input, output, fixes, dry_run):
    """Fix bibliography issues"""
    # Implementation
```

### 3. Reproducible Execution

#### A. Configuration-Driven Processing
```yaml
# .claude/workflows/fix_bibliography.yaml
name: Fix Bibliography
description: Complete bibliography fixing workflow

steps:
  - name: Load bibliography
    action: load_file
    params:
      file: "{{ input_file }}"

  - name: Validate structure
    action: validate_bibtex
    params:
      strict: true

  - name: Fix authors
    action: fix_authors
    params:
      use_cache: true
      sources:
        - crossref
        - arxiv

  - name: Fix encoding
    action: fix_encoding
    params:
      target: utf-8

  - name: Save result
    action: save_file
    params:
      file: "{{ output_file }}"
      backup: true
```

#### B. Caching Strategy
```python
# utils/cache.py
class DeterministicCache:
    """Cache with explicit versioning for reproducibility"""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.version = self._get_version()

    def get(self, key: str, version: str = None) -> Optional[Any]:
        """Get with optional version pinning"""
        cache_key = self._make_key(key, version or self.version)
        cache_file = self.cache_dir / f"{cache_key}.json"

        if cache_file.exists():
            with open(cache_file) as f:
                data = json.load(f)
                return data['value']
        return None

    def set(self, key: str, value: Any, metadata: dict = None):
        """Set with metadata for traceability"""
        cache_key = self._make_key(key, self.version)
        cache_file = self.cache_dir / f"{cache_key}.json"

        data = {
            'key': key,
            'value': value,
            'version': self.version,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }

        with open(cache_file, 'w') as f:
            json.dump(data, f, indent=2)
```

### 4. Error Handling for Claude

#### A. Structured Errors
```python
# utils/errors.py
class BibliographyError(Exception):
    """Base error with structured information"""

    def __init__(self, message: str, entry: str = None,
                 field: str = None, suggestion: str = None):
        super().__init__(message)
        self.entry = entry
        self.field = field
        self.suggestion = suggestion

    def to_dict(self) -> dict:
        """Convert to structured format for Claude"""
        return {
            'error': self.__class__.__name__,
            'message': str(self),
            'entry': self.entry,
            'field': self.field,
            'suggestion': self.suggestion
        }

class AuthorFormatError(BibliographyError):
    """Specific error for author formatting issues"""
    pass
```

#### B. Graceful Degradation
```python
# bibliography/enrichers/metadata.py
class MetadataEnricher:
    """Enricher with fallback strategies"""

    def enrich(self, entry: dict) -> dict:
        """Try multiple sources with fallbacks"""
        enriched = entry.copy()

        # Try DOI first
        if 'doi' in entry:
            try:
                metadata = self.fetch_doi_metadata(entry['doi'])
                enriched.update(metadata)
                return enriched
            except Exception as e:
                logger.warning(f"DOI fetch failed: {e}")

        # Fallback to arXiv
        if 'url' in entry and 'arxiv.org' in entry['url']:
            try:
                metadata = self.fetch_arxiv_metadata(entry['url'])
                enriched.update(metadata)
                return enriched
            except Exception as e:
                logger.warning(f"arXiv fetch failed: {e}")

        # Return original if all fails
        enriched['_enrichment_failed'] = True
        return enriched
```

### 5. Testing for Determinism

#### A. Property-Based Tests
```python
# tests/test_determinism.py
from hypothesis import given, strategies as st

class TestDeterminism:

    @given(st.text())
    def test_fix_authors_deterministic(self, author_string):
        """Same input always produces same output"""
        config = {'fix_authors': True}

        result1 = fix_authors(author_string, config)
        result2 = fix_authors(author_string, config)

        assert result1 == result2

    def test_workflow_reproducible(self, sample_bibliography):
        """Entire workflow produces same result"""
        state1 = run_workflow(sample_bibliography, seed=42)
        state2 = run_workflow(sample_bibliography, seed=42)

        assert state1.snapshot() == state2.snapshot()
```

#### B. Regression Tests
```python
# tests/regression/test_known_issues.py
class TestKnownIssues:
    """Test specific issues that Claude encountered"""

    def test_et_al_catastrophe(self):
        """Test the 'al, Author et' pattern fix"""
        input_author = "al, Smith et"
        expected = "Smith"

        result = fix_et_al_catastrophe(input_author)
        assert result == expected

    def test_incomplete_author_moss(self):
        """Test Moss author completion"""
        entry = {'author': 'Moss', 'journal': 'arXiv'}
        expected = {'author': 'Moss, Adam', 'journal': 'arXiv'}

        result = fix_incomplete_authors(entry)
        assert result == expected
```

### 6. Claude Code Workflow Integration

#### A. Workflow Templates
```python
# .claude/templates/bibliography_workflow.py
"""Template for Claude to use when processing bibliographies"""

def process_bibliography(input_file: str, output_file: str):
    """Standard workflow for bibliography processing"""

    # 1. Load and validate
    content = load_bibliography(input_file)
    issues = validate_bibliography(content)

    if issues:
        print(f"Found {len(issues)} validation issues")
        for issue in issues[:5]:
            print(f"  - {issue}")

    # 2. Apply fixes
    fixes_to_apply = ['authors', 'encoding', 'urls']
    fixed_content = content

    for fix_type in fixes_to_apply:
        fixed_content, changes = apply_fix(fixed_content, fix_type)
        print(f"Applied {len(changes)} {fix_type} fixes")

    # 3. Enrich metadata
    enriched_content = enrich_metadata(fixed_content)

    # 4. Save result
    save_bibliography(enriched_content, output_file)
    print(f"Saved fixed bibliography to {output_file}")
```

#### B. Interactive Mode
```python
# cli/interactive.py
class InteractiveBibliographyFixer:
    """Interactive mode for Claude Code"""

    def run(self):
        """Run interactive fixing session"""
        print("Bibliography Interactive Fixer")
        print("=" * 40)

        while True:
            action = self.prompt_action()

            if action == 'load':
                self.load_bibliography()
            elif action == 'validate':
                self.validate_current()
            elif action == 'fix':
                fix_type = self.prompt_fix_type()
                self.apply_fix(fix_type)
            elif action == 'save':
                self.save_current()
            elif action == 'quit':
                break

    def prompt_action(self) -> str:
        """Get action from user/Claude"""
        print("\nAvailable actions:")
        print("  load    - Load bibliography file")
        print("  validate - Check for issues")
        print("  fix     - Apply fixes")
        print("  save    - Save current state")
        print("  quit    - Exit")

        return input("\nAction: ").strip().lower()
```

### 7. Monitoring and Logging

#### A. Structured Logging
```python
# utils/logging.py
import structlog

logger = structlog.get_logger()

def log_operation(operation: str, **kwargs):
    """Log operation for Claude visibility"""
    logger.info(
        operation,
        timestamp=datetime.utcnow().isoformat(),
        **kwargs
    )

# Usage
log_operation(
    "fix_authors",
    entry_id="smith2023",
    original="Smith",
    fixed="Smith, John",
    source="crossref"
)
```

#### B. Progress Tracking
```python
# utils/progress.py
class ProgressTracker:
    """Track progress for long operations"""

    def __init__(self, total: int, description: str):
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = time.time()

    def update(self, increment: int = 1):
        """Update progress"""
        self.current += increment
        percent = (self.current / self.total) * 100
        elapsed = time.time() - self.start_time
        rate = self.current / elapsed if elapsed > 0 else 0

        print(f"\r{self.description}: {percent:.1f}% "
              f"({self.current}/{self.total}) "
              f"Rate: {rate:.1f}/s", end='')

    def finish(self):
        """Mark as complete"""
        elapsed = time.time() - self.start_time
        print(f"\n{self.description} completed in {elapsed:.1f}s")
```

### 8. Integration Examples

#### Example 1: Simple Fix
```bash
# Claude can run this deterministically
claude-biblio fix references.bib --output fixed.bib --fixes authors,urls
```

#### Example 2: Complex Workflow
```python
# Claude can execute this step by step
from deep_biblio_tools import Workflow

workflow = Workflow.from_config("bibliography_processing.yaml")
workflow.add_observer(claude_progress_callback)

result = workflow.run(
    input_file="manuscript.md",
    cache_version="2024-01-15",
    dry_run=False
)

print(f"Processed in {result.duration}s")
print(f"Fixed {result.fixes_count} issues")
print(f"Validation score: {result.validation_score}")
```

This integration strategy ensures that Deep-Biblio-Tools works seamlessly with Claude Code while maintaining deterministic, reproducible behavior.
