"""Official Elsevier API client using their developer API."""

import os
from typing import Any

from .base import APIClient


class ElsevierAPIClient(APIClient):
    """Client for Elsevier's official APIs (ScienceDirect, Scopus)."""

    BASE_URL = "https://api.elsevier.com/content"
    SEARCH_URL = "https://api.elsevier.com/content/search/sciencedirect"

    def __init__(
        self, api_key: str = None, inst_token: str = None, delay: float = 0.1
    ):
        """
        Initialize Elsevier API client.

        Args:
            api_key: Your Elsevier API key (get from https://dev.elsevier.com/)
            inst_token: Optional institutional token for enhanced access
            delay: Delay between requests (default 0.1s for API)
        """
        super().__init__(delay=delay)

        # Get API key from environment if not provided
        self.api_key = api_key or os.environ.get("ELSEVIER_API_KEY")
        self.inst_token = inst_token or os.environ.get("ELSEVIER_INST_TOKEN")

        if not self.api_key:
            raise ValueError(
                "Elsevier API key required. Get one at https://dev.elsevier.com/ "
                "and set ELSEVIER_API_KEY environment variable"
            )

        # Set headers
        self.session.headers.update(
            {"X-ELS-APIKey": self.api_key, "Accept": "application/json"}
        )

        if self.inst_token:
            self.session.headers["X-ELS-Insttoken"] = self.inst_token

    def search_articles(
        self,
        query: str,
        count: int = 25,
        start: int = 0,
        pub_name: str = None,
        year: str = None,
    ) -> dict[str, Any]:
        """
        Search for articles using ScienceDirect Search API.

        Args:
            query: Search query
            count: Number of results per page (max 100)
            start: Starting index for pagination
            pub_name: Publication name to filter by
            year: Year or year range (e.g., "2023" or "2020-2023")

        Returns:
            API response with search results
        """
        params = {
            "query": query,
            "count": min(count, 100),
            "start": start,
            "view": "COMPLETE",  # Get full metadata
        }

        if pub_name:
            params["pub"] = pub_name

        if year:
            params["date"] = year

        return self._make_request(self.SEARCH_URL, params=params)

    def get_article(
        self, pii: str = None, doi: str = None, include_refs: bool = True
    ) -> dict[str, Any]:
        """
        Retrieve full article metadata by PII or DOI.

        Args:
            pii: Paper Identification Number (PII)
            doi: Digital Object Identifier
            include_refs: Whether to include references

        Returns:
            Full article metadata including abstract
        """
        if not pii and not doi:
            raise ValueError("Either PII or DOI must be provided")

        # Construct URL based on identifier type
        if pii:
            url = f"{self.BASE_URL}/article/pii/{pii}"
        else:
            url = f"{self.BASE_URL}/article/doi/{doi}"

        params = {"view": "FULL", "httpAccept": "application/json"}

        if not include_refs:
            params["view"] = "META_ABS"  # Metadata and abstract only

        return self._make_request(url, params=params)

    def get_article_abstract(self, identifier: str) -> str | None:
        """
        Extract just the abstract from an article.

        Args:
            identifier: PII or DOI

        Returns:
            Abstract text or None if not found
        """
        try:
            # Try as PII first, then DOI
            article = self.get_article(pii=identifier, include_refs=False)
        except Exception:
            try:
                article = self.get_article(doi=identifier, include_refs=False)
            except Exception:
                return None

        # Navigate the response structure
        coredata = article.get("full-text-retrieval-response", {}).get(
            "coredata", {}
        )
        return coredata.get("dc:description")

    def search_and_retrieve(
        self,
        query: str,
        max_results: int = None,
        pub_name: str = None,
        year: str = None,
        include_abstracts: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Search for articles and retrieve their full metadata.

        Args:
            query: Search query
            max_results: Maximum number of articles to retrieve
            pub_name: Publication name filter
            year: Year filter
            include_abstracts: Whether to fetch full article data

        Returns:
            List of article dictionaries with metadata
        """
        articles = []
        start = 0
        count = 25

        while max_results is None or len(articles) < max_results:
            # Search for articles
            response = self.search_articles(
                query=query,
                count=count,
                start=start,
                pub_name=pub_name,
                year=year,
            )

            # Extract results
            results = response.get("search-results", {}).get("entry", [])

            if not results:
                break

            for entry in results:
                if max_results and len(articles) >= max_results:
                    break

                article_data = {
                    "title": entry.get("dc:title"),
                    "authors": entry.get("dc:creator"),
                    "publication": entry.get("prism:publicationName"),
                    "doi": entry.get("prism:doi"),
                    "pii": entry.get("pii"),
                    "url": entry.get("link", [{}])[0].get("@href"),
                    "cover_date": entry.get("prism:coverDate"),
                    "open_access": entry.get("openaccess") == "true",
                }

                # Fetch full article data if requested
                if include_abstracts and (
                    article_data["pii"] or article_data["doi"]
                ):
                    try:
                        full_article = self.get_article(
                            pii=article_data["pii"],
                            doi=article_data["doi"],
                            include_refs=False,
                        )

                        coredata = full_article.get(
                            "full-text-retrieval-response", {}
                        ).get("coredata", {})

                        article_data.update(
                            {
                                "abstract": coredata.get("dc:description"),
                                "keywords": coredata.get("dcterms:subject", []),
                                "page_range": coredata.get("prism:pageRange"),
                            }
                        )

                    except Exception as e:
                        print(f"Error fetching article details: {e}")

                articles.append(article_data)

            start += count

        return articles

    def to_bibtex(self, article: dict[str, Any]) -> str:
        """Convert article data to BibTeX format."""
        # Extract year from cover date
        year = (
            article.get("cover_date", "")[:4]
            if article.get("cover_date")
            else ""
        )

        # Create BibTeX key
        first_author = (
            article.get("authors", "Unknown").split(",")[0].split()[-1]
        )
        key = f"{first_author}{year}" if year else first_author

        # Build BibTeX entry
        bibtex = f"@article{{{key},\n"

        if article.get("title"):
            title = article["title"].replace("{", "").replace("}", "")
            bibtex += f"  title = {{{{{title}}}}},\n"

        if article.get("authors"):
            bibtex += f"  author = {{{article['authors']}}},\n"

        if article.get("publication"):
            bibtex += f"  journal = {{{article['publication']}}},\n"

        if year:
            bibtex += f"  year = {{{year}}},\n"

        if article.get("doi"):
            bibtex += f"  doi = {{{article['doi']}}},\n"

        if article.get("abstract"):
            abstract = (
                article["abstract"]
                .replace("\n", " ")
                .replace("{", "")
                .replace("}", "")
            )
            bibtex += f"  abstract = {{{{{abstract}}}}},\n"

        if article.get("keywords"):
            keywords = (
                ", ".join(article["keywords"])
                if isinstance(article["keywords"], list)
                else article["keywords"]
            )
            bibtex += f"  keywords = {{{keywords}}},\n"

        if article.get("url"):
            bibtex += f"  url = {{{article['url']}}},\n"

        if article.get("open_access"):
            bibtex += "  note = {Open Access},\n"

        bibtex = bibtex.rstrip(",\n") + "\n}"

        return bibtex


# Example usage:
if __name__ == "__main__":
    # Set your API key as environment variable: ELSEVIER_API_KEY=your_key_here

    client = ElsevierAPIClient()

    # Search for BIM papers in Automation in Construction
    articles = client.search_and_retrieve(
        query="BIM",
        pub_name="Automation in Construction",
        year="2023-2024",
        max_results=5,
    )

    # Convert to BibTeX
    for article in articles:
        print(client.to_bibtex(article))
        print()
