# No Regex Policy - AST-Based Parsing Only

## Policy Statement

**This project strictly prohibits the use of regular expressions for parsing structured text formats.** All parsing must be done using appropriate Abstract Syntax Tree (AST) based parsers or dedicated parsing libraries.

## Rationale

Regular expressions are brittle, error-prone, and inadequate for parsing structured formats like:
- BibTeX entries with nested braces
- LaTeX documents with complex command structures
- Markdown with embedded code blocks
- Citation formats with optional fields

## Approved Parsers

### For BibTeX
```python
# ✅ CORRECT: Use bibtexparser
import bibtexparser
from bibtexparser.bparser import BibTexParser

parser = BibTexParser(common_strings=True)
with open('references.bib', 'r') as bibfile:
    bib_database = bibtexparser.load(bibfile, parser)

# ❌ WRONG: Never use regex
# import re
# entries = re.findall(r'@(\w+)\{([^,]+),\s*(.*?)\}', bibtex_content)
```

### For Markdown
```python
# ✅ CORRECT: Use markdown-it-py
from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode

md = MarkdownIt()
tokens = md.parse(markdown_content)
ast = SyntaxTreeNode(tokens)

# ❌ WRONG: Never use regex
# citations = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', markdown)
```

### For LaTeX
```python
# ✅ CORRECT: Use pylatexenc
from pylatexenc.latexwalker import LatexWalker, LatexEnvironmentNode

walker = LatexWalker(latex_content)
nodes, _, _ = walker.get_latex_nodes()

# ❌ WRONG: Never use regex
# citations = re.findall(r'\\cite\{([^}]+)\}', latex)
```

### For Citations
```python
# ✅ CORRECT: Use structured parsing
from deep_biblio_tools.parsers import CitationParser

parser = CitationParser()
citation = parser.parse("[Smith et al. (2023)](https://doi.org/10.1234/example)")

# ❌ WRONG: Never use regex
# match = re.match(r'\[([^\]]+)\]\(([^)]+)\)', citation_text)
```

## Exceptions

The ONLY acceptable uses of regex are:

1. **Simple validation** (not parsing):
   ```python
   # OK: Validate DOI format
   if re.match(r'^10\.\d{4,}\/[-._;()\/:a-zA-Z0-9]+$', doi):
       process_doi(doi)
   ```

2. **Simple string cleaning**:
   ```python
   # OK: Remove extra whitespace
   cleaned = re.sub(r'\s+', ' ', text).strip()
   ```

3. **Non-structured text search**:
   ```python
   # OK: Find email addresses in free text
   emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
   ```

## Implementation Guidelines

### When Adding New Parsers

1. **Research existing parsers first**
   - Check PyPI for domain-specific parsers
   - Look for well-maintained libraries with good test coverage
   - Prefer libraries with AST/CST output

2. **If no parser exists, build a proper one**
   - Use parser generators (pyparsing, lark, parsimonious)
   - Implement proper tokenization
   - Build an AST representation
   - Never try to parse with regex

3. **Document parser choice**
   ```python
   """
   This module uses bibtexparser for BibTeX parsing.

   Why:
   - Handles nested braces correctly
   - Preserves entry order
   - Supports string variables
   - Has proper error reporting

   Never use regex for BibTeX - it cannot handle:
   - Nested braces in titles/abstracts
   - Escaped characters
   - String concatenation
   - Comment handling
   """
   ```

## Testing Requirements

All parsers must include tests for:

1. **Edge cases** that break regex:
   ```python
   # Test nested structures
   test_bibtex = '''
   @article{test2023,
     title = {A {Study} of {Nested {Braces}} in {BibTeX}},
     abstract = {This has a } inside which would break regex}
   }
   '''
   ```

2. **Malformed input**:
   ```python
   # Parser should provide meaningful errors
   with pytest.raises(ParseError) as exc:
       parser.parse("@article{missing_closing_brace")
   assert "Unclosed entry" in str(exc.value)
   ```

3. **Performance** on large files:
   ```python
   # Should handle 10MB bibliography files
   large_bib = generate_large_bibliography(entries=10000)
   start = time.time()
   result = parser.parse(large_bib)
   assert time.time() - start < 5.0  # Should parse in < 5 seconds
   ```

## Code Review Checklist

- [ ] No regex used for parsing structured formats
- [ ] Appropriate AST parser selected and documented
- [ ] Parser choice justification in docstring
- [ ] Edge case tests included
- [ ] Error handling for malformed input
- [ ] Performance tests for large inputs

## Learning Resources

1. **Why not regex**: ["Now you have two problems"](https://blog.codinghorror.com/regular-expressions-now-you-have-two-problems/)
2. **Parser theory**: [Crafting Interpreters](https://craftinginterpreters.com/)
3. **Python parsing**: [pyparsing documentation](https://pyparsing.readthedocs.io/)
4. **AST concepts**: [Python AST module](https://docs.python.org/3/library/ast.html)

## Enforcement

1. **Pre-commit hooks** will flag regex use in parsers
2. **Code review** must verify parser appropriateness
3. **CI/CD** will run parser stress tests
4. **Documentation** must justify any regex use

Remember: **Structured text requires structured parsing!**
