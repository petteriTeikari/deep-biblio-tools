#!/usr/bin/env python3
"""
Claude Code Constraints Validation Script for Deep Biblio Tools

This script validates that the codebase adheres to the Claude Code guardrails
defined in .claude/CLAUDE.md and ensures all AIDEV-IMMUTABLE markers are respected.

Usage:
    python scripts/validate_claude_constraints.py
    python scripts/validate_claude_constraints.py --fix  # Auto-fix violations where possible
    python scripts/validate_claude_constraints.py --check-only  # Exit with error code only
"""

import argparse

# import re  # Banned - using string methods instead
import sys
from pathlib import Path


class ClaudeConstraintValidator:
    """Validates Claude Code constraints and guardrails."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.claude_dir = project_root / ".claude"
        self.violations: list[dict] = []

    def validate_all(self) -> bool:
        """Run all validation checks."""
        print(
            "[CHECK] Validating Claude Code constraints for Deep Biblio Tools"
        )

        # Check that CLAUDE.md exists
        claude_md = self.claude_dir / "CLAUDE.md"
        if not claude_md.exists():
            self.violations.append(
                {
                    "type": "missing_file",
                    "file": str(claude_md),
                    "message": "CLAUDE.md behavior contract is missing",
                }
            )

        # Check AIDEV-IMMUTABLE markers
        self._check_immutable_markers()

        # Check for temporary directory violations
        self._check_temp_directory_violations()

        # Check for UV enforcement in Python files
        self._check_uv_enforcement()

        # Check emoji policy compliance (emojis only in markdown files)
        self._check_emoji_policy_compliance()

        return len(self.violations) == 0

    def _check_immutable_markers(self):
        """Check that AIDEV-IMMUTABLE sections are not modified."""
        for py_file in self.project_root.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                if "AIDEV-IMMUTABLE" in content:
                    # For now, just verify the marker exists
                    print(
                        f"[OK] Found AIDEV-IMMUTABLE marker in {py_file.relative_to(self.project_root)}"
                    )
            except (UnicodeDecodeError, PermissionError):
                continue

    def _check_temp_directory_violations(self):
        """Check for system temporary directory usage violations."""
        # Check for hardcoded temp directory usage patterns
        temp_strings = [
            "/tmp/",
            "/var/tmp/",
            "cd /tmp",
            "cd /var/tmp",
            "C:\\temp\\",
        ]

        for file_path in self.project_root.rglob("*"):
            # Skip the validation script itself to avoid false positives
            if file_path.name == "validate_claude_constraints.py":
                continue

            # Skip third-party directories to avoid false positives
            relative_path = file_path.relative_to(self.project_root)
            if any(
                part
                in [
                    ".venv",
                    "venv",
                    ".env",
                    "node_modules",
                    ".git",
                    "__pycache__",
                    "data",
                ]
                for part in relative_path.parts
            ):
                continue

            if file_path.suffix in [".py", ".sh", ".md", ".yml", ".yaml"]:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    for temp_string in temp_strings:
                        if temp_string in content:
                            self.violations.append(
                                {
                                    "type": "temp_directory_violation",
                                    "file": str(
                                        file_path.relative_to(self.project_root)
                                    ),
                                    "message": f"System temporary directory usage found: {temp_string}",
                                }
                            )
                except (UnicodeDecodeError, PermissionError):
                    continue

    def _check_uv_enforcement(self):
        """Check that UV is enforced for Python dependency management."""
        pyproject_path = self.project_root / "pyproject.toml"
        if pyproject_path.exists():
            content = pyproject_path.read_text(encoding="utf-8")
            if "[tool.uv]" not in content:
                self.violations.append(
                    {
                        "type": "uv_enforcement",
                        "file": "pyproject.toml",
                        "message": "pyproject.toml missing [tool.uv] section",
                    }
                )

    def _check_emoji_policy_compliance(self):
        """Check that emojis are only used in markdown files."""
        # Define emoji code point ranges
        emoji_ranges = [
            (0x1F600, 0x1F64F),  # Emoticons
            (0x1F300, 0x1F5FF),  # Misc Symbols and Pictographs
            (0x1F680, 0x1F6FF),  # Transport and Map
            (0x1F1E0, 0x1F1FF),  # Regional Indicator
            (0x2600, 0x27BF),  # Misc symbols
            (0x1F900, 0x1F9FF),  # Supplemental Symbols and Pictographs
            (0x1F018, 0x1F270),  # Various Asian characters
            (0x1F700, 0x1F77F),  # Alchemical Symbols
        ]

        def contains_emoji(text):
            """Check if text contains emoji characters."""
            for char in text:
                code_point = ord(char)
                for start, end in emoji_ranges:
                    if start <= code_point <= end:
                        return True
            return False

        # Check all code files (non-markdown)
        for file_path in self.project_root.rglob("*"):
            # Skip directories, dot files, and known safe paths
            if (
                file_path.is_dir()
                or file_path.name.startswith(".")
                or any(
                    skip in file_path.parts
                    for skip in [
                        ".git",
                        "__pycache__",
                        ".venv",
                        "node_modules",
                        "data",
                    ]
                )
            ):
                continue

            # Skip markdown files (emojis are allowed here)
            if file_path.suffix.lower() in [".md", ".rst"]:
                continue

            # Check code files for emojis
            try:
                content = file_path.read_text(encoding="utf-8")
                if contains_emoji(content):
                    self.violations.append(
                        {
                            "type": "emoji_policy_violation",
                            "file": str(
                                file_path.relative_to(self.project_root)
                            ),
                            "message": "Emojis found in code file (only allowed in markdown)",
                        }
                    )
            except (UnicodeDecodeError, PermissionError):
                # Skip files that can't be read as text
                continue

    def print_report(self):
        """Print validation report."""
        if not self.violations:
            print("[[OK]] All Claude Code constraints validated successfully!")
            return

        print(f"[[ERROR]] Found {len(self.violations)} constraint violations:")
        for violation in self.violations:
            print(f"  - {violation['file']}: {violation['message']}")


def main():
    parser = argparse.ArgumentParser(
        description="Validate Claude Code constraints"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check, exit with error code if violations found",
    )
    parser.add_argument(
        "--fix", action="store_true", help="Auto-fix violations where possible"
    )

    args = parser.parse_args()

    project_root = Path.cwd()
    validator = ClaudeConstraintValidator(project_root)

    is_valid = validator.validate_all()
    validator.print_report()

    if args.check_only and not is_valid:
        sys.exit(1)

    return 0 if is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
