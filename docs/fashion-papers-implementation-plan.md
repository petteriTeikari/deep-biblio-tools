# Fashion Papers Implementation Plan: Zotero MCP + E2E Testing

**Created**: 2025-10-27
**Context**: Testing 3 new fashion manuscripts with challenging citations
**Goal**: Zero (?) citations in PDFs + Standalone Zotero MCP server

---

## Executive Summary

We'll convert 3 fashion manuscripts to LaTeX/PDF for arXiv submission:
1. `fashion-lca-draft-v3.md` (Life Cycle Assessment)
2. `4dgs-fashion-comprehensive-v2.md` (4D Gaussian Splatting)
3. `fashion-cad-review-v3.md` (3D CAD Review)

**Challenge**: Many inline citations NOT in Zotero yet → will trigger (?) citations
**Validation**: E2E test suite MUST catch these and fail with clear error messages
**Architecture**: Extract Zotero operations into standalone MCP server for reusability

---

## Phase 1: Baseline Testing (Verify E2E Suite Works)

### Objective
Run E2E tests on new manuscripts to confirm they catch missing citations

### Manuscripts Analysis (From Reading)

**fashion-lca-draft-v3.md** (~100 citations):
- Pattern: `[Author (Year)](URL)` format
- Many arXiv links, some DOIs
- Topics: Sustainability, textile lifecycle, environmental impact
- **Expected issues**: Many citations likely NOT in your Zotero

**4dgs-fashion-comprehensive-v2.md** (~80 citations):
- Pattern: Mix of `[Author et al., Year](URL)` and `[Author (Year)](URL)`
- Heavy computer vision/graphics citations
- Topics: Gaussian splatting, NeRF, 3D reconstruction
- **Expected issues**: Specialized CV papers may not be in Zotero

**fashion-cad-review-v3.md** (~120 citations):
- Pattern: Inline citations with URLs
- Topics: CAD systems, fashion design tools, parametric modeling
- **Expected issues**: Industry papers, CAD vendor docs not in academic databases

### Test Execution Plan

```bash
# Step 1: Create real-world E2E tests for fashion papers
# tests/e2e/test_fashion_papers.py

pytest tests/e2e/test_fashion_papers.py -v --tb=short
```

### Expected Test Results (FIRST RUN)

**Prediction**: Tests will FAIL with many (?) citations

```
FAILED test_fashion_lca_pdf_quality - AssertionError: Found 45 unresolved citations (?)
FAILED test_fashion_4dgs_pdf_quality - AssertionError: Found 38 unresolved citations (?)
FAILED test_fashion_cad_pdf_quality - AssertionError: Found 52 unresolved citations (?)
```

**This is GOOD** - it proves our E2E suite catches the issues!

### Test Output Should Include

1. **Count of (?) citations**: Exact number
2. **List of missing citations**: First 10 with author/year/URL
3. **references.bib inspection**: Show "Unknown" or "Anonymous" entries
4. **PDF excerpt**: Show sample (?) citation in context
5. **Actionable next step**: "Add missing citations to Zotero collection"

---

## Phase 2: Zotero MCP Architecture Design

### Current State (Embedded in md2latex Converter)

```
src/converters/md_to_latex/converter.py
├── Citation extraction logic
├── Zotero API calls (pyzotero)
├── Auto-add missing citations
├── BibTeX generation
└── LaTeX compilation
```

**Problem**: Zotero operations tightly coupled to conversion pipeline

### Target State (MCP Server Architecture)

```
┌─────────────────────────────────────────────────────────┐
│                     MCP CLIENT                           │
│            (md2latex converter or CLI tool)              │
└─────────────────┬───────────────────────────────────────┘
                  │ MCP Protocol (stdio/SSE)
                  ▼
┌─────────────────────────────────────────────────────────┐
│                  ZOTERO MCP SERVER                       │
│                                                           │
│  Tools:                                                   │
│  - search_items(query) → List[ZoteroItem]               │
│  - get_item(item_id) → ZoteroItem                       │
│  - create_item(data) → item_id                          │
│  - add_to_collection(item_id, collection_id)            │
│  - export_bibtex(collection_id) → BibTeX string         │
│  - list_collections() → List[Collection]                │
│                                                           │
│  Resources:                                               │
│  - zotero://library/{id}                                 │
│  - zotero://collection/{id}                              │
│                                                           │
└─────────────────┬───────────────────────────────────────┘
                  │ Zotero Web API (HTTPS)
                  ▼
┌─────────────────────────────────────────────────────────┐
│                   ZOTERO WEB API                         │
│              (api.zotero.org/users/{id})                 │
└─────────────────────────────────────────────────────────┘
```

