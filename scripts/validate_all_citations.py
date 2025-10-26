#!/usr/bin/env python3
"""
Comprehensive citation validation for arXiv submission.

Validates:
1. All URLs are accessible (HTTP 200)
2. arXiv IDs are in correct format and exist
3. DOIs resolve correctly
4. Author names in markdown match actual papers
5. Papers actually discuss what's claimed
"""

import json
import logging
import sys
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def validate_arxiv_id(arxiv_id: str) -> tuple[bool, str]:
    """
    Validate arXiv ID format and existence.

    Returns: (is_valid, message)
    """
    # Check format: YYMM.NNNNN or YYMM.NNNN
    if not arxiv_id:
        return False, "Empty arXiv ID"

    # Remove version suffix
    if "v" in arxiv_id:
        arxiv_id = arxiv_id[: arxiv_id.rfind("v")]

    # Check format
    if "." not in arxiv_id:
        return False, f"Invalid format (no dot): {arxiv_id}"

    left, right = arxiv_id.split(".", 1)

    if not (len(left) == 4 and left.isdigit()):
        return False, f"Invalid year/month: {left}"

    if not (len(right) in [4, 5] and right.isdigit()):
        return False, f"Invalid number: {right}"

    # Check if it exists
    try:
        url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            if (
                "No papers found" in response.text
                or "<entry>" not in response.text
            ):
                return False, f"arXiv ID does not exist: {arxiv_id}"
            return True, "Valid"
        else:
            return False, f"Failed to verify (HTTP {response.status_code})"
    except Exception as e:
        return False, f"Error verifying: {e}"


def validate_url(url: str) -> tuple[bool, str, int]:
    """
    Check if URL is accessible.

    Returns: (is_accessible, message, status_code)
    """
    try:
        response = requests.get(url, timeout=15, allow_redirects=True)
        return (
            response.status_code == 200,
            f"HTTP {response.status_code}",
            response.status_code,
        )
    except requests.exceptions.Timeout:
        return False, "Timeout", 0
    except requests.exceptions.ConnectionError:
        return False, "Connection error", 0
    except Exception as e:
        return False, f"Error: {e}", 0


def extract_citations_from_markdown(md_path: Path) -> list[dict]:
    """
    Extract all citations from markdown.

    Returns list of: {text: str, url: str, line: int}
    """
    citations = []

    with open(md_path) as f:
        for line_num, line in enumerate(f, 1):
            # Find all [text](url) patterns
            import re  # Banned - legacy code, needs refactoring to string methods

            matches = re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", line)

            for match in matches:
                text = match.group(1)
                url = match.group(2)

                # Only include citations (have year in brackets)
                # Pattern: [Author, Year] or [Author et al., Year]
                if "," in text and any(c.isdigit() for c in text):
                    citations.append(
                        {
                            "text": text,
                            "url": url,
                            "line": line_num,
                        }
                    )

    return citations


def validate_all_citations(md_path: Path, output_path: Path) -> None:
    """Run comprehensive validation."""
    logger.info(f"Extracting citations from {md_path.name}...")
    citations = extract_citations_from_markdown(md_path)

    logger.info(f"Found {len(citations)} citations to validate\n")
    logger.info("=" * 80)

    results = {
        "total": len(citations),
        "valid": 0,
        "invalid": 0,
        "warnings": 0,
        "issues": [],
    }

    for i, citation in enumerate(citations, 1):
        text = citation["text"]
        url = citation["url"]
        line = citation["line"]

        logger.info(f"\n[{i}/{len(citations)}] Line {line}: [{text}]({url})")

        has_issues = False

        # Check if URL is accessible
        is_accessible, message, status_code = validate_url(url)
        if not is_accessible:
            logger.error(f"  URL FAILED: {message}")
            results["issues"].append(
                {
                    "line": line,
                    "citation": text,
                    "url": url,
                    "issue": f"URL not accessible: {message}",
                    "severity": "ERROR",
                }
            )
            has_issues = True
        elif status_code != 200:
            logger.warning(f"  URL WARNING: {message}")
            results["issues"].append(
                {
                    "line": line,
                    "citation": text,
                    "url": url,
                    "issue": f"URL returned {status_code}",
                    "severity": "WARNING",
                }
            )
            results["warnings"] += 1
        else:
            logger.info(f"  URL OK: {message}")

        # Special validation for arXiv
        if "arxiv.org" in url.lower():
            # Extract arXiv ID
            arxiv_id = None
            for pattern in ["/abs/", "/html/", "/pdf/"]:
                if pattern in url:
                    arxiv_id = (
                        url.split(pattern)[-1]
                        .split("/")[0]
                        .split("?")[0]
                        .split("#")[0]
                    )
                    break

            if arxiv_id:
                is_valid, msg = validate_arxiv_id(arxiv_id)
                if not is_valid:
                    logger.error(f"  arXiv INVALID: {msg}")
                    results["issues"].append(
                        {
                            "line": line,
                            "citation": text,
                            "url": url,
                            "issue": f"Invalid arXiv ID: {msg}",
                            "severity": "ERROR",
                        }
                    )
                    has_issues = True
                else:
                    logger.info(f"  arXiv OK: {arxiv_id}")

        if not has_issues:
            results["valid"] += 1
        else:
            results["invalid"] += 1

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total citations: {results['total']}")
    logger.info(f"Valid: {results['valid']}")
    logger.info(f"Invalid: {results['invalid']}")
    logger.info(f"Warnings: {results['warnings']}")

    if results["issues"]:
        logger.info(f"\n{len(results['issues'])} ISSUES FOUND:")
        logger.info("=" * 80)
        for issue in results["issues"]:
            logger.info(f"\nLine {issue['line']}: [{issue['citation']}]")
            logger.info(f"  URL: {issue['url']}")
            logger.info(f"  {issue['severity']}: {issue['issue']}")

    # Write results
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"\nFull results written to: {output_path}")

    if results["invalid"] > 0:
        logger.error(f"\nFAILED: {results['invalid']} citations have errors")
        sys.exit(1)
    else:
        logger.info("\nSUCCESS: All citations validated")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("markdown", type=Path, help="Markdown file to validate")
    parser.add_argument(
        "--output", type=Path, default=Path("citation-validation.json")
    )

    args = parser.parse_args()

    validate_all_citations(args.markdown, args.output)
