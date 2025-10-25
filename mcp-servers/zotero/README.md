# zotero MCP Server

MCP server for Zotero library sync and automated paper import.

## Features

- **import_from_zotero**: Auto-import papers from Zotero library
- **sync_metadata**: Keep Zotero metadata synced with Chroma
- **trigger_conversion**: Use deep-biblio-tools for PDF conversion
- **get_zotero_item**: Retrieve item metadata by ID

## Installation

```bash
cd mcp-servers/zotero
uv sync
```

## Configuration

Set environment variables:

```bash
export ZOTERO_LIBRARY_ID="your_library_id"
export ZOTERO_LIBRARY_TYPE="user"  # or "group"
export ZOTERO_API_KEY="your_api_key"
```

### Get Zotero API Credentials

1. Go to https://www.zotero.org/settings/keys
2. Click "Create new private key"
3. Give it a name and select permissions
4. Copy the API key
5. Find your library ID in Zotero settings

## Usage

### Run as MCP Server

```bash
uv run python -m zotero.server
```

### Configure in Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "zotero": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/petteri/Dropbox/LABs/open-mode/github/dpp-fashion/mcp-servers/zotero",
        "run",
        "python",
        "-m",
        "zotero.server"
      ],
      "env": {
        "ZOTERO_LIBRARY_ID": "your_id",
        "ZOTERO_LIBRARY_TYPE": "user",
        "ZOTERO_API_KEY": "your_key"
      }
    }
  }
}
```

## Tools

### import_from_zotero

Auto-import papers from Zotero library.

**Arguments:**
- `collection_id` (str, optional): Zotero collection ID
- `limit` (int, default=50): Max papers to import
- `tags` (list[str], optional): Filter by tags

**Example:**
```json
{
  "collection_id": "ABC123",
  "limit": 50,
  "tags": ["formal-verification", "machine-learning"]
}
```

### sync_metadata

Sync metadata between Zotero and Chroma.

**Arguments:**
- `arxiv_id` (str): ArXiv ID to sync
- `direction` (str, default="zotero_to_chroma"): Sync direction

**Example:**
```json
{
  "arxiv_id": "2509.23864",
  "direction": "zotero_to_chroma"
}
```

### trigger_conversion

Trigger PDF conversion using deep-biblio-tools.

**Arguments:**
- `zotero_item_id` (str): Zotero item ID
- `deep_biblio_tools_path` (str): Path to deep-biblio-tools

**Example:**
```json
{
  "zotero_item_id": "ABC123",
  "deep_biblio_tools_path": "/Users/petteri/Dropbox/github-personal/deep-biblio-tools"
}
```

### get_zotero_item

Retrieve Zotero item metadata.

**Arguments:**
- `item_id` (str): Zotero item ID

**Example:**
```json
{
  "item_id": "ABC123"
}
```

## Workflows

### Auto-Import from Zotero to om-knowledge-base

1. **Import papers**: Use `import_from_zotero` to get metadata
2. **Convert PDFs**: Use `trigger_conversion` with deep-biblio-tools
3. **Sync metadata**: Use `sync_metadata` to update Chroma
4. **Index papers**: Papers automatically indexed in Chroma

### Keep Zotero and Chroma in Sync

1. **Monitor Zotero**: Periodically check for new items
2. **Sync metadata**: Auto-sync changes to Chroma
3. **Bidirectional sync**: Keep both systems updated

## Integration with deep-biblio-tools

The `trigger_conversion` tool integrates with deep-biblio-tools for:
- PDF to Markdown conversion
- Metadata extraction
- YAML frontmatter generation
- Citation graph analysis

**Note**: Full deep-biblio-tools integration is pending - requires API development.

## Dependencies

- mcp>=1.3.2
- pyzotero>=1.5.22
- pydantic>=2.10.6
