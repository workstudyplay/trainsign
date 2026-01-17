# Installation Guide

## Quick Install

### Development (macOS/Linux - uses emulator)

**Easiest method:**
```bash
./scripts/install.sh
```

**Or manually:**
```bash
pip install -r src/requirements.txt --no-build-isolation
```

The `--no-build-isolation` flag prevents the adafruit-blinka build error on non-Raspberry Pi systems.

### Raspberry Pi (with hardware support)

```bash
# Use the smart installer
./scripts/install-deps.sh --raspberry-pi

# Or manually
pip install -r src/requirements.txt
# Then install hardware-specific packages if needed
```

## Troubleshooting

### Error: Failed building wheel for adafruit-blinka-raspberry-pi5-piomatter

This error occurs on non-Raspberry Pi systems when pip tries to build Raspberry Pi-specific packages. This is **normal and safe to ignore** if you're using the emulator.

**Solutions:**

1. **Skip the problematic package** (recommended for development):
   ```bash
   pip install -r src/requirements.txt --no-build-isolation
   ```

2. **Install without building wheels**:
   ```bash
   pip install -r src/requirements.txt --no-binary :all:
   ```

3. **Use the smart installer**:
   ```bash
   ./scripts/install-deps.sh
   ```

4. **Install with constraints** (skip adafruit packages):
   ```bash
   pip install -r src/requirements.txt --constraint <(echo "adafruit-blinka-raspberry-pi5-piomatter==0.0.0")
   ```

### The emulator works fine without hardware packages

The `RGBMatrixEmulator` package doesn't require any Raspberry Pi hardware dependencies. The error you see is from optional dependencies that are only needed for actual hardware control.

## Platform-Specific Notes

### macOS
- Uses `RGBMatrixEmulator` automatically
- No hardware dependencies needed
- Safe to ignore adafruit-blinka build errors

### Linux (non-Raspberry Pi)
- Uses `RGBMatrixEmulator` automatically
- No hardware dependencies needed
- Safe to ignore adafruit-blinka build errors

### Raspberry Pi
- Can use either emulator or real hardware
- Real hardware requires `rpi-rgb-led-matrix` (compiled from source)
- May need adafruit-blinka packages for some hardware configurations

## Verification

After installation, verify it works:

```bash
python -c "from RGBMatrixEmulator import RGBMatrix; print('✓ RGBMatrixEmulator works')"
python -c "from opentelemetry import trace; print('✓ OpenTelemetry works')"
python -c "import flask; print('✓ Flask works')"
```

If all three print successfully, your installation is complete!
