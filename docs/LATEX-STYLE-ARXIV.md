# arXiv LaTeX Style Template

**Reference Paper**: https://arxiv.org/pdf/2508.02765 (UAD Review Paper)
**Template Source**: `/Users/petteri/Dropbox/LABs/KusiKasa/papers/uadReview/main.tex`

---

## Style Overview

The arXiv submission style produces professional academic papers with:

- **Two-column layout** with tight margins for content density
- **Hyperlinked author names** in citations (BrickRed color)
- **Embedded bibliography** (.bbl pasted into main.tex for single-file arXiv submission)
- **Formatted cross-references** with proper capitalization
- **Custom tcolorbox** environments for concept boxes
- **spbasic_pt** bibliography style with author-year citations

---

## Document Class and Geometry

```latex
\documentclass[10pt,a4paper,twocolumn]{article}
\geometry{top=0.75in, bottom=0.75in, left=0.75in, right=0.75in, columnsep=0.25in}
```

**Key Parameters**:
- `10pt` font size (arXiv standard)
- `a4paper` for international compatibility
- `twocolumn` for compact layout
- Tight margins (0.75in) for maximum content density
- Column separation: 0.25in

---

## Essential Packages (in order)

```latex
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage[dvipsnames]{xcolor}  % Named colors for hyperref
\usepackage[english]{babel}
\usepackage{geometry}
\usepackage{microtype}  % Better typography
\usepackage{listings}
\usepackage{caption}
\usepackage{subcaption}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{multirow}
\usepackage{array}
\usepackage{float}
\usepackage{textcomp}  % Special symbols
\usepackage{balance}  % Balance last page columns
```

---

## Bibliography Configuration

```latex
\usepackage[authoryear,round]{natbib}
```

**Critical Detail**: Uses **natbib** with traditional BibTeX (NOT biblatex).
This allows embedding the `.bbl` file directly for arXiv single-file submission.

---

## Hyperref Configuration (The Key Style Element!)

```latex
\usepackage{hyperref}
\hypersetup{
    colorlinks=true,
    linkcolor=NavyBlue,     % Internal links (sections, figures)
    citecolor=NavyBlue,     % Citation links (author names)
    urlcolor=NavyBlue       % URLs in bibliography
}
```

**This is what creates the signature look**:
- Author names in citations are **hyperlinked in NavyBlue**
- Internal references (Figure X, Section Y) are in **NavyBlue**
- URLs in bibliography entries are in **NavyBlue**
- All hyperlinks use the same professional dark blue color

---

## Custom Symbol Commands

```latex
\newcommand{\textinfty}{\ensuremath{\infty}}
\newcommand{\textapprox}{\ensuremath{\approx}}
\newcommand{\textdiv}{\ensuremath{\div}}
\newcommand{\textneq}{\ensuremath{\neq}}
\newcommand{\textgreaterequal}{\ensuremath{\geq}}
\newcommand{\textlessequal}{\ensuremath{\leq}}
\newcommand{\texttimes}{\ensuremath{\times}}
```

For text-mode mathematical symbols (avoid inline math mode).

---

## URL Prefix Definition

```latex
\newcommand{\urlprefix}{URL: }
```

Required for `spbasic_pt` bibliography style.

---

## Concept Box Styling

```latex
\usepackage{tcolorbox}
\tcbuselibrary{skins,breakable}

\begin{tcolorbox}[
    colback={rgb,255:red,218;green,224;blue,232},   % Light blue background
    colframe={rgb,255:red,180;green,190;blue,200},  % Darker blue border
    title={\textbf{Box Title}},
    fonttitle=\bfseries,
    boxrule=1pt,
    arc=4pt,
    outer arc=4pt,
    top=10pt,
    bottom=10pt,
    left=10pt,
    right=10pt
]
Content here
\end{tcolorbox}
```

---

## Citation Format Examples

### In-text Citations
```latex
\citep{author2024}              % (Author, 2024)
\citep{author2023, author2024}  % (Author, 2023, 2024)
\cite{author2024}               % Author (2024)
```

