# Comprehensive End-to-End Test Suite Plan for MD→LaTeX→PDF Pipeline

## Executive Summary

**Problem**: Current test suite has critical gaps:
- Tests pass but don't verify the actual MD→LaTeX→PDF conversion works
- No automated detection of broken citation resolution, hyperlink colors, template issues, or bibliography problems
- Manual verification required (you had to ask if the pipeline still works)

**Solution**: Build comprehensive end-to-end integration tests that validate:
1. Full conversion pipeline (MD → LaTeX → PDF)
2. Citation resolution (no `(?)` markers in PDF)
3. Hyperlink colors and styling
4. Template and preamble correctness
5. BBL transformer functionality
6. Bibliography completeness

## Current Test Suite Analysis

### What Works ✅
- **Unit tests**: 348 passing tests for individual components
- **Citation extraction**: Tests verify citations are extracted from markdown
- **DOI/arXiv API mocking**: Tests mock external API calls
- **BibTeX generation**: Tests verify `.bib` file creation

### Critical Gaps ❌
1. **No PDF verification**: Tests don't read generated PDFs to verify citation resolution
2. **No hyperlink color tests**: No validation of link colors in PDF output
3. **No template validation**: Don't verify correct LaTeX preamble is used
4. **No BBL transformer tests**: Missing validation of hyperlinked author names
5. **No end-to-end pipeline tests**: Don't test full MD→LaTeX→PDF flow
6. **No visual regression**: Can't detect if PDF output quality degrades

## Comprehensive Test Plan

### Test Suite Structure

```
tests/
├── integration/
│   ├── test_e2e_conversion.py          # NEW: Full pipeline tests
│   ├── test_pdf_validation.py          # NEW: PDF content verification
│   ├── test_hyperlink_styling.py       # NEW: Color and styling tests
│   ├── test_template_validation.py     # NEW: Preamble tests
│   └── test_bbl_transformer.py         # NEW: BBL transformation tests
├── fixtures/
│   ├── golden-pdfs/                    # NEW: Reference PDFs for comparison
│   ├── test-markdown/                  # NEW: Test markdown files
│   └── expected-output/                # NEW: Expected LaTeX/BibTeX
└── golden-runs/                        # EXISTING: Debug conversion artifacts
```

### Test Categories

## 1. End-to-End Conversion Tests (`test_e2e_conversion.py`)

**Purpose**: Verify complete MD→LaTeX→PDF pipeline produces valid output

**Test Cases**:

### 1.1 Basic Conversion Success
```python
def test_basic_md_to_pdf_conversion(self):
    """Test that simple markdown converts to PDF with citations."""
    # Given: Simple markdown with 2 citations
    markdown_content = """
# Test Document

Citation 1: [Mildenhall et al. (2022)](https://doi.org/10.1145/3503250)
Citation 2: [Zhang et al. (2020)](https://arxiv.org/abs/2003.08934)
"""

    # When: Convert to PDF
    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.md"
        input_file.write_text(markdown_content)

        converter = MarkdownToLatexConverter(output_dir=tmpdir)
        output = converter.convert(markdown_file=input_file)

        # Then: PDF exists and is valid
        pdf_file = Path(tmpdir) / "test.pdf"
        assert pdf_file.exists(), "PDF was not generated"
        assert pdf_file.stat().st_size > 1000, "PDF is suspiciously small"

        # Verify PDF is valid
        with open(pdf_file, 'rb') as f:
            header = f.read(4)
            assert header == b'%PDF', "Not a valid PDF file"
```

