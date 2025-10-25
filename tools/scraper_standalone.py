#!/usr/bin/env python3
"""
Improved Elsevier ScienceDirect scraper with better author parsing and BibTeX formatting.
"""

import argparse
import json
import re
import shutil
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class ElsevierScraper:
    """Improved scraper for Elsevier ScienceDirect with better parsing capabilities."""

    BASE_URL = "https://www.sciencedirect.com"

    def __init__(self, delay: float = 1.0):
        """Initialize scraper with delay between requests."""
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )
        self._last_request_time = 0

    def _make_request(self, url: str, params: dict = None) -> requests.Response:
        """Make a rate-limited request."""
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self.delay:
            time.sleep(self.delay - time_since_last)

        self._last_request_time = time.time()
        response = self.session.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response

    def _extract_authors_from_preloaded_state(
        self, preloaded_data: dict
    ) -> list[str]:
        """Extract authors from the __PRELOADED_STATE__ JSON data."""
        authors = []

        try:
            # Navigate through the nested structure
            authors_content = preloaded_data.get("authors", {}).get(
                "content", []
            )

            for author_group in authors_content:
                if author_group.get("#name") == "author-group":
                    author_list = author_group.get("$$", [])

                    for author in author_list:
                        if author.get("#name") == "author":
                            given_name = ""
                            surname = ""

                            # Extract name components
                            for component in author.get("$$", []):
                                if component.get("#name") == "given-name":
                                    given_name = component.get("_", "").strip()
                                elif component.get("#name") == "surname":
                                    surname = component.get("_", "").strip()

                            # Combine names in "FirstName LastName" format
                            if given_name and surname:
                                full_name = f"{given_name} {surname}"
                                authors.append(full_name)

        except (KeyError, TypeError, AttributeError):
            pass

        return authors

    def _extract_doi_from_preloaded_state(
        self, preloaded_data: dict
    ) -> str | None:
        """Extract DOI from the __PRELOADED_STATE__ JSON data."""
        try:
            # The DOI is stored in the article metadata
            doi = preloaded_data.get("article", {}).get("doi", "")
            # Clean the DOI - remove any URL prefix
            if doi:
                doi = doi.replace("https://doi.org/", "").replace(
                    "http://doi.org/", ""
                )
                return doi
        except (KeyError, TypeError):
            pass
        return None

    def search_papers(
        self,
        query: str,
        journal: str = None,
        years: list[int] = None,
        max_results: int = None,
    ) -> list[dict[str, Any]]:
        """Search for papers on ScienceDirect."""
        papers = []
        offset = 0
        page_size = 100

        while max_results is None or len(papers) < max_results:
            params = {"qs": query, "offset": offset}

            if journal:
                params["pub"] = journal

            if years:
                params["years"] = ",".join(map(str, years))
                params["lastSelectedFacet"] = "years"

            try:
                response = self._make_request(
                    f"{self.BASE_URL}/search", params=params
                )
                soup = BeautifulSoup(response.text, "html.parser")

                # Find paper links
                paper_links = soup.find_all(
                    "a", {"class": "result-list-title-link"}
                )

                if not paper_links:
                    break

                for link in paper_links:
                    if max_results and len(papers) >= max_results:
                        break

                    paper_url = urljoin(self.BASE_URL, link.get("href", ""))
                    title = link.get_text(strip=True)

                    # Extract PII
                    pii_match = re.search(r"/pii/([A-Z0-9]+)$", paper_url)
                    pii = pii_match.group(1) if pii_match else None

                    papers.append(
                        {"title": title, "url": paper_url, "pii": pii}
                    )

                offset += page_size

                # Check for next page
                next_button = soup.find("a", {"aria-label": "Next page"})
                if not next_button or "disabled" in next_button.get(
                    "class", []
                ):
                    break

            except requests.RequestException as e:
                print(f"Error fetching search results: {e}")
                break

        return papers

    def get_paper_details(self, paper_url: str) -> dict[str, Any]:
        """Extract detailed information from a paper page or HTML file."""
        try:
            # Check if this is a file path or URL
            if paper_url.startswith("http"):
                response = self._make_request(paper_url)
                html_content = response.text
            else:
                # Read from file
                with open(paper_url, encoding="utf-8") as f:
                    html_content = f.read()

            soup = BeautifulSoup(html_content, "html.parser")
            details = {"url": paper_url}

            # Extract from __PRELOADED_STATE__ if available
            preloaded_data = {}
            script_elem = soup.find(
                "script", string=lambda x: x and "__PRELOADED_STATE__" in x
            )
            if script_elem:
                match = re.search(
                    r"window\.__PRELOADED_STATE__\s*=\s*({.*?});",
                    script_elem.string,
                    re.DOTALL,
                )
                if match:
                    try:
                        preloaded_data = json.loads(match.group(1))
                    except json.JSONDecodeError:
                        pass

            # Title - try from preloaded state first
            if preloaded_data:
                try:
                    title_content = (
                        preloaded_data.get("article", {})
                        .get("title", {})
                        .get("content", [])
                    )
                    for item in title_content:
                        if item.get("#name") == "title":
                            details["title"] = item.get("_", "").strip()
                            break
                except Exception:
                    pass

            # Fallback to HTML
            if not details.get("title"):
                title_elem = soup.find("span", {"class": "title-text"})
                if title_elem:
                    details["title"] = title_elem.get_text(strip=True)

            # Authors - extract from preloaded state
            if preloaded_data:
                authors = self._extract_authors_from_preloaded_state(
                    preloaded_data
                )
                if authors:
                    details["authors"] = authors

            # Fallback to HTML parsing if no authors found
            if not details.get("authors"):
                authors = []
                author_group = soup.find("div", {"class": "author-group"})
                if author_group:
                    author_links = author_group.find_all(
                        "a", {"class": "author"}
                    )
                    for author in author_links:
                        name = author.get_text(strip=True)
                        if name:
                            authors.append(name)
                details["authors"] = authors

            # Abstract
            abstract_text = self._extract_abstract(soup, preloaded_data)
            if abstract_text:
                details["abstract"] = abstract_text

            # Full text (if available for open access papers)
            # Note: Most Elsevier HTML previews don't include full text
            # This would need to be extended if full text becomes available
            full_text = self._extract_full_text(soup, preloaded_data)
            if full_text:
                details["full_text"] = full_text

                # Only extract images if we have full text
                # Preview pages often have placeholder images that aren't useful
                images = self._extract_images(
                    soup,
                    preloaded_data,
                    paper_url if not paper_url.startswith("http") else None,
                )
                if images:
                    details["images"] = images

            # DOI - extract from preloaded state or meta tags
            doi = None
            if preloaded_data:
                doi = self._extract_doi_from_preloaded_state(preloaded_data)

            if not doi:
                # Try meta tags
                doi_meta = soup.find("meta", {"name": "citation_doi"})
                if doi_meta:
                    doi = doi_meta.get("content", "")
                    doi = doi.replace("https://doi.org/", "").replace(
                        "http://doi.org/", ""
                    )

            if not doi:
                # Try the DOI link in the page
                doi_elem = soup.find("a", {"class": "doi"})
                if doi_elem:
                    doi = doi_elem.get_text(strip=True)
                    doi = doi.replace("https://doi.org/", "").replace(
                        "http://doi.org/", ""
                    )

            if doi:
                details["doi"] = doi

            # Journal information
            journal_meta = soup.find("meta", {"name": "citation_journal_title"})
            if journal_meta:
                details["journal"] = journal_meta.get("content", "")

            # Volume and pages
            volume_meta = soup.find("meta", {"name": "citation_volume"})
            if volume_meta:
                details["volume"] = volume_meta.get("content", "")

            firstpage_meta = soup.find("meta", {"name": "citation_firstpage"})
            if firstpage_meta:
                details["pages"] = firstpage_meta.get("content", "")

            # Publication info
            pub_elem = soup.find("div", {"class": "publication-volume"})
            if pub_elem:
                details["publication_info"] = pub_elem.get_text(strip=True)

            # Open access check
            oa_elem = soup.find("span", {"class": "pdf-download-label"})
            details["open_access"] = bool(
                oa_elem and "Open access" in oa_elem.get_text()
            )

            # Keywords
            keywords = []
            keyword_section = soup.find("div", {"class": "keywords-section"})
            if keyword_section:
                keyword_elems = keyword_section.find_all(
                    "div", {"class": "keyword"}
                )
                for kw in keyword_elems:
                    keywords.append(kw.get_text(strip=True))
            details["keywords"] = keywords

            # Extract year from preloaded state or publication info
            if preloaded_data:
                try:
                    year_str = preloaded_data.get("article", {}).get(
                        "cover-date-start", ""
                    )
                    if year_str:
                        year = int(year_str[:4])
                        details["year"] = year
                except Exception:
                    pass

            if not details.get("year"):
                # Try publication date meta tag
                pub_date_meta = soup.find(
                    "meta", {"name": "citation_publication_date"}
                )
                if pub_date_meta:
                    date_str = pub_date_meta.get("content", "")
                    year_match = re.search(r"(\d{4})", date_str)
                    if year_match:
                        details["year"] = int(year_match.group(1))

                # Fallback to publication info
                if not details.get("year") and details.get("publication_info"):
                    year_match = re.search(
                        r"\b(19|20)\d{2}\b", details["publication_info"]
                    )
                    if year_match:
                        details["year"] = int(year_match.group())

            return details

        except requests.RequestException as e:
            print(f"Error fetching paper details: {e}")
            return {"url": paper_url, "error": str(e)}

    def _extract_abstract(
        self, soup: BeautifulSoup, preloaded_data: dict
    ) -> str | None:
        """Extract abstract from various sources."""
        abstract_text = None
        highlights_text = None

        # Try from preloaded state first
        if preloaded_data:
            try:
                abstracts = preloaded_data.get("abstracts", {})
                content = abstracts.get("content", [])

                for item in content:
                    # Get regular abstract
                    if item.get("$", {}).get("class") == "author":
                        sections = item.get("$$", [])
                        for section in sections:
                            if section.get("#name") == "abstract-sec":
                                # Look for the abstract content
                                for subsection in section.get("$$", []):
                                    if subsection.get("#name") == "simple-para":
                                        abstract_text = subsection.get(
                                            "_", ""
                                        ).strip()
                                        break
                            elif section.get("#name") == "simple-para":
                                abstract_text = section.get("_", "").strip()

                    # Get highlights
                    elif item.get("$", {}).get("class") == "author-highlights":
                        sections = item.get("$$", [])
                        for section in sections:
                            if section.get("#name") == "abstract-sec":
                                # Look for list items in highlights
                                for subsection in section.get("$$", []):
                                    if subsection.get("#name") == "simple-para":
                                        list_items = subsection.get("$$", [])
                                        if list_items:
                                            highlights = []
                                            for list_item in list_items:
                                                if (
                                                    list_item.get("#name")
                                                    == "list"
                                                ):
                                                    items = list_item.get(
                                                        "$$", []
                                                    )
                                                    for item_elem in items:
                                                        if (
                                                            item_elem.get(
                                                                "#name"
                                                            )
                                                            == "list-item"
                                                        ):
                                                            para_items = (
                                                                item_elem.get(
                                                                    "$$", []
                                                                )
                                                            )
                                                            for (
                                                                para
                                                            ) in para_items:
                                                                if (
                                                                    para.get(
                                                                        "#name"
                                                                    )
                                                                    == "para"
                                                                ):
                                                                    highlights.append(
                                                                        para.get(
                                                                            "_",
                                                                            "",
                                                                        ).strip()
                                                                    )
                                            if highlights:
                                                highlights_text = "\n".join(
                                                    f"• {h}" for h in highlights
                                                )
            except Exception:
                pass

        # If we didn't get abstract from preloaded state, try HTML
        if not abstract_text:
            # Method 1: Look for div with class "abstract author" and id "ab0005"
            abstract_elem = soup.find(
                "div", {"class": "abstract author", "id": "ab0005"}
            )
            if abstract_elem:
                # Look for the actual content div
                content_div = abstract_elem.find("div", {"id": "sp0140"})
                if content_div:
                    abstract_text = content_div.get_text(strip=True)

            # Method 2: Fallback to any div with class containing "abstract"
            if not abstract_text:
                abstract_elem = soup.find(
                    "div", {"class": lambda x: x and "abstract" in x}
                )
                if abstract_elem:
                    # Remove headers
                    for h in abstract_elem.find_all(["h2", "h3", "h4"]):
                        h.decompose()
                    abstract_text = abstract_elem.get_text(strip=True)

        # Combine abstract and highlights
        result = ""
        if highlights_text:
            result = highlights_text
        if abstract_text:
            if result:
                result += "\n\n" + abstract_text
            else:
                result = abstract_text

        return result if result else None

    def _extract_full_text(
        self, soup: BeautifulSoup, preloaded_data: dict
    ) -> str | None:
        """Extract full article text if available (for open access papers).

        Note: Most Elsevier HTML files are preview pages that don't include
        the full text. This method is a placeholder for future enhancement
        if full text HTML becomes available.
        """
        full_text = None

        # Try to extract from preloaded state
        if preloaded_data:
            try:
                # Check for sections/body content
                sections = preloaded_data.get("sections", {})
                body = preloaded_data.get("body", {})

                if sections and sections.get("content"):
                    # Would process full sections here
                    pass
                elif body and body.get("content"):
                    # Would process body content here
                    pass
            except Exception:
                pass

        # Try HTML extraction if no preloaded data
        if not full_text:
            # Look for article body sections
            article_body = soup.find("div", {"class": "article-body"})
            if not article_body:
                article_body = soup.find("section", {"class": "body"})

            if article_body:
                # Extract section headings and content
                sections = []
                for section in article_body.find_all(
                    ["section", "div"],
                    {"class": re.compile(r"section|body-sec")},
                ):
                    heading = section.find(["h2", "h3", "h4"])
                    if heading:
                        section_title = heading.get_text(strip=True)
                        # Remove the heading from section
                        heading.decompose()
                        section_content = section.get_text(strip=True)
                        if section_content:
                            sections.append(
                                f"## {section_title}\n\n{section_content}"
                            )

                if sections:
                    full_text = "\n\n".join(sections)

        return full_text

    def _extract_images(
        self,
        soup: BeautifulSoup,
        preloaded_data: dict,
        html_file_path: str = None,
    ) -> list[dict[str, str]]:
        """Extract image references from the HTML.

        Note: This method is only called when full text is available.
        Preview pages often contain placeholder images or references
        that aren't useful without the actual article content.

        Returns a list of dictionaries with 'type', 'path', and 'caption' keys.
        """
        images = []

        # Extract cover image
        cover_img = soup.find("img", {"class": "cover-image"})
        if not cover_img:
            # Try to find cover image in other locations
            cover_img = soup.find("img", src=re.compile(r"cov150h\.gif$"))

        if cover_img:
            img_src = cover_img.get("src", "")
            if img_src:
                images.append(
                    {
                        "type": "cover",
                        "path": img_src,
                        "caption": "Journal cover image",
                    }
                )

        # Note: Full article figures (gr1.jpg, fx1.jpg, etc.) are not available
        # in these HTML preview pages. This section is prepared for future
        # enhancement when full article HTML or API access becomes available.

        # Try to extract figure references from preloaded data
        if preloaded_data:
            try:
                # Look for figure data in various possible locations
                figures = preloaded_data.get("figures", {})
                if figures and figures.get("content"):
                    # Would process figure data here when available
                    pass
            except Exception:
                pass

        # Try to find figure references in HTML
        # These might be placeholders or references without actual images
        figure_elements = soup.find_all("figure")
        for fig in figure_elements:
            img = fig.find("img")
            if img and img.get("src"):
                caption_elem = fig.find("figcaption")
                caption = (
                    caption_elem.get_text(strip=True) if caption_elem else ""
                )
                images.append(
                    {
                        "type": "figure",
                        "path": img.get("src"),
                        "caption": caption,
                    }
                )

        return images

    def _process_images(
        self, images: list[dict], html_file: Path, images_dir: Path
    ) -> list[dict]:
        """Process and copy images to the output directory.

        Returns updated image references with new paths.
        """
        processed_images = []

        for img in images:
            img_path = img.get("path", "")
            if not img_path:
                continue

            # Handle relative paths
            if img_path.startswith("./"):
                # Resolve relative to HTML file location
                source_path = html_file.parent / img_path[2:]
            elif img_path.startswith("http"):
                # Skip remote images for now
                processed_images.append(img)
                continue
            else:
                source_path = html_file.parent / img_path

            if source_path.exists():
                # Generate unique filename
                base_name = f"{html_file.stem}_{img['type']}"
                if img["type"] == "figure":
                    # Try to extract figure number from path
                    fig_match = re.search(r"(gr|fx)(\d+)", img_path)
                    if fig_match:
                        base_name = f"{html_file.stem}_fig{fig_match.group(2)}"

                dest_name = f"{base_name}{source_path.suffix}"
                dest_path = images_dir / dest_name

                try:
                    shutil.copy2(source_path, dest_path)
                    # Update image reference with new path
                    processed_img = img.copy()
                    processed_img["original_path"] = img_path
                    processed_img["path"] = f"images/{dest_name}"
                    processed_images.append(processed_img)
                    print(f"    Copied image: {dest_name}")
                except Exception as e:
                    print(f"    Error copying image {source_path}: {e}")
                    processed_images.append(img)
            else:
                print(f"    Image not found: {source_path}")
                processed_images.append(img)

        return processed_images

    def to_bibtex(self, paper: dict[str, Any]) -> str:
        """Convert paper details to BibTeX format with Better BibTeX compatible keys."""
        authors = paper.get("authors", [])

        # Create a Better BibTeX style key
        if authors:
            # Extract first author's last name
            first_author = authors[0]
            # Split name and get last part (surname)
            name_parts = first_author.strip().split()
            first_author_surname = name_parts[-1] if name_parts else "Unknown"
        else:
            first_author_surname = "Unknown"

        year = paper.get("year", "YYYY")

        # Create key in format: LastnameYear (with optional suffix for duplicates)
        key = f"{first_author_surname}{year}"

        # Clean up the key - remove special characters
        key = re.sub(r"[^\w]", "", key)

        title = paper.get("title", "Untitled").replace("{", "").replace("}", "")
        author_str = " and ".join(authors) if authors else "Unknown"

        bibtex = f"@article{{{key},\n"
        bibtex += f"  title = {{{{{title}}}}},\n"
        bibtex += f"  author = {{{author_str}}},\n"

        if paper.get("journal"):
            bibtex += f"  journal = {{{paper['journal']}}},\n"

        if paper.get("year"):
            bibtex += f"  year = {{{paper['year']}}},\n"

        if paper.get("volume"):
            bibtex += f"  volume = {{{paper['volume']}}},\n"

        if paper.get("pages"):
            bibtex += f"  pages = {{{paper['pages']}}},\n"

        if paper.get("doi"):
            # Clean DOI - remove any URL prefix
            doi = paper["doi"]
            doi = doi.replace("https://doi.org/", "").replace(
                "http://doi.org/", ""
            )
            bibtex += f"  doi = {{{doi}}},\n"
            # Add URL as DOI permalink
            bibtex += f"  url = {{https://doi.org/{doi}}},\n"
        else:
            # Fallback to original URL if no DOI
            if paper.get("url"):
                bibtex += f"  url = {{{paper['url']}}},\n"

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

        bibtex = bibtex.rstrip(",\n") + "\n}"

        return bibtex

    def process_html_files(
        self, directory: str, output_format: str = "both"
    ) -> dict[str, Any]:
        """Process all HTML files in a directory."""
        results = {"papers": [], "errors": []}

        path = Path(directory)
        html_files = list(path.glob("*.html"))

        # Create output directory at ../markdown_parse relative to input
        output_dir = path.parent / "markdown_parse"
        output_dir.mkdir(exist_ok=True)

        # Create images subdirectory
        images_dir = output_dir / "images"
        images_dir.mkdir(exist_ok=True)

        print(f"Found {len(html_files)} HTML files to process")
        print(f"Output directory: {output_dir}")
        print(f"Images directory: {images_dir}")

        for i, html_file in enumerate(html_files):
            print(f"\nProcessing {i + 1}/{len(html_files)}: {html_file.name}")

            try:
                details = self.get_paper_details(str(html_file))

                if "error" not in details:
                    results["papers"].append(details)

                    # Process images if any were found
                    if details.get("images"):
                        image_refs = self._process_images(
                            details["images"], html_file, images_dir
                        )
                        # Update details with processed image references
                        details["processed_images"] = image_refs

                    # Save individual files if requested
                    if output_format in ["markdown", "both"]:
                        md_content = self._to_markdown(details)
                        md_file = output_dir / f"{html_file.stem}.md"
                        with open(md_file, "w", encoding="utf-8") as f:
                            f.write(md_content)
                        print(f"  Saved markdown: {md_file.name}")

                    if output_format in ["bibtex", "both"]:
                        bib_content = self.to_bibtex(details)
                        bib_file = output_dir / f"{html_file.stem}.bib"
                        with open(bib_file, "w", encoding="utf-8") as f:
                            f.write(bib_content)
                        print(f"  Saved BibTeX: {bib_file.name}")
                else:
                    results["errors"].append(
                        {"file": html_file.name, "error": details["error"]}
                    )
                    print(f"  Error: {details['error']}")

            except Exception as e:
                results["errors"].append(
                    {"file": html_file.name, "error": str(e)}
                )
                print(f"  Error: {e}")

        return results

    def _to_markdown(self, paper: dict[str, Any]) -> str:
        """Convert paper details to markdown format."""
        md = f"# {paper.get('title', 'Untitled')}\n\n"

        if paper.get("authors"):
            md += f"**Authors:** {', '.join(paper['authors'])}\n\n"

        if paper.get("journal"):
            md += f"**Journal:** {paper['journal']}\n"

        if paper.get("year"):
            md += f"**Year:** {paper['year']}\n"

        if paper.get("volume"):
            md += f"**Volume:** {paper['volume']}\n"

        if paper.get("pages"):
            md += f"**Pages:** {paper['pages']}\n"

        if paper.get("doi"):
            doi = paper["doi"]
            md += f"**DOI:** [{doi}](https://doi.org/{doi})\n"

        md += "\n"

        if paper.get("abstract"):
            md += f"## Abstract\n\n{paper['abstract']}\n\n"

        if paper.get("keywords"):
            md += f"## Keywords\n\n{', '.join(paper['keywords'])}\n\n"

        if paper.get("full_text"):
            md += f"## Full Text\n\n{paper['full_text']}\n\n"

        # Add images section if available
        processed_images = paper.get(
            "processed_images", paper.get("images", [])
        )
        if processed_images:
            md += "## Images\n\n"
            for img in processed_images:
                img_path = img.get("path", "")
                caption = img.get("caption", "")
                img_type = img.get("type", "image")

                if img_type == "cover":
                    md += "### Journal Cover\n\n"
                elif img_type == "figure" and caption:
                    md += f"### {caption}\n\n"

                md += f"![{caption or img_type}]({img_path})\n\n"

                if caption and img_type != "figure":
                    md += f"*{caption}*\n\n"

        # Add BibTeX at the end
        md += "## BibTeX\n\n```bibtex\n"
        md += self.to_bibtex(paper)
        md += "\n```\n"

        return md


