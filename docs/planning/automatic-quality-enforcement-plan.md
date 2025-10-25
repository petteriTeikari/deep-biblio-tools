# Automatic Quality Enforcement Plan

## 🎯 Objective
Create multiple layers of automatic enforcement to maintain code quality and consistency, reducing reliance on AI assistants remembering guardrails.

## 🔒 Enforcement Layers

### 1. Pre-commit Hooks (First Line of Defense)
**File**: `.pre-commit-config.yaml`

```yaml
repos:
  # Code formatting
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  # Import validation
  - repo: local
    hooks:
      - id: validate-imports
        name: Validate import structure
        entry: python scripts/validate_imports.py
        language: python
        files: \.py$

  # Guardrail compliance
  - repo: local
    hooks:
      - id: check-guardrails
        name: Check Claude guardrails
        entry: python scripts/check_guardrails.py
        language: python
        always_run: true

  # No regex in parsers
  - repo: local
    hooks:
      - id: no-regex-parser
        name: No regex for structured parsing
        entry: python scripts/check_no_regex_parsing.py
        language: python
        files: \.(py|md)$

  # Decision documentation
  - repo: local
    hooks:
      - id: check-decision-docs
        name: Check decision documentation
        entry: python scripts/check_decision_docs.py
        language: python
        files: \.py$
```

### 2. Automated Scripts

#### `scripts/validate_imports.py`
```python
#!/usr/bin/env python3
"""Validate import structure according to guardrails."""
import ast
import sys
from pathlib import Path

def check_imports(filepath: Path) -> list[str]:
    """Check import ordering and location."""
    errors = []
    with open(filepath) as f:
        tree = ast.parse(f.read())

    # Check all imports are at top
    import_ended = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if import_ended and node.lineno > 10:  # Allow some docstrings
                errors.append(f"{filepath}:{node.lineno}: Import not at top of file")
        elif isinstance(node, ast.FunctionDef):
            import_ended = True

    return errors

if __name__ == "__main__":
    errors = []
    for py_file in Path("src").rglob("*.py"):
        errors.extend(check_imports(py_file))

    if errors:
        print("\n".join(errors))
        sys.exit(1)
```

#### `scripts/check_guardrails.py`
```python
#!/usr/bin/env python3
"""Check compliance with Claude guardrails."""
import sys
from pathlib import Path

REQUIRED_FILES = [
    "CLAUDE.md",
    ".claude/CLAUDE.md",
    ".claude/golden-paths.md",
    ".claude/auto-context.yaml",
    ".claude/guardrails-learnings.md"
]

FORBIDDEN_PATTERNS = [
    ("**/*_improved.py", "No *_improved.py files allowed"),
    ("**/*_v2.py", "No *_v2.py files allowed"),
    ("**/*_v3.py", "No *_v3.py files allowed"),
    ("**/script_*.py", "No generic script_* names allowed"),
]

def check_guardrails() -> bool:
    """Check all guardrail requirements."""
    errors = []

    # Check required files exist
    for req_file in REQUIRED_FILES:
        if not Path(req_file).exists():
            errors.append(f"Missing required file: {req_file}")

    # Check forbidden patterns
    for pattern, message in FORBIDDEN_PATTERNS:
        matches = list(Path(".").glob(pattern))
        for match in matches:
            if not any(p in str(match) for p in [".git", "__pycache__", ".pytest_cache"]):
                errors.append(f"{match}: {message}")

    # Check for decision documentation
    decisions_dir = Path("docs/decisions")
    if not decisions_dir.exists():
        errors.append("Missing docs/decisions directory for ADRs")

    if errors:
        print("Guardrail violations found:")
        for error in errors:
            print(f"  - {error}")
        return False

    return True

if __name__ == "__main__":
    if not check_guardrails():
        sys.exit(1)
```

#### `scripts/check_no_regex_parsing.py`
```python
#!/usr/bin/env python3
"""Ensure no regex is used for structured format parsing."""
import re
import sys
from pathlib import Path

STRUCTURED_FORMATS = ["markdown", "latex", "bibtex", "xml", "json", "yaml"]
ALLOWED_SIMPLE_PATTERNS = [
    r"r'[\\^]?\\d{4}[\\$]?'",  # Year extraction
    r"r'10\\.\\d+/[^\\s]+'",   # DOI pattern
    r"r'\\d{4}\\.\\d{4,5}'",   # arXiv ID
]

def check_file(filepath: Path) -> list[str]:
    """Check for regex parsing of structured formats."""
    errors = []

    with open(filepath) as f:
        content = f.read()
        lines = content.splitlines()

    for i, line in enumerate(lines, 1):
        # Skip comments and strings
        if line.strip().startswith("#") or '"""' in line:
            continue

        # Check for regex patterns near structured format keywords
        if any(fmt in line.lower() for fmt in STRUCTURED_FORMATS):
            if "re." in line or "regex" in line:
                # Check if it's an allowed simple pattern
                if not any(pattern in line for pattern in ALLOWED_SIMPLE_PATTERNS):
                    errors.append(
                        f"{filepath}:{i}: Possible regex parsing of structured format"
                    )

    return errors

if __name__ == "__main__":
    errors = []
    for py_file in Path("src").rglob("*.py"):
        errors.extend(check_file(py_file))

    if errors:
        print("Regex parsing violations found:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
```

