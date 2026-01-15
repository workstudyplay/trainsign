#!/usr/bin/env python3
"""
Christmas RGB Matrix Animation (96x32)

Features:
- Falling snow (random + wind drift)
- Santa in a sleigh (color) flying across the top
- Reindeer team (color) pulling sleigh
- Snowmen on the ground (two)
- Twinkling stars / sparkles

Works with:
- hzeller/rpi-rgb-led-matrix (rgbmatrix)
- RGBMatrixEmulator fallback (if installed)

Usage:
  python xmas_matrix.py
  python xmas_matrix.py --width 96 --height 32 --fps 30
  python xmas_matrix.py --duration 120
  python xmas_matrix.py --no-santa
  python xmas_matrix.py --emulator

If you need sudo for hardware access, prefer using capabilities (setcap) instead.
"""

import argparse
import math
import random
import time
from dataclasses import dataclass
from typing import List, Tuple, Optional

from matrix import load_matrix, import_matrix
_, _, graphics = import_matrix()

# ---- Utility ----
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

def lerp(a, b, t):
    return a + (b - a) * t

@dataclass
class RGB:
    r: int
    g: int
    b: int

    def tup(self):
        return (int(self.r), int(self.g), int(self.b))

# palette
C_BLACK   = RGB(0, 0, 0)
C_WHITE   = RGB(255, 255, 255)
C_WARMWH  = RGB(255, 245, 220)
C_RED     = RGB(255, 40, 40)
C_DRED    = RGB(180, 0, 0)
C_GREEN   = RGB(0, 220, 80)
C_DGREEN  = RGB(0, 120, 40)
C_BLUE    = RGB(80, 120, 255)
C_SKY1    = RGB(6, 10, 20)
C_SKY2    = RGB(10, 18, 38)
C_SKY3    = RGB(16, 28, 56)
C_YELLOW  = RGB(255, 220, 80)
C_ORANGE  = RGB(255, 130, 10)
C_BROWN   = RGB(120, 70, 30)
C_GRAY    = RGB(170, 180, 190)
C_DGRAY   = RGB(90, 100, 110)
C_PINK    = RGB(255, 120, 170)


# ---- Drawing primitives ----
def pset(canvas, x, y, c: RGB):
    canvas.SetPixel(int(x), int(y), c.r, c.g, c.b)

def rect_fill(canvas, x, y, w, h, c: RGB):
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            pset(canvas, xx, yy, c)

def circle_fill(canvas, cx, cy, r, c: RGB):
    r2 = r * r
    for y in range(cy - r, cy + r + 1):
        dy = y - cy
        for x in range(cx - r, cx + r + 1):
            dx = x - cx
            if dx*dx + dy*dy <= r2:
                pset(canvas, x, y, c)

def line(canvas, x0, y0, x1, y1, c: RGB):
    # Bresenham
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        pset(canvas, x0, y0, c)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy

def text(canvas, graphics, font, x, y, c: RGB, s: str):
    graphics.DrawText(canvas, font, x, y, graphics.Color(c.r, c.g, c.b), s)


# ---- Scene elements ----
@dataclass
class Snowflake:
    x: float
    y: float
    vy: float
    vx: float
    phase: float
    size: int
    tw: float  # twinkle factor

def init_snow(width: int, height: int, count: int) -> List[Snowflake]:
    flakes = []
    for _ in range(count):
        flakes.append(Snowflake(
            x=random.uniform(0, width - 1),
            y=random.uniform(0, height - 1),
            vy=random.uniform(7.0, 22.0),     # pixels/sec
            vx=random.uniform(-3.0, 3.0),     # wind baseline
            phase=random.uniform(0, math.tau),
            size=random.choice([1, 1, 1, 2]), # mostly 1px, some 2px
            tw=random.uniform(0.3, 1.0)
        ))
    return flakes

