# pylatexenc Reference Guide

## Overview

pylatexenc is a Python library for parsing LaTeX code and converting between LaTeX and Unicode text. It's not a full LaTeX engine but provides lightweight parsing capabilities.

## Key Modules

### 1. `latexwalker`
Parses LaTeX structure and returns a logical structure of objects.

```python
from pylatexenc.latexwalker import LatexWalker, LatexMacroNode

walker = LatexWalker(latex_text)
nodes, pos, len = walker.get_latex_nodes()
```

### 2. `latex2text`
Converts LaTeX to plain Unicode text.

```python
from pylatexenc.latex2text import LatexNodes2Text
converter = LatexNodes2Text()
plain_text = converter.latex_to_text(latex_code)
```

### 3. `latexencode`
Converts Unicode text to LaTeX.

```python
from pylatexenc import latexencode
latex = latexencode.unicode_to_latex(unicode_text)
```

## Node Types

### LatexCharsNode
- Represents plain text characters
- Properties: `chars` (the text content)

### LatexMacroNode
- Represents LaTeX macros/commands (e.g., `\textbf`)
- Properties:
  - `macroname`: The command name without backslash
  - `nodeargd`: ParsedMacroArgs object (for known macros)
  - `pos`: Starting position in the source

### LatexGroupNode
- Represents content in braces `{...}`
- Properties:
  - `nodelist`: List of child nodes
  - `delimiters`: The delimiters used (usually `{` and `}`)

### LatexEnvironmentNode
- Represents LaTeX environments
- Properties:
  - `environmentname`: Name of the environment
  - `nodelist`: Content nodes
  - `nodeargd`: Arguments to the environment

### LatexMathNode
- Represents math mode content
- Properties:
  - `displaytype`: 'inline' or 'display'
  - `nodelist`: Math content nodes

### LatexCommentNode
- Represents comments (starting with %)
- Properties: `comment` (the comment text)

## Macro Argument Parsing

### Known vs Unknown Macros

pylatexenc has built-in knowledge of standard LaTeX macros through its macro specification system. This affects how arguments are parsed:

**Known Macros** (built into pylatexenc):
- Standard LaTeX commands: `\textbf`, `\emph`, `\cite`, `\ref`, etc.
- Math commands: `\frac`, `\sqrt`, etc.
- Have predefined argument specifications

**Unknown Macros** (custom or less common):
- Commands not in pylatexenc's database
- Examples: `\href`, `\passthrough`, custom commands
- Arguments parsed as separate following nodes

### ParsedMacroArgs Structure

For known macros, the `nodeargd` attribute contains:
```python
ParsedMacroArgs(
    argspec='*[[{',  # Argument specification string
    argnlist=[...]    # List of parsed argument nodes
)
```

Argument specification characters:
- `{`: Mandatory argument in braces
- `[`: Optional argument in brackets
- `*`: Star variant of command
- Numbers indicate multiple arguments

### Example: Argument Parsing Differences

```python
# Known macro - arguments in nodeargd
r"\cite[p.10]{author2020}"
# Parsed as single LatexMacroNode with:
# - nodeargd.argnlist = [None, LatexGroupNode(chars="p.10"), LatexGroupNode(chars="author2020")]

# Unknown macro - arguments as separate nodes
r"\href{url}{text}"
# Parsed as three nodes:
# 1. LatexMacroNode(macroname="href", nodeargd=None)
# 2. LatexGroupNode(nodelist=[LatexCharsNode(chars="url")])
# 3. LatexGroupNode(nodelist=[LatexCharsNode(chars="text")])
```

## Parser Configuration

### Creating a Custom Context

```python
from pylatexenc.latexnodes import LatexNodesContext
from pylatexenc.macrospec import MacroSpec, EnvironmentSpec

# Define custom macros
custom_macros = [
    MacroSpec("mymacro", args_parser="{["),  # One mandatory, one optional
]

# Create context
context = LatexNodesContext(
    macros=custom_macros,
    environments=[...],
)

# Use with walker
walker = LatexWalker(latex_text, latex_context=context)
```

## Best Practices

1. **Always check for nodeargd**: Not all macros have parsed arguments
2. **Handle position tracking**: Use node positions for accurate reconstruction
3. **Preserve structure**: Maintain the relationship between macros and their arguments
4. **Test edge cases**: Include nested structures, optional arguments, and custom commands

## Common Patterns

### Extracting Text from Nodes

```python
def extract_text(node):
    if hasattr(node, 'chars'):
        return node.chars
    elif hasattr(node, 'nodelist'):
        return ''.join(extract_text(n) for n in node.nodelist)
    return ''
```

### Walking the Node Tree

```python
def walk_nodes(nodelist):
    for node in nodelist:
        yield node
        if hasattr(node, 'nodelist'):
            yield from walk_nodes(node.nodelist)
```

### Checking Macro Types

```python
if isinstance(node, LatexMacroNode):
    if node.nodeargd:  # Known macro
        args = node.nodeargd.argnlist
    else:  # Unknown macro
        # Look for following group nodes
```

## Limitations

- Not a full LaTeX engine - doesn't understand all LaTeX semantics
- Limited math parsing - focuses on structure, not mathematical meaning
- No document class awareness - treats all documents the same
- Custom package commands often unknown - may need manual specification

## Version Compatibility

- Python 3.4+ and 2.7 supported
- API has been stable across recent versions
- Check changelog for breaking changes

## References

- [Official Documentation](https://pylatexenc.readthedocs.io/)
- [GitHub Repository](https://github.com/phfaist/pylatexenc)
- [PyPI Package](https://pypi.org/project/pylatexenc/)
