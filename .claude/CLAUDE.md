# CLAUDE.md - Behavior Contract for Claude Code

## Project Context
Deep Biblio Tools is a Python library for processing LLM-generated bibliographies. The main challenge is that LLMs frequently hallucinate citation details, especially author names. This project provides deterministic validation against authoritative sources.

## Forbidden Actions

### Development Workflow (CRITICAL - Added 2025-10-31)
- **NEVER** make blind fixes without comprehensive search (Added 2025-10-31)
  - **ALWAYS** search for ALL occurrences using grep/Glob/Grep tools before fixing
  - **ALWAYS** document all locations found in a table or list
  - **ALWAYS** fix ALL instances, not just the first hit
  - User quote: "are you just getting the first hit that your search gives and be happy to fix that without doing any comprehensive / systematic testing of the issues"
  - Example: Don't just fix one `fetch_citation_metadata()` call - grep for ALL calls
  - Before fixing, ask: "Are there other places this pattern appears?"

- **NEVER** claim success without verification (Added 2025-10-31)
  - **ALWAYS** run developer smoke test BEFORE committing
  - **ALWAYS** verify with grep/logs that the fix actually works
  - **ALWAYS** use test-driven development (TDD) with comprehensive debug logging
  - **NEVER** trust compilation success as measure of correctness
  - **NEVER** trust "code looks right" - empirical verification only
  - Pattern from SELF-REFLECTION-WHY-I-FAIL-2025-10-31.md:
    - Research → Implement → **Verify** → Commit → User Confirms
    - NOT: Research → Implement → Claim Done → User Finds Bugs

- **ALWAYS** create programmatic tests (Added 2025-10-31)
  - Tests should import from production code, not hard-code expectations
  - Tests should detect regressions automatically
  - Tests should run after each conversion to verify rules
  - Example: `verify_citation_filtering.py` imports NON_ACADEMIC_DOMAINS to test

- **ALWAYS** add comprehensive debug logging (Added 2025-10-31)
  - Log at INFO level for important decisions
  - Log at DEBUG level for detailed flow
  - Include context in logs (line numbers, URLs, keys)
  - Logs should make it immediately obvious when rules are violated
  - Example: "Skipping non-academic link (GitHub): [Text](URL)" makes violations visible

### Code Quality and File Management
- **NEVER** use regex to parse structured formats (Markdown, LaTeX, BibTeX)
- **NEVER** create files with version suffixes (`_new.py`, `_v2.py`, `_final.py`)
- **NEVER** modify files in place without explicit user request
- **NEVER** import after sys.path modifications
- **NEVER** move Claude guardrail files without updating GitHub Actions
- **NEVER** re-implement existing functionality from scratch (Added 2025-10-31)
  - **ALWAYS** search for existing code/tools in the codebase before creating new implementations
  - **ALWAYS** read documentation in `docs/` directory for existing patterns and solutions
  - **ALWAYS** reference existing code in new documentation (with file paths and line numbers)
  - User quote: "we struggle so much with this as you try to create stuff from scratch and end up re-implementing the same stuff all over again without re-using old tools :("
  - This is the ROOT CAUSE of long processes and repeated work
  - Example: `CitationMatcher` class already exists with multi-strategy matching - don't create a new matcher
  - Example: `extract_arxiv_id()` already strips versions - don't create a new function
  - Before coding, ask: "Does this already exist? Where would it be? Did we document this before?"
- **NEVER** implement directory cleaning operations - Claude Code cannot be trusted with this
  - Directory structures are too complex and Claude Code can easily wipe everything
  - ONLY remove specific, known output files (e.g., `output.pdf`) that will be regenerated
  - NEVER use `shutil.rmtree()`, `rm -rf`, or loop deletions of directory contents
  - If cleaning is absolutely necessary, only delete files with explicit extensions (`.pdf`, `.aux`, `.log`)

### Bibliography Quality (CRITICAL - Added 2025-10-30)
- **NEVER** claim conversion success without running `verify_bbl_quality.py`
- **NEVER** claim conversion success without reading `.bbl` file contents with Read tool
- **NEVER** claim conversion success without reading PDF output with Read tool
- **NEVER** skip `bib_sanitizer.py` pre-processing step before BibTeX compilation
- **NEVER** claim success based on "compilation succeeded" - verify ACTUAL output
- **NEVER** trust intermediate steps (citations extracted, BibTeX generated, PDF compiled)
  - The ONLY measure of success: PDF has ZERO (?) citations AND all citations are correct

