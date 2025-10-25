# AST/Regex Refactoring Guidelines

## Overview
This document provides specific guidelines for Claude Code when encountering regex usage in the deep-biblio-tools codebase and how to systematically replace it with AST-based parsing or string methods.

## Immediate Recognition Patterns

### Red Flags - Immediate Regex Removal Required
```python
# 🚨 BANNED - Remove immediately
import re
from re import *
import regex

# 🚨 BANNED - Replace with string methods
re.search(pattern, text)
re.findall(pattern, text)
re.match(pattern, text)
re.sub(pattern, replacement, text)
re.split(pattern, text)
```

### Green Flags - Approved Alternatives
```python
# ✅ APPROVED - String methods
text.startswith('prefix')
text.endswith('suffix')
text.find('pattern')
text.replace('old', 'new')
'delimiter'.join(parts)

# ✅ APPROVED - AST parsers
from markdown_it import MarkdownIt
from pylatexenc.latexwalker import LatexWalker
import bibtexparser
```

## Systematic Refactoring Process

### Step 1: Assessment
Run these commands to identify regex usage:
```bash
# Find all regex imports
grep -r "import re" src/ scripts/ tests/

# Find all regex method calls
grep -r "re\." src/ scripts/ tests/ | grep -v "# TODO" | grep -v "#.*re\."

# Count total occurrences
rg "re\." --type py | wc -l
```

### Step 2: Categorization
Classify each regex pattern by complexity:

#### Simple Patterns → String Methods
- **Prefix/suffix matching**: `^pattern` → `text.startswith()`
- **Substring search**: `pattern` → `'pattern' in text`
- **Simple splitting**: `[,;]` → `text.replace(';', ',').split(',')`
- **Basic substitution**: `pattern` → `text.replace()`

#### Complex Patterns → Character-by-Character Parsing
- **Nested structures**: LaTeX braces `{...}`
- **Command parsing**: `\cite{key1,key2}`
- **Multi-delimiter patterns**: Citation lists
- **State-dependent parsing**: Context-sensitive formats

#### Structured Formats → AST Parsers
- **LaTeX documents**: Use `pylatexenc.latexwalker`
- **Markdown content**: Use `markdown-it-py`
- **BibTeX entries**: Use `bibtexparser`

### Step 3: Implementation Patterns

#### Pattern A: Simple String Method Replacement
```python
# BEFORE
import re
pattern = r'^\\cite'
if re.match(pattern, line):
    matches = re.findall(r'\\cite\{([^}]+)\}', line)

# AFTER
if line.startswith('\\cite'):
    # Extract citation keys manually
    citations = []
    i = 0
    while i < len(line):
        if line[i:i+5] == '\\cite':
            # Find opening brace
            j = line.find('{', i)
            if j != -1:
                # Find closing brace
                k = line.find('}', j)
                if k != -1:
                    citations.append(line[j+1:k])
```

#### Pattern B: State Machine for Complex Parsing
```python
# BEFORE
import re
bib_pattern = r'@(\w+)\s*\{\s*([^,\s]+)\s*,'
matches = re.findall(bib_pattern, content)

# AFTER
def parse_bibtex_entries(content):
    """Parse BibTeX entries using state machine."""
    entries = []
    i = 0
    while i < len(content):
        if content[i] == '@':
            entry = parse_single_entry(content, i)
            if entry:
                entries.append(entry)
                i = entry['end_pos']
            else:
                i += 1
        else:
            i += 1
    return entries
```

#### Pattern C: AST Parser Integration
```python
# BEFORE
import re
latex_pattern = r'\\begin\{(\w+)\}(.*?)\\end\{\1\}'
matches = re.findall(latex_pattern, content, re.DOTALL)

# AFTER
from pylatexenc.latexwalker import LatexWalker

def extract_latex_environments(content):
    """Extract LaTeX environments using AST parser."""
    walker = LatexWalker(content)
    nodes, _, _ = walker.get_latex_nodes()

    environments = []
    for node in nodes:
        if hasattr(node, 'environmentname'):
            environments.append({
                'name': node.environmentname,
                'content': node.nodelist
            })
    return environments
```

## Common Refactoring Scenarios

### Scenario 1: Citation Extraction
**Context**: LaTeX citation commands like `\cite{key1,key2}`

**Regex Pattern**: `r'\\cite(?:p|t)?\{([^}]+)\}'`

**String Method Replacement**:
```python
def extract_citations(content):
    """Extract LaTeX citations using string methods."""
    citations = []
    i = 0
    while i < len(content):
        if content[i:i+5] == "\\cite":
            # Handle \citep, \citet variants
            j = i + 5
            if j < len(content) and content[j] in 'pt':
                j += 1

            # Find opening brace
            if j < len(content) and content[j] == '{':
                # Extract content until matching brace
                k = j + 1
                brace_count = 1
                while k < len(content) and brace_count > 0:
                    if content[k] == '{':
                        brace_count += 1
                    elif content[k] == '}':
                        brace_count -= 1
                    k += 1

                if brace_count == 0:
                    cite_content = content[j+1:k-1]
                    # Split multiple citations
                    keys = [key.strip() for key in cite_content.split(',')]
                    citations.extend(keys)

                i = k
                continue
        i += 1
    return citations
```

### Scenario 2: DOI Validation
**Context**: Validate DOI format

**Regex Pattern**: `r'^10\.\d{4,}/.+'`