### 1.2 Citation Resolution Validation
```python
def test_citations_resolved_in_pdf(self):
    """Test that citations in PDF show author names, not (?)."""
    markdown_content = """
# Test

Citation: [Smith (2020)](https://doi.org/10.1234/example)
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.md"
        input_file.write_text(markdown_content)

        converter = MarkdownToLatexConverter(output_dir=tmpdir)
        converter.convert(markdown_file=input_file)

        # Read PDF text content
        pdf_file = Path(tmpdir) / "test.pdf"
        pdf_text = self._extract_pdf_text(pdf_file)

        # CRITICAL CHECKS
        assert "(?)" not in pdf_text, "Found unresolved citation (?)"
        assert "(Unknown)" not in pdf_text, "Found Unknown author"
        assert "(Anonymous)" not in pdf_text, "Found Anonymous author"

        # Verify bibliography section exists
        assert "References" in pdf_text or "Bibliography" in pdf_text
```

### 1.3 Bibliography Completeness
```python
def test_bibliography_contains_all_citations(self):
    """Test that bibliography has entries for all citations."""
    markdown_content = """
# Test
[Author1 (2020)](https://doi.org/10.1111/1111)
[Author2 (2021)](https://doi.org/10.2222/2222)
[Author3 (2022)](https://doi.org/10.3333/3333)
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.md"
        input_file.write_text(markdown_content)

        converter = MarkdownToLatexConverter(output_dir=tmpdir)
        converter.convert(markdown_file=input_file)

        # Check .bib file
        bib_file = Path(tmpdir) / "references.bib"
        bib_content = bib_file.read_text()

        # Should have 3 entries
        entry_count = bib_content.count("@article{") + bib_content.count("@misc{")
        assert entry_count == 3, f"Expected 3 bib entries, found {entry_count}"

        # No Unknown/Anonymous
        assert "Unknown" not in bib_content
        assert "Anonymous" not in bib_content
```

### 1.4 Multiple Paper Sizes (A4 vs Letter)
```python
def test_paper_size_templates(self):
    """Test conversion with different paper sizes."""
    markdown_content = "# Test\n[Author (2020)](https://doi.org/10.1234/5678)"

    for paper_size in ["a4", "letter"]:
        with tempfile.TemporaryDirectory() as tmpdir:
            converter = MarkdownToLatexConverter(
                output_dir=tmpdir,
                paper_size=paper_size
            )

            input_file = Path(tmpdir) / "test.md"
            input_file.write_text(markdown_content)
            converter.convert(markdown_file=input_file)

            # Verify LaTeX uses correct paper size
            tex_file = Path(tmpdir) / "test.tex"
            tex_content = tex_file.read_text()

            if paper_size == "a4":
                assert "a4paper" in tex_content
            else:
                assert "letterpaper" in tex_content
```

## 2. PDF Validation Tests (`test_pdf_validation.py`)

**Purpose**: Deep validation of PDF content and structure

### 2.1 PDF Text Extraction Helper
```python
def _extract_pdf_text(self, pdf_path: Path) -> str:
    """Extract text from PDF for validation."""
    import PyPDF2

    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text
```

### 2.2 Citation Format Validation
```python
def test_citation_format_author_year(self):
    """Test citations use author-year format, not numbers."""
    markdown_content = """
# Test
Citation: [Goodfellow et al. (2014)](https://arxiv.org/abs/1406.2661)
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.md"
        input_file.write_text(markdown_content)

        converter = MarkdownToLatexConverter(output_dir=tmpdir)
        converter.convert(markdown_file=input_file)

        pdf_text = self._extract_pdf_text(Path(tmpdir) / "test.pdf")

        # Should see (Goodfellow et al., 2014), NOT [1]
        assert "(Goodfellow et al., 2014)" in pdf_text or \
               "(Goodfellow et al. 2014)" in pdf_text, \
               "Citation not in author-year format"

        # Should NOT see numbered citations
        assert not re.search(r'\[\d+\]', pdf_text), \
               "Found numbered citation instead of author-year"
```