def main():
    parser = argparse.ArgumentParser(
        description="Improved Elsevier ScienceDirect scraper"
    )
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument(
        "--directory", help="Directory containing HTML files to process"
    )
    parser.add_argument(
        "--output-format",
        choices=["markdown", "bibtex", "both"],
        default="both",
        help="Output format for processed files",
    )
    parser.add_argument("--test-file", help="Test with a single HTML file")
    parser.add_argument("--journal", help="Filter by journal name")
    parser.add_argument("--years", nargs="+", type=int, help="Filter by years")
    parser.add_argument(
        "--max-results", type=int, help="Maximum number of papers"
    )
    parser.add_argument("--bibtex", help="Export to BibTeX file")
    parser.add_argument("--json", help="Export to JSON file")
    parser.add_argument(
        "--delay", type=float, default=1.0, help="Delay between requests"
    )
    parser.add_argument(
        "--no-abstracts", action="store_true", help="Skip abstracts"
    )

    args = parser.parse_args()

    scraper = ElsevierScraper(delay=args.delay)

    if args.test_file:
        # Test single file
        print(f"Testing with: {args.test_file}")
        details = scraper.get_paper_details(args.test_file)

        print("\nExtracted details:")
        print(f"Title: {details.get('title', 'NOT FOUND')}")
        print(
            f"Authors: {', '.join(details.get('authors', [])) if details.get('authors') else 'NOT FOUND'}"
        )
        print(f"Year: {details.get('year', 'NOT FOUND')}")
        print(f"DOI: {details.get('doi', 'NOT FOUND')}")
        print(f"Journal: {details.get('journal', 'NOT FOUND')}")

        if details.get("abstract"):
            print(f"\nAbstract: {details['abstract'][:200]}...")

        print("\nBibTeX:")
        print(scraper.to_bibtex(details))

    elif args.directory:
        # Process directory
        results = scraper.process_html_files(args.directory, args.output_format)

        print("\n\nSummary:")
        print(f"- Successfully processed: {len(results['papers'])} papers")
        print(f"- Errors: {len(results['errors'])} files")

        if results["errors"]:
            print("\nErrors:")
            for error in results["errors"]:
                print(f"  - {error['file']}: {error['error']}")

        # Save combined BibTeX file
        if args.output_format in ["bibtex", "both"] and results["papers"]:
            output_dir = Path(args.directory).parent / "markdown_parse"
            combined_bib = output_dir / "combined.bib"
            with open(combined_bib, "w", encoding="utf-8") as f:
                for paper in results["papers"]:
                    f.write(scraper.to_bibtex(paper))
                    f.write("\n\n")
            print(f"\nSaved combined BibTeX to: {combined_bib}")

    elif args.query:
        # Original search functionality
        print(f"Searching for: '{args.query}'")
        if args.journal:
            print(f"Journal: {args.journal}")
        if args.years:
            print(f"Years: {args.years}")

        # Search papers
        papers = scraper.search_papers(
            query=args.query,
            journal=args.journal,
            years=args.years,
            max_results=args.max_results,
        )

        if not papers:
            print("No papers found")
            return 0

        print(f"Found {len(papers)} papers")

        # Fetch details if needed
        if not args.no_abstracts:
            print("Fetching paper details...")
            for i, paper in enumerate(papers):
                print(f"  {i + 1}/{len(papers)}: {paper['title'][:60]}...")
                details = scraper.get_paper_details(paper["url"])
                paper.update(details)

        # Save results
        if args.json:
            with open(args.json, "w", encoding="utf-8") as f:
                json.dump(papers, f, indent=2, ensure_ascii=False)
            print(f"Saved to {args.json}")

        if args.bibtex:
            with open(args.bibtex, "w", encoding="utf-8") as f:
                for paper in papers:
                    bibtex = scraper.to_bibtex(paper)
                    f.write(bibtex + "\n\n")
            print(f"Saved BibTeX to {args.bibtex}")

        # Print summary
        print("\nSummary:")
        print(f"- Total papers: {len(papers)}")
        if not args.no_abstracts:
            open_access = sum(1 for p in papers if p.get("open_access"))
            print(f"- Open access: {open_access}")

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
    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    main()
