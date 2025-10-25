# Architecture Documentation

This directory contains technical architecture documentation for Deep Biblio Tools, including system design, implementation details, and technical specifications.

## 📐 Core Architecture Documents

- **[Deterministic Citation System](deterministic-citation-system.md)** - Core design principles for deterministic bibliography processing
- **[Module Structure Design](module-structure-design.md)** - Organization and structure of the codebase modules
- **[BibTeX Key Formats](bibtex-key-formats.md)** - Standards and conventions for BibTeX citation keys
- **[LaTeX Author Names Conversion Spec](latex-authornames-conversion-spec.md)** - Technical specification for author name formatting

## 📊 Analysis and Reports

- **[ArXiv Missing Citations Report](arxiv-missing-citations-report.md)** - Analysis of citation gaps in arXiv metadata
- **[Hardcoded Bibliography Extended](hardcode-biblio-extended.md)** - Extended bibliography handling documentation
- **[Manual Bibliography Knowledge](manual-bibliography-knowledge.md)** - Domain knowledge for manual bibliography processing

## 🔄 Migration and Usage

- **[Migration Usage Examples](migration-usage-examples.md)** - Examples for migrating between different bibliography formats

## 🏛️ Design Principles

The architecture follows these key principles:

1. **Deterministic Processing** - Same input always produces same output
2. **Modular Design** - Clear separation of concerns between modules
3. **AST-Based Parsing** - No regex for structured format parsing
4. **Audit Trail** - Complete tracking of all processing decisions
5. **Performance** - Efficient batch processing and caching

## 📝 Contributing to Architecture Docs

When adding architecture documentation:
- Focus on technical implementation details
- Include diagrams where helpful
- Document design decisions and rationale
- Keep documents focused on single topics
- Update this README when adding new documents
