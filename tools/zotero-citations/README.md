# Zotero 4DGS Citations Manager

Adds verified 4DGS citations to the `dpp-fashion` Zotero collection using `uv`.

## Setup

The project uses `uv` for dependency management (no pip needed):

```bash
# Dependencies are already installed in .venv
# Just run the script
uv run main.py
```

## Zotero API Key Setup

**IMPORTANT**: Your Zotero API key needs **write permissions**.

1. Go to https://www.zotero.org/settings/keys
2. Find your existing key or create a new one:
   - Name: "deep-biblio-tools" (or similar)
   - **Check "Allow library access" with READ/WRITE**
   - Check "Allow notes access" (optional)
3. Copy the API key
4. Update `/Users/petteri/Dropbox/github-personal/deep-biblio-tools/.env`:
   ```bash
   ZOTERO_API_KEY=your_new_key_with_write_access
   ZOTERO_LIBRARY_ID=4953359
   ```

## Citations Added

The script adds these 6 verified 4DGS papers:

1. **Gaussian Garments** - arXiv:2409.08189
2. **ClothingTwin** - DOI:10.1111/cgf.70240 ✅ (already in collection)
3. **D3GA** - arXiv:2311.08581
4. **3DGS-Avatar** - arXiv:2312.09228
5. **MPMAvatar** - arXiv:2510.01619
6. **Offset Geometric Contact** - DOI:10.1145/3731205

## Usage

```bash
cd /Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/paper-manuscripts/fashion_3D_CAD/scripts/zotero-citations
uv run main.py
```

## Current Status

- ✅ Script runs successfully with `uv`
- ✅ Found `dpp-fashion` collection
- ✅ ClothingTwin already exists (skipped)
- ❌ 5 citations failed: **403 Write access denied**

**Next Step**: Update Zotero API key with write permissions, then re-run `uv run main.py`

## Dependencies

Managed by `uv` (see `pyproject.toml`):
- `pyzotero` - Zotero API client
- `requests` - HTTP requests for arXiv/CrossRef APIs

## Project Structure

```
zotero-citations/
├── main.py          # Main script
├── pyproject.toml   # uv project config
├── uv.lock          # Dependency lock file
├── .venv/           # Virtual environment (managed by uv)
└── README.md        # This file
```