### Design Decisions

#### Decision 1: Standalone MCP vs Forking Existing

**Option A**: Use existing `54yyyu/zotero-mcp`
- ✅ Pro: Already implements MCP protocol
- ✅ Pro: Has basic search/get/create operations
- ❌ Con: May not have BibTeX export (critical for us)
- ❌ Con: Unknown code quality, maintainability
- ❌ Con: May not support collections properly

**Option B**: Fork and extend `54yyyu/zotero-mcp`
- ✅ Pro: Start with working MCP implementation
- ✅ Pro: Add missing features (BibTeX export, collection management)
- ❌ Con: Need to understand their codebase first
- ❌ Con: Maintenance burden if upstream changes

**Option C**: Build our own MCP server from scratch
- ✅ Pro: Full control over features and architecture
- ✅ Pro: Optimized for our exact use case (bibliography management)
- ✅ Pro: Clean codebase that follows CLAUDE.md conventions
- ❌ Con: More initial development time
- ❌ Con: Need to implement MCP protocol ourselves

**RECOMMENDATION**: **Option C - Build from Scratch**

**Reasoning**:
1. **Specific requirements**: We need BibTeX export, collection management, auto-add missing citations - may not exist in existing servers
2. **Code quality**: We can follow CLAUDE.md from start (no regex, AST parsers, deterministic behavior)
3. **Learning opportunity**: Understanding MCP protocol deeply will help with future MCP development
4. **MCP SDK available**: Anthropic provides `@modelcontextprotocol/sdk` (TypeScript) and Python MCP SDK
5. **Not that complex**: MCP servers are surprisingly simple - mostly thin wrappers around pyzotero with standardized input/output

#### Decision 2: Language Choice (Python vs TypeScript)

**Python**:
- ✅ Pro: `pyzotero` library already mature
- ✅ Pro: Matches rest of deep-biblio-tools stack
- ✅ Pro: Team familiar with Python
- ❌ Con: Python MCP SDK less documented than TypeScript

**TypeScript**:
- ✅ Pro: Official MCP SDK from Anthropic
- ✅ Pro: Better async/await for API calls
- ❌ Con: Would need `zotero-api-client` npm package (less mature)
- ❌ Con: Separate deployment from main Python codebase

**RECOMMENDATION**: **Python**

**Reasoning**: Code reuse with existing `src/integrations/zotero_integration.py`, team expertise, ecosystem match

#### Decision 3: Deployment Model

**Option A**: Separate repository `deep-biblio-zotero-mcp`
- ✅ Pro: Clean separation of concerns
- ✅ Pro: Can be used by other projects
- ❌ Con: Versioning complexity
- ❌ Con: Deployment coordination

**Option B**: Subdirectory in deep-biblio-tools `/mcp-servers/zotero/`
- ✅ Pro: Monorepo benefits (shared dependencies, single CI/CD)
- ✅ Pro: Easy to test integration with md2latex converter
- ❌ Con: Repo size grows

**Option C**: External package published to PyPI
- ✅ Pro: Proper packaging and distribution
- ✅ Pro: Version management via pip
- ❌ Con: Overkill for single-user tool (for now)

**RECOMMENDATION**: **Option B - Monorepo Subdirectory**

**Structure**:
```
deep-biblio-tools/
├── src/                  # Existing converters, CLI
├── tests/                # Existing tests
├── mcp-servers/          # NEW: MCP servers
│   └── zotero/
│       ├── __main__.py   # MCP server entry point
│       ├── server.py     # MCP protocol handling
│       ├── tools.py      # Zotero operations (search, create, export)
│       ├── resources.py  # Zotero resources (library, collections)
│       └── README.md     # Server documentation
├── pyproject.toml        # Add MCP dependencies
└── README.md             # Document MCP server usage
```

