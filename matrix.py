#!/usr/bin/env python3

# ---- Matrix import (real or emulator) ----
def import_matrix(prefer_emulator: bool = False):
    if prefer_emulator:
        try:
            from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions, graphics
            return RGBMatrix, RGBMatrixOptions, graphics
        except Exception:
            pass
    try:
        from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
        return RGBMatrix, RGBMatrixOptions, graphics
    except Exception:
        # fallback to emulator if available
        from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions, graphics
        return RGBMatrix, RGBMatrixOptions, graphics


def load_matrix(width=96,height=32):
    RGBMatrix, RGBMatrixOptions, _ = import_matrix()
    options = RGBMatrixOptions()
    options.rows = height
    options.cols = width
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = "adafruit-hat"

    options.brightness = 70
    options.gpio_slowdown = 2

    matrix = RGBMatrix(options=options)
    canvas = matrix.CreateFrameCanvas()

    return matrix, canvas
