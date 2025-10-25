# Standards Documentation

This directory contains coding standards, style guides, and best practices for the Deep Biblio Tools project.

## 📏 Available Standards

- **[Ruff Best Practices](ruff-best-practices.md)** - Code formatting and linting standards using Ruff

## 🎯 Standards Overview

### Code Quality Standards
- **Linting**: Ruff with strict configuration
- **Formatting**: Ruff format (Black-compatible)
- **Type Hints**: Required for all public functions
- **Documentation**: Docstrings for all modules, classes, and public functions

### Bibliography Processing Standards
- **Citation Keys**: Follow `AuthorYEAR` or `AuthorYEARa` format
- **Author Names**: `Last, First` format with proper handling of prefixes
- **Date Format**: ISO 8601 (YYYY-MM-DD) for all dates
- **DOI Format**: Lowercase, no URL prefix (just `10.xxxx/yyyy`)

### Testing Standards
- **Coverage**: Minimum 80% for new code
- **Test Types**: Unit, integration, and end-to-end tests
- **Test Names**: Descriptive `test_function_scenario_expected` format
- **Fixtures**: Use pytest fixtures for common test data

### Documentation Standards
- **README Files**: Every directory should have a README
- **Markdown Format**: Use GitHub-flavored markdown
- **Code Examples**: Include working examples in documentation
- **Update Policy**: Update docs with code changes

### Git Standards
- **Commit Messages**: Conventional commits format
  - `feat:` for new features
  - `fix:` for bug fixes
  - `docs:` for documentation
  - `refactor:` for code refactoring
  - `test:` for test additions/changes
- **Branch Names**: `type/description` (e.g., `feat/batch-processing`)
- **PR Size**: Keep PRs focused and under 500 lines when possible

## 🛠️ Tool Configuration

### Ruff Configuration
```toml
[tool.ruff]
target-version = "py312"
line-length = 80
src = ["src"]
```

### Pre-commit Hooks
- Ruff check and format
- Type checking with mypy
- Import sorting
- Trailing whitespace removal

## 📋 Compliance

All code must pass:
1. `uv run ruff check --fix`
2. `uv run ruff format`
3. `uv run mypy src`
4. `uv run pytest`

## 🔄 Updating Standards

Standards evolve with the project. When proposing changes:
1. Document the rationale
2. Update relevant configuration files
3. Update this README
4. Communicate changes to the team

## 🎓 Learning Resources

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [GitHub Flavored Markdown](https://guides.github.com/features/mastering-markdown/)
