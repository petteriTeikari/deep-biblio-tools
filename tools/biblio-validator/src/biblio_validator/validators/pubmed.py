"""PubMed validator implementation."""

import re
from typing import Any
from xml.etree import ElementTree

from ..models.citation import Citation, ValidationResult
from .base import BaseValidator


class PubMedValidator(BaseValidator):
    """Validates citations against PubMed database."""

    SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def get_source_name(self) -> str:
        return "pubmed"

    def validate(self, citation: Citation) -> ValidationResult:
        """Validate citation against PubMed."""
        # Extract components from citation
        year_match = re.search(r"(19|20)\d{2}", citation.key)
        year = year_match.group(0) if year_match else None
        author = re.sub(r"\d{4}$", "", citation.key).rstrip("EtAl")

        if not author:
            return ValidationResult(
                citation=citation,
                is_valid=False,
                confidence=0.0,
                issues=["Could not extract author from citation key"],
            )

        # Search PubMed
        search_params = {
            "db": "pubmed",
            "term": f"{author}[Author]",
            "retmode": "json",
            "retmax": 10,
        }

        if year:
            search_params["term"] += f" AND {year}[Publication Date]"

        try:
            search_data = self._make_request(self.SEARCH_URL, search_params)
            id_list = search_data.get("esearchresult", {}).get("idlist", [])

            if not id_list:
                return ValidationResult(
                    citation=citation,
                    is_valid=False,
                    confidence=0.0,
                    issues=["No matching entries found in PubMed"],
                )

            # Fetch details for matches
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(id_list[:5]),  # Fetch top 5
                "retmode": "xml",
            }

            response = self.session.get(
                self.FETCH_URL, params=fetch_params, timeout=self.timeout
            )
            response.raise_for_status()

            # Parse XML response
            root = ElementTree.fromstring(response.text)
            articles = root.findall(".//PubmedArticle")

            # Find best match
            best_match = self._find_best_match(citation, articles, author, year)

            if best_match:
                return ValidationResult(
                    citation=citation,
                    is_valid=True,
                    confidence=best_match["confidence"],
                    source=self.get_source_name(),
                    matched_entry=best_match["entry"],
                )
            else:
                return ValidationResult(
                    citation=citation,
                    is_valid=False,
                    confidence=0.3,
                    issues=["No sufficiently confident match found in PubMed"],
                    suggestions=self._generate_suggestions(articles),
                )

        except Exception as e:
            return ValidationResult(
                citation=citation,
                is_valid=False,
                confidence=0.0,
                issues=[f"PubMed API error: {str(e)}"],
            )

    def _find_best_match(
        self, citation: Citation, articles: list, author: str, year: str
    ) -> dict[str, Any]:
        """Find the best matching article from PubMed results."""
        best_score = 0
        best_entry = None

        for article in articles:
            score = 0
            article_data = self._extract_article_data(article)

            # Check year match
            if year and article_data["year"] == year:
                score += 0.5

            # Check author match
            if author and article_data["authors"]:
                first_author = article_data["authors"][0].split()[
                    -1
                ]  # Last name
                if (
                    author.lower() in first_author.lower()
                    or first_author.lower() in author.lower()
                ):
                    score += 0.4

            # Check title similarity
            title = article_data["title"].lower()
            citation_words = set(citation.text.lower().split())
            title_words = set(title.split())
            common_words = citation_words & title_words
            if len(common_words) > 2:
                score += 0.1 * min(len(common_words) / 10, 0.1)

            if score > best_score:
                best_score = score
                best_entry = article_data

        if best_score >= 0.7:
            return {"confidence": best_score, "entry": best_entry}

        return None

    def _extract_article_data(self, article) -> dict[str, Any]:
        """Extract relevant data from PubMed article XML."""
        # Extract title
        title_elem = article.find(".//ArticleTitle")
        title = title_elem.text if title_elem is not None else ""

        # Extract authors
        authors = []
        author_list = article.find(".//AuthorList")
        if author_list is not None:
            for author in author_list.findall("Author"):
                last_name = author.find("LastName")
                first_name = author.find("ForeName")
                if last_name is not None:
                    name = last_name.text
                    if first_name is not None:
                        name = f"{first_name.text} {name}"
                    authors.append(name)

        # Extract year
        pub_date = article.find(".//PubDate")
        year = ""
        if pub_date is not None:
            year_elem = pub_date.find("Year")
            if year_elem is not None:
                year = year_elem.text

        # Extract journal
        journal_elem = article.find(".//Journal/Title")
        journal = journal_elem.text if journal_elem is not None else ""

        # Extract PMID
        pmid_elem = article.find(".//PMID")
        pmid = pmid_elem.text if pmid_elem is not None else ""

        return {
            "title": title,
            "authors": authors,
            "author": "; ".join(authors),
            "year": year,
            "journal": journal,
            "pmid": pmid,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
        }

    def _generate_suggestions(self, articles: list) -> list:
        """Generate suggestions from PubMed results."""
        suggestions = []
        for article in articles[:3]:
            data = self._extract_article_data(article)
            if data["authors"] and data["year"]:
                first_author = data["authors"][0].split()[-1]
                suggestions.append(
                    f"Did you mean {first_author} ({data['year']})?"
                )
        return suggestions
