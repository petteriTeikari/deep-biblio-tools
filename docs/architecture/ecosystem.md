# Open Mode Four-Component Ecosystem

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        OPEN MODE ECOSYSTEM                       │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────┐  ┌──────────────────────┐
│   dpp-fashion        │  │  om-knowledge-base   │
│   THE PRODUCT        │  │  KNOWLEDGE REPO      │
├──────────────────────┤  ├──────────────────────┤
│ • Fashion DPP app    │  │ • Manuscripts (.md)  │
│ • Supply chain data  │  │ • Knowledge (.json)  │
│ • Harmonization      │  │ • Research papers    │
│ • Internal reviews   │  │ • Future: Chroma DB  │
│                      │  │                      │
│ Uses ↓               │  │ Content ↓            │
└──────┬───────────────┘  └──────┬───────────────┘
       │                         │
       │ Citations               │ Academic
       │ Internal reviews        │ Publishing
       │                         │
       ├─────────────────────────┘
       │
       ↓
┌──────────────────────┐  ┌──────────────────────┐
│ deep-biblio-tools    │  │ claude-code-ops      │
│ ACADEMIC TOOLING     │  │ AI ENGINEERING       │
├──────────────────────┤  ├──────────────────────┤
│ • MCP servers        │  │ • Context engineer   │
│ • CLI tools          │  │ • Guardrails         │
│ • Zotero manager     │  │ • Alignment models   │
│ • Format converters  │  │ • Prompt patterns    │
│ • Publication tools  │  │                      │
└──────────────────────┘  └──────────────────────┘
```

## Component Responsibilities

### 1. dpp-fashion (Product)
**Type**: Application
**Owner**: Product team
**Purpose**: Fashion Digital Product Passport

**Key Features**:
- Supply chain data harmonization
- Knowledge engineering workflows
- Multi-agent coordination
- Internal research reviews

**Dependencies**:
- Uses `deep-biblio-tools` for citation management
- Stores knowledge in `om-knowledge-base`
- Constrained by `claude-code-ops`

### 2. om-knowledge-base (Knowledge)
**Type**: Content Repository
**Owner**: Research team
**Purpose**: Organizational knowledge storage

**Key Features**:
- Research manuscripts (markdown)
- Structured knowledge (JSON)
- Academic papers
- Planned: Chroma vector DB

**Dependencies**:
- Processed by `deep-biblio-tools` for citations
- Referenced by `dpp-fashion` for reviews
- Pure content, no tooling

### 3. claude-code-ops (AI Engineering)
**Type**: Tooling & Constraints
**Owner**: AI Engineering team
**Purpose**: Claude Code alignment & safety

**Key Features**:
- Context engineering frameworks
- Guardrails for AI operations
- Alignment modeling
- Prompt patterns

**Dependencies**:
- Constrains `dpp-fashion` Claude usage
- May use `deep-biblio-tools` for documentation

### 4. deep-biblio-tools (Academic Tools)
**Type**: Tooling & Infrastructure
**Owner**: Research ops team
**Purpose**: Bibliography & citation management

**Key Features**:
- Zotero integration
- Citation extraction & conversion
- Academic review workflows
- Publication tooling (arXiv, LaTeX)

**Dependencies**:
- Serves `dpp-fashion` (internal reviews)
- Serves `om-knowledge-base` (publications)
- Independent, self-contained

## Information Flow

### Academic Publishing Workflow
```
om-knowledge-base/paper.md
    ↓ (extract citations)
deep-biblio-tools/zotero-citations
    ↓ (convert to BibTeX)
deep-biblio-tools/md-to-latex
    ↓ (output)
paper.tex + references.bib → arXiv
```

### Internal Review Workflow
```
dpp-fashion/internal-review.md
    ↓ (citation management)
deep-biblio-tools/MCP-server
    ↓ (store knowledge)
om-knowledge-base/reviews/
```

### Knowledge Engineering Workflow
```
dpp-fashion/supply-chain-data
    ↓ (harmonize & extract)
