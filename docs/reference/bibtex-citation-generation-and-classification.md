# BibTeX Citation Generation and Classification

**Date**: 2025-10-31
**Purpose**: Define what hyperlinks should generate BibTeX entries vs remain as inline links
**Status**: Background reference document

---

## Table of Contents

1. [Citation vs Hyperlink Classification](#citation-vs-hyperlink-classification)
2. [BibTeX Entry Types](#bibtex-entry-types)
3. [Citation Format in Markdown](#citation-format-in-markdown)
4. [What Gets a BibTeX Entry](#what-gets-a-bibtex-entry)
5. [What Remains an Inline Link](#what-remains-an-inline-link)
6. [Edge Cases](#edge-cases)
7. [Implementation Logic](#implementation-logic)

---

## Citation vs Hyperlink Classification

### The Fundamental Distinction

**Citations** are references to scholarly work that should appear in the bibliography:
- Academic papers (journal articles, conference papers)
- Technical reports
- Books
- Theses/dissertations
- Preprints (arXiv, bioRxiv)
- Standards documents (ISO, IEEE, RFC)

**Hyperlinks** are navigational elements that should NOT appear in bibliography:
- GitHub repositories
- Company websites
- Social media posts
- News articles
- Blog posts
- Government websites
- Tool/product documentation

### Pattern Recognition

#### Citation Pattern (HAS author AND year)
```markdown
[Author (Year)](URL)
[Author et al., Year](URL)
[First Author et al. (2024)](URL)
```

**Examples**:
```markdown
[Fletcher (2016)](https://www.amazon.de/.../dp/1138021016)  ← CITATION
[Wang et al., 2024](https://arxiv.org/abs/2410.10762)       ← CITATION
[Smith and Jones (2023)](https://doi.org/10.1234/example)   ← CITATION
```

#### Hyperlink Pattern (NO author/year)
```markdown
[Descriptive Text](URL)
[Organization Name](URL)
[Product/Tool Name](URL)
```

**Examples**:
```markdown
[Google Docs](https://docs.google.com)                      ← HYPERLINK
[GitHub](https://github.com/user/repo)                      ← HYPERLINK
[EON](https://www.eon.xyz/)                                 ← HYPERLINK
[Entrupy](https://www.entrupy.com/)                         ← HYPERLINK
```

---

## BibTeX Entry Types

### Academic Citations → BibTeX Entry

| Source Type | BibTeX Type | Example URL Pattern | Required Fields |
|-------------|-------------|---------------------|-----------------|
| Journal Article | `@article` | `doi.org/10.*`, `*.sciencedirect.com`, `*.springer.com` | author, title, journal, year, doi |
| Conference Paper | `@inproceedings` | `doi.org/10.*`, `ieeexplore.ieee.org` | author, title, booktitle, year, doi |
| arXiv Preprint | `@article` | `arxiv.org/abs/*`, `arxiv.org/pdf/*` | author, title, year, eprint (arXiv ID) |
| Book | `@book` | `amazon.*/dp/*`, `*.routledge.com` | author, title, publisher, year, isbn |
| Technical Report | `@techreport` | `*.gov/*`, `*.edu/*` (with author/year) | author, title, institution, year |

### Non-Academic Links → Inline Hyperlink

| Source Type | Example URL Pattern | Why NOT a citation |
|-------------|---------------------|-------------------|
| GitHub Repository | `github.com/*` | Code repository, not peer-reviewed publication |
| Company Website | `*.com/`, `*.xyz/` | Company info page, not scholarly work |
| Social Media | `x.com/*`, `twitter.com/*`, `linkedin.com/*` | Social media post, not peer-reviewed |
| News Article | `fashionunited.com/*`, `*.news/*` | Journalism, not academic publication |
| Blog Post | `*.medium.com/*`, `*.substack.com/*` | Opinion/commentary, not peer-reviewed |
| Product Documentation | `developers.google.com/*`, `docs.*.com` | Technical documentation, not academic |

---

## Citation Format in Markdown

### Valid Citation Formats

From CLAUDE.md:

> **Citations**: `[Author (Year)](URL)` or `[Author et al., Year](URL)`
> - Has author name AND year in brackets
> - Should be processed for bibliography

### Pattern Matching Rules

1. **MUST have parentheses with year**: `(YYYY)` or `, YYYY`
2. **MUST have author indicator**: Name or "et al."
3. **MAY have multiple authors**: `[Smith, Jones, and Lee (2024)]`
4. **MAY use comma separator**: `[Author et al., 2024]`

### Regular Expression (for reference only)

**NOTE**: Deep Biblio Tools NEVER uses regex for parsing. This is documentation only.

Conceptual pattern (not implemented):
```
\[([A-Z][a-z]+(?: et al\.?)?(?:,? \d{4}| \(\d{4}\)))\]\(https?://[^\)]+\)
```

### Implementation (AST-based)

Deep Biblio Tools uses markdown-it-py AST parser:

```python
# Extract link nodes
for node in ast.walk():
    if node.type == "link":
        text = node.children[0].content  # "[Author (Year)]"
        url = node.attrGet("href")       # "https://..."

        # Check if text contains year pattern
        if has_year_pattern(text):  # String methods only
            # This is a CITATION
            create_bibtex_entry(text, url)
        else:
            # This is a regular HYPERLINK
            keep_as_inline_link(url)
```

---

## What Gets a BibTeX Entry

### Criteria

A hyperlink gets converted to BibTeX entry if ALL of these are true:

1. ✅ **Has author/year pattern** in link text
2. ✅ **URL points to academic source** (DOI, arXiv, PubMed, academic publisher)
3. ✅ **Can be matched or fetched** from Zotero RDF or citation metadata APIs

### Examples

```markdown
[Fletcher (2016)](https://www.amazon.de/.../dp/1138021016)
```
- ✅ Has author "Fletcher"
- ✅ Has year "(2016)"
- ✅ Amazon book URL (academic book publisher)
- **Result**: Create `@book` entry in references.bib

```markdown
[Wang et al., 2024](https://arxiv.org/abs/2410.10762)
```
- ✅ Has author "Wang et al."
- ✅ Has year "2024"
- ✅ arXiv preprint URL
- **Result**: Create `@article` entry with arXiv eprint

```markdown
[Niinimäki et al. (2020)](https://doi.org/10.1016/j.jclepro.2019.119096)
```
- ✅ Has author "Niinimäki et al."
- ✅ Has year "(2020)"
- ✅ DOI URL (journal article)
- **Result**: Create `@article` entry with DOI

---

## What Remains an Inline Link

### Criteria

A hyperlink remains as `\href{URL}{text}` in LaTeX if ANY of these are true:

1. ❌ **No author/year pattern** in link text
2. ❌ **URL points to non-academic source** (GitHub, company site, social media)
3. ❌ **Explicitly a tool/product reference** (not scholarly work)

### Examples

```markdown
[Google Docs](https://docs.google.com)
```
- ❌ No author name
- ❌ No year
- ❌ Product documentation
- **Result**: `\href{https://docs.google.com}{Google Docs}`

```markdown
[GitHub repository](https://github.com/emcie-co/parlant)
```
- ❌ No author name
- ❌ No year
- ❌ Code repository (not peer-reviewed publication)
- **Result**: `\href{https://github.com/emcie-co/parlant}{GitHub repository}`

```markdown
[EON](https://www.eon.xyz/)
```
- ❌ No author name
- ❌ No year
- ❌ Company website
- **Result**: `\href{https://www.eon.xyz/}{EON}`

```markdown
[SIGKITTEN tweet](https://x.com/SIGKITTEN/status/1982926935278899599)
```
- ❌ No author/year pattern
- ❌ Social media post
- **Result**: `\href{https://x.com/SIGKITTEN/status/...}{SIGKITTEN tweet}`

---

## Edge Cases

### Case 1: News Articles About Research

```markdown
[Fashion United report on DPP pilot](https://fashionunited.com/news/h-m-zalando-dpp-pilot)
```

**Decision**: Inline hyperlink
- ❌ No author/year pattern
- ❌ Journalism, not peer-reviewed research
- **Rationale**: News articles ABOUT research are not themselves citations

**Better approach**: Cite the original research paper, add footnote with news link

### Case 2: Government Reports

```markdown
[European Commission (2024)](https://ec.europa.eu/environment/circular-economy)
```

**Decision**: BibTeX entry (`@techreport` or `@misc`)
- ✅ Has organizational author "European Commission"
- ✅ Has year "(2024)"
- ✅ Official policy document (citable gray literature)

**Note**: Government reports with author/year ARE citeable if they are official policy documents

### Case 3: arXiv vs Published Version

```markdown
[Smith et al. (2024)](https://arxiv.org/abs/2410.10762)
```

**If also published**:
```markdown
[Smith et al. (2024)](https://doi.org/10.1234/journal.2024.001)
```

**Decision**: Prefer DOI of published version
- ✅ DOI is more stable
- ✅ Published version is peer-reviewed
- **Note**: Can include arXiv as `note = {arXiv:2410.10762}` in BibTeX

### Case 4: Books on Amazon vs Publisher Site

```markdown
[Fletcher (2016)](https://www.amazon.de/.../dp/1138021016)
```

vs

```markdown
[Fletcher (2016)](https://www.routledge.com/Craft-of-Use/Fletcher/p/book/9781138021013)
```

**Decision**: Both are citations (same book)
- ✅ Extract ISBN from Amazon URL: `1138021016`
- ✅ Match by ISBN in Zotero
- **Result**: Same BibTeX entry regardless of URL

---

## Implementation Logic

### Extraction Phase (citation_extractor_unified.py)

```python
def extract_citations(markdown_content: str) -> list[Citation]:
    """Extract citations from markdown using AST parser."""
    ast = markdown_it_parser.parse(markdown_content)
    citations = []

    for link_node in ast.find_all(type="link"):
        text = link_node.text  # e.g., "Fletcher (2016)"
        url = link_node.url     # e.g., "https://..."

        # Classification logic
        if is_citation_pattern(text):
            # Has author/year pattern → potential citation
            citation_type = classify_url(url)

            if citation_type in ["academic", "book", "preprint"]:
                # Academic source → create citation
                citations.append(Citation(
                    text=text,
                    url=url,
                    type=citation_type
                ))
            else:
                # Non-academic source → inline link
                # Even with author/year pattern, GitHub/company sites
                # should remain inline links
                pass
        else:
            # No author/year pattern → definitely inline link
            pass

    return citations
```

### Classification Functions

```python
def is_citation_pattern(text: str) -> bool:
    """Check if text has author/year citation pattern."""
    # Use string methods ONLY (no regex)

    # Check for year in parentheses: "(YYYY)"
    if "(" in text and ")" in text:
        # Extract content between parens
        paren_content = text[text.find("(")+1:text.find(")")]
        if paren_content.isdigit() and len(paren_content) == 4:
            # Has (YYYY) pattern
            return True

    # Check for comma-separated year: ", YYYY"
    if ", 20" in text:  # Assumes 2000-2099 range
        parts = text.split(", ")
        if len(parts) >= 2:
            year_part = parts[-1].strip()
            if year_part.isdigit() and len(year_part) == 4:
                # Has ", YYYY" pattern
                return True

    return False

def classify_url(url: str) -> str:
    """Classify URL as academic, book, company, etc."""
    url_lower = url.lower()

    # Academic sources
    if any(domain in url_lower for domain in [
        "doi.org", "dx.doi.org",
        "arxiv.org",
        "pubmed", "ncbi.nlm.nih.gov",
        "sciencedirect.com", "springer.com", "ieee.org",
        "acm.org", "nature.com", "science.org"
    ]):
        return "academic"

    # Books
    if "amazon." in url_lower and "/dp/" in url_lower:
        return "book"
    if any(domain in url_lower for domain in [
        "routledge.com", "cambridge.org", "oup.com"
    ]):
        return "book"

    # Preprints
    if "arxiv.org" in url_lower:
        return "preprint"
    if "biorxiv.org" in url_lower:
        return "preprint"

    # Non-academic
    if "github.com" in url_lower:
        return "code_repository"
    if "x.com" in url_lower or "twitter.com" in url_lower:
        return "social_media"
    if any(domain in url_lower for domain in [
        ".xyz", "entrupy.com", "haelixa.com", "oritain.com", "eon.xyz"
    ]):
        return "company_website"

    # Default: check for organizational TLD
    if url_lower.endswith((".gov", ".edu", ".org")):
        return "gray_literature"  # May be citeable

    return "unknown"
```

### Matching Phase (citation_manager.py)

Once classified as citation, match against Zotero:

```python
def match_citation(self, citation: Citation) -> str | None:
    """Match citation against Zotero RDF entries."""
    # Multi-strategy matching (see identifier-matching-strategies.md)

    # Priority 1: DOI
    if doi := extract_doi_from_url(citation.url):
        if match := self._match_by_doi(doi):
            return match.key

    # Priority 2: arXiv ID
    if "arxiv" in citation.url.lower():
        if arxiv_id := extract_arxiv_id(citation.url):
            if match := self._match_by_arxiv(arxiv_id):
                return match.key

    # Priority 3: ISBN (for books)
    if "amazon" in citation.url.lower() or citation.type == "book":
        if isbn := extract_isbn_from_url(citation.url):
            if match := self._match_by_isbn(isbn):
                return match.key

    # Priority 4: Normalized URL
    if match := self._match_by_url(citation.url):
        return match.key

    # Not in Zotero
    return None
```

---

## Success Criteria

### For Citation Extraction

1. ✅ All `[Author (Year)](URL)` patterns extracted
2. ✅ All `[Author et al., YYYY](URL)` patterns extracted
3. ❌ No `[GitHub](https://github.com/...)` extracted as citations
4. ❌ No `[Company Name](https://company.com)` extracted as citations

### For BibTeX Generation

1. ✅ Academic papers → `@article` with DOI
2. ✅ Books → `@book` with ISBN
3. ✅ arXiv preprints → `@article` with eprint
4. ❌ GitHub repos NOT in references.bib
5. ❌ Company sites NOT in references.bib
6. ❌ Social media NOT in references.bib

### For LaTeX Output

```latex
% Citations (in bibliography)
Academic work \citep{fletcher2016craft}
According to \cite{wang2024deep}

% Inline links (NOT in bibliography)
See the \href{https://github.com/user/repo}{GitHub repository}
Company site: \href{https://eon.xyz/}{EON}
```

---

## References

1. [CLAUDE.md](.claude/CLAUDE.md) - Citation format rules
2. [citation-commands-guide.md](./citation-commands-guide.md) - \cite vs \citep usage
3. [deterministic-citation-system.md](../architecture/deterministic-citation-system.md) - Architecture
4. [identifier-matching-strategies.md](./identifier-matching-strategies.md) - Robust matching

---

**Status**: Reference document for citation extraction and classification logic
**Next**: See [identifier-matching-strategies.md](./identifier-matching-strategies.md) for matching rules
