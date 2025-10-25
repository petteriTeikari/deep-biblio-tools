# Deterministic Citation System - Refactoring Plan

## Current State Analysis

### Problem Files
1. **`biblio_checker.py` (1455 lines)**
   - Mixes: validation, fixing, API calls, file I/O
   - 106 if statements - high complexity
   - Should be split into ~5 focused modules

2. **`citation_manager.py` (1130 lines)**
   - Handles: extraction, validation, Zotero integration
   - 111 if statements - too complex
   - Core functionality that needs deterministic approach

## Refactoring Strategy

### Phase 1: Create Deterministic Core (Week 1)

#### 1.1 Citation Models (`src/citations/models.py`)
```python
# Extract from existing code and enhance
- CitationData dataclass with source tracking
- AuthorData with confidence scores
- ValidationResult with detailed audit trail
- DataSource enum for trust levels
```

#### 1.2 Split `biblio_checker.py` into:

**`src/citations/extractor.py`** (~250 lines)
```python
class CitationExtractor:
    """Extract citations from various formats."""
    def extract_from_markdown(self, text: str) -> List[RawCitation]
    def extract_from_latex(self, text: str) -> List[RawCitation]
    def extract_from_bibtex(self, text: str) -> List[RawCitation]
```

**`src/citations/validator.py`** (~300 lines)
```python
class DeterministicValidator:
    """Validate citations against authoritative sources."""
    def validate_via_doi(self, doi: str) -> CitationData
    def validate_via_arxiv(self, arxiv_id: str) -> CitationData
    def validate_via_title(self, title: str, authors: str) -> CitationData
```

**`src/citations/hallucination_detector.py`** (~200 lines)
```python
class HallucinationDetector:
    """Detect LLM hallucinations in citations."""
    def check_authors(self, claimed: str, validated: List[AuthorData]) -> List[Issue]
    def check_title(self, title: str) -> List[Issue]
    def check_year(self, year: str) -> List[Issue]
```

**`src/api_clients/crossref.py`** (~150 lines)
```python
class CrossRefClient(APIClient):
    """Deterministic CrossRef API client."""
    def get_by_doi(self, doi: str) -> Optional[CitationData]
    def search_by_title(self, title: str) -> List[CitationData]
```

**`src/api_clients/arxiv.py`** (~150 lines)
```python
class ArXivClient(APIClient):
    """Deterministic arXiv API client."""
    def get_by_id(self, arxiv_id: str) -> Optional[CitationData]
    def parse_arxiv_response(self, xml: str) -> CitationData
```

### Phase 2: Refactor Citation Manager (Week 1-2)

Split `citation_manager.py` into:

**`src/citations/parser.py`** (~300 lines)
```python
class CitationParser:
    """Parse citations from text deterministically."""
    def parse_markdown_citation(self, text: str) -> RawCitation
    def parse_latex_citation(self, text: str) -> RawCitation
    def extract_identifiers(self, text: str) -> Dict[str, str]
```

**`src/citations/cache.py`** (~200 lines)
```python
class CitationCache:
    """Deterministic caching for citation lookups."""
    def get_validated(self, identifier: str) -> Optional[CitationData]
    def store_validated(self, identifier: str, data: CitationData)
    def get_cache_stats(self) -> Dict[str, Any]
```

**`src/citations/formatter.py`** (~200 lines)
```python
class CitationFormatter:
    """Format validated citations."""
    def to_bibtex(self, citation: CitationData) -> str
    def to_markdown(self, citation: CitationData) -> str
    def to_json(self, citation: CitationData) -> Dict[str, Any]
```

### Phase 3: Agent Infrastructure (Week 2)

#### 3.1 Function Registry (`src/agents/registry.py`)
```python
class FunctionRegistry:
    """Registry for deterministic function calls."""
    def register(self, func: Callable) -> Callable
    def call(self, name: str, **kwargs) -> Any
    def list_functions(self) -> List[FunctionDef]
```

#### 3.2 Citation Tools (`src/agents/citation_tools.py`)
```python
@function_registry.register
def validate_bibliography(file_path: str, strict: bool = True) -> ValidationResult:
    """Validate bibliography with deterministic rules."""

@function_registry.register
def fix_hallucinated_entries(input_file: str, output_file: str) -> FixResult:
    """Fix hallucinated citations deterministically."""
```

#### 3.3 Workflow Engine (`src/agents/workflow.py`)
```python
class WorkflowEngine:
    """Execute deterministic workflows."""
    def load_workflow(self, definition: Dict[str, Any])
    def execute(self) -> List[StepResult]
    def get_audit_trail(self) -> List[AuditEntry]
```

### Phase 4: Migration & Integration (Week 2-3)

1. **Update existing code** to use new deterministic validators
2. **Create migration scripts** for old validation logic
3. **Add compatibility layer** for existing CLI commands
4. **Comprehensive testing** of deterministic behavior

## File Size Targets

All new files should follow these constraints:
- **Max 400 lines** per file
- **Max 10 methods** per class
- **Max 50 lines** per method
- **Single responsibility** per file

## Success Metrics

1. **Deterministic validation**: Same input always produces same output
2. **Author accuracy**: 100% correct author names when DOI/arXiv available
3. **Hallucination detection**: >95% detection rate for common patterns
4. **Performance**: <100ms per citation validation (with cache)
5. **Code quality**: All files under 400 lines, cyclomatic complexity <10

## Migration Example

Before (non-deterministic):
```python
# Old way - might get different results
validator = BiblioChecker()
result = validator.check_and_fix(entry)  # Mixed concerns, unclear what happened
```

After (deterministic):
```python
# New way - deterministic and auditable
validator = DeterministicValidator()
validated = validator.validate_citation(entry)

if validated.source == DataSource.CROSSREF:
    # We know exactly where the data came from
    print(f"Validated via CrossRef: {validated.validation_log}")

detector = HallucinationDetector()
issues = detector.check_citation(entry, validated)
if issues:
    print(f"Detected hallucinations: {issues}")
```

## Timeline

- **Week 1**: Core models, split biblio_checker.py
- **Week 2**: Split citation_manager.py, agent infrastructure
- **Week 3**: Integration, testing, migration

This approach ensures we have a fully deterministic system for the critical problem of LLM citation hallucinations while maintaining clean, manageable code.
