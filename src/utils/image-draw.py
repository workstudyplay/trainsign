#!/usr/bin/env python
import os
import sys
import time

from PIL import Image
from PIL import ImageDraw

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.matrix import load_matrix

matrix, _ = load_matrix()

image = Image.new("RGB", (32, 32))  # Can be larger than matrix if wanted!!
draw = ImageDraw.Draw(image)  # Declare Draw instance before prims

draw.rectangle((0, 0, 2, 2), fill=(255, 0, 0), outline=(0, 0, 255))
# draw.line((0, 0, 31, 31), fill=(255, 0, 0))
# draw.line((0, 31, 31, 0), fill=(0, 255, 0))
while True:

    for n in range(-32, 33):  # Start off top-left, move off bottom-right
        matrix.Clear()
        matrix.SetImage(image, n, n)
        time.sleep(0.05)

matrix.Clear()
