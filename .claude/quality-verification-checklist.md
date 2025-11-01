# Quality Verification Checklist

**Purpose**: Step-by-step verification commands to run BEFORE claiming conversion success.

**Last Updated**: 2025-11-01

---

## When to Use This Checklist

**ALWAYS run this checklist before claiming**:
- Conversion succeeded
- PDF is ready
- Citations are working
- "Everything looks good"

**NEVER claim success based on**:
- "Citations extracted" (meaningless without verification)
- "BibTeX generated" (meaningless if contains Unknown entries)
- "PDF compiled" (meaningless if citations show as ?)
- "No LaTeX errors" (meaningless if bibliography is broken)

---

## The Checklist

Run these commands in order. ALL must pass before claiming success.

### 1. Verify Output Directory Correct

**Command**:
```bash
# Check output is next to input, NOT in /tmp
INPUT="/path/to/input/file.md"
OUTPUT_DIR="$(dirname "$INPUT")/output"
ls -lh "$OUTPUT_DIR/"
```

**Expected**:
```
-rw-r--r-- file.tex
-rw-r--r-- file.pdf
-rw-r--r-- references.bib
-rw-r--r-- missing-citations-report.json
-rw-r--r-- missing-citations-review.csv
```

**Pass Criteria**:
- ✅ Output directory is `input_dir/output/`
- ✅ NOT in `/tmp/` or repository root
- ✅ All expected files exist

**Fail If**:
- ❌ Output in `/tmp/test/`
- ❌ Output in `/home/user/repo/output/`
- ❌ Missing expected files

---

### 2. Verify ZERO failedAutoAdd in .bib

**Command**:
```bash
grep -c "failedAutoAdd" output/references.bib
```

**Expected**:
```
0
```

**Pass Criteria**:
- ✅ Returns exactly `0`
- ✅ No failedAutoAdd entries anywhere in references.bib

**Fail If**:
- ❌ Returns any number > 0
- ❌ See `@article{failedAutoAdd_*` in .bib

**If Failed**:
- Check `citation_manager.py:1792-1805` filtering code
- Verify `if not key.startswith("failedAutoAdd_")` is working

---

### 3. Verify ZERO Unknown/Anonymous in .bib

**Command**:
```bash
grep -c "Unknown" output/references.bib
grep -c "Anonymous" output/references.bib
```

**Expected**:
```
0
0
```

**Pass Criteria**:
- ✅ Both return `0`
- ✅ No phantom/hallucinated author names

**Fail If**:
- ❌ Either returns > 0
- ❌ See `author = {Unknown}` or `author = {Anonymous}`

**If Failed**:
- Emergency mode should extract authors from markdown
- Check RDF parser for missing author extraction
- Verify URL matching is working

---

### 4. Verify Citation Counts Match

**Command**:
```bash
# From conversion logs or output
grep "Citations extracted:" conversion.log
grep "Matched to RDF:" conversion.log
grep "Missing citations:" conversion.log
```

**Expected** (example):
```
Citations extracted: 308
Matched to RDF: 210
Missing citations: 98
```

**Pass Criteria**:
- ✅ Total = Matched + Missing (308 = 210 + 98)
- ✅ Numbers are consistent
- ✅ Missing count seems reasonable

**Fail If**:
- ❌ Numbers don't add up
- ❌ Missing count is suspiciously high (>50% = likely bug)
- ❌ Missing count is 0 but you see (?) in PDF

**If Failed**:
- Check citation extraction logic
- Verify RDF parser loaded entries correctly
- Review URL matching algorithm

---

### 5. Verify Missing Citations Reports Exist

**Command**:
```bash
ls -lh output/missing-citations-report.json output/missing-citations-review.csv
wc -l output/missing-citations-review.csv
jq '.missing_count' output/missing-citations-report.json
```

**Expected**:
```
-rw-r--r-- missing-citations-report.json (10-50 KB)
-rw-r--r-- missing-citations-review.csv (5-20 KB)

99  # Line count (98 citations + 1 header)
98  # JSON missing_count
```

**Pass Criteria**:
- ✅ Both files exist
- ✅ CSV line count = JSON missing_count + 1 (header)
- ✅ Counts match "Missing citations" from logs

**Fail If**:
- ❌ Files don't exist
- ❌ Files are empty (0 bytes)
- ❌ Counts don't match