---

## Phase 3: Zotero MCP Server Implementation

### MCP Server Architecture

```python
# mcp-servers/zotero/__main__.py
"""
Zotero MCP Server - Standalone server for Zotero operations

Usage:
    python -m mcp_servers.zotero

Configuration (via environment variables):
    ZOTERO_API_KEY=your_key
    ZOTERO_LIBRARY_ID=your_id
    ZOTERO_LIBRARY_TYPE=user
"""

from mcp import Server, Tool, Resource
from mcp.server.stdio import stdio_server
import asyncio
from .tools import ZoteroTools
from .resources import ZoteroResources

async def main():
    server = Server("zotero-mcp")
    zotero_tools = ZoteroTools()
    zotero_resources = ZoteroResources()

    # Register tools
    server.add_tool(zotero_tools.search_items)
    server.add_tool(zotero_tools.get_item)
    server.add_tool(zotero_tools.create_item)
    server.add_tool(zotero_tools.add_to_collection)
    server.add_tool(zotero_tools.export_bibtex)
    server.add_tool(zotero_tools.list_collections)

    # Register resources
    server.add_resource_provider(zotero_resources)

    # Run server
    await stdio_server(server)

if __name__ == "__main__":
    asyncio.run(main())
```

### Core Tools Implementation

```python
# mcp-servers/zotero/tools.py
"""Zotero MCP Tools - Operations exposed via MCP protocol"""

from pyzotero import zotero
import os
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class ZoteroTools:
    """Zotero operations accessible via MCP"""

    def __init__(self):
        self.api_key = os.getenv("ZOTERO_API_KEY")
        self.library_id = os.getenv("ZOTERO_LIBRARY_ID")
        self.library_type = os.getenv("ZOTERO_LIBRARY_TYPE", "user")

        if not self.api_key or not self.library_id:
            raise ValueError("ZOTERO_API_KEY and ZOTERO_LIBRARY_ID required")

        self.zot = zotero.Zotero(
            self.library_id,
            self.library_type,
            self.api_key
        )

    async def search_items(self, query: str, limit: int = 10) -> List[Dict]:
        """Search Zotero library for items matching query

        Args:
            query: Search query (title, author, year)
            limit: Max results to return

        Returns:
            List of matching items with metadata
        """
        try:
            results = self.zot.items(q=query, limit=limit)
            return [self._simplify_item(item) for item in results]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    async def get_item(self, item_id: str) -> Optional[Dict]:
        """Get full metadata for specific Zotero item"""
        try:
            item = self.zot.item(item_id)
            return item
        except Exception as e:
            logger.error(f"Get item {item_id} failed: {e}")
            return None

    async def create_item(self, data: Dict) -> Optional[str]:
        """Create new item in Zotero library

        Args:
            data: Item metadata (title, creators, date, itemType, etc.)

        Returns:
            New item ID or None if failed
        """
        try:
            template = self.zot.item_template(data.get("itemType", "journalArticle"))
            template.update(data)

            resp = self.zot.create_items([template])
            if resp["success"]:
                return resp["success"]["0"]
            else:
                logger.error(f"Create failed: {resp}")
                return None
        except Exception as e:
            logger.error(f"Create item failed: {e}")
            return None

    async def add_to_collection(self, item_id: str, collection_id: str) -> bool:
        """Add item to specific collection"""
        try:
            self.zot.addto_collection(collection_id, self.zot.item(item_id))
            return True
        except Exception as e:
            logger.error(f"Add to collection failed: {e}")
            return False

    async def export_bibtex(self, collection_id: Optional[str] = None) -> str:
        """Export collection (or entire library) to BibTeX format

        Args:
            collection_id: Collection to export (None = entire library)

        Returns:
            BibTeX string
        """
        try:
            if collection_id:
                items = self.zot.collection_items(collection_id)
            else:
                items = self.zot.items()

            # Use Zotero's native BibTeX export
            bibtex = self.zot.item(items, format='bibtex')
            return bibtex
        except Exception as e:
            logger.error(f"BibTeX export failed: {e}")
            return ""

    async def list_collections(self) -> List[Dict]:
        """List all collections in library"""
        try:
            collections = self.zot.collections()
            return [
                {
                    "id": col["key"],
                    "name": col["data"]["name"],
                    "parentCollection": col["data"].get("parentCollection"),
                    "numItems": col["meta"]["numItems"]
                }
                for col in collections
            ]
        except Exception as e:
            logger.error(f"List collections failed: {e}")
            return []

    def _simplify_item(self, item: Dict) -> Dict:
        """Simplify Zotero item for MCP response"""
        data = item.get("data", {})
        return {
            "id": item.get("key"),
            "title": data.get("title"),
            "creators": data.get("creators", []),
            "date": data.get("date"),
            "itemType": data.get("itemType"),
            "doi": data.get("DOI"),
            "url": data.get("url")
        }
```

