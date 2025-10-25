"""Enhanced bibliography validator with batch API processing."""

import logging
from typing import Any

from ..api_clients.arxiv import ArXivClient
from ..api_clients.crossref import CrossRefClient
from ..utils.api_clients.batch_processor import (
    BatchArXivProcessor,
    BatchDOIProcessor,
)
from .core import Bibliography, BibliographyEntry
from .validator import BibliographyValidator


class BatchBibliographyValidator(BibliographyValidator):
    """Bibliography validator with batch API processing for improved performance."""

    def __init__(
        self,
        crossref_client: CrossRefClient | None = None,
        arxiv_client: ArXivClient | None = None,
        batch_size: int = 20,
        max_workers: int = 5,
        logger: logging.Logger | None = None,
    ):
        """Initialize batch validator.

        Args:
            crossref_client: CrossRef API client
            arxiv_client: arXiv API client
            batch_size: Number of items to process per batch
            max_workers: Maximum concurrent API requests
            logger: Logger instance
        """
        super().__init__()
        self.logger = logger or logging.getLogger(__name__)

        # Initialize API clients if not provided
        self.crossref_client = crossref_client or CrossRefClient()
        self.arxiv_client = arxiv_client or ArXivClient()

        # Initialize batch processors
        self.doi_processor = BatchDOIProcessor(
            self.crossref_client,
            batch_size=batch_size,
            max_workers=max_workers,
            logger=self.logger,
        )

        self.arxiv_processor = BatchArXivProcessor(
            self.arxiv_client,
            batch_size=batch_size,
            max_workers=max_workers,
            logger=self.logger,
        )

    def process(self, bibliography: Bibliography) -> list[str]:
        """Process bibliography with batch API validation.

        Args:
            bibliography: Bibliography to validate

        Returns:
            List of validation errors
        """
        # First, do basic validation
        errors = super().process(bibliography)

        # Collect all DOIs and arXiv IDs for batch processing
        dois_to_validate = []
        arxiv_ids_to_validate = []
        entry_lookup = {}

        for entry in bibliography:
            # Collect DOI
            doi = entry.get_field("doi")
            if doi:
                dois_to_validate.append(doi)
                entry_lookup[f"doi:{doi}"] = entry

            # Collect arXiv ID
            eprint = entry.get_field("eprint")
            if eprint and entry.get_field("archivePrefix") == "arXiv":
                arxiv_ids_to_validate.append(eprint)
                entry_lookup[f"arxiv:{eprint}"] = entry

            # Check URL for DOI or arXiv
            url = entry.get_field("url")
            if url:
                if "doi.org/" in url and not doi:
                    extracted_doi = url.split("doi.org/")[-1].strip("/")
                    dois_to_validate.append(extracted_doi)
                    entry_lookup[f"doi:{extracted_doi}"] = entry
                elif "arxiv.org/abs/" in url and not eprint:
                    extracted_id = url.split("arxiv.org/abs/")[-1].strip("/")
                    arxiv_ids_to_validate.append(extracted_id)
                    entry_lookup[f"arxiv:{extracted_id}"] = entry

        # Batch validate DOIs
        if dois_to_validate:
            self.logger.info(f"Batch validating {len(dois_to_validate)} DOIs")
            doi_results = self._batch_validate_dois(
                dois_to_validate, entry_lookup
            )
            errors.extend(doi_results)

        # Batch validate arXiv IDs
        if arxiv_ids_to_validate:
            self.logger.info(
                f"Batch validating {len(arxiv_ids_to_validate)} arXiv IDs"
            )
            arxiv_results = self._batch_validate_arxiv(
                arxiv_ids_to_validate, entry_lookup
            )
            errors.extend(arxiv_results)

        return errors

    def _batch_validate_dois(
        self, dois: list[str], entry_lookup: dict[str, BibliographyEntry]
    ) -> list[str]:
        """Validate DOIs in batch.

        Args:
            dois: List of DOIs to validate
            entry_lookup: Mapping from identifier to entry

        Returns:
            List of validation errors
        """
        errors = []

        # Process DOIs in batch
        doi_metadata = self.doi_processor.process_dois(dois)

        # Check results
        for doi in dois:
            entry = entry_lookup.get(f"doi:{doi}")
            if not entry:
                continue

            if doi not in doi_metadata:
                errors.append(
                    f"Entry '{entry.key}': DOI '{doi}' not found in CrossRef"
                )
                continue

            # Validate metadata matches
            metadata = doi_metadata[doi]
            validation_errors = self._validate_against_crossref(entry, metadata)
            errors.extend(validation_errors)

        return errors

    def _batch_validate_arxiv(
        self, arxiv_ids: list[str], entry_lookup: dict[str, BibliographyEntry]
    ) -> list[str]:
        """Validate arXiv IDs in batch.

        Args:
            arxiv_ids: List of arXiv IDs to validate
            entry_lookup: Mapping from identifier to entry

        Returns:
            List of validation errors
        """
        errors = []

        # Process arXiv IDs in batch
        arxiv_metadata = self.arxiv_processor.process_arxiv_ids(arxiv_ids)

        # Check results
        for arxiv_id in arxiv_ids:
            entry = entry_lookup.get(f"arxiv:{arxiv_id}")
            if not entry:
                continue

            if arxiv_id not in arxiv_metadata:
                errors.append(
                    f"Entry '{entry.key}': arXiv ID '{arxiv_id}' not found"
                )
                continue

            # Validate metadata matches
            metadata = arxiv_metadata[arxiv_id]
            validation_errors = self._validate_against_arxiv(entry, metadata)
            errors.extend(validation_errors)

        return errors

    def _validate_against_crossref(
        self, entry: BibliographyEntry, metadata: dict[str, Any]
    ) -> list[str]:
        """Validate entry against CrossRef metadata.

        Args:
            entry: Bibliography entry
            metadata: CrossRef metadata

        Returns:
            List of validation errors
        """
        errors = []
        key = entry.key

        # Check title match
        if "title" in metadata:
            crossref_title = (
                metadata["title"][0]
                if isinstance(metadata["title"], list)
                else metadata["title"]
            )
            entry_title = entry.get_field("title", "").lower()

            if not self._fuzzy_match(entry_title, crossref_title.lower()):
                errors.append(
                    f"Entry '{key}': Title mismatch. "
                    f"Entry: '{entry.get_field('title')}', "
                    f"CrossRef: '{crossref_title}'"
                )

        # Check authors
        if "author" in metadata:
            crossref_authors = self._extract_crossref_authors(
                metadata["author"]
            )
            entry_authors = entry.get_field("author", "")

            if "et al" in entry_authors.lower():
                errors.append(
                    f"Entry '{key}': Author field contains 'et al.' - "
                    f"full author list should be: {', '.join(crossref_authors)}"
                )

        # Check year
        if "published-print" in metadata or "published-online" in metadata:
            pub_data = metadata.get("published-print") or metadata.get(
                "published-online"
            )
            if pub_data and "date-parts" in pub_data:
                crossref_year = str(pub_data["date-parts"][0][0])
                entry_year = entry.get_field("year", "")

                if entry_year != crossref_year:
                    errors.append(
                        f"Entry '{key}': Year mismatch. "
                        f"Entry: {entry_year}, CrossRef: {crossref_year}"
                    )

        return errors

    def _validate_against_arxiv(
        self, entry: BibliographyEntry, metadata: dict[str, Any]
    ) -> list[str]:
        """Validate entry against arXiv metadata.

        Args:
            entry: Bibliography entry
            metadata: arXiv metadata

        Returns:
            List of validation errors
        """
        errors = []
        key = entry.key

        # Similar validation logic for arXiv
        if "title" in metadata:
            arxiv_title = metadata["title"]
            entry_title = entry.get_field("title", "").lower()

            if not self._fuzzy_match(entry_title, arxiv_title.lower()):
                errors.append(f"Entry '{key}': Title mismatch with arXiv")

        if "authors" in metadata:
            arxiv_authors = metadata["authors"]
            entry_authors = entry.get_field("author", "")

            if "et al" in entry_authors.lower() and len(arxiv_authors) > 1:
                errors.append(
                    f"Entry '{key}': Author field contains 'et al.' - "
                    f"see arXiv for full author list"
                )

        return errors

    def _fuzzy_match(
        self, str1: str, str2: str, threshold: float = 0.85
    ) -> bool:
        """Check if two strings are similar enough.

        Args:
            str1: First string
            str2: Second string
            threshold: Similarity threshold (0-1)

        Returns:
            True if strings are similar enough
        """
        # Simple implementation - could use more sophisticated matching
        # Remove punctuation and extra spaces without regex
        # import re  # Banned

        # Keep only alphanumeric and whitespace characters
        clean1_chars = []
        for char in str1:
            if char.isalnum() or char.isspace():
                clean1_chars.append(char.lower())
        clean1 = "".join(clean1_chars).strip()

        clean2_chars = []
        for char in str2:
            if char.isalnum() or char.isspace():
                clean2_chars.append(char.lower())
        clean2 = "".join(clean2_chars).strip()

        # Check if one contains the other (common for subtitles)
        if clean1 in clean2 or clean2 in clean1:
            return True

        # Check word overlap
        words1 = set(clean1.split())
        words2 = set(clean2.split())

        if not words1 or not words2:
            return False

        overlap = len(words1 & words2)
        total = len(words1 | words2)

        return overlap / total >= threshold

    def _extract_crossref_authors(
        self, author_data: list[dict[str, str]]
    ) -> list[str]:
        """Extract author names from CrossRef data.

        Args:
            author_data: List of author dictionaries from CrossRef

        Returns:
            List of formatted author names
        """
        authors = []

        for author in author_data:
            if "family" in author:
                name = author["family"]
                if "given" in author:
                    name = f"{author['family']}, {author['given']}"
                authors.append(name)

        return authors
