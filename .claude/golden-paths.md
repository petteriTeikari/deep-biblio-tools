# Golden Paths - Deep Biblio Tools

This document outlines the recommended approaches for common workflows in the Deep Biblio Tools project.

## Core Development Patterns

### 1. Adding New Bibliography Validation Rules

When adding new validation rules for LLM hallucination detection:

```python
# src/bibliography/validator.py
class LLMCitationValidator:
    def validate_new_pattern(self, entry: BibliographyEntry) -> ValidationResult:
        """
        1. Check against known patterns first
        2. Validate against external APIs (CrossRef, ArXiv)
        3. Log all validation steps for audit trail
        4. Return detailed ValidationResult with confidence score
        """
        result = ValidationResult()

        # Always validate deterministically
        if self._check_suspicious_patterns(entry):
            result.add_issue("suspicious_pattern", "...")

        # API validation with caching
        cached = self.cache.get(entry.key)
        if not cached:
            api_data = self._fetch_from_apis(entry)
            self.cache.set(entry.key, api_data)

        return result
```

### 2. Processing Large Bibliography Files

For processing large files efficiently:

```python
# Use streaming approach
def process_large_bibliography(file_path: Path):
    with open(file_path, 'r') as f:
        parser = bibtexparser.bparser.BibTexParser()
        parser.customization = lambda record: record

        # Process in chunks
        chunk_size = 100
        entries = []

        for line in f:
            entries.append(line)
            if len(entries) >= chunk_size:
                yield process_chunk(entries)
                entries = []

        # Process remaining
        if entries:
            yield process_chunk(entries)
```

### 3. API Integration with Rate Limiting

All API integrations should follow this pattern:

```python
# src/api_clients/base.py
class BaseAPIClient:
    def __init__(self):
        self.rate_limiter = RateLimiter(calls_per_second=10)
        self.cache = SmartCache()

    @with_retry(max_attempts=3)
    def fetch(self, identifier: str) -> Optional[Dict]:
        # Check cache first
        cached = self.cache.get(identifier)
        if cached:
            return cached

        # Rate limit
        self.rate_limiter.wait_if_needed()

        # Make request
        response = self._make_request(identifier)

        # Cache successful responses
        if response:
            self.cache.set(identifier, response)

        return response
```

### 4. Testing Deterministic Behavior

All tests should verify deterministic behavior:

```python
# tests/test_deterministic.py
def test_same_input_same_output():
    """Ensure processing is deterministic."""
    input_data = load_test_data()

    # Run multiple times
    results = []
    for _ in range(5):
        result = process_bibliography(input_data)
        results.append(result)

    # All results should be identical
    assert all(r == results[0] for r in results[1:])
```

### 5. Error Handling and Recovery

Use fallback chains for resilient processing:

```python
# src/bibliography/processor.py
def validate_citation(citation: CitationData) -> ValidationResult:
    """Validate with fallback strategies."""
    strategies = [
        lambda: validate_with_crossref(citation),
        lambda: validate_with_arxiv(citation),
        lambda: validate_with_pubmed(citation),
        lambda: validate_with_cache(citation),
    ]

    for strategy in strategies:
        try:
            result = strategy()
            if result and result.confidence > 0.8:
                return result
        except Exception as e:
            logger.warning(f"Strategy failed: {e}")
            continue

    # Return low-confidence result if all fail
    return ValidationResult(confidence=0.1, source="fallback")
```

### 6. CLI Command Structure

When adding new CLI commands:

```python
# src/cli/commands/validate.py
@click.command()
@click.argument('bibliography_file', type=click.Path(exists=True))
@click.option('--format', type=click.Choice(['bibtex', 'json', 'yaml']))
@click.option('--strict', is_flag=True, help='Fail on any validation error')
@click.option('--cache-dir', type=click.Path(), default='.cache')
def validate(bibliography_file, format, strict, cache_dir):
    """Validate bibliography for LLM hallucinations."""
    # Always provide progress feedback
    with click.progressbar(entries) as bar:
        for entry in bar:
            result = validator.validate(entry)
            if result.has_issues() and strict:
                raise click.ClickException(f"Validation failed: {result}")
```

