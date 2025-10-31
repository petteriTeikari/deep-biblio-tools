# Amazon Book URL Issue - 2025-10-31

## Executive Summary

**Problem**: RDF parser only finds 1 Amazon book instead of 2+ because Amazon URLs are buried in `dc:identifier` XML structure, not in the `rdf:about` attribute that the parser currently reads.

**Impact**: Books with Amazon URLs get wrong citation keys (title-based instead of `amazon_*`)

**Root Cause**: Parser only checks `rdf:about` attribute, ignores `dc:identifier/dcterms:URI/rdf:value` nested URLs

**Solution**: Update `_parse_rdf_item()` to check both locations for URLs

---

## The Issue

### Current Behavior

**Book #1: "Patterns for API Design"**
```xml
<bib:Book rdf:about="urn:isbn:978-0-13-767010-9">
    <dc:title>Patterns for API Design...</dc:title>
    <dc:identifier>
        <dcterms:URI>
            <rdf:value>https://www.amazon.com/.../dp/0137670109</rdf:value>
        </dcterms:URI>
    </dc:identifier>
</bib:Book>
```

**Parser behavior**:
- Reads `rdf:about="urn:isbn:978-0-13-767010-9"`
- Passes to `_extract_citation_key_from_url("urn:isbn:978-0-13-767010-9", title)`
- "urn:isbn" doesn't match "amazon" or "/dp/"
- Falls back to title-based key: `patterns_for_api`
- **WRONG**: Should be `amazon_0137670109`

**Book #2: "Craft of Use"**
```xml
<bib:Book rdf:about="https://www.amazon.de/.../dp/1138021016">
    <dc:title>Craft of Use: Post-Growth Fashion</dc:title>
    <dc:identifier>
        <dcterms:URI>
            <rdf:value>https://www.amazon.de/.../dp/1138021016</rdf:value>
        </dcterms:URI>
    </dc:identifier>
</bib:Book>
```

**Parser behavior**:
- Reads `rdf:about="https://www.amazon.de/.../dp/1138021016"`
- Passes to `_extract_citation_key_from_url("https://www.amazon.de/.../dp/1138021016", title)`
- Matches "amazon" and "/dp/"
- Generates key: `amazon_1138021016`
- **CORRECT**

---

## Why This Happens

### Zotero RDF Export Behavior

When Zotero exports to RDF, it uses two different strategies for the `rdf:about` attribute:

1. **If item has a web URL**: Use the URL
   - Example: `rdf:about="https://www.amazon.de/.../dp/1138021016"`

2. **If item has no web URL** (or ISBN is preferred): Use URN
   - Example: `rdf:about="urn:isbn:978-0-13-767010-9"`

3. **If item is not yet published**: Use internal Zotero ID
   - Example: `rdf:about="#item_20299"`

The actual URLs are ALWAYS in `dc:identifier/dcterms:URI/rdf:value`, but the parser ignores those!

---

## Affected Books

Out of 20 books total in RDF:

### Books with Amazon URLs (should get amazon_* keys)

1. **"Patterns for API Design"**
   - Current key: `patterns_for_api` ❌
   - Should be: `amazon_0137670109` ✓
   - URL location: `dc:identifier` only

2. **"Craft of Use"**
   - Current key: `amazon_1138021016` ✓
   - Already correct
   - URL location: Both `rdf:about` and `dc:identifier`

### Books with DOI URLs (might also be affected)

3. **"Sustainable Enterprise Resource Planning"**
   - Current key: `sustainable_enterprise_resource` (title-based)
   - Has DOI in `dc:identifier`: `https://doi.org/10.1007/978-981-96-7734-4`
   - Should probably be: `doi_10_1007_978_981_96_7734_4`

### Books with urn:isbn only (no web URL)

- **8 books** have `rdf:about="urn:isbn:..."` with no web URL in `dc:identifier`
- These correctly get title-based keys

### Books with no URLs at all

- **6 books** have empty `rdf:about` and no `dc:identifier`
- These correctly get title-based keys

### Books with other URLs

- **3 books** have non-Amazon, non-DOI URLs (capitalinstitute.org, etc.)
- These correctly get URL-based or title-based keys

---

## The Solution

### Required Change

Update `_parse_rdf_item()` to check multiple URL sources in priority order:

