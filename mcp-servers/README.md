# MCP Servers for Deep Biblio Tools

This directory contains Model Context Protocol (MCP) servers for bibliography management, consolidated from various projects.

## Architecture

**Source of Truth**: All bibliography tooling lives in `deep-biblio-tools`
- Other projects (dpp-fashion, om-knowledge-base) reference these servers
- Single `.env` file in root directory with write-access credentials

## Available Servers

### deep-biblio
Full bibliography management MCP server with:
- Citation extraction from markdown
- Zotero integration
- arXiv/CrossRef metadata fetching
- BibTeX conversion

**Location**: `/Users/petteri/Dropbox/github-personal/deep-biblio-tools/mcp-servers/deep-biblio`

### zotero
Dedicated Zotero MCP server for:
- Zotero library access
- Collection management
- Item creation/updates

**Location**: `/Users/petteri/Dropbox/github-personal/deep-biblio-tools/mcp-servers/zotero`

## Configuration

All servers use centralized credentials from:
```
/Users/petteri/Dropbox/github-personal/deep-biblio-tools/.env
```

Required variables:
```bash
ZOTERO_API_KEY=CvF3rPEqyRUPtREz7gGcvOWP  # Write-access key
ZOTERO_LIBRARY_ID=4953359
```

## Usage from Other Projects

### dpp-fashion
Reference the MCP servers in Claude Code config:
```json
{
  "mcpServers": {
    "deep-biblio": {
      "command": "uv",
      "args": ["--directory", "/Users/petteri/Dropbox/github-personal/deep-biblio-tools/mcp-servers/deep-biblio", "run", "deep-biblio"]
    }
  }
}
```

### om-knowledge-base
No MCP servers needed - this is a content repository (markdown/JSON) with planned Chroma integration for semantic search.

## Migration Complete

**Moved from**:
- `dpp-fashion/mcp-servers/deep-biblio` → `deep-biblio-tools/mcp-servers/deep-biblio`
- `dpp-fashion/mcp-servers/zotero` → `deep-biblio-tools/mcp-servers/zotero`

**Removed**:
- Multiple scattered `.env` files consolidated to one
- Old duplicate scripts in om-knowledge-base