### 7. Performance Optimization

For CPU-intensive operations:

```python
# Use multiprocessing for parallel validation
from multiprocessing import Pool

def validate_parallel(entries: List[BibliographyEntry]) -> List[ValidationResult]:
    # Determine optimal worker count
    num_workers = min(cpu_count(), len(entries), 8)

    # Create chunks for each worker
    chunk_size = max(1, len(entries) // num_workers)
    chunks = [entries[i:i+chunk_size] for i in range(0, len(entries), chunk_size)]

    # Process in parallel
    with Pool(num_workers) as pool:
        results = pool.map(validate_chunk, chunks)

    # Flatten results
    return [r for chunk_results in results for r in chunk_results]
```

### 8. Cache Management

Implement smart caching with TTL:

```python
# src/cache/manager.py
class CacheManager:
    def __init__(self, cache_dir: Path = Path(".cache")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)

    def get_or_fetch(self, key: str, fetcher: Callable, ttl: int = 3600):
        """Get from cache or fetch if expired."""
        cache_file = self.cache_dir / f"{hashlib.md5(key.encode()).hexdigest()}.json"

        # Check cache
        if cache_file.exists():
            with open(cache_file) as f:
                data = json.load(f)

            # Check TTL
            if time.time() - data['timestamp'] < ttl:
                return data['value']

        # Fetch and cache
        value = fetcher()
        with open(cache_file, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'value': value
            }, f)

        return value
```

### 9. Logging and Debugging

Use structured logging for debugging:

```python
# src/utils/logging.py
import structlog

logger = structlog.get_logger()

def process_with_logging(entry: BibliographyEntry):
    log = logger.bind(entry_key=entry.key, entry_type=entry.entry_type)

    log.info("processing_entry")

    try:
        result = validate_entry(entry)
        log.info("validation_complete",
                confidence=result.confidence,
                issues=len(result.issues))
        return result
    except Exception as e:
        log.error("validation_failed", error=str(e))
        raise
```

### 10. Data Migration

When updating data formats:

```python
# scripts/migrate_bibliography.py
def migrate_v1_to_v2(old_data: Dict) -> Dict:
    """Migrate bibliography format with validation."""
    new_data = {
        'version': 2,
        'entries': []
    }

    for entry in old_data.get('entries', []):
        # Validate and transform
        if 'author' in entry and ' et al' in entry['author']:
            # Flag for manual review
            entry['needs_review'] = True
            entry['review_reason'] = 'et al in author field'

        # Add new required fields
        entry['validation_status'] = 'pending'
        entry['last_validated'] = None

        new_data['entries'].append(entry)

    return new_data
```

## Testing Guidelines

### Unit Tests
- Test each validation rule independently
- Mock external API calls
- Verify deterministic behavior

### Integration Tests
- Test full validation pipeline
- Use real API calls with recorded responses
- Verify cache behavior

### Performance Tests
- Benchmark large file processing
- Profile memory usage
- Test parallel processing

## Deployment Patterns

### Docker Development
```bash
# Development with hot reload
docker-compose up dev
docker-compose exec dev uv run pytest

# Production build
docker-compose build prod
docker-compose up prod
```

### CI/CD Pipeline
1. Run all tests in Docker
2. Check code quality (ruff)
3. Validate Claude constraints
4. Build and tag images
5. Deploy with rollback capability

## Common Pitfalls to Avoid

1. **Don't trust LLM-generated author names** - Always validate
2. **Don't skip caching** - API rate limits are real
3. **Don't process entire file in memory** - Use streaming
4. **Don't ignore edge cases** - Unicode, special characters matter
5. **Don't forget audit trails** - Track all validation decisions

## Performance Benchmarks

Target performance metrics:
- Single entry validation: <100ms with cache
- 1000 entry file processing: <30 seconds
- API validation with retries: <500ms per entry
- Cache hit rate: >80% in normal usage

## Security Considerations

1. **Never log API keys** - Use environment variables
2. **Validate all inputs** - Especially file paths
3. **Sanitize error messages** - Don't leak internal paths
4. **Limit file sizes** - Prevent DoS via large files
5. **Use timeouts** - For all external calls
