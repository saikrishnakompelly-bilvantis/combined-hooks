# APIGenie - API Validation Tool Installer

APIGenie is a standalone installer application that sets up global Git hooks for API validation. It provides a user-friendly GUI to install and manage API validation hooks that enforce compliance standards across all your Git repositories.

## Features

- **Easy Installation**: Simple GUI interface for installing/uninstalling hooks
- **Global Git Hooks**: Works across all repositories automatically
- **Zero Dependencies**: Standalone executable requires no additional software
- **Cross-Platform**: Supports Windows, macOS, and Linux
- **CLI Support**: Command-line interface for automated deployments
- **API Validation**: Enforces 20+ compliance rules for API metadata

## Quick Start

### Download and Run
1. Download the appropriate executable for your platform:
   - Windows: `APIGenie.exe`
   - macOS: `APIGenie.app` 
   - Linux: `APIGenie`

2. Double-click to run the installer
3. Click "Install Hooks" to set up API validation
4. Your Git repositories will now validate API compliance automatically

### Command Line Usage
```bash
# Install hooks without GUI
./APIGenie /install

# Uninstall hooks
./APIGenie /uninstall

# Show help
./APIGenie /help
```

## What Gets Installed

APIGenie installs the following in your `~/.apigenie` directory:

- **Git Hooks**: `pre-commit`, `pre-push`, `commit-msg`
- **Validation Engine**: Complete API validation system
- **Interactive UI**: Tkinter-based validation dialogs
- **Git Configuration**: Global hooks path setup

## How It Works

1. **Global Installation**: Sets `core.hooksPath` to `~/.apigenie/hooks`
2. **Repository Detection**: Automatically identifies API project types:
   - **General**: No validation (no SHP/IKP folders, no "-decision-service-")
   - **PCF**: Validation required (contains "-decision-service-") 
   - **SHP/IKP**: Validation required (has SHP/IKP folders OR contains "-ds-")

3. **Validation Flow**:
   - **Pre-commit**: Shows friendly reminders (non-blocking)
   - **Pre-push**: Full validation with interactive UI for failures
   - **Interactive Dialogs**: Handle validation failures with justification entry

## API Validation Rules

APIGenie enforces 20+ compliance rules including:

- **API Layer**: Must be `xAPI`, `sAPI`, or `eAPI`
- **API Audience**: Must be `internal` or `external`
- **Asset Version**: Must follow pattern `1.0.0.*`
- **GBGF Values**: Validates business unit codes
- **Case Sensitivity**: Strict validation of all values
- **Required Fields**: Ensures all mandatory metadata is present

## Building from Source

### Prerequisites
- Python 3.9+
- PySide6
- PyInstaller

### Setup
```bash
# Clone or download the source code
cd apigenie-installer

# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Build Instructions

#### Windows
```bash
# Run the build script
build.bat

# Output: dist/APIGenie.exe
```

#### macOS/Linux
```bash
# Make script executable
chmod +x build.sh

# Run the build script
./build.sh

# Output: 
# - macOS: dist/APIGenie.app
# - Linux: dist/APIGenie
```

### Adding Your Logo
1. Place logo files in the `assets/` directory:
   - `logo.png` (256x256 recommended)
   - `logo.ico` (Windows)
   - `logo.icns` (macOS)

2. See `assets/README.md` for detailed instructions

## File Structure

```
apigenie-installer/
├── main.py                 # Main application code
├── apigenie.spec          # PyInstaller configuration
├── requirements.txt       # Python dependencies
├── build.bat             # Windows build script
├── build.sh              # macOS/Linux build script
├── apigenie-cli.bat      # Windows CLI wrapper
├── apigenie-cli.ps1      # PowerShell CLI wrapper
├── apigenie-cli.sh       # Unix CLI wrapper
├── assets/               # Logo and visual assets
├── hooks/                # Git hooks to be installed
└── validation/           # API validation system
```

## Installation Directory Structure

After installation, your `~/.apigenie` directory will contain:

```
~/.apigenie/
├── hooks/
│   ├── pre-commit        # Git pre-commit hook
│   ├── pre-push          # Git pre-push hook
│   ├── commit-msg        # Git commit-msg hook
│   └── [other files]     # Supporting scripts
├── validation/           # Complete validation system
│   ├── ui/              # Interactive dialogs
│   ├── validators/      # Validation rules
│   └── [other files]    # Core validation logic
└── config               # Installation configuration
```

## Troubleshooting

### Installation Issues
- **Git not found**: Install Git and ensure it's in your PATH
- **Permission denied**: Run as administrator (Windows) or use `sudo` (Unix)
- **Already installed**: Run uninstall first, then reinstall

### Validation Issues
- **UI not showing**: Check if Tkinter is available in your Python installation
- **Validation not triggering**: Verify `git config --global core.hooksPath`
- **False positives**: Review validation rules in validation configuration

### CLI Wrapper Issues
- **Command not found**: Ensure CLI wrapper is in your PATH
- **Permission denied**: Make CLI wrapper executable (`chmod +x`)

## System Requirements

### Minimum Requirements
- **OS**: Windows 10+, macOS 10.14+, Ubuntu 18.04+
- **RAM**: 512 MB available memory
- **Disk**: 100 MB free space
- **Git**: Version 2.0 or higher

### Recommended
- **OS**: Latest stable versions
- **RAM**: 1 GB available memory
- **Git**: Latest stable version
- **Python**: 3.9+ (if running from source)

## License

This project is proprietary software. All rights reserved.

## Support

For support and questions:
1. Check the troubleshooting section above
2. Review validation logs in your repository
3. Contact your system administrator 