**If Failed**:
- Check `converter.py:1171-1244` report generation
- Verify `self.citation_manager.failed_citations` is populated
- Ensure code isn't checking for "Unknown" authors

---

### 6. Verify PDF Compiles Successfully

**Command**:
```bash
ls -lh output/file.pdf
pdfinfo output/file.pdf | head -10
```

**Expected**:
```
-rw-r--r-- file.pdf (200 KB - 5 MB typical)

Title:          Your Paper Title
Author:         Your Name
Pages:          20-50 (typical)
PDF version:    1.5 or higher
```

**Pass Criteria**:
- ✅ PDF file exists
- ✅ File size reasonable (not 0 bytes, not suspiciously small)
- ✅ pdfinfo shows valid metadata
- ✅ Page count seems correct

**Fail If**:
- ❌ PDF doesn't exist
- ❌ PDF is 0 bytes or corrupted
- ❌ pdfinfo shows errors
- ❌ Page count is 1 (likely compilation error)

---

### 7. Count (?) in PDF (CRITICAL)

**Command**:
```bash
pdftotext output/file.pdf - | grep -o "(\\?)" | wc -l
```

**Expected** (example):
```
98  # Should match missing citations count
```

**Pass Criteria**:
- ✅ Count approximately matches missing citations count
- ✅ (?) appearing is CORRECT (not a bug)
- ✅ Each (?) represents paper not in Zotero RDF

**CRITICAL UNDERSTANDING**:
- **(?) in PDF is EXPECTED and CORRECT**
- NOT a bug to eliminate at all costs
- Goal: Accurate citations, NOT zero (?)
- If 98 missing citations → seeing ~98 (?) is SUCCESS ✅

**Fail If**:
- ❌ Count is 0 but missing citations > 0 (phantom entries!)
- ❌ Count is way higher than missing count (extraction bug)
- ❌ You see (Unknown) or (Anonymous) instead of (?)

**If Failed**:
- Check if failedAutoAdd entries leaked into .bib
- Verify filtering is working
- Read PDF with Read tool to see actual citations

---

### 8. Manually Read PDF (REQUIRED)

**Command**:
```bash
# Use Read tool to visually inspect PDF
```

**What to Check**:
1. **Bibliography section exists** and is properly formatted
2. **Matched citations** show proper author names:
   - ✅ "Smith et al., 2020" or "(Smith et al., 2020)"
   - ❌ NOT "(Unknown, Unknown)" or "(?, ?)"
3. **Missing citations** show as (?):
   - ✅ "(?)" in text
   - ✅ NO phantom bibliography entries
4. **Hyperlinks work** (if .bbl hardcoded):
   - Click author-year in bibliography
   - Should open DOI/arXiv in browser

**Pass Criteria**:
- ✅ All matched citations show real author names
- ✅ All missing citations show as (?)
- ✅ ZERO Unknown/Anonymous in PDF
- ✅ Bibliography is clean and well-formatted

**Fail If**:
- ❌ See (Unknown) or (Anonymous) in PDF
- ❌ See phantom entries for missing citations
- ❌ Bibliography has garbled entries
- ❌ Hyperlinks don't work (if hardcoded)

---

### 9. Verify No Network Activity (Emergency Mode Only)

**Command**:
```bash
# During conversion, monitor network
grep -i "fetch\|http request\|api call\|doi.org\|crossref\|arxiv api" conversion.log
```

**Expected**:
```
(no matches found)
```

**Pass Criteria**:
- ✅ ZERO matches in logs
- ✅ No evidence of web fetching
- ✅ All data from RDF only

**Fail If**:
- ❌ See "Fetching metadata from..."
- ❌ See "Querying CrossRef API..."
- ❌ See "DOI resolution..."
- ❌ Any HTTP requests detected

**Advanced Check** (if suspicious):
```bash
# Run conversion with network monitoring
strace -e trace=network python scripts/deterministic_convert.py ... 2>&1 | grep -i "connect"
# Should see ONLY local connections, NO external
```

---

### 10. Check LaTeX/BibTeX Logs

**Command**:
```bash
grep -i "error" output/file.log
grep -i "warning.*citation" output/file.blg
```

**Expected**:
```
# .log file: ZERO errors (warnings OK)
# .blg file: Warnings about missing citations (EXPECTED)
```

