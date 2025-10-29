# Markdown-to-LaTeX Vision Document

**Created**: 2025-10-29
**Branch**: `fix/verify-md-to-latex-conversion`
**Status**: Critical State - 372 Broken Citations

---

## Vision Statement

**This branch is a total failure if we cannot get a PDF with ZERO (?) citations and ZERO Unknown citations.**

The markdown-to-latex conversion system must produce publication-ready PDFs from LLM-generated manuscripts with **perfect citation resolution**. Every citation must show proper author names and years. No shortcuts. No temporary keys for papers that should be in Zotero. No manual intervention required.

### Success Criteria (Zero Tolerance)

1. ✅ PDF generates without LaTeX errors
2. ✅ PDF has ZERO `(?)` citations
3. ✅ PDF has ZERO `(Unknown)` or `(Anonymous)` citations
4. ✅ All citations show proper author names and years
5. ✅ `references.bib` has ZERO "Unknown" entries
6. ✅ LaTeX log has ZERO compilation errors
7. ✅ BibTeX log has ZERO fatal errors (warnings OK)

**Anything less is complete failure.**

---

## Current State (CRITICAL FAILURE)

### The Numbers

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| **Total citations** | 381 | 381 | ✅ |
| **Temp citations** | 122 (32%) | 0 (0%) | ❌ -122 |
| **From Zotero** | 259 (68%) | 381 (100%) | ❌ -122 |
| **(?) marks in PDF** | **372** | **0** | ❌ **-372** |
| **Truncated authors** | 70 | 0 | ❌ -70 |

### What's Broken

1. **122 papers NOT in Zotero library** (32% failure rate)
   - These create Temp citations
   - Each Temp citation causes 2-4 (?) marks in PDF
   - Cannot be resolved without adding papers to Zotero

2. **70 papers have truncated authors** ("Author and others")
   - Zotero exports show "Duan and others" instead of full author list
   - This is Zotero Better BibTeX export settings, NOT our code
   - Author enrichment implemented but needs proper Zotero data

3. **No automatic citation addition is running**
   - Script exists: `scripts/add_missing_to_zotero.py`
   - NOT being called during conversion
   - User has to run manually (unacceptable)

### What Works

1. ✅ **Author enrichment implemented** (Phase 5)
   - Fetches complete authors from CrossRef/arXiv APIs
   - 21/21 unit tests passing
   - 100% success rate on test entries
   - Ready to fix truncated authors once Zotero data is correct

2. ✅ **AST-based citation parsing** (Phase 3)
   - No regex usage anywhere
   - Robust handling of special characters
   - Proper URL normalization

3. ✅ **Comprehensive test suite**
   - 64/64 unit tests passing
   - Golden dataset for regression testing
   - MCP tools for citation quality checking

4. ✅ **Zotero credentials configured**
   - `.env` file exists with API key
   - Write access enabled
   - Integration tested and working

---

## Root Cause Analysis

### Why Are There 372 (?) Citations?

**Direct Cause**: 122 papers not in Zotero library → 122 Temp citations → 372 (?) marks

**Math**: 122 Temp citations × ~3 average references per paper = ~366 (?) marks ≈ 372 actual

**Why Not Auto-Added?**
- Automatic addition script exists but is NOT integrated into conversion pipeline
- User must run manually after conversion
- This violates the "zero manual intervention" principle

### Why Are Authors Truncated?

**Direct Cause**: Zotero Better BibTeX export settings truncate to "First Author and others"

**Example**:
```bibtex
@misc{duan_uprop_2025,
  author = {Duan and others},  # Should be: Duan, Jinhao and Diffenderfer, James and ...
  title = {UProp: Uncertainty-Aware Prompt Selection},
  year = {2025},
  doi = {10.48550/arXiv.2506.17419},
}
```

**Why Not Fixed?**
- Author enrichment implemented but ran without Zotero credentials in test
- Even with credentials, can only fix papers that ARE in library
- Cannot fix the 122 missing papers

