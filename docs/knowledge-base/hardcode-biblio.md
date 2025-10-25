# Hardcoding Bibliography in LaTeX Files with Python

## Overview

This guide explains how to bypass BibTeX/BST file complexities by directly generating formatted bibliography entries in LaTeX using Python. This approach gives you complete control over citation formatting and avoids common BibTeX parsing errors.

## Why Hardcode Bibliography?

1. **Avoid BibTeX limitations**: No more "too many commas" errors or character encoding issues
2. **Full control**: Format citations exactly as needed without learning BST language
3. **Dynamic generation**: Use Python to fetch metadata and format consistently
4. **Debugging**: Easier to debug Python code than BST stack-based language

## Basic Approach

Instead of using `\bibliography{references}` and `\bibliographystyle{style}`, we generate a `thebibliography` environment directly:

```latex
\begin{thebibliography}{99}
\bibitem{pagourtzi2003}
Pagourtzi, E., Assimakopoulos, V., Hatzichristos, T., and French, N. (2003).
Real estate appraisal: a review of valuation methods.
\textit{Journal of Property Investment \& Finance}, 21(4), 383--401.
doi: \href{https://doi.org/10.1108/14635780310483656}{10.1108/14635780310483656}

\bibitem{mooya2016}
Mooya, M. M. (2016).
\textit{Real Estate Valuation Theory}.
Springer Berlin Heidelberg.
doi: \href{https://doi.org/10.1007/978-3-662-49164-5}{10.1007/978-3-662-49164-5}
\end{thebibliography}
```

## Python Implementation

### 1. Data Structure for Citations

```python
from dataclasses import dataclass
from typing import Optional, List
import re

@dataclass
class Citation:
    key: str  # BibTeX key like "pagourtzi2003"
    authors: List[str]
    year: str
    title: str
    journal: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    url: Optional[str] = None
    publisher: Optional[str] = None
    book_title: Optional[str] = None
    note: Optional[str] = None
```

### 2. Author Formatting

```python
def format_authors(authors: List[str], style: str = "apa") -> str:
    """Format author list according to citation style."""
    if not authors:
        return ""

    if style == "apa":
        if len(authors) == 1:
            return authors[0]
        elif len(authors) == 2:
            return f"{authors[0]} and {authors[1]}"
        elif len(authors) <= 6:
            return ", ".join(authors[:-1]) + f", and {authors[-1]}"
        else:
            # More than 6 authors: show first 3, ellipsis, last author
            return ", ".join(authors[:3]) + ", ... " + authors[-1]

    # Add other styles as needed
    return ", ".join(authors)
```

### 3. Citation Formatting

```python
def format_citation_latex(citation: Citation, style: str = "authoryear") -> str:
    """Format a single citation for LaTeX bibliography."""
    parts = []

    # Start with \bibitem
    parts.append(f"\\bibitem{{{citation.key}}}")

    # Format authors
    author_str = format_authors(citation.authors, style="apa")
    parts.append(f"{author_str} ({citation.year}).")

    # Title
    if citation.journal:
        # Article: regular title
        parts.append(f"{citation.title}.")
    else:
        # Book/misc: italic title
        parts.append(f"\\textit{{{citation.title}}}.")

    # Journal/Book details
    if citation.journal:
        journal_str = f"\\textit{{{citation.journal}}}"
        if citation.volume:
            journal_str += f", {citation.volume}"
            if citation.issue:
                journal_str += f"({citation.issue})"
        if citation.pages:
            journal_str += f", {citation.pages}"
        parts.append(journal_str + ".")

    if citation.publisher and not citation.journal:
        parts.append(f"{citation.publisher}.")

    # DOI with hyperlink
    if citation.doi:
        doi_clean = citation.doi.replace("\\_", "_")
        parts.append(f"doi: \\href{{https://doi.org/{doi_clean}}}{{{doi_clean}}}")

    # ArXiv with hyperlink
    elif citation.arxiv_id:
        arxiv_clean = citation.arxiv_id.replace("\\_", "_")
        parts.append(f"arXiv: \\href{{https://arxiv.org/abs/{arxiv_clean}}}{{{arxiv_clean}}}")

    # URL as fallback
    elif citation.url and not citation.doi and not citation.arxiv_id:
        parts.append(f"\\url{{{citation.url}}}")

    # Combine all parts
    return "\n".join(parts)
```

### 4. Complete Bibliography Generation

```python
def generate_bibliography_latex(citations: List[Citation], style: str = "authoryear") -> str:
    """Generate complete bibliography environment."""
    # Sort citations by key for consistent ordering
    sorted_citations = sorted(citations, key=lambda c: c.key.lower())

    # Calculate widest label for spacing
    max_label_width = max(len(c.key) for c in sorted_citations) if sorted_citations else 10

    lines = ["\\begin{thebibliography}{" + "9" * len(str(len(sorted_citations))) + "}"]

    for citation in sorted_citations:
        formatted = format_citation_latex(citation, style)
        lines.append("")  # Empty line between entries
        lines.append(formatted)

    lines.append("")
    lines.append("\\end{thebibliography}")

    return "\n".join(lines)
```

