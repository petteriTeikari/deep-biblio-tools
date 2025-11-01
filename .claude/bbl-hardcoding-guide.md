# .bbl Hardcoding Guide

**Purpose**: Understand when and how to use hardcoded .bbl files with hyperlinked authors for final paper submission.

**Last Updated**: 2025-11-01

---

## What is .bbl Hardcoding?

**.bbl hardcoding** converts your bibliography from external .bib file format to inline LaTeX code embedded directly in your .tex file.

**Normal workflow**:
```latex
\bibliography{references}
\bibliographystyle{spbasic}
```
→ BibTeX reads references.bib → generates .bbl → included at compile time

**Hardcoded workflow**:
```latex
\begin{thebibliography}{99}
\bibitem{niinimaki_environmental_2020}
\href{https://doi.org/10.1038/s43017-020-0039-9}{Niinimäki K, Peters G, Dahlbo H, Perry P, Rissanen T, Gwilt A (2020)} The environmental price of fast fashion. {\em Nature Reviews Earth \& Environment 1}(4):189--200.
\end{thebibliography}
```
→ Bibliography is part of .tex file → no external files needed

---

## Why Hardcode .bbl?

### 1. Hyperlinked Authors (Main Benefit)

**Normal bibliography**:
```
Niinimäki K, Peters G, Dahlbo H, et al. (2020) The environmental price...
```
→ Authors are plain text, not clickable

**Hardcoded with hyperlinks**:
```latex
\href{https://doi.org/10.1038/...}{Niinimäki K, et al. (2020)} The environmental...
```
→ Authors + year become clickable link to DOI/arXiv in PDF

**Result**: Readers can click author names to access the paper directly.

### 2. Final Submission Requirements

Some journals/conferences require:
- Single .tex file (no external .bib)
- Standalone document
- Camera-ready format

### 3. Archival Versions

For long-term storage:
- Self-contained document
- No dependency on external bibliography file
- Easier to share and reproduce

### 4. Manual Control

Allows hand-editing .bbl for:
- Fixing formatting issues
- Adjusting spacing
- Handling special cases

---

## When to Use .bbl Hardcoding

### Use Hardcoded .bbl When:
- ✅ Final journal/conference submission
- ✅ Creating archival version
- ✅ Want clickable author-year links in PDF
- ✅ Need to manually edit bibliography formatting
- ✅ Submitting to arXiv or similar

### Keep External .bib When:
- ❌ Still developing/writing paper
- ❌ Bibliography might change
- ❌ Collaborating with others who use .bib
- ❌ Need to regenerate bibliography from Zotero

---

## User's Workflow (From Planning Docs)

Based on research, this is your actual workflow:

1. **Run markdown → LaTeX conversion**
   - Input: `mcp-draft-refined-v5.md`
   - Output: `output/mcp-draft-refined-v5.tex`, `output/references.bib`
   - references.bib is EPHEMERAL (deleted before each conversion)

2. **Compile with BibTeX**
   ```bash
   cd output/
   xelatex mcp-draft-refined-v5
   bibtex mcp-draft-refined-v5
   xelatex mcp-draft-refined-v5
   xelatex mcp-draft-refined-v5
   ```
   - This generates `mcp-draft-refined-v5.bbl`

3. **Optionally modify .bbl by hand**
   - Fix formatting issues
   - Adjust author names
   - Handle special cases
   - The .bbl is now your working file

4. **Hardcode .bbl into .tex** (two options):

   **Option A**: Use hardcoding script
   ```bash
   python scripts/hardcode_bibliography.py output/references.bib output/mcp-draft-refined-v5.tex
   ```

   **Option B**: Manually copy .bbl content
   - Copy content from .bbl file
   - Paste into .tex file before `\end{document}`
   - Remove `\bibliography{}` and `\bibliographystyle{}` commands

5. **Final .tex has embedded bibliography**
   - No external .bib or .bbl needed
   - Self-contained document
   - Hyperlinked authors (if script was used)

---

## Available Scripts

### Script 1: hardcode_bibliography.py

**Location**: `scripts/hardcode_bibliography.py` (731 lines)

**Purpose**: Standard .bbl hardcoding with hyperlinked authors

**Key Function** (`format_entry`, lines 417-505):
```python
def format_entry(self, entry: BibEntry) -> str:
    """Format a single bibliography entry with hyperlinked authors and year."""
    # Get URL for hyperlinking (DOI preferred, then URL)
    link_url = entry.url or (f"https://doi.org/{entry.doi}" if entry.doi else "")

    # Create hyperlinked author-year
    if link_url:
        author_year = f"\\href{{{link_url}}}{{{entry.authors} ({entry.year})}}"
    else:
        author_year = f"{entry.authors} ({entry.year})"

    # Build entry
    parts = [f"\\bibitem{{{entry.key}}}", author_year, entry.title]

    # Add venue (journal/conference) in italics
    if entry.journal:
        parts.append(f"{{\\em {entry.journal} {entry.volume}}}({entry.number}):{entry.pages}")

    return " ".join(parts) + "."
```

**Usage**:
```bash
python scripts/hardcode_bibliography.py INPUT.bib OUTPUT.tex
```

**What it does**:
1. Parses .bib file
2. For each entry, creates formatted bibliography item with hyperlinked author-year
3. Generates `\begin{thebibliography}...\end{thebibliography}`
4. Optionally embeds into .tex file (replaces `\bibliography{}` commands)

### Script 2: create_hardcoded_bibliography_uadreview.py

**Location**: `scripts/create_hardcoded_bibliography_uadreview.py` (581 lines)

