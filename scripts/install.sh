#!/bin/bash
# Simple installation script that handles the adafruit-blinka build error
# Usage: ./scripts/install.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REQUIREMENTS_DIR="$PROJECT_ROOT/src"

cd "$PROJECT_ROOT"

echo "Installing dependencies for TRAINSIGN..."
echo ""

# Try normal installation first
if pip install -r "$REQUIREMENTS_DIR/requirements.txt" 2>&1 | tee /tmp/pip-install.log; then
    echo ""
    echo "✓ Installation successful!"
    exit 0
fi

# If it failed, check if it's the adafruit-blinka issue
if grep -q "adafruit-blinka-raspberry-pi5-piomatter" /tmp/pip-install.log; then
    echo ""
    echo "⚠ Build error detected with adafruit-blinka-raspberry-pi5-piomatter"
    echo "This is normal on non-Raspberry Pi systems and safe to ignore."
    echo ""
    echo "Retrying with --no-build-isolation..."
    echo ""
    
    # Retry with --no-build-isolation
    if pip install -r "$REQUIREMENTS_DIR/requirements.txt" --no-build-isolation; then
        echo ""
        echo "✓ Installation successful (with workaround)!"
        echo ""
        echo "Note: The adafruit-blinka package is only needed for Raspberry Pi hardware."
        echo "The RGBMatrixEmulator works fine without it."
        exit 0
    fi
fi

echo ""
echo "✗ Installation failed. Please check the error messages above."
echo ""
echo "Troubleshooting:"
echo "1. Make sure you have Python 3.9+ installed"
echo "2. Try: pip install --upgrade pip setuptools wheel"
echo "3. See INSTALL.md for more help"
exit 1
