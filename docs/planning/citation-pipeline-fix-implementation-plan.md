# Citation Pipeline Fix - Implementation Plan

**Date**: 2025-10-29
**Status**: Ready for implementation
**Context**: Response to OpenAI code review feedback

---

## Executive Summary

**Problem**: 32% citation failure rate (121/381 citations incomplete)
**Root Cause**: Auto-add exists but not integrated; validation has 86% false positive rate; invalid DOIs silently accepted
**Solution**: Hybrid approach combining DOI validation, auto-add integration, policy enforcement, and comprehensive testing

---

## Assessment of OpenAI Feedback

### What I Agree With ✅

1. **Hybrid Auto-Add Approach (H5)** - Most robust solution
   - Validates DOI before fetch
   - Attempts auto-add for missing citations
   - Updates Zotero key from API
   - Fallback to Temp key only for truly invalid citations
   - **Critical**: Prevents "cheating" with Temp keys for valid DOIs

2. **DOI Validation Strategy**
   - HEAD request to CrossRef before full metadata fetch
   - Cache negative responses (404s) to avoid repeated failed requests
   - Treat invalid DOIs as CRITICAL errors, not silent stubs
   - Fail fast and report clearly

3. **Policy Enforcement**
   - **Zero tolerance** for Temp keys with valid DOIs
   - Raise RuntimeError or CRITICAL log if shortcut attempted
   - Audit report showing all Temp keys with reasons
   - Tests that verify policy compliance

4. **Author Validation Fix**
   - Parse BibTeX author format properly: `"Last, First and Last2, First2"`
   - Only flag incomplete if:
     - Single author with "others"/"et al"
     - Author count < expected from DOI metadata
   - Accept large author lists (≥6) as likely complete
   - Reduce false positive rate from 86% to <5%

5. **Comprehensive Testing**
   - Unit tests with mocks for Zotero/CrossRef
   - Integration tests for full pipeline
   - Policy enforcement tests
   - Clear test matrix with all edge cases

6. **Error Reporting**
   - Severity levels: CRITICAL, ERROR, WARNING
   - End-of-pipeline report with all issues
   - Include: citation text, DOI/URL, Temp key (if any), suggested fix

### What Needs Adjustment ⚠️

1. **Async/Batch Implementation**
   - **OpenAI suggests**: Async from the start
   - **My assessment**: Start synchronous, optimize later if needed
   - **Rationale**:
     - Correctness first, performance second
     - Easier to debug synchronous code
     - Async adds complexity (error handling, timeouts, rate limits)
     - Current test file (381 citations) processes in ~30s synchronously
     - Only optimize if performance becomes actual bottleneck

2. **PDF Compilation in Tests**
   - **OpenAI suggests**: Full LaTeX compilation in every test
   - **My assessment**: Separate E2E tests only
   - **Rationale**:
     - Unit tests should be fast (<1s each)
     - LaTeX compilation is slow (3-5s minimum)
     - Test pyramid: many fast unit tests, few slow E2E tests
     - Use mocks for unit tests, real compilation for E2E only

3. **Test Scaffold Assumptions**
   - OpenAI's code uses `batch_auto_add=True` parameter (doesn't exist yet)
   - OpenAI's code assumes methods we haven't implemented yet
   - **Adjustment**: Build test scaffold incrementally as we implement features

---

## Implementation Strategy

### Phase 1: Core Infrastructure (P0 - Must Fix)

#### 1.1 DOI Validation with Caching

**File**: `src/converters/md_to_latex/citation_manager.py`

**New Method**:
```python
def _validate_doi(self, doi: str) -> bool:
    """Validate DOI via CrossRef HEAD request.

    Returns True if DOI exists (200 OK), False if not found (404).
    Results are cached to avoid repeated failed requests.
    """
    # Check cache first
    if doi in self._doi_validation_cache:
        return self._doi_validation_cache[doi]

    # HEAD request to CrossRef
    url = f"https://api.crossref.org/works/{doi}"
    try:
        response = requests.head(url, timeout=5)
        is_valid = response.status_code == 200

        # Cache result (especially 404s to avoid repeated failures)
        self._doi_validation_cache[doi] = is_valid

        if not is_valid:
            logger.critical(f"Invalid DOI detected: {doi} (HTTP {response.status_code})")

        return is_valid
    except Exception as e:
        logger.warning(f"DOI validation failed for {doi}: {e}")
        return False  # Treat network errors as invalid
```