---

## Architecture Overview

### The Pipeline (8 Steps)

```
1. Read Markdown (.md file)
   ↓
2. Extract Citations ([Author (Year)](URL) format)
   ↓
3. Match Against Zotero Library (via Web API)
   ↓  [IF NOT FOUND]
   ↓→ Auto-Add to Zotero (fetch metadata from CrossRef/arXiv)
   ↓  [ALWAYS]
   ↓
4. Enrich Authors (fix "Author and others" from APIs)
   ↓
5. Generate BibTeX Keys (Better BibTeX format)
   ↓
6. Replace Markdown Links → LaTeX \citep{} Commands
   ↓
7. Generate references.bib File
   ↓
8. Compile LaTeX → PDF
```

### Key Design Principles

1. **NO REGEX for structured parsing**
   - ✅ `markdown-it-py` for Markdown AST
   - ✅ `pylatexenc` for LaTeX AST
   - ✅ `bibtexparser` for BibTeX AST

2. **Zotero Web API = Single Source of Truth**
   - ❌ NO manual exports (.json, .bib files)
   - ✅ ALWAYS fetch fresh from API
   - ✅ Auto-add missing citations to Zotero

3. **Deterministic Behavior**
   - Same input → Same output (always)
   - All API responses cached
   - Audit trails for every decision

4. **Zero Manual Intervention**
   - User should NEVER have to manually do something
   - Everything automatic
   - Never lose .env file

---

## Complete Tool Inventory

### MCP Servers (Behind MCP Interface)

Located in `/mcp-servers/`

#### 1. **deep-biblio** (`mcp-servers/deep-biblio/`)
**Purpose**: Full citation management pipeline
**Tools Provided**:
- `convert-with-zotero-api.py` - Main conversion with Zotero integration
- `add-missing-to-zotero.py` - Add citations not found in library
- `generate-missing-report.py` - Report on missing citations
- `get-zotero-info.py` - Query Zotero library info
- `check_status.py` - Check pipeline status

**Status**: Production-ready, actively used

#### 2. **citation_quality** (`mcp-servers/citation_quality/`)
**Purpose**: Citation quality auditing
**Tools Provided**:
- `audit.py` - Comprehensive citation audit
- `url_quality.py` - Check citation URL quality
- `zotero_match.py` - Verify citations match Zotero
- `link_health.py` - Check HTTP link health
- `bibtex_keys.py` - Validate BibTeX key format

**Status**: Fully implemented, 100% test coverage

#### 3. **zotero** (`mcp-servers/zotero/`)
**Purpose**: Direct Zotero operations
**Status**: Basic implementation

### Python Scripts (Core Conversion)

Located in `/src/converters/md_to_latex/`

#### Core Modules

1. **`converter.py`** (1,200+ lines)
   - Main conversion orchestration
   - Markdown → LaTeX → PDF pipeline
   - Integrates all components
   - **Critical**: This is where auto-add should be triggered

2. **`citation_manager.py`** (1,500+ lines)
   - Citation extraction from markdown
   - Zotero library matching
   - BibTeX generation
   - **Contains**: `_handle_missing_citation()` method
   - **Missing**: Automatic trigger of auto-add

3. **`citation_matcher.py`** (500+ lines)
   - Zotero API integration
   - `add_to_zotero_library()` method
   - **Status**: Implemented but not wired up in converter

4. **`author_enrichment.py`** (400+ lines)
   - Fetches complete authors from CrossRef/arXiv
   - Fixes "Author and others" truncation
   - Caching for performance
   - **Status**: Implemented, tested, working

5. **`latex_generator.py`** (300+ lines)
   - LaTeX template generation
   - Bibliography style handling
   - Concept box formatting

6. **`zotero_integration.py`** (200+ lines)
   - Load bibliography from Zotero API
   - Better BibTeX key extraction
   - **Line 185-188**: Calls author enrichment

