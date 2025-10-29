# Synthesized Auto-Add Implementation Plan
## Critical Assessment of OpenAI Plan + Original Plan

**Date**: 2025-10-29
**Status**: Ready for Implementation

---

## Executive Summary

This document synthesizes the OpenAI-generated plan with our original plan, correcting critical misunderstandings about Zotero APIs while preserving the excellent validation logic, testing strategy, and guardrails from both approaches.

---

## Critical Issues in OpenAI Plan

### 1. **CRITICAL: Zotero API Misunderstanding** ❌

**OpenAI's Assumption**:
```python
# WRONG - This endpoint doesn't exist!
TRANSLATION_ENDPOINT = "/users/{user_id}/items"  # POST with url to translate
```

**Reality**: Zotero Web API has TWO separate services:

1. **Zotero Web API** (`https://api.zotero.org/users/{id}/items`)
   - Purpose: CRUD operations on Zotero library items
   - POST requires: Complete item JSON with all metadata fields
   - Does NOT accept URL and magically fetch metadata

2. **Zotero Translation Server** (separate service)
   - Default: `http://localhost:1969` (requires separate installation)
   - Purpose: URL → metadata translation
   - POST `{url: "https://..."}` → returns item JSON
   - Requires: Running `zotero/translation-server` Docker container OR Node.js app

**Our Solution**: Use Translation Server (separate service) to fetch metadata, then POST complete item to Web API.

### 2. **CRITICAL: Better BibTeX Key Retrieval** ⚠️

**OpenAI's Assumption**:
```python
# Partially correct but incomplete
bibtex = self._get_item_bibtex(item_key)  # ?format=bibtex
better_bibtex_key = self._extract_bibtex_key(bibtex)
```

**Reality**:
- `?format=bibtex` returns ZOTERO keys (e.g., `smith2024`)
- Better BibTeX keys (e.g., `smithMachineLearning2024`) come from Better BibTeX plugin
- Better BibTeX plugin stores keys in item's `extra` field OR generates them on-the-fly during export

**Our Solution**:
1. After adding item to Zotero, wait briefly for Better BibTeX sync
2. Re-fetch entire collection BibTeX export (includes Better BibTeX keys)
3. OR: Use collection export endpoint which triggers Better BibTeX key generation

### 3. **Dependency Bloat** ⚠️

**OpenAI adds**:
- `tldextract` (for domain extraction)
- `idutils` (mentioned but not used)

**Our codebase already has**:
- `urllib.parse` (can extract domains)
- DOI extraction logic in `utils.py`

**Our Solution**: Use stdlib `urllib.parse.urlparse()` for domain extraction, no new dependencies.

### 4. **SQLite Caching Complexity** ⚠️

**OpenAI**: Full SQLite implementation with schema, connection management, etc.

**Trade-off**:
- ✅ Good: Persistent cache across runs
- ❌ Bad: Adds complexity, file management, migration concerns
- ❌ Bad: May cache stale/incorrect metadata

**Our Solution**: Start with in-memory dict cache (simple), add SQLite later if needed.

### 5. **DOI Validation Performance** ⚠️

**OpenAI**: HEAD request to `https://doi.org/{doi}` for EVERY entry

**Problem**:
- Network call per validation = slow
- Rate limiting risk
- Unnecessary for most entries

**Our Solution**: Make DOI validation optional/async, log warnings instead of blocking.

---

## What OpenAI Got RIGHT ✅

### 1. **Excellent Validation Logic**
```python
def _validate_entry(self, metadata: Dict[str, Any]) -> Tuple[bool, List[str]]:
    # Check title, authors, year, DOI, truncation patterns
    # Return (is_valid, list_of_issues)
```
**Keep**: This structure with severity levels (CRITICAL vs WARNING)

### 2. **Comprehensive Test Suite**
- Unit tests for validation logic
- Mocked network calls
- Integration tests with full pipeline
- Grouping by status in reports

