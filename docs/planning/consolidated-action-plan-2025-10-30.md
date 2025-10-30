# Consolidated Action Plan: Citations + Headings Fix
## Post-Crash Recovery Guide

**Date**: 2025-10-30
**Purpose**: Complete action plan for fixing ALL remaining conversion issues
**Can resume from**: This markdown file after any crash

---

## Issue Summary

### Issue 1: Temp/Stub Citations (CRITICAL)
**Evidence**: `anthropicTemp2024`, `brownTemp2024` in BibTeX output
**Root Cause**: Translation server not running → auto-add fails → fallback to temp keys
**Impact**: (?) citations in PDF, unusable bibliography

### Issue 2: No Headings in PDF (CRITICAL)
**Evidence**: PDF has plain text "Introduction" instead of formatted section headings
**Root Cause**: Pandoc not generating `\section{}` commands OR they're being stripped
**Impact**: No document structure, unreadable PDF

### Issue 3: Broken Heading Hierarchy (HIGH)
**Evidence**: Markdown jumps from `#` to `###` (skips `##`)
**Location**: `mcp-draft-refined-v4.md:10` (Introduction section)
**Impact**: Invalid document structure

---

## PART 1: Citation Fixes (80 minutes)

### Fix 1.1: START TRANSLATION SERVER (5 min)
**Priority**: 🔴 DO FIRST
**Status**: Not running (confirmed via `docker ps`)

```bash
# Start server
docker run -d -p 1969:1969 --name zotero-translation zotero/translation-server

# Verify running
docker ps | grep translation

# Test endpoint
curl http://localhost:1969/
# Expected: HTTP 200 OK

# If you get "port already in use":
docker stop zotero-translation
docker rm zotero-translation
# Then retry docker run command above
```

**Verification**:
- `docker ps` shows container running
- `curl localhost:1969` returns 200
- No "Connection refused" errors

### Fix 1.2: ADD TRANSLATION SERVER HEALTH CHECK (30 min)
**Priority**: 🔴 CRITICAL
**File**: `src/converters/md_to_latex/converter.py`
**Location**: In `__init__` method, after `self.citation_manager` initialization

**Add this method to MarkdownToLatexConverter class**:
```python
def _check_translation_server(self, url: str = "http://localhost:1969") -> bool:
    """Check if translation server is accessible.

    Returns:
        True if server responds, False otherwise
    """
    try:
        import requests
        resp = requests.get(url, timeout=2)
        return resp.status_code == 200
    except Exception as e:
        logger.debug(f"Translation server check failed: {e}")
        return False
```

**Add this check in `__init__` after line 136**:
```python
# After citation_manager initialization...
self.citation_manager = CitationManager(...)

# NEW: Check translation server if auto-add enabled
if self.citation_manager.zotero_auto_add:
    if not self._check_translation_server():
        error_msg = (
            "\n" + "=" * 70 + "\n"
            "❌ TRANSLATION SERVER NOT RUNNING\n"
            "\n"
            "Auto-add requires translation server at localhost:1969\n"
            "\n"
            "Start with:\n"
            "  docker run -d -p 1969:1969 zotero/translation-server\n"
            "\n"
            "Verify with:\n"
            "  curl http://localhost:1969/\n"
            "\n"
            "=" * 70
        )
        logger.error(error_msg)
        raise RuntimeError("Translation server required but not running")
    else:
        logger.info("✓ Translation server is running")
```

**Test**:
```bash
# Without server:
docker stop zotero-translation
uv run python -m src.cli_md_to_latex test.md
# Expected: Clear error message, conversion stops

# With server:
docker start zotero-translation
uv run python -m src.cli_md_to_latex test.md
# Expected: "Translation server is running" message
```

### Fix 1.3: ENFORCE FAIL-FAST VALIDATION (15 min)
**Priority**: 🟡 HIGH
**File**: `src/converters/md_to_latex/converter.py:1088`

**Current code**:
```python
temp_keys = self.citation_manager.validate_no_temp_keys(
    fail_on_temp=False  # ← CHANGE THIS
)
```