### Python Scripts (Validation & Fixes)

Located in `/scripts/`

#### Citation Management

1. **`add_missing_to_zotero.py`** ⭐ **KEY SCRIPT**
   - Adds citations not in Zotero library
   - Fetches metadata from DOI/arXiv
   - Creates proper Zotero entries
   - **Issue**: Not called automatically during conversion

2. **`add_unknown_citations_to_zotero.py`**
   - Alternative implementation
   - Similar functionality
   - Slightly different approach

3. **`add_remaining_dois.py`**
   - Adds citations with valid DOIs
   - Batch processing

#### Validation Scripts

4. **`validate_bib_source.py`** ⭐ **KEY VALIDATION**
   - Validates references.bib quality
   - Checks for incomplete authors
   - Checks for missing metadata
   - Reports by severity

5. **`check_bibliography_quality.py`**
   - Comprehensive quality checks
   - BibTeX format validation

6. **`extract_incomplete_authors.py`**
   - Identifies truncated author lists
   - Generates report for manual fixing

#### Analysis Scripts

7. **`analyze_citation_mismatches.py`**
   - Finds mismatches between citations and bibliography

8. **`analyze_zotero_json.py`**
   - Analyzes Zotero export quality

9. **`audit_zotero_collection.py`**
   - Audits Zotero collection completeness

### Python Scripts (Utilities)

Located in `/src/utils/`

1. **`url_utils.py`** - URL normalization
2. **`zotero_client.py`** - Zotero API wrapper
3. **`doi_utils.py`** - DOI extraction and validation
4. **`bibtex_utils.py`** - BibTeX parsing utilities

### Shell Scripts

Located in `/scripts/` and `/tools/paper-processor/`

1. **`setup-claude-hooks.sh`** - Pre-commit hook setup
2. **`setup-regex-enforcement.sh`** - Enforce no-regex policy
3. **`run_zotero_cleanup.sh`** - Zotero library cleanup
4. **`process-biblio-theme-folder.sh`** - Batch bibliography processing
5. **`run-regression-test.sh`** - Run full test suite
6. **`run-batch-summarization.sh`** - Batch paper summarization

### Test Suite

Located in `/tests/`

#### Unit Tests (64 total, all passing ✅)

1. **`test_author_enrichment.py`** (21 tests)
   - Detection tests: "and others", "et al"
   - Extraction tests: DOI, arXiv ID
   - CrossRef/arXiv API tests
   - Enrichment integration tests

2. **`test_citation_manager_auto_add.py`** (22 tests)
   - DOI validation and caching
   - Missing citation handling
   - Policy enforcement
   - Error reporting

3. **`test_citation_manager.py`** (12 tests)
   - Citation extraction
   - Duplicate key handling
   - Citation replacement

4. **`test_author_validation.py`** (9 tests)
   - BibTeX author counting
   - Incomplete author detection
   - DOI metadata validation

#### Integration Tests

5. **`test_better_bibtex_conversion.py`**
   - Full conversion with Better BibTeX keys
   - Regression testing

6. **`test_golden_dataset.py`**
   - Golden dataset for deterministic testing
   - Frozen bibliography snapshots

---

## Documented Work Sessions

### Phase Reports

1. **Phase 3-5 Implementation** (`docs/retrospectives/phase3-5-implementation-report.md`)
   - AST-based citation replacement
   - Fixed special character handling
   - URL normalization
   - Status: ✅ Complete

2. **Phase 4 Integration Test** (`docs/retrospectives/phase-4-integration-test-results.md`)
   - Tested on mcp-draft-refined-v4.md
   - Identified Zotero data quality issues
   - Found 70 truncated authors
   - Status: ✅ Complete - Root cause identified

3. **Phase 5 Author Enrichment** (`docs/retrospectives/phase-5-author-enrichment-solution.md`)
   - Implemented AuthorEnricher module
   - CrossRef/arXiv API integration
   - 21/21 tests passing
   - Status: ✅ Complete - Ready to use

