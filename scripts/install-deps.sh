#!/bin/bash
# Smart dependency installer that handles platform-specific packages
# Usage: ./scripts/install-deps.sh [--raspberry-pi]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REQUIREMENTS_DIR="$PROJECT_ROOT/src"

cd "$PROJECT_ROOT"

# Detect platform
PLATFORM="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Check if we're on Raspberry Pi
    if [ -f /proc/device-tree/model ] && grep -q "Raspberry Pi" /proc/device-tree/model; then
        PLATFORM="raspberrypi"
    else
        PLATFORM="linux"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
fi

echo "Detected platform: $PLATFORM"

# Install base requirements
echo "Installing base requirements..."
pip install -r "$REQUIREMENTS_DIR/requirements.txt" || {
    echo "Warning: Some packages failed to install. Continuing..."
}

# Handle platform-specific packages
if [[ "$1" == "--raspberry-pi" ]] || [[ "$PLATFORM" == "raspberrypi" ]]; then
    echo "Installing Raspberry Pi specific packages..."
    if [ -f "$REQUIREMENTS_DIR/requirements-raspberrypi.txt" ]; then
        pip install -r "$REQUIREMENTS_DIR/requirements-raspberrypi.txt" || {
            echo "Warning: Some Raspberry Pi packages failed to install."
            echo "This is normal if you're not on Raspberry Pi hardware."
        }
    fi
else
    echo "Skipping Raspberry Pi specific packages (not on Raspberry Pi)"
    echo "Using RGBMatrixEmulator for development/testing"
fi

echo ""
echo "✓ Dependency installation complete!"
echo ""
echo "If you encounter build errors with adafruit-blinka packages,"
echo "this is normal on non-Raspberry Pi systems. The emulator will work fine."