**Fixed code**:
```python
temp_keys = self.citation_manager.validate_no_temp_keys(
    fail_on_temp=True  # ← Now raises exception if temp keys found
)
```

**Also check line 1465** for BibTeX validation:
```python
# Ensure this raises on critical issues:
results = validator.validate_file(output_bib)
if results["critical_count"] > 0:
    raise RuntimeError(
        f"BibTeX validation FAILED with {results['critical_count']} critical issues\n"
        "Check validation report for details"
    )
```

### Fix 1.4: COMMIT TEMP KEY REMOVAL (15 min)
**Priority**: 🟡 HIGH
**File**: `src/converters/md_to_latex/citation_manager.py`
**Action**: Review and commit uncommitted changes

**Current uncommitted changes remove temp key fallback**:
```bash
# Check what's uncommitted
git diff src/converters/md_to_latex/citation_manager.py | head -50

# If changes look good (remove temp key fallback), commit:
git add src/converters/md_to_latex/citation_manager.py
git commit -m "fix: Remove temp key fallback, fail explicitly when auto-add unavailable

- _handle_missing_citation() now raises RuntimeError instead of creating temp keys
- Provides clear error messages with troubleshooting steps
- Forces users to fix root cause (add to Zotero or start translation server)
- Part of fail-fast strategy for bibliography quality

Addresses root cause analysis from 2025-10-30"
```

### Fix 1.5: TEST CITATION FIXES (30 min)
**Priority**: 🟡 HIGH

**Test 1: Verify Server Health Check Works**:
```bash
# Stop server
docker stop zotero-translation

# Try conversion - should FAIL with clear message
cd /home/petteri/Dropbox/github-personal/deep-biblio-tools
uv run python -m src.cli_md_to_latex \
  /home/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/mcp-draft-refined-v4.md \
  --output-dir /tmp/test_citations_noserver \
  --verbose

# Expected: RuntimeError about translation server
# Should NOT create temp keys
```

**Test 2: Full Conversion With Server Running**:
```bash
# Start server
docker start zotero-translation

# Clean output directory
rm -rf /tmp/test_citations_withserver
mkdir -p /tmp/test_citations_withserver

# Run conversion
uv run python -m src.cli_md_to_latex \
  /home/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/mcp-draft-refined-v4.md \
  --output-dir /tmp/test_citations_withserver \
  --verbose 2>&1 | tee /tmp/conversion_test.log

# Check results
echo "=== CITATION STATISTICS ==="
grep "Temp\|dryrun_" /tmp/test_citations_withserver/references.bib | wc -l
# Expected: 0 (or conversion should have failed with clear error)

echo "=== PDF QUALITY ==="
pdftotext /tmp/test_citations_withserver/*.pdf - | grep -c "(?"
# Expected: 0 or much lower than 372

echo "=== AUTO-ADD REPORT ==="
ls -la /tmp/test_citations_withserver/auto_add_report.txt
cat /tmp/test_citations_withserver/auto_add_report.txt
```

**Success Criteria**:
- ✅ No temp keys in references.bib (or clear error why)
- ✅ Significant reduction in (?) marks in PDF
- ✅ Auto-add report shows successful additions
- ✅ Server down = immediate clear error, not silent failure

---

## PART 2: Heading Fixes (90 minutes)

### Fix 2.1: INVESTIGATE MISSING SECTIONS (30 min)
**Priority**: 🔴 CRITICAL

**Check what Pandoc actually generates**:
```bash
# Create test markdown with clear headings
cat > /tmp/test_headings.md <<'EOF'
# Main Title

## Abstract

This is the abstract.

# Introduction

Some intro text.

## Background

Background section.

### Subsection

Subsection text.
EOF

# Convert directly with Pandoc
pandoc /tmp/test_headings.md -f markdown -t latex -o /tmp/test_pandoc.tex

# Check if sections exist
grep "\\section" /tmp/test_pandoc.tex
# Expected: Should see \section{Introduction}, \subsection{Background}, etc.
```

