# Elsevier Parser Abstract Extraction Fix

## Problem
The Elsevier HTML scraper was not correctly extracting abstracts from ScienceDirect pages. The parser was looking for a simple `<div class="abstract">` element, but the actual HTML structure is more complex.

## Solution
Updated the `get_paper_details` method in `scraper_standalone.py` to use multiple extraction methods:

### Method 1: Direct HTML extraction
- Looks for `<div class="abstract author" id="ab0005">`
- Then finds the nested `<div id="sp0140">` which contains the actual abstract text

### Method 2: Fallback HTML extraction
- Searches for any div with class containing "abstract"
- Removes headers (h2, h3, h4) before extracting text

### Method 3: JavaScript object extraction
- Parses the `window.__PRELOADED_STATE__` JavaScript object
- Navigates the complex JSON structure to find the abstract
- Handles both simple text and complex nested structures with topic links

## HTML Structure Found
The abstract in Elsevier HTML files is structured as:
```html
<div id="preview-section-abstract">
  <div class="abstract author" id="ab0005" lang="en">
    <h2>Abstract</h2>
    <div id="as0005">
      <div id="sp0140">
        <!-- Abstract text with topic links and formatting -->
      </div>
    </div>
  </div>
</div>
```

## Testing
The fix was tested on the sample file:
- `/data/elsevier_manual_scrape/2D–3D fusion approach for improved point cloud segmentation - ScienceDirect.html`

The parser now correctly extracts:
- Full abstract text (1105 characters)
- Title: "2D–3D fusion approach for improved point cloud segmentation"
- DOI: "https://doi.org/10.1016/j.autcon.2025.106336"

## Files Modified
- `tools/scraper_standalone.py` - Updated the abstract extraction logic in `get_paper_details` method
