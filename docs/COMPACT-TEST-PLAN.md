# Compact Test Plan: MD→LaTeX→PDF Pipeline

**Problem**: Unit tests pass but PDF output verification is manual. Need automated E2E tests.

**Goal**: Detect pipeline breaks automatically (citations, hyperlinks, templates, BBL transformer).

## Critical Test Categories

### 1. E2E Conversion (`test_e2e_conversion.py`)

```python
def test_citations_resolved_in_pdf(self):
    """ZERO TOLERANCE: No (?), (Unknown), or (Anonymous) in PDF."""
    md = '# Test\n[Smith (2020)](https://doi.org/10.1234/example)'

    pdf_text = self._convert_and_extract_pdf(md)

    assert "(?)" not in pdf_text
    assert "(Unknown)" not in pdf_text
    assert "(Anonymous)" not in pdf_text
    assert "Smith" in pdf_text  # Author name present
```

### 2. PDF Validation (`test_pdf_validation.py`)

```python
def test_bibliography_present(self):
    """Verify references section exists with full entries."""
    pdf_text = self._convert_and_extract_pdf(SAMPLE_MD_WITH_CITATIONS)

    # Check bibliography header
    assert "References" in pdf_text or "REFERENCES" in pdf_text

    # Check for BibTeX fields
    assert any(year in pdf_text for year in ["2020", "2021", "2022"])
```

### 3. Hyperlink Styling (`test_hyperlink_styling.py`)

```python
def test_hyperref_navy_blue_links(self):
    """Verify hyperlinks are NavyBlue, not default red."""
    tex_content = self._convert_to_latex(SAMPLE_MD)

    assert "\\usepackage{hyperref}" in tex_content
    assert "colorlinks=true" in tex_content
    assert "linkcolor=NavyBlue" in tex_content
    assert "citecolor=NavyBlue" in tex_content
    assert "urlcolor=NavyBlue" in tex_content
```

### 4. Template Validation (`test_template_validation.py`)

```python
def test_correct_preamble(self):
    """Verify LaTeX preamble has required packages."""
    tex = self._convert_to_latex(SAMPLE_MD)

    required_packages = [
        "\\usepackage[utf8]{inputenc}",
        "\\usepackage[authoryear,round]{natbib}",
        "\\usepackage{hyperref}",
        "\\bibliographystyle{spbasic_pt}",
    ]

    for pkg in required_packages:
        assert pkg in tex, f"Missing: {pkg}"
```

### 5. BBL Transformer (`test_bbl_transformer.py`)

```python
def test_bbl_hyperlinked_authors(self):
    """Verify BBL has \\href{} around author names for arXiv."""
    bbl_content = self._get_bbl_content()

    assert "\\href{" in bbl_content
    assert "}{\\nolinkurl{" in bbl_content
    # Should wrap author names with hyperlinks to DOI/arXiv
```

### 6. Regression Tests (`test_regression.py`)

```python
def test_golden_pdf_comparison(self):
    """Compare output against known-good reference PDF."""
    current_pdf_text = self._convert_and_extract_pdf(GOLDEN_INPUT)
    golden_pdf_text = self._extract_pdf_text(GOLDEN_PDF_PATH)

    # Allow minor differences (page numbers, dates)
    similarity = self._text_similarity(current_pdf_text, golden_pdf_text)
    assert similarity > 0.95, f"Output diverged: {similarity:.2%}"
```

### 7. Error Handling (`test_error_handling.py`)

```python
def test_missing_doi_fallback(self):
    """Verify graceful degradation when DOI API fails."""
    md = '[Smith (2020)](https://doi.org/10.9999/nonexistent)'

    with patch('requests.get', side_effect=RequestException):
        pdf_text = self._convert_and_extract_pdf(md)

        # Should still compile, maybe with placeholder
        assert "Smith" in pdf_text
        # Should NOT crash the entire pipeline
```

## Helper Pattern

```python
class TestBase:
    def _convert_and_extract_pdf(self, markdown_content: str) -> str:
        """Convert markdown to PDF and extract text."""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "test.md"
            input_file.write_text(markdown_content)

            converter = MarkdownToLatexConverter(output_dir=tmpdir)
            converter.convert(markdown_file=input_file)

            pdf_file = Path(tmpdir) / "test.pdf"
            return self._extract_pdf_text(pdf_file)

    def _extract_pdf_text(self, pdf_path: Path) -> str:
        """Extract text from PDF."""
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            return '\n'.join(page.extract_text() for page in reader.pages)
```

## GitHub Actions Configuration

```yaml
name: E2E Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install LaTeX
        run: sudo apt-get install -y texlive-xetex pandoc
      - name: Install Python deps
        run: |
          pip install uv
          uv sync
      - name: Run E2E tests
        env:
          ZOTERO_API_KEY: ${{ secrets.ZOTERO_API_KEY }}
          ZOTERO_LIBRARY_ID: ${{ secrets.ZOTERO_LIBRARY_ID }}
        run: uv run pytest tests/test_e2e_*.py -v
```

**Required GitHub Secrets**:
- `ZOTERO_API_KEY`: From https://www.zotero.org/settings/keys (read + write access)
- `ZOTERO_LIBRARY_ID`: Numeric user ID from Zotero account

## Implementation Priority

**Phase 1 (Week 1)**: Core E2E tests
- `test_citations_resolved_in_pdf()`
- `test_bibliography_present()`
- `test_correct_preamble()`

**Phase 2 (Week 2)**: Styling & BBL
- `test_hyperref_navy_blue_links()`
- `test_bbl_hyperlinked_authors()`

**Phase 3 (Week 3)**: Regression & Error Handling
- `test_golden_pdf_comparison()`
- `test_missing_doi_fallback()`

## Success Criteria

- ✅ All E2E tests pass locally
- ✅ CI/CD runs E2E tests on every commit
- ✅ ZERO manual PDF verification needed
- ✅ Pipeline breaks detected automatically
- ✅ Golden PDFs maintained for regression detection

## Key Takeaways

1. **PDF text extraction is mandatory** - Only way to verify citations resolved
2. **Check for `(?)`** - Primary indicator of broken pipeline
3. **Test end-to-end** - Unit tests ≠ working product
4. **Golden PDFs** - Reference outputs prevent regressions
5. **CI/CD integration** - Automated checks on every commit
