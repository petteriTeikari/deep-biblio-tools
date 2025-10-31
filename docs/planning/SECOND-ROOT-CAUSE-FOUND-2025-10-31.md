# SECOND ROOT CAUSE FOUND - RDF Parser Loading Only Half the Entries

## The Discovery

Running diagnostic script revealed:
```
✓ Loaded 313 entries from RDF
✓ Entries with 'id' field: 313/313
✓ Entries with 'URL' field: 313/313
✓ Entries with 'DOI' field: 145/313

📊 Index Statistics:
  DOI index: 145 entries
  ISBN index: 0 entries  ← BROKEN!
  arXiv index: 3 entries
  URL index: 313 entries

🧪 Testing matches:
  ✗ https://arxiv.org/abs/2509.25370 - NO MATCH
  ✗ https://arxiv.org/abs/2503.13657 - NO MATCH
  ✗ https://doi.org/10.1007/978-3-031-70262-4_5 - NO MATCH
```

## The Problem

**Expected**: 665 entries (user's Zotero dpp-fashion collection)
**Actual**: 313 entries loaded

**Result**: Missing 352 entries (53% of collection!)

## Why Citations Don't Match

1. Paper has ~380 citations
2. RDF only loaded 313 entries
3. Missing entries include the arXiv papers being tested
4. CitationMatcher tries all strategies (DOI, arXiv, ISBN, URL)
5. All fail because entries not in the 313 loaded
6. Falls back to auto-add via Zotero API
7. Creates "Auto-added" entries without 'id' field
8. Results in hundreds of failed matches

## Secondary Issues Found

### ISBN Extraction Broken
- Entry 2: `https://www.amazon.de/-/en/Craft-Use-Post-Growth-Kate-Fletcher/dp/1138021016`
- Has ISBN 1138021016 in URL
- But ISBN index is 0 entries
- `extract_isbn_from_url()` utility exists but not being used correctly

### arXiv Coverage Low
- Only 3 arXiv entries in 313 loaded
- But paper has many arXiv citations (2509.25370, 2503.13657, etc.)
- These citations must be in the missing 352 entries

## Next Steps

1. **Find why RDF parser loads only 313/665 entries**
   - Check `_load_rdf()` in bibliography_sources.py
   - Check itemType filtering (lines 282-300)
   - Check if some entry types are being skipped

2. **Fix ISBN extraction**
   - Entry 2 shows Amazon URL but no ISBN indexed
   - Check `extract_isbn_from_url()` is being called
   - Check normalization in CitationMatcher._build_indices()

3. **Verify fix loads all 665 entries**
   - Re-run diagnostic script
   - Confirm 665 entries loaded
   - Confirm ISBN index > 0
   - Confirm arXiv index includes test papers

## Evidence

### What Works
- RDF parser correctly sets 'id' field on all loaded entries ✓
- RDF parser correctly sets 'URL' field on all loaded entries ✓
- DOI extraction works (145 DOIs found) ✓
- URL index built correctly (313 entries) ✓

### What's Broken
- Only 313/665 entries loaded (47% coverage) ✗
- ISBN index completely empty (0 entries) ✗
- Low arXiv coverage (3 entries when paper has many) ✗
- Test citations don't match (not in the 313 loaded) ✗

## Impact

This explains ALL the matching failures:
- Not a CitationMatcher bug (it works correctly)
- Not a URL normalization bug (it works correctly)
- Not an identifier extraction bug (DOI works)
- **It's a data loading bug** - half the entries never loaded!

User was right: RDF should have ~665 entries with max 5 missing.
Reality: RDF parser only loading 313 entries.