### Emergency Mode (RDF-Only, Added 2025-10-30, Zero-Fetch Implemented 2025-10-31)
- **NEVER** allow web fetching when `emergency_mode=True`
  - GUARANTEED: Zero network calls when `emergency_mode=True` (implemented in `generate_bibtex_file()`)
  - Uses ONLY RDF metadata, skips all `fetch_citation_metadata()` calls
  - Expected performance: <30 seconds (was ~11 minutes with fetching)
- **NEVER** proceed if RDF file is missing in emergency mode (MUST HARD CRASH)
- **NEVER** proceed if RDF file is empty in emergency mode (MUST HARD CRASH)
- **NEVER** auto-merge duplicate citations (FLAG only, require manual review)
- **NEVER** allow >5 missing citations without WARNING (likely indicates matching bug)

### Citation Processing
- **NEVER** trust author names from LLM output without validation
- **NEVER** switch to `plainnat` style or use numbered citations unless requested
- **NEVER** convert "$50-200" to LaTeX math mode

## Required Patterns

- **ALWAYS** produce deterministic output for the same input
- **ALWAYS** use AST-based parsers (markdown-it-py, pylatexenc, bibtexparser)
- **ALWAYS** validate author names against DOI/CrossRef/arXiv metadata
- **ALWAYS** run linters before claiming code is complete
- **ALWAYS** place imports at the top in order: stdlib → third-party → local
- **ALWAYS** check API response success and log failures
- **ALWAYS** escape dollar signs as `\$` when converting to LaTeX
- **ALWAYS** verify PDF after conversion - read it with Read tool to check citations
- **NEVER** claim conversion success without verifying PDF has ZERO (?) citations

## Architecture Context

Deep Biblio Tools addresses the critical problem of LLM citation hallucinations through:

- **Deterministic validation** against authoritative sources (CrossRef, arXiv)
- **AST-based parsing** for structured text formats
- **Caching mechanisms** for API responses to ensure reproducibility
- **Audit trails** for all validation decisions
- **Default style**: `spbasic_pt` with `authoryear` citations

## Core Principles

### 1. Deterministic Behavior
- **ALWAYS** produce the same output for the same input
- **NEVER** rely on non-deterministic external factors without explicit caching
- **ALWAYS** provide audit trails for validation decisions

### 2. No Regex for Structured Text Parsing
- **NEVER** use regex to parse structured formats (Markdown, LaTeX, BibTeX)
- **NEVER** import or use the `re` module anywhere in the codebase
- **ALWAYS** use appropriate alternatives:
  - **For simple patterns**: String methods (`startswith()`, `endswith()`, `find()`, `replace()`)
  - **For structured formats**: AST-based parsers
    - `markdown-it-py` for Markdown
    - `pylatexenc` for LaTeX
    - `bibtexparser` for BibTeX
  - **For complex parsing**: Character-by-character state machines

#### Regex Replacement Patterns
- ❌ `re.search(r'\d+', text)` → ✅ `any(c.isdigit() for c in text)`
- ❌ `re.findall(r'\\cite\{([^}]+)\}', text)` → ✅ Manual brace parsing
- ❌ `re.sub(r'pattern', 'replacement', text)` → ✅ `text.replace()`
- ❌ `re.match(r'^pattern', text)` → ✅ `text.startswith()`
- ❌ `re.split(r'[,;]', text)` → ✅ `text.replace(';', ',').split(',')`

#### When Refactoring Legacy Regex Code
1. **Assessment**: Identify all regex usage with `grep -r "import re" src/`
2. **Categorization**: Simple patterns vs complex structured parsing
3. **Replacement Strategy**: String methods for simple, AST parsers for complex
4. **Validation**: Maintain test coverage throughout refactoring
5. **Cleanup**: Remove all `import re` statements and mark as `# Banned`