4. **Citation Pipeline Auto-Add** (`docs/retrospectives/citation-pipeline-auto-add-implementation.md`)
   - DOI validation
   - Auto-add integration points
   - Policy enforcement
   - Status: ✅ Implemented, ⚠️ Not integrated into pipeline

### Planning Documents

5. **Comprehensive Completion Plan** (`docs/planning/comprehensive-completion-plan.md`)
   - 4-file conversion goal
   - Diagnostic strategy
   - Success criteria
   - 937 lines, very comprehensive

6. **MCP Citation Quality Plan** (`docs/planning/mcp-citation-quality-plan.md`)
   - MCP server architecture
   - Citation quality tools
   - Usage scenarios

7. **Systematic Fix Plan** (`docs/planning/systematic-fix-plan.md`)
   - Multi-hypothesis diagnostic approach
   - Step-by-step debugging strategy

### Architecture Documentation

8. **Architecture Overview** (`docs/architecture/architecture.md`)
   - Four-component ecosystem
   - Repository separation
   - Integration patterns

9. **Better BibTeX Key Strategy** (`docs/better-bibtex-key-strategy.md`)
   - Key format specification
   - Validation requirements

10. **Deterministic Citation System** (`docs/architecture/deterministic-citation-system.md`)
    - Same input → same output
    - Caching strategy
    - Audit trails

### Troubleshooting & Learnings

11. **Citation Quality Issues** (`docs/known-issues/citation-quality-issues.md`)
    - Known failure patterns
    - Workarounds

12. **Bibliography Extraction Issues** (`docs/known-issues/bibliography-extraction-issues.md`)
    - ACM Digital Library title truncation
    - Publisher-specific quirks

13. **LLM Citation Validation Learnings** (`docs/learnings/llm-citation-validation-learnings.md`)
    - Why LLMs hallucinate citations
    - Validation strategies

### Other Key Documents

14. **Consolidation Summary** (`docs/retrospectives/consolidation-summary.md`)
    - Repo organization (October 2025)
    - MCP server consolidation
    - Credentials unification

15. **Citation Audit All Manuscripts** (`docs/retrospectives/citation-audit-all-manuscripts.md`)
    - Cross-manuscript analysis
    - Common issues found

16. **Golden Paths** (`.claude/golden-paths.md`)
    - Common workflows
    - Best practices

17. **CLAUDE.md** (`.claude/CLAUDE.md`)
    - AI behavior contract
    - No-regex policy
    - Forbidden patterns
    - Required patterns

---

## All Markdown Documents (Comprehensive List)

### docs/retrospectives/ (Project history)

1. **`citation-audit-all-manuscripts.md`** - Comprehensive audit across all manuscripts revealing patterns of citation failures and quality issues. Documents systematic review of 4 manuscripts with 381 total citations.

2. **`phase3-5-implementation-report.md`** - AST-based citation replacement implementation fixing special character handling (ampersands, brackets) using markdown-it-py. Removed 100+ lines of fragile string manipulation code.

3. **`consolidation-summary.md`** - Repository consolidation (Oct 2025) merging bibliography tools from 3 repos into single source of truth. Unified Zotero credentials and MCP servers.

4. **`phase-4-integration-test-results.md`** - Integration test on mcp-draft-refined-v4.md (381 citations) identifying upstream Zotero data quality as root cause. Found 70 truncated authors and 121 temp citations.

5. **`phase-5-author-enrichment-solution.md`** - Automatic author enrichment from CrossRef/arXiv APIs fixing "Author and others" truncation. 21/21 tests passing, 100% success on real API calls.

6. **`citation-pipeline-auto-add-implementation.md`** - Auto-add integration with DOI validation, policy enforcement, and comprehensive error reporting. 43/43 unit tests passing.

