#!/usr/bin/env python3
"""
Fix LaTeX citation commands to use \\cite vs \\citep correctly.

This script applies the following rules:
1. Remove parentheses around \\citep commands
2. Convert \\citep to \\cite when preceded by prepositions
3. Combine multiple adjacent citations

Usage:
    python scripts/fix_latex_citations.py input.tex [output.tex]

If output file is not specified, modifies the input file in place.
"""

import argparse

# import re  # Banned - using string methods instead
import sys
from pathlib import Path


def fix_double_parentheses(content: str) -> str:
    """Remove parentheses around \\citep commands to avoid double parentheses."""
    # Fix patterns using string methods

    # Fix (\\citep{key})
    i = 0
    while i < len(content):
        if content[i : i + 7] == "(\\citep":
            # Find the matching closing brace and parenthesis
            j = i + 7
            if j < len(content) and content[j] == "{":
                brace_count = 1
                k = j + 1
                while k < len(content) and brace_count > 0:
                    if content[k] == "{":
                        brace_count += 1
                    elif content[k] == "}":
                        brace_count -= 1
                    k += 1

                if brace_count == 0 and k < len(content) and content[k] == ")":
                    # Extract the key
                    key = content[j + 1 : k - 1]
                    # Replace the whole pattern
                    replacement = f"\\citep{{{key}}}"
                    content = content[:i] + replacement + content[k + 1 :]
                    i += len(replacement)
                    continue

        # Fix [\\citep{key}]
        elif content[i : i + 7] == "[\\citep":
            j = i + 7
            if j < len(content) and content[j] == "{":
                brace_count = 1
                k = j + 1
                while k < len(content) and brace_count > 0:
                    if content[k] == "{":
                        brace_count += 1
                    elif content[k] == "}":
                        brace_count -= 1
                    k += 1

                if brace_count == 0 and k < len(content) and content[k] == "]":
                    key = content[j + 1 : k - 1]
                    replacement = f"\\citep{{{key}}}"
                    content = content[:i] + replacement + content[k + 1 :]
                    i += len(replacement)
                    continue

        i += 1

    return content


def convert_citep_to_cite(content: str) -> str:
    """Convert \\citep to \\cite when preceded by prepositions."""
    # Prepositions and phrases that should use \cite
    prepositions = [
        "by",
        "from",
        "according to",
        "following",
        "per",
        "in",
        "as described by",
        "as documented by",
        "as shown by",
        "as demonstrated by",
        "as reported by",
        "as noted by",
        "as discussed by",
        "as explained by",
        "as stated by",
        "as defined by",
        "as proposed by",
        "as suggested by",
        "as presented by",
        "as outlined by",
        "as analyzed by",
        "as reviewed by",
        "based on",
        "building on",
        "extending",
        "adapting",
        "modifying",
        "improving upon",
    ]

    # Sort by length (longest first) to avoid partial matches
    prepositions.sort(key=len, reverse=True)

    lines = content.split("\n")
    for line_idx, line in enumerate(lines):
        line_lower = line.lower()

        for prep in prepositions:
            prep_lower = prep.lower()
            # Look for preposition followed by space and \citep
            i = 0
            while i < len(line_lower):
                pos = line_lower.find(prep_lower, i)
                if pos == -1:
                    break

                # Check word boundary before
                if pos > 0 and line[pos - 1].isalnum():
                    i = pos + 1
                    continue

                # Check for space and \citep after
                end_pos = pos + len(prep_lower)
                if (
                    end_pos < len(line)
                    and line[end_pos : end_pos + 7] == " \\citep"
                ):
                    # Find the citation key
                    cite_start = end_pos + 7
                    if cite_start < len(line) and line[cite_start] == "{":
                        brace_count = 1
                        j = cite_start + 1
                        while j < len(line) and brace_count > 0:
                            if line[j] == "{":
                                brace_count += 1
                            elif line[j] == "}":
                                brace_count -= 1
                            j += 1

                        if brace_count == 0:
                            # Replace \citep with \cite
                            key = line[cite_start + 1 : j - 1]
                            new_cite = f" \\cite{{{key}}}"
                            line = line[:end_pos] + new_cite + line[j:]
                            line_lower = line.lower()

                i = pos + 1

        lines[line_idx] = line

    return "\n".join(lines)


