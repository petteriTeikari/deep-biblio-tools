# Systematic Fix Plan: Citation Replacement & Metadata Quality

## Executive Summary

This document outlines a comprehensive, verifiable plan to fix the root causes of:
1. **Citation replacement failures** (markdown links not converted to `\citep{}`)
2. **Metadata quality issues** (malformed Zotero entries with link text as title)
3. **Ampersand escaping bugs** (unescaped `&` in LaTeX output)

**Root Cause**: Using fragile string `.find()` methods instead of AST-based parsing, combined with poor metadata extraction from link text instead of fetching actual webpage/DOI metadata.

## Critical Analysis of OpenAI's Recommendation

### What to Adopt (Excellent Suggestions)

✅ **1. AST-Based Citation Replacement**
- **Why**: Eliminates brittle bracket-matching and URL variant mismatches
- **How**: Use markdown-it-py tokens to find and replace link nodes
- **Benefit**: Handles nested structures, whitespace, URL variants correctly

✅ **2. URL Normalization**
- **Why**: DOIs have multiple forms (http vs https, dx.doi.org vs doi.org, trailing slashes)
- **How**: Canonical mapping `doi:10.1145/3618394` regardless of input variant
- **Benefit**: Reliable citation matching even with URL inconsistencies

✅ **3. Pre-commit Hooks with Banned Pattern Scanner**
- **Why**: Prevents regression to fragile string methods
- **How**: Scan for `.find(`, `.index(`, `re.search(` in src/converters/
- **Benefit**: Enforces architectural constraints automatically

✅ **4. Comprehensive Debug Logging**
- **Why**: Current "function ran but no effect" indicates lack of observability
- **How**: Log before/after each transformation, log citation counts, log matches
- **Benefit**: Immediate visibility into what's failing

✅ **5. Unit Tests for Each Component**
- **Why**: No tests = can't verify fixes work
- **How**: Test URL normalization, AST replacement, ampersand escaping separately
- **Benefit**: Regression prevention

### What to Modify (Good Ideas, Wrong Implementation)

⚠️ **Citation Key Lookup by Normalized URL**
- **OpenAI's Suggestion**: `normalized_to_key = {normalize(url): key}`
- **Problem**: Assumes we HAVE valid metadata for each URL
- **Reality**: Many citations have WRONG metadata (see zotero_deleted_malformed_entries.json)
- **Fix**: Build lookup AFTER validating metadata quality, not just from extracted citations

⚠️ **Rendering Modified AST Back to Markdown**
- **OpenAI's Suggestion**: `md.renderer.render(tokens)` → modified markdown → Pandoc
- **Problem**: Adds extra markdown→markdown conversion step
- **Better**: Replace tokens, write to temp file, pass directly to Pandoc (no re-rendering)
- **Benefit**: One less transformation = fewer edge cases

### What to Reject (Architecturally Wrong)

❌ **Escaping Ampersands in Markdown Before Pandoc**
- **OpenAI says**: Escape `&` to `\&` in markdown link text before Pandoc
- **Problem**: Pandoc will see `\&` as a LaTeX command IN markdown and may re-interpret it
- **Correct**: Escape ampersands in LaTeX OUTPUT, not markdown input
- **Already tried this**: Failed because Pandoc undoes it

❌ **Using Pandoc's citeproc**
- **OpenAI suggests**: "Consider using Pandoc citations [@key]"
- **Problem**: Requires changing entire user workflow and markdown format
- **Reality**: Users write `[Author (Year)](URL)` naturally; we can't change this
- **Decision**: Keep current format, fix the replacement logic

## Root Cause Analysis: The Real Issues

### Issue #1: Metadata Quality (CRITICAL)

**Problem**: Zotero entries have citation text as title
```json
{
  "title": "Fashion Revolution, 2024",  // ❌ WRONG - This is link text, not webpage title
  "author": [{"family": "Fashion Revolution", "given": ""}]
}
```

**Root Cause**: When fetching metadata fails, we use the markdown link text as a fallback:
```python
# citation text: "Fashion Revolution (2024)"
# becomes title: "Fashion Revolution, 2024"
# Should be: Fetch actual webpage title from <title> tag
```

**Consequences**:
1. Zotero has polluted bibliography entries
2. Users have to manually delete/fix them (you just deleted 30+ entries)
3. Citations don't match because titles are wrong
4. BibTeX output is embarrassing

**Fix Plan**:
1. NEVER use link text as title - it's not a title
2. Fetch actual webpage metadata from:
   - DOI → CrossRef API (proper title, authors, journal)
   - arXiv → arXiv API (proper title, authors)
   - Webpage → Scrape `<title>` tag and `<meta>` tags
