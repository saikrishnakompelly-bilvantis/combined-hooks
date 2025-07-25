#!/bin/bash

# Simple Git Hooks Installation Script
# Copies hooks to ~/.genie/hooks and sets git core.hooksPath

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
GENIE_DIR="$HOME/.genie"
HOOKS_DIR="$GENIE_DIR/hooks"

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                     UNIFIED GIT HOOKS INSTALLER              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Get the script directory (where this install.sh is located)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

echo -e "${BLUE}📁 Creating .genie directory...${NC}"
mkdir -p "$HOOKS_DIR"

echo -e "${BLUE}📋 Copying hooks directory...${NC}"
if [ -d "$SCRIPT_DIR/hooks" ]; then
    cp -r "$SCRIPT_DIR/hooks/"* "$HOOKS_DIR/"
    
    # Make all hook files executable
    find "$HOOKS_DIR" -type f -exec chmod +x {} \;
    
    echo -e "${GREEN}✅ Hooks copied to $HOOKS_DIR${NC}"
else
    echo -e "${RED}❌ Hooks directory not found at $SCRIPT_DIR/hooks${NC}"
    exit 1
fi

echo -e "${BLUE}⚙️  Setting git core.hooksPath...${NC}"
git config --global core.hooksPath "$HOOKS_DIR"

echo -e "${GREEN}✅ Git configured to use hooks from $HOOKS_DIR${NC}"

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                   INSTALLATION COMPLETE!                     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}🎉 Hooks installed successfully!${NC}"
echo -e "${CYAN}📁 Hooks Directory:${NC} $HOOKS_DIR"
echo -e "${CYAN}⚙️  Git Config:${NC} core.hooksPath = $HOOKS_DIR"
echo ""
echo -e "${GREEN}🚀 All git repositories will now use these hooks!${NC}" 