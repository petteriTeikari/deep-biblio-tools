#!/bin/bash
# Setup script for regex enforcement in deep-biblio-tools

set -e

echo "Setting up regex enforcement for deep-biblio-tools..."

# Check if we're in the right directory
if [[ ! -f "pyproject.toml" ]]; then
    echo "Error: Must be run from project root directory"
    exit 1
fi

# Install pre-commit if not already installed
echo "Installing pre-commit..."
if ! command -v pre-commit &> /dev/null; then
    echo "Installing pre-commit via pip..."
    pip install pre-commit
else
    echo "pre-commit already installed"
fi

# Install the pre-commit hooks
echo "Installing pre-commit hooks..."
pre-commit install

# Run the hooks on all files to check current status
echo "Running initial check on all files..."
pre-commit run --all-files || {
    echo "Some hooks failed on existing files."
    echo "This is expected if there are existing issues to fix."
    echo ""
    echo "To fix issues automatically where possible:"
    echo "  pre-commit run --all-files --hook-stage manual"
    echo ""
    echo "To check specific files:"
    echo "  pre-commit run --files src/path/to/file.py"
}

echo ""
echo "Regex enforcement setup complete!"
echo ""
echo "What was configured:"
echo "   - Pre-commit hooks installed"
echo "   - Comprehensive regex policy enforcement"
echo "   - Automatic ruff linting and formatting"
echo "   - File naming conventions enforcement"
echo "   - Code quality checks"
echo ""
echo "To manually run regex enforcement:"
echo "   python scripts/enforce_no_regex_policy.py"
echo ""
echo "To run compliance tests:"
echo "   PYTHONPATH=. python tests/test_regex_compliance.py"
echo ""
echo "The hooks will now run automatically on every commit!"
echo "   To bypass temporarily (not recommended):"
echo "   git commit --no-verify"
echo ""
echo "For more information, see:"
echo "   - docs/development/regex-removal-best-practices.md"
echo "   - .claude/ast-regex-refactoring-guidelines.md"