**Init Changes**:
```python
def __init__(self, ...):
    # ... existing init code ...
    self._doi_validation_cache: dict[str, bool] = {}
    self._citation_errors: list[dict] = []  # Track all errors for end report
```

#### 1.2 Auto-Add Integration

**File**: `src/converters/md_to_latex/citation_manager.py`

**New Method**:
```python
def _handle_missing_citation(self, citation: Citation, url: str) -> str:
    """Handle citation not found in Zotero.

    Flow:
    1. Extract DOI from URL if present
    2. Validate DOI (HEAD request to CrossRef)
    3. If valid DOI:
       a. Fetch metadata from CrossRef/arXiv
       b. Attempt auto-add to Zotero
       c. Wait 0.5s for Zotero to process
       d. Re-fetch collection to get new key
       e. Return Zotero key
    4. If invalid DOI or no DOI:
       a. Log CRITICAL error
       b. Return Temp key as fallback
       c. Add to error report

    Returns:
        Zotero key (if added) or Temp key (if failed)
    """
    # Extract DOI from URL
    doi = self._extract_doi_from_url(url)

    if doi:
        # Validate DOI before proceeding
        if not self._validate_doi(doi):
            self._citation_errors.append({
                "severity": "CRITICAL",
                "issue": "INVALID_DOI",
                "doi": doi,
                "url": url,
                "citation": citation.authors,
            })
            return self._generate_temp_key(citation)

        # Fetch metadata from CrossRef/arXiv
        metadata = self._fetch_metadata(doi, url)

        if not metadata or not metadata.get("title"):
            self._citation_errors.append({
                "severity": "ERROR",
                "issue": "INCOMPLETE_METADATA",
                "doi": doi,
                "url": url,
            })
            return self._generate_temp_key(citation)

        # Attempt auto-add to Zotero
        if self.citation_matcher:
            result = self.citation_matcher.add_to_zotero_library(url)

            if result:
                # Wait for Zotero to process (avoid race condition)
                time.sleep(0.5)

                # Re-fetch collection to get new key
                new_entry = self._fetch_newly_added_entry(doi)

                if new_entry and "key" in new_entry:
                    logger.info(f"Successfully added to Zotero: {doi} → {new_entry['key']}")
                    return new_entry["key"]
                else:
                    logger.warning(f"Auto-add succeeded but couldn't fetch new key for {doi}")
                    return self._generate_temp_key(citation)

    # Fallback: Temp key for citations without DOI or after failures
    self._citation_errors.append({
        "severity": "WARNING",
        "issue": "NO_DOI_OR_FAILED_ADD",
        "url": url,
    })
    return self._generate_temp_key(citation)
```

#### 1.3 Policy Enforcement

**File**: `src/converters/md_to_latex/citation_manager.py`

**New Method**:
```python
def _enforce_no_temp_key_for_valid_doi(self, citation: Citation) -> None:
    """Enforce policy: Temp keys only allowed for invalid/missing DOIs.

    Raises RuntimeError if a Temp key exists for a citation with valid DOI.
    This prevents "cheating" by using Temp keys as shortcuts.
    """
    if "Temp" in citation.key:
        doi = self._extract_doi_from_url(citation.url)

        if doi and self._validate_doi(doi):
            raise RuntimeError(
                f"Policy violation: Temp key '{citation.key}' created for valid DOI {doi}. "
                f"This citation should have been added to Zotero automatically."
            )
```

**Integration Point** (in main extraction flow):
```python
# After all citations processed
for citation in self.citations.values():
    self._enforce_no_temp_key_for_valid_doi(citation)
```

#### 1.4 Author Validation Fix

**File**: `scripts/validate_bib_source.py`

