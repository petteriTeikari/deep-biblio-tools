# Article Summarizer

A comprehensive tool for processing academic papers and creating literature reviews with proper citations.

## Features

- **Batch Processing**: Process entire folders of academic HTML papers
- **25% Summarization**: Creates comprehensive summaries that are exactly 25% of the original content size
- **Citation Preservation**: Maintains author-year citations with hyperlinks where available
- **Reference Deduplication**: Combines and deduplicates references across multiple papers
- **Literature Review Generation**: Automatically creates comprehensive literature reviews from paper summaries
- **Theme Contextualization**: Allows custom contextualization for specific research domains

## Usage

### Processing a Bibliography Theme Folder

```bash
./scripts/process_biblio_theme_folder.sh /path/to/papers/folder
```

The script will prompt you for:
1. **Theme Context**: e.g., "BIM and point cloud processing"
2. **Contextualization**: e.g., "And if you could have a final chapter contextualizing the learnings for scan-to-bim solutions"

### Output Structure

For each folder processed, the tool creates:
- `markdown_parse/`: Extracted content from HTML papers in markdown format
- `summaries/`: 25% comprehensive summaries with preserved citations
- `.prompt` files: Intermediate prompts showing processing details
- `literature_review_[timestamp].md`: Combined literature review (optional)

### Example Workflow

```bash
# Process BIM-related papers
./scripts/process_biblio_theme_folder.sh ~/papers/bim

# When prompted:
Theme/Context: BIM and digital twin technologies
Contextualization: Implications for modern construction workflows

# The script will:
# 1. Extract content from all HTML files
# 2. Create 25% summaries preserving citations
# 3. Optionally generate a comprehensive literature review
```

## Technical Details

### Components

1. **extract_sciencedirect_paper.py**: Extracts content from ScienceDirect HTML papers
2. **create_literature_summary.py**: Creates 25% summaries with citation preservation
3. **create_theme_review.py**: Generates comprehensive literature reviews
4. **process_biblio_theme_folder.sh**: Main orchestration script

### Citation Format

The tool preserves citations in author-year format:
- Input: `[42]` or numeric references
- Output: `[Smith et al., 2023](url)` with preserved hyperlinks

### Summary Algorithm

The 25% summarization:
- Prioritizes sections by importance (abstract > results > methods)
- Preserves complete sentences
- Maintains all metadata (title, authors, DOI, keywords)
- Includes complete reference list

## Requirements

- Python 3.8+
- BeautifulSoup4
- Standard Unix tools (bash, find, wc)

## Configuration

The tool saves configuration in the processed folder:
- `.theme_context`: The theme/domain of the papers
- `.contextualization`: How to contextualize findings

This allows for reproducible processing and future reference.