3. If metadata fetch fails → Mark as "MISSING-METADATA" not "use link text"
4. Generate citations report: "X citations need manual metadata entry"

### Issue #2: Citation Replacement Fails Silently

**Problem**: `replace_citations_in_text()` uses `content.find()](url))` but never logs failures

**Root Cause**: No validation that replacement happened
```python
for key, citation in self.citations.items():
    pos = content.find(f"]({citation.url})")
    if pos == -1:
        # ❌ SILENT FAILURE - no log, no error, no nothing
        continue
```

**Consequences**:
1. Citations stay as markdown links
2. Pandoc leaves them as-is or converts to `\href{}`
3. Ampersands in link text cause LaTeX errors
4. No way to debug which citations failed

**Fix Plan**:
1. Log every citation being searched
2. Log every failure to find pattern
3. Return count of replacements made
4. Assert: `replacements_made == len(academic_citations)` or raise error
5. Write intermediate files for debugging

### Issue #3: URL Matching Fails Due to Variants

**Problem**: Citation extracted with `https://doi.org/10.1145/3618394` but metadata has `http://dx.doi.org/10.1145/3618394/`

**Root Cause**: No URL normalization

**Fix Plan**: Implement OpenAI's `normalize_url_for_lookup()` exactly as suggested

## Systematic Implementation Plan

### Phase 1: Infrastructure & Observability (Day 1)

**Goal**: Make the system observable before fixing anything

#### Task 1.1: Add Comprehensive Logging
```python
# src/converters/md_to_latex/converter.py

logger.info(f"=== CITATION EXTRACTION ===")
logger.info(f"Extracted {len(citations)} citations")
for cit in citations[:5]:  # Log first 5 as sample
    logger.debug(f"  - {cit.text} → {cit.url}")

logger.info(f"=== CITATION REPLACEMENT ===")
logger.info(f"Attempting to replace {len(self.citations)} citations")
replacements = self.citation_manager.replace_citations_in_text_ast(content)
logger.info(f"Successfully replaced {replacements} citations")

if replacements < len(academic_citations):
    missing = len(academic_citations) - replacements
    logger.error(f"❌ {missing} citations were NOT replaced!")
    # Write debug file
    Path("debug/unreplaced_citations.json").write_text(json.dumps(...))
```

**Verification**:
- Run conversion with `--verbose`
- Check logs show citation counts at each stage
- Confirm debug files written when failures occur

#### Task 1.2: Write Intermediate Artifacts
```python
def convert(self, ...):
    # After each major step, write debug output
    (self.output_dir / "debug").mkdir(exist_ok=True)

    # After extraction
    (self.output_dir / "debug/1-extracted-citations.json").write_text(...)

    # After replacement (modified markdown)
    (self.output_dir / "debug/2-markdown-after-replacement.md").write_text(content)

    # After Pandoc
    (self.output_dir / "debug/3-latex-from-pandoc.tex").write_text(latex_content)

    # After escaping
    (self.output_dir / "debug/4-latex-after-escaping.tex").write_text(latex_content)
```

**Verification**:
- Run conversion
- Check debug/ folder has 4 files
- Diff between stages to see what changed

### Phase 2: URL Normalization (Day 1-2)

#### Task 2.1: Implement normalize_url_for_lookup()
Use OpenAI's code EXACTLY as provided in `src/utils/url_utils.py`

**Test Cases**:
```python
def test_doi_normalization():
    assert normalize("https://doi.org/10.1145/3618394") == "doi:10.1145/3618394"
    assert normalize("http://dx.doi.org/10.1145/3618394/") == "doi:10.1145/3618394"
    assert normalize("https://doi.org/10.1145/3618394?foo=bar") == "doi:10.1145/3618394"

def test_arxiv_normalization():
    assert normalize("https://arxiv.org/abs/2101.12345v2") == "arxiv:2101.12345v2"
    assert normalize("https://arxiv.org/pdf/2101.12345.pdf") == "arxiv:2101.12345"
```

**Verification**:
```bash
pytest tests/test_url_normalization.py -v
```

#### Task 2.2: Build Normalized Lookup Map
```python
class CitationManager:
    def __init__(self, citations):
        self.citations = citations
        self.normalized_to_key = {}

        for key, cit in citations.items():
            if cit.url:
                norm = normalize_url_for_lookup(cit.url)
                if norm in self.normalized_to_key:
                    logger.warning(f"URL collision: {norm} maps to both {key} and {self.normalized_to_key[norm]}")
                self.normalized_to_key[norm] = key

        logger.info(f"Built normalized lookup with {len(self.normalized_to_key)} entries")
```

