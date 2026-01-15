#!/usr/bin/env python3
"""
Pong for RGB Matrix (default 128x32)

- 1px borders only
- Paddles: 2px wide x 8px tall
- Ball: 2x2
- Playable with keyboard in RGBMatrixEmulator (arrow keys + W/S)
- Demo mode (AI) if emulator events aren't available
- Single file

Controls (Emulator / pygame-like):
  Left paddle:  W (up), S (down)
  Right paddle: Up / Down arrows
  R: reset
  Q or Esc: quit
"""

import argparse
import os
import random
import sys
import time
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.matrix import load_matrix, import_matrix
_, _, graphics = import_matrix()

# Asset paths
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "../../assets")

def now_s() -> float:
    return time.monotonic()


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


@dataclass
class PaddleInput:
    up: bool = False
    down: bool = False


class Pong:
    def __init__(self, width: int, height: int, seed=None):
        if seed is not None:
            random.seed(seed)

        self.w = width
        self.h = height

        # Colors
        self.c_bg = graphics.Color(0, 0, 0)
        self.c_border = graphics.Color(80, 80, 80)
        self.c_paddle_l = graphics.Color(0, 220, 255)
        self.c_paddle_r = graphics.Color(255, 120, 255)
        self.c_ball = graphics.Color(255, 255, 255)
        self.c_text = graphics.Color(120, 120, 120)

        self.font = graphics.Font()
        self.font.LoadFont(os.path.join(ASSETS_DIR, "fonts/4x6.bdf"))

        # Playfield inside 1px border
        self.x0 = 0
        self.y0 = 0
        self.x1 = self.w - 1
        self.y1 = self.h - 1

        # Geometry
        self.paddle_w = 2
        self.paddle_h = 8
        self.ball_sz = 2

        self.left_in = PaddleInput()
        self.right_in = PaddleInput()

        self.reset()

    def reset(self, serve_dir: int | None = None):
        # Score
        self.score_l = 0
        self.score_r = 0
        self._reset_round(serve_dir=serve_dir)

    def _reset_round(self, serve_dir: int | None = None):
        # Paddles
        self.pad_l_x = self.x0 + 2
        self.pad_r_x = self.x1 - 2 - self.paddle_w + 1
        self.pad_l_y = (self.h - self.paddle_h) // 2
        self.pad_r_y = (self.h - self.paddle_h) // 2

        # Ball (center)
        self.ball_x = (self.w - self.ball_sz) / 2.0
        self.ball_y = (self.h - self.ball_sz) / 2.0

        # Velocity (px/s)
        base = 75.0
        ang = random.uniform(-0.35, 0.35)  # radians-ish small
        dirx = serve_dir if serve_dir in (-1, 1) else random.choice([-1, 1])
        self.ball_vx = dirx * base
        self.ball_vy = base * ang

        # Paddle speed
        self.paddle_speed = 95.0

        # Round pause
        self.round_pause = 0.25

        # AI fallback toggles (used when no events)
        # self.ai_left = False
        # self.ai_right = False

    # -----------------------
    # Input hooks
    # -----------------------
    def on_left_up(self, down: bool):
        self.left_in.up = down

    def on_left_down(self, down: bool):
        self.left_in.down = down

    def on_right_up(self, down: bool):
        self.right_in.up = down

    def on_right_down(self, down: bool):
        self.right_in.down = down

    # -----------------------
    # Physics helpers
    # -----------------------
    def _rects_overlap(self, ax, ay, aw, ah, bx, by, bw, bh):
        return (ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by)

    def _clamp_paddles(self):
        top = self.y0 + 1
        bottom = self.y1 - 1 - self.paddle_h + 1
        self.pad_l_y = int(clamp(self.pad_l_y, top, bottom))
        self.pad_r_y = int(clamp(self.pad_r_y, top, bottom))

    def _ai_step(self, dt):
        # Simple AI: track ball y with a bit of lag
        target_y = int(self.ball_y + self.ball_sz / 2 - self.paddle_h / 2)

        if self.ai_left:
            if self.pad_l_y < target_y:
                self.pad_l_y += int(self.paddle_speed * 0.85 * dt)
            elif self.pad_l_y > target_y:
                self.pad_l_y -= int(self.paddle_speed * 0.85 * dt)

        if self.ai_right:
            if self.pad_r_y < target_y:
                self.pad_r_y += int(self.paddle_speed * 0.85 * dt)
            elif self.pad_r_y > target_y:
                self.pad_r_y -= int(self.paddle_speed * 0.85 * dt)

    # -----------------------
    # Update
    # -----------------------
    def update(self, dt: float):
        dt = min(dt, 0.05)

        # Pause after serve
        if self.round_pause > 0:
            self.round_pause = max(0.0, self.round_pause - dt)
            return

        # Paddle movement
        dy_l = 0.0
        if self.left_in.up:
            dy_l -= self.paddle_speed * dt
        if self.left_in.down:
            dy_l += self.paddle_speed * dt
        self.pad_l_y += int(dy_l)

        dy_r = 0.0
        if self.right_in.up:
            dy_r -= self.paddle_speed * dt
        if self.right_in.down:
            dy_r += self.paddle_speed * dt
        self.pad_r_y += int(dy_r)

        # AI (if enabled)
        self._ai_step(dt)

        self._clamp_paddles()

        # Ball motion (continuous)
        bx0 = self.ball_x
        by0 = self.ball_y
        self.ball_x += self.ball_vx * dt
        self.ball_y += self.ball_vy * dt

        # Collide with top/bottom borders (1px)
        top = self.y0 + 1
        bottom = self.y1 - 1 - self.ball_sz + 1
        if self.ball_y <= top:
            self.ball_y = top
            self.ball_vy *= -1
        elif self.ball_y >= bottom:
            self.ball_y = bottom
            self.ball_vy *= -1

        # Paddle rectangles
        plx, ply, plw, plh = self.pad_l_x, self.pad_l_y, self.paddle_w, self.paddle_h
        prx, pry, prw, prh = self.pad_r_x, self.pad_r_y, self.paddle_w, self.paddle_h

        # Ball rectangle
        brx, bry, brw, brh = int(self.ball_x), int(self.ball_y), self.ball_sz, self.ball_sz

        # Left paddle collision (only if moving left)
        if self.ball_vx < 0 and self._rects_overlap(brx, bry, brw, brh, plx, ply, plw, plh):
            self.ball_x = plx + plw  # push out
            self.ball_vx *= -1.0

            # Add "english" based on hit position
            hit = ( (self.ball_y + self.ball_sz/2) - (ply + plh/2) ) / (plh/2)
            hit = clamp(hit, -1.0, 1.0)
            self.ball_vy += hit * 55.0

            # Slight speedup
            self.ball_vx *= 1.03
            self.ball_vy *= 1.01

        # Right paddle collision (only if moving right)
        brx, bry = int(self.ball_x), int(self.ball_y)
        if self.ball_vx > 0 and self._rects_overlap(brx, bry, brw, brh, prx, pry, prw, prh):
            self.ball_x = prx - self.ball_sz
            self.ball_vx *= -1.0

            hit = ( (self.ball_y + self.ball_sz/2) - (pry + prh/2) ) / (prh/2)
            hit = clamp(hit, -1.0, 1.0)
            self.ball_vy += hit * 55.0

            self.ball_vx *= 1.03
            self.ball_vy *= 1.01

        # Score: ball out of bounds left/right
        if self.ball_x < self.x0:
            self.score_r += 1
            self._reset_round(serve_dir=1)
        elif self.ball_x > self.x1 - self.ball_sz + 1:
            self.score_l += 1
            self._reset_round(serve_dir=-1)

        # Keep velocities sane
        self.ball_vy = clamp(self.ball_vy, -140.0, 140.0)
        self.ball_vx = clamp(self.ball_vx, -160.0, 160.0)

    # -----------------------
    # Render
    # -----------------------
    def render(self, canvas):
        canvas.Clear()

        # 1px border
        for x in range(self.x0, self.x1 + 1):
            canvas.SetPixel(x, self.y0, self.c_border.red, self.c_border.green, self.c_border.blue)
            canvas.SetPixel(x, self.y1, self.c_border.red, self.c_border.green, self.c_border.blue)
        for y in range(self.y0, self.y1 + 1):
            canvas.SetPixel(self.x0, y, self.c_border.red, self.c_border.green, self.c_border.blue)
            canvas.SetPixel(self.x1, y, self.c_border.red, self.c_border.green, self.c_border.blue)

        # Center dashed line (1px)
        cx = self.w // 2
        for y in range(self.y0 + 1, self.y1):
            if (y // 2) % 2 == 0:
                canvas.SetPixel(cx, y, self.c_border.red, self.c_border.green, self.c_border.blue)

        # Paddles (2x8)
        for yy in range(self.paddle_h):
            for xx in range(self.paddle_w):
                canvas.SetPixel(self.pad_l_x + xx, self.pad_l_y + yy,
                                self.c_paddle_l.red, self.c_paddle_l.green, self.c_paddle_l.blue)
                canvas.SetPixel(self.pad_r_x + xx, self.pad_r_y + yy,
                                self.c_paddle_r.red, self.c_paddle_r.green, self.c_paddle_r.blue)

        # Ball (2x2)
        bx = int(self.ball_x)
        by = int(self.ball_y)
        for yy in range(self.ball_sz):
            for xx in range(self.ball_sz):
                canvas.SetPixel(bx + xx, by + yy, self.c_ball.red, self.c_ball.green, self.c_ball.blue)

        # Score (top area inside border)
        graphics.DrawText(canvas, self.font, self.w // 2 - 18, 6, self.c_text, f"{self.score_l}")
        graphics.DrawText(canvas, self.font, self.w // 2 + 10, 6, self.c_text, f"{self.score_r}")


# -----------------------
# Main / Input handling
# -----------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--width", type=int, default=96)
    parser.add_argument("--height", type=int, default=32)
    parser.add_argument("--fps", type=int, default=60)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--ai-left", action="store_true", help="AI controls left paddle")
    parser.add_argument("--ai-right", action="store_true", help="AI controls right paddle")
    args = parser.parse_args()

    matrix, off = load_matrix()

    game = Pong(args.width, args.height, seed=args.seed)
    game.ai_left = True
    game.ai_right = True

    target_dt = 1.0 / max(1.0, args.fps)
    last = now_s()

    have_events = hasattr(matrix, "process")

    # If no events, default to AI vs AI so it animates
    if not have_events and not (args.ai_left or args.ai_right):
        game.ai_left = True
        game.ai_right = True

    try:
        while True:
            t0 = now_s()
            dt = t0 - last
            last = t0
            dt = min(dt, 0.05)

            if have_events:
                try:
                    for e in matrix.process():
                        et = getattr(e, "type", None)
                        key = getattr(e, "key", None)

                        # pygame: KEYDOWN=2, KEYUP=3
                        if et == 2:  # down
                            # Left paddle: W/S (119/115)
                            if key == 119:  # w
                                game.on_left_up(True)
                            elif key == 115:  # s
                                game.on_left_down(True)

                            # Right paddle: Up/Down arrows (273/274)
                            elif key == 273:
                                game.on_right_up(True)
                            elif key == 274:
                                game.on_right_down(True)

                            elif key in (114, 82):  # r/R
                                game.reset()
                            elif key in (113, 27):  # q/ESC
                                raise KeyboardInterrupt

                        elif et == 3:  # up
                            if key == 119:
                                game.on_left_up(False)
                            elif key == 115:
                                game.on_left_down(False)
                            elif key == 273:
                                game.on_right_up(False)
                            elif key == 274:
                                game.on_right_down(False)
                except Exception:
                    pass

            game.update(dt)
            game.render(off)
            off = matrix.SwapOnVSync(off)

            elapsed = now_s() - t0
            sleep_for = target_dt - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
