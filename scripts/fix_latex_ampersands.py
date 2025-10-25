#!/usr/bin/env python3
"""
Fix misplaced & characters in LaTeX documents.
The & character needs to be escaped as \\& in LaTeX unless it's:
1. In a URL (the first argument of \\href)
2. Inside a tabular, array, or align environment
3. Already escaped
"""

import argparse
import logging

# import re  # Banned - using string methods instead
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


class AmpersandFixer:
    """Fix unescaped ampersand characters in LaTeX documents."""

    def __init__(self):
        # Environments where & is used for alignment
        self.align_environments = [
            "align",
            "align*",
            "aligned",
            "alignat",
            "alignat*",
            "array",
            "tabular",
            "tabular*",
            "tabularx",
            "matrix",
            "pmatrix",
            "bmatrix",
            "vmatrix",
            "Vmatrix",
            "cases",
            "split",
            "multline",
            "multline*",
            "gather",
            "gather*",
            "flalign",
            "flalign*",
        ]

    def is_in_alignment_env(self, content: str, position: int) -> bool:
        """Check if position is inside an alignment environment."""
        # Look backwards for environment starts
        before = content[:position]

        # Stack to track environments
        env_stack = []

        # Find all \begin and \end commands before this position
        all_envs = []

        # Find \begin{...} commands
        i = 0
        while i < len(before):
            if before[i : i + 7] == "\\begin{":
                # Find the closing brace
                j = i + 7
                while j < len(before) and before[j] != "}":
                    j += 1
                if j < len(before):
                    env_name = before[i + 7 : j]
                    if (
                        env_name.isalnum() or "_" in env_name
                    ):  # Valid environment name
                        all_envs.append((i, "begin", env_name))
                i = j
            else:
                i += 1

        # Find \end{...} commands
        i = 0
        while i < len(before):
            if before[i : i + 5] == "\\end{":
                # Find the closing brace
                j = i + 5
                while j < len(before) and before[j] != "}":
                    j += 1
                if j < len(before):
                    env_name = before[i + 5 : j]
                    if (
                        env_name.isalnum() or "_" in env_name
                    ):  # Valid environment name
                        all_envs.append((i, "end", env_name))
                i = j
            else:
                i += 1

        # Sort by position
        all_envs.sort(key=lambda x: x[0])

        # Build environment stack
        for _, cmd_type, env_name in all_envs:
            if cmd_type == "begin":
                env_stack.append(env_name)
            elif cmd_type == "end" and env_stack and env_stack[-1] == env_name:
                env_stack.pop()

        # Check if we're in any alignment environment
        return any(env in self.align_environments for env in env_stack)

    def fix_ampersands_in_href(self, url: str, text: str) -> tuple[str, int]:
        """Fix ampersands in \\href{url}{text} command."""
        changes = 0

        # Don't modify the URL part, only fix ampersands in the display text
        if (
            "&" in text and "http" not in text
        ):  # Don't modify if text is also a URL
            # Count unescaped ampersands
            i = 0
            while i < len(text):
                if text[i] == "&" and (i == 0 or text[i - 1] != "\\"):
                    changes += 1
                i += 1

            # Fix unescaped ampersands
            fixed_text = ""
            i = 0
            while i < len(text):
                if text[i] == "&" and (i == 0 or text[i - 1] != "\\"):
                    fixed_text += "\\&"
                else:
                    fixed_text += text[i]
                i += 1
        else:
            fixed_text = text

        return f"\\href{{{url}}}{{{fixed_text}}}", changes

    def fix_ampersands_in_line(
        self, line: str, full_content: str, line_start_pos: int
    ) -> tuple[str, int]:
        """Fix unescaped ampersands in a single line."""
        changes = 0

        # First, handle \href commands specially
        # Find all \href{...}{...} commands
        new_line = line
        offset = 0
        i = 0

        while i < len(line):
            if line[i : i + 6] == "\\href{":
                href_start = i
                # Find first closing brace (end of URL)
                j = i + 6
                brace_count = 1
                url_start = j
                while j < len(line) and brace_count > 0:
                    if line[j] == "{":
                        brace_count += 1
                    elif line[j] == "}":
                        brace_count -= 1
                    j += 1

                if brace_count == 0 and j < len(line) and line[j] == "{":
                    # Found URL, now find text
                    url = line[url_start : j - 1]
                    text_start = j + 1
                    j += 1
                    brace_count = 1
                    while j < len(line) and brace_count > 0:
                        if line[j] == "{":
                            brace_count += 1
                        elif line[j] == "}":
                            brace_count -= 1
                        j += 1

                    if brace_count == 0:
                        # Found complete href
                        text = line[text_start : j - 1]
                        href_end = j

                        # Check if this href is in an alignment environment
                        global_pos = line_start_pos + href_start + offset
                        if not self.is_in_alignment_env(
                            full_content, global_pos
                        ):
                            fixed_href, href_changes = (
                                self.fix_ampersands_in_href(url, text)
                            )
                            if href_changes > 0:
                                # Replace in the new_line
                                start = href_start + offset
                                end = href_end + offset
                                new_line = (
                                    new_line[:start]
                                    + fixed_href
                                    + new_line[end:]
                                )
                                offset += len(fixed_href) - (end - start)
                                changes += href_changes
                        i = j
                        continue
            i += 1

        # Now handle remaining ampersands not in hrefs or URLs
        # We need to protect hrefs and URLs from modification
        protected_ranges = []

        # Find all \href{...}{...} ranges
        i = 0
        while i < len(new_line):
            if new_line[i : i + 6] == "\\href{":
                start = i
                # Skip to end of href
                j = i + 6
                brace_count = 1
                while j < len(new_line) and brace_count > 0:
                    if new_line[j] == "{":
                        brace_count += 1
                    elif new_line[j] == "}":
                        brace_count -= 1
                    j += 1
                if (
                    brace_count == 0
                    and j < len(new_line)
                    and new_line[j] == "{"
                ):
                    j += 1
                    brace_count = 1
                    while j < len(new_line) and brace_count > 0:
                        if new_line[j] == "{":
                            brace_count += 1
                        elif new_line[j] == "}":
                            brace_count -= 1
                        j += 1
                    if brace_count == 0:
                        protected_ranges.append((start, j))
                        i = j
                        continue
            i += 1

        # Find all http:// or https:// URLs
        i = 0
        while i < len(new_line):
            if (
                new_line[i : i + 7] == "http://"
                or new_line[i : i + 8] == "https://"
            ):
                start = i
                # Find end of URL (whitespace or line end)
                j = i + 7 if new_line[i : i + 7] == "http://" else i + 8
                while j < len(new_line) and not new_line[j].isspace():
                    j += 1
                protected_ranges.append((start, j))
                i = j
            else:
                i += 1

        # Sort and merge overlapping ranges
        protected_ranges.sort(key=lambda x: x[0])
        merged_ranges = []
        for start, end in protected_ranges:
            if merged_ranges and start <= merged_ranges[-1][1]:
                merged_ranges[-1] = (
                    merged_ranges[-1][0],
                    max(merged_ranges[-1][1], end),
                )
            else:
                merged_ranges.append((start, end))

        # Check if position is in a protected range
        def is_protected(pos):
            for start, end in merged_ranges:
                if start <= pos < end:
                    return True
            return False

        # Process ampersands
        result = ""
        i = 0
        while i < len(new_line):
            if new_line[i] == "&" and not is_protected(i):
                # Check if it's escaped
                if i > 0 and new_line[i - 1] == "\\":
                    result += new_line[i]
                else:
                    # Check if we're in an alignment environment
                    char_pos = line_start_pos + len(result)
                    if not self.is_in_alignment_env(full_content, char_pos):
                        # Escape the ampersand
                        result += "\\&"
                        changes += 1
                    else:
                        result += new_line[i]
            else:
                result += new_line[i]
            i += 1

        return result, changes

    def fix_file(
        self,
        input_path: Path,
        output_path: Path = None,
        in_place: bool = False,
        backup: bool = True,
    ) -> int:
        """Fix ampersands in a LaTeX file."""
        # Read the file
        content = input_path.read_text(encoding="utf-8")
        lines = content.splitlines(keepends=True)

        # Process each line
        total_changes = 0
        fixed_lines = []
        current_pos = 0

        for i, line in enumerate(lines):
            fixed_line, changes = self.fix_ampersands_in_line(
                line, content, current_pos
            )
            if changes > 0:
                logger.info(f"Line {i + 1}: Fixed {changes} ampersand(s)")
                logger.info(f"  Before: {line.strip()}")
                logger.info(f"  After:  {fixed_line.strip()}")
            fixed_lines.append(fixed_line)
            total_changes += changes
            current_pos += len(line)

        if total_changes == 0:
            logger.info("No unescaped ampersands found.")
            return 0

        # Join the fixed content
        fixed_content = "".join(fixed_lines)

        # Handle output
        if in_place:
            if backup:
                backup_path = input_path.with_suffix(input_path.suffix + ".bak")
                input_path.rename(backup_path)
                logger.info(f"Created backup: {backup_path}")

            input_path.write_text(fixed_content, encoding="utf-8")
            logger.info(f"Fixed {total_changes} ampersand(s) in {input_path}")
        elif output_path:
            output_path.write_text(fixed_content, encoding="utf-8")
            logger.info(
                f"Fixed {total_changes} ampersand(s), saved to {output_path}"
            )
        else:
            print(fixed_content)

        return total_changes

    def check_file(self, input_path: Path) -> list[tuple[int, str, str]]:
        """Check for unescaped ampersands without fixing."""
        content = input_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        issues = []
        current_pos = 0

        for i, line in enumerate(lines):
            # Check for unescaped ampersands
            if "&" in line:
                # Quick check if any are unescaped
                # Quick check for unescaped ampersands
                has_unescaped = False
                for j in range(len(line)):
                    if line[j] == "&" and (j == 0 or line[j - 1] != "\\"):
                        has_unescaped = True
                        break
                if has_unescaped:
                    # Do detailed check
                    _, changes = self.fix_ampersands_in_line(
                        line, content, current_pos
                    )
                    if changes > 0:
                        # Find the specific positions
                        positions = []
                        for j, char in enumerate(line):
                            if char == "&" and (j == 0 or line[j - 1] != "\\"):
                                char_pos = current_pos + j
                                if not self.is_in_alignment_env(
                                    content, char_pos
                                ):
                                    positions.append(j)

                        if positions:
                            context = line.strip()
                            if len(context) > 80:
                                # Find the first & position and show context around it
                                first_pos = positions[0]
                                start = max(0, first_pos - 30)
                                end = min(len(line), first_pos + 50)
                                context = (
                                    "..." + line[start:end].strip() + "..."
                                )

                            issues.append(
                                (i + 1, context, f"Columns: {positions}")
                            )

            current_pos += len(line) + 1  # +1 for newline

        return issues


