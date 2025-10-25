# AST Reconstruction Troubleshooting Guide

## Current Known Issues

### 1. Complex Document Reconstruction (ACTIVE ISSUE)

**Symptom**: In complex documents, some macros lose their arguments during reconstruction.
- `\section{Introduction}` → `\section`
- `\cite{author2020}` → `\cite`
- `\emph{emphasis}` → `\emph`

**Root Cause**: The issue is NOT in parsing - pylatexenc correctly parses these macros with their arguments. The problem is in our reconstruction logic's position tracking.

**Debug Findings**:
```python
# Individual macros reconstruct correctly:
\section{Introduction} → has parsed_args at position [2] → reconstructs correctly

# But in complex documents:
# The position calculation gets confused by surrounding whitespace/nodes
```

**Temporary Workaround**: Use individual macro reconstruction for critical transformations.

**Proper Fix Needed**: Improve position tracking in `_reconstruct_node_with_args` to handle complex document contexts.

### 2. Environment End Position

**Issue**: Environment nodes report `pos_end` as the end of `\begin{env}`, not `\end{env}`.

**Solution Implemented**:
```python
# Find actual end position by searching for \end{envname}
search_text = f"\\end{{{env_name}}}"
end_idx = doc.raw_text.find(search_text, node.start_pos)
```

### 3. Transformed Node Position Tracking

**Issue**: After transforming a node (e.g., href → cite), the original positions no longer match the new content.

**Solution Implemented**:
- Track transformation history in metadata
- Calculate end position by parsing the original text structure
- Remove associated argument nodes from the document

## Debugging Techniques

### 1. Node Structure Inspection

```python
# Always check both patterns
print(f"has parsed_args: {'parsed_args' in node.metadata}")
if 'parsed_args' in node.metadata:
    for i, arg in enumerate(node.metadata['parsed_args']):
        if arg:
            print(f"arg {i}: {extract_text(arg)}")
```

### 2. Position Tracking Debug

```python
# Debug position calculations
result, end_pos = processor._reconstruct_node_with_args(node, doc, i)
print(f"Node {i}: {repr(result)}, end_pos={end_pos}")
print(f"Original text: {repr(doc.raw_text[node.start_pos:end_pos])}")
```

### 3. Walk Nodes Verification

```python
# Ensure _walk_nodes finds all nodes
for node in processor._walk_nodes(doc.nodes):
    print(f"type={node.type}, name={node.metadata.get('macro_name')}")
```

## Common Pitfalls

### 1. Assuming Parsed Args Exist
```python
# WRONG
args = node.metadata["parsed_args"]  # KeyError!

# RIGHT
if "parsed_args" in node.metadata:
    args = node.metadata["parsed_args"]
```

### 2. Not Handling None Arguments
```python
# WRONG
for arg in node.metadata["parsed_args"]:
    text = extract_text(arg)  # Error if arg is None

# RIGHT
for arg in node.metadata["parsed_args"]:
    if arg is not None:
        text = extract_text(arg)
```

### 3. Forgetting Position Updates
```python
# WRONG
node.type = "comment"
# Still has old positions!

# RIGHT
node.type = "comment"
# Must recalculate end_pos in reconstruction
```

## Test Coverage Requirements

For any AST reconstruction change, test:

1. **Simple cases**: Single macro/environment
2. **Complex documents**: Multiple nested structures
3. **Transformation cases**: Nodes that have been modified
4. **Edge cases**: Empty arguments, optional arguments, unknown macros

## Future Improvements Needed

1. **Better Position Tracking**: Implement a position manager that handles transformations
2. **Serialization Support**: Add proper LaTeX serialization to ParsedNode
3. **Comprehensive Test Suite**: Test every combination of node type × transformation
4. **Macro Database**: Document which macros are known/unknown in pylatexenc

## Emergency Fixes

If reconstruction is completely broken:

1. **Fallback to Original**: Return `doc.raw_text` for untransformed documents
2. **Selective Reconstruction**: Only reconstruct transformed nodes
3. **Debug Mode**: Add logging to track each reconstruction step
4. **Bisect**: Test with progressively simpler documents to isolate issue

Remember: The parser works correctly - issues are almost always in our reconstruction logic!
