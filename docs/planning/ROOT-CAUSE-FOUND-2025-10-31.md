# ROOT CAUSE FOUND - Citation Matching Failure

## The Bug

**CitationMatcher is not being used**.

### What Exists
- `citation_matcher.py` - Production-grade multi-strategy matcher (DOI → ISBN → arXiv → URL)
- Fully implemented with proper identifier extraction
- Has comprehensive index building

### What's Actually Being Used
- `citation_manager.py:_lookup_zotero_entry_by_url()` (lines 381+)
- Simpler lookup that just checks DOI and URL string equality
- NO identifier normalization
- NO arXiv ID extraction
- NO ISBN matching

### Code Evidence
```python
# citation_manager.py line 601
zotero_result = self._lookup_zotero_entry_by_url(url)

# Instead of using:
# matcher = CitationMatcher(zotero_entries)
# result = matcher.match(url)
```

### Why converter.py isn't being used
Looking at converter.py lines 240-252, it DOES use CitationMatcher, but this code path might not be the one running. The citation_manager.py path is being used instead.

## The Fix

**Option 1**: Replace `_lookup_zotero_entry_by_url()` with `CitationMatcher`
- citation_manager.py should use CitationMatcher internally
- Remove duplicate matching logic
- Use existing, tested code

**Option 2**: Fix `_lookup_zotero_entry_by_url()` to match CitationMatcher quality
- Add identifier extraction
- Add normalization
- Add multi-strategy fallback

**Decision**: Option 1 - use existing CitationMatcher (don't reinvent)

## Implementation Plan

1. Import CitationMatcher in citation_manager.py
2. Initialize CitationMatcher in __init__ when zotero_entries loaded
3. Replace `_lookup_zotero_entry_by_url()` calls with CitationMatcher.match()
4. Remove duplicate code

This follows my commitment: **Use existing code, don't reinvent**.
