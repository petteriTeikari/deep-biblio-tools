# Identifier Matching Strategies for Robust Citation Resolution

**Date**: 2025-10-31
**Purpose**: Document multi-strategy citation matching using DOI, arXiv, ISBN, PubMed identifiers
**Status**: Background reference document
**Implementation**: `src/converters/md_to_latex/citation_matcher.py` and `utils.py`

---

## Table of Contents

1. [Overview](#overview)
2. [Matching Priority Order](#matching-priority-order)
3. [DOI Matching](#doi-matching)
4. [arXiv Matching](#arxiv-matching)
5. [ISBN Matching](#isbn-matching)
6. [PubMed Matching](#pubmed-matching)
7. [URL Normalization Matching](#url-normalization-matching)
8. [Implementation Guide](#implementation-guide)
9. [Test Cases](#test-cases)

---

## Overview

### The Problem

When matching citations from markdown `[Author (Year)](URL)` to Zotero entries, naive URL-only matching fails ~12% of the time because:

1. **Zotero entries often lack URLs** (especially books added via ISBN)
2. **URLs vary in format** (http vs https, www vs non-www, trailing slashes)
3. **Same content has multiple URLs** (arXiv html vs abs vs pdf, DOI.org vs dx.doi.org)

### The Solution: Multi-Strategy Matching

**CLAUDE.md Rule**: Match by DOI/URL/arXiv ID, NEVER by citation keys

**Priority Order** (from most to least reliable):
1. DOI matching → 10.1234/journal.2024.001
2. arXiv ID matching → 2410.10762 (version-stripped)
3. ISBN matching → 1138021016
4. PubMed ID matching → PMID:12345678
5. Normalized URL matching → Last resort

### Key Principle

> **Citation keys are IDENTITY, not MATCH CRITERIA**
>
> - Match by persistent identifiers (DOI, arXiv, ISBN)
> - USE whatever citation key Zotero provides
> - NEVER generate keys locally
> - NEVER validate key format

From: `docs/zotero-matching-vision.md`

---

## Matching Priority Order

### Why This Order?

| Strategy | Reliability | Stability | Coverage | Notes |
|----------|-------------|-----------|----------|-------|
| **1. DOI** | ★★★★★ | Permanent | ~60% | Official digital identifier, never changes |
| **2. arXiv** | ★★★★☆ | Stable | ~15% | Preprints, version-agnostic matching |
| **3. ISBN** | ★★★★☆ | Permanent | ~10% | Books, unique per edition |
| **4. PubMed** | ★★★★☆ | Permanent | ~5% | Biomedical literature |
| **5. URL** | ★★☆☆☆ | Unstable | ~100% | Last resort, URL drift over time |

### Expected Match Rates

From `docs/plea-to-openai-robust-matching.md`:

- **Current (URL-only)**: 88% match rate
- **After multi-strategy**: 98%+ expected match rate
- **Improvement breakdown**:
  - +20% from DOI extraction
  - +15% from ISBN extraction (Amazon books)
  - +10% from arXiv ID extraction
  - +5% from improved URL normalization

---

## DOI Matching

### What is a DOI?

**Digital Object Identifier**: Permanent identifier for academic publications

**Format**: `10.{publisher}/{identifier}`
- Example: `10.1016/j.jclepro.2019.119096`

### Extraction from URLs

**Supported URL patterns**:
```
https://doi.org/10.1016/j.jclepro.2019.119096
https://dx.doi.org/10.1038/s41746-024-01085-w
https://www.nature.com/articles/s41746-024-01085-w  # DOI embedded in path
https://sciencedirect.com/science/article/pii/S0959652619327489  # DOI in redirect
```

### Normalization Rules

**Implementation**: `src/converters/md_to_latex/utils.py:714`

```python
def extract_doi_from_url(url: str) -> str | None:
    """Extract DOI from URL if present."""
    url_lower = url.lower()

    # Pattern 1: doi.org/{DOI}
    if "doi.org/" in url_lower:
        start = url_lower.find("doi.org/") + 8
        doi = url[start:].strip()

        # Clean up: remove query params, fragments, trailing punctuation
        if " " in doi:
            doi = doi[: doi.find(" ")]
        if "?" in doi:
            doi = doi[: doi.find("?")]
        if "#" in doi:
            doi = doi[: doi.find("#")]

        # Remove trailing punctuation
        while doi and doi[-1] in ")]}>,;:":
            doi = doi[:-1]

        return doi

    # Pattern 2: doi:{DOI}
    if "doi:" in url_lower:
        start = url_lower.find("doi:") + 4
        doi = url[start:].strip()
        # (same cleanup as above)

    # Pattern 3: /doi/{DOI} in path
    if "/doi/" in url_lower:
        start = url_lower.find("/doi/") + 5
        doi = url[start:].strip()
        # (same cleanup as above)

    return None
```

### Matching Logic

**Implementation**: `src/converters/md_to_latex/citation_matcher.py:168`

```python
# Strategy 1: DOI matching (most reliable)
doi = extract_doi_from_url(citation_url)
if doi:
    normalized_doi = doi.lower().strip()
    if normalized_doi in self.doi_index:
        self.stats["matched_by_doi"] += 1
        return self.doi_index[normalized_doi], "doi"
```

### Test Cases

```python
assert extract_doi_from_url("https://doi.org/10.1016/j.jclepro.2019.119096") == "10.1016/j.jclepro.2019.119096"
assert extract_doi_from_url("https://dx.doi.org/10.1038/s41746-024-01085-w") == "10.1038/s41746-024-01085-w"
assert extract_doi_from_url("https://doi.org/10.1234/test?utm_source=twitter") == "10.1234/test"  # Query stripped
assert extract_doi_from_url("https://doi.org/10.1234/test);") == "10.1234/test"  # Punctuation stripped
```

---

## arXiv Matching

### What is arXiv?

**arXiv.org**: Preprint repository for physics, mathematics, computer science, etc.

**Format**: `YYMM.NNNNN` or `YYMM.NNNN`
- Example: `2410.10762` (October 2024, submission #10762)
- Old format: `hep-th/9901001` (category/year-month-number)

### Critical: Version Stripping

**arXiv URLs include version numbers that MUST be stripped for matching**:

```
https://arxiv.org/abs/2410.10762v1  → Match: 2410.10762
https://arxiv.org/abs/2410.10762v2  → Match: 2410.10762
https://arxiv.org/html/2410.10762v1 → Match: 2410.10762
```

**Why?** Zotero may store v1, markdown may link v2, but they're the same paper.

### URL Variants

**All point to the same paper**:
```
https://arxiv.org/abs/2410.10762    # Abstract page
https://arxiv.org/html/2410.10762   # HTML full text
https://arxiv.org/pdf/2410.10762    # PDF download
https://arxiv.org/abs/2410.10762v1  # Specific version
```

**Normalization**: Always match to version-stripped ID: `2410.10762`

### Extraction Implementation

**Implementation**: `src/converters/md_to_latex/utils.py:797`

```python
def extract_arxiv_id(url: str) -> str | None:
    """Extract arXiv ID from URL if present."""
    url_lower = url.lower()

    if "arxiv.org" not in url_lower:
        return None

    # Pattern: arxiv.org/abs/2410.10762 or arxiv.org/html/2509.10691v1
    for pattern in ["/abs/", "/html/", "/pdf/"]:
        if pattern in url_lower:
            start = url_lower.find(pattern) + len(pattern)
            rest = url[start:]

            # arXiv ID is next segment
            end = rest.find("/")
            if end == -1:
                end = rest.find("?")
            if end == -1:
                end = rest.find("#")
            if end == -1:
                end = len(rest)

            arxiv_id = rest[:end].strip()

            # **CRITICAL: Remove version suffix if present (e.g., "v1")**
            if "v" in arxiv_id:
                v_pos = arxiv_id.rfind("v")
                # Check if everything after 'v' is digits
                version_part = arxiv_id[v_pos + 1 :]
                if version_part.isdigit():
                    arxiv_id = arxiv_id[:v_pos]  # Strip version

            # Validate format: YYMM.NNNNN or YYMM.NNNN
            if "." in arxiv_id:
                left, right = arxiv_id.split(".", 1)
                if (
                    len(left) == 4
                    and left.isdigit()
                    and len(right) in [4, 5]
                    and right.isdigit()
                ):
                    return arxiv_id  # e.g., "2410.10762"

    return None
```

### URL Normalization

**Implementation**: `src/converters/md_to_latex/utils.py:468`

```python
def normalize_arxiv_url(url: str) -> str:
    """Normalize arXiv URL by removing version specifiers.

    Converts:
    - https://arxiv.org/abs/2508.12683v1 -> https://arxiv.org/abs/2508.12683
    - https://arxiv.org/html/2410.20199v1 -> https://arxiv.org/abs/2410.20199
    """
    if not url or "arxiv.org" not in url:
        return url

    # Normalize to use /abs/ instead of /html/ or /pdf/
    url = url.replace("arxiv.org/html/", "arxiv.org/abs/")
    url = url.replace("arxiv.org/pdf/", "arxiv.org/abs/")

    # Remove version specifier (vN at the end)
    if "arxiv.org/abs/" in url:
        abs_pos = url.find("arxiv.org/abs/")
        after_abs = url[abs_pos + 14 :]

        # Find where the ID ends (look for v followed by digits)
        for i in range(len(after_abs)):
            if after_abs[i] == "v" and i > 0:
                # Check if followed by digits
                remaining = after_abs[i + 1 :]
                if (
                    remaining
                    and remaining.split("/")[0].split("?")[0].isdigit()
                ):
                    # Found version specifier, remove it
                    url = url[: abs_pos + 14 + i]
                    break

    return url
```

### Matching Logic

**Implementation**: `src/converters/md_to_latex/citation_matcher.py:198`

```python
# Strategy 3: arXiv matching (for preprints)
arxiv_id = extract_arxiv_id(citation_url)
if arxiv_id:
    normalized_arxiv = arxiv_id.lower()
    if normalized_arxiv in self.arxiv_index:
        self.stats["matched_by_arxiv"] += 1
        logger.info(f"Matched by arXiv: {arxiv_id}")
        return self.arxiv_index[normalized_arxiv], "arxiv"
```

### Test Cases

```python
# Version stripping
assert extract_arxiv_id("https://arxiv.org/abs/2410.10762v1") == "2410.10762"
assert extract_arxiv_id("https://arxiv.org/abs/2410.10762v2") == "2410.10762"
assert extract_arxiv_id("https://arxiv.org/abs/2410.10762") == "2410.10762"

# URL variant handling
assert extract_arxiv_id("https://arxiv.org/html/2410.10762v1") == "2410.10762"
assert extract_arxiv_id("https://arxiv.org/pdf/2410.10762") == "2410.10762"

# Normalization
assert normalize_arxiv_url("https://arxiv.org/abs/2508.12683v1") == "https://arxiv.org/abs/2508.12683"
assert normalize_arxiv_url("https://arxiv.org/html/2410.20199v1") == "https://arxiv.org/abs/2410.20199"
```

---

## ISBN Matching

### What is ISBN?

**International Standard Book Number**: Unique identifier for books

**Formats**:
- ISBN-10: `1138021016` (10 digits)
- ISBN-13: `9781138021013` (13 digits)

### Extraction from Amazon URLs

**Amazon URL patterns**:
```
https://www.amazon.de/-/en/Craft-Use-Post-Growth-Kate-Fletcher/dp/1138021016
https://www.amazon.com/gp/product/1138021016
https://www.amazon.co.uk/dp/1138021016/ref=xyz
```

**Pattern**: `/dp/{ISBN}` or `/gp/product/{ISBN}`

### Extraction Implementation

**Implementation**: `src/converters/md_to_latex/utils.py:761`

```python
def extract_isbn_from_url(url: str) -> str | None:
    """Extract ISBN from Amazon or book vendor URL."""
    url_lower = url.lower()

    # Amazon URLs: /dp/{ISBN} or /gp/product/{ISBN}
    if "amazon" in url_lower:
        # Look for /dp/ pattern
        if "/dp/" in url_lower:
            start = url_lower.find("/dp/") + 4
            isbn = url[start:]

            # ISBN is next segment (before / or ? or #)
            for sep in ["/", "?", "#"]:
                if sep in isbn:
                    isbn = isbn[: isbn.find(sep)]

            # Remove hyphens, keep only digits
            isbn_digits = "".join(c for c in isbn if c.isdigit())

            # Validate: ISBN-10 (10 digits) or ISBN-13 (13 digits)
            if len(isbn_digits) in [10, 13]:
                return isbn_digits

        # Look for /gp/product/ pattern
        if "/gp/product/" in url_lower:
            # (similar logic)

    return None
```

### Matching Logic

**Implementation**: `src/converters/md_to_latex/citation_matcher.py:187`

```python
# Strategy 2: ISBN matching (for books)
isbn = extract_isbn_from_url(citation_url)
if isbn:
    if isbn in self.isbn_index:
        self.stats["matched_by_isbn"] += 1
        logger.info(f"Matched by ISBN: {isbn}")
        return self.isbn_index[isbn], "isbn"
```

### Index Building

**Implementation**: `src/converters/md_to_latex/citation_matcher.py:94`

```python
# ISBN index
isbn = entry.get("ISBN", "")
if isbn:
    # Normalize: remove hyphens, keep only digits
    normalized_isbn = "".join(c for c in isbn if c.isdigit())
    if normalized_isbn:
        self.isbn_index[normalized_isbn] = entry
```

### Test Cases

```python
# Amazon DE
assert extract_isbn_from_url("https://www.amazon.de/.../dp/1138021016") == "1138021016"

# Amazon US
assert extract_isbn_from_url("https://www.amazon.com/gp/product/9781138021013") == "9781138021013"

# With query params
assert extract_isbn_from_url("https://www.amazon.co.uk/dp/1138021016/ref=sr_1_1") == "1138021016"

# Hyphenated ISBN in Zotero
zotero_isbn = "978-1-138-02101-3"
normalized = "".join(c for c in zotero_isbn if c.isdigit())
assert normalized == "9781138021013"  # Matches Amazon ISBN-13
```

---

## PubMed Matching

### What is PubMed ID?

**PubMed**: Biomedical literature database (NCBI)

**Format**: `PMID:{digits}`
- Example: `PMID:12345678`

### Extraction from URLs

**Supported URL patterns**:
```
https://pubmed.ncbi.nlm.nih.gov/12345678/
https://www.ncbi.nlm.nih.gov/pubmed/12345678
https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7654321/
```

### Implementation Notes

**Current status**: Not yet implemented in `citation_matcher.py`

**Proposed implementation**:

```python
def extract_pubmed_id(url: str) -> str | None:
    """Extract PubMed ID from URL if present."""
    url_lower = url.lower()

    # Pattern: pubmed.ncbi.nlm.nih.gov/{PMID}
    if "pubmed.ncbi.nlm.nih.gov/" in url_lower:
        start = url_lower.find("pubmed.ncbi.nlm.nih.gov/") + 24
        pmid = url[start:]

        # PMID is next segment
        for sep in ["/", "?", "#"]:
            if sep in pmid:
                pmid = pmid[: pmid.find(sep)]

        if pmid.isdigit():
            return pmid

    # Pattern: /pubmed/{PMID}
    if "/pubmed/" in url_lower:
        start = url_lower.find("/pubmed/") + 8
        pmid = url[start:]

        for sep in ["/", "?", "#"]:
            if sep in pmid:
                pmid = pmid[: pmid.find(sep)]

        if pmid.isdigit():
            return pmid

    return None
```

### Matching Priority

**Add to multi-strategy matching**:

```python
# Strategy 4: PubMed matching (for biomedical literature)
pmid = extract_pubmed_id(citation_url)
if pmid:
    if pmid in self.pubmed_index:
        self.stats["matched_by_pubmed"] += 1
        return self.pubmed_index[pmid], "pubmed"
```

---

## URL Normalization Matching

### The Last Resort

URL matching is LEAST reliable because:
- URLs change over time (link drift)
- Same content has multiple URLs
- Protocol variations (http vs https)
- Subdomain variations (www vs non-www)
- Trailing slash inconsistencies

### Normalization Rules

**Implementation**: `src/converters/md_to_latex/utils.py:16`

```python
def normalize_url(url: str) -> str:
    """Normalize URL for consistent matching."""
    if not url:
        return ""

    url = url.lower().strip()

    # Remove protocol
    url = url.replace("https://", "").replace("http://", "")

    # Remove www
    url = url.replace("www.", "")

    # Remove trailing slashes
    url = url.rstrip("/")

    # Remove query parameters and fragments
    if "?" in url:
        url = url[: url.find("?")]
    if "#" in url:
        url = url[: url.find("#")]

    return url
```

### Special Cases

**Amazon URLs**: Extract ISBN instead (see ISBN Matching)

**arXiv URLs**: Extract arXiv ID instead (see arXiv Matching)

**DOI URLs**: Extract DOI instead (see DOI Matching)

### Matching Logic

**Implementation**: `src/converters/md_to_latex/citation_matcher.py:216`

```python
# Strategy 4: URL matching (normalized)
normalized_url = normalize_url(citation_url)
if normalized_url and normalized_url in self.url_index:
    self.stats["matched_by_url"] += 1
    return self.url_index[normalized_url], "url"
```

---

## Implementation Guide

### Class: CitationMatcher

**Location**: `src/converters/md_to_latex/citation_matcher.py`

**Initialization**:

```python
matcher = CitationMatcher(
    zotero_entries=rdf_entries,  # List of CSL JSON dicts
    allow_zotero_write=False     # Emergency mode: NO writes
)
```

**Indices Built**:

```python
self.doi_index = {}      # doi -> entry
self.isbn_index = {}     # isbn -> entry
self.arxiv_index = {}    # arxiv_id -> entry
self.url_index = {}      # normalized_url -> entry
```

**Matching**:

```python
entry, strategy = matcher.match(citation_url)

if entry:
    # Found in Zotero
    citation_key = entry.get("id")  # Use Zotero's key
    authors = entry.get("author", [])
    # ...
else:
    # Not in Zotero
    # Create failedAutoAdd entry or report as missing
```

### Statistics Tracking

```python
stats = matcher.get_statistics()

print(f"Total citations: {stats['total_citations']}")
print(f"Matched by DOI: {stats['matched_by_doi']}")
print(f"Matched by ISBN: {stats['matched_by_isbn']}")
print(f"Matched by arXiv: {stats['matched_by_arxiv']}")
print(f"Matched by URL: {stats['matched_by_url']}")
print(f"Unmatched: {stats['unmatched']}")
print(f"Match rate: {stats['match_rate']:.1f}%")
```

### Integration with CitationManager

**Current usage** (needs verification):

```python
# citation_manager.py
def _match_citation(self, url: str) -> dict | None:
    """Match citation against Zotero entries."""

    # Use CitationMatcher if available
    if hasattr(self, 'citation_matcher'):
        entry, strategy = self.citation_matcher.match(url)
        if entry:
            logger.debug(f"Matched by {strategy}: {url}")
            return entry

    # Fallback to old logic
    # ...
```

---

## Test Cases

### DOI Matching

```python
# Test DOI extraction
test_cases = [
    ("https://doi.org/10.1016/j.jclepro.2019.119096", "10.1016/j.jclepro.2019.119096"),
    ("https://dx.doi.org/10.1038/s41746-024-01085-w", "10.1038/s41746-024-01085-w"),
    ("https://doi.org/10.1234/test?utm_source=x", "10.1234/test"),
]

for url, expected_doi in test_cases:
    assert extract_doi_from_url(url) == expected_doi
```

### arXiv Matching

```python
# Test arXiv ID extraction with version stripping
test_cases = [
    ("https://arxiv.org/abs/2410.10762v1", "2410.10762"),
    ("https://arxiv.org/abs/2410.10762v2", "2410.10762"),
    ("https://arxiv.org/abs/2410.10762", "2410.10762"),
    ("https://arxiv.org/html/2509.10691v1", "2509.10691"),
    ("https://arxiv.org/pdf/2508.12683.pdf", "2508.12683"),
]

for url, expected_id in test_cases:
    assert extract_arxiv_id(url) == expected_id

# Test URL normalization
test_cases = [
    ("https://arxiv.org/abs/2508.12683v1", "https://arxiv.org/abs/2508.12683"),
    ("https://arxiv.org/html/2410.20199v1", "https://arxiv.org/abs/2410.20199"),
]

for url, expected_norm in test_cases:
    assert normalize_arxiv_url(url) == expected_norm
```

### ISBN Matching

```python
# Test ISBN extraction from Amazon
test_cases = [
    ("https://www.amazon.de/.../dp/1138021016", "1138021016"),
    ("https://www.amazon.com/gp/product/9781138021013", "9781138021013"),
    ("https://www.amazon.co.uk/dp/1138021016/ref=sr_1_1", "1138021016"),
]

for url, expected_isbn in test_cases:
    assert extract_isbn_from_url(url) == expected_isbn
```

### Integration Test

```python
# Test full matching pipeline
zotero_entries = [
    {
        "id": "fletcher2016craft",
        "title": "Craft of Use: Post-Growth Fashion",
        "author": [{"family": "Fletcher", "given": "Kate"}],
        "ISBN": "978-1-138-02101-3",
        "URL": "",  # No URL in Zotero
    },
]

matcher = CitationMatcher(zotero_entries)

# Should match by ISBN despite missing URL
url = "https://www.amazon.de/.../dp/1138021016"
entry, strategy = matcher.match(url)

assert entry is not None
assert strategy == "isbn"
assert entry["id"] == "fletcher2016craft"
```

---

## References

1. **[plea-to-openai-robust-matching.md](../plea-to-openai-robust-matching.md)**
   - Original proposal for multi-strategy matching
   - Expected success rate improvements
   - Motivation and examples

2. **[zotero-matching-vision.md](../zotero-matching-vision.md)**
   - "Keys are IDENTITY, not MATCH CRITERIA" principle
   - What NOT to do (key validation, local generation)
   - Correct workflow

3. **[COMPREHENSIVE-MATCHING-ANALYSIS-2025-10-31.md](../planning/COMPREHENSIVE-MATCHING-ANALYSIS-2025-10-31.md)**
   - Synthesis of historical matching issues
   - Root causes of matching failures
   - Solutions and hypotheses

4. **[CLAUDE.md](.claude/CLAUDE.md)**
   - Emergency mode rules
   - Zotero Web API as single source of truth
   - Bibliography workflow requirements

---

## Status

**Implementation Status**:
- ✅ DOI extraction and matching: IMPLEMENTED
- ✅ arXiv extraction (with version stripping): IMPLEMENTED
- ✅ arXiv URL normalization: IMPLEMENTED
- ✅ ISBN extraction and matching: IMPLEMENTED
- ✅ URL normalization and matching: IMPLEMENTED
- ❌ PubMed ID extraction and matching: NOT IMPLEMENTED
- ❌ Fuzzy title+author matching: NOT IMPLEMENTED

**Next Steps**:
1. Verify CitationMatcher is being used in citation_manager.py
2. Add PubMed ID extraction and matching
3. Implement fuzzy fallback matching
4. Add comprehensive integration tests

**Files to Review**:
- `src/converters/md_to_latex/citation_matcher.py` - Multi-strategy matcher
- `src/converters/md_to_latex/utils.py` - Extraction functions
- `src/converters/md_to_latex/citation_manager.py` - Integration point
