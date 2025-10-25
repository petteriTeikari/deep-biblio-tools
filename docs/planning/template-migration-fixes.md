# Template-to-Project Migration Fixes

## Issue Summary
The deep-biblio-tools repository was experiencing CI failures on GitHub Actions despite tests passing locally. The root cause was that this repository had evolved from a cookiecutter template to an actual project, but still contained legacy template-testing workflows.

## Root Cause Analysis
1. **Legacy Template Workflows**: Three workflows were still configured to run on PRs:
   - `test-template.yml` - Testing template syntax and generation
   - `test-template-act.yml` - Act-compatible template testing
   - `test-template-act-compatible.yml` - Testing for template structure

2. **Non-existent Files**: These workflows referenced files that don't exist in the current project:
   - `tests/test_template_syntax.py`
   - `tests/test_hooks.py`
   - `tests/test_template_generation.py`
   - `cookiecutter.json`
   - `hooks/` directory

3. **Incorrect Workflow Reference**: The main CI workflow tried to call the guardrails workflow as an action instead of letting it run independently.

## Fixes Applied

### 1. Removed Legacy Template Workflows
```bash
rm .github/workflows/test-template.yml
rm .github/workflows/test-template-act.yml
rm .github/workflows/test-template-act-compatible.yml
```

### 2. Fixed Main CI Workflow
- Removed incorrect guardrails workflow call
- Cleaned up `.github/workflows/ci.yml` to focus on actual project needs:
  - Python 3.12 setup with uv
  - Ruff linting and formatting
  - Pytest with coverage
  - Claude constraints validation

### 3. Fixed Claude Constraints Validator
Updated `scripts/validate_claude_constraints.py` to exclude third-party directories:
```python
# Skip third-party directories to avoid false positives
relative_path = file_path.relative_to(self.project_root)
if any(part in ['.venv', 'venv', '.env', 'node_modules', '.git', '__pycache__']
       for part in relative_path.parts):
    continue
```

## Current Working CI Setup
- **ci.yml**: Main CI workflow (linting, testing, validation)
- **validate-claude-guardrails.yml**: Claude Code safety checks (runs independently)
- **branch-naming.yml**: Branch naming validation

## Verification
All CI steps now pass both locally and on GitHub Actions:
```bash
uv run ruff check .                                    # [OK] Passes
uv run ruff format --check .                          # [OK] Passes
uv run pytest --cov --cov-report=xml                  # [OK] 9 tests pass
uv run python scripts/validate_claude_constraints.py  # [OK] Passes
```

## Lessons Learned
1. **Template Evolution**: When a repository evolves from template to project, legacy workflows must be cleaned up
2. **Root Cause vs Symptoms**: Don't just patch individual failures - investigate the underlying cause
3. **Workflow Dependencies**: Understand the difference between calling workflows as actions vs independent workflows
4. **Third-party Code**: Validation scripts should exclude vendor/dependency directories to avoid false positives

## Additional Template Issues Discovered

### Missing Pre-commit Setup (2025-07-29)
The Cookiecutter template is missing critical pre-commit configuration that developers need to manually add:

1. **Missing `.pre-commit-config.yaml`**: The template should include this file with:
   ```yaml
   repos:
     - repo: https://github.com/astral-sh/ruff-pre-commit
       rev: v0.8.6
       hooks:
         - id: ruff
           args: [ --fix ]
         - id: ruff-format

     - repo: https://github.com/pre-commit/pre-commit-hooks
       rev: v5.0.0
       hooks:
         - id: trailing-whitespace
         - id: end-of-file-fixer
         - id: check-yaml
         - id: check-added-large-files
         - id: check-merge-conflict
         - id: detect-private-key
   ```

2. **Missing pre-commit installation in setup**: The template should automatically:
   - Include pre-commit in dev dependencies
   - Run `pre-commit install` as part of initial setup
   - Document this in the generated README

3. **Impact**: Without this, developers must manually:
   - Create the pre-commit config file
   - Install pre-commit hooks
   - Fix numerous formatting issues that accumulate without automated checks