def draw_snow(canvas, width: int, height: int, flakes: List[Snowflake], t: float):
    for f in flakes:
        # twinkle: modulate brightness subtly
        tw = 0.65 + 0.35 * math.sin(t * 3.0 + f.phase) * f.tw
        col = RGB(int(lerp(160, 255, tw)), int(lerp(170, 255, tw)), int(lerp(190, 255, tw)))

        x = int(f.x)
        y = int(f.y)

        if 0 <= x < width and 0 <= y < height:
            pset(canvas, x, y, col)
            if f.size == 2:
                if x + 1 < width: pset(canvas, x + 1, y, col)
                if y + 1 < height: pset(canvas, x, y + 1, col)

def update_snow(width: int, height: int, flakes: List[Snowflake], dt: float, wind: float):
    for f in flakes:
        sway = math.sin(f.phase + f.y * 0.18) * 2.0
        f.x += (f.vx + wind + sway) * dt
        f.y += f.vy * dt

        # wrap
        if f.y >= height:
            f.y = random.uniform(-6, 0)
            f.x = random.uniform(0, width - 1)
            f.vy = random.uniform(8.0, 24.0)
            f.vx = random.uniform(-3.0, 3.0)
            f.size = random.choice([1, 1, 1, 2])
            f.tw = random.uniform(0.3, 1.0)

        if f.x < -4:
            f.x = width + random.uniform(0, 4)
        elif f.x > width + 4:
            f.x = -random.uniform(0, 4)


