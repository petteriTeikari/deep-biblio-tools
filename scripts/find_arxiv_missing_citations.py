#!/usr/bin/env python3
"""
Find \bibitem keys from main.tex that are missing in references.bib.
"""

import argparse
import logging

# import re  # Banned - using string methods instead
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def extract_bibitem_keys(tex_file: Path) -> list[str]:
    """Extract all \bibitem keys from a tex file."""
    keys = []
    content = tex_file.read_text(encoding="utf-8")

    # Match \bibitem[...]{key} or \bibitem{key}
    i = 0
    while i < len(content):
        if content[i : i + 8] == "\\bibitem":
            j = i + 8

            # Skip optional [...] part
            if j < len(content) and content[j] == "[":
                bracket_count = 1
                j += 1
                while j < len(content) and bracket_count > 0:
                    if content[j] == "[":
                        bracket_count += 1
                    elif content[j] == "]":
                        bracket_count -= 1
                    j += 1

            # Now look for {key}
            if j < len(content) and content[j] == "{":
                brace_start = j + 1
                brace_count = 1
                j += 1
                while j < len(content) and brace_count > 0:
                    if content[j] == "{":
                        brace_count += 1
                    elif content[j] == "}":
                        brace_count -= 1
                    j += 1

                if brace_count == 0:
                    key = content[brace_start : j - 1]
                    if key:
                        keys.append(key)

                i = j
                continue

        i += 1

    return keys


def extract_bib_keys(bib_file: Path) -> list[str]:
    """Extract all entry keys from a bib file."""
    keys = []
    content = bib_file.read_text(encoding="utf-8")

    # Match @type{key, where type can be article, misc, online, book, etc.
    i = 0
    while i < len(content):
        if content[i] == "@":
            # Skip entry type
            j = i + 1
            while j < len(content) and (
                content[j].isalnum() or content[j] == "_"
            ):
                j += 1

            # Look for opening brace
            if j < len(content) and content[j] == "{":
                # Extract key (everything until comma)
                key_start = j + 1
                k = key_start
                while k < len(content) and content[k] != ",":
                    k += 1

                if k > key_start:
                    key = content[key_start:k].strip()
                    if key:
                        keys.append(key)

                i = k
                continue

        i += 1

    return keys


def main():
    parser = argparse.ArgumentParser(
        description="Find \\bibitem keys from main.tex that are missing in references.bib"
    )
    parser.add_argument(
        "tex_file", type=Path, help="Main .tex file with \\bibitem entries"
    )
    parser.add_argument("bib_file", type=Path, help="Bibliography .bib file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("arxiv_missing_citations_report.md"),
        help="Output report file",
    )

    args = parser.parse_args()

    if not args.tex_file.exists():
        logger.error(f"TeX file not found: {args.tex_file}")
        return

    if not args.bib_file.exists():
        logger.error(f"Bibliography file not found: {args.bib_file}")
        return

    logger.info(f"Extracting \\bibitem keys from {args.tex_file}...")
    bibitem_keys = extract_bibitem_keys(args.tex_file)
    logger.info(f"Found {len(bibitem_keys)} \\bibitem entries")

    logger.info(f"\nExtracting keys from {args.bib_file}...")
    bib_keys = extract_bib_keys(args.bib_file)
    logger.info(f"Found {len(bib_keys)} bibliography entries")

    # Find missing keys
    bibitem_set = set(bibitem_keys)
    bib_set = set(bib_keys)
    missing_keys = sorted(bibitem_set - bib_set)

    logger.info(
        f"\nMissing citations: {len(missing_keys)} keys found in main.tex but not in references.bib"
    )

    # Check for duplicates in bibitem
    duplicates = []
    seen = set()
    for key in bibitem_keys:
        if key in seen:
            duplicates.append(key)
        seen.add(key)

    # Write report
    with open(args.output, "w", encoding="utf-8") as f:
        f.write("# ArXiv Missing Citations Report\n\n")
        f.write(
            f"- Total \\\\bibitem entries in {args.tex_file.name}: {len(bibitem_keys)}\n"
        )
        f.write(f"- Total entries in {args.bib_file.name}: {len(bib_keys)}\n")
        f.write(f"- Missing entries: {len(missing_keys)}\n\n")

        if missing_keys:
            f.write("## Missing Keys\n\n")
            f.write(
                "The following keys are cited in main.tex but not found in references.bib:\n\n"
            )
            for key in missing_keys:
                f.write(f"- `{key}`\n")
        else:
            f.write("All citations are properly defined in references.bib!\n")

        if duplicates:
            f.write("\n## Duplicate \\\\bibitem Keys\n\n")
            f.write("The following keys appear multiple times in main.tex:\n\n")
            for key in sorted(set(duplicates)):
                count = bibitem_keys.count(key)
                f.write(f"- `{key}` (appears {count} times)\n")

    if missing_keys:
        logger.info("\nMissing keys:")
        for i, key in enumerate(missing_keys[:20]):  # Show first 20
            logger.info(f"  {i + 1}. {key}")

        if len(missing_keys) > 20:
            logger.info(f"  ... and {len(missing_keys) - 20} more")
    else:
        logger.info("\nAll \\bibitem keys are present in references.bib!")

    logger.info(f"\nFull report written to: {args.output}")


if __name__ == "__main__":
    main()
