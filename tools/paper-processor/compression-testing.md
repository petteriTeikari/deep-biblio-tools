# Compression Testing Guide

This document describes how to use the compression regression testing system to monitor model/prompt drift in the summarization pipeline.

## Overview

The regression test uses a reference paper (BIM-based quantity takeoff) to track changes in summarization behavior over time. This helps detect:

- Model drift (when AI model behavior changes)
- Prompt effectiveness changes
- Unintended side effects from code changes
- API parameter impacts

## Quick Start

### 1. Run a Test

```bash
cd tools/paper-processor
./run_regression_test.sh
```

### 2. Save New Baseline

When you intentionally change the summarization behavior:

```bash
./run_regression_test.sh --save-baseline
```

### 3. Monitor Drift

Check for compression drift:

```bash
python3 monitor_compression_drift.py --check
```

Generate a report:

```bash
python3 monitor_compression_drift.py --report
```

## Baseline Metrics

Current baseline (as of 2025-08-23):
- **Paper**: BIM-based quantity takeoff (26,259 words)
- **Summary**: ~2,100 words
- **Compression**: ~8.0%
- **Target Range**: 10-25%

## Thresholds

The system alerts when:
- Word count changes by >20%
- Compression ratio changes by >25%

## CI/CD Integration

The regression test runs automatically:
- On PRs that modify summarization code
- Weekly via GitHub Actions
- On manual workflow dispatch

## What to Do When Drift is Detected

1. **Check if intentional**: Did you modify prompts or parameters?
2. **Review changes**: Look at the comparison files in `tests/`
3. **Investigate causes**:
   - Model version changes
   - API parameter changes
   - Prompt modifications
   - Temperature or max_tokens changes
4. **Update baseline** if changes are acceptable:
   ```bash
   ./run_regression_test.sh --save-baseline
   ```

## Files

- `tests/compression_baseline.json` - Current baseline metrics
- `tests/comparison_*.json` - Historical test results
- `compression_trends.png` - Visual trend analysis

## Extending the System

To add more test papers:

1. Edit `test_compression_regression.py`
2. Add paper paths to a list
3. Run tests on multiple papers
4. Average the results for more robust detection

## Future Enhancements

- Integration with Evidently AI for advanced drift detection
- Multiple reference papers for different document types
- Automatic baseline updates on stable branches
- Slack/email alerts for significant drift
- A/B testing for prompt improvements