### Integration with md2latex Converter

```python
# src/converters/md_to_latex/converter.py (MODIFIED)

from mcp import Client
from mcp.client.stdio import stdio_client

class MarkdownToLatexConverter:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.mcp_client = None  # Will connect to Zotero MCP server

    async def _init_zotero_mcp(self):
        """Initialize connection to Zotero MCP server"""
        self.mcp_client = await stdio_client(
            command=["python", "-m", "mcp_servers.zotero"]
        )

    async def _fetch_zotero_bibtex(self, collection_name: str) -> str:
        """Fetch BibTeX from Zotero via MCP"""
        if not self.mcp_client:
            await self._init_zotero_mcp()

        # List collections to find ID
        collections = await self.mcp_client.call_tool(
            "list_collections",
            {}
        )

        collection_id = None
        for col in collections:
            if col["name"] == collection_name:
                collection_id = col["id"]
                break

        if not collection_id:
            raise ValueError(f"Collection '{collection_name}' not found")

        # Export BibTeX
        bibtex = await self.mcp_client.call_tool(
            "export_bibtex",
            {"collection_id": collection_id}
        )

        return bibtex

    async def _add_missing_citation_to_zotero(self, citation_data: Dict) -> bool:
        """Add missing citation to Zotero via MCP"""
        if not self.mcp_client:
            await self._init_zotero_mcp()

        item_id = await self.mcp_client.call_tool(
            "create_item",
            {"data": citation_data}
        )

        if item_id:
            # Add to collection
            await self.mcp_client.call_tool(
                "add_to_collection",
                {"item_id": item_id, "collection_id": self.collection_id}
            )
            return True
        return False
```

### Fallback Strategy (If MCP Server Has Issues)

**Plan B**: Direct pyzotero integration (existing approach)

```python
# If MCP server fails to start or has issues, fall back to direct pyzotero

try:
    await self._init_zotero_mcp()
except Exception as e:
    logger.warning(f"MCP server unavailable, using direct Zotero API: {e}")
    self.use_direct_zotero = True
```

**Benefit**: MCP is an enhancement, not a dependency. If it doesn't work, we still have working conversion.

---

## Phase 4: Testing Strategy

### E2E Test Suite Structure

