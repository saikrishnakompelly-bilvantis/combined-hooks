#!/bin/bash

# Setup script for API validation git hooks

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to detect Python command
detect_python() {
    if command -v python3 &> /dev/null; then
        echo "python3"
    elif command -v python &> /dev/null; then
        # Check if it's Python 3
        if python --version 2>&1 | grep -q "Python 3"; then
            echo "python"
        else
            echo ""
        fi
    else
        echo ""
    fi
}

echo -e "${BLUE}Setting up API Validation Git Hooks...${NC}"

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo -e "${RED}Error: Not in a git repository. Please run this script from the root of your git repository.${NC}"
    exit 1
fi

# Create .git/hooks directory if it doesn't exist
mkdir -p .git/hooks

# Copy and make hooks executable
echo -e "${YELLOW}Installing pre-commit hook...${NC}"
cp "$PROJECT_ROOT/hooks/pre-commit" .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

echo -e "${YELLOW}Installing pre-push hook...${NC}"
cp "$PROJECT_ROOT/hooks/pre-push" .git/hooks/pre-push
chmod +x .git/hooks/pre-push

# Check Python dependencies
echo -e "${YELLOW}Checking Python dependencies...${NC}"
PYTHON_CMD=$(detect_python)
if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}Error: Python 3 is not installed or not in PATH${NC}"
    echo -e "${YELLOW}Please install Python 3 (python3 or python command)${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python detected: $PYTHON_CMD${NC}"

# All functionality uses Python standard library only - no external packages needed

# Test the API identifier
echo -e "${YELLOW}Testing API type identification...${NC}"
cd "$PROJECT_ROOT"
$PYTHON_CMD -m validation.api_validator --identify-only

echo -e "${GREEN}✓ Git hooks installed successfully!${NC}"
echo -e "${BLUE}Hooks installed:${NC}"
echo -e "  - pre-commit: Validates staged files before commit"
echo -e "  - pre-push: Comprehensive validation before push"
echo -e ""
echo -e "${BLUE}Usage:${NC}"
echo -e "  - Hooks will run automatically during git commit and git push"
echo -e "  - To run validation manually: $PYTHON_CMD -m validation.api_validator --files <file1> <file2>"
echo -e "  - To identify API type: $PYTHON_CMD -m validation.api_validator --identify-only"
echo -e ""
echo -e "${GREEN}Setup complete!${NC}" 