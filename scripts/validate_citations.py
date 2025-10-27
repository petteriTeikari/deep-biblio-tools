#!/usr/bin/env python3
"""Validate citations in markdown files using the unified citation extractor.

This script reuses the same logic that the converter uses to determine
what counts as an academic citation vs a regular hyperlink.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.converters.md_to_latex.citation_extractor_unified import (
    UnifiedCitationExtractor,
)

logger = logging.getLogger(__name__)


def categorize_non_academic_url(url: str) -> str:
    """Categorize non-academic URLs for reporting."""
    url_lower = url.lower()

    # Empty URLs
    if not url or url.strip() == "":
        return "BROKEN - Empty URL"

    # Project pages and repos
    if "github.io" in url_lower or (
        "github.com" in url_lower and "/tree/" not in url_lower
    ):
        return "PROBLEMATIC - Project page/repo"

    # Personal/university pages (but NOT publications)
    if (
        any(pattern in url_lower for pattern in ["~", "/people/", "/staff/"])
        and "publications" not in url_lower
    ):
        return "PROBLEMATIC - Personal website"

    # Amazon book links (should use proper publisher citation)
    if "amazon." in url_lower:
        return "PROBLEMATIC - Amazon link"

    # News sites
    if any(domain in url_lower for domain in ["bbc.com", "bloomberg.com"]):
        return "QUESTIONABLE - News article"

    # YouTube
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "QUESTIONABLE - YouTube video"

    # Company marketing sites
    if any(
        domain in url_lower
        for domain in ["mckinsey.com", "ibm.com/thought-leadership"]
    ):
        return "QUESTIONABLE - Company marketing"

    # Technical documentation (borderline)
    if any(
        domain in url_lower
        for domain in [
            "modelcontextprotocol.io",
            "developers.google.com",
            "developer.okta.com",
        ]
    ):
        return "QUESTIONABLE - Technical docs"

    # University repositories
    if "researchdiscovery" in url_lower or "esploro" in url_lower:
        return "QUESTIONABLE - University repository"

    # Grey literature (acceptable)
    # Government/EU documents
    if any(
        domain in url_lower
        for domain in [
            "eur-lex.europa.eu",
            "ec.europa.eu",
            "commission.europa.eu",
            "europarl.europa.eu",
        ]
    ):
        return "GREY_LIT - Government/EU docs"

    # Standards bodies
    if any(
        domain in url_lower
        for domain in ["gs1.org", "gs1.eu", "standardsmap.org"]
    ):
        return "GREY_LIT - Standards"

    # Research institutions
    if any(
        domain in url_lower for domain in ["nist.gov/publications", "nber.org"]
    ):
        return "GREY_LIT - Research institution"

    # Non-profit foundations
    if any(
        domain in url_lower
        for domain in ["ellenmacarthurfoundation.org", "wbcsd.org"]
    ):
        return "GREY_LIT - Non-profit"

    # Books from legitimate sources
    if "oreilly.com/library" in url_lower:
        return "GREY_LIT - Book"

    return "OTHER - Uncategorized"


def validate_markdown_file(filepath: Path) -> dict:
    """Validate citations in a markdown file.

    Args:
        filepath: Path to markdown file

    Returns:
        Dictionary with validation results
    """
    print(f"\n{'=' * 60}")
    print(f"Validating: {filepath.name}")
    print(f"{'=' * 60}")

    # Read content
    content = filepath.read_text(encoding="utf-8")

    # Extract citations using the unified extractor
    extractor = UnifiedCitationExtractor()
    citations = extractor.extract_citations(content)

    # Categorize
    academic = [c for c in citations if c.is_academic]
    non_academic = [c for c in citations if not c.is_academic]

    # Further categorize non-academic
    problematic = []
    questionable = []
    grey_lit = []
    other = []

    for citation in non_academic:
        category = categorize_non_academic_url(citation.url)

        if category.startswith("PROBLEMATIC"):
            problematic.append((citation, category))
        elif category.startswith("QUESTIONABLE"):
            questionable.append((citation, category))
        elif category.startswith("GREY_LIT"):
            grey_lit.append((citation, category))
        else:
            other.append((citation, category))

    # Print summary
    total = len(citations)
    print(f"\nTotal links found: {total}")
    print(f"  Academic citations: {len(academic)}")
    print(f"  Grey literature (acceptable): {len(grey_lit)}")
    print(f"  Questionable (review needed): {len(questionable)}")
    print(f"  Problematic (need fixing): {len(problematic)}")
    print(f"  Other: {len(other)}")

    # Report problematic
    if problematic:
        print(f"\nPROBLEMATIC Citations ({len(problematic)} need fixing):")
        for citation, category in problematic:
            print(
                f"\n  Line {citation.line}: [{citation.text}]({citation.url})"
            )
            print(f"  Issue: {category}")

    # Report questionable (first 5)
    if questionable:
        print(f"\nQUESTIONABLE Citations ({len(questionable)} - need review):")
        for citation, category in questionable[:5]:
            print(
                f"  Line {citation.line}: [{citation.text}]({citation.url}) - {category}"
            )
        if len(questionable) > 5:
            print(f"  ... and {len(questionable) - 5} more")

    if not problematic and not questionable:
        print("\nAll citations look good!")

    return {
        "total": total,
        "academic": len(academic),
        "grey_lit": len(grey_lit),
        "questionable": len(questionable),
        "problematic": len(problematic),
        "other": len(other),
    }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate citations in markdown files"
    )
    parser.add_argument(
        "files", nargs="+", type=Path, help="Markdown files to validate"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )

    # Validate each file
    results = {}
    for filepath in args.files:
        if not filepath.exists():
            print(f"ERROR: File not found: {filepath}")
            continue

        results[filepath.name] = validate_markdown_file(filepath)

    # Overall summary
    if len(results) > 1:
        print(f"\n{'=' * 60}")
        print("OVERALL SUMMARY")
        print(f"{'=' * 60}\n")

        total_problematic = sum(r["problematic"] for r in results.values())
        total_questionable = sum(r["questionable"] for r in results.values())
        total_citations = sum(r["total"] for r in results.values())

        print(f"Total citations across all files: {total_citations}")
        print(f"Problematic citations: {total_problematic}")
        print(f"Questionable citations: {total_questionable}")

        if total_problematic > 0:
            error_rate = (total_problematic / total_citations) * 100
            print(f"\nError rate: {error_rate:.1f}%")
        else:
            print("\nNo problematic citations found!")

        # Exit with error code if there are problems
        sys.exit(1 if total_problematic > 0 else 0)


if __name__ == "__main__":
    main()