```python
# tests/e2e/test_fashion_papers.py
"""
E2E tests for fashion manuscript conversions

Tests the complete MD→LaTeX→PDF pipeline with real-world challenging manuscripts.
"""

import pytest
from pathlib import Path
from src.converters.md_to_latex import MarkdownToLatexConverter
from tests.e2e.helpers_pdf import extract_text_from_pdf

FASHION_PAPERS = [
    {
        "name": "fashion-lca",
        "path": Path("/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/fashion_LCA/fashion-lca-draft-v3.md"),
        "expected_citations": 100  # Approximate
    },
    {
        "name": "fashion-4dgs",
        "path": Path("/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/fashion_4DGS/4dgs-fashion-comprehensive-v2.md"),
        "expected_citations": 80
    },
    {
        "name": "fashion-cad",
        "path": Path("/Users/petteri/Dropbox/LABs/open-mode/github/om-knowledge-base/publications/fashion_3D_CAD/fashion-cad-review-v3.md"),
        "expected_citations": 120
    }
]

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.parametrize("paper", FASHION_PAPERS, ids=lambda p: p["name"])
class TestFashionPaperConversions:
    """Test conversions of fashion manuscripts with challenging citations"""

    def test_zero_unresolved_citations(self, paper):
        """CRITICAL: PDF must have ZERO (?) citation markers"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_dir = Path(tmpdir)
            output_dir = paper["path"].parent / "output"

            # Convert
            converter = MarkdownToLatexConverter(output_dir=output_dir)
            converter.convert(markdown_file=paper["path"], verbose=False)

            # Get PDF path
            pdf_file = output_dir / f"{paper['path'].stem}.pdf"
            assert pdf_file.exists(), f"PDF not generated for {paper['name']}"

            # Extract text
            pdf_text = extract_text_from_pdf(pdf_file)

            # ZERO TOLERANCE checks
            unresolved_count = pdf_text.count("(?)")
            unknown_count = pdf_text.count("(Unknown)")
            anonymous_count = pdf_text.count("(Anonymous)")

            # Detailed error message
            if unresolved_count > 0 or unknown_count > 0 or anonymous_count > 0:
                # Extract first 10 problem citations for debugging
                lines = pdf_text.split("\n")
                problem_lines = [
                    line for line in lines
                    if "(?)" in line or "(Unknown)" in line or "(Anonymous)" in line
                ][:10]

                error_msg = f"""
{paper['name']} has citation resolution failures:
  - Unresolved (?): {unresolved_count}
  - Unknown authors: {unknown_count}
  - Anonymous authors: {anonymous_count}

First 10 problematic citations:
{chr(10).join(f'  {i+1}. {line.strip()}' for i, line in enumerate(problem_lines))}

ACTION REQUIRED:
1. Check references.bib for "Unknown" or "Anonymous" entries
2. Add missing citations to Zotero collection
3. Re-run conversion
"""
                pytest.fail(error_msg)

    def test_bibliography_has_author_names(self, paper):
        """Verify references section has actual author names"""
        # Similar to above but checks bibliography section specifically
        pass

    def test_citation_count_reasonable(self, paper):
        """Verify citation count matches expected range"""
        # Count citations in PDF and compare to expected_citations ±20%
        pass
```

### Test Execution Workflow

```bash
# Phase 4.1: Run tests expecting failures (baseline)
pytest tests/e2e/test_fashion_papers.py -v --tb=short > test-results-baseline.txt

# Phase 4.2: Analyze failures, identify missing citations
python scripts/analyze_missing_citations.py test-results-baseline.txt

# Phase 4.3: Add missing citations to Zotero (via MCP or manually)
python scripts/populate_zotero_from_failed_tests.py

# Phase 4.4: Re-run tests expecting success
pytest tests/e2e/test_fashion_papers.py -v --tb=short > test-results-final.txt

# Phase 4.5: Compare results
diff test-results-baseline.txt test-results-final.txt
```

---

## Phase 5: Update Documentation

### Update PLAYWRIGHT-TESTING-GUIDE.md

Add new section at end of file:

```markdown
## Section 8: Testing Academic Paper Conversions with Claude Code

### For Sofiia (Visualization Engineering Intern)

This section shows a DIFFERENT use case for automated testing: validating academic paper conversions for arXiv submission.

#### The Challenge

You're given 3 fashion manuscripts with ~300 total citations. Your task:
1. Convert markdown to LaTeX to PDF
2. Ensure ZERO unresolved citations (no "(?)" markers)
3. Verify all citations have proper author names
4. Check that generated PDFs meet arXiv submission standards

**Without automated tests**: You'd manually open each PDF, search for "(?)", count citations, compare to references section. Time-consuming and error-prone for 300+ citations.

**With automated E2E tests**: Run `pytest tests/e2e/test_fashion_papers.py` and get instant verification.

#### How to Request These Tests from Claude Code

**Template**:
```
"Write end-to-end tests for converting {MANUSCRIPTS} to PDF that verify:
1. Zero unresolved citations (no '(?)', '(Unknown)', or '(Anonymous)')
2. All citations in text have corresponding bibliography entries
3. PDF has proper structure (title, abstract, sections, references)
4. Hyperlinks are preserved and colored correctly
5. Special characters (mathematical symbols, accented letters) render properly

