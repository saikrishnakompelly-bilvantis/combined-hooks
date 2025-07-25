#!/bin/bash

# Unified Genie - Global Git Hooks Installation Script
# This script installs both Secret and API validation hooks globally for all git repositories

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
VALIDATION_DIR="$GENIE_DIR/validation"
SECRET_GENIE_DIR="$GENIE_DIR/secret-genie"

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    UNIFIED GENIE TOOLS                       ║"
echo "║          Global Git Hooks Installation (Secret + API)        ║"
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

# Function to backup existing global hooks path
backup_existing_hooks() {
    local current_hooks_path=$(git config --global --get core.hooksPath 2>/dev/null || echo "")
    if [ ! -z "$current_hooks_path" ]; then
        echo -e "${YELLOW}⚠️  Found existing global hooks path: $current_hooks_path${NC}"
        echo -e "${YELLOW}   This will be backed up to: $GENIE_DIR/backup_hooks_path.txt${NC}"
        
        # Create the directory if it doesn't exist
        mkdir -p "$GENIE_DIR"
        echo "$current_hooks_path" > "$GENIE_DIR/backup_hooks_path.txt"
    fi
}

# Function to create directory structure
create_directories() {
    echo -e "${BLUE}📁 Creating Unified Genie directory structure...${NC}"
    
    # Remove existing installation if it exists
    if [ -d "$GENIE_DIR" ]; then
        echo -e "${YELLOW}⚠️  Existing Genie installation found. Removing...${NC}"
        rm -rf "$GENIE_DIR"
    fi
    
    # Create directories
    mkdir -p "$HOOKS_DIR"
    mkdir -p "$VALIDATION_DIR"
    mkdir -p "$VALIDATION_DIR/ui"
    mkdir -p "$VALIDATION_DIR/validators"
    mkdir -p "$SECRET_GENIE_DIR/commit_scripts"
    mkdir -p "$SECRET_GENIE_DIR/commit_scripts/templates"
    
    echo -e "${GREEN}✅ Directory structure created${NC}"
}

# Function to copy validation files
copy_validation_files() {
    echo -e "${BLUE}📋 Copying validation system files...${NC}"
    
    # Get the script directory (where this install.sh is located)
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    
    # Find Secret-Genie directory (assuming it's in the same parent directory)
    SECRET_GENIE_SOURCE="$(dirname "$SCRIPT_DIR")/Secret-Genie/src"
    
    if [ ! -d "$SECRET_GENIE_SOURCE" ]; then
        echo -e "${RED}❌ Secret-Genie source directory not found at: $SECRET_GENIE_SOURCE${NC}"
        echo -e "${YELLOW}   Please ensure Secret-Genie is in the same parent directory as API-Genie${NC}"
        exit 1
    fi
    
    # Copy API validation package
    cp -r "$SCRIPT_DIR/validation/"* "$VALIDATION_DIR/"
    
    # Copy Secret-Genie validation files (from local Combined-Hooks)
    cp -r "$SCRIPT_DIR/secretgenie/commit_scripts/"* "$SECRET_GENIE_DIR/commit_scripts/"
    cp "$SCRIPT_DIR/secretgenie/commit_scripts/pre_push.py" "$SECRET_GENIE_DIR/commit_scripts/"
    
    # Copy the unified hooks
    cp "$SCRIPT_DIR/hooks/pre-push" "$HOOKS_DIR/"
    cp "$SCRIPT_DIR/hooks/pre-commit" "$HOOKS_DIR/"
    
    # Copy requirements and demo files
    cp "$SCRIPT_DIR/requirements.txt" "$GENIE_DIR/"
    if [ -f "$SCRIPT_DIR/demo_interactive.py" ]; then
        cp "$SCRIPT_DIR/demo_interactive.py" "$GENIE_DIR/"
    fi
    
    # Copy Secret-Genie requirements if they exist
    if [ -f "$SECRET_GENIE_SOURCE/../requirements.txt" ]; then
        # Merge requirements files
        cat "$SECRET_GENIE_SOURCE/../requirements.txt" >> "$GENIE_DIR/requirements.txt"
        # Remove duplicates
        sort "$GENIE_DIR/requirements.txt" | uniq > "$GENIE_DIR/requirements_temp.txt"
        mv "$GENIE_DIR/requirements_temp.txt" "$GENIE_DIR/requirements.txt"
    fi
    
    # Make hooks executable
    chmod +x "$HOOKS_DIR/pre-push"
    chmod +x "$HOOKS_DIR/pre-commit"
    
    echo -e "${GREEN}✅ Validation files copied${NC}"
}

# Function to create version info
create_version_info() {
    cat > "$GENIE_DIR/version.txt" << EOF
Unified Genie Tools Version 1.0.0
- Secret-Genie: Secret detection and validation
- API-Genie: API compliance validation
Installation Date: $(date)
Installation Path: $GENIE_DIR
Git Hooks Path: $HOOKS_DIR
EOF
}

