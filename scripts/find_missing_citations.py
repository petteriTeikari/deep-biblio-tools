#!/usr/bin/env python3
"""
Find missing citations in references.bib based on arXiv error report.
"""

import argparse
import logging

# import re  # Banned - using string methods instead
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# The missing citations from arXiv error report
MISSING_CITATIONS = [
    "sebastian2020",
    "vong2021",
    "batoolImpedanceGPTVLMdrivenImpedance2025a",
    # Add more as we find them
]


def extract_citations_from_tex(tex_file: Path) -> set[str]:
    """Extract all citation keys used in the tex file."""
    content = tex_file.read_text(encoding="utf-8")

    # Find all \cite commands and their variants
    cite_commands = [
        "\\cite{",
        "\\citep{",
        "\\citet{",
        "\\citeauthor{",
        "\\citeyear{",
        "\\citealp{",
        "\\citealt{",
    ]

    citations = set()
    for cmd in cite_commands:
        pos = 0
        while True:
            # Find the next citation command
            pos = content.find(cmd, pos)
            if pos == -1:
                break

            # Find the closing brace
            start = pos + len(cmd)
            end = content.find("}", start)
            if end == -1:
                pos += 1
                continue

            # Extract citation keys
            cite_content = content[start:end]
            # Handle multiple citations in one command
            for cite in cite_content.split(","):
                citations.add(cite.strip())

            pos = end + 1

    return citations


def find_citations_in_bib(
    bib_file: Path, citations: set[str]
) -> tuple[dict, set[str]]:
    """Find which citations exist in the bib file."""
    content = bib_file.read_text(encoding="utf-8")
    content_lower = content.lower()

    found = {}
    not_found = set()

    for cite in citations:
        # Look for @article{cite, @inproceedings{cite, etc.
        # Try to find the citation key after an @ and {
        search_patterns = [
            f"@article{{{cite},",
            f"@inproceedings{{{cite},",
            f"@book{{{cite},",
            f"@misc{{{cite},",
            f"@phdthesis{{{cite},",
            f"@mastersthesis{{{cite},",
            f"@techreport{{{cite},",
            f"@inbook{{{cite},",
            f"@incollection{{{cite},",
            f"@conference{{{cite},",
            f"@online{{{cite},",
            f"@report{{{cite},",
            f"@software{{{cite},",
            # Also check with whitespace
            f"@article{{{cite} ,",
            f"@inproceedings{{{cite} ,",
            f"@book{{{cite} ,",
            f"@misc{{{cite} ,",
            f"@phdthesis{{{cite} ,",
            f"@mastersthesis{{{cite} ,",
            f"@techreport{{{cite} ,",
            f"@inbook{{{cite} ,",
            f"@incollection{{{cite} ,",
            f"@conference{{{cite} ,",
            f"@online{{{cite} ,",
            f"@report{{{cite} ,",
            f"@software{{{cite} ,",
        ]

        entry_found = False
        for pattern in search_patterns:
            pos = content_lower.find(pattern.lower())
            if pos != -1:
                # Extract the entry
                start = pos
                # Find the end of this entry (next @ or end of file)
                next_at = content.find("@", start + 1)
                if next_at == -1:
                    next_at = len(content)

                # Count braces to find the actual end
                brace_count = 0
                i = start
                while i < next_at and i < len(content):
                    if content[i] == "{":
                        brace_count += 1
                    elif content[i] == "}":
                        brace_count -= 1
                        if brace_count == 0:
                            found[cite] = content[start : i + 1]
                            entry_found = True
                            break
                    i += 1
                if entry_found:
                    break

        if not entry_found:
            not_found.add(cite)

    return found, not_found


def check_hardcoded_bibliography(
    tex_file: Path, citations: set[str]
) -> tuple[dict, set[str]]:
    """Check if citations exist in hardcoded bibliography."""
    content = tex_file.read_text(encoding="utf-8")

    # Find bibliography section
    bib_start = content.find("\\begin{thebibliography}")
    if bib_start == -1:
        return {}, citations

    bib_end = content.find("\\end{thebibliography}", bib_start)
    if bib_end == -1:
        return {}, citations

    bib_content = content[bib_start:bib_end]

    found = {}
    not_found = set()

    for cite in citations:
        # Look for \bibitem{cite} or \bibitem[...]{cite}
        search_strings = [
            f"\\bibitem{{{cite}}}",
            "\\bibitem[",  # Need to check if followed by ]{cite}
        ]

        cite_found = False

        # Check simple case first
        if search_strings[0] in bib_content:
            found[cite] = "Found in hardcoded bibliography"
            cite_found = True
        else:
            # Check for \bibitem[...]{cite} pattern
            pos = 0
            while True:
                pos = bib_content.find(search_strings[1], pos)
                if pos == -1:
                    break

                # Find the closing bracket
                bracket_end = bib_content.find("]", pos)
                if bracket_end == -1:
                    pos += 1
                    continue

                # Check if {cite} follows
                after_bracket = bib_content[
                    bracket_end + 1 : bracket_end + len(cite) + 3
                ]
                if after_bracket == f"{{{cite}}}":
                    found[cite] = "Found in hardcoded bibliography"
                    cite_found = True
                    break

                pos += 1

        if not cite_found:
            not_found.add(cite)

    return found, not_found


def main():
    parser = argparse.ArgumentParser(
        description="Find missing citations in bibliography"
    )
    parser.add_argument("tex_file", type=Path, help="Main LaTeX file")
    parser.add_argument("bib_file", type=Path, help="Bibliography .bib file")
    parser.add_argument(
        "--check-hardcoded",
        action="store_true",
        help="Also check hardcoded bibliography in tex file",
    )
    parser.add_argument(
        "--output", type=Path, help="Output missing entries to file"
    )

    args = parser.parse_args()

    # Extract all citations from tex file
    logger.info(f"Extracting citations from {args.tex_file}...")
    all_citations = extract_citations_from_tex(args.tex_file)
    logger.info(f"Found {len(all_citations)} unique citations in tex file")

    # Find which ones exist in bib file
    logger.info(f"\nChecking citations in {args.bib_file}...")
    found_in_bib, not_in_bib = find_citations_in_bib(
        args.bib_file, all_citations
    )

    logger.info(f"\nFound in .bib file: {len(found_in_bib)}")
    logger.info(f"NOT found in .bib file: {len(not_in_bib)}")

    if not_in_bib:
        logger.info("\nMissing citations:")
        for cite in sorted(not_in_bib):
            logger.info(f"  - {cite}")

    # Check hardcoded bibliography if requested
    if args.check_hardcoded and not_in_bib:
        logger.info(f"\nChecking hardcoded bibliography in {args.tex_file}...")
        found_hardcoded, still_missing = check_hardcoded_bibliography(
            args.tex_file, not_in_bib
        )

        if found_hardcoded:
            logger.info(
                f"\nFound in hardcoded bibliography: {len(found_hardcoded)}"
            )
            for cite in sorted(found_hardcoded):
                logger.info(f"  - {cite}")

        if still_missing:
            logger.info(
                f"\nSTILL MISSING (not in .bib or hardcoded): {len(still_missing)}"
            )
            for cite in sorted(still_missing):
                logger.info(f"  - {cite}")

    # Output to file if requested
    if args.output and not_in_bib:
        with open(args.output, "w") as f:
            f.write("Missing citations:\n")
            for cite in sorted(not_in_bib):
                f.write(f"{cite}\n")
        logger.info(f"\nWrote missing citations to {args.output}")


if __name__ == "__main__":
    main()
