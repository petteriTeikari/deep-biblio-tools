#!/usr/bin/env python3
"""
Fix citation keys in LaTeX document based on arXiv error analysis.
"""

import argparse
import logging

# import re  # Banned - using string methods instead
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# Citation key mappings based on analysis
CITATION_FIXES = {
    "gutierrez-barraganIToF2dToFRobustFlexible2021": "gutierrez-barraganIToF2dToFRobustFlexible2021a",
    "hernandezSingleShotMetricDepth2024": "lasheras-hernandezSingleShotMetricDepth2024",
    # ni2024 doesn't need fixing - it's not in references.bib
}


def fix_citations_in_file(
    tex_file: Path,
    output_file: Path | None = None,
    in_place: bool = False,
    backup: bool = True,
):
    """Fix citation keys in a LaTeX file."""

    content = tex_file.read_text(encoding="utf-8")

    changes_made = 0

    # Fix each citation
    for old_key, new_key in CITATION_FIXES.items():
        # Match various citation commands
        patterns = [
            f"\\cite{{{old_key}}}",
            f"\\citep{{{old_key}}}",
            f"\\citet{{{old_key}}}",
            f"\\citeauthor{{{old_key}}}",
            f"\\citeyear{{{old_key}}}",
            f"\\citealp{{{old_key}}}",
            f"\\citealt{{{old_key}}}",
        ]

        for pattern in patterns:
            count = content.count(pattern)
            if count > 0:
                new_pattern = pattern.replace(old_key, new_key)
                content = content.replace(pattern, new_pattern)
                changes_made += count
                logger.info(f"Fixed: {old_key} -> {new_key}")

    # Special case: Check if ni2024 is actually missing from the bibliography
    ni2024_patterns = [
        "\\cite{ni2024}",
        "\\citep{ni2024}",
        "\\citet{ni2024}",
    ]

    ni2024_found = False
    for pattern in ni2024_patterns:
        if pattern in content:
            ni2024_found = True
            logger.warning(
                "Citation 'ni2024' found in document but not in references.bib"
            )
            logger.warning(
                "This citation needs to be added to the bibliography or removed from the text"
            )

    if changes_made == 0 and not ni2024_found:
        logger.info("No citation fixes needed")
        return

    # Handle output
    if in_place:
        if backup:
            backup_path = tex_file.with_suffix(tex_file.suffix + ".bak")
            tex_file.rename(backup_path)
            logger.info(f"Created backup: {backup_path}")

        tex_file.write_text(content, encoding="utf-8")
        logger.info(
            f"Updated {tex_file} in-place ({changes_made} citations fixed)"
        )
    elif output_file:
        output_file.write_text(content, encoding="utf-8")
        logger.info(
            f"Wrote fixed content to {output_file} ({changes_made} citations fixed)"
        )
    else:
        print(content)

    return changes_made


def find_ni2024_context(tex_file: Path):
    """Find context around ni2024 citations to help locate the missing reference."""
    content = tex_file.read_text(encoding="utf-8")

    # Find all ni2024 citations with context
    search_strings = [
        "\\cite{ni2024}",
        "\\citep{ni2024}",
        "\\citet{ni2024}",
        "\\cite{",  # Check for ni2024 in multi-citation
    ]

    contexts = []
    for search in search_strings[:3]:  # First three are direct matches
        pos = 0
        while True:
            pos = content.find(search, pos)
            if pos == -1:
                break

            start = max(0, pos - 200)
            end = min(len(content), pos + len(search) + 200)
            context = content[start:end]
            contexts.append(context)
            pos += 1

    # Check for ni2024 in multi-citation commands
    pos = 0
    while True:
        pos = content.find("\\cite{", pos)
        if pos == -1:
            break

        # Find closing brace
        end_brace = content.find("}", pos)
        if end_brace != -1:
            cite_content = content[pos : end_brace + 1]
            if "ni2024" in cite_content:
                start = max(0, pos - 200)
                end = min(len(content), end_brace + 200)
                context = content[start:end]
                contexts.append(context)

        pos += 1

    if contexts:
        logger.info("\nContext around ni2024 citations:")
        for i, context in enumerate(contexts, 1):
            logger.info(f"\nContext {i}:")
            # Clean up the context for display
            context = context.replace("\n", " ").strip()
            logger.info(f"...{context}...")

    return contexts


def main():
    parser = argparse.ArgumentParser(
        description="Fix citation keys in LaTeX document"
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
        "--find-ni2024",
        action="store_true",
        help="Find context around ni2024 citations",
    )

    args = parser.parse_args()

    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        return

    if args.in_place and args.output:
        logger.error("Cannot use both --in-place and --output")
        return

    # Fix citations
    fix_citations_in_file(args.input, args.output, args.in_place, args.backup)

    # Find ni2024 context if requested
    if args.find_ni2024:
        find_ni2024_context(args.input)


if __name__ == "__main__":
    main()
