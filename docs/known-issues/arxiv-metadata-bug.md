# arXiv Metadata Fetching Bug

## Issue Description

The arXiv metadata fetching is returning incorrect paper information for arXiv ID 2003.08934.

### Expected Behavior
- URL: https://arxiv.org/abs/2003.08934
- Title: "NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis"
- Authors: Ben Mildenhall, Pratul P. Srinivasan, Matthew Tancik, et al.

### Actual Behavior (in Docker/CI)
- URL: https://arxiv.org/abs/2003.08934
- Title: "Gated Fusion Network for Degraded Image Super Resolution"
- Authors: Xinyi Zhang, Hang Dong, Zhe Hu, et al.

## Investigation Notes

1. The arXiv URL is correct - visiting it in a browser shows the NeRF paper
2. The issue only occurs in Docker/CI environments, not locally
3. Both test_nerf_full_title and test_nerf_with_prefer_arxiv fail with the same issue

## Possible Causes

1. **API Endpoint Differences**: Docker container might be hitting a different arXiv API endpoint
2. **Caching Issues**: There might be cached incorrect data somewhere
3. **Network/Proxy Issues**: Container networking might be redirecting requests
4. **API Response Parsing**: The code might be parsing the wrong field from the API response

## Temporary Solution

Tests are skipped in CI/Container environments until the root cause is identified and fixed.

## To Reproduce

```bash
docker build -f Dockerfile.test -t deep-biblio-test .
docker run --rm deep-biblio-test uv run pytest tests/test_nerf_citation.py -v
```

## Next Steps

1. Add debug logging to arXiv API calls to see actual responses
2. Compare API responses between local and Docker environments
3. Check if other arXiv papers have the same issue
4. Review the arXiv metadata extraction code for bugs
