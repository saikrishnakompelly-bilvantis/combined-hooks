#!/bin/bash

# API Genie - Quick Uninstaller
# This script calls the main uninstall script from ~/.apigenie

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

APIGENIE_DIR="$HOME/.apigenie"

echo -e "${BLUE}API Genie - Quick Uninstaller${NC}"
echo ""

# Check if API Genie is installed
if [ ! -d "$APIGENIE_DIR" ]; then
    echo -e "${YELLOW}⚠️  API Genie is not installed (no ~/.apigenie directory found)${NC}"
    exit 0
fi

# Check if uninstall script exists
if [ ! -f "$APIGENIE_DIR/uninstall.sh" ]; then
    echo -e "${RED}❌ API Genie uninstall script not found${NC}"
    echo -e "${YELLOW}💡 You can manually remove: rm -rf ~/.apigenie${NC}"
    echo -e "${YELLOW}   And reset git config: git config --global --unset core.hooksPath${NC}"
    exit 1
fi

# Run the actual uninstall script
echo -e "${BLUE}🔄 Running API Genie uninstaller...${NC}"
exec "$APIGENIE_DIR/uninstall.sh" 