**Fix BibTeX Author Parsing**:
```python
def count_bibtex_authors(author_field: str) -> int:
    """Count authors in BibTeX author field.

    BibTeX format: "Last1, First1 and Last2, First2 and Last3, First3"
    """
    if not author_field or author_field.strip() == "":
        return 0

    # Check for "others" or "et al" (indicates truncated list)
    if "others" in author_field.lower() or "et al" in author_field.lower():
        # Return negative to indicate truncation
        return -1

    # Split by " and " to count authors
    authors = [a.strip() for a in author_field.split(" and ") if a.strip()]
    return len(authors)

def validate_author_completeness(entry: dict, doi_metadata: dict | None = None) -> list[str]:
    """Validate author completeness.

    Returns empty list if complete, list of issues if incomplete.
    """
    issues = []

    author_field = entry.get("author", "")
    author_count = count_bibtex_authors(author_field)

    # If author count is negative, list was truncated with "others"/"et al"
    if author_count == -1:
        # Check if DOI metadata available to verify expected count
        if doi_metadata and "author" in doi_metadata:
            expected_count = len(doi_metadata["author"])

            # Only flag as incomplete if expected authors < 15
            # (for 15+ author papers, "et al" is acceptable)
            if expected_count < 15:
                issues.append(f"INCOMPLETE_AUTHORS: has 'et al' but only {expected_count} expected")
        else:
            issues.append("INCOMPLETE_AUTHORS: has 'others'/'et al' (check if acceptable)")
        return issues

    # If no authors at all
    if author_count == 0:
        issues.append("NO_AUTHORS: empty author field")
        return issues

    # If ≥6 complete authors, accept as complete (not truncated)
    if author_count >= 6:
        return []  # No issues

    # For 1-5 authors, check against DOI metadata if available
    if doi_metadata and "author" in doi_metadata:
        expected_count = len(doi_metadata["author"])

        if author_count < expected_count:
            issues.append(f"INCOMPLETE_AUTHORS: has {author_count} but expected {expected_count}")

    return issues
```

---

### Phase 2: Testing Infrastructure (P0)

#### 2.1 Unit Tests

**File**: `tests/unit/test_citation_manager.py`

**Key Tests**:
1. `test_validate_doi_success()` - Valid DOI returns True
2. `test_validate_doi_failure()` - Invalid DOI returns False
3. `test_validate_doi_caching()` - 404s are cached
4. `test_handle_missing_citation_valid_doi()` - Auto-adds and returns Zotero key
5. `test_handle_missing_citation_invalid_doi()` - Returns Temp key, logs CRITICAL
6. `test_policy_enforcement_raises()` - RuntimeError for Temp key + valid DOI
7. `test_author_parsing()` - BibTeX author counts
8. `test_author_validation_large_list()` - 6+ authors not flagged
9. `test_author_validation_et_al()` - Handles "et al" correctly

#### 2.2 Integration Tests

**File**: `tests/integration/test_citation_pipeline.py`

**Key Tests**:
1. `test_pipeline_mixed_citations()` - Valid DOI, invalid DOI, web page
2. `test_pipeline_all_zotero_keys()` - No Temp keys for valid DOIs
3. `test_pipeline_error_reporting()` - End report has all issues
4. `test_pipeline_validation_false_positives()` - duan2025, beigi2024 not flagged

#### 2.3 E2E Tests

**File**: `tests/e2e/test_full_conversion.py`

**Key Tests**:
1. `test_full_conversion_mcp_draft()` - Real file, PDF compilation, zero (?) citations
2. `test_conversion_performance()` - 381 citations in <60s

---

### Phase 3: Error Reporting (P1)

#### 3.1 End-of-Pipeline Report

**File**: `src/converters/md_to_latex/citation_manager.py`