def combine_adjacent_citations(content: str) -> str:
    """Combine multiple adjacent citations into single commands."""
    # Apply patterns repeatedly until no more changes
    changed = True
    while changed:
        changed = False
        old_content = content

        # Find and combine adjacent citations
        i = 0
        while i < len(content):
            # Look for \citep or \cite
            if (
                content[i : i + 6] == "\\citep"
                or content[i : i + 5] == "\\cite"
            ):
                cmd_len = 6 if content[i : i + 6] == "\\citep" else 5
                cmd = content[i : i + cmd_len]

                # Find the first citation
                if i + cmd_len < len(content) and content[i + cmd_len] == "{":
                    brace_count = 1
                    j = i + cmd_len + 1
                    while j < len(content) and brace_count > 0:
                        if content[j] == "{":
                            brace_count += 1
                        elif content[j] == "}":
                            brace_count -= 1
                        j += 1

                    if brace_count == 0:
                        first_key = content[i + cmd_len + 1 : j - 1]

                        # Look for separator and second citation
                        k = j
                        while k < len(content) and content[k] in " \t":
                            k += 1

                        # Check for separators: ; , or just space
                        if k < len(content) and content[k] in ";,":
                            content[k]
                            k += 1
                            while k < len(content) and content[k] in " \t":
                                k += 1

                        # Look for second citation with same command
                        if (
                            content[k : k + cmd_len] == cmd
                            and k + cmd_len < len(content)
                            and content[k + cmd_len] == "{"
                        ):
                            brace_count = 1
                            pos = k + cmd_len + 1
                            while pos < len(content) and brace_count > 0:
                                if content[pos] == "{":
                                    brace_count += 1
                                elif content[pos] == "}":
                                    brace_count -= 1
                                pos += 1

                            if brace_count == 0:
                                second_key = content[k + cmd_len + 1 : pos - 1]
                                # Combine the citations
                                replacement = (
                                    f"{cmd}{{{first_key}, {second_key}}}"
                                )
                                content = (
                                    content[:i] + replacement + content[pos:]
                                )
                                changed = True
                                continue

                        i = j
                    else:
                        i += 1
                else:
                    i += 1
            else:
                i += 1

        if content != old_content:
            changed = True

    return content


def fix_special_cases(content: str) -> str:
    """Fix special citation cases using string methods."""
    lines = content.split("\n")

    for line_idx, line in enumerate(lines):
        # Fix sentence-starting citations: "\citep{key} found that..." -> "\cite{key} found that..."
        if line.startswith("\\citep"):
            # Find the citation
            if line.startswith("\\citep{"):
                brace_count = 1
                i = 7  # After \citep{
                while i < len(line) and brace_count > 0:
                    if line[i] == "{":
                        brace_count += 1
                    elif line[i] == "}":
                        brace_count -= 1
                    i += 1

                if brace_count == 0:
                    key = line[7 : i - 1]
                    # Check if followed by verb-like words
                    rest = line[i:].lstrip()
                    if rest and (
                        rest.startswith(
                            (
                                "found",
                                "showed",
                                "demonstrated",
                                "reported",
                                "noted",
                                "discussed",
                                "explained",
                                "stated",
                                "defined",
                                "proposed",
                                "suggested",
                                "presented",
                                "outlined",
                                "analyzed",
                                "reviewed",
                            )
                        )
                    ):
                        line = f"\\cite{{{key}}}" + line[i:]
                        lines[line_idx] = line

        # Fix cases like "Author et al. \citep{key}" -> "Author et al. \cite{key}"
        i = 0
        while i < len(line):
            # Look for potential author patterns before \citep
            if line[i : i + 6] == "\\citep":
                # Look backwards for author patterns
                j = i - 1
                while j >= 0 and line[j] in " \t":
                    j -= 1

                # Check for "et al." pattern
                if j >= 5 and line[j - 5 : j + 1] == "et al.":
                    # Look further back for author name
                    k = j - 6
                    while k >= 0 and line[k] in " \t":
                        k -= 1

                    # Check for capitalized word (author name)
                    word_start = k
                    while word_start >= 0 and (
                        line[word_start].isalnum() or line[word_start] in "&"
                    ):
                        word_start -= 1
                    word_start += 1

                    if word_start < k and line[word_start].isupper():
                        # This looks like "Author et al. \citep" - convert to \cite
                        if i + 6 < len(line) and line[i + 6] == "{":
                            brace_count = 1
                            cite_end = i + 7
                            while cite_end < len(line) and brace_count > 0:
                                if line[cite_end] == "{":
                                    brace_count += 1
                                elif line[cite_end] == "}":
                                    brace_count -= 1
                                cite_end += 1

                            if brace_count == 0:
                                key = line[i + 7 : cite_end - 1]
                                line = (
                                    line[:i]
                                    + f"\\cite{{{key}}}"
                                    + line[cite_end:]
                                )
                                lines[line_idx] = line
                                i += 5  # Skip past \cite
                                continue

                i += 1
            else:
                i += 1

    return "\n".join(lines)


