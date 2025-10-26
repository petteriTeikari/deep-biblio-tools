# Plan: Direct Zotero Integration - End the Manual Export Hell

**Date**: 2025-10-26
**Status**: PLANNING
**Goal**: Replace all manual CSL JSON exports with direct Zotero API access

---

## Problem Statement

### Current Workflow (BROKEN)
1. User manually exports Zotero collection → CSL JSON file
2. File gets stale the moment it's exported
3. Any changes in Zotero require re-export
4. Manual file management causes confusion and errors
5. Multiple outdated copies of bibliography data

### User's Critical Feedback
> "it would be so much easier if you could access the local Zotero or the internet Zotero! why do I keep on manually exporting files to you that become stale!"

> "only source of truth should be Zotero, not the snapshop JSON that gets outdated in a moment"

**This is 100% correct.** We need direct Zotero access.

---

## Solution: Zotero Web API Integration

### Why Zotero Web API (Not Local SQLite)

**Recommended**: Zotero Web API
- ✅ Works without local Zotero installation
- ✅ Syncs automatically (always up to date)
- ✅ Official Python library (`pyzotero`) well-maintained
- ✅ RESTful API with good documentation
- ✅ Already have credentials in `.env`
- ✅ Already successfully used in cleanup scripts

**Alternative**: Local SQLite
- ❌ Requires parsing SQLite schema (complex)
- ❌ Only works when Zotero is running locally
- ❌ No sync - may not have latest data
- ❌ More fragile (schema changes between Zotero versions)

**Decision**: Use Zotero Web API exclusively

---

## Implementation Plan

### Phase 1: Replace CSL JSON Loading with Zotero API (HIGH PRIORITY)

**Files to Modify**:
1. `src/converters/md_to_latex/citation_manager.py` (~line 100-150)
2. `src/converters/md_to_latex/converter.py` (~line 200-250)

**Changes Needed**:

#### Current Code (citation_manager.py)
```python
def load_bibliography(self, csl_json_path: Path) -> None:
    """Load bibliography from CSL JSON file."""
    with open(csl_json_path) as f:
        self.bibliography = json.load(f)
```

#### New Code (with Zotero API)
```python
def load_bibliography_from_zotero(
    self,
    collection_name: str = "dpp-fashion",
    library_id: str | None = None,
    api_key: str | None = None
) -> None:
    """Load bibliography directly from Zotero API.

    Args:
        collection_name: Name of Zotero collection
        library_id: Zotero user/group ID (from env if None)
        api_key: Zotero API key (from env if None)
    """
    from pyzotero import zotero
    import os

    # Get credentials from env or args
    lib_id = library_id or os.getenv("ZOTERO_LIBRARY_ID")
    api_k = api_key or os.getenv("ZOTERO_API_KEY")
    lib_type = os.getenv("ZOTERO_LIBRARY_TYPE", "user")

    if not lib_id or not api_k:
        raise ValueError("Zotero credentials not found in .env")

    # Initialize Zotero client
    zot = zotero.Zotero(lib_id, lib_type, api_k)

    # Find collection by name
    collections = zot.collections()
    collection_id = None
    for coll in collections:
        if coll["data"]["name"] == collection_name:
            collection_id = coll["key"]
            break

    if not collection_id:
        raise ValueError(f"Collection '{collection_name}' not found")

    # Fetch all items from collection in CSL JSON format
    items = zot.everything(
        zot.collection_items(
            collection_id,
            format='csljson'
        )
    )

    # Store as bibliography (same format as CSL JSON file)
    self.bibliography = items

    logger.info(f"Loaded {len(items)} items from Zotero collection '{collection_name}'")
```

#### Update Converter to Use API
```python
# In converter.py convert() method
# BEFORE:
csl_json = self.input_file.with_suffix(".json")
if not csl_json.exists():
    raise FileNotFoundError(f"CSL JSON not found: {csl_json}")
self.citation_manager.load_bibliography(csl_json)

# AFTER:
collection = os.getenv("ZOTERO_COLLECTION", "dpp-fashion")
self.citation_manager.load_bibliography_from_zotero(collection)
```

**Testing**:
- Run conversion without any JSON file
- Verify it fetches latest data from Zotero
- Verify citation matching still works

---

### Phase 2: Add Missing Citations to Zotero Automatically (HIGH PRIORITY)

