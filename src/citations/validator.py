"""Deterministic citation validation against authoritative sources."""

import logging

from ..api_clients.base import APIClient
from .models import AuthorData, CitationData, DataSource


class DeterministicValidator:
    """Validate citations against authoritative sources with full audit trail."""

    def __init__(
        self,
        crossref_client: APIClient | None = None,
        arxiv_client: APIClient | None = None,
        pubmed_client: APIClient | None = None,
        semantic_scholar_client: APIClient | None = None,
    ):
        """Initialize validator with API clients."""
        self.logger = logging.getLogger(__name__)

        # API clients will be injected or created
        self.crossref_client = crossref_client
        self.arxiv_client = arxiv_client
        self.pubmed_client = pubmed_client
        self.semantic_scholar_client = semantic_scholar_client

        # Validation statistics
        self.stats = {
            "total_validated": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "sources_used": {},
        }

    def validate_citation(
        self, raw_data: dict[str, any], strict: bool = True
    ) -> CitationData:
        """
        Validate a citation deterministically.

        Priority order:
        1. DOI lookup via CrossRef
        2. ArXiv ID lookup
        3. PubMed ID lookup
        4. Semantic Scholar lookup
        5. Title/author fuzzy matching (with warnings)

        Args:
            raw_data: Raw citation data to validate
            strict: If True, require high confidence matches

        Returns:
            CitationData with validation results and audit trail
        """
        self.stats["total_validated"] += 1

        # Create base citation object
        citation = CitationData(
            title=raw_data.get("title"),
            year=self._parse_year(raw_data.get("year")),
            journal=raw_data.get("journal"),
            original_data=raw_data,
        )

        # Extract identifiers
        identifiers = self._extract_identifiers(raw_data)

        # Try validation in priority order
        validated = False

        # 1. DOI validation (most trusted)
        if identifiers.get("doi") and self.crossref_client:
            validated = self._validate_via_doi(citation, identifiers["doi"])

        # 2. ArXiv validation
        if not validated and identifiers.get("arxiv") and self.arxiv_client:
            validated = self._validate_via_arxiv(citation, identifiers["arxiv"])

        # 3. PubMed validation
        if not validated and identifiers.get("pmid") and self.pubmed_client:
            validated = self._validate_via_pubmed(citation, identifiers["pmid"])

        # 4. Semantic Scholar validation
        if not validated and self.semantic_scholar_client:
            # Try by any available identifier
            for id_type, id_value in identifiers.items():
                if id_value:
                    validated = self._validate_via_semantic_scholar(
                        citation, id_type, id_value
                    )
                    if validated:
                        break

        # 5. Fuzzy matching as last resort
        if not validated and raw_data.get("title"):
            self._validate_via_fuzzy_match(citation, raw_data, strict)

        # Update statistics
        if citation.confidence > 0.5:
            self.stats["successful_validations"] += 1
        else:
            self.stats["failed_validations"] += 1

        source_name = citation.source.value
        self.stats["sources_used"][source_name] = (
            self.stats["sources_used"].get(source_name, 0) + 1
        )

        return citation

    def _validate_via_doi(self, citation: CitationData, doi: str) -> bool:
        """Validate using CrossRef DOI lookup."""
        try:
            self.logger.info(f"Validating via DOI: {doi}")

            # Query CrossRef
            result = self.crossref_client.get_by_doi(doi)

            if result:
                # Update citation with validated data
                citation.doi = doi
                citation.title = result.get("title", citation.title)
                citation.year = result.get("year", citation.year)
                citation.journal = result.get("journal", citation.journal)
                citation.volume = result.get("volume")
                citation.issue = result.get("issue")
                citation.pages = result.get("pages")
                citation.publisher = result.get("publisher")

                # Process authors
                if "authors" in result:
                    citation.authors = self._parse_authors(
                        result["authors"], DataSource.CROSSREF
                    )

                # Update tracking
                citation.source = DataSource.CROSSREF
                citation.confidence = 1.0
                citation.add_validation_step(
                    action="validate_doi",
                    source=DataSource.CROSSREF,
                    success=True,
                    message=f"Successfully validated via CrossRef DOI: {doi}",
                    data={"doi": doi, "title": citation.title},
                )

                return True

        except Exception as e:
            self.logger.warning(f"DOI validation failed: {e}")
            citation.add_validation_step(
                action="validate_doi",
                source=DataSource.CROSSREF,
                success=False,
                message=f"DOI validation failed: {str(e)}",
                data={"doi": doi},
            )

        return False

    def _validate_via_arxiv(
        self, citation: CitationData, arxiv_id: str
    ) -> bool:
        """Validate using arXiv API."""
        try:
            self.logger.info(f"Validating via arXiv: {arxiv_id}")

            # Query arXiv
            result = self.arxiv_client.get_by_id(arxiv_id)

            if result:
                # Update citation
                citation.arxiv_id = arxiv_id
                citation.title = result.get("title", citation.title)
                citation.year = result.get("year", citation.year)

                # ArXiv specific fields
                if result.get("journal_ref"):
                    citation.journal = result["journal_ref"]

                # Process authors
                if "authors" in result:
                    citation.authors = self._parse_authors(
                        result["authors"], DataSource.ARXIV
                    )

                # Check if there's a DOI in arXiv data
                if result.get("doi"):
                    citation.doi = result["doi"]

                # Update tracking
                citation.source = DataSource.ARXIV
                citation.confidence = 0.95
                citation.add_validation_step(
                    action="validate_arxiv",
                    source=DataSource.ARXIV,
                    success=True,
                    message=f"Successfully validated via arXiv: {arxiv_id}",
                    data={"arxiv_id": arxiv_id, "title": citation.title},
                )

                return True

        except Exception as e:
            self.logger.warning(f"ArXiv validation failed: {e}")
            citation.add_validation_step(
                action="validate_arxiv",
                source=DataSource.ARXIV,
                success=False,
                message=f"ArXiv validation failed: {str(e)}",
                data={"arxiv_id": arxiv_id},
            )

        return False

    def _validate_via_pubmed(self, citation: CitationData, pmid: str) -> bool:
        """Validate using PubMed API."""
        try:
            self.logger.info(f"Validating via PubMed: {pmid}")

            # Query PubMed
            result = self.pubmed_client.get_by_pmid(pmid)

            if result:
                # Update citation
                citation.pmid = pmid
                citation.title = result.get("title", citation.title)
                citation.year = result.get("year", citation.year)
                citation.journal = result.get("journal", citation.journal)

                # PubMed specific
                if result.get("pmcid"):
                    citation.pmcid = result["pmcid"]
                if result.get("doi"):
                    citation.doi = result["doi"]

                # Process authors
                if "authors" in result:
                    citation.authors = self._parse_authors(
                        result["authors"], DataSource.PUBMED
                    )

                # Update tracking
                citation.source = DataSource.PUBMED
                citation.confidence = 0.95
                citation.add_validation_step(
                    action="validate_pubmed",
                    source=DataSource.PUBMED,
                    success=True,
                    message=f"Successfully validated via PubMed: {pmid}",
                    data={"pmid": pmid, "title": citation.title},
                )

                return True

        except Exception as e:
            self.logger.warning(f"PubMed validation failed: {e}")
            citation.add_validation_step(
                action="validate_pubmed",
                source=DataSource.PUBMED,
                success=False,
                message=f"PubMed validation failed: {str(e)}",
                data={"pmid": pmid},
            )

        return False

    def _validate_via_semantic_scholar(
        self, citation: CitationData, id_type: str, id_value: str
    ) -> bool:
        """Validate using Semantic Scholar API."""
        # Implementation would follow similar pattern
        # Placeholder for now
        return False

    def _validate_via_fuzzy_match(
        self, citation: CitationData, raw_data: dict[str, any], strict: bool
    ) -> None:
        """Last resort fuzzy matching with warnings."""
        self.logger.warning(
            f"Using fuzzy matching for: {raw_data.get('title', 'Unknown')}"
        )

        # Keep original data but mark as low confidence
        citation.source = DataSource.LLM_OUTPUT
        citation.confidence = 0.1

        # Add warning
        citation.add_issue(
            field="validation",
            severity="warning",
            message="Could not validate against authoritative sources",
            expected="Validated citation",
            actual="Unvalidated citation",
        )

        citation.add_validation_step(
            action="fuzzy_match",
            source=DataSource.LLM_OUTPUT,
            success=False,
            message="No authoritative source found, using original data",
            data=raw_data,
        )

    def _extract_identifiers(self, raw_data: dict[str, any]) -> dict[str, str]:
        """Extract all available identifiers."""
        identifiers = {}

        # Direct fields
        if raw_data.get("doi"):
            identifiers["doi"] = raw_data["doi"]
        if raw_data.get("arxiv"):
            identifiers["arxiv"] = raw_data["arxiv"]
        if raw_data.get("pmid"):
            identifiers["pmid"] = raw_data["pmid"]

        # Check URL for identifiers
        if raw_data.get("url"):
            url = raw_data["url"]
            # DOI in URL
            if "doi.org/" in url:
                # Extract DOI without regex
                doi_pos = url.find("doi.org/")
                if doi_pos != -1:
                    identifiers["doi"] = url[doi_pos + 8 :].strip()
            # ArXiv in URL
            elif "arxiv.org" in url:
                # Extract arXiv ID without regex
                abs_pos = url.find("arxiv.org/abs/")
                if abs_pos != -1:
                    arxiv_id = url[abs_pos + 14 :]
                    # Validate format
                    if len(arxiv_id) >= 9 and arxiv_id[4] == ".":
                        # Extract just the ID part (YYYY.NNNNN)
                        parts = arxiv_id.split("/")
                        arxiv_id = parts[0] if parts else arxiv_id
                        if arxiv_id[:4].isdigit() and arxiv_id[5:9].isdigit():
                            identifiers["arxiv"] = (
                                arxiv_id[:10]
                                if len(arxiv_id) >= 10
                                else arxiv_id
                            )

        return identifiers

    def _parse_authors(
        self, authors_data: list[dict[str, any]], source: DataSource
    ) -> list[AuthorData]:
        """Parse author data from API response."""
        authors = []

        for author_dict in authors_data:
            author = AuthorData(
                given_name=author_dict.get("given", ""),
                family_name=author_dict.get("family", ""),
                full_name=author_dict.get("name", ""),
                orcid=author_dict.get("orcid"),
                affiliation=author_dict.get("affiliation"),
                source=source,
            )
            authors.append(author)

        return authors

    def _parse_year(self, year_str: str | None) -> int | None:
        """Parse year from string."""
        if not year_str:
            return None

        try:
            # Handle various year formats
            year_str = str(year_str).strip()
            # Extract 4-digit year
            # Extract 4-digit year without regex
            # Look for 4-digit year starting with 19 or 20
            for word in year_str.split():
                word = word.strip("()[]{}.,;:")
                if len(word) == 4 and word.isdigit():
                    if word.startswith("19") or word.startswith("20"):
                        return int(word)
        except Exception:
            pass

        return None

    def get_validation_stats(self) -> dict[str, any]:
        """Get validation statistics."""
        return self.stats.copy()
