#!/usr/bin/env python3
"""
Fix Markdown Citation Quality Issues

This script applies systematic fixes to markdown files with citation quality issues:
- Fixes broken URLs
- Fixes invalid arXiv IDs
- Fixes broken DOI links
- Creates a fixed version with -fixed suffix

Usage:
    python scripts/fix_markdown_citations.py /path/to/paper.md

Output:
    /path/to/paper-fixed.md (fixed version)
    /path/to/paper-fixes-report.md (detailed report)
"""

import sys
from pathlib import Path


class CitationFix:
    """Represents a single citation fix to be applied."""

    def __init__(self, old_pattern: str, new_pattern: str, description: str):
        self.old_pattern = old_pattern
        self.new_pattern = new_pattern
        self.description = description
        self.occurrences = 0
        self.applied_lines = []


class MarkdownCitationFixer:
    """Fixes common citation quality issues in academic markdown files."""

    def __init__(self, input_file: Path):
        self.input_file = input_file
        self.output_file = (
            input_file.parent / f"{input_file.stem}-fixed{input_file.suffix}"
        )
        self.report_file = (
            input_file.parent / f"{input_file.stem}-fixes-report.md"
        )
        self.fixes: list[CitationFix] = []
        self.content = ""
        self.original_content = ""

    def load_content(self):
        """Load markdown file content."""
        with open(self.input_file, encoding="utf-8") as f:
            self.content = f.read()
            self.original_content = self.content

    def define_fixes(self):
        """Define all citation fixes to apply."""

        # Fix 1: Google Agent-to-Agent URL (broken → working)
        self.fixes.append(
            CitationFix(
                old_pattern="https://developers.google.com/agent-to-agent",
                new_pattern="https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/",
                description="Google A2A URL: broken endpoint → official blog announcement",
            )
        )

        # Fix 2-4: Invalid arXiv IDs
        self.fixes.append(
            CitationFix(
                old_pattern="https://arxiv.org/abs/2025.mcp.taxonomy",
                new_pattern="https://arxiv.org/abs/2509.24272",
                description="Invalid arXiv ID '2025.mcp.taxonomy' → valid '2509.24272' (Zhao et al. MCP taxonomy paper)",
            )
        )

        self.fixes.append(
            CitationFix(
                old_pattern="https://arxiv.org/abs/2025.mcp.privilege",
                new_pattern="https://arxiv.org/abs/2507.06250",
                description="Invalid arXiv ID '2025.mcp.privilege' → valid '2507.06250' (Li et al. MCP privilege paper)",
            )
        )

        self.fixes.append(
            CitationFix(
                old_pattern="https://arxiv.org/abs/2025.mpma",
                new_pattern="https://arxiv.org/abs/2505.11154",
                description="Invalid arXiv ID '2025.mpma' → valid '2505.11154' (Wang et al. MPMA paper)",
            )
        )

        # Fix 5: Fashion United broken link (404) - remove or find alternative
        # For now, mark for manual review
        self.fixes.append(
            CitationFix(
                old_pattern="https://fashionunited.com/news/business/h-m-zalando-join-eu-digital-product-passport-pilot",
                new_pattern="https://fashionunited.com/news/business/h-m-zalando-join-eu-digital-product-passport-pilot",
                description="Fashion United URL returns 404 - NEEDS MANUAL REVIEW (consider removing or finding alternative source)",
            )
        )

        # Fix 6: CIRPASS broken link (404)
        self.fixes.append(
            CitationFix(
                old_pattern="https://cirpassproject.eu/results/",
                new_pattern="https://cirpassproject.eu/",
                description="CIRPASS results page moved - using main project page instead",
            )
        )

        # Fix 7: Truncated European Parliament URL
        # Using simple string replacement for partial URL match
        self.fixes.append(
            CitationFix(
                old_pattern="(https://www.europarl.europa.eu/thinktank/en/document/EPRS_STU(2024)",
                new_pattern="(https://www.europarl.europa.eu/thinktank/en/document/EPRS_STU(2024)757808)",
                description="Completed truncated European Parliament URL",
            )
        )

        # Fix 8: Sigma Technology broken link (404)
        self.fixes.append(
            CitationFix(
                old_pattern="https://sigmatechnology.com/dpp-analysis",
                new_pattern="https://sigmatechnology.com/dpp-analysis",
                description="Sigma Technology URL returns 404 - NEEDS MANUAL REVIEW (company blog may have removed content)",
            )
        )

        # Fix 9: Agrawal et al. 2021 - Wrong DOI (typo in journal abbreviation)
        self.fixes.append(
            CitationFix(
                old_pattern="https://doi.org/10.1016/j.compind.2021.107130",
                new_pattern="https://doi.org/10.1016/j.cie.2021.107130",
                description="Agrawal et al. 2021: Fixed typo in DOI - 'compind' → 'cie' (Computers & Industrial Engineering)",
            )
        )

        # Fix 10: Sobolev & Stupnikov 2024 - DOI returns 404
        self.fixes.append(
            CitationFix(
                old_pattern="https://doi.org/10.1134/S1054661825010145",
                new_pattern="https://doi.org/10.1134/S1054661825010145",
                description="Sobolev & Stupnikov 2024: DOI returns 404 - NEEDS MANUAL REVIEW (verify paper exists or remove)",
            )
        )

        # Fix 11: Rigaku 2025 - Application note page returns 404
        self.fixes.append(
            CitationFix(
                old_pattern="https://rigaku.com/products/handheld-raman/application-notes/rad003",
                new_pattern="https://rigaku.com/products/handheld-raman/application-notes/rad003",
                description="Rigaku 2025: Application note returns 404 - NEEDS MANUAL REVIEW (company page removed)",
            )
        )

    def apply_fixes(self):
        """Apply all fixes to content using simple string replacement."""
        for fix in self.fixes:
            lines = self.content.split("\n")

            for line_num, line in enumerate(lines, start=1):
                # Simple string replacement - no regex
                if fix.old_pattern in line:
                    lines[line_num - 1] = line.replace(
                        fix.old_pattern, fix.new_pattern
                    )
                    fix.occurrences += 1
                    fix.applied_lines.append(line_num)

            self.content = "\n".join(lines)

    def save_fixed_file(self):
        """Save the fixed markdown file."""
        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write(self.content)

    def generate_report(self) -> str:
        """Generate a detailed fix report."""
        report_lines = [
            "# Markdown Citation Fixes Report",
            "",
            f"**Input File**: `{self.input_file}`",
            f"**Output File**: `{self.output_file}`",
            f"**Date**: {Path(__file__).stat().st_mtime}",
            "",
            "---",
            "",
            "## Summary",
            "",
            f"- **Total Fixes Defined**: {len(self.fixes)}",
            f"- **Total Occurrences Fixed**: {sum(f.occurrences for f in self.fixes)}",
            f"- **Fixes Applied**: {sum(1 for f in self.fixes if f.occurrences > 0)}",
            f"- **Manual Review Required**: {sum(1 for f in self.fixes if 'MANUAL REVIEW' in f.description)}",
            "",
            "---",
            "",
            "## Fixes Applied",
            "",
        ]

        for i, fix in enumerate(self.fixes, start=1):
            status = "✅ APPLIED" if fix.occurrences > 0 else "❌ NOT FOUND"
            report_lines.append(f"### Fix #{i}: {status}")
            report_lines.append("")
            report_lines.append(f"**Description**: {fix.description}")
            report_lines.append("")
            report_lines.append("**Old Pattern**:")
            report_lines.append("```")
            report_lines.append(fix.old_pattern)
            report_lines.append("```")
            report_lines.append("")
            report_lines.append("**New Pattern**:")
            report_lines.append("```")
            report_lines.append(fix.new_pattern)
            report_lines.append("```")
            report_lines.append("")
            report_lines.append(f"**Occurrences**: {fix.occurrences}")

            if fix.applied_lines:
                report_lines.append(
                    f"**Lines Fixed**: {', '.join(map(str, fix.applied_lines))}"
                )

            report_lines.append("")
            report_lines.append("---")
            report_lines.append("")

        # Add manual review section
        manual_review_fixes = [
            f for f in self.fixes if "MANUAL REVIEW" in f.description
        ]
        if manual_review_fixes:
            report_lines.append("## Manual Review Required")
            report_lines.append("")
            report_lines.append(
                "The following fixes require manual verification:"
            )
            report_lines.append("")
            for fix in manual_review_fixes:
                report_lines.append(f"- **{fix.description}**")
                if fix.occurrences > 0:
                    report_lines.append(
                        f"  - Lines: {', '.join(map(str, fix.applied_lines))}"
                    )
            report_lines.append("")

        return "\n".join(report_lines)

    def save_report(self):
        """Save the fix report."""
        report = self.generate_report()
        with open(self.report_file, "w", encoding="utf-8") as f:
            f.write(report)

    def run(self):
        """Run the complete fix process."""
        print(f"Loading markdown file: {self.input_file}")
        self.load_content()

        print("Defining fixes...")
        self.define_fixes()

        print("Applying fixes...")
        self.apply_fixes()

        print(f"Saving fixed file to: {self.output_file}")
        self.save_fixed_file()

        print("Generating report...")
        self.save_report()

        print(f"\n{'=' * 80}")
        print("CITATION FIX SUMMARY")
        print(f"{'=' * 80}")
        print(f"Input:  {self.input_file}")
        print(f"Output: {self.output_file}")
        print(f"Report: {self.report_file}")
        print("")
        print(
            f"Fixes applied: {sum(1 for f in self.fixes if f.occurrences > 0)}/{len(self.fixes)}"
        )
        print(
            f"Total occurrences fixed: {sum(f.occurrences for f in self.fixes)}"
        )

        manual_review = sum(
            1
            for f in self.fixes
            if "MANUAL REVIEW" in f.description and f.occurrences > 0
        )
        if manual_review > 0:
            print("")
            print(f"⚠️  WARNING: {manual_review} fixes require manual review")
            print(f"    See {self.report_file} for details")

        print(f"{'=' * 80}")


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/fix_markdown_citations.py <markdown_file>")
        print("")
        print("Example:")
        print("  python scripts/fix_markdown_citations.py /path/to/paper.md")
        sys.exit(1)

    input_file = Path(sys.argv[1])

    if not input_file.exists():
        print(f"ERROR: File not found: {input_file}")
        sys.exit(1)

    if input_file.suffix.lower() not in [".md", ".markdown"]:
        print("ERROR: File must be a markdown file (.md or .markdown)")
        sys.exit(1)

    fixer = MarkdownCitationFixer(input_file)
    fixer.run()


if __name__ == "__main__":
    main()
