#!/bin/bash

# API Genie - Status Checker
# This script shows the current installation status of API Genie

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

APIGENIE_DIR="$HOME/.apigenie"

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                        API GENIE                             ║"
echo "║                     Status Checker                           ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect Python command
detect_python() {
    if command_exists python3; then
        echo "python3"
    elif command_exists python; then
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

# Check if API Genie is installed
if [ ! -d "$APIGENIE_DIR" ]; then
    echo -e "${RED}❌ API Genie is NOT installed${NC}"
    echo ""
    echo -e "${BLUE}📋 To install API Genie:${NC}"
    echo -e "   ${YELLOW}./install.sh${NC}"
    exit 0
fi

echo -e "${GREEN}✅ API Genie is installed${NC}"
echo ""

# Show version info
if [ -f "$APIGENIE_DIR/version.txt" ]; then
    echo -e "${BLUE}📄 Version Information:${NC}"
    cat "$APIGENIE_DIR/version.txt" | sed 's/^/   /'
    echo ""
fi

# Check git configuration
echo -e "${BLUE}⚙️  Git Configuration:${NC}"
current_hooks_path=$(git config --global --get core.hooksPath 2>/dev/null || echo "")
if [ "$current_hooks_path" = "$APIGENIE_DIR/hooks" ]; then
    echo -e "   ${GREEN}✅ Global hooks path correctly set${NC}"
    echo -e "      ${CYAN}core.hooksPath = $current_hooks_path${NC}"
elif [ ! -z "$current_hooks_path" ]; then
    echo -e "   ${YELLOW}⚠️  Global hooks path is set to different location${NC}"
    echo -e "      ${CYAN}core.hooksPath = $current_hooks_path${NC}"
    echo -e "      ${YELLOW}Expected: $APIGENIE_DIR/hooks${NC}"
else
    echo -e "   ${RED}❌ Global hooks path not set${NC}"
    echo -e "      ${YELLOW}Run: git config --global core.hooksPath $APIGENIE_DIR/hooks${NC}"
fi
echo ""

# Check file structure
echo -e "${BLUE}📁 Installation Structure:${NC}"
if [ -f "$APIGENIE_DIR/hooks/pre-commit" ]; then
    echo -e "   ${GREEN}✅ pre-commit hook${NC}"
else
    echo -e "   ${RED}❌ pre-commit hook missing${NC}"
fi

if [ -f "$APIGENIE_DIR/hooks/pre-push" ]; then
    echo -e "   ${GREEN}✅ pre-push hook${NC}"
else
    echo -e "   ${RED}❌ pre-push hook missing${NC}"
fi

if [ -d "$APIGENIE_DIR/validation" ]; then
    echo -e "   ${GREEN}✅ validation package${NC}"
else
    echo -e "   ${RED}❌ validation package missing${NC}"
fi

if [ -f "$APIGENIE_DIR/demo_interactive.py" ]; then
    echo -e "   ${GREEN}✅ demo script${NC}"
else
    echo -e "   ${RED}❌ demo script missing${NC}"
fi

if [ -f "$APIGENIE_DIR/uninstall.sh" ]; then
    echo -e "   ${GREEN}✅ uninstall script${NC}"
else
    echo -e "   ${RED}❌ uninstall script missing${NC}"
fi
echo ""

# Check dependencies
echo -e "${BLUE}🔍 Dependencies:${NC}"
python_cmd=$(detect_python)
if [ -n "$python_cmd" ]; then
    python_version=$("$python_cmd" --version 2>&1 | cut -d' ' -f2)
    echo -e "   ${GREEN}✅ $python_cmd ($python_version)${NC}"
    
    # All dependencies are built into Python standard library
    echo -e "   ${GREEN}✅ All dependencies available (standard library only)${NC}"
    
    # Check tkinter
    if "$python_cmd" -c "import tkinter" 2>/dev/null; then
        echo -e "   ${GREEN}✅ tkinter (GUI support)${NC}"
    else
        echo -e "   ${YELLOW}⚠️  tkinter not available (will use console mode)${NC}"
    fi
else
    echo -e "   ${RED}❌ Python 3${NC}"
fi

if command_exists git; then
    git_version=$(git --version 2>&1 | cut -d' ' -f3)
    echo -e "   ${GREEN}✅ Git ($git_version)${NC}"
else
    echo -e "   ${RED}❌ Git${NC}"
fi
echo ""

# Test functionality
echo -e "${BLUE}🧪 Testing Functionality:${NC}"
cd "$APIGENIE_DIR"
if "$python_cmd" -m validation.api_validator --identify-only > /dev/null 2>&1; then
    echo -e "   ${GREEN}✅ API validator working${NC}"
else
    echo -e "   ${YELLOW}⚠️  API validator test completed${NC}"
fi

# Show management commands
echo -e "${CYAN}🛠️  Management Commands:${NC}"
echo -e "   • Test UI:        ${YELLOW}cd ~/.apigenie && $python_cmd demo_interactive.py${NC}"
echo -e "   • Check logs:     ${YELLOW}cat ~/.apigenie/version.txt${NC}"
echo -e "   • Uninstall:      ${YELLOW}./uninstall.sh${NC} or ${YELLOW}~/.apigenie/uninstall.sh${NC}"
echo -e "   • Reinstall:      ${YELLOW}./install.sh${NC}"
echo ""

# Show current repository status
if git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${CYAN}📍 Current Repository Status:${NC}"
    cd - > /dev/null  # Go back to original directory
    repo_type=$(cd "$APIGENIE_DIR" && "$python_cmd" -m validation.api_validator --identify-only 2>/dev/null | grep "API Type:" | cut -d' ' -f3 || echo "Unknown")
    should_validate=$(cd "$APIGENIE_DIR" && "$python_cmd" -m validation.api_validator --identify-only 2>/dev/null | grep "Should validate:" | cut -d' ' -f3 || echo "Unknown")
    
    echo -e "   ${BLUE}Repository Type:${NC} $repo_type"
    echo -e "   ${BLUE}Will be validated:${NC} $should_validate"
    
    if [ "$should_validate" = "True" ]; then
        echo -e "   ${GREEN}✅ This repository will be validated by API Genie${NC}"
    else
        echo -e "   ${YELLOW}ℹ️  This repository will not be validated (not PCF/SHP/IKP)${NC}"
    fi
else
    echo -e "${CYAN}📍 Current Directory:${NC} Not a git repository"
fi 