### 3. File Management
- **NEVER** create files with version indicators anywhere in the name:
  - Suffixes: `_new`, `_v2`, `_v3`, `_final`, `_revised`, `_updated`, `_fixed`, `_old`, `_backup`
  - Prefixes: `new_`, `updated_`, `fixed_`, `final_`, `v2_`, `temp_`, `tmp_`
  - Infixes: `module_new_parser.py`, `citation_v2_extractor.py`
  - Date stamps: `parser_20240315.py`, `module_2024_version.py`
  - Examples of what NOT to do:
    - ❌ `citation_extractor_new.py`
    - ❌ `new_citation_extractor.py`
    - ❌ `citation_new_extractor.py`
    - ❌ `citation_extractor_20240315.py`
    - ❌ `citation_extractor_FIXED.py`
- **ALWAYS** modify the existing file directly - Git tracks history
- **NEVER** create parallel versions of the same functionality
- **ACCEPTABLE** patterns only for genuinely different implementations:
  - Strategy pattern: `parser_ast.py`, `parser_regex.py` (different algorithms)
  - NOT versions: `parser.py`, `new_parser.py` (same algorithm, different version)
- **NEVER** modify files in place without explicit user request

### 4. Repository Organization & Data Management
- **NEVER** save ANY output files inside the repository
  - ❌ `/dinov3_academic_rephrase.md` (repository root)
  - ❌ `/data/processed/dinov3_academic_rephrase.md` (inside repo)
  - ✅ Save outputs to external data folders where inputs come from
  - ✅ Example: Input from `/home/petteri/Dropbox/.../mllm_vlm/` → Output to same location
- **NEVER** use the repository `/data/` folder for generated outputs
  - The `/data/` folder is for example files and test data ONLY
  - Generated outputs belong in external folders (Dropbox, blob storage, etc.)
  - This prevents repository bloat and accidental commits of large data files
- **NEVER** create new scripts when existing tools can do the job
  - ❌ Creating `process_dinov3_25_percent.py`
  - ✅ Using existing `tools/paper-processor/academic_rephrasing.py`
- **ALWAYS** keep data separate from code:
  - Repository: Contains only code, tools, documentation, and minimal example data
  - External folders: Contains actual input data and ALL generated outputs
  - Example: Process files from `/home/petteri/Dropbox/.../papers/` and save outputs there
- **BEFORE** creating any new file, ask yourself:
  1. Does an existing tool already do this?
  2. Is this output data? If yes, save OUTSIDE the repository
  3. Am I creating a duplicate/versioned file?
- **Output File Locations**:
  - If input is from `/path/to/input/file.md`
  - Save output to `/path/to/input/file_processed.md` or `/path/to/input/processed/file.md`
  - NEVER save to repository directories
- **MD→LaTeX Conversion Pipeline Output Locations (CRITICAL)**:
  - **NEVER** use `/tmp` or any system temp directory for pipeline outputs
  - **ALWAYS** create an `output/` subdirectory next to the input markdown file
  - **Pattern**: Input at `/path/to/paper/file.md` → Output to `/path/to/paper/output/`
  - **Example**:
    - Input: `/home/petteri/Dropbox/.../mcp-review/mcp-draft-refined-v4.md`
    - Output: `/home/petteri/Dropbox/.../mcp-review/output/mcp-draft-refined-v4.tex`
    - Output: `/home/petteri/Dropbox/.../mcp-review/output/mcp-draft-refined-v4.pdf`
  - This applies to ALL conversion artifacts: .tex, .pdf, .bib, .log, .aux, etc.
  - User must be able to easily find outputs next to their source files

### 5. Generic Solutions Only
- **NEVER** create paper-specific or file-specific solutions
  - ❌ `clean_dinov3.py`, `process_dinov3_special.py`
  - ✅ Update existing tools to handle ALL cases generically
- **ALWAYS** think in terms of batch processing and folders
  - If processing one paper, the solution should work for 1000 papers
  - If fixing an issue in one file, fix it for all files
- **NEVER** hardcode paper names or specific content
  - ❌ `if "DINOv3" in title: special_processing()`
  - ✅ Generic rules that apply to all papers
- **Example**: User shows issue in one paper → Fix the tool to handle that issue for ALL papers

### 6. Code Quality
- **ALWAYS** run linters before claiming code is complete:
  1. `uv run ruff check --fix`
  2. `uv run ruff format`
- **NO** unused variables, imports, or functions
- **CLEAN** code only - no debug prints or commented code

### 5. Import Organization
- **ALWAYS** place imports at the top of files
- **ORDER**: stdlib → third-party → local imports
- **NEVER** import after sys.path modifications

## Bibliography Workflow - SINGLE SOURCE OF TRUTH

