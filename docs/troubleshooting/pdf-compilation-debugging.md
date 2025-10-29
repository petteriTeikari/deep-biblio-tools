# PDF Compilation Debugging Guide

## Common PDF Compilation Failures

### 1. Undefined Citations (?)

**Symptom**: PDF shows (?) instead of proper citations, document may be truncated.

**Root Cause**: LaTeX cannot find bibliography entries for citations used in the document.

**What "undefined citations" means**:
- These are citations that appear in the .tex file (e.g., `\citep{smith2023}`)
- But have NO corresponding entry in the .bib file
- LaTeX reports these as "Citation 'smith2023' undefined"

**CRITICAL BUG TO AVOID**:
```python
# WRONG - This removes the wrong entries!
if compilation_results.get("undefined_citations"):
    for entry in bib_database.entries:
        if entry.get("ID") not in compilation_results["undefined_citations"]:
            cited_keys.add(entry.get("ID"))
```

The above code KEEPS entries that are NOT undefined, which is backwards. Undefined citations are ones that NEED to be in the bibliography but are MISSING.

**Correct Approach**:
1. Undefined citations should trigger ADDING missing entries or fixing citation keys
2. Never remove entries just because they're "undefined" - they're undefined because they're missing!
3. The fix is to either:
   - Add the missing bibliography entries
   - Fix the citation keys in the .tex file to match existing entries
   - Remove the citations from the .tex file if they're not needed

### 2. Bibliography Entry Quality Issues

**Missing Required Fields**:
- `@article` requires: author, title, journal, year
- `@inproceedings` requires: author, title, booktitle, year
- `@book` requires: author, title, publisher, year
- `@misc` requires: author, title, year

**Special Character Escaping**:
- Characters that MUST be escaped in BibTeX: `& % $ # _ { } ~ ^ < >`
- HTML entities must be converted: `&amp;` → `&`, `&lt;` → `<`, etc.
- HTML tags must be removed: `<span>`, `</span>`, etc.

### 3. Duplicate Bibliography Keys

**Issue**: Multiple entries with the same citation key
**Solution**: Keep only the first occurrence (in markdown, multiple citations of the same paper should map to one BibTeX entry)

### 4. Debug Workflow

1. **Check citation counts**:
   ```bash
   # Count citations in .tex file
   grep -o "\\\\cite[p]*{[^}]*}" file.tex | wc -l

   # Count entries in .bib file
   grep -c "^@" file.bib
   ```

2. **Find undefined citations**:
   ```bash
   # Extract all citations from .tex
   grep -o "\\\\cite[p]*{[^}]*}" file.tex | sed 's/.*{\(.*\)}/\1/' | sort -u > tex_citations.txt

   # Extract all keys from .bib
   grep "^@" file.bib | sed 's/.*{\(.*\),/\1/' | sort -u > bib_keys.txt

   # Find citations not in bibliography
   comm -23 tex_citations.txt bib_keys.txt
   ```

3. **Validate PDF quality**:
   - Check page count vs expected
   - Search for (?) in PDF text
   - Verify PDF file size is reasonable
   - Compare section counts between .tex and PDF

### 5. Common Failure Patterns

**Pattern 1: Mass Citation Removal**
- Symptom: Working .bib file becomes much smaller after "fixing"
- Cause: Misunderstanding "undefined citations" as entries to remove
- Fix: Undefined citations indicate MISSING entries, not excess entries

**Pattern 2: Comment Blocks**
- Symptom: Entries wrapped in `@comment{...}`
- Cause: Some tools comment out problematic entries
- Fix: Uncomment needed entries, fix any issues

**Pattern 3: Incomplete Entries**
- Symptom: Missing year, author as "Unknown", etc.
- Cause: Failed metadata fetching or LLM hallucinations
- Fix: Validate against DOI/arXiv, use placeholder data if needed

## Prevention Strategies

1. **Always validate citation-bibliography correspondence** before PDF compilation
2. **Never trust LLM-generated author names** - always validate
3. **Run PDF validation** to detect truncation and (?) citations
4. **Keep original .bib as backup** before any automated fixes
5. **Test with small documents first** before processing large files
