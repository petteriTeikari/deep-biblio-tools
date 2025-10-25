# Deep-Biblio-Tools Refactoring Context for AI Assistants

## Project Context

### What This Project Does
Deep-Biblio-Tools processes academic documents, converting markdown (often LLM-generated) to publication-ready LaTeX with validated bibliographies. It fixes common LLM citation errors like incomplete author names, hallucinated references, and formatting issues.

### Current Pain Points
1. **81 separate scripts** with overlapping functionality
2. **No unified workflow** - users run 5-7 scripts manually
3. **Scattered configuration** across hardcoded values, env vars, CLI args
4. **Poor test coverage** - most scripts untested
5. **Documentation fragmentation** - 76 markdown files in various locations

## Technical Details for Analysis

### Script Examples Showing Duplication

**Six different bibliography fixers:**
```python
# fix_bibliography.py (300 lines)
def fix_bibliography(filename, validate=False):
    # Basic fixing logic

# fix_bibliography_enhanced.py (450 lines)
def fix_bibliography(filename, validate=True, enrich=True):
    # Same logic + metadata enrichment

# fix_bibliography_comprehensive.py (600 lines)
def fix_bibliography(filename, validate=True, enrich=True, deep_check=True):
    # Same logic + more validation

# ... and 3 more variants
```

### Typical User Workflow (Current)

```bash
# What users must do now (error-prone, order-dependent):
python extract_markdown_bibliography.py paper.md -o refs.bib
python validate_llm_citations.py refs.bib
python fix_incomplete_authors.py refs.bib
python fix_bibliography_ampersands.py refs.bib
python fix_et_al_catastrophe.py refs.bib
python convert_markdown_to_latex.py paper.md -b refs.bib -o paper.tex
python qa_check_citations.py paper.pdf

# What users want:
biblio process paper.md --output paper.tex --fix-all
```

### Architecture Smells

1. **Side Effects Everywhere**
```python
# Current (bad):
def fix_authors(filename):
    with open(filename, 'r') as f:
        content = f.read()
    fixed = do_fixes(content)
    with open(filename, 'w') as f:  # Modifies file!
        f.write(fixed)
```

2. **No State Management**
```python
# Each script starts fresh, no context preserved
Script1: found_issues = ["author_incomplete", "doi_invalid"]
Script2: # Doesn't know about Script1's findings
Script3: # Repeats same validation Script1 did
```

3. **Inconsistent Error Handling**
```python
# Pattern 1: Silent failure
try: fetch_doi(doi)
except: pass

# Pattern 2: Print and continue
try: fetch_doi(doi)
except Exception as e: print(f"Error: {e}")

# Pattern 3: Unclear errors
if not result: raise ValueError("Failed")
```

### Real Issues This Causes

1. **Performance**: Same DOI fetched 5 times across scripts
2. **Reliability**: Scripts fail silently, users don't know why
3. **Maintenance**: Bug fixed in one script, still in 5 others
4. **Usability**: New users give up due to complexity

### Specific Examples of Problems

#### The "et al" Bug
```python
# LLMs generate: "Smith et al (2023)"
# Parser mangles it to: author = "al, Smith et"
# Appears in 4 different scripts with different fixes
```

#### Missing Author Names
```python
# LLM generates:
@article{moss2023,
  author = {Moss},  # Just last name
  title = {...}
}

# Should be:
@article{moss2023,
  author = {Moss, Adam},  # Full name from DOI lookup
  title = {...}
}
```

#### Encoding Issues
```python
# Common in titles/journals:
"AT&T Labs" → LaTeX compilation fails
"Müller" → Encoding errors
"50% improvement" → Treated as comment
```

## Questions for External Review

### Architecture Questions

1. **Consolidation Strategy**
   - Should we have one mega-script with options or multiple focused scripts?
   - How to handle the ~40% code duplication?
   - Is a plugin architecture appropriate here?

2. **API Design**
   ```python
   # Option A: Object-oriented
   doc = Document("paper.md")
   doc.fix_bibliography()
   doc.to_latex()

   # Option B: Functional pipeline
   result = pipeline(
       load("paper.md"),
       extract_bibliography,
       fix_authors,
       validate_citations,
       convert_to_latex
   )

   # Option C: Builder pattern
   Document.from_markdown("paper.md")
       .with_bibliography_fixes()
       .with_validation()
       .to_latex("output.tex")
   ```

