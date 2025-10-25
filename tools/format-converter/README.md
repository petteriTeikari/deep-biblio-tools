# format-converter

> Part of the Deep Biblio Tools suite

Convert between various academic document formats with citation preservation.

## Features

- 📄 **Multi-format Support**: Markdown, LaTeX, BibTeX, Word, HTML
- 🔗 **Citation Preservation**: Maintains citation formatting across conversions
- 📚 **Bibliography Handling**: Smart bibliography format conversion
- 🎨 **Style Templates**: Academic journal templates included
- ⚡ **Batch Processing**: Convert entire directories
- 🔧 **Customizable**: Extensible conversion rules

## Installation

```bash
pip install format-converter
```

## Quick Start

### Convert Markdown to LaTeX
```bash
format-converter convert paper.md --to latex -o paper.tex
```

### Convert LaTeX to Word
```bash
format-converter convert paper.tex --to docx -o paper.docx
```

### Batch Convert Directory
```bash
format-converter batch papers/ --from md --to tex -o converted/
```

### Extract Bibliography
```bash
format-converter extract-bib paper.md -o references.bib
```

## Supported Formats

| From | To | Citation Support | Notes |
|------|----|-----------------|-------|
| Markdown | LaTeX | ✓ | Full citation conversion |
| Markdown | HTML | ✓ | Academic HTML output |
| Markdown | DOCX | ✓ | Via pandoc |
| LaTeX | Markdown | ✓ | Preserves citations |
| LaTeX | DOCX | ✓ | With bibliography |
| BibTeX | Various | ✓ | Bibliography conversion |

## Configuration

Create `.format-converter.yml`:
```yaml
conversion:
  preserve_citations: true
  include_bibliography: true
  citation_style: author-year

latex:
  document_class: article
  packages:
    - hyperref
    - natbib

templates:
  ieee: templates/ieee.tex
  acm: templates/acm.tex
```

## Usage Examples

### Custom LaTeX Template
```bash
format-converter convert paper.md --to latex --template ieee
```

### Citation Style Conversion
```bash
format-converter convert paper.md --to latex --citation-style numeric
```

## License

MIT - See LICENSE in root repository
