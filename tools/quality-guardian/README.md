# quality-guardian

> Part of the Deep Biblio Tools suite

Ensure high-quality academic writing with automated checks and improvements.

## Features

- ✍️ **Writing Quality**: Grammar, style, and clarity checks
- 📏 **Academic Standards**: Ensure proper academic writing conventions
- 🔍 **Plagiarism Detection**: Check for unintentional similarities
- 📊 **Readability Analysis**: Flesch scores and complexity metrics
- 🎯 **Consistency Checks**: Terminology and formatting consistency
- 💡 **Improvement Suggestions**: AI-powered writing enhancements

## Installation

```bash
pip install quality-guardian
```

## Quick Start

### Check Document Quality
```bash
quality-guardian check paper.md
```

### Full Analysis with Report
```bash
quality-guardian analyze paper.md -o quality-report.html
```

### Fix Common Issues
```bash
quality-guardian fix paper.md --output paper-fixed.md
```

### Batch Processing
```bash
quality-guardian batch-check papers/ -o reports/
```

## Quality Checks

### 1. Grammar and Spelling
- Spelling errors
- Grammar mistakes
- Punctuation issues
- Subject-verb agreement

### 2. Academic Style
- Passive vs. active voice balance
- Formal language usage
- Avoiding contractions
- Proper citation format

### 3. Clarity and Readability
- Sentence length variation
- Paragraph structure
- Transition words
- Jargon usage

### 4. Consistency
- Terminology consistency
- Citation style consistency
- Formatting consistency
- Abbreviation usage

### 5. Structure
- Section organization
- Logical flow
- Abstract completeness
- Conclusion effectiveness

## Configuration

Create `.quality-guardian.yml`:
```yaml
checks:
  grammar: true
  style: true
  plagiarism: false
  readability: true
  consistency: true

standards:
  min_readability_score: 30
  max_sentence_length: 40
  passive_voice_percentage: 20

style_guide: apa  # or ieee, chicago, mla

reporting:
  format: html
  include_suggestions: true
  highlight_issues: true
```

## Usage Examples

### Custom Style Guide
```bash
quality-guardian check paper.md --style ieee
```

### Readability Focus
```bash
quality-guardian analyze paper.md --focus readability
```

### Generate Improvement Suggestions
```bash
quality-guardian suggest paper.md --ai-powered
```

## Integration

### Pre-commit Hook
```yaml
- repo: local
  hooks:
    - id: quality-guardian
      name: Check document quality
      entry: quality-guardian check
      language: system
      files: \.(md|tex|txt)$
```

### CI/CD Pipeline
```yaml
quality-check:
  script:
    - quality-guardian check manuscripts/*.md
    - quality-guardian report --format json > quality.json
```

## License

MIT - See LICENSE in root repository
