# Docker-First Development Workflow

## Core Principle

**All development, testing, and CI/CD must run identically in Docker containers.** This ensures perfect reproducibility and eliminates "works on my machine" issues.

## Development Workflow

### 1. Initial Setup
```bash
# Clone and enter project
git clone <repo>
cd deep-biblio-tools

# Build development container
docker compose build dev

# Start development environment
docker compose up -d dev

# Enter container for interactive work
docker compose exec dev bash
```

### 2. Daily Development
```bash
# Always work inside container
docker compose exec dev bash

# Run tests
uv run pytest

# Run linting
uv run ruff check .
uv run ruff format

# Run scripts
uv run python scripts/fix_bibliography.py input.bib
```

### 3. Testing Workflow
```bash
# Run full test suite in fresh container
docker compose run --rm test

# Run specific tests
docker compose run --rm test pytest tests/test_bibliography.py

# Run with coverage
docker compose run --rm test pytest --cov --cov-report=html
```

## Docker Compose Services

```yaml
# docker-compose.yml
version: '3.8'

services:
  dev:
    build:
      context: .
      dockerfile: Dockerfile.dev
    volumes:
      - .:/workspace
      - ~/.cache:/home/user/.cache  # Share cache for APIs
    environment:
      - PYTHONPATH=/workspace
    command: tail -f /dev/null  # Keep container running

  test:
    build:
      context: .
      dockerfile: Dockerfile.test
    volumes:
      - .:/workspace:ro  # Read-only for tests
    environment:
      - CI=true
    command: pytest

  prod:
    build:
      context: .
      dockerfile: Dockerfile
    command: python -m deep_biblio_tools
```

## Dockerfile Best Practices

### Development Image
```dockerfile
# Dockerfile.dev
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /workspace

# Copy dependency files only
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Development tools
RUN uv sync --group dev --frozen

# Set up user
RUN useradd -m -s /bash user
USER user
```

### Test Image
```dockerfile
# Dockerfile.test
FROM python:3.12-slim

# Minimal dependencies for testing
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /workspace

# Copy everything for tests
COPY . .

# Install with dev dependencies
RUN uv sync --frozen && uv sync --group dev --frozen

# Run as non-root
USER nobody

CMD ["pytest"]
```

## CI/CD Integration

### GitHub Actions
```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Build test image
      run: docker build -f Dockerfile.test -t test .

    - name: Run tests
      run: docker run --rm test

    - name: Run linting
      run: docker run --rm test ruff check .
```

## Cache Management

### API Response Caching
```python
# Use Docker volumes for persistent cache
CACHE_DIR = Path("/cache")  # Mounted volume

def get_cache_path(key: str) -> Path:
    """Get cache file path within Docker volume."""
    return CACHE_DIR / f"{key}.json"
```

### Docker Volume for Cache
```bash
# Create named volume for cache
docker volume create biblio-cache

# Mount in compose
volumes:
  - biblio-cache:/cache
```

## Environment Variables

### Development
```env
# .env.development
CROSSREF_API_KEY=your-dev-key
CACHE_TTL=3600
LOG_LEVEL=DEBUG
```

### Production
```env
# .env.production
CROSSREF_API_KEY=${CROSSREF_API_KEY}  # From secrets
CACHE_TTL=86400
LOG_LEVEL=INFO
```

## Debugging in Containers

### Interactive Debugging
```bash
# Start with debugging enabled
docker compose run --rm -e PYTHONBREAKPOINT=ipdb.set_trace dev python scripts/debug.py

# Attach to running container
docker compose exec dev bash
ps aux  # Find process
gdb -p <pid>  # Attach debugger
```

### Logging
```python
# Always log to stdout for Docker
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]  # stdout
)
```

## Performance Optimization

### Multi-stage Builds
```dockerfile
# Dockerfile (production)
# Stage 1: Builder
FROM python:3.12-slim as builder
RUN pip install uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Stage 2: Runtime
FROM python:3.12-slim
COPY --from=builder /root/.cache/uv /root/.cache/uv
COPY . .
CMD ["python", "-m", "deep_biblio_tools"]
```

### Layer Caching
```dockerfile
# Order matters for caching
COPY pyproject.toml uv.lock ./  # Changes less often
RUN uv sync --frozen
COPY src/ ./src/  # Changes more often
```

## Security

### Non-root User
```dockerfile
# Always run as non-root
RUN useradd -m appuser
USER appuser
```

### Read-only Filesystem
```yaml
# docker-compose.yml
services:
  app:
    read_only: true
    tmpfs:
      - /tmp
      - /var/tmp
```

## Troubleshooting

### Common Issues

1. **Permission Errors**
   ```bash
   # Fix ownership issues
   docker compose exec --user root dev chown -R user:user /workspace
   ```

2. **Slow Performance on macOS/Windows**
   ```yaml
   # Use delegated mounts
   volumes:
     - .:/workspace:delegated
   ```

3. **Out of Space**
   ```bash
   # Clean up
   docker system prune -a
   docker volume prune
   ```

## Best Practices Summary

1. **Always use Docker Compose** for development
2. **Never install dependencies locally** - only in containers
3. **Test in fresh containers** to ensure reproducibility
4. **Use multi-stage builds** for smaller production images
5. **Mount source code as volumes** during development
6. **Copy code into image** for production/testing
7. **Use named volumes** for persistent data (cache, etc.)
8. **Log to stdout** for container compatibility
9. **Run as non-root user** for security
10. **Keep images minimal** - only install what's needed
