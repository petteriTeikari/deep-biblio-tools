#!/bin/bash
# Script to run tests in Docker environment matching GitHub Actions

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running tests in Docker environment...${NC}"

# Build the Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -f Dockerfile.test -t deep-biblio-tools-test . || {
    echo -e "${RED}Failed to build Docker image${NC}"
    exit 1
}

# Run linting
echo -e "\n${YELLOW}Running linting checks...${NC}"
docker run --rm deep-biblio-tools-test sh -c "uv run ruff check . && uv run ruff format --check ." || {
    echo -e "${RED}Linting failed!${NC}"
    echo -e "${YELLOW}To fix formatting issues, run:${NC}"
    echo -e "  docker-compose -f docker-compose.test.yml run format"
    exit 1
}

# Run tests
echo -e "\n${YELLOW}Running tests...${NC}"
docker run --rm deep-biblio-tools-test uv run pytest tests/ -v || {
    echo -e "${RED}Tests failed!${NC}"
    exit 1
}

# Run Claude constraints validation
echo -e "\n${YELLOW}Running Claude constraints validation...${NC}"
docker run --rm deep-biblio-tools-test uv run python scripts/validate_claude_constraints.py || {
    echo -e "${RED}Claude constraints validation failed!${NC}"
    exit 1
}

echo -e "\n${GREEN}All tests passed!${NC}"
