# Markdown→LaTeX Citation Conversion: Ampersand Escaping Issue

## Problem Statement

A Python tool converts Markdown academic documents to LaTeX/PDF. Citations in markdown use the format `[Author (Year)](URL)`. The tool extracts these citations, fetches metadata from DOIs/arXiv, generates BibTeX, and replaces markdown citations with LaTeX `\citep{key}` commands before running Pandoc to convert to LaTeX.

**Current Issue**: Some citations remain as raw markdown links in the final LaTeX output with unescaped ampersands (`&`), causing LaTeX compilation to fail with "Misplaced alignment tab character &".

## Example Failing Case

**Input Markdown**:
```markdown
[GarmentCode (Korosteleva & Sorkine-Hornung, 2023)](https://doi.org/10.1145/3618394)
```

**Expected LaTeX Output**:
```latex
\citep{korosteleva2023}
```

**Actual LaTeX Output**:
```latex
[GarmentCode (Korosteleva & Sorkine-Hornung, 2023)](https://doi.org/10.1145/3618394)
```

The ampersand is unescaped, causing LaTeX errors.

## System Architecture

### Conversion Pipeline

```
1. Read Markdown
2. Extract citations ([text](url) where url is academic domain)
3. Fetch metadata from DOI/arXiv APIs
4. Generate BibTeX file
5. Replace citations in markdown: [text](url) → \citep{key}
6. Run Pandoc: markdown → LaTeX
7. Post-process LaTeX (fix dollar signs, ampersands, etc.)
8. Compile: xelatex → bibtex → xelatex → xelatex → PDF
```

### Citation Extraction (citation_extractor_unified.py)

Uses markdown-it-py AST parser to extract all `[text](url)` links. Filters by academic domains (arxiv.org, doi.org, etc.). Returns:
```python
Citation(text="GarmentCode (Korosteleva & Sorkine-Hornung, 2023)",
         url="https://doi.org/10.1145/3618394",
         is_academic=True)
```

### Citation Replacement (citation_manager.py:1171)

```python
def replace_citations_in_text(self, content: str) -> str:
    """Replace markdown citations with LaTeX cite commands."""
    for key, citation in self.citations.items():
        if not citation.url.startswith("#orphan-"):
            search_pattern = f"]({citation.url})"
            # Find all occurrences
            pos = content.find(search_pattern)
            # Go backwards from ] to find matching [
            # Replace entire [text](url) with \citep{key}
```

Uses character-by-character state machine (no regex) to find the opening `[` by tracking bracket depth.

## Root Cause Investigation

### Test Results

1. **Character-by-character ampersand escaping WORKS in isolation**:
   ```python
   input  = "[GarmentCode (Korosteleva & Sorkine-Hornung, 2023)](URL)"
   output = "[GarmentCode (Korosteleva \& Sorkine-Hornung, 2023)](URL)"
   ```

2. **The escaping function runs but has NO EFFECT on the TEX file**: The output TEX still contains the unescaped `&`.

3. **The citations.items() dict shows the wrong author**:
   ```python
   author = "GarmentCode (Korosteleva \& Sorkine-Hornung"
   # The entire markdown link text became the author name
   ```

4. **The DOI points to the WRONG paper**:
   - DOI `10.1145/3618394` resolves to "Metric Optimization in Penner Coordinates" by Ryan Capouellez
   - NOT "GarmentCode" by Korosteleva & Sorkine-Hornung
   - This is a user error in the source markdown

### Why Citations Aren't Being Replaced

The replacement logic searches for `](https://doi.org/10.1145/3618394)` in the content and goes backwards to find `[`. This should work IF:
1. The citation exists in `self.citations` dict
2. The URL matches exactly

**Hypothesis**: The citation IS in the dict (we saw it in BibTeX), but the replacement is failing silently. Possible reasons:
- URL normalization mismatch (e.g., http vs https, trailing slashes)
- The citation key generation failed
- The citation was marked as "failed" and skipped
- The markdown content was modified between extraction and replacement

### Where Ampersand Escaping Happens

**Attempt 1** (Failed): Escape before Pandoc
```python
# Line 1138: After citation replacement, before Pandoc
content = self._escape_ampersands_in_markdown_links(content)
# Problem: Pandoc processes the escaped content and may re-interpret \&
```

**Attempt 2** (Current): Escape after Pandoc
```python
# Line 1205: After Pandoc, in LaTeX content
latex_content = self._escape_ampersands_in_markdown_links(latex_content)
# Then line 1207-1228: Escape all remaining & characters
```

## Questions for External Review

### Q1: Citation Replacement Debugging Strategy

The `replace_citations_in_text()` function should replace `[text](url)` with `\citep{key}`, but it's not working for some citations. What's the best debugging approach to diagnose why?