**Purpose**: Variant with natbib label support

**Key Function** (`format_natbib_entry`, lines 431-497):
```python
def format_natbib_entry(self, entry: BibEntry) -> str:
    """Format with natbib authoryear labels like [Smith et al.(2020)]."""
    # Creates: \bibitem[Smith et al.(2020)]{key}
    # Instead of: \bibitem{key}
```

**Usage**:
```bash
python scripts/create_hardcoded_bibliography_uadreview.py INPUT.bib OUTPUT.tex
```

**Difference**: Includes natbib-style labels for authoryear citation style.

---

## Example: Before vs After Hardcoding

### Before (Normal .tex with external .bib):
```latex
\documentclass{article}
\begin{document}

Fashion industry impacts \citep{niinimaki_environmental_2020}.

\bibliographystyle{spbasic}
\bibliography{references}

\end{document}
```

**Requires**:
- `references.bib` file
- BibTeX compilation step
- Generated .bbl file

### After (Hardcoded .bbl):
```latex
\documentclass{article}
\begin{document}

Fashion industry impacts \citep{niinimaki_environmental_2020}.

\begin{thebibliography}{99}

\bibitem{niinimaki_environmental_2020}
\href{https://doi.org/10.1038/s43017-020-0039-9}{Niinimäki K, Peters G, Dahlbo H, Perry P, Rissanen T, Gwilt A (2020)} The environmental price of fast fashion. {\em Nature Reviews Earth \& Environment 1}(4):189--200.

\end{thebibliography}

\end{document}
```

**Requires**:
- Nothing external
- Single .tex file
- Clickable author-year links

---

## Formatting Rules (from bibliography-formatting-rules.md)

### Academic Papers (DOI/arXiv)

**Journal article**:
```latex
\href{URL}{Authors (Year)} Title. {\em Journal Volume}(Number):Pages.
```

**arXiv preprint**:
```latex
\href{URL}{Authors (Year)} Title. {\em arXiv:ID}.
```

**Conference paper**:
```latex
\href{URL}{Authors (Year)} Title. {\em Proceedings Title}:Pages.
```

### Non-Academic References

**Include access date**:
```latex
\href{URL}{Organization (Year)} Title. (accessed YYYY-MM-DD).
```

### Special Characters

- **Page ranges**: `46-56` → `46--56` (double dash)
- **HTML entities**: `&amp;` → `&`, `&lt;` → `<`
- **LaTeX escaping**: `$` → `\$`, `%` → `\%`

---

## Common Issues and Solutions

### Issue 1: References.bib is Missing

**Problem**: Script can't find references.bib after conversion

**Reason**: references.bib is EPHEMERAL (deleted before each conversion as stated in planning docs)

**Solution**:
1. Run conversion → generates fresh references.bib
2. Immediately run hardcoding script
3. OR save references.bib to permanent location first

### Issue 2: .bbl Has Manual Edits

**Problem**: Hardcoding script overwrites manual edits in .bbl

**Solution**:
1. Save your manually edited .bbl to a different file
2. Copy content manually into .tex (don't use script)
3. OR apply manual edits after script runs

### Issue 3: Hyperlinks Don't Work

**Problem**: Author-year appears as plain text, not clickable

**Check**:
1. Did you use `\href{}{}` commands?
2. Is `hyperref` package loaded in .tex?
3. Did you compile with XeLaTeX (not pdfLaTeX)?

### Issue 4: Bibliography Order Wrong

**Problem**: Want alphabetical but got citation order (or vice versa)

**Solution**:
- Script has options for sort order
- OR manually reorder entries in .bbl before embedding

---

## Integration with Conversion Pipeline

**Current State** (from research):

1. **Conversion generates references.bib** (ephemeral)
2. **User compiles with BibTeX** → generates .bbl
3. **User may modify .bbl** by hand
4. **User copies .bbl into .tex** for final submission

**Key Insight**: references.bib is NOT the source of truth. The modified .bbl is.

**Workflow**:
```
Markdown → Conversion → references.bib (ephemeral)
                              ↓
                        BibTeX compile
                              ↓
                          .bbl file
                              ↓
                     Manual edits (optional)
                              ↓
                     Copy into .tex (hardcode)
                              ↓
                    Final .tex (standalone)
```

---

## Verification

### Check Hyperlinks Work:
```bash
# Compile and open PDF
xelatex mcp-draft-refined-v5.tex
open mcp-draft-refined-v5.pdf

# Try clicking on author names in bibliography
# Should open DOI/arXiv link in browser
```

### Count Hardcoded Entries:
```bash
# Count bibitem commands
grep -c "\\bibitem{" mcp-draft-refined-v5.tex

# Should match total bibliography entries
```

### Verify No External Dependencies:
```bash
# Search for external bibliography commands
grep -E "\\bibliography{|\\bibliographystyle{" mcp-draft-refined-v5.tex

# Should return empty (no matches)
```

---

## Summary

**Key Takeaways**:

1. **.bbl hardcoding = embed bibliography in .tex** with hyperlinked authors
2. **Use for**: Final submissions, archival versions, clickable links
3. **Don't use for**: Active development, changing bibliography
4. **references.bib is ephemeral** - deleted before each conversion
5. **Two scripts available**: standard and natbib variant
6. **Manual workflow**: Compile → Edit .bbl → Copy into .tex

**For More Context**:
- Example formatting: `docs/reference/bibliography-formatting-rules.md`
- Script implementation: `scripts/hardcode_bibliography.py:417-656`
- User workflow: Research report Section 3 (2025-11-01)