**Check our conversion**:
```bash
# Look at debug output from last conversion
grep "\\section\|\\subsection\|\\subsubsection" \
  /tmp/mcp_test_output/debug/3-latex-from-pandoc.tex | head -20

# If empty: Pandoc is NOT generating sections
# If present: Post-processing is stripping them
```

**Possible causes**:
1. **Title/Abstract extraction removes ALL headings**: Check `_apply_structure_heuristics()`
2. **Pandoc flags wrong**: Missing section generation flags
3. **Post-processing strips sections**: Check `post_process_latex_file()`

### Fix 2.2: FIX SECTION GENERATION (30 min)
**Priority**: 🔴 CRITICAL

**Option A: If Pandoc doesn't generate sections**:

**File**: `src/converters/md_to_latex/converter.py:1234`
**Problem**: Using `--standalone` might suppress sections when building custom document

**Try adding these pandoc flags**:
```python
latex_content = pypandoc.convert_text(
    content,
    "latex",
    format="markdown+tex_math_dollars+raw_tex+pipe_tables",
    extra_args=[
        "--standalone",
        "--wrap=preserve",
        "--columns=80",
        "--listings",
        "--no-highlight",
        "--top-level-division=section",  # ← ADD THIS: Force section generation
        "--number-sections",  # ← ADD THIS: Number sections
        "-V",
        "documentclass=article",
        "-V",
        "geometry:margin=1in",
        "-V",
        "tables=true",
    ],
)
```

**Option B: If post-processing strips sections**:

**File**: `src/converters/md_to_latex/post_processing.py`
**Action**: Check if `post_process_latex_file()` removes section commands

```bash
# Check post-processing function
grep -A50 "def post_process_latex_file" \
  /home/petteri/Dropbox/github-personal/deep-biblio-tools/src/converters/md_to_latex/post_processing.py
```

If it strips sections, modify to preserve them.

### Fix 2.3: FIX HEADING HIERARCHY IN MARKDOWN (20 min)
**Priority**: 🟡 HIGH
**File**: `mcp-draft-refined-v4.md`

**Problem**: Document jumps from `#` to `###` (line 10)

**Solution**: Add hierarchy validator to preprocessing

**File**: `src/converters/md_to_latex/utils.py`
**Add new function**:
```python
def validate_heading_hierarchy(content: str) -> tuple[bool, list[str]]:
    """Validate markdown heading hierarchy.

    Checks for:
    - Headings that skip levels (# → ###)
    - Multiple H1 headings (should be title only)

    Returns:
        (is_valid, list_of_issues)
    """
    lines = content.split("\n")
    issues = []
    previous_level = 0
    h1_count = 0

    for line_num, line in enumerate(lines, start=1):
        if line.strip().startswith("#"):
            # Count heading level
            level = 0
            for char in line:
                if char == "#":
                    level += 1
                else:
                    break

            if level == 1:
                h1_count += 1
                if h1_count > 2:  # Allow title + abstract
                    issues.append(
                        f"Line {line_num}: Multiple H1 headings found (should use H2-H6 for sections)"
                    )

            # Check for skipped levels
            if previous_level > 0:
                expected_max = previous_level + 1
                if level > expected_max:
                    issues.append(
                        f"Line {line_num}: Heading jumps from level {previous_level} to {level} "
                        f"(skips level {previous_level + 1}): {line[:60]}"
                    )

            previous_level = level

    return len(issues) == 0, issues
```

**Integrate in converter**:
```python
# In converter.py, after clean_markdown_headings():
is_valid, hierarchy_issues = validate_heading_hierarchy(content)
if not is_valid:
    logger.warning("Heading hierarchy issues found:")
    for issue in hierarchy_issues:
        logger.warning(f"  {issue}")
    logger.warning("Consider fixing these before conversion")
    # Optionally: raise error if strict mode enabled
```

**Manual fix for mcp-draft-refined-v4.md**:
```bash
# Lines 10, 16, 20, 30 should be ## (not ###)
# Change:
# ### The Magnitude of the Crisis
# To:
## The Magnitude of the Crisis
```

