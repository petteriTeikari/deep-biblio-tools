# CLAUDE.md - Behavior Contract for Claude Code

## Project Context
Deep Biblio Tools is a Python library for processing LLM-generated bibliographies. The main challenge is that LLMs frequently hallucinate citation details, especially author names. This project provides deterministic validation against authoritative sources.

## Forbidden Actions

- **NEVER** use regex to parse structured formats (Markdown, LaTeX, BibTeX)
- **NEVER** create files with version suffixes (`_new.py`, `_v2.py`, `_final.py`)
- **NEVER** modify files in place without explicit user request
- **NEVER** trust author names from LLM output without validation
- **NEVER** switch to `plainnat` style or use numbered citations unless requested
- **NEVER** convert "$50-200" to LaTeX math mode
- **NEVER** import after sys.path modifications
- **NEVER** move Claude guardrail files without updating GitHub Actions

## Required Patterns

- **ALWAYS** produce deterministic output for the same input
- **ALWAYS** use AST-based parsers (markdown-it-py, pylatexenc, bibtexparser)
- **ALWAYS** validate author names against DOI/CrossRef/arXiv metadata
- **ALWAYS** run linters before claiming code is complete
- **ALWAYS** place imports at the top in order: stdlib → third-party → local
- **ALWAYS** check API response success and log failures
- **ALWAYS** escape dollar signs as `\$` when converting to LaTeX

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
- **Exception for Temporary Debug Files**:
  - ✅ CAN create temporary files in system temp directories for debugging
  - ✅ These directories are already in `.gitignore`
  - ✅ Use for: Quick tests, debugging output, intermediate processing
  - ❌ But NOT for: Final outputs, processed data, or anything permanent
  - Example: Use tempfile module or Path.cwd() / "temp" for troubleshooting

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

## Citation Processing Rules

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

## Dollar Sign Handling
- **Dollar signs in markdown = currency (USD)**
- **NEVER** convert "$50-200" to LaTeX math mode
- **ALWAYS** escape as `\$` when converting to LaTeX

## Development Workflow

### Before Committing
1. Run comprehensive validation: `uv run python scripts/validate_claude_constraints.py`
2. Fix all issues systematically
3. Run linters and formatters
4. Ensure all tests pass

### When Creating PRs
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
