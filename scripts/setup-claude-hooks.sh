#!/bin/bash
"""
Setup Claude Code Git Hooks

This script installs git hooks that enforce Claude Code guardrails and constraints
during development workflow.

Usage:
    ./scripts/setup-claude-hooks.sh
    ./scripts/setup-claude-hooks.sh --force  # Overwrite existing hooks
"""

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_DIR="${PROJECT_ROOT}/.git/hooks"
FORCE_INSTALL=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_INSTALL=true
            shift
            ;;
        -h|--help)
            echo "Setup Claude Code Git Hooks"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --force    Overwrite existing hooks"
            echo "  -h, --help Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if we're in a git repository
if [[ ! -d "${PROJECT_ROOT}/.git" ]]; then
    echo "[EMOJI] Error: Not in a git repository"
    exit 1
fi

# Check if required files exist
REQUIRED_FILES=(
    ".claude/CLAUDE.md"
    ".claude/golden-paths.md"
    "scripts/validate_claude_constraints.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "${PROJECT_ROOT}/${file}" ]]; then
        echo "[EMOJI] Error: Required file missing: ${file}"
        exit 1
    fi
done

echo "[EMOJI] Setting up Claude Code git hooks..."

# Create hooks directory if it doesn't exist
mkdir -p "${HOOKS_DIR}"

# Pre-commit hook
PRE_COMMIT_HOOK="${HOOKS_DIR}/pre-commit"

if [[ -f "${PRE_COMMIT_HOOK}" ]] && [[ "${FORCE_INSTALL}" != true ]]; then
    echo "[EMOJI]  Pre-commit hook already exists. Use --force to overwrite."
else
    echo "[EMOJI] Installing pre-commit hook..."
    cat > "${PRE_COMMIT_HOOK}" << 'EOF'
#!/bin/bash
# Claude Code Pre-commit Hook
# Validates Claude Code constraints before allowing commits

set -e

PROJECT_ROOT="$(git rev-parse --show-toplevel)"

echo "[EMOJI] Running Claude Code constraints validation..."

# Run Claude constraints validation
if ! uv run python "${PROJECT_ROOT}/scripts/validate_claude_constraints.py" --check-only; then
    echo ""
    echo "[EMOJI] Claude Code constraints validation failed!"
    echo "[EMOJI] Run 'python scripts/validate_claude_constraints.py' for details"
    echo "[EMOJI] Use '# noqa: claude' to suppress specific violations"
    echo "[EMOJI] Use 'HUMAN-OVERRIDE: [reason]' in commit message for architectural changes"
    exit 1
fi

# Check for AIDEV tag violations in staged files
echo "[EMOJI] Checking AIDEV markers in staged files..."

# Get list of staged files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=M)

for file in $STAGED_FILES; do
    if [[ -f "$file" ]]; then
        # Check if file contains AIDEV-IMMUTABLE markers
        if grep -q "AIDEV-IMMUTABLE" "$file"; then
            # Check if there are changes within immutable blocks
            if git diff --cached "$file" | grep -A5 -B5 "AIDEV-IMMUTABLE" | grep -q "^[+-]"; then
                echo "[EMOJI] Attempted to modify AIDEV-IMMUTABLE section in: $file"
                echo "[EMOJI] These sections are protected and require manual review"
                exit 1
            fi
        fi
    fi
done

# Check for AIDEV-REPLACEMENT-TODO markers that should be addressed before push
if git grep -n "AIDEV-REPLACEMENT-TODO" -- ':!scripts/validate_claude_constraints.py'; then
    echo "[EMOJI]  Found AIDEV-REPLACEMENT-TODO markers that should be addressed before push"
    echo "[EMOJI] Consider resolving these or updating them to AIDEV-NOTE if intentional"
fi

# Check for AIDEV-GENERATED-TEST markers requiring review
if git grep -n "AIDEV-GENERATED-TEST" -- ':!scripts/validate_claude_constraints.py'; then
    echo "[EMOJI] Found AIDEV-GENERATED-TEST markers requiring human review"
    echo "[EMOJI] Ensure these AI-generated tests have been reviewed before deployment"
fi

# Run pre-commit hooks if they exist
if command -v pre-commit &> /dev/null; then
    echo "[EMOJI] Running pre-commit hooks..."
    pre-commit run --files $STAGED_FILES
fi

echo "[EMOJI] Claude Code validation passed!"

EOF

    chmod +x "${PRE_COMMIT_HOOK}"
    echo "[EMOJI] Pre-commit hook installed"
fi

# Commit-msg hook
COMMIT_MSG_HOOK="${HOOKS_DIR}/commit-msg"

if [[ -f "${COMMIT_MSG_HOOK}" ]] && [[ "${FORCE_INSTALL}" != true ]]; then
    echo "[EMOJI]  Commit-msg hook already exists. Use --force to overwrite."
else
    echo "[EMOJI] Installing commit-msg hook..."
    cat > "${COMMIT_MSG_HOOK}" << 'EOF'
#!/bin/bash
# Claude Code Commit Message Hook
# Validates commit message format and checks for override syntax

set -e

COMMIT_MSG_FILE="$1"
COMMIT_MSG=$(cat "$COMMIT_MSG_FILE")

# Check for HUMAN-OVERRIDE syntax
if echo "$COMMIT_MSG" | grep -q "HUMAN-OVERRIDE:"; then
    echo "[EMOJI] HUMAN-OVERRIDE detected in commit message"
    echo "[EMOJI]  This commit bypasses some Claude Code constraints"

    # Validate HUMAN-OVERRIDE format
    if ! echo "$COMMIT_MSG" | grep -q "HUMAN-OVERRIDE: \[.*\]"; then
        echo "[EMOJI] Invalid HUMAN-OVERRIDE format"
        echo "[EMOJI] Use: HUMAN-OVERRIDE: [reason] - your commit message"
        exit 1
    fi

    echo "[EMOJI] HUMAN-OVERRIDE format is valid"
    exit 0
fi

# Check for conventional commit format (optional)


# Check for TODO/FIXME in commit message
if echo "$COMMIT_MSG" | grep -qi "TODO\|FIXME"; then
    echo "[EMOJI]  Commit message contains TODO/FIXME - consider creating an issue instead"
fi

echo "[EMOJI] Commit message validation passed!"

EOF

    chmod +x "${COMMIT_MSG_HOOK}"
    echo "[EMOJI] Commit-msg hook installed"
fi

# Pre-push hook (optional, for critical projects)


echo ""
echo "[EMOJI] Claude Code git hooks setup complete!"
echo ""
echo "Installed hooks:"
echo "  [EMOJI] pre-commit  - Validates constraints before commits"
echo "  [EMOJI] commit-msg  - Validates commit message format"

echo ""
echo "[EMOJI] Hooks will automatically run during git operations"
echo "[EMOJI] Use 'git commit --no-verify' to skip validation (not recommended)"
echo "[EMOJI] Use 'HUMAN-OVERRIDE: [reason]' in commit messages when needed"
echo ""
echo "[EMOJI] For more information, see:"
echo "   .claude/CLAUDE.md        - Complete behavior contract"
echo "   .claude/golden-paths.md  - Development patterns"
