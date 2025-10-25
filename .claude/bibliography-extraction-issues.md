# Bibliography Extraction Issues

This document captures known issues with bibliography extraction that need to be addressed in future improvements.

## Critical Issues Found (2025-08-02)

### 1. Author Field Format

**Problem**: Authors are not in proper BibTeX format
- Current: `author = "FirstName LastName and FirstName2 LastName2"`
- Expected: `author = {LastName, FirstName and LastName2, FirstName2}`

**Example**:
```bibtex
# Current (wrong):
author = "Ruzena Bajcsy and Yiannis Aloimonos and John K. Tsotsos"

# Should be:
author = {Bajcsy, Ruzena and Aloimonos, Yiannis and Tsotsos, John K.}
```

**Root Cause**: The citation manager is not properly formatting author names when generating BibTeX entries.

### 2. "et al" in Author Fields

**Problem**: Some entries have "et al" instead of full author lists
```bibtex
author = "Arkin et al"
```

**Root Cause**:
- Markdown citations often use "et al" for brevity
- The extractor doesn't attempt to fetch full author lists
- Especially problematic for arXiv entries where full metadata is available

### 3. arXiv HTML URLs

**Problem**: Using HTML URLs instead of abstract URLs
```bibtex
url = "https://arxiv.org/html/2503.02723v1"
```

**Should use**:
```bibtex
url = "https://arxiv.org/abs/2503.02723"
```

**Impact**: HTML URLs don't work with arXiv API, preventing proper metadata extraction

### 4. ResearchGate Blocking

**Problem**: ResearchGate blocks automated requests, resulting in:
```bibtex
@misc{2015,
  author = "Asdrubali et al. )",
  title = "Asdrubali et al. )",
  url = "https://www.researchgate.net/publication/..."
}
```

**Solution Needed**:
- Detect ResearchGate URLs
- Look for DOI in the URL or page
- Use DOI instead of ResearchGate URL when available

### 5. Missing Entry Types

**Problem**: Everything defaults to `@misc` or `@article`
- Should use `@inproceedings` for conference papers
- Should use `@book` for books
- Should use `@techreport` for technical reports

## Recommendations for Fix

### Short Term
1. Fix author name formatting in `citation_manager.py`
2. Convert arXiv HTML URLs to abstract URLs before fetching
3. Skip ResearchGate URLs and use DOI if available

### Long Term
1. Implement proper author parsing with name disambiguation
2. Use Zotero translation server for better metadata extraction
3. Add heuristics to determine proper entry types
4. Implement retry logic with exponential backoff

## Code Locations to Fix

1. **Author Formatting**:
   - `src/deep_biblio_tools/converters/md_to_latex/citation_manager.py`
   - Method: `generate_bibtex_entry()`

2. **URL Processing**:
   - `src/deep_biblio_tools/converters/md_to_latex/citation_manager.py`
   - Method: `_fetch_from_arxiv()`

3. **Entry Type Detection**:
   - `src/deep_biblio_tools/converters/md_to_latex/citation_manager.py`
   - Method: `_determine_entry_type()`

## Additional Edge Cases Found (2025-08-02)

### 6. Missing First Names in Author Fields

**Problem**: Some entries only have last names without first names
```bibtex
# Current (wrong):
@article{alqudsi2025,
  author = "Alqudsi and Makaraci",
  ...
}

# Should be:
@article{alqudsi2025,
  author = {Alqudsi, Yunes and Makaraci, Murat},
  ...
}
```

**More Examples**:
```bibtex
# Current: author = "Amin and Ahmad"
# Should be: author = {Amin, Moeness G. and Ahmad, Fauzia}

# Current: author = "Arteaga and Kahr"
# Should be: author = {Arteaga, M. and Kahr, B.}
```

**Root Cause**: Incomplete metadata extraction or partial author parsing from sources

### 7. Commercial/Non-Academic Sources

**Problem**: Commercial websites result in poor quality entries
```bibtex
@misc{biblus2025,
  author = "BibLus",
  title = "BibLus",
  url = "https://biblus.accasoftware.com/en/what-is-ifc-5/",
  ...
}
```

**Issues**:
- Organization name as author instead of proper formatting
- Title is same as author (no real title extraction)
- No meaningful metadata

**Similar Examples**:
- bimgym2025
- blc2018 (BLC as author)
- Consumer Affairs entries

### 8. Ampersand Author Separator Edge Case

