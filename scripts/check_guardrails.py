#!/usr/bin/env python3
"""Check compliance with Claude guardrails."""

import sys
from pathlib import Path

REQUIRED_FILES = [
    "CLAUDE.md",
    ".claude/CLAUDE.md",
    ".claude/golden-paths.md",
    ".claude/auto-context.yaml",
]

FORBIDDEN_PATTERNS = [
    ("**/*_improved.py", "No *_improved.py files allowed"),
    ("**/*_v2.py", "No *_v2.py files allowed"),
    ("**/*_v3.py", "No *_v3.py files allowed"),
    ("**/*_fixed.py", "No *_fixed.py files allowed"),
    ("**/*_new.py", "No *_new.py files allowed"),
    ("**/script_*.py", "No generic script_* names allowed"),
]


def check_guardrails() -> bool:
    """Check all guardrail requirements."""
    errors = []
    project_root = Path(__file__).parent.parent

    # Check required files exist
    for req_file in REQUIRED_FILES:
        file_path = project_root / req_file
        if not file_path.exists():
            errors.append(f"Missing required file: {req_file}")

    # Check root CLAUDE.md references .claude/CLAUDE.md
    root_claude = project_root / "CLAUDE.md"
    if root_claude.exists():
        content = root_claude.read_text()
        if ".claude/CLAUDE.md" not in content:
            errors.append("Root CLAUDE.md must reference .claude/CLAUDE.md")

    # Check forbidden patterns
    for pattern, message in FORBIDDEN_PATTERNS:
        matches = list(project_root.glob(pattern))
        for match in matches:
            # Skip hidden directories and caches
            if any(
                p in str(match)
                for p in [
                    ".git",
                    "__pycache__",
                    ".pytest_cache",
                    "venv",
                    ".venv",
                ]
            ):
                continue
            errors.append(f"{match.relative_to(project_root)}: {message}")

    if errors:
        print("[FAIL] Guardrail violations found:")
        for error in errors:
            print(f"  - {error}")
        return False

    print("[PASS] All guardrail checks passed!")
    return True


if __name__ == "__main__":
    if not check_guardrails():
        sys.exit(1)
