# Root Cause Analysis: Non-Academic Links in Missing Citations List
## Date: 2025-10-31 23:54 UTC

## Problem Statement
69 non-academic links (GitHub, company websites, news sites) were appearing in the missing citations list despite having filters implemented.

## Investigation Trail

### Discovery 1: Filter Code Exists But Doesn't Execute
- Added comprehensive NON_ACADEMIC_DOMAINS exclusions (80+ domains)
- Added filter logic in `citation_extractor_unified.py:484-499`
- NO log messages appeared during conversion → Filter code not executing?

### Discovery 2: Logging Was Suppressed
- Added print() statements to bypass logging config
- CONFIRMED: Filter code IS executing
- Statistics:
  - 578 total links extracted
  - 16 filtered (no year in text)
  - 123 filtered (non-academic domains) ✅
  - 439 kept (academic citations)

### Discovery 3: TWO Different Code Paths
The breakthrough came from analyzing trace output:

**Path 1: Citation Extraction** (converter.py:945)
```python
citations = self.citation_manager.extract_citations(content)
└── citation_manager.py:574 → extractor.extract_citations_from_markdown()
    └── citation_extractor_unified.py:427 → Filters working! ✅
```
- Filters non-academic links correctly
- Populates `self.citations` dictionary with ONLY academic citations

**Path 2: Citation Replacement** (converter.py:1260)
```python
content = self.citation_manager.replace_citations_in_text(content)
└── citation_manager.py:1757 → replace_citations_in_text_ast()
    └── Parses markdown AST AGAIN
    └── Processes ALL links (including non-academic)
    └── Lookups fail for filtered links (not in self.citations)
    └── Logs "No citation key found" ❌
```

## Root Cause

The architecture has two stages:

1. **Extraction Stage**: Filters correctly, builds `self.citations` with only academic citations
2. **Replacement Stage**: Parses markdown independently, tries to look up ALL links

When replacement stage encounters a filtered non-academic link:
- URL not in `self.citations` (was filtered)
- Lookup fails: `key = url_to_key.get(normalized_href)` returns None
- Link added to `failed_urls` list
- "No citation key found" logged
- Later added to missing citations report

**The filter works perfectly, but the replacement stage doesn't know which links were filtered vs genuinely missing!**

## Solution

Add filter check in `replace_citations_in_text_ast()` BEFORE attempting lookup:

```python
# Line ~1638 in citation_manager.py
if href:
    # FILTER: Skip non-academic links (they're regular hyperlinks, not citations)
    extractor = UnifiedCitationExtractor()
    if not extractor._is_academic_url(href):
        print(f"[TRACE-H6] Skipping non-academic link in replacement: {href}", flush=True)
        i += 1
        continue

    # Existing lookup code...
    normalized_href = normalize_url(normalize_arxiv_url(href))
    key = url_to_key.get(normalized_href)
```

This prevents non-academic links from:
1. Being looked up in `url_to_key` (pointless - they were filtered)
2. Being logged as "No citation key found" (misleading - they're not citations)
3. Being added to missing citations list (wrong - they're inline links, not missing citations)

## Implementation Status

- ✅ Filter code implemented and working (123 links filtered)
- ✅ Root cause identified (dual extraction paths)
- ⏳ Fix needed in `replace_citations_in_text_ast()`
- ⏳ Remove trace print() statements after verification
- ⏳ Test to confirm 69 non-academic links no longer in missing list

## Expected Outcome

After fix:
- Missing citations: ~66 (98 total - 32 non-academic that will be filtered)
- All missing citations will be genuine academic papers
- Non-academic links remain as regular hyperlinks (correct behavior)

## Timeline

- 2025-10-31 22:00 → Initial investigation started
- 2025-10-31 22:45 → Filters added but not working
- 2025-10-31 23:20 → Discovered logging suppression
- 2025-10-31 23:35 → Added print() traces, confirmed filters work
- 2025-10-31 23:50 → Identified dual extraction paths (ROOT CAUSE)
- 2025-10-31 23:54 → Solution designed, ready to implement
