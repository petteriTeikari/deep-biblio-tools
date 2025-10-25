#!/usr/bin/env python3
"""
Analyze and fix arXiv submission errors for LaTeX documents.
Handles missing citations, misplaced & characters, and undefined references.
"""

import argparse
import logging

# import re  # Banned - using string methods instead
from dataclasses import dataclass
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


@dataclass
class ArxivError:
    """Represents an error from arXiv compilation."""

    error_type: str
    line_number: int | None
    details: str
    context: str = ""


class ArxivErrorAnalyzer:
    """Analyze and suggest fixes for arXiv LaTeX compilation errors."""

    def __init__(self, tex_file: Path, bib_file: Path | None = None):
        self.tex_file = tex_file
        self.bib_file = bib_file
        self.tex_content = tex_file.read_text(encoding="utf-8")
        self.bib_content = (
            bib_file.read_text(encoding="utf-8") if bib_file else ""
        )

        # Extract bibliography section if present
        start_tag = "\\begin{thebibliography}"
        end_tag = "\\end{thebibliography}"

        start_idx = self.tex_content.find(start_tag)
        if start_idx != -1:
            end_idx = self.tex_content.find(end_tag, start_idx)
            if end_idx != -1:
                self.hardcoded_bib = self.tex_content[
                    start_idx : end_idx + len(end_tag)
                ]
            else:
                self.hardcoded_bib = ""
        else:
            self.hardcoded_bib = ""

    def find_undefined_citations(self) -> list[str]:
        """Find all undefined citations in the document."""
        # Extract all citations used in the document
        cite_commands = [
            "\\cite{",
            "\\citep{",
            "\\citet{",
            "\\citeauthor{",
            "\\citeyear{",
            "\\citealp{",
            "\\citealt{",
        ]

        used_citations = set()
        for cmd in cite_commands:
            i = 0
            while i < len(self.tex_content):
                idx = self.tex_content.find(cmd, i)
                if idx == -1:
                    break

                # Find closing brace
                start = idx + len(cmd)
                brace_count = 1
                j = start
                while j < len(self.tex_content) and brace_count > 0:
                    if self.tex_content[j] == "{":
                        brace_count += 1
                    elif self.tex_content[j] == "}":
                        brace_count -= 1
                    j += 1

                if brace_count == 0:
                    citation_text = self.tex_content[start : j - 1]
                    # Handle multiple citations in one command
                    for cite in citation_text.split(","):
                        used_citations.add(cite.strip())

                i = idx + 1

        # Find defined citations in bibliography
        defined_citations = set()

        # Check .bib file
        if self.bib_content:
            i = 0
            while i < len(self.bib_content):
                if self.bib_content[i] == "@":
                    # Skip entry type
                    j = i + 1
                    while j < len(self.bib_content) and (
                        self.bib_content[j].isalnum()
                        or self.bib_content[j] == "_"
                    ):
                        j += 1

                    # Look for opening brace
                    if j < len(self.bib_content) and self.bib_content[j] == "{":
                        # Extract key
                        key_start = j + 1
                        k = key_start
                        while (
                            k < len(self.bib_content)
                            and self.bib_content[k] not in ",\\s\n\t"
                        ):
                            k += 1

                        if k > key_start:
                            key = self.bib_content[key_start:k].strip()
                            if key:
                                defined_citations.add(key)

                        i = k
                        continue

                i += 1

        # Check hardcoded bibliography
        if self.hardcoded_bib:
            i = 0
            while i < len(self.hardcoded_bib):
                if self.hardcoded_bib[i : i + 8] == "\\bibitem":
                    j = i + 8

                    # Skip optional [...] part
                    if (
                        j < len(self.hardcoded_bib)
                        and self.hardcoded_bib[j] == "["
                    ):
                        bracket_count = 1
                        j += 1
                        while j < len(self.hardcoded_bib) and bracket_count > 0:
                            if self.hardcoded_bib[j] == "[":
                                bracket_count += 1
                            elif self.hardcoded_bib[j] == "]":
                                bracket_count -= 1
                            j += 1

                    # Now look for {key}
                    if (
                        j < len(self.hardcoded_bib)
                        and self.hardcoded_bib[j] == "{"
                    ):
                        brace_start = j + 1
                        brace_count = 1
                        j += 1
                        while j < len(self.hardcoded_bib) and brace_count > 0:
                            if self.hardcoded_bib[j] == "{":
                                brace_count += 1
                            elif self.hardcoded_bib[j] == "}":
                                brace_count -= 1
                            j += 1

                        if brace_count == 0:
                            key = self.hardcoded_bib[brace_start : j - 1]
                            if key:
                                defined_citations.add(key)

                        i = j
                        continue

                i += 1

        # Find undefined citations
        undefined = used_citations - defined_citations
        return sorted(list(undefined))

    def find_misplaced_ampersands(self) -> list[tuple[int, str]]:
        """Find lines with misplaced & characters in bibliography."""
        issues = []

        if not self.hardcoded_bib:
            return issues

        lines = self.hardcoded_bib.split("\n")
        for i, line in enumerate(lines):
            # Skip URLs and LaTeX commands that use &
            if any(
                skip in line
                for skip in [
                    "http",
                    "\\href",
                    "\\url",
                    "tabular",
                    "array",
                    "align",
                ]
            ):
                continue

            # Find unescaped & (not preceded by \)
            unescaped = []
            j = 0
            while j < len(line):
                if j > 0 and line[j] == "&" and line[j - 1] != "\\":
                    # Check it's not part of &&
                    if j + 1 < len(line) and line[j + 1] != "&":
                        unescaped.append(j)
                elif j == 0 and line[j] == "&":
                    unescaped.append(j)
                j += 1

            if unescaped:
                issues.append((i, line.strip()))

        return issues

    def find_undefined_references(self) -> list[str]:
        """Find undefined figure, table, section references."""
        # Find all references
        used_refs = set()
        ref_cmd = "\\ref{"
        i = 0
        while i < len(self.tex_content):
            idx = self.tex_content.find(ref_cmd, i)
            if idx == -1:
                break

            # Find closing brace
            start = idx + len(ref_cmd)
            end = self.tex_content.find("}", start)
            if end != -1:
                ref_text = self.tex_content[start:end]
                if ref_text:
                    used_refs.add(ref_text)

            i = idx + 1

        # Find all labels
        defined_labels = set()
        label_cmd = "\\label{"
        i = 0
        while i < len(self.tex_content):
            idx = self.tex_content.find(label_cmd, i)
            if idx == -1:
                break

            # Find closing brace
            start = idx + len(label_cmd)
            end = self.tex_content.find("}", start)
            if end != -1:
                label_text = self.tex_content[start:end]
                if label_text:
                    defined_labels.add(label_text)

            i = idx + 1

        # Find undefined
        undefined = used_refs - defined_labels
        return sorted(list(undefined))

    def suggest_citation_fixes(
        self, missing_citations: list[str]
    ) -> dict[str, list[str]]:
        """Suggest possible fixes for missing citations."""
        suggestions = {}

        for cite in missing_citations:
            similar = []

            # Search in .bib file for similar keys
            if self.bib_content:
                all_keys = []
                # Extract all keys from bib content
                i = 0
                while i < len(self.bib_content):
                    if self.bib_content[i] == "@":
                        # Skip entry type
                        j = i + 1
                        while j < len(self.bib_content) and (
                            self.bib_content[j].isalnum()
                            or self.bib_content[j] == "_"
                        ):
                            j += 1

                        # Look for opening brace
                        if (
                            j < len(self.bib_content)
                            and self.bib_content[j] == "{"
                        ):
                            # Extract key
                            key_start = j + 1
                            k = key_start
                            while (
                                k < len(self.bib_content)
                                and self.bib_content[k] not in ",\\s\n\t"
                            ):
                                k += 1

                            if k > key_start:
                                key = self.bib_content[key_start:k].strip()
                                if key:
                                    all_keys.append(key)

                            i = k
                            continue

                    i += 1

                # Look for similar keys
                cite_lower = cite.lower()
                for key in all_keys:
                    key_lower = key.lower()

                    # Check various similarity conditions
                    if cite_lower in key_lower or key_lower in cite_lower:
                        similar.append(key)
                    elif any(
                        part in key_lower for part in cite_lower.split("_")
                    ):
                        similar.append(key)
                    elif self._similarity_score(cite_lower, key_lower) > 0.6:
                        similar.append(key)

            if similar:
                suggestions[cite] = similar[:5]  # Top 5 suggestions

        return suggestions

    def _similarity_score(self, s1: str, s2: str) -> float:
        """Simple similarity score between two strings."""

        # Extract common elements by splitting on delimiters
        def split_parts(s):
            parts = []
            current = ""
            for char in s:
                if char in "_-" or char.isdigit():
                    if current:
                        parts.append(current)
                        current = ""
                else:
                    current += char
            if current:
                parts.append(current)
            return set(parts)

        s1_parts = split_parts(s1)
        s2_parts = split_parts(s2)

        if not s1_parts or not s2_parts:
            return 0.0

        common = len(s1_parts & s2_parts)
        total = len(s1_parts | s2_parts)

        return common / total if total > 0 else 0.0

    def generate_report(self) -> str:
        """Generate a comprehensive error report."""
        report = ["# arXiv Submission Error Analysis Report\n"]

        # Undefined citations
        undefined_cites = self.find_undefined_citations()
        report.append(
            f"## Undefined Citations ({len(undefined_cites)} found)\n"
        )

        if undefined_cites:
            suggestions = self.suggest_citation_fixes(undefined_cites)

            for cite in undefined_cites:
                report.append(f"- `{cite}`")
                if cite in suggestions:
                    report.append(
                        f"  Suggestions: {', '.join(suggestions[cite][:3])}"
                    )
            report.append("")

        # Misplaced ampersands
        ampersand_issues = self.find_misplaced_ampersands()
        report.append(
            f"## Misplaced & Characters ({len(ampersand_issues)} found)\n"
        )

        if ampersand_issues:
            for line_num, line in ampersand_issues[:10]:
                report.append(f"- Line {line_num}: `{line[:80]}...`")
            if len(ampersand_issues) > 10:
                report.append(f"- ... and {len(ampersand_issues) - 10} more")
            report.append("")

        # Undefined references
        undefined_refs = self.find_undefined_references()
        report.append(
            f"## Undefined References ({len(undefined_refs)} found)\n"
        )

        if undefined_refs:
            for ref in undefined_refs:
                report.append(f"- `{ref}`")
                # Try to guess what type of reference
                if ref.startswith("fig:"):
                    report.append("  Type: Figure")
                elif ref.startswith("tab:"):
                    report.append("  Type: Table")
                elif ref.startswith("sec:"):
                    report.append("  Type: Section")
                elif ref.startswith("eq:"):
                    report.append("  Type: Equation")
            report.append("")

        # Summary and recommendations
        report.append("## Summary and Recommendations\n")

        total_errors = (
            len(undefined_cites) + len(ampersand_issues) + len(undefined_refs)
        )
        report.append(f"Total errors found: {total_errors}\n")

        if undefined_cites:
            report.append("### Missing Citations:")
            report.append(
                "1. Check if citations exist with different keys in references.bib"
            )
            report.append(
                "2. Some citations might be in the hardcoded bibliography with different keys"
            )
            report.append("3. Use the suggested similar keys if appropriate")
            report.append("")

        if ampersand_issues:
            report.append("### Ampersand Issues:")
            report.append("1. Replace `&` with `\\&` in bibliography entries")
            report.append("2. Exception: Keep `&` unchanged in URLs")
            report.append(
                "3. Run: `python scripts/fix_bibliography_ampersands.py main.tex --in-place`"
            )
            report.append("")

        if undefined_refs:
            report.append("### Undefined References:")
            report.append(
                "1. Add missing \\label{} commands to figures/tables/sections"
            )
            report.append("2. Check for typos in \\ref{} commands")
            report.append("3. Ensure labels match exactly (case-sensitive)")

        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze arXiv submission errors"
    )
    parser.add_argument("tex_file", type=Path, help="Main LaTeX file")
    parser.add_argument("--bib", type=Path, help="Bibliography .bib file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("arxiv_error_analysis.md"),
        help="Output report file",
    )
    parser.add_argument(
        "--fix-ampersands",
        action="store_true",
        help="Automatically fix ampersand issues",
    )

    args = parser.parse_args()

    if not args.tex_file.exists():
        logger.error(f"TeX file not found: {args.tex_file}")
        return

    # Analyze errors
    analyzer = ArxivErrorAnalyzer(args.tex_file, args.bib)

    # Generate report
    report = analyzer.generate_report()

    # Save report
    args.output.write_text(report, encoding="utf-8")
    logger.info(f"Analysis report saved to: {args.output}")

    # Print summary
    undefined_cites = analyzer.find_undefined_citations()
    ampersand_issues = analyzer.find_misplaced_ampersands()
    undefined_refs = analyzer.find_undefined_references()

    logger.info("\nError Summary:")
    logger.info(f"  Undefined citations: {len(undefined_cites)}")
    logger.info(f"  Misplaced & characters: {len(ampersand_issues)}")
    logger.info(f"  Undefined references: {len(undefined_refs)}")

    # Fix ampersands if requested
    if args.fix_ampersands and ampersand_issues:
        logger.info("\nFixing ampersand issues...")
        from fix_bibliography_ampersands import fix_bibliography_ampersands

        fix_bibliography_ampersands(args.tex_file, in_place=True, backup=True)


if __name__ == "__main__":
    main()