### references.bib is EPHEMERAL - NEVER STATIC

**CRITICAL RULE #1**: `references.bib` DOES NOT EXIST as a static file. It is ONLY generated during conversion.

- ❌ **NEVER** assume `references.bib` exists on disk to read from
- ❌ **NEVER** ask user to "check references.bib" - it doesn't exist until conversion runs
- ❌ **NEVER** treat it as a source file - it's a build artifact
- ✅ **ALWAYS** generate it fresh from Zotero API during each conversion
- ✅ **DELETE** it before conversion if it exists (stale artifact from previous run)
- ✅ Think of it like a `.pdf` or `.aux` file - ephemeral output only

**If you find yourself wanting to read references.bib, STOP. You should be querying Zotero API instead.**

### Zotero Web API Only

**CRITICAL RULE #2**: The ONLY source of bibliography data is the Zotero Web API. Period.

**FORBIDDEN** - NEVER use these:
- ❌ Manual CSL JSON exports (`.json` files) - they get stale immediately
- ❌ Manual BibTeX files (`.bib`, `.bibtex`) - they are GENERATED only
- ❌ RDF exports (`.rdf`) - never use these
- ❌ `LOCAL_BIBTEX_PATH` environment variable - OBSOLETE, delete it
- ❌ Any local snapshot/export of bibliography data
- ❌ Generated citation keys - NEVER create keys locally