def main():
    parser = argparse.ArgumentParser(
        description="Fix unescaped & characters in LaTeX documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.tex -o output.tex
  %(prog)s input.tex --in-place --backup
  %(prog)s input.tex --check-only

This tool intelligently handles & characters:
- Escapes & to \\& in regular text
- Preserves & in URLs
- Preserves & in alignment environments (tabular, align, etc.)
- Fixes & in \\href display text while preserving URLs
        """,
    )

    parser.add_argument("input", type=Path, help="Input LaTeX file")
    parser.add_argument("-o", "--output", type=Path, help="Output file")
    parser.add_argument(
        "--in-place", action="store_true", help="Modify the input file in-place"
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        default=True,
        help="Create backup when using --in-place (default: True)",
    )
    parser.add_argument(
        "--no-backup",
        action="store_false",
        dest="backup",
        help="Don't create backup",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check for issues, don't fix",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show detailed information"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate arguments
    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        return 1

    if args.in_place and args.output:
        logger.error("Cannot use both --in-place and --output")
        return 1

    # Create fixer
    fixer = AmpersandFixer()

    if args.check_only:
        # Just check for issues
        issues = fixer.check_file(args.input)

        if issues:
            logger.info(
                f"Found {len(issues)} lines with unescaped & characters:\n"
            )
            for line_num, context, info in issues:
                logger.info(f"Line {line_num}: {info}")
                logger.info(f"  {context}\n")
        else:
            logger.info("No unescaped & characters found.")

        return len(issues)
    else:
        # Fix the file
        changes = fixer.fix_file(
            args.input, args.output, args.in_place, args.backup
        )
        return 0 if changes >= 0 else 1


if __name__ == "__main__":
    exit(main())
