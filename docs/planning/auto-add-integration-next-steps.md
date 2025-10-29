# Auto-Add Integration - Next Steps

**Date**: 2025-10-29
**Status**: Infrastructure Complete - Ready for Integration
**Translation Server**: ✅ Running at `localhost:1969`

---

## Current Status: READY ✅

### Completed Infrastructure
1. ✅ **TranslationClient** (`translation_client.py`) - Working translation server integration
2. ✅ **EntryValidator** (`entry_validator.py`) - **PROVEN to block October 26 garbage!**
3. ✅ **Site Author Mapping** (`site_author_mapping.py`) - 25+ domain mappings
4. ✅ **ZoteroAutoAdd** (`zotero_auto_add.py`) - Full orchestration with validation
5. ✅ **54 Passing Tests** - Including garbage blocking tests
6. ✅ **Translation Server** - Running and tested with BBC article

### Test Results Proving Safety
```bash
# Entry Validator Tests (29 tests)
test_october_26_cris_garbage: PASSED ✅  # BLOCKS "Implementation plan"
test_october_26_truncated_url_title: PASSED ✅  # BLOCKS "Added from URL"
test_good_bbc_entry: PASSED ✅  # ALLOWS good entries

# Coverage: 94.41% on entry_validator.py
```

---

## Integration Steps (2-3 hours)

### Step 1: Add Auto-Add to CitationManager (30 minutes)

**File**: `src/converters/md_to_latex/citation_manager.py`

**Changes Needed**:

#### 1a. Add import at top:
```python
from src.converters.md_to_latex.zotero_auto_add import ZoteroAutoAdd
```

#### 1b. Modify `__init__` (around line 240):
```python
def __init__(
    self,
    cache_dir: Path | None = None,
    prefer_arxiv: bool = False,
    zotero_api_key: str | None = None,
    zotero_library_id: str | None = None,
    zotero_collection: str | None = None,
    use_cache: bool = True,
    use_better_bibtex_keys: bool = True,
    enable_auto_add: bool = True,  # NEW: Enable auto-add (default dry-run)
    auto_add_dry_run: bool = True,  # NEW: Safe dry-run by default
):
    # ... existing initialization ...

    # NEW: Initialize auto-add system (after zotero_client initialization)
    self.zotero_auto_add = None
    if enable_auto_add and self.zotero_client and zotero_collection:
        try:
            self.zotero_auto_add = ZoteroAutoAdd(
                zotero_client=self.zotero_client,
                collection_name=zotero_collection,
                translation_server_url="http://localhost:1969",
                dry_run=auto_add_dry_run,  # Safe by default!
                max_auto_add=50  # Threshold limit
            )
            mode = "DRY-RUN" if auto_add_dry_run else "REAL"
            logger.info(f"Auto-add initialized in {mode} mode")
        except Exception as e:
            logger.warning(f"Auto-add initialization failed: {e}")
            self.zotero_auto_add = None
```

#### 1c. Replace `_handle_missing_citation` (around line 1801):
```python
def _handle_missing_citation(
    self, citation: Citation, url: str
) -> str:
    """Handle citation not found in Zotero.

    Flow:
    1. Attempt auto-add via ZoteroAutoAdd (if enabled)
    2. If successful, return Better BibTeX key
    3. If failed or disabled, fall back to Temp key

    Args:
        citation: Citation object
        url: Citation URL

    Returns:
        Better BibTeX key (if added) or Temp key (if failed)
    """
    # Try auto-add if enabled
    if self.zotero_auto_add:
        logger.info(f"Attempting auto-add for: {url}")

        key, warnings = self.zotero_auto_add.add_citation(url, citation.authors)

        if key:
            # Success! (either added or dry-run simulated)
            if warnings:
                for warning in warnings:
                    logger.warning(f"  Auto-add warning: {warning}")
            return key
        else:
            # Validation failed or translation failed
            logger.warning(f"Auto-add BLOCKED or failed for: {url}")
            for warning in warnings:
                logger.warning(f"  {warning}")
            # Fall through to Temp key

    # Fallback: Generate Temp key
    logger.info(f"Falling back to Temp key for: {url}")
    self._citation_errors.append({
        "severity": "WARNING",
        "issue": "NO_AUTO_ADD_OR_FAILED",
        "url": url,
    })
    return self._generate_temp_key(citation)
```