**Current observations**:
- The function uses `content.find(search_pattern)` where `search_pattern = f"]({citation.url})"`
- For GarmentCode citation: `search_pattern = "](https://doi.org/10.1145/3618394)"`
- This pattern SHOULD exist in the markdown content
- But the TEX output shows the markdown link is still there

**Debugging steps to consider**:
1. Log `len(self.citations)` to confirm citations were extracted
2. Log each `citation.url` being searched
3. Log whether `content.find(search_pattern)` returns -1 (not found)
4. Log the actual `content` substring around where the citation should be
5. Check if URL normalization happened differently between extraction and replacement

### Q2: Pandoc's Markdown Link Handling

When Pandoc converts markdown to LaTeX, how does it handle markdown links `[text](url)` that weren't already converted to LaTeX commands?

**Observed behavior**:
- Input to Pandoc: `[GarmentCode (Korosteleva & Sorkine-Hornung, 2023)](https://doi.org/10.1145/3618394)`
- Output from Pandoc: Same markdown syntax (not converted)
- Expected: Pandoc should convert to `\href{URL}{text}` or similar

**Questions**:
- Does Pandoc only convert links if they're simple text, not complex citations?
- Does Pandoc preserve markdown links in certain contexts (e.g., inside code blocks)?
- Are there Pandoc flags that force markdown link conversion?

### Q3: Character-by-Character vs AST Parsing

The codebase policy is "NEVER use regex, use AST parsers". Currently using character-by-character state machines for:
- Finding markdown links: Track `[` and `]` depth, then check for `(`
- Escaping ampersands: Iterate through string, escape unescaped `&`

**Questions**:
- Is character-by-character parsing considered "AST" or is it just "not regex"?
- For markdown links, should we use markdown-it-py's AST output instead of manual parsing?
- Would markdown-it-py's AST give us better handling of nested structures?

### Q4: Post-Pandoc Escaping Timing

Currently escaping ampersands AFTER Pandoc at line 1205. But the TEX file still has unescaped `&`.

**Possible explanations**:
1. The function runs but the modified `latex_content` isn't saved (variable scope issue?)
2. The markdown links are in a format the parser doesn't recognize after Pandoc processing
3. Pandoc is doing something special with these links (wrapping them, escaping them differently)
4. There's a later step that overwrites the escaped content

**How to verify**:
- Add `print(latex_content[:1000])` before and after escaping to confirm it ran
- Check if the escaped content is actually returned and used
- Verify no later processing steps modify the content

## Proposed Solutions

### Immediate Fix: Escape ALL Ampersands (Brute Force)

Since the markdown-link-specific escaping isn't working, just escape EVERY unescaped `&` in the entire LaTeX output:

```python
# After Pandoc, lines 1207-1228 already do this
# But it should catch the & in the markdown links too
# Why isn't it working?
```

**Verify this is actually running**: Add debug logging.

### Proper Fix: Debug Citation Replacement

1. Add comprehensive logging to `replace_citations_in_text()`:
   ```python
   logger.info(f"Replacing {len(self.citations)} citations")
   for key, citation in self.citations.items():
       search_pattern = f"]({citation.url})"
       pos = content.find(search_pattern)
       if pos == -1:
           logger.warning(f"Citation not found in content: {citation.url}")
           logger.debug(f"Searching for: {search_pattern}")
           # Log nearby content to see what's actually there
       else:
           logger.info(f"Found citation at position {pos}")
   ```

2. Check URL normalization consistency
3. Verify the citation wasn't filtered out as "failed"

### Alternative: Use Pandoc's Citation Extension

Pandoc has built-in citation support with `--citeproc`. Could reformat citations to Pandoc's format:
```markdown
[@korosteleva2023]
```

But this requires changing the entire input format.

## Implementation Notes

- **NO REGEX allowed**: Project policy is to use AST parsers or character-by-character state machines
- **Must be deterministic**: Same input must produce same output every time
- **Existing code uses**:
  - markdown-it-py for AST parsing of markdown
  - pypandoc for markdown→LaTeX conversion
  - Character-by-character iteration for string transformations

## Questions for Review

1. Why would `content.find("](' + url + ')")` fail if the URL exists in the content?
2. What could cause escaping functions to run without modifying the output?
3. How can we verify Pandoc isn't re-processing or undoing our markdown link modifications?
4. Is there a better architectural approach than "escape after Pandoc"?

## Related Files

- `src/converters/md_to_latex/converter.py` (main conversion pipeline)
- `src/converters/md_to_latex/citation_manager.py` (citation replacement logic)
- `src/converters/md_to_latex/citation_extractor_unified.py` (extraction using AST)
- `src/parsers/markdown_parser.py` (markdown-it-py wrapper)
