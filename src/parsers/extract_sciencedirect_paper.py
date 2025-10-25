#!/usr/bin/env python3
"""Extract full content from ScienceDirect HTML paper"""

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
    # Remove download links
    text = re.sub(r"Download:Download.*?(?=\s|$)", "", text)
    return text.strip()


def extract_citations_to_author_year(text):
    """Convert numeric citations to author-year format"""
    # This is a placeholder - would need reference mapping
    return text


def extract_full_content(html_path):
    """Extract complete paper content from ScienceDirect HTML"""

    with open(html_path, encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()

    # Extract metadata from meta tags
    metadata = {}

    # Title
    title_meta = soup.find("meta", {"name": "citation_title"})
    if title_meta:
        metadata["title"] = title_meta.get("content", "")
    else:
        # Try alternative title extraction
        title_elem = soup.find("h1", class_="title-text") or soup.find("h1")
        metadata["title"] = (
            title_elem.get_text(strip=True) if title_elem else "Unknown Title"
        )

    # Authors
    metadata["authors"] = []
    author_metas = soup.find_all("meta", {"name": "citation_author"})
    for author in author_metas:
        metadata["authors"].append(author.get("content", ""))

    # If no authors in meta, try alternative
    if not metadata["authors"]:
        author_group = soup.find("div", class_="author-group")
        if author_group:
            authors = author_group.find_all("span", class_="given-name")
            for author in authors:
                metadata["authors"].append(author.get_text(strip=True))

    # Journal and year
    journal_meta = soup.find("meta", {"name": "citation_journal_title"})
    metadata["journal"] = (
        journal_meta.get("content", "") if journal_meta else ""
    )

    year_meta = soup.find("meta", {"name": "citation_publication_date"})
    metadata["year"] = year_meta.get("content", "")[:4] if year_meta else ""

    # Volume and pages
    volume_meta = soup.find("meta", {"name": "citation_volume"})
    metadata["volume"] = volume_meta.get("content", "") if volume_meta else ""

    pages_meta = soup.find("meta", {"name": "citation_firstpage"})
    metadata["pages"] = pages_meta.get("content", "") if pages_meta else ""

    # DOI
    doi_meta = soup.find("meta", {"name": "citation_doi"})
    metadata["doi"] = doi_meta.get("content", "") if doi_meta else ""

    # Extract abstract
    abstract_meta = soup.find("meta", {"name": "citation_abstract"})
    abstract = abstract_meta.get("content", "") if abstract_meta else ""

    if not abstract:
        # Try alternative abstract extraction
        abstract_div = soup.find("div", class_="abstract") or soup.find(
            "section", {"id": "abstract"}
        )
        if abstract_div:
            abstract = abstract_div.get_text(strip=True)

    # Extract main content sections
    sections = []

    # Look for article body
    article_elem = (
        soup.find("article")
        or soup.find("div", {"class": "article-content"})
        or soup.find("main")
    )

    if article_elem:
        # Find all sections
        section_elements = article_elem.find_all(
            ["section", "div"], recursive=True
        )

        for section in section_elements:
            # Skip if it's a reference section
            if (
                "reference" in str(section.get("class", [])).lower()
                or "bibliography" in str(section.get("id", "")).lower()
            ):
                continue

            # Get section title
            title_elem = section.find(["h2", "h3", "h4"])
            if not title_elem:
                continue

            section_title = clean_text(title_elem.get_text())

            # Get section content
            content_parts = []

            # Get paragraphs
            paragraphs = section.find_all("p", recursive=False)
            for p in paragraphs:
                text = clean_text(p.get_text())
                if text and len(text) > 20:
                    content_parts.append(text)

            # Get lists
            lists = section.find_all(["ul", "ol"], recursive=False)
            for lst in lists:
                items = lst.find_all("li")
                for item in items:
                    text = clean_text(item.get_text())
                    if text:
                        content_parts.append(f"• {text}")

            # Get tables
            tables = section.find_all("table", recursive=False)
            for table in tables:
                caption = table.find("caption")
                if caption:
                    content_parts.append(
                        f"\n**Table:** {clean_text(caption.get_text())}\n"
                    )

            # Get figures
            figures = section.find_all("figure", recursive=False)
            for figure in figures:
                caption = figure.find("figcaption")
                if caption:
                    content_parts.append(
                        f"\n**Figure:** {clean_text(caption.get_text())}\n"
                    )

            if content_parts:
                sections.append(
                    {"title": section_title, "content": content_parts}
                )

    # Extract references
    references = []

    # Look for reference section
    ref_section = soup.find(
        "section", {"id": re.compile("bibliography|references", re.I)}
    )
    if not ref_section:
        ref_section = soup.find(
            "div", {"class": re.compile("bibliography|references", re.I)}
        )

    if ref_section:
        ref_items = ref_section.find_all(["li", "div", "p"])
        for ref in ref_items:
            ref_text = clean_text(ref.get_text())
            # Filter out very short or irrelevant text
            if (
                ref_text
                and len(ref_text) > 50
                and not ref_text.startswith("Download")
            ):
                references.append(ref_text)

    # Create output structure
    output = {
        "metadata": metadata,
        "abstract": abstract,
        "sections": sections,
        "references": references,
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

    if data["metadata"]["journal"]:
        md_lines.append(f"**Journal:** {data['metadata']['journal']}")

    if data["metadata"]["year"]:
        md_lines.append(f"**Year:** {data['metadata']['year']}")

    if data["metadata"]["volume"]:
        md_lines.append(f"**Volume:** {data['metadata']['volume']}")

    if data["metadata"]["doi"]:
        md_lines.append(f"**DOI:** {data['metadata']['doi']}")

    md_lines.append("")

    # Abstract
    if data["abstract"]:
        md_lines.append("## Abstract")
        md_lines.append("")
        md_lines.append(data["abstract"])
        md_lines.append("")

    # Main content
    for section in data["sections"]:
        md_lines.append(f"## {section['title']}")
        md_lines.append("")
        for paragraph in section["content"]:
            md_lines.append(paragraph)
            md_lines.append("")

    # References
    if data["references"]:
        md_lines.append("## References")
        md_lines.append("")
        for i, ref in enumerate(data["references"], 1):
            md_lines.append(f"{i}. {ref}")
            md_lines.append("")

    return "\n".join(md_lines)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_sciencedirect_paper.py <html_file>")
        sys.exit(1)

    try:
        data = extract_full_content(sys.argv[1])
        markdown = format_as_markdown(data)
        print(markdown)
    except Exception as e:
        print(f"Error: {str(e)}")
        traceback.print_exc()
