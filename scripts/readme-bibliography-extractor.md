# Bibliography Extractor with Metadata Fetching

## Overview

The `extract_bibliography_with_metadata.py` script extracts citations from markdown files and automatically fetches real metadata from various sources, creating properly formatted BibTeX entries with actual paper titles instead of generic placeholders.

## Features

- **Citation Pattern Recognition**: Extracts citations in format `[Author (Year)](URL)`
- **Multi-Source Metadata Fetching**:
  - **CrossRef API**: For DOI URLs (e.g., `https://doi.org/10.1234/test`)
  - **arXiv API**: For arXiv papers (e.g., `https://arxiv.org/abs/2401.12345`)
  - **Web Scraping**: Attempts to fetch page titles for other URLs
- **Smart URL Parsing**: Automatically detects DOIs and arXiv IDs from various URL formats
- **Rate Limiting**: Respects API rate limits with configurable delays
- **Progress Feedback**: Real-time logging of extraction progress
- **Error Handling**: Graceful handling of failed requests with clear error messages
- **Output Formats**:
  - **BibTeX file**: Properly formatted bibliography entries
  - **JSON summary**: Detailed report with metadata sources and fetch status

## Installation

The script requires Python 3.7+ and the following dependencies:
```bash
pip install requests
```

## Usage

### Basic Usage
```bash
python extract_bibliography_with_metadata.py input.md
```

This will create:
- `input.bib` - The BibTeX bibliography
- `input.json` - Summary report with metadata details

### Custom Output Path
```bash
python extract_bibliography_with_metadata.py input.md -o bibliography.bib
```

### Verbose Mode
```bash
python extract_bibliography_with_metadata.py input.md -v
```

## Output Format

### BibTeX Output

The generated BibTeX file groups entries by metadata source:

```bibtex
% CROSSREF SOURCES (15 entries)
% ============================================================

@article{smith2023,
  author = "Smith et al.",
  title = "Real Paper Title from CrossRef",
  year = "2023",
  journal = "Journal Name",
  volume = "42",
  pages = "123-456",
  doi = "10.1234/test",
  url = "https://doi.org/10.1234/test",
  note = "Metadata from: CrossRef",
}

% ARXIV SOURCES (5 entries)
% ============================================================

@misc{johnson2024,
  author = "Johnson",
  title = "Machine Learning Paper Title",
  year = "2024",
  arxivId = "2401.12345",
  eprint = "2401.12345",
  archivePrefix = "arXiv",
  url = "https://arxiv.org/abs/2401.12345",
  note = "Metadata from: arXiv",
}

% MANUAL SOURCES (2 entries)
% ============================================================

@misc{unknown2022,
  author = "Unknown Author",
  title = "[Title not available - manual entry needed]",
  year = "2022",
  url = "https://example.com/paper",
  note = "Metadata fetch error: Could not fetch metadata automatically",
}
```

### JSON Summary

The JSON summary provides detailed statistics and metadata:

```json
{
  "source_file": "input.md",
  "extraction_date": "2025-08-01T12:00:00",
  "total_citations": 22,
  "metadata_sources": {
    "CrossRef": 15,
    "arXiv": 5,
    "webpage": 1,
    "manual": 1
  },
  "citations": [
    {
      "authors": "Smith et al.",
      "year": "2023",
      "title": "Real Paper Title from CrossRef",
      "url": "https://doi.org/10.1234/test",
      "metadata_source": "CrossRef",
      "fetch_error": null
    }
  ]
}
```

## API Configuration

The script includes reasonable defaults for API usage:
- **Request Delay**: 0.5 seconds between API calls
- **Max Retries**: 3 attempts for failed requests
- **Timeout**: 10 seconds per request
- **User Agent**: Identifies as "DeepBiblioTools/1.0"

## Limitations

1. **PDF URLs**: The script cannot extract metadata from direct PDF links (except arXiv PDFs)
2. **Authentication**: Some sources may require authentication (e.g., SSRN, some publisher sites)
3. **Rate Limits**: Large documents may take time due to API rate limiting
4. **Title Extraction**: Web page title extraction is basic and may not always get the full paper title

## Error Handling

Citations that fail metadata fetching will:
1. Still appear in the bibliography with placeholder titles
2. Include a note indicating manual entry is needed
3. Be tracked in the JSON summary with error details

## Example

Given a markdown file with:
```markdown
Recent AI research by [Smith et al. (2023)](https://doi.org/10.1234/test) shows...
See also [Johnson (2024)](https://arxiv.org/abs/2401.12345) for details.
```

The script will:
1. Extract both citations
2. Fetch "Real Paper Title" from CrossRef for the DOI
3. Fetch "Machine Learning Paper" from arXiv
4. Generate properly formatted BibTeX entries
5. Create a summary report

## Testing

Run the test suite with:
```bash
pytest tests/test_bibliography_extraction.py -v
```

## Future Enhancements

Potential improvements for future versions:
- Support for more citation formats (e.g., footnotes, numbered references)
- Integration with Zotero/Mendeley APIs
- Batch processing of multiple files
- Caching of fetched metadata
- Support for book ISBN lookups
- Better PDF metadata extraction
