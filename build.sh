#!/bin/bash
echo "Building APIGenie application..."

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Install requirements if not already installed
pip install -r requirements.txt

# Build the executable
pyinstaller --clean apigenie.spec

# For Mac, create a proper .app bundle if it's not already done
if [ "$(uname)" = "Darwin" ]; then
    # Check if we need to sign the app
    if [ -n "$APPLE_DEVELOPER_ID" ]; then
        echo "Signing the application with Developer ID: $APPLE_DEVELOPER_ID"
        codesign --force --options runtime --sign "$APPLE_DEVELOPER_ID" "dist/APIGenie.app"
    fi
    
    # Create a DMG if the create_dmg tool is available
    if command -v create-dmg &> /dev/null; then
        echo "Creating DMG package..."
        create-dmg --volname "APIGenie" --volicon "assets/logo.icns" \
                   --window-pos 200 120 --window-size 600 400 \
                   --icon-size 100 --icon "APIGenie.app" 175 190 \
                   --hide-extension "APIGenie.app" --app-drop-link 425 190 \
                   "dist/APIGenie.dmg" "dist/APIGenie.app"
    fi
fi

# Copy CLI wrapper script to dist folder
echo "Copying CLI wrapper script..."
cp apigenie-cli.sh dist/apigenie-cli.sh 2>/dev/null || true
chmod +x dist/apigenie-cli.sh 2>/dev/null || true
echo "CLI wrapper script copied to dist folder."

echo "Build complete!"
if [ "$(uname)" = "Darwin" ]; then
    echo "The application can be found at dist/APIGenie.app"
    if [ -f "dist/APIGenie.dmg" ]; then
        echo "DMG installer created at dist/APIGenie.dmg"
    fi
else
    echo "The executable can be found at dist/APIGenie"
fi
echo "CLI wrapper: dist/apigenie-cli.sh" 