### Fix 2.4: TEST HEADING FIXES (10 min)
**Priority**: 🔴 CRITICAL

```bash
# Test with simple markdown
uv run python -m src.cli_md_to_latex /tmp/test_headings.md \
  --output-dir /tmp/test_headings_output

# Check LaTeX has sections
grep "\\section" /tmp/test_headings_output/*.tex

# Check PDF has formatted headings (not just plain text)
pdftotext /tmp/test_headings_output/*.pdf - | head -20
# Sections should be visually formatted, not plain text
```

---

## PART 3: Integration Testing (30 min)

### Test 3.1: Full Pipeline Test
**Purpose**: Verify ALL fixes work together

```bash
# Ensure prerequisites
docker ps | grep translation  # Should be running
docker logs zotero-translation  # Check for errors

# Clean environment
rm -rf /tmp/full_pipeline_test
mkdir -p /tmp/full_pipeline_test

# Run full conversion
cd /home/petteri/Dropbox/github-personal/deep-biblio-tools

time uv run python -m src.cli_md_to_latex \
  /home/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/mcp-draft-refined-v4.md \
  --output-dir /tmp/full_pipeline_test \
  --verbose \
  2>&1 | tee /tmp/full_pipeline_test/conversion.log

# Run all checks
echo "=== CITATION CHECK ==="
temp_count=$(grep -c "Temp\|dryrun_" /tmp/full_pipeline_test/references.bib || echo "0")
echo "Temp keys found: $temp_count"

echo "=== HEADING CHECK ==="
section_count=$(grep -c "\\\\section\|\\\\subsection" /tmp/full_pipeline_test/*.tex || echo "0")
echo "Section commands found: $section_count"

echo "=== PDF QUALITY CHECK ==="
question_marks=$(pdftotext /tmp/full_pipeline_test/*.pdf - | grep -c "(?" || echo "0")
echo "(?) marks in PDF: $question_marks"

echo "=== VALIDATION REPORT ==="
if [ -f /tmp/full_pipeline_test/validation_report.csv ]; then
    echo "Critical issues:"
    grep "CRITICAL" /tmp/full_pipeline_test/validation_report.csv | wc -l
fi

echo "=== AUTO-ADD REPORT ==="
if [ -f /tmp/full_pipeline_test/auto_add_report.txt ]; then
    cat /tmp/full_pipeline_test/auto_add_report.txt
fi
```

**Success Criteria**:
- ✅ Temp keys: 0 (or explicit failure with clear error)
- ✅ Section commands: >10 (document has many sections)
- ✅ (?) marks: 0 or <50 (down from 372)
- ✅ Critical validation issues: 0
- ✅ Auto-add report shows successes, not failures

---

## PART 4: Crash Recovery Procedure

### If VSCode/Terminal Crashes During Implementation

**Step 1: Check This File**
```bash
# This file contains the complete plan
less /home/petteri/Dropbox/github-personal/deep-biblio-tools/docs/planning/consolidated-action-plan-2025-10-30.md
```

**Step 2: Check What Was Completed**
```bash
# Check git status
cd /home/petteri/Dropbox/github-personal/deep-biblio-tools
git status
git log --oneline -5

# Check docker status
docker ps | grep translation

# Check if tests were run
ls -la /tmp/full_pipeline_test/
ls -la /tmp/test_citations_withserver/
```

**Step 3: Resume From Last Checkpoint**
Use this checklist:

- [ ] Fix 1.1: Translation server running? (`docker ps | grep translation`)
- [ ] Fix 1.2: Health check added? (Check `converter.py` for `_check_translation_server`)
- [ ] Fix 1.3: Fail-fast enabled? (Check `fail_on_temp=True` at line 1088)
- [ ] Fix 1.4: Changes committed? (`git log | grep "temp key"`)
- [ ] Fix 1.5: Citation tests passed? (Check `/tmp/test_citations_withserver/`)
- [ ] Fix 2.1: Section generation investigated? (Notes about Pandoc behavior)
- [ ] Fix 2.2: Section generation fixed? (Check pandoc extra_args)
- [ ] Fix 2.3: Hierarchy validator added? (Check `utils.py` for `validate_heading_hierarchy`)
- [ ] Fix 2.4: Heading tests passed? (Check `/tmp/test_headings_output/`)
- [ ] Test 3.1: Full pipeline tested? (Check `/tmp/full_pipeline_test/`)

