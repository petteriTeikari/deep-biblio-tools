# Comprehensive Plan: Complete MD-to-LaTeX Citation Pipeline

**Date**: 2025-10-27
**Goal**: Convert ALL 4 markdown files to PDFs with ZERO missing citations
**Target Audience**: 3rd-party LLM consultants without codebase access

---

## Executive Summary

### Current State
- **3 out of 4 files work** (mcp, fashion-cad, fashion-lca)
- **1 file crashes** with `'str' object has no attribute 'group'` error
- **Critical blocker**: The AST-based citation replacement has been fixed but there's a remaining regex Match object handling bug

### Success Criteria (ZERO TOLERANCE)
1. ✅ PDF generates without LaTeX errors
2. ✅ PDF has ZERO `(?)` citations
3. ✅ PDF has ZERO `(Unknown)` or `(Anonymous)` citations
4. ✅ All citations show proper author names and years
5. ✅ `references.bib` has ZERO "Unknown" entries
6. ✅ LaTeX log has ZERO compilation errors
7. ✅ BibTeX log has ZERO fatal errors (warnings OK)

### The 4 Target Files

```bash
# File locations
/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/

1. mcp-review/mcp-draft-refined-v4.md                    # ✅ WORKING (368 citations)
2. fashion_3D_CAD/fashion-cad-review-v3.md               # ✅ WORKING (71 citations)
3. fashion_LCA/fashion-lca-draft-v3.md                   # ✅ WORKING (44 citations)
4. fashion_4DGS/4dgs-fashion-comprehensive-v2.md         # ❌ CRASHES
```

---

## Part 1: Architecture Context

### What This Tool Does

Deep Biblio Tools converts LLM-generated markdown papers with inline citations into publication-ready LaTeX/PDFs. The key challenge: **LLMs hallucinate citation details**, especially author names.

### Core Pipeline (8 Steps)

```
1. Read Markdown (.md)
   ↓
2. Extract Citations ([Author (Year)](URL))
   ↓
3. Match Against Zotero Library (via Web API)
   ↓
4. Fetch Missing Metadata (CrossRef, arXiv, DOI APIs)
   ↓
5. Generate BibTeX Keys (Better BibTeX format)
   ↓
6. Replace Markdown Links → LaTeX \citep{} Commands
   ↓
7. Generate references.bib File
   ↓
8. Compile LaTeX → PDF
```

### Key Design Decisions

1. **NO REGEX for structured parsing** - Use AST parsers only
   - ✅ `markdown-it-py` for Markdown AST
   - ✅ `pylatexenc` for LaTeX AST
   - ✅ `bibtexparser` for BibTeX AST

2. **Zotero Web API = Single Source of Truth**
   - NO manual exports (.json, .bib files)
   - ALWAYS fetch fresh from API
   - Auto-add missing citations to Zotero

3. **Deterministic Behavior**
   - Same input ALWAYS produces same output
   - All API responses cached
   - Audit trails for every decision

4. **Distinguish Citations from Regular Hyperlinks**
   - Citation: `[Author (Year)](URL)` → Process for bibliography
   - Hyperlink: `[Text](URL)` → Leave as regular link
   - This prevents false "Unknown, Unknown" entries

---

## Part 2: What We Fixed in Last 2 Days

### Day 1: AST-Based Citation Replacement (Commits 31d71f4 → 476dc90)

**Problem**: Citation replacement failed completely - no markdown links converted to `\citep{}`.

**Root Causes Found and Fixed**:

#### Issue 1: Token Mutation Not Reflected in Output
```python
# BROKEN (tokens modified but lost)
for token in tokens:
    if token.type == "link_open":
        token.type = "text"  # Changed token
        token.content = r"\citep{key}"  # Added citation

# Renderer still saw ORIGINAL unmodified tokens!
output = md.renderer.render(tokens, ...)  # Lost all changes
```

**Fix**: Use markdown-it renderer directly, don't try to mutate tokens
```python
# CORRECT
output = md.renderer.render(tokens, md.options, {})
# Renderer preserves all token modifications
```

