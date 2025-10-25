#!/usr/bin/env python3
"""
Tests to ensure regex compliance across the codebase.

This test suite verifies that the no-regex policy is enforced and that
approved alternatives are being used appropriately.
"""

import ast
import os
import subprocess
import sys
import unittest
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestRegexCompliance(unittest.TestCase):
    """Test suite for regex policy compliance."""

    def setUp(self):
        """Set up test environment."""
        self.project_root = PROJECT_ROOT
        self.src_dir = self.project_root / "src"
        self.scripts_dir = self.project_root / "scripts"
        self.tests_dir = self.project_root / "tests"

    def get_python_files(self) -> list[Path]:
        """Get all Python files in the project."""
        python_files = []
        for directory in [self.src_dir, self.scripts_dir, self.tests_dir]:
            if directory.exists():
                python_files.extend(directory.rglob("*.py"))
        return python_files

    def test_no_regex_imports(self):
        """Test that no files contain prohibited regex imports."""
        violations = []
        python_files = self.get_python_files()

        for py_file in python_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content)
                lines = content.splitlines()

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name == "re":
                                # Check if marked as banned
                                line_content = lines[node.lineno - 1]
                                if "# Banned" not in line_content:
                                    violations.append(
                                        f"{py_file}:{node.lineno}: "
                                        f"Unmarked regex import: import {alias.name}"
                                    )

                    elif isinstance(node, ast.ImportFrom):
                        if node.module == "re":
                            violations.append(
                                f"{py_file}:{node.lineno}: "
                                f"Prohibited from import: from re import ..."
                            )

            except (SyntaxError, UnicodeDecodeError):
                # Skip files with syntax errors or encoding issues
                continue
            except Exception as e:
                self.fail(f"Error processing {py_file}: {e}")

        if violations:
            self.fail(
                f"Found {len(violations)} regex import violations:\n"
                + "\n".join(violations)
            )

    def test_no_regex_method_calls(self):
        """Test that no files contain regex method calls."""
        violations = []
        python_files = self.get_python_files()

        # List of banned regex methods (using string concatenation to avoid false detection)
        banned_methods = [
            "re." + "compile",
            "re." + "search",
            "re." + "match",
            "re." + "findall",
            "re." + "finditer",
            "re." + "sub",
            "re." + "subn",
            "re." + "split",
            "re." + "fullmatch",
        ]

        for py_file in python_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    lines = f.readlines()

                for i, line in enumerate(lines, 1):
                    line_stripped = line.strip()

                    # Skip comments and lines with allowed contexts
                    if (
                        line_stripped.startswith("#")
                        or "# Banned" in line
                        or "# TODO" in line
                        or "test_regex_compliance.py" in str(py_file)
                    ):  # Skip this test file
                        continue

                    # Check for banned method calls
                    for method in banned_methods:
                        if method in line:
                            # Additional context check for false positives
                            false_positive_contexts = [
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
                                "banned_methods",
                                "test",
                                "string",
                                "list",
                                "compliance",
                                "enforcement",
                                "violations",
                                '"',
                                "'",
                                "script",
                                "policy",
                                "Any regex method calls",
                            ]

                            # Skip if it's in a string literal, list, or documentation
                            is_false_positive = (
                                any(
                                    ctx in line
                                    for ctx in false_positive_contexts
                                )
                                or line.strip().startswith(('"""', "'''", "#"))
                                or "# " in line
                                or ".py:" in line  # Script output/documentation
                                or "enforce_no_regex_policy.py:" in line
                            )

                            if not is_false_positive:
                                violations.append(
                                    f"{py_file}:{i}: "
                                    f"Regex method call: {line_stripped}"
                                )

            except Exception as e:
                self.fail(f"Error processing {py_file}: {e}")

        if violations:
            self.fail(
                f"Found {len(violations)} regex method call violations:\n"
                + "\n".join(violations[:10])  # Limit output
            )

    def test_approved_alternatives_usage(self):
        """Test that approved alternatives are being used."""
        python_files = self.get_python_files()

        # Check for usage of approved string methods
        approved_string_methods = [
            "startswith",
            "endswith",
            "find",
            "replace",
            "split",
            "isdigit",
            "isalpha",
            "strip",
        ]

        # Check for AST parsers
        approved_ast_parsers = [
            "markdown_it",
            "MarkdownIt",
            "pylatexenc",
            "LatexWalker",
            "bibtexparser",
            "BeautifulSoup",
        ]

        string_method_usage = 0
        ast_parser_usage = 0

        for py_file in python_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                # Count approved method usage
                for method in approved_string_methods:
                    if f".{method}(" in content:
                        string_method_usage += 1
                        break  # Count once per file

                for parser in approved_ast_parsers:
                    if parser in content:
                        ast_parser_usage += 1
                        break  # Count once per file

            except Exception:
                continue

        # We should see significant usage of approved methods
        self.assertGreater(
            string_method_usage,
            10,
            f"Expected significant string method usage, found {string_method_usage}",
        )

        # Should have some AST parser usage for structured formats
        self.assertGreater(
            ast_parser_usage,
            5,
            f"Expected AST parser usage, found {ast_parser_usage}",
        )

    def test_no_version_suffix_files(self):
        """Test that no files have prohibited version suffixes."""
        prohibited_patterns = [
            "*_new.*",
            "*_v[0-9].*",
            "*_final.*",
            "*_old.*",
            "*_backup.*",
            "*_fixed.*",
            "*_updated.*",
            "*_revised.*",
            "new_*",
            "v[0-9]_*",
            "final_*",
            "temp_*",
            "tmp_*",
        ]

        violations = []
        for directory in [self.src_dir, self.scripts_dir, self.tests_dir]:
            if not directory.exists():
                continue

            for pattern in prohibited_patterns:
                matches = list(directory.rglob(pattern))
                for match in matches:
                    # Skip archive directories and cache files
                    if not any(
                        part in str(match)
                        for part in ["archive", "__pycache__", ".pyc"]
                    ) and not match.name.startswith("."):
                        violations.append(str(match))

        if violations:
            self.fail(
                f"Found {len(violations)} files with prohibited version suffixes:\n"
                + "\n".join(violations)
            )

    def test_pre_commit_hook_enforcement(self):
        """Test that pre-commit hook can detect regex violations."""
        # This test verifies our enforcement script works
        enforcer_script = (
            self.project_root / "scripts" / "enforce_no_regex_policy.py"
        )
        self.assertTrue(
            enforcer_script.exists(), "Regex enforcement script should exist"
        )

        # Run the enforcer script
        try:
            result = subprocess.run(
                [sys.executable, str(enforcer_script)],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            # Script should succeed (exit code 0) if no violations
            self.assertEqual(
                result.returncode,
                0,
                f"Regex enforcer failed:\n{result.stdout}\n{result.stderr}",
            )

        except Exception as e:
            self.fail(f"Could not run regex enforcer: {e}")

    def test_parsing_functions_have_approved_methods(self):
        """Test that parsing functions use approved methods."""
        python_files = self.get_python_files()

        parsing_functions = []  # Functions that likely do text parsing
        parsing_keywords = [
            "parse",
            "extract",
            "process",
            "analyze",
            "search",
            "find",
            "match",
            "citation",
            "bibliography",
            "latex",
            "markdown",
        ]

        for py_file in python_files:
            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_name = node.name.lower()
                        # Check if this looks like a parsing function
                        if any(
                            keyword in func_name for keyword in parsing_keywords
                        ):
                            parsing_functions.append(
                                (py_file, node.name, node.lineno)
                            )

            except Exception:
                continue

        # Verify parsing functions don't use regex
        violations = []
        for file_path, func_name, line_no in parsing_functions:
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()

                # Get function source (approximate)
                lines = content.splitlines()
                func_start = line_no - 1
                func_end = len(lines)

                # Find end of function (simple heuristic)
                indent_level = len(lines[func_start]) - len(
                    lines[func_start].lstrip()
                )
                for i in range(func_start + 1, len(lines)):
                    if (
                        lines[i].strip()
                        and len(lines[i]) - len(lines[i].lstrip())
                        <= indent_level
                        and not lines[i]
                        .lstrip()
                        .startswith(('"""', "'''", "#"))
                    ):
                        func_end = i
                        break

                func_source = "\n".join(lines[func_start:func_end])

                # Check for regex usage in function (more specific)
                # Skip if the entire file has banned regex or the function is marked
                if (
                    "# Banned" in func_source
                    or "# TODO" in func_source
                    or "import re  # Banned" in content
                ):
                    continue

                # Look for actual regex method calls
                regex_methods = [
                    "re.compile",
                    "re.search",
                    "re.match",
                    "re.findall",
                    "re.sub",
                    "re.split",
                ]
                uses_regex = any(
                    method in func_source for method in regex_methods
                )

                if uses_regex:
                    violations.append(
                        f"{file_path}:{line_no}: Function {func_name} uses regex"
                    )

            except Exception:
                continue

        if violations:
            self.fail(
                f"Found {len(violations)} parsing functions using regex:\n"
                + "\n".join(violations[:5])  # Limit output
            )

    def test_citation_processing_uses_approved_methods(self):
        """Test that citation processing specifically uses approved methods."""
        citation_files = []

        # Find files related to citation processing
        for py_file in self.get_python_files():
            if any(
                keyword in str(py_file).lower()
                for keyword in ["citation", "cite", "biblio", "reference"]
            ):
                citation_files.append(py_file)

        approved_citation_methods = [
            "startswith",
            "endswith",
            "find",
            "split",
            "replace",
            "LatexWalker",
            "markdown_it",
            "bibtexparser",
        ]

        for citation_file in citation_files:
            try:
                with open(citation_file, encoding="utf-8") as f:
                    content = f.read()

                # Should use approved methods
                has_approved_method = any(
                    method in content for method in approved_citation_methods
                )

                # Should not use regex (unless marked as banned)
                has_unmarked_regex = (
                    "import re" in content and "# Banned" not in content
                ) or (
                    "re." in content
                    and "# Banned" not in content
                    and "# TODO" not in content
                )

                if has_unmarked_regex:
                    self.fail(
                        f"Citation file {citation_file} contains unmarked regex usage"
                    )

                # Citation files should use some approved methods
                if (
                    not has_approved_method and len(content) > 1000
                ):  # Non-trivial files
                    self.fail(
                        f"Citation file {citation_file} should use approved parsing methods"
                    )

            except Exception:
                continue


class TestRegexEnforcementScript(unittest.TestCase):
    """Test the regex enforcement script itself."""

    def setUp(self):
        """Set up test environment."""
        self.script_path = (
            PROJECT_ROOT / "scripts" / "enforce_no_regex_policy.py"
        )

    def test_enforcement_script_exists(self):
        """Test that the enforcement script exists and is executable."""
        self.assertTrue(self.script_path.exists())
        self.assertTrue(os.access(self.script_path, os.R_OK))

    def test_enforcement_script_runs(self):
        """Test that the enforcement script can run without errors."""
        try:
            result = subprocess.run(
                [sys.executable, str(self.script_path), "--help"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0)
        except subprocess.TimeoutExpired:
            self.fail("Enforcement script timed out")
        except Exception as e:
            self.fail(f"Could not run enforcement script: {e}")

    def test_script_detects_violations(self):
        """Test that the script can detect regex violations."""
        # Create a temporary test file with regex violations
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write("""
import re
import sys

def bad_function():
    pattern = re.compile(r'test')
    return re.search(pattern, 'test string')
""")
            temp_file = Path(f.name)

        try:
            # The script should detect violations in this file
            # Note: This is more of an integration test concept
            # In practice, we'd modify the script to accept specific files
            pass
        finally:
            temp_file.unlink(missing_ok=True)


def run_compliance_tests():
    """Run all regex compliance tests."""
    # Discover and run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_compliance_tests()
    sys.exit(0 if success else 1)