**Problem**: Authors separated by "&" are incorrectly parsed
```bibtex
# Current (wrong):
@article{botton2019,
  author = "Chatzidakis & Botton",
  ...
}

# Should be:
@article{chatzidakis2019,
  author = {Chatzidakis, M. and Botton, G. A.},
  title = {Towards calibration-invariant spectroscopy using deep learning},
  ...
}
```

**Issues**:
- Wrong author order (last author moved to front)
- Missing first names/initials
- Incorrect BibTeX key (should use first author's name)
- Special character "&" not properly handled

### 9. Missing Author Names from Parsed Text

**Problem**: Only last names extracted when full names are available
```bibtex
# From markdown: [Abdulsaheb & Kadhim 2023]
# Current: author = "Abdulsaheb and Kadhim"
# Should fetch full names from the paper/DOI
```

## Test Cases to Add

### Test Case 1: Missing First Names
```python
# Input from markdown
"[Alqudsi & Makaraci 2025](https://doi.org/10.1177/09544062241275359)"

# Expected output
@article{alqudsi2025,
  author = {Alqudsi, Yunes and Makaraci, Murat},
  ...
}
```

### Test Case 2: Ampersand Separator
```python
# Input from markdown
"[M. Chatzidakis & G. A. Botton 2019](https://doi.org/10.1038/s41598-019-38482-1)"

# Expected output
@article{chatzidakis2019,
  author = {Chatzidakis, M. and Botton, G. A.},
  ...
}
```

### Test Case 3: Commercial Sources
```python
# Input
"[BibLus 2025](https://biblus.accasoftware.com/en/what-is-ifc-5/)"

# Expected behavior
- Detect commercial/non-academic source
- Skip or flag for manual review
- Or extract proper page title instead of domain name
```

### Test Case 4: Full Citation Metadata
```python
# When DOI is available, should fetch complete metadata:
doi = "10.1038/s41598-019-38482-1"

# Expected complete entry:
@article{chatzidakis2019,
  title = {Towards calibration-invariant spectroscopy using deep learning},
  author = {Chatzidakis, M. and Botton, G. A.},
  year = {2019},
  month = {feb},
  journal = {Scientific Reports},
  volume = {9},
  number = {1},
  pages = {2126},
  publisher = {Nature Publishing Group},
  issn = {2045-2322},
  doi = {10.1038/s41598-019-38482-1},
  abstract = {...},
}
```

## Additional Edge Cases Found (2025-08-02) - Part 2

### 10. "et al" Parsing Catastrophe

**Problem**: "et al" is being parsed as if "al" is a last name, creating entries like:
```bibtex
# Current (catastrophically wrong):
@misc{al2024,
  author = "al, Zheng et",
  title = "Zheng et al",
  ...
}

# Should be (from DOI metadata):
@article{lee2024,
  author = {Lee, Gao Yu and Dam, Tanmoy and Ferdaus, Md. Meftahul and Poenar, Daniel Puiu and Duong, Vu N.},
  title = {Unlocking the capabilities of explainable few-shot learning in remote sensing},
  ...
}
```

**More Examples**:
```bibtex
# Wrong: author = "al, Zhang et"
# From: [Zhang et al. 2024](https://doi.org/10.1126/sciadv.adi0606)

# Wrong: author = "al, Zhang et"
# From: [Zhang et al. 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC8018814/)
```

**Root Cause**: The citation parser is splitting "Author et al" incorrectly, treating "et" as first name and "al" as last name, then reversing them to "al, Author et"

### 11. DOI Extraction from Academic URLs

**Problem**: DOIs embedded in URLs are not being extracted
```bibtex
# Has Springer URL with DOI but not extracted:
url = "https://link.springer.com/article/10.1007/s10462-024-10803-5"
# Should extract: doi = "10.1007/s10462-024-10803-5"

# Has PMC URL that could be converted to DOI:
url = "https://pmc.ncbi.nlm.nih.gov/articles/PMC8018814/"
# Should lookup DOI from PMC ID
```

**URL patterns with embedded DOIs**:
- Springer: `https://link.springer.com/article/{DOI}`
- Nature: `https://www.nature.com/articles/{DOI}`
- Wiley: `https://onlinelibrary.wiley.com/doi/{DOI}`
- ScienceDirect: `https://www.sciencedirect.com/science/article/pii/{PII}` (needs conversion)

### 12. Broken Link Detection

**Problem**: No indication when URLs are broken or inaccessible
- Should add a note field when URL returns 404 or other errors
- Should flag entries that may need manual verification

## Test Cases to Add - Part 2

### Test Case 5: "et al" Parsing
```python
# Input from markdown
"[Zheng et al. 2024](https://link.springer.com/article/10.1007/s10462-024-10803-5)"

# Current wrong output
@misc{al2024,
  author = "al, Zheng et",
  ...
}

# Expected: Parse correctly and fetch from DOI
@article{lee2024,
  author = {Lee, Gao Yu and Dam, Tanmoy and ...},
  doi = {10.1007/s10462-024-10803-5},
  ...
}
```

### Test Case 6: DOI Extraction from URLs
```python
# Input
url = "https://link.springer.com/article/10.1007/s10462-024-10803-5"

# Expected behavior
1. Extract DOI: "10.1007/s10462-024-10803-5"
2. Fetch metadata using extracted DOI
3. Add doi field to entry
```

### Test Case 7: PMC to DOI Conversion
```python
# Input
url = "https://pmc.ncbi.nlm.nih.gov/articles/PMC8018814/"

# Expected behavior
1. Extract PMC ID: "PMC8018814"
2. Query PMC API to get DOI
3. Fetch metadata using DOI
```

## Critical Parsing Fix Needed

The citation extractor MUST be fixed to:
1. Recognize "et al" as a citation indicator, not part of an author name
2. When seeing "Author et al", extract only "Author" as the first author
3. Never split "et al" into separate name parts

## Root Cause Analysis (2025-08-02)

### Why These Fixes Keep Failing

1. **Wrong Layer of Fix**: I keep trying to fix the bibliography AFTER it's generated, but the real problem is in the citation extraction from markdown. If the markdown has `[Ahmad et al. 2024]`, the extractor only saves "Ahmad" as the author.

2. **Silent Failures**: When metadata fetching fails (blocked by MDPI, ResearchGate, etc.), the system silently uses incomplete data without any indication of failure.

3. **Incomplete DOI Fetching**: Even when DOIs are available, the system doesn't always use them to fetch complete metadata during initial extraction.

4. **No Failure Tracking**: The bibliography doesn't indicate WHY entries are incomplete (blocked, timeout, 404, etc.)

### Additional Persistent Issues (2025-08-02)

### 13. First Names Still Missing Despite DOI

**Problem**: Entries with DOIs still have incomplete author names
```bibtex
@article{abdulsaheb2023,
  author = "Abdulsaheb and Kadhim",
  doi = "10.1155/2023/9967236",
  # Should have full names from DOI lookup
}

@article{alqudsi2025a,
  author = "Alqudsi and Makaraci",
  doi = "10.1186/s44147-025-00582-3",
  # Same authors as alqudsi2025 but missing first names
}
```

### 14. MDPI Blocking Issues

**Problem**: MDPI journals may be blocking automated requests
```bibtex
@article{ahmad2024,
  author = "Ahmad",  # Only one author extracted
  doi = "10.3390/buildings15101584",
  # Real authors: "Fahad Iqbal and Shayan Mirzabeigi"
}
```

### 15. No Failure Reason in Bibliography

**Problem**: No indication why metadata is incomplete
```bibtex
# Should be:
@article{ahmad2024,
  author = "Ahmad",
  note = "Metadata fetch failed: Blocked by MDPI (403)",
  ...
}
```

## Proper Fix Strategy

1. **Fix at Extraction Time**: Modify citation extractor to immediately fetch DOI metadata when available
2. **Add Failure Tracking**: Include note field explaining why metadata is incomplete
3. **Implement Retry Logic**: For rate limits and temporary failures
4. **Better Author Parsing**: Don't rely on markdown citation text for author names

## Testing Requirements

When fixing these issues, ensure:
1. Author names are properly formatted for all sources
2. arXiv entries use abstract URLs
3. ResearchGate entries fallback to DOI when available
4. Entry types are correctly determined
5. No "et al" remains in author fields
6. Full author names are fetched when DOI is available
7. Ampersand (&) separators are properly handled
8. Commercial sources are detected and handled appropriately
9. BibTeX keys use first author's last name
10. Complete metadata is fetched for entries with DOIs
11. "et al" is NEVER parsed as part of an author name
12. DOIs are extracted from academic URLs when possible
13. Broken links are detected and flagged
14. **Failure reasons are documented in note field**
15. **DOI metadata is fetched during initial extraction, not post-processing**
16. **MDPI and other publisher blocks are detected and noted**
