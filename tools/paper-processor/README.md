# paper-processor

> Part of the Deep Biblio Tools suite

Extract and process content from academic papers in various formats.

## Features

- 📄 **Multi-format Support**: HTML, PDF, LaTeX, XML (JATS/MDPI)
- 🔍 **Smart Extraction**: Papers, citations, references
- 📊 **Metadata Parsing**: Author, title, abstract, DOI
- 🧹 **Clean Output**: Structured markdown with preserved formatting
- 🔗 **Citation Preservation**: Maintains links and references
- 💾 **Batch Processing**: Handle entire directories efficiently
- 🚀 **Advanced PDF Processing**: Marker & PyMuPDF4LLM for high-accuracy extraction
- 🎯 **All Formats Support**: Process mixed file types in one command

## Installation

```bash
# Basic installation
pip install paper-processor

# With summarization support
pip install paper-processor[summarization]

# With advanced PDF processing
pip install paper-processor[advanced-pdf]

# With all features
pip install paper-processor[all]
```

## Quick Start

### Process a Single Paper
```bash
paper-processor extract paper.html -o paper.md
```

### Process Directory of Papers
```bash
paper-processor batch-extract papers/ -o extracted/
```

### Extract Specific Sections
```bash
paper-processor extract paper.pdf --sections abstract,introduction,conclusion
```

### Convert Format
```bash
paper-processor convert paper.html --to markdown
```

### Create Summary
```bash
paper-processor summarize paper.html -o summary.md
```

### Summarize Entire Folder
```bash
# Process all HTML files
paper-processor summarize-folder papers/ -o summaries/

# Process all supported formats (HTML, PDF, LaTeX, XML)
paper-processor summarize-folder papers/ -o summaries/ --pattern all_formats

# Process specific patterns
paper-processor summarize-folder papers/ -o summaries/ --pattern "*.pdf"
```

## Configuration

Create `.paper-processor.yml`:
```yaml
extraction:
  formats:
    - html
    - pdf
    - latex
  sections:
    - abstract
    - introduction
    - methodology
    - results
    - conclusion
    - references

output:
  format: markdown
  preserve_citations: true
  clean_text: true

processing:
  parallel: true
  max_workers: 4

pdf:
  use_advanced: true      # Enable advanced PDF processing
  use_marker: true        # Use Marker for highest accuracy (slower)
  use_pymupdf4llm: true  # Use PyMuPDF4LLM for speed (fallback)

summarization:
  compression_ratio: 0.25
  preserve_citations: true
  ai:
    model: "claude-3.5-sonnet"
    temperature: 0.3
```

## License

MIT - See LICENSE in root repository
