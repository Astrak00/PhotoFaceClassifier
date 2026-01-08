# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Face Classifier Backend.
This creates a single-file executable that bundles the FastAPI server
with all dependencies including PyTorch and facenet-pytorch.
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_all

block_cipher = None

# Collect all necessary packages
hiddenimports = [
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
    'sqlalchemy.ext.asyncio',
    'sqlalchemy.dialects.sqlite',
    'aiosqlite',
    
    # ML/AI packages
    'torch',
    'torch._C',
    'torch.utils',
    'torchvision',
    'torchvision.models',
    'facenet_pytorch',
    'facenet_pytorch.models.inception_resnet_v1',
    'facenet_pytorch.models.mtcnn',
    'sklearn',
    'sklearn.cluster',
    'sklearn.preprocessing',
    'sklearn.neighbors',
    'hdbscan',
    
    # Image processing
    'PIL',
    'PIL.Image',
    'PIL.ExifTags',
    'rawpy',
    'rawpy._rawpy',
    'numpy',
    'numpy.core',
    
    # Our modules
    'models',
    'models.database',
    'models.schemas',
    'services',
    'services.face_processor',
    'services.clustering',
    'services.folder_manager',
    'services.raw_handler',
    
    # Standard library that might be missed
    'multiprocessing',
    'concurrent.futures',
    'asyncio',
    'json',
    'pathlib',
    'typing',
    'contextlib',
    'datetime',
    'argparse',
    'email.mime.multipart',
    'email.mime.text',
]

# Add all torch submodules
hiddenimports += collect_submodules('torch')
hiddenimports += collect_submodules('torchvision')

# Collect data files from packages that need them
datas = []

# Explicitly collect facenet_pytorch - need entire package structure for relative paths
import facenet_pytorch
import os
facenet_pkg_path = os.path.dirname(facenet_pytorch.__file__)
# Include the entire facenet_pytorch package with data
datas += [(os.path.join(facenet_pkg_path, 'data'), 'facenet_pytorch/data')]
datas += [(os.path.join(facenet_pkg_path, 'models'), 'facenet_pytorch/models')]

# Collect torch data files (model configs, etc.)
try:
    datas += collect_data_files('torch')
except Exception:
    pass

try:
    datas += collect_data_files('torchvision')
except Exception:
    pass

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
        'tkinter',
        'matplotlib',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'sphinx',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Remove duplicate binaries and data files
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='face-classifier-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Disable UPX compression for better compatibility
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep console for logging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,  # Will be set by build script
    codesign_identity=None,
    entitlements_file=None,
)