#### Issue 2: HTML Entities Not Stripped
```python
# markdown-it renderer outputs HTML entities
output = "&lt;https://example.com&gt;"

# LaTeX chokes on these
```

**Fix**: Strip HTML tags and decode entities after rendering
```python
output = strip_html_tags(output)
output = html.unescape(output)
```

#### Issue 3: URL Normalization Mismatch
```python
# Extraction used one normalization
extracted_url = normalize_arxiv_url(url)  # → "https://arxiv.org/abs/2301.12345"

# Replacement used different normalization
lookup_url = normalize_url(url)  # → "https://arxiv.org/abs/2301.12345v2"

# Keys don't match → replacement fails
```

**Fix**: Apply SAME normalization chain in both extraction and replacement
```python
def unified_normalize(url: str) -> str:
    """Single normalization function for all URLs."""
    return normalize_url(normalize_arxiv_url(url))
```

### Day 2: Remaining Issues (Current State)

**3 files work perfectly** after the fixes above.

**1 file crashes** with this error:
```
Conversion failed: 'str' object has no attribute 'group'
```

This means somewhere in the code, we're treating a string as if it were a regex Match object.

---

## Part 3: Current Blocker - The `.group()` Error

### Error Details

```bash
# Command that crashes
cd /Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/fashion_3D_CAD
uv run --project /Users/petteri/Dropbox/github-personal/deep-biblio-tools \
  python -m src.cli md2latex fashion-cad-review-v3.md --collection dpp-fashion

# Output
Conversion failed: 'str' object has no attribute 'group'
Error converting file: 'str' object has no attribute 'group'
```

### What `.group()` Means

In Python regex:
```python
import re

# Correct usage
match = re.search(r'(\d+)', 'year 2024')
if match:
    year = match.group(1)  # → "2024"

# WRONG - treating string as Match object
text = "2024"
year = text.group(1)  # ❌ AttributeError: 'str' object has no attribute 'group'
```

### Likely Locations (Need Investigation)

Given our NO REGEX policy, this is likely in:

1. **Citation extraction** (markdown link parsing)
2. **Author name parsing** (splitting "Author et al., Year")
3. **URL parsing** (extracting arxiv IDs, DOI patterns)
4. **Year extraction** (finding "(Year)" or ", Year")

### Why It Only Affects 1 File

The `fashion-cad-review-v3.md` file likely has:
- A citation format variant we haven't seen
- Special characters in author names
- Edge case URL format
- Markdown structure that triggers different code path

---

## Part 4: Diagnostic Strategy

### Step 1: Find the Exact Location

Add comprehensive exception handling with stack traces:

```python
# In src/converters/md_to_latex/converter.py (main convert function)

try:
    # ... existing conversion code ...
except AttributeError as e:
    if "'str' object has no attribute 'group'" in str(e):
        logger.error("=" * 80)
        logger.error("CAUGHT THE .group() ERROR!")
        logger.error("=" * 80)
        import traceback
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        raise
```

### Step 2: Run with Full Traceback

```bash
cd /Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/fashion_3D_CAD
uv run --project /Users/petteri/Dropbox/github-personal/deep-biblio-tools \
  python -m src.cli md2latex fashion-cad-review-v3.md \
  --collection dpp-fashion --verbose 2>&1 | tee /tmp/traceback.log
```

### Step 3: Inspect the Problematic Citation

Once we know the line number, check the markdown file around that citation:

```bash
# If error is at citation #25, check context
sed -n '1,1000p' fashion-cad-review-v3.md | grep -n "\[.*\](http" | head -30
```

---

## Part 5: Known Code Locations to Check

### Location 1: Citation Extraction (citation_manager.py)

**File**: `src/converters/md_to_latex/citation_manager.py`
**Function**: `extract_citations()`
**Lines**: ~200-400

```python
# Check for regex usage disguised as string operations
# Look for patterns like:

# BAD - treating result as Match object
author_match = some_string  # Actually a string, not a Match
year = author_match.group(1)  # ❌ CRASHES

# GOOD - check type first
if isinstance(result, re.Match):
    year = result.group(1)
else:
    year = result  # It's already a string
```

