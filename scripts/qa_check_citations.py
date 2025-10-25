#!/usr/bin/env python3
"""QA script to check if all citations are properly resolved in the PDF."""

# import re  # Banned - using string methods instead
import subprocess
from pathlib import Path


def extract_citations_from_pdf(pdf_path):
    """Extract text from PDF and analyze citations."""
    # Extract text from PDF
    try:
        result = subprocess.run(
            ["pdftotext", str(pdf_path), "-"],
            capture_output=True,
            text=True,
            check=True,
        )
        text = result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error extracting text from PDF: {e}")
        return None

    # Find all citation patterns
    # Pattern for resolved citations: (Author, Year) or Author (Year)
    # Pattern for unresolved citations: (?)

    resolved_citations = []
    author_year_citations = []
    unresolved_citations = []

    # Count unresolved citations (?)
    unresolved_citations = text.split("(?)")
    unresolved_count = len(unresolved_citations) - 1

    # Find resolved citations - look for patterns like (Author, Year)
    # This is a simplified approach using string methods
    lines = text.split("\n")
    for line in lines:
        # Find all parentheses pairs
        pos = 0
        while True:
            start = line.find("(", pos)
            if start == -1:
                break
            end = line.find(")", start)
            if end == -1:
                break

            content = line[start + 1 : end]

            # Check if it looks like a citation
            if "," in content:
                parts = content.split(",")
                if len(parts) == 2:
                    author_part = parts[0].strip()
                    year_part = parts[1].strip()

                    # Check if year part contains a 4-digit year
                    has_year = False
                    for i in range(len(year_part) - 3):
                        if year_part[i : i + 4].isdigit():
                            has_year = True
                            break

                    # Check if author part looks like an author (contains letters)
                    has_author = any(c.isalpha() for c in author_part)

                    if has_year and has_author:
                        resolved_citations.append(f"({content})")

            pos = end + 1

        # Find Author (Year) patterns
        words = line.split()
        for i in range(len(words) - 1):
            word = words[i]
            next_word = words[i + 1] if i + 1 < len(words) else ""

            # Check if current word starts with capital and next contains (Year)
            if (
                word
                and word[0].isupper()
                and "(" in next_word
                and ")" in next_word
            ):
                # Extract year from parentheses
                paren_start = next_word.find("(")
                paren_end = next_word.find(")")
                if paren_start != -1 and paren_end != -1:
                    year_content = next_word[paren_start + 1 : paren_end]
                    # Check if it's a 4-digit year
                    if len(year_content) >= 4:
                        for j in range(len(year_content) - 3):
                            if year_content[j : j + 4].isdigit():
                                author_year_citations.append(
                                    f"{word} {next_word}"
                                )
                                break

    unresolved_citations = ["(?)" for _ in range(unresolved_count)]

    return {
        "resolved": len(resolved_citations) + len(author_year_citations),
        "unresolved": len(unresolved_citations),
        "total": len(resolved_citations)
        + len(author_year_citations)
        + len(unresolved_citations),
        "sample_resolved": resolved_citations[:10],
        "sample_unresolved": unresolved_citations[:10],
    }


def main():
    pdf_path = Path("uadReview/main.pdf")

    # Try to find the PDF in current directory if not found
    if not pdf_path.exists():
        pdf_path = Path("main.pdf")

    if not pdf_path.exists():
        print(f"Error: PDF not found at {pdf_path}")
        return

    print("=== Citation Quality Check ===\n")

    results = extract_citations_from_pdf(pdf_path)

    if results is None:
        return

    print(f"Total citations found: {results['total']}")
    print(f"Resolved citations: {results['resolved']}")
    print(f"Unresolved citations (?): {results['unresolved']}")

    if results["resolved"] > 0:
        success_rate = (results["resolved"] / results["total"]) * 100
        print(f"\nSuccess rate: {success_rate:.1f}%")

    if results["sample_resolved"]:
        print("\nSample resolved citations:")
        for cite in results["sample_resolved"]:
            print(f"  - {cite}")

    if results["unresolved"] > 0:
        print(
            f"\nWARNING: {results['unresolved']} citations are still unresolved!"
        )
        if results["sample_unresolved"]:
            print("Sample unresolved citations:")
            for cite in results["sample_unresolved"]:
                print(f"  - {cite}")
    else:
        print("\nAll citations are properly resolved!")

    # Check PDF size and page count
    pdf_size = pdf_path.stat().st_size / 1024 / 1024  # MB
    print(f"\nPDF size: {pdf_size:.2f} MB")

    # Get page count
    try:
        result = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        for line in result.stdout.split("\n"):
            if "Pages:" in line:
                pages = line.split(":")[1].strip()
                print(f"Page count: {pages}")
    except subprocess.CalledProcessError:
        pass


if __name__ == "__main__":
    main()
