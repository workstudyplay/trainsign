#!/usr/bin/env python
"""
Display scrolling text with double-buffering on RGB Matrix.
"""
import argparse
import os
import sys
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.matrix import load_matrix, import_matrix

# Graphics module needed at module level for Font and Color
_, _, graphics = import_matrix()

# Asset paths
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "../../assets")


class RunText:
    """Scrolling text animation for RGB Matrix."""

    def __init__(self, width: int = 128, height: int = 32, text: str = None,
                 font_path: str = None, color: tuple = (255, 0, 0), speed: float = 0.05):
        self.width = width
        self.height = height
        self.text = text or "1   2   3   4   5   6   7   8   9   10    A    B    C    D    E    F    G"
        self.speed = speed

        # Load font
        self.font = graphics.Font()
        font_file = font_path or os.path.join(ASSETS_DIR, "fonts/10x20.bdf")
        self.font.LoadFont(font_file)

        # Text color
        self.text_color = graphics.Color(color[0], color[1], color[2])

        # Position tracking
        self.pos = width

    def update(self, canvas):
        """Update one frame of the animation. Returns the text length."""
        canvas.Clear()
        text_len = graphics.DrawText(canvas, self.font, self.pos, 20, self.text_color, self.text)
        self.pos -= 1
        if self.pos + text_len < 0:
            self.pos = canvas.width
        return text_len

    def render(self, canvas):
        """Render current frame (alias for update for consistency)."""
        return self.update(canvas)


def main():
    parser = argparse.ArgumentParser(description="Scrolling text animation")
    parser.add_argument("-t", "--text", help="The text to scroll", default=None)
    parser.add_argument("--width", type=int, default=128, help="Display width")
    parser.add_argument("--height", type=int, default=32, help="Display height")
    parser.add_argument("--speed", type=float, default=0.05, help="Scroll speed (seconds per pixel)")
    parser.add_argument("--font", help="Path to BDF font file", default=None)
    parser.add_argument("--color", type=str, default="255,0,0", help="Text color as R,G,B")
    args = parser.parse_args()

    # Parse color
    color = tuple(int(c) for c in args.color.split(","))

    matrix, canvas = load_matrix()

    animation = RunText(
        width=args.width,
        height=args.height,
        text=args.text,
        font_path=args.font,
        color=color,
        speed=args.speed
    )

    try:
        while True:
            animation.update(canvas)
            time.sleep(args.speed)
            canvas = matrix.SwapOnVSync(canvas)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()