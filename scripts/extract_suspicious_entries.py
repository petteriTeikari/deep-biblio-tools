#!/usr/bin/env python3
"""
Extract and save all suspicious bibliography entries for manual review.
"""

import argparse
import json

# import re  # Banned - using string methods instead
from collections import defaultdict
from pathlib import Path


class SuspiciousEntryExtractor:
    """Extracts suspicious bibliography entries with full context."""

    def __init__(self, bbl_file: Path):
        self.bbl_file = bbl_file
        self.suspicious_entries = defaultdict(list)

    def extract_entries(self):
        """Extract all entries and categorize suspicious ones."""
        with open(self.bbl_file, encoding="utf-8") as f:
            content = f.read()

        # Split into individual entries
        entries = []
        current_entry = ""
        i = 0
        while i < len(content):
            if content[i:].startswith("\\bibitem{"):
                if current_entry.strip():
                    entries.append(current_entry.strip())
                current_entry = content[i : i + 9]  # Start with "\\bibitem{"
                i += 9
            else:
                if current_entry:
                    current_entry += content[i]
                i += 1
        if current_entry.strip() and "\\bibitem{" in current_entry:
            entries.append(current_entry.strip())

        for entry in entries:
            self._analyze_entry(entry)

        return self.suspicious_entries

    def _analyze_entry(self, entry: str):
        """Analyze a single entry for various issues."""
        # Extract citation key
        if not entry.startswith("\\bibitem{"):
            return

        # Find the closing brace
        close_brace = entry.find("}", 9)
        if close_brace == -1:
            return

        key = entry[9:close_brace]

        # Clean entry for analysis
        entry_single_line = entry.replace("\n", " ").strip()

        # Store entry data
        entry_data = {
            "key": key,
            "full_text": entry,
            "issues": [],
        }

        # 1. Check for "et al."
        if " et al." in entry_single_line:
            entry_data["issues"].append("incomplete_authors")
            self.suspicious_entries["incomplete_authors"].append(
                entry_data.copy()
            )

        # 2. Check for missing hyperlinks
        # Check if contains \href{...}
        has_href = False
        href_start = entry_single_line.find("\\href{")
        if href_start != -1:
            # Check if there's a closing brace
            brace_count = 1
            i = href_start + 6
            while i < len(entry_single_line) and brace_count > 0:
                if entry_single_line[i] == "{":
                    brace_count += 1
                elif entry_single_line[i] == "}":
                    brace_count -= 1
                i += 1
            has_href = brace_count == 0
        has_url_keywords = any(
            kw in entry_single_line.lower()
            for kw in ["accessed", "http", "arxiv", "doi.org"]
        )

        if not has_href and not has_url_keywords:
            entry_data["issues"].append("missing_hyperlink")
            self.suspicious_entries["missing_hyperlink"].append(
                entry_data.copy()
            )

        # 3. Check for arXiv entries without proper IDs
        if "arXiv" in entry_single_line:
            # Check for arXiv:NNNN.NNNN pattern
            has_arxiv_id = False
            arxiv_pos = entry_single_line.find("arXiv:")
            if arxiv_pos != -1:
                # Check if followed by digit pattern
                i = arxiv_pos + 6
                # Check for digits, dot, digits pattern
                digit_count = 0
                while (
                    i < len(entry_single_line)
                    and entry_single_line[i].isdigit()
                ):
                    digit_count += 1
                    i += 1
                if (
                    i < len(entry_single_line)
                    and entry_single_line[i] == "."
                    and digit_count > 0
                ):
                    i += 1
                    digit_count2 = 0
                    while (
                        i < len(entry_single_line)
                        and entry_single_line[i].isdigit()
                    ):
                        digit_count2 += 1
                        i += 1
                    if digit_count2 > 0:
                        has_arxiv_id = True
            if not has_arxiv_id:
                entry_data["issues"].append("missing_arxiv_id")
                self.suspicious_entries["missing_arxiv_id"].append(
                    entry_data.copy()
                )

        # 4. Check for malformed author names
        # Extract author section (between bibitem and year)
        after_bibitem = entry_single_line.split("}", 1)[-1]
        # Find year pattern (NNNN where N is digit)
        before_year = after_bibitem
        year_pos = -1
        for i in range(len(after_bibitem) - 5):
            if (
                after_bibitem[i] == "("
                and after_bibitem[i + 1 : i + 5].isdigit()
                and (
                    i + 5 >= len(after_bibitem)
                    or not after_bibitem[i + 5].isdigit()
                )
            ):
                year_pos = i
                break
        if year_pos != -1:
            before_year = after_bibitem[:year_pos]

        # Look for problematic comma patterns
        # Pattern 1: "First, Last (" - likely reversed name order
        # Pattern 2: ", LastName (" - incomplete name
        has_bad_pattern = False

        # Check for pattern like "Capitalized, Capitalized ("
        i = 0
        while i < len(before_year) - 3:
            if (
                before_year[i].isupper()
                and i + 1 < len(before_year)
                and before_year[i + 1].islower()
            ):
                # Found capital letter followed by lowercase
                j = i + 1
                while j < len(before_year) and before_year[j].islower():
                    j += 1
                # Check if followed by ", "
                if j + 2 < len(before_year) and before_year[j : j + 2] == ", ":
                    k = j + 2
                    # Check if followed by another capitalized word
                    if k < len(before_year) and before_year[k].isupper():
                        m = k + 1
                        while m < len(before_year) and before_year[m].islower():
                            m += 1
                        # Check if followed by space and "("
                        if m < len(before_year):
                            n = m
                            while (
                                n < len(before_year) and before_year[n] == " "
                            ):
                                n += 1
                            if n < len(before_year) and before_year[n] == "(":
                                has_bad_pattern = True
                                break
            i += 1

        # Also check for ", Name (" pattern at start
        if before_year.strip().startswith(", "):
            rest = before_year.strip()[2:]
            if rest and rest[0].isupper():
                # Find next space or (
                j = 1
                while j < len(rest) and rest[j].isalpha():
                    j += 1
                if j < len(rest) and (rest[j] == " " or rest[j] == "("):
                    has_bad_pattern = True

        if has_bad_pattern:
            # Exclude known OK patterns (Jr., Sr., etc.)
            has_suffix = False
            for suffix in ["Jr.", "Sr.", "III.", "II.", "IV."]:
                if suffix in before_year:
                    has_suffix = True
                    break

            if not has_suffix:
                entry_data["issues"].append("malformed_authors")
                self.suspicious_entries["malformed_authors"].append(
                    entry_data.copy()
                )

        # 5. Single name authors
        # Look for entries that start with just one capitalized word then year
        trimmed = after_bibitem.strip()
        if trimmed:
            # Check if starts with capital letter
            if trimmed[0].isupper():
                # Find end of word
                i = 1
                while i < len(trimmed) and trimmed[i].islower():
                    i += 1
                # Check if followed by whitespace then (YYYY)
                if i < len(trimmed):
                    j = i
                    while j < len(trimmed) and trimmed[j].isspace():
                        j += 1
                    if (
                        j + 6 < len(trimmed)
                        and trimmed[j] == "("
                        and trimmed[j + 1 : j + 5].isdigit()
                        and trimmed[j + 5] == ")"
                    ):
                        # Found single name author pattern
                        entry_data["issues"].append("single_name_author")
                        self.suspicious_entries["single_name_author"].append(
                            entry_data.copy()
                        )

        # 6. Future publications (2025+)
        # Find year in parentheses (YYYY)
        i = 0
        while i < len(entry_single_line) - 5:
            if entry_single_line[i] == "(" and entry_single_line[i + 5] == ")":
                year_str = entry_single_line[i + 1 : i + 5]
                if year_str.isdigit():
                    year = int(year_str)
                    if (
                        year >= 2025
                        and "accessed" not in entry_single_line.lower()
                    ):
                        entry_data["issues"].append("future_publication")
                        self.suspicious_entries["future_publication"].append(
                            entry_data.copy()
                        )
                        break
            i += 1

        # 7. Missing venue
        has_venue = False

        # Check for {\em ...} pattern (journal in italics)
        if "{\\em" in entry_single_line:
            # Find matching closing brace
            start = entry_single_line.find("{\\em")
            brace_count = 1
            i = start + 4
            while i < len(entry_single_line) and brace_count > 0:
                if entry_single_line[i] == "{":
                    brace_count += 1
                elif entry_single_line[i] == "}":
                    brace_count -= 1
                i += 1
            if brace_count == 0:
                has_venue = True

        # Check for "In:" or "In " pattern
        if not has_venue:
            if "In:" in entry_single_line or "In " in entry_single_line:
                has_venue = True

        # Check for other venue keywords
        venue_keywords = [
            "arxiv",
            "http",
            "technical report",
            "phd thesis",
            "master",
        ]
        if not has_venue:
            entry_lower = entry_single_line.lower()
            for keyword in venue_keywords:
                if keyword in entry_lower:
                    has_venue = True
                    break

        if not has_venue:
            entry_data["issues"].append("missing_venue")
            self.suspicious_entries["missing_venue"].append(entry_data.copy())

        # 8. Website citations without URLs
        if key.startswith("https") or key.startswith("http"):
            if not has_href and "http" not in entry_single_line:
                entry_data["issues"].append("website_no_url")
                self.suspicious_entries["website_no_url"].append(
                    entry_data.copy()
                )

        # 9. Check for specific patterns that might be false positives
        # If entry has multiple issues, check if it's a known OK pattern
        if len(entry_data["issues"]) > 0:
            # Check if it's a website/online resource (these often lack traditional venue info)
            online_keywords = [
                "website",
                "online",
                "accessed",
                "retrieved",
                "available",
            ]
            entry_lower = entry_single_line.lower()
            is_online_resource = any(
                keyword in entry_lower for keyword in online_keywords
            )

            if is_online_resource:
                # Remove missing_venue flag for online resources
                if "missing_venue" in entry_data["issues"]:
                    entry_data["issues"].remove("missing_venue")
                    # Remove from that category if it was the only issue
                    if (
                        len(entry_data["issues"]) == 0
                        and entry_data
                        in self.suspicious_entries["missing_venue"]
                    ):
                        self.suspicious_entries["missing_venue"].remove(
                            entry_data
                        )

    def save_report(self, output_file: Path):
        """Save detailed report of suspicious entries."""
        report = {
            "total_suspicious": sum(
                len(entries) for entries in self.suspicious_entries.values()
            ),
            "by_category": {},
        }

        # Create examples for each category
        for category, entries in self.suspicious_entries.items():
            report["by_category"][category] = {
                "count": len(entries),
                "examples": [],
            }

            # Save up to 5 examples per category
            for entry in entries[:5]:
                example = {
                    "key": entry["key"],
                    "text": entry["full_text"][:500] + "..."
                    if len(entry["full_text"]) > 500
                    else entry["full_text"],
                    "full_text": entry["full_text"],
                }
                report["by_category"][category]["examples"].append(example)

        # Save JSON report
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # Also save a text report for easy reading
        text_file = output_file.with_suffix(".txt")
        with open(text_file, "w", encoding="utf-8") as f:
            f.write("SUSPICIOUS BIBLIOGRAPHY ENTRIES REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(
                f"Total suspicious entries: {report['total_suspicious']}\n\n"
            )

            for category, data in report["by_category"].items():
                f.write(f"\n{category.upper().replace('_', ' ')}\n")
                f.write(f"Count: {data['count']}\n")
                f.write("-" * 80 + "\n")

                for i, example in enumerate(data["examples"], 1):
                    f.write(f"\n[{i}] Key: {example['key']}\n")
                    f.write(f"Entry:\n{example['full_text']}\n")
                    f.write("-" * 40 + "\n")

                if data["count"] > 5:
                    f.write(f"\n... and {data['count'] - 5} more entries\n")
                f.write("\n" + "=" * 80 + "\n")

        # Save all suspicious entries to separate files by category
        suspicious_dir = output_file.parent / "suspicious_entries"
        suspicious_dir.mkdir(exist_ok=True)

        for category, entries in self.suspicious_entries.items():
            category_file = suspicious_dir / f"{category}.txt"
            with open(category_file, "w", encoding="utf-8") as f:
                f.write(f"{category.upper().replace('_', ' ')} ENTRIES\n")
                f.write(f"Total: {len(entries)}\n")
                f.write("=" * 80 + "\n\n")

                for i, entry in enumerate(entries, 1):
                    f.write(f"[{i}] Key: {entry['key']}\n")
                    f.write(f"Issues: {', '.join(entry['issues'])}\n")
                    f.write(f"Entry:\n{entry['full_text']}\n")
                    f.write("\n" + "-" * 80 + "\n\n")


def main():
    parser = argparse.ArgumentParser(
        description="Extract suspicious bibliography entries for review"
    )
    parser.add_argument("bbl_file", type=Path, help="Path to the .bbl file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output file for report (default: suspicious_entries.json)",
        default=Path("suspicious_entries.json"),
    )

    args = parser.parse_args()

    if not args.bbl_file.exists():
        print(f"Error: File not found: {args.bbl_file}")
        return 1

    extractor = SuspiciousEntryExtractor(args.bbl_file)
    extractor.extract_entries()
    extractor.save_report(args.output)

    print(f"Report saved to: {args.output}")
    print(f"Text report saved to: {args.output.with_suffix('.txt')}")
    print(
        f"Individual category files saved to: {args.output.parent / 'suspicious_entries'}"
    )

    return 0


if __name__ == "__main__":
    exit(main())
