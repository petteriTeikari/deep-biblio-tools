# Regex to AST Migration Plan

## Executive Summary

The deep-biblio-tools repository has **250+ regex parsing violations** across multiple modules. These violations represent technical debt and potential parsing errors when handling structured formats like LaTeX, BibTeX, and Markdown.

**Verdict**: Yes, we can and should migrate everything to AST-based parsing. The effort is significant but achievable.

## Current Violation Analysis

### By Module

1. **Core Bibliography Checker** (`src/core/biblio_checker.py`)
   - 34 violations
   - Uses regex for LaTeX citations, BibTeX entries, and markdown parsing
   - CRITICAL: Core functionality depends on fragile regex patterns

2. **Citation System** (`src/citations/`)
   - `extractor.py`: 21 violations
   - `hallucination_detector.py`: 6 violations
   - Parses LaTeX citation commands with regex

3. **Converters** (`src/converters/md_to_latex/`)
   - `citation_manager.py`: 38 violations
   - `utils.py`: 35 violations
   - `post_processing.py`: 17 violations
   - `latex_builder.py`: 22 violations
   - Heavy regex use for markdown-to-LaTeX conversion

4. **Utilities** (`src/utils/`)
   - `mdpi_workaround.py`: 23 violations
   - `validators.py`: 6 violations
   - `extractors.py`: 8 violations
   - `pdf_parser.py`: 11 violations
   - Various regex patterns for validation and extraction

5. **API Clients** (`src/api_clients/`)
   - `arxiv.py`: 1 violation
   - Minor regex usage

6. **Bibliography Module** (`src/bibliography/`)
   - `validator.py`: 1 violation
   - `fixer.py`: 5 violations
   - Citation key and format validation

## Regex Patterns Being Used

### LaTeX Patterns
```python
# Citation commands
r'\\cite\{([^}]+)\}'
r'\\citep?\{([^}]+)\}'
r'\\textcite\{([^}]+)\}'

# Document structure
r'\\begin\{([^}]+)\}'
r'\\section\{([^}]+)\}'
r'\\label\{([^}]+)\}'
```

### BibTeX Patterns
```python
# Entry detection
r'@(\w+)\{([^,]+),'
r'(\w+)\s*=\s*\{([^}]+)\}'
r'author\s*=\s*\{([^}]+)\}'
```

### Markdown Patterns
```python
# Links and references
r'\[([^\]]+)\]\(([^)]+)\)'
r'!\[([^\]]+)\]\(([^)]+)\)'
r'\[([^\]]+)\]:\s*(.+)'
```

## AST-Based Alternatives

### 1. LaTeX Parsing: `pylatexenc`
```python
# Current (regex)
citations = re.findall(r'\\cite\{([^}]+)\}', latex_text)

# Future (AST)
from pylatexenc.latexwalker import LatexWalker, LatexCharsNode
walker = LatexWalker(latex_text)
nodes, pos, len_ = walker.get_latex_nodes()
citations = [node for node in nodes if node.macroname == 'cite']
```

### 2. BibTeX Parsing: `bibtexparser`
```python
# Current (regex)
entries = re.findall(r'@(\w+)\{([^,]+),', bibtex_text)

# Future (AST)
import bibtexparser
bib_db = bibtexparser.loads(bibtex_text)
entries = [(e['ENTRYTYPE'], e['ID']) for e in bib_db.entries]
```

### 3. Markdown Parsing: `markdown-it-py`
```python
# Current (regex)
links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', markdown_text)

# Future (AST)
from markdown_it import MarkdownIt
md = MarkdownIt()
tokens = md.parse(markdown_text)
links = [t for t in tokens if t.type == 'link']
```

## Migration Strategy

### Phase 1: Foundation (Week 1)
1. **Create parser abstraction layer**
   ```python
   # src/parsers/base.py
   class StructuredParser(ABC):
       @abstractmethod
       def parse(self, text: str) -> ParsedDocument:
           pass
   ```