# Function to create uninstall script
create_uninstall_script() {
    cat > "$GENIE_DIR/uninstall.sh" << 'EOF'
#!/bin/bash

# Unified Genie - Global Git Hooks Uninstallation Script

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

GENIE_DIR="$HOME/.genie"

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    UNIFIED GENIE TOOLS                       ║"
echo "║           Global Git Hooks Uninstallation                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${YELLOW}This will remove the global Secret and API validation hooks.${NC}"
echo -e "${YELLOW}Your repositories will no longer have automatic validation.${NC}"
echo ""
read -p "Are you sure you want to continue? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Uninstallation cancelled.${NC}"
    exit 0
fi

echo -e "${BLUE}🔧 Removing global git hooks configuration...${NC}"

# Remove global hooks path
git config --global --unset core.hooksPath

# Restore backup if it exists
if [ -f "$GENIE_DIR/backup_hooks_path.txt" ]; then
    backup_path=$(cat "$GENIE_DIR/backup_hooks_path.txt")
    echo -e "${YELLOW}📁 Restoring previous hooks path: $backup_path${NC}"
    git config --global core.hooksPath "$backup_path"
fi

echo -e "${BLUE}🗑️  Removing Unified Genie directory...${NC}"
rm -rf "$GENIE_DIR"

echo -e "${GREEN}✅ Unified Genie has been successfully uninstalled!${NC}"
echo -e "${BLUE}ℹ️  Your git repositories will now use default or local hooks.${NC}"
EOF

    chmod +x "$GENIE_DIR/uninstall.sh"
    echo -e "${GREEN}✅ Uninstall script created${NC}"
}

# Function to update hook paths in copied files
update_hook_paths() {
    echo -e "${BLUE}🔧 Updating hook file paths...${NC}"
    
    # Update pre-push hook to use the correct paths
    sed -i.bak "s|APIGENIE_ROOT=\"\$(dirname \"\$HOOK_DIR\")\"|GENIE_ROOT=\"$GENIE_DIR\"|g" "$HOOKS_DIR/pre-push"
    sed -i.bak "s|GENIE_ROOT=\"\$(dirname \"\$HOOK_DIR\")\"|GENIE_ROOT=\"$GENIE_DIR\"|g" "$HOOKS_DIR/pre-push"
    
    # Remove backup files
    rm -f "$HOOKS_DIR/pre-push.bak"
    
    echo -e "${GREEN}✅ Hook paths updated${NC}"
}

# Function to check dependencies
check_dependencies() {
    echo -e "${BLUE}🔍 Checking dependencies...${NC}"
    
    # Detect Python command
    PYTHON_CMD=$(detect_python)
    if [ -z "$PYTHON_CMD" ]; then
        echo -e "${RED}❌ Python 3 is required but not installed${NC}"
        echo -e "${YELLOW}   Please install Python 3 (python3 or python command)${NC}"
        exit 1
    fi
    
    # Check Git
    if ! command_exists git; then
        echo -e "${RED}❌ Git is required but not installed${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Python detected: $PYTHON_CMD${NC}"
    echo -e "${GREEN}✅ Dependencies checked${NC}"
}

# Function to configure git
configure_git() {
    echo -e "${BLUE}⚙️  Configuring global git hooks...${NC}"
    
    # Set global hooks path
    git config --global core.hooksPath "$HOOKS_DIR"
    
    echo -e "${GREEN}✅ Git configured to use Unified Genie hooks${NC}"
}

# Function to test installation
test_installation() {
    echo -e "${BLUE}🧪 Testing installation...${NC}"
    
    # Test API validator
    cd "$GENIE_DIR"
    if $PYTHON_CMD -m validation.api_validator --identify-only > /dev/null 2>&1; then
        echo -e "${GREEN}✅ API validator is working${NC}"
    else
        echo -e "${YELLOW}⚠️  API validator test completed (this is normal for non-API repositories)${NC}"
    fi
    
    # Test Secret scanner
    if $PYTHON_CMD -c "
import sys
sys.path.append('$SECRET_GENIE_DIR/commit_scripts')
from commit_scripts.secretscan import SecretScanner
scanner = SecretScanner()
print('✅ Secret scanner is working')
" 2>/dev/null; then
        echo -e "${GREEN}✅ Secret scanner is working${NC}"
    else
        echo -e "${YELLOW}⚠️  Secret scanner test had issues but may still work${NC}"
    fi
}

# Function to display success message
display_success() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                   INSTALLATION COMPLETE!                     ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}🎉 Unified Genie Tools have been successfully installed globally!${NC}"
    echo ""
    echo -e "${CYAN}📁 Installation Directory:${NC} $GENIE_DIR"
    echo -e "${CYAN}🪝 Git Hooks Directory:${NC} $HOOKS_DIR"
    echo ""
    echo -e "${YELLOW}📋 What happens now:${NC}"
    echo -e "   • All your git repositories will use Unified Genie hooks"
    echo -e "   • Secret validation runs on all pushes"
    echo -e "   • API validation runs only on PCF/SHP/IKP repositories"
    echo -e "   • Other repositories will proceed normally after secret scan"
    echo -e "   • Push operations will be blocked if secrets or API issues are found"
    echo ""
    echo -e "${CYAN}🛠️  Management Commands:${NC}"
    echo -e "   • Check version:  ${YELLOW}cat ~/.genie/version.txt${NC}"
    echo -e "   • Uninstall:      ${YELLOW}~/.genie/uninstall.sh${NC}"
    echo ""
    echo -e "${GREEN}🚀 Happy coding with validated secrets and APIs!${NC}"
}

# Main installation process
main() {
    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        echo -e "${RED}❌ Please do not run this script as root${NC}"
        echo -e "${YELLOW}   Run it as your normal user to install in your home directory${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}🚀 Starting Unified Genie installation...${NC}"
    echo ""
    
    # Installation steps
    check_dependencies
    backup_existing_hooks
    create_directories
    copy_validation_files
    update_hook_paths
    create_version_info
    create_uninstall_script
    configure_git
    test_installation
    display_success
}

# Run main function
main "$@" 