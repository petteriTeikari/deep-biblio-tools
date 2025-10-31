# Actionable Plan: Fix Citation Matching to Reduce False "Missing" Reports

**Date**: 2025-10-31
**Status**: Ready for implementation
**Problem**: Reporting 153 "missing citations" when most should match (GitHub repos, company sites shouldn't be citations)
**Root Cause**: (1) Not classifying citations vs inline links, (2) arXiv version matching not being used properly

---

## Background Documents

**Required reading before implementing**:

1. **[bibtex-citation-generation-and-classification.md](../reference/bibtex-citation-generation-and-classification.md)**
   - What counts as citation vs inline hyperlink
   - Pattern: `[Author (Year)](URL)` = citation
   - Pattern: `[Text](URL)` = inline link
   - GitHub/company sites/social media = NOT citations

2. **[identifier-matching-strategies.md](../reference/identifier-matching-strategies.md)**
   - Multi-strategy matching: DOI → arXiv → ISBN → URL
   - arXiv version stripping implementation (ALREADY EXISTS)
   - Code references to `citation_matcher.py` and `utils.py`

---

## Problem Analysis

### Current Behavior

**Log output**: "153 citations not found in RDF"

**From /tmp/missing-citations.txt** (19 unique URLs):
```
https://arxiv.org/abs/2409.08006v1          ← arXiv with version
https://arxiv.org/abs/2502.02533v1          ← arXiv with version
https://arxiv.org/html/2410.20199           ← arXiv html variant
https://doi.org/10.1016/j.jclepro.2024.141024  ← Academic (should match)
https://github.com/emcie-co/parlant         ← GitHub (NOT a citation!)
https://github.com/rednote-hilab/dots.ocr   ← GitHub (NOT a citation!)
https://github.com/yusufkaraaslan/Skill_Seekers/ ← GitHub (NOT a citation!)
https://haelixa.com/                        ← Company site (NOT a citation!)
https://oritain.com//                       ← Company site (NOT a citation!)
https://www.entrupy.com/                    ← Company site (NOT a citation!)
https://www.eon.xyz/                        ← Company site (NOT a citation!)
https://x.com/SIGKITTEN/status/...          ← Social media (NOT a citation!)
```

### Issues Identified

1. **GitHub/company/social URLs being treated as citations**
   - Should be inline links: `\href{URL}{Text}`
   - Should NOT appear in "missing citations" list
   - Should NOT generate BibTeX entries

2. **arXiv version numbers not stripped during matching**
   - Code EXISTS to strip versions (`extract_arxiv_id()`, `normalize_arxiv_url()`)
   - But may not be used during citation extraction
   - Result: `2410.10762v1` doesn't match `2410.10762` in RDF

3. **arXiv URL variants (html vs abs) not normalized**
   - Code EXISTS to normalize (`normalize_arxiv_url()`)
   - But may not be used consistently

---

## Solution Overview

### Phase 1: Citation Classification (MUST DO FIRST)

**Goal**: Don't extract GitHub/company/social links as citations

**Implementation**: Update `citation_extractor_unified.py`

**Key function**: `is_citation_pattern(text: str) -> bool`

### Phase 2: Use Existing CitationMatcher

**Goal**: Reuse `citation_matcher.py` instead of reimplementing matching

**Current status**: CitationMatcher class EXISTS with all matching strategies

**Need to verify**: Is CitationManager using CitationMatcher?

### Phase 3: Verification

**Goal**: Confirm missing citations list is now accurate (academic papers only)

**Expected result**: ~10-20 truly missing academic papers, NOT 153

---

## Implementation Steps

### Step 1: Find Citation Extraction Code

**File**: `src/converters/md_to_latex/citation_extractor_unified.py`

**Search for**:
- How citations are extracted from markdown
- Is `is_citation_pattern()` or similar function used?
- Are GitHub/company URLs being filtered out?

**Action**:
```bash
# Find the extraction logic
grep -n "def extract" src/converters/md_to_latex/citation_extractor_unified.py

# Check if URL classification exists
grep -n "github\|company\|social" src/converters/md_to_latex/citation_extractor_unified.py -i
```

### Step 2: Verify CitationMatcher Usage

**File**: `src/converters/md_to_latex/citation_manager.py`

**Search for**:
- Is `CitationMatcher` class imported and used?
- Or is matching reimplemented with ad-hoc logic?

**Action**:
```bash
# Check if CitationMatcher is used
grep -n "CitationMatcher" src/converters/md_to_latex/citation_manager.py

# Check if extraction functions are called
grep -n "extract_arxiv_id\|extract_doi_from_url\|normalize_arxiv_url" src/converters/md_to_latex/citation_manager.py
```

### Step 3: Read Existing Code

**Files to read**:
1. `citation_extractor_unified.py` - How are citations extracted?
2. `citation_manager.py` - Is CitationMatcher being used?
3. `bibliography_sources.py` - How are RDF entries indexed?

**Goal**: Understand what's ALREADY implemented vs what needs adding

### Step 4: Implement Citation Classification

**Where**: `citation_extractor_unified.py`

**Add functions** (reference: [bibtex-citation-generation-and-classification.md](../reference/bibtex-citation-generation-and-classification.md)):

```python
def is_citation_pattern(text: str) -> bool:
    """Check if link text has author/year citation pattern."""
    # Use string methods ONLY (no regex per CLAUDE.md)

    # Check for year in parentheses: "(YYYY)"
    if "(" in text and ")" in text:
        paren_content = text[text.find("(")+1:text.find(")")]
        if paren_content.isdigit() and len(paren_content) == 4:
            return True

    # Check for comma-separated year: ", YYYY"
    if ", 20" in text:  # Assumes 2000-2099
        parts = text.split(", ")
        if len(parts) >= 2:
            year_part = parts[-1].strip()
            if year_part.isdigit() and len(year_part) == 4:
                return True

    return False


def classify_url(url: str) -> str:
    """Classify URL as academic, company, code repository, etc."""
    url_lower = url.lower()

    # Non-academic sources (should be inline links, NOT citations)
    if "github.com" in url_lower:
        return "code_repository"
    if "x.com" in url_lower or "twitter.com" in url_lower:
        return "social_media"
    if any(domain in url_lower for domain in [
        ".xyz", "entrupy.com", "haelixa.com", "oritain.com", "eon.xyz"
    ]):
        return "company_website"

    # Academic sources (should be citations)
    if any(domain in url_lower for domain in [
        "doi.org", "dx.doi.org",
        "arxiv.org",
        "pubmed", "ncbi.nlm.nih.gov",
        "sciencedirect.com", "springer.com", "ieee.org"
    ]):
        return "academic"

    # Books
    if "amazon." in url_lower and "/dp/" in url_lower:
        return "book"

    return "unknown"


def should_create_citation(text: str, url: str) -> bool:
    """Determine if this link should create a BibTeX entry."""
    # MUST have author/year pattern
    if not is_citation_pattern(text):
        return False

    # Classify URL type
    url_type = classify_url(url)

    # Academic sources and books → citation
    if url_type in ["academic", "book"]:
        return True

    # Non-academic sources → inline link (even with author/year pattern)
    if url_type in ["code_repository", "social_media", "company_website"]:
        return False

    # Unknown → default to citation if it has author/year pattern
    return True
```

**Integrate into extraction**:

```python
def extract_citations(markdown_content: str) -> list[Citation]:
    """Extract citations from markdown, filtering out inline links."""
    ast = markdown_it_parser.parse(markdown_content)
    citations = []

    for link_node in ast.find_all(type="link"):
        text = link_node.text  # e.g., "Fletcher (2016)" or "GitHub"
        url = link_node.url    # e.g., "https://..."

        # NEW: Check if this should be a citation
        if should_create_citation(text, url):
            citations.append(Citation(text=text, url=url))
        else:
            logger.debug(f"Skipping non-citation link: {text} → {url}")

    return citations
```

### Step 5: Ensure CitationMatcher is Used

**Where**: `citation_manager.py`

**Check**: Is `CitationMatcher` instantiated and used?

**If NOT currently used**, add:

```python
from src.converters.md_to_latex.citation_matcher import CitationMatcher

class CitationManager:
    def __init__(self, ...):
        # ... existing init ...

        # NEW: Initialize CitationMatcher with RDF entries
        if hasattr(self, 'rdf_entries') and self.rdf_entries:
            self.citation_matcher = CitationMatcher(
                zotero_entries=self.rdf_entries,
                allow_zotero_write=False  # Emergency mode: NO writes
            )
            logger.info(f"CitationMatcher initialized with {len(self.rdf_entries)} entries")


    def match_citation(self, url: str) -> tuple[dict | None, str]:
        """Match citation against Zotero RDF entries."""
        # NEW: Use CitationMatcher if available
        if hasattr(self, 'citation_matcher'):
            entry, strategy = self.citation_matcher.match(url)
            if entry:
                logger.info(f"Matched by {strategy}: {url[:80]}")
                return entry, strategy

        # Fallback to old logic (or remove if CitationMatcher handles all cases)
        logger.warning(f"CitationMatcher not available, using fallback matching")
        # ... old matching code ...
```

### Step 6: Verify arXiv Normalization is Applied

**Goal**: Ensure `normalize_arxiv_url()` is called during matching

**Check in CitationMatcher** (`citation_matcher.py:198`):

```python
# Strategy 3: arXiv matching (for preprints)
arxiv_id = extract_arxiv_id(citation_url)  # ← Should strip version
if arxiv_id:
    normalized_arxiv = arxiv_id.lower()
    if normalized_arxiv in self.arxiv_index:
        self.stats["matched_by_arxiv"] += 1
        return self.arxiv_index[normalized_arxiv], "arxiv"
```

**This code ALREADY strips versions** (see `utils.py:821-827`).

**But**: Need to verify RDF entries are also indexed WITHOUT versions

**Check index building** (`citation_matcher.py:102-120`):

```python
# arXiv index
url = entry.get("URL", "")
if url and "arxiv.org" in url.lower():
    arxiv_id = extract_arxiv_id(url)  # ← Should strip version from RDF too
    if arxiv_id:
        self.arxiv_index[arxiv_id.lower()] = entry
```

**This is CORRECT** - versions stripped from both markdown URLs AND RDF URLs.

### Step 7: Test with Missing Citations List

**After implementing Steps 4-6**, re-run conversion:

```bash
time uv run python scripts/deterministic_convert.py \
  "/path/to/mcp-draft-refined-v5.md" \
  --rdf "/path/to/dpp-fashion-zotero.rdf" \
  --output-dir "/tmp/test-matching" \
  --allow-failures \
  2>&1 | tee /tmp/test-matching.log
```

**Check new missing citations count**:

```bash
grep "citations not found in RDF" /tmp/test-matching.log
```

**Expected**:
- GitHub/company/social URLs: NOT in missing list (classified as inline links)
- arXiv with versions: MATCHED (version stripped)
- arXiv html/pdf variants: MATCHED (normalized to /abs/)
- Truly missing academic papers: ~10-20 (down from 153)

### Step 8: Generate Clean Missing Citations List

**After verification**, generate list of ONLY academic papers missing from Zotero:

```python
def generate_missing_citations_report(citations: list[Citation], output_file: Path):
    """Generate report of truly missing academic citations."""
    missing_academic = []

    for citation in citations:
        if citation.key.startswith("failedAutoAdd"):
            # This citation was not found in RDF

            # Classify it
            if should_create_citation(citation.text, citation.url):
                # This is an academic citation that's truly missing
                missing_academic.append({
                    "text": citation.text,
                    "url": citation.url,
                    "type": classify_url(citation.url)
                })

    # Write markdown report
    with open(output_file, "w") as f:
        f.write("# Missing Academic Citations - Manual Review Required\n\n")
        f.write(f"**Date**: {datetime.now().isoformat()}\n")
        f.write(f"**Total**: {len(missing_academic)} citations\n\n")
        f.write("---\n\n")

        for i, citation in enumerate(missing_academic, 1):
            f.write(f"## {i}. {citation['text']}\n\n")
            f.write(f"- **URL**: [{citation['url']}]({citation['url']})\n")
            f.write(f"- **Type**: {citation['type']}\n")
            f.write(f"- **Action**: Review and add to Zotero if appropriate\n\n")

    logger.info(f"Missing citations report written to: {output_file}")
    logger.info(f"Found {len(missing_academic)} truly missing academic citations")
```

---

## Success Criteria

### Before Fix (Current State)

- ✗ 153 "citations not found in RDF" reported
- ✗ GitHub repos in missing citations list
- ✗ Company websites in missing citations list
- ✗ Social media in missing citations list
- ✗ arXiv v1/v2 URLs not matching
- ✗ arXiv html/pdf variants not matching

### After Fix (Expected State)

- ✅ ~10-20 truly missing academic citations reported
- ✅ GitHub repos classified as inline links (NOT in missing list)
- ✅ Company websites classified as inline links (NOT in missing list)
- ✅ Social media classified as inline links (NOT in missing list)
- ✅ arXiv v1/v2 URLs matching correctly (version stripped)
- ✅ arXiv html/pdf/abs variants matching correctly (normalized)
- ✅ Clean report of truly missing citations with clickable URLs

---

## Code References

### Existing Code to Reuse

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| `CitationMatcher` | `citation_matcher.py` | 33-310 | ✅ IMPLEMENTED |
| `extract_arxiv_id()` | `utils.py` | 797-840 | ✅ IMPLEMENTED (strips versions) |
| `normalize_arxiv_url()` | `utils.py` | 468-507 | ✅ IMPLEMENTED (normalizes variants) |
| `extract_doi_from_url()` | `utils.py` | 714-760 | ✅ IMPLEMENTED |
| `extract_isbn_from_url()` | `utils.py` | 761-796 | ✅ IMPLEMENTED |
| `normalize_url()` | `utils.py` | 16-467 | ✅ IMPLEMENTED |

### Code to Add

| Component | File | Purpose | Status |
|-----------|------|---------|--------|
| `is_citation_pattern()` | `citation_extractor_unified.py` | Check if link text has author/year | ❌ NEEDS ADDING |
| `classify_url()` | `citation_extractor_unified.py` | Classify URL type (academic/GitHub/etc) | ❌ NEEDS ADDING |
| `should_create_citation()` | `citation_extractor_unified.py` | Decide if link becomes citation | ❌ NEEDS ADDING |
| CitationMatcher integration | `citation_manager.py` | Use CitationMatcher for matching | ⚠️ VERIFY USAGE |

---

## Verification Checklist

### After Implementation

- [ ] Read `citation_extractor_unified.py` - understand current extraction logic
- [ ] Read `citation_manager.py` - verify CitationMatcher usage
- [ ] Implement `is_citation_pattern()` function
- [ ] Implement `classify_url()` function
- [ ] Implement `should_create_citation()` function
- [ ] Integrate classification into extraction logic
- [ ] Verify CitationMatcher is instantiated and used
- [ ] Run test conversion with updated code
- [ ] Check missing citations count (should be ~10-20, not 153)
- [ ] Generate clean missing citations report
- [ ] Verify GitHub/company URLs NOT in missing list
- [ ] Verify arXiv versions matched correctly

### Smoke Test

```bash
# Run conversion
time uv run python scripts/deterministic_convert.py \
  "mcp-draft-refined-v5.md" \
  --rdf "dpp-fashion-zotero.rdf" \
  --output-dir "/tmp/test" \
  --allow-failures \
  2>&1 | tee test.log

# Check results
grep "citations not found in RDF" test.log          # Should be ~10-20
grep "Matched by arxiv" test.log | head             # Should see arXiv matches
grep "Matched by doi" test.log | head               # Should see DOI matches
grep "Skipping non-citation link" test.log | head   # Should see GitHub/company skipped

# Verify references.bib
grep -c "@" /tmp/test/references.bib                 # Count BibTeX entries
grep "github.com" /tmp/test/references.bib           # Should be ZERO
grep "haelixa.com" /tmp/test/references.bib          # Should be ZERO

# Check LaTeX output
grep "\\href{https://github.com" /tmp/test/*.tex | head  # GitHub as inline links
grep "\\cite{" /tmp/test/*.tex | head                    # Academic citations
```

---

## Timeline

### Immediate (Next 30 Minutes)

1. Read `citation_extractor_unified.py` (understand current logic)
2. Read `citation_manager.py` (verify CitationMatcher usage)
3. Document findings

### Short Term (This Session)

4. Implement citation classification functions
5. Integrate into extraction logic
6. Verify CitationMatcher usage
7. Run test conversion
8. Generate missing citations report

### Validation (After Implementation)

9. User reviews missing citations list
10. User adds truly missing papers to Zotero manually
11. Re-run conversion → should match ~100%

---

## References

### Background Documentation

1. **[bibtex-citation-generation-and-classification.md](../reference/bibtex-citation-generation-and-classification.md)**
   - Citation vs hyperlink patterns
   - Classification logic
   - BibTeX entry type rules

2. **[identifier-matching-strategies.md](../reference/identifier-matching-strategies.md)**
   - Multi-strategy matching implementation
   - arXiv version stripping
   - DOI/ISBN/URL normalization
   - Code references and test cases

### Historical Context

3. **[COMPREHENSIVE-MATCHING-ANALYSIS-2025-10-31.md](./COMPREHENSIVE-MATCHING-ANALYSIS-2025-10-31.md)**
   - Historical matching failures
   - Root causes
   - Solutions and hypotheses

4. **[plea-to-openai-robust-matching.md](../plea-to-openai-robust-matching.md)**
   - Original proposal for multi-strategy matching
   - Expected success rate improvements

5. **[zotero-matching-vision.md](../zotero-matching-vision.md)**
   - "Keys are IDENTITY, not MATCH CRITERIA" principle
   - What NOT to do (key matching, validation)

### Implementation Files

6. `src/converters/md_to_latex/citation_matcher.py` - Multi-strategy matcher (IMPLEMENTED)
7. `src/converters/md_to_latex/utils.py` - Extraction functions (IMPLEMENTED)
8. `src/converters/md_to_latex/citation_extractor_unified.py` - Extraction logic (NEEDS UPDATES)
9. `src/converters/md_to_latex/citation_manager.py` - Integration point (VERIFY USAGE)

---

**Status**: Ready for implementation
**Next Step**: Read existing code to understand current extraction logic
**Expected Outcome**: Missing citations reduced from 153 to ~10-20 truly missing academic papers