---

### Step 2: Update MarkdownToLatexConverter (15 minutes)

**File**: `src/converters/md_to_latex/converter.py`

**Changes Needed**:

#### 2a. Add parameters to `__init__` (around line 60):
```python
def __init__(
    self,
    output_dir: Path | None = None,
    cache_dir: Path | None = None,
    # ... existing parameters ...
    collection_name: str | None = None,
    enable_auto_add: bool = True,  # NEW
    auto_add_dry_run: bool = True,  # NEW: Safe by default
):
    # ... existing code ...

    # Pass auto-add parameters to CitationManager
    self.citation_manager = CitationManager(
        cache_dir=self.cache_dir,
        prefer_arxiv=self.prefer_arxiv,
        zotero_api_key=self.zotero_api_key,
        zotero_library_id=self.zotero_library_id,
        zotero_collection=self.collection_name,
        use_cache=self.use_cache,
        use_better_bibtex_keys=self.use_better_bibtex_keys,
        enable_auto_add=enable_auto_add,  # NEW
        auto_add_dry_run=auto_add_dry_run,  # NEW
    )
```

#### 2b. Add report generation at end of `convert()` (around line 2000+):
```python
# At end of convert() method, after LaTeX compilation
if self.citation_manager.zotero_auto_add:
    # Generate auto-add report
    report = self.citation_manager.zotero_auto_add.generate_report()
    report_path = self.output_dir / "auto_add_report.txt"
    report_path.write_text(report)

    # Get statistics
    stats = self.citation_manager.zotero_auto_add.get_statistics()

    logger.info("=" * 60)
    logger.info("AUTO-ADD SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total processed: {stats['total']}")
    logger.info(f"Added: {stats['added']}")
    logger.info(f"Dry-run: {stats['dry_run']}")
    logger.info(f"Failed: {stats['translation_failed'] + stats['validation_failed']}")
    logger.info(f"Report written to: {report_path}")
    logger.info("=" * 60)
```

---

### Step 3: Update CLI (10 minutes)

**File**: `src/cli_md_to_latex.py`

**Add CLI flags**:
```python
@click.option(
    "--enable-auto-add/--no-auto-add",
    default=True,
    help="Enable automatic addition of missing citations to Zotero (default: enabled)"
)
@click.option(
    "--auto-add-dry-run/--auto-add-real",
    default=True,
    help="Dry-run mode for auto-add (default: dry-run for safety)"
)
def main(
    input_file,
    # ... existing params ...
    enable_auto_add,
    auto_add_dry_run
):
    # Pass to converter
    converter = MarkdownToLatexConverter(
        # ... existing params ...
        enable_auto_add=enable_auto_add,
        auto_add_dry_run=auto_add_dry_run
    )
```

---

### Step 4: Test Dry-Run (30 minutes)

**Run conversion with default dry-run**:
```bash
# Start translation server if not running
cd /tmp/translation-server && node ./src/server.js &

# Run conversion in dry-run mode (SAFE!)
uv run python -m src.cli_md_to_latex \
  "/home/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/mcp-draft-refined-v4.md" \
  --output-dir /tmp/auto_add_test \
  --enable-auto-add \
  --auto-add-dry-run \
  -v
```

**Expected Output**:
- Conversion completes successfully
- `auto_add_report.txt` created in output directory
- Report shows what WOULD be added
- NO actual changes to Zotero
- Log shows validation results

**Check Report**:
```bash
cat /tmp/auto_add_test/auto_add_report.txt
```

**Look for**:
- How many would be added
- How many blocked (validation failed)
- What warnings were raised

---

### Step 5: Review & Decide (1 hour)

**Manual Review Checklist**:

1. **Check Dry-Run Report**:
   ```bash
   grep "SUCCESSFULLY ADDED" /tmp/auto_add_test/auto_add_report.txt
   grep "FAILED TO ADD" /tmp/auto_add_test/auto_add_report.txt
   ```

2. **Review Failed Entries**:
   - Should show CRITICAL issues for garbage
   - Verify October 26 patterns are blocked

3. **Sample Good Entries**:
   - Pick 5 random "would be added" entries
   - Check their titles, authors, dates in report
   - Verify quality looks good