2. **Implement parser adapters**
   - `LatexParser` using `pylatexenc`
   - `BibtexParser` using `bibtexparser`
   - `MarkdownParser` using `markdown-it-py`

3. **Add comprehensive tests**
   - Test all current regex patterns
   - Ensure AST parsers handle edge cases

### Phase 2: Core Migration (Week 2)
1. **Migrate `biblio_checker.py`**
   - Replace citation extraction
   - Update bibliography validation
   - Maintain backward compatibility

2. **Migrate citation system**
   - Update `extractor.py`
   - Fix `hallucination_detector.py`

### Phase 3: Converters (Week 3)
1. **Refactor md-to-latex converter**
   - Use AST for markdown parsing
   - Generate LaTeX using proper builders
   - Remove all regex-based transformations

2. **Update post-processing**
   - AST-based cleanup operations
   - Structured transformations

### Phase 4: Utilities (Week 4)
1. **Update validators**
   - Use parsers for format validation
   - Structured error reporting

2. **Fix workarounds**
   - MDPI workaround using AST
   - ResearchGate fixes with proper parsing

## Implementation Plan

### Step 1: Parser Infrastructure
```python
# src/parsers/__init__.py
from .latex import LatexParser
from .bibtex import BibtexParser
from .markdown import MarkdownParser

# src/parsers/latex.py
from pylatexenc.latexwalker import LatexWalker
from typing import List, Dict, Any

class LatexParser:
    def __init__(self):
        self.walker = None

    def parse(self, text: str) -> 'LatexDocument':
        self.walker = LatexWalker(text)
        return LatexDocument(self.walker)

    def extract_citations(self, text: str) -> List[Dict[str, Any]]:
        doc = self.parse(text)
        return doc.get_citations()
```

### Step 2: Gradual Replacement
```python
# src/core/biblio_checker.py
# OLD
def extract_citations_regex(text):
    return re.findall(r'\\cite\{([^}]+)\}', text)

# NEW
def extract_citations(text):
    parser = LatexParser()
    return parser.extract_citations(text)
```

### Step 3: Compatibility Layer
```python
# During migration, support both
def extract_citations(text, use_ast=True):
    if use_ast:
        return LatexParser().extract_citations(text)
    else:
        return extract_citations_regex(text)
```

## Benefits of Migration

### 1. **Accuracy**
- No more regex edge cases
- Proper handling of nested structures
- Context-aware parsing

### 2. **Maintainability**
- Clear parser APIs
- Easier to debug
- Better error messages

### 3. **Performance**
- Parsers are optimized
- Single-pass parsing
- Cacheable parse trees

### 4. **Features**
- Extract more information
- Preserve formatting
- Enable refactoring tools

## Risk Mitigation

### 1. **Parallel Implementation**
- Keep regex as fallback
- A/B test results
- Gradual rollout

### 2. **Comprehensive Testing**
- Test against real-world data
- Fuzzing for edge cases
- Performance benchmarks

### 3. **Documentation**
- Migration guide
- API documentation
- Example conversions

## Timeline

- **Week 1**: Parser infrastructure + tests
- **Week 2**: Core module migration
- **Week 3**: Converter migration
- **Week 4**: Utilities + cleanup
- **Week 5**: Testing + documentation
- **Week 6**: Deprecation + monitoring

## Success Metrics

1. **Zero regex violations** in pre-commit
2. **100% test coverage** for parsers
3. **No performance regression**
4. **Improved error messages**
5. **Reduced bug reports** for parsing issues

## Conclusion

The migration from regex to AST-based parsing is not only feasible but essential for the long-term health of the project. With proper planning and execution, we can eliminate all 250+ regex violations and create a more robust, maintainable codebase.

The investment is approximately 6 weeks of focused development, but the payoff is:
- Fewer parsing bugs
- Easier feature additions
- Better user experience
- Compliance with guardrails

**Recommendation**: Proceed with the migration as part of this refactoring effort.