### Location 2: Author Parsing (citation_manager.py)

**Function**: `_parse_citation_text()`
**Purpose**: Extracts author and year from "[Author (Year)](URL)"

```python
# Check this pattern:
def _parse_citation_text(self, text: str) -> tuple[str, str]:
    # If we do: author = re.search(r'(.*)\s*\((\d{4})\)', text)
    # And later: name = author.group(1)  # Correct

    # But if somewhere we do: author = text.split("(")[0]
    # And later: name = author.group(1)  # ❌ CRASH - author is str, not Match
```

### Location 3: URL Normalization (url_utils.py)

**File**: `src/utils/url_utils.py`
**Functions**: `normalize_arxiv_url()`, `normalize_url()`

```python
# Check for:
arxiv_id = extract_arxiv_id(url)  # Returns string "2301.12345"
# Later someone does:
full_id = arxiv_id.group(0)  # ❌ CRASH
```

### Location 4: Better BibTeX Key Generation (citation_manager.py)

**Function**: `generate_better_bibtex_key()`
**Purpose**: Creates keys like `author2024title`

```python
# Check for:
author_part = extract_author(author_string)  # Returns string
# Later:
last_name = author_part.group(1)  # ❌ CRASH
```

---

## Part 6: The Fix Strategy

### Once We Find the Location

1. **Identify the variable** that should be a Match object but is a string
2. **Trace backwards** to see where it was assigned
3. **Fix in one of two ways**:

#### Option A: The variable SHOULD be a Match object
```python
# BEFORE (wrong)
result = some_string_operation(text)
value = result.group(1)  # ❌ result is str

# AFTER (fixed)
result = re.search(r'pattern', text)
if result:
    value = result.group(1)  # ✅ result is Match
else:
    value = "default"
```

#### Option B: The variable is correctly a string, remove `.group()` call
```python
# BEFORE (wrong)
author = text.split("(")[0].strip()  # Returns str
last_name = author.group(1)  # ❌ author is str, not Match

# AFTER (fixed)
author = text.split("(")[0].strip()  # Returns str
last_name = author  # ✅ Use string directly
```

### After the Fix

1. **Test the crashing file**:
```bash
cd /Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/fashion_3D_CAD
uv run --project /Users/petteri/Dropbox/github-personal/deep-biblio-tools \
  python -m src.cli md2latex fashion-cad-review-v3.md -c dpp-fashion
```

2. **Verify PDF has no (?) citations**:
```bash
# Read the PDF visually - check every citation shows author names
```

3. **Test all 4 files** to ensure no regression:
```bash
# Run all 4 conversions in parallel
```

---

## Part 7: Final Verification Checklist

### For Each of 4 Files

```bash
# 1. Conversion completes without errors
cd <file_directory>
uv run --project /path/to/deep-biblio-tools python -m src.cli md2latex <file.md> -c dpp-fashion
# → Should see "Conversion complete" message

# 2. Check references.bib has no Unknown entries
grep -i "unknown" output/references.bib
# → Should return nothing

grep -i "anonymous" output/references.bib
# → Should return nothing

# 3. Check .tex file has \citep{} commands, not markdown links
grep '\[.*\](http' output/<file>.tex
# → Should return nothing (all converted to \citep{})

grep '\\citep{' output/<file>.tex | wc -l
# → Should return citation count

# 4. Check PDF has no (?) citations
# Use Read tool to visually inspect PDF
# Every citation should show: (Author, Year) or (Author1 et al., Year)
# ZERO citations should show: (?)

# 5. Check .aux file has all citations
grep '\\citation{' output/<file>.aux | wc -l
# → Should match citation count in .tex file
```

### Success Metrics

| File | Citations | PDF Size | Status |
|------|-----------|----------|--------|
| mcp-draft-refined-v4.md | 368 | ~311KB | ✅ MUST WORK |
| fashion-cad-review-v3.md | 71 | ~102KB | ✅ MUST WORK |
| fashion-lca-draft-v3.md | 44 | ~82KB | ✅ MUST WORK |
| 4dgs-fashion-comprehensive-v2.md | TBD | TBD | ✅ MUST WORK |