**Result in PDF**:
- Author names are **hyperlinked** to bibliography
- Links appear in **BrickRed** color
- Clicking jumps to bibliography entry

---

## Formatted Cross-References

### Section References
```latex
Section~\ref{sec:intro}         % Section 1
see Section~\ref{sec:methods}   % see Section 3.2
```

**Style Rule**: Capitalize "Section" when referencing explicitly.

### Figure References
```latex
Figure~\ref{fig:diagram}        % Figure 3
(see Figure~\ref{fig:plot})     % (see Figure 5)
```

**Style Rule**: Always capitalize "Figure", use non-breaking space `~`.

### Table References
```latex
Table~\ref{tab:results}         % Table 2
as shown in Table~\ref{tab:comparison}
```

**Style Rule**: Always capitalize "Table", use non-breaking space `~`.

---

## Bibliography Embedding (arXiv Single-File Submission)

### Step 1: Compile with BibTeX
```bash
xelatex main
bibtex main  # Generates main.bbl
xelatex main
xelatex main
```

### Step 2: Embed .bbl into main.tex

Replace this:
```latex
{\scriptsize
\bibliographystyle{spbasic_pt}
\bibliography{references}
}
```

With this:
```latex
{\scriptsize
\begin{thebibliography}{999}

\bibitem[Author(2024)]{author2024}
Author, A. (2024) \emph{Paper Title}.
Journal Name 12(3):45--67,
\href{https://doi.org/10.1234/example}{https://doi.org/10.1234/example}

% ... more entries ...

\end{thebibliography}
}
```

**Key Details**:
- Copy entire content of `.bbl` file
- Paste inside `\begin{thebibliography}...\end{thebibliography}`
- Keep `{\scriptsize` wrapper for compact bibliography
- URLs are automatically hyperlinked via hyperref

---

## Table Formatting

### Two-Column Spanning Tables
```latex
\begin{table*}[htbp]
\centering
\footnotesize
\begin{tabular}{@{}p{0.19\textwidth} p{0.19\textwidth} p{0.19\textwidth} p{0.19\textwidth} p{0.19\textwidth}@{}}
\toprule
Header 1 & Header 2 & Header 3 & Header 4 & Header 5 \\
\midrule
Data & Data & Data & Data & Data \\
\bottomrule
\end{tabular}
\caption{Table caption goes here}
\label{tab:example}
\end{table*}
```

**Key Features**:
- `table*` spans both columns
- `\footnotesize` for compact text
- `booktabs` rules (\toprule, \midrule, \bottomrule)
- No vertical lines (clean academic style)

---

## End Matter Structure

```latex
\clearpage          % Start bibliography on new page

{\scriptsize        % Smaller bibliography font
\bibliographystyle{spbasic_pt}
\bibliography{references}
}

\clearpage          % Page break after bibliography

% Appendix sections here (if any)

\end{document}
```

---

## ArXiv Submission Checklist

1. ✅ Compile with `xelatex` + `bibtex` + `xelatex` + `xelatex`
2. ✅ Copy `.bbl` content into `main.tex` (replace `\bibliography{}` commands)
3. ✅ Remove `\bibliography{references}` and `\bibliographystyle{}` commands
4. ✅ Verify all figures are included
5. ✅ Test compile with only `main.tex` (no external files)
6. ✅ Check PDF: all citations hyperlinked, bibliography renders correctly
7. ✅ Submit `main.tex` + figure files as ZIP to arXiv

---

## Style Comparison: Current vs. arXiv Template

### Current Output (latex_builder.py)
- ❌ BibLaTeX with `\printbibliography`
- ❌ External `references.bib` file
- ❌ No embedded bibliography
- ✅ Hyperref with colored links

### arXiv Template (target)
- ✅ natbib with traditional BibTeX
- ✅ Embedded `.bbl` in main.tex
- ✅ Single-file submission ready
- ✅ Hyperref with BrickRed citations
- ✅ spbasic_pt bibliography style

---

## Implementation Architecture

### Proposed: `LatexStyleApplicator` Class

