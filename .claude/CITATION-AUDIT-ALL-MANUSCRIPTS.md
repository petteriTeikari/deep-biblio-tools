# Citation Quality Audit - All 4 Manuscripts

**Date**: 2025-10-27
**Status**: COMPREHENSIVE AUDIT COMPLETED

## Executive Summary

Systematic audit of all 4 working paper manuscripts reveals **significant citation quality issues**:

| Manuscript | Total Citations | Problematic | Error Rate | Status |
|-----------|----------------|-------------|------------|---------|
| **fashion-cad-review-v3.md** | 67 | 14 | **21%** | CRITICAL |
| **mcp-draft-refined-v4.md** | 558 | 139 | **25%** | CRITICAL |
| **fashion-lca-draft-v3.md** | 54 | 6 | **11%** | WARNING |
| **4dgs-fashion-comprehensive-v2.md** | 0 | 0 | **0%** | OK |
| **TOTAL** | **679** | **159** | **23%** | CRITICAL |

**Nearly 1 in 4 citations (23%) have data quality issues that will produce garbage BibTeX entries.**

## Problem Categories

### 1. fashion-cad-review-v3.md (21% error rate)

**Critical Issues**:
- Personal/university websites: 2 citations
- Project pages (GitHub.io): 1 citation
- Company websites: 2 citations
- Research portals: 4 citations
- Other problematic: 5 citations

**Detailed List**:
1. `[Chen et al. (2024)](https://engineering.purdue.edu/~chen2086/)` - Personal website (4 occurrences)
2. `[GaussianVTON (Cao et al., 2024)](https://yukangcao.github.io/GS-VTON/)` - Project page, should be https://arxiv.org/abs/2410.05259
3. `[Fiori et al. (2024)](https://researchdiscovery.drexel.edu/esploro/...)` - University repository (4 occurrences)
4. `[Company (2024)](https://www.mckinsey.com)` - Company website (2 occurrences)
5. `[di Milano (2024)](https://www.polimi.it)` - University homepage
6. `[Making (2023)](https://www.smartpatternmaking.com/blogs/...)` - Blog post
7. `[Boyd & Vandenberghe (2004)](https://web.stanford.edu/~boyd/cvxbook/)` - Personal website (2 occurrences)

**Unicode Encoding Issues**:
- Kuźniak → Kuniak (author name corruption)

**Wrong Source Identification**:
- Kuźniak paper labeled as "arXiv" when it's actually published in JINST
- DOI: 10.1088/1748-0221/20/05/C05006
- Should use Better BibTeX key: `kuzniakNewCandidatePolymeric2025`

### 2. mcp-draft-refined-v4.md (25% error rate)

**Critical Issues**:
- Company/blog URLs: 48 citations
- Personal/university websites: 8 citations
- GitHub repositories: 1 citation
- Other problematic: 82 citations

**Sample Problematic Citations**:
1. `[Fletcher, 2016](https://www.amazon.de/-/en/Craft-Use-Post-Growth-Kate-Fletcher/dp/1138021016)` - Amazon book link
2. `[BBC, 2018](https://www.bbc.com/news/business-44885983)` - News article
3. `[Bloomberg, 2018](https://www.bloomberg.com/news/articles/...)` - News article
4. `[Karpathy (2025)](https://www.youtube.com/watch?v=lXUZvyajciY)` - YouTube video
5. `[Anthropic, 2024](https://modelcontextprotocol.io/docs/concepts/architecture)` - Documentation site (14 occurrences)
6. `[Google, 2024](https://developers.google.com/agent-to-agent)` - Developer docs (11 occurrences)
7. `[Newman, 2021](https://www.oreilly.com/library/view/building-microservices-2nd/9781492034018/)` - O'Reilly book link (3 occurrences)
8. `[Wooldridge, 2009](https://www.amazon.de/-/en/Introduction-MultiAgent-Systems-Second/dp/0470519460)` - Amazon book link (2 occurrences)
9. `[Zhuang, 2025](https://github.com/EvanZhuang/knowledge_flow)` - GitHub repo
10. `[NYU Stern Center for Business and Human Rights, 2015](https://bhr.stern.nyu.edu/rana-plaza)` - University website
11. `[Sodhi and Wang, 2019]()` - **EMPTY URL!**

**Grey Literature Issues**:
- EU regulation documents (should be acceptable)
- NIST publications (should be acceptable)
- NBER working papers (should be acceptable)
- Industry reports and white papers (questionable)

### 3. fashion-lca-draft-v3.md (11% error rate)

**Critical Issues**:
- All 6 problematic citations point to the SAME URL!
- `[European Commission 2025](https://pefapparelandfootwear.eu/)` (6 occurrences)

**Analysis**:
- This is an EU PEF (Product Environmental Footprint) project site
- May be legitimate grey literature, but not a traditional academic paper
- Should verify if this should be treated as a report/standard rather than academic citation

### 4. 4dgs-fashion-comprehensive-v2.md (0% error rate)

