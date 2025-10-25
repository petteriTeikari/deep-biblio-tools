#!/usr/bin/env python3
"""Enhance GitHub citations by finding associated academic papers.

This script helps identify academic papers associated with GitHub repositories,
especially useful for LLM-generated bibliographies where GitHub repos are cited
instead of the actual papers.
"""

# import re  # Banned - using string methods instead
import sys
import time
from pathlib import Path

import bibtexparser
import requests
from bibtexparser.bwriter import BibTexWriter

# Add validation functionality
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.validate_llm_citations import CitationValidator


class GitHubCitationEnhancer:
    """Enhance GitHub citations by finding associated papers."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "DeepBiblioTools/1.0 (mailto:petteri.teikari@gmail.com)"
            }
        )
        self.validator = CitationValidator()

    def extract_github_info(self, url: str) -> tuple[str | None, str | None]:
        """Extract owner and repo name from GitHub URL."""
        # Look for github.com/ or github.io/
        github_pos = -1
        if "github.com/" in url:
            github_pos = url.find("github.com/") + 11
        elif "github.io/" in url:
            github_pos = url.find("github.io/") + 10

        if github_pos == -1:
            return None, None

        # Extract owner and repo
        rest = url[github_pos:]
        parts = rest.split("/")

        if len(parts) >= 2:
            owner = parts[0]
            repo = parts[1].rstrip("/")
            return owner, repo

        return None, None

    def fetch_github_metadata(self, owner: str, repo: str) -> dict:
        """Fetch repository metadata from GitHub API."""
        api_url = f"https://api.github.com/repos/{owner}/{repo}"

        try:
            response = self.session.get(api_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {
                    "title": data.get("description", ""),
                    "abstract": data.get("description", ""),
                    "topics": data.get("topics", []),
                    "homepage": data.get("homepage", ""),
                }
        except Exception as e:
            print(f"GitHub API error: {e}")

        return {}

    def search_for_paper(
        self, repo_info: dict, authors: list[str]
    ) -> dict | None:
        """Search for academic paper associated with repository."""
        # Build search query from repo info
        search_terms = []

        if repo_info.get("title"):
            search_terms.append(repo_info["title"])

        # Add author last names
        for author in authors:
            if "," in author:
                last_name = author.split(",")[0].strip()
                search_terms.append(last_name)

        if not search_terms:
            return None

        # Search CrossRef
        search_query = " ".join(search_terms)
        return self._search_crossref(search_query)

    def _search_crossref(self, query: str) -> dict | None:
        """Search CrossRef for papers."""
        url = "https://api.crossref.org/works"
        params = {
            "query": query,
            "rows": 5,  # Get top 5 results
            "filter": "type:proceedings-article,type:journal-article",
        }

        try:
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                items = data.get("message", {}).get("items", [])

                if items:
                    # Return the first result
                    return self._parse_crossref_item(items[0])

        except Exception as e:
            print(f"CrossRef search error: {e}")

        return None

    def _parse_crossref_item(self, item: dict) -> dict:
        """Parse CrossRef item into bibliography entry."""
        entry = {
            "ENTRYTYPE": "inproceedings" if item.get("event") else "article",
            "doi": item.get("DOI", ""),
            "title": item.get("title", [""])[0]
            if isinstance(item.get("title"), list)
            else item.get("title", ""),
            "year": str(
                item.get("published-print", {}).get("date-parts", [[""]])[0][0]
            )
            or str(
                item.get("published-online", {}).get("date-parts", [[""]])[0][0]
            ),
        }

        # Parse authors
        authors = []
        for author in item.get("author", []):
            family = author.get("family", "")
            given = author.get("given", "")
            if family and given:
                authors.append(f"{family}, {given}")
            elif family:
                authors.append(family)

        if authors:
            entry["author"] = " and ".join(authors)

        # Add venue info
        if item.get("event"):
            entry["booktitle"] = item.get("event", {}).get("name", "")
        elif item.get("container-title"):
            entry["journal"] = (
                item.get("container-title", [""])[0]
                if isinstance(item.get("container-title"), list)
                else item.get("container-title", "")
            )

        return entry

    def enhance_entry(self, entry: dict) -> tuple[dict, list[str]]:
        """Enhance a GitHub citation entry."""
        notes = []

        # Check if this is a GitHub URL
        url = entry.get("url", "")
        if "github.com" not in url and "github.io" not in url:
            return entry, []

        owner, repo = self.extract_github_info(url)
        if not owner or not repo:
            return entry, []

        print(f"\nProcessing GitHub citation: {owner}/{repo}")

        # Fetch GitHub metadata
        repo_info = self.fetch_github_metadata(owner, repo)

        # Extract current authors
        author_text = entry.get("author", "")
        authors = (
            [a.strip() for a in author_text.split(" and ")]
            if author_text
            else []
        )

        # Search for associated paper
        paper = self.search_for_paper(repo_info, authors)

        if paper:
            print(f"  Found associated paper: {paper.get('title', 'Unknown')}")
            notes.append(
                f"Found associated paper with DOI: {paper.get('doi', 'Unknown')}"
            )

            # Create enhanced entry
            enhanced = paper.copy()
            enhanced["ID"] = entry.get("ID", "")
            enhanced["note"] = f"GitHub: {url}; " + entry.get("note", "")

            # If we have a DOI, validate it
            if paper.get("doi"):
                validation_url = f"https://doi.org/{paper['doi']}"
                result = self.validator.validate_citation(
                    citation_text=enhanced["ID"],
                    url=validation_url,
                    original_authors=[
                        a.strip()
                        for a in enhanced.get("author", "").split(" and ")
                    ],
                )

                if (
                    result.validation_status == "validated"
                    and result.validated_authors
                ):
                    enhanced["author"] = " and ".join(result.validated_authors)
                    notes.append("Authors validated from DOI")

            return enhanced, notes
        else:
            # Just enhance with GitHub metadata
            if repo_info.get("title") and not entry.get("title"):
                entry["title"] = repo_info["title"]
                notes.append("Added title from GitHub")

            if repo_info.get("abstract") and not entry.get("abstract"):
                entry["abstract"] = repo_info["abstract"]
                notes.append("Added abstract from GitHub")

            return entry, notes

    def enhance_bibliography_file(
        self, input_file: Path, output_file: Path | None = None
    ) -> Path:
        """Enhance all GitHub citations in a bibliography file."""
        print(f"Enhancing GitHub citations in: {input_file}")

        with open(input_file, encoding="utf-8") as f:
            bib_database = bibtexparser.load(f)

        enhanced_count = 0
        github_count = 0

        for entry in bib_database.entries:
            url = entry.get("url", "")
            if "github.com" in url or "github.io" in url:
                github_count += 1
                enhanced_entry, notes = self.enhance_entry(entry)

                if notes:
                    enhanced_count += 1
                    # Replace the entry
                    for key, value in enhanced_entry.items():
                        entry[key] = value

                    print(f"  Enhanced: {entry.get('ID', 'Unknown')}")
                    for note in notes:
                        print(f"    - {note}")

                time.sleep(0.5)  # Rate limiting

        # Write output
        if output_file is None:
            output_file = (
                input_file.parent / f"{input_file.stem}_github_enhanced.bib"
            )

        writer = BibTexWriter()
        writer.indent = "  "
        writer.order_entries_by = "ID"
        writer.align_values = True

        with open(output_file, "w", encoding="utf-8") as f:
            bibtexparser.dump(bib_database, f, writer)

        print("\n\nSummary:")
        print(f"  GitHub citations found: {github_count}")
        print(f"  Successfully enhanced: {enhanced_count}")
        print(f"  Output written to: {output_file}")

        return output_file


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Enhance GitHub citations by finding associated academic papers",
        epilog="""
This script helps convert GitHub repository citations to proper academic citations
by searching for associated papers in CrossRef and other databases.

Example:
  %(prog)s references.bib -o enhanced_references.bib
""",
    )

    parser.add_argument("input", type=Path, help="Input bibliography file")
    parser.add_argument("-o", "--output", type=Path, help="Output file")

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: File not found: {args.input}")
        return 1

    try:
        enhancer = GitHubCitationEnhancer()
        output_file = enhancer.enhance_bibliography_file(
            args.input, args.output
        )
        print(f"\nSuccess! Enhanced bibliography: {output_file}")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