**Keep**: All test structure and mocking patterns

### 3. **Guardrails and Audit Trail**
- `dry_run` mode
- `max_auto_add` threshold
- Detailed `audit` list tracking every action
- `generate_report()` with grouping

**Keep**: All of these!

### 4. **Retry Logic with Backoff**
```python
for attempt in range(attempts):
    try:
        # ... network call ...
    except RequestException:
        time.sleep(delay_secs)
        delay_secs *= 2.0
```
**Keep**: Exponential backoff for robustness

### 5. **Author Fallback from Site**
```python
if not metadata.get("creators"):
    author_from_site = extract_author_from_url(url)
```
**Keep**: Site-to-author mapping for sources like BBC, Bloomberg

---

## Synthesized Architecture

### Phase 1: Translation Server Integration

**File**: `src/converters/md_to_latex/translation_client.py`

```python
class TranslationClient:
    """Client for Zotero translation-server (separate service)."""

    def __init__(self, server_url: str = "http://localhost:1969"):
        self.server_url = server_url
        self.session = requests.Session()
        self.cache: dict[str, dict[str, Any]] = {}  # In-memory cache

    def translate_url(self, url: str, retry: bool = True) -> dict[str, Any] | None:
        """Fetch metadata from URL using translation-server.

        Returns:
            Zotero item JSON (with itemType, title, creators, etc.)
            None if translation failed
        """
        # Check cache
        if url in self.cache:
            return self.cache[url]

        # POST to translation server
        attempts = 3 if retry else 1
        delay = 1.0

        for attempt in range(attempts):
            try:
                resp = self.session.post(
                    f"{self.server_url}/web",
                    json=url,  # Translation server expects raw URL string as JSON
                    headers={"Content-Type": "text/plain"},
                    timeout=10
                )

                if resp.status_code == 300:
                    # Multiple translators available - use first
                    options = resp.json()
                    # Select best translator and retry with session ID
                    # (implementation details here)
                    pass

                elif resp.status_code == 200:
                    items = resp.json()
                    if items and len(items) > 0:
                        metadata = items[0]
                        self.cache[url] = metadata
                        return metadata

                else:
                    logger.warning(f"Translation failed: HTTP {resp.status_code}")

            except requests.RequestException as exc:
                logger.debug(f"Translation attempt {attempt + 1} failed: {exc}")
                time.sleep(delay)
                delay *= 2.0

        return None
```

**Key Differences from OpenAI**:
- Correct endpoint: `POST /web` to translation-server, NOT Web API
- Handles translation-server's multi-translator protocol (HTTP 300)
- Simple in-memory cache (not SQLite)

### Phase 2: Entry Validation

**File**: `src/converters/md_to_latex/entry_validator.py`

```python
class EntryValidator:
    """Validates Zotero item metadata quality."""

    def validate(self, metadata: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate entry and return (is_valid, issues).

        Issues are classified as:
        - CRITICAL: Entry should not be added
        - WARNING: Entry can be added but has issues
        """
        issues: list[str] = []

        # 1. Title checks
        title = metadata.get("title", "")
        if not title:
            issues.append("CRITICAL: Title missing")
            return False, issues

        if len(title) < 10:
            issues.append("CRITICAL: Title suspiciously short")
            return False, issues

        # Detect truncation patterns
        truncation_markers = [
            "Added from URL:",
            "...",
            "[truncated]",
            "Implementation plan"  # Garbage from CRIS system
        ]
        for marker in truncation_markers:
            if marker in title:
                issues.append(f"CRITICAL: Title contains truncation marker '{marker}'")
                return False, issues

        # 2. Author/Creator checks
        creators = metadata.get("creators", [])
        if not creators or len(creators) == 0:
            issues.append("WARNING: No creators/authors present")
        else:
            # Check for incomplete names
            for creator in creators:
                last_name = creator.get("lastName", "")
                if not last_name:
                    issues.append("WARNING: Creator missing lastName field")

        # 3. Year checks
        date = metadata.get("date", "")
        year = self._extract_year(date)
        if year:
            if year < 1900 or year > 2030:
                issues.append(f"WARNING: Year {year} outside expected range")
        else:
            issues.append("WARNING: No valid year found in date field")

        # 4. DOI checks (non-blocking)
        doi = metadata.get("DOI") or metadata.get("doi")
        if doi:
            # Just validate format, don't do network call
            if not doi.startswith("10."):
                issues.append(f"WARNING: DOI '{doi}' has unusual format")

        # 5. ItemType checks
        item_type = metadata.get("itemType", "")
        if item_type == "webpage" and not creators:
            issues.append("WARNING: Webpage entry without author (extract from site name)")

        return True, issues

    def _extract_year(self, date_str: str) -> int | None:
        """Extract 4-digit year from date string without regex."""
        if not date_str:
            return None

        # Split by common separators
        tokens = date_str.replace("-", " ").replace("/", " ").split()

        for token in tokens:
            if len(token) == 4 and token.isdigit():
                return int(token)

        return None
```

