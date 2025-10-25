# Comprehensive Plan: ZERO-GLITCH Markdown → arXiv-Ready PDF Workflow

**Document Version:** 1.0
**Date:** 2025-10-25
**Status:** Planning Phase
**Branch:** `fix/verify-md-to-latex-conversion`

---

## Executive Summary

This document outlines a comprehensive validation and testing plan for the Deep Biblio Tools markdown-to-LaTeX converter to ensure **ZERO-GLITCH** conversion from academic markdown manuscripts to arXiv-ready PDF submissions.

### Problem Statement

Academic researchers write manuscripts in markdown with inline citations like `[Author (Year)](DOI_URL)`. These must be converted to LaTeX with proper BibTeX citations, compiled to PDF without errors, and formatted to meet arXiv submission standards. The current challenge is ensuring:

1. **100% citation resolution** - No (?) or (Unknown) citations in output
2. **ZERO compilation errors** - LaTeX compiles perfectly on first try
3. **arXiv-compliant formatting** - Proper bibliography with hyperlinked authors
4. **Reproducible workflow** - MCP server can handle this autonomously

### Success Criteria (ZERO TOLERANCE)

- ✅ **ZERO** markdown syntax errors (brackets, tables)
- ✅ **ZERO** (?) or (Unknown) citations in PDF output
- ✅ **ZERO** LaTeX compilation errors
- ✅ **ZERO** LaTeX compilation warnings
- ✅ **ZERO** raw URLs in bibliography (all embedded in hyperlinks)
- ✅ **100%** citations resolved from Zotero or fallback sources
- ✅ **100%** authors hyperlinked in bibliography to publication DOIs

---

## Background Context

### Current Technology Stack

**Programming Language:** Python 3.12+
**Package Manager:** uv
**Markdown Parser:** markdown-it-py (AST-based, no regex)
**LaTeX Compilation:** xelatex + bibtex
**Bibliography Style:** spbasic_pt.bst (Springer Basic with author-year)
**Citation Format:** natbib with `\citep{}` and `\citet{}`
**Font Size:** 10pt (arXiv default)

### Repository Structure

```
deep-biblio-tools/
├── src/
│   ├── converters/md_to_latex/    # Markdown → LaTeX converter
│   │   ├── converter.py            # Main conversion engine
│   │   ├── citation_manager.py     # Citation extraction & BibTeX generation
│   │   ├── latex_builder.py        # LaTeX preamble construction
│   │   ├── utils.py                # Text sanitization, Unicode handling
│   │   └── zotero_integration.py   # Zotero API client
│   ├── bibliography/               # Citation validation
│   └── parsers/                    # AST-based parsers
├── mcp-servers/deep-biblio/        # Model Context Protocol server
│   └── src/deep_biblio/
│       ├── server.py               # MCP tool implementations
│       └── arxiv_converter.py      # arXiv-specific workflows
├── scripts/                        # CLI utilities
├── tests/                          # Test suite (326 tests)
└── templates/
    └── spbasic_pt.bst              # Bibliography style file
```

### Existing Functionality

**What Works:**
- Markdown parsing with markdown-it-py
- Citation extraction from `[Author (Year)](URL)` format
- BibTeX key generation (`firstauthor<year><keyword>`)
- Table extraction and conversion to LaTeX
- Basic LaTeX compilation pipeline
- Zotero API integration for metadata lookup

**What Needs Validation:**
- End-to-end workflow reliability
- Citation resolution completeness (no missing citations)
- Compilation error handling
- Bibliography formatting (hyperlinked authors, no raw URLs)
- MCP server automation capabilities

---

## Test Case: Target Manuscript

### Input File

**Path:** `/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/mcp-review/mcp-draft-refined-v3.md`

**File Description:**
- Academic manuscript about Model Context Protocol (MCP)
- Contains inline citations in markdown format: `[Author (Year)](DOI_URL)`
- Includes tables (potentially complex)
- Multiple citation types: journal articles, conference papers, preprints
- Real-world complexity (not a toy example)

**Expected Output Location:** Same directory as input
- `mcp-draft-refined-v3.tex` - LaTeX source
- `mcp-draft-refined-v3.pdf` - Compiled PDF
- `references.bib` - BibTeX database
- `spbasic_pt.bst` - Bibliography style (copied automatically)
- `tables/` (if tables exist) - Extracted table files

### Reference Standard

**Previously Submitted arXiv Paper:** https://arxiv.org/pdf/2508.01965v1

This paper demonstrates the expected bibliography format:

**Key Characteristics:**
1. **Hyperlinked Authors:** Each author's name is a clickable link to the publication
2. **No Raw URLs:** All links embedded in text, not displayed as plain URLs
3. **Consistent Formatting:** Volume(issue):pages for journals, proper italics
4. **Springer Style:** Uses spbasic_pt.bst bibliography style

**Example Reference Entry:**
```latex
Hazem Abaza, Debayan Roy, Bohdan Trach, Wanli Chang,
Selma Saidi, Antonios Motakis, Wei Ren, Yutao Lin (2024)
Managing End-to-End Timing Jitters in ROS2 Computation Chains
Proceedings of the 32nd International Conference on Real-Time
Networks and Systems:229–241.
```

Where in the actual `.bbl` file, each author would be:
```latex
\href{https://doi.org/10.1145/...}{Hazem Abaza},
\href{https://doi.org/10.1145/...}{Debayan Roy}, ...
```

---

## Phase 1: Markdown Validation (Pre-conversion)

### Objective
Validate the input markdown file has correct syntax before attempting conversion.

### Tasks

#### 1.1 Bracket Matching Validation

**Purpose:** Ensure all markdown links are properly formed.

**Checks:**
- Every `[` has a matching `]`
- Every `(` has a matching `)`
- Citation format: `[Text](URL)` - brackets immediately followed by parentheses
- No orphaned brackets or parentheses

**Implementation:**
- Use character-by-character state machine (no regex per repository policy)
- Track nesting depth
- Report line numbers of mismatched brackets

**Expected Output:**
```
✓ Bracket matching: 847 citations, 0 errors
✓ All citations properly formed
```

#### 1.2 Table Structure Validation

**Purpose:** Detect malformed tables that would cause LaTeX conversion issues.

**Checks:**
- Parse tables with markdown-it-py AST parser
- Verify header separator lines: `|---|---|---| `
- Check column count consistency across all rows
- Detect empty cells or malformed pipes
- Validate alignment markers (`:---`, `:---:`, `---:`)

**Known Issues:**
- Multiline cell content (not standard markdown)
- Tables with merged cells (not supported)
- Nested tables (extremely rare)

**Expected Output:**
```
✓ Found 3 tables
  - Table 1: 5 columns, 12 rows (valid)
  - Table 2: 3 columns, 8 rows (valid)
  - Table 3: 4 columns, 15 rows (valid)
✓ All tables structurally valid
```

