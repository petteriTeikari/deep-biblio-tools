#!/usr/bin/env python3
"""verify_bbl_quality.py
-------------------------
Verify .bbl file quality by detecting common citation issues.

This script implements ALL quality checks from the comprehensive test plan:
1. Domain-as-title detection (Amazon.de, Arxiv.org)
2. Stub title detection (Web page by X)
3. Missing title detection
4. Temp key detection (Temp, dryrun_, Unknown)
5. Organization name format issues
6. Generic/low-quality titles (single words, site chrome)

Usage:
    python verify_bbl_quality.py output.bbl
    python verify_bbl_quality.py output.bbl --report report.json
    python verify_bbl_quality.py output.bbl --strict  # Exit 1 on any issues

Exit codes:
    0 - All checks passed
    1 - Hard failures (domain titles, stub titles, missing titles, temp keys)
    2 - Soft failures only (warnings, low-quality titles)
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------

DOMAIN_PATTERNS = [
    r"\b[a-z0-9-]+\.(com|org|net|edu|gov|de|uk|fr|io|co)\b",  # example.com
    r"\bAmazon\.(de|com|uk|fr)\b",  # Amazon.de
    r"\bArxiv\.org\b",  # Arxiv.org
]

STUB_PATTERNS = [
    r"^Web page by ",
    r"^Web article by ",
    r"^Web site by ",
    r"^Added from URL:",
]

TEMP_MARKERS = [
    "temp",
    "dryrun_",
    "unknown",
    "anonymous",
]

MALFORMED_ORG_PATTERNS = [
    r"\bCommission E\b",  # European Commission
    r"\bFoundation EM\b",  # Ellen MacArthur Foundation
    r"\bRevolution F\b",  # Fashion Revolution
    r"\bNations U\b",  # United Nations
    r"\bBank W\b",  # World Bank
]

SITE_CHROME_PATTERNS = [
    r"\|",  # Pipe character (often in titles like "Page | Site Name")
]

# Whitelist for legitimate short titles
LEGIT_SHORT_TITLES = {"Nature", "Science", "Cell", "PLOS", "Wired", "arXiv"}

# --------------------------------------------------------------------
# .bbl Parser
# --------------------------------------------------------------------


def parse_bbl_file(bbl_path: Path) -> list[dict[str, Any]]:
    """
    Parse .bbl file to extract bibliography entries.

    Handles multiple \bibitem forms and uses fallback heuristics
    for title extraction.
    """
    text = bbl_path.read_text(encoding="utf8", errors="ignore")

    # Split on \bibitem
    items = re.split(r"\\bibitem(?:\[[^\]]*\])?\{", text)[1:]

    entries = []
    for item in items:
        # Extract key
        key_match = re.match(r"([^}]*)\}", item)
        if not key_match:
            continue

        key = key_match.group(1).strip()
        body = item[key_match.end() :].strip()

        # Try multiple heuristics for title extraction
        title = ""

        # 1. Try \newblock
        m = re.search(r"\\newblock\s+(.+?)\.(?:\s|\\)", body, re.DOTALL)

        # 2. Fallback to \emph or \textit
        if not m:
            m = re.search(r"\\emph\{(.+?)\}", body, re.DOTALL) or re.search(
                r"\\textit\{(.+?)\}", body, re.DOTALL
            )

        # 3. Fallback to first sentence after author line
        if not m:
            lines = [l.strip() for l in body.split("\n") if l.strip()]
            if len(lines) > 1:
                # Take second line, split by period
                potential_title = lines[1].split(".")[0]
                # Remove LaTeX commands
                potential_title = re.sub(r"\\[a-z]+\{?", "", potential_title)
                potential_title = re.sub(r"\}", "", potential_title)
                title = potential_title.strip()

        if m:
            title = m.group(1).strip()
            # Clean LaTeX commands
            title = re.sub(r"\\[a-z]+\{?", "", title)
            title = re.sub(r"\}", "", title)

        # Extract first author line (usually first non-empty line)
        first_line = body.split("\n")[0].strip() if body else ""

        # Extract year from citation label if present
        year = ""
        label_match = re.search(r"\((\d{4})\)", key) or re.search(
            r"\((\d{4})\)", body
        )
        if label_match:
            year = label_match.group(1)

        entries.append(
            {
                "key": key,
                "author": first_line,
                "title": title,
                "year": year,
                "body": body,  # Keep full text for additional checks
            }
        )

    return entries


# --------------------------------------------------------------------
# Quality Checks
# --------------------------------------------------------------------


def check_domain_titles(entries: list[dict]) -> list[str]:
    """Check for domain names as titles."""
    issues = []
    for entry in entries:
        title = entry.get("title", "")
        for pattern in DOMAIN_PATTERNS:
            if re.search(pattern, title, re.IGNORECASE):
                issues.append(f"{entry['key']}: Title is domain name '{title}'")
    return issues


def check_stub_titles(entries: list[dict]) -> list[str]:
    """Check for stub titles like 'Web page by X'."""
    issues = []
    for entry in entries:
        title = entry.get("title", "")
        for pattern in STUB_PATTERNS:
            if re.search(pattern, title, re.IGNORECASE):
                issues.append(f"{entry['key']}: Stub title '{title}'")
    return issues


def check_missing_titles(entries: list[dict]) -> list[str]:
    """Check for missing or empty titles."""
    issues = []
    for entry in entries:
        title = entry.get("title", "").strip()
        if not title or len(title) < 2:
            author = entry.get("author", "Unknown")
            year = entry.get("year", "Unknown")
            issues.append(
                f"{entry['key']}: Missing title (Author: {author}, Year: {year})"
            )
    return issues


def check_temp_keys(entries: list[dict]) -> list[str]:
    """Check for temporary/placeholder citation keys."""
    issues = []
    for entry in entries:
        key = entry["key"].lower()
        for marker in TEMP_MARKERS:
            if marker in key:
                issues.append(
                    f"{entry['key']}: Contains temp marker '{marker}'"
                )
    return issues


def check_malformed_orgs(entries: list[dict]) -> list[str]:
    """Check for malformed organization names in body."""
    issues = []
    for entry in entries:
        body = entry.get("body", "")
        for pattern in MALFORMED_ORG_PATTERNS:
            if re.search(pattern, body):
                issues.append(
                    f"{entry['key']}: Malformed organization name found (pattern: {pattern})"
                )
    return issues


def check_generic_titles(entries: list[dict]) -> list[str]:
    """Check for generic/low-quality titles."""
    issues = []
    for entry in entries:
        title = entry.get("title", "")

        # Check for pipe symbols (often indicate site chrome)
        if "|" in title:
            issues.append(f"{entry['key']}: Title contains pipe '|': '{title}'")

        # Check for single-word titles (likely domain or app name)
        words = title.split()
        if len(words) == 1 and len(title) < 20:
            if title not in LEGIT_SHORT_TITLES:
                issues.append(f"{entry['key']}: Single-word title: '{title}'")

    return issues


# --------------------------------------------------------------------
# Main
# --------------------------------------------------------------------


def verify_bbl_quality(bbl_path: Path, strict: bool = False) -> dict[str, Any]:
    """
    Verify .bbl file quality.

    Returns report dict with all issues found.
    """
    if not bbl_path.exists():
        raise FileNotFoundError(f".bbl file not found: {bbl_path}")

    # Parse .bbl file
    entries = parse_bbl_file(bbl_path)

    if not entries:
        return {
            "success": False,
            "error": "No entries found in .bbl file (parsing failed or empty)",
            "issues": {},
        }

    # Run all checks
    report = {
        "success": True,
        "total_entries": len(entries),
        "issues": {
            "domain_titles": check_domain_titles(entries),
            "stub_titles": check_stub_titles(entries),
            "missing_titles": check_missing_titles(entries),
            "temp_keys": check_temp_keys(entries),
            "malformed_orgs": check_malformed_orgs(entries),
            "generic_titles": check_generic_titles(entries),
        },
    }

    # Count issues
    hard_failures = sum(
        len(report["issues"][k])
        for k in ["domain_titles", "stub_titles", "missing_titles", "temp_keys"]
    )

    soft_failures = sum(
        len(report["issues"][k]) for k in ["malformed_orgs", "generic_titles"]
    )

    report["hard_failures"] = hard_failures
    report["soft_failures"] = soft_failures

    # Determine success
    if strict:
        report["success"] = hard_failures == 0 and soft_failures == 0
    else:
        report["success"] = hard_failures == 0

    return report


def print_report(report: dict[str, Any]):
    """Print human-readable report."""
    print("=" * 70)
    print("Bibliography Quality Report")
    print("=" * 70)
    print(f"\nTotal entries: {report.get('total_entries', 0)}")

    issues = report.get("issues", {})
    hard_failures = report.get("hard_failures", 0)
    soft_failures = report.get("soft_failures", 0)

    if report.get("error"):
        print(f"\n❌ ERROR: {report['error']}")
        return

    print(f"\nHard failures: {hard_failures}")
    print(f"Soft failures: {soft_failures}")

    # Print each issue category
    for category, items in issues.items():
        if items:
            print(f"\n{category.upper().replace('_', ' ')} ({len(items)}):")
            for item in items[:10]:  # Show first 10
                print(f"  - {item}")
            if len(items) > 10:
                print(f"  ... and {len(items) - 10} more")

    print("\n" + "=" * 70)
    if report["success"]:
        print("✅ ALL QUALITY CHECKS PASSED")
    elif hard_failures > 0:
        print(f"❌ HARD FAILURES: {hard_failures}")
        print("   Fix these before claiming conversion success!")
    else:
        print(f"⚠️  SOFT FAILURES: {soft_failures}")
        print(
            "   These are warnings - conversion may proceed but quality is suboptimal"
        )
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify .bbl file quality")
    parser.add_argument("bbl_file", type=Path, help=".bbl file to verify")
    parser.add_argument("--report", type=Path, help="Write JSON report to file")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any issues (including warnings)",
    )

    args = parser.parse_args()

    try:
        report = verify_bbl_quality(args.bbl_file, strict=args.strict)

        # Write JSON report if requested
        if args.report:
            with open(args.report, "w", encoding="utf8") as f:
                json.dump(report, f, indent=2)
            print(f"\n✅ JSON report written to {args.report}")

        # Print human-readable report
        print_report(report)

        # Exit with appropriate code
        if not report["success"]:
            if report.get("hard_failures", 0) > 0:
                exit(1)  # Hard failures
            else:
                exit(2)  # Soft failures only
        else:
            exit(0)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        exit(1)
