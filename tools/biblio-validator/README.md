# biblio-validator

> Part of the Deep Biblio Tools suite

Professional citation validation tool that checks academic citations against publisher databases.

## Features

- 🔍 **Multi-source Validation**: CrossRef, PubMed, arXiv, and more
- 📚 **Bibliography Quality Checking**: Find incomplete or incorrect entries
- 🔗 **Citation-Bibliography Matching**: Ensure all citations have references
- 💾 **Smart Caching**: Avoid repeated API calls
- 📊 **Detailed Reports**: Get actionable insights about citation issues
- 🛠️ **Fix Suggestions**: Automatic correction proposals

## Installation

```bash
pip install biblio-validator
```

## Quick Start

### Validate Citations in a Document
```bash
biblio-validator check paper.md
```

### Validate a BibTeX File
```bash
biblio-validator check-bib references.bib
```

### Match Citations to Bibliography
```bash
biblio-validator match paper.md references.bib
```

### Generate Validation Report
```bash
biblio-validator report paper.md --output validation-report.md
```

## Configuration

Create `.biblio-validator.yml`:
```yaml
cache:
  enabled: true
  directory: ~/.cache/biblio-validator
  ttl: 604800  # 1 week

validation:
  sources:
    - crossref
    - pubmed
    - arxiv
  timeout: 30
  parallel: true

reporting:
  format: markdown
  include_suggestions: true
```

## License

MIT - See LICENSE in root repository
