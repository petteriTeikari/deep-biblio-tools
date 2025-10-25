#!/usr/bin/env python3
"""
Fix misplaced & characters in LaTeX bibliography entries.
The & character needs to be escaped as \\& in LaTeX unless it's in a URL.
"""

import argparse
import logging

# import re  # Banned - using string methods instead
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def fix_ampersands_in_entry(entry: str) -> tuple[str, int]:
    """Fix unescaped & characters in a bibliography entry."""
    changes = 0

    # Split entry into URL parts and non-URL parts
    # Protect URLs from modification
    urls = []

    # Find \href{...}{...} patterns
    i = 0
    while i < len(entry):
        if entry[i:].startswith("\\href{"):
            start = i
            i += 6  # Skip "\href{"
            brace_count = 1
            # Find matching close brace for first argument
            while i < len(entry) and brace_count > 0:
                if entry[i] == "{":
                    brace_count += 1
                elif entry[i] == "}":
                    brace_count -= 1
                i += 1
            # Now find second argument
            if i < len(entry) and entry[i] == "{":
                i += 1
                brace_count = 1
                while i < len(entry) and brace_count > 0:
                    if entry[i] == "{":
                        brace_count += 1
                    elif entry[i] == "}":
                        brace_count -= 1
                    i += 1
                urls.append((start, i, entry[start:i]))
        elif entry[i:].startswith("\\url{"):
            start = i
            i += 5  # Skip "\url{"
            brace_count = 1
            while i < len(entry) and brace_count > 0:
                if entry[i] == "{":
                    brace_count += 1
                elif entry[i] == "}":
                    brace_count -= 1
                i += 1
            urls.append((start, i, entry[start:i]))
        elif entry[i:].startswith("http://") or entry[i:].startswith(
            "https://"
        ):
            start = i
            # Find end of URL (space, }, or end of string)
            while i < len(entry) and entry[i] not in " \n\t}":
                i += 1
            urls.append((start, i, entry[start:i]))
        else:
            i += 1

    # Build a list of segments (URL and non-URL)
    segments = []
    last_end = 0

    for start, end, url in urls:
        if start > last_end:
            segments.append(("text", entry[last_end:start]))
        segments.append(("url", url))
        last_end = end

    if last_end < len(entry):
        segments.append(("text", entry[last_end:]))

    # Process non-URL segments
    fixed_segments = []
    for seg_type, content in segments:
        if seg_type == "text":
            # Find unescaped & characters (not preceded by \)
            fixed_content = ""
            i = 0
            local_changes = 0
            while i < len(content):
                if content[i] == "&":
                    # Check if it's already escaped
                    if i == 0 or content[i - 1] != "\\":
                        fixed_content += "\\&"
                        local_changes += 1
                    else:
                        fixed_content += "&"
                else:
                    fixed_content += content[i]
                i += 1
            if local_changes > 0:
                changes += local_changes
                fixed_segments.append(fixed_content)
            else:
                fixed_segments.append(content)
        else:
            # Keep URLs unchanged
            fixed_segments.append(content)

    fixed_entry = "".join(fixed_segments)
    return fixed_entry, changes


