# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Face Classifier Backend.
Uses directory mode (onedir) for faster startup - files don't need to be extracted.
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_all

block_cipher = None

# Collect all onnxruntime submodules automatically
onnxruntime_hiddenimports = collect_submodules('onnxruntime')

# Collect all insightface submodules
insightface_hiddenimports = collect_submodules('insightface')

 # Hidden imports - combination of auto-collected and explicit
hiddenimports = onnxruntime_hiddenimports + insightface_hiddenimports + [
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

    # ML/AI packages
    'onnxruntime',
    'onnxruntime.capi',
    'onnxruntime.capi.onnxruntime_pybind11_state',
    'insightface',
    'insightface.app',
    'insightface.model_zoo',
    'insightface.utils',
    'cv2',
    'cv2.data',
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

    # Setuptools vendored modules
    'jaraco',
    'jaraco.context',
    'jaraco.functools',
    'jaraco.classes',
    'jaraco.path',
    'jaraco.text',
    'jaraco.vcs',
    'setuptools._vendor.jaraco',
]

# Collect data files from packages that need them
datas = []

# Collect insightface data files
import insightface
insightface_pkg_path = os.path.dirname(insightface.__file__)
datas += [(os.path.join(insightface_pkg_path, 'data'), 'insightface/data')]

# Collect cv2 data files
import cv2
cv2_data = os.path.dirname(cv2.data.__file__)
datas += [(cv2_data, 'cv2/data')]

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
         'IPython',
         'jupyter',
         'notebook',
         'pytest',
         'sphinx',
         'setuptools',
         'pip',
         # PyTorch (no longer needed, using ONNX)
         'torch',
         'torchvision',
         'torch.nn',
         'torch.optim',
         'torch.utils',
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
