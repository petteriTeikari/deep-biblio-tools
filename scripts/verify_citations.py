#!/usr/bin/env python3
"""
Citation verification script for markdown files.
Extracts all citations and checks for common issues.
"""

import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests


def extract_citations(file_path: str) -> list[tuple[int, str, str, str]]:
    """
    Extract all citations from markdown file.
    Returns list of (line_num, full_match, text, url) tuples.
    """
    citations = []
    with open(file_path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            # Find all [text](url) patterns
            start = 0
            while True:
                bracket_start = line.find("[", start)
                if bracket_start == -1:
                    break

                bracket_end = line.find("]", bracket_start)
                if bracket_end == -1:
                    break

                paren_start = line.find("(", bracket_end)
                if paren_start != bracket_end + 1:
                    start = bracket_end + 1
                    continue

                paren_end = line.find(")", paren_start)
                if paren_end == -1:
                    start = bracket_end + 1
                    continue

                text = line[bracket_start + 1 : bracket_end]
                url = line[paren_start + 1 : paren_end]

                # Only include URLs (skip internal links)
                if url.startswith("http://") or url.startswith("https://"):
                    full_match = line[bracket_start : paren_end + 1]
                    citations.append((line_num, full_match, text, url))

                start = paren_end + 1

    return citations


def is_academic_citation(text: str) -> bool:
    """Check if citation text looks like academic format."""
    # Academic: "Author (Year)" or "Author et al., Year"
    # Look for year pattern (4 digits)
    return any(c.isdigit() for c in text) and (
        "(" in text or "," in text or "et al" in text.lower()
    )


def check_url_format(url: str) -> list[str]:
    """Check URL for common formatting issues."""
    issues = []

    # Check for truncation indicators
    if url.endswith("...") or "..." in url:
        issues.append("URL appears truncated (contains '...')")

    # Check for spaces (should be encoded)
    if " " in url:
        issues.append("URL contains unencoded spaces")

    # Check for incomplete URLs
    parsed = urlparse(url)
    if not parsed.scheme:
        issues.append("Missing URL scheme (http/https)")
    if not parsed.netloc:
        issues.append("Missing domain name")

    # Check for common malformations
    if url.count("http://") > 1 or url.count("https://") > 1:
        issues.append("URL contains multiple protocols")

    return issues


def check_author_name(text: str) -> list[str]:
    """Check for problematic author names."""
    issues = []

    # Organization names that shouldn't be authors
    org_indicators = [
        "OECD",
        "UN",
        "WHO",
        "UNESCO",
        "UNECE",
        "EPA",
        "European Commission",
        "European Parliament",
        "BBC",
        "Bloomberg",
        "Fashion United",
        "Fashion Revolution",
        "H&M Foundation",
        "WBCSD",
        "GS1",
        "ITC",
        "Anthropic",
        "Google",
        "OpenAI",
        "Microsoft",
        "Web page",
        "Website",
        "Blog post",
        "News article",
    ]

    for indicator in org_indicators:
        if indicator.lower() in text.lower():
            issues.append(
                f"Author field contains organization name: '{indicator}'"
            )
            break

    # Check for generic placeholders
    if "Unknown" in text or "Anonymous" in text:
        issues.append("Author is Unknown/Anonymous")

    # Check for missing author (just year)
    if text.strip().startswith("(") and text.strip().endswith(")"):
        if any(c.isdigit() for c in text):
            issues.append("Missing author name (only year present)")

    return issues


def verify_url_accessible(url: str) -> tuple[bool, str]:
    """Check if URL is accessible (with timeout)."""
    try:
        # Use HEAD request first (faster)
        response = requests.head(url, timeout=5, allow_redirects=True)
        if response.status_code < 400:
            return True, "OK"
        else:
            return False, f"HTTP {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "Timeout (5s)"
    except requests.exceptions.ConnectionError:
        return False, "Connection failed"
    except requests.exceptions.RequestException as e:
        return False, f"Request error: {str(e)[:50]}"
    except Exception as e:
        return False, f"Error: {str(e)[:50]}"


def main():
    if len(sys.argv) != 2:
        print("Usage: python verify_citations.py <markdown_file>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    print(f"Extracting citations from: {file_path}")
    citations = extract_citations(file_path)
    print(f"Found {len(citations)} citations\n")

    # Group issues by category
    broken_urls = []
    author_issues = []
    url_format_issues = []
    non_academic_links = []

    print("Verifying citations (this may take a while)...\n")

    for line_num, full_match, text, url in citations:
        # Check if it's an academic citation
        is_academic = is_academic_citation(text)

        # Check URL format
        format_issues = check_url_format(url)
        if format_issues:
            url_format_issues.append(
                {
                    "line": line_num,
                    "citation": full_match,
                    "text": text,
                    "url": url,
                    "issues": format_issues,
                }
            )

        # Check author name for academic citations
        if is_academic:
            author_probs = check_author_name(text)
            if author_probs:
                author_issues.append(
                    {
                        "line": line_num,
                        "citation": full_match,
                        "text": text,
                        "url": url,
                        "issues": author_probs,
                    }
                )
        else:
            # Non-academic link - check if it should be a footnote
            if any(
                domain in url.lower()
                for domain in ["blog", "medium.com", "news", "article"]
            ):
                non_academic_links.append(
                    {
                        "line": line_num,
                        "citation": full_match,
                        "text": text,
                        "url": url,
                    }
                )

        # Check URL accessibility (only if no format issues)
        if not format_issues:
            accessible, status = verify_url_accessible(url)
            if not accessible:
                broken_urls.append(
                    {
                        "line": line_num,
                        "citation": full_match,
                        "text": text,
                        "url": url,
                        "status": status,
                    }
                )

            # Rate limiting
            time.sleep(0.5)

        # Progress indicator
        if line_num % 10 == 0:
            print(f"Checked {line_num} citations...")

    # Print summary
    print("\n" + "=" * 80)
    print("CITATION VERIFICATION SUMMARY")
    print("=" * 80)

    print(f"\nTotal citations found: {len(citations)}")
    print(f"Broken/inaccessible URLs: {len(broken_urls)}")
    print(f"Author name issues: {len(author_issues)}")
    print(f"URL format issues: {len(url_format_issues)}")
    print(
        f"Non-academic links (potential footnotes): {len(non_academic_links)}"
    )

    # Detailed reports
    if broken_urls:
        print("\n" + "=" * 80)
        print("BROKEN OR INACCESSIBLE URLs")
        print("=" * 80)
        for item in broken_urls:
            print(f"\nLine {item['line']}:")
            print(f"  Citation: {item['citation']}")
            print(f"  Status: {item['status']}")
            print(f"  URL: {item['url']}")

    if author_issues:
        print("\n" + "=" * 80)
        print("AUTHOR NAME ISSUES")
        print("=" * 80)
        for item in author_issues:
            print(f"\nLine {item['line']}:")
            print(f"  Citation: {item['citation']}")
            print("  Issues:")
            for issue in item["issues"]:
                print(f"    - {issue}")

    if url_format_issues:
        print("\n" + "=" * 80)
        print("URL FORMAT ISSUES")
        print("=" * 80)
        for item in url_format_issues:
            print(f"\nLine {item['line']}:")
            print(f"  Citation: {item['citation']}")
            print("  Issues:")
            for issue in item["issues"]:
                print(f"    - {issue}")

    if non_academic_links:
        print("\n" + "=" * 80)
        print("NON-ACADEMIC LINKS (Consider converting to footnotes)")
        print("=" * 80)
        for item in non_academic_links:
            print(f"\nLine {item['line']}:")
            print(f"  Citation: {item['citation']}")
            print(f"  URL: {item['url']}")

    # Generate markdown report
    report_path = "/home/petteri/Dropbox/github-personal/deep-biblio-tools/docs/planning/CITATION-VERIFICATION-REPORT-2025-10-31.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Citation Verification Report\n\n")
        f.write("**Generated:** 2025-10-31\n")
        f.write(f"**Source File:** `{file_path}`\n\n")

        f.write("## Summary\n\n")
        f.write(f"- Total citations: {len(citations)}\n")
        f.write(f"- Broken/inaccessible URLs: {len(broken_urls)}\n")
        f.write(f"- Author name issues: {len(author_issues)}\n")
        f.write(f"- URL format issues: {len(url_format_issues)}\n")
        f.write(f"- Non-academic links: {len(non_academic_links)}\n\n")

        if broken_urls:
            f.write("## Broken or Inaccessible URLs\n\n")
            for item in broken_urls:
                f.write(f"### Line {item['line']}\n\n")
                f.write(f"**Citation:** `{item['citation']}`\n\n")
                f.write(f"**Status:** {item['status']}\n\n")
                f.write(f"**URL:** {item['url']}\n\n")
                f.write(
                    "**Recommendation:** Verify URL and update if necessary\n\n"
                )
                f.write("---\n\n")

        if author_issues:
            f.write("## Author Name Issues\n\n")
            for item in author_issues:
                f.write(f"### Line {item['line']}\n\n")
                f.write(f"**Citation:** `{item['citation']}`\n\n")
                f.write("**Issues:**\n")
                for issue in item["issues"]:
                    f.write(f"- {issue}\n")
                f.write("\n**Recommendation:** ")
                if "organization" in item["issues"][0].lower():
                    f.write("Convert to footnote or use proper author name\n\n")
                else:
                    f.write("Verify author name from original source\n\n")
                f.write("---\n\n")

        if url_format_issues:
            f.write("## URL Format Issues\n\n")
            for item in url_format_issues:
                f.write(f"### Line {item['line']}\n\n")
                f.write(f"**Citation:** `{item['citation']}`\n\n")
                f.write("**Issues:**\n")
                for issue in item["issues"]:
                    f.write(f"- {issue}\n")
                f.write("\n**Recommendation:** Fix URL formatting\n\n")
                f.write("---\n\n")

        if non_academic_links:
            f.write("## Non-Academic Links (Consider Footnotes)\n\n")
            for item in non_academic_links:
                f.write(f"### Line {item['line']}\n\n")
                f.write(f"**Citation:** `{item['citation']}`\n\n")
                f.write(
                    "**Recommendation:** Consider converting to footnote\n\n"
                )
                f.write("---\n\n")

    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
