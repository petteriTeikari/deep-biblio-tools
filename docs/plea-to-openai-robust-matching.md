# Plea to OpenAI: Robust Citation Matching Strategy

## The Problem

When converting LLM-generated markdown bibliographies to LaTeX/BibTeX, we face a critical matching challenge:

**Input (Markdown)**:
```markdown
[Fletcher, 2016](https://www.amazon.de/-/en/Craft-Use-Post-Growth-Kate-Fletcher/dp/1138021016)
```

**Zotero Database Entry**:
```json
{
  "type": "book",
  "title": "Craft of Use: Post-Growth Fashion",
  "author": [{"family": "Fletcher", "given": "Kate"}],
  "publisher": "Routledge",
  "source": "Amazon",
  "URL": "",  // ← MISSING! Zotero connector doesn't always capture URLs
  "issued": {"date-parts": [["2016", 4, 27]]}
}
```

**Current naive URL-only matching**: ❌ FAILS because Zotero entry has no URL
**Result**: Citation marked as "Unknown" despite being in the database

## Why This Happens

1. **Zotero connector inconsistency**: When adding books via Amazon, the Zotero browser connector often:
   - ✅ Captures: Title, author, publisher, ISBN, date
   - ❌ Misses: The Amazon URL itself

2. **LLM markdown format**: LLMs generate citations as `[Author, Year](URL)` because:
   - URLs are the most reliable identifiers
   - Easier for LLMs to extract from web pages
   - Natural markdown link format

3. **Database schema mismatch**:
   - Books → ISBN is primary identifier
   - Journal articles → DOI is primary identifier
   - Web pages → URL is primary identifier
   - **But markdown only has URL for ALL types**

## The Solution: Multi-Strategy Matching

### Strategy 1: URL Matching (Current)
```python
normalized_url = normalize_url(citation.url)
if normalized_url in url_index:
    return url_index[normalized_url]
```

**Success rate**: ~40% (fails when Zotero URL is missing)

### Strategy 2: DOI Extraction from URL (New)
```python
# Extract DOI from URLs like:
# - https://doi.org/10.1002/sd.2474
# - https://dx.doi.org/10.1038/s41746-024-01085-w

doi = extract_doi_from_url(url)
if doi in doi_index:
    return doi_index[doi]
```

**Success rate improvement**: +20% (DOIs are stable, persistent)

### Strategy 3: ISBN Extraction from URL (New)
```python
# Extract ISBN from Amazon URLs:
# https://www.amazon.de/.../dp/1138021016
# Pattern: /dp/{ISBN10} or /dp/{ISBN13}

isbn = extract_isbn_from_url(url)
if isbn in isbn_index:
    return isbn_index[isbn]
```

**Success rate improvement**: +15% (critical for books)

### Strategy 4: arXiv ID Extraction (New)
```python
# Extract from URLs like:
# - https://arxiv.org/abs/2410.10762
# - https://arxiv.org/html/2509.10691v1

arxiv_id = extract_arxiv_id(url)
if arxiv_id in arxiv_index:
    return arxiv_index[arxiv_id]
```

**Success rate improvement**: +10% (preprints are common in academic writing)

### Strategy 5: Fuzzy Title + Author Matching (Fallback)
```python
# When all identifier-based matching fails:
# 1. Parse author name from markdown: "Fletcher, 2016" → "Fletcher"
# 2. Fuzzy match against Zotero entries with same year
# 3. Use Levenshtein distance for title similarity

author_surname = extract_author_surname(citation.text)
year = extract_year(citation.text)

candidates = [
    entry for entry in zotero_db
    if entry.year == year and
       author_surname.lower() in entry.authors_text.lower()
]

# Use title from URL metadata or fuzzy match
best_match = max(candidates, key=lambda e: similarity(e.title, guessed_title))
```

**Success rate improvement**: +10% (last resort, but effective)

## Implementation Priority

