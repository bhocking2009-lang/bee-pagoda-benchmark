#!/usr/bin/env bash
# Build a .deb package for Bee Pagoda Benchmark.
#
# Requirements:
#   - python3.12 + pip
#   - dpkg-deb
#
# Usage:
#   cd <repo-root>
#   bash packaging/build-deb.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$ROOT/build/deb"
DIST_DIR="$ROOT/dist"
VERSION="1.0.0"
ARCH="$(dpkg --print-architecture 2>/dev/null || echo amd64)"
PKG_NAME="bee-pagoda-benchmark"
PKG_DIR="$BUILD_DIR/${PKG_NAME}_${VERSION}_${ARCH}"

echo "[INFO] Building .deb v${VERSION} for ${ARCH}"

rm -rf "$BUILD_DIR"
mkdir -p "$DIST_DIR" \
  "$PKG_DIR/DEBIAN" \
  "$PKG_DIR/usr/bin" \
  "$PKG_DIR/usr/lib/bee-pagoda-benchmark" \
  "$PKG_DIR/usr/share/applications" \
  "$PKG_DIR/usr/share/doc/${PKG_NAME}"

# DEBIAN/control
cat > "$PKG_DIR/DEBIAN/control" <<EOF
Package: ${PKG_NAME}
Version: ${VERSION}
Architecture: ${ARCH}
Maintainer: Bee Pagoda <hello@beepagoda.example>
Depends: python3 (>= 3.12), python3-pyside6 | python3-pyside6.qtwidgets
Section: utils
Priority: optional
Homepage: https://github.com/bhocking2009-lang/bee-pagoda-benchmark
Description: Linux Benchmark Suite
 Professional Linux benchmark suite with a native PySide6 desktop GUI.
 Supports CPU, GPU compute, GPU graphics, AI, memory, and storage benchmarks.
 Provides full run history, result comparison, and export.
EOF

# DEBIAN/postinst — create desktop file
cat > "$PKG_DIR/DEBIAN/postinst" <<'EOF'
#!/bin/bash
set -e
update-desktop-database /usr/share/applications 2>/dev/null || true
EOF
chmod 0755 "$PKG_DIR/DEBIAN/postinst"

# Install app files
cp -r "$ROOT/app"      "$PKG_DIR/usr/lib/bee-pagoda-benchmark/"
cp -r "$ROOT/scripts"  "$PKG_DIR/usr/lib/bee-pagoda-benchmark/"
cp -r "$ROOT/profiles" "$PKG_DIR/usr/lib/bee-pagoda-benchmark/"
cp    "$ROOT/run_suite.sh" "$PKG_DIR/usr/lib/bee-pagoda-benchmark/"

# Launcher script
cat > "$PKG_DIR/usr/bin/bee-pagoda" <<'EOF'
#!/bin/bash
exec python3 -m app.gui.main "$@"
EOF
chmod 0755 "$PKG_DIR/usr/bin/bee-pagoda"

cat > "$PKG_DIR/usr/bin/bee-pagoda-cli" <<'EOF'
#!/bin/bash
exec python3 -m app.core.runner "$@"
EOF
chmod 0755 "$PKG_DIR/usr/bin/bee-pagoda-cli"

# Desktop file
cp "$ROOT/packaging/bee-pagoda-benchmark.desktop" \
   "$PKG_DIR/usr/share/applications/"

# Docs
cp "$ROOT/README.md" "$PKG_DIR/usr/share/doc/${PKG_NAME}/README.md"

# Build the package
OUTPUT="$DIST_DIR/${PKG_NAME}_${VERSION}_${ARCH}.deb"
dpkg-deb --build "$PKG_DIR" "$OUTPUT"

echo "[OK] .deb: $OUTPUT"
