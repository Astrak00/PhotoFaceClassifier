#!/bin/bash
#
# Face Classifier - Full Build Script
# Builds the complete application for the specified platform and architecture
#
# Usage:
#   ./build.sh [platform] [arch]
#
# Platforms: macos, windows, linux
# Architectures: x64, arm64
#
# Examples:
#   ./build.sh macos arm64      # Build for macOS ARM64 (Apple Silicon)
#   ./build.sh macos x64        # Build for macOS x64 (Intel)
#   ./build.sh windows x64      # Build for Windows x64
#   ./build.sh linux x64        # Build for Linux x64
#   ./build.sh linux arm64      # Build for Linux ARM64
#   ./build.sh                   # Build for current platform/arch

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "=============================================="
echo "  Face Classifier - Full Build Script"
echo "=============================================="
echo -e "${NC}"

# Detect current platform
detect_platform() {
    case "$(uname -s)" in
        Linux*)     echo "linux";;
        Darwin*)    echo "darwin";;
        MINGW*|MSYS*|CYGWIN*)    echo "win32";;
        *)          echo "unknown";;
    esac
}

# Detect current architecture
detect_arch() {
    case "$(uname -m)" in
        x86_64|amd64)   echo "x64";;
        arm64|aarch64)  echo "arm64";;
        *)              echo "unknown";;
    esac
}

# Parse arguments
CURRENT_PLATFORM=$(detect_platform)
CURRENT_ARCH=$(detect_arch)

TARGET_PLATFORM="${1:-$CURRENT_PLATFORM}"
TARGET_ARCH="${2:-$CURRENT_ARCH}"

# Normalize platform name
case "$TARGET_PLATFORM" in
    macos|darwin|mac)   TARGET_PLATFORM="darwin";;
    windows|win|win32)  TARGET_PLATFORM="win32";;
    linux)              TARGET_PLATFORM="linux";;
    *)
        echo -e "${RED}Error: Unknown platform '$TARGET_PLATFORM'${NC}"
        echo "Valid platforms: macos, windows, linux"
        exit 1
        ;;
esac

# Normalize arch name
case "$TARGET_ARCH" in
    x64|x86_64|amd64)   TARGET_ARCH="x64";;
    arm64|aarch64)      TARGET_ARCH="arm64";;
    *)
        echo -e "${RED}Error: Unknown architecture '$TARGET_ARCH'${NC}"
        echo "Valid architectures: x64, arm64"
        exit 1
        ;;
esac

echo -e "${GREEN}Target Platform:${NC} $TARGET_PLATFORM"
echo -e "${GREEN}Target Architecture:${NC} $TARGET_ARCH"
echo -e "${GREEN}Current Platform:${NC} $CURRENT_PLATFORM"
echo -e "${GREEN}Current Architecture:${NC} $CURRENT_ARCH"
echo ""

# Check if cross-compiling
if [ "$TARGET_PLATFORM" != "$CURRENT_PLATFORM" ]; then
    echo -e "${YELLOW}Warning: Cross-platform building detected.${NC}"
    echo "PyInstaller can only build for the current platform."
    echo "You need to run this script on the target platform."
    echo ""
    
    if [ "$TARGET_PLATFORM" = "darwin" ]; then
        echo "To build for macOS, run this script on a Mac."
    elif [ "$TARGET_PLATFORM" = "win32" ]; then
        echo "To build for Windows, run this script on Windows."
    elif [ "$TARGET_PLATFORM" = "linux" ]; then
        echo "To build for Linux, run this script on Linux."
    fi
    exit 1
fi

# Check if cross-architecture on non-macOS
if [ "$TARGET_ARCH" != "$CURRENT_ARCH" ] && [ "$TARGET_PLATFORM" != "darwin" ]; then
    echo -e "${RED}Error: Cross-architecture building is only supported on macOS.${NC}"
    echo "You need to run this script on a machine with the target architecture."
    exit 1
fi

# ============================================
# Step 1: Build Python Backend
# ============================================
echo -e "${BLUE}"
echo "=============================================="
echo "  Step 1: Building Python Backend"
echo "=============================================="
echo -e "${NC}"

cd "$BACKEND_DIR"

# Install build dependencies
echo "Installing Python build dependencies..."
uv sync --group build

# Clean previous builds
echo "Cleaning previous backend builds..."
rm -rf dist build

# Set output directory
BACKEND_OUTPUT_DIR="dist/${TARGET_PLATFORM}-${TARGET_ARCH}"
mkdir -p "$BACKEND_OUTPUT_DIR"

# Build with PyInstaller
echo "Building backend with PyInstaller..."

# Set architecture for macOS cross-arch builds
if [ "$TARGET_PLATFORM" = "darwin" ] && [ "$TARGET_ARCH" != "$CURRENT_ARCH" ]; then
    PYINSTALLER_ARCH="--target-architecture $TARGET_ARCH"
else
    PYINSTALLER_ARCH=""
fi