### 2.3 No Broken References
```python
def test_no_broken_references(self):
    """Test PDF has no ?? or undefined references."""
    markdown_content = """
# Test
[Author (2020)](https://doi.org/10.1234/5678)
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.md"
        input_file.write_text(markdown_content)

        converter = MarkdownToLatexConverter(output_dir=tmpdir)
        converter.convert(markdown_file=input_file)

        # Check LaTeX log for warnings
        log_file = Path(tmpdir) / "test.log"
        log_content = log_file.read_text()

        assert "undefined" not in log_content.lower(), \
               "LaTeX log shows undefined references"
        assert "??" not in self._extract_pdf_text(Path(tmpdir) / "test.pdf"), \
               "PDF contains ?? markers"
```

## 3. Hyperlink Styling Tests (`test_hyperlink_styling.py`)

**Purpose**: Verify hyperlinks have correct colors and are clickable

### 3.1 LaTeX Hyperref Configuration
```python
def test_hyperlink_colors_in_preamble(self):
    """Test LaTeX preamble sets correct hyperlink colors."""
    markdown_content = "# Test\n[Link](https://example.com)"

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.md"
        input_file.write_text(markdown_content)

        converter = MarkdownToLatexConverter(output_dir=tmpdir)
        converter.convert(markdown_file=input_file)

        tex_file = Path(tmpdir) / "test.tex"
        tex_content = tex_file.read_text()

        # Check hyperref is loaded
        assert r"\usepackage{hyperref}" in tex_content or \
               r"\usepackage[" in tex_content and "hyperref" in tex_content

        # Check color configuration
        # Expected: blue for URLs, blue for citations
        assert "colorlinks=true" in tex_content, \
               "Hyperlinks should use colors, not boxes"
        assert "linkcolor=blue" in tex_content or \
               "citecolor=blue" in tex_content, \
               "Citation links should be blue"
```

### 3.2 Citation Hyperlinks
```python
def test_citations_are_hyperlinked(self):
    """Test that citations in PDF are clickable links to bibliography."""
    markdown_content = """
# Test
See [Author (2020)](https://doi.org/10.1234/5678) for details.
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.md"
        input_file.write_text(markdown_content)

        converter = MarkdownToLatexConverter(output_dir=tmpdir)
        converter.convert(markdown_file=input_file)

        # Check LaTeX uses \citep which hyperref makes clickable
        tex_file = Path(tmpdir) / "test.tex"
        tex_content = tex_file.read_text()

        assert r"\citep{" in tex_content, "Should use \\citep for parenthetical citations"

        # TODO: Extract PDF metadata to verify clickable links
        # This requires parsing PDF annotations/links structure
```

### 3.3 URL Hyperlinks
```python
def test_url_hyperlinks_preserved(self):
    """Test regular URLs are preserved as blue clickable links."""
    markdown_content = """
# Test
Visit [Google](https://www.google.com) or see [arXiv](https://arxiv.org).
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.md"
        input_file.write_text(markdown_content)

        converter = MarkdownToLatexConverter(output_dir=tmpdir)
        converter.convert(markdown_file=input_file)

        tex_file = Path(tmpdir) / "test.tex"
        tex_content = tex_file.read_text()

        # URLs should use \href or \url
        assert r"\href{https://www.google.com}" in tex_content or \
               r"\url{https://www.google.com}" in tex_content, \
               "URLs should be hyperlinked"
```

## 4. Template Validation Tests (`test_template_validation.py`)

**Purpose**: Verify correct LaTeX templates and preambles are used

### 4.1 Preamble Structure
```python
def test_latex_preamble_completeness(self):
    """Test LaTeX file has all required preamble elements."""
    markdown_content = "# Test\n[Author (2020)](https://doi.org/10.1234/5678)"

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.md"
        input_file.write_text(markdown_content)

        converter = MarkdownToLatexConverter(output_dir=tmpdir)
        converter.convert(markdown_file=input_file)

        tex_file = Path(tmpdir) / "test.tex"
        tex_content = tex_file.read_text()

        # Required preamble elements
        required = [
            r"\documentclass",
            r"\usepackage{natbib}",  # For author-year citations
            r"\usepackage{hyperref}",  # For clickable links
            r"\usepackage{graphicx}",  # For images
            r"\usepackage{xcolor}",  # For colors
            r"\begin{document}",
            r"\end{document}",
        ]

        for element in required:
            assert element in tex_content, f"Missing required element: {element}"
```