**Key Differences from OpenAI**:
- No DOI network validation (too slow, optional feature)
- More specific truncation detection based on October 26 incident
- Webpage-specific validation logic

### Phase 3: Site Author Mapping

**File**: `src/converters/md_to_latex/site_author_mapping.py`

```python
from urllib.parse import urlparse

# Domain → Author/Publisher mapping
SITE_AUTHOR_MAPPINGS = {
    "bbc.com": "BBC",
    "bbc.co.uk": "BBC",
    "bloomberg.com": "Bloomberg",
    "reuters.com": "Reuters",
    "europa.eu": "European Commission",
    "europarl.europa.eu": "European Parliament",
    "hmfoundation.com": "H&M Foundation",
    "gs1.eu": "GS1 Europe",
    "wbcsd.org": "World Business Council for Sustainable Development",
    # Add more as needed
}

def extract_domain(url: str) -> str | None:
    """Extract domain from URL using urllib.parse (no dependencies)."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Remove 'www.' prefix
        if domain.startswith("www."):
            domain = domain[4:]

        return domain
    except Exception:
        return None

def extract_author_from_url(url: str) -> str | None:
    """Map URL domain to author/publisher name."""
    domain = extract_domain(url)
    if not domain:
        return None

    # Direct lookup
    if domain in SITE_AUTHOR_MAPPINGS:
        return SITE_AUTHOR_MAPPINGS[domain]

    # Fallback: check if any key is suffix of domain
    # (handles subdomains like "ec.europa.eu")
    for known_domain, author in SITE_AUTHOR_MAPPINGS.items():
        if domain.endswith(known_domain):
            return author

    return None

def augment_metadata_with_site_author(metadata: dict[str, Any], url: str) -> dict[str, Any]:
    """Add author from site name if missing."""
    if metadata.get("creators"):
        return metadata  # Already has authors

    site_author = extract_author_from_url(url)
    if site_author:
        metadata["creators"] = [
            {"creatorType": "author", "lastName": site_author}
        ]

    return metadata
```

**Key Differences from OpenAI**:
- Uses stdlib `urllib.parse` instead of `tldextract`
- Handles subdomains correctly (e.g., ec.europa.eu)
- Simpler fallback logic

### Phase 4: Auto-Add Integration

**File**: `src/converters/md_to_latex/zotero_auto_add.py`