**ONLY claim success when all 4 files pass ALL 5 checks above.**

---

## Part 8: Testing Infrastructure

### Regression Test Suite (To Be Created)

After all 4 files work, create automated tests:

```python
# tests/test_end_to_end_regression.py

import pytest
from pathlib import Path

TEST_FILES = [
    ("mcp-review", "mcp-draft-refined-v4.md", 368),
    ("fashion_3D_CAD", "fashion-cad-review-v3.md", 71),
    ("fashion_LCA", "fashion-lca-draft-v3.md", 44),
    ("fashion_4DGS", "4dgs-fashion-comprehensive-v2.md", None),  # Count TBD
]

@pytest.mark.parametrize("folder,filename,expected_citations", TEST_FILES)
def test_paper_converts_successfully(folder, filename, expected_citations):
    """Test that known-good papers always convert successfully."""

    # Run conversion
    result = run_conversion(folder, filename, collection="dpp-fashion")

    # Verify success criteria
    assert result.exit_code == 0, "Conversion failed"

    # Check references.bib has no Unknown entries
    bib_content = read_file(result.output_dir / "references.bib")
    assert "Unknown" not in bib_content
    assert "Anonymous" not in bib_content

    # Check .tex has no markdown links
    tex_content = read_file(result.output_dir / f"{result.stem}.tex")
    assert "[" not in tex_content or "](http" not in tex_content

    # Check citation count matches (if known)
    if expected_citations:
        cite_count = tex_content.count(r"\citep{")
        assert cite_count == expected_citations, \
            f"Expected {expected_citations} citations, found {cite_count}"

    # Check PDF compiled
    pdf_path = result.output_dir / f"{result.stem}.pdf"
    assert pdf_path.exists(), "PDF not generated"
    assert pdf_path.stat().st_size > 10000, "PDF too small (likely empty)"

@pytest.mark.parametrize("folder,filename", [f[:2] for f in TEST_FILES])
def test_pdf_has_no_missing_citations(folder, filename):
    """Verify PDF has zero (?) citations by reading it."""

    # This test requires PDF reading capability
    # Use PyPDF2 or similar to extract text
    pdf_text = extract_pdf_text(f"output/{filename.replace('.md', '.pdf')}")

    # Check for (?) pattern
    question_mark_citations = pdf_text.count("(?)")
    assert question_mark_citations == 0, \
        f"Found {question_mark_citations} missing citations (?)"
```

---

## Part 9: The One Remaining Task

### Task Breakdown

1. **[IN PROGRESS]** Create this comprehensive plan ← YOU ARE HERE
2. **[PENDING]** Find and fix the `.group()` error
   - Add traceback logging
   - Run failing conversion
   - Identify exact location
   - Apply fix (Option A or B from Part 6)
   - Verify fix doesn't break other files
3. **[PENDING]** Verify all 4 files convert successfully
   - Run conversions
   - Check each file against 5-point checklist
   - Read PDFs visually for (?) citations
4. **[PENDING]** Create regression test suite
   - Implement tests from Part 8
   - Run `pytest tests/test_end_to_end_regression.py`
   - Ensure all tests pass
5. **[PENDING]** Document root causes fixed
   - Update CLAUDE.md if needed
   - Write session notes summarizing the 2-day work
6. **[PENDING]** Commit working state
   - Clean commit messages
   - Tag as stable version

### Estimated Time
- Fix `.group()` error: **30-60 minutes** (depends on finding it)
- Verify all files: **20 minutes**
- Create test suite: **60 minutes**
- Documentation: **30 minutes**
- **Total: 2.5-3 hours**

---

## Part 10: Code Snippets for LLM Consultation

### How to Add Debugging

