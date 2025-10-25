#!/usr/bin/env python3
"""Validate LLM-generated citations against real metadata sources.

This script assumes ALL author names from LLM-generated markdown are potentially
hallucinated and validates each one against DOI/CrossRef/arXiv metadata.
"""

import json

# import re  # Banned - using string methods instead
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import bibtexparser
import requests
from bibtexparser.bwriter import BibTexWriter


@dataclass
class ValidationResult:
    """Result of validating a citation."""

    citation_id: str
    original_authors: list[str]
    validated_authors: list[str] = field(default_factory=list)
    validation_source: str = ""
    validation_status: str = (
        "unvalidated"  # unvalidated, validated, failed, partial
    )
    issues: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    confidence_score: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "citation_id": self.citation_id,
            "original_authors": self.original_authors,
            "validated_authors": self.validated_authors,
            "validation_source": self.validation_source,
            "validation_status": self.validation_status,
            "issues": self.issues,
            "metadata": self.metadata,
            "confidence_score": self.confidence_score,
        }


class CitationValidator:
    """Validates LLM-generated citations against real sources."""

    def __init__(self, cache_dir: Path | None = None):
        """Initialize the validator with optional cache directory."""
        self.cache_dir = cache_dir or Path(".cache/citation_validation")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "DeepBiblioTools/1.0 (mailto:petteri.teikari@gmail.com) LLM-Citation-Validator"
            }
        )

        # Track API calls for rate limiting
        self.api_calls = {"crossref": 0, "arxiv": 0, "pubmed": 0}

        # Load cache if exists
        self.cache_file = self.cache_dir / "validation_cache.json"
        self.cache = self._load_cache()

    def _load_cache(self) -> dict:
        """Load validation cache from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file) as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_cache(self):
        """Save validation cache to disk."""
        with open(self.cache_file, "w") as f:
            json.dump(self.cache, f, indent=2)

    def extract_doi_from_url(self, url: str) -> str | None:
        """Extract DOI from various academic URLs."""
        url_lower = url.lower()

        # Check various DOI URL patterns
        doi_domains = [
            "doi.org/",
            "dx.doi.org/",
            "link.springer.com/article/",
            "link.springer.com/chapter/",
            "nature.com/articles/",
            "onlinelibrary.wiley.com/doi/abs/",
            "onlinelibrary.wiley.com/doi/full/",
            "onlinelibrary.wiley.com/doi/",
            "sciencedirect.com/science/article/pii/",
            "sciencedirect.com/science/article/abs/pii/",
        ]

        for domain in doi_domains:
            if domain in url_lower:
                # Find the DOI part after the domain
                start_idx = url_lower.find(domain) + len(domain)
                if start_idx < len(url):
                    # Extract the DOI/identifier
                    doi = url[start_idx:].strip()
                    # Remove any trailing whitespace or path elements
                    for end_char in [" ", "\n", "\t", "?", "#"]:
                        if end_char in doi:
                            doi = doi[: doi.find(end_char)]

                    doi = doi.strip("/")

                    # Handle ScienceDirect PIIs
                    if "sciencedirect.com" in url and not doi.startswith("10."):
                        # This is a PII, not a DOI
                        continue

                    if doi:  # Make sure we found something
                        return doi

        # Check for simple doi/ pattern
        if "doi/" in url_lower:
            start_idx = url_lower.find("doi/") + 4
            if start_idx < len(url):
                doi = url[start_idx:].strip()
                for end_char in [" ", "\n", "\t", "?", "#"]:
                    if end_char in doi:
                        doi = doi[: doi.find(end_char)]
                doi = doi.strip("/")
                if doi:
                    return doi

        return None

    def extract_arxiv_id(self, url: str) -> str | None:
        """Extract arXiv ID from URL."""
        url_lower = url.lower()

        # Check if it's an arXiv URL
        if "arxiv.org/" not in url_lower:
            return None

        # Look for abs/, pdf/, or html/ patterns
        for prefix in ["/abs/", "/pdf/", "/html/"]:
            if prefix in url_lower:
                start_idx = url_lower.find(prefix) + len(prefix)
                if start_idx < len(url):
                    arxiv_id = url[start_idx:].strip()

                    # Remove any file extensions or query parameters
                    for end_char in [".", "?", "#", " ", "\n", "\t"]:
                        if end_char in arxiv_id:
                            arxiv_id = arxiv_id[: arxiv_id.find(end_char)]

                    # Validate format: either YYMM.NNNNN or category/NNNNNNN
                    # New format: 4 digits, dot, 4-5 digits
                    if "." in arxiv_id:
                        parts = arxiv_id.split(".")
                        if (
                            len(parts) == 2
                            and parts[0].isdigit()
                            and len(parts[0]) == 4
                            and parts[1][:5].isdigit()
                        ):
                            # Remove version if present (vN at the end)
                            if "v" in parts[1]:
                                v_idx = parts[1].find("v")
                                if (
                                    v_idx > 0
                                    and parts[1][v_idx + 1 :].isdigit()
                                ):
                                    arxiv_id = parts[0] + "." + parts[1][:v_idx]
                            return arxiv_id

                    # Old format: category/7digits
                    elif "/" in arxiv_id:
                        parts = arxiv_id.split("/")
                        if (
                            len(parts) == 2
                            and parts[1][:7].isdigit()
                            and len(parts[1]) >= 7
                        ):
                            # Remove version if present
                            if "v" in parts[1]:
                                v_idx = parts[1].find("v")
                                if (
                                    v_idx >= 7
                                    and parts[1][v_idx + 1 :].isdigit()
                                ):
                                    arxiv_id = parts[0] + "/" + parts[1][:v_idx]
                            else:
                                arxiv_id = parts[0] + "/" + parts[1][:7]
                            return arxiv_id

        return None

    def extract_pmc_id(self, url: str) -> str | None:
        """Extract PMC ID from URL."""
        url_lower = url.lower()

        if "pmc/articles/pmc" in url_lower:
            start_idx = url_lower.find("pmc/articles/pmc") + len(
                "pmc/articles/"
            )
            if start_idx < len(url):
                # Extract PMC followed by digits
                pmc_part = url[start_idx:]
                if pmc_part.startswith("PMC") or pmc_part.startswith("pmc"):
                    # Find where the digits end
                    digits_start = 3  # After "PMC"
                    digits_end = digits_start
                    while (
                        digits_end < len(pmc_part)
                        and pmc_part[digits_end].isdigit()
                    ):
                        digits_end += 1

                    if digits_end > digits_start:
                        return "PMC" + pmc_part[digits_start:digits_end]

        return None

    def validate_via_crossref(self, doi: str) -> ValidationResult:
        """Validate citation via CrossRef API."""
        cache_key = f"crossref:{doi}"
        if cache_key in self.cache:
            return ValidationResult(**self.cache[cache_key])

        url = f"https://api.crossref.org/works/{doi}"

        try:
            self.api_calls["crossref"] += 1
            time.sleep(0.3)  # Rate limiting

            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                message = data.get("message", {})

                # Extract authors
                authors = []
                if "author" in message:
                    for author in message["author"]:
                        family = author.get("family", "")
                        given = author.get("given", "")
                        if family and given:
                            authors.append(f"{family}, {given}")
                        elif family:
                            authors.append(family)

                result = ValidationResult(
                    citation_id=doi,
                    original_authors=[],  # Will be filled by caller
                    validated_authors=authors,
                    validation_source="CrossRef",
                    validation_status="validated" if authors else "failed",
                    metadata={
                        "title": message.get("title", [""])[0]
                        if isinstance(message.get("title"), list)
                        else message.get("title", ""),
                        "journal": message.get("container-title", [""])[0]
                        if isinstance(message.get("container-title"), list)
                        else message.get("container-title", ""),
                        "year": str(
                            message.get("published-print", {}).get(
                                "date-parts", [[]]
                            )[0][0]
                        )
                        if message.get("published-print")
                        else "",
                        "volume": str(message.get("volume", "")),
                        "pages": message.get("page", ""),
                        "doi": doi,
                    },
                    confidence_score=1.0 if authors else 0.0,
                )

                if not authors:
                    result.issues.append(
                        "No authors found in CrossRef metadata"
                    )

                # Cache the result
                self.cache[cache_key] = result.to_dict()
                self._save_cache()

                return result

            elif response.status_code == 404:
                result = ValidationResult(
                    citation_id=doi,
                    original_authors=[],
                    validation_status="failed",
                    issues=["DOI not found in CrossRef"],
                )
                self.cache[cache_key] = result.to_dict()
                self._save_cache()
                return result

            else:
                return ValidationResult(
                    citation_id=doi,
                    original_authors=[],
                    validation_status="failed",
                    issues=[f"CrossRef returned HTTP {response.status_code}"],
                )

        except Exception as e:
            return ValidationResult(
                citation_id=doi,
                original_authors=[],
                validation_status="failed",
                issues=[f"CrossRef error: {str(e)[:100]}"],
            )

    def validate_via_arxiv(self, arxiv_id: str) -> ValidationResult:
        """Validate citation via arXiv API."""
        cache_key = f"arxiv:{arxiv_id}"
        if cache_key in self.cache:
            return ValidationResult(**self.cache[cache_key])

        url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}"

        try:
            self.api_calls["arxiv"] += 1
            time.sleep(0.5)  # arXiv rate limiting

            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                # Parse arXiv XML response
                import xml.etree.ElementTree as ET

                root = ET.fromstring(response.text)

                # Find entry
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                entry = root.find(".//atom:entry", ns)

                if entry is not None:
                    # Extract authors
                    authors = []
                    for author_elem in entry.findall(".//atom:author", ns):
                        name_elem = author_elem.find("atom:name", ns)
                        if name_elem is not None and name_elem.text:
                            # arXiv gives "FirstName LastName", convert to "LastName, FirstName"
                            parts = name_elem.text.strip().split()
                            if len(parts) >= 2:
                                last_name = parts[-1]
                                first_names = " ".join(parts[:-1])
                                authors.append(f"{last_name}, {first_names}")
                            else:
                                authors.append(name_elem.text.strip())

                    # Extract other metadata
                    title_elem = entry.find("atom:title", ns)
                    title = (
                        title_elem.text.strip()
                        if title_elem is not None
                        else ""
                    )

                    published_elem = entry.find("atom:published", ns)
                    year = ""
                    if published_elem is not None and published_elem.text:
                        year = published_elem.text[:4]

                    result = ValidationResult(
                        citation_id=arxiv_id,
                        original_authors=[],
                        validated_authors=authors,
                        validation_source="arXiv",
                        validation_status="validated" if authors else "failed",
                        metadata={
                            "title": title,
                            "year": year,
                            "arxiv_id": arxiv_id,
                            "url": f"https://arxiv.org/abs/{arxiv_id}",
                        },
                        confidence_score=1.0 if authors else 0.0,
                    )

                    if not authors:
                        result.issues.append(
                            "No authors found in arXiv metadata"
                        )

                    # Cache the result
                    self.cache[cache_key] = result.to_dict()
                    self._save_cache()

                    return result

                else:
                    result = ValidationResult(
                        citation_id=arxiv_id,
                        original_authors=[],
                        validation_status="failed",
                        issues=["arXiv ID not found"],
                    )
                    self.cache[cache_key] = result.to_dict()
                    self._save_cache()
                    return result

            else:
                return ValidationResult(
                    citation_id=arxiv_id,
                    original_authors=[],
                    validation_status="failed",
                    issues=[f"arXiv returned HTTP {response.status_code}"],
                )

        except Exception as e:
            return ValidationResult(
                citation_id=arxiv_id,
                original_authors=[],
                validation_status="failed",
                issues=[f"arXiv error: {str(e)[:100]}"],
            )

    def compare_authors(
        self, original: list[str], validated: list[str]
    ) -> tuple[float, list[str]]:
        """Compare original authors with validated ones and return confidence score."""
        if not original or not validated:
            return 0.0, ["No authors to compare"]

        issues = []
        matches = 0

        # Normalize author names for comparison
        def normalize_name(name: str) -> str:
            # Remove punctuation and convert to lowercase
            normalized = name.lower()
            # Remove common punctuation
            for punct in ".,;:!?'\"()[]{}":
                normalized = normalized.replace(punct, "")
            # Replace hyphens and underscores with spaces
            normalized = normalized.replace("-", " ").replace("_", " ")
            # Normalize whitespace
            return " ".join(normalized.split())

        original_normalized = [normalize_name(a) for a in original]
        validated_normalized = [normalize_name(a) for a in validated]

        # Check each original author
        for i, orig in enumerate(original):
            orig_norm = original_normalized[i]
            found = False

            for j, val_norm in enumerate(validated_normalized):
                # Check if last name matches
                orig_parts = orig_norm.split()
                val_parts = val_norm.split()

                if orig_parts and val_parts:
                    # Simple last name match
                    if (
                        orig_parts[-1] == val_parts[0]
                        or orig_parts[0] == val_parts[0]
                    ):
                        found = True
                        matches += 1

                        # Check if we have more complete name in validated
                        if len(val_parts) > len(orig_parts):
                            issues.append(
                                f"Incomplete name '{orig}' validated as '{validated[j]}'"
                            )
                        break

            if not found:
                issues.append(
                    f"Author '{orig}' not found in validated metadata"
                )

        # Check for extra authors in validated that weren't in original
        if len(validated) > len(original):
            issues.append(
                f"Found {len(validated) - len(original)} additional authors in metadata"
            )

        # Check for "et al" in original
        if any("et al" in a.lower() for a in original):
            issues.append(
                "Original contained 'et al' - full author list retrieved"
            )

        # Calculate confidence score
        if not original:
            confidence = 0.0
        else:
            confidence = matches / len(original)

        return confidence, issues

    def validate_citation(
        self,
        citation_text: str,
        url: str = "",
        original_authors: list[str] = None,
    ) -> ValidationResult:
        """Validate a single citation."""
        # Default result
        result = ValidationResult(
            citation_id=citation_text,
            original_authors=original_authors or [],
            validation_status="unvalidated",
        )

        # Try to extract identifiers
        doi = None
        arxiv_id = None
        pmc_id = None

        if url:
            doi = self.extract_doi_from_url(url)
            if not doi:
                arxiv_id = self.extract_arxiv_id(url)
            if not arxiv_id:
                pmc_id = self.extract_pmc_id(url)

        # Try validation in order of preference
        if doi:
            result = self.validate_via_crossref(doi)
            result.original_authors = original_authors or []
        elif arxiv_id:
            result = self.validate_via_arxiv(arxiv_id)
            result.original_authors = original_authors or []
        elif pmc_id:
            # TODO: Implement PMC validation
            result.issues.append("PMC validation not yet implemented")
        else:
            result.issues.append("No DOI, arXiv ID, or PMC ID found in URL")

        # Compare authors if we have both original and validated
        if result.original_authors and result.validated_authors:
            confidence, comparison_issues = self.compare_authors(
                result.original_authors, result.validated_authors
            )
            result.confidence_score = confidence
            result.issues.extend(comparison_issues)

            # Update status based on confidence
            if confidence >= 0.8:
                result.validation_status = "validated"
            elif confidence >= 0.5:
                result.validation_status = "partial"
            else:
                result.validation_status = "failed"
                result.issues.append(f"Low confidence score: {confidence:.2f}")

        return result

    def validate_bibliography_file(
        self, bib_file: Path
    ) -> dict[str, ValidationResult]:
        """Validate all entries in a bibliography file."""
        print(f"Validating bibliography: {bib_file}")

        with open(bib_file, encoding="utf-8") as f:
            bib_database = bibtexparser.load(f)

        results = {}
        total = len(bib_database.entries)

        print(f"Total entries to validate: {total}")
        print("This assumes ALL author names may be hallucinated!\n")

        for i, entry in enumerate(bib_database.entries):
            entry_id = entry.get("ID", f"entry_{i}")

            if (i + 1) % 10 == 0:
                print(f"Progress: {i + 1}/{total} entries validated...")

            # Extract original authors
            original_authors = []
            if "author" in entry:
                # Parse BibTeX author field
                authors_str = entry["author"]
                # Handle both "and" and "&" separators
                authors_str = authors_str.replace(" & ", " and ")
                original_authors = [
                    a.strip() for a in authors_str.split(" and ")
                ]

            # Get URL and DOI
            url = entry.get("url", "")
            doi = entry.get("doi", "")

            # If we have DOI in the entry, use it
            if doi and not url:
                url = f"https://doi.org/{doi}"

            # Validate
            result = self.validate_citation(
                citation_text=entry_id,
                url=url,
                original_authors=original_authors,
            )

            results[entry_id] = result

        # Print summary
        print(f"\n{'=' * 60}")
        print("VALIDATION SUMMARY")
        print(f"{'=' * 60}\n")

        validated = sum(
            1 for r in results.values() if r.validation_status == "validated"
        )
        partial = sum(
            1 for r in results.values() if r.validation_status == "partial"
        )
        failed = sum(
            1 for r in results.values() if r.validation_status == "failed"
        )
        unvalidated = sum(
            1 for r in results.values() if r.validation_status == "unvalidated"
        )

        print(f"Validated:    {validated:4d} ({validated / total * 100:.1f}%)")
        print(f"Partial:      {partial:4d} ({partial / total * 100:.1f}%)")
        print(f"Failed:       {failed:4d} ({failed / total * 100:.1f}%)")
        print(
            f"Unvalidated:  {unvalidated:4d} ({unvalidated / total * 100:.1f}%)"
        )
        print(f"{'=' * 40}")
        print(f"Total:        {total:4d}")

        # Show examples of issues
        print(f"\n{'=' * 60}")
        print("CRITICAL ISSUES FOUND")
        print(f"{'=' * 60}\n")

        # Hallucinated authors (low confidence)
        hallucinated = [
            (k, v)
            for k, v in results.items()
            if v.confidence_score < 0.5 and v.validated_authors
        ]
        if hallucinated:
            print(
                f"\nLikely Hallucinated Authors ({len(hallucinated)} entries):"
            )
            for entry_id, result in hallucinated[:5]:
                print(f"\n  {entry_id}:")
                print(
                    f"    Original:  {', '.join(result.original_authors[:3])}"
                )
                print(
                    f"    Validated: {', '.join(result.validated_authors[:3])}"
                )
                print(f"    Issues:    {'; '.join(result.issues[:2])}")

        # Missing metadata
        no_validation = [
            (k, v)
            for k, v in results.items()
            if v.validation_status == "unvalidated"
        ]
        if no_validation:
            print(f"\n\nNo Validation Possible ({len(no_validation)} entries):")
            for entry_id, result in no_validation[:5]:
                print(f"  {entry_id}: {'; '.join(result.issues)}")

        return results

    def generate_validated_bibliography(
        self,
        bib_file: Path,
        results: dict[str, ValidationResult],
        output_file: Path | None = None,
    ) -> Path:
        """Generate a new bibliography with validated data and notes."""
        if output_file is None:
            output_file = bib_file.parent / f"{bib_file.stem}_validated.bib"

        print(f"\nGenerating validated bibliography: {output_file}")

        with open(bib_file, encoding="utf-8") as f:
            bib_database = bibtexparser.load(f)

        # Update entries with validated data
        for entry in bib_database.entries:
            entry_id = entry.get("ID", "")
            if entry_id in results:
                result = results[entry_id]

                # Update authors if we have better data
                if result.validated_authors and result.validation_status in [
                    "validated",
                    "partial",
                ]:
                    entry["author"] = " and ".join(result.validated_authors)

                # Update other metadata if available
                if result.metadata:
                    for field in [
                        "title",
                        "journal",
                        "year",
                        "volume",
                        "pages",
                    ]:
                        if field in result.metadata and result.metadata[field]:
                            entry[field] = str(result.metadata[field])

                # Add validation notes
                notes = []

                if result.validation_status == "validated":
                    notes.append(f"Validated via {result.validation_source}")
                elif result.validation_status == "partial":
                    notes.append(
                        f"Partially validated via {result.validation_source}"
                    )
                elif result.validation_status == "failed":
                    notes.append(
                        "VALIDATION FAILED - authors may be hallucinated!"
                    )
                else:
                    notes.append(
                        "Could not validate - manual verification needed"
                    )

                if result.confidence_score < 0.5 and result.validated_authors:
                    notes.append(
                        f"LOW CONFIDENCE ({result.confidence_score:.2f}) - likely hallucination"
                    )

                if result.issues:
                    notes.extend(result.issues[:2])  # Add first 2 issues

                # Update note field
                if notes:
                    existing_note = entry.get("note", "")
                    if existing_note:
                        entry["note"] = existing_note + "; " + "; ".join(notes)
                    else:
                        entry["note"] = "; ".join(notes)

        # Write output
        writer = BibTexWriter()
        writer.indent = "  "
        writer.order_entries_by = "ID"
        writer.align_values = True

        with open(output_file, "w", encoding="utf-8") as f:
            bibtexparser.dump(bib_database, f, writer)

        return output_file


def validate_markdown_citations(md_file: Path) -> list[dict]:
    """Extract and validate citations from a markdown file."""
    print(f"Extracting citations from: {md_file}")

    with open(md_file, encoding="utf-8") as f:
        content = f.read()

    # Extract citations (simple pattern matching for now)
    # Format: [Author et al. Year](URL)
    citations = []

    # Find all markdown links that look like citations
    i = 0
    while i < len(content):
        # Look for [text](url) pattern
        if content[i] == "[" and i > 0:
            # Find closing bracket
            bracket_end = content.find("]", i + 1)
            if (
                bracket_end > i
                and bracket_end + 1 < len(content)
                and content[bracket_end + 1] == "("
            ):
                # Find closing parenthesis
                paren_end = content.find(")", bracket_end + 2)
                if paren_end > bracket_end:
                    # Extract parts
                    text_part = content[i + 1 : bracket_end]
                    url_part = content[bracket_end + 2 : paren_end]

                    # Check if it looks like a citation (has year)
                    # Split by spaces and check last part for year
                    parts = text_part.strip().split()
                    if parts and len(parts[-1]) >= 4:
                        potential_year = parts[-1]
                        # Check if last part is a year (4 digits, optionally followed by a letter)
                        is_year = False
                        if (
                            len(potential_year) >= 4
                            and potential_year[:4].isdigit()
                        ):
                            year_num = int(potential_year[:4])
                            if (
                                1900 <= year_num <= 2100
                            ):  # Reasonable year range
                                is_year = True
                                year = potential_year
                                author_text = " ".join(parts[:-1])

                        if is_year and author_text:
                            # Parse authors
                            authors = []
                            # Handle "et al"
                            if " et al" in author_text:
                                # Only extract first author
                                first_author = author_text.replace(
                                    " et al", ""
                                ).strip()
                                authors = [first_author]
                            else:
                                # Handle multiple authors
                                author_text = author_text.replace(
                                    " & ", " and "
                                )
                                authors = [
                                    a.strip()
                                    for a in author_text.split(" and ")
                                ]

                            citations.append(
                                {
                                    "text": content[i : paren_end + 1],
                                    "authors": authors,
                                    "year": year,
                                    "url": url_part,
                                }
                            )

                    i = paren_end + 1
                    continue

        i += 1

    print(f"Found {len(citations)} citations to validate")

    # Validate each citation
    validator = CitationValidator()
    results = []

    for i, citation in enumerate(citations):
        if (i + 1) % 10 == 0:
            print(f"Validating citation {i + 1}/{len(citations)}...")

        result = validator.validate_citation(
            citation_text=citation["text"],
            url=citation["url"],
            original_authors=citation["authors"],
        )

        results.append({"citation": citation, "validation": result})

    # Print summary
    print(f"\n{'=' * 60}")
    print("MARKDOWN CITATION VALIDATION SUMMARY")
    print(f"{'=' * 60}\n")

    validated = sum(
        1 for r in results if r["validation"].validation_status == "validated"
    )
    failed = sum(
        1 for r in results if r["validation"].validation_status == "failed"
    )

    print(f"Total citations:     {len(citations)}")
    print(f"Validated:          {validated}")
    print(f"Failed/Suspicious:  {failed}")

    # Show examples of problematic citations
    problematic = [r for r in results if r["validation"].confidence_score < 0.5]
    if problematic:
        print("\n\nLIKELY HALLUCINATED CITATIONS:")
        for r in problematic[:10]:
            print(f"\n{r['citation']['text']}")
            val = r["validation"]
            if val.validated_authors:
                print(f"  Should be: {', '.join(val.validated_authors[:3])}")
            print(f"  Issues: {'; '.join(val.issues[:2])}")

    return results


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate LLM-generated citations against real sources"
    )
    parser.add_argument("input", type=Path, help="Input file (.bib or .md)")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output file for validated bibliography",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        help="Directory for caching validation results",
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: File not found: {args.input}")
        return 1

    # Create validator
    validator = CitationValidator(cache_dir=args.cache_dir)

    try:
        if args.input.suffix == ".bib":
            # Validate bibliography file
            results = validator.validate_bibliography_file(args.input)

            # Generate validated bibliography
            output_file = validator.generate_validated_bibliography(
                args.input, results, args.output
            )

            print(f"\nValidated bibliography written to: {output_file}")

            # Show API usage
            print("\nAPI calls made:")
            for api, count in validator.api_calls.items():
                if count > 0:
                    print(f"  {api}: {count}")

        elif args.input.suffix == ".md":
            # Validate markdown citations
            results = validate_markdown_citations(args.input)

            # Save results
            output_file = (
                args.output
                or args.input.parent / f"{args.input.stem}_validation.json"
            )
            with open(output_file, "w") as f:
                json.dump(
                    [
                        {
                            "citation": r["citation"],
                            "validation": r["validation"].to_dict(),
                        }
                        for r in results
                    ],
                    f,
                    indent=2,
                )

            print(f"\nValidation results written to: {output_file}")

        else:
            print(f"Error: Unsupported file type: {args.input.suffix}")
            return 1

        return 0

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