```python
class LatexStyleApplicator:
    """Apply template-specific LaTeX styles (arXiv, Springer, Sage, etc.)"""

    def __init__(self, template: str = "arxiv"):
        self.template = template  # "arxiv", "springer", "sage", etc.

    def build_preamble(self) -> str:
        """Load template-specific preamble"""

    def format_citations(self, content: str) -> str:
        """Ensure citation commands match template style"""

    def format_cross_references(self, content: str) -> str:
        """Format Figure/Table/Section references per template"""

    def embed_bibliography(self, bbl_file: Path) -> str:
        """Embed .bbl content for single-file submission"""

    def apply_template(self, content: str, metadata: dict) -> str:
        """Apply full template to content"""
```

### Directory Structure
```
src/converters/md_to_latex/
├── latex_builder.py           # Current dynamic builder
├── latex_style_applicator.py  # New template system
└── templates/
    ├── arxiv/
    │   ├── preamble.tex
    │   ├── style_config.yaml
    │   └── README.md
    ├── springer/
    │   └── (future)
    └── sage/
        └── (future)
```

---

## Cross-Reference Formatting Rules

### AST-Based Detection (NO REGEX!)

Use `pylatexenc` to parse LaTeX and identify reference patterns:

```python
# Detect: "figure 3" or "fig 3" → "Figure~\ref{fig:3}"
# Detect: "section 2.1" → "Section~\ref{sec:2.1}"
# Detect: "table 5" → "Table~\ref{tab:5}"
```

**Capitalization Rules**:
- Always capitalize: Figure, Table, Section
- Use non-breaking space: `~` before `\ref{}`
- Examples:
  - "see figure 3" → "see Figure~\ref{fig:3}"
  - "in section 2" → "in Section~\ref{sec:2}"
  - "table 1 shows" → "Table~\ref{tab:1} shows"

---

## Key Differences from Current System

| Aspect | Current System | arXiv Template |
|--------|---------------|----------------|
| **Bib System** | BibLaTeX | natbib + BibTeX |
| **Bib Command** | `\printbibliography` | `\begin{thebibliography}` |
| **Bib File** | External `.bib` | Embedded `.bbl` |
| **Citation Color** | BrickRed (same) | BrickRed (same) |
| **Cross-Refs** | Plain `\ref{}` | Formatted `Figure~\ref{}` |
| **Submission** | Multi-file | Single main.tex |

---

## Next Steps

1. **Copy arXiv preamble** to `src/converters/md_to_latex/templates/arxiv/preamble.tex`
2. **Implement `LatexStyleApplicator` class** with pluggable templates
3. **Add BBL embedding** functionality (parse `.bbl`, insert into document)
4. **Add cross-reference formatter** using AST parsing (no regex!)
5. **Update converter.py** to use style applicator
6. **Test with MCP review paper** (365 citations)

---

## Example Citation Output

### In LaTeX:
```latex
\citep{alexandrov2023, eriksen2019}
```

### In PDF (visual):
```
(Alexandrov et al., 2023; Eriksen et al., 2019)
```
Where "Alexandrov et al., 2023" and "Eriksen et al., 2019" are **hyperlinked in BrickRed**, clicking jumps to bibliography.

### In Bibliography (embedded .bbl):
```latex
\bibitem[Alexandrov et al.(2023)]{alexandrov2023}
Alexandrov, A., Goodman, L. and Neal, M. (2023) Reengineering the Appraisal Process Better Leveraging Both Automated Valuation Models and Manual Appraisals Urban Institute.
\href{https://www.urban.org/...}{https://www.urban.org/...}
```

The URL is **hyperlinked in BrickRed** automatically by hyperref.

---

## Summary

The arXiv style creates professional, submission-ready papers with:
- ✅ **Hyperlinked citations** (author names clickable, red)
- ✅ **Embedded bibliography** (single-file submission)
- ✅ **Formatted cross-references** (Figure X, Table Y, Section Z)
- ✅ **Two-column layout** with tight margins
- ✅ **Professional typography** via microtype
- ✅ **Concept boxes** with tcolorbox

This style is suitable for arXiv preprints and many journal submissions that accept LaTeX.