### 3. GitHub Actions Enforcement

#### `.github/workflows/quality-enforcement.yml`
```yaml
name: Quality Enforcement

on:
  pull_request:
  push:
    branches: [main]

jobs:
  enforce-quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install uv
        run: pip install uv

      - name: Install dependencies
        run: uv pip install -r requirements.txt

      - name: Run pre-commit checks
        uses: pre-commit/action@v3.0.0

      - name: Check guardrails compliance
        run: python scripts/check_guardrails.py

      - name: Validate no regex parsing
        run: python scripts/check_no_regex_parsing.py

      - name: Check decision documentation
        run: python scripts/check_decision_docs.py

      - name: Run comprehensive validation
        run: python scripts/validate_claude_constraints.py
```

### 4. Decision Documentation Enforcement

#### Architecture Decision Records (ADRs)
Create `docs/decisions/` directory with template:

```markdown
# ADR-001: [Title]

## Status
[Proposed | Accepted | Deprecated | Superseded]

## Context
[Why this decision is needed]

## Decision
[What we're doing]

## Consequences
[What happens as a result]

## Alternatives Considered
[Other options we evaluated]
```

#### `scripts/check_decision_docs.py`
```python
#!/usr/bin/env python3
"""Check that significant changes have decision documentation."""
import subprocess
import sys
from pathlib import Path

def get_changed_files() -> list[str]:
    """Get list of changed files in current branch."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "main...HEAD"],
            capture_output=True,
            text=True
        )
        return result.stdout.strip().split("\n")
    except:
        return []

def check_needs_adr(files: list[str]) -> bool:
    """Check if changes need an ADR."""
    significant_changes = [
        "src/api_clients/",  # API client changes
        "src/bibliography/",  # Core bibliography logic
        ".github/workflows/", # CI/CD changes
        "pyproject.toml",     # Dependency changes
    ]

    for file in files:
        for pattern in significant_changes:
            if pattern in file:
                return True
    return False

def check_has_recent_adr() -> bool:
    """Check if there's a recent ADR."""
    import datetime
    decisions_dir = Path("docs/decisions")

    if not decisions_dir.exists():
        return False

    # Check for ADRs modified in last 7 days
    cutoff = datetime.datetime.now() - datetime.timedelta(days=7)
    for adr in decisions_dir.glob("*.md"):
        if adr.stat().st_mtime > cutoff.timestamp():
            return True

    return False

if __name__ == "__main__":
    changed_files = get_changed_files()

    if check_needs_adr(changed_files) and not check_has_recent_adr():
        print("Significant changes detected but no recent ADR found!")
        print("Please document your decision in docs/decisions/")
        sys.exit(1)
```

### 5. Enhanced Ruff Configuration

#### `pyproject.toml` additions:
```toml
[tool.ruff]
target-version = "py312"
line-length = 80
src = ["src"]

select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
    "ARG", # flake8-unused-arguments
    "PTH", # flake8-use-pathlib
    "SIM", # flake8-simplify
    "TID", # flake8-tidy-imports
    "RET", # flake8-return
    "FBT", # flake8-boolean-trap
    "LOG", # flake8-logging
    "RUF", # Ruff-specific rules
]

[tool.ruff.per-file-ignores]
"tests/*" = ["ARG", "FBT"]

[tool.ruff.isort]
force-single-line = false
lines-after-imports = 2
```

### 6. VS Code Integration

#### `.vscode/settings.json`:
```json
{
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true,
        "source.fixAll": true
    },
    "[python]": {
        "editor.rulers": [80]
    },
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        "**/*_improved.py": true,
        "**/*_v2.py": true
    }
}
```

### 7. Claude-Specific Enforcement

#### `.claude/auto-context.yaml` enhancement:
```yaml
patterns:
  - .claude/**
  - docs/decisions/*.md
  - scripts/check_*.py

always_include:
  - .claude/CLAUDE.md
  - .claude/guardrails-learnings.md
  - .pre-commit-config.yaml

context_hints:
  - "ALWAYS run 'uv run ruff check --fix' before claiming completion"
  - "ALWAYS document decisions in docs/decisions/ for significant changes"
  - "NEVER create *_improved.py or *_v2.py files"
  - "NEVER use regex for parsing Markdown, LaTeX, or BibTeX"
```

## 🚀 Implementation Priority

1. **Phase 1** (Immediate):
   - Create pre-commit hooks
   - Add validation scripts
   - Update GitHub Actions

2. **Phase 2** (Next Sprint):
   - Implement ADR system
   - Enhance VS Code settings
   - Add more sophisticated checks

3. **Phase 3** (Future):
   - Create custom Claude Code plugin
   - Add AI review bot
   - Implement automatic fix suggestions

## 📊 Success Metrics

- Zero guardrail violations in CI/CD
- All PRs have appropriate ADRs
- No regex parsing violations
- Consistent code style across codebase
- Reduced "fix linting" commits

## 🔄 Maintenance

- Review and update checks monthly
- Add new patterns as issues arise
- Document enforcement decisions
- Keep guardrails current with project evolution