# Set output directory
mkdir -p "dist/${TARGET_PLATFORM}-${TARGET_ARCH}"

uv run pyinstaller \
    --clean \
    --noconfirm \
    --distpath "dist/${TARGET_PLATFORM}-${TARGET_ARCH}" \
    --workpath "build/${TARGET_PLATFORM}-${TARGET_ARCH}" \
    $PYINSTALLER_ARCH \
    backend.spec

# Verify backend was built
if [ "$TARGET_PLATFORM" = "win32" ]; then
    BACKEND_BINARY="$BACKEND_OUTPUT_DIR/face-classifier-backend.exe"
else
    BACKEND_BINARY="$BACKEND_OUTPUT_DIR/face-classifier-backend"
fi

if [ ! -f "$BACKEND_BINARY" ]; then
    echo -e "${RED}Error: Backend binary was not created!${NC}"
    exit 1
fi

echo -e "${GREEN}Backend built successfully: $BACKEND_BINARY${NC}"
ls -lh "$BACKEND_BINARY"

# ============================================
# Step 2: Build Frontend
# ============================================
echo -e "${BLUE}"
echo "=============================================="
echo "  Step 2: Building Frontend"
echo "=============================================="
echo -e "${NC}"

cd "$FRONTEND_DIR"

# Install frontend dependencies
echo "Installing frontend dependencies..."
bun install

# Build frontend
echo "Building frontend..."
bun run build:frontend

# ============================================
# Step 3: Package with Electron Builder
# ============================================
echo -e "${BLUE}"
echo "=============================================="
echo "  Step 3: Packaging with Electron Builder"
echo "=============================================="
echo -e "${NC}"

# Create a temporary electron-builder config with the correct backend path
BUILDER_CONFIG="electron-builder-temp.json"
cat > "$BUILDER_CONFIG" << EOF
{
  "extends": null,
  "appId": "com.faceclassifier.app",
  "productName": "Face Classifier",
  "artifactName": "\${productName}-\${version}-\${os}-\${arch}.\${ext}",
  "directories": {
    "output": "release"
  },
  "files": [
    "dist/**/*",
    "electron/**/*"
  ],
  "extraResources": [
    {
      "from": "../backend/dist/${TARGET_PLATFORM}-${TARGET_ARCH}/face-classifier-backend$([ "$TARGET_PLATFORM" = "win32" ] && echo ".exe")",
      "to": "backend/face-classifier-backend$([ "$TARGET_PLATFORM" = "win32" ] && echo ".exe")"
    }
  ],
  "mac": {
    "category": "public.app-category.photography",
    "target": [
      {
        "target": "dmg",
        "arch": ["${TARGET_ARCH}"]
      },
      {
        "target": "zip",
        "arch": ["${TARGET_ARCH}"]
      }
    ],
    "icon": "public/icon.icns",
    "hardenedRuntime": true,
    "gatekeeperAssess": false,
    "entitlements": "build/entitlements.mac.plist",
    "entitlementsInherit": "build/entitlements.mac.plist"
  },
  "win": {
    "target": [
      {
        "target": "nsis",
        "arch": ["${TARGET_ARCH}"]
      },
      {
        "target": "portable",
        "arch": ["${TARGET_ARCH}"]
      }
    ],
    "icon": "public/icon.ico"
  },
  "linux": {
    "target": [
      {
        "target": "AppImage",
        "arch": ["${TARGET_ARCH}"]
      }
    ],
    "category": "Graphics",
    "icon": "public/icons"
  },
  "nsis": {
    "oneClick": false,
    "perMachine": true,
    "allowToChangeInstallationDirectory": true,
    "createDesktopShortcut": true,
    "createStartMenuShortcut": true
  }
}
EOF

# Run electron-builder with platform-specific flag
case "$TARGET_PLATFORM" in
    darwin)
        echo "Building macOS package..."
        npx electron-builder --mac --${TARGET_ARCH} --config "$BUILDER_CONFIG"
        ;;
    win32)
        echo "Building Windows package..."
        npx electron-builder --win --${TARGET_ARCH} --config "$BUILDER_CONFIG"
        ;;
    linux)
        echo "Building Linux package..."
        npx electron-builder --linux --${TARGET_ARCH} --config "$BUILDER_CONFIG"
        ;;
esac

# Clean up temp config
rm -f "$BUILDER_CONFIG"

# ============================================
# Done!
# ============================================
echo -e "${GREEN}"
echo "=============================================="
echo "  Build Complete!"
echo "=============================================="
echo -e "${NC}"

echo "Output files are in: $FRONTEND_DIR/release/"
ls -la "$FRONTEND_DIR/release/" 2>/dev/null || echo "No release files found."

echo ""
echo -e "${GREEN}Build Summary:${NC}"
echo "  Platform: $TARGET_PLATFORM"
echo "  Architecture: $TARGET_ARCH"
echo "  Backend: $BACKEND_BINARY"
echo "  Frontend: $FRONTEND_DIR/release/"
