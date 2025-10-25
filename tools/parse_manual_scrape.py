#!/usr/bin/env python3
"""
Parse manually downloaded ScienceDirect HTML files to extract paper metadata and abstracts.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


def parse_sciencedirect_html(html_path: Path) -> dict[str, Any]:
    """Parse a ScienceDirect HTML file to extract paper metadata."""
    with open(html_path, encoding="utf-8") as f:
        html_content = f.read()

    soup = BeautifulSoup(html_content, "html.parser")

    paper_data = {"filename": html_path.name, "path": str(html_path)}

    # Title
    title_elem = soup.find("span", {"class": "title-text"})
    if title_elem:
        paper_data["title"] = title_elem.get_text(strip=True)

    # Authors
    authors = []
    author_group = soup.find("div", {"class": "author-group"})
    if author_group:
        author_links = author_group.find_all("a", {"class": "author"})
        for author in author_links:
            name = author.get_text(strip=True)
            if name:
                authors.append(name)
    paper_data["authors"] = authors

    # Abstract
    abstract_elem = soup.find("div", {"class": "abstract"})
    if abstract_elem:
        # Clone and remove heading
        abstract_text = abstract_elem.get_text(strip=True)
        if abstract_text.startswith("Abstract"):
            abstract_text = abstract_text[8:].strip()
        paper_data["abstract"] = abstract_text

    # DOI
    doi_elem = soup.find("a", {"class": "doi"})
    if doi_elem:
        paper_data["doi"] = doi_elem.get_text(strip=True)

    # Journal and publication info
    pub_elem = soup.find("div", {"class": "publication-volume"})
    if pub_elem:
        paper_data["publication_info"] = pub_elem.get_text(strip=True)

    # Journal name (from breadcrumb or publication title)
    journal_elem = soup.find("a", {"class": "publication-title-link"})
    if journal_elem:
        paper_data["journal"] = journal_elem.get_text(strip=True)

    # Year extraction
    if "publication_info" in paper_data:
        year_match = re.search(
            r"\b(19|20)\d{2}\b", paper_data["publication_info"]
        )
        if year_match:
            paper_data["year"] = int(year_match.group())

    # Keywords
    keywords = []
    keyword_section = soup.find("div", {"class": "keywords-section"})
    if keyword_section:
        keyword_elems = keyword_section.find_all("div", {"class": "keyword"})
        for kw in keyword_elems:
            keywords.append(kw.get_text(strip=True))
    paper_data["keywords"] = keywords

    # Open access check
    oa_elem = soup.find("span", {"class": "pdf-download-label"})
    if oa_elem:
        paper_data["open_access"] = "Open access" in oa_elem.get_text()
    else:
        paper_data["open_access"] = False

    # URL (extract from meta tags or canonical link)
    canonical = soup.find("link", {"rel": "canonical"})
    if canonical:
        paper_data["url"] = canonical.get("href")

    # PII from URL or meta
    if "url" in paper_data:
        pii_match = re.search(r"/pii/([A-Z0-9]+)", paper_data["url"])
        if pii_match:
            paper_data["pii"] = pii_match.group(1)

    return paper_data


def to_bibtex(paper: dict[str, Any]) -> str:
    """Convert paper data to BibTeX format."""
    authors = paper.get("authors", [])
    first_author = authors[0].split()[-1] if authors else "Unknown"
    year = paper.get("year", "YYYY")
    key = f"{first_author}{year}"

    title = paper.get("title", "Untitled").replace("{", "").replace("}", "")
    author_str = " and ".join(authors) if authors else "Unknown"

    bibtex = f"@article{{{key},\n"
    bibtex += f"  title = {{{{{title}}}}},\n"
    bibtex += f"  author = {{{author_str}}},\n"

    if paper.get("journal"):
        bibtex += f"  journal = {{{paper['journal']}}},\n"

    if paper.get("year"):
        bibtex += f"  year = {{{year}}},\n"

    if paper.get("doi"):
        bibtex += f"  doi = {{{paper['doi']}}},\n"

    if paper.get("abstract"):
        abstract = (
            paper["abstract"]
            .replace("\n", " ")
            .replace("{", "")
            .replace("}", "")
        )
        bibtex += f"  abstract = {{{{{abstract}}}}},\n"

    if paper.get("keywords"):
        keywords = ", ".join(paper["keywords"])
        bibtex += f"  keywords = {{{keywords}}},\n"

    if paper.get("url"):
        bibtex += f"  url = {{{paper['url']}}},\n"

    if paper.get("open_access"):
        bibtex += "  note = {Open Access},\n"

    return bibtex.rstrip(",\n") + "\n}"


def main():
    parser = argparse.ArgumentParser(
        description="Parse manually downloaded ScienceDirect HTML files"
    )
    parser.add_argument("input_dir", help="Directory containing HTML files")
    parser.add_argument("--json", help="Output JSON file")
    parser.add_argument("--bibtex", help="Output BibTeX file")
    parser.add_argument(
        "--pattern", default="*.html", help="File pattern to match"
    )

    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"Error: Directory {input_dir} does not exist")
        return 1

    # Find all HTML files
    html_files = list(input_dir.glob(args.pattern))
    print(f"Found {len(html_files)} HTML files")

    # Parse all files
    papers = []
    for html_file in html_files:
        print(f"Parsing: {html_file.name}")
        try:
            paper_data = parse_sciencedirect_html(html_file)
            papers.append(paper_data)
        except Exception as e:
            print(f"  Error: {e}")
            continue

    print(f"\nSuccessfully parsed {len(papers)} papers")

    # Save results
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(papers, f, indent=2, ensure_ascii=False)
        print(f"Saved JSON to {args.json}")

    if args.bibtex:
        with open(args.bibtex, "w", encoding="utf-8") as f:
            for paper in papers:
                f.write(to_bibtex(paper) + "\n\n")
        print(f"Saved BibTeX to {args.bibtex}")

    # Print summary
    print("\nSummary:")
    print(f"- Total papers: {len(papers)}")
    print(
        f"- Papers with abstracts: {sum(1 for p in papers if p.get('abstract'))}"
    )
    print(
        f"- Open access papers: {sum(1 for p in papers if p.get('open_access'))}"
    )

    # Show first few papers
    print("\nFirst 3 papers:")
    for i, paper in enumerate(papers[:3]):
        print(f"\n{i + 1}. {paper.get('title', 'Untitled')}")
        if paper.get("authors"):
            print(f"   Authors: {', '.join(paper['authors'][:3])}")
        if paper.get("abstract"):
            abstract = (
                paper["abstract"][:150] + "..."
                if len(paper["abstract"]) > 150
                else paper["abstract"]
            )
            print(f"   Abstract: {abstract}")

    return 0


if __name__ == "__main__":
    exit(main())
