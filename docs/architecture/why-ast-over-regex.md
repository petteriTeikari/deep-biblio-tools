# Why AST Over Regex: A Practical Decision

## The Problem with Regex-Based Parsing

This document explains why we chose to migrate from regex to AST-based parsing. This decision was made based on practical coding experience, particularly when working with AI coding assistants like Claude Code.

## The Whack-a-Mole Problem

### What Happened with Regex

When using regex to parse structured documents (LaTeX, Markdown, BibTeX), we encountered a frustrating pattern:

1. **Initial regex works** for simple cases:
   ```python
   # Looks simple enough
   citation_pattern = r'\\cite\{([^}]+)\}'
   ```

2. **Edge case appears**:
   ```latex
   \cite{author{2020}}  # Nested braces break it
   ```

3. **Fix the regex**:
   ```python
   # Now handling nested braces... getting complex
   citation_pattern = r'\\cite\{(?:[^{}]|\{[^}]*\})*\}'
   ```

4. **Another edge case**:
   ```latex
   \cite{author\{2020\}}  # Escaped braces break it
   ```

5. **Fix again** (regex becomes unreadable):
   ```python
   # Now it's a monster
   citation_pattern = r'\\cite\{(?:[^{}\\]|\\.|\\{(?:[^{}\\]|\\.)*\\})*\}'
   ```

6. **And another**:
   ```latex
   \cite{%
     author2020  % Comment in citation
   }
   ```

7. **Give up** or create an even more complex regex that nobody understands

### The AI Assistant Problem

When working with Claude Code or similar AI assistants:

1. **AI suggests a regex** that works for the example you gave
2. **You find an edge case** the regex doesn't handle
3. **AI fixes the regex** for that specific case
4. **You find another edge case**
5. **AI fixes again**, often breaking the previous fix
6. **Repeat endlessly**

This whack-a-mole game happens because:
- Regex is not the right tool for parsing nested structures
- Each fix makes the regex more complex and fragile
- AI assistants struggle to see all edge cases at once
- Testing becomes combinatorial (which edge cases combine?)

## Why AST Works Better

### 1. Proper Tool for the Job

AST parsers are designed for structured documents:
```python
# With AST, this just works
parser = LaTeXParser()
doc = parser.parse(content)
for node in doc.find_all('cite'):
    citations = node.arguments  # Handles ALL cases
```

### 2. AI Assistants Work Better with AST

When using AST:
- **Clear structure**: "Find all citation nodes" vs "Match this pattern but not when..."
- **Predictable behavior**: Parser handles edge cases, not our code
- **Easier to explain**: "Update the journal field" vs "Replace the text between the 3rd and 4th comma unless..."

### 3. Maintainability

Compare these two approaches:

**Regex approach** (real example from our codebase):
```python
# What does this even do? Good luck modifying it!
pattern = r'(?<!\w)(?:DOI|doi)[\s:]*(?:https?://(?:dx\.)?doi\.org/)?(?P<doi>10\.\d{4,}(?:\.\d+)*/.+?)(?=[\s,;]|$)'
```

**AST approach**:
```python
# Self-documenting
doi_nodes = doc.find_all(type='doi')
for node in doi_nodes:
    if node.is_valid():
        process_doi(node.value)
```

### 4. Robustness

AST parsers handle:
- Nested structures (braces within braces within braces)
- Comments in unexpected places
- Escaped characters
- Malformed input (with error recovery)
- Unicode properly
- Whitespace variations

All without us writing complex patterns.

## Real Examples from This Codebase

### Example 1: Citation Extraction

**Regex attempt** (simplified from actual code):
```python
# Started simple
r'\\cite\{([^}]+)\}'

# Grew to handle edge cases
r'\\cite(?:\[[^\]]*\])?\{([^}]+)\}'

# Grew more for nested braces
r'\\cite(?:\[[^\]]*\])?\{(?:[^{}]|\{[^}]*\})*\}'

# Still breaks on \cite{author{2020}{nested}}
```

**AST solution**:
```python
citations = doc.find_all('cite')
# Done. It handles everything.
```

### Example 2: MDPI Journal Fix

**Regex nightmare**:
```python
# Need to find journal name in BibTeX, but:
# - Could be journal = {Name}
# - Could be journal={Name}
# - Could be journal = "Name"
# - Could have newlines
# - Could have escaped quotes
# - Could be commented out
# Each "fix" broke other cases
```

**AST approach**:
```python
entry = bibtex_parser.parse_entry(text)
if entry.fields.get('journal'):
    entry.fields['journal'] = fix_mdpi_name(entry.fields['journal'])
# Parser handles ALL syntax variations
```

## When Regex is Still OK

We're not saying "never use regex". Use regex for:
- Simple, flat patterns (DOIs, ISBNs, email addresses)
- Quick validation before parsing
- Content that's guaranteed to be simple

But for structured documents, use a proper parser.

## The Empirical Evidence

We don't have formal benchmarks, but empirically:
- Time spent debugging regex edge cases: Hours per pattern
- Time spent debugging AST code: Minutes
- Regex code that handles all cases: Often impossible
- AST code that handles all cases: Default behavior

## Message to Future Developers (Including AI Assistants)

**DO NOT GO BACK TO REGEX** for parsing structured documents.

If you're tempted because:
- "Regex would be simpler here" - It won't be once you handle edge cases
- "AST is overkill" - It's the right tool for the job
- "Performance concerns" - Measure first; correctness matters more
- "The AST parser is complex" - Less complex than correct regex

Remember: Every complex regex in this codebase started as a "simple" pattern.

## The Vibe Check

The ultimate test: Which code would you rather debug at 3 AM?

```python
# Regex
if re.match(r'(?:\\(?:sub)*section\{[^}]*\}|\\cite(?:\[[^\]]*\])?\{(?:[^{}]|\{[^}]*\})*\})', text):
    # What does this match? What doesn't it? Who knows!
```

```python
# AST
if node.type in ['section', 'subsection', 'cite']:
    # Crystal clear
```

Choose tools that make coding enjoyable, not frustrating.

---

*This document exists because we learned this lesson the hard way. Please don't repeat our mistakes.*
