#!/usr/bin/env python3
"""
Universal parser for academic papers from multiple sources (Elsevier, arXiv, etc.)
Extracts full article content when available and saves as Markdown with images.
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, NavigableString


class UniversalPaperParser:
    """Parse academic papers from various sources."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.images_dir = output_dir / "images"
        self.images_dir.mkdir(exist_ok=True)

    def detect_source(self, soup: BeautifulSoup, html_path: Path) -> str:
        """Detect the source of the paper (Elsevier, arXiv, etc.)."""
        # Check for ScienceDirect/Elsevier
        if soup.find(
            "a", {"href": re.compile(r"sciencedirect\.com")}
        ) or soup.find(
            "meta", {"name": "citation_publisher", "content": "Elsevier"}
        ):
            return "elsevier"

        # Check for arXiv
        if (
            "arxiv" in html_path.name.lower()
            or soup.find("a", {"href": re.compile(r"arxiv\.org")})
            or soup.find("meta", {"name": "citation_arxiv_id"})
        ):
            return "arxiv"

        # Check for IEEE
        if soup.find(
            "meta",
            {
                "name": "citation_publisher",
                "content": re.compile(r"IEEE", re.I),
            },
        ):
            return "ieee"

        # Check for Springer
        if soup.find(
            "meta",
            {
                "name": "citation_publisher",
                "content": re.compile(r"Springer", re.I),
            },
        ):
            return "springer"

        # Default to generic
        return "generic"

    def parse_elsevier(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Parse Elsevier/ScienceDirect papers."""
        paper_data = {}

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

        # Abstract - try multiple methods
        abstract_text = None

        # Method 1: Try to find the abstract div with specific ID structure
        abstract_elem = soup.find("div", {"class": "abstract author"})
        if abstract_elem:
            # Look for the actual abstract text in nested divs
            abstract_content = abstract_elem.find(
                "div", {"id": re.compile(r"^sp\d+")}
            )
            if abstract_content:
                abstract_text = abstract_content.get_text(strip=True)
                if abstract_text.startswith("Abstract"):
                    abstract_text = abstract_text[8:].strip()

        # Method 2: Fallback to searching for divs containing abstract text
        if not abstract_text:
            for div in soup.find_all("div"):
                text = div.get_text(strip=True)
                # Skip if it starts with "Highlights" or contains bullet points
                if text.startswith("Highlights") or text.startswith(
                    "Highlights•"
                ):
                    continue
                # Look for actual abstract content
                if (
                    len(text) > 200 and "•" not in text[:100]
                ):  # Avoid highlights with bullet points
                    # Check if it looks like an abstract
                    if any(
                        start in text[:100]
                        for start in [
                            "Semantic segmentation",
                            "This paper",
                            "This study",
                            "We propose",
                            "In this",
                        ]
                    ):
                        abstract_text = text
                        if abstract_text.startswith("Abstract"):
                            abstract_text = abstract_text[8:].strip()
                        break

        # Method 3: Try to extract from JavaScript preloaded state
        if not abstract_text:
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string and "__PRELOADED_STATE__" in script.string:
                    try:
                        # Extract JSON from the script
                        import json

                        json_str = script.string.split(
                            "__PRELOADED_STATE__ = "
                        )[1].split(";\n")[0]
                        data = json.loads(json_str)

                        # Navigate through the structure to find abstract
                        if (
                            "article" in data
                            and "item" in data["article"]
                            and "abstract" in data["article"]["item"]
                        ):
                            abstract_data = data["article"]["item"]["abstract"]
                            if "content" in abstract_data:
                                for content in abstract_data["content"]:
                                    if content.get(
                                        "$$type"
                                    ) == "paragraph" and content.get("text"):
                                        abstract_text = content["text"]
                                        break
                    except Exception:
                        pass

        if abstract_text:
            paper_data["abstract"] = abstract_text

        # DOI
        doi_elem = soup.find("a", {"class": "doi"})
        if doi_elem:
            paper_data["doi"] = doi_elem.get_text(strip=True)

        # Journal info
        journal_elem = soup.find("a", {"class": "publication-title-link"})
        if journal_elem:
            paper_data["journal"] = journal_elem.get_text(strip=True)

        pub_elem = soup.find("div", {"class": "publication-volume"})
        if pub_elem:
            paper_data["publication_info"] = pub_elem.get_text(strip=True)

        # Year
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
            keyword_elems = keyword_section.find_all(
                "div", {"class": "keyword"}
            )
            for kw in keyword_elems:
                keywords.append(kw.get_text(strip=True))
        paper_data["keywords"] = keywords

        # Full article content
        article_content = self.extract_elsevier_article(soup)
        if article_content:
            paper_data["full_text"] = article_content

        return paper_data

    def parse_arxiv(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Parse arXiv papers."""
        paper_data = {}

        # Try meta tags first
        title_meta = soup.find("meta", {"name": "citation_title"})
        if title_meta:
            paper_data["title"] = title_meta.get("content", "")
        else:
            # Fallback to h1 or title
            h1 = soup.find("h1")
            if h1:
                paper_data["title"] = h1.get_text(strip=True)

        # Authors from meta tags
        authors = []
        author_metas = soup.find_all("meta", {"name": "citation_author"})
        for meta in author_metas:
            authors.append(meta.get("content", ""))
        paper_data["authors"] = authors

        # Abstract
        abstract_meta = soup.find("meta", {"name": "citation_abstract"})
        if abstract_meta:
            paper_data["abstract"] = abstract_meta.get("content", "")
        else:
            # Look for abstract section
            abstract_elem = soup.find(
                ["div", "section"], {"class": re.compile(r"abstract", re.I)}
            )
            if abstract_elem:
                paper_data["abstract"] = abstract_elem.get_text(strip=True)

        # arXiv ID
        arxiv_meta = soup.find("meta", {"name": "citation_arxiv_id"})
        if arxiv_meta:
            paper_data["arxiv_id"] = arxiv_meta.get("content", "")

        # Date
        date_meta = soup.find("meta", {"name": "citation_date"})
        if date_meta:
            date_str = date_meta.get("content", "")
            year_match = re.search(r"\b(19|20)\d{2}\b", date_str)
            if year_match:
                paper_data["year"] = int(year_match.group())

        return paper_data

    def parse_generic(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Generic parser using meta tags and common patterns."""
        paper_data = {}

        # Title
        title_meta = soup.find("meta", {"name": "citation_title"})
        if title_meta:
            paper_data["title"] = title_meta.get("content", "")
        elif soup.title:
            paper_data["title"] = soup.title.get_text(strip=True)

        # Authors
        authors = []
        author_metas = soup.find_all("meta", {"name": "citation_author"})
        for meta in author_metas:
            authors.append(meta.get("content", ""))
        paper_data["authors"] = authors

        # Abstract
        abstract_meta = soup.find("meta", {"name": "citation_abstract"})
        if abstract_meta:
            paper_data["abstract"] = abstract_meta.get("content", "")

        # DOI
        doi_meta = soup.find("meta", {"name": "citation_doi"})
        if doi_meta:
            paper_data["doi"] = doi_meta.get("content", "")

        # Journal
        journal_meta = soup.find("meta", {"name": "citation_journal_title"})
        if journal_meta:
            paper_data["journal"] = journal_meta.get("content", "")

        # Year
        date_meta = soup.find("meta", {"name": "citation_publication_date"})
        if date_meta:
            date_str = date_meta.get("content", "")
            year_match = re.search(r"\b(19|20)\d{2}\b", date_str)
            if year_match:
                paper_data["year"] = int(year_match.group())

        return paper_data

    def extract_elsevier_article(self, soup: BeautifulSoup) -> dict[str, Any]:
        """Extract full article content from Elsevier HTML if available."""
        article_data = {}

        # Main article content
        article_elem = soup.find("article") or soup.find(
            "div", {"class": "article-content"}
        )
        if not article_elem:
            return None

        sections = []

        # Extract sections
        for section in article_elem.find_all(
            ["section", "div"], recursive=False
        ):
            section_data = {}

            # Section title
            heading = section.find(["h2", "h3", "h4"])
            if heading:
                section_data["title"] = heading.get_text(strip=True)

            # Section content
            content_parts = []
            for elem in section.children:
                if isinstance(elem, NavigableString):
                    continue

                if elem.name == "p":
                    content_parts.append(elem.get_text(strip=True))
                elif elem.name == "figure":
                    # Extract figure
                    fig_data = self.extract_figure(elem)
                    if fig_data:
                        content_parts.append(fig_data)
                elif elem.name in ["ul", "ol"]:
                    # Extract list
                    list_items = []
                    for li in elem.find_all("li"):
                        list_items.append(li.get_text(strip=True))
                    content_parts.append({"type": "list", "items": list_items})
                elif elem.name == "table":
                    # Extract table
                    table_data = self.extract_table(elem)
                    if table_data:
                        content_parts.append(table_data)

            section_data["content"] = content_parts
            sections.append(section_data)

        article_data["sections"] = sections
        return article_data

    def extract_figure(self, figure_elem) -> dict[str, Any]:
        """Extract figure data."""
        fig_data = {"type": "figure"}

        # Caption
        caption = figure_elem.find("figcaption")
        if caption:
            fig_data["caption"] = caption.get_text(strip=True)

        # Image
        img = figure_elem.find("img")
        if img:
            fig_data["src"] = img.get("src", "")
            fig_data["alt"] = img.get("alt", "")

        return fig_data

    def extract_table(self, table_elem) -> dict[str, Any]:
        """Extract table data."""
        table_data = {"type": "table"}

        # Caption
        caption = table_elem.find("caption")
        if caption:
            table_data["caption"] = caption.get_text(strip=True)

        # Extract rows
        rows = []
        for tr in table_elem.find_all("tr"):
            row = []
            for cell in tr.find_all(["td", "th"]):
                row.append(cell.get_text(strip=True))
            rows.append(row)

        table_data["rows"] = rows
        return table_data

    def save_as_markdown(self, paper_data: dict[str, Any], filename: str):
        """Save paper data as Markdown file."""
        md_path = self.output_dir / f"{filename}.md"

        with open(md_path, "w", encoding="utf-8") as f:
            # Header
            f.write(f"# {paper_data.get('title', 'Untitled')}\n\n")

            # Authors
            if paper_data.get("authors"):
                f.write(f"**Authors:** {', '.join(paper_data['authors'])}\n\n")

            # Publication info
            if paper_data.get("journal"):
                f.write(f"**Journal:** {paper_data['journal']}\n")
            if paper_data.get("year"):
                f.write(f"**Year:** {paper_data['year']}\n")
            if paper_data.get("doi"):
                f.write(f"**DOI:** {paper_data['doi']}\n")
            if paper_data.get("arxiv_id"):
                f.write(f"**arXiv:** {paper_data['arxiv_id']}\n")

            f.write("\n")

            # Abstract
            if paper_data.get("abstract"):
                f.write("## Abstract\n\n")
                f.write(f"{paper_data['abstract']}\n\n")

            # Keywords
            if paper_data.get("keywords"):
                f.write("## Keywords\n\n")
                f.write(f"{', '.join(paper_data['keywords'])}\n\n")

            # Full article content if available
            if paper_data.get("full_text") and paper_data["full_text"].get(
                "sections"
            ):
                f.write("## Full Article\n\n")

                for section in paper_data["full_text"]["sections"]:
                    if section.get("title"):
                        f.write(f"### {section['title']}\n\n")

                    for content in section.get("content", []):
                        if isinstance(content, str):
                            f.write(f"{content}\n\n")
                        elif isinstance(content, dict):
                            if content["type"] == "figure":
                                f.write(
                                    f"![{content.get('alt', 'Figure')}]({content.get('src', '')})\n"
                                )
                                if content.get("caption"):
                                    f.write(f"*{content['caption']}*\n\n")
                            elif content["type"] == "list":
                                for item in content["items"]:
                                    f.write(f"- {item}\n")
                                f.write("\n")
                            elif content["type"] == "table":
                                if content.get("caption"):
                                    f.write(f"*{content['caption']}*\n\n")
                                # Simple table rendering
                                for row in content.get("rows", []):
                                    f.write("| " + " | ".join(row) + " |\n")
                                f.write("\n")

    def to_bibtex(self, paper: dict[str, Any], source: str) -> str:
        """Convert paper data to BibTeX format."""
        # Generate key
        authors = paper.get("authors", [])
        first_author = authors[0].split()[-1] if authors else "Unknown"
        year = paper.get("year", datetime.now().year)
        key = f"{first_author}{year}"

        # Entry type
        if paper.get("arxiv_id"):
            entry_type = "misc"
        elif paper.get("journal"):
            entry_type = "article"
        else:
            entry_type = "inproceedings"

        # Build BibTeX
        bibtex = f"@{entry_type}{{{key},\n"

        # Title
        title = paper.get("title", "Untitled").replace("{", "").replace("}", "")
        bibtex += f"  title = {{{{{title}}}}},\n"

        # Authors
        if authors:
            author_str = " and ".join(authors)
            bibtex += f"  author = {{{author_str}}},\n"

        # Year
        bibtex += f"  year = {{{year}}},\n"

        # Journal/Conference
        if paper.get("journal"):
            bibtex += f"  journal = {{{paper['journal']}}},\n"

        # DOI
        if paper.get("doi"):
            bibtex += f"  doi = {{{paper['doi']}}},\n"

        # arXiv
        if paper.get("arxiv_id"):
            bibtex += "  archivePrefix = {arXiv},\n"
            bibtex += f"  eprint = {{{paper['arxiv_id']}}},\n"

        # Abstract
        if paper.get("abstract"):
            abstract = (
                paper["abstract"]
                .replace("\n", " ")
                .replace("{", "")
                .replace("}", "")
            )
            bibtex += f"  abstract = {{{{{abstract}}}}},\n"

        # Keywords
        if paper.get("keywords"):
            keywords = ", ".join(paper["keywords"])
            bibtex += f"  keywords = {{{keywords}}},\n"

        # URL
        if paper.get("url"):
            bibtex += f"  url = {{{paper['url']}}},\n"

        # Note about source
        bibtex += f"  note = {{Scraped from {source}}},\n"

        return bibtex.rstrip(",\n") + "\n}"

    def parse_html_file(self, html_path: Path) -> tuple[dict[str, Any], str]:
        """Parse a single HTML file."""
        with open(html_path, encoding="utf-8") as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, "html.parser")

        # Detect source
        source = self.detect_source(soup, html_path)

        # Parse based on source
        if source == "elsevier":
            paper_data = self.parse_elsevier(soup)
        elif source == "arxiv":
            paper_data = self.parse_arxiv(soup)
        else:
            paper_data = self.parse_generic(soup)

        # Add metadata
        paper_data["filename"] = html_path.name
        paper_data["source"] = source

        # Extract URL from canonical link or meta
        canonical = soup.find("link", {"rel": "canonical"})
        if canonical:
            paper_data["url"] = canonical.get("href")

        return paper_data, source


def main():
    parser = argparse.ArgumentParser(
        description="Universal academic paper parser"
    )
    parser.add_argument("input_dir", help="Directory containing HTML files")
    parser.add_argument(
        "--output-dir", default="parsed_papers", help="Output directory"
    )
    parser.add_argument("--json", help="Output JSON file with all papers")
    parser.add_argument("--bibtex", help="Output BibTeX file")
    parser.add_argument("--pattern", default="*.html", help="File pattern")

    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    # Initialize parser
    universal_parser = UniversalPaperParser(output_dir)

    # Find HTML files
    html_files = list(input_dir.glob(args.pattern))
    print(f"Found {len(html_files)} HTML files")

    # Parse all files
    all_papers = []
    bibtex_entries = []

    for i, html_file in enumerate(html_files):
        print(f"\n[{i + 1}/{len(html_files)}] Parsing: {html_file.name}")

        try:
            paper_data, source = universal_parser.parse_html_file(html_file)
            print(f"  Source: {source}")
            print(f"  Title: {paper_data.get('title', 'Unknown')[:60]}...")

            # Save as Markdown
            safe_filename = re.sub(
                r"[^\w\s-]", "", paper_data.get("title", html_file.stem)
            )
            safe_filename = re.sub(r"[-\s]+", "-", safe_filename)[:100]
            universal_parser.save_as_markdown(paper_data, safe_filename)

            # Generate BibTeX
            bibtex = universal_parser.to_bibtex(paper_data, source)
            bibtex_entries.append(bibtex)

            all_papers.append(paper_data)

        except Exception as e:
            print(f"  Error: {e}")
            continue

    # Save combined outputs
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(all_papers, f, indent=2, ensure_ascii=False)
        print(f"\nSaved JSON to {args.json}")

    if args.bibtex:
        with open(args.bibtex, "w", encoding="utf-8") as f:
            for entry in bibtex_entries:
                f.write(entry + "\n\n")
        print(f"Saved BibTeX to {args.bibtex}")

    # Summary
    print("\n\nSummary:")
    print(f"- Total papers parsed: {len(all_papers)}")

    # Count by source
    source_counts = {}
    for paper in all_papers:
        source = paper.get("source", "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1

    print("\nPapers by source:")
    for source, count in source_counts.items():
        print(f"  {source}: {count}")

    print(f"\nMarkdown files saved to: {output_dir}")
    print(f"Images directory: {output_dir / 'images'}")


if __name__ == "__main__":
    main()
