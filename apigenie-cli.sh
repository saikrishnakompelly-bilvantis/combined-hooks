#!/bin/bash
# APIGenie CLI wrapper for macOS and Linux
# This script allows you to use APIGenie from the command line

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Determine the correct executable path based on the platform
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS - look for .app bundle
    APIGENIE_EXE="$SCRIPT_DIR/APIGenie.app/Contents/MacOS/APIGenie"
    if [ ! -f "$APIGENIE_EXE" ]; then
        # Fallback to direct executable
        APIGENIE_EXE="$SCRIPT_DIR/APIGenie"
    fi
else
    # Linux
    APIGENIE_EXE="$SCRIPT_DIR/APIGenie"
fi

# Check if the executable exists
if [ ! -f "$APIGENIE_EXE" ]; then
    echo "Error: APIGenie executable not found at $APIGENIE_EXE"
    echo "Make sure APIGenie is properly installed."
    exit 1
fi

# Make sure the executable is executable
if [ ! -x "$APIGENIE_EXE" ]; then
    echo "Error: APIGenie executable is not executable"
    echo "Try running: chmod +x '$APIGENIE_EXE'"
    exit 1
fi

# Execute APIGenie with all provided arguments
exec "$APIGENIE_EXE" "$@" 