def fix_bibliography_ampersands(
    tex_file: Path,
    output_file: Path | None = None,
    in_place: bool = False,
    backup: bool = True,
):
    """Fix unescaped & characters in a LaTeX file's bibliography."""

    content = tex_file.read_text(encoding="utf-8")

    # Find bibliography section
    begin_str = "\\begin{thebibliography}"
    end_str = "\\end{thebibliography}"

    begin_pos = content.find(begin_str)
    if begin_pos == -1:
        logger.warning("No bibliography section found")
        return

    end_pos = content.find(end_str, begin_pos)
    if end_pos == -1:
        logger.warning("No closing \\end{thebibliography} found")
        return

    end_pos += len(end_str)
    bib_start = begin_pos
    bib_end = end_pos
    bib_content = content[bib_start:bib_end]

    # Split into entries
    entries = []
    current_entry = []

    for line in bib_content.split("\n"):
        if line.strip().startswith("\\bibitem"):
            if current_entry:
                entries.append("\n".join(current_entry))
            current_entry = [line]
        elif current_entry:
            current_entry.append(line)
        else:
            # Lines before first \bibitem or after last entry
            entries.append(line)

    # Don't forget the last entry
    if current_entry:
        entries.append("\n".join(current_entry))

    # Fix ampersands in each entry
    fixed_entries = []
    total_changes = 0
    entries_changed = 0

    for i, entry in enumerate(entries):
        if "\\bibitem" in entry:
            fixed_entry, changes = fix_ampersands_in_entry(entry)
            if changes > 0:
                entries_changed += 1
                total_changes += changes
                logger.info(f"Fixed {changes} & character(s) in entry {i}")
                # Show a preview of the change
                if "&" in entry and "\\&" in fixed_entry:
                    # Find the first change for preview
                    for j, (old_char, new_chars) in enumerate(
                        zip(entry, fixed_entry)
                    ):
                        if old_char == "&" and entry[max(0, j - 1) : j] != "\\":
                            preview_start = max(0, j - 20)
                            preview_end = min(len(entry), j + 20)
                            logger.info(
                                f"  Preview: ...{entry[preview_start:preview_end]}..."
                            )
                            logger.info(
                                f"       ->: ...{fixed_entry[preview_start:preview_end]}..."
                            )
                            break
            fixed_entries.append(fixed_entry)
        else:
            fixed_entries.append(entry)

    if total_changes == 0:
        logger.info("No unescaped & characters found in bibliography")
        return

    # Reconstruct the content
    new_bib = "\n".join(fixed_entries)
    new_content = content[:bib_start] + new_bib + content[bib_end:]

    # Handle output
    if in_place:
        if backup:
            backup_path = tex_file.with_suffix(tex_file.suffix + ".bak")
            tex_file.rename(backup_path)
            logger.info(f"Created backup: {backup_path}")

        tex_file.write_text(new_content, encoding="utf-8")
        logger.info(f"Updated {tex_file} in-place")
    elif output_file:
        output_file.write_text(new_content, encoding="utf-8")
        logger.info(f"Wrote fixed content to {output_file}")
    else:
        print(new_content)

    logger.info(
        f"\nSummary: Fixed {total_changes} & character(s) in {entries_changed} entries"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Fix unescaped & characters in LaTeX bibliography"
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
        help="Create backup when using --in-place",
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

    args = parser.parse_args()

    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        return

    if args.in_place and args.output:
        logger.error("Cannot use both --in-place and --output")
        return

    if args.check_only:
        # Just report issues
        content = args.input.read_text(encoding="utf-8")
        begin_str = "\\begin{thebibliography}"
        end_str = "\\end{thebibliography}"

        begin_pos = content.find(begin_str)
        if begin_pos != -1:
            end_pos = content.find(end_str, begin_pos)
            if end_pos != -1:
                end_pos += len(end_str)
                bib_content = content[begin_pos:end_pos]
                # Look for unescaped & not in URLs
                lines = bib_content.split("\n")
                issues = []

                for i, line in enumerate(lines):
                    # Skip URLs
                    if "http" in line or "\\href" in line or "\\url" in line:
                        continue

                    # Find unescaped &
                    j = 0
                    while j < len(line):
                        if line[j] == "&":
                            if j == 0 or line[j - 1] != "\\":
                                issues.append((i, line.strip()))
                                break
                        j += 1

            if issues:
                logger.info(
                    f"Found {len(issues)} lines with unescaped & characters:"
                )
                for line_num, line in issues[:10]:
                    logger.info(f"  Line {line_num}: {line[:80]}...")
                if len(issues) > 10:
                    logger.info(f"  ... and {len(issues) - 10} more")
            else:
                logger.info("No unescaped & characters found")
    else:
        fix_bibliography_ampersands(
            args.input, args.output, args.in_place, args.backup
        )


if __name__ == "__main__":
    main()
