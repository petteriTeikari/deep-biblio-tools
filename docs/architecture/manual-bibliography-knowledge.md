# Manual Bibliography Knowledge Base

## Table of Contents
1. [Why Manual Bibliographies Exist](#why-manual-bibliographies-exist)
2. [The Width Parameter Mystery](#the-width-parameter-mystery)
3. [Author-Year Format Patterns](#author-year-format-patterns)
4. [Common Failure Modes](#common-failure-modes)
5. [Integration with natbib](#integration-with-natbib)
6. [Best Practices](#best-practices)
7. [Troubleshooting Guide](#troubleshooting-guide)

## Why Manual Bibliographies Exist

Despite the availability of BibTeX and modern bibliography management tools, manual bibliographies using `\begin{thebibliography}` are still common for several reasons:

### Journal Requirements
Many academic journals, especially older or more traditional ones, require submissions with self-contained LaTeX files. They may not accept:
- External `.bib` files
- Custom `.bst` style files
- Complex bibliography setups

### Legacy Document Maintenance
- Documents created before BibTeX became standard
- Inherited documents from colleagues or predecessors
- Documents that have been manually maintained for years

### Special Formatting Needs
- Custom citation formats not easily achievable with standard styles
- Mixed citation styles within a single document
- Non-standard bibliographic entries (e.g., social media posts, software)

### Legal/Archival Requirements
- Documents that must be completely self-contained
- Submissions to repositories that don't allow external files
- Legal documents requiring specific citation formats

### Control and Simplicity
- Authors who prefer direct control over formatting
- Small documents where BibTeX setup seems overkill
- Quick one-off documents

## The Width Parameter Mystery

The `\begin{thebibliography}{width}` parameter is one of the most misunderstood aspects of LaTeX bibliographies.

### What It Really Does

The width parameter is **NOT** the number of bibliography entries! It's a template for the widest label that will appear in the bibliography.

```latex
\begin{thebibliography}{9}    % Space for labels like [1], [2], ..., [9]
\begin{thebibliography}{99}   % Space for labels like [1], [2], ..., [99]
\begin{thebibliography}{999}  % Space for labels like [1], [2], ..., [999]
\begin{thebibliography}{ABC}  % Space based on width of "ABC"
```

### Common Mistakes

1. **Using entry count as width**
   ```latex
   % WRONG: 50 entries doesn't mean width should be 50
   \begin{thebibliography}{50}
   ```

2. **Not updating width when bibliography grows**
   ```latex
   % Problem: Started with <100 entries, now have 150
   \begin{thebibliography}{99}  % Labels [100]-[150] will misalign!
   ```

3. **Using arbitrary strings**
   ```latex
   % Confusing: What does this even mean?
   \begin{thebibliography}{Smith2023}
   ```

### How to Choose Correct Width

| Number of Entries | Correct Width Parameter |
|-------------------|------------------------|
| 1-9               | `{9}`                  |
| 10-99             | `{99}`                 |
| 100-999           | `{999}`                |
| 1000-9999         | `{9999}`               |

### Visual Example of Width Problems

With `{99}` for 100+ entries:
```
[98]  Smith, J. (2023). Title...
[99]  Jones, A. (2023). Title...
[100] Williams, B. (2023). Title...  ← Misaligned!
[101] Brown, C. (2023). Title...     ← Misaligned!
```

With correct `{999}`:
```
[98]  Smith, J. (2023). Title...
[99]  Jones, A. (2023). Title...
[100] Williams, B. (2023). Title...  ← Properly aligned
[101] Brown, C. (2023). Title...     ← Properly aligned
```

## Author-Year Format Patterns

### Basic Rules

1. **Single Author**
   ```latex
   \bibitem[Smith(2025)]{smith2025}
   ```

2. **Two Authors**
   ```latex
   \bibitem[Smith and Jones(2025)]{smithjones2025}
   ```

3. **Three or More Authors**
   ```latex
   \bibitem[Smith et al.(2025)]{smith2025}
   ```

4. **No Space Before Year**
   - Correct: `Smith(2025)`
   - Wrong: `Smith (2025)`

### International Name Handling

#### Surname Prefixes
Common prefixes that should be included with the surname:

| Language | Prefixes | Example |
|----------|----------|---------|
| Dutch | van, van der, van den | van der Waals |
| German | von, von der | von Neumann |
| French | de, de la, du | de Gaulle |
| Italian | di, della, del | di Marco |
| Portuguese | da, das, do, dos | da Silva |
| Spanish | de, de la, de los | de la Cruz |

#### Capitalization Rules
- At sentence start: "Van der Waals showed..."
- Mid-sentence: "The work by van der Waals..."

#### Asian Names
Be careful with name order:
- Chinese: Often "Family Given" (e.g., Wang Xiaoming)
- Japanese: Can be either order in English publications
- Korean: Usually "Family Given" (e.g., Kim Jong-un)

### Organization/Corporate Authors

1. **Single Organization**
   ```latex
   \bibitem[IEEE(2025)]{ieee2025}
   \bibitem[Microsoft(2025)]{microsoft2025}
   ```

2. **Organization with "and" in Name**
   ```latex
   \bibitem[Procter and Gamble(2025)]{pg2025}  % NOT "Procter and Gamble"
   ```

3. **Government Agencies**
   ```latex
   \bibitem[U.S. Department of Energy(2025)]{doe2025}
   ```

4. **Websites/URLs as Authors**
   ```latex
   \bibitem[github.com(2025)]{github2025}
   ```

### Special Cases

1. **Anonymous Works**
   ```latex
   \bibitem[Anonymous(2025)]{anon2025}
   ```

2. **No Year**
   ```latex
   \bibitem[Smith(n.d.)]{smithnd}
   ```

3. **In Press/Forthcoming**
   ```latex
   \bibitem[Jones(in press)]{jonesinpress}
   \bibitem[Williams(forthcoming)]{williams2025}
   ```

## Common Failure Modes

### 1. Ambiguous Author-Title Boundaries

**Problem:**
```latex
\bibitem{prob1} \href{...}{Smith (2025) Machine Learning (2025) Applications}
```

**Why it fails:** Multiple years make it unclear where authors end.

**Solution:** Look for the first year in parentheses after text that looks like names.

### 2. Already Formatted Entries

**Problem:**
```latex
\bibitem{prob2} \href{...}{Smith et al. (2025)}
```

**Why it fails:** Processing "et al." again would create "Smith et al. et al."

**Solution:** Detect existing "et al." and handle appropriately.

### 3. LaTeX Commands in Names

**Problem:**
```latex
\bibitem{prob3} \href{...}{Sm\"{i}th, Jos\'{e} (2025)}
```

**Why it fails:** LaTeX accents complicate name parsing.

**Solution:** Strip LaTeX commands before processing, preserve in output.

### 4. Multiple Hyperlinks

**Problem:**
```latex
\bibitem{prob4} \href{url1}{Smith (2025)} Also at \href{url2}{mirror}
```

**Why it fails:** Multiple `\href` commands complicate parsing.

**Solution:** Process only the first `\href` for author extraction.

### 5. Malformed BibTeX Field Names in Content

**Problem:**
```latex
\bibitem{prob5} given=John, family=Smith (2025)
```

**Why it fails:** BibTeX field syntax leaked into manual entry.

**Solution:** Detect and parse BibTeX-like patterns specially.

## Integration with natbib

### How `\bibitem[label]{key}` Works

The natbib package uses the optional argument to `\bibitem` for author-year citations:

```latex
\usepackage[authoryear,round]{natbib}

% In bibliography:
\bibitem[Smith(2025)]{smith2025} Smith, J. (2025). Title...

% In text:
\citep{smith2025}     % Produces: (Smith, 2025)
\citet{smith2025}     % Produces: Smith (2025)
\citep*{smith2025}    % Produces: (Smith, 2025) with full author list
\citeauthor{smith2025} % Produces: Smith
\citeyear{smith2025}   % Produces: 2025
```

### Sorting Considerations

Manual bibliographies don't automatically sort. Options:

1. **Maintain alphabetical order manually**
2. **Use citation order** (order of first appearance)
3. **Group by type** (books, articles, websites)

### Multiple Citations

With proper labels, natbib handles multiple citations:
```latex
\citep{smith2025,jones2024,williams2023}
% Produces: (Smith, 2025; Jones, 2024; Williams, 2023)
```

## Best Practices

### When to Use Manual Bibliographies

✅ **Good Cases:**
- Journal requires self-contained submission
- Small document with <20 references
- One-time document with special formatting needs
- Legacy document maintenance

❌ **Avoid When:**
- Managing >50 references
- Multiple documents share references
- Frequent updates needed
- Standard formatting is acceptable

### Formatting Guidelines

1. **Consistency is Key**
   - Use the same format for all entries
   - Consistent punctuation and spacing
   - Consistent abbreviations

2. **Include All Information**
   ```latex
   \bibitem[Author(Year)]{key} \href{url}{Author (Year)} Title.
   Journal Volume(Number):Pages.
   ```

3. **Version Control Friendly**
   - One entry per `\bibitem`
   - Consistent indentation
   - Meaningful citation keys

### Validation Strategies

1. **Check Label Width**
   ```bash
   # Count entries
   grep -c "\\bibitem" bibliography.tex
   ```

2. **Verify All Citations Exist**
   ```bash
   # Find all \cite commands
   grep -oh "\\cite{[^}]*}" main.tex | sort | uniq
   ```

3. **Look for Duplicates**
   ```bash
   # Find duplicate keys
   grep -oh "\\bibitem{[^}]*}" bibliography.tex | sort | uniq -d
   ```

## Troubleshooting Guide

### Error Messages and Solutions

1. **"Citation undefined"**
   - Check citation key matches exactly
   - Ensure bibliography is processed
   - Run LaTeX twice

2. **"Missing number, treated as zero"**
   - Width parameter might be wrong
   - Check for malformed `\bibitem` commands

3. **Misaligned Bibliography**
   - Width parameter too small
   - Mixed label formats

### Common Fixes

1. **Convert to BibTeX**
   ```python
   # Extract to .bib format
   python scripts/extract_to_bib.py manual.tex -o refs.bib
   ```

2. **Fix Width Parameter**
   ```python
   python scripts/fix-manual-biblio-to-authornames.py input.tex --fix-width
   ```

3. **Sort Entries**
   ```python
   python scripts/sort_manual_bib.py input.tex -o sorted.tex
   ```

### When to Give Up and Use BibTeX

Consider switching when:
- You spend more time formatting than writing
- You need to reuse references across documents
- You need complex formatting (e.g., different styles for different entry types)
- Your bibliography exceeds 100 entries
- Multiple authors need to maintain the bibliography

### Getting Help

1. **Check LaTeX logs**
   ```bash
   grep -i "warning\|error" document.log
   ```

2. **Validate format**
   ```bash
   python scripts/validate_manual_bib.py document.tex
   ```

3. **Community resources**
   - tex.stackexchange.com
   - LaTeX subreddit
   - Journal style guides

## Quick Reference Card

### Width Parameter Quick Check
```
Entries    Width
1-9        {9}
10-99      {99}
100-999    {999}
1000+      {9999}
```

### Author Formatting Quick Reference
```
1 author:     Smith(2025)
2 authors:    Smith and Jones(2025)
3+ authors:   Smith et al.(2025)
Organization: IEEE(2025)
No year:      Smith(n.d.)
```

### Debugging Commands
```bash
# Count entries
grep -c "\\bibitem" file.tex

# Check width
grep "begin{thebibliography}" file.tex

# Find malformed entries
grep -n "\\bibitem" file.tex | grep -v "\\bibitem\[.*\]{"

# Extract all keys
grep -o "\\bibitem{[^}]*}" file.tex | sed 's/\\bibitem{//' | sed 's/}//'
```

## Conclusion

Manual bibliographies remain a necessary evil in academic publishing. While BibTeX is generally preferred, understanding manual bibliography management is essential for:
- Meeting journal requirements
- Maintaining legacy documents
- Handling special cases
- Emergency situations

The key to success is understanding the width parameter, maintaining consistency, and knowing when to convert to BibTeX.