```python
class ZoteroAutoAdd:
    """Automatically add missing citations to Zotero with quality validation."""

    def __init__(
        self,
        zotero_client: ZoteroClient,
        collection_name: str,
        translation_server_url: str = "http://localhost:1969",
        dry_run: bool = False,
        max_auto_add: int = 50
    ):
        self.zotero_client = zotero_client
        self.collection_name = collection_name
        self.translation_client = TranslationClient(translation_server_url)
        self.validator = EntryValidator()
        self.dry_run = dry_run
        self.max_auto_add = max_auto_add

        self.audit: list[dict[str, Any]] = []
        self.added_count = 0

    def add_citation(
        self,
        url: str,
        citation_text: str
    ) -> tuple[str | None, list[str]]:
        """Attempt to auto-add URL to Zotero collection.

        Returns:
            (better_bibtex_key_or_none, warnings)
        """
        warnings: list[str] = []

        # Guardrail: check threshold
        if self.added_count >= self.max_auto_add:
            warning = f"Hit max_auto_add threshold ({self.max_auto_add}). Skipping."
            warnings.append(warning)
            self._record_audit(url, "threshold_exceeded", warnings)
            return None, warnings

        # Step 1: Fetch metadata from translation server
        logger.info(f"Translating URL: {url}")
        metadata = self.translation_client.translate_url(url)

        if not metadata:
            warnings.append("Translation server failed or returned no metadata")
            self._record_audit(url, "translation_failed", warnings)
            return None, warnings

        # Step 2: Augment with site author if missing
        metadata = augment_metadata_with_site_author(metadata, url)
        if not metadata.get("creators"):
            # Still no author after augmentation
            warnings.append("No author available from translation or site mapping")
            metadata["creators"] = [{"creatorType": "author", "lastName": "Unknown"}]

        # Step 3: Validate quality
        is_valid, issues = self.validator.validate(metadata)
        warnings.extend(issues)

        if not is_valid:
            self._record_audit(url, "validation_failed", warnings, metadata)
            return None, warnings

        # Step 4: Add to Zotero (or simulate if dry_run)
        if self.dry_run:
            fake_key = f"dryrun_{int(time.time())}"
            self._record_audit(url, "dry_run_added", warnings, metadata, fake_key)
            return fake_key, warnings

        try:
            # Add item to collection
            item_key = self._add_to_zotero_collection(metadata)
            self.added_count += 1

            # Wait briefly for Better BibTeX sync (if plugin installed)
            time.sleep(0.5)

            # Fetch Better BibTeX key by re-loading collection
            better_bibtex_key = self._get_better_bibtex_key_for_item(item_key)

            self._record_audit(url, "added", warnings, metadata, better_bibtex_key)
            return better_bibtex_key, warnings

        except Exception as exc:
            error_msg = f"Failed to add to Zotero: {exc}"
            warnings.append(error_msg)
            self._record_audit(url, "add_failed", warnings, metadata)
            return None, warnings

    def _add_to_zotero_collection(self, metadata: dict[str, Any]) -> str:
        """POST item to Zotero and add to collection."""
        # Find collection ID
        collection_id = self.zotero_client._find_collection_id(self.collection_name)
        if not collection_id:
            raise ValueError(f"Collection '{self.collection_name}' not found")

        # POST item to /users/{id}/items
        url = f"{self.zotero_client.base_url}/{self.zotero_client.library_type}s/{self.zotero_client.library_id}/items"

        headers = {
            "Zotero-API-Key": self.zotero_client.api_key,
            "Content-Type": "application/json"
        }

        # Wrap in array (Zotero API accepts multiple items)
        payload = [metadata]

        resp = requests.post(url, json=payload, headers=headers, timeout=15)

        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Zotero API returned {resp.status_code}: {resp.text[:200]}")

        # Parse response to get item key
        result = resp.json()
        if "successful" in result and "0" in result["successful"]:
            item_data = result["successful"]["0"]
            item_key = item_data["key"]
        else:
            raise RuntimeError(f"Could not parse item key from response: {result}")

        # Add to collection
        collection_url = f"{url}/{item_key}/collections"
        resp = requests.post(
            collection_url,
            json=[collection_id],
            headers=headers,
            timeout=10
        )

        if resp.status_code not in (200, 204):
            logger.warning(f"Failed to add item to collection: {resp.status_code}")

        return item_key

    def _get_better_bibtex_key_for_item(self, item_key: str) -> str:
        """Fetch Better BibTeX key by re-exporting collection.

        This is necessary because Better BibTeX keys are generated by the
        plugin and not immediately available via API.
        """
        # Re-fetch collection BibTeX export
        bibtex_content = self.zotero_client.get_collection_bibtex(self.collection_name)

        # Parse to find entry with matching Zotero key
        # (This is inefficient but only happens once per add)
        parser = bibtexparser.bparser.BibTexParser()
        bib_db = bibtexparser.loads(bibtex_content, parser=parser)

        # Try to find entry by checking 'note' or 'file' fields for Zotero key
        # (Better BibTeX includes Zotero key in exported fields)
        for entry in bib_db.entries:
            # Heuristic: use most recently added entry's cite key
            # (assumes entries are in reverse chronological order)
            return entry["ID"]

        # Fallback: return Zotero key
        return item_key

    def _record_audit(
        self,
        url: str,
        status: str,
        warnings: list[str],
        metadata: dict[str, Any] | None = None,
        key: str | None = None
    ):
        """Record action in audit trail."""
        entry = {
            "url": url,
            "status": status,
            "warnings": warnings,
            "metadata_sample": {
                "title": metadata.get("title") if metadata else None,
                "itemType": metadata.get("itemType") if metadata else None
            },
            "key": key,
            "timestamp": time.time()
        }
        self.audit.append(entry)
        logger.info(f"Audit: {status} {url} {warnings}")

    def generate_report(self) -> str:
        """Generate human-readable report grouped by status."""
        added = [a for a in self.audit if a["status"] == "added"]
        dry_run = [a for a in self.audit if a["status"] == "dry_run_added"]
        failed = [a for a in self.audit if a["status"] in (
            "translation_failed", "validation_failed", "add_failed", "threshold_exceeded"
        )]
        with_warnings = [a for a in self.audit if a["warnings"]]

        lines = []
        lines.append("=" * 60)
        lines.append("CITATION AUTO-ADD REPORT")
        lines.append("=" * 60)
        lines.append(f"Total processed: {len(self.audit)}")
        lines.append(f"Successfully added: {len(added)}")
        lines.append(f"Dry-run simulated: {len(dry_run)}")
        lines.append(f"Failed: {len(failed)}")
        lines.append(f"With warnings: {len(with_warnings)}")
        lines.append("")

        if added:
            lines.append("✅ SUCCESSFULLY ADDED:")
            for a in added:
                lines.append(f"  - {a['url']}")
                lines.append(f"    Key: {a['key']}")
                if a['warnings']:
                    lines.append(f"    Warnings: {', '.join(a['warnings'])}")
            lines.append("")

        if with_warnings and len(with_warnings) > len(added):
            lines.append("⚠️  ADDED WITH WARNINGS:")
            warned_only = [a for a in with_warnings if a["status"] not in ("added", "dry_run_added")]
            for a in warned_only:
                lines.append(f"  - {a['url']}: {a['status']}")
                lines.append(f"    {', '.join(a['warnings'])}")
            lines.append("")

        if failed:
            lines.append("❌ FAILED TO ADD:")
            for a in failed:
                lines.append(f"  - {a['url']}: {a['status']}")
                if a['warnings']:
                    lines.append(f"    {', '.join(a['warnings'])}")
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)
```

