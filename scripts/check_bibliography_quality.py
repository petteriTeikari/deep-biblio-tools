#!/usr/bin/env python3
"""Check quality of extracted bibliography entries."""

import sys
from collections import defaultdict
from pathlib import Path

import bibtexparser


def check_author_format(entry):
    """Check if author field is properly formatted."""
    issues = []

    if "author" not in entry:
        return ["Missing author field"]

    author = entry["author"]

    # Check for improper delimiters (quotes instead of braces)
    if author.startswith('"') and author.endswith('"'):
        issues.append("Author field uses quotes instead of braces")

    # Check for "et al" in author field
    if "et al" in author.lower():
        issues.append("Author field contains 'et al' - should list all authors")

    # Check for proper "LastName, FirstName" format
    if " and " in author:
        authors = author.split(" and ")
        for a in authors:
            if "," not in a and not a.strip().startswith("{"):
                issues.append(
                    f"Author '{a}' not in 'LastName, FirstName' format"
                )

    return issues


def check_arxiv_entries(entry):
    """Check arXiv entries for completeness."""
    issues = []

    if "url" in entry and "arxiv.org" in entry["url"]:
        # Check if using HTML URL instead of abstract
        if "/html/" in entry["url"]:
            issues.append("Using arXiv HTML URL instead of abstract URL")

        # Check if title is missing or generic
        if "title" not in entry or not entry.get("title", "").strip():
            issues.append("Missing title for arXiv entry")
        elif entry.get("title", "").lower() == entry.get("author", "").lower():
            issues.append("Title same as author - likely parsing error")

    return issues


def check_year_field(entry):
    """Check if year field is reasonable."""
    issues = []

    if "year" not in entry:
        issues.append("Missing year field")
    else:
        try:
            year = int(entry["year"])
            if year < 1900 or year > 2026:
                issues.append(f"Suspicious year: {year}")
        except ValueError:
            issues.append(f"Invalid year format: {entry['year']}")

    return issues


def check_researchgate_entries(entry):
    """Check ResearchGate entries."""
    issues = []

    if "url" in entry and "researchgate.net" in entry["url"]:
        # Check if we got blocked
        if "title" in entry and entry["title"] == entry.get("author", ""):
            issues.append(
                "ResearchGate entry likely blocked - title same as author"
            )

        # Check if DOI is available but not used
        if "doi" not in entry and "/publication/" in entry["url"]:
            issues.append("ResearchGate entry might have DOI available")

    return issues


def analyze_bibliography(bib_file):
    """Analyze bibliography file for quality issues."""
    print(f"Analyzing bibliography: {bib_file}")
    print("=" * 80)

    with open(bib_file, encoding="utf-8") as f:
        bib_database = bibtexparser.load(f)

    entries = bib_database.entries
    print(f"Total entries: {len(entries)}")
    print()

    # Statistics
    stats = defaultdict(int)
    issues_by_type = defaultdict(list)

    # Check each entry
    for entry in entries:
        entry_id = entry.get("ID", "unknown")
        all_issues = []

        # Run checks
        issues = check_author_format(entry)
        if issues:
            all_issues.extend(issues)
            stats["author_format_issues"] += 1

        issues = check_arxiv_entries(entry)
        if issues:
            all_issues.extend(issues)
            stats["arxiv_issues"] += 1

        issues = check_year_field(entry)
        if issues:
            all_issues.extend(issues)
            stats["year_issues"] += 1

        issues = check_researchgate_entries(entry)
        if issues:
            all_issues.extend(issues)
            stats["researchgate_issues"] += 1

        # Check for duplicate keys
        if entry_id in issues_by_type:
            all_issues.append("Duplicate entry key")
            stats["duplicate_keys"] += 1

        if all_issues:
            issues_by_type[entry_id] = all_issues
            stats["total_problematic_entries"] += 1

    # Print summary
    print("SUMMARY")
    print("-" * 40)
    for key, count in sorted(stats.items()):
        print(f"{key}: {count}")

    print(
        f"\nProblematic entries: {stats['total_problematic_entries']} / {len(entries)} "
        + f"({100 * stats['total_problematic_entries'] / len(entries):.1f}%)"
    )

    # Print detailed issues for first 20 problematic entries
    print("\nDETAILED ISSUES (first 20)")
    print("-" * 40)

    count = 0
    for entry_id, issues in issues_by_type.items():
        if count >= 20:
            break
        count += 1

        # Find the entry
        entry = next((e for e in entries if e.get("ID") == entry_id), None)
        if entry:
            print(f"\n@{entry.get('ENTRYTYPE', 'misc')}{{{entry_id},")
            if "author" in entry:
                print(f"  author = {entry['author'][:60]}...")
            if "title" in entry:
                print(f'  title = "{entry["title"][:60]}..."')
            if "url" in entry:
                print(f'  url = "{entry["url"][:60]}..."')
            print("Issues:")
            for issue in issues:
                print(f"  - {issue}")

    if len(issues_by_type) > 20:
        print(f"\n... and {len(issues_by_type) - 20} more entries with issues")

    # Specific examples from user
    print("\n\nSPECIFIC EXAMPLES TO CHECK")
    print("-" * 40)

    # Check for the specific entries mentioned
    for entry in entries:
        if entry.get("ID") == "bajcsy2017":
            print("\nbajcsy2017:")
            print(f"  author = {entry.get('author', 'NOT FOUND')}")
            print(
                "  Should be: author = {Bajcsy, Ruzena and Aloimonos, Yiannis and Tsotsos, John K.}"
            )

        if entry.get("ID") == "arkin2025":
            print("\narkin2025:")
            print(f"  author = {entry.get('author', 'NOT FOUND')}")
            print(f"  url = {entry.get('url', 'NOT FOUND')}")
            print("  Issue: Using HTML URL and missing full author list")

        if "asdrubali" in entry.get("ID", "").lower() and "2015" in entry.get(
            "ID", ""
        ):
            print(f"\n{entry.get('ID')}:")
            print(f"  title = {entry.get('title', 'NOT FOUND')}")
            print(f"  author = {entry.get('author', 'NOT FOUND')}")
            print("  Issue: Likely blocked from ResearchGate")


def main():
    """Check bibliography quality."""
    if len(sys.argv) > 1:
        bib_file = Path(sys.argv[1])
    else:
        # Default to the most recent output
        bib_file = Path("drone_data/latex_output_limited/references.bib")

    if not bib_file.exists():
        print(f"Error: Bibliography file not found: {bib_file}")
        print(
            "\nUsage: python check_bibliography_quality.py [path/to/references.bib]"
        )
        return 1

    try:
        analyze_bibliography(bib_file)
        return 0
    except Exception as e:
        print(f"Error analyzing bibliography: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