### 5. Integration with LaTeX Document

```python
def inject_bibliography_into_latex(tex_file_path: str, bibliography: str):
    """Replace bibliography commands with hardcoded bibliography."""
    with open(tex_file_path, 'r') as f:
        content = f.read()

    # Remove existing bibliography commands
    content = re.sub(r'\\bibliographystyle\{[^}]+\}', '', content)
    content = re.sub(r'\\bibliography\{[^}]+\}', bibliography, content)

    # If no \bibliography command exists, insert before \end{document}
    if '\\bibliography' not in content:
        content = content.replace('\\end{document}',
                                  f'\n{bibliography}\n\\end{{document}}')

    with open(tex_file_path, 'w') as f:
        f.write(content)
```

## Example Usage

```python
# Load citations from your data source
citations = [
    Citation(
        key="eriksen2019",
        authors=["Michael D. Eriksen", "Hamilton B. Fout", "Mark Palim", "Eric Rosenblatt"],
        year="2019",
        title="Contract Price Confirmation Bias: Evidence from Repeat Appraisals",
        journal="The Journal of Real Estate Finance and Economics",
        volume="60",
        pages="77-98",
        doi="10.1007/s11146-019-09716-w"
    ),
    Citation(
        key="zhang2018",
        authors=["Brian Hu Zhang", "Blake Lemoine", "Margaret Mitchell"],
        year="2018",
        title="Mitigating Unwanted Biases with Adversarial Learning",
        arxiv_id="1801.07593"
    )
]

# Generate bibliography
bibliography = generate_bibliography_latex(citations)

# Inject into LaTeX file
inject_bibliography_into_latex("manuscript/v6_UAD.tex", bibliography)
```

## Advanced Features

### 1. Custom Formatting Rules

```python
def apply_custom_formatting(text: str, format_type: str) -> str:
    """Apply custom formatting rules."""
    if format_type == "title":
        # Preserve capitalization for certain words
        protected_words = ["AI", "ML", "COVID-19", "DNA", "RNA"]
        for word in protected_words:
            text = text.replace(word.lower(), word)

    return text
```

### 2. Handling Special Characters

```python
def escape_latex(text: str) -> str:
    """Escape special LaTeX characters."""
    replacements = {
        '&': '\\&',
        '%': '\\%',
        '$': '\\$',
        '#': '\\#',
        '_': '\\_',
        '{': '\\{',
        '}': '\\}',
        '~': '\\textasciitilde{}',
        '^': '\\textasciicircum{}',
    }

    for char, replacement in replacements.items():
        text = text.replace(char, replacement)

    return text
```

### 3. Multiple Citation Styles

```python
CITATION_STYLES = {
    "authoryear": {
        "author_format": "lastname_first",
        "year_position": "after_authors",
        "title_emphasis": "plain",
        "journal_emphasis": "italic"
    },
    "numeric": {
        "author_format": "full_names",
        "year_position": "end",
        "title_emphasis": "quotes",
        "journal_emphasis": "plain"
    }
}
```

## Benefits Over .bst Files

1. **Readable code**: Python is easier to understand and modify than BST
2. **Debugging**: Standard Python debugging tools work
3. **Flexibility**: Easy to add custom logic for specific citations
4. **Integration**: Can fetch metadata from APIs during generation
5. **Version control**: Changes are clear in git diffs

## Common Patterns

### DOI Formatting
```python
f"doi: \\href{{https://doi.org/{doi}}}{{{doi}}}"
```

### ArXiv Formatting
```python
f"arXiv: \\href{{https://arxiv.org/abs/{arxiv_id}}}{{{arxiv_id}}}"
```

### URL Shortening
```python
def shorten_url(url: str, max_length: int = 50) -> str:
    """Shorten long URLs for display."""
    if len(url) <= max_length:
        return url
    return url[:max_length-3] + "..."
```

## Troubleshooting

1. **Missing citations**: Check that citation keys in `\cite{}` match those in `\bibitem{}`
2. **Encoding issues**: Ensure files are UTF-8 encoded
3. **Special characters**: Use the `escape_latex()` function
4. **Compilation errors**: Check for unmatched braces in generated LaTeX

## Conclusion

Hardcoding bibliography entries with Python provides a robust alternative to wrestling with BibTeX and .bst files. While it requires more initial setup, the flexibility and maintainability benefits often outweigh the costs, especially for complex formatting requirements or when dealing with diverse citation sources.
