#!/usr/bin/env python3
"""Check for citation-bibliography mismatches in LaTeX files."""

import argparse

# import re  # Banned - using string methods instead
from pathlib import Path


def extract_citations(tex_content: str) -> set[str]:
    r"""Extract all citation keys from \cite commands in the text."""
    citations = set()

    # Find all \cite{...} commands
    # Handle multiple citations in one \cite command
    cite_cmd = "\\cite{"

    pos = 0
    while True:
        # Find the next \cite{ command
        pos = tex_content.find(cite_cmd, pos)
        if pos == -1:
            break

        # Find the closing brace
        start = pos + len(cite_cmd)
        end = tex_content.find("}", start)
        if end == -1:
            pos += 1
            continue

        # Extract citation keys
        cite_content = tex_content[start:end]
        # Split by comma to handle multiple citations
        keys = [k.strip() for k in cite_content.split(",")]
        citations.update(keys)

        pos = end + 1

    return citations


def extract_bibitem_keys(tex_content: str) -> set[str]:
    """Extract all bibliography item keys from \bibitem commands."""
    bibitems = set()

    # Find all \bibitem{key} or \bibitem[...]{key} commands
    bibitem_cmd = "\\bibitem"

    pos = 0
    while True:
        # Find the next \bibitem command
        pos = tex_content.find(bibitem_cmd, pos)
        if pos == -1:
            break

        # Skip past \bibitem
        pos += len(bibitem_cmd)

        # Check if there's an optional argument []
        if pos < len(tex_content) and tex_content[pos] == "[":
            # Skip the optional argument
            bracket_end = tex_content.find("]", pos)
            if bracket_end == -1:
                continue
            pos = bracket_end + 1

        # Now we should have a {
        if pos >= len(tex_content) or tex_content[pos] != "{":
            continue

        # Find the closing brace
        start = pos + 1
        end = tex_content.find("}", start)
        if end == -1:
            continue

        # Extract the key
        key = tex_content[start:end].strip()
        if key:
            bibitems.add(key)

        pos = end + 1

    return bibitems


def check_citation_bibliography_match(
    tex_path: Path,
) -> tuple[set[str], set[str]]:
    """
    Check for mismatches between citations and bibliography entries.

    Returns:
        Tuple of (uncited_bibitems, missing_bibitems)
    """
    content = tex_path.read_text(encoding="utf-8")

    # Extract citations and bibliography items
    citations = extract_citations(content)
    bibitems = extract_bibitem_keys(content)

    # Find mismatches
    uncited_bibitems = bibitems - citations
    missing_bibitems = citations - bibitems

    return uncited_bibitems, missing_bibitems


def main():
    parser = argparse.ArgumentParser(
        description="Check for citation-bibliography mismatches in LaTeX files"
    )
    parser.add_argument("input", type=Path, help="Input LaTeX file")
    parser.add_argument(
        "--remove-uncited",
        action="store_true",
        help="Remove uncited bibliography entries (creates new file)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output file when using --remove-uncited",
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: File not found: {args.input}")
        return 1

    # Check for mismatches
    uncited, missing = check_citation_bibliography_match(args.input)

    # Report findings
    print(f"Analysis of {args.input}:")
    print("-" * 80)

    if uncited:
        print(f"\nFound {len(uncited)} uncited bibliography entries:")
        for key in sorted(uncited):
            print(f"  - {key}")
    else:
        print("\nNo uncited bibliography entries found.")

    if missing:
        print(f"\nFound {len(missing)} citations without bibliography entries:")
        for key in sorted(missing):
            print(f"  - {key}")
    else:
        print("\nNo missing bibliography entries found.")

    # Remove uncited entries if requested
    if args.remove_uncited and uncited:
        content = args.input.read_text(encoding="utf-8")
        new_content = []
        lines = content.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i]

            # Check if this line starts a bibitem entry for an uncited key
            is_uncited_entry = False
            for key in uncited:
                if f"\\bibitem{{{key}}}" in line or (
                    "\\bibitem[" in line and f"]{{{key}}}" in line
                ):
                    is_uncited_entry = True
                    break

            if is_uncited_entry:
                # Skip this line and subsequent lines until next \\bibitem
                i += 1
                while i < len(lines) and not lines[i].strip().startswith(
                    "\\bibitem"
                ):
                    i += 1
                continue

            new_content.append(line)
            i += 1

        # Join and clean up extra blank lines
        content = "\n".join(new_content)
        while "\n\n\n" in content:
            content = content.replace("\n\n\n", "\n\n")

        # Write output
        output_path = args.output or args.input.with_stem(
            args.input.stem + "_cleaned"
        )
        output_path.write_text(content, encoding="utf-8")
        print(
            f"\nRemoved {len(uncited)} uncited entries. Output written to: {output_path}"
        )

    return 0


if __name__ == "__main__":
    exit(main())
