#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv-build"
BUILD_DIR="$SCRIPT_DIR/build"
DIST_DIR="$SCRIPT_DIR/dist"
ICONSET_DIR="$SCRIPT_DIR/ItoSubIcon.iconset"
SOURCE_ICON="$PROJECT_ROOT/assets/image/ItoSubIcon.png"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Python 3.11 or 3.12 is required to build ItoSub.app."
    echo "Install it with Homebrew: brew install python@3.12"
    exit 1
fi

"$PYTHON_BIN" - <<'PY'
import sys

if sys.version_info < (3, 10) or sys.version_info >= (3, 14):
    raise SystemExit(
        f"Unsupported build Python {sys.version.split()[0]}; use Python 3.11, 3.12, or 3.13."
    )
PY

if [[ ! -f "$SOURCE_ICON" ]]; then
    echo "Missing application icon: $SOURCE_ICON"
    exit 1
fi

case "$(uname -m)" in
    arm64) export ITOSUB_TARGET_ARCH="${ITOSUB_TARGET_ARCH:-arm64}" ;;
    x86_64) export ITOSUB_TARGET_ARCH="${ITOSUB_TARGET_ARCH:-x86_64}" ;;
    *) echo "Unsupported Mac architecture: $(uname -m)"; exit 1 ;;
esac

echo "Creating isolated build environment..."
"$PYTHON_BIN" -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r "$SCRIPT_DIR/requirements-macos.txt"
python -m pip install --editable "$PROJECT_ROOT"

echo "Checking runtime imports..."
python - <<'PY'
import PyQt6
import argostranslate
import ctranslate2
import faster_whisper
import numpy
import sounddevice
import torch

print("macOS runtime imports OK")
PY

echo "Generating macOS application icon..."
rm -rf "$ICONSET_DIR"
mkdir -p "$ICONSET_DIR"
sips -z 16 16     "$SOURCE_ICON" --out "$ICONSET_DIR/icon_16x16.png" >/dev/null
sips -z 32 32     "$SOURCE_ICON" --out "$ICONSET_DIR/icon_16x16@2x.png" >/dev/null
sips -z 32 32     "$SOURCE_ICON" --out "$ICONSET_DIR/icon_32x32.png" >/dev/null
sips -z 64 64     "$SOURCE_ICON" --out "$ICONSET_DIR/icon_32x32@2x.png" >/dev/null
sips -z 128 128   "$SOURCE_ICON" --out "$ICONSET_DIR/icon_128x128.png" >/dev/null
sips -z 256 256   "$SOURCE_ICON" --out "$ICONSET_DIR/icon_128x128@2x.png" >/dev/null
sips -z 256 256   "$SOURCE_ICON" --out "$ICONSET_DIR/icon_256x256.png" >/dev/null
sips -z 512 512   "$SOURCE_ICON" --out "$ICONSET_DIR/icon_256x256@2x.png" >/dev/null
sips -z 512 512   "$SOURCE_ICON" --out "$ICONSET_DIR/icon_512x512.png" >/dev/null
sips -z 1024 1024 "$SOURCE_ICON" --out "$ICONSET_DIR/icon_512x512@2x.png" >/dev/null
iconutil -c icns "$ICONSET_DIR" -o "$SCRIPT_DIR/ItoSubIcon.icns"

echo "Building ItoSub.app for $ITOSUB_TARGET_ARCH..."
python -m PyInstaller \
    --noconfirm \
    --clean \
    --workpath "$BUILD_DIR" \
    --distpath "$DIST_DIR" \
    "$SCRIPT_DIR/ItoSub-mac.spec"

APP_PATH="$DIST_DIR/ItoSub.app"
if [[ ! -d "$APP_PATH" ]]; then
    echo "Build failed: $APP_PATH was not created."
    exit 1
fi

echo "Creating distributable ZIP and DMG..."
rm -f "$DIST_DIR/ItoSub-macOS-$ITOSUB_TARGET_ARCH.zip"
rm -f "$DIST_DIR/ItoSub-macOS-$ITOSUB_TARGET_ARCH.dmg"
ditto -c -k --sequesterRsrc --keepParent \
    "$APP_PATH" "$DIST_DIR/ItoSub-macOS-$ITOSUB_TARGET_ARCH.zip"
hdiutil create \
    -volname "ItoSub" \
    -srcfolder "$APP_PATH" \
    -ov \
    -format UDZO \
    "$DIST_DIR/ItoSub-macOS-$ITOSUB_TARGET_ARCH.dmg" >/dev/null

echo
echo "Build complete:"
echo "  $APP_PATH"
echo "  $DIST_DIR/ItoSub-macOS-$ITOSUB_TARGET_ARCH.zip"
echo "  $DIST_DIR/ItoSub-macOS-$ITOSUB_TARGET_ARCH.dmg"
echo
echo "The destination Mac does not need Python."
echo "The first transcription/translation run still needs internet to download language models."
