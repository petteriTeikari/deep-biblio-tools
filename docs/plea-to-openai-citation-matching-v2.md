# Plea to OpenAI: Help Us Understand Citation Matching (CORRECTED)

## The Actual Problem (After Investigation)

The converter IS fetching citation metadata, but:
1. 124 out of 376 citations (33%) are failing to fetch and become "Unknown"
2. The local bibliography files exist but may not be used correctly
3. There's an invalid character (`^^?`) in the LaTeX output causing compilation failure

## The CORRECT Fallback Logic (From User)

The expected fallback order is:

1. **Try local Zotero MCP server** (Not available in this case)
2. **Try Zotero API** (Not sure if configured)
3. **Try `mcp-draft-refined-v3.rdf`** (Local RDF file - **EXISTS**, 2.7 MB)
4. **Try `mcp-draft-refined-v3.json`** (Local CSL JSON - **EXISTS**, 1.2 MB)
5. **Try `references.bib`** (Generated output - should NOT use this as it's the OUTPUT of conversion)

## What Files Actually Exist

In `/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/`:

```bash
-rw-r--r--  2.7M  mcp-draft-refined-v3.rdf    # Zotero RDF export
-rw-r--r--  1.2M  mcp-draft-refined-v3.json   # Zotero CSL JSON export
-rw-r--r--   78K  references.bib              # GENERATED (incorrect source)
```

Both the RDF and JSON files are substantial (2.7MB and 1.2MB) suggesting they contain comprehensive citation data.

## What's Happening in the Conversion

From the log output:

```
Fetching metadata for 376 citations:
Fetching: Adisorn et al...    [SUCCESS]
Fetching: Agarwal et al...    [SUCCESS]
...
Fetching: Unknown...          [FAILED - appears 124 times]
...
✗ Local BibTeX not initialized (path: None)
```

**Analysis:**
- The converter IS attempting to fetch metadata
- Many citations succeed (Adisorn, Agarwal, etc.)
- 124 citations fail and become "Unknown"
- The LOCAL_BIBTEX_PATH environment variable is not being picked up

## Critical Questions

### Q1: Is the fallback chain implemented?

Looking at the code, there's Zotero JSON matching at `converter.py:147-194`, but:
- Is it checking for `mcp-draft-refined-v3.rdf` in the same directory?
- Is it checking for `mcp-draft-refined-v3.json` in the same directory?
- What's the actual order of fallbacks?

### Q2: Why are 124 citations failing?

The logs show "Fetching: Unknown..." 124 times. This means:
- The citation text itself is "Unknown" before fetching
- OR the fetching is failing and falling back to "Unknown"

Which is it? And why isn't it using the local RDF/JSON files?

### Q3: What is the invalid character bug?

```
! Text line contains an invalid character.
l.247 ..., \textbackslash citep\{unknownUnknown^^?
```

There's an invalid character (`^^?`) being written to the LaTeX file. This suggests:
- Citation key generation is producing non-ASCII characters
- OR there's a Unicode handling issue in the citation text parsing

## Appendix A: Sample RDF Entry

```xml
<bib:Article rdf:about="https://doi.org/10.1038/s41746-024-01085-w">
    <z:itemType>journalArticle</z:itemType>
    <dcterms:isPartOf rdf:resource="urn:issn:2398-6352"/>
    <bib:authors>
        <rdf:Seq>
            <rdf:li>
                <foaf:Person>
                    <foaf:surname>Koch</foaf:surname>
                    <foaf:givenName>Lisa M.</foaf:givenName>
                </foaf:Person>
            </rdf:li>
            <rdf:li>
                <foaf:Person>
                    <foaf:surname>Baumgartner</foaf:surname>
                    <foaf:givenName>Christian F.</foaf:givenName>
                </foaf:Person>
            </rdf:li>
        </rdf:Seq>
    </bib:authors>
    <dc:title>Distribution shift detection for the postmarket surveillance of medical AI algorithms</dc:title>
    <dc:date>2024-05-09</dc:date>
    <dc:identifier>
        <dcterms:URI>
           <rdf:value>https://doi.org/10.1038/s41746-024-01085-w</rdf:value>
        </dcterms:URI>
    </dc:identifier>
</bib:Article>
```

**Key fields for matching:**
- `rdf:about` or `dc:identifier/dcterms:URI/rdf:value` - URL for matching
- `bib:authors/rdf:Seq/rdf:li/foaf:Person` - author names
- `dc:title` - title
- `dc:date` - publication date

## Appendix B: Sample JSON Entry

```json
{
  "id": "http://zotero.org/users/4953359/items/QT2KMVQC",
  "type": "article-journal",
  "DOI": "10.1038/s41746-024-01085-w",
  "URL": "https://doi.org/10.1038/s41746-024-01085-w",
  "title": "Distribution shift detection for the postmarket surveillance of medical AI algorithms",
  "author": [
    {
      "family": "Koch",
      "given": "Lisa M."
    },
    {
      "family": "Baumgartner",
      "given": "Christian F."
    }
  ],
  "issued": {
    "date-parts": [
      [
        "2024",
        5,
        9
      ]
    ]
  }
}
```

**Key fields for matching:**
- `URL` or `DOI` - for URL matching
- `author` array - with `family` and `given` names
- `title` - title
- `issued` - publication date

## What We Need from OpenAI

### 1. Verify the Fallback Implementation

**Question:** Does the converter actually check for:
1. `{basename}.rdf` in the same directory as the markdown?
2. `{basename}.json` in the same directory as the markdown?
3. If not, where should these files be located?

**Expected behavior:**
```
Input: mcp-draft-refined-v3.md
Look for:
  1. mcp-draft-refined-v3.rdf (same directory)
  2. mcp-draft-refined-v3.json (same directory)
  3. Fall back to fetching if not found
```

### 2. Explain Why 124 Citations Fail

**Given that:**
- `mcp-draft-refined-v3.json` is 1.2MB (likely hundreds of entries)
- `mcp-draft-refined-v3.rdf` is 2.7MB (likely hundreds of entries)
- Many citations DO succeed (Adisorn, Agarwal, etc.)

**Why are 124 failing?**
- Is URL matching case-sensitive?
- Are there URL normalization issues (http vs https, trailing slashes)?
- Is the converter even LOOKING at these files?

### 3. Fix the Invalid Character Bug

The `^^?` character in the LaTeX output suggests:
- Citation key sanitization is missing
- OR there's a Unicode issue in the text parsing

**Where should we look?**
- Citation key generation code
- Text sanitization for LaTeX
- Unicode to ASCII conversion

### 4. Provide a Test Case

Can you provide a minimal test case showing:

**Input markdown:**
```markdown
Recent work by [Smith et al., 2023](https://doi.org/10.1234/example) shows...
```

**Matching RDF entry:**
```xml
<bib:Article rdf:about="https://doi.org/10.1234/example">
    <bib:authors>...</bib:authors>
    <dc:title>Example Paper</dc:title>
</bib:Article>
```

**Expected output BibTeX:**
```bibtex
@article{smith2023example,
  author = {Smith, John and Jones, Mary},
  title = {Example Paper},
  year = {2023},
  doi = {10.1234/example}
}
```

**How should the matching work?**
- Extract URL from markdown: `https://doi.org/10.1234/example`
- Look up in RDF by `rdf:about` or `dc:identifier`
- Extract author/title/year from RDF
- Generate BibTeX entry

## Current Implementation Questions

### Where is URL matching done?

We found code at `converter.py:147-194` that matches against Zotero JSON:

```python
def _populate_from_zotero_json(self, citations: list) -> tuple[int, int]:
    # Build lookup indices
    url_index = {}
    for entry in zotero_entries:
        url = entry.get("URL", "")
        if url:
            url_index[url] = entry

    # Match citations
    for citation in citations:
        if citation.url in url_index:
            self._populate_citation_from_csl_json(citation, url_index[citation.url])
```

**Questions:**
1. Is this being called for `mcp-draft-refined-v3.json`?
2. Is there similar code for `.rdf` files?
3. Where is the file discovery logic (finding {basename}.json)?

### What about the "Fetching: ..." progress?

The logs show "Fetching: Author..." which suggests:
- Active network requests OR
- Reading from local files with progress bar

**Where is this code?** We need to understand if it's:
- Fetching from APIs (Zotero API, CrossRef, etc.)
- Reading from local files
- Both (with fallback)

## Summary

We have:
- ✅ Local RDF file (2.7 MB)
- ✅ Local CSL JSON file (1.2 MB)
- ✅ Test suite showing 124 Unknown citations
- ✅ Logs showing "Fetching: Unknown..." repeatedly
- ❌ Understanding of why local files aren't being used
- ❌ Fix for the invalid character bug

Please help us understand:
1. How to verify the fallback chain is working
2. Why 124 citations are failing when local files exist
3. How to fix the `^^?` invalid character bug
4. What the "Fetching: ..." progress actually does

---

**Generated:** 2025-10-26
**Test Suite:** `scripts/test_mcp_conversion.py` (working, shows deterministic failures)
**Files Verified:** Both `.rdf` and `.json` exist and contain substantial data
**Current Branch:** `fix/verify-md-to-latex-conversion`