**Key Differences from OpenAI**:
- Uses our existing `ZoteroClient` instead of reinventing
- Correct Zotero Web API usage (POST items, then add to collection)
- Better BibTeX key retrieval uses collection re-export (correct approach)
- More realistic error handling

---

## Integration with CitationManager

**File**: `src/converters/md_to_latex/converter.py` (modifications)

```python
class MarkdownToLatexConverter:
    def __init__(self, ..., auto_add_enabled: bool = True):
        # ... existing init ...

        # Initialize auto-add if enabled
        self.auto_add_enabled = auto_add_enabled and self.zotero_client
        if self.auto_add_enabled:
            self.zotero_auto_add = ZoteroAutoAdd(
                zotero_client=self.zotero_client,
                collection_name=self.collection_name,
                dry_run=False,  # Set via env var or CLI flag
                max_auto_add=50  # Configurable threshold
            )
        else:
            self.zotero_auto_add = None

    def _match_citation_to_zotero(self, citation: Citation) -> str | None:
        """Match citation to Zotero or auto-add if missing."""
        # Existing matching logic ...
        key = self.citation_manager.match_to_zotero(citation)

        if key:
            return key

        # NEW: Auto-add if enabled
        if self.zotero_auto_add and citation.url:
            logger.info(f"Citation not in Zotero, attempting auto-add: {citation.url}")
            key, warnings = self.zotero_auto_add.add_citation(
                citation.url,
                citation.text
            )

            if key:
                logger.info(f"Successfully auto-added: {citation.url} → {key}")
                if warnings:
                    for warning in warnings:
                        logger.warning(f"  {warning}")
                return key
            else:
                logger.warning(f"Failed to auto-add: {citation.url}")
                for warning in warnings:
                    logger.warning(f"  {warning}")

        # Fallback to Temp key
        return self.citation_manager.create_temp_key(citation)

    def convert(self, ...) -> ConversionResult:
        # ... existing conversion logic ...

        # At end, generate auto-add report if used
        if self.zotero_auto_add and len(self.zotero_auto_add.audit) > 0:
            report = self.zotero_auto_add.generate_report()
            report_path = self.output_dir / "auto_add_report.txt"
            report_path.write_text(report)
            logger.info(f"Auto-add report written to: {report_path}")
```

