#!/bin/bash

# API Genie + Secret Genie - Global Git Hooks Installation Script
# This script installs both API validation and secret scanning hooks globally for all git repositories

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration - following Secret-Genie's pattern
APIGENIE_DIR="$HOME/.apigenie"
HOOKS_DIR="$APIGENIE_DIR/hooks"
VALIDATION_DIR="$APIGENIE_DIR/validation"

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    API GENIE + SECRET GENIE                  ║"
echo "║         Global Git Hooks Installation (Combined)             ║"
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
        echo -e "${YELLOW}   This will be backed up to: $APIGENIE_DIR/backup_hooks_path.txt${NC}"
        
        # Create the directory if it doesn't exist
        mkdir -p "$APIGENIE_DIR"
        echo "$current_hooks_path" > "$APIGENIE_DIR/backup_hooks_path.txt"
    fi
}

# Function to create directory structure
create_directories() {
    echo -e "${BLUE}📁 Creating combined directory structure...${NC}"
    
    # Remove existing installation if it exists
    if [ -d "$APIGENIE_DIR" ]; then
        echo -e "${YELLOW}⚠️  Existing installation found. Removing...${NC}"
        rm -rf "$APIGENIE_DIR"
    fi
    
    # Create directories following Secret-Genie pattern
    mkdir -p "$HOOKS_DIR"
    mkdir -p "$VALIDATION_DIR"
    mkdir -p "$VALIDATION_DIR/ui"
    mkdir -p "$VALIDATION_DIR/validators"
    
    echo -e "${GREEN}✅ Combined directory structure created${NC}"
}

# Function to copy validation files
copy_validation_files() {
    echo -e "${BLUE}📋 Copying API validation system files...${NC}"
    
    # Get the script directory (where this install.sh is located)
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    
    # Copy API validation package
    cp -r "$SCRIPT_DIR/validation/"* "$VALIDATION_DIR/"
    
    # Copy API requirements and demo
    cp "$SCRIPT_DIR/requirements.txt" "$APIGENIE_DIR/api_requirements.txt"
    cp "$SCRIPT_DIR/demo_interactive.py" "$APIGENIE_DIR/"
    
    echo -e "${GREEN}✅ API validation files copied${NC}"
}

# Function to copy secret validation files - following Secret-Genie's exact pattern
copy_secret_files() {
    echo -e "${BLUE}🔒 Copying Secret-Genie validation files...${NC}"
    
    # Get the script directory
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
    
    # Copy Secret-Genie files following their exact pattern
    if [ -d "$SCRIPT_DIR/Secret-Genie/src/hooks" ]; then
        # Copy the main hook files exactly as Secret-Genie does
        hook_files=("pre-push" "pre_push.py" "scan-config")
        for hook_file in "${hook_files[@]}"; do
            source_file="$SCRIPT_DIR/Secret-Genie/src/hooks/$hook_file"
            target_file="$HOOKS_DIR/$hook_file"
            
            if [ -f "$source_file" ]; then
                cp "$source_file" "$target_file"
                chmod 755 "$target_file"
                echo -e "${GREEN}✅ Copied $hook_file${NC}"
            fi
        done
        
        # Copy commit_scripts directory exactly as Secret-Genie does
        if [ -d "$SCRIPT_DIR/Secret-Genie/src/hooks/commit_scripts" ]; then
            cp -r "$SCRIPT_DIR/Secret-Genie/src/hooks/commit_scripts" "$HOOKS_DIR/"
            echo -e "${GREEN}✅ Copied commit_scripts directory${NC}"
        fi
        
        # Copy requirements
        cp "$SCRIPT_DIR/Secret-Genie/requirements.txt" "$APIGENIE_DIR/secret_requirements.txt"
        
        echo -e "${GREEN}✅ Secret validation files copied${NC}"
    else
        echo -e "${YELLOW}⚠️  Secret-Genie directory not found, skipping secret validation${NC}"
    fi
}

