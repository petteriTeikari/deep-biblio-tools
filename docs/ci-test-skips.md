# CI Test Skips Documentation

This document explains why certain tests are skipped in CI environments.

## tex2lyx Tests

**Status**: Skipped in CI
**Location**: `tests/converters/test_to_lyx.py`
**Reason**: tex2lyx requires a fully configured LyX user directory which is not available in minimal Docker containers

### Technical Details
- tex2lyx expects files like `textclass.lst`, `lyxmodules.lst`, and layout files
- Creating these in Docker requires significant configuration
- Tests pass locally where LyX is properly installed

### Future Fix
See `docs/tex2lyx-docker-setup.md` for the plan to properly configure tex2lyx in Docker.

## NeRF Citation Tests

**Status**: Skipped in CI
**Location**: `tests/test_nerf_citation.py`
**Reason**: arXiv API responses are inconsistent in CI environment

### Technical Details
- Tests verify that the full NeRF paper title is fetched from arXiv
- Works consistently in local development
- In CI, the API sometimes returns incomplete or different metadata
- Could be due to:
  - Rate limiting
  - Network conditions
  - Geographic API endpoints
  - Caching differences

### What the Tests Verify
1. `test_nerf_full_title`: Checks that arXiv title "NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis" is fetched
2. `test_nerf_with_prefer_arxiv`: Verifies prefer_arxiv option still gets full title

### Why It's Safe to Skip
- Core citation extraction functionality is tested by other tests
- The issue is specific to this one paper's metadata retrieval
- Manual testing confirms the functionality works correctly

## General CI Skip Strategy

Tests are skipped in CI when:
1. They require system dependencies not available in minimal containers
2. They depend on external APIs with inconsistent responses
3. The functionality is thoroughly tested in other tests
4. Local testing confirms the functionality works

All skipped tests should:
- Have clear skip reasons
- Be documented here
- Have a plan for future resolution (if applicable)
- Still run in local development
