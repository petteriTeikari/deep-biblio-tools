#!/usr/bin/env python3
"""Clean bibliography to only include cited entries while preserving document structure."""

import argparse

# import re  # Banned - using string methods instead
from pathlib import Path


def clean_bibliography(tex_path: Path, output_path: Path | None = None):
    """Remove uncited bibliography entries while preserving document structure."""

    content = tex_path.read_text(encoding="utf-8")

    # Extract all citations
    citations = set()

    # Find all \cite{...} and \citep{...} commands
    i = 0
    while i < len(content):
        if content[i:].startswith("\\cite{") or (
            i + 1 < len(content) and content[i:].startswith("\\citep{")
        ):
            # Find where the cite command starts
            if content[i:].startswith("\\citep{"):
                i += 7  # Skip "\citep{"
            else:
                i += 6  # Skip "\cite{"

            # Find the closing brace
            brace_count = 1
            start = i
            while i < len(content) and brace_count > 0:
                if content[i] == "{":
                    brace_count += 1
                elif content[i] == "}":
                    brace_count -= 1
                i += 1

            # Extract the citation keys
            if brace_count == 0:
                cite_content = content[start : i - 1]
                keys = [k.strip() for k in cite_content.split(",")]
                citations.update(keys)
        else:
            i += 1

    print(f"Found {len(citations)} unique citations: {sorted(citations)}")

    # Find bibliography section
    begin_str = "\\begin{thebibliography}{"
    end_str = "\\end{thebibliography}"

    begin_pos = content.find(begin_str)
    if begin_pos == -1:
        print("No bibliography section found!")
        return

    # Find the closing brace of \begin{thebibliography}{...}
    brace_pos = begin_pos + len(begin_str)
    brace_count = 1
    while brace_pos < len(content) and brace_count > 0:
        if content[brace_pos] == "{":
            brace_count += 1
        elif content[brace_pos] == "}":
            brace_count -= 1
        brace_pos += 1

    bib_start = content[begin_pos:brace_pos]

    # Find the end
    end_pos = content.find(end_str, brace_pos)
    if end_pos == -1:
        print("No closing \\end{thebibliography} found!")
        return

    bib_content = content[brace_pos:end_pos]
    bib_end = end_str

    # Extract bibitem entries
    entries = {}

    # Split by \bibitem to get each entry
    parts = bib_content.split("\\bibitem")

    for part in parts[1:]:  # Skip the first empty part
        # Extract the key
        # Handle optional argument in square brackets
        if part.startswith("["):
            # Find closing bracket
            bracket_end = part.find("]")
            if bracket_end == -1:
                continue
            part = part[bracket_end + 1 :].lstrip()

        # Now find the key in braces
        if not part.startswith("{"):
            continue

        brace_end = part.find("}")
        if brace_end == -1:
            continue

        key = part[1:brace_end].strip()

        # The entry is everything from \bibitem to the next \bibitem
        # Since we split by \bibitem, the entire part is this entry
        entries[key] = "\\bibitem" + part

    print(f"Found {len(entries)} bibliography entries")

    # Find cited entries
    cited_entries = []
    uncited_keys = []

    for key in sorted(entries.keys()):
        if key in citations:
            cited_entries.append(entries[key])
        else:
            uncited_keys.append(key)

    print(f"Keeping {len(cited_entries)} cited entries")
    print(f"Removing {len(uncited_keys)} uncited entries")

    # Check for missing entries
    missing = citations - set(entries.keys())
    if missing:
        print(
            f"\nWARNING: {len(missing)} citations without bibliography entries:"
        )
        for key in sorted(missing):
            print(f"  - {key}")

    # Rebuild bibliography
    new_bib_content = "\n\n".join(cited_entries)

    # Replace old bibliography with new one
    new_content = (
        content[:begin_pos]
        + bib_start
        + "\n\n"
        + new_bib_content
        + "\n\n"
        + bib_end
        + content[end_pos + len(end_str) :]
    )

    # Write output
    if output_path is None:
        output_path = tex_path.with_stem(tex_path.stem + "_cleaned")

    output_path.write_text(new_content, encoding="utf-8")
    print(f"\nCleaned bibliography written to: {output_path}")

    # Add note about missing entry
    if missing:
        print(
            "\nNote: You need to manually add the missing bibliography entry for:"
        )
        print("  raistrickInfinigenIndoorsPhotorealistic2024")
        print("\nSuggested entry:")
        print(
            "\\bibitem{raistrickInfinigenIndoorsPhotorealistic2024} \\href{https://doi.org/10.48550/arXiv.2406.11824}{Alexander Raistrick, Lingjie Mei, Karhan Kayan, David Yan, Yiming Zuo, Beining Han, Hongyu Wen, Meenal Parakh, Stamatis Alexandropoulos, Lahav Lipson, Zeyu Ma, Jia Deng (2024)} Infinigen Indoors: Photorealistic Indoor Scenes Using Procedural Generation {\\em arXiv:2406.11824}."
        )


def main():
    parser = argparse.ArgumentParser(
        description="Clean bibliography to only include cited entries"
    )
    parser.add_argument("input", type=Path, help="Input LaTeX file")
    parser.add_argument("-o", "--output", type=Path, help="Output file")

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: File not found: {args.input}")
        return 1

    clean_bibliography(args.input, args.output)
    return 0


if __name__ == "__main__":
    exit(main())