---

## Testing Strategy

### Unit Tests

**File**: `tests/unit/test_entry_validator.py`
```python
import pytest
from src.converters.md_to_latex.entry_validator import EntryValidator

def test_valid_entry():
    validator = EntryValidator()
    metadata = {
        "title": "Burberry burns bags, clothes and perfume worth millions",
        "creators": [{"creatorType": "author", "lastName": "BBC"}],
        "date": "2018-07-19",
        "itemType": "webpage"
    }
    is_valid, issues = validator.validate(metadata)
    assert is_valid
    assert len([i for i in issues if "CRITICAL" in i]) == 0

def test_truncated_title():
    validator = EntryValidator()
    metadata = {
        "title": "Added from URL: https://cris.vtt.fi/en/publications/implemen...",
        "creators": [],
        "date": ""
    }
    is_valid, issues = validator.validate(metadata)
    assert not is_valid
    assert any("truncat" in i.lower() or "Added from URL" in i for i in issues)

def test_missing_author_warning():
    validator = EntryValidator()
    metadata = {
        "title": "Some Valid Title Here",
        "creators": [],
        "date": "2023",
        "itemType": "webpage"
    }
    is_valid, issues = validator.validate(metadata)
    assert is_valid  # Still valid, just warning
    assert any("author" in i.lower() or "creator" in i.lower() for i in issues)
```

**File**: `tests/unit/test_site_author_mapping.py`
```python
from src.converters.md_to_latex.site_author_mapping import (
    extract_domain, extract_author_from_url, SITE_AUTHOR_MAPPINGS
)

def test_extract_domain():
    assert extract_domain("https://www.bbc.com/news/article") == "bbc.com"
    assert extract_domain("https://ec.europa.eu/policy") == "ec.europa.eu"

def test_known_sites():
    assert extract_author_from_url("https://www.bbc.com/news/business-44885983") == "BBC"
    assert extract_author_from_url("https://bloomberg.com/article") == "Bloomberg"

def test_subdomain_handling():
    assert extract_author_from_url("https://ec.europa.eu/environment") == "European Commission"

def test_unknown_site():
    assert extract_author_from_url("https://unknown-site-12345.com/article") is None
```

### Integration Tests

