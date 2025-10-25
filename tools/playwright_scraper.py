#!/usr/bin/env python3
"""
Playwright-based scraper for ScienceDirect that handles JavaScript and anti-bot measures.
"""

import argparse
import asyncio
import json
import re
from typing import Any
from urllib.parse import quote

from playwright.async_api import Browser, Page, async_playwright


class ScienceDirectPlaywrightScraper:
    """Scraper for ScienceDirect using Playwright browser automation."""

    BASE_URL = "https://www.sciencedirect.com"

    def __init__(self, headless: bool = True, delay: float = 2.0):
        """
        Initialize scraper.

        Args:
            headless: Run browser in headless mode
            delay: Delay between page loads (seconds)
        """
        self.headless = headless
        self.delay = delay
        self.browser: Browser | None = None
        self.page: Page | None = None

    async def setup(self):
        """Setup browser and page."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )

        # Create context with realistic viewport and user agent
        context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        self.page = await context.new_page()

        # Add some randomness to appear more human
        await self.page.add_init_script("""
            // Override navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

    async def cleanup(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()

    async def search_papers(
        self,
        query: str,
        journal: str = None,
        years: list[int] = None,
        max_results: int = None,
    ) -> list[dict[str, Any]]:
        """Search for papers and extract results."""
        papers = []

        # Build search URL
        search_url = f"{self.BASE_URL}/search"
        params = [f"qs={quote(query)}"]

        if journal:
            params.append(f"pub={quote(journal)}")

        if years:
            years_str = ",".join(map(str, years))
            params.append(f"years={years_str}")
            params.append("lastSelectedFacet=years")

        full_url = f"{search_url}?{'&'.join(params)}"

        print(f"Navigating to: {full_url}")
        await self.page.goto(full_url, wait_until="networkidle")

        # Take a screenshot for debugging
        await self.page.screenshot(path="debug_search.png")

        # Try multiple selectors
        try:
            # Wait for search results to load
            await self.page.wait_for_selector(
                ".result-list-title-link", timeout=10000
            )
        except Exception:
            # Try alternative selectors
            try:
                await self.page.wait_for_selector(
                    "a[data-aa-title]", timeout=5000
                )
            except Exception:
                # Check if we got blocked or redirected
                current_url = self.page.url
                page_title = await self.page.title()
                print(f"Current URL: {current_url}")
                print(f"Page title: {page_title}")

                # Save page content for debugging
                content = await self.page.content()
                with open("debug_page.html", "w") as f:
                    f.write(content)
                print("Saved page content to debug_page.html")

                # Check for common blocking messages
                if (
                    "access" in page_title.lower()
                    or "verify" in page_title.lower()
                ):
                    print("Possible access verification required")

                raise Exception(
                    f"Could not find search results. Page title: {page_title}"
                )

        page_num = 1
        while max_results is None or len(papers) < max_results:
            print(f"Scraping page {page_num}...")

            # Extract paper links and titles from current page
            paper_elements = await self.page.query_selector_all(
                ".result-list-title-link"
            )

            for element in paper_elements:
                if max_results and len(papers) >= max_results:
                    break

                title = await element.inner_text()
                href = await element.get_attribute("href")
                paper_url = (
                    f"{self.BASE_URL}{href}" if href.startswith("/") else href
                )

                # Extract PII from URL
                pii_match = re.search(r"/pii/([A-Z0-9]+)$", paper_url)
                pii = pii_match.group(1) if pii_match else None

                papers.append(
                    {"title": title.strip(), "url": paper_url, "pii": pii}
                )

            # Check if there's a next page
            next_button = await self.page.query_selector(
                'a[aria-label="Next page"]:not(.disabled)'
            )
            if not next_button or (max_results and len(papers) >= max_results):
                break

            # Click next page
            await next_button.click()
            await self.page.wait_for_load_state("networkidle")
            await asyncio.sleep(self.delay)
            page_num += 1

        return papers

    async def get_paper_details(self, paper_url: str) -> dict[str, Any]:
        """Extract detailed information from a paper page."""
        print(f"Fetching details for: {paper_url}")
        await self.page.goto(paper_url, wait_until="networkidle")
        await asyncio.sleep(self.delay)

        details = {"url": paper_url}

        # Title
        title_elem = await self.page.query_selector("span.title-text")
        if title_elem:
            details["title"] = await title_elem.inner_text()

        # Authors
        authors = []
        author_elements = await self.page.query_selector_all(
            ".author-group a.author"
        )
        for elem in author_elements:
            author_name = await elem.inner_text()
            if author_name:
                authors.append(author_name.strip())
        details["authors"] = authors

        # Abstract
        abstract_elem = await self.page.query_selector("div.abstract")
        if abstract_elem:
            # Get all text except the "Abstract" heading
            abstract_text = await abstract_elem.evaluate("""
                (element) => {
                    const clone = element.cloneNode(true);
                    const heading = clone.querySelector('h2');
                    if (heading) heading.remove();
                    return clone.textContent.trim();
                }
            """)
            details["abstract"] = abstract_text

        # DOI
        doi_elem = await self.page.query_selector("a.doi")
        if doi_elem:
            details["doi"] = await doi_elem.inner_text()

        # Publication info
        pub_elem = await self.page.query_selector(".publication-volume")
        if pub_elem:
            details["publication_info"] = await pub_elem.inner_text()

        # Year extraction
        if "publication_info" in details:
            year_match = re.search(
                r"\b(19|20)\d{2}\b", details["publication_info"]
            )
            if year_match:
                details["year"] = int(year_match.group())

        # Keywords
        keywords = []
        keyword_elements = await self.page.query_selector_all(
            ".keywords-section .keyword"
        )
        for elem in keyword_elements:
            keyword = await elem.inner_text()
            if keyword:
                keywords.append(keyword.strip())
        details["keywords"] = keywords

        # Open access check
        oa_elem = await self.page.query_selector(".pdf-download-label")
        if oa_elem:
            oa_text = await oa_elem.inner_text()
            details["open_access"] = "Open access" in oa_text
        else:
            details["open_access"] = False

        # PDF link if available
        pdf_button = await self.page.query_selector(
            'a.link-button-primary[href*="pdf"]'
        )
        if pdf_button:
            pdf_href = await pdf_button.get_attribute("href")
            details["pdf_url"] = (
                f"{self.BASE_URL}{pdf_href}"
                if pdf_href.startswith("/")
                else pdf_href
            )

        return details

    async def scrape_papers(
        self,
        query: str,
        journal: str = None,
        years: list[int] = None,
        max_results: int = None,
        include_abstracts: bool = True,
    ) -> list[dict[str, Any]]:
        """Main method to search and scrape papers."""
        print(f"Starting scrape for query: '{query}'")

        # Search for papers
        papers = await self.search_papers(query, journal, years, max_results)
        print(f"Found {len(papers)} papers")

        if not include_abstracts:
            return papers

        # Fetch details for each paper
        print("Fetching paper details...")
        for i, paper in enumerate(papers):
            try:
                details = await self.get_paper_details(paper["url"])
                paper.update(details)
                print(f"Progress: {i + 1}/{len(papers)} papers")

                # Add delay between papers
                if i < len(papers) - 1:
                    await asyncio.sleep(self.delay)

            except Exception as e:
                print(f"Error fetching details for paper {i + 1}: {e}")
                paper["error"] = str(e)

        return papers

    def to_bibtex(self, paper: dict[str, Any]) -> str:
        """Convert paper to BibTeX format."""
        authors = paper.get("authors", [])
        first_author_surname = authors[0].split()[-1] if authors else "Unknown"
        year = paper.get("year", "YYYY")
        key = f"{first_author_surname}{year}"

        title = paper.get("title", "Untitled").replace("{", "").replace("}", "")
        author_str = " and ".join(authors) if authors else "Unknown"

        bibtex = f"@article{{{key},\n"
        bibtex += f"  title = {{{{{title}}}}},\n"
        bibtex += f"  author = {{{author_str}}},\n"

        if paper.get("year"):
            bibtex += f"  year = {{{paper['year']}}},\n"

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

        bibtex += f"  url = {{{paper['url']}}},\n"

        if paper.get("open_access"):
            bibtex += "  note = {Open Access},\n"

        bibtex = bibtex.rstrip(",\n") + "\n}"

        return bibtex


async def main():
    parser = argparse.ArgumentParser(
        description="Scrape papers from ScienceDirect using Playwright"
    )
    parser.add_argument(
        "query", help='Search query (e.g., "BIM", "scan to BIM")'
    )
    parser.add_argument("--journal", help="Filter by journal name")
    parser.add_argument("--years", nargs="+", type=int, help="Filter by years")
    parser.add_argument(
        "--max-results", type=int, help="Maximum number of papers"
    )
    parser.add_argument("--bibtex", help="Export to BibTeX file")
    parser.add_argument("--json", help="Export to JSON file")
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay between requests (seconds)",
    )
    parser.add_argument(
        "--no-abstracts", action="store_true", help="Skip fetching abstracts"
    )
    parser.add_argument(
        "--visible", action="store_true", help="Show browser window"
    )

    args = parser.parse_args()

    # Initialize scraper
    scraper = ScienceDirectPlaywrightScraper(
        headless=not args.visible, delay=args.delay
    )

    try:
        await scraper.setup()

        # Scrape papers
        papers = await scraper.scrape_papers(
            query=args.query,
            journal=args.journal,
            years=args.years,
            max_results=args.max_results,
            include_abstracts=not args.no_abstracts,
        )

        # Save results
        if args.json:
            with open(args.json, "w", encoding="utf-8") as f:
                json.dump(papers, f, indent=2, ensure_ascii=False)
            print(f"\nSaved JSON to {args.json}")

        if args.bibtex:
            with open(args.bibtex, "w", encoding="utf-8") as f:
                for paper in papers:
                    bibtex = scraper.to_bibtex(paper)
                    f.write(bibtex + "\n\n")
            print(f"Saved BibTeX to {args.bibtex}")

        # Print summary
        print("\nSummary:")
        print(f"- Total papers scraped: {len(papers)}")
        if not args.no_abstracts:
            open_access = sum(1 for p in papers if p.get("open_access"))
            print(f"- Open access papers: {open_access}")

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

    finally:
        await scraper.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
