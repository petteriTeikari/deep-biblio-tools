#!/usr/bin/env python3
"""Remove duplicate bibliography sections from a LaTeX file."""

import argparse

# import re  # Banned - using string methods instead
from pathlib import Path


def remove_duplicate_bibliography(
    tex_path: Path, output_path: Path | None = None
):
    """Remove duplicate bibliography sections, keeping only the last one."""

    content = tex_path.read_text(encoding="utf-8")

    # Find all bibliography sections
    matches = []
    begin_str = "\\begin{thebibliography}"
    end_str = "\\end{thebibliography}"

    pos = 0
    while True:
        begin_pos = content.find(begin_str, pos)
        if begin_pos == -1:
            break

        # Find the closing brace after \begin{thebibliography}{
        brace_start = content.find("{", begin_pos + len(begin_str))
        if brace_start == -1:
            break

        # Find matching end
        end_pos = content.find(end_str, brace_start)
        if end_pos == -1:
            break

        end_pos += len(end_str)

        # Create a match-like object
        class Match:
            def __init__(self, start, end):
                self._start = start
                self._end = end

            def start(self):
                return self._start

            def end(self):
                return self._end

        matches.append(Match(begin_pos, end_pos))
        pos = end_pos

    if len(matches) <= 1:
        print(
            f"Found {len(matches)} bibliography section(s). No duplicates to remove."
        )
        return

    print(
        f"Found {len(matches)} bibliography sections. Removing all but the last one."
    )

    # Remove all but the last bibliography
    # Work backwards to avoid position shifts
    for i in range(len(matches) - 2, -1, -1):
        match = matches[i]
        content = content[: match.start()] + content[match.end() :]

    # Write output
    if output_path is None:
        output_path = tex_path.with_stem(tex_path.stem + "_fixed")

    output_path.write_text(content, encoding="utf-8")
    print(f"Written fixed content to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Remove duplicate bibliography sections"
    )
    parser.add_argument("input", type=Path, help="Input LaTeX file")
    parser.add_argument("-o", "--output", type=Path, help="Output file")

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}")
        return 1

    remove_duplicate_bibliography(args.input, args.output)
    return 0


if __name__ == "__main__":
    exit(main())
