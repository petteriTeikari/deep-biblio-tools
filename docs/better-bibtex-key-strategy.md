# Better BibTeX Key Strategy: Root Cause Analysis and Fix Plan

**Context**: Python tool converts LLM-generated markdown to LaTeX. Citations must use Better BibTeX keys from Zotero.

**Problem**: Generated bibliographies use short keys (`adisorn2021`) instead of Better BibTeX keys (`adisornDigitalProductPassport2021`). Some entries don't exist in Zotero.

**Root Cause**: Code generates keys instead of using Zotero's Better BibTeX keys.

---

## Design Principle

**Never generate citation keys. Only use Better BibTeX keys from Zotero.**

### Better BibTeX Format
- Pattern: `[author][ShortTitle][year]`
- Example: `adisornDigitalProductPassport2021` (valid)
- Anti-pattern: `adisorn2021` (invalid - generated)

### Benefits
- Self-documenting: key indicates paper content
- Consistent: same paper always gets same key in Zotero
- Unique: title words prevent collisions
- Traceable: every entry maps back to Zotero

---

## Current Architecture Problems

### Problem 1: Wrong Zotero API Method
**Current**: Uses `get_collection_items()` → Returns CSL JSON → No Better BibTeX keys
**Fix**: Use `get_collection_bibtex()` → Returns BibTeX export → Includes Better BibTeX keys

### Problem 2: Key Generation Code Exists
**Locations**:
- `utils.py:510` - `generate_citation_key()` function
- `citation_manager.py:64-66` - Initial key generation
- `citation_manager.py:69-76` - `regenerate_key_with_title()` method
- `citation_manager.py:556-566` - Post-enrichment regeneration

**Fix**: Remove all key generation. Require keys from Zotero only.

### Problem 3: Creates Hallucinated Entries
**Current**: If citation not in Zotero → generates stub entry with fake key
**Example**: `agrawal2021` - has no title, no metadata, doesn't exist in Zotero
**Fix**: Fail explicitly if citation not in Zotero. Never create stub entries.

### Problem 4: No Better BibTeX Plugin Verification
**Current**: Assumes plugin installed, falls back to generation if not
**Fix**: Verify plugin on startup. Fail if not installed with clear error.

---

## Correct Workflow

```
1. Extract citation from markdown
   → [Adisorn et al., 2021](https://doi.org/10.3390/en14082289)

2. Load Zotero collection via BibTeX export (not CSL JSON)
   → bibtex = zotero.get_collection_bibtex("dpp-fashion")
   → Parse BibTeX entries
   → Build mapping: {DOI: {key, metadata}}

3. Match citation to Zotero by DOI
   → doi_to_key["10.3390/en14082289"] = {
       key: "adisornDigitalProductPassport2021",
       metadata: {...}
     }

4. Use key as-is in bibliography
   → @article{adisornDigitalProductPassport2021, ...}

5. If citation NOT in Zotero
   → Raise error: "Citation not in Zotero: [details]"
   → Never generate key
```

---

## Implementation Plan

### Phase 1: Disable Key Generation (Critical)
```python
# utils.py:510
def generate_citation_key(*args, **kwargs):
    raise RuntimeError(
        "Key generation forbidden. Keys must come from Zotero Better BibTeX."
    )
```

### Phase 2: Require Zotero Keys
```python
# citation_manager.py
class Citation:
    def __init__(self, authors: str, year: str, key: str, **kwargs):
        if not key:
            raise ValueError("Citation key required from Zotero")
        if len(key) < 15 or not self._is_better_bibtex_format(key):
            raise ValueError(f"Invalid key format: {key}")
        self.key = key
```

### Phase 3: Use BibTeX Export
```python
# zotero_integration.py
def load_collection_with_keys(self, collection_name: str) -> dict:
    """Returns {DOI: {key, metadata}} mapping with Better BibTeX keys."""
    bibtex_content = self.get_collection_bibtex(collection_name)
    entries = parse_bibtex(bibtex_content)
    return {entry.doi: {
        'key': entry.citation_key,
        'metadata': entry
    } for entry in entries if entry.doi}
```

