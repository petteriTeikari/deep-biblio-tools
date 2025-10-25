# Detailed Regex Violations by File

## Summary Statistics

- **Total Violations**: 250+
- **Files Affected**: 26
- **Most Affected**: `citation_manager.py` (38 violations)
- **Critical Files**: Core modules with 10+ violations each

## File-by-File Analysis

### 1. `/src/core/biblio_checker.py` (34 violations)

**Current Usage**:
```python
# Line 188: LaTeX citation extraction
pattern = r'\\cite\{([^}]+)\}'

# Line 451: BibTeX entry parsing
entry_pattern = r'@(\w+)\{([^,]+),'

# Line 498: Bibliography key validation
key_pattern = r'^[a-zA-Z0-9_-]+$'

# Line 801: Markdown reference detection
ref_pattern = r'\[([^\]]+)\]:\s*(.+)'
```

**Migration Path**:
- Use `pylatexenc` for LaTeX citation parsing
- Use `bibtexparser` for BibTeX entry handling
- Create structured key validator class
- Use `markdown-it-py` for reference parsing

### 2. `/src/converters/md_to_latex/citation_manager.py` (38 violations)

**Current Usage**:
```python
# Line 77: Complex citation pattern
r'\\(text)?cite[pt]?\*?\{([^}]+)\}'

# Line 375: Author extraction from BibTeX
r'author\s*=\s*\{([^}]+)\}'

# Line 403: Year extraction
r'year\s*=\s*\{(\d{4})\}'

# Line 711: LaTeX command detection
r'\\[a-zA-Z]+\{[^}]*\}'
```

**Migration Strategy**:
- Build `CitationExtractor` class using AST
- Create `BibtexFieldExtractor` for metadata
- Implement `LatexCommandParser` for commands

### 3. `/src/converters/md_to_latex/utils.py` (35 violations)

**Current Usage**:
```python
# Line 113: LaTeX special character escaping
special_chars = r'[#$%&_{}~^\\]'

# Line 270: Math environment detection
r'\\begin\{(equation|align|gather)\*?\}'

# Line 338: Label extraction
r'\\label\{([^}]+)\}'
```

**Required Changes**:
- Create `LatexEscaper` class with proper rules
- Use AST to detect math environments
- Parse labels through LaTeX walker

### 4. `/src/converters/md_to_latex/latex_builder.py` (22 violations)

**Current Usage**:
```python
# Line 392: Section command building
r'\\(sub)*section\{([^}]+)\}'

# Line 586: Figure environment parsing
r'\\begin\{figure\}.*?\\end\{figure\}'
```

**AST Alternative**:
- Build LaTeX using structured nodes
- Generate commands programmatically
- Parse existing LaTeX with proper walker

### 5. `/src/utils/mdpi_workaround.py` (23 violations)

**Current Usage**:
```python
# Line 219: MDPI-specific citation format
r'\\cite\{MDPI-\d+\}'

# Line 353: Journal name extraction
r'journal\s*=\s*\{([^}]+)\}'
```

**Migration**:
- Create MDPI-specific parser subclass
- Handle format quirks in structured way

### 6. `/src/converters/md_to_latex/post_processing.py` (17 violations)

**Current Usage**:
```python
# Line 62: Whitespace normalization
r'\s+'

# Line 204: Empty line handling
r'\n\s*\n'
```

**Better Approach**:
- Use AST transformations
- Preserve document structure
- Apply formatting rules properly

### 7. `/src/utils/pdf_parser.py` (11 violations)

**Current Usage**:
```python
# Line 223: PDF text extraction patterns
r'References\s*\n'

# Line 281: Citation detection in PDF
r'\[\d+\]'
```

**Improvement**:
- Use structured PDF parsing libraries
- Extract text with layout information
- Parse citations contextually

### 8. `/src/bibliography/fixer.py` (5 violations)

**Current Usage**:
```python
# Line 138: Citation key fixing
r'[^a-zA-Z0-9_-]'

# Line 215: Duplicate detection
r'_\d+$'
```

**AST Solution**:
- Parse bibliography entries properly
- Fix at structural level, not text

### 9. `/src/citations/extractor.py` (21 violations)

**Current Usage**:
```python
# Line 72: Citation command variants
r'\\cite[pt]?\*?\{([^}]+)\}'

# Line 233: Multi-citation handling
r'([^,]+)'
```

**Migration**:
- Use LaTeX parser for all variants
- Handle multi-citations structurally

### 10. `/src/utils/validators.py` (6 violations)

**Current Usage**:
```python
# Line 107: Format validation
r'^[A-Z][a-z]+\d{4}[a-z]?$'

# Line 138: DOI validation
r'10\.\d{4,}/[-._;()/:\w]+'
```

**Better Validation**:
- Create typed validator classes
- Use proper parsing for formats

## Common Patterns to Replace

### Citation Patterns
```python
# OLD: Regex
citations = re.findall(r'\\cite\{([^}]+)\}', text)

# NEW: AST
from pylatexenc.latexwalker import LatexWalker
walker = LatexWalker(text)
nodes, _, _ = walker.get_latex_nodes()
citations = [n.nodeargd.argnlist[0].nodelist
             for n in nodes
             if hasattr(n, 'macroname') and n.macroname == 'cite']
```

### BibTeX Parsing
```python
# OLD: Regex
entries = re.findall(r'@(\w+)\{([^,]+),', bibtex)

# NEW: AST
import bibtexparser
bib_db = bibtexparser.loads(bibtex)
entries = [(e['ENTRYTYPE'], e['ID']) for e in bib_db.entries]
```

### Markdown Links
```python
# OLD: Regex
links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', markdown)

# NEW: AST
from markdown_it import MarkdownIt
from markdown_it.token import Token
md = MarkdownIt()
tokens = md.parse(markdown)
links = extract_links_from_tokens(tokens)
```

## Priority Order for Migration

### High Priority (Core Functionality)
1. `biblio_checker.py` - Core validation logic
2. `citation_manager.py` - Critical for conversions
3. `extractor.py` - Citation extraction

### Medium Priority (Features)
4. `utils.py` - Utility functions
5. `latex_builder.py` - LaTeX generation
6. `post_processing.py` - Output cleanup

### Low Priority (Workarounds)
7. `mdpi_workaround.py` - Specific publisher
8. `validators.py` - Input validation
9. `pdf_parser.py` - PDF handling

## Effort Estimates

### Phase 1: Core (1-2 weeks)
- Set up parser infrastructure
- Migrate critical files
- Ensure backward compatibility

### Phase 2: Features (1-2 weeks)
- Convert utility modules
- Update converters
- Add comprehensive tests

### Phase 3: Cleanup (1 week)
- Remove all regex patterns
- Update documentation
- Performance optimization

## Success Criteria

1. **All tests pass** with AST parsers
2. **No regex violations** in pre-commit
3. **Performance within 10%** of regex
4. **Better error messages** for users
5. **Easier to maintain** and extend
