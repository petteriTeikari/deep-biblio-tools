# Paper Scraper for Academic Publishers

## Overview

This tool provides scrapers for academic publishers, starting with Elsevier's ScienceDirect. The scraper is designed to:

- Search for papers by keyword, journal, and year
- Extract abstracts and metadata
- Save results as BibTeX with abstracts
- Identify open access papers
- Implement respectful rate limiting

## Current Status

### ScienceDirect/Elsevier Scraper

**Status**: Code complete but blocked by anti-scraping measures (403 Forbidden errors).

**Files created**:
- `src/api_clients/elsevier.py` - Full-featured scraper class with rate limiting
- `tools/paper_scraper.py` - CLI tool with database storage
- `tools/scraper_standalone.py` - Standalone version without dependencies

### Features Implemented

1. **Search functionality**: Query papers with filters for journal and years
2. **Abstract extraction**: Parse paper pages to get abstracts, authors, DOI, keywords
3. **Rate limiting**: Configurable delays between requests (default 1s)
4. **Database storage**: JSON database to store scraped papers
5. **BibTeX export**: Convert papers to BibTeX format with abstracts
6. **Open access detection**: Identify papers with free PDF access

## Alternative Approaches

Since direct web scraping is blocked, here are recommended alternatives:

### 1. Official APIs (Recommended)

**Elsevier Developer Portal**: https://dev.elsevier.com/
- Requires registration and API key
- Provides legitimate access to:
  - ScienceDirect Article Retrieval API
  - Scopus Search API
  - Abstract Retrieval API
- Rate limits: ~20,000 requests/week for academic use

### 2. Browser Automation

Use Selenium or Playwright to automate a real browser:
```python
from selenium import webdriver
from selenium.webdriver.common.by import By
import time

driver = webdriver.Chrome()
driver.get("https://www.sciencedirect.com/search?qs=BIM")
time.sleep(5)  # Wait for page load
# Extract data...
```

### 3. Semi-Automated Approach

1. Use the scraper to generate URLs
2. Manually download search results pages
3. Parse the saved HTML files locally

### 4. Zotero Integration

Since you mentioned Zotero:
1. Use Zotero's browser connector to save papers
2. Export from Zotero with abstracts included
3. Use Zotero's API to access your library programmatically

## Usage Examples

### Basic search (if scraping worked):
```bash
python tools/scraper_standalone.py "BIM" --journal "Automation in Construction" --years 2023 2024 --max-results 100
```

### With database and BibTeX export:
```bash
python tools/paper_scraper.py "scan to bim" \
  --journal "Automation in Construction" \
  --years 2021 2022 2023 2024 2025 \
  --max-results 50 \
  --bibtex scan_to_bim.bib \
  --db papers_db.json
```

## Next Steps

1. **Register for Elsevier API**: Get legitimate access
2. **Implement API client**: Replace scraper with API calls
3. **Add other publishers**: IEEE, Springer, ACM, etc.
4. **Batch processing**: Handle large-scale searches efficiently

## Ethical Considerations

- Always respect robots.txt and terms of service
- Use official APIs when available
- Implement rate limiting to avoid overloading servers
- Identify your tool with proper User-Agent headers
- Consider the impact on publisher resources

## Technical Details

The scraper implements:
- Session management with connection pooling
- Exponential backoff for rate limiting
- Robust error handling
- Incremental database updates
- Configurable delays between requests

Even though direct scraping is blocked, the code provides a solid foundation for:
- Working with official APIs
- Processing downloaded HTML files
- Managing bibliography databases
- Converting between formats
