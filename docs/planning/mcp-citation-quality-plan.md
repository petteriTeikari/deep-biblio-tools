# Citation Quality MCP Server - Implementation Plan

**Status**: Planning
**Priority**: High
**Goal**: Create reusable MCP server for citation quality auditing that can be used standalone or integrated with the converter

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                Citation Quality MCP Server                   │
│                                                              │
│  Tools:                                                      │
│  1. audit_markdown_citations                                │
│  2. check_citation_url_quality                              │
│  3. verify_zotero_match                                     │
│  4. check_link_health                                       │
│  5. validate_bibtex_keys                                    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│              Reuses Existing Components                      │
│                                                              │
│  • UnifiedCitationExtractor (citation detection)            │
│  • CitationManager (Zotero matching)                        │
│  • URL categorization logic                                 │
│  • Better BibTeX key validation                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                    Usage Scenarios                           │
│                                                              │
│  1. Standalone: Claude Code calls MCP tools directly        │
│  2. Integrated: md2latex --audit calls MCP internally       │
│  3. Pre-commit: Git hook validates citations before commit  │
└─────────────────────────────────────────────────────────────┘
```

## MCP Tools Design

### 1. `audit_markdown_citations`

**Purpose**: Comprehensive audit of all citations in a markdown file

**Input**:
```json
{
  "file_path": "/path/to/manuscript.md",
  "zotero_collection": "dpp-fashion",
  "check_link_health": true,
  "validate_metadata": true
}
```

**Output**:
```json
{
  "summary": {
    "total_links": 712,
    "academic_citations": 560,
    "grey_literature": 34,
    "regular_hyperlinks": 118,
    "problematic": 9,
    "questionable": 22,
    "broken_links": 3
  },
  "issues": [
    {
      "line": 79,
      "type": "problematic_url",
      "severity": "error",
      "citation": "[GaussianVTON (Cao et al., 2024)](https://yukangcao.github.io/GS-VTON/)",
      "issue": "Project page instead of paper",
      "suggestion": "https://arxiv.org/abs/2410.05259"
    },
    {
      "line": 156,
      "type": "metadata_mismatch",
      "severity": "warning",
      "citation": "[Kuźniak et al. (2024)](https://arxiv.org/abs/2504.01483)",
      "issue": "Wrong source - this is a published JINST paper",
      "correct_url": "https://doi.org/10.1088/1748-0221/20/05/C05006",
      "correct_key": "kuzniakNewCandidatePolymeric2025"
    },
    {
      "line": 203,
      "type": "broken_link",
      "severity": "error",
      "url": "https://example.com/paper.pdf",
      "http_status": 404
    }
  ],
  "recommendations": [
    "Fix 1 project page URL to point to actual paper",
    "Update 2 citations with wrong BibTeX keys",
    "Verify 3 broken links"
  ]
}
```

### 2. `check_citation_url_quality`

**Purpose**: Validate a single citation URL

**Input**:
```json
{
  "url": "https://yukangcao.github.io/GS-VTON/",
  "citation_text": "GaussianVTON (Cao et al., 2024)"
}
```

**Output**:
```json
{
  "is_valid": false,
  "category": "project_page",
  "severity": "error",
  "issue": "GitHub Pages project site - not a paper URL",
  "suggestions": [
    {
      "url": "https://arxiv.org/abs/2410.05259",
      "source": "Project page analysis",
      "confidence": "high"
    }
  ]
}
```

### 3. `verify_zotero_match`

**Purpose**: Check if citation exists in Zotero and validate metadata

**Input**:
```json
{
  "url": "https://arxiv.org/abs/2410.05259",
  "citation_text": "Cao et al., 2024",
  "collection": "dpp-fashion"
}
```

**Output**:
```json
{
  "found_in_zotero": true,
  "better_bibtex_key": "caoGSVTONControllable3D2024",
  "metadata": {
    "authors": ["Yukang Cao", "..."],
    "title": "GS-VTON: Controllable 3D Virtual Try-on with Gaussian Splatting",
    "year": 2024,
    "source": "arXiv"
  },
  "validation": {
    "author_match": true,
    "year_match": true,
    "encoding_issues": []
  }
}
```

### 4. `check_link_health`

**Purpose**: Verify HTTP links are reachable

**Input**:
```json
{
  "urls": [
    "https://example.com/paper.pdf",
    "https://github.com/user/repo"
  ]
}
```

**Output**:
```json
{
  "results": [
    {
      "url": "https://example.com/paper.pdf",
      "status": 404,
      "reachable": false,
      "error": "Not Found"
    },
    {
      "url": "https://github.com/user/repo",
      "status": 200,
      "reachable": true
    }
  ]
}
```

### 5. `validate_bibtex_keys`

**Purpose**: Check if BibTeX keys match Better BibTeX format

**Input**:
```json
{
  "citations": [
    {
      "url": "https://arxiv.org/abs/2410.05259",
      "current_key": "cao2024a"
    }
  ],
  "collection": "dpp-fashion"
}
```

**Output**:
```json
{
  "mismatches": [
    {
      "url": "https://arxiv.org/abs/2410.05259",
      "current_key": "cao2024a",
      "correct_key": "caoGSVTONControllable3D2024",
      "source": "Zotero Better BibTeX"
    }
  ]
}
```

## Implementation Steps

### Phase 1: MCP Server Setup
- [ ] Create `mcp_servers/citation_quality/` directory
- [ ] Set up MCP server scaffold using `mcp` Python package
- [ ] Define tool schemas for all 5 tools
- [ ] Create server entry point `server.py`

### Phase 2: Tool Implementation
- [ ] Implement `audit_markdown_citations` (uses all other tools)
- [ ] Implement `check_citation_url_quality` (reuse validation logic)
- [ ] Implement `verify_zotero_match` (wrap CitationManager)
- [ ] Implement `check_link_health` (HTTP HEAD requests)
- [ ] Implement `validate_bibtex_keys` (Zotero API)

### Phase 3: Integration with Converter
- [ ] Add `--audit` flag to `md2latex` command
- [ ] MCP client integration in converter
- [ ] Call `audit_markdown_citations` before conversion
- [ ] Display audit results and pause for user confirmation
- [ ] Option to auto-fix certain issues (with user approval)

### Phase 4: Testing & Documentation
- [ ] Unit tests for each MCP tool
- [ ] Integration tests with real manuscripts
- [ ] MCP server usage documentation
- [ ] Update README with MCP server setup instructions

## File Structure

```
deep-biblio-tools/
├── mcp_servers/
│   └── citation_quality/
│       ├── __init__.py
│       ├── server.py              # MCP server entry point
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── audit.py           # audit_markdown_citations
│       │   ├── url_quality.py     # check_citation_url_quality
│       │   ├── zotero_match.py    # verify_zotero_match
│       │   ├── link_health.py     # check_link_health
│       │   └── bibtex_keys.py     # validate_bibtex_keys
│       └── utils/
│           ├── __init__.py
│           └── url_analyzer.py    # Shared URL analysis logic
├── src/
│   ├── cli.py                     # Add --audit flag here
│   └── converters/
│       └── md_to_latex/
│           └── converter.py       # Call MCP server if --audit
└── tests/
    └── mcp_servers/
        └── citation_quality/
            ├── test_audit.py
            ├── test_url_quality.py
            └── ...
