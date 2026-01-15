#!/usr/bin/env python3
"""
Elf Toy Workshop RGB Matrix Animation (96x32)

- Fixed size: 96x32
- Fixed FPS: 30
- Hardware mapping: adafruit-hat
- Uses RGBMatrixEmulator if env var RGB_MATRIX_EMULATOR is set (to any non-empty value)

Other options are configurable below in the CONFIG section.
"""

import os
import math
import random
import time
from dataclasses import dataclass
from typing import List

from matrix import load_matrix, import_matrix
_, _, graphics = import_matrix()

# ----------------------------
# CONFIG
# ----------------------------
WIDTH = 96
HEIGHT = 32
FPS = 30

# Matrix options (tweak as needed)
BRIGHTNESS = 70          # 1..100
GPIO_SLOWDOWN = 2        # 0..5 typical
PWM_BITS = None          # e.g. 11; None = default
PWM_LSB_NANOSECONDS = None  # e.g. 130; None = default
LIMIT_REFRESH_RATE_HZ = None  # e.g. 120; None = default

# Animation tuning
BELT_Y = 23              # conveyor top y (belt is 5px tall)
BELT_SPEED = 18.0        # px/sec
GIFT_DENSITY = 1.0       # higher = more gifts
WINDOW_X, WINDOW_Y, WINDOW_W, WINDOW_H = 3, 4, 26, 12
SNOW_COUNT = 22

# Deterministic visuals (set to 0 for random each run)
RNG_SEED = 1337

# ----------------------------
# Colors + helpers
# ----------------------------
@dataclass(frozen=True)
class RGB:
    r: int
    g: int
    b: int

def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t

C_BLACK   = RGB(0, 0, 0)
C_WHITE   = RGB(255, 255, 255)
C_WARMWH  = RGB(255, 245, 220)
C_YELLOW  = RGB(255, 210, 70)
C_ORANGE  = RGB(255, 130, 20)
C_RED     = RGB(255, 40, 40)
C_DRED    = RGB(160, 0, 0)
C_GREEN   = RGB(0, 220, 90)
C_DGREEN  = RGB(0, 110, 40)
C_BLUE    = RGB(70, 120, 255)
C_PINK    = RGB(255, 120, 170)
C_BROWN   = RGB(120, 70, 30)
C_DBROWN  = RGB(80, 45, 20)
C_TAN     = RGB(200, 160, 110)
C_GRAY    = RGB(150, 160, 170)
C_DGRAY   = RGB(80, 90, 100)
C_SKY1    = RGB(10, 14, 26)
C_SKY2    = RGB(16, 26, 48)
C_WALL1   = RGB(40, 22, 18)
C_WALL2   = RGB(55, 30, 22)
C_FLOOR1  = RGB(30, 18, 14)
C_FLOOR2  = RGB(45, 28, 20)

def pset(canvas, x, y, c: RGB):
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        canvas.SetPixel(int(x), int(y), c.r, c.g, c.b)

def rect_fill(canvas, x, y, w, h, c: RGB):
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            pset(canvas, xx, yy, c)

def rect_outline(canvas, x, y, w, h, c: RGB):
    for xx in range(x, x + w):
        pset(canvas, xx, y, c)
        pset(canvas, xx, y + h - 1, c)
    for yy in range(y, y + h):
        pset(canvas, x, yy, c)
        pset(canvas, x + w - 1, yy, c)

def line(canvas, x0, y0, x1, y1, c: RGB):
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


# ----------------------------
# Snow outside window
# ----------------------------
@dataclass
class Snowflake:
    x: float
    y: float
    vy: float
    phase: float

def init_snow(count: int) -> List[Snowflake]:
    flakes = []
    for _ in range(count):
        flakes.append(Snowflake(
            x=random.uniform(WINDOW_X, WINDOW_X + WINDOW_W - 1),
            y=random.uniform(WINDOW_Y, WINDOW_Y + WINDOW_H - 1),
            vy=random.uniform(6.0, 18.0),
            phase=random.uniform(0, math.tau),
        ))
    return flakes

def update_snow(flakes: List[Snowflake], dt: float, wind: float):
    for f in flakes:
        f.y += f.vy * dt
        f.x += wind * dt + math.sin(f.phase + f.y * 0.25) * 0.3

        if f.y >= WINDOW_Y + WINDOW_H:
            f.y = WINDOW_Y + random.uniform(-3, 0)
            f.x = random.uniform(WINDOW_X, WINDOW_X + WINDOW_W - 1)
            f.vy = random.uniform(6.0, 18.0)

        if f.x < WINDOW_X:
            f.x = WINDOW_X + WINDOW_W - 1
        elif f.x >= WINDOW_X + WINDOW_W:
            f.x = WINDOW_X