**Verification**:
- Log shows "Built normalized lookup with N entries"
- No collision warnings (or investigate if any)

### Phase 3: AST-Based Replacement (Day 2-3)

#### Task 3.1: Implement replace_citations_in_text_ast()
Use OpenAI's code with modifications:

```python
def replace_citations_in_text_ast(self, content: str) -> tuple[str, int]:
    """
    Returns: (modified_content, replacement_count)
    """
    from markdown_it import MarkdownIt
    md = MarkdownIt()

    tokens = md.parse(content)
    replacements = 0
    failed_urls = []

    i = 0
    while i < len(tokens):
        if tokens[i].type == 'link_open':
            href = self._extract_href(tokens[i])
            key = self._find_key_for_href(href)

            if key:
                # Replace tokens i to link_close with \citep{key}
                j = self._find_link_close(tokens, i)
                link_text = self._extract_link_text(tokens, i, j)

                logger.debug(f"Replacing [{link_text}]({href}) → \\citep{{{key}}}")

                # Create new text token
                new_token = Token("text", "", 0)
                new_token.content = f"\\citep{{{key}}}"

                # Replace tokens[i:j+1] with new_token
                del tokens[i:j+1]
                tokens.insert(i, new_token)
                replacements += 1
            else:
                logger.warning(f"No citation key found for URL: {href}")
                failed_urls.append(href)
                # Don't replace, move past this link
                i += 1
                continue
        i += 1

    # Render back to markdown
    output = md.renderer.render(tokens, md.options, {})

    logger.info(f"AST replacement: {replacements} citations replaced, {len(failed_urls)} failed")
    if failed_urls:
        logger.error(f"Failed URLs: {json.dumps(failed_urls, indent=2)}")

    return output, replacements
```

**Verification**:
```python
def test_ast_replacement_simple():
    citations = {"korosteleva2023": Citation(text="...", url="https://doi.org/10.1145/3618394")}
    manager = CitationManager(citations)

    input_md = "[GarmentCode (Korosteleva & Sorkine-Hornung, 2023)](https://doi.org/10.1145/3618394)"
    output, count = manager.replace_citations_in_text_ast(input_md)

    assert "\\citep{korosteleva2023}" in output
    assert "GarmentCode" not in output
    assert count == 1
```

### Phase 4: Metadata Quality Fix (Day 3-4)

#### Task 4.1: Fix Metadata Extraction

**Problem**: Currently uses link text as title when metadata fetch fails

**Fix**:
```python
# src/scrapers/metadata_fetcher.py

def fetch_metadata(url: str) -> dict:
    """Fetch actual webpage/DOI metadata, not link text"""

    if "doi.org" in url:
        return fetch_crossref_metadata(url)
    elif "arxiv.org" in url:
        return fetch_arxiv_metadata(url)
    else:
        return fetch_webpage_metadata(url)

def fetch_webpage_metadata(url: str) -> dict:
    """Scrape webpage for actual title and metadata"""
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Try various metadata sources in order of reliability
        title = (
            soup.find('meta', property='og:title')['content'] or
            soup.find('meta', attrs={'name': 'title'})['content'] or
            soup.find('title').text or
            "Unknown Title"
        )

        # Extract author from meta tags if available
        author = (
            soup.find('meta', attrs={'name': 'author'})['content'] or
            soup.find('meta', property='article:author')['content'] or
            extract_domain_as_author(url)
        )

        return {
            'title': title.strip(),
            'author': author,
            'url': url,
            'type': 'webpage'
        }
    except Exception as e:
        logger.error(f"Failed to fetch metadata for {url}: {e}")
        return {
            'title': "MISSING-METADATA",  # NOT the link text!
            'author': extract_domain_as_author(url),
            'url': url,
            'type': 'webpage',
            '_needs_manual_review': True
        }
```

**Verification**:
```python
def test_webpage_metadata_extraction():
    metadata = fetch_webpage_metadata("https://www.fashionrevolution.org/wff-2024/")
    assert metadata['title'] != "Fashion Revolution, 2024"  # NOT link text
    assert "Fashion Revolution" in metadata['title'] or metadata['title'] == "MISSING-METADATA"
```