```

## MCP Server Configuration

**Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`)**:
```json
{
  "mcpServers": {
    "citation-quality": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/petteri/Dropbox/github-personal/deep-biblio-tools",
        "run",
        "mcp-citation-quality"
      ]
    }
  }
}
```

**pyproject.toml update**:
```toml
[project.scripts]
mcp-citation-quality = "mcp_servers.citation_quality.server:main"
```

## Usage Examples

### Standalone in Claude Code:
```
User: "Check citation quality in fashion-cad-review-v3.md"
Claude: <uses audit_markdown_citations tool>
```

### Integrated with Converter:
```bash
uv run python -m src.cli md2latex fashion-cad-review-v3.md --audit

# Output:
# Running citation quality audit...
#
# AUDIT RESULTS:
# - 64 academic citations detected
# - 1 problematic URL found (project page)
# - 2 questionable URLs (company sites)
#
# ISSUES:
# Line 79: [GaussianVTON] - Project page instead of paper
#   Suggestion: https://arxiv.org/abs/2410.05259
#
# Continue with conversion? [y/N]
```

### Pre-commit Hook:
```bash
# .git/hooks/pre-commit
uv run mcp-citation-quality audit manuscript.md --fail-on-error
```

## Success Criteria

- [ ] MCP server runs and responds to tool calls
- [ ] All 5 tools implemented and tested
- [ ] Converter `--audit` flag works
- [ ] Audit catches the 9 problematic citations in test manuscripts
- [ ] Zero false positives on legitimate grey literature
- [ ] Documentation complete
- [ ] CI/CD integration working

## Timeline Estimate

- **Phase 1** (MCP Setup): 2-3 hours
- **Phase 2** (Tool Implementation): 4-6 hours
- **Phase 3** (Converter Integration): 2-3 hours
- **Phase 4** (Testing & Docs): 2-3 hours

**Total**: 10-15 hours of focused work

## Dependencies

**New packages needed**:
```toml
[project.dependencies]
mcp = "^1.0.0"  # MCP Python SDK
httpx = "^0.27.0"  # For link health checks (async HTTP)
```

## Notes

- Reuse existing `UnifiedCitationExtractor` - don't duplicate logic
- Keep MCP tools stateless - all state in Zotero/filesystem
- Provide both JSON output (for programmatic use) and pretty-printed (for CLI)
- Consider caching HTTP health checks to avoid rate limiting
- Make audit report exportable (JSON, Markdown, HTML)

## Future Enhancements

- Auto-fix mode: Automatically correct known issues with user approval
- Batch mode: Audit entire directories of manuscripts
- Dashboard: Web UI showing citation quality trends over time
- Smart suggestions: Use LLM to suggest correct paper URLs from project pages
- Integration with other reference managers (Mendeley, EndNote)