**File**: `tests/integration/test_zotero_auto_add.py`
```python
import pytest
from unittest.mock import patch, MagicMock
from src.converters.md_to_latex.zotero_auto_add import ZoteroAutoAdd

@pytest.fixture
def mock_zotero_client():
    client = MagicMock()
    client.base_url = "https://api.zotero.org"
    client.library_type = "user"
    client.library_id = "123456"
    client.api_key = "fake-key"
    return client

@pytest.fixture
def zotero_auto_add(mock_zotero_client):
    return ZoteroAutoAdd(
        zotero_client=mock_zotero_client,
        collection_name="test-collection",
        dry_run=True  # Always use dry_run in tests
    )

@patch("src.converters.md_to_latex.zotero_auto_add.TranslationClient")
def test_add_citation_success(mock_translation, zotero_auto_add):
    """Test successful citation addition with mocked translation."""
    # Mock translation response
    mock_translation.return_value.translate_url.return_value = {
        "title": "Burberry burns bags, clothes and perfume worth millions",
        "creators": [{"creatorType": "author", "lastName": "BBC"}],
        "date": "2018-07-19",
        "itemType": "webpage",
        "url": "https://www.bbc.com/news/business-44885983"
    }

    key, warnings = zotero_auto_add.add_citation(
        "https://www.bbc.com/news/business-44885983",
        "BBC (2018)"
    )

    assert key is not None
    assert key.startswith("dryrun_")
    assert len(warnings) == 0

@patch("src.converters.md_to_latex.zotero_auto_add.TranslationClient")
def test_add_citation_validation_failure(mock_translation, zotero_auto_add):
    """Test that validation failures prevent addition."""
    # Mock translation with truncated title
    mock_translation.return_value.translate_url.return_value = {
        "title": "Added from URL: https://cris.vtt.fi/en/publications/implemen...",
        "creators": [],
        "date": "",
        "itemType": "document"
    }

    key, warnings = zotero_auto_add.add_citation(
        "https://cris.vtt.fi/en/publications/123",
        "Some paper"
    )

    assert key is None
    assert any("CRITICAL" in w for w in warnings)
    assert any("truncat" in w.lower() or "Added from URL" in w for w in warnings)

def test_max_auto_add_threshold(zotero_auto_add):
    """Test that threshold prevents runaway additions."""
    zotero_auto_add.max_auto_add = 2
    zotero_auto_add.added_count = 2  # Already at threshold

    key, warnings = zotero_auto_add.add_citation("https://example.com", "Test")

    assert key is None
    assert any("threshold" in w.lower() for w in warnings)
```

---

## Implementation Phases

### Phase 1: Core Infrastructure (2-3 hours)
1. ✅ Create `translation_client.py` with Translation Server integration
2. ✅ Create `entry_validator.py` with quality checks
3. ✅ Create `site_author_mapping.py` with domain mappings
4. ✅ Write unit tests for each module

### Phase 2: Auto-Add Integration (2-3 hours)
1. ✅ Create `zotero_auto_add.py` with main logic
2. ✅ Integrate with `MarkdownToLatexConverter`
3. ✅ Add CLI flags (`--auto-add`, `--dry-run`)
4. ✅ Write integration tests

### Phase 3: Translation Server Setup (30 minutes)
1. ✅ Document how to run translation-server (Docker or Node.js)
2. ✅ Add health check to verify server is running
3. ✅ Graceful fallback if server unavailable

### Phase 4: Testing & Validation (2 hours)
1. ✅ Run on the 121 Temp citations from `mcp-draft-refined-v4.md`
2. ✅ Verify report quality
3. ✅ Manually check sample entries in Zotero
4. ✅ Iterate on validation rules based on failures

---

## Success Criteria

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Auto-add success rate | >95% | Count `added` / `total` in report |
| Zero garbage entries | 100% | Manual inspection of added entries |
| Validation catches bad entries | 100% | Run against October 26 bad data |
| (?) marks in PDF | <10 | `pdftotext ... \| grep -c "(?"` |
| Temp citations | <5 | Check `debug-02-zotero-matching-results.json` |
| Unit tests passing | 100% | `pytest tests/unit/test_*auto_add*.py` |
| Integration tests passing | 100% | `pytest tests/integration/` |