### 4.2 Bibliography Style
```python
def test_bibliography_style_spbasic_pt(self):
    """Test bibliography uses spbasic_pt style."""
    markdown_content = "# Test\n[Author (2020)](https://doi.org/10.1234/5678)"

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.md"
        input_file.write_text(markdown_content)

        converter = MarkdownToLatexConverter(output_dir=tmpdir)
        converter.convert(markdown_file=input_file)

        tex_file = Path(tmpdir) / "test.tex"
        tex_content = tex_file.read_text()

        # Should use spbasic_pt, not plainnat or other styles
        assert r"\bibliographystyle{spbasic_pt}" in tex_content, \
               "Should use spbasic_pt bibliography style"

        # Should NOT use numbered styles
        assert "plainnat" not in tex_content, \
               "Should not use plainnat (numbered citations)"
```

### 4.3 Citation Package Configuration
```python
def test_natbib_configuration(self):
    """Test natbib is configured for author-year citations."""
    markdown_content = "# Test\n[Author (2020)](https://doi.org/10.1234/5678)"

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.md"
        input_file.write_text(markdown_content)

        converter = MarkdownToLatexConverter(output_dir=tmpdir)
        converter.convert(markdown_file=input_file)

        tex_file = Path(tmpdir) / "test.tex"
        tex_content = tex_file.read_text()

        # natbib should be loaded with authoryear option
        assert r"\usepackage[authoryear]{natbib}" in tex_content or \
               (r"\usepackage{natbib}" in tex_content and \
                r"\setcitestyle{authoryear}" in tex_content), \
               "natbib should be configured for author-year citations"
```

## 5. BBL Transformer Tests (`test_bbl_transformer.py`)

**Purpose**: Validate BBL transformer creates hyperlinked author names for arXiv

### 5.1 BBL Transformation Flag
```python
def test_bbl_transformer_flag_enabled(self):
    """Test BBL transformer can be enabled via flag."""
    markdown_content = "# Test\n[Author (2020)](https://arxiv.org/abs/2020.12345)"

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.md"
        input_file.write_text(markdown_content)

        # Convert WITH BBL transformer
        converter = MarkdownToLatexConverter(
            output_dir=tmpdir,
            use_bbl_transformer=True
        )
        converter.convert(markdown_file=input_file)

        # Check .bbl file has hyperlinked authors
        bbl_file = Path(tmpdir) / "test.bbl"
        bbl_content = bbl_file.read_text()

        # Should have \href commands for author names
        assert r"\href{" in bbl_content, \
               "BBL should contain hyperlinked authors"
```

### 5.2 BBL vs BibTeX Mode
```python
def test_bbl_vs_bibtex_mode(self):
    """Test conversion supports both .bbl and .bib modes."""
    markdown_content = "# Test\n[Author (2020)](https://doi.org/10.1234/5678)"

    # Test .bib mode (default)
    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.md"
        input_file.write_text(markdown_content)

        converter = MarkdownToLatexConverter(
            output_dir=tmpdir,
            use_bbl_transformer=False  # Use .bib
        )
        converter.convert(markdown_file=input_file)

        tex_file = Path(tmpdir) / "test.tex"
        tex_content = tex_file.read_text()

        # Should use \bibliography{references}
        assert r"\bibliography{references}" in tex_content, \
               "Should use \\bibliography command for .bib mode"

    # Test .bbl mode
    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.md"
        input_file.write_text(markdown_content)

        converter = MarkdownToLatexConverter(
            output_dir=tmpdir,
            use_bbl_transformer=True  # Use .bbl
        )
        converter.convert(markdown_file=input_file)

        tex_file = Path(tmpdir) / "test.tex"
        tex_content = tex_file.read_text()

        # Should directly include .bbl content
        assert r"\begin{thebibliography}" in tex_content or \
               Path(tmpdir / "test.bbl").exists(), \
               "Should generate .bbl file for direct inclusion"
```