4. **Decision Point**:
   - If ALL blocked entries are garbage → Safe to proceed
   - If ANY good entries blocked → Adjust validation rules
   - If ANY garbage would be added → **STOP** and fix validation

---

### Step 6: Enable Real Mode (IF Step 5 passes)

**Only proceed if dry-run looks perfect!**

```bash
# REAL MODE - Actually adds to Zotero
uv run python -m src.cli_md_to_latex \
  "mcp-draft-refined-v4.md" \
  --output-dir /tmp/auto_add_real \
  --enable-auto-add \
  --auto-add-real \
  -v
```

**Monitor carefully**:
- Check logs for validation failures
- Review report after completion
- Manually check a few added entries in Zotero web UI

---

## Safety Guardrails

### Built-In Safety Features ✅
1. **Dry-run by default** - No changes unless explicitly enabled
2. **CRITICAL issue blocking** - Validation STOPS bad entries
3. **Threshold limits** - Won't add more than 50 without review
4. **Comprehensive audit trail** - Every action logged
5. **Clear reporting** - Human-readable grouped reports

### Manual Safety Checks
Before enabling real mode:
- ✅ Review dry-run report thoroughly
- ✅ Check for October 26 patterns being blocked
- ✅ Verify good entries are being added
- ✅ Sample check titles and authors
- ✅ Translation server is running

---

## Validation Patterns (PROVEN to Work)

### BLOCKED Patterns (October 26 Garbage)
- ✅ `"Added from URL: https://..."`
- ✅ `"Implementation plan..."`
- ✅ Titles with ellipsis (`...`)
- ✅ Titles <10 characters
- ✅ Truncated titles

### ALLOWED Patterns (Good Entries)
- ✅ BBC article: "Burberry burns bags..."
- ✅ Complete titles >10 chars
- ✅ Proper author names
- ✅ Valid years (1900-2030)

---

## Expected Results

### Before Auto-Add
- **Temp citations**: 121 (31.8%)
- **(?) marks in PDF**: 0 (already fixed!)
- **From Zotero**: 260 (68.2%)

### After Auto-Add (Projected)
- **Successfully added**: ~100-110 (85-90% success rate)
- **Blocked (garbage)**: ~5-10
- **Failed (translation)**: ~5-10
- **Temp citations remaining**: <10 (down from 121!)

### Quality Metrics
- **Garbage entries added**: 0 (BLOCKED by validation)
- **False positives** (good blocked): <5 expected
- **Overall success rate**: >90%

---

## Troubleshooting

### Translation Server Issues
```bash
# Check if running
curl http://localhost:1969/
# Should return "Not Found" (correct!)

# Check logs
tail -f /tmp/translation-server.log

# Restart if needed
pkill -f "node.*server.js"
cd /tmp/translation-server && node ./src/server.js &
```

### No Metadata Returned
- Check translation-server logs
- Site may not be supported
- Will fall back to Temp key (safe)

### Validation Too Strict
- Check validation rules in `entry_validator.py`
- Adjust truncation markers if needed
- Consider adding site-specific rules

---

## Next Session Plan

1. **Integrate** (30 min): Add code changes from Steps 1-3
2. **Test Dry-Run** (30 min): Run and review report
3. **Manual Review** (1 hour): Check quality thoroughly
4. **Decision**: Enable real mode OR iterate on validation
5. **Production Use**: Add 100+ citations automatically!

---

## Files Modified

Will need to modify:
1. `src/converters/md_to_latex/citation_manager.py` (~50 lines changed)
2. `src/converters/md_to_latex/converter.py` (~30 lines changed)
3. `src/cli_md_to_latex.py` (~10 lines changed)

Total: ~90 lines of production code changes

---

## Success Criteria

| Metric | Target | How to Verify |
|--------|--------|---------------|
| Garbage blocked | 100% | Check "FAILED" in report for October 26 patterns |
| Good entries added | >90% | Sample check titles/authors in report |
| Temp citations reduced | <10 | Count remaining Temp citations after conversion |
| No manual cleanup | 0 entries | Check Zotero - should all be clean |
| Report quality | Clear | Human-readable, actionable |

---

**Generated**: 2025-10-29 19:30 UTC
**Ready to proceed**: YES - all infrastructure tested and working!
**Estimated time to production**: 2-3 hours (including thorough testing)
