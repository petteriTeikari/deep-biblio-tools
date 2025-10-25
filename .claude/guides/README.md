# Implementation Guides

This directory contains comprehensive implementation guides and examples that serve as institutional knowledge for the deep-biblio-tools project.

## Available Guides

### arxiv-converter-guide.md
A comprehensive implementation example (1600+ lines) showing how to build a markdown to LaTeX converter with:
- Multi-source citation fetching (Zotero, CrossRef, arXiv, etc.)
- 5 different concept box styles for technical content
- Caching system for citations
- Progress tracking with colored output
- Automated BibTeX generation
- arXiv-ready LaTeX output

This guide demonstrates best practices for:
- Modular architecture design
- Progressive enhancement approach
- Error handling and fallback strategies
- User-friendly CLI design
- Comprehensive testing strategies

## Usage

These guides should be consulted when:
1. Implementing similar features (use as a pattern reference)
2. Understanding the project's coding style and conventions
3. Learning about complex implementations already done in the project
4. Planning new features that might interact with existing systems

## Contributing

When adding new guides:
- Use lowercase-with-hyphens.md naming convention
- Include a clear purpose statement at the top
- Provide concrete implementation examples
- Document design decisions and trade-offs
- Update this README with a description of the new guide
