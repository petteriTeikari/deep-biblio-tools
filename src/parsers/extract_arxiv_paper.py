#!/usr/bin/env python3
"""Extract full content from arXiv HTML paper"""

import re  # Banned - legacy code for simple pattern matching
import sys
import traceback

from bs4 import BeautifulSoup


def clean_text(text):
    """Clean extracted text"""
    if not text:
        return ""
    # Remove multiple spaces and newlines
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_full_content(html_path):
    """Extract complete paper content from arXiv HTML"""

    with open(html_path, encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    # Extract metadata
    metadata = {}

    # Title - from meta tag or h1
    title_meta = soup.find("meta", {"name": "citation_title"})
    if title_meta:
        metadata["title"] = title_meta.get("content", "")
    else:
        title_elem = soup.find("h1", class_="title") or soup.find("h1")
        metadata["title"] = (
            title_elem.get_text(strip=True) if title_elem else "Unknown Title"
        )

    # Authors from meta tags
    metadata["authors"] = []
    author_metas = soup.find_all("meta", {"name": "citation_author"})
    for author in author_metas:
        metadata["authors"].append(author.get("content", ""))

    # If no authors in meta, try from page content
    if not metadata["authors"]:
        authors_div = soup.find("div", class_="authors")
        if authors_div:
            # Extract author names from links
            author_links = authors_div.find_all("a")
            for link in author_links:
                name = link.get_text(strip=True)
                if name and not name.startswith("("):
                    metadata["authors"].append(name)

    # Date and arXiv ID
    date_meta = soup.find("meta", {"name": "citation_date"})
    metadata["date"] = date_meta.get("content", "") if date_meta else ""

    arxiv_meta = soup.find("meta", {"name": "citation_arxiv_id"})
    metadata["arxiv_id"] = arxiv_meta.get("content", "") if arxiv_meta else ""

    # Extract abstract
    abstract = ""
    abstract_meta = soup.find("meta", {"name": "citation_abstract"})
    if abstract_meta:
        abstract = abstract_meta.get("content", "")

    if not abstract:
        # Try from page content
        abstract_block = soup.find("blockquote", class_="abstract")
        if abstract_block:
            abstract = abstract_block.get_text(strip=True)
            # Remove "Abstract:" prefix if present
            if abstract.startswith("Abstract:"):
                abstract = abstract[9:].strip()

    # Extract subjects/categories
    subjects = []
    subjects_div = soup.find("div", class_="subjects")
    if subjects_div:
        subjects_text = subjects_div.get_text(strip=True)
        if subjects_text:
            subjects = [s.strip() for s in subjects_text.split(";")]

    # Extract main content (if available - usually arXiv only has abstract)
    content_sections = []

    # Look for any additional content blocks
    content_div = soup.find("div", class_="content") or soup.find(
        "div", id="content"
    )
    if content_div:
        # Find all paragraphs and sections
        sections = content_div.find_all(["section", "div", "p"])
        for section in sections:
            text = clean_text(section.get_text())
            if text and len(text) > 50:  # Skip very short text
                content_sections.append(text)

    # Extract comments if any
    comments = ""
    comments_td = soup.find("td", class_="tablecell comments")
    if comments_td:
        comments = comments_td.get_text(strip=True)

    # Create output structure
    output = {
        "metadata": metadata,
        "abstract": abstract,
        "subjects": subjects,
        "comments": comments,
        "content_sections": content_sections,
    }

    return output


def format_as_markdown(data):
    """Format extracted data as markdown"""
    md_lines = []

    # Title and metadata
    md_lines.append(f"# {data['metadata']['title']}")
    md_lines.append("")

    if data["metadata"]["authors"]:
        md_lines.append(
            f"**Authors:** {', '.join(data['metadata']['authors'])}"
        )

    if data["metadata"]["arxiv_id"]:
        md_lines.append(f"**arXiv ID:** {data['metadata']['arxiv_id']}")

    if data["metadata"]["date"]:
        md_lines.append(f"**Date:** {data['metadata']['date']}")

    if data["subjects"]:
        md_lines.append(f"**Subjects:** {'; '.join(data['subjects'])}")

    md_lines.append("")

    # Abstract
    if data["abstract"]:
        md_lines.append("## Abstract")
        md_lines.append("")
        md_lines.append(data["abstract"])
        md_lines.append("")

    # Comments
    if data["comments"]:
        md_lines.append("## Comments")
        md_lines.append("")
        md_lines.append(data["comments"])
        md_lines.append("")

    # Additional content
    if data["content_sections"]:
        md_lines.append("## Additional Content")
        md_lines.append("")
        for section in data["content_sections"]:
            md_lines.append(section)
            md_lines.append("")

    return "\n".join(md_lines)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_arxiv_paper.py <html_file>")
        sys.exit(1)

    try:
        data = extract_full_content(sys.argv[1])
        markdown = format_as_markdown(data)
        print(markdown)
    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()