#### 1.3 Citation Extraction

**Purpose:** Build complete citation inventory before resolution.

**Process:**
1. Extract all inline citations: `[Author (Year)](URL)`
2. Parse author names, year, DOI/arXiv ID from each
3. Build structured citation list
4. Detect duplicates (same DOI cited multiple times)
5. Categorize by source type (DOI, arXiv, URL)

**Citation Format Examples:**
```markdown
[Abaza et al. (2024)](https://doi.org/10.1145/3626091)
[Consumer Affairs (2025)](https://www.consumeraffairs.com/...)
[Alqudsi and Makaraci (2025)](https://arxiv.org/abs/2505.06748)
```

**Expected Output:**
```
Citation Statistics:
- Total citations: 87
- Unique DOIs: 65
- arXiv preprints: 12
- Web URLs (non-DOI): 10
- Duplicate citations: 8 (same work cited multiple times)
```

### Validation Script

**File:** `scripts/validate_markdown_structure.py` (to be created)

**Usage:**
```bash
python scripts/validate_markdown_structure.py \
  /path/to/manuscript.md \
  --output validation-report.json
```

**Output Format:**
```json
{
  "brackets": {"status": "pass", "errors": []},
  "tables": {"status": "pass", "count": 3, "errors": []},
  "citations": {
    "total": 87,
    "unique_dois": 65,
    "arxiv": 12,
    "web_urls": 10,
    "duplicates": 8,
    "citations": [...]
  }
}
```

---

## Phase 2: Citation Resolution (Zotero-First Strategy)

### Objective
Resolve **100%** of citations to complete bibliographic metadata before LaTeX generation.

### Resolution Priority Chain

#### Priority 1: Zotero API (Primary)

**API Endpoint:** Zotero Translation Server
**Method:** POST to `http://localhost:1969/search`

**Lookup Strategies:**
1. **By DOI** (most reliable)
   ```python
   POST /search
   Body: "10.1145/3626091"
   ```

2. **By arXiv ID**
   ```python
   POST /search
   Body: "2505.06748"
   ```

3. **By Title + Author** (fallback for web URLs)
   ```python
   POST /search
   Body: "Managing End-to-End Timing Jitters Abaza 2024"
   ```

**Expected Response:**
- Full author list (not "et al")
- Complete title
- Journal/conference name
- Volume, issue, pages
- Publication year
- DOI (if available)

**Advantages:**
- Authoritative metadata
- Consistent formatting
- Handles author name variations
- Resolves publisher-specific quirks

#### Priority 2: Local Fallback (Secondary)

**Search Locations:**
1. User-specified `.bib` files
2. Zotero export files (`.json`, `.xml`)
3. Cached API responses (`.cache/citation_validation/`)

**Search Method:**
- Match by DOI (exact)
- Match by title (fuzzy, >90% similarity)
- Match by author + year (requires both)

**Rationale:**
- Offline capability
- Faster for repeated conversions
- Handles non-standard sources

#### Priority 3: Missing Citations Report

**If citation cannot be resolved:**

1. **Do NOT generate LaTeX** (BLOCK conversion)
2. **Generate missing citations report:**
   ```markdown
   # Missing Citations Report

   The following citations could not be resolved:

   1. **Consumer Affairs (2025)** - Water Damage Insurance Claims
      - URL: https://www.consumeraffairs.com/...
      - Action: Add to Zotero manually
      - Import URL: https://www.zotero.org/save?url=...

   2. **Author (Year)** - Title (if extractable)
      - DOI: 10.xxxx/xxxxx
      - Action: Verify DOI is correct, add to Zotero
   ```

3. **Provide Zotero import commands:**
   ```bash
   # Quick add to Zotero:
   zotero-cli add --doi 10.xxxx/xxxxx
   ```

4. **Exit with error code:** Conversion fails until all citations resolved

### Citation Resolution Tool

**File:** `mcp-servers/deep-biblio/convert-with-zotero-api.py`

**Usage:**
```bash
python convert-with-zotero-api.py \
  --input mcp-draft-refined-v3.md \
  --zotero-url http://localhost:1969 \
  --fallback-bib ~/.zotero/library.bib \
  --missing-report missing-citations.md
```

**Expected Output:**
```
Resolving citations...
✓ Resolved 75/87 via Zotero API (86%)
✓ Resolved 10/87 via local .bib files (11%)
✗ Failed to resolve 2/87 (2%)

Missing citations written to: missing-citations.md
BLOCKING: Cannot proceed until all citations resolved
```

### BibTeX Key Generation

**Format:** `firstauthor<year><keyword>`

**Examples:**
- Abaza et al. (2024) → `abaza2024managing`
- Consumer Affairs (2025) → `consumeraffairs2025water`
- Alqudsi and Makaraci (2025) → `alqudsi2025uav`

**Keyword Extraction:**
- First significant word from title (not "the", "a", "an")
- Lowercase
- Maximum 15 characters
- Remove special characters

**Collision Handling:**
- If key exists: append `b`, `c`, etc.
- `abaza2024managing`, `abaza2024managingb`

---

## Phase 3: Markdown → LaTeX Conversion

### Objective
Convert validated markdown to LaTeX with proper citations and structure.

### Conversion Components

#### 3.1 Citation Replacement

**Input Format:**
```markdown
Recent work by [Abaza et al. (2024)](https://doi.org/10.1145/3626091)
shows that...
```

**Output Format:**
```latex
Recent work by \citep{abaza2024managing} shows that...
```

**Citation Commands:**
- `\citep{key}` - Parenthetical: (Abaza et al., 2024)
- `\citet{key}` - Textual: Abaza et al. (2024)

**Logic:**
- Default: `\citep{}`
- If citation starts sentence: `\citet{}`
- If after "by", "of", "according to": `\citet{}`

#### 3.2 Table Extraction (Modular Approach)

**Problem:** LaTeX tables can cause duplication bugs in AST processing.

**Solution:** Strip tables before pandoc conversion.

**Process:**
1. Parse markdown with markdown-it-py
2. Extract table line ranges from AST `token.map`
3. Remove tables from markdown
4. Insert placeholders: `[TABLE 1 REMOVED - See tables file]`
5. Convert table-free markdown to LaTeX via pandoc
6. Convert extracted tables separately
7. Insert converted tables back into LaTeX

**Table Conversion:**
- Simple tables → `tabular`
- Long tables → `longtable`
- Wide tables → `landscape` + `longtable`

**Output:**
```
tables/
├── table_1.tex
├── table_2.tex
└── table_3.tex
```

#### 3.3 Preamble Generation

**Requirements (MANDATORY for arXiv):**

