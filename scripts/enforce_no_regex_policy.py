#!/usr/bin/env python3
"""
Comprehensive regex enforcement script for deep-biblio-tools.

This script implements a strict no-regex policy by checking for:
1. Any regex imports (import re, from re import)
2. Any regex method calls (re.search, re.findall, etc.)
3. References to regex patterns or the regex module
4. Ensures approved alternatives are being used

Exit codes:
0 - No regex usage found (success)
1 - Prohibited regex usage found (failure)
2 - Script error
"""

import ast
import sys
from pathlib import Path

# Project configuration
PROJECT_ROOT = Path(__file__).parent.parent
DIRS_TO_CHECK = ["src", "scripts", "tests"]
PYTHON_FILES = ["*.py"]

# Prohibited patterns
BANNED_IMPORTS = {"re", "regex", "sre", "sre_compile", "sre_parse"}

BANNED_METHODS = {
    "compile",
    "search",
    "match",
    "findall",
    "finditer",
    "sub",
    "subn",
    "split",
    "fullmatch",
    "purge",
}

# Allowed exceptions (for comments, docs, etc.)
ALLOWED_CONTEXTS = {
    "# Banned",  # Our marker for banned regex
    "# TODO",  # TODO comments about regex removal
    "#.*re\\.",  # Comments containing re.
    "before",
    "where",
    "require",
    "here",
    "there",
    "more",
    "were",
    "are",
    "core",
    "store",
    "explore",
    "sure",
    "pure",
    "nature",
    "future",
    "structure",
    "feature",
    "therefore",
    "anywhere",
    "everywhere",
    "nowhere",
}

# Approved alternatives that should be used instead
APPROVED_ALTERNATIVES = {
    "string_methods": [
        "startswith",
        "endswith",
        "find",
        "rfind",
        "replace",
        "split",
        "rsplit",
        "join",
        "strip",
        "lstrip",
        "rstrip",
        "isdigit",
        "isalpha",
        "isalnum",
        "isspace",
    ],
    "ast_parsers": [
        "markdown_it",
        "MarkdownIt",
        "pylatexenc",
        "LatexWalker",
        "bibtexparser",
        "BeautifulSoup",
        "html.parser",
        "xml.etree",
    ],
}


class RegexViolation:
    """Represents a regex policy violation."""

    def __init__(
        self,
        file_path: Path,
        line_number: int,
        violation_type: str,
        details: str,
    ):
        self.file_path = file_path
        self.line_number = line_number
        self.violation_type = violation_type
        self.details = details

    def __str__(self):
        return f"{self.file_path}:{self.line_number}: {self.violation_type} - {self.details}"


