# Bibliography Source Refactor Plan - 2025-10-30

## The Problem

The current converter requires Zotero API credentials EVEN when using local JSON exports. This makes emergency conversions impossible.

**Root Cause**: `CitationManager` enforces `use_better_bibtex_keys=True` → requires Zotero credentials check, even though local JSON already contains the citation keys.

## The Goal

Support 3 independent bibliography sources with proper modularity:

### 1. Zotero Web API (Long-term, Production)
- Uses `pyzotero` package
- Fetches from Zotero collections
- Gets Better BibTeX keys
- **Requirements**: API credentials
- **Status**: Partially working, needs fixes

### 2. Local Zotero Database (Future)
- Direct SQLite access to local Zotero DB
- No network required
- Gets Better BibTeX keys from local DB
- **Requirements**: Zotero desktop app installed
- **Status**: NOT IMPLEMENTED

### 3. Local Bibliography Export (Emergency, NOW)
- Uses manually exported files from Zotero
- Formats: CSL JSON (.json), BibTeX (.bib), RDF (.rdf)
- Citation keys ALREADY in the file
- **Requirements**: Just the file path
- **Status**: BROKEN - requires Zotero credentials even though it shouldn't

## Immediate Fix (Emergency Path)

### Problem
```python
# citation_manager.py line 269-281
if use_better_bibtex_keys and not (zotero_api_key and zotero_library_id):
    raise ValueError("CRITICAL ERROR: Zotero keys are required...")
```

This check fires even when:
- User provides `zotero_json_path` with pre-existing citation keys
- No key generation is needed
- No Zotero API calls will be made

### Solution 1: Skip Credential Check When Using Local File (QUICK FIX)

```python
# citation_manager.py line 268
# Only require credentials if NOT using a local file with keys
if use_better_bibtex_keys and not zotero_json_path:
    if not (zotero_api_key and zotero_library_id):
        raise ValueError("CRITICAL ERROR...")
```

**Rationale**: If local JSON has citation keys, we don't need credentials.

### Solution 2: Add `--allow-local-keys` Flag (SAFER)

```python
# converter.py
def __init__(
    ...
    allow_local_citation_keys: bool = False,  # NEW FLAG
):
    # Only enforce Zotero requirement if not allowing local keys
    if use_better_bibtex_keys and not allow_local_citation_keys:
        if not (zotero_api_key and zotero_library_id):
            raise ValueError(...)
```

**Rationale**: Explicit opt-in for emergency mode.

## Current Status (2025-10-30 18:30)

### What We Tried
1. ✅ Used existing `deterministic_convert.py` with `--json` flag
2. ❌ Failed: Requires Zotero credentials
3. ✅ Added `load_dotenv()` to script
4. ❌ Still failed: `uv run` doesn't pass env vars properly
5. ❌ Tried exporting env vars: Still failed

### What We Learned
- The credential check is too early and too strict
- Even with credentials in `.env`, they're not loading properly
- The architecture couples matching logic with credential validation

## Next Actions (In Order)

### Immediate (Get PDF NOW)
1. **Apply Solution 1**: Modify `citation_manager.py` to skip credential check when `zotero_json_path` is provided
2. **Test**: Run `deterministic_convert.py` with local JSON
3. **Verify**: Check PDF has citations (not ?)
4. **Submit**: User can finally submit manuscript!

### Short-term (This Week)
1. **Add env loading**: Ensure `.env` loads properly in all entry points
2. **Add Solution 2 flag**: Implement `--allow-local-keys` for explicit emergency mode
3. **Document**: Update CLI help text and README

### Long-term (Next Month)
1. **Modular refactor**: Create `BiblographySource` abstract base class
2. **Three implementations**:
   - `ZoteroAPISource(BiblographySource)`
   - `LocalZoteroSource(BiblographySource)`
   - `LocalFileSource(BiblographySource)`
3. **Factory pattern**: Choose source based on arguments
4. **No coupling**: Citation matching logic independent of source

## Refactor Design (Long-term)

### Abstract Interface

```python
from abc import ABC, abstractmethod

class BiblographySource(ABC):
    """Abstract interface for bibliography data sources."""

    @abstractmethod
    def load_entries(self) -> List[dict]:
        """Load bibliography entries as CSL JSON."""
        pass

    @abstractmethod
    def get_citation_key(self, entry: dict) -> str:
        """Get citation key for an entry."""
        pass

    @abstractmethod
    def requires_credentials(self) -> bool:
        """Whether this source needs authentication."""
        pass
```

### Implementations

```python
class ZoteroAPISource(BiblographySource):
    """Fetch from Zotero Web API."""

    def __init__(self, api_key: str, library_id: str, collection: str):
        self.zot = zotero.Zotero(library_id, 'user', api_key)
        self.collection = collection

    def load_entries(self):
        return self.zot.collection_items(self.collection)

    def requires_credentials(self):
        return True

class LocalFileSource(BiblographySource):
    """Load from local JSON/BibTeX/RDF export."""

    def __init__(self, file_path: Path):
        self.file_path = file_path

    def load_entries(self):
        # Parse JSON/BibTeX/RDF based on extension
        with open(self.file_path) as f:
            return json.load(f)  # or bibtexparser, etc.

    def requires_credentials(self):
        return False  # No credentials needed!
```

### Usage

```python
# Automatic source selection
def create_bibliography_source(
    zotero_api_key: str | None,
    zotero_library_id: str | None,
    collection_name: str | None,
    local_file_path: Path | None,
) -> BiblographySource:
    """Factory to create appropriate source."""

    if local_file_path:
        return LocalFileSource(local_file_path)
    elif zotero_api_key and zotero_library_id:
        return ZoteroAPISource(zotero_api_key, zotero_library_id, collection_name)
    else:
        raise ValueError("Must provide either local file or Zotero credentials")
```

## Related Issues From Old Docs

From `docs/known-issues/bibliography-extraction-issues.md`:
1. "et al" parsing catastrophes (line 246)
2. Missing first names despite DOI (line 365)
3. MDPI blocking (line 382)
4. No failure tracking (line 393)

**These are SEPARATE issues from the current emergency** - we'll fix them later.

## Decision Log

### Why Not Just Use Better BibTeX Export?

**Question**: Can't we just export BibTeX from Zotero and use that?

**Answer**: YES! That's exactly what we're trying to do. But the code currently REQUIRES API credentials even when using a pre-exported file. That's the bug we're fixing.

### Why Not Disable use_better_bibtex_keys?

**Question**: Can't we just set `use_better_bibtex_keys=False`?

**Answer**: NO! That would cause the code to GENERATE keys locally, which violates the CLAUDE.md rule. The local JSON ALREADY HAS proper Better BibTeX keys - we just need to use them.

## Success Criteria

### For Emergency Fix (NOW)
- [x] User can run converter with local JSON file
- [ ] Converter completes without requiring Zotero API credentials
- [ ] PDF generates with proper citations (no ? marks)
- [ ] User can submit manuscript TODAY

### For Long-term Refactor (LATER)
- [ ] Three independent bibliography sources work
- [ ] No coupling between source type and matching logic
- [ ] Clear error messages for each source type
- [ ] Comprehensive tests for all three sources

## Timeline

- **TODAY (Oct 30)**: Emergency fix + user submits manuscript
- **This Week**: Proper env loading + documentation
- **Next Month**: Full modular refactor

## References

- Current code: `src/converters/md_to_latex/citation_manager.py:269-281`
- Entry point: `scripts/deterministic_convert.py`
- Related docs: `docs/known-issues/bibliography-extraction-issues.md`
- CLAUDE.md rules: Never generate citation keys locally
