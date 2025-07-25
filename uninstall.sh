#!/bin/bash

# Combined Genie - Quick Uninstaller
# This script calls the main uninstall script from ~/.genie

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

GENIE_DIR="$HOME/.genie"

echo -e "${BLUE}Combined Genie - Quick Uninstaller${NC}"
echo ""

# Check if Genie is installed
if [ ! -d "$GENIE_DIR" ]; then
    echo -e "${YELLOW}⚠️  Genie is not installed (no ~/.genie directory found)${NC}"
    exit 0
fi

# Check if uninstall script exists
if [ ! -f "$GENIE_DIR/uninstall.sh" ]; then
    echo -e "${RED}❌ Genie uninstall script not found${NC}"
    echo -e "${YELLOW}💡 You can manually remove: rm -rf ~/.genie${NC}"
    echo -e "${YELLOW}   And reset git config: git config --global --unset core.hooksPath${NC}"
    exit 1
fi

# Run the actual uninstall script
echo -e "${BLUE}🔄 Running Genie uninstaller...${NC}"
exec "$GENIE_DIR/uninstall.sh" 