**New Method**:
```python
def generate_error_report(self) -> str:
    """Generate human-readable error report.

    Groups errors by severity and provides actionable information.
    """
    if not self._citation_errors:
        return "✅ All citations processed successfully (no errors)"

    report = ["", "=" * 80, "CITATION PROCESSING ERROR REPORT", "=" * 80, ""]

    # Group by severity
    critical = [e for e in self._citation_errors if e["severity"] == "CRITICAL"]
    errors = [e for e in self._citation_errors if e["severity"] == "ERROR"]
    warnings = [e for e in self._citation_errors if e["severity"] == "WARNING"]

    # Report each severity level
    if critical:
        report.append(f"🔴 CRITICAL ({len(critical)} issues) - Invalid DOIs from LLM hallucinations")
        for err in critical:
            report.append(f"  - {err['issue']}: {err.get('doi', err.get('url', 'N/A'))}")
            report.append(f"    Citation: {err.get('citation', 'Unknown')}")
        report.append("")

    if errors:
        report.append(f"⚠️  ERROR ({len(errors)} issues) - Missing/incomplete metadata")
        for err in errors:
            report.append(f"  - {err['issue']}: {err.get('doi', err.get('url', 'N/A'))}")
        report.append("")

    if warnings:
        report.append(f"ℹ️  WARNING ({len(warnings)} issues) - Citations without DOI")
        report.append(f"    {len(warnings)} citations could not be auto-added (web pages, etc.)")
        report.append("")

    report.append("=" * 80)
    return "\n".join(report)
```

**Integration** (at end of conversion):
```python
# Generate and print report
report = self.citation_manager.generate_error_report()
print(report)

# Also save to file
with open(output_dir / "citation_errors.txt", "w") as f:
    f.write(report)
```

---

## Priority and Timeline

### P0 - Must Fix (Implement First)
1. ✅ DOI validation with caching (~2 hours)
2. ✅ Auto-add integration (~3 hours)
3. ✅ Policy enforcement (~1 hour)
4. ✅ Author validation fix (~2 hours)
5. ✅ Unit tests (~3 hours)
6. ✅ Integration tests (~2 hours)

**Total P0**: ~13 hours of implementation

### P1 - Should Fix (Implement Second)
1. Error reporting (~2 hours)
2. E2E tests (~2 hours)

**Total P1**: ~4 hours

### P2 - Nice to Have (Defer)
1. Async/batch optimization (only if performance issues)
2. Advanced caching strategies
3. Additional validation heuristics

---

## Success Criteria

### Definition of Done

1. **Zero Temp Keys for Valid DOIs**
   - Test with mcp-draft-refined-v4.md
   - All citations with valid DOIs must have Zotero keys
   - Temp keys only for invalid DOIs or web pages

2. **False Positive Rate <5%**
   - Run validation on references.bib
   - Verify duan2025 (6 authors) and beigi2024 (12 authors) not flagged
   - Accept large author lists without flagging

3. **Clear Error Reporting**
   - Invalid DOIs logged as CRITICAL with context
   - End-of-pipeline report shows all issues
   - User understands what went wrong and why

4. **Policy Enforcement**
   - Tests verify no shortcuts with Temp keys
   - RuntimeError raised if policy violated
   - Audit trail for all citation decisions

5. **Test Coverage ≥80%**
   - All new methods have unit tests
   - Integration tests cover main pipeline
   - E2E test verifies PDF output

---

## Risk Mitigation

### Potential Issues

1. **Zotero API Rate Limits**
   - Risk: Auto-add triggers rate limiting
   - Mitigation: Add exponential backoff, respect API limits
   - Fallback: Batch processing with delays

2. **Race Condition After Auto-Add**
   - Risk: Zotero key not immediately available
   - Mitigation: 0.5s sleep + polling (max 3 attempts)
   - Fallback: Use Temp key if key not found after 3 attempts

3. **Invalid DOI Caching**
   - Risk: Legitimate DOI marked as invalid due to transient error
   - Mitigation: Only cache 404s, not network errors
   - Fallback: Cache expiry after 24 hours

4. **Performance Degradation**
   - Risk: Additional API calls slow down pipeline
   - Mitigation: DOI HEAD requests are fast (<100ms each)
   - Fallback: Implement async if synchronous too slow

---

## Next Steps

1. **Commit current work** (Better BibTeX integration + docs reorganization)
2. **Create test scaffolding** (mocks for Zotero/CrossRef)
3. **Implement P0 fixes** in order:
   - DOI validation
   - Auto-add integration
   - Policy enforcement
   - Author validation
4. **Run tests** and verify all passing
5. **Test with mcp-draft-refined-v4.md** to confirm 121 Temp citations resolved

---

Generated: 2025-10-29