### 5.3 Hyperlinked Author Names Format
```python
def test_hyperlinked_author_names_format(self):
    """Test BBL transformer creates correct hyperlink format."""
    markdown_content = """
# Test
[Mildenhall et al. (2020)](https://arxiv.org/abs/2003.08934)
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.md"
        input_file.write_text(markdown_content)

        converter = MarkdownToLatexConverter(
            output_dir=tmpdir,
            use_bbl_transformer=True
        )
        converter.convert(markdown_file=input_file)

        bbl_file = Path(tmpdir) / "test.bbl"
        bbl_content = bbl_file.read_text()

        # Format should be: \href{https://arxiv.org/abs/2003.08934}{Mildenhall}
        # Each author name should be individually hyperlinked
        assert r"\href{https://arxiv.org/abs/2003.08934}{" in bbl_content, \
               "Author names should be hyperlinked to paper URL"
```

## 6. Regression Tests (`test_regression.py`)

**Purpose**: Detect regressions in conversion quality

### 6.1 Golden File Comparison
```python
def test_golden_pdf_comparison(self):
    """Test conversion matches known-good golden PDF."""
    # Use a fixed test file
    test_file = Path(__file__).parent / "fixtures" / "test-markdown" / "nerf-paper.md"
    golden_pdf = Path(__file__).parent / "fixtures" / "golden-pdfs" / "nerf-paper.pdf"

    with tempfile.TemporaryDirectory() as tmpdir:
        converter = MarkdownToLatexConverter(output_dir=tmpdir)
        converter.convert(markdown_file=test_file)

        generated_pdf = Path(tmpdir) / "nerf-paper.pdf"

        # Compare PDF text content
        golden_text = self._extract_pdf_text(golden_pdf)
        generated_text = self._extract_pdf_text(generated_pdf)

        # Should have same citations
        golden_citations = re.findall(r'\([^)]+\d{4}[^)]*\)', golden_text)
        generated_citations = re.findall(r'\([^)]+\d{4}[^)]*\)', generated_text)

        assert golden_citations == generated_citations, \
               "Citations differ from golden PDF"
```

### 6.2 No Regression in Citation Count
```python
def test_citation_count_matches_markdown(self):
    """Test all markdown citations appear in PDF."""
    markdown_content = """
# Test
Citation 1: [Author1 (2020)](https://doi.org/10.1111/1111)
Citation 2: [Author2 (2021)](https://doi.org/10.2222/2222)
Citation 3: [Author3 (2022)](https://doi.org/10.3333/3333)
"""

    # Count citations in markdown
    markdown_citation_count = markdown_content.count("https://doi.org/")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.md"
        input_file.write_text(markdown_content)

        converter = MarkdownToLatexConverter(output_dir=tmpdir)
        converter.convert(markdown_file=input_file)

        # Count citations in PDF
        pdf_text = self._extract_pdf_text(Path(tmpdir) / "test.pdf")
        pdf_citation_count = len(re.findall(r'\([^)]+\d{4}[^)]*\)', pdf_text))

        assert pdf_citation_count >= markdown_citation_count, \
               f"PDF has fewer citations ({pdf_citation_count}) than markdown ({markdown_citation_count})"
```

## 7. Error Handling Tests (`test_error_handling.py`)

