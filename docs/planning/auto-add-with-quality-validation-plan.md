# Auto-Add Citations to Zotero with Quality Validation - Implementation Plan

**Date**: 2025-10-29
**Branch**: `fix/verify-md-to-latex-conversion`
**Status**: Design Phase
**Purpose**: For OpenAI assistance

---

## Context: The Problem

We successfully fixed citation matching (391 → 0 (?) marks in PDF!), but **121 citations still create Temp keys** instead of being added to Zotero.

**Current behavior** (WRONG):
- Extract citation: `[BBC](https://www.bbc.com/news/business-44885983)`
- Not in Zotero → create Temp key: `bBCTemp2018` ❌
- Result: Works but uses temporary keys instead of proper Better BibTeX keys

**Expected behavior** (CORRECT):
- Extract citation: `[BBC](https://www.bbc.com/news/business-44885983)`
- Not in Zotero → Auto-add to Zotero using translation server
- Zotero creates entry with Better BibTeX key: `bbcBurberryBurnsBags2018` ✅
- Conversion uses proper Zotero key

---

## Previous Failures

### Incident: October 26, 2025 - Garbage Zotero Additions

**What went wrong**: Script added 28 entries to Zotero, but 9 were garbage:
```python
# WRONG approach - created useless entries
{
    "itemType": "webpage",
    "title": "Added from URL: https://cris.vtt.fi/en/publications/implemen",  # Truncated!
    "url": url,
    # No authors, no proper metadata
}
```

**What SHOULD happen** (when user adds manually):
```bibtex
@article{bbcBurberryBurnsBags2018,
    title = {Burberry burns bags, clothes and perfume worth millions},
    author = {BBC},  # Extracted from site when no author available
    url = {https://www.bbc.com/news/business-44885983},
    journal = {BBC},
    year = {2018},
    language = {en-GB},
}
```

**Key insight**: Zotero's translation server does this automatically! We just need to use it correctly.

Reference: `docs/post-mortem-garbage-zotero-additions.md`

---

## Requirements

### 1. Auto-Add Missing Citations ✅ MUST HAVE
- When citation not found in Zotero collection
- Use Zotero Web API translation server to fetch metadata
- Add to specified collection (`dpp-fashion`)
- Get Better BibTeX key from added entry

### 2. Quality Validation ✅ MUST HAVE
**NEVER add garbage to Zotero again**