#### Task 4.2: Re-populate Zotero with Correct Metadata
```python
# scripts/fix_malformed_zotero_entries.py

def fix_zotero_entries():
    """Re-fetch metadata for all deleted malformed entries"""

    deleted = json.loads(Path("zotero_deleted_malformed_entries.json").read_text())

    fixed = []
    needs_manual = []

    for entry in deleted:
        url = entry['URL']
        logger.info(f"Re-fetching metadata for {url}")

        metadata = fetch_metadata(url)

        if metadata.get('_needs_manual_review'):
            needs_manual.append({' url': url, 'current_title': entry['title']})
        else:
            fixed.append(metadata)
            # Add back to Zotero via API
            add_to_zotero_collection(metadata, collection="dpp-fashion")

    # Write report
    Path("zotero_fix_report.md").write_text(f"""
    # Zotero Metadata Fix Report

    ## Successfully Fixed: {len(fixed)}
    {json.dumps(fixed, indent=2)}

    ## Needs Manual Review: {len(needs_manual)}
    {json.dumps(needs_manual, indent=2)}
    """)
```

**Verification**:
```bash
python scripts/fix_malformed_zotero_entries.py
# Check zotero_fix_report.md
# Manually review "Needs Manual Review" entries
```

### Phase 5: Pre-commit Enforcement (Day 4)

#### Task 5.1: Banned Pattern Scanner
Use OpenAI's `check_banned_string_wrangling.py` EXACTLY as provided

**Verification**:
```bash
python tools/check_banned_string_wrangling.py
# Should pass (no banned patterns found)

# Test it catches violations
echo "content.find('test')" >> src/converters/test.py
python tools/check_banned_string_wrangling.py
# Should fail with error message
```

#### Task 5.2: Pre-commit Configuration
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: banned-patterns
        name: "Ban fragile string methods"
        entry: tools/check_banned_string_wrangling.py
        language: system
        types: [python]
        pass_filenames: false

      - id: citation-tests
        name: "Run citation tests"
        entry: pytest tests/test_citation*.py -q
        language: system
        pass_filenames: false

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.8
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
```

**Verification**:
```bash
pre-commit install
pre-commit run --all-files
# Should pass all hooks
```

### Phase 6: Comprehensive Testing (Day 5)

#### Test Suite Structure
```
tests/
├── test_url_normalization.py      # URL variants → canonical form
├── test_citation_extraction.py    # Markdown → Citation objects
├── test_citation_replacement.py   # AST-based replacement
├── test_metadata_fetching.py      # DOI/arXiv/webpage → metadata
└── test_integration.py            # End-to-end conversion
```

#### Critical Test Cases
```python
def test_citation_with_ampersand():
    """Regression test for GarmentCode citation"""
    input_md = "[GarmentCode (Korosteleva & Sorkine-Hornung, 2023)](https://doi.org/10.1145/3618394)"

    # Should extract citation
    citations = extract_citations(input_md)
    assert len(citations) == 1

    # Should fetch correct metadata (not use link text as title)
    metadata = fetch_metadata(citations[0].url)
    assert metadata['title'] != "GarmentCode (Korosteleva & Sorkine-Hornung, 2023)"

    # Should replace in markdown
    output, count = replace_citations_ast(input_md, {citations[0].url: "korosteleva2023"})
    assert "\\citep{korosteleva2023}" in output
    assert count == 1

    # Should compile to PDF without ampersand errors
    latex = pandoc_convert(output)
    pdf = compile_latex(latex)
    assert pdf_has_no_errors(pdf)
```

**Verification**:
```bash
pytest tests/ -v --cov=src/converters --cov-report=html
# Target: >90% coverage on citation_manager.py
```

### Phase 7: Documentation & Knowledge Transfer (Day 5-6)

#### Task 7.1: Update PLAYWRIGHT-TESTING-GUIDE.md

Create comprehensive guide at `/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/figures/PLAYWRIGHT-TESTING-GUIDE.md`:

```markdown
# Testing & Validation Guide: Citation Processing Pipeline

## Context: Why This Guide Exists

We discovered systematic issues with citation replacement where:
1. String `.find()` methods failed on URL variants
2. Metadata extraction used link text as titles
3. No tests caught these failures before production

This guide ensures future changes are properly validated.

## Core Principle: AST Over String Manipulation

❌ **NEVER DO THIS**:
\`\`\`python
pos = content.find("](" + url + ")")  # Brittle, fails on variants
\`\`\`

✅ **ALWAYS DO THIS**:
\`\`\`python
tokens = md.parse(content)
for token in tokens:
    if token.type == 'link_open':
        # Robust parsing
\`\`\`

## Pre-commit Workflow

Before EVERY commit:
1. `pre-commit run --all-files` - catches banned patterns
2. `pytest tests/test_citation*.py -v` - verifies citation logic
3. Manual check: Debug artifacts in `output/debug/`

## Testing Visualization Changes

[Rest of Playwright testing guide for UI/visualization testing]
```

