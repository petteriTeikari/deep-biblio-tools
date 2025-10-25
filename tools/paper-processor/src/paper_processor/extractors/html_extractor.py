"""HTML paper extractor."""

from pathlib import Path

from bs4 import BeautifulSoup, NavigableString

from ..models.paper import Paper, Reference, Section
from .base import BaseExtractor


class HTMLExtractor(BaseExtractor):
    """Extract content from HTML papers."""

    def extract(self, file_path: Path) -> Paper:
        """Extract paper content from HTML file."""
        with open(file_path, encoding="utf-8") as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, "html.parser")

        # Remove unwanted elements
        for element in soup.find_all(
            ["script", "style", "nav", "header", "footer"]
        ):
            element.decompose()

        # Create paper object
        paper = Paper(source_path=str(file_path))

        # Extract metadata
        self._extract_metadata(soup, paper)

        # Extract abstract
        paper.abstract = self._extract_abstract(soup)

        # Extract keywords
        paper.keywords = self._extract_keywords(soup)

        # Extract main content
        paper.sections = self._extract_sections(soup)

        # Extract references
        paper.references = self._extract_references(soup)

        return paper

    def _extract_metadata(self, soup: BeautifulSoup, paper: Paper):
        """Extract metadata from meta tags and other sources."""
        # Title
        title_meta = soup.find("meta", {"name": "citation_title"})
        if title_meta:
            paper.title = title_meta.get("content", "")
        else:
            # Try alternative methods
            title_elem = soup.find("h1", class_="title-text") or soup.find("h1")
            if title_elem:
                paper.title = title_elem.get_text(strip=True)

        # Authors
        author_metas = soup.find_all("meta", {"name": "citation_author"})
        for author_meta in author_metas:
            author = author_meta.get("content", "")
            if author:
                paper.authors.append(author)

        # If no authors in meta, try alternatives
        if not paper.authors:
            author_elements = soup.find_all(
                ["span", "div"], class_=["author-name", "author"]
            )
            for elem in author_elements:
                author = elem.get_text(strip=True)
                if author and author not in paper.authors:
                    paper.authors.append(author)

        # Journal
        journal_meta = soup.find("meta", {"name": "citation_journal_title"})
        if journal_meta:
            paper.journal = journal_meta.get("content", "")

        # Year
        year_meta = soup.find("meta", {"name": "citation_publication_date"})
        if year_meta:
            date_content = year_meta.get("content", "")
            if len(date_content) >= 4:
                paper.year = date_content[:4]

        # Volume and pages
        volume_meta = soup.find("meta", {"name": "citation_volume"})
        if volume_meta:
            paper.volume = volume_meta.get("content", "")

        pages_meta = soup.find("meta", {"name": "citation_firstpage"})
        if pages_meta:
            paper.pages = pages_meta.get("content", "")
            lastpage_meta = soup.find("meta", {"name": "citation_lastpage"})
            if lastpage_meta:
                paper.pages += f"-{lastpage_meta.get('content', '')}"

        # DOI
        doi_meta = soup.find("meta", {"name": "citation_doi"})
        if doi_meta:
            paper.doi = doi_meta.get("content", "")

    def _extract_abstract(self, soup: BeautifulSoup) -> str | None:
        """Extract abstract from HTML."""
        # Try meta tag first
        abstract_meta = soup.find("meta", {"name": "citation_abstract"})
        if abstract_meta:
            return abstract_meta.get("content", "")

        # Try common abstract containers
        abstract_selectors = [
            {"class": "abstract"},
            {"id": "abstract"},
            {"class": "abstract-content"},
            {"class": "article-abstract"},
        ]

        for selector in abstract_selectors:
            abstract_elem = soup.find(["div", "section"], selector)
            if abstract_elem:
                # Remove heading if present
                heading = abstract_elem.find(
                    ["h1", "h2", "h3"], string=["Abstract", "ABSTRACT"]
                )
                if heading:
                    heading.decompose()
                return abstract_elem.get_text(strip=True)

        return None

    def _extract_keywords(self, soup: BeautifulSoup) -> list[str]:
        """Extract keywords from HTML."""
        keywords = []

        # Try meta tags
        keyword_metas = soup.find_all(
            "meta", {"name": ["citation_keywords", "keywords"]}
        )
        for meta in keyword_metas:
            content = meta.get("content", "")
            if content:
                # Split by common delimiters
                for delimiter in [";", ",", "|"]:
                    if delimiter in content:
                        keywords.extend(
                            [k.strip() for k in content.split(delimiter)]
                        )
                        break
                else:
                    keywords.append(content.strip())

        # Try keyword containers
        if not keywords:
            keyword_elem = soup.find(
                ["div", "section"], class_=["keywords", "article-keywords"]
            )
            if keyword_elem:
                # Extract individual keywords
                keyword_items = keyword_elem.find_all(["span", "li", "a"])
                for item in keyword_items:
                    keyword = item.get_text(strip=True)
                    if keyword and keyword not in [
                        "Keywords:",
                        "Keywords",
                        "Key words",
                    ]:
                        keywords.append(keyword)

        return keywords

    def _extract_sections(self, soup: BeautifulSoup) -> list[Section]:
        """Extract main content sections."""
        sections = []

        # Look for main content container
        main_content = soup.find(
            ["main", "article", "div"],
            class_=["main-content", "article-content", "body"],
        )
        if not main_content:
            main_content = soup.body

        # Extract sections based on headings
        current_section = None
        current_content = []

        for element in main_content.descendants:
            if isinstance(element, NavigableString):
                continue

            # Check if it's a heading
            if element.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                # Save previous section if exists
                if current_section:
                    current_section.content = "\n".join(current_content).strip()
                    sections.append(current_section)

                # Start new section
                level = int(element.name[1])
                title = element.get_text(strip=True)

                # Skip certain headings
                skip_titles = [
                    "Abstract",
                    "Keywords",
                    "References",
                    "Bibliography",
                ]
                if any(skip in title for skip in skip_titles):
                    current_section = None
                    current_content = []
                    continue

                current_section = Section(title=title, content="", level=level)
                current_content = []

            # Collect content
            elif current_section and element.name in ["p", "div", "span"]:
                text = element.get_text(strip=True)
                if text and len(text) > 20:  # Skip very short texts
                    current_content.append(text)

        # Save last section
        if current_section:
            current_section.content = "\n".join(current_content).strip()
            sections.append(current_section)

        # Organize into hierarchy
        return self._organize_sections(sections)

    def _organize_sections(self, flat_sections: list[Section]) -> list[Section]:
        """Organize flat sections into hierarchy based on levels."""
        if not flat_sections:
            return []

        organized = []
        stack = []

        for section in flat_sections:
            # Find parent
            while stack and stack[-1].level >= section.level:
                stack.pop()

            if stack:
                # Add as subsection to parent
                stack[-1].subsections.append(section)
            else:
                # Top-level section
                organized.append(section)

            stack.append(section)

        return organized

    def _extract_references(self, soup: BeautifulSoup) -> list[Reference]:
        """Extract references from HTML."""
        references = []

        # Look for reference section
        ref_section = None
        ref_selectors = [
            {"class": "references"},
            {"id": "references"},
            {"class": "bibliography"},
            {"id": "bibliography"},
        ]

        for selector in ref_selectors:
            ref_section = soup.find(["div", "section"], selector)
            if ref_section:
                break

        if not ref_section:
            # Try to find by heading
            ref_heading = soup.find(
                ["h1", "h2", "h3"],
                string=["References", "Bibliography", "REFERENCES"],
            )
            if ref_heading:
                ref_section = ref_heading.find_next_sibling()

        if ref_section:
            # Extract individual references
            ref_items = ref_section.find_all(
                ["li", "p", "div"], class_=["reference", "bib-reference"]
            )

            if not ref_items:
                # Try to find references by pattern
                for elem in ref_section.find_all(["p", "div"]):
                    text = elem.get_text(strip=True)
                    # Simple heuristic: references often start with [number] or author name
                    if text and (text[0].isdigit() or text[0] == "["):
                        ref_items.append(elem)

            for i, item in enumerate(ref_items):
                ref_text = item.get_text(strip=True)
                if ref_text:
                    # Extract DOI if present
                    doi = None
                    doi_link = item.find("a", href=True)
                    if doi_link and "doi.org" in doi_link["href"]:
                        doi = doi_link["href"].split("doi.org/")[-1]

                    reference = Reference(
                        key=f"ref{i + 1}", text=ref_text, doi=doi
                    )

                    # Try to parse structured info
                    self._parse_reference_details(reference)
                    references.append(reference)

        return references

    def _parse_reference_details(self, reference: Reference):
        """Parse structured information from reference text."""
        text = reference.text

        # Extract year (look for 4-digit number in parentheses)
        import re

        year_match = re.search(r"\((\d{4})\)", text)
        if year_match:
            reference.year = year_match.group(1)

        # Extract authors (text before first parenthesis or period)
        author_end = text.find("(")
        if author_end == -1:
            author_end = text.find(".")

        if author_end > 0:
            authors_text = text[:author_end].strip()
            # Split by common delimiters
            if " and " in authors_text:
                reference.authors = [
                    a.strip() for a in authors_text.split(" and ")
                ]
            elif ", " in authors_text:
                reference.authors = [
                    a.strip() for a in authors_text.split(", ")
                ]
            else:
                reference.authors = [authors_text]
