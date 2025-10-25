# Guardrails Template Improvements

Based on refactoring Deep Biblio Tools, here are critical improvements needed for the claude-code-guardrails-template.

## 1. Missing Generated Content

### Problem
The template has excellent guardrails for its own development but fails to generate equivalent patterns in child repositories.

### Required Additions

#### A. Golden Paths Template
```yaml
# cookiecutter.json addition
"include_golden_paths": true,
"common_workflows": ["api_integration", "data_processing", "cli_tool", "web_service"]
```

Generate `.claude/golden-paths.md` with:
- Domain-specific workflow examples
- Performance optimization patterns
- Error handling strategies
- Caching implementations

#### B. Domain-Specific Policies
```yaml
# For bibliography/academic tools
"domain": "academic_tools",
"domain_policies": {
  "academic_tools": {
    "parsers": ["bibtexparser", "markdown-it-py", "pylatexenc"],
    "apis": ["crossref", "arxiv", "semantic_scholar"],
    "caching": "required",
    "rate_limiting": "required"
  }
}
```

#### C. Performance Patterns
```python
# Generate rate_limiting.py
class RateLimiter:
    """Template-generated rate limiter for API calls."""
    def __init__(self, calls_per_second=10):
        self.calls_per_second = calls_per_second
        self.last_call = 0

    def wait_if_needed(self):
        # Implementation...
```

## 2. Real-World Integration Patterns

### Missing API Patterns
The template should generate:

```python
# src/{{cookiecutter.project_slug}}/integrations/base_api.py
from abc import ABC, abstractmethod
import time
from typing import Optional, Dict, Any
import requests
from functools import wraps

class BaseAPIClient(ABC):
    """Base class for API integrations with built-in resilience."""

    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()

    def with_retry(self, max_attempts: int = 3):
        """Decorator for automatic retry with exponential backoff."""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except requests.RequestException as e:
                        if attempt == max_attempts - 1:
                            raise
                        wait_time = 2 ** attempt
                        time.sleep(wait_time)
                return None
            return wrapper
        return decorator

    @abstractmethod
    def validate_response(self, response: Dict[str, Any]) -> bool:
        """Validate API response has required fields."""
        pass
```

### Missing Cache Implementation
```python
# src/{{cookiecutter.project_slug}}/cache/smart_cache.py
from pathlib import Path
import json
import time
from typing import Optional, Any
import hashlib

class SmartCache:
    """Intelligent caching with TTL and invalidation."""

    def __init__(self, cache_dir: Path = Path(".cache")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)

    def get(self, key: str, ttl: int = 3600) -> Optional[Any]:
        """Get from cache if not expired."""
        cache_file = self._get_cache_path(key)
        if not cache_file.exists():
            return None

        with open(cache_file, 'r') as f:
            data = json.load(f)

        if time.time() - data['timestamp'] > ttl:
            cache_file.unlink()  # Delete expired
            return None

        return data['value']

    def set(self, key: str, value: Any):
        """Store in cache with timestamp."""
        cache_file = self._get_cache_path(key)
        with open(cache_file, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'value': value
            }, f)

    def _get_cache_path(self, key: str) -> Path:
        """Generate cache file path from key."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"
```

## 3. State Management for Long-Running Processes

### Missing Checkpoint System
```python
# src/{{cookiecutter.project_slug}}/state/checkpoint.py
from dataclasses import dataclass, asdict
from pathlib import Path
import json
from typing import Any, Dict
import uuid

@dataclass
class ProcessState:
    """State for resumable processes."""
    process_id: str
    total_items: int
    processed_items: int
    failed_items: list
    current_batch: int
    metadata: Dict[str, Any]

    def save(self, checkpoint_dir: Path = Path(".checkpoints")):
        """Save state to disk."""
        checkpoint_dir.mkdir(exist_ok=True)
        checkpoint_file = checkpoint_dir / f"{self.process_id}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, process_id: str, checkpoint_dir: Path = Path(".checkpoints")):
        """Load state from disk."""
        checkpoint_file = checkpoint_dir / f"{process_id}.json"
        if not checkpoint_file.exists():
            return None
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
        return cls(**data)

    @classmethod
    def create_new(cls, total_items: int) -> 'ProcessState':
        """Create new process state."""
        return cls(
            process_id=str(uuid.uuid4()),
            total_items=total_items,
            processed_items=0,
            failed_items=[],
            current_batch=0,
            metadata={}
        )
```

## 4. Docker-First Implementation

### Missing Docker Files
The template should generate complete Docker setup:

```yaml
# docker-compose.yml (generated)
version: '3.8'

services:
  dev:
    build:
      context: .
      dockerfile: Dockerfile.dev
      args:
        - PYTHON_VERSION=${PYTHON_VERSION:-3.12}
    volumes:
      - .:/workspace
      - ${HOME}/.cache:/home/developer/.cache
    environment:
      - PYTHONPATH=/workspace
    ports:
      - "${DEV_PORT:-8000}:8000"
    command: tail -f /dev/null

  test:
    build:
      context: .
      dockerfile: Dockerfile.test
    volumes:
      - .:/workspace:ro
    environment:
      - CI=true
      - COVERAGE_FILE=/workspace/.coverage
    command: pytest --cov --cov-report=xml

  prod:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    restart: unless-stopped
```

## 5. Error Recovery Patterns

