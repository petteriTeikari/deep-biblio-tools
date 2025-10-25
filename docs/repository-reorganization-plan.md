# Repository Reorganization Plan for Deep Biblio Tools

## Executive Summary

This plan outlines a comprehensive reorganization of the Deep Biblio Tools repository to create a professional, modular structure inspired by the Sibelius repository's organization. The reorganization will transform the current mixed structure into clearly defined subtools with proper documentation, testing, and deployment strategies.

## Current State Analysis

### Strengths
- Strong foundation of bibliography processing tools
- Comprehensive citation validation capabilities
- Well-developed article summarization features
- Good pre-commit hooks and quality checks

### Weaknesses
- Mixed organization (scripts scattered in root scripts/ directory)
- Unclear tool boundaries and purposes
- Limited documentation structure
- No clear deployment or packaging strategy
- Overlapping functionality between scripts

## Proposed Subtools Architecture

### 1. **biblio-validator** - Academic Citation Validator
Core functionality for validating citations against publisher databases.
- Citation extraction and validation
- Publisher API integrations (CrossRef, PubMed, etc.)
- Bibliography quality checking
- Citation-bibliography matching

### 2. **paper-processor** - Academic Paper Processing Suite
Tools for extracting and processing academic papers.
- HTML/PDF paper extraction
- ScienceDirect/Elsevier scraper
- ArXiv paper processor
- Metadata extraction

### 3. **literature-reviewer** - Literature Review Generator
Automated literature review and summarization tools.
- Article summarizer (25% compression)
- Theme-based literature review generator
- Citation graph builder
- Reference deduplication

### 4. **format-converter** - Academic Format Converter
Convert between various academic formats.
- Markdown to LaTeX converter
- LaTeX to LyX converter
- BibTeX format standardization
- Citation style converter

### 5. **biblio-assistant** - Interactive Bibliography Assistant
Web-based tools for manual bibliography management.
- Interactive proofreader
- Citation resolver interface
- Bibliography merger/deduplicator
- Manual citation correction tool

### 6. **quality-guardian** - Academic Quality Assurance
Quality checks and pre-commit hooks for academic writing.
- No-emoji enforcement
- No-regex policy checker
- Import structure validation
- Citation consistency checker

## Proposed Directory Structure

```
deep-biblio-tools/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   ├── release.yml
│   │   └── quality-checks.yml
│   └── ISSUE_TEMPLATE/
├── docs/
│   ├── 01-getting-started/
│   │   ├── README.md
│   │   ├── installation.md
│   │   └── quickstart.md
│   ├── 02-architecture/
│   │   ├── README.md
│   │   ├── system-design.md
│   │   └── tool-boundaries.md
│   ├── 03-tools/
│   │   ├── biblio-validator/
│   │   ├── paper-processor/
│   │   ├── literature-reviewer/
│   │   ├── format-converter/
│   │   ├── biblio-assistant/
│   │   └── quality-guardian/
│   ├── 04-api-reference/
│   ├── 05-development/
│   ├── 06-deployment/
│   └── images/
├── tools/
│   ├── biblio-validator/
│   │   ├── src/
│   │   ├── tests/
│   │   ├── README.md
│   │   └── pyproject.toml
│   ├── paper-processor/
│   │   ├── src/
│   │   ├── tests/
│   │   ├── README.md
│   │   └── pyproject.toml
│   ├── literature-reviewer/
│   │   ├── src/
│   │   ├── tests/
│   │   ├── README.md
│   │   └── pyproject.toml
│   ├── format-converter/
│   │   ├── src/
│   │   ├── tests/
│   │   ├── README.md
│   │   └── pyproject.toml
│   ├── biblio-assistant/
│   │   ├── src/
│   │   ├── tests/
│   │   ├── static/
│   │   ├── templates/
│   │   ├── README.md
│   │   └── pyproject.toml
│   └── quality-guardian/
│       ├── src/
│       ├── hooks/
│       ├── README.md
│       └── pyproject.toml
├── shared/
│   ├── core/
│   │   ├── models/
│   │   ├── utils/
│   │   └── constants/
│   ├── api-clients/
│   └── tests/
├── scripts/
│   ├── development/
│   ├── deployment/
│   └── migration/
├── examples/
│   ├── biblio-validator/
│   ├── paper-processor/
│   └── literature-reviewer/
├── tests/
│   ├── integration/
│   └── e2e/
├── .claude/
│   └── (keep existing Claude-specific files)
├── pyproject.toml         # Root project configuration
├── Makefile              # Common tasks
├── README.md             # Professional overview
├── CHANGELOG.md          # Version history
└── LICENSE
```

## Migration Strategy

### Phase 1: Documentation and Planning (Week 1)
1. Create comprehensive documentation structure
2. Document each tool's purpose and boundaries
3. Create migration scripts
4. Set up new directory structure

### Phase 2: Tool Extraction (Week 2-3)
1. Extract biblio-validator functionality
2. Extract paper-processor tools
3. Extract literature-reviewer components
4. Extract format-converter utilities
5. Extract biblio-assistant web interface
6. Consolidate quality-guardian hooks

### Phase 3: Testing and Integration (Week 4)
1. Create comprehensive test suites for each tool
2. Set up integration tests
3. Update CI/CD pipelines
4. Create example usage scenarios

### Phase 4: Polish and Release (Week 5)
1. Update all documentation
2. Create tool-specific READMEs
3. Set up release automation
4. Create migration guide for existing users

## Key Improvements

### 1. **Modular Architecture**
- Each tool can be installed and used independently
- Clear boundaries between functionality
- Easier to maintain and extend

### 2. **Professional Documentation**
- Numbered documentation structure for logical flow
- Tool-specific guides
- API reference documentation
- Architecture diagrams

### 3. **Improved Developer Experience**
- Clear contribution guidelines
- Tool-specific development environments
- Comprehensive testing strategies
- Better error messages and logging

### 4. **Enhanced Packaging**
- Each tool has its own pyproject.toml
- Can publish tools separately to PyPI
- Semantic versioning per tool
- Clear dependency management

### 5. **Better CLI Experience**
```bash
# Current (confusing)
python scripts/fix_bibliography.py
python scripts/process_biblio_theme_folder.sh

# New (clear and professional)
biblio-tools validate citations paper.md
biblio-tools process-papers /path/to/papers
biblio-tools generate-review --theme "BIM and ML"
biblio-tools convert md-to-latex paper.md
```

## Next Steps

1. **Review and approve this plan**
2. **Create feature branch**: `feature/repository-reorganization`
3. **Begin Phase 1**: Documentation structure
4. **Gradual migration**: Move functionality piece by piece
5. **Maintain backwards compatibility** during transition

## Success Metrics

- Clear separation of concerns between tools
- Improved documentation coverage (>80%)
- Reduced script duplication
- Professional CLI interface
- Published packages on PyPI
- Active community engagement

This reorganization will transform Deep Biblio Tools from a collection of scripts into a professional suite of academic tools, making it more accessible, maintainable, and valuable to the academic community.