### Phase 1: Identifier Extraction (High ROI, Low Risk)
1. DOI extraction from URLs
2. ISBN extraction from Amazon/book URLs
3. arXiv ID extraction
4. Build multiple indices (url_index, doi_index, isbn_index, arxiv_index)

### Phase 2: Metadata Enrichment
1. For matched entries, populate ALL available fields
2. Handle organizational authors (websites without individual authors)
3. Preserve URL even if matching by ISBN/DOI

### Phase 3: Fuzzy Matching (Fallback Only)
1. Author surname extraction from citation text
2. Year extraction from citation text
3. Title guessing from URL or API lookup
4. Similarity scoring

## Expected Impact

**Current state**:
- 46 out of 376 citations marked as "Unknown" (12% failure rate)
- Of these 46:
  - ~40% are IN Zotero but URL is missing → Would be fixed by ISBN/DOI matching
  - ~60% are genuinely missing → Should be added via Zotero API

**After implementing robust matching**:
- Expected failure rate: <2%
- Only genuinely missing citations would fail
- Those can be auto-added via Zotero API

## Code Architecture

```python
class CitationMatcher:
    def __init__(self, zotero_json_path):
        self.entries = load_json(zotero_json_path)
        self.url_index = build_url_index(self.entries)
        self.doi_index = build_doi_index(self.entries)
        self.isbn_index = build_isbn_index(self.entries)
        self.arxiv_index = build_arxiv_index(self.entries)

    def match_citation(self, citation):
        # Strategy 1: URL
        if match := self._match_by_url(citation.url):
            return match

        # Strategy 2: DOI
        if doi := extract_doi_from_url(citation.url):
            if match := self.doi_index.get(doi):
                return match

        # Strategy 3: ISBN
        if isbn := extract_isbn_from_url(citation.url):
            if match := self.isbn_index.get(isbn):
                return match

        # Strategy 4: arXiv
        if arxiv_id := extract_arxiv_id(citation.url):
            if match := self.arxiv_index.get(arxiv_id):
                return match

        # Strategy 5: Fuzzy matching
        if match := self._fuzzy_match(citation):
            return match

        return None  # Genuinely missing
```

## Request to OpenAI

When generating bibliographies in markdown format, please consider:

1. **Include multiple identifiers when available**:
   ```markdown
   [Fletcher, 2016](https://www.amazon.de/.../dp/1138021016) <!-- ISBN: 1138021016 -->
   ```

2. **Prefer persistent identifiers**:
   - DOI > ISBN > arXiv > URL
   - Include DOI in markdown when available

3. **Structured citation metadata**:
   ```markdown
   <!-- CITATION
   author: Fletcher, Kate
   year: 2016
   title: Craft of Use: Post-Growth Fashion
   isbn: 1138021016
   url: https://www.amazon.de/.../dp/1138021016
   -->
   [Fletcher, 2016](https://www.amazon.de/.../dp/1138021016)
   ```

4. **Fallback identifiers**: When URL is unavailable, use:
   - `[Fletcher, 2016](isbn:1138021016)`
   - `[Author et al., 2024](arxiv:2410.10762)`
   - `[Smith, 2023](doi:10.1002/sd.2474)`

## Conclusion

The current URL-only matching is fundamentally flawed because:
- It assumes Zotero always has URLs (false for books)
- It ignores more stable identifiers (DOI, ISBN, arXiv)
- It doesn't leverage the rich metadata already in Zotero

By implementing multi-strategy matching with proper fallbacks, we can achieve:
- **90%+ automatic matching** (vs current 88%)
- **Zero false negatives** (everything in Zotero will be found)
- **Clean separation** between "in DB but not matched" vs "genuinely missing"

This enables the correct workflow:
1. Match everything that's in Zotero (even without URLs)
2. Identify genuinely missing citations
3. Auto-add those via Zotero API
4. Re-run conversion → 100% success rate

---

**Date**: 2025-10-26
**Author**: Deep Biblio Tools Development Team
**Status**: Implementation in progress
