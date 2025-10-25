#!/usr/bin/env python3
"""
Post-conversion QA validation for hardcoded bibliography files.
Identifies potential issues that may need manual verification.
"""

import argparse
import json
import logging

# import re  # Banned - using string methods instead
import sys
from collections import defaultdict
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class BibliographyValidator:
    """Validates hardcoded bibliography entries for potential issues."""

    def __init__(self, bbl_file: Path):
        self.bbl_file = bbl_file
        self.issues: dict[str, list[tuple[int, str, str, str]]] = defaultdict(
            list
        )
        self.entries_checked = 0
        self.entries = []

    def validate(self) -> dict[str, list[tuple[int, str, str, str]]]:
        """Run all validation checks on the bibliography file."""
        logger.info(f"Validating {self.bbl_file}")

        with open(self.bbl_file, encoding="utf-8") as f:
            content = f.read()

        # Split into individual entries
        entries = []
        current_entry = ""
        for line in content.split("\n"):
            if line.strip().startswith("\\bibitem{"):
                if current_entry:
                    entries.append(current_entry.strip())
                current_entry = line + "\n"
            else:
                current_entry += line + "\n"
        if current_entry and "\\bibitem{" in current_entry:
            entries.append(current_entry.strip())

        for entry in entries:
            self._validate_entry(entry)

        return self.issues

    def _validate_entry(self, entry: str):
        """Validate a single bibliography entry with improved rules."""
        # Extract citation key
        if not entry.startswith("\\bibitem{"):
            return

        start_idx = entry.find("{")
        end_idx = entry.find("}", start_idx)
        if start_idx == -1 or end_idx == -1:
            return

        key = entry[start_idx + 1 : end_idx]
        self.entries_checked += 1

        # Clean entry for analysis
        entry_single_line = entry.replace("\n", " ").strip()

        # Extract the line number (approximate)
        line_num = self.entries_checked  # Simplified for now

        # HIGH PRIORITY ISSUES

        # 1. Check for "et al." - always a problem in LLM-generated bibliographies
        if " et al." in entry_single_line:
            self.issues["incomplete_authors"].append(
                (
                    line_num,
                    key,
                    "Entry contains 'et al.' - missing full author list",
                    entry[:200],
                )
            )

        # 2. Check for malformed author names
        # Look for "Jung-Min, Park" pattern (comma between first and last)
        after_bibitem = entry_single_line.split("}", 1)[-1]
        # Find the part before year (which usually comes in parentheses)
        before_year = after_bibitem
        paren_idx = after_bibitem.find("(")
        if paren_idx != -1:
            # Check if it's followed by a 4-digit year
            if (
                paren_idx + 5 <= len(after_bibitem)
                and after_bibitem[paren_idx + 1 : paren_idx + 5].isdigit()
            ):
                before_year = after_bibitem[:paren_idx]

        # Pattern: First-name, Lastname (wrong comma placement)
        # Look for pattern like "Jung-Min, Park"
        words = before_year.split()
        for word in words:
            if "-" in word and "," in word:
                # Check if it matches First-name, pattern
                parts = word.split(",")
                if len(parts) == 2 and "-" in parts[0]:
                    name_parts = parts[0].split("-")
                    if all(
                        p and p[0].isupper() and p[1:].islower()
                        for p in name_parts
                        if p
                    ):
                        self.issues["malformed_authors"].append(
                            (
                                line_num,
                                key,
                                "Author name has comma in wrong place (First-name, Last)",
                                entry[:200],
                            )
                        )
                        break

        # 3. ArXiv entries without proper IDs
        if "arXiv" in entry_single_line:
            # Should have format arXiv:XXXX.XXXXX
            has_proper_id = False
            if "arXiv:" in entry_single_line:
                arxiv_idx = entry_single_line.find("arXiv:")
                after_arxiv = entry_single_line[arxiv_idx + 6 :]
                # Check if it follows pattern XXXX.XXXXX
                if len(after_arxiv) >= 10:
                    if (
                        after_arxiv[0:4].isdigit()
                        and after_arxiv[4] == "."
                        and after_arxiv[5:9].isdigit()
                    ):
                        has_proper_id = True
                    elif (
                        after_arxiv[0:4].isdigit()
                        and after_arxiv[4] == "."
                        and after_arxiv[5:10].isdigit()
                    ):
                        has_proper_id = True

            if not has_proper_id:
                self.issues["missing_arxiv_id"].append(
                    (
                        line_num,
                        key,
                        "arXiv entry missing proper ID (should be arXiv:XXXX.XXXXX)",
                        entry[:200],
                    )
                )

        # 4. Single-name authors (often indicates incomplete data)
        # Skip if it's clearly a website/organization
        is_organization = any(
            org in entry_single_line
            for org in [
                "Foundation",
                "Institute",
                "Corporation",
                "Agency",
                "Office",
                "Department",
                "Inc.",
                "LLC",
                "Affairs",
                ".com",
                ".org",
                "http",
            ]
        )

        if not is_organization:
            # Check for single word followed by year
            trimmed = after_bibitem.strip()
            if trimmed and trimmed[0].isupper():
                # Find first space or opening parenthesis
                trimmed.find(" ")
                paren_idx = trimmed.find("(")

                if paren_idx != -1:
                    # Check if we have pattern like "Author (2024)"
                    word_before_paren = trimmed[:paren_idx].strip()
                    if " " not in word_before_paren and word_before_paren:
                        # Check if parenthesis contains year
                        if (
                            paren_idx + 5 < len(trimmed)
                            and trimmed[paren_idx + 1 : paren_idx + 5].isdigit()
                        ):
                            self.issues["single_name_author"].append(
                                (
                                    line_num,
                                    key,
                                    "Author appears to have only surname (may need first name)",
                                    entry[:200],
                                )
                            )

        # MEDIUM PRIORITY ISSUES

        # 5. Future publications (but only flag if really suspicious)
        year = None
        # Look for year in parentheses
        start_idx = 0
        while True:
            paren_idx = entry_single_line.find("(", start_idx)
            if paren_idx == -1:
                break
            close_idx = entry_single_line.find(")", paren_idx)
            if close_idx != -1 and close_idx - paren_idx == 5:
                year_str = entry_single_line[paren_idx + 1 : close_idx]
                if year_str.isdigit() and len(year_str) == 4:
                    year = int(year_str)
                    break
            start_idx = paren_idx + 1

        if year:
            # Only flag 2026+ as definitely wrong, 2025 might be legitimate
            if year >= 2026:
                self.issues["future_publication"].append(
                    (
                        line_num,
                        key,
                        f"Publication year {year} is in the future",
                        entry[:200],
                    )
                )
            elif year == 2025 and "accessed" not in entry_single_line.lower():
                # For 2025, only flag if it has a DOI (suggesting published paper)
                if "doi.org" in entry_single_line:
                    self.issues["suspicious_2025_doi"].append(
                        (
                            line_num,
                            key,
                            "2025 publication with DOI - verify if actually published",
                            entry[:200],
                        )
                    )

        # 6. Missing hyperlinks - but be smart about it
        has_href = "\\href{" in entry_single_line and "}" in entry_single_line

        # Check if it should have a hyperlink
        has_doi = False
        if "10." in entry_single_line:
            doi_idx = entry_single_line.find("10.")
            after_doi = entry_single_line[doi_idx + 3 :]
            if len(after_doi) >= 4 and after_doi[:4].isdigit():
                has_doi = True
        has_arxiv = "arXiv:" in entry_single_line
        has_url = (
            "http://" in entry_single_line or "https://" in entry_single_line
        )

        if (has_doi or has_arxiv or has_url) and not has_href:
            self.issues["missing_hyperlink"].append(
                (
                    line_num,
                    key,
                    "Entry has DOI/arXiv/URL but no hyperlink",
                    entry[:200],
                )
            )

        # 7. Website entries without URLs
        if key.startswith(("http", "www")):
            if not (
                "http://" in entry_single_line
                or "https://" in entry_single_line
            ):
                self.issues["website_no_url"].append(
                    (
                        line_num,
                        key,
                        "Website citation missing actual URL",
                        entry[:200],
                    )
                )

        # LOW PRIORITY ISSUES

        # 8. Missing venue - but with many exceptions
        venue_indicators = [
            "{\\em ",  # Journal in italics
            "In:",  # Conference proceedings
            "In ",  # Conference proceedings alt
            "arXiv",
            "Proceedings",
            "Journal",
            "Conference",
            "Technical Report",
            "PhD thesis",
            "Master",
            "accessed",  # Online resources
            "http",
        ]

        has_venue = any(
            indicator.lower() in entry_single_line.lower()
            for indicator in venue_indicators
        )

        # Only flag if it's not obviously a website/online resource
        if (
            not has_venue
            and not is_organization
            and "accessed" not in entry_single_line
        ):
            self.issues["possibly_missing_venue"].append(
                (
                    line_num,
                    key,
                    "Entry may be missing publication venue",
                    entry[:200],
                )
            )

    def print_report(self):
        """Print a formatted report of all issues found."""
        print("\n" + "=" * 80)
        print("BIBLIOGRAPHY VALIDATION REPORT")
        print(f"File: {self.bbl_file}")
        print(f"Total entries checked: {self.entries_checked}")
        print("=" * 80 + "\n")

        if not self.issues:
            print("No issues found!")
            return

        total_issues = sum(len(issues) for issues in self.issues.values())
        print(
            f"Found {total_issues} potential issues in {len(self.issues)} categories:\n"
        )

        # Categorize by severity
        high_priority = [
            "incomplete_authors",
            "malformed_authors",
            "missing_arxiv_id",
            "single_name_author",
        ]

        medium_priority = [
            "future_publication",
            "suspicious_2025_doi",
            "missing_hyperlink",
            "website_no_url",
        ]

        low_priority = [
            "possibly_missing_venue",
        ]

        for severity, categories in [
            ("HIGH PRIORITY", high_priority),
            ("MEDIUM PRIORITY", medium_priority),
            ("LOW PRIORITY", low_priority),
        ]:
            severity_issues = [cat for cat in categories if cat in self.issues]
            if severity_issues:
                print(f"\n{severity} ISSUES:")
                print("=" * 50)

                for category in severity_issues:
                    issues = self.issues[category]
                    print(
                        f"\n{category.upper().replace('_', ' ')} ({len(issues)} issues):"
                    )
                    print("-" * 50)

                    # Show first 5 issues in each category
                    for i, (line_num, key, desc, preview) in enumerate(
                        issues[:5]
                    ):
                        print(f"\n[{i + 1}] {key}")
                        print(f"    Issue: {desc}")
                        print(f"    Preview: {preview}...")

                    if len(issues) > 5:
                        print(f"\n    ... and {len(issues) - 5} more")

        print("\n" + "=" * 80)
        print("RECOMMENDATIONS:")
        print("\nHIGH PRIORITY (likely errors):")
        print("- Expand all 'et al.' entries with full author lists")
        print("- Fix malformed author names (check comma placement)")
        print("- Add proper arXiv IDs (format: arXiv:XXXX.XXXXX)")
        print("- Verify single-name authors aren't missing first names")

        # Special guidance for export format issues
        arxiv_missing = len(self.issues.get("missing_arxiv_id", []))
        hyperlink_missing = len(self.issues.get("missing_hyperlink", []))

        if arxiv_missing > 10 or (arxiv_missing > 5 and hyperlink_missing > 5):
            print("\n[!] ZOTERO EXPORT FORMAT ISSUE DETECTED:")
            print(
                "  Many entries are missing URLs/arXiv IDs. This commonly happens when using"
            )
            print(
                "  'Better BibTeX' export format instead of 'Better BibLaTeX' in Zotero."
            )
            print(
                "  -> Solution: Re-export your bibliography using 'Better BibLaTeX' format"
            )
            print(
                "  -> This format preserves URLs, DOIs, and arXiv identifiers properly"
            )

        print("\nMEDIUM PRIORITY (verify correctness):")
        print("- Check 2025 publications with DOIs are actually published")
        print("- Add hyperlinks for entries with DOIs/URLs")

        print("\nLOW PRIORITY (may be false positives):")
        print("- Review entries flagged for missing venues")
        print("=" * 80 + "\n")

    def save_actionable_report(self, output_file: Path):
        """Save a report focused on actionable fixes."""
        report = {
            "summary": {
                "total_entries": self.entries_checked,
                "total_issues": sum(
                    len(issues) for issues in self.issues.values()
                ),
                "high_priority_count": sum(
                    len(self.issues.get(cat, []))
                    for cat in [
                        "incomplete_authors",
                        "malformed_authors",
                        "missing_arxiv_id",
                        "single_name_author",
                    ]
                ),
            },
            "high_priority_fixes": {},
            "verification_needed": {},
        }

        # High priority fixes
        for category in [
            "incomplete_authors",
            "malformed_authors",
            "missing_arxiv_id",
        ]:
            if category in self.issues:
                report["high_priority_fixes"][category] = [
                    {
                        "key": key,
                        "issue": desc,
                        "action": self._get_fix_action(category, key, desc),
                    }
                    for _, key, desc, _ in self.issues[category]
                ]

        # Items needing verification
        for category in ["suspicious_2025_doi", "single_name_author"]:
            if category in self.issues:
                report["verification_needed"][category] = [
                    {"key": key, "issue": desc}
                    for _, key, desc, _ in self.issues[category]
                ]

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    def _get_fix_action(self, category: str, key: str, desc: str) -> str:
        """Get specific fix action for an issue."""
        actions = {
            "incomplete_authors": "Look up the paper and replace 'et al.' with full author list",
            "malformed_authors": "Fix author name format - should be 'First Last' or 'Last, First' consistently",
            "missing_arxiv_id": "Find the arXiv paper and add ID in format arXiv:XXXX.XXXXX",
        }
        return actions.get(category, "Manual review needed")


def main():
    parser = argparse.ArgumentParser(
        description="Validate hardcoded bibliography for potential issues"
    )
    parser.add_argument(
        "bbl_file", type=Path, help="Path to the .bbl file to validate"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with error code if HIGH priority issues found",
    )
    parser.add_argument(
        "--save-report",
        type=Path,
        help="Save actionable report to JSON file",
    )

    args = parser.parse_args()

    if not args.bbl_file.exists():
        logger.error(f"File not found: {args.bbl_file}")
        sys.exit(1)

    validator = BibliographyValidator(args.bbl_file)
    issues = validator.validate()
    validator.print_report()

    if args.save_report:
        validator.save_actionable_report(args.save_report)
        print(f"\nActionable report saved to: {args.save_report}")

    # Only exit with error on HIGH priority issues
    if args.strict:
        high_priority_count = sum(
            len(issues.get(cat, []))
            for cat in [
                "incomplete_authors",
                "malformed_authors",
                "missing_arxiv_id",
            ]
        )
        if high_priority_count > 0:
            sys.exit(1)


if __name__ == "__main__":
    main()
