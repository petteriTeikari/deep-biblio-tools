#!/usr/bin/env python3
"""
Filename Convention Tests

Ensures consistent naming conventions for Deep Biblio Tools:
- README.md and CLAUDE.md files should always be uppercase
- All other .md files should be lowercase with hyphens for word separation
- No duplicate files with different cases
"""

import fnmatch
import unittest
from pathlib import Path


class TestFilenameConventions(unittest.TestCase):
    """Test that files follow consistent naming conventions."""

    def setUp(self):
        """Set up test environment."""
        self.project_dir = Path(__file__).parent.parent

        # Directories to skip
        self.skip_dirs = {
            ".git",
            "__pycache__",
            ".pytest_cache",
            "node_modules",
            ".venv",
            "htmlcov",
            ".coverage",
            "temp_test_projects",
            "build",
            "dist",
        }

        # Load .gitignore patterns
        self.gitignore_patterns = self._load_gitignore()

    def _load_gitignore(self) -> list[str]:
        """Load patterns from .gitignore file."""
        gitignore_path = self.project_dir / ".gitignore"
        patterns = []

        if gitignore_path.exists():
            with open(gitignore_path) as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith("#"):
                        patterns.append(line)

        return patterns

    def _is_gitignored(self, file_path: Path) -> bool:
        """Check if a file matches any .gitignore pattern."""
        # Get relative path from project root
        try:
            relative_path = file_path.relative_to(self.project_dir)
        except ValueError:
            return False

        relative_str = str(relative_path)

        for pattern in self.gitignore_patterns:
            # Handle directory patterns (ending with /)
            if pattern.endswith("/"):
                dir_pattern = pattern.rstrip("/")
                if relative_str.startswith(dir_pattern + "/"):
                    return True
            # Handle glob patterns
            elif fnmatch.fnmatch(relative_str, pattern):
                return True

        return False

    def _find_markdown_files(self) -> list[Path]:
        """Find all markdown files in the project."""
        markdown_files = []

        for pattern in ["*.md"]:
            for file_path in self.project_dir.rglob(pattern):
                # Skip excluded directories
                if any(
                    skip_dir in file_path.parts for skip_dir in self.skip_dirs
                ):
                    continue

                # Skip files that are gitignored
                if self._is_gitignored(file_path):
                    continue

                markdown_files.append(file_path)

        return markdown_files

    def _find_case_duplicates(self) -> dict[tuple[str, str], list[Path]]:
        """Find files that exist in multiple cases."""
        markdown_files = self._find_markdown_files()

        # Group files by their lowercase name within the same directory
        lowercase_groups = {}
        for file_path in markdown_files:
            key = (str(file_path.parent), file_path.name.lower())
            if key not in lowercase_groups:
                lowercase_groups[key] = []
            lowercase_groups[key].append(file_path)

        # Find groups with multiple files
        duplicates = {}
        for key, file_list in lowercase_groups.items():
            if len(file_list) > 1:
                duplicates[key] = file_list

        return duplicates

    def test_no_case_duplicate_files(self):
        """Test that no files exist in multiple cases."""
        duplicates = self._find_case_duplicates()

        if duplicates:
            duplicate_msg = "\\n".join(
                [
                    f"  {parent}/{files[0].name.lower()}: {[f.name for f in files]}"
                    for (parent, _), files in duplicates.items()
                ]
            )
            self.fail(
                f"Found files with case conflicts:\\n{duplicate_msg}\\n\\n"
                f"Fix: Remove duplicate files or rename to follow convention"
            )

    def test_readme_files_uppercase(self):
        """Test that README files are uppercase."""
        markdown_files = self._find_markdown_files()
        violations = []

        for file_path in markdown_files:
            if (
                file_path.name.lower() == "readme.md"
                and file_path.name != "README.md"
            ):
                violations.append(file_path)

        if violations:
            violation_msg = "\\n".join(
                [
                    f"  {file.relative_to(self.project_dir)}"
                    for file in violations
                ]
            )
            self.fail(
                f"README files should be uppercase:\\n{violation_msg}\\n\\n"
                f"Fix: Rename to README.md"
            )

    def test_consistent_naming_pattern(self):
        """Test that non-README files follow consistent naming."""
        markdown_files = self._find_markdown_files()
        violations = []

        # Files that should follow lowercase-with-hyphens
        for file_path in markdown_files:
            if file_path.name == "README.md":
                continue  # Skip README files

            # Special files that are allowed to be uppercase
            special_files = {
                "CLAUDE.md",  # Project behavior contract
                "CHANGELOG.md",
                "LICENSE.md",
                "CONTRIBUTING.md",
            }

            if file_path.name in special_files:
                continue

            filename = file_path.stem

            # Check for mixed case issues
            if filename != filename.lower():
                violations.append(
                    (file_path, f"Should be lowercase: {filename.lower()}.md")
                )

            # Check for underscores (should be hyphens)
            if "_" in filename and file_path.name not in special_files:
                suggested = filename.replace("_", "-").lower()
                violations.append(
                    (file_path, f"Use hyphens not underscores: {suggested}.md")
                )

        if violations:
            violation_msg = "\\n".join(
                [
                    f"  {file.relative_to(self.project_dir)} → {suggestion}"
                    for file, suggestion in violations
                ]
            )
            self.fail(
                f"Files don't follow naming convention:\\n{violation_msg}\\n\\n"
                f"Convention: README.md and CLAUDE.md (uppercase), others lowercase-with-hyphens"
            )

    def test_no_problematic_characters(self):
        """Test that filenames don't contain problematic characters."""
        markdown_files = self._find_markdown_files()
        violations = []

        # Characters that can cause issues across platforms
        problematic_chars = {
            " ",
            "&",
            "(",
            ")",
            "[",
            "]",
            "{",
            "}",
            "|",
            "\\",
            "/",
            ":",
            "*",
            "?",
            '"',
            "<",
            ">",
            "'",
        }

        for file_path in markdown_files:
            filename = file_path.name

            for char in problematic_chars:
                if char in filename:
                    violations.append(
                        (file_path, f"Contains problematic character '{char}'")
                    )
                    break

        if violations:
            violation_msg = "\\n".join(
                [
                    f"  {file.relative_to(self.project_dir)} → {issue}"
                    for file, issue in violations
                ]
            )
            self.fail(
                f"Files contain problematic characters:\\n{violation_msg}\\n\\n"
                f"Fix: Use only letters, numbers, hyphens, and dots"
            )


if __name__ == "__main__":
    unittest.main()
