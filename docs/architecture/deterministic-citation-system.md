# Deterministic Citation System Architecture

## Problem Statement

LLMs frequently hallucinate citation details, especially:
- Author names (e.g., "Bhat et al" when it's actually "Marsal et al")
- Publication years
- Journal/conference names
- Even paper titles

This system must provide **deterministic, verifiable** citation extraction and validation.

## Design Principles

1. **Trust URLs/DOIs over text**: Papers/URLs are more reliable than author names in LLM output
2. **Always validate against authoritative sources**: CrossRef, arXiv, PubMed
3. **Fail loudly**: Never silently accept potentially hallucinated data
4. **Provide audit trails**: Show exactly where each piece of data came from

## Proposed Architecture

### 1. Citation Data Model

```python
# src/citations/models.py
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Dict, Any

class DataSource(Enum):
    """Source of citation data with trust levels."""
    CROSSREF = "crossref"      # Most trusted for DOIs
    ARXIV = "arxiv"            # Trusted for arXiv papers
    PUBMED = "pubmed"          # Trusted for biomedical
    ZOTERO = "zotero"          # Translation server
    LLM_OUTPUT = "llm"         # Least trusted
    USER_PROVIDED = "user"     # Manual corrections

@dataclass
class AuthorData:
    """Verified author information."""
    given_name: str
    family_name: str
    orcid: Optional[str] = None
    source: DataSource = DataSource.LLM_OUTPUT
    confidence: float = 0.0  # 0-1 confidence score

@dataclass
class CitationData:
    """Deterministic citation data."""
    # Identifiers (most reliable)
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    pmid: Optional[str] = None
    url: Optional[str] = None

    # Validated metadata
    title: Optional[str] = None
    authors: List[AuthorData] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    volume: Optional[str] = None
    pages: Optional[str] = None

    # Tracking
    source: DataSource = DataSource.LLM_OUTPUT
    validation_log: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.authors is None:
            self.authors = []
        if self.validation_log is None:
            self.validation_log = []
```

### 2. Deterministic Validation Pipeline

```python
# src/citations/validator.py
class DeterministicCitationValidator:
    """Validates citations against authoritative sources."""

    def __init__(self):
        self.crossref_client = CrossRefClient()
        self.arxiv_client = ArXivClient()
        self.pubmed_client = PubMedClient()

    def validate_citation(self, raw_citation: Dict[str, Any]) -> CitationData:
        """
        Deterministically validate a citation.

        Priority order:
        1. DOI lookup via CrossRef
        2. ArXiv ID lookup
        3. PubMed ID lookup
        4. URL-based validation
        5. Fuzzy title matching (with warnings)
        """
        citation = CitationData()

        # Step 1: Extract identifiers
        if doi := self._extract_doi(raw_citation):
            citation.doi = doi
            self._validate_via_doi(citation)
        elif arxiv_id := self._extract_arxiv_id(raw_citation):
            citation.arxiv_id = arxiv_id
            self._validate_via_arxiv(citation)
        elif pmid := self._extract_pmid(raw_citation):
            citation.pmid = pmid
            self._validate_via_pubmed(citation)
        else:
            # Last resort - validate by title/authors
            self._validate_via_metadata(citation, raw_citation)

        return citation
```

### 3. Hallucination Detection

```python
# src/citations/hallucination_detector.py
class HallucinationDetector:
    """Detects potential hallucinations in citations."""

    # Common hallucination patterns
    SUSPICIOUS_PATTERNS = {
        'author': [
            r'\bet al\.?\b',           # "et al" in author field
            r'^[A-Z]\.$',              # Single letter "authors"
            r'^\W+$',                  # Non-alphanumeric
            r'^(Author|Unknown|TBD)$', # Placeholder text
        ],
        'title': [
            r'^(Title|Paper|Article)',  # Generic titles
            r'\.\.\.$',                 # Ellipsis (truncated)
            r'^\[.*\]$',                # Bracketed placeholders
        ],
        'journal': [
            r'^(Journal|Conference|Proceedings)$',  # Generic names
            r'^International Conference$',          # Too generic
        ]
    }

    def check_citation(self, citation: Dict[str, Any]) -> List[str]:
        """Return list of potential hallucinations."""
        issues = []

        # Check authors
        if authors := citation.get('author', ''):
            if self._is_hallucinated_authors(authors):
                issues.append(f"Suspicious author format: '{authors}'")

        # Check if claimed authors match validated data
        if citation.source != DataSource.LLM_OUTPUT:
            if not self._authors_match(citation.authors, authors):
                issues.append(
                    f"Author mismatch: LLM said '{authors}' but "
                    f"{citation.source.value} shows '{self._format_authors(citation.authors)}'"
                )

        return issues
```

### 4. Deterministic CLI Interface

```python
# src/cli_deterministic.py
@click.group()
def deterministic():
    """Deterministic citation operations."""
    pass

@deterministic.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', help='Output file for validated citations')
@click.option('--format', type=click.Choice(['json', 'bibtex']), default='bibtex')
def validate_citations(input_file, output, format):
    """Validate citations deterministically."""

    # Load citations
    with open(input_file) as f:
        if input_file.endswith('.json'):
            citations = json.load(f)
        else:
            # Parse BibTeX
            citations = parse_bibtex(f.read())

    # Validate each citation
    validator = DeterministicCitationValidator()
    detector = HallucinationDetector()

    results = []
    for cite in citations:
        # Validate
        validated = validator.validate_citation(cite)

        # Check for hallucinations
        issues = detector.check_citation(cite, validated)

        if issues:
            click.echo(f"⚠️  Citation '{cite.get('id', 'unknown')}' has issues:")
            for issue in issues:
                click.echo(f"   - {issue}")

        results.append({
            'original': cite,
            'validated': validated,
            'issues': issues
        })

    # Output results
    if output:
        save_results(results, output, format)
```

### 5. Agent-Friendly Interface

```python
# src/agents/citation_tools.py
from typing import Dict, Any, List

class CitationTools:
    """Deterministic tools for citation processing."""

    @staticmethod
    @tool_definition(
        name="extract_citations",
        description="Extract citations from text deterministically",
        parameters={
            "text": "string",
            "format": "enum[markdown, latex, plain]"
        }
    )
    def extract_citations(text: str, format: str = "plain") -> List[Dict[str, Any]]:
        """Extract citations with confidence scores."""
        extractor = CitationExtractor(format=format)
        raw_citations = extractor.extract(text)

        results = []
        for cite in raw_citations:
            # Always validate immediately
            validated = DeterministicCitationValidator().validate_citation(cite)

            results.append({
                "raw": cite,
                "validated": validated.to_dict(),
                "confidence": validated.confidence,
                "source": validated.source.value,
                "issues": HallucinationDetector().check_citation(cite, validated)
            })

        return results

    @staticmethod
    @tool_definition(
        name="fix_hallucinated_authors",
        description="Replace hallucinated authors with validated data",
        parameters={
            "bibtex_file": "string",
            "output_file": "string"
        }
    )
    def fix_hallucinated_authors(bibtex_file: str, output_file: str) -> Dict[str, Any]:
        """Fix author hallucinations deterministically."""
        bib = Bibliography.from_file(bibtex_file)
        validator = DeterministicCitationValidator()

        fixes = []
        for entry in bib:
            if entry.get_field('doi') or entry.get_field('arxiv'):
                validated = validator.validate_citation(entry.to_dict())

                if validated.authors and validated.source != DataSource.LLM_OUTPUT:
                    old_authors = entry.get_field('author')
                    new_authors = format_authors_bibtex(validated.authors)

                    if old_authors != new_authors:
                        entry.set_field('author', new_authors)
                        fixes.append({
                            'key': entry.key,
                            'old': old_authors,
                            'new': new_authors,
                            'source': validated.source.value
                        })

        bib.to_file(output_file)

        return {
            "status": "success",
            "fixes_applied": len(fixes),
            "details": fixes
        }
```

## Implementation Priorities

1. **Phase 1: Core Models & Validation**
   - Citation data model with source tracking
   - CrossRef/arXiv/PubMed clients
   - Deterministic validation pipeline

2. **Phase 2: Hallucination Detection**
   - Pattern-based detection
   - Author name validation
   - Confidence scoring

3. **Phase 3: Agent Interface**
   - Tool definitions
   - JSON-based workflows
   - Audit trail generation

4. **Phase 4: Integration**
   - Update existing modules to use new system
   - Migration scripts for old format
   - Performance optimization

## Example Workflow

```json
{
  "workflow": "validate_llm_bibliography",
  "steps": [
    {
      "tool": "extract_citations",
      "params": {
        "text": "@file:llm_output.md",
        "format": "markdown"
      }
    },
    {
      "tool": "validate_citations",
      "params": {
        "input": "@previous.output",
        "strict": true
      }
    },
    {
      "tool": "fix_hallucinated_authors",
      "params": {
        "citations": "@previous.validated",
        "output": "fixed_citations.bib"
      }
    },
    {
      "tool": "generate_report",
      "params": {
        "validation_results": "@step[1].output",
        "output": "validation_report.md"
      }
    }
  ]
}
```

This provides a fully deterministic, auditable system for handling LLM-generated citations.
