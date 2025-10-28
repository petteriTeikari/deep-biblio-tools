# Complete Learnings and Enforcement Plan: Better BibTeX Citation Key System

**Date**: 2025-10-28
**Purpose**: Comprehensive documentation for OpenAI to provide expert advice on system robustness
**Context**: OpenAI does not have access to the codebase - this document provides full context

---

## Executive Summary

**The Problem**: Citation keys in generated bibliographies are wrong format (`adisorn2021`) instead of Better BibTeX format (`adisornDigitalProductPassport2021`). Some entries (`agrawal2021`) don't even exist in Zotero.

**Root Cause**: Code generates its own citation keys instead of using Better BibTeX keys from Zotero.

**Critical Design Rule Violated**: **NEVER generate BibTeX citation keys - ONLY use Better BibTeX keys from Zotero as-is.**

**Impact**:
- Generated bibliographies have non-descriptive short keys
- Inconsistent with Zotero collection which has proper Better BibTeX keys
- Hallucinated entries with fake keys and no metadata
- Manual editing required to fix every conversion

---

## Background: Better BibTeX Strategy

### Original Design Document

See: [`docs/architecture/bibtex-key-formats.md`](file:///home/petteri/Dropbox/github-personal/deep-biblio-tools/docs/architecture/bibtex-key-formats.md)

### Vision

**Single Source of Truth**: Zotero collection with Better BibTeX plugin is the ONLY source of citation keys.

**No Key Generation**: The converter should NEVER generate citation keys. It should ONLY:
1. Extract citations from markdown
2. Match them to Zotero entries
3. Use the Better BibTeX key from Zotero as-is
4. Generate BibTeX entries with those keys

### Better BibTeX Format

**Pattern**: `[authorLastName][ShortTitle][Year]`

**Examples**:
- ✅ `adisornDigitalProductPassport2021` (Better BibTeX)
- ❌ `adisorn2021` (Short garbage format - WRONG)

**Benefits**:
- **Self-documenting**: Key tells you what paper it refers to
- **Unique**: Title words prevent collisions
- **Consistent**: Same paper always gets same key in Zotero
- **Human-readable**: Easy to identify papers in LaTeX source

### Implementation Goals

1. **Deterministic**: Same Zotero collection → same keys every time
2. **Zero manual editing**: Generated `.bib` file should be ready to use
3. **Traceable**: Every entry must trace back to Zotero
4. **No hallucinations**: If citation not in Zotero → fail clearly, don't create stub entries

---

## Technical Architecture Context

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Markdown Document                         │
│  [Adisorn et al., 2021](https://doi.org/10.3390/en14082289) │
└────────────────────┬────────────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────────────────┐
│            Citation Extractor (Unified)                      │
│  - Parses markdown for [Author (Year)](URL) patterns        │
│  - Extracts: author, year, DOI/URL                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────────────────┐
│              Citation Manager                                │
│  - Creates Citation objects                                  │
│  - Manages citation registry                                 │
│  - ❌ CURRENTLY: Generates keys via generate_citation_key()  │
│  - ✅ SHOULD: Accept keys from Zotero only                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────────────────┐
│            Zotero Integration                                │
│  - get_collection_items() → CSL JSON (no Better BibTeX keys)│
│  - get_collection_bibtex() → BibTeX export (has keys) ✅     │
│  - ❌ CURRENTLY: Uses CSL JSON                               │
│  - ✅ SHOULD: Use BibTeX export                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     v
┌─────────────────────────────────────────────────────────────┐
│           Zotero Collection (dpp-fashion)                    │
│  - Entry: adisornDigitalProductPassport2021                  │
│  - Better BibTeX plugin generates descriptive keys           │
│  - Single source of truth                                    │
└─────────────────────────────────────────────────────────────┘
```

### File Structure

```
deep-biblio-tools/
├── src/converters/md_to_latex/
│   ├── converter.py              # Main conversion orchestrator
│   ├── citation_extractor_unified.py  # Parses markdown for citations
│   ├── citation_manager.py       # ❌ Generates keys (WRONG!)
│   ├── zotero_integration.py     # API calls to Zotero
│   └── utils.py                  # ❌ generate_citation_key() (WRONG!)
├── docs/
│   ├── architecture/
│   │   └── bibtex-key-formats.md # Better BibTeX strategy document
│   └── usage/
│       └── zotero-setup-guide.md # Zotero API setup
└── scripts/
    ├── validate_bib_source.py    # Validates source .bib file
    └── extract_bbl_entries_raw.py # Extracts formatted .bbl entries
```

---

## Comprehensive Root Cause Analysis

### Hypothesis 1: Zotero API Returns CSL JSON (No Better BibTeX Keys)

**Evidence**: `docs/zotero-api-integration-complete.md` states:
> "Load Collection in CSL JSON format"

**Code Location**: `src/converters/md_to_latex/zotero_integration.py:78`

```python
def get_collection_items(self, collection_name: str) -> list[dict]:
    """Fetch collection items from Zotero API.

    Returns CSL JSON format - does NOT include Better BibTeX keys.
    """
    # Returns items in CSL JSON format
    items = self.zotero.collection_items(collection_id)
    return items
```

**Why This Is Wrong**:
- CSL JSON format does NOT include Better BibTeX keys
- Better BibTeX keys are plugin-specific metadata
- Zotero Web API standard format doesn't expose them

**Fix Required**: Use `get_collection_bibtex()` method instead.

---

### Hypothesis 2: Code Generates Its Own Keys ⚠️ CONFIRMED

**Evidence**: `src/converters/md_to_latex/utils.py:510`

```python
def generate_citation_key(
    authors: str, year: str, title: str = "", use_better_bibtex: bool = True
) -> str:
    """Generate a citation key from authors, year, and optionally title.

    Args:
        authors: Author string (e.g., "Smith, John and Doe, Jane")
        year: Publication year
        title: Paper title (used for Better BibTeX style keys)
        use_better_bibtex: If True, use Better BibTeX style (default),
                          otherwise use simple authorYear style

    Returns:
        Citation key in either Better BibTeX format (smithMachineLearning2023)
        or simple format (smith2023)
    """
    # THIS ENTIRE FUNCTION VIOLATES THE DESIGN PRINCIPLE
    # Keys should NEVER be generated
    # Keys should ONLY come from Zotero Better BibTeX
```

**Called By**: `src/converters/md_to_latex/citation_manager.py:64-66`

```python
# Generate key - will be regenerated after title is available if using Better BibTeX
self.key = key or generate_citation_key(
    authors, year, "", use_better_bibtex=False
)  # Start with simple key
```

**Also Called**: `src/converters/md_to_latex/citation_manager.py:556-566`

```python
# Regenerate citation key with title if using Better BibTeX
if self.use_better_bibtex_keys and citation.title:
    # Generate new key
    new_key = citation.regenerate_key_with_title()
```

**Why This Is Wrong**:
- Violates fundamental design principle: NEVER generate keys
- "Regenerating" keys means generating NEW ones, not preserving Zotero keys
- Even with `use_better_bibtex=True`, still generates locally instead of using Zotero's
- Creates inconsistency between Zotero collection and generated bibliography

**Fix Required**:
1. Remove ALL calls to `generate_citation_key()`
2. ONLY accept keys from Zotero
3. If key not available from Zotero → citation doesn't exist → FAIL

---

### Hypothesis 3: `use_better_bibtex_keys` Flag Exists But Misimplemented

**Evidence**: `src/converters/md_to_latex/citation_manager.py:216-221`

```python
def __init__(
    self,
    use_better_bibtex_keys: bool = True,  # Flag exists
    zotero_client: Optional[ZoteroIntegration] = None,
):
    self.use_better_bibtex_keys = use_better_bibtex_keys
```

**The Misunderstanding**:
- Flag name suggests "use Better BibTeX keys FROM ZOTERO"
- Implementation interprets it as "generate Better BibTeX-STYLE keys"
- These are COMPLETELY different things!

**Correct Interpretation**:
- `use_better_bibtex_keys=True` → Use long keys from Zotero Better BibTeX plugin
- `use_better_bibtex_keys=False` → Use short standard keys from Zotero

**Both cases** should get keys FROM ZOTERO, not generate them!

**Fix Required**: Rename flag to clarify intent, update implementation to fetch keys from Zotero.

---

### Hypothesis 4: Wrong Zotero API Method Being Used

**Evidence**: Two methods exist in `zotero_integration.py`:

**Method 1 (Currently Used)**: `get_collection_items()`
```python
def get_collection_items(self, collection_name: str) -> list[dict]:
    """Fetch collection items from Zotero API.

    Returns CSL JSON format.
    """
    items = self.zotero.collection_items(collection_id)
    return items  # CSL JSON - NO Better BibTeX keys
```

**Method 2 (Should Use)**: `get_collection_bibtex()`
```python
def get_collection_bibtex(self, collection_name: str) -> str:
    """Fetch BibTeX export from Zotero collection with Better BibTeX keys.

    If Better BibTeX plugin is installed, this will include citation keys
    generated by Better BibTeX. Otherwise, falls back to standard Zotero keys.

    Returns:
        Complete BibTeX file content as string
    """
```

**Why This Matters**:
- `get_collection_items()` → CSL JSON → No Better BibTeX keys available
- `get_collection_bibtex()` → BibTeX export → Includes Better BibTeX keys (if plugin installed)

**Fix Required**:
1. Switch to using `get_collection_bibtex()`
2. Parse returned BibTeX to extract citation keys
3. Build mapping: `{DOI → Better BibTeX key}`
4. Use this mapping when creating bibliography entries

---

### Hypothesis 5: Hallucinated Entries (`agrawal2021`)

**Evidence**: From compiled `.bbl` file:

```latex
\bibitem[{Agrawal et~al.(2021)}]{agrawal2021}
\href{https://doi.org/10.1016/j.compind.2021.107130}{Agrawal, et~al. (2021)}
```

**Observations**:
- Entry has citation key `agrawal2021`
- Entry has NO title
- Entry has NO content (just author and year)
- Entry does NOT exist in Zotero dpp-fashion collection (confirmed by user)
- DOI returns 404 from CrossRef

**What Happened**:
1. Citation extractor found `[Agrawal et al., 2021](DOI:10.1016/j.compind.2021.107130)` in markdown
2. Tried to match to Zotero → NOT FOUND
3. Instead of failing, generated stub entry with short key `agrawal2021`
4. Tried to fetch metadata from CrossRef → DOI returned 404
5. Created empty entry anyway

**Why This Is Wrong**:
- Creates entries that don't exist in Zotero
- Pollutes bibliography with garbage entries
- No way to trace back to source

**Fix Required**:
1. If citation NOT in Zotero → Either:
   - Option A: Add to Zotero via API (with proper metadata)
   - Option B: FAIL with clear error: "Citation not in Zotero: Agrawal 2021"
2. NEVER create stub entries with generated keys
3. NEVER create entries without full metadata

---

### Hypothesis 6: Matching Logic Doesn't Preserve Better BibTeX Keys

**Evidence**: `docs/plea-to-openai-robust-matching.md` describes matching strategies:
- URL matching
- DOI matching
- ISBN matching
- arXiv ID matching
- Author/title fuzzy matching

**Missing**: No mention of Better BibTeX keys in matching logic!

**The Problem**:
1. Extractor finds citation in markdown with DOI
2. Zotero collection has entry with same DOI
3. Matching succeeds by DOI
4. But then code GENERATES new key instead of using Zotero's Better BibTeX key

**Example**:
```
Markdown:    [Adisorn et al., 2021](https://doi.org/10.3390/en14082289)
Zotero:      adisornDigitalProductPassport2021 (DOI: 10.3390/en14082289)
Generated:   adisorn2021  ← WRONG! Should use Zotero's key!
```

**Fix Required**:
1. When match found, PRESERVE the Better BibTeX key from Zotero
2. Store key in Citation object: `citation.key = zotero_entry.better_bibtex_key`
3. Use that key when writing BibTeX entries
4. NEVER regenerate or override

---

### Hypothesis 7: Multiple Code Paths Generate Keys

**Evidence**: Key generation happens in multiple places:

**Location 1**: `utils.py:510` - `generate_citation_key()` function

**Location 2**: `citation_manager.py:64-66` - Initial key generation
```python
self.key = key or generate_citation_key(authors, year, "", use_better_bibtex=False)
```

**Location 3**: `citation_manager.py:69-72` - `regenerate_key_with_title()` method
```python
def regenerate_key_with_title(self) -> str:
    """Regenerate citation key using title if Better BibTeX is enabled."""
    if self.use_better_bibtex and self.title:
        new_key = generate_citation_key(
            self.authors, self.year, self.title, use_better_bibtex=True
        )
```

**Location 4**: `citation_manager.py:556-566` - Post-enrichment regeneration

**Why This Is A Problem**:
- Even if one path is fixed, others may still generate keys
- No single source of truth
- Hard to enforce "no key generation" rule
- Debugging is difficult - which path created which key?

**Fix Required**:
1. Remove ALL key generation code paths
2. Single rule: Keys come from Zotero ONLY
3. Add guard at Citation class level: Raise error if key not provided from Zotero

---

### Hypothesis 8: System Doesn't Verify Better BibTeX Plugin Is Installed

**Evidence**: `zotero_integration.py:81-84` comment:

```python
def get_collection_bibtex(self, collection_name: str) -> str:
    """Fetch BibTeX export from Zotero collection with Better BibTeX keys.

    If Better BibTeX plugin is installed, this will include citation keys
    generated by Better BibTeX. Otherwise, falls back to standard Zotero keys.
    """
```

**The Problem**:
- Comment suggests Better BibTeX plugin might not be installed
- If plugin not installed, keys won't be available in proper format
- Code might have fallback to generate keys
- But user HAS Better BibTeX installed (screenshot shows proper keys)

**Questions**:
1. Does system verify Better BibTeX plugin is installed?
2. What happens if plugin not installed?
3. Is there a fallback that generates keys?

**Fix Required**:
1. Add explicit check: Is Better BibTeX plugin installed?
2. Make it a REQUIREMENT - fail early if not installed
3. NEVER fall back to key generation
4. Clear error message: "Better BibTeX plugin required. Install from: [URL]"

---

## What SHOULD Happen: Correct Workflow

### Step 1: Extract Citation from Markdown

```markdown
[Adisorn et al., 2021](https://doi.org/10.3390/en14082289)
```

**Extracted Data**:
- Authors: "Adisorn et al."
- Year: 2021
- DOI: 10.3390/en14082289

### Step 2: Load Zotero Collection via Better BibTeX Export

```python
# CORRECT: Use BibTeX export, not CSL JSON
bibtex_content = zotero_client.get_collection_bibtex("dpp-fashion")

# Parse BibTeX to extract keys
entries = parse_bibtex(bibtex_content)

# Build mapping: DOI → Better BibTeX key
doi_to_key = {}
for entry in entries:
    if entry.doi:
        doi_to_key[entry.doi] = entry.citation_key

# Example mapping:
# {
#   "10.3390/en14082289": "adisornDigitalProductPassport2021",
#   "10.1234/example": "smithMachineLearning2023",
#   ...
# }
```

### Step 3: Match Citation to Zotero Entry

```python
doi = "10.3390/en14082289"

if doi in doi_to_key:
    citation_key = doi_to_key[doi]  # "adisornDigitalProductPassport2021"
else:
    # Citation NOT in Zotero
    raise ValueError(f"Citation not in Zotero collection: DOI {doi}")
```

### Step 4: Use Key As-Is in Generated Bibliography

```bibtex
@article{adisornDigitalProductPassport2021,
  author = {Adisorn, Tunn and ... },
  title = {Digital product passports for the circular economy ...},
  journal = {Energies},
  year = {2021},
  doi = {10.3390/en14082289}
}
```

### Step 5: NEVER Generate Keys

```python
# ❌ WRONG - Never do this
generated_key = f"{first_author}{year}"  # "adisorn2021"

# ✅ CORRECT - Always use Zotero key
zotero_key = get_better_bibtex_key_from_zotero(doi)  # "adisornDigitalProductPassport2021"
```

---

## What ACTUALLY Happens: Current Broken Workflow

### Step 1: Extract Citation from Markdown ✅

**Status**: This part works correctly

### Step 2: Load Zotero Collection in CSL JSON ❌

```python
# WRONG: Uses CSL JSON
items = zotero_client.get_collection_items("dpp-fashion")
# Returns CSL JSON → No Better BibTeX keys available
```

### Step 3: Match by DOI ✅/❌

```python
# Matching works
found_entry = match_by_doi(citation.doi, zotero_items)
# But then...
```

### Step 4: Generate Key from Author+Year ❌

```python
# WRONG: Generates new key
citation_key = generate_citation_key(
    authors="Adisorn et al.",
    year="2021",
    title="",
    use_better_bibtex=False
)
# Returns: "adisorn2021"  ← SHORT GARBAGE FORMAT
```

### Step 5: Fetch Metadata from CrossRef ✅/❌

```python
# CrossRef fetch works for valid DOIs
metadata = fetch_from_crossref(doi)
# But for invalid DOIs...
```

### Step 6: Create Entry Even If DOI Invalid ❌

```python
# WRONG: Creates stub entry with no metadata
if crossref_failed:
    # Still creates entry with generated key
    entry = create_stub_entry(
        key="agrawal2021",  # Generated
        authors="Agrawal et al.",
        year="2021"
        # No title, no content!
    )
```

---

## Enforcement Mechanisms: Making the System Robust

### 1. Code-Level Guards

#### Guard 1: Disable Key Generation

```python
# src/converters/md_to_latex/utils.py

def generate_citation_key(*args, **kwargs):
    """DEPRECATED: Citation keys must come from Zotero only.

    This function violates the design principle: NEVER generate keys.
    Use Better BibTeX keys from Zotero collection instead.

    Raises:
        RuntimeError: Always - this function should never be called
    """
    raise RuntimeError(
        "Citation key generation is FORBIDDEN. "
        "Keys must come from Zotero Better BibTeX only. "
        "See docs/architecture/bibtex-key-formats.md"
    )
```

#### Guard 2: Require Keys from Zotero

```python
# src/converters/md_to_latex/citation_manager.py

class Citation:
    def __init__(
        self,
        authors: str,
        year: str,
        key: str,  # Make required, not optional
        zotero_source: bool = True,  # Track source
        **kwargs
    ):
        if not key:
            raise ValueError("Citation key is required and must come from Zotero")

        if not zotero_source:
            raise ValueError(
                "Citation keys must originate from Zotero. "
                "Key generation is forbidden."
            )

        self.key = key
        self.zotero_source = zotero_source
```

#### Guard 3: Validate Better BibTeX Key Format

```python
# src/converters/md_to_latex/utils.py

def validate_better_bibtex_key(key: str) -> bool:
    """Validate that key matches Better BibTeX format.

    Better BibTeX keys have pattern: [author][ShortTitle][Year]
    Example: adisornDigitalProductPassport2021

    Short keys like "adisorn2021" are INVALID.
    """
    # Better BibTeX keys are long (20+ chars typically)
    if len(key) < 15:
        return False

    # Should have camelCase title component
    # Look for mix of lowercase and uppercase
    has_lowercase = any(c.islower() for c in key)
    has_uppercase = any(c.isupper() for c in key)

    if not (has_lowercase and has_uppercase):
        return False

    # Should end with 4-digit year
    if not key[-4:].isdigit():
        return False

    return True


def enforce_better_bibtex_key(key: str) -> str:
    """Enforce Better BibTeX key format or raise error.

    Raises:
        ValueError: If key doesn't match Better BibTeX format
    """
    if not validate_better_bibtex_key(key):
        raise ValueError(
            f"Invalid citation key format: '{key}'\n"
            f"Expected Better BibTeX format (e.g., 'adisornDigitalProductPassport2021')\n"
            f"Got short format (e.g., 'adisorn2021')\n"
            f"Keys must come from Zotero Better BibTeX plugin."
        )
    return key
```

#### Guard 4: Verify Zotero Source for All Entries

```python
# src/converters/md_to_latex/citation_manager.py

def add_citation(self, citation: Citation) -> str:
    """Add citation to registry with validation."""

    # Validate key format
    enforce_better_bibtex_key(citation.key)

    # Verify Zotero source
    if not citation.zotero_source:
        raise ValueError(
            f"Citation '{citation.key}' not from Zotero. "
            f"All citations must exist in Zotero collection."
        )

    # Verify not stub/empty entry
    if not citation.title or citation.title == "Unknown":
        raise ValueError(
            f"Citation '{citation.key}' has no title. "
            f"Incomplete entries not allowed. "
            f"Add complete entry to Zotero first."
        )

    self.citations[citation.key] = citation
    return citation.key
```

---

### 2. Zotero Integration Enforcement

#### Change 1: Always Use BibTeX Export

```python
# src/converters/md_to_latex/zotero_integration.py

class ZoteroIntegration:
    def load_collection(self, collection_name: str) -> dict[str, dict]:
        """Load collection with Better BibTeX keys.

        Returns:
            Mapping of {DOI: {key, metadata}} where key is Better BibTeX key
        """
        # STEP 1: Verify Better BibTeX plugin is installed
        self._verify_better_bibtex_plugin()

        # STEP 2: Get BibTeX export (includes Better BibTeX keys)
        bibtex_content = self.get_collection_bibtex(collection_name)

        # STEP 3: Parse BibTeX entries
        entries = self._parse_bibtex_entries(bibtex_content)

        # STEP 4: Build DOI → key mapping
        doi_to_key = {}
        for entry in entries:
            doi = entry.get('doi')
            key = entry.get('ID')  # Citation key from BibTeX

            if doi and key:
                # Validate Better BibTeX key format
                enforce_better_bibtex_key(key)

                doi_to_key[doi] = {
                    'key': key,
                    'metadata': entry
                }

        return doi_to_key
```

#### Change 2: Verify Better BibTeX Plugin

```python
def _verify_better_bibtex_plugin(self):
    """Verify Better BibTeX plugin is installed and working.

    Raises:
        RuntimeError: If Better BibTeX plugin not installed
    """
    # Try to get BibTeX export for a test collection
    # Better BibTeX keys have specific format
    # We can detect if plugin is installed by checking key format

    try:
        # Get library collections
        collections = self.zotero.collections()
        if not collections:
            logger.warning("No collections found in Zotero library")
            return

        # Try to export first collection
        test_collection = collections[0]['key']
        bibtex = self.zotero.collection_items(test_collection, format='bibtex')

        # Check if keys match Better BibTeX pattern
        if not self._has_better_bibtex_keys(bibtex):
            raise RuntimeError(
                "Better BibTeX plugin not detected in Zotero.\n"
                "Install from: https://retorque.re/zotero-better-bibtex/\n"
                "This plugin is REQUIRED for deep-biblio-tools."
            )

        logger.info("✅ Better BibTeX plugin detected")

    except Exception as e:
        raise RuntimeError(
            f"Failed to verify Better BibTeX plugin: {e}\n"
            f"Ensure Better BibTeX is installed in Zotero."
        )


def _has_better_bibtex_keys(self, bibtex_content: str) -> bool:
    """Check if BibTeX content has Better BibTeX format keys."""
    # Parse first few entries and check key format
    # Better BibTeX keys are long with camelCase
    entries = self._parse_bibtex_entries(bibtex_content)

    if not entries:
        return False

    # Check first entry
    first_key = entries[0].get('ID', '')

    # Better BibTeX keys are typically 20+ chars
    # Have both upper and lowercase (camelCase)
    return validate_better_bibtex_key(first_key)
```

---

### 3. Testing Strategy

#### Unit Tests

```python
# tests/test_citation_keys.py

def test_citation_key_generation_is_forbidden():
    """Ensure generate_citation_key() raises error."""
    with pytest.raises(RuntimeError, match="Citation key generation is FORBIDDEN"):
        generate_citation_key("Smith", "2024", "Machine Learning")


def test_citation_requires_zotero_key():
    """Ensure Citation class requires key from Zotero."""
    with pytest.raises(ValueError, match="must come from Zotero"):
        Citation(
            authors="Smith",
            year="2024",
            key="smith2024",  # Short key
            zotero_source=False  # Not from Zotero
        )


def test_short_keys_are_rejected():
    """Ensure short keys are rejected."""
    with pytest.raises(ValueError, match="Invalid citation key format"):
        enforce_better_bibtex_key("smith2024")  # Too short


def test_better_bibtex_keys_are_accepted():
    """Ensure proper Better BibTeX keys are accepted."""
    key = "smithMachineLearning2024"
    assert enforce_better_bibtex_key(key) == key


def test_citation_requires_title():
    """Ensure citations must have titles."""
    with pytest.raises(ValueError, match="has no title"):
        Citation(
            authors="Smith",
            year="2024",
            key="smithMachineLearning2024",
            title="",  # Empty title
            zotero_source=True
        )
```

#### Integration Tests

```python
# tests/test_zotero_integration.py

def test_loads_better_bibtex_keys_from_zotero():
    """Ensure Zotero integration loads Better BibTeX keys."""
    zotero = ZoteroIntegration(api_key=API_KEY, library_id=LIBRARY_ID)

    entries = zotero.load_collection("test-collection")

    # Check all keys are Better BibTeX format
    for doi, data in entries.items():
        key = data['key']
        assert validate_better_bibtex_key(key), f"Invalid key format: {key}"
        assert len(key) > 15, f"Key too short: {key}"


def test_fails_if_better_bibtex_not_installed():
    """Ensure system fails gracefully if Better BibTeX not installed."""
    # Mock Zotero response without Better BibTeX keys
    with pytest.raises(RuntimeError, match="Better BibTeX plugin not detected"):
        zotero = ZoteroIntegration(api_key=API_KEY, library_id=LIBRARY_ID)
        zotero._verify_better_bibtex_plugin()
```

#### End-to-End Tests

```python
# tests/test_converter_e2e.py

def test_conversion_preserves_zotero_keys():
    """Ensure full conversion uses Zotero Better BibTeX keys."""
    # Setup
    markdown_content = """
    # Test Paper

    Citation: [Adisorn et al., 2021](https://doi.org/10.3390/en14082289)
    """

    converter = MarkdownToLatexConverter(
        zotero_api_key=API_KEY,
        zotero_library_id=LIBRARY_ID,
        collection_name="dpp-fashion"
    )

    # Convert
    output = converter.convert_string(markdown_content)

    # Verify
    # 1. Check generated .bib file has Better BibTeX keys
    bib_content = output['references.bib']
    assert 'adisornDigitalProductPassport2021' in bib_content
    assert 'adisorn2021' not in bib_content  # Short key should NOT exist

    # 2. Check LaTeX uses same key
    tex_content = output['output.tex']
    assert '\\cite{adisornDigitalProductPassport2021}' in tex_content

    # 3. Compile PDF and verify no (?) citations
    compile_latex(tex_content)
    pdf_content = read_pdf('output.pdf')
    assert '(?)' not in pdf_content
    assert '(Unknown)' not in pdf_content


def test_fails_on_missing_zotero_entries():
    """Ensure conversion fails if citation not in Zotero."""
    markdown_content = """
    Citation: [NonExistent et al., 2099](https://doi.org/10.9999/fake)
    """

    converter = MarkdownToLatexConverter(...)

    with pytest.raises(ValueError, match="Citation not in Zotero collection"):
        converter.convert_string(markdown_content)
```

---

### 4. Documentation Updates

#### Update CLAUDE.md

```markdown
# .claude/CLAUDE.md

## Bibliography Workflow - CRITICAL RULES

### NEVER Generate Citation Keys

**ABSOLUTE RULE**: The code must NEVER generate BibTeX citation keys.

- ❌ `generate_citation_key()` is FORBIDDEN
- ❌ Creating keys from author + year is FORBIDDEN
- ❌ Any form of key generation is FORBIDDEN

**ONLY ALLOWED**: Use Better BibTeX keys from Zotero as-is.

### Better BibTeX Key Format

**Valid**: `adisornDigitalProductPassport2021` (long, descriptive, camelCase)
**Invalid**: `adisorn2021` (short, garbage format)

### Enforcement

If you see:
- Short citation keys (< 15 chars)
- Keys in format `author2024`
- Any call to `generate_citation_key()`

→ This is a CRITICAL BUG and must be fixed immediately.

### Zotero Integration

**Required**:
- Better BibTeX plugin must be installed
- Use `get_collection_bibtex()` NOT `get_collection_items()`
- Parse BibTeX to extract Better BibTeX keys
- Use those keys as-is in generated bibliography

**Verification**:
- Every conversion should verify Better BibTeX plugin is installed
- Every citation should have Better BibTeX key from Zotero
- Every generated .bib file should only have Better BibTeX keys
```

#### Update README

```markdown
# README.md

## Prerequisites

### Required: Better BibTeX Plugin

deep-biblio-tools requires the Better BibTeX plugin for Zotero.

**Install**:
1. Download from https://retorque.re/zotero-better-bibtex/
2. In Zotero: Tools → Add-ons → Install Add-on From File
3. Restart Zotero

**Why required**: Better BibTeX generates descriptive citation keys
(e.g., `smithMachineLearning2024`) instead of short keys (e.g., `smith2024`).

The converter uses these keys to maintain consistency between your Zotero
collection and generated bibliographies.

### Configure Better BibTeX

Recommended settings in Zotero → Preferences → Better BibTeX:

- **Citation Key Format**: `[auth][shorttitle][year]`
- **Auto-export**: Enabled (optional but recommended)

See docs/architecture/bibtex-key-formats.md for details.
```

---

### 5. CI/CD Checks

#### Pre-commit Hook

```bash
# .pre-commit-config.yaml

repos:
  - repo: local
    hooks:
      - id: check-citation-key-generation
        name: Check for forbidden citation key generation
        entry: python scripts/check_key_generation.py
        language: system
        files: 'src/.*\.py$'
```

```python
# scripts/check_key_generation.py

"""Check that code doesn't generate citation keys."""

import sys
from pathlib import Path

FORBIDDEN_PATTERNS = [
    "generate_citation_key(",
    "f\"{author}{year}\"",
    "f'{author}{year}'",
    "regenerate_key",
]

ALLOWED_FILES = [
    "tests/test_deprecated_key_generation.py",  # Tests that it's forbidden
]


def check_file(filepath: Path) -> list[str]:
    """Check file for forbidden patterns."""
    if str(filepath) in ALLOWED_FILES:
        return []

    violations = []
    content = filepath.read_text()

    for line_num, line in enumerate(content.split('\n'), 1):
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in line and not line.strip().startswith('#'):
                violations.append(
                    f"{filepath}:{line_num}: Forbidden citation key generation: {pattern}"
                )

    return violations


def main():
    src_files = Path('src').rglob('*.py')

    all_violations = []
    for filepath in src_files:
        violations = check_file(filepath)
        all_violations.extend(violations)

    if all_violations:
        print("❌ FORBIDDEN: Citation key generation detected!")
        print("\nViolations:")
        for violation in all_violations:
            print(f"  {violation}")
        print("\nCitation keys must come from Zotero Better BibTeX ONLY.")
        print("See: docs/architecture/bibtex-key-formats.md")
        sys.exit(1)

    print("✅ No citation key generation detected")
    sys.exit(0)


if __name__ == '__main__':
    main()
```

#### GitHub Actions

```yaml
# .github/workflows/validate-citations.yml

name: Validate Citation Key Handling

on: [push, pull_request]

jobs:
  check-key-generation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Check for citation key generation
        run: python scripts/check_key_generation.py

      - name: Run citation key tests
        run: |
          uv run pytest tests/test_citation_keys.py -v
```

---

### 6. Runtime Monitoring

#### Logging

```python
# Add to citation_manager.py

import logging

logger = logging.getLogger(__name__)

class Citation:
    def __init__(self, ..., key: str, zotero_source: bool = True):
        # Log all key assignments
        logger.info(
            f"Citation created: key={key}, "
            f"zotero_source={zotero_source}, "
            f"length={len(key)}"
        )

        # Validate
        if not validate_better_bibtex_key(key):
            logger.error(
                f"INVALID KEY FORMAT: '{key}' - "
                f"Expected Better BibTeX format"
            )
            raise ValueError(f"Invalid citation key format: {key}")

        self.key = key
```

#### Metrics

```python
# Track citation key sources

class CitationMetrics:
    def __init__(self):
        self.total_citations = 0
        self.from_zotero = 0
        self.invalid_keys = 0
        self.short_keys = 0

    def record_citation(self, citation: Citation):
        self.total_citations += 1

        if citation.zotero_source:
            self.from_zotero += 1

        if not validate_better_bibtex_key(citation.key):
            self.invalid_keys += 1

        if len(citation.key) < 15:
            self.short_keys += 1

    def report(self):
        print(f"\n{'='*60}")
        print("Citation Key Metrics")
        print(f"{'='*60}")
        print(f"Total citations:     {self.total_citations}")
        print(f"From Zotero:         {self.from_zotero} ({self.from_zotero/self.total_citations*100:.1f}%)")
        print(f"Invalid key format:  {self.invalid_keys}")
        print(f"Short keys (< 15):   {self.short_keys}")

        if self.invalid_keys > 0 or self.short_keys > 0:
            print(f"\n⚠️  WARNING: Found {self.invalid_keys + self.short_keys} problematic keys")
        else:
            print(f"\n✅ All keys are valid Better BibTeX format")
        print(f"{'='*60}\n")
```

---

## Implementation Plan

### Phase 1: Immediate Fixes (1-2 hours)

#### Step 1.1: Disable Key Generation

```python
# src/converters/md_to_latex/utils.py

def generate_citation_key(*args, **kwargs):
    """DEPRECATED - DO NOT USE.

    Raises:
        RuntimeError: Always
    """
    raise RuntimeError(
        "Citation key generation is FORBIDDEN. "
        "Keys must come from Zotero Better BibTeX only."
    )
```

#### Step 1.2: Update Citation Class

```python
# src/converters/md_to_latex/citation_manager.py

class Citation:
    def __init__(
        self,
        authors: str,
        year: str,
        key: str,  # Required
        url: str,
        **kwargs
    ):
        # Validate key
        if not key:
            raise ValueError("Citation key required (from Zotero)")

        if not validate_better_bibtex_key(key):
            raise ValueError(f"Invalid key format: {key}")

        self.key = key
        self.authors = authors
        self.year = year
        self.url = url
        # ... rest of init
```

#### Step 1.3: Update Zotero Integration

```python
# src/converters/md_to_latex/zotero_integration.py

def load_collection_with_keys(self, collection_name: str) -> dict:
    """Load collection with Better BibTeX keys.

    Returns:
        dict: {DOI: {key: str, metadata: dict}}
    """
    # Get BibTeX export
    bibtex_content = self.get_collection_bibtex(collection_name)

    # Parse entries
    entries = bibtexparser.loads(bibtex_content).entries

    # Build mapping
    doi_to_key = {}
    for entry in entries:
        doi = entry.get('doi', '').strip()
        key = entry.get('ID', '').strip()

        if doi and key:
            doi_to_key[doi] = {
                'key': key,
                'metadata': entry
            }

    return doi_to_key
```

---

### Phase 2: Integration (2-3 hours)

#### Step 2.1: Update Converter Flow

```python
# src/converters/md_to_latex/converter.py

class MarkdownToLatexConverter:
    def convert(self, markdown_path: str):
        # 1. Load Zotero collection with Better BibTeX keys
        zotero_entries = self.zotero.load_collection_with_keys(self.collection_name)

        # 2. Extract citations from markdown
        citations = self.citation_extractor.extract(markdown_content)

        # 3. Match citations to Zotero entries
        for citation in citations:
            doi = citation.url  # Simplified

            if doi not in zotero_entries:
                raise ValueError(
                    f"Citation not in Zotero: {citation.authors} ({citation.year})\n"
                    f"DOI: {doi}\n"
                    f"Add to Zotero collection '{self.collection_name}' first."
                )

            # Use Better BibTeX key from Zotero
            zotero_data = zotero_entries[doi]
            citation.key = zotero_data['key']
            citation.metadata = zotero_data['metadata']

        # 4. Generate BibTeX with Zotero keys
        self._write_bibliography(citations)
```

---

### Phase 3: Testing (1-2 hours)

#### Step 3.1: Unit Tests

Create `tests/test_citation_keys.py` with tests from Testing Strategy section above.

#### Step 3.2: Integration Tests

Create `tests/test_zotero_integration.py` with Zotero integration tests.

#### Step 3.3: End-to-End Tests

Create `tests/test_converter_e2e.py` with full conversion tests.

---

### Phase 4: Documentation (1 hour)

#### Step 4.1: Update CLAUDE.md

Add Better BibTeX key rules to `.claude/CLAUDE.md`

#### Step 4.2: Update README

Add Better BibTeX plugin requirement to README.md

#### Step 4.3: Create Migration Guide

```markdown
# docs/migration-to-better-bibtex.md

# Migration Guide: Better BibTeX Keys

## For Existing Projects

If you have existing projects with short citation keys:

### Step 1: Install Better BibTeX Plugin

See README.md for installation instructions.

### Step 2: Configure Better BibTeX

In Zotero → Preferences → Better BibTeX:
- Citation Key Format: `[auth][shorttitle][year]`

### Step 3: Regenerate Keys

In Zotero:
1. Select all items in collection
2. Right-click → Better BibTeX → Refresh BibTeX Key

### Step 4: Re-run Conversion

```bash
deep-biblio-md2latex paper.md --collection your-collection
```

The converter will now use the new Better BibTeX keys.

### Step 5: Update LaTeX Files

Replace old short keys with new Better BibTeX keys in .tex files:

```bash
# Use provided migration script
python scripts/migrate_citation_keys.py paper.tex
```
```

---

### Phase 5: CI/CD (30 minutes)

#### Step 5.1: Add Pre-commit Hook

Create `.pre-commit-config.yaml` as shown in CI/CD Checks section.

#### Step 5.2: Add GitHub Action

Create `.github/workflows/validate-citations.yml` as shown above.

---

## Questions for OpenAI

Given this comprehensive context, we need expert advice on:

### 1. Architecture Questions

**Q1**: Is the proposed architecture (BibTeX export → parse keys → map to DOIs) the best approach?

**Alternative approaches**:
- A: Use Zotero's search API to look up each citation individually
- B: Maintain a local cache of Zotero collection (synced periodically)
- C: Use Better BibTeX's own API endpoints (if they exist)

**Q2**: Should we require Better BibTeX plugin, or provide fallback?

**Current plan**: Require it (fail if not installed)

**Alternative**: Support both Better BibTeX keys AND standard keys, detect which is available

### 2. Error Handling Questions

**Q3**: What should happen when citation is NOT in Zotero?

**Options**:
- A: Fail immediately (current plan)
- B: Auto-add to Zotero via API (if metadata found on CrossRef/arXiv)
- C: Allow user to approve missing citations interactively
- D: Generate warning but continue (create entry in .bib but flag for review)

**Q4**: How to handle citations with valid DOI but no Zotero entry?

**Current**: Raise error

**Alternative**: Offer to add to Zotero automatically:
```
Citation not in Zotero: Adisorn et al. (2021)
DOI: 10.3390/en14082289
Metadata found on CrossRef.

Add to Zotero? [y/N]
```

### 3. Testing Questions

**Q5**: How to test Zotero integration without real API calls?

**Options**:
- A: Mock pyzotero responses
- B: Use test Zotero collection with known data
- C: Record/replay HTTP interactions with VCR.py
- D: Combination of above

**Q6**: What's the minimum test coverage for robustness?

**Current plan**: Unit tests + integration tests + E2E tests

**Additional ideas**: Property-based testing? Fuzzing?

### 4. Robustness Questions

**Q7**: How to prevent regression back to key generation?

**Current plan**:
- Code guards (raise errors)
- Unit tests
- Pre-commit hooks
- GitHub Actions
- Documentation

**Is this sufficient?** What else?

**Q8**: How to handle race conditions / stale data?

**Scenario**: Zotero collection updated between:
1. Loading collection
2. Converting document

**Current**: No handling

**Options**:
- A: Add timestamp checking
- B: Lock collection during conversion
- C: Accept eventual consistency
- D: Warn user if collection modified during conversion

### 5. Performance Questions

**Q9**: BibTeX parsing vs CSL JSON - performance implications?

**Current plan**: Parse entire BibTeX export for every conversion

**Concerns**:
- Large collections (1000+ entries) → slow parsing
- Multiple conversions → repeated parsing

**Alternatives**:
- Cache parsed BibTeX
- Use CSL JSON for metadata, separate call for keys
- Index collection for faster lookups

**Q10**: How to optimize for large collections?

**Current**: Load entire collection into memory

**Alternatives**:
- Lazy loading (load only needed entries)
- Persistent cache (SQLite database?)
- Incremental updates

### 6. User Experience Questions

**Q11**: How to make Better BibTeX requirement user-friendly?

**Current**: Hard requirement, fail if not installed

**Better UX**:
- Auto-detect if not installed
- Provide clear installation instructions
- Link to detailed setup guide
- Check on first run, cache result

**Q12**: How to handle multi-collection scenarios?

**Current**: Single collection per conversion

**Use case**: Paper cites from multiple collections

**Options**:
- A: Support multiple collections (combine all entries)
- B: Primary + fallback collections
- C: Entire library (no collection filter)

### 7. Maintenance Questions

**Q13**: How to keep enforcement mechanisms synchronized?

**Components**:
- Code guards
- Tests
- Pre-commit hooks
- GitHub Actions
- Documentation

**Risk**: One updated, others forgotten

**Solution**?

**Q14**: How to document "why" this architecture?

**Current**: This document

**Maintenance**: How to ensure future devs understand reasoning and don't break it?

---

## Additional Context for OpenAI

### Project Goals

**Primary**: Convert LLM-generated markdown academic papers to LaTeX with zero manual bibliography editing.

**Secondary**:
- Validate all citations against authoritative sources
- Detect and report hallucinated author names
- Maintain single source of truth (Zotero)
- Produce publication-ready PDFs

### Constraints

1. **LLMs hallucinate**: Cannot trust author names from LLM output
2. **APIs are slow**: CrossRef/arXiv rate limits
3. **Zotero is truth**: User's Zotero collection is authoritative
4. **Better BibTeX is standard**: User already uses it for other work
5. **Must be deterministic**: Same input → same output always

### Non-Goals

- Supporting other reference managers (Mendeley, EndNote, etc.)
- Supporting other citation key formats
- Real-time collaborative editing
- Web-based GUI

### Technology Stack

- **Language**: Python 3.11+
- **Zotero API**: pyzotero library
- **BibTeX parsing**: bibtexparser library
- **Markdown parsing**: markdown-it-py
- **LaTeX generation**: Custom code + pylatexenc
- **Testing**: pytest
- **CI/CD**: GitHub Actions

### Related Documentation

- `docs/architecture/bibtex-key-formats.md` - Better BibTeX strategy (foundational)
- `docs/usage/zotero-setup-guide.md` - Setup instructions
- `.claude/CLAUDE.md` - Development guidelines
- `docs/zotero-api-integration-complete.md` - API integration notes
- `docs/plea-to-openai-robust-matching.md` - Citation matching strategies

---

## Success Criteria

### Before Declaring "Fixed"

1. ✅ Zero citation key generation in codebase
2. ✅ All tests pass (unit + integration + E2E)
3. ✅ Pre-commit hooks prevent regressions
4. ✅ GitHub Actions validate on every commit
5. ✅ Documentation updated
6. ✅ Full conversion produces ONLY Better BibTeX keys
7. ✅ Conversion fails gracefully if citation not in Zotero
8. ✅ Better BibTeX plugin verified on startup
9. ✅ All entries have complete metadata (no "Unknown" or empty)
10. ✅ PDF compiles with zero (?) citations

### Verification Commands

```bash
# 1. Check no key generation in code
git grep "generate_citation_key" src/
# Should only show: "raise RuntimeError"

# 2. Run all tests
uv run pytest tests/ -v

# 3. Run validation
python scripts/check_key_generation.py

# 4. Test full conversion
deep-biblio-md2latex test_paper.md --collection dpp-fashion

# 5. Verify output
python scripts/validate_bib_source.py output/references.bib

# 6. Check all keys are Better BibTeX format
python scripts/check_key_lengths.py output/references.bib
# Should show: All keys >= 15 chars

# 7. Compile and verify PDF
cd output && pdflatex paper.tex && bibtex paper && pdflatex paper.tex
# PDF should have zero (?) citations
```

---

## Appendix: Code Locations

### Files Needing Changes

| File | Changes Needed | Priority |
|------|----------------|----------|
| `src/converters/md_to_latex/utils.py:510` | Make `generate_citation_key()` raise error | CRITICAL |
| `src/converters/md_to_latex/citation_manager.py:64-66` | Remove key generation, require key from Zotero | CRITICAL |
| `src/converters/md_to_latex/citation_manager.py:69-76` | Remove `regenerate_key_with_title()` | CRITICAL |
| `src/converters/md_to_latex/citation_manager.py:556-566` | Remove post-enrichment key regeneration | CRITICAL |
| `src/converters/md_to_latex/zotero_integration.py:78` | Add `load_collection_with_keys()` method | HIGH |
| `src/converters/md_to_latex/converter.py` | Update to use Zotero keys from BibTeX export | HIGH |
| `src/converters/md_to_latex/citation_manager.py` | Add Better BibTeX key validation | MEDIUM |
| `.claude/CLAUDE.md` | Document Better BibTeX key rules | MEDIUM |
| `README.md` | Add Better BibTeX plugin requirement | MEDIUM |

### New Files Needed

| File | Purpose | Priority |
|------|---------|----------|
| `tests/test_citation_keys.py` | Unit tests for key validation | HIGH |
| `tests/test_zotero_integration.py` | Zotero integration tests | HIGH |
| `tests/test_converter_e2e.py` | End-to-end conversion tests | HIGH |
| `scripts/check_key_generation.py` | Pre-commit hook script | MEDIUM |
| `.pre-commit-config.yaml` | Pre-commit configuration | MEDIUM |
| `.github/workflows/validate-citations.yml` | GitHub Actions workflow | MEDIUM |
| `docs/migration-to-better-bibtex.md` | Migration guide | LOW |

---

## Summary

**The Core Problem**: Code generates citation keys instead of using Better BibTeX keys from Zotero.

**The Core Solution**: Stop all key generation. Use Zotero as single source of truth.

**The Core Enforcement**: Code guards + tests + CI/CD + documentation.

**The Open Questions**: See "Questions for OpenAI" section for architectural decisions and robustness advice.

---

**Document Status**: ✅ Complete
**Next Step**: Review with OpenAI for architectural advice and robustness recommendations
**Revision Date**: 2025-10-28
