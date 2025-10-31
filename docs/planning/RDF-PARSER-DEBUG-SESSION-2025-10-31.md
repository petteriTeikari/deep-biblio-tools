# RDF Parser Debugging Session - 2025-10-31

## Summary

User reported 297 failed citations during MD→LaTeX conversion despite 665 entries being in Zotero RDF export.

## Investigation Findings

### RDF File Structure

**File**: `dpp-fashion-zotero.rdf`
- **Size**: 2.8 MB, 52,291 lines
- **Total XML elements**: 1,324

**Element breakdown**:
```
Attachment:    528  (skip - not bibliography items)
Description:   339  (rdf:Description format - mostly arXiv preprints)
Article:       281  (bib:Article format - DOI/journal articles)
Journal:       132  (skip - metadata, not bibliography items)
BookSection:    10  (bib:BookSection)
Book:           10  (bib:Book)
Document:        9  (bib:Document)
Report:          8  (bib:Report)
Thesis:          5  (bib:Thesis)
Recording:       1  (bib:Recording)
Patent:          1  (bib:Patent)
```

**Expected to parse**: **664-665 bibliography entries**
- Skip: 528 attachments + 132 metadata = 660
- Parse: 1324 - 660 = 664 entries (or 665 per Zotero's count)

**Important**: User's Zotero RDF export contains 665 entries. The RDF parser MUST return all 665. However, the final .bbl file will only include the subset of entries that are actually cited in the markdown file.

### z:itemType Distribution

**All entries with z:itemType** (total 1,192):
```
attachment:        528  (skip)
preprint:          277  (parse)
journalArticle:    276  (parse)
conferencePaper:    60  (parse)
book:               10  (parse)
bookSection:        10  (parse)
report:              8  (parse)
webpage:             7  (parse)
thesis:              5  (parse)
magazineArticle:     3  (parse)
newspaperArticle:    2  (parse)
document:            2  (parse)
blogPost:            2  (parse)
podcast:             1  (parse)
patent:              1  (parse)
```

## Current Parser Status

### What Works ✅

1. **RDF file loading**: Successfully loads 2.8MB RDF file
2. **Element iteration**: `for child in root:` finds all 1,324 elements
3. **Filter logic**: Correctly identifies:
   - 528 attachments to skip
   - 132 bib:Journal metadata to skip
   - Title existence and validity
   - z:itemType validation

4. **_parse_rdf_item() method**: Successfully parses BOTH formats:
   - `<rdf:Description>` entries (arXiv format)
   - `<bib:Article>` entries (DOI format)

5. **Citation key generation**:
   - arXiv: `arxiv_2311.14570`
   - DOI: `doi_10_1038_s41746_024_01085_w`
   - Amazon: `amazon_1138021016`

### What's Broken ❌

**Parser only finds 311 entries instead of 664!**

#### Symptom Analysis

- ✅ All 281 bib:Article entries have valid z:itemType (journalArticle, magazineArticle, or newspaperArticle)
- ✅ All pass filtering checks (has title, valid item type, has authors)
- ✅ Manual test of `_parse_rdf_item()` on bib:Article succeeds
- ❌ **But bib:Article entries DON'T appear in final parsed output!**

#### What's Actually Parsed

Looking at the 311 entries parsed:
- All are arXiv format (rdf:Description)
- Examples: `arxiv_2311.14570`, `arxiv_2402.00809v4`, etc.
- **ZERO bib:Article/bib:Book/bib:* entries parsed**

#### Missing Entries

- **Missing**: 664 - 311 = **353 bibliography entries**
- Breakdown of missing:
  - 281 bib:Article (DOI/journal articles)
  - 10 bib:Book
  - 10 bib:BookSection
  - 9 bib:Document
  - 8 bib:Report
  - 5 bib:Thesis
  - 1 bib:Recording
  - 1 bib:Patent
  - Plus ~28 rdf:Description entries that get filtered

### The Mystery 🔍

**Paradox**:
1. Iteration finds bib:Article elements ✅
2. Filtering logic passes them ✅
3. Parsing method works on them ✅
4. **But they don't appear in output ❌**

**Possible causes** (not yet verified):
1. Element deduplication removing bib:* entries incorrectly?
2. URL extraction failing for bib:* entries causing parse to return None?
3. Some subtle namespace or iteration order issue?
4. Caching or state issue in LocalFileSource?

## Code Changes Made

### bibliography_sources.py Changes

1. **Added two-strategy approach** (lines 283-337):
   - Strategy 1: Find specific bib:* typed items
   - Strategy 2: Find rdf:Description entries
   - Added deduplication by element ID

2. **Added valid item types whitelist** (lines 284-290):
   - Added: magazineArticle, newspaperArticle, blogPost, podcast

3. **Added metadata exclusion list** (lines 292-293):
   - Exclude: Journal, Series, Periodical

4. **Improved filtering logic** (lines 308-331):
   - Check for metadata exclusion
   - Check for non-empty title
   - Validate z:itemType against whitelist
   - Check for authors OR valid itemType OR bib:* typed

5. **Added debug logging** (lines 338-341):
   - Log skipped entries (but didn't produce output in tests)

### Test Scripts Created

1. **test_rdf_parsing.py**: Basic RDF parser test
2. **test_rdf_missing_entries.py**: Identifies which entries are missing
3. **test_iteration.py**: Verifies iteration finds all elements
4. **debug_filtering.py**: Tests filtering logic on sample entries
5. **test_parse_item.py**: Tests _parse_rdf_item() directly
6. **test_filtering_counters.py**: Tracks where entries are filtered out

## Recommendations for Next Session

### Immediate Actions

1. **Add hardcoded test assertion**:
   ```python
   assert len(entries) == 664, f"Expected 664 entries, got {len(entries)}"
   ```

2. **Add entry type breakdown assertion**:
   ```python
   by_type = count_by_citation_key_prefix(entries)
   assert by_type['arxiv'] == 277  # preprints
   assert by_type['doi'] >= 276     # journal articles
   assert by_type['amazon'] >= 10   # books
   ```

3. **Enable DEBUG logging** in actual conversion to see what's filtered

4. **Simplify _load_rdf** logic - current two-strategy approach may have bugs

### Root Cause Investigation

**Hypothesis**: The `for child in root:` iteration in _load_rdf() may be behaving differently than in standalone tests due to:
- XML parsing mode differences
- Namespace handling in ElementTree
- Iterator state issues

**Next steps**:
1. Add print statements directly in _load_rdf() to count bib:Article elements
2. Check if element ID deduplication is removing bib:* entries
3. Verify bib:* entries have non-None URLs
4. Check if _parse_rdf_item returns None for bib:* entries in actual execution

### Alternative Approach

If debugging continues to be difficult:
1. Use the .bib file as reference (user provided dpp-fashion-bibtex.bib)
2. Cross-reference .bib entries with .rdf entries to understand mapping
3. Consider parsing BOTH formats and merging results
4. Note: .bib drops some fields (URLs for Amazon books) so .rdf is primary source

## Test File Locations

All test scripts are in: `/home/petteri/Dropbox/github-personal/deep-biblio-tools/scripts/`

RDF file tested: `~/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/dpp-fashion-zotero.rdf`

## Status: INCOMPLETE

**Current**: Parser finds 311/664 entries (46.8% success rate)
**Target**: Parser must find 664-665 entries (100%)
**Blocker**: bib:* entries (325 items) are not being parsed despite passing all checks

**Next session**: Focus on root cause, not more testing. Add extensive logging to actual _load_rdf() execution path.
