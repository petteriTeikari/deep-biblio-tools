# Citation Quality Issues Found in fashion-cad-review-v3.pdf

**Date**: 2025-10-27
**Status**: CRITICAL - These issues prevent the PDF from being publication-ready

## Executive Summary

While the PDF compiles without (?) citations, systematic review reveals **MAJOR data quality issues**:
- Wrong author names (Unicode encoding failures)
- Incorrect source identification (arXiv vs published papers)
- Wrong BibTeX keys (generated vs Better BibTeX)
- Project page URLs instead of paper URLs
- Missing/broken hyperlinks

## Detailed Issues

### Issue 1: Kuźniak Paper - Multiple Critical Problems

**What the PDF shows:**
```
Kuniak M, Choudhary S, Pawowski S, Cortez AFV, Kac-
zorowski M, Kumosiski M, Abramowicz A, cki T, Nier-
adka G, Sworobowicz T, Jamanek D (2024) New candi-
date polymeric wavelength shifters for noble liquid de-
tectors. arXiv
```

**Problems:**
1. ❌ **Wrong Author Name**: "Kuniak" should be "Kuźniak" (Unicode ź lost)
2. ❌ **Wrong Source**: Labeled as "arXiv" but it's actually a published JINST paper
3. ❌ **Missing DOI**: Should show DOI `10.1088/1748-0221/20/05/C05006`
4. ❌ **No Hyperlink**: The reference is NOT hyperlinked
5. ❌ **Wrong BibTeX Key**: Using `nakayama2024`, should be `kuzniakNewCandidatePolymeric2025`

**Correct Reference:**
```
Kuźniak, M., S. Choudhary, S. Pawłowski, et al. "New Candidate Polymeric
Wavelength Shifters for Noble Liquid Detectors." Journal of Instrumentation
20, no. 05 (2025): C05006. https://doi.org/10.1088/1748-0221/20/05/C05006
```

**BibTeX Key**: `kuzniakNewCandidatePolymeric2025`

**Root Cause**: Markdown source has wrong URL: `https://arxiv.org/abs/2504.01483`

### Issue 2: GaussianVTON (Cao) - Project Page Instead of Paper

**What the PDF shows:**
```
(Cao G, et al. (2024) Gs-vton
```

**Problems:**
1. ❌ **Project Page URL**: `https://yukangcao.github.io/GS-VTON/` (NOT a paper!)
2. ❌ **Wrong Author Format**: "GaussianVTON (Cao and others" in BibTeX
3. ❌ **Wrong Title**: Just "GS-VTON" instead of full paper title
4. ❌ **Wrong BibTeX Key**: Using `cao2024a`, should be `caoGSVTONControllable3D2024`
5. ❌ **Missing arXiv Info**: No indication this is an arXiv paper

**Correct Reference:**
- **arXiv**: `https://arxiv.org/abs/2410.05259`
- **Title**: "GS-VTON: Controllable 3D Virtual Try-on with Gaussian Splatting"
- **Authors**: Yukang Cao, et al.

**Root Cause**: Markdown source line 79:
```markdown
[GaussianVTON (Cao et al., 2024)](https://yukangcao.github.io/GS-VTON/)
```

### Issue 3: Chen LBCO - Personal Website Instead of Paper

**What the markdown shows:**
```markdown
[Chen et al. (2024)](https://engineering.purdue.edu/~chen2086/)
```

**Problems:**
1. ❌ **Personal Website URL**: Not a paper!
2. ❌ **Wrong BibTeX Entry**: Generated garbage metadata
3. ❌ **Wrong Author**: "Latent-Based Constrained Optimization (Chen and others"
4. ❌ **Wrong Title**: "Web page by Latent-Based Constrained Optimization"

**Root Cause**: Need to find the actual paper this refers to.

## Systematic Problems Identified

### 1. No URL Validation

**Current Behavior**: Converter silently accepts ANY URL, including:
- Project pages (`github.io`, `yukangcao.github.io`)
- Personal websites (`engineering.purdue.edu/~username`)
- Company websites (`mckinsey.com`)

**Should Do**:
- ⚠️ Detect non-paper URLs
- 🔍 Try to find actual paper from project page
- ❌ FAIL or WARN on suspicious URLs

### 2. Wrong BibTeX Key Strategy

**Current**: Generates short keys like `cao2024a`, `nakayama2024`

**Should**: Use Better BibTeX keys from Zotero:
- `caoGSVTONControllable3D2024`
- `kuzniakNewCandidatePolymeric2025`

### 3. No Post-Conversion Quality Check

**Missing**:
- Author name encoding verification (Unicode)
- Hyperlink presence verification
- Source type verification (arXiv vs DOI vs journal)
- BibTeX key validation against Zotero

### 4. Silent Failures

**Current**: Converter produces PDF even with garbage metadata

**Should**: Generate quality report:
```
⚠️ WARNINGS:
- 2 citations using project page URLs
- 1 citation using personal website URL
- 3 citations with generated keys (not Better BibTeX)

❌ ERRORS:
- 1 author name with encoding issues (Kuźniak → Kuniak)
- 2 missing hyperlinks
```

## Impact Assessment

**Current State**: PDF appears to have "0 missing citations" but has:
- 3 citations with WRONG metadata
- 1 citation with WRONG author name
- 2+ citations with NO/WRONG hyperlinks

**This is NOT production-ready!**

## Required Fixes

### Immediate (Markdown Source)

1. Fix Kuźniak URL: `https://arxiv.org/abs/2504.01483` → `https://doi.org/10.1088/1748-0221/20/05/C05006`
2. Fix GaussianVTON URL: `https://yukangcao.github.io/GS-VTON/` → `https://arxiv.org/abs/2410.05259`
3. Fix Chen LBCO: Find actual paper URL

### Short-term (Converter)

1. **URL Validator**: Detect and warn on non-paper URLs
2. **Better BibTeX Integration**: Use Zotero citation keys
3. **Quality Report**: Generate post-conversion validation report
4. **Unicode Handling**: Fix author name encoding

### Long-term (Pipeline)

1. **Smart URL Resolution**:
   - Parse project pages for paper links
   - Try DOI lookup from title/authors
   - Fallback to Semantic Scholar/CrossRef search

2. **Zotero Verification**:
   - Check if citation exists in Zotero BEFORE conversion
   - Flag mismatches between markdown and Zotero
   - Suggest Better BibTeX key corrections

3. **Automated Citation Fixing**:
   - Find correct arXiv/DOI from project pages
   - Update markdown sources automatically
   - Create PR with fixes

## Testing Strategy

Create validation suite for all 4 working papers:
1. Extract all citations from markdown
2. Validate each URL (paper vs project page)
3. Verify Zotero lookup succeeds
4. Check Better BibTeX key usage
5. Verify PDF hyperlinks work
6. Check author name encoding

## Success Criteria

✅ **All citations must have:**
- Correct author names (with Unicode characters)
- Proper source identification (journal/arXiv/conference)
- Working hyperlinks to papers (not project pages)
- Better BibTeX keys from Zotero
- Accurate metadata in final PDF

Only then can we claim "0 missing citations" success!
