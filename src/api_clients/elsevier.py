"""Elsevier ScienceDirect scraper with rate limiting and respectful practices."""

from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .base import APIClient


class ElsevierScraper(APIClient):
    """Scraper for Elsevier ScienceDirect with built-in rate limiting."""

    BASE_URL = "https://www.sciencedirect.com"

    def __init__(self, delay: float = 1.0):
        """
        Initialize Elsevier scraper.

        Args:
            delay: Delay between requests in seconds (default 1.0 for respectful scraping)
        """
        super().__init__(delay=delay)
        # Set user agent to identify as a research tool
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (compatible; Academic Research Tool; +https://github.com)"
            }
        )

    def search_papers(
        self,
        query: str,
        journal: str = None,
        years: list[int] = None,
        max_results: int = None,
    ) -> list[dict[str, Any]]:
        """
        Search for papers on ScienceDirect.

        Args:
            query: Search query (e.g., "BIM", "scan to BIM")
            journal: Journal name to filter by
            years: List of years to filter by
            max_results: Maximum number of results to return

        Returns:
            List of paper metadata dictionaries
        """
        papers = []
        offset = 0
        page_size = 100  # ScienceDirect typically shows 100 results per page

        while max_results is None or len(papers) < max_results:
            # Build search URL
            params = {"qs": query, "offset": offset}

            if journal:
                params["pub"] = journal

            if years:
                params["years"] = ",".join(map(str, years))
                params["lastSelectedFacet"] = "years"

            search_url = f"{self.BASE_URL}/search"

            try:
                response = self._make_request(
                    search_url, params=params, json_response=False
                )
                soup = BeautifulSoup(response.text, "html.parser")

                # Find all paper links in search results
                paper_links = soup.find_all(
                    "a", {"class": "result-list-title-link"}
                )

                if not paper_links:
                    # No more results
                    break

                for link in paper_links:
                    if max_results and len(papers) >= max_results:
                        break

                    paper_url = urljoin(self.BASE_URL, link.get("href", ""))
                    title = link.get_text(strip=True)

                    # Extract PII from URL using string methods
                    pii = None
                    if "/pii/" in paper_url:
                        pii = paper_url.split("/pii/")[-1]

                    papers.append(
                        {"title": title, "url": paper_url, "pii": pii}
                    )

                offset += page_size

                # Check if there's a next page
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
        """
        Extract detailed information from a paper page.

        Args:
            paper_url: URL of the paper on ScienceDirect

        Returns:
            Dictionary with paper details including abstract
        """
        try:
            response = self._make_request(paper_url, json_response=False)
            soup = BeautifulSoup(response.text, "html.parser")

            details = {"url": paper_url}

            # Extract title
            title_elem = soup.find("span", {"class": "title-text"})
            if title_elem:
                details["title"] = title_elem.get_text(strip=True)

            # Extract authors
            authors = []
            author_group = soup.find("div", {"class": "author-group"})
            if author_group:
                author_links = author_group.find_all("a", {"class": "author"})
                for author in author_links:
                    name = author.get_text(strip=True)
                    if name:
                        authors.append(name)
            details["authors"] = authors

            # Extract abstract
            abstract_elem = soup.find("div", {"class": "abstract"})
            if abstract_elem:
                # Remove the "Abstract" heading if present
                abstract_heading = abstract_elem.find("h2")
                if abstract_heading:
                    abstract_heading.decompose()
                details["abstract"] = abstract_elem.get_text(strip=True)

            # Extract DOI
            doi_elem = soup.find("a", {"class": "doi"})
            if doi_elem:
                details["doi"] = doi_elem.get_text(strip=True)

            # Extract publication info
            pub_elem = soup.find("div", {"class": "publication-info"})
            if pub_elem:
                details["publication_info"] = pub_elem.get_text(strip=True)

            # Check if open access
            oa_elem = soup.find("span", {"class": "pdf-download-label"})
            details["open_access"] = bool(
                oa_elem and "Open access" in oa_elem.get_text()
            )

            # Extract PDF link if available
            pdf_link = soup.find("a", {"class": "link-button-primary"})
            if pdf_link and "pdf" in pdf_link.get("href", "").lower():
                details["pdf_url"] = urljoin(
                    self.BASE_URL, pdf_link.get("href")
                )

            # Extract keywords
            keywords = []
            keyword_section = soup.find("div", {"class": "keywords-section"})
            if keyword_section:
                keyword_elems = keyword_section.find_all(
                    "div", {"class": "keyword"}
                )
                for kw in keyword_elems:
                    keywords.append(kw.get_text(strip=True))
            details["keywords"] = keywords

            # Extract year from publication info using string methods
            pub_info = details.get("publication_info", "")
            # Simple year extraction for 19xx or 20xx
            for word in pub_info.split():
                # Remove comma if present
                word_clean = word.rstrip(",")
                if len(word_clean) == 4 and word_clean.isdigit():
                    if word_clean.startswith("19") or word_clean.startswith(
                        "20"
                    ):
                        details["year"] = int(word_clean)
                        break

            return details

        except requests.RequestException as e:
            print(f"Error fetching paper details: {e}")
            return {"url": paper_url, "error": str(e)}

    def scrape_papers(
        self,
        query: str,
        journal: str = None,
        years: list[int] = None,
        max_results: int = None,
        include_abstracts: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Search and scrape papers with their details.

        Args:
            query: Search query
            journal: Journal name to filter by
            years: List of years to filter by
            max_results: Maximum number of papers to scrape
            include_abstracts: Whether to fetch full paper details including abstracts

        Returns:
            List of paper dictionaries with full details
        """
        print(f"Searching for papers with query: {query}")
        papers = self.search_papers(query, journal, years, max_results)

        if not include_abstracts:
            return papers

        print(f"Found {len(papers)} papers. Fetching details...")

        detailed_papers = []
        for i, paper in enumerate(papers):
            print(
                f"Fetching paper {i + 1}/{len(papers)}: {paper['title'][:60]}..."
            )
            details = self.get_paper_details(paper["url"])

            # Merge search result with detailed info
            paper.update(details)
            detailed_papers.append(paper)

            # Show progress every 10 papers
            if (i + 1) % 10 == 0:
                print(f"Progress: {i + 1}/{len(papers)} papers scraped")

        print(f"Successfully scraped {len(detailed_papers)} papers")
        return detailed_papers

    def to_bibtex(self, paper: dict[str, Any]) -> str:
        """
        Convert paper details to BibTeX format.

        Args:
            paper: Paper dictionary with details

        Returns:
            BibTeX entry as string
        """
        # Generate BibTeX key from first author and year
        authors = paper.get("authors", [])
        first_author_surname = authors[0].split()[-1] if authors else "Unknown"
        year = paper.get("year", "YYYY")
        key = f"{first_author_surname}{year}"

        # Clean up title
        title = paper.get("title", "Untitled").replace("{", "").replace("}", "")

        # Format authors for BibTeX
        author_str = " and ".join(authors) if authors else "Unknown"

        bibtex = f"@article{{{key},\n"
        bibtex += f"  title = {{{{{title}}}}},\n"
        bibtex += f"  author = {{{author_str}}},\n"

        if paper.get("year"):
            bibtex += f"  year = {{{paper['year']}}},\n"

        if paper.get("doi"):
            bibtex += f"  doi = {{{paper['doi']}}},\n"

        if paper.get("abstract"):
            # Clean abstract for BibTeX
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

        bibtex += f"  url = {{{paper['url']}}},\n"

        if paper.get("open_access"):
            bibtex += "  note = {Open Access},\n"

        bibtex = bibtex.rstrip(",\n") + "\n}"

        return bibtex