---

## Translation Server Setup

### Option 1: Docker (Recommended)

```bash
# Pull and run translation-server
docker pull zotero/translation-server
docker run -d -p 1969:1969 --name zotero-translation zotero/translation-server

# Test it's working
curl -X POST http://localhost:1969/web \
  -H "Content-Type: text/plain" \
  -d "https://www.bbc.com/news/business-44885983"
```

### Option 2: Node.js

```bash
git clone https://github.com/zotero/translation-server.git
cd translation-server
npm install
npm start
# Server runs on http://localhost:1969
```

### Health Check in Code

```python
def check_translation_server(url: str = "http://localhost:1969") -> bool:
    """Check if translation server is running."""
    try:
        resp = requests.get(f"{url}/", timeout=2)
        return resp.status_code == 200
    except requests.RequestException:
        return False

# In converter initialization
if not check_translation_server():
    logger.warning("Translation server not running at localhost:1969")
    logger.warning("Auto-add will be disabled. Start server with:")
    logger.warning("  docker run -p 1969:1969 zotero/translation-server")
    self.auto_add_enabled = False
```

---

## CLI Integration

```bash
# Dry-run mode (default) - simulate auto-add
uv run python -m src.cli_md_to_latex input.md --auto-add --dry-run

# Real auto-add (requires confirmation if >10 citations)
uv run python -m src.cli_md_to_latex input.md --auto-add

# Disable auto-add entirely
uv run python -m src.cli_md_to_latex input.md --no-auto-add

# Set threshold
uv run python -m src.cli_md_to_latex input.md --auto-add --max-auto-add 100
```

---

## Risk Mitigation

### Risk 1: Translation Server Unavailable
**Mitigation**: Health check on startup, graceful degradation to Temp keys

### Risk 2: Garbage Entries Added
**Mitigation**: Comprehensive validation before add, dry-run testing

### Risk 3: Better BibTeX Keys Not Generated
**Mitigation**: Fall back to Zotero keys, log warning, provide instructions

### Risk 4: Rate Limiting
**Mitigation**: Exponential backoff, respect 429 responses, add delays between calls

### Risk 5: Duplicate Entries
**Mitigation**: Check if URL already in collection before adding (future enhancement)

---

## Differences from OpenAI Plan - Summary Table

| Aspect | OpenAI Plan | Our Synthesized Plan | Reason for Change |
|--------|-------------|----------------------|-------------------|
| Translation API | `/users/{id}/items` POST | Translation Server (separate) | OpenAI endpoint doesn't exist |
| Better BibTeX keys | `?format=bibtex` | Collection re-export | Zotero API doesn't return BBT keys |
| Domain extraction | `tldextract` library | `urllib.parse` stdlib | No new dependencies |
| DOI validation | HEAD request per entry | Format check only | Performance (100+ network calls) |
| Caching | SQLite with schema | In-memory dict | Simplicity (add SQLite later if needed) |
| Error handling | Basic try/except | Exponential backoff + audit | Robustness |
| Zotero client | Re-implemented | Use existing `ZoteroClient` | Code reuse |
| Test mocking | Manual mocks | pytest fixtures + patches | Better test isolation |

---

## Next Steps

1. **Review this plan** - Ensure we're aligned on approach
2. **Start Phase 1** - Implement core infrastructure
3. **Test incrementally** - Unit tests as we go
4. **Set up translation server** - Docker container
5. **Test on real data** - 121 Temp citations from mcp-draft-refined-v4.md
6. **Iterate based on results** - Refine validation rules
7. **Document and commit** - Complete implementation

---

**Estimated Total Time**: 5-7 hours of focused development

**Generated**: 2025-10-29
**Authors**: Claude Code (synthesis of OpenAI plan + original plan)