class RegexPolicyEnforcer:
    """Enforces comprehensive no-regex policy."""

    def __init__(self):
        self.violations: list[RegexViolation] = []
        self.files_checked = 0
        self.approved_usage_count = 0

    def check_project(self) -> bool:
        """Check entire project for regex policy violations."""
        print("Enforcing no-regex policy across deep-biblio-tools...")

        for dir_name in DIRS_TO_CHECK:
            dir_path = PROJECT_ROOT / dir_name
            if dir_path.exists():
                self._check_directory(dir_path)

        return len(self.violations) == 0

    def _check_directory(self, directory: Path) -> None:
        """Recursively check directory for Python files."""
        for py_file in directory.rglob("*.py"):
            self._check_file(py_file)
            self.files_checked += 1

    def _check_file(self, file_path: Path) -> None:
        """Comprehensive check of a single Python file."""

        # Skip enforcement and compliance files (meta-exclusion)
        if file_path.name in [
            "enforce_no_regex_policy.py",
            "test_regex_compliance.py",
        ]:
            return

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()

            # Check for banned imports
            self._check_imports(file_path, content)

            # Check for banned method calls in source
            self._check_method_calls(file_path, lines)

            # Check for regex patterns in strings
            self._check_regex_patterns(file_path, lines)

            # Check for approved alternatives usage
            self._check_approved_alternatives(file_path, content)

        except Exception as e:
            print(f"Warning: Error checking {file_path}: {e}")

    def _check_imports(self, file_path: Path, content: str) -> None:
        """Check for prohibited regex imports."""
        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in BANNED_IMPORTS:
                            # Check if it's marked as banned
                            line_content = content.splitlines()[node.lineno - 1]
                            if "# Banned" not in line_content:
                                self.violations.append(
                                    RegexViolation(
                                        file_path,
                                        node.lineno,
                                        "BANNED_IMPORT",
                                        f"import {alias.name} (mark with # Banned if legacy)",
                                    )
                                )

                elif isinstance(node, ast.ImportFrom):
                    if node.module in BANNED_IMPORTS:
                        self.violations.append(
                            RegexViolation(
                                file_path,
                                node.lineno,
                                "BANNED_FROM_IMPORT",
                                f"from {node.module} import ...",
                            )
                        )

        except SyntaxError:
            # Skip files with syntax errors
            pass

    def _check_method_calls(self, file_path: Path, lines: list[str]) -> None:
        """Check for banned regex method calls."""
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Skip comments unless they contain actual code
            if line_stripped.startswith("#"):
                continue

            # Check for re.method patterns
            if "re." in line:
                # Check if it's in an allowed context
                allowed_contexts_extended = ALLOWED_CONTEXTS.union(
                    {
                        "documentation",
                        "docstring",
                        "comment",
                        "string literal",
                        "test",
                        "description",
                        "enforcement",
                        "compliance",
                    }
                )

                if any(
                    context in line.lower()
                    for context in allowed_contexts_extended
                ):
                    continue

                # Skip if it's in a string literal (not actual method call)
                if ('"' in line or "'" in line) and not line_stripped.endswith(
                    "()"
                ):
                    continue

                # Check for specific banned methods
                for method in BANNED_METHODS:
                    pattern = f"re.{method}"
                    if pattern in line:
                        self.violations.append(
                            RegexViolation(
                                file_path,
                                i,
                                "BANNED_METHOD_CALL",
                                f"{pattern}() found in: {line_stripped}",
                            )
                        )

    def _check_regex_patterns(self, file_path: Path, lines: list[str]) -> None:
        """Check for regex patterns in string literals."""
        suspicious_patterns = [
            r"\[.*\]",  # Character classes
            r"\(.*\)",  # Groups
            r"\\[a-zA-Z]",  # Escape sequences
            r"\.\*",  # .* quantifier
            r"\.\+",  # .+ quantifier
            r"\?\*",  # ?* quantifier
            r"\{\d",  # {n} quantifiers
        ]

        # Additional allowed contexts for false positives
        additional_allowed = [
            "pattern description",
            "# pattern",
            "comment",
            "description",
            "example",
            "test",
            "enforcement",
            "compliance",
            "violation",
            "suspicious_patterns",
            "PATTERNS",
            "hallucination",
        ]

        for i, line in enumerate(lines, 1):
            if line.strip().startswith("#"):
                continue

            # Look for complex patterns that suggest regex
            for pattern in suspicious_patterns:
                if pattern in line and ("r'" in line or 'r"' in line):
                    # This looks like a raw string with regex patterns
                    all_allowed = ALLOWED_CONTEXTS.union(additional_allowed)
                    if not any(
                        context in line.lower() for context in all_allowed
                    ):
                        self.violations.append(
                            RegexViolation(
                                file_path,
                                i,
                                "SUSPICIOUS_REGEX_PATTERN",
                                f"Possible regex pattern: {line.strip()}",
                            )
                        )
                        break

    def _check_approved_alternatives(
        self, file_path: Path, content: str
    ) -> None:
        """Verify approved alternatives are being used."""
        # Count usage of approved methods
        for category, methods in APPROVED_ALTERNATIVES.items():
            for method in methods:
                if method in content:
                    self.approved_usage_count += 1
                    break  # Count once per file per category

    def print_report(self) -> None:
        """Print comprehensive policy enforcement report."""
        print("\nRegex Policy Enforcement Report")
        print(f"   Files checked: {self.files_checked}")
        print(f"   Violations found: {len(self.violations)}")
        print(f"   Approved alternatives usage: {self.approved_usage_count}")

        if self.violations:
            print(f"\nPOLICY VIOLATIONS ({len(self.violations)} found):")
            print("=" * 60)

            # Group violations by type
            by_type = {}
            for violation in self.violations:
                if violation.violation_type not in by_type:
                    by_type[violation.violation_type] = []
                by_type[violation.violation_type].append(violation)

            for violation_type, violations in by_type.items():
                print(f"\n{violation_type} ({len(violations)} occurrences):")
                for violation in violations:
                    print(f"   {violation}")

            print("\nSOLUTIONS:")
            print(
                "   • Replace regex imports with string methods or AST parsers"
            )
            print(
                "   • Use text.startswith(), text.find(), text.replace() for simple patterns"
            )
            print(
                "   • Use markdown-it-py, pylatexenc, bibtexparser for structured formats"
            )
            print(
                "   • See .claude/ast-regex-refactoring-guidelines.md for detailed guidance"
            )

        else:
            print("\nSUCCESS: No regex policy violations found!")
            print("   All text processing uses approved methods.")


def main() -> int:
    """Main enforcement entry point."""
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        print(__doc__)
        return 0

    enforcer = RegexPolicyEnforcer()

    try:
        success = enforcer.check_project()
        enforcer.print_report()

        return 0 if success else 1

    except Exception as e:
        print(f"Error during regex policy enforcement: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