**Problem**: When a citation is missing from Zotero, currently we just warn. Instead, we should ADD it.

**Implementation**:

```python
def add_missing_citation_to_zotero(
    self,
    url: str,
    collection_id: str,
    markdown_citation: dict
) -> dict | None:
    """Add a missing citation to Zotero collection.

    Args:
        url: Citation URL
        collection_id: Zotero collection to add to
        markdown_citation: Parsed citation from markdown

    Returns:
        Zotero item data if successful, None otherwise
    """
    # Try translation-server first (best metadata)
    metadata = self._fetch_from_translator(url)

    if not metadata:
        # Try DOI/arXiv extraction
        metadata = self._fetch_from_doi_or_arxiv(url)

    if not metadata:
        # Create minimal entry from markdown
        metadata = {
            "itemType": "webpage",
            "title": markdown_citation.get("title", "Unknown"),
            "URL": url,
            "accessDate": datetime.utcnow().isoformat()
        }

        # Try to extract authors from markdown
        if markdown_citation.get("authors"):
            metadata["creators"] = [
                {"creatorType": "author", "name": author}
                for author in markdown_citation["authors"]
            ]

    # Add to Zotero
    try:
        item = self.zot.create_items([metadata], collection_id)
        logger.info(f"Added to Zotero: {metadata.get('title', url)[:50]}")
        return item
    except Exception as e:
        logger.error(f"Failed to add to Zotero: {e}")
        return None
```

**Workflow**:
1. Extract citations from markdown
2. For each citation URL:
   - Try to find in Zotero collection
   - If NOT found → `add_missing_citation_to_zotero()`
   - Re-fetch collection to get updated data
3. Generate BibTeX from complete Zotero data

**Result**: Zero missing citations, always!

---

### Phase 3: Environment Configuration

**Update `.env.example`**:
```bash
# Zotero API Configuration (REQUIRED)
ZOTERO_API_KEY=your_api_key_here
ZOTERO_LIBRARY_ID=your_library_id_here
ZOTERO_LIBRARY_TYPE=user  # or 'group'
ZOTERO_COLLECTION=dpp-fashion  # Default collection name

# Translation Server (for metadata extraction)
ZOTERO_TRANSLATOR_URL=http://localhost:1969
```

**Remove Obsolete Variables**:
```bash
# OBSOLETE - DO NOT USE
# LOCAL_BIBTEX_PATH=/path/to/file.bib  # DELETE THIS
```

---

### Phase 4: CLI Updates

**New Command**: `deep-biblio zotero-sync`

```bash
# Sync markdown citations to Zotero
uv run deep-biblio zotero-sync mcp-draft-refined-v3.md \
  --collection dpp-fashion \
  --add-missing  # Automatically add citations not in Zotero

# Just check what's missing (dry-run)
uv run deep-biblio zotero-sync mcp-draft-refined-v3.md \
  --collection dpp-fashion \
  --dry-run
```

**Update Existing Command**: `deep-biblio md2latex`

```bash
# No more CSL JSON needed!
uv run deep-biblio md2latex mcp-draft-refined-v3.md \
  --zotero-collection dpp-fashion \
  --add-missing  # Auto-add citations if missing

# Old way (still supported for legacy)
uv run deep-biblio md2latex mcp-draft-refined-v3.md \
  --csl-json mcp-draft-refined-v3.json  # DEPRECATED
```

---

### Phase 5: Update CLAUDE.md

**Add Section**: Bibliography Workflow

```markdown
## Bibliography Workflow

### Single Source of Truth: Zotero Web API

**NEVER** use manual BibTeX files. **NEVER** use stale CSL JSON exports. **ALWAYS** use Zotero Web API.

**Workflow**:
1. Update Zotero collection via web or desktop app
2. Run conversion - it fetches latest data from API automatically
3. Missing citations are added to Zotero automatically (if `--add-missing`)
4. `references.bib` is GENERATED from Zotero API data

**Environment Setup**:
```bash
ZOTERO_API_KEY=...        # Get from zotero.org/settings/keys
ZOTERO_LIBRARY_ID=...     # Your user ID
ZOTERO_COLLECTION=dpp-fashion
```

**DO NOT**:
- ❌ Use `LOCAL_BIBTEX_PATH` environment variable (obsolete)
- ❌ Manually export CSL JSON files (they get stale)
- ❌ Manually edit `references.bib` (it's generated)
- ❌ Keep manual BibTeX files like `dpp-fashion.bib`

**DO**:
- ✅ Use Zotero Web API exclusively
- ✅ Let converter auto-add missing citations to Zotero
- ✅ Delete `references.bib` before each conversion (it's regenerated)
- ✅ Trust Zotero as single source of truth
```

