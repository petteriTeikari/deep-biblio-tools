# arXiv LaTeX Template

This template produces professional academic papers suitable for arXiv preprint submission.

## Key Features

- **Two-column layout** with tight margins (0.75in)
- **Hyperlinked citations** with author names in BrickRed
- **natbib + BibTeX** (not BibLaTeX) for arXiv compatibility
- **spbasic_pt** bibliography style
- **Single-file submission** ready (embed .bbl)

## Files

- `preamble.tex` - Document preamble (packages, settings)
- `style_config.yaml` - Template configuration
- `README.md` - This file

## Usage

```python
from src.converters.md_to_latex.latex_style_applicator import LatexStyleApplicator

applicator = LatexStyleApplicator(template="arxiv")
latex_content = applicator.apply_template(content, metadata)
```

## Reference Paper

https://arxiv.org/pdf/2508.02765 (UAD Review Paper)

## Style Details

See `docs/LATEX-STYLE-ARXIV.md` for complete documentation.
