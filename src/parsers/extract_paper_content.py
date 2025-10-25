#!/usr/bin/env python3
"""Extract content from ScienceDirect HTML paper"""

import sys

from bs4 import BeautifulSoup


def extract_paper_content(html_path):
    """Extract structured content from ScienceDirect HTML"""

    with open(html_path, encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    # Extract metadata
    title = soup.find("meta", {"name": "citation_title"})
    title_text = title.get("content", "") if title else ""

    authors = []
    author_tags = soup.find_all("meta", {"name": "citation_author"})
    for author in author_tags:
        authors.append(author.get("content", ""))

    journal = soup.find("meta", {"name": "citation_journal_title"})
    journal_text = journal.get("content", "") if journal else ""

    year = soup.find("meta", {"name": "citation_publication_date"})
    year_text = year.get("content", "")[:4] if year else ""

    abstract = soup.find("meta", {"name": "citation_abstract"})
    abstract_text = abstract.get("content", "") if abstract else ""

    # Extract main content
    content = []

    # Try to find article body
    article_body = (
        soup.find("div", {"class": "Body"})
        or soup.find("div", {"id": "body"})
        or soup.find("article")
    )

    if article_body:
        # Extract sections
        sections = article_body.find_all(
            ["h2", "h3", "h4", "p", "ul", "ol", "table", "figure"]
        )

        current_section = None
        section_content = []

        for elem in sections:
            if elem.name in ["h2", "h3", "h4"]:
                if current_section and section_content:
                    content.append(
                        {
                            "type": "section",
                            "title": current_section,
                            "content": "\n".join(section_content),
                        }
                    )
                current_section = elem.get_text(strip=True)
                section_content = []
            elif elem.name == "p":
                text = elem.get_text(strip=True)
                if text:
                    section_content.append(text)
            elif elem.name in ["ul", "ol"]:
                items = []
                for li in elem.find_all("li"):
                    items.append(f"- {li.get_text(strip=True)}")
                if items:
                    section_content.append("\n".join(items))

    # Extract references
    references = []
    ref_section = soup.find("div", {"class": "bibliography"}) or soup.find(
        "section", {"id": "bibliography"}
    )
    if ref_section:
        ref_items = ref_section.find_all(["li", "div", "p"])
        for ref in ref_items:
            ref_text = ref.get_text(strip=True)
            if ref_text and len(ref_text) > 20:
                references.append(ref_text)

    # Output results
    print(f"# {title_text}")
    print(f"\n**Authors:** {', '.join(authors)}")
    print(f"\n**Journal:** {journal_text}")
    print(f"\n**Year:** {year_text}")
    print(f"\n## Abstract\n\n{abstract_text}")

    print("\n## Content Summary\n")
    for section in content[:10]:  # First 10 sections
        if section["type"] == "section":
            print(f"\n### {section['title']}")
            print(f"{section['content'][:500]}...")

    print(f"\n## References ({len(references)} found)")
    for i, ref in enumerate(references[:10]):
        print(f"\n{i + 1}. {ref}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_paper_content.py <html_file>")
        sys.exit(1)

    extract_paper_content(sys.argv[1])