### Missing Graceful Degradation
```python
# src/{{cookiecutter.project_slug}}/resilience/fallback.py
from typing import List, Callable, Any, Optional
import logging

logger = logging.getLogger(__name__)

class FallbackChain:
    """Execute operations with fallback strategies."""

    def __init__(self):
        self.strategies: List[Callable] = []

    def add_strategy(self, func: Callable, name: str = None):
        """Add a fallback strategy."""
        func._strategy_name = name or func.__name__
        self.strategies.append(func)
        return self

    def execute(self, *args, **kwargs) -> Optional[Any]:
        """Try each strategy until one succeeds."""
        errors = []

        for strategy in self.strategies:
            try:
                result = strategy(*args, **kwargs)
                if result is not None:
                    return result
            except Exception as e:
                errors.append({
                    'strategy': strategy._strategy_name,
                    'error': str(e)
                })
                logger.warning(f"Strategy {strategy._strategy_name} failed: {e}")

        logger.error(f"All strategies failed. Errors: {errors}")
        return None

# Usage example in generated code:
def fetch_metadata(identifier: str) -> Optional[Dict]:
    chain = FallbackChain()
    chain.add_strategy(lambda: fetch_from_crossref(identifier), "CrossRef")
    chain.add_strategy(lambda: fetch_from_arxiv(identifier), "arXiv")
    chain.add_strategy(lambda: fetch_from_cache(identifier), "Cache")
    return chain.execute()
```

## 6. Testing Reality

### Missing Test Generators
```python
# hooks/post_gen_project.py addition
def generate_edge_case_tests():
    """Generate tests for common edge cases."""
    test_content = '''
import pytest
from {{cookiecutter.project_slug}} import process_data

class TestEdgeCases:
    """Auto-generated edge case tests."""

    def test_empty_input(self):
        """Test with empty input."""
        assert process_data("") == []

    def test_malformed_input(self):
        """Test with malformed input."""
        with pytest.raises(ValueError):
            process_data("invalid{data}")

    def test_unicode_handling(self):
        """Test Unicode characters."""
        result = process_data("Schrödinger's cat: 🐱")
        assert "🐱" in str(result)

    def test_large_input(self):
        """Test performance with large input."""
        large_data = "x" * 10_000_000  # 10MB
        result = process_data(large_data)
        assert result is not None

    @pytest.mark.timeout(5)
    def test_timeout_handling(self):
        """Test timeout scenarios."""
        # Should complete within 5 seconds
        process_data("normal_data")
'''

    test_file = Path("tests/test_edge_cases.py")
    test_file.write_text(test_content)
```

## 7. CLI Improvements

### Missing CLI Patterns
```python
# Generate better CLI structure
def generate_cli_commands():
    """Generate comprehensive CLI with subcommands."""
    cli_content = '''
import click
from {{cookiecutter.project_slug}} import __version__

@click.group()
@click.version_option(version=__version__)
@click.option('--verbose', '-v', count=True, help='Increase verbosity')
@click.option('--quiet', '-q', is_flag=True, help='Suppress output')
@click.option('--config', '-c', type=click.Path(exists=True), help='Config file')
@click.pass_context
def cli(ctx, verbose, quiet, config):
    """{{cookiecutter.project_description}}"""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['quiet'] = quiet
    ctx.obj['config'] = config

@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output file')
@click.option('--format', '-f', type=click.Choice(['json', 'yaml', 'csv']))
@click.option('--dry-run', is_flag=True, help='Preview without changes')
@click.pass_context
def process(ctx, input_file, output, format, dry_run):
    """Process input file."""
    # Implementation

@cli.command()
@click.option('--all', '-a', is_flag=True, help='Validate all files')
@click.pass_context
def validate(ctx, all):
    """Validate data integrity."""
    # Implementation

@cli.command()
@click.pass_context
def clean(ctx):
    """Clean cache and temporary files."""
    # Implementation
'''

    cli_file = Path(f"src/{{cookiecutter.project_slug}}/cli.py")
    cli_file.write_text(cli_content)
```

## 8. Documentation Generation

### Missing API Documentation
The template should auto-generate:
- API endpoint documentation
- Data flow diagrams
- Performance benchmarks template
- Troubleshooting guide

## 9. Monitoring and Observability

### Missing Metrics Collection
```python
# src/{{cookiecutter.project_slug}}/metrics/collector.py
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path

@dataclass
class Metric:
    name: str
    value: float
    timestamp: datetime
    tags: dict

class MetricsCollector:
    """Collect and export metrics."""

    def __init__(self, export_dir: Path = Path(".metrics")):
        self.export_dir = export_dir
        self.export_dir.mkdir(exist_ok=True)
        self.metrics = []

    def record(self, name: str, value: float, **tags):
        """Record a metric."""
        metric = Metric(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags
        )
        self.metrics.append(metric)

    def export(self):
        """Export metrics to file."""
        export_file = self.export_dir / f"metrics_{datetime.now():%Y%m%d_%H%M%S}.json"
        with open(export_file, 'w') as f:
            json.dump([
                {
                    'name': m.name,
                    'value': m.value,
                    'timestamp': m.timestamp.isoformat(),
                    'tags': m.tags
                }
                for m in self.metrics
            ], f, indent=2)
```

## Summary of Required Changes

1. **Generate actual implementation files**, not just documentation
2. **Include domain-specific patterns** (API integration, caching, etc.)
3. **Add state management** for long-running processes
4. **Provide complete Docker setup**, not just Dockerfiles
5. **Include error recovery patterns** with fallback chains
6. **Generate comprehensive test suites** with edge cases
7. **Create full CLI structure** with subcommands
8. **Add monitoring and metrics** collection
9. **Include performance optimization** patterns
10. **Provide troubleshooting tools** and debug helpers

The template should ask during generation:
- What type of project? (CLI tool, API service, data processor)
- What external APIs? (to generate appropriate clients)
- Performance requirements? (to configure caching/batching)
- Deployment target? (to customize Docker setup)

This would make the generated projects production-ready from day one.