7. **`self-reflection-and-broader-context.md`** - Philosophical reflection on AI assistance, deterministic systems, and academic citation integrity challenges.

8. **`latex-bibliography-conversion-retrospective.md`** - Historical retrospective on LaTeX bibliography conversion challenges and solutions implemented over time.

9. **`current-state-analysis.md`** - Current state snapshot documenting what works, what's broken, and path forward for the conversion pipeline.

### docs/planning/ (Future work)

10. **`mcp-citation-quality-plan.md`** - Architecture plan for MCP citation quality server with 5 tools (audit, URL quality, Zotero match, link health, BibTeX keys).

11. **`comprehensive-completion-plan.md`** - Massive 937-line comprehensive plan for converting ALL 4 markdown files to PDF with ZERO missing citations. Includes diagnostic strategies and success criteria.

12. **`systematic-fix-plan.md`** - Systematic diagnostic plan with multi-hypothesis approach for debugging citation replacement failures.

13. **`deep-code-review-and-continuation-plan.md`** - Deep code review covering production cleanup, regression tests, golden dataset, and MCP implementation.

14. **`multi-hypothesis-diagnostic-plan.md`** - Five hypotheses for citation replacement failures with empirical testing framework.

15. **`root-cause-analysis-and-fix-plan.md`** - Root cause analysis methodology for systematic problem-solving in citation pipeline.

### docs/architecture/ (System design)

16. **`architecture.md`** - Four-component ecosystem architecture (dpp-fashion, om-knowledge-base, claude-code-ops, deep-biblio-tools) with clear separation of concerns.

17. **`deterministic-citation-system.md`** - Design principles for deterministic behavior: same input always produces same output, comprehensive caching, audit trails.

18. **`bibtex-key-formats.md`** - Better BibTeX key format specification and validation requirements (camelCase, author+title+year format).

19. **`why-ast-over-regex.md`** - Rationale for AST-based parsing over regex: handles nested structures, maintainable, reliable edge case handling.

20. **`module-structure-design.md`** - Code organization and module boundaries for maintainability.

### docs/development/ (Dev guidelines)

21. **`regex-removal-summary.md`** - Summary of regex removal effort converting to AST-based parsing across entire codebase.

22. **`regex-removal-best-practices.md`** - Best practices for avoiding regex: string methods, AST parsers, state machines.

23. **`file-naming-conventions.md`** - File naming standards: lowercase, underscores for Python, hyphens for other files.

24. **`temporary-files.md`** - Guidance on temporary file handling and cleanup.

### docs/known-issues/ (Bugs & limitations)

25. **`citation-quality-issues.md`** - Catalog of known citation quality problems and workarounds.

26. **`bibliography-extraction-issues.md`** - Publisher-specific issues (ACM shortened titles, etc.).

27. **`arxiv-metadata-bug.md`** - Specific bug in arXiv metadata extraction.

### docs/troubleshooting/ (Debugging guides)

28. **`citation-replacement-failure-report.md`** - Systematic diagnosis of why citations fail to replace.

29. **`ampersand-issue-analysis.md`** - Deep dive on ampersand escaping issues in LaTeX.

30. **`pdf-compilation-debugging.md`** - Guide to debugging LaTeX/PDF compilation failures.

### docs/standards/ (Standards & specs)

31. **`bibliography-formatting-rules.md`** - Bibliography formatting standards and style requirements.

### docs/reference/ (Reference docs)

32. **`citation-commands-guide.md`** - LaTeX citation command reference (\citep, \citet, etc.).

33. **`bibtex-key-generation-guide.md`** - Guide to generating Better BibTeX keys.

### docs/learnings/ (Lessons learned)

34. **`llm-citation-validation-learnings.md`** - Why LLMs hallucinate citations and how to validate them.

35. **`test-fixing-session-learnings.md`** - Lessons from test fixing sessions.

### Root docs/