**Pass Criteria**:
- ✅ No LaTeX errors in .log
- ✅ BibTeX warnings about missing citations are OK
- ✅ No fatal BibTeX errors

**Fail If**:
- ❌ LaTeX errors in .log
- ❌ BibTeX fatal errors in .blg
- ❌ "Undefined control sequence" errors

---

## Summary Checklist (Quick)

Run this quick version if you've done full check before:

```bash
cd /path/to/paper/output/

# 1. Output in correct location?
pwd  # Should be input_dir/output/

# 2. Zero failedAutoAdd in .bib?
grep -c "failedAutoAdd" references.bib  # → 0

# 3. Zero Unknown/Anonymous in .bib?
grep -c "Unknown\|Anonymous" references.bib  # → 0

# 4. Missing reports exist?
ls missing-citations-*.{json,csv}  # Both exist

# 5. PDF exists and valid?
pdfinfo file.pdf | grep Pages  # Shows page count

# 6. (?) count matches missing?
pdftotext file.pdf - | grep -o "(\\?)" | wc -l  # Matches missing count

# 7. Visual check PDF
# Use Read tool, verify citations look correct
```

**If ALL pass → Conversion SUCCESS ✅**

**If ANY fail → DO NOT claim success, investigate and fix ❌**

---

## When to Claim Success

**ONLY claim success when**:
1. ✅ All checklist items pass
2. ✅ You've READ the PDF with Read tool
3. ✅ You've VERIFIED citations visually
4. ✅ Output is in correct directory
5. ✅ Missing citations reports generated

**Messages to use**:
```
✅ Conversion completed successfully:
- 210 citations matched (appear with author names)
- 98 citations missing (appear as ? in PDF)
- Missing citations report: output/missing-citations-review.csv
- PDF compiled: output/file.pdf

Next step: Review missing-citations-review.csv and add papers to Zotero.
```

**NEVER say**:
- ❌ "Conversion succeeded!" (without verification)
- ❌ "All citations working!" (without reading PDF)
- ❌ "No issues found!" (without running checks)

---

## Red Flags - Investigate Immediately

**If you see ANY of these, STOP and investigate**:

1. **Missing count suspiciously high** (>50% of total)
   - Likely: URL matching broken
   - Check: RDF parser loaded entries correctly

2. **Missing count is 0** (but paper has citations)
   - Likely: Not using emergency mode correctly
   - Check: Are you fetching from web?

3. **failedAutoAdd in .bib** (count > 0)
   - Likely: Filtering broken
   - Check: `citation_manager.py:1792-1805`

4. **No (?) in PDF** (but missing count > 0)
   - Likely: Phantom entries in .bib
   - Check: references.bib for Unknown/Anonymous

5. **Output in /tmp**
   - Likely: Wrong output_dir configuration
   - Check: `self.output_dir` in converter

6. **Reports don't exist** (but missing count > 0)
   - Likely: Report generation broken
   - Check: `converter.py:1171-1244`

---

## Example Successful Output

```bash
$ cd /home/petteri/Dropbox/.../mcp-review/output/

$ grep -c "failedAutoAdd" references.bib
0

$ grep -c "Unknown\|Anonymous" references.bib
0

$ ls missing-citations-*
missing-citations-report.json
missing-citations-review.csv

$ jq '.missing_count' missing-citations-report.json
98

$ pdftotext mcp-draft-refined-v5.pdf - | grep -o "(\\?)" | wc -l
98

$ pdfinfo mcp-draft-refined-v5.pdf | grep Pages
Pages:           42
```

**This is SUCCESS**: 98 missing citations showing as (?) in PDF, no phantom entries, reports generated.

---

## Related Documents

- **Requirements**: `.claude/CITATION-REQUIREMENTS.md` (read first)
- **Emergency Mode**: `.claude/emergency-mode-specification.md` (success criteria)
- **Understanding (?)**: `.claude/CLAUDE.md:463-523`
- **Missing Reports**: `.claude/CITATION-REQUIREMENTS.md:98-133`

---

## Remember

**The goal is NOT zero (?) in PDF.**

**The goal is ACCURATE citations:**
- ✅ Papers in Zotero → Full citation
- ✅ Papers NOT in Zotero → (?) to show what's missing
- ❌ Papers NOT in Zotero → Phantom citation with fetched data

**(?) is your friend. It shows what work remains.**
