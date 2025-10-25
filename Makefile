.PHONY: test test-parallel test-coverage lint format all

# Run tests normally (sequential)
test:
	uv run pytest

# Run tests in parallel using all available CPU cores
test-parallel:
	uv run pytest -n auto

# Run tests in parallel with coverage
test-coverage:
	uv run pytest -n auto --cov --cov-report=xml --cov-report=term

# Run linters
lint:
	uv run ruff check --fix
	uv run mypy src

# Format code
format:
	uv run ruff format

# Run everything
all: format lint test-parallel