def draw_window(canvas, t: float, flakes: List[Snowflake]):
    # glass gradient
    for y in range(WINDOW_Y, WINDOW_Y + WINDOW_H):
        k = (y - WINDOW_Y) / max(1, WINDOW_H - 1)
        c = RGB(
            int(lerp(C_SKY2.r, C_SKY1.r, k)),
            int(lerp(C_SKY2.g, C_SKY1.g, k)),
            int(lerp(C_SKY2.b, C_SKY1.b, k)),
        )
        for x in range(WINDOW_X, WINDOW_X + WINDOW_W):
            pset(canvas, x, y, c)

    # window frame + mullions
    rect_outline(canvas, WINDOW_X - 1, WINDOW_Y - 1, WINDOW_W + 2, WINDOW_H + 2, C_TAN)
    line(canvas, WINDOW_X + WINDOW_W // 2, WINDOW_Y, WINDOW_X + WINDOW_W // 2, WINDOW_Y + WINDOW_H - 1, C_TAN)
    line(canvas, WINDOW_X, WINDOW_Y + WINDOW_H // 2, WINDOW_X + WINDOW_W - 1, WINDOW_Y + WINDOW_H // 2, C_TAN)

    # snowflakes
    for f in flakes:
        tw = 0.65 + 0.35 * math.sin(t * 3.0 + f.phase)
        col = RGB(int(lerp(160, 255, tw)), int(lerp(170, 255, tw)), int(lerp(190, 255, tw)))
        pset(canvas, int(f.x), int(f.y), col)


# ----------------------------
# Workshop background
# ----------------------------
def draw_workshop_bg(canvas, t: float):
    wall_h = 18
    for y in range(wall_h):
        k = y / max(1, wall_h - 1)
        c = RGB(
            int(lerp(C_WALL2.r, C_WALL1.r, k)),
            int(lerp(C_WALL2.g, C_WALL1.g, k)),
            int(lerp(C_WALL2.b, C_WALL1.b, k)),
        )
        for x in range(WIDTH):
            pset(canvas, x, y, c)

    for y in range(wall_h, HEIGHT):
        k = (y - wall_h) / max(1, HEIGHT - wall_h - 1)
        c = RGB(
            int(lerp(C_FLOOR2.r, C_FLOOR1.r, k)),
            int(lerp(C_FLOOR2.g, C_FLOOR1.g, k)),
            int(lerp(C_FLOOR2.b, C_FLOOR1.b, k)),
        )
        for x in range(WIDTH):
            pset(canvas, x, y, c)

    # garland string across top
    y = 1
    for x in range(0, WIDTH, 2):
        yy = y + int(1.2 * math.sin(x * 0.18 + t * 1.3))
        pset(canvas, x, yy, C_DGREEN)

    # twinkly bulbs
    bulbs = [C_RED, C_YELLOW, C_BLUE, C_PINK]
    for i, x in enumerate(range(3, WIDTH - 3, 8)):
        yy = 1 + int(1.2 * math.sin(x * 0.18 + t * 1.3))
        tw = (math.sin(t * 2.6 + i) * 0.5 + 0.5)
        if tw > 0.35:
            pset(canvas, x, yy + 1, bulbs[i % len(bulbs)])


# ----------------------------
# Conveyor belt + gifts
# ----------------------------
@dataclass
class Gift:
    x: float
    kind: int      # 0=box,1=box2,2=toyblock
    color_a: RGB
    color_b: RGB

def spawn_gift() -> Gift:
    kind = random.choice([0, 0, 1, 2])
    palettes = [
        (C_RED, C_WHITE),
        (C_GREEN, C_WHITE),
        (C_BLUE, C_WHITE),
        (C_PINK, C_WHITE),
        (C_ORANGE, C_WHITE),
    ]
    a, b = random.choice(palettes)
    return Gift(x=WIDTH + random.uniform(0, 12), kind=kind, color_a=a, color_b=b)

def draw_gift(canvas, x: int, y: int, g: Gift):
    if g.kind in (0, 1):
        rect_fill(canvas, x, y, 5, 4, g.color_a)
        # ribbon cross
        for yy in range(y, y + 4):
            pset(canvas, x + 2, yy, g.color_b)
        for xx in range(x, x + 5):
            pset(canvas, xx, y + 1, g.color_b)
        # bow
        if g.kind == 1:
            pset(canvas, x + 1, y + 0, g.color_b)
            pset(canvas, x + 3, y + 0, g.color_b)
    else:
        rect_fill(canvas, x, y + 1, 4, 3, g.color_a)
        pset(canvas, x + 1, y + 2, g.color_b)
        pset(canvas, x + 2, y + 2, g.color_b)

def draw_conveyor(canvas, t: float):
    rect_fill(canvas, 0, BELT_Y, WIDTH, 5, C_DGRAY)
    rect_fill(canvas, 0, BELT_Y + 4, WIDTH, 1, C_GRAY)
    for x in range(0, WIDTH, 3):
        phase = (x * 0.25 + t * 6.0)
        yy = BELT_Y + 1 + int(1.0 * (math.sin(phase) * 0.5 + 0.5))
        pset(canvas, x, yy, C_GRAY)


# ----------------------------
# Elf sprites + props
# ----------------------------
def draw_elf(canvas, x: int, y: int, frame: int, job: int):
    """
    Tiny elf about 7x7.
    job: 0=hammer, 1=paint, 2=carry
    """
    skin = C_WARMWH
    suit = C_GREEN if (x // 2) % 2 == 0 else C_RED
    hat = C_RED if suit == C_GREEN else C_GREEN
    boot = C_DBROWN

    # head
    pset(canvas, x + 3, y + 0, skin)
    pset(canvas, x + 2, y + 1, skin)
    pset(canvas, x + 3, y + 1, skin)
    pset(canvas, x + 4, y + 1, skin)

    # hat + pom
    pset(canvas, x + 2, y + 0, hat)
    pset(canvas, x + 1, y + 1, hat)
    pset(canvas, x + 5, y + 1, hat)
    pset(canvas, x + 5, y + 0, C_WHITE)

    # body
    rect_fill(canvas, x + 2, y + 2, 3, 3, suit)
    pset(canvas, x + 3, y + 3, C_BLACK)  # belt dot

    # legs / boots
    pset(canvas, x + 2, y + 5, suit)
    pset(canvas, x + 4, y + 5, suit)
    step = frame % 2
    if step == 0:
        pset(canvas, x + 2, y + 6, boot)
        pset(canvas, x + 4, y + 6, boot)
    else:
        pset(canvas, x + 3, y + 6, boot)
        pset(canvas, x + 5, y + 6, boot)

    # arms + tool
    if job == 0:  # hammer
        pset(canvas, x + 1, y + 3, suit)
        swing = (frame // 4) % 3
        if swing == 0:
            pset(canvas, x + 0, y + 2, C_GRAY)
            pset(canvas, x + 0, y + 1, C_GRAY)
        elif swing == 1:
            pset(canvas, x + 0, y + 3, C_GRAY)
            pset(canvas, x + 0, y + 2, C_GRAY)
        else:
            pset(canvas, x + 1, y + 2, C_GRAY)
            pset(canvas, x + 0, y + 1, C_GRAY)
    elif job == 1:  # paint
        pset(canvas, x + 5, y + 3, suit)
        pset(canvas, x + 6, y + 2, C_BROWN)  # brush handle
        if (frame % 8) < 3:
            pset(canvas, x + 6, y + 1, C_YELLOW)  # paint dab
    else:  # carry
        pset(canvas, x + 1, y + 3, suit)
        pset(canvas, x + 5, y + 3, suit)
        box_c = C_RED if (frame // 10) % 2 == 0 else C_BLUE
        rect_fill(canvas, x + 2, y + 2, 3, 2, box_c)
        pset(canvas, x + 3, y + 2, C_WHITE)

def draw_workbench(canvas, x: int, y: int, w: int):
    rect_fill(canvas, x, y, w, 2, C_TAN)
    for lx in range(x + 1, x + w, 6):
        rect_fill(canvas, lx, y + 2, 2, 5, C_DBROWN)

    # toy on bench
    rect_fill(canvas, x + w - 10, y - 1, 6, 2, C_BLUE)
    pset(canvas, x + w - 8, y - 2, C_YELLOW)

def draw_box_stack(canvas, base_x: int, base_y: int):
    rect_fill(canvas, base_x + 0, base_y - 4, 6, 5, C_RED)
    rect_fill(canvas, base_x + 1, base_y - 8, 5, 4, C_GREEN)
    for yy in range(base_y - 4, base_y + 1):
        pset(canvas, base_x + 3, yy, C_WHITE)
    for xx in range(base_x + 0, base_x + 6):
        pset(canvas, xx, base_y - 2, C_WHITE)
    for yy in range(base_y - 8, base_y - 4):
        pset(canvas, base_x + 3, yy, C_WHITE)
    for xx in range(base_x + 1, base_x + 6):
        pset(canvas, xx, base_y - 6, C_WHITE)

    rect_fill(canvas, base_x + 8, base_y - 4, 7, 5, C_BLUE)
    rect_fill(canvas, base_x + 9, base_y - 9, 6, 5, C_PINK)
    for yy in range(base_y - 9, base_y + 1):
        pset(canvas, base_x + 11, yy, C_WHITE)


# ----------------------------
# Main
# ----------------------------
def main():
    if RNG_SEED != 0:
        random.seed(RNG_SEED)
    else:
        random.seed()

    matrix, canvas = load_matrix()

    
    # Optional font
    font = graphics.Font()
    have_font = True
    try:
        font.LoadFont("fonts/4x6.bdf")
    except Exception:
        have_font = False

    flakes = init_snow(SNOW_COUNT)
    gifts: List[Gift] = []
    next_spawn = 0.0

    bench_x, bench_y, bench_w = 34, 16, 30

    t0 = time.time()
    last = t0
    frame = 0

    try:
        while True:
            now = time.time()
            dt = now - last
            last = now
            t = now - t0
            frame += 1

            # update snow outside
            wind = 2.2 * math.sin(t * 0.6)
            update_snow(flakes, dt, wind)

            # spawn gifts
            next_spawn -= dt
            spawn_interval = max(0.12, 0.35 / max(0.2, GIFT_DENSITY))
            if next_spawn <= 0.0:
                gifts.append(spawn_gift())
                next_spawn = spawn_interval

            # move gifts on belt
            for g in gifts:
                g.x -= BELT_SPEED * dt
            gifts = [g for g in gifts if g.x > -10]

            # ---- draw frame ----
            draw_workshop_bg(canvas, t)
            draw_window(canvas, t, flakes)

            # window sill mini-lights
            for i, x in enumerate(range(WINDOW_X, WINDOW_X + WINDOW_W, 4)):
                if (math.sin(t * 2.8 + i) * 0.5 + 0.5) > 0.55:
                    pset(canvas, x, WINDOW_Y + WINDOW_H + 1, [C_RED, C_YELLOW, C_BLUE, C_PINK][i % 4])

            # workbench + elves
            draw_workbench(canvas, bench_x, bench_y, bench_w)
            draw_elf(canvas, bench_x + 2,  bench_y - 3, frame,     job=0)  # hammer
            draw_elf(canvas, bench_x + 12, bench_y - 3, frame + 2, job=1)  # paint

            # carrying elf walks near belt
            carry_x = 10 + int((t * 10) % (WIDTH - 40))
            draw_elf(canvas, carry_x, BELT_Y - 8, frame + 5, job=2)

            # conveyor + gifts
            draw_conveyor(canvas, t)
            for g in gifts:
                draw_gift(canvas, int(g.x), BELT_Y - 4, g)

            # stacks of presents at right
            draw_box_stack(canvas, base_x=WIDTH - 20, base_y=HEIGHT - 1)

            # sign text (blink)
            if have_font and (int(t * 2) % 2 == 0):
                graphics.DrawText(
                    canvas, font, 34, 10,
                    graphics.Color(C_WARMWH.r, C_WARMWH.g, C_WARMWH.b),
                    "ELF SHOP"
                )

            # sparkles near toy on bench
            if (frame % 10) < 3:
                pset(canvas, bench_x + bench_w - 4, bench_y - 3, C_WHITE)
                pset(canvas, bench_x + bench_w - 2, bench_y - 2, C_WHITE)

            # present
            canvas = matrix.SwapOnVSync(canvas)

            # pacing
            target = 1.0 / FPS
            work = time.time() - now
            if work < target:
                time.sleep(target - work)

    except KeyboardInterrupt:
        pass
    finally:
        canvas.Clear()
        matrix.SwapOnVSync(canvas)


if __name__ == "__main__":
    main()