### 7.1 Graceful Failure on Invalid DOI
```python
def test_invalid_doi_graceful_fallback(self):
    """Test conversion continues with invalid DOI."""
    markdown_content = """
# Test
Valid: [Author1 (2020)](https://doi.org/10.1145/3503250)
Invalid: [Author2 (2021)](https://doi.org/INVALID_DOI)
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.md"
        input_file.write_text(markdown_content)

        converter = MarkdownToLatexConverter(output_dir=tmpdir)

        # Should NOT raise exception
        converter.convert(markdown_file=input_file)

        # PDF should still be generated
        pdf_file = Path(tmpdir) / "test.pdf"
        assert pdf_file.exists(), "PDF should be generated even with invalid DOI"

        # Should have at least the valid citation
        pdf_text = self._extract_pdf_text(pdf_file)
        assert "(Author1" in pdf_text or "2020" in pdf_text
```

### 7.2 Network Failure Handling
```python
@patch("requests.get")
def test_network_failure_graceful_degradation(self, mock_get):
    """Test conversion works even if API calls fail."""
    mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

    markdown_content = "# Test\n[Author (2020)](https://doi.org/10.1234/5678)"

    with tempfile.TemporaryDirectory() as tmpdir:
        input_file = Path(tmpdir) / "test.md"
        input_file.write_text(markdown_content)

        converter = MarkdownToLatexConverter(output_dir=tmpdir)

        # Should complete without crashing
        converter.convert(markdown_file=input_file)

        # PDF should exist (even if citations not fully resolved)
        assert Path(tmpdir / "test.pdf").exists()
```

## GitHub Actions Configuration

### Required Secrets

Add these to GitHub repository settings → Secrets and variables → Actions:

```yaml
# .github/workflows/comprehensive-tests.yml
name: Comprehensive E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y \
            texlive-xetex \
            texlive-latex-extra \
            texlive-fonts-recommended \
            pandoc

      - name: Install Python dependencies
        run: |
          pip install uv
          uv sync

      - name: Set up Zotero credentials
        env:
          ZOTERO_API_KEY: ${{ secrets.ZOTERO_API_KEY }}
          ZOTERO_LIBRARY_ID: ${{ secrets.ZOTERO_LIBRARY_ID }}
        run: |
          # Create .env file if Zotero secrets are available
          if [ -n "$ZOTERO_API_KEY" ]; then
            echo "ZOTERO_API_KEY=$ZOTERO_API_KEY" >> .env
            echo "ZOTERO_LIBRARY_ID=$ZOTERO_LIBRARY_ID" >> .env
            echo "ZOTERO_LIBRARY_TYPE=user" >> .env
            echo "ZOTERO_COLLECTION=dpp-fashion" >> .env
          fi

      - name: Run unit tests
        run: |
          uv run pytest tests/ -v --ignore=tests/integration/

      - name: Run E2E tests (with Zotero)
        if: env.ZOTERO_API_KEY != ''
        run: |
          uv run pytest tests/integration/test_e2e_conversion.py -v

      - name: Run E2E tests (without Zotero - fallback mode)
        if: env.ZOTERO_API_KEY == ''
        run: |
          uv run pytest tests/integration/test_e2e_conversion.py -v -m "not requires_zotero"

      - name: Run PDF validation tests
        run: |
          uv run pytest tests/integration/test_pdf_validation.py -v

      - name: Run hyperlink styling tests
        run: |
          uv run pytest tests/integration/test_hyperlink_styling.py -v

      - name: Run template validation tests
        run: |
          uv run pytest tests/integration/test_template_validation.py -v

      - name: Run BBL transformer tests
        run: |
          uv run pytest tests/integration/test_bbl_transformer.py -v

      - name: Upload test artifacts
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: test-failures
          path: |
            /tmp/test-output-*/
            *.log
            *.pdf
```

### Required GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add:

1. **`ZOTERO_API_KEY`**
   - Value: Your Zotero API key from https://www.zotero.org/settings/keys
   - Type: Repository secret
   - Required for: Tests that use Zotero API

2. **`ZOTERO_LIBRARY_ID`**
   - Value: Your Zotero user ID (numeric)
   - Type: Repository secret
   - Required for: Tests that use Zotero API

