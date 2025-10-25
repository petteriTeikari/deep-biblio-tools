#!/usr/bin/env python3
"""
Comprehensive LaTeX document fixer for arXiv submission errors.
Combines multiple fixes:
- Unescaped ampersands
- Missing citations
- Undefined references
- Bibliography width parameter
"""

import argparse
import logging

# import re  # Banned - using string methods instead
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


class ArxivSubmissionFixer:
    """Fix common arXiv submission errors in LaTeX documents."""

    def __init__(self, tex_file: Path, bib_file: Path = None):
        self.tex_file = tex_file
        self.bib_file = bib_file
        self.content = tex_file.read_text(encoding="utf-8")
        self.bib_content = (
            bib_file.read_text(encoding="utf-8") if bib_file else ""
        )

        # Track all fixes made
        self.fixes_made = {
            "ampersands": 0,
            "citations": 0,
            "width_parameter": False,
            "references": 0,
        }

    def fix_all(self) -> str:
        """Apply all fixes to the document."""
        content = self.content

        # 1. Fix bibliography width parameter
        content = self._fix_bibliography_width(content)

        # 2. Fix unescaped ampersands
        content = self._fix_ampersands(content)

        # 3. Fix citation keys
        content = self._fix_citation_keys(content)

        # 4. Report on missing references
        self._check_undefined_references(content)

        return content

    def _fix_bibliography_width(self, content: str) -> str:
        """Fix the width parameter in \begin{thebibliography}."""
        # Count bibliography entries
        # Find \begin{thebibliography}{...}
        bib_start = content.find("\\begin{thebibliography}{")
        if bib_start == -1:
            return content

        # Find the width parameter
        width_start = bib_start + len("\\begin{thebibliography}{")
        width_end = content.find("}", width_start)
        if width_end == -1:
            return content

        current_width = content[width_start:width_end]

        # Count actual entries
        entry_count = content.count("\\bibitem")

        # Determine correct width
        if entry_count <= 9:
            correct_width = "9"
        elif entry_count <= 99:
            correct_width = "99"
        elif entry_count <= 999:
            correct_width = "999"
        else:
            correct_width = "9999"

        if current_width != correct_width:
            logger.info(
                f"Fixing bibliography width: {current_width} -> {correct_width} (for {entry_count} entries)"
            )
            # Replace the width parameter
            content = (
                content[:width_start] + correct_width + content[width_end:]
            )
            self.fixes_made["width_parameter"] = True

        return content

    def _fix_ampersands(self, content: str) -> str:
        """Fix unescaped ampersands in the document."""
        # Import the ampersand fixer logic
        from fix_latex_ampersands import AmpersandFixer

        fixer = AmpersandFixer()
        lines = content.splitlines(keepends=True)
        fixed_lines = []
        current_pos = 0
        total_fixes = 0

        for i, line in enumerate(lines):
            fixed_line, changes = fixer.fix_ampersands_in_line(
                line, content, current_pos
            )
            if changes > 0:
                logger.info(f"Line {i + 1}: Fixed {changes} ampersand(s)")
                total_fixes += changes
            fixed_lines.append(fixed_line)
            current_pos += len(line)

        self.fixes_made["ampersands"] = total_fixes
        return "".join(fixed_lines)

    def _fix_citation_keys(self, content: str) -> str:
        """Fix known citation key mismatches."""
        # Known fixes from analysis
        citation_fixes = {
            "gutierrez-barraganIToF2dToFRobustFlexible2021": "gutierrez-barraganIToF2dToFRobustFlexible2021a",
            "hernandezSingleShotMetricDepth2024": "lasheras-hernandezSingleShotMetricDepth2024",
        }

        fixes_applied = 0

        for old_key, new_key in citation_fixes.items():
            # Match various citation commands
            patterns = [
                f"\\\\cite\\{{{old_key}\\}}",
                f"\\\\citep\\{{{old_key}\\}}",
                f"\\\\citet\\{{{old_key}\\}}",
                f"\\\\citeauthor\\{{{old_key}\\}}",
                f"\\\\citeyear\\{{{old_key}\\}}",
                f"\\\\citealp\\{{{old_key}\\}}",
                f"\\\\citealt\\{{{old_key}\\}}",
            ]

            for pattern in patterns:
                # Simple string replacement for each pattern
                old_pattern = pattern.replace("{{", "{").replace("}}", "}")
                if old_pattern in content:
                    new_pattern = old_pattern.replace(old_key, new_key)
                    # Count occurrences before replacement
                    count = content.count(old_pattern)
                    content = content.replace(old_pattern, new_pattern)
                    fixes_applied += count
                    logger.info(f"Fixed citation: {old_key} -> {new_key}")

        self.fixes_made["citations"] = fixes_applied
        return content

    def _check_undefined_references(self, content: str) -> None:
        """Check for undefined references and report them."""
        # Find all \ref{} commands
        used_refs = set()
        i = 0
        while i < len(content):
            if content[i : i + 5] == "\\ref{":
                j = i + 5
                brace_count = 1
                while j < len(content) and brace_count > 0:
                    if content[j] == "{":
                        brace_count += 1
                    elif content[j] == "}":
                        brace_count -= 1
                    j += 1
                if brace_count == 0:
                    used_refs.add(content[i + 5 : j - 1])
                    i = j
                    continue
            i += 1

        # Find all \label{} commands
        defined_labels = set()
        i = 0
        while i < len(content):
            if content[i : i + 7] == "\\label{":
                j = i + 7
                brace_count = 1
                while j < len(content) and brace_count > 0:
                    if content[j] == "{":
                        brace_count += 1
                    elif content[j] == "}":
                        brace_count -= 1
                    j += 1
                if brace_count == 0:
                    defined_labels.add(content[i + 7 : j - 1])
                    i = j
                    continue
            i += 1

        # Find undefined
        undefined = used_refs - defined_labels

        if undefined:
            logger.warning(f"\nFound {len(undefined)} undefined references:")
            for ref in sorted(undefined):
                logger.warning(f"  - {ref}")
                # Try to guess the type
                if ref.startswith("fig:"):
                    logger.warning(
                        "    Type: Figure - add \\label{} to the figure"
                    )
                elif ref.startswith("tab:"):
                    logger.warning(
                        "    Type: Table - add \\label{} to the table"
                    )
                elif ref.startswith("sec:"):
                    logger.warning(
                        "    Type: Section - add \\label{} to the section"
                    )
                elif ref.startswith("eq:"):
                    logger.warning(
                        "    Type: Equation - add \\label{} to the equation"
                    )

        self.fixes_made["references"] = len(undefined)

    def find_missing_citations(self) -> list[str]:
        """Find citations that are used but not defined."""
        # Extract all citations used
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
            while i < len(self.content):
                pos = self.content.find(cmd, i)
                if pos == -1:
                    break
                # Find closing brace
                j = pos + len(cmd)
                brace_count = 1
                while j < len(self.content) and brace_count > 0:
                    if self.content[j] == "{":
                        brace_count += 1
                    elif self.content[j] == "}":
                        brace_count -= 1
                    j += 1
                if brace_count == 0:
                    # Extract citations
                    cite_str = self.content[pos + len(cmd) : j - 1]
                    # Handle multiple citations in one command
                    for cite in cite_str.split(","):
                        used_citations.add(cite.strip())
                i = j if brace_count == 0 else pos + 1

        # Find defined citations
        defined_citations = set()

        # In .bib file
        if self.bib_content:
            # Find @type{key, patterns
            i = 0
            while i < len(self.bib_content):
                if self.bib_content[i] == "@":
                    # Find entry type
                    j = i + 1
                    while (
                        j < len(self.bib_content)
                        and self.bib_content[j].isalnum()
                    ):
                        j += 1
                    if j < len(self.bib_content) and self.bib_content[j] == "{":
                        # Find key
                        k = j + 1
                        while (
                            k < len(self.bib_content)
                            and self.bib_content[k] not in r",\s"
                        ):
                            k += 1
                        key = self.bib_content[j + 1 : k].strip()
                        if key:
                            defined_citations.add(key)
                        i = k
                        continue
                i += 1

        # In hardcoded bibliography
        # Find \bibitem{key} or \bibitem[...]{key}
        i = 0
        while i < len(self.content):
            if self.content[i : i + 8] == "\\bibitem":
                j = i + 8
                # Skip optional argument
                if j < len(self.content) and self.content[j] == "[":
                    bracket_count = 1
                    j += 1
                    while j < len(self.content) and bracket_count > 0:
                        if self.content[j] == "[":
                            bracket_count += 1
                        elif self.content[j] == "]":
                            bracket_count -= 1
                        j += 1
                # Now find {key}
                if j < len(self.content) and self.content[j] == "{":
                    k = j + 1
                    brace_count = 1
                    while k < len(self.content) and brace_count > 0:
                        if self.content[k] == "{":
                            brace_count += 1
                        elif self.content[k] == "}":
                            brace_count -= 1
                        k += 1
                    if brace_count == 0:
                        key = self.content[j + 1 : k - 1]
                        if key:
                            defined_citations.add(key)
                        i = k
                        continue
            i += 1

        # Find missing
        missing = used_citations - defined_citations
        return sorted(list(missing))

    def generate_report(self) -> str:
        """Generate a comprehensive fix report."""
        report = ["# LaTeX Document Fix Report\n"]

        # Summary of fixes
        report.append("## Fixes Applied\n")
        report.append(f"- Ampersands fixed: {self.fixes_made['ampersands']}")
        report.append(f"- Citations fixed: {self.fixes_made['citations']}")
        report.append(
            f"- Bibliography width fixed: {'Yes' if self.fixes_made['width_parameter'] else 'No'}"
        )
        report.append(
            f"- Undefined references found: {self.fixes_made['references']}"
        )
        report.append("")

        # Missing citations
        missing_cites = self.find_missing_citations()
        if missing_cites:
            report.append(
                f"## Still Missing Citations ({len(missing_cites)})\n"
            )
            for cite in missing_cites:
                report.append(f"- {cite}")
            report.append(
                "\nThese citations need to be added to the bibliography or removed from the text."
            )
            report.append("")

        # Next steps
        if missing_cites or self.fixes_made["references"] > 0:
            report.append("## Next Steps\n")
            if missing_cites:
                report.append(
                    "1. Add missing citations to bibliography or remove from text"
                )
            if self.fixes_made["references"] > 0:
                report.append(
                    "2. Add \\label{} commands to referenced figures/tables/sections"
                )

        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(
        description="Fix common arXiv submission errors in LaTeX documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool fixes common LaTeX errors that prevent arXiv submission:
- Unescaped & characters outside of alignment environments
- Incorrect bibliography width parameter
- Known citation key mismatches
- Reports undefined references

Example usage:
  %(prog)s main.tex --bib references.bib -o main_fixed.tex
  %(prog)s main.tex --in-place --backup
        """,
    )

    parser.add_argument("input", type=Path, help="Input LaTeX file")
    parser.add_argument("--bib", type=Path, help="Bibliography .bib file")
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
    parser.add_argument("--report", type=Path, help="Save fix report to file")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check for issues, don't fix",
    )

    args = parser.parse_args()

    # Validate
    if not args.input.exists():
        logger.error(f"Input file not found: {args.input}")
        return 1

    if args.in_place and args.output:
        logger.error("Cannot use both --in-place and --output")
        return 1

    # Create fixer
    fixer = ArxivSubmissionFixer(args.input, args.bib)

    if args.check_only:
        # Just generate report
        report = fixer.generate_report()
        print(report)

        if args.report:
            args.report.write_text(report, encoding="utf-8")
            logger.info(f"\nReport saved to: {args.report}")
    else:
        # Apply fixes
        logger.info(f"Fixing {args.input}...\n")
        fixed_content = fixer.fix_all()

        # Generate report
        report = fixer.generate_report()

        # Handle output
        if args.in_place:
            if args.backup:
                backup_path = args.input.with_suffix(args.input.suffix + ".bak")
                if backup_path.exists():
                    # Find unique backup name
                    i = 1
                    while True:
                        backup_path = args.input.with_suffix(
                            f"{args.input.suffix}.bak{i}"
                        )
                        if not backup_path.exists():
                            break
                        i += 1
                args.input.rename(backup_path)
                logger.info(f"Created backup: {backup_path}")

            args.input.write_text(fixed_content, encoding="utf-8")
            logger.info(f"\nFixed file saved to: {args.input}")
        elif args.output:
            args.output.write_text(fixed_content, encoding="utf-8")
            logger.info(f"\nFixed file saved to: {args.output}")
        else:
            print(fixed_content)

        # Save report if requested
        if args.report:
            args.report.write_text(report, encoding="utf-8")
            logger.info(f"Report saved to: {args.report}")
        else:
            print("\n" + "=" * 60 + "\n")
            print(report)

    return 0


if __name__ == "__main__":
    exit(main())
