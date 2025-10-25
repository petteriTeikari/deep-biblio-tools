# Claude Code Guardrails Template - End-to-End Plan

## Overview
This is your comprehensive plan for continuing work on the **claude-code-guardrails-template** project. This plan incorporates lessons learned from fixing the template-to-project migration issues in deep-biblio-tools.

## Background Context
- The **deep-biblio-tools** repository evolved from a cookiecutter template to an actual project
- We recently fixed CI issues caused by legacy template-testing workflows
- The actual **claude-code-guardrails-template** project needs proper template structure and testing

## Current State Assessment Needed

### 1. Repository Structure Validation
```bash
# When you start working on claude-code-guardrails-template, first validate:
ls -la                          # Check for cookiecutter.json
test -f cookiecutter.json       # Should exist for a template
test -d "{{cookiecutter.project_slug}}"  # Template directory structure
test -d hooks/                  # Cookiecutter hooks directory
```

### 2. Template Testing Infrastructure
Verify these template-specific test files exist and are working:
- `tests/test_template_syntax.py` - Validates template syntax
- `tests/test_hooks.py` - Tests cookiecutter hooks
- `tests/test_template_generation.py` - Tests template generation
- `tests/test_cookiecutter_json.py` - Validates cookiecutter.json

## Required Template Components

### 1. Core Template Structure
```
claude-code-guardrails-template/
├── cookiecutter.json                    # Template variables
├── hooks/                              # Pre/post generation hooks
│   ├── pre_gen_project.py
│   └── post_gen_project.py
├── {{cookiecutter.project_slug}}/      # Template directory
│   ├── .claude/
│   │   ├── CLAUDE.md                   # Claude behavior contract
│   │   ├── golden-paths.md             # Development patterns
│   │   └── auto-context.yaml           # Context configuration
│   ├── .github/workflows/
│   │   ├── ci.yml                      # Rendered CI workflow
│   │   ├── validate-claude-guardrails.yml
│   │   └── branch-naming.yml
│   ├── scripts/
│   │   └── validate_claude_constraints.py
│   ├── CLAUDE.md                       # Project-level reference
│   └── ...
└── tests/                              # Template tests
    ├── test_template_syntax.py
    ├── test_hooks.py
    └── test_template_generation.py
```

### 2. Cookiecutter Variables (`cookiecutter.json`)
Define variables like:
```json
{
    "project_name": "My Project",
    "project_slug": "{{ cookiecutter.project_name.lower().replace(' ', '_').replace('-', '_') }}",
    "primary_language": ["python", "javascript", "typescript", "go", "rust"],
    "dependency_manager_python": ["uv", "poetry", "pip"],
    "linter_python": ["ruff", "flake8"],
    "testing_framework_python": ["pytest", "unittest"],
    "include_ci_cd": ["yes", "no"],
    "cloud_provider": ["none", "gcp", "aws", "azure"],
    "enable_security_scanning": ["yes", "no"],
    "enable_code_coverage": ["yes", "no"]
}
```

## Template-Specific Workflows

### 1. Template Testing Workflows
These should exist in the template repository (NOT in generated projects):

**`.github/workflows/test-template.yml`**:
```yaml
name: Test Template
on:
  pull_request:
    branches: [ main ]
jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.10', '3.11', '3.12']
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    - name: Install dependencies
      run: |
        pip install cookiecutter pytest pyyaml
    - name: Run template tests
      run: |
        pytest tests/ -v
```

### 2. Generated Project Workflows
These go in `{{cookiecutter.project_slug}}/.github/workflows/`:

**Template for `ci.yml`**:
```yaml
name: CI
on:
  pull_request:
    branches: [ main, dev ]
jobs:
{% if cookiecutter.primary_language == "python" -%}
  test-python:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.12"
    {% if cookiecutter.dependency_manager_python == "uv" -%}
    - name: Install uv
      uses: astral-sh/setup-uv@v4
    - name: Install dependencies
      run: |
        uv sync
        uv sync --group dev
    - name: Run linting
      run: |
        {% if cookiecutter.linter_python == "ruff" -%}
        uv run ruff check .
        uv run ruff format --check .
        {% endif -%}
    - name: Run tests
      run: |
        uv run pytest --cov --cov-report=xml
    {% endif -%}
    - name: Run Claude constraints validation
      run: |
        uv run python scripts/validate_claude_constraints.py
{% endif -%}
```

## Implementation Steps

### Phase 1: Template Structure Setup
1. **Create/verify cookiecutter.json** with all necessary variables
2. **Set up template directory structure** under `{{cookiecutter.project_slug}}/`
3. **Create cookiecutter hooks** for pre/post generation validation
4. **Template the .claude/ directory** with proper variable substitution

### Phase 2: Workflow Templates
1. **Create templated CI workflows** with cookiecutter conditionals
2. **Template the Claude constraints validator** to work for any generated project
3. **Ensure guardrails workflow** templates correctly
4. **Test variable substitution** in all templated files

### Phase 3: Template Testing
1. **Write comprehensive template tests**:
   - Template syntax validation
   - Variable substitution correctness
   - Generated project structure validation
   - Generated CI workflow functionality
2. **Set up template CI workflows** (separate from generated project workflows)
3. **Test template generation** with various variable combinations

### Phase 4: Generated Project Validation
1. **Test generated projects** across different configurations
2. **Validate CI workflows work** in generated projects
3. **Ensure Claude constraints work** in generated projects
4. **Test Docker builds** and other features in generated projects

## Common Pitfalls to Avoid

### 1. Template vs Generated Project Confusion
- **Template repository** contains cookiecutter.json and template tests
- **Generated projects** contain actual project code and CI workflows
- Don't mix template-testing workflows with generated project workflows

### 2. Variable Substitution Issues
- Test all cookiecutter variables actually substitute correctly
- Handle edge cases like special characters in project names
- Validate that conditional blocks render properly

### 3. CI Workflow Complexity
- Keep generated CI workflows simple and focused
- Avoid complex nested conditionals that are hard to debug
- Test generated workflows actually work, not just template syntax

### 4. Validation Script Portability
- Ensure `validate_claude_constraints.py` works across different project types
- Handle different dependency managers, languages, and structures
- Exclude appropriate directories (node_modules, .venv, etc.)

## Testing Strategy

### 1. Unit Tests
- Template syntax validation
- Variable substitution correctness
- Hook functionality

### 2. Integration Tests
- Full template generation with various configurations
- Generated project CI workflow execution
- Cross-platform compatibility

### 3. End-to-End Tests
- Generate projects and run their CI locally
- Test Docker builds of generated projects
- Validate Claude constraints in generated projects

## Success Criteria
1. **Template generates valid projects** for all supported configurations
2. **Generated projects pass CI** on GitHub Actions
3. **Template tests pass** on multiple platforms and Python versions
4. **No legacy template artifacts** remain in generated projects
5. **Claude constraints validation works** in all generated projects

## Next Actions When You Resume
1. Navigate to the **claude-code-guardrails-template** repository
2. Run the **Current State Assessment** commands above
3. Follow the **Implementation Steps** in order
4. Reference the **template-migration-fixes.md** for lessons learned
5. Test thoroughly before releasing template updates

This plan ensures you avoid the template-to-project confusion we just solved and build a robust, well-tested cookiecutter template.