This defeats the purpose of a Cookiecutter template, which should provide a fully configured development environment out of the box.

### Missing Docker Testing Enforcement (2025-07-29)
The Cookiecutter template is missing critical Docker-based testing enforcement that exists in the claude-code-guardrails-template repository:

1. **Missing Docker Testing Infrastructure**:
   - No `scripts/claude_default_test_command.sh` to override and enforce Docker testing
   - No `scripts/run_github_actions_locally.sh` for GitHub Actions environment replication
   - No `docker/github-actions/Dockerfile` with exact Ubuntu 22.04 + Python 3.12 setup
   - No resource constraints (7GB RAM, 2 CPU) to match GitHub Actions limits

2. **Current State Problems**:
   - Projects generated from template allow local `pytest` execution
   - No enforcement of Docker-only testing
   - Vulnerable to "works on my machine" issues
   - CI/CD failures due to environment differences (OS, Python versions, dependencies)

3. **What the Template Should Include**:
   ```bash
   # The template should generate these files:
   scripts/claude_default_test_command.sh  # Forces Docker validation
   scripts/run_github_actions_locally.sh   # Runs tests in GHA environment
   docker/github-actions/Dockerfile        # Exact GHA replica
   docs/testing-guide.md                   # Explains Docker-only testing
   ```

4. **Expected Behavior**:
   - Running `pytest` locally should be blocked/redirected to Docker
   - All tests MUST run in Docker container matching GitHub Actions
   - 95% cloud-local parity guaranteed
   - Resource constraints enforced (prevents local machine advantages)

5. **Impact**:
   - The guardrails template achieved 93% reduction in CI/CD failures with this approach
   - Without it, generated projects suffer from environment-related test failures
   - Developers waste time debugging "works locally, fails in CI" issues

This is a critical missing feature that undermines the template's goal of providing a production-ready development environment with reliable testing infrastructure.

### Missing uv Enforcement in Claude Commands (2025-07-29)
The Cookiecutter template enforces `uv` for Python dependency management but doesn't properly configure Claude to understand this requirement:

1. **Problem**: Claude tries to run `python` or `python3` commands directly instead of using `uv run python`
   - Example: `python scripts/test_script.py` fails with "python: command not found"
   - Should be: `uv run python scripts/test_script.py`

2. **Missing Configuration**:
   - The template should generate a CLAUDE.md with explicit instructions about uv usage
   - Should include common commands that require `uv run` prefix:
     ```bash
     # WRONG - these will fail:
     python script.py
     python3 -m module
     pytest tests/
     ruff check .

     # CORRECT - always use uv:
     uv run python script.py
     uv run python -m module
     uv run pytest tests/
     uv run ruff check .
     ```

3. **Impact**:
   - Claude wastes time attempting direct Python commands that fail
   - Developers must repeatedly correct Claude's command attempts
   - Creates confusion about the project's Python environment setup

4. **Solution for Template**:
   - Generate comprehensive CLAUDE.md with uv enforcement rules
   - Include examples of all common Python commands with uv prefix
   - Add clear "NEVER run python/python3 directly" instruction

This is particularly important because uv is a key part of the modern Python development workflow, and Claude needs explicit guidance to use it consistently.

### Missing Pre-commit Hooks and Scripts (2025-07-29)
The Cookiecutter template is missing critical pre-commit hooks and scripts that cause CI failures:

1. **Missing Essential Hooks**:
   - `check-case-conflict` - Prevents case conflicts in filenames (Windows/Mac compatibility)
   - `no-emojis` hook - Prevents emoji usage that causes encoding issues
   - `pygrep-hooks` - Documentation validation (rst-backticks, rst-directive-colons, etc.)
   - `uv-lock` - Keeps uv.lock file updated when dependencies change
   - `detect-secrets` - Security scanning for accidental secret commits

2. **Missing Claude-specific Hooks**:
   - `aidev-immutable-check` - Validates AIDEV-IMMUTABLE markers
   - `claude-context-check` - Ensures required Claude files exist
   - `cross-platform-compatibility` - Platform compatibility validation
   - `cross-platform-compliance` - Encoding and escape validation

