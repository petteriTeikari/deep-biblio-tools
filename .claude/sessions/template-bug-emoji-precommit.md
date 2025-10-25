# Template Bug: Pre-commit Emoji Check Too Restrictive

**Date**: 2025-07-29
**Reported By**: Claude
**Status**: Open

## Issue
The pre-commit hook for emoji checking is configured to check ALL file types including markdown files, but according to the validation script and the claude-code-guardrails-template design, emojis should be ALLOWED in markdown files since they only cause problems in code files.

## Current Behavior
In `.pre-commit-config.yaml`:
```yaml
- id: no-emojis
  name: No emojis allowed
  entry: uv run python scripts/check_no_emojis.py
  language: system
  types_or: [python, markdown, yaml, text]  # <-- Includes markdown
  exclude: '^(\.git/|node_modules/|venv/|\.venv/)'
```

## Expected Behavior
The pre-commit hook should exclude markdown files from emoji checking, similar to how `validate_claude_constraints.py` handles it:
```python
# Skip markdown files (emojis are allowed here)
if file_path.suffix.lower() in [".md", ".rst"]:
    continue
```

## Fix Needed
Either:
1. Remove `markdown` from the `types_or` list in `.pre-commit-config.yaml`
2. Add logic to `scripts/check_no_emojis.py` to skip markdown files
3. Use `exclude` pattern to skip `*.md` files

## Impact
Currently, developers cannot use emojis in documentation, which may reduce readability and expressiveness of markdown documentation files.