For EACH entry BEFORE adding, validate:
- [ ] Title is complete (not truncated)
- [ ] Author exists (even if it's just site name like "BBC")
- [ ] Year is valid (4-digit number, 1900-2030)
- [ ] URL is valid and accessible
- [ ] If DOI exists, it resolves (HTTP 200)

**Validation test harness** should check:
```python
def validate_zotero_entry(entry: dict) -> tuple[bool, list[str]]:
    """
    Validate Zotero entry quality before adding.

    Returns:
        (is_valid, list_of_issues)

    Example issues:
        - "Title truncated (ends with ...)"
        - "No author field"
        - "Year outside valid range: 2099"
        - "DOI returns 404"
    """
```

### 3. Author Handling ✅ MUST HAVE
When no author in metadata:
1. Try to extract from site name (BBC, Bloomberg, European Commission)
2. Try to extract from domain (www.bbc.com → BBC)
3. If still no author, **log WARNING** and use "Unknown" (but still add entry)

**NEVER** fail silently - always report to user.

### 4. Better BibTeX Key Format ✅ MUST HAVE
Get actual Better BibTeX key from Zotero after adding:
- Expected: `bbcBurberryBurnsBags2018` (camelCase)
- NOT: `bBCTemp2018` (our current Temp format)

### 5. Error Reporting ✅ MUST HAVE
Generate clear report at end:
```
Citation Auto-Add Report
========================

✅ Successfully added: 115/121 (95%)

⚠️  Added with warnings: 4
    - bbc.com/news/... (no author, used site name "BBC")
    - europa.eu/... (no author, used "European Commission")

❌ Failed to add: 2
    - https://broken-link.com (404 error)
    - https://no-metadata.com (translation server failed)

Instructions for manual addition:
1. Open Zotero
2. File → Add Item by Identifier
3. Paste URLs above
```

### 6. Retry Logic ✅ NICE TO HAVE
- If translation server fails, retry once after 1 second
- Cache translation results to avoid duplicate API calls
- Network errors: report but don't fail entire conversion

---

## Technical Design

### Architecture

```
┌─────────────────────────────────────────────────┐
│ Markdown Citation Extraction                     │
│  [BBC](https://www.bbc.com/news/...)            │
└────────────────┬────────────────────────────────┘
                 │
                 v
┌─────────────────────────────────────────────────┐
│ Check Zotero Collection (via Web API)           │
│  GET /collections/{id}/items?q=url              │
└────────────────┬────────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
    Found           Not Found
        │                 │
        v                 v
┌──────────────┐  ┌──────────────────────────────┐
│ Use Zotero   │  │ Auto-Add Pipeline            │
│ Better       │  │                              │
│ BibTeX Key   │  │ 1. Fetch metadata            │
└──────────────┘  │    (Zotero translation API)  │
                  │                              │
                  │ 2. Validate quality          │
                  │    (test harness)            │
                  │                              │
                  │ 3. Add author if missing     │
                  │    (site name extraction)    │
                  │                              │
                  │ 4. POST to Zotero            │
                  │    (add to collection)       │
                  │                              │
                  │ 5. Get Better BibTeX key     │
                  │    (from added entry)        │
                  │                              │
                  │ 6. Log result                │
                  │    (success/warning/error)   │
                  └──────────────────────────────┘
```

### Implementation Steps

#### Step 1: Zotero Translation Server Integration

**Location**: `src/converters/md_to_latex/zotero_auto_add.py` (NEW FILE)

```python
class ZoteroAutoAdd:
    """Handle auto-adding citations to Zotero with quality validation."""

    def __init__(self, api_key: str, library_id: str, collection_name: str):
        self.api_key = api_key
        self.library_id = library_id
        self.collection_name = collection_name
        self.validation_results = []  # Track all validations

    def add_citation(self, url: str, citation_text: str) -> tuple[str | None, list[str]]:
        """
        Add citation to Zotero using translation server.

        Returns:
            (better_bibtex_key, list_of_warnings)
        """
        # 1. Fetch metadata from Zotero translation server
        metadata = self._fetch_metadata_via_translation(url)

        # 2. Validate quality
        is_valid, issues = self._validate_entry(metadata)

        # 3. Handle missing author
        if not metadata.get('creators'):
            metadata = self._add_author_from_site(url, metadata)

        # 4. If critical issues, report and skip
        if not is_valid:
            logger.error(f"Failed validation for {url}: {issues}")
            return None, issues

        # 5. Add to Zotero
        zotero_key = self._add_to_collection(metadata)

        # 6. Get Better BibTeX key
        better_bibtex_key = self._get_better_bibtex_key(zotero_key)

        # 7. Log and return
        self.validation_results.append({
            'url': url,
            'status': 'success',
            'key': better_bibtex_key,
            'warnings': issues if not is_valid else []
        })

        return better_bibtex_key, issues

    def _fetch_metadata_via_translation(self, url: str) -> dict | None:
        """Use Zotero translation server to fetch metadata."""
        # Zotero Web API endpoint for translation
        # POST /users/{id}/items with URL
        # Zotero automatically detects source type and fetches metadata
        pass

    def _validate_entry(self, metadata: dict) -> tuple[bool, list[str]]:
        """Validate entry quality before adding."""
        issues = []

        # Check title
        title = metadata.get('title', '')
        if len(title) > 80 and title.endswith('...'):
            issues.append("Title appears truncated")
        if not title:
            issues.append("CRITICAL: No title")
            return False, issues

        # Check author
        creators = metadata.get('creators', [])
        if not creators:
            issues.append("WARNING: No author (will extract from site)")

        # Check year
        year = metadata.get('date', '')
        if not year or not self._is_valid_year(year):
            issues.append(f"WARNING: Invalid year: {year}")

        # Check DOI if present
        doi = metadata.get('DOI')
        if doi and not self._validate_doi(doi):
            issues.append(f"CRITICAL: DOI returns 404: {doi}")
            return False, issues

        # Valid if no critical issues
        return len([i for i in issues if 'CRITICAL' in i]) == 0, issues

    def _add_author_from_site(self, url: str, metadata: dict) -> dict:
        """Extract author from site name when missing."""
        # Parse domain: www.bbc.com → BBC
        # Known mappings: bloomberg.com → Bloomberg, etc.
        pass

    def _validate_doi(self, doi: str) -> bool:
        """Validate DOI returns HTTP 200."""
        # HEAD request to https://doi.org/{doi}
        # Cache results
        pass

    def generate_report(self) -> str:
        """Generate human-readable report of auto-add results."""
        # Group by status: success, warning, error
        # Format with emojis and actionable instructions
        pass
```

#### Step 2: Integration into Citation Manager

**Location**: `src/converters/md_to_latex/citation_manager.py:543-571`

```python
# CURRENT CODE (simplified):
else:
    # Not found in Zotero - create Temp key
    key = self._generate_temp_key(citation)

# NEW CODE:
else:
    # Not found in Zotero - try auto-add
    if self.zotero_auto_add:
        better_bibtex_key, warnings = self.zotero_auto_add.add_citation(url, citation_text)
        if better_bibtex_key:
            key = better_bibtex_key
            logger.info(f"✓ Auto-added to Zotero: {key}")
        else:
            # Auto-add failed - fall back to Temp key
            key = self._generate_temp_key(citation)
            logger.warning(f"Auto-add failed, using Temp key: {key}")
    else:
        # Auto-add not enabled - use Temp key
        key = self._generate_temp_key(citation)
```

#### Step 3: Quality Validation Test Harness

**Location**: `tests/unit/test_zotero_auto_add_validation.py` (NEW FILE)

```python
def test_validate_entry_complete():
    """Test validation passes for complete entry."""
    entry = {
        'title': 'Burberry burns bags, clothes and perfume worth millions',
        'creators': [{'lastName': 'BBC'}],
        'date': '2018',
        'url': 'https://www.bbc.com/news/business-44885983'
    }
    is_valid, issues = validate_entry(entry)
    assert is_valid
    assert len(issues) == 0

def test_validate_entry_truncated_title():
    """Test validation fails for truncated title."""
    entry = {
        'title': 'Added from URL: https://cris.vtt.fi/en/publications/implemen...',
        'url': 'https://cris.vtt.fi/...'
    }
    is_valid, issues = validate_entry(entry)
    assert not is_valid
    assert 'truncated' in ' '.join(issues).lower()

def test_validate_entry_missing_author():
    """Test validation warns for missing author."""
    entry = {
        'title': 'Some Article',
        'creators': [],  # No author
        'date': '2023'
    }
    is_valid, issues = validate_entry(entry)
    # Valid (will extract from site) but has warning
    assert is_valid
    assert any('author' in i.lower() for i in issues)

def test_validate_entry_invalid_doi():
    """Test validation fails for 404 DOI."""
    entry = {
        'title': 'Paper',
        'DOI': '10.1234/invalid-doi-404',
        'date': '2023'
    }
    # Mock DOI validation to return False
    is_valid, issues = validate_entry(entry)
    assert not is_valid
    assert '404' in ' '.join(issues)
```

#### Step 4: Site Name → Author Mapping

**Location**: `src/converters/md_to_latex/site_author_mapping.py` (NEW FILE)

```python
SITE_AUTHOR_MAPPINGS = {
    'bbc.com': 'BBC',
    'bbc.co.uk': 'BBC',
    'bloomberg.com': 'Bloomberg',
    'europa.eu': 'European Commission',
    'europarl.europa.eu': 'European Parliament',
    'hmfoundation.com': 'H&M Foundation',
    'gs1.eu': 'GS1',
    'wbcsd.org': 'WBCSD',
    # Add more as needed
}

def extract_author_from_url(url: str) -> str | None:
    """Extract author name from URL domain."""
    # Parse domain from URL
    # Check against known mappings
    # Return author name or None
    pass
```

---

## Success Criteria

### Functional Requirements

- [ ] 121 Temp citations → ≤5 Temp citations (>95% auto-add success rate)
- [ ] All added entries have complete titles (no truncation)
- [ ] All added entries have authors (extracted from site if needed)
- [ ] Zero garbage entries added to Zotero
- [ ] Better BibTeX keys used (not Temp keys)

### Quality Requirements

- [ ] Each entry validated before adding (test harness passes)
- [ ] Clear error report generated
- [ ] Manual addition URLs provided for failures
- [ ] Warnings logged for incomplete metadata
- [ ] No silent failures

### Performance Requirements

- [ ] Auto-add overhead: ≤60 seconds for 121 citations (first run)
- [ ] Translation results cached (subsequent runs instant)
- [ ] Network errors handled gracefully (no pipeline crash)

---

## Testing Strategy

### Unit Tests
```bash
# Test validation logic
uv run pytest tests/unit/test_zotero_auto_add_validation.py -v

# Test author extraction
uv run pytest tests/unit/test_site_author_mapping.py -v

# Test Zotero API integration (mocked)
uv run pytest tests/unit/test_zotero_auto_add.py -v
```

### Integration Test
```bash
# Run conversion with auto-add enabled
uv run python -m src.cli_md_to_latex \
    mcp-draft-refined-v4.md \
    --output-dir /tmp/auto_add_test \
    --enable-auto-add \
    -v

# Check results
cat /tmp/auto_add_test/auto_add_report.txt
```

### Manual Validation
1. Check Zotero library for new entries (should be ~115 new entries)
2. Verify entry quality (complete titles, authors, years)
3. Check Better BibTeX keys (camelCase, not Temp)
4. Verify PDF has 0 (?) marks
5. Verify bibliography is complete

---

## Risks and Mitigations

### Risk 1: Zotero Translation Server Failures
**Mitigation**:
- Retry logic (1 retry after 1 second)
- Graceful fallback to Temp keys
- Clear error reporting

### Risk 2: Rate Limiting
**Mitigation**:
- Add 200ms delay between translation requests
- Cache translation results
- Batch requests if possible

### Risk 3: Missing Author Metadata
**Mitigation**:
- Site name extraction as fallback
- Manual mapping table for common sites
- Log warnings but still add entry

### Risk 4: Garbage Entries (Again!)
**Mitigation**:
- Comprehensive validation test harness
- Dry-run mode for testing
- User confirmation for batch adds >10 entries

---

## Files to Create/Modify

### New Files
1. `src/converters/md_to_latex/zotero_auto_add.py` (~400 lines)
2. `src/converters/md_to_latex/site_author_mapping.py` (~100 lines)
3. `tests/unit/test_zotero_auto_add_validation.py` (~300 lines)
4. `tests/unit/test_zotero_auto_add.py` (~200 lines)
5. `tests/unit/test_site_author_mapping.py` (~150 lines)

### Modified Files
1. `src/converters/md_to_latex/citation_manager.py` (add auto-add integration ~50 lines)
2. `src/converters/md_to_latex/converter.py` (initialize ZoteroAutoAdd ~20 lines)

### Total: ~1,220 lines of new code + tests

---

## Zotero Web API Endpoints

### Translation Server
```
POST /users/{userID}/items
Content-Type: application/json

{
    "url": "https://www.bbc.com/news/business-44885983",
    "items": true  # Request item data, not just URL
}

Response:
{
    "itemType": "newspaperArticle",
    "title": "Burberry burns bags, clothes and perfume worth millions",
    "creators": [{"lastName": "BBC"}],
    "date": "2018-07-19",
    ...
}
```

### Add to Collection
```
POST /users/{userID}/collections/{collectionKey}/items
Content-Type: application/json

{
    ... (metadata from translation)
}

Response:
{
    "success": {
        "0": "ABCD1234"  # Zotero key
    }
}
```

### Get Better BibTeX Key
```
GET /users/{userID}/items/{itemKey}?format=bibtex

Response:
@article{bbcBurberryBurnsBags2018,
    ...
}
```

---

## Implementation Timeline

### Phase 1: Core Infrastructure (2-3 hours)
- [ ] Create `ZoteroAutoAdd` class
- [ ] Implement translation server integration
- [ ] Add validation test harness
- [ ] Unit tests (basic)

### Phase 2: Quality Features (1-2 hours)
- [ ] Site author extraction
- [ ] DOI validation
- [ ] Error reporting
- [ ] Unit tests (comprehensive)

### Phase 3: Integration (1 hour)
- [ ] Wire into citation_manager
- [ ] Initialize in converter
- [ ] Integration test

### Phase 4: Validation (1 hour)
- [ ] Run full conversion test
- [ ] Manual Zotero inspection
- [ ] PDF verification
- [ ] Fix any issues

**Total estimate: 5-7 hours**

---

## References

- **Previous failure**: `docs/post-mortem-garbage-zotero-additions.md`
- **Auto-add plan**: `docs/retrospectives/citation-pipeline-auto-add-implementation.md`
- **Zotero API docs**: https://www.zotero.org/support/dev/web_api/v3/start
- **Better BibTeX**: `docs/better-bibtex-key-strategy.md`

---

**Generated**: 2025-10-29
**For**: OpenAI assistance implementation
**Status**: Ready for development