36. **`better-bibtex-key-strategy.md`** - Strategy document for Better BibTeX key usage.

37. **`plan-zotero-direct-integration.md`** - Plan for direct Zotero Web API integration.

38. **`workflow-mcp-paper-conversion.md`** - MCP-based paper conversion workflow.

39. **`zotero-api-integration-complete.md`** - Documentation of completed Zotero API integration.

40. **`citation-issues-to-fix.md`** - List of citation issues requiring fixes.

---

## The Critical Gap: Automatic Citation Addition

### What Exists

1. ✅ **Script**: `scripts/add_missing_to_zotero.py`
   - Reads `conversion_results.json`
   - Extracts DOI from URLs
   - Fetches metadata from CrossRef/arXiv
   - Adds to Zotero via API
   - **Proven to work**

2. ✅ **Integration Point**: `citation_manager.py:543-571`
   - Detects missing citations
   - Calls `_handle_missing_citation()`
   - Placeholder for auto-add
   - **Missing**: Actual auto-add trigger

3. ✅ **Policy Enforcement**: `_enforce_no_temp_key_for_valid_doi()`
   - Prevents shortcuts
   - No Temp keys for valid DOIs
   - **Working**

### What's Missing

1. ❌ **Auto-add NOT called during conversion**
   - Citation extraction finds missing papers
   - Creates Temp keys instead of adding to Zotero
   - User must run `add_missing_to_zotero.py` manually
   - **This is unacceptable**

2. ❌ **CitationMatcher not initialized**
   - `citation_matcher` attribute exists
   - Not wired up in converter initialization
   - `add_to_zotero_library()` never called

3. ❌ **No integration test**
   - Unit tests pass
   - But end-to-end flow not tested
   - Missing verification that auto-add actually runs

### What Needs to Happen

**CRITICAL FIX** (Estimated: 2 hours):

1. **Initialize CitationMatcher in converter** (`converter.py:__init__`)
   ```python
   from .citation_matcher import CitationMatcher

   self.citation_matcher = CitationMatcher(
       zotero_client=self.zotero_client,
       collection_name=self.collection
   )
   ```

2. **Pass CitationMatcher to CitationManager** (`converter.py:convert()`)
   ```python
   citation_manager = CitationManager(
       collection_name=self.collection,
       citation_matcher=self.citation_matcher  # NEW
   )
   ```

3. **Call auto-add in _handle_missing_citation** (`citation_manager.py:_handle_missing_citation`)
   ```python
   # After fetching metadata
   if metadata and self.citation_matcher:
       success = self.citation_matcher.add_to_zotero_library(
           doi=doi,
           metadata=metadata
       )
       if success:
           # Fetch newly added entry key
           zotero_key = self._fetch_newly_added_entry(doi)
           if zotero_key:
               return zotero_key
   ```

4. **Implement _fetch_newly_added_entry** (Currently returns None)
   ```python
   def _fetch_newly_added_entry(self, doi: str) -> str | None:
       """Fetch Zotero key for recently added entry."""
       # Search Zotero library by DOI
       # Return Better BibTeX key
   ```

5. **Test end-to-end**
   - Run conversion on mcp-draft-refined-v4.md
   - Verify auto-add is triggered
   - Check Zotero library for new entries
   - Confirm Temp citations drop from 122 to ~0

---

## Path to Zero Broken Citations

### Step 1: Enable Automatic Citation Addition (2 hours)

**Actions**:
1. Initialize CitationMatcher in converter
2. Wire up auto-add in _handle_missing_citation
3. Implement _fetch_newly_added_entry
4. Test with small markdown file (5-10 citations)

**Success Criteria**:
- Script automatically adds missing citations to Zotero
- No manual intervention required
- Temp citations = 0 for papers with valid DOIs

### Step 2: Run Full Conversion with Auto-Add (30 minutes)

