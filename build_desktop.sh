#!/usr/bin/env bash
# =============================================================================
# Race Timing System — macOS / Linux desktop build script
# =============================================================================
# Prerequisites:
#   pip install pyinstaller
#   All packages in requirements.txt must be installed in the active venv.
#
# Usage:
#   chmod +x build_desktop.sh
#   ./build_desktop.sh
#
# Output:
#   dist/RaceTimingSystem/   — distributable folder (zip or copy to target)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo " Race Timing System — Desktop Build"
echo "============================================================"

# ── 1. Check Python ──────────────────────────────────────────────
PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" &>/dev/null; then
    echo "ERROR: Python not found. Set PYTHON env var or install Python 3.11+."
    exit 1
fi
echo "Python: $($PYTHON --version)"

# ── 2. Ensure virtual environment ────────────────────────────────
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment …"
    "$PYTHON" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
echo "Venv: $(which python)"

# ── 3. Install / upgrade dependencies ────────────────────────────
echo "Installing dependencies …"
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
pip install --quiet pyinstaller

# ── 4. Clean previous build ──────────────────────────────────────
echo "Cleaning previous build artefacts …"
rm -rf build dist

# ── 5. Run PyInstaller ───────────────────────────────────────────
echo "Running PyInstaller …"
pyinstaller race_timing.spec --noconfirm

# ── 6. Copy runtime assets not captured by spec ──────────────────
DIST_DIR="dist/RaceTimingSystem"

# Copy .env.example as a template for first-run configuration
cp .env.example "$DIST_DIR/.env.example"

# Create empty data directory placeholder
mkdir -p "$DIST_DIR/data"

echo ""
echo "============================================================"
echo " Build complete!"
echo " Output: $DIST_DIR"
echo ""
echo " To run on this machine:"
echo "   $DIST_DIR/RaceTimingSystem"
echo ""
echo " To distribute:"
echo "   zip -r RaceTimingSystem-\$(uname -s)-\$(uname -m).zip $DIST_DIR"
echo "============================================================"

# Made with Bob