**String Method Replacement**:
```python
def is_valid_doi(text):
    """Validate DOI format using string methods."""
    if not text.startswith('10.'):
        return False

    # Find slash separator
    slash_pos = text.find('/', 3)  # Skip "10."
    if slash_pos == -1:
        return False

    # Check prefix has digits after "10."
    prefix = text[3:slash_pos]
    if not prefix.isdigit() or len(prefix) < 4:
        return False

    # Check suffix exists
    suffix = text[slash_pos+1:]
    return len(suffix) > 0
```

### Scenario 3: Markdown Link Parsing
**Context**: Extract markdown links `[text](url)`

**AST Parser Replacement**:
```python
from markdown_it import MarkdownIt

def extract_markdown_links(content):
    """Extract markdown links using AST parser."""
    md = MarkdownIt()
    tokens = md.parse(content)

    links = []
    for token in tokens:
        if token.type == 'inline':
            for child in token.children or []:
                if child.type == 'link_open':
                    href = child.attrGet('href')
                    # Find corresponding link_close and text
                    links.append({
                        'url': href,
                        'text': extract_link_text(child)
                    })
    return links
```

## Quality Assurance Checklist

### Before Submitting Refactored Code
- [ ] No `import re` statements remain
- [ ] No `re.` method calls exist
- [ ] All tests pass with new implementation
- [ ] Ruff linting shows no errors
- [ ] Performance is comparable or better
- [ ] Edge cases are handled correctly
- [ ] Code is more readable than regex version

### Validation Commands
```bash
# Verify complete regex removal
grep -r "import re" src/ | grep -v "# Banned"
grep -r "re\." src/ | grep -v "# TODO" | grep -v "#.*re\."

# Run quality checks
ruff check .
ruff format .

# Test functionality
PYTHONPATH=. pytest tests/
```

## Performance Considerations

### When String Methods Are Faster
- Simple prefix/suffix checks
- Single character searches
- Basic replacements
- Short text processing

### When AST Parsers Are Better
- Complex nested structures
- Semantic meaning preservation
- Error handling and recovery
- Long-term maintainability

### Benchmarking Example
```python
import time

def benchmark_approaches(content):
    # String method approach
    start = time.time()
    result1 = extract_citations_string(content)
    string_time = time.time() - start

    # AST parser approach
    start = time.time()
    result2 = extract_citations_ast(content)
    ast_time = time.time() - start

    print(f"String methods: {string_time:.4f}s")
    print(f"AST parser: {ast_time:.4f}s")
    print(f"Results match: {result1 == result2}")
```

## Error Handling Patterns

### String Method Error Handling
```python
def safe_string_parse(content):
    """Safe string parsing with error handling."""
    try:
        result = []
        i = 0
        while i < len(content):
            # Parsing logic with bounds checking
            if i + 5 < len(content) and content[i:i+5] == "\\cite":
                # Safe extraction with validation
                pass
            i += 1
        return result
    except (IndexError, ValueError) as e:
        logger.error(f"String parsing failed: {e}")
        return []
```

### AST Parser Error Handling
```python
def safe_ast_parse(content):
    """Safe AST parsing with error handling."""
    try:
        walker = LatexWalker(content)
        nodes, _, _ = walker.get_latex_nodes()
        return process_nodes(nodes)
    except Exception as e:
        logger.error(f"AST parsing failed: {e}")
        # Fallback to string methods if needed
        return fallback_string_parse(content)
```

## Documentation Requirements

### Code Comments
```python
# ✅ Good documentation
def extract_latex_commands(content):
    """Extract LaTeX commands using string methods (no regex).

    Replaces regex pattern: r'\\\\(\\w+)(?:\\*)?(?:\\[[^\\]]*\\])?\\{([^}]*)\\}'

    Args:
        content: LaTeX content string

    Returns:
        List of (command, args) tuples

    Note: Uses character-by-character parsing for reliability.
    """
```

### Commit Messages
```
feat: replace regex with string methods for citation extraction

- Remove re.findall usage in citation_extractor.py
- Implement character-by-character parsing for LaTeX citations
- Maintain exact same functionality with improved readability
- Performance improved by 15% for typical citation patterns

Fixes regex usage as per CLAUDE.md guidelines.
```

## Common Pitfalls and Solutions

### Pitfall 1: Incomplete Variable Updates
```python
# ❌ WRONG - 'matches' variable undefined after regex removal
for pattern in self.citation_patterns:
    # matches = re.findall(pattern, content)  # Removed
    for match in matches:  # ← This will fail!
        process_match(match)

# ✅ CORRECT - Update entire logic block
citations = self.extract_citations_string_method(content)
for citation in citations:
    process_citation(citation)
```

### Pitfall 2: Multiline Pattern Handling
```python
# ❌ WRONG - Ignoring multiline complexity
content.find("pattern")  # Won't handle newlines correctly

# ✅ CORRECT - Process line by line when needed
lines = content.split('\n')
for i, line in enumerate(lines):
    if line.strip().startswith("pattern"):
        # Handle multiline context
        block = extract_multiline_block(lines, i)
```

### Pitfall 3: Performance Assumptions
```python
# ❌ WRONG - Assuming regex is always faster
# Complex regex with backtracking can be slow

# ✅ CORRECT - Profile both approaches
def choose_best_method(content_size):
    if content_size < 1000:
        return string_method_parse
    else:
        return ast_parser_parse
```

## Integration with Claude Code Guardrails

This document supplements the main CLAUDE.md guardrails. When Claude Code encounters regex usage:

1. **Immediate Action**: Flag as violation of core principle #2
2. **Assessment**: Categorize pattern complexity
3. **Replacement**: Apply appropriate pattern from this guide
4. **Validation**: Run quality assurance checklist
5. **Documentation**: Update with clear explanation of changes

The goal is systematic, complete elimination of regex usage while maintaining or improving functionality, readability, and performance.