**Step 4: Continue From Next Unchecked Item**

---

## PART 5: Documentation Updates (30 min)

### Update README
**File**: `README.md`
**Add section**:

```markdown
## Prerequisites

### Translation Server (Required for Auto-Add)

The auto-add feature requires the Zotero translation server:

\`\`\`bash
# Start server
docker run -d -p 1969:1969 --name zotero-translation zotero/translation-server

# Verify running
curl http://localhost:1969/
\`\`\`

If server is not running, conversion will fail with a clear error message.
```

### Update CLAUDE.md
**File**: `.claude/CLAUDE.md`
**Add to "Known Issues" section**:

```markdown
## Fixed Issues

### October 30, 2025: Citation Pipeline
- **Issue**: Temp keys created despite auto-add infrastructure
- **Root Cause**: Translation server not running
- **Fix**: Added health check, fail-fast validation
- **Prevention**: Server status checked at conversion start

### October 30, 2025: Heading Conversion
- **Issue**: No section headings in PDF output
- **Root Cause**: Pandoc section generation not enabled
- **Fix**: Added `--top-level-division=section` flag
- **Prevention**: Heading hierarchy validation added
```

---

## Summary of Changes

### Files Modified
1. `src/converters/md_to_latex/converter.py`
   - Added `_check_translation_server()` method
   - Added health check in `__init__()`
   - Changed `fail_on_temp=True` (line 1088)
   - Added pandoc flags for section generation (line 1234)

2. `src/converters/md_to_latex/utils.py`
   - Added `validate_heading_hierarchy()` function

3. `src/converters/md_to_latex/citation_manager.py`
   - Committed removal of temp key fallback (uncommitted → committed)

4. `README.md`
   - Added translation server prerequisite

5. `.claude/CLAUDE.md`
   - Documented fixes and prevention strategies

### Time Investment
- **Citation fixes**: 80 minutes (5 + 30 + 15 + 15 + 15)
- **Heading fixes**: 90 minutes (30 + 30 + 20 + 10)
- **Integration testing**: 30 minutes
- **Documentation**: 30 minutes
- **Total**: 230 minutes (~4 hours)

### Success Metrics
| Metric | Before | Target | How To Measure |
|--------|--------|--------|----------------|
| Temp keys | 121 | 0 | `grep -c Temp references.bib` |
| (?) citations | 372 | <50 | `pdftotext pdf \| grep -c "?"` |
| Section commands | 0 | >10 | `grep -c "\\\\section" tex` |
| PDF has headings | No | Yes | Visual inspection |
| Clear errors | No | Yes | Test with server down |

---

## If Everything Fails

### Nuclear Option: Simplified Testing

```bash
# Create minimal test case
cat > /tmp/minimal_test.md <<'EOF'
# Test Document

## Abstract
Test abstract.

## Introduction
Test introduction text with citation: [Smith (2020)](https://doi.org/10.1234/test).

## Conclusion
Test conclusion.
EOF

# Test conversion
uv run python -m src.cli_md_to_latex /tmp/minimal_test.md \
  --output-dir /tmp/minimal_output \
  --verbose

# Check results
grep "\\section" /tmp/minimal_output/*.tex
grep "Temp" /tmp/minimal_output/*.bib
pdftotext /tmp/minimal_output/*.pdf -
```

If this works: Problem is with complex document (mcp-draft-refined-v4.md)
If this fails: Problem is with core conversion logic

---

**Generated**: 2025-10-30 14:00 UTC
**Maintainer**: Resume from this file after any crash
**Next Action**: Start with Fix 1.1 (Translation Server)