def process_file(input_path: Path, output_path: Path) -> tuple[int, list[str]]:
    """Process a LaTeX file to fix citations."""
    if output_path.resolve() == input_path.resolve():
        raise ValueError("Output path cannot be the same as input path")

    # Read file
    with open(input_path, encoding="utf-8") as f:
        content = f.read()

    original_content = content
    changes = []

    # Apply fixes in order
    content = fix_double_parentheses(content)
    if content != original_content:
        changes.append("Removed parentheses around \\citep commands")

    temp = content
    content = convert_citep_to_cite(content)
    if content != temp:
        changes.append("Converted \\citep to \\cite after prepositions")

    temp = content
    content = combine_adjacent_citations(content)
    if content != temp:
        changes.append("Combined adjacent citations")

    temp = content
    content = fix_special_cases(content)
    if content != temp:
        changes.append("Fixed special citation cases")

    # Count changes
    citep_before = original_content.count("\\citep{")
    cite_before = original_content.count("\\cite{")
    citep_after = content.count("\\citep{")
    cite_after = content.count("\\cite{")

    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Return statistics
    total_changes = abs(citep_before - citep_after) + abs(
        cite_before - cite_after
    )

    if total_changes > 0:
        changes.append(f"\\citep: {citep_before} → {citep_after}")
        changes.append(f"\\cite: {cite_before} → {cite_after}")

    return total_changes, changes


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Fix LaTeX citation commands (\\cite vs \\citep)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s document.tex                    # Creates document_citefix.tex
  %(prog)s input.tex output.tex           # Save to specified file
  %(prog)s --suffix _fixed document.tex   # Creates document_fixed.tex
  %(prog)s --dry-run document.tex         # Preview changes without modifying
        """,
    )

    parser.add_argument("input_file", type=Path, help="Input LaTeX file")

    parser.add_argument(
        "output_file",
        type=Path,
        nargs="?",
        help="Output LaTeX file (default: input_citefix.tex)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying files",
    )

    parser.add_argument(
        "--suffix",
        default="_citefix",
        help="Suffix to add to output filename (default: _citefix)",
    )

    args = parser.parse_args()

    # Validate input
    if not args.input_file.exists():
        print(f"Error: Input file not found: {args.input_file}")
        return 1

    # Handle dry run
    if args.dry_run:
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".tex", delete=False
        ) as tmp:
            temp_path = Path(tmp.name)

        total_changes, changes = process_file(args.input_file, temp_path)

        if total_changes > 0:
            print(f"Would make {total_changes} changes:")
            for change in changes:
                print(f"  - {change}")
        else:
            print("No changes needed")

        temp_path.unlink()
        return 0

    # Determine output path - NEVER overwrite the original
    if args.output_file:
        output_path = args.output_file
    else:
        # Generate output filename with suffix
        stem = args.input_file.stem
        suffix = args.input_file.suffix
        output_path = args.input_file.parent / f"{stem}{args.suffix}{suffix}"

    # Check if output would overwrite input
    if output_path.resolve() == args.input_file.resolve():
        print(
            "Error: Output path would overwrite input file. Use a different output name or suffix."
        )
        return 1
    total_changes, changes = process_file(args.input_file, output_path)

    # Report results
    if total_changes > 0:
        print(
            f"[SUCCESS] Fixed {total_changes} citation commands in {output_path}"
        )
        for change in changes:
            print(f"  - {change}")
    else:
        print(f"[INFO] No citation fixes needed in {args.input_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