**Command**:
```bash
uv run python -m src.cli_md_to_latex \
  mcp-draft-refined-v4.md \
  --output-dir /tmp/mcp_final_test \
  -v
```

**Expected Results**:
- 122 citations automatically added to Zotero
- Temp citations drop from 122 to ~0
- (?) marks drop from 372 to ~10-20

**Monitor**:
- Watch logs for "Adding to Zotero: [URL]"
- Check Zotero library grows by ~122 entries
- Verify references.bib has proper keys

### Step 3: Verify Author Enrichment (10 minutes)

**Check**:
```bash
grep "and others" /tmp/mcp_final_test/references.bib | wc -l
```

**Expected**: ~5-10 (down from 70)

**Why**: Author enrichment automatically fetches complete authors from CrossRef/arXiv

**If Still 70**:
- Check logs for "Enriching BibTeX entries"
- Verify Zotero credentials are being used
- Ensure enrichment is running AFTER Zotero load

### Step 4: Compile and Inspect PDF (15 minutes)

**Compile**:
```bash
cd /tmp/mcp_final_test
make  # or xelatex mcp-draft-refined-v4.tex
```

**Inspect**:
```bash
pdftotext mcp-draft-refined-v4.pdf - | grep -c "(?"
```

**Expected**: 0 (or ≤10)

**Manual Check**:
- Open PDF
- Scan through document
- Verify EVERY citation shows author names
- No (?) anywhere

### Step 5: Validate References (5 minutes)

**Run Validation**:
```bash
uv run python scripts/validate_bib_source.py \
  /tmp/mcp_final_test/references.bib \
  --output-dir /tmp/mcp_final_test
```

**Expected**:
- CRITICAL errors: 0
- HIGH errors: ≤10 (down from 70)
- MEDIUM/LOW: acceptable

### Step 6: Claim Success (Only if all above pass)

**Criteria for Success**:
- ✅ PDF generated
- ✅ Zero (?) citations in PDF
- ✅ Zero Unknown entries in references.bib
- ✅ Author enrichment worked (≤10 truncated authors)
- ✅ Automatic citation addition worked (0 Temp citations)

**Documentation**:
1. Update this vision document with results
2. Create Phase 6 completion report
3. Commit working state
4. Tag as stable release

---

## Appendix: Claude Skills Migration Plan

### Background

**Claude Skills** is Anthropic's new architecture (October 2025) that shifts from MCP server external calls to embedded expertise. Instead of calling out to tools via MCP, Claude can load "skills" that provide domain-specific knowledge and capabilities directly.

**Key Resources**:
- https://github.com/yusufkaraaslan/Skill_Seekers/
- https://github.com/anthropics/skills
- https://simonwillison.net/2025/Oct/16/claude-skills/

### Current MCP Architecture

**What We Have**:
```
Claude Code
    ↓ (MCP calls)
deep-biblio MCP Server
    ↓ (tool invocations)
Citation Tools (Python scripts)
    ↓ (API calls)
Zotero / CrossRef / arXiv APIs
```

**Characteristics**:
- External process communication
- JSON-RPC protocol
- Tool discovery at runtime
- State maintained in server process

### Skills Architecture

**What It Would Be**:
```
Claude Code
    ↓ (loads skill)
Deep Biblio Skill (embedded knowledge)
    ↓ (direct Python execution)
Citation Tools (same Python scripts)
    ↓ (API calls)
Zotero / CrossRef / arXiv APIs
```

**Characteristics**:
- Embedded domain knowledge
- Direct Python execution in Claude's context
- No MCP protocol overhead
- State in Claude's working memory

### Migration Strategy

#### Phase 1: Document Current Capabilities (1 week)

**Actions**:
1. Create skill manifest for deep-biblio
2. Document all tool capabilities
3. Map tool inputs/outputs
4. Identify shared state requirements

**Deliverable**: `deep-biblio-skill-manifest.json`

#### Phase 2: Package as Skill (2 weeks)