```latex
\documentclass[10pt,a4paper,twocolumn]{article}

% Core packages
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb}
\usepackage{graphicx}
\usepackage{hyperref}

% Bibliography (CRITICAL)
\usepackage[authoryear,round]{natbib}
\bibliographystyle{spbasic_pt}

% Tables
\usepackage{longtable}
\usepackage{booktabs}

% Spacing
\usepackage{setspace}
\setstretch{1.0}

% Margins (arXiv compliant)
\usepackage[margin=1in]{geometry}
```

**Font Size Verification:**
- MUST be 10pt (arXiv default)
- NOT 11pt or 12pt
- Verified in tests: `test_latex_builder.py`

#### 3.4 Text Sanitization Pipeline

**6-Step Process (in utils.py):**

1. **HTML Entities → Unicode**
   - `&nbsp;` → space
   - `&mdash;` → —
   - `&ldquo;` → "

2. **Unicode → LaTeX Commands**
   - `—` → `---`
   - `"` → ` `` `
   - `"` → `''`
   - `≤` → `\leq`
   - `×` → `\times`

3. **Special Character Escaping**
   - `$` → `\$` (unless in math mode)
   - `%` → `\%`
   - `&` → `\&`
   - `_` → `\_`

4. **Quote Normalization**
   - Smart quotes → LaTeX quotes
   - Preserve code blocks unchanged

5. **Whitespace Cleanup**
   - Multiple spaces → single space
   - Trailing whitespace removed
   - Normalize line endings

6. **Math Mode Detection**
   - Preserve `$...$` and `$$...$$`
   - Don't escape `$` inside math

### Conversion Tool

**Primary Interface:** Python module

```python
from src.converters.md_to_latex import MarkdownToLatexConverter

converter = MarkdownToLatexConverter(
    output_dir=input_dir,  # Same as input
    bibliography_style="spbasic_pt",
    zotero_api_key="...",
    zotero_library_id="..."
)

tex_file = converter.convert(
    markdown_file=Path("mcp-draft-refined-v3.md"),
    verbose=True
)
```

**CLI Interface:**

```bash
deep-biblio-md2latex mcp-draft-refined-v3.md \
  --bibliography-style spbasic_pt \
  --zotero-api-key $ZOTERO_KEY \
  --zotero-library-id $ZOTERO_ID
```

**Output Files:**
```
mcp-draft-refined-v3.tex         # Main LaTeX file
references.bib                    # BibTeX database
spbasic_pt.bst                   # Bibliography style (copied)
tables/table_1.tex               # Extracted tables
```

---

## Phase 4: LaTeX → PDF Compilation (ZERO Errors/Warnings)

### Objective
Compile LaTeX to PDF with **ZERO** errors and **ZERO** warnings.

### Compilation Pipeline

**Standard LaTeX Build Sequence:**

```bash
cd /Users/petteri/Dropbox/.../mcp-review/

# First pass - expand references
xelatex mcp-draft-refined-v3.tex

# Process bibliography
bibtex mcp-draft-refined-v3

# Second pass - insert citations
xelatex mcp-draft-refined-v3.tex

# Third pass - resolve cross-references
xelatex mcp-draft-refined-v3.tex
```

**Why xelatex?**
- Unicode support (handles special characters)
- Modern font support
- Better handling of hyperlinks
- Preferred by many journals/conferences

**Why 3 passes?**
1. First pass: Create `.aux` file with citation keys
2. BibTeX: Generate `.bbl` file from `.bib` using citation keys
3. Second pass: Insert bibliography and citations
4. Third pass: Resolve page numbers and cross-references

### Error Detection

**Critical Errors (MUST NOT EXIST):**

```bash
# Check for LaTeX errors
grep "^!" mcp-draft-refined-v3.log

# Common errors:
# ! Undefined control sequence
# ! Missing $ inserted
# ! File not found
# ! Package error
```

**Example Error:**
```
! Undefined control sequence.
l.123 \citep{abaza2024managing}
```

**Resolution:** Citation key not in `.bib` file → missing citation

**Warnings (MUST NOT EXIST):**

```bash
# Check for warnings
grep "Warning" mcp-draft-refined-v3.log

# Common warnings:
# LaTeX Warning: Citation 'key' undefined
# LaTeX Warning: Reference 'label' undefined
# Package hyperref Warning: ...
# Package natbib Warning: ...
```

**Example Warning:**
```
LaTeX Warning: Citation `consumeraffairs2025water' undefined on input line 245.
```

**Resolution:** Citation in text but not in bibliography

### PDF Validation

**Check for Placeholder Citations:**

```bash
# Extract text from PDF
pdftotext mcp-draft-refined-v3.pdf

# Search for problematic patterns
grep -E "\(\?\)" mcp-draft-refined-v3.txt        # (?) citations
grep -E "Unknown" mcp-draft-refined-v3.txt      # (Unknown) citations
grep -E "\[1\]|\[2\]" mcp-draft-refined-v3.txt  # Numbered citations (wrong style)
```

**Expected:** ZERO matches for all patterns

**Visual Inspection Points:**
1. Title page formatting
2. Abstract structure
3. Section numbering
4. Figure/table captions
5. Bibliography formatting
6. Hyperlink colors (blue for external, black for internal)

### Automated Compilation Tool

**File:** `scripts/compile_latex_with_validation.py` (to be created)

**Usage:**
```bash
python scripts/compile_latex_with_validation.py \
  mcp-draft-refined-v3.tex \
  --validate-citations \
  --check-warnings \
  --output-report compilation-report.json
```

**Expected Output:**
```
Compiling mcp-draft-refined-v3.tex...
✓ Pass 1 (xelatex): Success
✓ BibTeX: 87 citations processed, 0 errors
✓ Pass 2 (xelatex): Success
✓ Pass 3 (xelatex): Success

Validation:
✓ ZERO LaTeX errors
✓ ZERO LaTeX warnings
✓ ZERO undefined citations
✓ ZERO (?) in PDF
✓ ZERO (Unknown) in PDF

PDF generated: mcp-draft-refined-v3.pdf
Status: READY FOR ARXIV SUBMISSION
```

---

## Phase 5: Bibliography Formatting Validation

### Objective
Ensure bibliography meets arXiv standards with hyperlinked authors and no raw URLs.

### Hard-Coded Bibliography (.bbl file)

**Why Hard-Code?**
- BibTeX styles have limitations (can't hyperlink individual authors)
- arXiv requires maximum compatibility
- Full control over formatting
- Consistent with previously accepted arXiv papers

**Structure:**

```latex
\begin{thebibliography}{99}