For each test failure, provide:
- Exact count of problematic citations
- First 10 examples with context
- Actionable fix (e.g., 'Add Smith (2020) to Zotero collection')
- Screenshot of PDF showing issue"
```

**Example request**:
```
"I have 3 fashion manuscripts (LCA, 4DGS, CAD) with ~100 citations each.
Write E2E tests that:
1. Convert each markdown file to PDF
2. Extract text from PDF using PyMuPDF
3. Count occurrences of '(?)', '(Unknown)', '(Anonymous)'
4. Verify ≥90% of citations are resolved (allow some missing for first run)
5. Generate report showing which citations need to be added to Zotero

Make tests parameterized so I can add more manuscripts easily."
```

#### Understanding Test Output

**When tests fail** (initial run with missing citations):
```bash
$ pytest tests/e2e/test_fashion_papers.py -v

FAILED test_fashion_lca_zero_unresolved_citations
  fashion-lca has citation resolution failures:
    - Unresolved (?): 45
    - Unknown authors: 12
    - Anonymous authors: 3

  First 10 problematic citations:
    1. "...environmental impact (?)" at line 234
    2. "...textile recycling (Unknown, 2020)" at line 456
    3. "...sustainability metrics (?)..." at line 789
    ...

  ACTION REQUIRED:
  1. Check references.bib for "Unknown" or "Anonymous" entries
  2. Add missing citations to Zotero collection
  3. Re-run conversion
```

**After fixing** (citations added to Zotero):
```bash
$ pytest tests/e2e/test_fashion_papers.py -v

PASSED test_fashion_lca_zero_unresolved_citations (12.3s)
PASSED test_fashion_4dgs_zero_unresolved_citations (10.1s)
PASSED test_fashion_cad_zero_unresolved_citations (14.7s)

3 passed in 37.1s
```

#### Key Differences from Playwright Visual Testing

| Aspect | Playwright (Figures) | pytest (Paper Conversions) |
|--------|---------------------|---------------------------|
| **What's tested** | Visual layout, overlaps, spacing | Citation resolution, content accuracy |
| **Tool** | Playwright (browser automation) | pytest + PyMuPDF (PDF parsing) |
| **Input** | HTML/SVG in browser | Markdown files |
| **Output check** | Bounding boxes, screenshots | Text extraction, pattern matching |
| **Failure mode** | Text overlaps graphic (28%) | Citation unresolved (?)(45) |
| **Fix** | Adjust layout code | Add citations to Zotero |

#### When to Use Each Testing Approach

**Use Playwright** for:
- Data visualizations (charts, diagrams)
- Web UI components
- Layout consistency
- Visual regression testing

**Use pytest E2E** for:
- Document conversions (MD→LaTeX→PDF)
- Content validation (citations, references)
- Pipeline testing (multi-step workflows)
- Academic paper quality assurance

#### Practice Exercise

Try requesting this from Claude Code:

```
"Write tests for my research paper 'deep-learning-survey.md' that verify:
1. All 50 expected citations are resolved in the PDF
2. No (?), (Unknown), or (Anonymous) markers anywhere
3. References section lists all 50 papers with full metadata
4. Each cited author appears in the references
5. DOI links are clickable and correctly formatted

If tests fail, show me:
- Which citations are missing from Zotero
- Which DOIs failed to resolve
- A summary report I can use to fix the issues"
```

Claude Code will create pytest tests similar to the fashion papers example above!

---

**Key Takeaway**: Same principles (automated quality checks, clear failure messages, actionable fixes) apply to DIFFERENT domains (visual testing vs document conversion). Learn to describe WHAT to test, and Claude Code implements HOW to test it.
```

---

## Implementation Timeline

### Week 1: Baseline Testing (2-3 days)
- Day 1: Create `test_fashion_papers.py` tests
- Day 2: Run tests, document failures (expect many)
- Day 3: Analyze failure patterns, identify missing citation types

### Week 2: Zotero MCP Server (4-5 days)
- Day 1-2: Implement MCP server structure and core tools
- Day 3: Test MCP server standalone (without md2latex integration)
- Day 4: Integrate MCP client into md2latex converter
- Day 5: Test integration, compare with direct pyzotero approach

### Week 3: Citation Resolution (3-4 days)
- Day 1-2: Add missing citations to Zotero (manual or via MCP)
- Day 3: Re-run conversion tests
- Day 4: Verify ZERO (?) citations in all 3 papers

