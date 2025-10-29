# Deep Biblio Tools Architecture

**Last Updated**: October 2025

## Overview

`deep-biblio-tools` is the **centralized repository** for all bibliography and citation management tooling.

## Directory Structure

```
deep-biblio-tools/
├── .env                              # Master credentials (Zotero API, etc.)
├── src/                              # Core library code
├── tools/                            # Standalone CLI tools
│   └── zotero-citations/            # Add citations to Zotero collections (uv)
├── mcp-servers/                     # MCP servers for Claude Code
│   ├── deep-biblio/                 # Main bibliography MCP server
│   └── zotero/                      # Zotero-specific MCP server
├── scripts/                         # Utility scripts
├── tests/                           # Test suite
└── docs/                            # Documentation
```

## Four-Component Architecture

The Open Mode ecosystem consists of four specialized repositories:

### 1. **dpp-fashion** - The Product
**Purpose**: Fashion Digital Product Passport application
**Contains**:
- Production application code
- Supply chain data harmonization
- Knowledge engineering workflows
- Project-specific MCP servers (knowledge-base, notion)

**Relationship**: Uses deep-biblio-tools for citation management in internal reviews

### 2. **om-knowledge-base** - Organization Knowledge
**Purpose**: Centralized knowledge repository
**Contains**:
- Research manuscripts (markdown)
- Structured knowledge (JSON)
- Academic papers and reviews
- Future: Chroma vector DB for semantic search

**Relationship**: Pure content storage, no tooling

### 3. **claude-code-ops** - AI Engineering
**Purpose**: Claude Code constraint and alignment engineering
**Contains**:
- Context engineering frameworks
- Guardrails and safety constraints
- Alignment modeling tools
- Prompt engineering patterns

**Relationship**: Ensures Claude Code operates within organizational constraints

### 4. **deep-biblio-tools** - Academic Tooling (This Repo)
**Purpose**: Bibliography and citation management
**Contains**:
- MCP servers for citation workflows
- CLI tools for Zotero/BibTeX management
- Academic review tooling (publication & internal)
- Format converters (markdown ↔ LaTeX ↔ BibTeX)

**Relationship**: Provides academic tooling for om-knowledge-base content and dpp-fashion reviews

## Design Principles

### 1. Single Source of Truth
- All bibliography tools live in `deep-biblio-tools`
- Other projects reference, not duplicate
- One `.env` file with write-access credentials

### 2. Clear Separation of Concerns
```
dpp-fashion/          → Product application
om-knowledge-base/    → Knowledge repository
claude-code-ops/      → AI constraint engineering
deep-biblio-tools/    → Academic tooling
```

### 3. No Pip - Use uv
- All Python projects use `uv` for dependency management
- Each tool has its own `pyproject.toml` and `.venv`
- No system-wide pip installations

## Key Components

### MCP Servers (for Claude Code)
**Location**: `/mcp-servers/`

- **deep-biblio**: Full citation management (extraction, conversion, Zotero sync)
- **zotero**: Dedicated Zotero operations

**Usage in other projects**:
```json
{
  "mcpServers": {
    "deep-biblio": {
      "command": "uv",
      "args": ["--directory", "/path/to/deep-biblio-tools/mcp-servers/deep-biblio", "run", "deep-biblio"]
    }
  }
}
```

### CLI Tools
**Location**: `/tools/`

- **zotero-citations**: Add verified citations to collections
  ```bash
  cd tools/zotero-citations
  uv run main.py
  ```

### Core Library
**Location**: `/src/`

- Citation parsers (markdown, LaTeX, BibTeX)
- API clients (Zotero, CrossRef, arXiv)
- Format converters

## Configuration

### Centralized Environment Variables
**File**: `/Users/petteri/Dropbox/github-personal/deep-biblio-tools/.env`

```bash
# Zotero API (write-access key)
ZOTERO_API_KEY=CvF3rPEqyRUPtREz7gGcvOWP
ZOTERO_LIBRARY_ID=4953359
```

### Why Centralized?
- Single point of credential management
- No duplicate keys across projects
- Easy rotation and updates

## Integration with Other Projects

### dpp-fashion
**Relationship**: References deep-biblio MCP servers

**What it does**:
- Fashion Digital Product Passport application
- Knowledge engineering for supply chain data
- Planned: Chroma vector DB integration

**What it doesn't do**:
- ❌ Host bibliography tools (references them instead)
- ❌ Duplicate MCP servers

### om-knowledge-base
**Relationship**: Pure content repository

**What it does**:
- Stores markdown manuscripts and research notes
- Structured JSON knowledge files
- Planned: Chroma vector DB for semantic search

**What it doesn't do**:
- ❌ Host tooling (content only)
- ❌ Duplicate scripts

## Migration History

### October 2025: Consolidation
**Before**:
- Bibliography tools scattered across 3 repositories
- Multiple `.env` files with different API keys
- Duplicate MCP servers in dpp-fashion and om-knowledge-base

**After**:
- ✅ All tools in `deep-biblio-tools`
- ✅ Single `.env` with write-access key
- ✅ MCP servers centralized
- ✅ Other projects reference, not duplicate

## Development Workflow

### Adding a New Tool
1. Create in `tools/new-tool/`
2. Use `uv init` for project setup
3. Add dependencies with `uv add`
4. Document in tool's README
5. Reference centralized `.env`

### Adding an MCP Server
1. Create in `mcp-servers/new-server/`
2. Implement MCP protocol
3. Document in mcp-servers/README.md
4. Other projects reference via config

### Credential Updates
1. Update `/Users/petteri/Dropbox/github-personal/deep-biblio-tools/.env`
2. All tools automatically use new credentials
3. No per-project updates needed

## Future Plans

### Chroma Integration
**Goal**: Semantic search over bibliography and knowledge base

**Architecture**:
```
deep-biblio-tools/     → Tools to populate Chroma
om-knowledge-base/     → Content to index
dpp-fashion/           → Application using Chroma search
```

**Status**: Planned (see dpp-fashion/docs/planning)

### API Server
**Goal**: REST API for bibliography operations

**Benefits**:
- Language-agnostic access
- Web application integration
- Microservice architecture

**Status**: Future consideration

## Getting Help

- **Issues**: https://github.com/petteriTeikari/deep-biblio-tools/issues
- **Docs**: `/docs/` directory
- **Examples**: `/examples/` directory