### Fallback Strategy

If Zotero secrets are not available:
- Tests will skip Zotero-specific validations
- Will use mock data for citation fetching
- Mark tests with `@pytest.mark.requires_zotero` to skip without secrets

```python
# In tests
import pytest

requires_zotero = pytest.mark.skipif(
    not os.getenv("ZOTERO_API_KEY"),
    reason="Zotero API credentials not available"
)

@requires_zotero
def test_zotero_integration(self):
    """Test that requires Zotero API."""
    pass
```

## Test Fixtures Structure

### Golden PDFs
```
tests/fixtures/golden-pdfs/
├── simple-citation.pdf          # Single citation
├── multiple-citations.pdf       # 10+ citations
├── nerf-paper.pdf              # Real paper (NeRF)
└── mixed-sources.pdf           # DOI + arXiv + URLs
```

### Test Markdown Files
```
tests/fixtures/test-markdown/
├── simple-citation.md
├── multiple-citations.md
├── nerf-paper.md
├── mixed-sources.md
├── edge-cases.md               # Et al., special chars, etc.
└── hyperlinks.md               # Regular URLs + citations
```

### Expected Outputs
```
tests/fixtures/expected-output/
├── simple-citation/
│   ├── test.tex                # Expected LaTeX
│   ├── references.bib          # Expected BibTeX
│   └── expected-citations.json # Expected citation list
└── ...
```

## Implementation Priority

### Phase 1: Core E2E Tests (Week 1)
1. ✅ `test_e2e_conversion.py` - Basic pipeline validation
2. ✅ `test_pdf_validation.py` - Citation resolution checks
3. ✅ GitHub Actions setup with Zotero secrets

### Phase 2: Styling & Templates (Week 2)
4. ✅ `test_hyperlink_styling.py` - Color and link tests
5. ✅ `test_template_validation.py` - Preamble verification
6. ✅ Create golden PDF fixtures

### Phase 3: Advanced Features (Week 3)
7. ✅ `test_bbl_transformer.py` - BBL transformation validation
8. ✅ `test_regression.py` - Regression detection
9. ✅ `test_error_handling.py` - Graceful failure tests

## Success Metrics

### Test Coverage Goals
- **Line coverage**: ≥90% for converter modules
- **E2E coverage**: 100% of user workflows
- **Regression detection**: Catches PDF quality degradation

### CI/CD Requirements
- **All tests must pass** before merge
- **E2E tests run on every PR**
- **Golden PDF comparison** on main branch changes
- **Artifacts uploaded** for failed tests

## Test Execution Strategy

### Local Development
```bash
# Run all tests
uv run pytest tests/ -v

# Run only E2E tests
uv run pytest tests/integration/ -v

# Run specific test file
uv run pytest tests/integration/test_e2e_conversion.py -v

# Run with coverage
uv run pytest tests/ --cov=src/converters/md_to_latex --cov-report=html
```

### CI/CD
- **On every commit**: Unit tests + fast E2E tests
- **On PR**: Full E2E suite + golden PDF comparison
- **On main branch**: Full suite + update golden PDFs if intentional change

## Maintenance Plan

### Updating Golden PDFs
When intentionally changing output format:
1. Review changes carefully
2. Generate new golden PDFs: `python scripts/update_golden_pdfs.py`
3. Commit with message explaining why output changed
4. Update this document if test expectations change

### Adding New Test Cases
When adding new features:
1. Add test markdown to `fixtures/test-markdown/`
2. Add expected output to `fixtures/expected-output/`
3. Add test case to appropriate `test_*.py` file
4. Update golden PDFs if needed

## Code Snippets for Context

### Helper Functions (Add to `tests/integration/conftest.py`)

