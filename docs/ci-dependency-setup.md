# CI Dependencies Setup

## Overview

This document describes the external system dependencies required for running all tests in the deep-biblio-tools project.

## Required Dependencies

1. **pandoc** - Document conversion tool used for markdown to LaTeX conversion
2. **tex2lyx** - LaTeX to LyX converter (provided by the `lyx` package)

## Installation

### Docker Images

Both `Dockerfile` and `Dockerfile.test` have been updated to include these dependencies:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    pandoc \
    lyx \
    && rm -rf /var/lib/apt/lists/*
```

### GitHub Actions

The CI workflows (`ci.yml` and `ci-docker.yml`) now install these dependencies:

```yaml
- name: Install system dependencies
  run: |
    sudo apt-get update
    sudo apt-get install -y pandoc lyx
```

## Test Behavior

Tests that require these dependencies are properly decorated with skip conditions:

```python
@pytest.mark.skipif(not PANDOC_AVAILABLE, reason="pandoc not available")
```

This ensures that:
- Tests pass when dependencies are available
- Tests are skipped (not failed) when dependencies are missing
- CI can run successfully with all tests enabled

## Package Notes

- Using `lyx` package instead of `texlive-base` + `texlive-extra-utils` significantly reduces Docker image size
- The `lyx` package provides `tex2lyx` binary needed for LaTeX to LyX conversion tests
- `pandoc` is a standalone package that handles various document format conversions

## Verification

To verify dependencies are installed:

```bash
# Check pandoc
pandoc --version

# Check tex2lyx
which tex2lyx
```

With these changes, all 344 tests should pass in CI without any skips due to missing dependencies.