# Function to create combined hooks - simple approach
create_combined_hooks() {
    echo -e "${BLUE}🔗 Creating combined pre-push hook...${NC}"
    
    # Create a simple wrapper pre-push hook that calls both validations
    cat > "$HOOKS_DIR/pre-push" << 'EOF'
#!/bin/bash

# Combined Pre-push hook for API validation and Secret scanning
# This hook runs before pushing to remote repository

set -e

# Get the directory where this script is located
HOOK_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
APIGENIE_ROOT="$(dirname "$HOOK_DIR")"
REPO_ROOT="$(pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}🛡️  Running comprehensive validation before push...${NC}"
echo -e "${BLUE}   • API validation${NC}"
echo -e "${BLUE}   • Secret scanning${NC}"

# Dynamic Python detection
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo -e "${RED}Error: Python is not installed or not in PATH${NC}"
    exit 1
fi

# Store stdin content for API validation
stdin_content=""
while IFS= read -r line; do
    stdin_content+="$line"$'\n'
done

# Function to run API validation
run_api_validation() {
    echo -e "${BLUE}🔍 Running API validation...${NC}"
    
    # Check if validation module exists
    if [ ! -f "$APIGENIE_ROOT/validation/api_validator.py" ]; then
        echo -e "${YELLOW}⚠️  API validation module not found, skipping API validation${NC}"
        return 0
    fi
    
    # Read from stdin for API validation
    echo "$stdin_content" | while read local_ref local_sha remote_ref remote_sha; do
        if [ "$local_sha" = "0000000000000000000000000000000000000000" ]; then
            # Branch is being deleted, nothing to validate
            continue
        fi
        
        if [ "$remote_sha" = "0000000000000000000000000000000000000000" ]; then
            # New branch, validate all commits
            range="$local_sha"
        else
            # Existing branch, validate new commits
            range="$remote_sha..$local_sha"
        fi
        
        # Get list of changed files in the push
        CHANGED_FILES=$(git diff --name-only "$range")
        
        if [ -n "$CHANGED_FILES" ]; then
            echo -e "${YELLOW}Validating API changes in range: $range${NC}"
            
            # Save current directory and run validation
            CURRENT_DIR="$(pwd)"
            cd "$APIGENIE_ROOT"
            $PYTHON -m validation.api_validator --commit-range="$range" --interactive --repo-path "$REPO_ROOT"
            
            VALIDATION_EXIT_CODE=$?
            cd "$CURRENT_DIR"
            
            if [ $VALIDATION_EXIT_CODE -ne 0 ]; then
                echo -e "${RED}✗ API validation failed or was cancelled${NC}"
                exit 1
            else
                echo -e "${GREEN}✓ API validation passed${NC}"
            fi
        fi
    done
}

# Function to run secret scanning - exactly like Secret-Genie
run_secret_scanning() {
    echo -e "${BLUE}🔒 Running secret scanning...${NC}"
    
    # Check if secret scanning module exists
    if [ ! -f "$HOOK_DIR/pre_push.py" ]; then
        echo -e "${YELLOW}⚠️  Secret scanning module not found, skipping secret validation${NC}"
        return 0
    fi
    
    # Run secret scanner exactly as Secret-Genie does
    $PYTHON "$HOOK_DIR/pre_push.py"
    
    SECRET_EXIT_CODE=$?
    
    if [ $SECRET_EXIT_CODE -ne 0 ]; then
        echo -e "${RED}✗ Secret scanning failed or was cancelled${NC}"
        exit 1
    else
        echo -e "${GREEN}✓ Secret scanning passed${NC}"
    fi
}

# Run API validation if we have stdin content
if [ -n "$stdin_content" ]; then
    run_api_validation
fi

# Run secret scanning
run_secret_scanning

echo -e "${GREEN}✅ All pre-push validations completed successfully${NC}"
exit 0
EOF

    # Copy the existing pre-commit hook as well
    if [ -f "$SCRIPT_DIR/hooks/pre-commit" ]; then
        cp "$SCRIPT_DIR/hooks/pre-commit" "$HOOKS_DIR/"
        chmod 755 "$HOOKS_DIR/pre-commit"
    fi
    
    # Make hooks executable
    chmod 755 "$HOOKS_DIR/pre-push"
    
    echo -e "${GREEN}✅ Combined hooks created${NC}"
}

# Function to create version info
create_version_info() {
    cat > "$APIGENIE_DIR/version.txt" << EOF
API Genie + Secret Genie Version 1.0.0
Installation Date: $(date)
Installation Path: $APIGENIE_DIR
Git Hooks Path: $HOOKS_DIR
Components: API Validation, Secret Scanning
EOF
}