```python
"""Shared fixtures and helpers for integration tests."""
import PyPDF2
import tempfile
from pathlib import Path
import pytest

@pytest.fixture
def temp_output_dir():
    """Provide a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

def extract_pdf_text(pdf_path: Path) -> str:
    """Extract text from PDF for validation.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Extracted text content
    """
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text

def count_citations_in_text(text: str) -> int:
    """Count author-year citations in text.

    Args:
        text: Text content to search

    Returns:
        Number of citations found
    """
    import re
    # Match patterns like (Author, 2020) or (Author et al., 2020)
    pattern = r'\([^)]+\d{4}[^)]*\)'
    return len(re.findall(pattern, text))

def verify_pdf_valid(pdf_path: Path) -> bool:
    """Verify file is a valid PDF.

    Args:
        pdf_path: Path to PDF file

    Returns:
        True if valid PDF, False otherwise
    """
    if not pdf_path.exists():
        return False

    with open(pdf_path, 'rb') as f:
        header = f.read(4)
        return header == b'%PDF'
```

### Example Test Implementation

```python
"""tests/integration/test_e2e_conversion.py"""
import pytest
import tempfile
from pathlib import Path
from src.converters.md_to_latex import MarkdownToLatexConverter
from tests.integration.conftest import extract_pdf_text, verify_pdf_valid

class TestEndToEndConversion:
    """End-to-end conversion tests."""

    def test_simple_conversion_success(self):
        """Test simple markdown converts to PDF with citations."""
        markdown_content = """
# Test Document

Here's a citation: [Mildenhall et al. (2022)](https://doi.org/10.1145/3503250)

And another: [Zhang et al. (2020)](https://arxiv.org/abs/2003.08934)
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            input_file = tmpdir / "test.md"
            input_file.write_text(markdown_content)

            # Convert
            converter = MarkdownToLatexConverter(output_dir=tmpdir)
            converter.convert(markdown_file=input_file)

            # Verify outputs exist
            pdf_file = tmpdir / "test.pdf"
            tex_file = tmpdir / "test.tex"
            bib_file = tmpdir / "references.bib"

            assert pdf_file.exists(), "PDF not generated"
            assert tex_file.exists(), "LaTeX not generated"
            assert bib_file.exists(), "BibTeX not generated"

            # Verify PDF is valid
            assert verify_pdf_valid(pdf_file), "Invalid PDF file"

            # Verify citations resolved
            pdf_text = extract_pdf_text(pdf_file)
            assert "(?)" not in pdf_text, "Unresolved citations found"
            assert "(Mildenhall" in pdf_text or "2022" in pdf_text, \
                   "Citation not found in PDF"

    def test_all_citations_resolved(self):
        """Test PDF has no (?) markers for citations."""
        markdown_content = """
# Test
[Author1 (2020)](https://doi.org/10.1145/3503250)
[Author2 (2021)](https://arxiv.org/abs/2003.08934)
"""

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            input_file = tmpdir / "test.md"
            input_file.write_text(markdown_content)

            converter = MarkdownToLatexConverter(output_dir=tmpdir)
            converter.convert(markdown_file=input_file)

            pdf_text = extract_pdf_text(tmpdir / "test.pdf")

            # Critical checks
            assert "(?)" not in pdf_text, "Found unresolved citation"
            assert "(Unknown)" not in pdf_text, "Found Unknown author"
            assert "(Anonymous)" not in pdf_text, "Found Anonymous author"
```

## Conclusion

This comprehensive test plan will:
1. ✅ Catch regressions before they reach production
2. ✅ Verify the actual product (MD→PDF) works, not just unit tests
3. ✅ Detect issues with citations, hyperlinks, templates, and styling
4. ✅ Run automatically on every PR via GitHub Actions
5. ✅ Provide clear failure messages for debugging

**Next Steps**:
1. Review and approve this plan
2. Implement Phase 1 tests (Core E2E)
3. Set up GitHub Actions with Zotero secrets
4. Create golden PDF fixtures
5. Implement remaining test phases