### Phase 4: Verify Plugin Installed
```python
# zotero_integration.py
def _verify_better_bibtex_plugin(self):
    # Check if keys match Better BibTeX pattern
    if not self._has_better_bibtex_keys(test_export):
        raise RuntimeError(
            "Better BibTeX plugin required. "
            "Install: https://retorque.re/zotero-better-bibtex/"
        )
```

---

## Enforcement Mechanisms

### Code Guards
- `generate_citation_key()` raises error always
- `Citation.__init__()` validates key format
- `load_collection_with_keys()` verifies Better BibTeX keys
- All entries require Zotero source flag

### Testing
- Unit tests: Key validation, generation forbidden
- Integration tests: Zotero API returns Better BibTeX keys
- E2E tests: Full conversion preserves Zotero keys, fails on missing entries

### CI/CD
- Pre-commit hook: Check for key generation code
- GitHub Actions: Run validation on every commit
- Script: `scripts/check_key_generation.py` scans for forbidden patterns

### Documentation
- Update `.claude/CLAUDE.md` with Better BibTeX rules
- Update `README.md` with plugin requirement
- Link to `docs/architecture/bibtex-key-formats.md` (design rationale)

---

## Questions for Expert Review

### Architecture
1. BibTeX export → parse keys vs. CSL JSON + separate key lookup?
2. Require Better BibTeX plugin (fail if missing) vs. support both formats?
3. Cache parsed collection vs. reload on each conversion?

### Error Handling
4. Citation not in Zotero: Fail immediately vs. auto-add via API vs. interactive approval?
5. Valid DOI but no Zotero entry: Error vs. offer to add vs. create temporary entry?

### Performance
6. Large collections (1000+ entries): Parse entire BibTeX vs. lazy loading vs. persistent cache?
7. Multiple conversions: Re-parse every time vs. cache with invalidation strategy?

### Testing
8. Mock Zotero API vs. test collection vs. recorded HTTP interactions (VCR.py)?
9. What test coverage is sufficient? Current plan: unit + integration + E2E.

### Robustness
10. Prevent regression to key generation: Code guards + tests + hooks sufficient?
11. Race conditions: Zotero updated between load and convert? Timestamp checking? Lock collection?
12. Multi-collection scenarios: Single collection vs. multiple vs. entire library?

### Maintenance
13. Keep enforcement synchronized: guards, tests, hooks, docs. How to prevent drift?
14. Document architectural decisions: How to ensure future developers understand "why"?

---

## Success Criteria

Before claiming "fixed":
1. Zero key generation code in codebase (only deprecation stubs that raise errors)
2. All citations have Better BibTeX keys (≥15 chars, camelCase pattern)
3. All tests pass (unit + integration + E2E)
4. Conversion fails gracefully if citation not in Zotero (no stub entries)
5. Better BibTeX plugin verified on startup
6. Pre-commit hooks prevent regressions
7. Generated PDF has zero `(?)` citations
8. All entries have complete metadata (no "Unknown" titles)

### Validation Commands
```bash
# No key generation (only deprecation stubs)
git grep "generate_citation_key" src/ | grep -v "raise RuntimeError"

# All keys are Better BibTeX format
python scripts/validate_better_bibtex_keys.py output/references.bib

# Tests pass
pytest tests/test_citation_keys.py tests/test_zotero_integration.py -v

# Full conversion works
deep-biblio-md2latex paper.md --collection dpp-fashion
# Verify: zero (?) in PDF, all keys ≥15 chars
```

---

## Related Documentation

- `docs/architecture/bibtex-key-formats.md` - Original design rationale
- `docs/usage/zotero-setup-guide.md` - Zotero API setup
- `.claude/CLAUDE.md` - Development guidelines (see Bibliography Workflow section)

---

**Status**: Analysis complete, implementation pending expert review
**Next**: Review architectural questions, implement fixes, add enforcement