```python
# In src/converters/md_to_latex/converter.py
# Around line 800-900 where conversion happens

def convert(self, markdown_file: Path, ...) -> Path:
    """Convert markdown to LaTeX."""

    logger.info(f"Starting conversion: {markdown_file}")

    try:
        # Read markdown
        content = markdown_file.read_text()

        # Extract citations
        logger.info("Extracting citations...")
        citations = self.citation_manager.extract_citations(content)
        logger.info(f"Extracted {len(citations)} citations")

        # ... rest of conversion ...

    except AttributeError as e:
        # CATCH THE .group() ERROR HERE
        if "'str' object has no attribute 'group'" in str(e):
            logger.error("=" * 80)
            logger.error("CAUGHT .group() ERROR!")
            logger.error(f"Error: {e}")
            logger.error("=" * 80)

            # Print full traceback
            import traceback
            logger.error(traceback.format_exc())

            # Print context
            logger.error(f"Current file: {markdown_file}")
            logger.error(f"Citations extracted so far: {len(citations)}")

            logger.error("=" * 80)

        # Re-raise to see in output
        raise
```

### How to Check for Regex Match Object Misuse

```bash
# Search codebase for .group() calls
cd /path/to/deep-biblio-tools
grep -rn "\.group(" src/ --include="*.py"

# Check each result:
# - Is the variable ACTUALLY a Match object?
# - Or is it a string being treated as Match?
```

### Common Patterns to Look For

```python
# PATTERN 1: Forgetting to check if search succeeded
author = re.search(r'pattern', text)  # Could be None or Match
name = author.group(1)  # ❌ Crashes if author is None

# FIX:
author = re.search(r'pattern', text)
if author:
    name = author.group(1)  # ✅ Safe
else:
    name = "Unknown"

# PATTERN 2: Assigning string to variable expected to be Match
author = text.split("(")[0]  # Returns str
# Later in code...
name = author.group(1)  # ❌ author is str, not Match

# FIX: Don't call .group() on strings
author = text.split("(")[0]  # Returns str
name = author.strip()  # ✅ Use string methods

# PATTERN 3: Function returns string but caller expects Match
def extract_author(text):
    return text.split("(")[0]  # Returns str

author = extract_author(citation_text)
name = author.group(1)  # ❌ author is str

# FIX: Change return type or change caller
def extract_author(text):
    match = re.search(r'(.*?)\s*\(', text)
    return match  # Returns Match or None

author = extract_author(citation_text)
if author:
    name = author.group(1)  # ✅ Safe
```

---

## Part 11: Environment and Dependencies

### System Requirements

```bash
# Python 3.11+ with uv package manager
python --version  # → Python 3.11.x or higher
uv --version      # → uv 0.x.x

# Virtual environment location
/Users/petteri/Dropbox/github-personal/deep-biblio-tools/.venv

# Project structure
deep-biblio-tools/
├── src/
│   ├── cli.py                                    # Entry point
│   ├── converters/
│   │   └── md_to_latex/
│   │       ├── converter.py                      # Main conversion logic
│   │       ├── citation_manager.py               # Citation extraction/replacement
│   │       └── latex_generator.py                # LaTeX template generation
│   └── utils/
│       ├── url_utils.py                          # URL normalization
│       └── zotero_client.py                      # Zotero API client
├── tests/
│   └── test_end_to_end_regression.py             # To be created
└── .env                                          # Zotero credentials

# Key dependencies (from pyproject.toml)
pyzotero = "^1.5"                # Zotero API
markdown-it-py = "^3.0"           # Markdown AST parser
bibtexparser = "^2.0"             # BibTeX parser
pylatexenc = "^2.10"              # LaTeX encoder
requests = "^2.31"                # HTTP client for APIs
```

### Running Conversions

```bash
# Template command
cd <publication_directory>
uv run --project <deep-biblio-tools-path> \
  python -m src.cli md2latex <file.md> \
  --collection <zotero-collection> \
  --verbose

# Actual example
cd /Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/fashion_3D_CAD
uv run --project /Users/petteri/Dropbox/github-personal/deep-biblio-tools \
  python -m src.cli md2latex fashion-cad-review-v3.md \
  --collection dpp-fashion \
  --verbose 2>&1 | tee /tmp/conversion.log
```

