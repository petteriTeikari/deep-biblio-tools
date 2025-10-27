# Golden Dataset for MD→LaTeX→PDF Conversion Testing

This golden dataset provides deterministic test fixtures for verifying the MD→LaTeX→PDF conversion pipeline. It ensures that future changes don't break the conversion quality of working papers.

## Dataset Structure

```
tests/fixtures/golden/
├── manuscripts/           # 4 verified markdown papers
│   ├── fashion_4DGS.md
│   ├── fashion_3D_CAD.md
│   ├── fashion_LCA.md
│   └── mcp_review.md
├── bibliography/          # Frozen Zotero collection snapshot
│   └── dpp-fashion-snapshot.bib  (25.4 KB, 12 entries)
└── expected_outputs/      # Verified outputs (once generated)
    ├── fashion_4DGS.tex
    ├── fashion_4DGS.pdf
    ├── fashion_4DGS.bbl
    ├── fashion_4DGS_refs.bib    # Subset of references cited
    └── ... (same for other 3 papers)
```

## Papers Included

1. **fashion_4DGS.md** - 4D Gaussian Splatting for Fashion (47 KB)
2. **fashion_3D_CAD.md** - 3D CAD Review for Fashion (70 KB)
3. **fashion_LCA.md** - Life Cycle Assessment for Fashion (52 KB)
4. **mcp_review.md** - Model Context Protocol Review (215 KB)

All papers have been verified to convert with:
- ✅ ZERO (?) missing citations
- ✅ ZERO Unknown/Anonymous authors
- ✅ Valid BibTeX entries
- ✅ Clean PDF output

## Bibliography Snapshot

The `dpp-fashion-snapshot.bib` file is a frozen export of the Zotero "dpp-fashion" collection taken on 2025-10-27. This ensures:

- **Deterministic testing**: Tests don't depend on live Zotero API access
- **Reproducibility**: Same input always produces same output
- **Version control**: Bibliography changes are explicit commits

To update the snapshot:
```bash
uv run python scripts/export_zotero_snapshot.py
```

## Expected Outputs

**Status**: Not yet populated (will be added after manual verification)

Once the 4 papers are confirmed to have zero missing citations, the expected outputs will include:

- `.tex` files - Generated LaTeX source
- `.pdf` files - Final compiled PDFs
- `.bbl` files - BibTeX processed bibliography
- `_refs.bib` files - Subset of `dpp-fashion-snapshot.bib` containing only cited entries

These serve as regression test baselines to detect:
- Citation resolution degradation
- LaTeX conversion quality changes
- PDF generation issues

## Usage in Tests

The regression test suite (`tests/e2e/test_regression_4_papers.py`) uses these fixtures:

```python
# Current: Tests against live manuscripts + Zotero API
PAPERS = [
    "/Users/petteri/Dropbox/.../fashion_4DGS/4dgs-fashion-comprehensive-v2.md",
    ...
]

# Future: Tests against golden dataset (no external dependencies)
PAPERS = [
    "tests/fixtures/golden/manuscripts/fashion_4DGS.md",
    ...
]
```

## Git LFS

If files become too large (>50 MB), consider using Git LFS:

```bash
git lfs track "tests/fixtures/golden/expected_outputs/*.pdf"
git lfs track "tests/fixtures/golden/bibliography/*.bib"
```

Current sizes are small (manuscripts: 384 KB total, bibliography: 25 KB), so LFS is not yet needed.

## Maintenance

- **Add new papers**: Copy to `manuscripts/`, verify conversion, add to test suite
- **Update bibliography**: Re-export snapshot after Zotero changes
- **Regenerate outputs**: Delete `expected_outputs/*`, re-run tests with `--update-golden` flag

## Testing Quality Criteria

All papers in this dataset must meet these criteria:

1. Convert to PDF without LaTeX errors
2. Have ZERO (?) citations in PDF
3. Have ZERO (Unknown) or (Anonymous) authors in references
4. Have valid BibTeX with proper citation keys
5. Match expected output baselines (once established)

See `.claude/CLAUDE.md` for full conversion success criteria.
