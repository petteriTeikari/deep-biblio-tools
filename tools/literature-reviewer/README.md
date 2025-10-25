# literature-reviewer

> Part of the Deep Biblio Tools suite

Generate comprehensive literature reviews with smart summarization capabilities.

## Features

- 📚 **Smart Summarization**: 25% comprehensive summaries preserving key insights
- 🔗 **Citation Preservation**: Maintains author-year citations with hyperlinks
- 🎯 **Theme-based Reviews**: Contextual literature reviews for research themes
- 📊 **Reference Deduplication**: Intelligent merging of duplicate references
- 🤖 **AI-powered Analysis**: Uses advanced models for quality summaries
- 📝 **Multiple Output Formats**: Markdown, LaTeX, and structured JSON

## Installation

```bash
pip install literature-reviewer
```

## Quick Start

### Create Summary of Single Paper
```bash
literature-reviewer summarize paper.md -o summary.md
```

### Generate Literature Review from Multiple Papers
```bash
literature-reviewer review papers/ -o literature-review.md --theme "Building Information Modeling"
```

### Batch Process Papers
```bash
literature-reviewer batch-summarize papers/ -o summaries/ --compression 0.25
```

## Configuration

Create `.literature-reviewer.yml`:
```yaml
summarization:
  compression_ratio: 0.25
  preserve_citations: true
  preserve_references: true

review:
  include_methodology: true
  include_findings: true
  deduplicate_references: true

ai:
  model: claude-3.5-sonnet
  temperature: 0.3
  max_retries: 3
```

## Usage Examples

### Custom Theme Context
```bash
literature-reviewer review papers/ \
  --theme "sustainable construction" \
  --context "Focus on environmental impact and green building practices"
```

### Different Compression Levels
```bash
# 10% ultra-concise summary
literature-reviewer summarize paper.md --compression 0.1

# 50% detailed summary
literature-reviewer summarize paper.md --compression 0.5
```

## License

MIT - See LICENSE in root repository