---

## Part 12: Contact Points and Resources

### Documentation Files

- **CLAUDE.md**: Main behavior contract (NO REGEX, deterministic, etc.)
- **golden-paths.md**: Common development workflows
- **MULTI-HYPOTHESIS-DIAGNOSTIC-PLAN.md**: The 5 hypothesis testing framework we created
- **.claude/sessions/**: Session-specific learnings

### Key Commits (Last 2 Days)

```bash
# View recent work
git log --oneline -20

# Key fixes
476dc90 fix: Strip HTML tags and entities from markdown-it renderer output
33ddbf7 fix: Fix AST-based citation replacement with 3 critical root causes
31d71f4 feat: Implement AST-based citation replacement using markdown-it-py
83b7fab feat: Apply URL normalization to citation extraction and replacement
```

### Testing Philosophy

From CLAUDE.md:
> **NEVER** claim conversion success without verifying PDF has ZERO (?) citations.

From CLAUDE.md:
> **The WORKFLOW must be:**
> 1. Run conversion
> 2. Check references.bib for Unknown/Anonymous entries
> 3. If found, FIX the root cause (don't just report it)
> 4. Re-run conversion
> 5. Read the PDF with Read tool
> 6. Verify EVERY citation shows author names (not ?)
> 7. ONLY THEN claim success

---

## Part 13: Summary for 3rd-Party LLM

### The Assignment

You are being asked to complete a markdown-to-LaTeX-to-PDF citation pipeline. The tool is 95% working - 3 out of 4 test files convert successfully. One file crashes with a Python error.

### What You Need to Do

1. **Find the bug**: Locate where code calls `.group()` on a string instead of a regex Match object
2. **Fix the bug**: Either make it a Match object, or remove the `.group()` call
3. **Verify the fix**: All 4 files must convert to PDF with zero missing citations
4. **Create tests**: Write automated regression tests so this stays fixed

### What Success Looks Like

```bash
# Run this command for each of 4 files - all succeed
uv run python -m src.cli md2latex <file.md> -c dpp-fashion

# Check this for each file - returns nothing
grep -i "unknown" output/references.bib

# Check this for each file - all markdown links converted
grep '\[.*\](http' output/<file>.tex  # Should return nothing

# Read PDF - verify citations show author names, not (?)
```

### Key Constraints

- **NO REGEX** for structured text parsing (use AST parsers)
- **NO file versioning** (don't create _v2, _new files)
- **Deterministic output** (same input = same output always)
- **Zero tolerance** for missing citations in PDFs

### Where to Start

1. Add exception logging (see Part 10, "How to Add Debugging")
2. Run the crashing conversion with `--verbose`
3. Read the traceback to find exact line number
4. Check that code location for `.group()` calls
5. Fix using Option A or B from Part 6
6. Test all 4 files

### Estimated Effort

2-3 hours total:
- 30-60 min: Find and fix bug
- 20 min: Verify all files
- 60 min: Write tests
- 30 min: Document

---

## Part 14: Open Questions / Edge Cases

### Questions to Investigate During Debugging

1. **Does the crashing file have special citation formats?**
   - Comma-separated authors: `[Author1, Author2, Author3 (2024)](...)`
   - Multiple "et al": `[Smith et al. and Jones et al., 2024](...)`
   - Non-ASCII characters: `[Müller (2024)](...)`

2. **Are there hyperlinks being misidentified as citations?**
   - Remember: `[EON](https://www.eon.xyz/)` is NOT a citation
   - Only `[Author (Year)](URL)` or `[Author et al., Year](URL)` are citations

3. **Is the metadata fetching timing out?**
   - Log shows: `Failed to fetch web page metadata for https://www.mckinsey.com/`
   - This is a warning, not the error
   - The `.group()` error happens AFTER metadata fetching

### If the Fix Doesn't Work

If you fix one `.group()` error but another appears:
- **Don't play whack-a-mole** - there may be a systemic issue
- **Check the entire call chain** for that function
- **Consider refactoring** to eliminate regex Match objects entirely
- **Use string methods** (`.split()`, `.startswith()`, `.find()`) instead

### If All Files Work But PDFs Have (?) Citations

This means citation replacement is silently failing:
- Check the "5 Hypotheses" in MULTI-HYPOTHESIS-DIAGNOSTIC-PLAN.md
- Add the diagnostic logging from that document
- Run conversion and analyze which hypothesis fails
- Fix that specific issue

---

## Appendix A: File Locations Quick Reference

```bash
# Project root
/Users/petteri/Dropbox/github-personal/deep-biblio-tools/

# Main conversion logic
src/converters/md_to_latex/converter.py                 # Lines 800-1200

# Citation extraction and replacement
src/converters/md_to_latex/citation_manager.py         # Lines 200-1300

# URL normalization utilities
src/utils/url_utils.py                                   # Lines 1-200

# CLI entry point
src/cli.py                                               # Lines 1-500

# Test files (4 markdown papers)
/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/
├── mcp-review/mcp-draft-refined-v4.md
├── fashion_3D_CAD/fashion-cad-review-v3.md
├── fashion_LCA/fashion-lca-draft-v3.md
└── fashion_4DGS/4dgs-fashion-comprehensive-v2.md

# Output directories (auto-created)
<publication_dir>/output/
├── <filename>.tex
├── <filename>.pdf
├── <filename>.aux
├── <filename>.bbl
└── references.bib
```

## Appendix B: Common LaTeX Compilation Issues

Even after citations work, LaTeX might fail:

### Issue 1: Special Characters Not Escaped
```tex
% WRONG
Price range: $50-200 per unit

% RIGHT (dollar escaped)
Price range: \$50-200 per unit
```

### Issue 2: BibTeX Not Run
```bash
# LaTeX compilation sequence (automatic in converter)
pdflatex main.tex      # First pass - creates .aux
bibtex main            # Process bibliography
pdflatex main.tex      # Second pass - insert citations
pdflatex main.tex      # Third pass - resolve references
```

### Issue 3: Missing LaTeX Packages
```tex
% Common packages needed
\usepackage{natbib}      % For \citep{} commands
\usepackage{hyperref}    % For URLs
\usepackage{graphicx}    % For figures
\usepackage{url}         % For URL formatting
```

The converter includes these automatically.

---

## Appendix C: Decision Tree for Bug Fixing

```
Start: "str object has no attribute 'group'" error
│
├─ Step 1: Run with traceback logging
│  │
│  ├─ Get file path + line number
│  │
│  └─ Identify function name
│
├─ Step 2: Read code at that location
│  │
│  ├─ Find the variable.group() call
│  │
│  └─ Trace backwards to variable assignment
│
├─ Step 3: Determine variable type
│  │
│  ├─ Is it from re.search() / re.match()?
│  │  │
│  │  ├─ YES → Should be Match object
│  │  │  │
│  │  │  └─ Is there a None check?
│  │  │     │
│  │  │     ├─ NO → Add None check (Option A)
│  │  │     └─ YES → Bug is elsewhere
│  │  │
│  │  └─ NO → It's a string, shouldn't use .group()
│  │     │
│  │     └─ Remove .group() call (Option B)
│  │
│  └─ Is it from a function call?
│     │
│     ├─ Check function return type
│     │  │
│     │  ├─ Returns str → Remove .group() at call site
│     │  └─ Returns Match → Add None check
│     │
│     └─ Document expected type in function signature
│
└─ Step 4: Verify fix
   │
   ├─ Run all 4 conversions
   │
   ├─ All succeed?
   │  │
   │  ├─ YES → Verify PDFs (no ? citations)
   │  └─ NO → Debug new error
   │
   └─ Write test to prevent regression
```

---

## End of Plan

**Next Steps**:
1. Hand this document to the 3rd-party LLM consultant
2. They find and fix the `.group()` error
3. Verify all 4 files convert successfully
4. Create regression tests
5. Done!

**Remember**: Success = 4 PDFs with ZERO (?) citations. Nothing less.
