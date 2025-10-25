#!/usr/bin/env python3
"""
Paper scraper tool for Elsevier ScienceDirect and other publishers.

This tool allows you to:
- Search for papers by keyword, journal, and year
- Extract abstracts and metadata
- Save results as BibTeX with abstracts
- Track open access papers
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.api_clients.elsevier import ElsevierScraper


class PaperDatabase:
    """Simple JSON-based database for storing scraped papers."""

    def __init__(self, db_path: str = "papers_db.json"):
        self.db_path = Path(db_path)
        self.papers = self._load_db()

    def _load_db(self) -> dict[str, Any]:
        """Load existing database or create new one."""
        if self.db_path.exists():
            with open(self.db_path, encoding="utf-8") as f:
                return json.load(f)
        return {
            "papers": {},
            "metadata": {"created": datetime.now().isoformat()},
        }

    def save(self):
        """Save database to disk."""
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(self.papers, f, indent=2, ensure_ascii=False)

    def add_papers(
        self, papers: list[dict[str, Any]], source: str = "elsevier"
    ):
        """Add papers to database."""
        for paper in papers:
            # Use DOI as key if available, otherwise use PII or URL
            key = paper.get("doi") or paper.get("pii") or paper["url"]

            if key not in self.papers["papers"]:
                self.papers["papers"][key] = {
                    "source": source,
                    "scraped_at": datetime.now().isoformat(),
                    **paper,
                }
            else:
                # Update existing entry
                self.papers["papers"][key].update(paper)

        self.papers["metadata"]["last_updated"] = datetime.now().isoformat()
        self.save()

    def export_bibtex(self, output_file: str, scraper: ElsevierScraper):
        """Export all papers to BibTeX file."""
        with open(output_file, "w", encoding="utf-8") as f:
            for key, paper in self.papers["papers"].items():
                bibtex = scraper.to_bibtex(paper)
                f.write(bibtex + "\n\n")
        print(f"Exported {len(self.papers['papers'])} papers to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape papers from academic publishers"
    )

    # Search parameters
    parser.add_argument(
        "query", help='Search query (e.g., "BIM", "scan to BIM")'
    )
    parser.add_argument("--journal", help="Filter by journal name")
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        help="Filter by years (e.g., 2021 2022 2023)",
    )
    parser.add_argument(
        "--max-results", type=int, help="Maximum number of papers to scrape"
    )

    # Output options
    parser.add_argument(
        "--db", default="papers_db.json", help="Database file path"
    )
    parser.add_argument("--bibtex", help="Export results to BibTeX file")
    parser.add_argument(
        "--no-abstracts",
        action="store_true",
        help="Skip fetching abstracts (faster)",
    )

    # Scraping options
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between requests in seconds",
    )
    parser.add_argument(
        "--publisher",
        default="elsevier",
        choices=["elsevier"],
        help="Publisher to scrape from",
    )

    args = parser.parse_args()

    # Initialize scraper
    if args.publisher == "elsevier":
        scraper = ElsevierScraper(delay=args.delay)
    else:
        print(f"Publisher {args.publisher} not supported yet")
        return 1

    # Initialize database
    db = PaperDatabase(args.db)

    print(f"Starting scrape with query: '{args.query}'")
    if args.journal:
        print(f"Filtering by journal: {args.journal}")
    if args.years:
        print(f"Filtering by years: {args.years}")

    try:
        # Scrape papers
        papers = scraper.scrape_papers(
            query=args.query,
            journal=args.journal,
            years=args.years,
            max_results=args.max_results,
            include_abstracts=not args.no_abstracts,
        )

        if papers:
            # Add to database
            db.add_papers(papers, source=args.publisher)

            # Export to BibTeX if requested
            if args.bibtex:
                db.export_bibtex(args.bibtex, scraper)

            # Print summary
            print("\nSummary:")
            print(f"- Total papers scraped: {len(papers)}")
            open_access = sum(1 for p in papers if p.get("open_access"))
            print(f"- Open access papers: {open_access}")
            print(f"- Database saved to: {db.db_path}")

            # Show first few papers as example
            print("\nFirst 3 papers:")
            for i, paper in enumerate(papers[:3]):
                print(f"\n{i + 1}. {paper.get('title', 'Untitled')}")
                print(
                    f"   Authors: {', '.join(paper.get('authors', ['Unknown'])[:3])}"
                )
                if paper.get("abstract"):
                    abstract_preview = (
                        paper["abstract"][:150] + "..."
                        if len(paper["abstract"]) > 150
                        else paper["abstract"]
                    )
                    print(f"   Abstract: {abstract_preview}")

        else:
            print("No papers found")

    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
        return 1
    except Exception as e:
        print(f"Error during scraping: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