Knowledge Engineering Agent
    ↓ (store structured)
om-knowledge-base/knowledge.json
    ↓ (index)
Chroma Vector DB (future)
```

### AI Constraint Workflow
```
claude-code-ops/guardrails.yaml
    ↓ (configure)
Claude Code MCP Config
    ↓ (constrain)
dpp-fashion/AI operations
```

## Technology Stack

### dpp-fashion
- **Runtime**: Python 3.12+
- **Framework**: FastAPI
- **Database**: PostgreSQL, Neo4j
- **AI**: Claude API, LangChain
- **Package Manager**: uv

### om-knowledge-base
- **Format**: Markdown, JSON
- **Future**: Chroma vector DB
- **Tooling**: None (content only)

### claude-code-ops
- **Language**: Python 3.12+
- **Framework**: Custom constraint DSL
- **Integration**: MCP protocol
- **Package Manager**: uv

### deep-biblio-tools
- **Language**: Python 3.12+
- **Package Manager**: uv
- **APIs**: Zotero, CrossRef, arXiv
- **Formats**: BibTeX, LaTeX, Markdown
- **Protocol**: MCP for Claude integration

## Credential Management

### Centralized in deep-biblio-tools
```bash
/Users/petteri/Dropbox/github-personal/deep-biblio-tools/.env
```

**Contains**:
- `ZOTERO_API_KEY` (write access)
- `ZOTERO_LIBRARY_ID`
- Other bibliography API keys

**Why Here?**:
- Single source of truth
- Used by all academic workflows
- Easy rotation and management

### Project-Specific Credentials
- **dpp-fashion**: Own `.env` for app secrets
- **om-knowledge-base**: No credentials needed
- **claude-code-ops**: Own `.env` for AI services

## Migration History

### Before (Scattered)
```
dpp-fashion/
├── mcp-servers/deep-biblio/    ← DUPLICATE
├── mcp-servers/zotero/         ← DUPLICATE
└── .env (different API key)

om-knowledge-base/
└── scripts/zotero-citations/   ← DUPLICATE

deep-biblio-tools/
└── .env (read-only API key)
```

### After (Consolidated) - October 2025
```
deep-biblio-tools/ (SINGLE SOURCE)
├── mcp-servers/
│   ├── deep-biblio/
│   └── zotero/
├── tools/
│   └── zotero-citations/
└── .env (write-access key)

dpp-fashion/
└── mcp-servers/ (project-specific only)

om-knowledge-base/
└── (content only, no tools)
```

## Usage Examples

### From dpp-fashion (Internal Review)
```python
# Claude Code with deep-biblio MCP server
# Automatically extracts citations from review markdown
# Adds to Zotero "dpp-fashion" collection
```

### From om-knowledge-base (Academic Paper)
```bash
# Convert manuscript to LaTeX for publication
cd ~/Dropbox/github-personal/deep-biblio-tools/tools/zotero-citations
uv run main.py  # Add verified citations

cd ~/Dropbox/github-personal/deep-biblio-tools/mcp-servers/deep-biblio
# Convert md → LaTeX with BibTeX
```

### From claude-code-ops (AI Constraint)
```yaml
# Configure Claude Code guardrails
constraints:
  - no_external_api_calls: true
  - require_citation_verification: true  # Uses deep-biblio-tools
```

## Future Roadmap

### Q1 2026: Chroma Integration
- `om-knowledge-base` → Chroma DB
- `deep-biblio-tools` → Indexing pipeline
- `dpp-fashion` → Semantic search API

### Q2 2026: Advanced Constraints
- `claude-code-ops` → Learning from interactions
- `dpp-fashion` → Adaptive guardrails
- `deep-biblio-tools` → Citation quality scoring

### Q3 2026: Public API
- `deep-biblio-tools` → REST API
- Public academic tooling service
- Community contributions

---

**Last Updated**: October 25, 2025
**Status**: Architecture finalized and documented
**Next Review**: January 2026