3. **Configuration Management**
   - Single YAML config vs environment vars vs CLI args?
   - How to handle per-document vs global settings?
   - Override precedence?

4. **Testing Strategy**
   - How to test bibliography fixes deterministically?
   - Mock external APIs or use fixtures?
   - Integration test strategy for full workflows?

5. **Error Handling Philosophy**
   - Fail fast vs graceful degradation?
   - How to report errors for both CLI and API usage?
   - Structured errors vs string messages?

### Specific Technical Decisions

1. **State Management**
   ```python
   # Should we track state explicitly?
   @dataclass
   class ProcessingState:
       original_content: str
       current_content: str
       fixes_applied: List[Fix]
       validation_errors: List[Error]
       metadata_cache: Dict[str, Any]
   ```

2. **Caching Strategy**
   - Cache DOI lookups between runs?
   - Invalidation strategy?
   - Disk vs memory cache?

3. **Plugin/Extension System**
   ```python
   # Should we support custom fixers?
   class CustomFixer(BibliographyFixer):
       def fix(self, entry: dict) -> dict:
           # Custom logic
           return entry

   register_fixer(CustomFixer())
   ```

4. **CLI vs Library Design**
   - Separate packages (deep-biblio-tools vs deep-biblio-tools-cli)?
   - How much logic in CLI vs library?
   - Interactive mode worth implementing?

5. **Backwards Compatibility**
   - Wrapper scripts for old commands?
   - How long to maintain compatibility?
   - Migration tool for old configs?

### Performance Considerations

Current issues:
- 7 scripts × 2s startup = 14s overhead
- No caching = redundant API calls
- Full file rewrites = slow for large documents

Goals:
- Single pass through document
- Cached API responses
- Incremental updates
- Parallel processing where possible

### AI/LLM Integration Considerations

1. **Determinism Requirements**
   - Same input → same output (with same cache)
   - Explicit randomness (if needed) with seeds
   - No hidden state between runs

2. **Observability**
   - Progress indicators for long operations
   - Structured logs for debugging
   - Clear error messages with context

3. **Scriptability**
   - Single commands for common tasks
   - Composable operations
   - Machine-readable output formats

## Ideal End State

### For Users
```bash
# Simple cases just work
biblio fix references.bib
biblio convert paper.md

# Complex cases are still simple
biblio process manuscript.md \
  --validate strict \
  --fix all \
  --style apa \
  --output final.tex
```

### For Developers
```python
from deep_biblio_tools import Bibliography, Document

# Clear, simple API
bib = Bibliography.from_file("refs.bib")
bib.validate()
bib.fix_all_issues()
bib.save()

# Or pipeline style
result = (
    Document.load("paper.md")
    .extract_bibliography()
    .fix_issues()
    .to_latex()
)
```

### For AI Assistants
- Predictable behavior
- Clear task boundaries
- Structured inputs/outputs
- No side effects
- Comprehensive error info

## Specific Refactoring Proposals to Evaluate

1. **Monorepo with Multiple Packages**
   ```
   deep-biblio-tools/
   ├── packages/
   │   ├── core/          # Core library
   │   ├── cli/           # CLI application
   │   ├── web/           # Future web API
   │   └── vscode/        # Future VS Code extension
   ```

2. **Single Package with Clear Modules**
   ```
   deep-biblio-tools/
   ├── src/
   │   ├── api/           # Public API
   │   ├── bibliography/  # Bib processing
   │   ├── converters/    # Format conversion
   │   ├── cli/           # CLI interface
   │   └── utils/         # Shared utilities
   ```

3. **Plugin-Based Architecture**
   ```
   deep-biblio-tools/
   ├── core/              # Minimal core
   ├── plugins/
   │   ├── validators/    # Validation plugins
   │   ├── fixers/        # Fixing plugins
   │   ├── enrichers/     # Enrichment plugins
   │   └── converters/    # Conversion plugins
   ```

## Questions for AI Reviewers

1. **Architecture**: Which refactoring approach would you recommend?
2. **API Design**: What pattern best balances simplicity and flexibility?
3. **Testing**: How would you approach testing bibliography transformations?
4. **Migration**: What's the smoothest path from current to target state?
5. **Documentation**: How should we structure docs for different audiences?
6. **Performance**: Where should we focus optimization efforts?
7. **Extensibility**: How much flexibility should we build in?

Please provide your analysis and recommendations based on this context.