### Week 4: Documentation & Polish (2-3 days)
- Day 1: Update PLAYWRIGHT-TESTING-GUIDE.md
- Day 2: Write MCP server README
- Day 3: Create example scripts for common workflows

**Total**: ~12-15 days for full implementation

---

## Risk Mitigation & Fallback Plans

### Risk 1: MCP Server Too Complex

**Symptoms**: MCP protocol debugging takes >3 days, unclear errors

**Fallback**: Skip MCP for now, use direct pyzotero integration
**Impact**: Still get working conversion, defer MCP to later sprint
**Decision point**: End of Week 2, Day 3

### Risk 2: Too Many Missing Citations

**Symptoms**: >100 missing citations, manual addition too tedious

**Fallback A**: Focus on 1 paper (fashion-lca) first, defer others
**Fallback B**: Use auto-add feature more aggressively (may add low-quality entries)
**Fallback C**: Create batch import script from DOI list
**Decision point**: Week 3, Day 1

### Risk 3: Citation Extraction Fails for New Formats

**Symptoms**: E2E tests fail because citation patterns not recognized

**Fallback**: Extend citation extractor to handle new patterns
**Impact**: +1-2 days, but improves robustness
**Decision point**: Week 1, Day 2 (during failure analysis)

### Risk 4: PDF Generation Breaks with Large Bibliographies

**Symptoms**: LaTeX compilation fails with >100 references

**Fallback**: Split bibliography across multiple .bib files
**Impact**: Requires LaTeX template changes
**Decision point**: Week 3, Day 3

---

## Success Criteria

### Must Have (Ship-Blocking)
1. ✅ All 3 fashion papers convert to PDF
2. ✅ ZERO (?) citations in any PDF
3. ✅ E2E tests pass for all 3 papers
4. ✅ Each paper has `output/` folder with .tex, .pdf, references.bib

### Should Have (High Priority)
1. ✅ Zotero MCP server functional and documented
2. ✅ PLAYWRIGHT-TESTING-GUIDE.md updated with examples
3. ✅ Test output shows clear actionable errors
4. ✅ Conversion runs in <5 minutes per paper

### Nice to Have (Future Work)
1. ⚠️ MCP server published as separate package
2. ⚠️ Batch conversion script for multiple papers
3. ⚠️ Auto-add citations via DOI lookup without manual review
4. ⚠️ Visual diff tool for comparing before/after PDFs

---

## Questions for User

1. **Zotero collection names**: Are these papers in separate collections or all in `dpp-fashion`?

2. **Citation tolerance**: Should we aim for 100% resolution or allow some (?) citations for obscure references?

3. **MCP priority**: Is Zotero MCP server a must-have or nice-to-have? Can we defer to later sprint if complex?

4. **Timeline**: Is 2-3 weeks reasonable, or do you need results faster? (Can focus on 1 paper first)

5. **Automation level**: Should auto-add feature be aggressive (add everything from DOI) or conservative (only high-confidence matches)?

---

## Comparison with Existing MCP Servers

### 54yyyu/zotero-mcp Analysis

**What it provides**:
- Basic MCP server structure
- Search, get, create item operations
- TypeScript implementation

**What's missing for our use case**:
- No BibTeX export
- No collection management
- No batch operations
- Unknown code quality

**Decision**: Build our own in Python with exact features we need

### Zotero Forums Discussion

From https://forums.zotero.org/discussion/124860/:
- Zotero team aware of MCP
- No official MCP server planned yet
- Community implementations emerging
- API is stable, MCP is good fit

**Implication**: Safe to build our own, won't conflict with future official server

---

## Next Steps (Immediate Actions)

1. **Create E2E test file** (`tests/e2e/test_fashion_papers.py`)
2. **Run baseline tests** on all 3 papers
3. **Analyze failures**, document missing citation patterns
4. **Review this plan** with user, adjust priorities
5. **Choose MCP implementation strategy** (build vs fork vs skip)
6. **Start Week 1 work** (baseline testing phase)

---

**Document Status**: DRAFT - Awaiting user feedback and decisions on open questions
**Next Review**: After baseline test results available
**Owner**: Claude Code + User collaboration
