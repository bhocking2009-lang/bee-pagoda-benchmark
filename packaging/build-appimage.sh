#!/usr/bin/env bash
# Build an AppImage for Bee Pagoda Benchmark.
#
# Requirements:
#   - python3.12 + pip
#   - appimagetool (https://appimage.github.io/appimagetool/)
#   - AppImageKit runtime (automatically downloaded if missing)
#
# Usage:
#   cd <repo-root>
#   bash packaging/build-appimage.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$ROOT/build/appimage"
APP_DIR="$BUILD_DIR/BeePagodaBenchmark.AppDir"
DIST_DIR="$ROOT/dist"

PYTHON_BIN="${BENCH_PYTHON:-python3}"
VERSION="1.0.0"

echo "[INFO] Building Bee Pagoda Benchmark AppImage v${VERSION}"
echo "[INFO] Root: $ROOT"
echo "[INFO] Python: $PYTHON_BIN"

# Clean previous build
rm -rf "$BUILD_DIR"
mkdir -p "$APP_DIR/usr" "$DIST_DIR"

# Install app into a virtual environment inside AppDir
"$PYTHON_BIN" -m venv "$APP_DIR/usr/python"
"$APP_DIR/usr/python/bin/pip" install --quiet --upgrade pip
"$APP_DIR/usr/python/bin/pip" install --quiet PySide6
"$APP_DIR/usr/python/bin/pip" install --quiet -e "$ROOT"

# AppRun entry point
cat > "$APP_DIR/AppRun" <<'APPRUN'
#!/bin/bash
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
export PATH="$SELF_DIR/usr/python/bin:$PATH"
exec "$SELF_DIR/usr/python/bin/bee-pagoda" "$@"
APPRUN
chmod +x "$APP_DIR/AppRun"

# Desktop file and icon
cp "$ROOT/packaging/bee-pagoda-benchmark.desktop" "$APP_DIR/bee-pagoda-benchmark.desktop"
# Placeholder icon (replace with a real 256x256 PNG)
if [[ -f "$ROOT/app/gui/assets/icon.png" ]]; then
  cp "$ROOT/app/gui/assets/icon.png" "$APP_DIR/bee-pagoda-benchmark.png"
else
  # Create a minimal placeholder PNG using Python if available
  "$APP_DIR/usr/python/bin/python3" - "$APP_DIR/bee-pagoda-benchmark.png" <<'PY' 2>/dev/null || true
import sys, struct, zlib
# Minimal 1x1 blue PNG
def make_png(path):
    def chunk(ctype, data):
        c = struct.pack('>I', len(data)) + ctype + data
        return c + struct.pack('>I', zlib.crc32(ctype + data) & 0xffffffff)
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
    raw = b'\x00\x2a\x52\xc9'
    idat = chunk(b'IDAT', zlib.compress(raw))
    iend = chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(sig + ihdr + idat + iend)
make_png(sys.argv[1])
PY
fi

# Resolve appimagetool
if ! command -v appimagetool >/dev/null 2>&1; then
  echo "[INFO] Downloading appimagetool…"
  TOOL_URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
  TOOL_PATH="/tmp/appimagetool"
  curl -sSfL "$TOOL_URL" -o "$TOOL_PATH"
  chmod +x "$TOOL_PATH"
  APPIMAGETOOL="$TOOL_PATH"
else
  APPIMAGETOOL="$(command -v appimagetool)"
fi

OUTPUT="$DIST_DIR/BeePagodaBenchmark-${VERSION}-x86_64.AppImage"
ARCH=x86_64 "$APPIMAGETOOL" "$APP_DIR" "$OUTPUT"

echo "[OK] AppImage: $OUTPUT"