**REQUIRED** - ALWAYS do this:
- ✅ Load bibliography from Zotero Web API using `pyzotero` (production mode)
- ✅ OR use local RDF export from Zotero (emergency mode)
- ✅ NEVER generate keys locally - always from source
- ✅ Auto-add missing citations to Zotero collection
- ✅ Generate `references.bib` fresh from Zotero data during each conversion
- ✅ Delete `references.bib` before each conversion (it's regenerated)
- ✅ Trust Zotero as single source of truth

### Citation Keys - Better BibTeX is BANNED

**CRITICAL**: Better BibTeX keys are **BANNED** from this repository as of 2025-10-30.

**Rationale**:
- Too difficult to get working consistently across all bibliography sources
- Zotero Web API doesn't support Better BibTeX key format reliably
- Local exports may have inconsistent key generation
- Causes validation warnings that flood output (1000+ lines)
- User spent multiple sessions trying to make it work - decision: ban it entirely

**What to use instead**:

1. **Simple keys** (preferred for emergency RDF mode):
   - `doi_10_1038_*` (generated from DOI)
   - `amazon_1138021016` (generated from ISBN in URL)
   - `arxiv_2401_12345` (generated from arXiv ID)
   - Pattern: `{source}_{identifier_sanitized}`

2. **Zotero Web API keys** (for production mode):
   - Format: `author_title_year` (lowercase, underscores)
   - Example: `niinimaki_environmental_2020`
   - Generated by Zotero API, not locally

**Code implications**:
- NO validation of citation key format (accept ANY string)
- Never generate keys locally (violates CLAUDE.md rules)
- RDF parser generates simple keys from URLs automatically
- Citation matching uses URL/DOI/ISBN extraction, NOT key format

**Historical context**: We spent multiple sessions trying to make Better BibTeX work.
User final decision (2025-10-30): "Ban it entirely from repo, simple keys are fine."

### Environment Configuration

```bash
# Required Zotero credentials in .env
ZOTERO_API_KEY=your_key_here
ZOTERO_LIBRARY_ID=your_id_here
ZOTERO_LIBRARY_TYPE=user
ZOTERO_COLLECTION=dpp-fashion  # Default collection name
```

### Conversion Workflow

1. **User updates Zotero** (web or desktop app)
2. **Converter fetches from API** - always fresh, no manual export
3. **Missing citations added** - automatically via Zotero API
4. **BibTeX generated** - from Zotero data, written to `references.bib`
5. **LaTeX compilation** - uses the generated `references.bib`

### Generated vs Source Files

| File | Type | Source | Action |
|------|------|--------|--------|
| `references.bib` | **GENERATED** | Converted from Zotero API | Delete before each conversion |
| Zotero collection | **SOURCE** | Zotero Web API | Always trust this |
| `*.json` CSL exports | **FORBIDDEN** | Manual export | Never use, never create |
| `dpp-fashion.bib` | **FORBIDDEN** | Old workflow | Delete entirely |

### Why This Matters

**The Problem**: Manual exports create stale data the moment they're saved. Any changes in Zotero require re-export. Multiple copies cause confusion and errors.

**The Solution**: Direct Zotero API access means always-current data, automatic sync, and zero manual file management.

## Citation Processing Rules

### Hyperlink vs Citation Format (CRITICAL)

**MUST distinguish between citations and regular hyperlinks:**

- **Citations**: `[Author (Year)](URL)` or `[Author et al., Year](URL)`
  - Has author name AND year in brackets
  - Should be processed for bibliography
  - Examples:
    - `[Smith (2020)](https://arxiv.org/abs/2020.12345)` ✅
    - `[Wang et al., 2023](https://doi.org/10.1234/example)` ✅
- **Regular Hyperlinks**: `[Text](URL)` - NO year in brackets
  - Just descriptive text, no author/year
  - Should be left as plain hyperlinks in LaTeX (NOT bibliography entries)
  - Examples:
    - `[Google Docs](https://docs.google.com)` ✅ Regular link
    - `[EON](https://www.eon.xyz/)` ✅ Regular link
    - `[GitHub repo](https://github.com/user/repo)` ✅ Regular link

**Implementation**: `citation_extractor_unified.py` MUST skip links without year format. This prevents creating false "Unknown, Unknown" citations from regular hyperlinks.

### Author Name Handling
- **TREAT** all "et al" as requiring full author lookup
- **VALIDATE** every author name against DOI/CrossRef/arXiv metadata
- **REPLACE** hallucinated names with validated ones automatically
- **NEVER** trust author names from LLM output without validation

### Bibliography Style
- **DEFAULT**: `spbasic_pt` with `authoryear` citations
- **NEVER** switch to `plainnat` style
- **NEVER** use numbered citations unless explicitly requested

### API Integration
- **ALWAYS** check if API responses are successful
- **STOP** extraction if APIs return incomplete data
- **LOG** all API failures with clear error messages

### Known Issues
- **ACM Digital Library**: Often provides shortened titles only. See `.claude/known-issues-acm.md` for details.

### Missing Citations - CRITICAL REQUIREMENT (Added 2025-10-31)

**RULE**: Missing citations MUST appear as (?) in the PDF, NOT get temp keys in .bib file.

**The Problem with failedAutoAdd_* keys** (now BANNED):
- They obscured which citations were actually missing from Zotero
- They created hallucinated "phantom" entries in the bibliography
- They made it unclear what needed to be added to Zotero
- User quote: "not hallucinating some weird temp citations to the list!"

**Correct Behavior**:
1. Citation found in RDF → Add to references.bib with proper metadata
2. Citation NOT found in RDF → Do NOT add to references.bib at all
3. LaTeX will automatically render missing \cite{} as (?) in PDF
4. User can then see EXACTLY which citations need to be added to Zotero

**Implementation** (citation_manager.py:1720-1776):
- `generate_bibtex_file()` filters out all `failedAutoAdd_*` keys
- `allow_failures=True` allows conversion to continue despite missing citations
- Missing citations remain as `\cite{failedAutoAdd_*}` in .tex but NOT in .bib
- LaTeX renders these as (?) since they're not in references.bib

**User Requirement**:
> "The correct way to handle a missing citation is to have (?) in the article so that it is clear that there are missing citations which need to be fixed."

**Historical Context**:
- User repeatedly asked to ban failedAutoAdd usage
- Previous behavior: Generated temp keys WITH fetched metadata (confusing!)
- Now: Generate temp \cite{} keys in .tex, but EXCLUDE from .bib entirely
- Result: Clear (?) in PDF shows what's missing, no phantom bibliography entries

### Missing Citations Report - AUTO-GENERATION REQUIRED (Added 2025-11-01)

**RULE**: Missing citations reports MUST be auto-generated on EVERY conversion if there are failed citations.

**Files That Must Be Generated**:
- `output/missing-citations-report.json` - Machine-readable format with counts and reasons
- `output/missing-citations-review.csv` - Human-reviewable with supervision columns

**Report Contents**:
- Citation text from markdown (e.g., `[Author (Year)](URL)`)
- URL
- Authors (extracted from markdown)
- Year (extracted from markdown)
- Reason (e.g., "Not found in RDF export")
- Action (e.g., "Add this paper to your Zotero collection and re-export RDF")
- Empty supervision columns for user's manual review

**Implementation**: `converter.py:1171-1244`

**Bug Fixed** (2025-11-01): Reports were checking for `citation.authors == "Unknown"` but emergency mode extracts authors from markdown text, so they're never "Unknown". Fixed to use `self.citation_manager.failed_citations` list which tracks ALL failed citation lookups.

**Verification**:
```bash
ls -lh output/missing-citations-report.json output/missing-citations-review.csv
jq '.missing_count' output/missing-citations-report.json
```

### .bbl Hardcoding Workflow (Added 2025-11-01)

**Purpose**: Convert .bib → hardcoded .bbl with hyperlinked authors for final submission.

**When to Use**:
- Final journal/conference submission
- Archival versions
- When you want clickable author-year links in PDF

**What It Does**:
- Converts `\bibliography{references}` → inline `\begin{thebibliography}...\end{thebibliography}`
- Hyperlinks author-year: `\href{https://doi.org/...}{Author (Year)}`
- Standalone bibliography (no external .bib file needed)

**Scripts Available**:
- `scripts/hardcode_bibliography.py` - Standard formatting (line 417-656)
- `scripts/create_hardcoded_bibliography_uadreview.py` - With natbib label support

**User's Workflow**:
1. Run markdown → LaTeX conversion (generates references.bib)
2. Compile with BibTeX (generates .bbl)
3. Optionally modify .bbl by hand (e.g., fix formatting)
4. Use hardcoding script OR manually copy .bbl into .tex
5. Final .tex has embedded bibliography

**Important**: references.bib is ephemeral (deleted before each conversion). User works with modified .bbl files which are copied into final .tex.

**For More Details**: See `.claude/bbl-hardcoding-guide.md`

## Quick Reference Summary

**ALWAYS READ FIRST**: `.claude/CITATION-REQUIREMENTS.md` contains a 1-page summary of ALL citation management requirements including:
- Current state
- Core non-negotiable requirements
- Quality checks before claiming success
- References to detailed documentation

This quick reference prevents forgetting critical requirements between sessions.

## Dollar Sign Handling
- **Dollar signs in markdown = currency (USD)**
- **NEVER** convert "$50-200" to LaTeX math mode
- **ALWAYS** escape as `\$` when converting to LaTeX

## Conversion Success Criteria - CORRECT UNDERSTANDING

### Understanding (?) Citations - CRITICAL CONCEPT

**(?) in PDF is EXPECTED and CORRECT behavior for citations missing from Zotero RDF.**

**Three types of citations in PDF**:
1. ✅ **GOOD**: Paper in Zotero → Full citation in bibliography (e.g., "Smith et al., 2020")
2. ✅ **GOOD**: Paper NOT in Zotero → (?) in PDF (shows what needs manual addition)
3. ❌ **BAD**: Paper NOT in Zotero → Phantom citation with hallucinated/fetched data

**The goal is NOT zero (?), the goal is ACCURATE citations.**
- (?) = Missing paper user needs to add to Zotero
- (?) is a FEATURE showing gaps, not a bug to eliminate

### Success Criteria (Emergency Mode)

**BEFORE claiming conversion success, verify ALL of these**:

1. ✅ **PDF generates** without LaTeX errors
2. ✅ **Citation counts match**: Total extracted = Matched + Missing
   - Example: 308 total = 210 matched + 98 missing
3. ✅ **Missing citations show as (?)** in PDF (use Read tool to verify)
4. ✅ **Missing citations reports generated**:
   - `output/missing-citations-report.json`
   - `output/missing-citations-review.csv`
5. ✅ **references.bib has ZERO**:
   - "Unknown" or "Anonymous" entries
   - `failedAutoAdd_*` entries (must be filtered out)
6. ✅ **Matched citations show proper** author names and years (not ?)
7. ✅ **LaTeX/BibTeX logs** have ZERO fatal errors (warnings OK)
8. ✅ **Output directory correct**: `input_dir/output/`, NOT `/tmp`

**Important**: If you have 98 missing citations, you SHOULD see ~98 (?) in the PDF. That's correct.

### What Counts as Failure

**THESE are actual problems**:
- ❌ Unknown/Anonymous entries in references.bib
- ❌ failedAutoAdd_* entries in references.bib (they were filtered but appeared anyway)
- ❌ Phantom citations with fetched data for missing papers
- ❌ Citation counts don't match (extraction vs matched+missing)
- ❌ Missing citations reports not generated
- ❌ Output saved to /tmp instead of input_dir/output/

**THESE are NOT problems**:
- ✅ (?) in PDF for papers not in Zotero (expected)
- ✅ 98 missing citations reported (user needs to add to Zotero)
- ✅ BibTeX warnings about missing citations (expected)

### Workflow for Success

1. Run conversion
2. Check citation counts: `total = matched + missing`
3. Verify missing reports exist in output/
4. Check references.bib for Zero Unknown/Anonymous/failedAutoAdd
5. Read PDF and verify:
   - Matched citations show author names ✅
   - Missing citations show (?) ✅
6. Count (?) in PDF matches missing count
7. THEN claim success (even with (?) present)

### Development Workflow

#### Before Committing
1. Run comprehensive validation: `uv run python scripts/validate_claude_constraints.py`
2. Fix all issues systematically
3. Run linters and formatters
4. Ensure all tests pass

#### When Creating PRs
1. Write clear, atomic commits
2. Include test coverage for new features
3. Update documentation as needed
4. Ensure CI/CD passes

## File Naming Conventions

### Required Naming Rules
1. **Lowercase Only**: All filenames must be lowercase
   - ✅ `setup-guide.md`, `docker-compose.yml`
   - ❌ `Setup_Guide.md`, `DockerCompose.yml`
   - **Exceptions**: `README`, `CHANGELOG`, `CLAUDE` files may use uppercase

2. **Word Separation Rules**:
   - **Python files (.py)**: MUST use underscores (_) for valid module names
     - ✅ `biblio_checker.py`, `citation_extractor.py`
     - ❌ `biblio-checker.py`, `citation-extractor.py`
   - **All other files**: MUST use hyphens (-) to separate words
     - ✅ `setup-guide.md`, `run-tests.sh`, `docker-compose.yml`
     - ❌ `setup_guide.md`, `run_tests.sh`, `docker_compose.yml`

3. **No CamelCase or PascalCase**: Convert to appropriate separator
   - Python: `extractIncompleteAuthors.py` → `extract_incomplete_authors.py`
   - Others: `SetupGuide.md` → `setup-guide.md`

### Examples by File Type
- **Python**: `citation_extractor.py`, `biblio_validator.py`, `paper_scraper.py` (underscores)
- **Shell**: `run-tests.sh`, `setup-environment.sh`, `check-linting.sh` (hyphens)
- **Markdown**: `setup-guide.md`, `api-reference.md`, `troubleshooting.md` (hyphens)
- **Config**: `pyproject.toml`, `docker-compose.yml`, `settings.json` (hyphens)

### Python Module Naming Exception
Python module names cannot contain hyphens. Therefore:
- Python files: `module_name.py` → imports as `import module_name`
- Python special files: `__init__.py`, `__main__.py` (always keep underscores)

### When Creating New Files
- **Python files**: Use lowercase with underscores
- **Other files**: Use lowercase with hyphens
- **VERIFY** naming before committing

## Testing Philosophy
- **Test deterministic behavior**: Same input → same output
- **Test hallucination detection**: Verify common patterns are caught
- **Test API failures**: Ensure graceful degradation

## Performance Targets
- Citation validation: <100ms with cache
- File processing: Linear time complexity
- Memory usage: Constant for streaming operations

## Repository Structure Requirements

### Claude Code Guardrail Files
**CRITICAL**: The following files MUST exist in these exact locations for GitHub Actions validation:

1. **`CLAUDE.md`** (root directory)
   - Must contain reference to `.claude/CLAUDE.md`
   - Acts as entry point for Claude Code guardrails

2. **`.claude/CLAUDE.md`** (this file)
   - Detailed behavioral contract and project guidelines

3. **`.claude/golden-paths.md`**
   - Common development workflows and patterns

4. **`.claude/auto-context.yaml`**
   - Auto-context configuration for Claude Code

**NEVER** move or rename these files without updating the GitHub Actions workflow at `.github/workflows/validate-claude-guardrails.yml`

### Debugging Guardrails Issues
For troubleshooting validation failures and understanding requirements, see **[.claude/guardrails-learnings.md](.claude/guardrails-learnings.md)**
