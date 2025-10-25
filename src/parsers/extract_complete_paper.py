#!/usr/bin/env python3
"""Extract complete content from ScienceDirect HTML paper with improved parsing"""

import re  # Banned - legacy code for simple pattern matching
import sys
import traceback

from bs4 import BeautifulSoup, NavigableString


def extract_text_recursive(element, depth=0):
    """Recursively extract text from HTML elements"""
    if element.name in ["script", "style", "noscript"]:
        return ""

    text_parts = []

    # Handle specific elements
    if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
        level = int(element.name[1])
        text_parts.append(
            "\n" + "#" * level + " " + element.get_text(strip=True) + "\n"
        )
    elif element.name == "p":
        text = element.get_text(strip=True)
        if text:
            text_parts.append(text + "\n")
    elif element.name == "li":
        text = element.get_text(strip=True)
        if text:
            text_parts.append("- " + text + "\n")
    elif element.name == "strong" or element.name == "b":
        text = element.get_text(strip=True)
        if text:
            text_parts.append("**" + text + "**")
    elif element.name == "em" or element.name == "i":
        text = element.get_text(strip=True)
        if text:
            text_parts.append("*" + text + "*")
    elif element.name == "table":
        caption = element.find("caption")
        if caption:
            text_parts.append(
                "\n**Table: " + caption.get_text(strip=True) + "**\n"
            )
    elif element.name == "figure":
        figcaption = element.find("figcaption")
        if figcaption:
            text_parts.append(
                "\n**Figure: " + figcaption.get_text(strip=True) + "**\n"
            )
    else:
        # Process children
        for child in element.children:
            if isinstance(child, NavigableString):
                text = str(child).strip()
                if text:
                    text_parts.append(text)
            else:
                child_text = extract_text_recursive(child, depth + 1)
                if child_text:
                    text_parts.append(child_text)

    return " ".join(text_parts)


def parse_sciencedirect_html(html_path):
    """Parse ScienceDirect HTML and extract paper content"""

    with open(html_path, encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    # Remove unwanted elements
    for element in soup.find_all(
        ["script", "style", "nav", "header", "footer"]
    ):
        element.decompose()

    # Extract metadata
    output = []

    # Title
    title = soup.find("meta", {"name": "citation_title"})
    if title:
        output.append(f"# {title.get('content', '')}\n")

    # Authors
    authors = []
    for author in soup.find_all("meta", {"name": "citation_author"}):
        authors.append(author.get("content", ""))
    if authors:
        output.append(f"**Authors:** {', '.join(authors)}\n")

    # Journal info
    journal = soup.find("meta", {"name": "citation_journal_title"})
    if journal:
        output.append(f"**Journal:** {journal.get('content', '')}")

    year = soup.find("meta", {"name": "citation_publication_date"})
    if year:
        output.append(f"**Year:** {year.get('content', '')[:4]}")

    volume = soup.find("meta", {"name": "citation_volume"})
    if volume:
        output.append(f"**Volume:** {volume.get('content', '')}")

    doi = soup.find("meta", {"name": "citation_doi"})
    if doi:
        output.append(f"**DOI:** {doi.get('content', '')}")

    output.append("\n")

    # Abstract
    abstract = soup.find("meta", {"name": "citation_abstract"})
    if abstract:
        output.append("## Abstract\n")
        output.append(abstract.get("content", "") + "\n\n")

    # Main content - look for article body
    main_content = None
    for selector in [
        "article",
        "div.article-content",
        "main",
        "div#body",
        "div.Body",
    ]:
        main_content = soup.select_one(selector)
        if main_content:
            break

    if main_content:
        # Extract all text content
        content_text = extract_text_recursive(main_content)

        # Clean up the text
        lines = content_text.split("\n")
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            # Skip empty lines and download links
            if not line or "Download:" in line or "Download high-res" in line:
                continue
            # Skip navigation elements
            if any(
                skip in line
                for skip in [
                    "Previous article",
                    "Next article",
                    "View PDF",
                    "Sign in",
                ]
            ):
                continue
            cleaned_lines.append(line)

        output.extend(cleaned_lines)

    # References section
    output.append("\n\n## References\n")

    # Look for bibliography
    bib_section = soup.find(
        "section", {"id": re.compile("bibliography|references", re.I)}
    )
    if not bib_section:
        bib_section = soup.find(
            "div", {"class": re.compile("bibliography|references", re.I)}
        )

    if bib_section:
        ref_count = 0
        for ref_item in bib_section.find_all(["li", "div", "p"]):
            ref_text = ref_item.get_text(strip=True)
            if ref_text and len(ref_text) > 50:
                ref_count += 1
                output.append(f"\n[{ref_count}] {ref_text}")

    return "\n".join(output)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_complete_paper.py <html_file>")
        sys.exit(1)

    try:
        content = parse_sciencedirect_html(sys.argv[1])
        print(content)
    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()
