#!/bin/bash
# Build script for Face Classifier Backend
# Creates a standalone executable using PyInstaller

set -e

cd "$(dirname "$0")"

echo "==================================="
echo "Face Classifier Backend Build"
echo "==================================="

# Detect OS and Architecture
OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
    Linux*)     PLATFORM="linux";;
    Darwin*)    PLATFORM="darwin";;
    MINGW*|MSYS*|CYGWIN*)    PLATFORM="win32";;
    *)          echo "Unknown OS: $OS"; exit 1;;
esac

case "$ARCH" in
    x86_64|amd64)   ARCH_NAME="x64";;
    arm64|aarch64)  ARCH_NAME="arm64";;
    *)              echo "Unknown architecture: $ARCH"; exit 1;;
esac

echo "Platform: $PLATFORM"
echo "Architecture: $ARCH_NAME"
echo ""

# Install build dependencies
echo "Installing build dependencies..."
uv sync --group build

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist build

# Output directory
OUTPUT_DIR="dist/$PLATFORM-$ARCH_NAME"
mkdir -p "$OUTPUT_DIR"

# Run PyInstaller
echo "Building executable with PyInstaller..."
uv run pyinstaller \
    --clean \
    --noconfirm \
    --distpath "$OUTPUT_DIR" \
    --workpath "build/$PLATFORM-$ARCH_NAME" \
    backend.spec

# Rename output if on Windows
if [ "$PLATFORM" = "win32" ]; then
    BINARY_NAME="face-classifier-backend.exe"
else
    BINARY_NAME="face-classifier-backend"
fi

echo ""
echo "==================================="
echo "Build complete!"
echo "Output: $OUTPUT_DIR/$BINARY_NAME"
echo "==================================="

# Show binary info
ls -lh "$OUTPUT_DIR/$BINARY_NAME"
