# Markdown to LaTeX Converter Implementation Plan

**Date**: 2025-07-29
**Purpose**: Convert UADReview_v4b.md to arXiv-ready LaTeX format
**Status**: Active Development

## Analysis Summary

### Source Document (UADReview_v4b.md)
- **Type**: Academic paper about AI-augmented real estate valuation
- **Size**: Large academic document with multiple sections
- **Key Features**:
  - Complex citations in format: `[Author et al. (Year)](URL)`
  - Technical concept boxes marked with `*Technical Concept Box: Title*`
  - Academic structure: Abstract, Introduction, multiple sections
  - Mix of narrative text and technical content

### Guide Document (arxiv_converter_guide.md)
- **Comprehensive implementation**: 1600+ lines of Python code
- **Key Features**:
  - Multi-source citation fetching (Zotero, CrossRef, arXiv, etc.)
  - 5 different concept box styles (professional_blue, modern_gradient, etc.)
  - Caching system for citations
  - Progress tracking with colored output
  - Automated BibTeX generation

## Implementation Plan

### Phase 1: Core Infrastructure
1. **Create project structure**
   ```
   src/deep_biblio_tools/converters/
   ├── __init__.py
   ├── md_to_latex/
   │   ├── __init__.py
   │   ├── converter.py         # Main converter class
   │   ├── citation_manager.py  # Citation fetching and management
   │   ├── concept_boxes.py     # Concept box styles and conversion
   │   ├── latex_builder.py     # LaTeX document construction
   │   └── utils.py            # Helper functions
   ```

2. **Implement base converter class**
   - Read markdown files
   - Basic pandoc integration
   - Output directory management

3. **Add configuration management**
   - Environment variables (.env support)
   - Command-line arguments
   - Default settings

### Phase 2: Citation Processing
1. **Implement citation extraction**
   - Regex pattern for `[Author (Year)](URL)` format
   - Parse authors and year
   - Generate unique citation keys

2. **Create citation fetcher (simplified version)**
   - Start with basic URL-based fetching
   - Add DOI resolution for doi.org links
   - Implement caching to avoid repeated API calls
   - Generate basic BibTeX entries

3. **Add Zotero integration (optional)**
   - Search existing library
   - Create collections
   - Add new citations

### Phase 3: Concept Box Conversion
1. **Implement concept box detection**
   - Pattern matching for `*Technical Concept Box: Title*`
   - Extract title and content
   - Handle multi-paragraph boxes

2. **Create style templates**
   - Start with professional_blue style
   - Use tcolorbox package
   - Ensure LaTeX compatibility

### Phase 4: LaTeX Generation
1. **Create document template**
   - arXiv-compliant preamble
   - Required packages
   - Bibliography setup with biblatex

2. **Implement post-processing**
   - Remove problematic commands
   - Convert hyperlinks to footnotes
   - Clean up pandoc artifacts

3. **Generate supporting files**
   - references.bib
   - Makefile for compilation
   - README with instructions

### Phase 5: Testing and Refinement
1. **Test with UADReview_v4b.md**
   - Verify all citations are captured
   - Check concept box rendering
   - Compile LaTeX to PDF

2. **Add error handling**
   - Network failures for citation fetching
   - Missing dependencies
   - Invalid markdown syntax

3. **Performance optimization**
   - Parallel citation fetching
   - Progress indicators
   - Efficient caching

## Technical Decisions

### Dependencies (Minimal Set)
```python
# Core
pypandoc>=1.11        # Markdown to LaTeX conversion
bibtexparser>=1.4.0   # BibTeX file generation
python-dotenv>=1.0.0  # Environment configuration
requests>=2.28.0      # HTTP requests for citations
click>=8.0.0          # CLI interface
tqdm>=4.65.0         # Progress bars

# Optional (can add later)
pyzotero>=1.5.0      # Zotero integration
habanero>=1.2.0      # CrossRef API
beautifulsoup4>=4.11.0  # HTML parsing
```

### Key Design Choices
1. **Modular architecture**: Separate concerns (citations, boxes, LaTeX)
2. **Progressive enhancement**: Start simple, add features incrementally
3. **Fallback strategies**: Handle API failures gracefully
4. **User-friendly output**: Clear progress, helpful error messages

## Implementation Priority

### MVP (Minimum Viable Product)
1. Basic markdown to LaTeX conversion
2. Citation extraction and simple BibTeX generation
3. Concept box conversion (one style)
4. Generate compilable LaTeX output

### Enhancements (Phase 2)
1. Multi-source citation fetching
2. Additional concept box styles
3. Zotero integration
4. Better error handling and logging

### Advanced Features (Phase 3)
1. Parallel processing
2. Custom style configurations
3. Batch processing multiple files
4. Integration with deep-biblio-tools ecosystem

## Next Steps
1. Create the module structure
2. Implement basic converter class
3. Add citation extraction
4. Test with sample markdown
5. Iterate based on results

## Success Criteria
- Successfully converts UADReview_v4b.md to LaTeX
- All citations properly extracted and formatted
- Concept boxes render correctly
- Output compiles with `xelatex` without errors
- Generated PDF looks professional and arXiv-ready
