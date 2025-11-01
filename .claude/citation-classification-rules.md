# Citation Classification Rules

**Purpose**: Determine which hyperlinks should be bibliography entries vs inline hyperlinks/footnotes.

**Last Updated**: 2025-11-01

---

## Core Principle

**NOT every hyperlink in markdown is a citation for the bibliography.**

- **Academic citations** → Bibliography entries with `\citep{}` commands
- **Non-academic links** → Should remain as inline hyperlinks or become footnotes

---

## Decision Tree

### 1. Check the URL Domain

**Academic Domains** (→ Bibliography):
- `doi.org` - Digital Object Identifiers
- `arxiv.org` - Preprint server
- `ieee.org` - IEEE publications
- `acm.org` - ACM Digital Library
- `springer.com`, `springerlink.com` - Springer journals
- `nature.com` - Nature journals
- `science.org`, `sciencemag.org` - Science journals
- `wiley.com` - Wiley publications
- `elsevier.com`, `sciencedirect.com` - Elsevier journals
- `jstor.org` - JSTOR archive
- `pubmed.gov` - Medical literature
- Amazon/ISBN links to academic books

**Non-Academic Domains** (→ Inline hyperlinks/footnotes):
- **News**: bbc.com, bloomberg.com, reuters.com, theguardian.com, nytimes.com
- **Company blogs**: anthropic.com, openai.com, google.com, microsoft.com
- **Social media**: x.com, twitter.com, youtube.com, linkedin.com, reddit.com
- **Code repositories**: github.com, gitlab.com, bitbucket.org
- **Government**: europa.eu, .gov, oecd.org, un.org
- **Documentation**: docs.*, developer.*, documentation.*
- **Tech blogs**: medium.com, substack.com, towardsdatascience.com

**Implementation**: See `citation_extractor_unified.py:92-178` (NON_ACADEMIC_DOMAINS filter)

### 2. Check the Citation Format

**Has Author + Year** (→ Bibliography):
```markdown
[Smith et al., 2020](https://doi.org/10.1234/example)
[Zhang (2023)](https://arxiv.org/abs/2301.12345)
[Niinimäki et al., 2020](https://nature.com/articles/...)
```

**No Author/Year or Organization Name** (→ Inline hyperlink/footnote):
```markdown
[Google Docs](https://docs.google.com)
[EON Platform](https://www.eon.xyz/)
[GitHub repo](https://github.com/user/repo)
[BBC News](https://bbc.com/news/...)
[Anthropic Blog Post](https://anthropic.com/blog/...)
```

### 3. Check Author Field

**Person Names** (→ Bibliography):
- Smith, Zhang, Niinimäki, García
- Multiple authors with "et al."
- Names that look like humans

**Organization Names** (→ Inline hyperlink/footnote):
- BBC, Bloomberg, Google, Anthropic, OpenAI
- European Commission, OECD, UN
- Company names, government agencies

**Issue Found**: 73 citations in v4.md have organization names in author field:
```
[BBC (2013)](https://bbc.com/...)
[Bloomberg (2021)](https://bloomberg.com/...)
[Google (2024)](https://google.com/...)
[Anthropic (2025)](https://anthropic.com/...)
```

These should likely be footnotes, not bibliography entries.

---

## Examples from Real Document (v4.md validation)

### Example 1: Academic Citation (→ Bibliography)
```markdown
[Niinimäki et al., 2020](https://doi.org/10.1038/s43017-020-0039-9)
```
- ✅ Author names: Niinimäki, Peters, Dahlbo (persons)
- ✅ Year: 2020
- ✅ URL: doi.org (academic)
- ✅ **Decision**: Bibliography entry

### Example 2: News Article (→ Inline hyperlink)
```markdown
[BBC News (2013)](https://bbc.com/news/world-asia-22476774)
```
- ❌ Author: BBC (organization)
- ❌ URL: bbc.com (news site)
- ❌ **Decision**: Should be footnote, NOT bibliography

### Example 3: Company Blog (→ Inline hyperlink)
```markdown
[Anthropic (2024)](https://anthropic.com/blog/claude-artifacts)
```
- ❌ Author: Anthropic (company)
- ❌ URL: anthropic.com (company website)
- ❌ **Decision**: Should be footnote, NOT bibliography

### Example 4: Code Repository (→ Inline hyperlink)
```markdown
[TensorFlow GitHub](https://github.com/tensorflow/tensorflow)
```
- ❌ No author/year format
- ❌ URL: github.com (code repo)
- ❌ **Decision**: Inline hyperlink, NOT bibliography