# Function to create uninstall script
create_uninstall_script() {
    cat > "$APIGENIE_DIR/uninstall.sh" << 'EOF'
#!/bin/bash

# API Genie + Secret Genie - Global Git Hooks Uninstallation Script

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

APIGENIE_DIR="$HOME/.apigenie"

echo -e "${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                API GENIE + SECRET GENIE                      ║"
echo "║             Global Git Hooks Uninstallation                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${YELLOW}This will remove the global validation hooks (API + Secret).${NC}"
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
if [ -f "$APIGENIE_DIR/backup_hooks_path.txt" ]; then
    backup_path=$(cat "$APIGENIE_DIR/backup_hooks_path.txt")
    echo -e "${YELLOW}📁 Restoring previous hooks path: $backup_path${NC}"
    git config --global core.hooksPath "$backup_path"
fi

echo -e "${BLUE}🗑️  Removing combined Genie directory...${NC}"
rm -rf "$APIGENIE_DIR"

echo -e "${GREEN}✅ API Genie + Secret Genie has been successfully uninstalled!${NC}"
echo -e "${BLUE}ℹ️  Your git repositories will now use default or local hooks.${NC}"
EOF

    chmod +x "$APIGENIE_DIR/uninstall.sh"
    echo -e "${GREEN}✅ Uninstall script created${NC}"
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

# Function to configure git - exactly like Secret-Genie
configure_git() {
    echo -e "${BLUE}⚙️  Configuring global git hooks...${NC}"
    
    # Set global hooks path exactly as Secret-Genie does
    git config --global core.hooksPath "$HOOKS_DIR"
    
    echo -e "${GREEN}✅ Git configured to use combined hooks${NC}"
}

# Function to test installation
test_installation() {
    echo -e "${BLUE}🧪 Testing installation...${NC}"
    
    # Test API validator
    cd "$APIGENIE_DIR"
    if [ -f "$VALIDATION_DIR/api_validator.py" ]; then
        if $PYTHON_CMD -m validation.api_validator --identify-only > /dev/null 2>&1; then
            echo -e "${GREEN}✅ API validator is working${NC}"
        else
            echo -e "${YELLOW}⚠️  API validator test completed${NC}"
        fi
    fi
    
    # Test secret scanner
    if [ -f "$HOOKS_DIR/commit_scripts/secretscan.py" ]; then
        echo -e "${GREEN}✅ Secret scanner components installed${NC}"
    fi
    
    # Test demo (if in interactive environment)
    if [ -t 0 ] && [ -t 1 ] && command_exists $PYTHON_CMD; then
        echo -e "${BLUE}🎯 Installation complete! You can test the API UI with:${NC}"
        echo -e "   ${CYAN}cd ~/.apigenie && $PYTHON_CMD demo_interactive.py${NC}"
    fi
}

# Function to display success message
display_success() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                   INSTALLATION COMPLETE!                     ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}🎉 API Genie + Secret Genie has been successfully installed globally!${NC}"
    echo ""
    echo -e "${CYAN}📁 Installation Directory:${NC} $APIGENIE_DIR"
    echo -e "${CYAN}🪝 Git Hooks Directory:${NC} $HOOKS_DIR"
    echo ""
    echo -e "${YELLOW}📋 What happens now:${NC}"
    echo -e "   • All your git repositories will use combined validation hooks"
    echo -e "   • API validation: Only PCF and SHP/IKP repositories will be validated"
    echo -e "   • Secret scanning: All repositories will be scanned for secrets"
    echo -e "   • Other repositories will proceed normally for API validation"
    echo -e "   • Push operations with failures will show interactive UI"
    echo ""
    echo -e "${CYAN}🛠️  Management Commands:${NC}"
    echo -e "   • Test API UI:    ${YELLOW}cd ~/.apigenie && $PYTHON_CMD demo_interactive.py${NC}"
    echo -e "   • Check version:  ${YELLOW}cat ~/.apigenie/version.txt${NC}"
    echo -e "   • Uninstall:      ${YELLOW}~/.apigenie/uninstall.sh${NC}"
    echo ""
    echo -e "${GREEN}🚀 Happy coding with validated APIs and secure secrets!${NC}"
}

# Main installation process
main() {
    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        echo -e "${RED}❌ Please do not run this script as root${NC}"
        echo -e "${YELLOW}   Run it as your normal user to install in your home directory${NC}"
        exit 1
    fi
    
    echo -e "${BLUE}🚀 Starting combined installation...${NC}"
    echo ""
    
    # Installation steps
    check_dependencies
    backup_existing_hooks
    create_directories
    copy_validation_files
    copy_secret_files
    create_combined_hooks
    create_version_info
    create_uninstall_script
    configure_git
    test_installation
    display_success
}

# Run main function
main "$@" 