# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Face Classifier Backend.
Uses directory mode (onedir) for faster startup - files don't need to be extracted.
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_all

block_cipher = None

# Collect all torch submodules automatically (torch has many internal dependencies)
torch_hiddenimports = collect_submodules('torch')

# Hidden imports - combination of auto-collected and explicit
hiddenimports = torch_hiddenimports + [
    # FastAPI and dependencies
    'fastapi',
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'starlette',
    'starlette.routing',
    'starlette.middleware',
    'starlette.middleware.cors',
    'pydantic',
    'pydantic_settings',
    'pydantic_core',
    'annotated_types',
    
    # Database
    'sqlalchemy',
    'sqlalchemy.dialects.sqlite',
    
    # ML/AI packages (torch handled above)
    'torchvision',
    'facenet_pytorch',
    'facenet_pytorch.models.inception_resnet_v1',
    'facenet_pytorch.models.mtcnn',
    'sklearn',
    'sklearn.cluster',
    'hdbscan',
    
    # Image processing
    'PIL',
    'PIL.Image',
    'PIL.ExifTags',
    'rawpy',
    'numpy',
    
    # Our modules
    'models',
    'models.database',
    'models.schemas',
    'services',
    'services.face_processor',
    'services.clustering',
    'services.folder_manager',
    'services.raw_handler',
]

# Collect data files from packages that need them
datas = []

# Explicitly collect facenet_pytorch data
import facenet_pytorch
facenet_pkg_path = os.path.dirname(facenet_pytorch.__file__)
datas += [(os.path.join(facenet_pkg_path, 'data'), 'facenet_pytorch/data')]
datas += [(os.path.join(facenet_pkg_path, 'models'), 'facenet_pytorch/models')]

# Analysis
a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # GUI toolkits (not needed)
        'tkinter',
        '_tkinter',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'wx',
        # Dev/test tools (not needed in production)
        'matplotlib',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'sphinx',
        'setuptools',
        'pip',
        # Unused torch components (caffe2 is large and not needed)
        'caffe2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Use COLLECT for directory mode (much faster startup!)
exe = EXE(
    pyz,
    a.scripts,
    [],  # Don't include binaries in exe - they go in the directory
    exclude_binaries=True,  # Key for directory mode
    name='face-classifier-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# COLLECT creates a directory with all files
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='face-classifier-backend',
)