### Example 5: Government Report (→ Inline hyperlink)
```markdown
[European Commission (2020)](https://europa.eu/environment/circular-economy)
```
- ❌ Author: European Commission (organization)
- ❌ URL: europa.eu (government)
- ❌ **Decision**: Should be footnote, NOT bibliography

### Example 6: Academic Book (→ Bibliography)
```markdown
[Fletcher (2014)](https://www.amazon.com/Sustainable-Fashion-Past-Kate-Fletcher/dp/1138021016)
```
- ✅ Author: Fletcher (person)
- ✅ Year: 2014
- ✅ URL: Amazon with ISBN (academic book)
- ✅ **Decision**: Bibliography entry

---

## Current Implementation

### Extraction Phase (citation_extractor_unified.py)

**NON_ACADEMIC_DOMAINS filter** (80+ domains):
```python
NON_ACADEMIC_DOMAINS = {
    # === Code Repositories ===
    "github.com", "gitlab.com", "bitbucket.org",

    # === Social Media ===
    "x.com", "twitter.com", "youtube.com", "linkedin.com", "reddit.com",

    # === News ===
    "bbc.com", "bloomberg.com", "reuters.com", "theguardian.com", "nytimes.com",

    # === Government ===
    "europa.eu", ".gov", "oecd.org", "un.org",

    # === Companies ===
    "anthropic.com", "openai.com", "google.com", "amazon.com", "microsoft.com",

    # === Fashion Industry ===
    "haelixa.com", "oritain.com", "entrupy.com", "eon.xyz",

    # ... (80+ total domains)
}
```

**Filter Statistics** (from mcp-draft-refined-v5.md conversion):
- 578 total hyperlinks extracted
- 123 filtered as non-academic
- 439 kept as academic citations

### What Gets Filtered Out

**Currently filtered** (123 links):
- GitHub repositories
- Company websites
- News articles
- Social media posts
- Government documents
- Documentation sites

**Still getting through** (potential issue):
- Organization-as-author citations (73 found in v4.md)
- These have academic-looking format `[Organization (Year)](URL)` but aren't academic papers

---

## Recommended Actions

### For Organization-As-Author Citations

**Current behavior**:
```markdown
[BBC (2013)](https://bbc.com/news/...)
```
→ Extracted as citation → Filtered by NON_ACADEMIC_DOMAINS → Not in bibliography ✅

**But if domain not in filter**:
```markdown
[Fashion United (2024)](https://fashionunited.com/news/...)
```
→ Extracted as citation → NOT filtered → Appears in bibliography ❌

**Solution**: The NON_ACADEMIC_DOMAINS filter is working correctly. If organization-as-author citations are still appearing, add their domains to the filter.

### For Mixed Cases

**Question**: What about legitimate academic papers published on company blogs?

Example:
```markdown
[Smith from Google Research (2024)](https://research.google/pubs/...)
```

**Answer**:
- If URL is `research.google.com` → Consider adding exception to filter
- If actual academic venue → Should have DOI/arXiv link instead
- Gray area → Ask user for clarification

---

## Verification Commands

### Count Non-Academic Links Filtered
```bash
# During conversion, check logs
grep "Skipping non-academic link" conversion.log | wc -l
```

### Find Organization-As-Author in Output
```bash
# Check .bib for organization names
grep -E "@article{.*,(BBC|Bloomberg|Google|Anthropic|OpenAI)" output/references.bib
```

### Review Borderline Cases
```bash
# Check CSV report for organization authors
grep -E "^(BBC|Bloomberg|Google|Anthropic)" output/missing-citations-review.csv
```

---

## When to Update Filter

**Add domain to NON_ACADEMIC_DOMAINS if**:
1. It's a news/media site
2. It's a company blog (not research)
3. It's a government/policy document
4. It's a code repository
5. It's social media
6. It's documentation site

**Don't add to filter if**:
1. It's an academic publisher
2. It's a preprint server
3. It's an academic institution repository
4. It's a digital library

---

## Summary

**Key Insight**: The presence of `[Text (Year)](URL)` doesn't make something a citation. Check:
1. Domain type (academic vs non-academic)
2. Author type (person vs organization)
3. Content type (research paper vs news article)

**Current Status**:
- ✅ NON_ACADEMIC_DOMAINS filter working (123/578 links filtered)
- ⚠️ Some organization-as-author citations may slip through if domain not in filter
- ✅ Solution: Expand filter as needed, verify with missing citations report

**For More Context**: See CITATION-VERIFICATION-REPORT-2025-10-31.md which found 73 organization-as-author citations in v4.md.
