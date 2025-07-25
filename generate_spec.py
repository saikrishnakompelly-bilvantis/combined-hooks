import os

# Create a runtime hook to force native UI mode
runtime_hook_content = '''
import os
import sys

# Set environment variable to force native UI
os.environ['GENIE_USE_NATIVE_UI'] = 'true'

# Override imports to prevent QtWebEngineCore from being imported
class ImportBlocker:
    def find_module(self, fullname, path=None):
        if fullname == 'PySide6.QtWebEngineCore':
            return self
        return None
        
    def load_module(self, fullname):
        raise ImportError(f"The {fullname} module is not available in this build")

# Install the import blocker
import sys
sys.meta_path.insert(0, ImportBlocker())
'''

# Write the runtime hook
with open('runtime_hook.py', 'w', encoding='utf-8') as f:
    f.write(runtime_hook_content)

spec_content = '''# -*- mode: python ; coding: utf-8 -*-
block_cipher = None
a = Analysis(['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/assets', 'assets'), 
        ('src/hooks', 'hooks'),
        ('src/hooks/.env.example', 'hooks/'),  # Explicitly include .env.example
        ('src/hooks/.env.sample', 'hooks/'),   # Explicitly include .env.sample
    ],
    hiddenimports=[
        'PySide6.QtWidgets',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtNetwork',
        'PySide6.QtPrintSupport',
        'python-dotenv'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['runtime_hook.py'],
    excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngine'],  # Exclude all web engine modules
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SecretGenie-HSBC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src/assets/logo.ico',
    version='file_version_info.txt'  # Add version information for Windows
)

# Only create the app bundle on macOS
import sys
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='SecretGenie-HSBC.app',
        icon='src/assets/logo.icns',  # Ensure you have an .icns file for macOS
        bundle_identifier=None,
        info_plist={
            'NSHighResolutionCapable': 'True',
            'LSBackgroundOnly': 'False',  # Ensures app shows in dock and doesn't run in background
            'CFBundleShortVersionString': '1.0.0',
            'NSPrincipalClass': 'NSApplication',
            'NSRequiresAquaSystemAppearance': 'False'  # Allows dark mode support
        }
    )
'''

with open('genie-hsbc.spec', 'w', encoding='utf-8') as f:
    f.write(spec_content) 