**Actions**:
1. Convert MCP tools to skill format
2. Create skill loader
3. Embed domain knowledge (citation best practices, common issues)
4. Test skill loading in Claude Code

**Deliverable**: `skills/deep-biblio/` directory

#### Phase 3: Parallel Operation (1 week)

**Actions**:
1. Support both MCP and Skill interfaces
2. A/B test performance
3. Compare user experience
4. Measure latency differences

**Deliverable**: Performance comparison report

#### Phase 4: Deprecate MCP (if better)

**Actions**:
1. Announce deprecation timeline
2. Migrate users to skill-based approach
3. Archive MCP server code
4. Update documentation

### Skill Capabilities

**What the Deep Biblio Skill Would Provide**:

1. **Citation Extraction**
   - Parse markdown for citations
   - Extract author, year, URL
   - Distinguish citations from hyperlinks

2. **Zotero Integration**
   - Query Zotero library
   - Add missing citations
   - Fetch Better BibTeX keys

3. **Metadata Enrichment**
   - CrossRef API lookups
   - arXiv API lookups
   - Author list completion

4. **Validation**
   - DOI validation
   - Author completeness checking
   - BibTeX format validation

5. **Quality Reporting**
   - Citation quality metrics
   - Missing citation reports
   - Severity-grouped errors

### Expected Benefits

**Performance**:
- Faster execution (no IPC overhead)
- Lower latency (no JSON serialization)
- Better caching (in Claude's memory)

**User Experience**:
- More natural interactions
- Better error messages (Claude understands context)
- Proactive suggestions

**Maintenance**:
- Simpler deployment (no separate server)
- Unified codebase
- Easier debugging

### Challenges

**Technical**:
- Skill format still evolving
- Limited documentation
- May require Python 3.13+ features

**Organizational**:
- Team training on new paradigm
- Migration of existing workflows
- Backward compatibility

**Risk Mitigation**:
- Keep MCP version as fallback
- Gradual rollout
- Extensive testing before deprecation

### Timeline

| Phase | Duration | Start | End |
|-------|----------|-------|-----|
| Phase 1: Document | 1 week | TBD | TBD |
| Phase 2: Package | 2 weeks | TBD | TBD |
| Phase 3: Parallel | 1 week | TBD | TBD |
| Phase 4: Deprecate | 2 weeks | TBD | TBD |
| **Total** | **6 weeks** | TBD | TBD |

### Open Questions

1. **State Management**: How does the skill maintain state across invocations?
2. **API Keys**: How are credentials managed in skill environment?
3. **Caching**: Can skills use file-based caching?
4. **Error Handling**: What's the skill error reporting format?
5. **Updates**: How are skills updated without breaking user workflows?

### Decision Point

**When to Migrate**:
- ✅ Skills architecture is stable (v1.0+)
- ✅ Documentation complete
- ✅ At least 2 example skills exist
- ✅ Performance benefits proven
- ✅ Migration path is clear

**When to Stay with MCP**:
- ❌ Skills still experimental
- ❌ MCP working well for our use case
- ❌ High migration risk
- ❌ Unclear benefits

**Current Recommendation**: **Wait for Skills v1.0 (Q2 2026?)**

---

## Summary

This branch represents months of work on the markdown-to-latex conversion pipeline:
- ✅ AST-based parsing implemented
- ✅ Author enrichment working
- ✅ Comprehensive test suite
- ✅ MCP tools created
- ✅ Documentation extensive

**But it's a total failure if we can't get zero (?) citations.**

The fix is clear:
1. Wire up automatic citation addition (2 hours)
2. Run full conversion with auto-add (30 min)
3. Verify zero broken citations (30 min)

**Total time to success: 3 hours**

Then we can finally claim victory and move on.

---

**Created**: 2025-10-29 12:30 UTC
**Author**: Claude Code (Sonnet 4.5)
**Branch**: `fix/verify-md-to-latex-conversion`
