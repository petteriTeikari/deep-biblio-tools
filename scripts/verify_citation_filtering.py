#!/usr/bin/env python3
"""
Verify that citation filtering is working correctly.

This script programmatically tests that:
1. Non-academic domains are excluded from citations
2. arXiv versions are properly stripped
3. arXiv URL variants (html/abs/pdf) are normalized
4. The NON_ACADEMIC_DOMAINS list is actually being used

Usage:
    python scripts/verify_citation_filtering.py <markdown_file> <conversion_log>
"""

import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

# Import the NON_ACADEMIC_DOMAINS from the actual source code
# This ensures our test uses the same list as the production code
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from converters.md_to_latex.citation_extractor_unified import (
    UnifiedCitationExtractor,
)
from parsers import MarkdownParser


def extract_all_links_from_markdown(markdown_file: Path) -> list[dict]:
    """Extract ALL links from markdown using the same parser as production."""
    parser = MarkdownParser()
    content = markdown_file.read_text()
    links = parser.extract_links(content)

    print(f"\n=== Extracted {len(links)} total links from markdown ===")
    return links


def classify_links(links: list[dict]) -> dict:
    """Classify links into academic vs non-academic using production code."""
    extractor = UnifiedCitationExtractor()

    classified = {
        "academic": [],
        "non_academic": [],
        "unknown": []
    }

    for link_info in links:
        url = link_info["href"]

        # Skip internal links
        if url.startswith("#"):
            continue

        # Use production code to classify
        is_academic = extractor._is_academic_url(url)

        if is_academic:
            classified["academic"].append(link_info)
        else:
            # Check if it matches NON_ACADEMIC_DOMAINS
            url_lower = url.lower()
            parsed = urlparse(url_lower)
            domain = parsed.netloc

            matched_exclusion = None
            for non_academic_domain in extractor.NON_ACADEMIC_DOMAINS:
                if non_academic_domain in domain:
                    matched_exclusion = non_academic_domain
                    break

            if matched_exclusion:
                classified["non_academic"].append({
                    **link_info,
                    "matched_exclusion": matched_exclusion
                })
            else:
                classified["unknown"].append(link_info)

    print("\n=== Link Classification ===")
    print(f"Academic: {len(classified['academic'])}")
    print(f"Non-academic (explicitly excluded): {len(classified['non_academic'])}")
    print(f"Unknown (not academic, not excluded): {len(classified['unknown'])}")

    return classified


def parse_missing_citations_from_log(log_file: Path) -> list[str]:
    """Parse 'No citation key found for URL' messages from log."""
    missing = []

    with open(log_file) as f:
        for line in f:
            if "No citation key found for URL:" in line:
                # Extract URL between "URL: " and " (normalized:"
                start = line.find("URL: ") + 5
                end = line.find(" (normalized:", start)
                if end > start:
                    url = line[start:end]
                    missing.append(url)

    print(f"\n=== Found {len(missing)} 'missing' citations in conversion log ===")
    return missing


def check_arxiv_normalization(missing_urls: list[str]) -> dict:
    """Check if arXiv URLs are properly normalized."""
    issues = {
        "versions_not_stripped": [],
        "html_not_normalized": [],
        "pdf_not_normalized": []
    }

    for url in missing_urls:
        if "arxiv.org" in url.lower():
            # Check for version numbers
            if url.endswith("v1") or url.endswith("v2") or url.endswith("v3"):
                issues["versions_not_stripped"].append(url)

            # Check for html variant
            if "/html/" in url:
                issues["html_not_normalized"].append(url)

            # Check for pdf variant
            if "/pdf/" in url:
                issues["pdf_not_normalized"].append(url)

    return issues


def verify_exclusions(classified: dict, missing_urls: list[str]) -> dict:
    """Verify that non-academic links are NOT in missing citations."""
    violations = defaultdict(list)

    # Check each non-academic link
    for link_info in classified["non_academic"]:
        url = link_info["href"]
        if url in missing_urls:
            domain = link_info["matched_exclusion"]
            violations[domain].append({
                "url": url,
                "text": link_info["text"],
                "line": link_info["line"]
            })

    return violations