\bibitem{abaza2024managing}
\href{https://doi.org/10.1145/3626091}{Hazem Abaza},
\href{https://doi.org/10.1145/3626091}{Debayan Roy},
\href{https://doi.org/10.1145/3626091}{Bohdan Trach},
\href{https://doi.org/10.1145/3626091}{Wanli Chang},
\href{https://doi.org/10.1145/3626091}{Selma Saidi},
\href{https://doi.org/10.1145/3626091}{Antonios Motakis},
\href{https://doi.org/10.1145/3626091}{Wei Ren},
\href{https://doi.org/10.1145/3626091}{Yutao Lin} (2024)
Managing End-to-End Timing Jitters in ROS2 Computation Chains
\textit{Proceedings of the 32nd International Conference on
Real-Time Networks and Systems} 229--241.

\end{thebibliography}
```

**Key Features:**
1. Each author individually hyperlinked
2. Same DOI for all authors of same paper
3. Title NOT hyperlinked (authors are the links)
4. Journal/conference name in italics
5. Pages with en-dash: `229--241` (not `229-241`)

### Raw URL Elimination

**FORBIDDEN Patterns:**

```latex
% ❌ WRONG - Raw URL visible
\bibitem{ref1}
Author (2024) Title. https://doi.org/10.1234/example

% ❌ WRONG - URL in \url{}
\bibitem{ref2}
Author (2024) Title. \url{https://doi.org/10.1234/example}

% ✅ CORRECT - URL embedded in hyperlink
\bibitem{ref3}
\href{https://doi.org/10.1234/example}{Author} (2024) Title.
```

**Detection:**
```bash
# Find raw URLs in .bbl file
grep -E "https?://" mcp-draft-refined-v3.bbl | grep -v "href"
```

**Expected:** Zero matches (all URLs should be inside `\href{}`)

### Formatting Rules (Springer spbasic_pt Style)

**Journal Articles:**
```
Author(s) (Year) Title Journal Volume(Issue):Pages
```

**Conference Papers:**
```
Author(s) (Year) Title Conference Proceedings Pages
```

**Books:**
```
Author(s) (Year) Title Publisher
```

**arXiv Preprints:**
```
Author(s) (Year) Title arXiv:ID
```

**Formatting Details:**
- **Authors:** Full names (First Last), not initials
- **Year:** (YYYY) after authors
- **Title:** Sentence case, no quotes
- **Journal/Conference:** Italicized (`\textit{}`)
- **Volume(Issue):** Bold volume, normal issue: `\textbf{239}(1)`
- **Pages:** En-dash: `180--204`
- **DOI:** Embedded in author hyperlinks, not displayed

### Hard-Coded Bibliography Generator

**File:** `scripts/hardcode_bibliography.py`

**Usage:**
```bash
python scripts/hardcode_bibliography.py \
  --bib references.bib \
  --output mcp-draft-refined-v3.bbl \
  --style arxiv-hyperlinked
```

**Process:**
1. Read BibTeX entries
2. For each entry:
   - Extract all authors
   - Wrap each author in `\href{DOI}{Author}`
   - Format title, journal, volume, pages
   - Apply italics, bold as needed
3. Write `.bbl` file
4. Validate: no raw URLs, all authors hyperlinked

**Validation Checks:**
```python
def validate_bbl_file(bbl_path):
    content = bbl_path.read_text()

    # Check 1: No raw URLs
    raw_urls = re.findall(r'https?://[^\s}]+', content)
    raw_urls_outside_href = [
        url for url in raw_urls
        if f'\\href{{{url}}}' not in content
    ]
    assert len(raw_urls_outside_href) == 0, f"Raw URLs found: {raw_urls_outside_href}"

    # Check 2: All authors hyperlinked
    bibitems = re.findall(r'\\bibitem\{[^}]+\}(.*?)(?=\\bibitem|\\end)', content, re.DOTALL)
    for item in bibitems:
        # Count authors (naive: look for commas before year)
        # Verify \href count matches author count
        pass

    # Check 3: Proper formatting
    assert '\\textit{' in content, "Journal names should be italicized"
    assert '--' in content, "Use en-dash for page ranges"

    return True
```

---

## Phase 6: Create Test Corpus from Reference Paper

### Objective
Extract reference examples from successfully submitted arXiv paper to use as ground truth.

### Source Paper

**URL:** https://arxiv.org/pdf/2508.01965v1
**Title:** (UAD Review paper - actual title to be extracted)
**Authors:** Petteri Teikari et al.
**Submitted:** August 2025
**Status:** Successfully accepted by arXiv

**Why This Paper?**
- Represents proven working format
- Uses spbasic_pt bibliography style
- Has hyperlinked authors
- No raw URLs in references
- Compiled without errors on arXiv servers

### Extraction Process

#### Step 1: Download and Parse PDF

```bash
# Download PDF
wget https://arxiv.org/pdf/2508.01965v1 -O arxiv-reference-paper.pdf

# Extract text (for analysis)
pdftotext arxiv-reference-paper.pdf arxiv-reference-paper.txt

# Extract images (for documentation)
pdfimages -png arxiv-reference-paper.pdf page
```

#### Step 2: Extract Reference Section

**Manual Extraction Required:**
- Locate "References" section in PDF
- Copy reference list (last 2-3 pages typically)
- Save as structured examples

**Sample References to Extract:**

From the image you showed me, I can see these reference examples:

1. **Conference Paper:**
```
Hazem Abaza, Debayan Roy, Bohdan Trach, Wanli Chang,
Selma Saidi, Antonios Motakis, Wei Ren, Yutao Lin (2024)
Managing End-to-End Timing Jitters in ROS2 Computation Chains
Proceedings of the 32nd International Conference on Real-Time
Networks and Systems:229–241.
```

2. **Journal Article:**
```
Alqudsi and Makaraci (2025) UAV Swarms: Research, Challenges,
and Future Directions Journal of Engineering and Applied
Science 72(1).
```

3. **arXiv Preprint:**
```
Abdullah Altawaitan, Jason Stanley, Sambaran Ghosal, Thai Duong,
Nikolay Atanasov (2025) Learned IMU Bias Prediction for Invariant
Visual Inertial Odometry arXiv:2505.06748.
```

4. **Online Source:**
```
Consumer Affairs (2025) Water Damage Insurance Claims Statistics
(accessed 2025-08-02).
```

#### Step 3: Create Test Files

**File 1:** `tests/test-files/arxiv-reference-examples.tex`

```latex
% Reference examples from successfully submitted arXiv paper
% Source: https://arxiv.org/pdf/2508.01965v1
% Date: 2025-08-02

\documentclass[10pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage{hyperref}

\begin{document}

\section*{Reference Format Examples}

These examples are extracted from an arXiv paper that successfully
passed all validation checks.

\subsection*{Conference Paper Format}
\begin{thebibliography}{99}
\bibitem{abaza2024}
\href{https://doi.org/10.1145/3626091}{Hazem Abaza},
\href{https://doi.org/10.1145/3626091}{Debayan Roy},
\href{https://doi.org/10.1145/3626091}{Bohdan Trach},
\href{https://doi.org/10.1145/3626091}{Wanli Chang},
\href{https://doi.org/10.1145/3626091}{Selma Saidi},
\href{https://doi.org/10.1145/3626091}{Antonios Motakis},
\href{https://doi.org/10.1145/3626091}{Wei Ren},
\href{https://doi.org/10.1145/3626091}{Yutao Lin} (2024)
Managing End-to-End Timing Jitters in ROS2 Computation Chains
\textit{Proceedings of the 32nd International Conference on
Real-Time Networks and Systems}:229--241.
\end{thebibliography}

% Key features:
% - Each author individually hyperlinked
% - Same DOI for all authors
% - Conference name in italics
% - En-dash for page range (229--241)
% - No raw URLs visible

\subsection*{Journal Article Format}
\begin{thebibliography}{99}
\bibitem{alqudsi2025}
\href{https://doi.org/...}{Alqudsi} and
\href{https://doi.org/...}{Makaraci} (2025)
UAV Swarms: Research, Challenges, and Future Directions
\textit{Journal of Engineering and Applied Science} 72(1).
\end{thebibliography}

% Key features:
% - "and" between two authors
% - Journal name in italics
% - Volume(Issue) format

\subsection*{arXiv Preprint Format}
\begin{thebibliography}{99}
\bibitem{altawaitan2025}
\href{https://arxiv.org/abs/2505.06748}{Abdullah Altawaitan},
\href{https://arxiv.org/abs/2505.06748}{Jason Stanley},
\href{https://arxiv.org/abs/2505.06748}{Sambaran Ghosal},
\href{https://arxiv.org/abs/2505.06748}{Thai Duong},
\href{https://arxiv.org/abs/2505.06748}{Nikolay Atanasov} (2025)
Learned IMU Bias Prediction for Invariant Visual Inertial Odometry
\textit{arXiv}:2505.06748.
\end{thebibliography}

% Key features:
% - arXiv URL in hyperlinks
% - arXiv ID displayed
% - "arXiv" in italics

\end{document}
```

**File 2:** `tests/test-files/test-mcp-conversion.md`

```markdown
# Minimal Test Case for MD→LaTeX Conversion

## Introduction

This minimal test case validates the complete conversion workflow
from markdown to arXiv-ready PDF.

## Test Citations

Recent work on ROS2 timing by [Abaza et al. (2024)](https://doi.org/10.1145/3626091)
demonstrates the importance of end-to-end jitter management.

UAV swarm research, as reviewed by [Alqudsi and Makaraci (2025)](https://doi.org/...),
shows significant challenges remain.

The work on visual odometry by [Altawaitan et al. (2025)](https://arxiv.org/abs/2505.06748)
provides learned IMU bias prediction.

## Test Table

| Method | Accuracy | Speed |
|--------|----------|-------|
| A      | 95%      | Fast  |
| B      | 92%      | Slow  |
| C      | 98%      | Medium|

## Conclusion

This test case covers:
- Conference papers
- Journal articles
- arXiv preprints
- Simple tables
```

**Expected Output Files:**
```
tests/test-files/
├── arxiv-reference-examples.tex     # Reference standard
├── test-mcp-conversion.md           # Minimal test input
├── test-mcp-conversion.tex          # Expected LaTeX output
├── test-mcp-conversion.bbl          # Expected bibliography
└── test-mcp-conversion.pdf          # Expected PDF
```

---

## Phase 7: MCP Server Integration

### Objective
Ensure the Model Context Protocol server can execute the entire workflow autonomously.

### MCP Server Architecture

**File:** `mcp-servers/deep-biblio/src/deep_biblio/server.py`

**MCP Protocol:** JSON-RPC based communication between Claude and Python tools

**Available Tools (Relevant to Workflow):**

1. `convert_markdown_to_arxiv_latex`
2. `validate_markdown_structure`
3. `resolve_citations_from_zotero`
4. `compile_latex_to_pdf`
5. `validate_bibliography_formatting`
6. `generate_hardcoded_bibliography`

### Tool Implementations

#### Tool 1: `convert_markdown_to_arxiv_latex`

**Purpose:** Complete end-to-end conversion with validation

**Input Parameters:**
```json
{
  "markdown_file": "/path/to/manuscript.md",
  "zotero_api_key": "...",
  "zotero_library_id": "...",
  "bibliography_style": "spbasic_pt",
  "output_dir": null  // null = same as input
}
```

**Workflow:**
1. Validate markdown structure (Phase 1)
2. Resolve citations via Zotero (Phase 2)
3. Convert to LaTeX (Phase 3)
4. Compile to PDF (Phase 4)
5. Validate bibliography (Phase 5)
6. Generate hardcoded .bbl if requested (Phase 5)

**Output:**
```json
{
  "status": "success",
  "latex_file": "/path/to/manuscript.tex",
  "pdf_file": "/path/to/manuscript.pdf",
  "bibliography_file": "/path/to/references.bib",
  "validation": {
    "markdown_errors": 0,
    "missing_citations": 0,
    "latex_errors": 0,
    "latex_warnings": 0,
    "pdf_unknown_citations": 0
  },
  "statistics": {
    "total_citations": 87,
    "resolved_citations": 87,
    "tables": 3,
    "compilation_time": "45.2s"
  }
}
```

**Error Response:**
```json
{
  "status": "error",
  "error_type": "missing_citations",
  "message": "2 citations could not be resolved",
  "missing_citations": [
    {
      "text": "Consumer Affairs (2025)",
      "url": "https://www.consumeraffairs.com/...",
      "action": "Add to Zotero manually"
    }
  ],
  "zotero_import_commands": [
    "zotero-cli add --url https://www.consumeraffairs.com/..."
  ]
}
```

#### Tool 2: `validate_markdown_structure`

**Purpose:** Pre-flight check before conversion

**Input:**
```json
{
  "markdown_file": "/path/to/manuscript.md"
}
```

**Output:**
```json
{
  "status": "pass",
  "brackets": {"matched": true, "errors": []},
  "tables": {"count": 3, "valid": true, "errors": []},
  "citations": {
    "total": 87,
    "dois": 65,
    "arxiv": 12,
    "web_urls": 10
  }
}
```

#### Tool 3: `compile_latex_to_pdf`

**Purpose:** Compile with validation

**Input:**
```json
{
  "latex_file": "/path/to/manuscript.tex",
  "validate_citations": true,
  "check_warnings": true
}
```

**Output:**
```json
{
  "status": "success",
  "pdf_file": "/path/to/manuscript.pdf",
  "compilation_passes": 3,
  "errors": 0,
  "warnings": 0,
  "undefined_citations": 0,
  "compilation_log": "..."
}
```

### MCP Server Testing

**Test File:** `mcp-servers/deep-biblio/tests/test_arxiv_workflow.py`

```python
import pytest
from deep_biblio.server import convert_markdown_to_arxiv_latex

def test_complete_workflow():
    """Test full MD→PDF workflow with real file"""
    result = convert_markdown_to_arxiv_latex(
        markdown_file="tests/test-files/test-mcp-conversion.md",
        zotero_api_key=os.getenv("ZOTERO_API_KEY"),
        zotero_library_id=os.getenv("ZOTERO_LIBRARY_ID")
    )

    assert result["status"] == "success"
    assert result["validation"]["markdown_errors"] == 0
    assert result["validation"]["missing_citations"] == 0
    assert result["validation"]["latex_errors"] == 0
    assert result["validation"]["latex_warnings"] == 0

    # Verify PDF exists and is valid
    pdf_path = Path(result["pdf_file"])
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 10000  # At least 10KB

    # Verify no (?) or (Unknown) in PDF
    pdf_text = extract_text_from_pdf(pdf_path)
    assert "(?" not in pdf_text
    assert "(Unknown)" not in pdf_text
```

**Integration Test:**
```bash
# Start MCP server
python mcp-servers/deep-biblio/src/deep_biblio/server.py

# Test via Claude (manual)
# User: "Convert mcp-draft-refined-v3.md to arXiv LaTeX"
# Claude calls: convert_markdown_to_arxiv_latex tool
# Expected: Success with zero errors
```

---

## Execution Workflow Summary

### Sequential Execution (Must Follow Order)

```
INPUT: mcp-draft-refined-v3.md
  ↓
[Phase 1] Validate Markdown Structure
  ├─ Check brackets: [ ] ( )
  ├─ Validate tables
  └─ Extract citations (87 total)
  ↓
  ✓ PASS → Continue
  ✗ FAIL → Report errors, STOP
  ↓
[Phase 2] Resolve Citations
  ├─ Query Zotero API (primary)
  ├─ Search local .bib (fallback)
  └─ Generate missing report
  ↓
  ✓ 100% resolved → Continue
  ✗ Missing citations → Report, STOP
  ↓
[Phase 3] Convert MD→LaTeX
  ├─ Replace citations with \citep{}
  ├─ Extract tables
  ├─ Generate preamble (10pt, spbasic_pt)
  └─ Create references.bib
  ↓
  → mcp-draft-refined-v3.tex
  → references.bib
  ↓
[Phase 4] Compile LaTeX→PDF
  ├─ xelatex (pass 1)
  ├─ bibtex
  ├─ xelatex (pass 2)
  └─ xelatex (pass 3)
  ↓
  ✓ 0 errors, 0 warnings → Continue
  ✗ Errors/warnings → Report, STOP
  ↓
[Phase 5] Validate Bibliography
  ├─ Check for (?) citations
  ├─ Check for raw URLs
  └─ Verify author hyperlinks
  ↓
  ✓ All checks pass → Continue
  ✗ Issues found → Generate .bbl, recompile
  ↓
OUTPUT: mcp-draft-refined-v3.pdf
  ✓ READY FOR ARXIV SUBMISSION
```

### Success Metrics (Zero Tolerance)

**Pre-Conversion:**
- ✅ 0 bracket mismatches
- ✅ 0 table structure errors
- ✅ 87/87 citations extracted

**Citation Resolution:**
- ✅ 87/87 citations resolved (100%)
- ✅ 0 missing citations
- ✅ 87 BibTeX entries generated

**LaTeX Compilation:**
- ✅ 0 LaTeX errors
- ✅ 0 LaTeX warnings
- ✅ 0 undefined citations
- ✅ 3 compilation passes successful

**PDF Validation:**
- ✅ 0 (?) in output
- ✅ 0 (Unknown) in output
- ✅ 0 raw URLs in bibliography
- ✅ 87 references with hyperlinked authors

---

## Troubleshooting Guide

### Common Issues and Resolutions

#### Issue 1: Missing Citations

**Symptom:**
```
LaTeX Warning: Citation `consumeraffairs2025water' undefined
```

**Diagnosis:**
- Citation key in `.tex` but not in `.bib`
- Zotero failed to resolve citation
- Web URL not in Zotero database

**Resolution:**
1. Check missing-citations.md report
2. Manually add to Zotero:
   ```bash
   # Via web interface
   open "https://www.zotero.org/save?url=..."

   # Via CLI (if available)
   zotero-cli add --url "https://..."
   ```
3. Re-run conversion

#### Issue 2: Table Conversion Errors

**Symptom:**
```
! Misplaced \noalign.
```

**Diagnosis:**
- Malformed table in markdown
- Column count mismatch
- Invalid alignment specifiers

**Resolution:**
1. Run validation: `python scripts/validate_markdown_structure.py`
2. Check reported line numbers
3. Fix table structure:
   ```markdown
   | A | B | C |
   |---|---|---|
   | 1 | 2 | 3 |  ✓ Correct
   | 4 | 5 |      ✗ Missing column
   ```

#### Issue 3: Undefined Control Sequence

**Symptom:**
```
! Undefined control sequence.
l.123 \citep{abaza2024managing}
```

**Diagnosis:**
- natbib package not loaded
- Citation command misspelled
- Wrong bibliography style

**Resolution:**
1. Verify preamble has:
   ```latex
   \usepackage[authoryear,round]{natbib}
   \bibliographystyle{spbasic_pt}
   ```
2. Check `.tex` file generated correctly
3. Re-run conversion with `--bibliography-style spbasic_pt`

#### Issue 4: Raw URLs in Bibliography

**Symptom:**
Visible URLs in PDF reference list

**Diagnosis:**
- BibTeX entry has `url` field displayed
- Style file shows URLs
- Not using hard-coded `.bbl`

**Resolution:**
1. Generate hard-coded bibliography:
   ```bash
   python scripts/hardcode_bibliography.py \
     --bib references.bib \
     --output manuscript.bbl \
     --style arxiv-hyperlinked
   ```
2. Recompile (will use `.bbl` instead of `.bib`)

#### Issue 5: Font Size Wrong

**Symptom:**
PDF has 11pt or 12pt font instead of 10pt

**Diagnosis:**
- Default in latex_builder.py incorrect
- User specified wrong font size
- Template override

**Resolution:**
1. Check `\documentclass[10pt,...]` in `.tex`
2. Verify latex_builder.py line ~50:
   ```python
   font_size = "10pt"  # MUST be 10pt for arXiv
   ```
3. Re-run conversion

---

## Deliverables Checklist

### Code Deliverables

- [ ] `scripts/validate_markdown_structure.py` - Phase 1 validation
- [ ] `scripts/compile_latex_with_validation.py` - Phase 4 compilation
- [ ] `scripts/hardcode_bibliography.py` - Phase 5 bibliography generation
- [ ] `mcp-servers/deep-biblio/src/deep_biblio/arxiv_converter.py` - Phase 7 MCP integration
- [ ] `tests/test-files/arxiv-reference-examples.tex` - Phase 6 reference standard
- [ ] `tests/test-files/test-mcp-conversion.md` - Phase 6 minimal test
- [ ] `tests/test_arxiv_workflow.py` - Phase 7 integration tests

### Documentation Deliverables

- [ ] This plan document (you're reading it)
- [ ] MCP server README with workflow examples
- [ ] Troubleshooting guide (included above)
- [ ] User guide for command-line tools
- [ ] API documentation for Python modules

### Test Results

- [ ] mcp-draft-refined-v3.pdf generated successfully
- [ ] Zero LaTeX errors
- [ ] Zero LaTeX warnings
- [ ] Zero (?) citations
- [ ] Zero (Unknown) citations
- [ ] Zero raw URLs
- [ ] All authors hyperlinked
- [ ] Validation report confirms all checks passed

### Workflow Validation

- [ ] MCP server can execute full workflow autonomously
- [ ] Claude can successfully convert markdown → PDF via MCP
- [ ] Missing citations are reported correctly
- [ ] Compilation errors are caught and reported
- [ ] Bibliography formatting validated automatically

---

## Timeline and Milestones

### Estimated Effort

**Total Time:** 8-12 hours of development + testing

**Phase Breakdown:**
- Phase 1 (Markdown validation): 2 hours
- Phase 2 (Citation resolution): 2 hours
- Phase 3 (MD→LaTeX conversion): 1 hour (mostly exists)
- Phase 4 (Compilation validation): 2 hours
- Phase 5 (Bibliography formatting): 3 hours
- Phase 6 (Test corpus creation): 1 hour
- Phase 7 (MCP integration): 2 hours

**Testing and Validation:** 3 hours

### Milestones

**Milestone 1:** Validation scripts complete
- [ ] validate_markdown_structure.py working
- [ ] Can detect bracket mismatches
- [ ] Can detect table errors
- [ ] Can extract all citations

**Milestone 2:** Citation resolution working
- [ ] Zotero API integration functional
- [ ] Fallback to local .bib working
- [ ] Missing citations report generated

**Milestone 3:** LaTeX compilation validated
- [ ] compile_latex_with_validation.py working
- [ ] Can detect all errors and warnings
- [ ] PDF validation (no ? or Unknown)

**Milestone 4:** Bibliography formatting correct
- [ ] hardcode_bibliography.py working
- [ ] Authors properly hyperlinked
- [ ] No raw URLs
- [ ] Matches arXiv reference style

**Milestone 5:** End-to-end test passing
- [ ] mcp-draft-refined-v3.md converts successfully
- [ ] Zero errors, zero warnings
- [ ] PDF ready for arXiv submission

**Milestone 6:** MCP server integration
- [ ] All tools implemented
- [ ] Claude can execute workflow
- [ ] Integration tests passing

---

## Success Criteria Verification

### Pre-Submission Checklist

Before marking this workflow as complete, verify:

**Markdown Validation:**
- [ ] Zero bracket mismatches detected
- [ ] Zero table structure errors detected
- [ ] All citations extracted (100% coverage)

**Citation Resolution:**
- [ ] 100% of citations resolved from Zotero or fallback
- [ ] Zero missing citations in final output
- [ ] BibTeX keys generated correctly

**LaTeX Compilation:**
- [ ] Zero LaTeX errors in compilation
- [ ] Zero LaTeX warnings in compilation
- [ ] Three-pass compilation successful
- [ ] PDF generated successfully

**PDF Quality:**
- [ ] No (?) citations in PDF text
- [ ] No (Unknown) citations in PDF text
- [ ] No numbered citations (must be author-year)
- [ ] Hyperlinks functional (authors → DOI)

**Bibliography Formatting:**
- [ ] No raw URLs visible in reference list
- [ ] All authors individually hyperlinked
- [ ] Journal/conference names italicized
- [ ] Page ranges use en-dash (--) not hyphen (-)
- [ ] Formatting matches arXiv reference paper

**MCP Server:**
- [ ] All tools working in isolation
- [ ] Full workflow executable via MCP
- [ ] Error reporting clear and actionable
- [ ] Integration tests passing

**Documentation:**
- [ ] This plan document complete
- [ ] User guide written
- [ ] Troubleshooting guide complete
- [ ] Example usage documented

---

## Appendix A: File Locations Reference

### Input Files

```
/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/
└── publications/mcp-review/
    └── mcp-draft-refined-v3.md  # Target test file
```

### Repository Structure

```
deep-biblio-tools/
├── src/converters/md_to_latex/
│   ├── converter.py               # Main conversion engine
│   ├── citation_manager.py        # Citation handling
│   ├── latex_builder.py           # LaTeX document structure
│   ├── utils.py                   # Text sanitization
│   └── zotero_integration.py      # Zotero API client
├── scripts/
│   ├── validate_markdown_structure.py  # NEW: Phase 1
│   ├── compile_latex_with_validation.py  # NEW: Phase 4
│   └── hardcode_bibliography.py   # NEW: Phase 5
├── mcp-servers/deep-biblio/
│   └── src/deep_biblio/
│       ├── server.py              # MCP tool implementations
│       └── arxiv_converter.py     # NEW: Phase 7
├── tests/test-files/
│   ├── arxiv-reference-examples.tex  # NEW: Phase 6
│   ├── test-mcp-conversion.md     # NEW: Phase 6
│   └── test-mcp-conversion.tex    # NEW: Expected output
└── docs/
    └── PLAN-arxiv-ready-conversion-validation.md  # This document
```

### Output Files (Generated)

```
/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/
└── publications/mcp-review/
    ├── mcp-draft-refined-v3.md    # Input
    ├── mcp-draft-refined-v3.tex   # Generated LaTeX
    ├── mcp-draft-refined-v3.pdf   # Final PDF
    ├── references.bib              # BibTeX database
    ├── mcp-draft-refined-v3.bbl   # Hard-coded bibliography
    ├── spbasic_pt.bst             # Bibliography style (copied)
    ├── validation-report.json     # Phase 1 output
    ├── missing-citations.md       # Phase 2 output (if any)
    ├── compilation-report.json    # Phase 4 output
    └── tables/                    # Extracted tables
        ├── table_1.tex
        ├── table_2.tex
        └── table_3.tex
```

---

## Appendix B: Command Reference

### Validation Commands

```bash
# Phase 1: Validate markdown structure
python scripts/validate_markdown_structure.py \
  /path/to/manuscript.md \
  --output validation-report.json

# Phase 2: Resolve citations
python mcp-servers/deep-biblio/convert-with-zotero-api.py \
  --input manuscript.md \
  --zotero-url http://localhost:1969 \
  --missing-report missing-citations.md

# Phase 3: Convert to LaTeX
deep-biblio-md2latex manuscript.md \
  --bibliography-style spbasic_pt \
  --zotero-api-key $ZOTERO_KEY

# Phase 4: Compile with validation
python scripts/compile_latex_with_validation.py \
  manuscript.tex \
  --validate-citations \
  --check-warnings

# Phase 5: Generate hard-coded bibliography
python scripts/hardcode_bibliography.py \
  --bib references.bib \
  --output manuscript.bbl \
  --style arxiv-hyperlinked
```

### Manual Compilation

```bash
# Standard LaTeX build
xelatex manuscript.tex
bibtex manuscript
xelatex manuscript.tex
xelatex manuscript.tex

# Check for errors
grep "^!" manuscript.log

# Check for warnings
grep "Warning" manuscript.log

# Validate PDF
pdftotext manuscript.pdf
grep "(?" manuscript.txt
grep "Unknown" manuscript.txt
```

### MCP Server Commands

```bash
# Start MCP server
cd mcp-servers/deep-biblio
python src/deep_biblio/server.py

# Test specific tool (via Python)
from deep_biblio.server import convert_markdown_to_arxiv_latex

result = convert_markdown_to_arxiv_latex(
    markdown_file="manuscript.md",
    zotero_api_key="...",
    zotero_library_id="..."
)
```

---

## Appendix C: Error Message Reference

### Markdown Validation Errors

```
Error: Unmatched opening bracket
  Line 145: [Author (Year]  # Missing closing )
  Fix: Add closing parenthesis

Error: Unmatched closing bracket
  Line 203: Author Year)]  # Missing opening [
  Fix: Add opening bracket

Error: Table structure invalid
  Line 78: Column count mismatch (expected 3, found 2)
  Fix: Add missing cell or adjust header
```

### Citation Resolution Errors

```
Error: Citation not found in Zotero
  Citation: Consumer Affairs (2025)
  URL: https://www.consumeraffairs.com/...
  Action: Add to Zotero manually
  Import: zotero-cli add --url "https://..."

Error: Multiple matches found
  Citation: Smith (2024)
  Matches:
    1. Smith, J. (2024) Title A
    2. Smith, R. (2024) Title B
  Action: Disambiguate in markdown [Smith, J. (2024)]
```

### LaTeX Compilation Errors

```
Error: Undefined control sequence
  File: manuscript.tex:123
  Line: \citep{abaza2024managing}
  Cause: natbib not loaded or citation key invalid
  Fix: Add \usepackage{natbib} to preamble

Error: Missing $ inserted
  File: manuscript.tex:456
  Cause: Special character not escaped
  Fix: Escape $ as \$ outside math mode

Error: File not found
  File: spbasic_pt.bst not found
  Cause: Bibliography style file not copied
  Fix: Ensure spbasic_pt.bst in same directory
```

### Bibliography Formatting Issues

```
Warning: Raw URL detected
  Line: https://doi.org/10.1234/example
  Fix: Wrap in \href{...}{text}

Warning: Author not hyperlinked
  Entry: Smith (2024) Title
  Fix: \href{DOI}{Smith} (2024) Title

Warning: Wrong dash type
  Pages: 123-456
  Fix: Use en-dash: 123--456
```

---

## Appendix D: Example Outputs

### Example 1: Successful Validation Report

```json
{
  "validation_date": "2025-10-25T19:00:00Z",
  "input_file": "mcp-draft-refined-v3.md",
  "status": "PASS",
  "markdown_validation": {
    "brackets": {
      "total_citations": 87,
      "unmatched_open": 0,
      "unmatched_close": 0,
      "status": "PASS"
    },
    "tables": {
      "total_tables": 3,
      "valid_tables": 3,
      "errors": [],
      "status": "PASS"
    },
    "citations": {
      "total": 87,
      "dois": 65,
      "arxiv": 12,
      "web_urls": 10,
      "status": "PASS"
    }
  },
  "citation_resolution": {
    "total_citations": 87,
    "resolved_zotero": 75,
    "resolved_local": 12,
    "missing": 0,
    "status": "PASS"
  },
  "latex_compilation": {
    "passes": 3,
    "errors": 0,
    "warnings": 0,
    "undefined_citations": 0,
    "status": "PASS"
  },
  "pdf_validation": {
    "unknown_citations": 0,
    "question_mark_citations": 0,
    "raw_urls": 0,
    "hyperlinked_authors": 87,
    "status": "PASS"
  },
  "overall_status": "READY_FOR_ARXIV"
}
```

### Example 2: Missing Citations Report

```markdown
# Missing Citations Report

Generated: 2025-10-25 19:00:00
Input: mcp-draft-refined-v3.md

## Summary

- Total citations: 87
- Resolved: 85 (97.7%)
- Missing: 2 (2.3%)

## Missing Citations

### 1. Consumer Affairs (2025) - Water Damage Insurance Claims

**Original citation:**
```markdown
[Consumer Affairs (2025)](https://www.consumeraffairs.com/homeowners-insurance/water-damage.html)
```

**Issue:** Web URL not in Zotero database

**Action Required:**
1. Visit URL to verify content
2. Add to Zotero:
   - Option A: Browser extension
   - Option B: Manual entry
3. Re-run conversion

**Zotero Import Command:**
```bash
# Using Zotero CLI (if available)
zotero-cli add --url "https://www.consumeraffairs.com/homeowners-insurance/water-damage.html"

# Or use web interface
open "https://www.zotero.org/save?url=https://www.consumeraffairs.com/homeowners-insurance/water-damage.html"
```

### 2. Ahmed and Jenihhin (2022) - UAV Computing Platforms Survey

**Original citation:**
```markdown
[Ahmed and Jenihhin (2022)](https://doi.org/10.3390/s22166286)
```

**Issue:** DOI lookup failed (possibly incorrect DOI)

**Action Required:**
1. Verify DOI is correct: https://doi.org/10.3390/s22166286
2. If correct, add manually to Zotero
3. If incorrect, find correct DOI and update markdown

**Verification:**
```bash
# Test DOI resolution
curl -L https://doi.org/10.3390/s22166286
```

## Next Steps

1. Resolve missing citations (add to Zotero)
2. Re-run conversion:
   ```bash
   deep-biblio-md2latex mcp-draft-refined-v3.md
   ```
3. Verify all citations resolved
```

---

## Conclusion

This comprehensive plan ensures a **ZERO-GLITCH** workflow from markdown manuscript to arXiv-ready PDF. By following the seven phases systematically and validating at each step, we guarantee that the final PDF will compile without errors, contain no missing citations, and meet all arXiv formatting requirements.

The plan is designed to be:
- **Reproducible:** Can be executed multiple times with same results
- **Automated:** MCP server can handle autonomously
- **Validated:** Every step has verification checks
- **Documented:** Full context for third-party review

**Key Success Factor:** ZERO tolerance means exactly zero - no approximations, no "close enough". Every check must pass before proceeding to the next phase.
