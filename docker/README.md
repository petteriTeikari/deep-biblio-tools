# Docker Testing Environment

This directory contains Docker configurations to ensure consistent testing between local development and GitHub Actions CI.

## Problem Solved

The Docker setup addresses the common issue of "works on my machine" by providing an exact replica of the GitHub Actions environment. This ensures that:
- Linting rules are applied consistently
- Import sorting behaves identically
- Test results are reproducible
- Dependencies are locked to specific versions

## Quick Start

### Run all tests in Docker (recommended)
```bash
./scripts/test-docker.sh
```

### Using docker-compose for specific tasks

```bash
# Run tests
docker-compose -f docker-compose.test.yml run test

# Run linting
docker-compose -f docker-compose.test.yml run lint

# Auto-fix formatting issues
docker-compose -f docker-compose.test.yml run format
```

### Build the Docker image manually
```bash
docker build -f Dockerfile.test -t deep-biblio-tools-test .
```

## Files

- `Dockerfile.test` - Replicates the GitHub Actions Ubuntu 22.04 environment with Python 3.12
- `docker-compose.test.yml` - Provides convenient commands for testing, linting, and formatting
- `scripts/test-docker.sh` - One-command script to run all tests in Docker

## Benefits

1. **Consistency**: Same environment locally and in CI
2. **Isolation**: No pollution of local Python environment
3. **Reproducibility**: Locked versions ensure same behavior over time
4. **Speed**: Docker image caching makes subsequent runs faster

## Troubleshooting

If you encounter issues:

1. **Rebuild the image**: `docker build -f Dockerfile.test -t deep-biblio-tools-test . --no-cache`
2. **Check Docker resources**: Ensure Docker has enough memory (at least 4GB recommended)
3. **Update dependencies**: Run `uv lock --upgrade` if dependencies need updating
