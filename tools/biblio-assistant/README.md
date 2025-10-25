# biblio-assistant

> Part of the Deep Biblio Tools suite

Web-based interface for interactive bibliography management and paper processing.

## Features

- 🌐 **Web Interface**: Modern, responsive UI for all tools
- 📝 **Interactive Editing**: Real-time citation and reference editing
- 🔍 **Smart Search**: Find papers, citations, and references quickly
- 📊 **Visualization**: Citation networks and reference graphs
- 🤖 **AI Assistant**: Chat interface for research help
- 🔄 **Live Preview**: See format conversions in real-time

## Installation

```bash
pip install biblio-assistant
```

## Quick Start

### Start the Web Server
```bash
biblio-assistant serve
# Opens browser at http://localhost:8000
```

### Command Line Interface
```bash
# Process paper through web UI
biblio-assistant process paper.pdf

# Validate bibliography
biblio-assistant validate refs.bib

# Start in specific mode
biblio-assistant serve --mode validator
```

## Features Overview

### 1. Paper Processing
- Upload papers (PDF, HTML, LaTeX)
- Extract content and metadata
- Generate summaries
- Export in multiple formats

### 2. Citation Validation
- Real-time citation checking
- Fix suggestions
- Batch validation
- Export reports

### 3. Literature Review Builder
- Drag-and-drop paper organization
- Theme-based grouping
- AI-powered synthesis
- Export to multiple formats

### 4. Format Converter
- Live preview
- Side-by-side comparison
- Template selection
- Batch conversion

### 5. Bibliography Manager
- Import/export BibTeX
- Duplicate detection
- Metadata enrichment
- Citation style preview

## Configuration

Create `.biblio-assistant.yml`:
```yaml
server:
  host: 0.0.0.0
  port: 8000
  debug: false

ui:
  theme: light
  language: en

features:
  enable_ai: true
  enable_collaboration: false

storage:
  type: local
  path: ~/.biblio-assistant/data
```

## API Endpoints

The web interface also provides REST API:

```bash
# Process paper
curl -X POST http://localhost:8000/api/process \
  -F "file=@paper.pdf" \
  -F "output_format=markdown"

# Validate citations
curl -X POST http://localhost:8000/api/validate \
  -F "file=@document.md"
```

## License

MIT - See LICENSE in root repository
