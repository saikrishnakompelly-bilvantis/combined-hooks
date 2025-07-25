# Combined-Hooks

This directory contains a unified set of Git hooks and validation logic for both Secret-Genie (secret scanning) and API-Genie (API compliance validation).

## Features
- **Secret Validation**: Scans for secrets in code before push
- **API Validation**: Validates PCF, SHP, and IKP API projects for compliance
- **Unified Installation**: Single script installs both validation tools globally
- **No UI popups**: Clean, terminal-based validation
- **Global Hooks**: Works across all your repositories automatically

## Installation

1. Clone this directory or copy it to your machine.
2. Run the install script:
   ```bash
   cd Combined-Hooks
   ./install.sh
   ```
3. The installer will:
   - Create `~/.genie/` directory with all validation tools
   - Copy both Secret-Genie and API-Genie validation logic
   - Install a unified pre-push and pre-commit hook globally
   - Configure Git to use the global hooks

## Usage
- **Pre-commit hook**: Provides reminders, never blocks commits
- **Pre-push hook**: Runs secret and API validation, blocks push if issues are found
- **Works in all repositories automatically**

## Management
- Check version: `cat ~/.genie/version.txt`
- Uninstall: `~/.genie/uninstall.sh`
- Check hooks path: `git config --global --get core.hooksPath`

## Directory Structure
```
Combined-Hooks/
├── hooks/
│   ├── pre-commit
│   └── pre-push
├── validation/         # API-Genie validation logic
├── secretgenie/        # Secret-Genie logic
├── install.sh
├── requirements.txt
└── README.md
```

---

**Happy coding with validated secrets and APIs!** 