# Cookiecutter Template Fixes - Detailed Implementation Plan

## Context for Future Claude Sessions

This plan addresses systematic issues discovered during the first migration from an existing repository to the Claude Guardrails cookiecutter template. Every issue here represents a **guaranteed failure** for future users unless fixed in the template.

**Template Location**: `../claude-code-guardrails-template`
**Priority**: CRITICAL - These fixes prevent template from working at all

## Phase 1: Critical File Generation Fixes

### 1.1 Missing .claude/auto-context.yaml
**Issue**: GitHub Actions fail with "Missing required Claude Code guardrail files"
**Root Cause**: Template doesn't generate this required file

**Implementation Steps**:
```bash
cd ../claude-code-guardrails-template
```

1. **Create template file**: `{{cookiecutter.project_slug}}/.claude/auto-context.yaml`
2. **Content template**:
```yaml
# Claude Code Auto-Context Configuration
project:
  name: "{{cookiecutter.project_name}}"
  type: "{{cookiecutter.project_type}}"
  language: "{{cookiecutter.language}}"
  framework: "{{cookiecutter.framework|default('none')}}"
  description: "{{cookiecutter.description}}"

context_files:
  always_include:
    - "CLAUDE.md"
    - ".claude/CLAUDE.md"
    - ".claude/golden-paths.md"
    - "pyproject.toml"
    - "README.md"

  conditional:
    api:
      - "src/{{cookiecutter.package_name}}/api/**/*.py"
    core:
      - "src/{{cookiecutter.package_name}}/core/**/*.py"
    utils:
      - "src/{{cookiecutter.package_name}}/utils/**/*.py"
    tests:
      - "tests/**/*.py"
    config:
      - "src/{{cookiecutter.package_name}}/config.py"
      - "src/{{cookiecutter.package_name}}/__init__.py"

patterns:
  related_files:
    "*.py": ["*_test.py", "test_*.py"]
    "src/**/*.py": ["tests/**/test_*.py"]

  exclude:
    - "**/__pycache__/**"
    - "**/.pytest_cache/**"
    - "**/node_modules/**"
    - "**/.venv/**"
    - "**/*.log"

session_management:
  update_current_session: true
  session_file: ".claude/sessions/current-session.md"
  capture_learnings: true
  learnings_file: ".claude/sessions/learnings.md"

integrations:
  github_actions: true
  docker: true
  pytest: true
  ruff: true
```

3. **Test**: Generate new project and verify file exists
4. **Validate**: Check GitHub Actions pass with this file

### 1.2 Dependency Group Standardization
**Issue**: GitHub Actions expect `test` group, template generates `dev` group
**Root Cause**: Inconsistency between pyproject.toml template and CI workflows

**Implementation Steps**:

1. **Update pyproject.toml template**:
```toml
[project.optional-dependencies]
dev = [
    {% if cookiecutter.language == "python" -%}
    "mypy>=1.7.0",
    "ruff>=0.1.6",
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.0",
    {%- endif %}
]
# ADD THIS - GitHub Actions expects 'test' group
test = [
    {% if cookiecutter.language == "python" -%}
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.0",
    {%- endif %}
]

[tool.uv]
dev-dependencies = [
    {% if cookiecutter.language == "python" -%}
    "mypy>=1.7.0",
    "ruff>=0.1.6",
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.21.0",
    {%- endif %}
]
```

2. **Update GitHub Actions workflow** to be consistent:
```yaml
- name: Install dependencies
  run: |
    uv sync --no-install-project
    uv sync --group test --no-install-project  # Use 'test' group
```

3. **Test**: Verify both `dev` and `test` groups work identically

### 1.3 Python Version Consistency
**Issue**: No `requires-python` field causes version conflicts between lock file and Docker
**Root Cause**: Template doesn't specify Python version requirements

**Implementation Steps**:

1. **Add to cookiecutter.json**:
```json
{
    "python_version": "3.12",
    "python_min_version": ">=3.12"
}
```

2. **Update pyproject.toml template**:
```toml
[project]
name = "{{cookiecutter.project_slug}}"
dynamic = ["version"]
description = "{{cookiecutter.description}}"
readme = "README.md"
license = "{{cookiecutter.license}}"
requires-python = "{{cookiecutter.python_min_version}}"  # ADD THIS LINE
authors = [
    {name = "{{cookiecutter.author_name}}", email = "{{cookiecutter.author_email}}"},
]
```

3. **Update Dockerfile template**:
```dockerfile
FROM python:{{cookiecutter.python_version}}-slim AS builder
```

4. **Test**: Generate project, check uv.lock has correct Python version

## Phase 2: Docker Strategy Fixes

### 2.1 Virtual Environment Portability
**Issue**: uv creates non-portable virtual environments with absolute paths
**Root Cause**: uv symlinks break in containers

**Implementation Options** (Choose one):

#### Option A: No-install-project approach (Recommended)
```dockerfile
# In Dockerfile template
RUN pip install uv && uv sync --frozen --no-dev --no-install-project

# Copy virtual environment
COPY --from=builder /app/.venv /app/.venv

# Install project in final stage
RUN /app/.venv/bin/pip install -e .
```

#### Option B: Pure pip fallback
```dockerfile
# Generate requirements.txt as backup
RUN uv export --no-dev > requirements.txt
RUN pip install -r requirements.txt
```

**Implementation Steps**:
1. Update Dockerfile template with chosen approach
2. Test Docker build succeeds
3. Test container runs correctly
4. Document the chosen strategy

### 2.2 Application Entry Point Generation
**Issue**: No main.py generated for web applications
**Root Cause**: Template doesn't create application entry points

**Implementation Steps**:

