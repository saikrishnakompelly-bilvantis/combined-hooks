# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Get the current directory
current_dir = Path.cwd()

# Add data files
datas = [
    ('hooks', 'hooks'),
    ('validation', 'validation'),
    ('assets', 'assets'),
]

# Hidden imports
hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtWidgets', 
    'PySide6.QtGui',
    'tkinter',
    'tkinter.messagebox',
    'tkinter.simpledialog',
    'json',
    'subprocess',
    'pathlib',
    'shutil',
    'platform',
    'logging',
]

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'QtWebEngine',
        'QtWebEngineCore', 
        'QtWebEngineWidgets',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
        'tensorflow',
        'torch',
        'sklearn',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Windows executable
if sys.platform == 'win32':
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='APIGenie',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon='assets/logo.ico' if os.path.exists('assets/logo.ico') else None,
    )

# macOS app bundle
elif sys.platform == 'darwin':
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='APIGenie',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='APIGenie'
    )
    app = BUNDLE(
        coll,
        name='APIGenie.app',
        icon='assets/logo.icns' if os.path.exists('assets/logo.icns') else None,
        bundle_identifier='com.apigenie.validation',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'CFBundleName': 'APIGenie',
            'CFBundleDisplayName': 'APIGenie - API Validation Tool',
            'CFBundleIdentifier': 'com.apigenie.validation',
            'CFBundlePackageType': 'APPL',
            'CFBundleSignature': 'APIG',
            'NSRequiresAquaSystemAppearance': 'False',
        },
    )

# Linux executable
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='APIGenie',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    ) 