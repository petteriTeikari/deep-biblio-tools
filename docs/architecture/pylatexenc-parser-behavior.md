# Understanding pylatexenc Parser Behavior

## Critical Discovery: Macro Argument Parsing

**Key Insight**: The pylatexenc parser behaves differently for different macros based on its built-in knowledge of LaTeX commands.

### Known Macros vs Unknown Macros

1. **Known Macros** (e.g., `\textbf`, `\cite`, `\emph`):
   - pylatexenc has built-in knowledge of their argument structure
   - Arguments are parsed and included in the `nodeargd` attribute
   - The macro node contains all its arguments
   - Example: `\textbf{bold}` returns a single LatexMacroNode with parsed arguments

2. **Unknown Macros** (e.g., `\href`, `\passthrough`, custom commands):
   - pylatexenc doesn't know their argument structure
   - Arguments appear as separate LatexGroupNode objects following the macro
   - You must look at subsequent nodes to find the arguments
   - Example: `\href{url}{text}` returns three nodes: LatexMacroNode, LatexGroupNode, LatexGroupNode

### Practical Implications

When processing LaTeX AST:
1. Always check if a macro has `nodeargd.argnlist` populated
2. If not, look for LatexGroupNode objects that immediately follow
3. Track node positions to avoid processing arguments twice

## How pylatexenc Works

### Core Concepts

1. **LatexWalker**: The main parser that traverses LaTeX content
   - Produces a list of nodes representing the document structure
   - Handles nested structures and special LaTeX syntax

2. **Node Types**:
   - `LatexMacroNode`: Commands like `\textbf`, `\cite`
   - `LatexGroupNode`: Content within braces `{...}`
   - `LatexCharsNode`: Plain text content
   - `LatexMathNode`: Math mode content `$...$` or `$$...$$`
   - `LatexEnvironmentNode`: Environments like `\begin{equation}...\end{equation}`
   - `LatexCommentNode`: Comments starting with `%`

3. **ParsedMacroArgs**: Structure containing parsed arguments for known macros
   - `argspec`: String describing expected arguments (e.g., '{' for one mandatory argument)
   - `argnlist`: List of parsed argument nodes

### Example: Different Parsing Behaviors

```python
# Known macro with one argument
text = r"\textbf{bold}"
# Result: Single LatexMacroNode with nodeargd containing the argument

# Unknown macro with arguments
text = r"\href{https://example.com}{link text}"
# Result: Three separate nodes:
# 1. LatexMacroNode (href)
# 2. LatexGroupNode (https://example.com)
# 3. LatexGroupNode (link text)

# Citation with optional arguments
text = r"\cite[p.10]{author2020}"
# Result: Single LatexMacroNode with all arguments in nodeargd
```

### Working with the AST

1. **Reconstruction Strategy**:
   - For known macros: Use `nodeargd.argnlist` to reconstruct arguments
   - For unknown macros: Look ahead for LatexGroupNode siblings
   - Track processed positions to avoid duplicating content

2. **Transformation Strategy**:
   - Modify the node's metadata and type
   - Update or create `nodeargd` for proper reconstruction
   - Remove separate argument nodes if converting unknown to known macro

## Common Pitfalls

1. **Assuming all macros have parsed arguments**: Always check `nodeargd` existence
2. **Not handling position tracking**: Can lead to duplicated content in reconstruction
3. **Forgetting about optional arguments**: Citations can have `\cite[optional]{required}`
4. **Not preserving whitespace**: Important for readability

## Best Practices

1. **Use debug scripts** to understand node structure before implementing transformations
2. **Test with both known and unknown macros** to ensure robustness
3. **Preserve original node positions** for error reporting
4. **Document macro knowledge** in your parser wrapper

## References

- [pylatexenc Documentation](https://pylatexenc.readthedocs.io/en/latest/)
- [pylatexenc GitHub Repository](https://github.com/phfaist/pylatexenc)

## Implementation Notes

Our LaTeX parser wrapper (`src/parsers/latex_parser.py`) handles this complexity by:
1. Storing parsed arguments in metadata when available
2. Providing helper methods for citation extraction
3. Converting pylatexenc nodes to our unified ParsedNode structure

The document reconstruction (`post_processing_ast.py`) must:
1. Check for `parsed_args` in metadata first
2. Look for following group nodes as fallback
3. Track processed positions to avoid duplication
4. Handle both known and unknown macro patterns