def draw_background(canvas, width: int, height: int, t: float):
    # simple vertical gradient night sky
    for y in range(height):
        k = y / max(1, height - 1)
        # blend between 3 tones
        if k < 0.5:
            tt = k / 0.5
            r = int(lerp(C_SKY3.r, C_SKY2.r, tt))
            g = int(lerp(C_SKY3.g, C_SKY2.g, tt))
            b = int(lerp(C_SKY3.b, C_SKY2.b, tt))
        else:
            tt = (k - 0.5) / 0.5
            r = int(lerp(C_SKY2.r, C_SKY1.r, tt))
            g = int(lerp(C_SKY2.g, C_SKY1.g, tt))
            b = int(lerp(C_SKY2.b, C_SKY1.b, tt))
        for x in range(width):
            canvas.SetPixel(x, y, r, g, b)

    # twinkling stars
    random.seed(1337)  # stable star field positions
    star_count = max(14, width // 4)
    for i in range(star_count):
        x = random.randint(0, width - 1)
        y = random.randint(0, max(1, height // 2) - 1)
        tw = 0.6 + 0.4 * math.sin(t * (2.0 + (i % 5) * 0.6) + i)
        c = RGB(int(lerp(120, 255, tw)), int(lerp(120, 255, tw)), int(lerp(140, 255, tw)))
        pset(canvas, x, y, c)


def draw_ground(canvas, width: int, height: int, t: float):
    # snow ground at bottom
    ground_h = 8
    y0 = height - ground_h
    for y in range(y0, height):
        k = (y - y0) / max(1, ground_h - 1)
        c = RGB(int(lerp(220, 255, k)), int(lerp(230, 255, k)), int(lerp(240, 255, k)))
        for x in range(width):
            canvas.SetPixel(x, y, c.r, c.g, c.b)

    # gentle drifts (small bumps)
    for x in range(0, width, 2):
        bump = int(1.5 + 1.5 * math.sin((x * 0.22) + t * 0.7))
        yy = y0 - bump
        if 0 <= yy < height:
            pset(canvas, x, yy, RGB(240, 250, 255))
            if x + 1 < width:
                pset(canvas, x + 1, yy, RGB(235, 245, 255))


def draw_snowman(canvas, ox: int, base_y: int, variant: int = 0):
    """
    Draw a small snowman anchored to ground.
    base_y is ground baseline (bottom row index).
    """
    # sizes for 32px tall display
    # body: 4 radius, head: 3 radius
    body_r = 4
    head_r = 3
    body_cx = ox
    body_cy = base_y - body_r
    head_cx = ox
    head_cy = body_cy - body_r - head_r + 1

    circle_fill(canvas, body_cx, body_cy, body_r, C_WHITE)
    circle_fill(canvas, head_cx, head_cy, head_r, C_WHITE)

    # eyes
    pset(canvas, head_cx - 1, head_cy - 1, C_BLACK)
    pset(canvas, head_cx + 1, head_cy - 1, C_BLACK)

    # carrot nose
    if variant % 2 == 0:
        pset(canvas, head_cx + 2, head_cy, C_ORANGE)
        pset(canvas, head_cx + 3, head_cy, C_ORANGE)
    else:
        pset(canvas, head_cx + 2, head_cy, C_ORANGE)

    # buttons
    pset(canvas, body_cx, body_cy - 1, C_BLACK)
    pset(canvas, body_cx, body_cy + 1, C_BLACK)

    # scarf
    scarf_c = C_RED if variant % 2 == 0 else C_GREEN
    line(canvas, head_cx - 3, head_cy + 2, head_cx + 3, head_cy + 2, scarf_c)
    pset(canvas, head_cx + 1, head_cy + 3, scarf_c)

    # hat
    hat_c = C_DGRAY
    rect_fill(canvas, head_cx - 3, head_cy - 5, 7, 2, hat_c)
    rect_fill(canvas, head_cx - 2, head_cy - 8, 5, 3, hat_c)

    # arms (sticks)
    arm_c = C_BROWN
    line(canvas, body_cx - 3, body_cy - 1, body_cx - 7, body_cy - 4, arm_c)
    line(canvas, body_cx + 3, body_cy - 1, body_cx + 7, body_cy - 4, arm_c)


def draw_reindeer(canvas, x: int, y: int, frame: int):
    """
    Tiny reindeer sprite at (x,y) top-left anchor.
    8x5-ish footprint.
    """
    # body
    body = C_BROWN
    dark = RGB(90, 55, 25)
    # body rectangle 5x3
    rect_fill(canvas, x + 1, y + 1, 5, 3, body)
    # head
    rect_fill(canvas, x + 6, y + 2, 2, 2, body)
    # nose (Rudolph for first reindeer handled by caller optionally)
    # legs (animate)
    step = frame % 2
    if step == 0:
        pset(canvas, x + 2, y + 4, dark)
        pset(canvas, x + 4, y + 4, dark)
    else:
        pset(canvas, x + 3, y + 4, dark)
        pset(canvas, x + 5, y + 4, dark)
    # antlers
    pset(canvas, x + 6, y + 1, dark)
    pset(canvas, x + 7, y + 0, dark)
    pset(canvas, x + 7, y + 1, dark)


def draw_sleigh_and_santa(canvas, x: int, y: int, frame: int):
    """
    Sleigh sprite ~18x7 with santa.
    (x,y) is top-left.
    """
    # sleigh base
    red = C_DRED
    gold = C_YELLOW
    # runner
    line(canvas, x + 1, y + 6, x + 15, y + 6, gold)
    line(canvas, x + 1, y + 6, x + 0, y + 5, gold)
    line(canvas, x + 15, y + 6, x + 17, y + 5, gold)

    # body
    rect_fill(canvas, x + 3, y + 3, 11, 3, red)
    rect_fill(canvas, x + 13, y + 2, 3, 4, red)

    # seat back
    rect_fill(canvas, x + 12, y + 1, 2, 2, red)

    # santa (simple)
    # head
    circle_fill(canvas, x + 10, y + 2, 1, C_WARMWH)
    # hat
    pset(canvas, x + 9, y + 1, C_RED)
    pset(canvas, x + 10, y + 1, C_RED)
    pset(canvas, x + 8, y + 2, C_RED)
    pset(canvas, x + 8, y + 1, C_RED)
    pset(canvas, x + 7, y + 2, C_WHITE)  # pom
    # body
    pset(canvas, x + 10, y + 3, C_RED)
    pset(canvas, x + 10, y + 4, C_RED)

    # gift sack
    sack = RGB(40, 140, 70)
    rect_fill(canvas, x + 4, y + 1, 4, 3, sack)
    pset(canvas, x + 5, y + 0, sack)
    pset(canvas, x + 6, y + 0, sack)
    # tie
    pset(canvas, x + 6, y + 2, C_RED)

    # sparkle
    if frame % 8 < 2:
        pset(canvas, x + 16, y + 1, C_WHITE)
        pset(canvas, x + 17, y + 2, C_WHITE)


def draw_reindeer_team(canvas, start_x: int, y: int, frame: int, count: int = 4):
    spacing = 11
    for i in range(count):
        rx = start_x + i * spacing
        draw_reindeer(canvas, rx, y, frame + i)
        # Rudolph nose for the lead
        if i == 0 and frame % 6 < 3:
            pset(canvas, rx + 8, y + 3, C_RED)

        # harness line to next / sleigh
        if i < count - 1:
            line(canvas, rx + 0, y + 3, rx + spacing - 2, y + 3, RGB(180, 160, 120))


# ---- Main loop ----
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=96)
    ap.add_argument("--height", type=int, default=32)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--duration", type=float, default=0.0, help="seconds; 0 = run forever")
    ap.add_argument("--emulator", action="store_true", help="force RGBMatrixEmulator")
    ap.add_argument("--no-santa", action="store_true", help="disable sleigh/reindeer flyby")
    ap.add_argument("--snow", type=int, default=90, help="number of snowflakes")
    ap.add_argument("--seed", type=int, default=0, help="random seed; 0 = random")
    args = ap.parse_args()

    if args.seed != 0:
        random.seed(args.seed)

    matrix, main_canvas = load_matrix()
    font = graphics.Font()
    try:
        font.LoadFont("fonts/4x6.bdf")
    except Exception:
        # ok if missing
        font = None
        
    width, height = args.width, args.height
    flakes = init_snow(width, height, args.snow)

    # Santa flight parameters
    santa_y = 3
    # keep enough room for team + sleigh
    team_count = 4
    team_len = team_count * 11
    sleigh_len = 18
    total_len = team_len + 8 + sleigh_len
    speed = 20.0  # px/sec
    start_x = width + 5
    x_pos = float(start_x)

    t0 = time.time()
    last = t0
    frame = 0

    # message blink
    msg = "MERRY XMAS!"
    msg_timer = 0.0

    while True:
        now = time.time()
        dt = now - last
        last = now
        t = now - t0
        frame += 1

        if args.duration and t >= args.duration:
            break

        # wind oscillates
        wind = 3.0 * math.sin(t * 0.35) + 1.0 * math.sin(t * 1.3)

        # update snow
        update_snow(width, height, flakes, dt, wind)

        # draw scene
        draw_background(main_canvas, width, height, t)
        draw_ground(main_canvas, width, height, t)

        # snowmen positions
        ground_base = height - 1
        draw_snowman(main_canvas, 18, ground_base, variant=0)
        draw_snowman(main_canvas, width - 22, ground_base, variant=1)

        # optional greeting text (blink)
        msg_timer += dt
        if font and (int(t * 2) % 2 == 0):
            text(main_canvas, graphics, font, 2, 10, C_WARMWH, msg)

        # Santa + reindeer flyby
        if not args.no_santa:
            # move left; wrap
            x_pos -= speed * dt
            if x_pos < -total_len - 10:
                x_pos = width + random.uniform(0, 25)
                # slight variation in altitude
                santa_y = random.choice([2, 3, 4, 5])

            # Bobbing
            bob = int(1.2 * math.sin(t * 2.2))

            # draw reindeer then sleigh
            team_x = int(x_pos)
            draw_reindeer_team(main_canvas, team_x, santa_y + bob, frame, count=team_count)

            sleigh_x = team_x + team_len + 6
            draw_sleigh_and_santa(main_canvas, sleigh_x, santa_y + bob - 1, frame)

            # reins line from lead to sleigh
            line(main_canvas, team_x + 6, santa_y + bob + 3, sleigh_x + 2, santa_y + bob + 4, RGB(210, 200, 160))

        # overlay snow last
        draw_snow(main_canvas, width, height, flakes, t)

        # present frame
        main_canvas = matrix.SwapOnVSync(main_canvas)

        # fps pacing
        target = 1.0 / max(1, args.fps)
        work = time.time() - now
        if work < target:
            time.sleep(target - work)

    # clear on exit
    main_canvas.Clear()
    matrix.SwapOnVSync(main_canvas)


if __name__ == "__main__":
    main()