---

## Files to Create/Modify

### New Files
1. `src/converters/md_to_latex/zotero_client.py` - Wrapper for pyzotero with our patterns
2. `src/cli/commands/zotero_sync.py` - New CLI command
3. `tests/test_zotero_integration.py` - Integration tests

### Modified Files
1. `src/converters/md_to_latex/citation_manager.py` - Add Zotero API methods
2. `src/converters/md_to_latex/converter.py` - Use Zotero instead of CSL JSON
3. `.env.example` - Add Zotero config, remove obsolete vars
4. `.claude/CLAUDE.md` - Add bibliography workflow section
5. `README.md` - Update setup instructions

### Deleted Files/Variables
1. Remove `LOCAL_BIBTEX_PATH` from all documentation
2. Delete any remaining `dpp-fashion.bib` files
3. Update docs to stop mentioning CSL JSON exports

---

## Testing Strategy

### Unit Tests
```python
def test_load_from_zotero_api():
    """Test loading bibliography from Zotero API."""
    manager = CitationManager()
    manager.load_bibliography_from_zotero("dpp-fashion")
    assert len(manager.bibliography) > 0
    assert all("title" in item for item in manager.bibliography)

def test_add_missing_citation():
    """Test adding missing citation to Zotero."""
    manager = CitationManager()
    url = "https://arxiv.org/abs/2101.00001"
    item = manager.add_missing_citation_to_zotero(
        url,
        collection_id="ABC123",
        markdown_citation={"title": "Test Paper"}
    )
    assert item is not None
    assert item["data"]["URL"] == url
```

### Integration Tests
```bash
# Test full workflow without CSL JSON
cd /path/to/markdown
rm -f mcp-draft-refined-v3.json  # Remove manual export
uv run deep-biblio md2latex mcp-draft-refined-v3.md --add-missing

# Verify:
# 1. No CSL JSON file needed
# 2. references.bib created
# 3. All citations resolved
# 4. LaTeX compiles without errors
```

---

## Migration Path

### Step 1: Keep Backward Compatibility (First PR)
- Add Zotero API methods alongside existing CSL JSON loading
- Make CSL JSON optional: try Zotero first, fall back to JSON if exists
- Add `--zotero-collection` flag to CLI

### Step 2: Deprecate CSL JSON (Second PR)
- Print warning if CSL JSON file is used
- Update all documentation to recommend Zotero API
- Make `--csl-json` flag show deprecation warning

### Step 3: Remove CSL JSON Support (Third PR)
- Remove all CSL JSON loading code
- Remove `LOCAL_BIBTEX_PATH` support
- Update CLAUDE.md to forbid manual exports

---

## Success Criteria

### Must Have
- ✅ Load bibliography from Zotero Web API
- ✅ No manual CSL JSON export needed
- ✅ Auto-add missing citations to Zotero
- ✅ Conversion works without any local bibliography files
- ✅ Updated CLAUDE.md and documentation

### Should Have
- ✅ Translation-server integration for metadata
- ✅ Dry-run mode for `zotero-sync` command
- ✅ Progress bars and clear logging
- ✅ Error handling for API failures

### Nice to Have
- Cache Zotero API responses for offline work
- Conflict resolution if citation already exists
- Batch operations for multiple markdown files

---

## Estimated Timeline

1. **Phase 1** (Load from Zotero): 30 minutes
2. **Phase 2** (Auto-add missing): 45 minutes
3. **Phase 3** (Environment config): 15 minutes
4. **Phase 4** (CLI updates): 30 minutes
5. **Phase 5** (Documentation): 30 minutes
6. **Testing**: 30 minutes

**Total**: ~3 hours of focused work

---

## Next Steps

1. ✅ This plan reviewed and approved
2. Start with Phase 1: Replace CSL JSON loading
3. Test with real markdown file
4. Iterate on auto-add logic
5. Update documentation
6. Deploy and validate

---

**End of Plan**