def generate_report(
    classified: dict,
    missing_urls: list[str],
    arxiv_issues: dict,
    violations: dict
) -> str:
    """Generate a comprehensive test report."""
    report = []
    report.append("=" * 80)
    report.append("CITATION FILTERING VERIFICATION REPORT")
    report.append("=" * 80)
    report.append("")

    # Summary statistics
    report.append("## Summary Statistics")
    report.append("")
    report.append(f"Total links in markdown: {len(classified['academic']) + len(classified['non_academic']) + len(classified['unknown'])}")
    report.append(f"  - Academic: {len(classified['academic'])}")
    report.append(f"  - Non-academic (excluded): {len(classified['non_academic'])}")
    report.append(f"  - Unknown: {len(classified['unknown'])}")
    report.append(f"Missing citations reported: {len(missing_urls)}")
    report.append("")

    # Test 1: Non-academic exclusions
    report.append("## Test 1: Non-Academic Domain Exclusions")
    report.append("")

    if not violations:
        report.append("✅ PASS: No non-academic domains found in missing citations list")
    else:
        report.append(f"❌ FAIL: Found {sum(len(v) for v in violations.values())} non-academic links in missing citations")
        report.append("")
        report.append("Violations by domain:")
        for domain, links in sorted(violations.items()):
            report.append(f"  {domain}: {len(links)} occurrences")
            for link in links[:3]:  # Show first 3 examples
                report.append(f"    - Line {link['line']}: [{link['text']}]({link['url']})")
            if len(links) > 3:
                report.append(f"    ... and {len(links) - 3} more")
    report.append("")

    # Test 2: arXiv normalization
    report.append("## Test 2: arXiv URL Normalization")
    report.append("")

    total_arxiv_issues = sum(len(v) for v in arxiv_issues.values())
    if total_arxiv_issues == 0:
        report.append("✅ PASS: All arXiv URLs properly normalized")
    else:
        report.append(f"❌ FAIL: Found {total_arxiv_issues} arXiv normalization issues")
        report.append("")

        if arxiv_issues["versions_not_stripped"]:
            report.append(f"  Version numbers not stripped: {len(arxiv_issues['versions_not_stripped'])}")
            for url in arxiv_issues["versions_not_stripped"][:3]:
                report.append(f"    - {url}")
            if len(arxiv_issues["versions_not_stripped"]) > 3:
                report.append(f"    ... and {len(arxiv_issues['versions_not_stripped']) - 3} more")

        if arxiv_issues["html_not_normalized"]:
            report.append(f"  /html/ variants not normalized to /abs/: {len(arxiv_issues['html_not_normalized'])}")
            for url in arxiv_issues["html_not_normalized"][:3]:
                report.append(f"    - {url}")
            if len(arxiv_issues["html_not_normalized"]) > 3:
                report.append(f"    ... and {len(arxiv_issues['html_not_normalized']) - 3} more")

        if arxiv_issues["pdf_not_normalized"]:
            report.append(f"  /pdf/ variants not normalized to /abs/: {len(arxiv_issues['pdf_not_normalized'])}")
            for url in arxiv_issues["pdf_not_normalized"][:3]:
                report.append(f"    - {url}")
            if len(arxiv_issues["pdf_not_normalized"]) > 3:
                report.append(f"    ... and {len(arxiv_issues['pdf_not_normalized']) - 3} more")
    report.append("")

    # Test 3: Expected missing citations
    report.append("## Test 3: Expected Missing Citations")
    report.append("")

    # Academic URLs that are actually missing
    academic_missing = []
    for url in missing_urls:
        # Skip if it's a non-academic violation
        is_violation = any(url in [v["url"] for v in violations_list]
                          for violations_list in violations.values())
        if not is_violation:
            # Check if it's an arXiv issue
            is_arxiv_issue = any(url in issue_list
                                for issue_list in arxiv_issues.values())
            if not is_arxiv_issue:
                academic_missing.append(url)

    report.append(f"Truly missing academic citations: {len(academic_missing)}")
    report.append("")
    if academic_missing:
        report.append("These are legitimate missing citations that should be added to Zotero:")
        for url in academic_missing[:10]:
            report.append(f"  - {url}")
        if len(academic_missing) > 10:
            report.append(f"  ... and {len(academic_missing) - 10} more")
    report.append("")

    # Overall result
    report.append("=" * 80)
    report.append("## Overall Result")
    report.append("")

    if not violations and total_arxiv_issues == 0:
        report.append("✅ ALL TESTS PASSED")
        report.append(f"Expected missing citations: {len(academic_missing)}")
    else:
        report.append("❌ TESTS FAILED")
        report.append("")
        report.append("Issues found:")
        if violations:
            report.append(f"  - {sum(len(v) for v in violations.values())} non-academic links not filtered")
        if total_arxiv_issues > 0:
            report.append(f"  - {total_arxiv_issues} arXiv normalization failures")
        report.append("")
        report.append(f"After fixing these issues, expected missing citations: {len(academic_missing)}")

    report.append("=" * 80)

    return "\n".join(report)


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts/verify_citation_filtering.py <markdown_file> <conversion_log>")
        print("")
        print("Example:")
        print("  python scripts/verify_citation_filtering.py \\")
        print("    /path/to/paper.md \\")
        print("    /tmp/conversion.log")
        sys.exit(1)

    markdown_file = Path(sys.argv[1])
    log_file = Path(sys.argv[2])

    if not markdown_file.exists():
        print(f"Error: Markdown file not found: {markdown_file}")
        sys.exit(1)

    if not log_file.exists():
        print(f"Error: Log file not found: {log_file}")
        sys.exit(1)

    print(f"Verifying citation filtering for: {markdown_file.name}")
    print(f"Using conversion log: {log_file.name}")

    # Step 1: Extract and classify all links from markdown
    links = extract_all_links_from_markdown(markdown_file)
    classified = classify_links(links)

    # Step 2: Parse missing citations from conversion log
    missing_urls = parse_missing_citations_from_log(log_file)

    # Step 3: Check arXiv normalization
    arxiv_issues = check_arxiv_normalization(missing_urls)

    # Step 4: Verify exclusions
    violations = verify_exclusions(classified, missing_urls)

    # Step 5: Generate report
    report = generate_report(classified, missing_urls, arxiv_issues, violations)

    print("\n" + report)

    # Write report to file
    report_file = log_file.parent / f"{log_file.stem}-verification-report.txt"
    report_file.write_text(report)
    print(f"\nReport written to: {report_file}")

    # Exit with error code if tests failed
    total_issues = sum(len(v) for v in violations.values()) + sum(len(v) for v in arxiv_issues.values())
    if total_issues > 0:
        print(f"\n❌ {total_issues} issues found - tests FAILED")
        sys.exit(1)
    else:
        print("\n✅ All tests PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