3. **Missing Required Scripts**:
   ```
   scripts/check_no_emojis.py
   scripts/remove_emojis.py
   scripts/validate_cross_platform_compatibility.py
   scripts/pre_commit_cross_platform_validation.py
   ```

4. **Current Impact**:
   - GitHub Actions CI fails on emoji detection (no script exists to check)
   - Cross-platform issues not caught before commit
   - Security vulnerabilities (secrets) could be committed
   - Case conflicts could break Windows/Mac checkouts
   - Documentation formatting issues not caught

5. **Template vs Project-specific Hooks**:

   **Should be in ALL projects (general hooks)**:
   - Basic pre-commit-hooks (trailing-whitespace, end-of-file-fixer, etc.)
   - Language-specific linting/formatting (ruff for Python)
   - Security scanning (detect-secrets)
   - Cross-platform compatibility checks
   - No-emojis check (for consistent encoding)

   **Should be OPTIONAL or Claude-specific**:
   - AIDEV-IMMUTABLE validation (only if using AI development markers)
   - Claude context file checks (only for Claude-compatible projects)
   - Project-type specific (e.g., ROS2 colcon-test, iOS xcode-build)

6. **Recommended Template Fix**:
   The template should generate:
   - Complete `.pre-commit-config.yaml` with all essential hooks
   - All required scripts in `scripts/` directory
   - Option to enable/disable Claude-specific hooks
   - Documentation explaining each hook's purpose

   Example structure:
   ```yaml
   # Always included
   - repo: https://github.com/pre-commit/pre-commit-hooks
     hooks:
       - id: check-case-conflict  # Missing in current projects!

   # Conditionally included based on cookiecutter variables
   {% if cookiecutter.enable_claude_hooks == "yes" %}
   - repo: local
     hooks:
       - id: no-emojis
         entry: python scripts/check_no_emojis.py
   {% endif %}
   ```

This missing infrastructure leads to "works locally, fails in CI" issues that waste developer time and undermine confidence in the development workflow.

### Filename Convention Tests Should Respect .gitignore (2025-07-29)
The Cookiecutter template's filename convention tests check all files, including those that should be ignored (data files, generated outputs, etc.):

1. **Problem**:
   - Tests fail on data files like `UADReview_v4.md` and files in `data/md_output/*`
   - These files are in `.gitignore` and shouldn't be subject to code naming conventions
   - Data files often have specific naming requirements (e.g., matching external sources)

2. **Current Behavior**:
   - `test_filename_conventions.py` scans ALL markdown files in the project
   - Doesn't respect `.gitignore` patterns
   - Fails on legitimate data/output files

3. **Required Fix**:
   The template should generate a smarter `test_filename_conventions.py` that:
   ```python
   def _load_gitignore(self) -> list[str]:
       """Load patterns from .gitignore file."""
       gitignore_path = self.project_dir / ".gitignore"
       patterns = []

       if gitignore_path.exists():
           with open(gitignore_path, 'r') as f:
               for line in f:
                   line = line.strip()
                   if line and not line.startswith('#'):
                       patterns.append(line)

       return patterns

   def _is_gitignored(self, file_path: Path) -> bool:
       """Check if a file matches any .gitignore pattern."""
       # Use fnmatch for glob pattern matching
       # Handle directory patterns (ending with /)
       # Return True if file should be ignored
   ```

4. **Impact**:
   - Without this fix, projects fail tests on legitimate data files
   - Developers must manually exclude directories or disable tests
   - Creates confusion about what files should follow conventions

5. **Best Practice**:
   - Only enforce naming conventions on tracked source files
   - Data files, generated outputs, and vendor code should be exempt
   - Tests should align with version control boundaries

This is especially important for data science and analysis projects where input/output files often have externally-defined naming requirements.

## Next Steps for Template Work
See `claude-code-guardrails-template-plan.md` for the end-to-end plan to continue work on the actual template project.