1. **Add to cookiecutter.json**:
```json
{
    "create_main_app": ["yes", "no"],
    "framework": ["fastapi", "flask", "django", "none"]
}
```

2. **Create conditional main.py template**:
```
{{cookiecutter.project_slug}}/src/{{cookiecutter.package_name}}/{% if cookiecutter.create_main_app == "yes" %}main.py{% endif %}
```

3. **FastAPI main.py content**:
```python
"""{{cookiecutter.framework|title}} application entry point for {{cookiecutter.project_name}}."""

{% if cookiecutter.framework == "fastapi" -%}
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="{{cookiecutter.project_name}}",
    description="{{cookiecutter.description}}",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "{{cookiecutter.project_name}} API",
        "version": "0.1.0",
        "docs": "/docs",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "{{cookiecutter.project_slug}}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
{%- endif %}
```

4. **Update Dockerfile CMD**:
```dockerfile
{% if cookiecutter.create_main_app == "yes" and cookiecutter.framework == "fastapi" -%}
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "src.{{cookiecutter.package_name}}.main:app", "--host", "0.0.0.0", "--port", "8000"]
{%- else -%}
CMD ["python", "-c", "print('No main application configured')"]
{%- endif %}
```

## Phase 3: Comprehensive Testing

### 3.1 Template Validation Scripts
**Create**: `scripts/validate-template.py` in template repo

```python
#!/usr/bin/env python3
"""Validate cookiecutter template generates working projects."""

import subprocess
import tempfile
import shutil
from pathlib import Path

def test_template_generation():
    """Test that template generates without errors."""
    # Implementation here

def test_required_files_exist():
    """Test all required Claude Guardrails files exist."""
    required_files = [
        ".claude/CLAUDE.md",
        ".claude/golden-paths.md",
        ".claude/auto-context.yaml",
        "CLAUDE.md"
    ]
    # Implementation here

def test_dependencies_install():
    """Test that dependencies install correctly."""
    # Implementation here

def test_docker_build():
    """Test that Docker build succeeds."""
    # Implementation here

def test_github_actions():
    """Test GitHub Actions workflow syntax."""
    # Implementation here

if __name__ == "__main__":
    test_template_generation()
    test_required_files_exist()
    test_dependencies_install()
    test_docker_build()
    test_github_actions()
    print("✅ All template validation tests passed!")
```

### 3.2 Integration Tests
**Create**: `tests/test_integration.py`

1. **Test multiple Python versions**: 3.12, 3.13
2. **Test multiple project types**: library, service, application
3. **Test different frameworks**: FastAPI, Flask, none
4. **Test Docker builds for each combination**
5. **Test GitHub Actions for each combination**

### 3.3 Continuous Validation
**Add to template CI/CD**:
```yaml
name: Template Validation
on: [push, pull_request]

jobs:
  validate-template:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]
        project-type: ["library", "service"]
        framework: ["fastapi", "none"]

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        pip install cookiecutter

    - name: Generate test project
      run: |
        cookiecutter . --no-input \
          project_name="Test Project" \
          python_version="${{ matrix.python-version }}" \
          project_type="${{ matrix.project-type }}" \
          framework="${{ matrix.framework }}"

    - name: Test generated project
      run: |
        cd test-project
        python scripts/validate-template.py
```

## Phase 4: Documentation and Migration Tools

### 4.1 Migration Guide
**Create**: `MIGRATION.md` in template repo

```markdown
# Migrating Existing Projects to Claude Guardrails Template

## Pre-Migration Checklist
- [ ] Backup existing project
- [ ] Run pre-migration validation
- [ ] Check Python version compatibility
- [ ] Verify dependency group naming

## Step-by-Step Migration
1. Generate new project structure
2. Copy functional code
3. Update configuration files
4. Test local functionality
5. Test Docker build
6. Test CI/CD pipeline

## Common Issues and Solutions
[Document all issues we found today]
```

### 4.2 Pre-Migration Validation Tool
**Create**: `scripts/pre-migration-check.py`

```python
def check_required_files():
    """Check if all required files will be generated."""

def check_python_version():
    """Check Python version compatibility."""

def check_dependency_groups():
    """Check dependency group consistency."""

def check_docker_compatibility():
    """Check Docker configuration."""
```

## Implementation Priority Order

### Critical (Do First)
1. ✅ Fix missing auto-context.yaml
2. ✅ Add requires-python to pyproject.toml
3. ✅ Standardize dependency groups
4. ✅ Fix Docker virtual environment issues

### High Priority (Do Next)
5. Create application entry point generation
6. Build template validation scripts
7. Add comprehensive integration tests
8. Update CI/CD to test template changes

### Medium Priority (After Core Works)
9. Create migration guide and tools
10. Add pre-migration validation
11. Document common issues and solutions
12. Build organizational rollout tools

## Success Criteria

### Template Generation Test
```bash
# This should work without any manual fixes
cookiecutter ../claude-code-guardrails-template
cd [generated-project]
uv sync
uv run pytest
docker build -t test .
docker run test
```

### GitHub Actions Test
- All workflows pass without modification
- No missing file errors
- Dependencies install correctly
- Tests run successfully

### Migration Test
- Existing project migrates successfully
- All functionality preserved
- No manual configuration needed
- Documentation is clear and complete

## Notes for Future Claude Sessions

When working on the template:
1. **Always test the full pipeline**: generation → dependencies → tests → Docker → CI/CD
2. **Test multiple project types**: Don't assume one configuration works for all
3. **Validate with fresh environment**: Template issues only show up in clean environments
4. **Document every fix**: Each issue will help other users
5. **Prioritize automation**: Manual steps will be forgotten or done incorrectly

The goal is a template that works perfectly on first generation, requiring zero manual fixes for common use cases.