**Status**: ✅ **CLEAN** - No citations found in this manuscript

**Note**: This paper may be in early draft stage or may reference figures/equations only without citations.

## Root Causes

### 1. No URL Validation in Converter
**Current Behavior**: Converter silently accepts ANY URL and tries to extract metadata, producing nonsense BibTeX entries.

**Should Do**:
- Detect non-paper URLs (project pages, personal sites, company blogs)
- Flag or reject citations with suspicious URLs
- Provide clear warnings to user

### 2. Grey Literature Handling
**Problem**: No clear policy on how to handle:
- Government reports and standards
- Industry white papers
- News articles and blog posts
- YouTube videos and documentation sites
- Books (Amazon/O'Reilly links instead of publisher DOIs)

**Needed**: Clear categorization of what counts as citable vs uncitable sources.

### 3. Better BibTeX Key Strategy
**Problem**: Generated short keys (`cao2024a`, `nakayama2024`) instead of Better BibTeX keys from Zotero.

**Solution**: Always use Zotero's Better BibTeX keys (e.g., `kuzniakNewCandidatePolymeric2025`).

### 4. No Post-Conversion Quality Checks
**Missing**:
- Author name encoding verification (Unicode)
- Hyperlink presence verification
- Source type verification (arXiv vs DOI vs journal)
- BibTeX key validation against Zotero
- Empty URL detection

## Impact Assessment

**Current State**: PDFs compile with "0 missing citations" but contain:
- 159 citations with questionable/wrong metadata (23% of total)
- Unknown number with encoding issues
- Unknown number with wrong BibTeX keys
- At least 1 citation with empty URL

**Publication Readiness**: ❌ **NOT READY**

## Recommended Actions

### Immediate (Manual Fixes Required)

1. **fashion-cad-review-v3.md**:
   - Fix GaussianVTON URL: `https://yukangcao.github.io/GS-VTON/` → `https://arxiv.org/abs/2410.05259`
   - Find actual paper for Chen LBCO (personal website)
   - Find actual paper for Fiori et al. (research portal)
   - Verify McKinsey and Politecnico di Milano citations (may need to remove or find papers)
   - Fix Kuźniak URL: `https://arxiv.org/abs/2504.01483` → `https://doi.org/10.1088/1748-0221/20/05/C05006`

2. **mcp-draft-refined-v4.md**:
   - Review all 139 problematic citations
   - Decide policy on grey literature (EU docs, NIST, NBER, etc.)
   - Fix Sodhi and Wang empty URL
   - Convert Amazon/O'Reilly book links to proper publisher citations
   - Decide on news articles (BBC, Bloomberg) - keep or remove?
   - Handle documentation sites (Anthropic MCP, Google A2A) - likely should NOT be in bibliography

3. **fashion-lca-draft-v3.md**:
   - Review European Commission PEF citations
   - Decide if this should be a report/standard citation
   - Possibly consolidate 6 identical citations into one reference

### Short-term (Tool Enhancements)

1. **URL Validator**:
   - Create `scripts/validate_citation_urls.py`
   - Categorize URLs: academic papers, grey literature, uncitable
   - Generate warnings for each manuscript

2. **Better BibTeX Integration**:
   - Modify citation_manager.py to ALWAYS use Zotero Better BibTeX keys
   - Never generate short keys

3. **Quality Report Generator**:
   - Create post-conversion validation report
   - Check: author names, hyperlinks, source types, BibTeX keys, empty URLs
   - Output clear list of issues requiring manual review

### Long-term (Pipeline Improvements)

1. **Smart URL Resolution**:
   - Parse project pages for paper links
   - Try DOI lookup from title/authors
   - Fallback to Semantic Scholar/CrossRef search

2. **Grey Literature Policy**:
   - Define clear categories: standards, reports, news, documentation
   - Implement appropriate BibTeX entry types (@techreport, @misc, @online)
   - Flag citations that need manual review

3. **Automated Citation Fixing**:
   - Find correct arXiv/DOI from project pages
   - Update markdown sources automatically
   - Create PR with fixes

## Testing Strategy

1. Create validation suite for all 4 manuscripts
2. Extract all citations from markdown
3. Validate each URL (paper vs project page vs grey literature)
4. Verify Zotero lookup succeeds
5. Check Better BibTeX key usage
6. Verify PDF hyperlinks work
7. Check author name encoding

## Success Criteria

✅ **All citations must have:**
- Proper URL (paper, DOI, or acceptable grey literature source)
- Correct author names (with Unicode characters)
- Proper source identification (journal/arXiv/conference/report)
- Working hyperlinks (or acceptable non-hyperlinked grey literature)
- Better BibTeX keys from Zotero
- Accurate metadata in final PDF

**Only then can we claim production-ready PDFs!**

## Next Steps

1. User review and approval of problematic citations list
2. Manual audit and correction of high-priority issues
3. Build URL validation tool
4. Implement Better BibTeX key integration
5. Create quality report for all papers
6. Build regression test suite