#### Task 7.2: Document Root Cause Lessons
```markdown
# LESSONS-LEARNED.md

## Root Cause: String Methods vs AST Parsing

### What Went Wrong
- Used `str.find()` to locate citations in markdown
- Assumed URLs would match exactly (no variants)
- No logging to detect silent failures

### Why It Manifested as Ampersand Errors
1. Citation not replaced due to URL mismatch
2. Raw markdown link remained in text
3. Pandoc left it as-is (unconverted)
4. Unescaped `&` in link text → LaTeX error

### The Fix
- AST-based replacement (markdown-it-py tokens)
- URL normalization (canonical forms)
- Comprehensive logging (visibility)
- Pre-commit hooks (prevention)

## Root Cause: Metadata Quality

### What Went Wrong
- When webpage fetch failed, used link text as title
- Created polluted Zotero entries
- Users had to manually delete 30+ entries

### The Fix
- Fetch actual webpage `<title>` tags
- Never use link text as title fallback
- Mark as "MISSING-METADATA" if fetch fails
- Generate manual review report
```

## Verification & Success Criteria

### Phase-by-Phase Acceptance

**Phase 1 Complete When**:
- ✅ Logs show citation counts at each stage
- ✅ Debug artifacts written to `output/debug/`
- ✅ Can diff artifacts to see transformations

**Phase 2 Complete When**:
- ✅ `test_url_normalization.py` passes 100%
- ✅ Log shows "Built normalized lookup with N entries"
- ✅ No URL collision warnings

**Phase 3 Complete When**:
- ✅ `test_citation_replacement.py` passes 100%
- ✅ GarmentCode citation replaced correctly
- ✅ Log shows "X citations replaced, Y failed"

**Phase 4 Complete When**:
- ✅ `test_metadata_fetching.py` passes 100%
- ✅ No webpage has link text as title
- ✅ `zotero_fix_report.md` shows fixes applied

**Phase 5 Complete When**:
- ✅ Pre-commit hook blocks commits with `.find(`
- ✅ `pre-commit run --all-files` passes
- ✅ Can't commit banned patterns

**Phase 6 Complete When**:
- ✅ All test suites pass
- ✅ Coverage >90% on citation modules
- ✅ Integration test: CAD paper compiles with ZERO (?) citations

**Phase 7 Complete When**:
- ✅ PLAYWRIGHT-TESTING-GUIDE.md updated
- ✅ LESSONS-LEARNED.md documents root causes
- ✅ Future maintainers can understand "why"

### Final Integration Test

```bash
# Clean slate
rm -rf output/

# Run conversion on problematic CAD paper
uv run python -m src.cli md2latex fashion-cad-review-v3.md --collection dpp-fashion

# Verify success
assert_file_exists output/fashion-cad-review-v3.pdf
assert_no_latex_errors output/fashion-cad-review-v3.log
assert_zero_question_mark_citations output/fashion-cad-review-v3.pdf
```

## Timeline & Resources

- **Day 1**: Infrastructure & Observability (4-6 hours)
- **Day 2**: URL Normalization (2-3 hours)
- **Day 3**: AST Replacement (4-6 hours)
- **Day 4**: Metadata Quality & Pre-commit (4-5 hours)
- **Day 5**: Testing Suite (6-8 hours)
- **Day 6**: Documentation (2-3 hours)

**Total**: ~25-35 hours of focused work

## Risk Mitigation

**Risk**: AST replacement breaks existing working citations
**Mitigation**:
- Test on small file first
- Keep old `replace_citations_in_text()` as fallback
- Add feature flag: `USE_AST_REPLACEMENT=true`

**Risk**: Webpage fetching times out on slow sites
**Mitigation**:
- 10-second timeout with retry
- Cache successful fetches
- Fallback to domain-based author

**Risk**: Pre-commit hook too slow
**Mitigation**:
- Only run scanner on `.find(` pattern (fast regex)
- Only run tests on changed files
- Cache pytest results with `--lf`

## Next Steps

1. ✅ Read and approve this plan
2. Start Phase 1 (logging infrastructure)
3. Run pilot test on single paper
4. Proceed through phases systematically
5. Document learnings as we go

This plan is comprehensive, verifiable, and addresses root causes rather than symptoms.