```python
def _parse_rdf_item(self, item: Any, namespaces: dict[str, str]) -> dict[str, Any] | None:
    """Parse a single RDF bibliography item to CSL JSON."""

    # Extract rdf:about as potential URL/identifier
    item_url = item.get(f"{{{namespaces['rdf']}}}about", "")

    # ALSO check dc:identifier/dcterms:URI/rdf:value for better URLs
    identifier_url = None
    for identifier in item.findall("dc:identifier", namespaces):
        uri_elem = identifier.find("dcterms:URI", namespaces)
        if uri_elem is not None:
            value_elem = uri_elem.find("rdf:value", namespaces)
            if value_elem is not None and value_elem.text:
                identifier_url = value_elem.text.strip()
                break  # Use first dc:identifier URL found

    # Prefer identifier URL if it's a proper web URL
    # (rdf:about might be urn:isbn or #item_xxx)
    if identifier_url and identifier_url.startswith(("http://", "https://")):
        item_url = identifier_url
    # Otherwise use rdf:about (might be URL, URN, or internal ID)

    # ... rest of parsing logic ...
```

### Priority Logic

1. **If `dc:identifier` has http/https URL**: Use it (highest priority)
2. **Else if `rdf:about` is http/https URL**: Use it
3. **Else use `rdf:about`**: Even if it's urn:isbn or #item_xxx
   - The citation key generator will handle these appropriately

### Why This Works

- **Amazon URLs** in `dc:identifier` will be used → `amazon_*` keys ✓
- **DOI URLs** in `dc:identifier` will be used → `doi_*` keys ✓
- **arXiv URLs** in `rdf:about` will still be used → `arxiv_*` keys ✓
- **URN ISBNs** without web URLs will fall back to title-based keys ✓

---

## Expected Impact

### Before Fix

```
Amazon books found: 1
- amazon_1138021016 (Craft of Use)

Missing Amazon books: 1
- patterns_for_api (should be amazon_0137670109)
```

### After Fix

```
Amazon books found: 2
- amazon_1138021016 (Craft of Use)
- amazon_0137670109 (Patterns for API Design)

DOI books also improved:
- sustainable_enterprise_resource → doi_10_1007_978_981_96_7734_4
```

### Test Results Expected

```
BEFORE:
- ❌ test_rdf_parser_includes_book_entries: 1 vs 10 Amazon books

AFTER:
- Test expectation needs adjustment (there are only 2 Amazon books, not 10)
- OR test should count all books (20 total) instead of just Amazon books
```

---

## Test Expectation Issue

The test expects "at least 10 Amazon book entries" based on this assumption:

```python
EXPECTED_AMAZON_ENTRIES = 10  # books with Amazon URLs
```

**Reality**: Only 2 books have Amazon URLs in the RDF

**Possible explanations**:
1. Test was written based on old RDF export with different data
2. Test author assumed all books would have Amazon URLs
3. Test should check total book count (20) instead of Amazon-specific count

**Recommendation**: Update test to check:
```python
EXPECTED_BOOK_ENTRIES = 20  # All books (bib:Book elements)
EXPECTED_AMAZON_ENTRIES = 2  # Books with Amazon URLs
```

---

## Related Issues

### Issue #1: DOI Books

Same problem affects books with DOI URLs in `dc:identifier`:
- "Sustainable Enterprise Resource Planning" should get `doi_*` key

### Issue #2: Citation Matching

If citations in markdown use Amazon URLs but citation keys are title-based, matching will fail:
- Markdown: `[Fletcher (2016)](https://www.amazon.com/.../dp/0137670109)`
- RDF key: `patterns_for_api`
- Matcher: Can't match by URL, must match by author+year

---

## Implementation Notes

### File to Modify

`src/converters/md_to_latex/bibliography_sources.py`

**Method**: `_parse_rdf_item()` (lines 388-500)

**Change**: Add dc:identifier URL extraction before using rdf:about

### Testing

1. **Unit test**: Verify dc:identifier URL extraction
2. **Integration test**: Check `amazon_*` key generation for both books
3. **Regression test**: Ensure existing keys don't change

### Validation

```bash
# After fix, run:
uv run pytest tests/test_rdf_parser_emergency_mode.py::test_rdf_parser_includes_book_entries -v

# Should see:
# Amazon books: 2 (was 1, +1 improvement)
```

---

## User Request

> "And these definitely should be fixed, and the Amazon book issue is really annoying and I want a solution for that"

**Response**: Acknowledged. The fix is straightforward - add dc:identifier URL checking. This will recover the missing Amazon book and likely improve DOI book keys as well.

**ETA**: ~30 minutes to implement, test, and verify
