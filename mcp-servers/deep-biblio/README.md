# Deep-Biblio MCP Server

**Convert academic manuscripts from Markdown to arXiv-ready LaTeX with automatic citation management via Zotero API.**

## What It Does

The Deep-Biblio MCP server helps you:
1. **Extract citations** from your Markdown manuscript
2. **Match them automatically** against your Zotero library (17,000+ items supported)
3. **Add missing citations** to Zotero with metadata from DOI/arXiv APIs
4. **Generate BibTeX** bibliography with proper permalinks
5. **Convert to LaTeX** ready for arXiv submission
6. **Organize your Zotero library** into collections

## Features

- **100% citation matching** via multi-strategy approach (DOI → arXiv → URL → author+year)
- **Automatic metadata fetching** from CrossRef and arXiv APIs
- **Collection management** - auto-organize citations in Zotero
- **Smart output location** - files go to your manuscript directory, not the repo
- **Comprehensive testing** - 22 tests ensure reliability
- **Handles large libraries** - tested with 17,626 Zotero items

## Quick Start

### 1. Install Dependencies

```bash
# Install pandoc (required for LaTeX conversion)
brew install pandoc  # macOS
# or
sudo apt-get install pandoc  # Ubuntu/Debian

# Install Python dependencies
uv sync
```

### 2. Set Up Zotero API

Create a `.env` file in this directory:

```bash
# Get your API key from https://www.zotero.org/settings/keys
ZOTERO_API_KEY=your_api_key_here
ZOTERO_LIBRARY_ID=your_library_id
ZOTERO_LIBRARY_TYPE=user
```

**How to get credentials:**
1. Go to https://www.zotero.org/settings/keys
2. Create a new key with "Read/Write" permissions
3. Copy the key to `ZOTERO_API_KEY`
4. Run `uv run python get-zotero-info.py` to auto-retrieve your library ID

### 3. Convert Your Manuscript

```bash
# Edit the manuscript path in convert-with-zotero-api.py
# Then run:
uv run python convert-with-zotero-api.py
```

This will:
- Fetch all items from your Zotero library
- Match 379 citations (or however many you have)
- Auto-organize matched items into your collection
- Generate `.bib` and `.tex` files in your manuscript directory

## Scripts Overview

### Core Scripts

#### `convert-with-zotero-api.py` - Main Conversion Tool

**Configuration** (edit these lines):
```python
MANUSCRIPT_PATH = "/path/to/your/manuscript.md"
OUTPUT_DIR = Path(MANUSCRIPT_PATH).parent  # Outputs to manuscript directory
COLLECTION_NAME = "your-collection-name"
```

**Output:**
- `references.bib` - Complete bibliography
- `manuscript.tex` - arXiv-ready LaTeX

#### `add-missing-to-zotero.py` - Auto-Add Missing Citations

Automatically adds citations that aren't in your Zotero library with metadata from DOI/arXiv APIs.

#### `get-zotero-info.py` - Test API Connection

Tests your Zotero API setup, retrieves library info, and auto-saves credentials to `.env`.

## Workflow Examples

### Example 1: First-Time Setup

```bash
# 1. Create .env file with your Zotero API key
echo "ZOTERO_API_KEY=your_key" > .env

# 2. Test connection and get library ID
uv run python get-zotero-info.py

# 3. Your .env now has both credentials!
```

### Example 2: Convert Manuscript

```bash
# 1. Edit manuscript path in convert-with-zotero-api.py
# 2. Run conversion
uv run python convert-with-zotero-api.py

# Expected output:
# ✅ Loaded 17626 items from Zotero
# ✅ Matched: 379/379
# ✅ Generated BibTeX and LaTeX files
```

## Citation Format Requirements

Your markdown must use this citation format:

```markdown
[Author(s), Year](URL)
```

**Examples:**
```markdown
[Doe, 2023](https://doi.org/10.1234/example)
[Smith et al., 2022](https://arxiv.org/abs/2201.12345)
[Johnson & Lee, 2021](https://example.com/paper)
```

## Testing

```bash
uv run pytest tests/test_zotero_workflow.py -v
# Expected: 22 passed in 0.11s
```

## Troubleshooting

### "Missing Zotero credentials"
Create `.env` file and run `get-zotero-info.py`

### "No pandoc found"
Install pandoc: `brew install pandoc`

### Low citation match rate
Run `add-missing-to-zotero.py` to add missing citations

## Performance

Tested with 17,626 Zotero items:
- Fetch all items: ~8 min (one-time per run)
- Match 379 citations: ~1 sec
- Generate BibTeX: <1 sec
- LaTeX conversion: ~2 min
- **Total: ~11 min for 100% citation coverage**

---

**Happy paper writing!** 🎓
