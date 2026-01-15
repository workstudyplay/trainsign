#!/usr/bin/env python3
"""
Cartoon chicken flock for 128x32 RGB matrix:
- Multiple chickens walking around (unique colors/patterns)
- Occasional pecking animation
- Occasional hop/flap "try to fly"
- Occasional egg laying (eggs remain on ground for a while)

Default uses RGBMatrixEmulator. For real hardware, swap imports:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
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

# ------------------------------------------------------------
# Utilities
# ------------------------------------------------------------
def now_s():
    return time.monotonic()


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def sprite_size(sprite):
    return len(sprite[0]), len(sprite)


def flip_sprite_h(sprite):
    return [row[::-1] for row in sprite]


def draw_sprite(canvas, x, y, sprite, color):
    """Draw a 1-bit mask sprite at integer coords."""
    for ry, row in enumerate(sprite):
        py = y + ry
        for rx, px in enumerate(row):
            if px == "1":
                canvas.SetPixel(x + rx, py, color.red, color.green, color.blue)


def draw_sprite_layers(canvas, x, y, body, comb, beak_feet, palette, facing):
    """Draw layered chicken sprites with optional horizontal flip."""
    if facing < 0:
        body = flip_sprite_h(body)
        comb = flip_sprite_h(comb)
        beak_feet = flip_sprite_h(beak_feet)

    draw_sprite(canvas, x, y, body, palette.body)
    draw_sprite(canvas, x, y, comb, palette.comb)
    draw_sprite(canvas, x, y, beak_feet, palette.accent)

    # Optional speckles/pattern overlay (small “uniqueness”)
    if palette.spot is not None and palette.spot_mask is not None:
        m = palette.spot_mask
        if facing < 0:
            m = flip_sprite_h(m)
        draw_sprite(canvas, x, y, m, palette.spot)


# ------------------------------------------------------------
# Sprites (9x8, layered)
# ------------------------------------------------------------
# BODY frames (white-ish / brown-ish / etc. via palette)
CHICKEN_BODY_WALK_0 = [
    "000111000",
    "001111100",
    "011111110",
    "011111110",
    "001111100",
    "000111000",
    "000000000",
    "000000000",
]

CHICKEN_BODY_WALK_1 = [
    "000111000",
    "001111100",
    "011111110",
    "011111110",
    "001111100",
    "000111000",
    "000000000",
    "000000000",
]

CHICKEN_BODY_FLAP_0 = [
    "000111000",
    "001111100",
    "111111111",  # wings out
    "011111110",
    "001111100",
    "000111000",
    "000000000",
    "000000000",
]

CHICKEN_BODY_FLAP_1 = [
    "000111000",
    "111111111",  # wings up
    "011111110",
    "011111110",
    "001111100",
    "000111000",
    "000000000",
    "000000000",
]

# PECK frames (head down a bit)
CHICKEN_BODY_PECK_0 = [
    "000111000",
    "001111100",
    "011111110",
    "011111110",
    "001111100",
    "000111000",
    "000000000",
    "000000000",
]

CHICKEN_BODY_PECK_1 = [
    "000000000",
    "000111000",
    "001111100",
    "011111110",
    "011111110",
    "001111100",
    "000111000",
    "000000000",
]

# COMB mask (red)
CHICKEN_COMB = [
    "000010000",
    "000101000",
    "000000000",
    "000000000",
    "000000000",
    "000000000",
    "000000000",
    "000000000",
]

# BEAK + FEET mask (orange)
CHICKEN_BEAK_FEET = [
    "000000100",  # beak
    "000000000",
    "000000000",
    "000000000",
    "000000000",
    "000000000",
    "000010000",  # feet
    "000100000",
]

# Spot masks (optional uniqueness overlay)
SPOT_MASK_A = [
    "000000000",
    "000000000",
    "000100000",
    "000000000",
    "000001000",
    "000000000",
    "000000000",
    "000000000",
]

SPOT_MASK_B = [
    "000000000",
    "000010000",
    "000000000",
    "000000100",
    "000000000",
    "000001000",
    "000000000",
    "000000000",
]

SPOT_MASK_C = [
    "000000000",
    "000000000",
    "001000000",
    "000000000",
    "000010000",
    "000000000",
    "000000000",
    "000000000",
]

# Egg sprite (5x4)
EGG_SPRITE = [
    "00100",
    "01110",
    "01110",
    "00100",
]


# ------------------------------------------------------------
# Data models
# ------------------------------------------------------------
@dataclass
class Palette:
    body: graphics.Color
    comb: graphics.Color
    accent: graphics.Color
    spot: graphics.Color | None = None
    spot_mask: list[str] | None = None


@dataclass
class Egg:
    x: int
    y: int
    ttl: float
    wobble_phase: float


# ------------------------------------------------------------
# Chicken agent
# ------------------------------------------------------------
class Chicken:
    def __init__(self, world_w: int, world_h: int, palette: Palette, seed: int | None = None):
        if seed is not None:
            random.seed(seed)

        self.world_w = world_w
        self.world_h = world_h

        self.palette = palette

        self.sw, self.sh = sprite_size(CHICKEN_BODY_WALK_0)
        self.ground_y = self.world_h - self.sh - 1

        # Start somewhere reasonable
        self.x = float(random.randint(0, max(0, self.world_w - self.sw)))
        self.y = float(self.ground_y)

        # Movement
        self.dir = random.choice([-1, 1])
        self.vx = random.uniform(10.0, 22.0)

        # Animation
        self.frame = 0
        self.anim_t = 0.0
        self.anim_rate_walk = random.uniform(0.12, 0.18)
        self.anim_rate_flap = 0.08
        self.anim_rate_peck = 0.10

        # Behavior state
        self.state = "walk"  # walk | fly | peck | lay
        self.state_t = 0.0

        # Fly params
        self.fly_t = 0.0
        self.fly_duration = random.uniform(0.75, 1.05)
        self.fly_height = random.uniform(6.0, 11.0)
        self.fly_boost = random.uniform(1.25, 1.6)

        # Peck params
        self.peck_duration = random.uniform(0.6, 1.3)

        # Lay params
        self.lay_duration = random.uniform(0.6, 1.0)

        # Timers (when to do fun stuff)
        self.next_fly_in = self._rand_fly_delay()
        self.next_peck_in = self._rand_peck_delay()
        self.next_lay_in = self._rand_lay_delay()

        # Egg spawn cooldown (so we don’t spam)
        self._just_laid = False

    def _rand_fly_delay(self):
        return random.uniform(2.5, 7.0)

    def _rand_peck_delay(self):
        return random.uniform(0.8, 3.5)

    def _rand_lay_delay(self):
        return random.uniform(4.0, 10.0)

    def _advance_anim(self, dt, rate):
        self.anim_t += dt
        if self.anim_t >= rate:
            self.anim_t -= rate
            self.frame ^= 1

    def update(self, dt: float, eggs_out: list[Egg]):
        dt = min(dt, 0.05)

        # Countdown timers
        self.next_fly_in -= dt
        self.next_peck_in -= dt
        self.next_lay_in -= dt

        # Decide to switch state (only from walk)
        if self.state == "walk":
            if self.next_lay_in <= 0:
                self.state = "lay"
                self.state_t = 0.0
                self._just_laid = False
                self.next_lay_in = self._rand_lay_delay()
            elif self.next_fly_in <= 0:
                self.state = "fly"
                self.fly_t = 0.0
                self.next_fly_in = self._rand_fly_delay()
            elif self.next_peck_in <= 0:
                self.state = "peck"
                self.state_t = 0.0
                self.next_peck_in = self._rand_peck_delay()

        # State logic
        if self.state == "walk":
            # Move
            self.x += self.dir * self.vx * dt
            self.y = float(self.ground_y)

            # Bounce edges
            if self.x <= 0:
                self.x = 0.0
                self.dir = 1
            elif self.x + self.sw >= self.world_w:
                self.x = float(self.world_w - self.sw)
                self.dir = -1

            # Walk anim
            self._advance_anim(dt, self.anim_rate_walk)

        elif self.state == "peck":
            self.state_t += dt
            self.y = float(self.ground_y)

            # Slight drift while pecking (tiny)
            self.x += self.dir * (self.vx * 0.2) * dt
            self.x = clamp(self.x, 0.0, float(self.world_w - self.sw))

            self._advance_anim(dt, self.anim_rate_peck)
            if self.state_t >= self.peck_duration:
                self.state = "walk"
                self.state_t = 0.0

        elif self.state == "fly":
            self.fly_t += dt
            t = clamp(self.fly_t / self.fly_duration, 0.0, 1.0)

            # Arc: 4t(1-t)
            arc = 4.0 * t * (1.0 - t)
            self.y = float(self.ground_y - arc * self.fly_height)

            # Forward a bit more
            self.x += self.dir * self.vx * self.fly_boost * dt

            # Bounce edges even in air
            if self.x <= 0:
                self.x = 0.0
                self.dir = 1
            elif self.x + self.sw >= self.world_w:
                self.x = float(self.world_w - self.sw)
                self.dir = -1

            self._advance_anim(dt, self.anim_rate_flap)
            if self.fly_t >= self.fly_duration:
                self.state = "walk"
                self.y = float(self.ground_y)

        elif self.state == "lay":
            self.state_t += dt
            self.y = float(self.ground_y)

            # Stand mostly still; tiny shuffle
            self.x += self.dir * (self.vx * 0.05) * dt
            self.x = clamp(self.x, 0.0, float(self.world_w - self.sw))

            # Animate gently (use walk frames)
            self._advance_anim(dt, self.anim_rate_walk)

            # Drop egg about halfway through
            if (not self._just_laid) and self.state_t >= (self.lay_duration * 0.5):
                ex = int(self.x) + (self.sw // 2) - 2  # center under body (egg width ~5)
                ey = self.ground_y + self.sh - 4       # egg height ~4, sits at ground-ish
                eggs_out.append(Egg(
                    x=clamp(ex, 0, self.world_w - 5),
                    y=clamp(ey, 0, self.world_h - 4),
                    ttl=random.uniform(8.0, 18.0),
                    wobble_phase=random.uniform(0.0, 6.28),
                ))
                self._just_laid = True

            if self.state_t >= self.lay_duration:
                self.state = "walk"
                self.state_t = 0.0

    def render(self, canvas):
        x = int(self.x)
        y = int(self.y)

        if self.state == "fly":
            body = CHICKEN_BODY_FLAP_0 if self.frame == 0 else CHICKEN_BODY_FLAP_1
        elif self.state == "peck":
            body = CHICKEN_BODY_PECK_0 if self.frame == 0 else CHICKEN_BODY_PECK_1
        else:
            body = CHICKEN_BODY_WALK_0 if self.frame == 0 else CHICKEN_BODY_WALK_1

        draw_sprite_layers(canvas, x, y, body, CHICKEN_COMB, CHICKEN_BEAK_FEET, self.palette, self.dir)


# ------------------------------------------------------------
# World
# ------------------------------------------------------------
class ChickenWorld:
    def __init__(self, width: int, height: int, chicken_count: int, seed: int | None = None):
        self.w = width
        self.h = height

        if seed is not None:
            random.seed(seed)

        self.eggs: list[Egg] = []
        self.chickens: list[Chicken] = []

        # Background & UI colors
        self.c_bg = graphics.Color(0, 0, 0)
        self.c_text = graphics.Color(90, 90, 90)
        self.c_egg = graphics.Color(245, 245, 230)  # off-white egg
        self.c_shadow = graphics.Color(20, 20, 20)

        # Create unique-ish palettes
        palettes = self._make_palettes()
        spot_masks = [SPOT_MASK_A, SPOT_MASK_B, SPOT_MASK_C, None]

        for i in range(chicken_count):
            base = random.choice(palettes)

            # Add random speckles/pattern sometimes
            if random.random() < 0.55:
                spot_mask = random.choice(spot_masks)
                spot_color = graphics.Color(
                    clamp(base.body.red - random.randint(30, 80), 0, 255),
                    clamp(base.body.green - random.randint(30, 80), 0, 255),
                    clamp(base.body.blue - random.randint(30, 80), 0, 255),
                ) if spot_mask is not None else None
            else:
                spot_mask = None
                spot_color = None

            pal = Palette(
                body=base.body,
                comb=base.comb,
                accent=base.accent,
                spot=spot_color,
                spot_mask=spot_mask,
            )
            self.chickens.append(Chicken(self.w, self.h, pal))

    def _make_palettes(self):
        """A handful of cartoon chicken variants."""
        # White, tan, brown, black-ish, bluish fantasy, etc.
        return [
            Palette(body=graphics.Color(255, 255, 255), comb=graphics.Color(255, 40, 40), accent=graphics.Color(255, 170, 0)),
            Palette(body=graphics.Color(245, 230, 200), comb=graphics.Color(255, 40, 40), accent=graphics.Color(255, 165, 0)),
            Palette(body=graphics.Color(210, 170, 120), comb=graphics.Color(255, 60, 60), accent=graphics.Color(255, 150, 0)),
            Palette(body=graphics.Color(120, 90, 60),  comb=graphics.Color(255, 80, 80), accent=graphics.Color(255, 140, 0)),
            Palette(body=graphics.Color(60, 60, 60),   comb=graphics.Color(255, 50, 50), accent=graphics.Color(255, 160, 0)),
            Palette(body=graphics.Color(190, 210, 255), comb=graphics.Color(255, 50, 50), accent=graphics.Color(255, 180, 0)),
        ]

    def update(self, dt: float):
        # Update eggs
        for e in self.eggs:
            e.ttl -= dt
            e.wobble_phase += dt * 5.0
        self.eggs = [e for e in self.eggs if e.ttl > 0]

        # Update chickens (they can append eggs)
        for c in self.chickens:
            c.update(dt, self.eggs)

        # Simple collision avoidance (light touch): nudge if overlapping too much
        # Keeps flock from stacking perfectly.
        for i in range(len(self.chickens)):
            for j in range(i + 1, len(self.chickens)):
                a = self.chickens[i]
                b = self.chickens[j]
                ax, ay = int(a.x), int(a.y)
                bx, by = int(b.x), int(b.y)
                # overlap check in x only (they share same ground most of time)
                if abs(ax - bx) < 6 and abs(ay - by) < 2:
                    # push apart slightly
                    if ax <= bx:
                        a.x = max(0.0, a.x - 0.5)
                        b.x = min(float(self.w - b.sw), b.x + 0.5)
                    else:
                        a.x = min(float(self.w - a.sw), a.x + 0.5)
                        b.x = max(0.0, b.x - 0.5)

    def render(self, canvas):
        canvas.Clear()

        # Draw ground shadow strip (subtle)
        gy = self.h - 1
        for x in range(self.w):
            canvas.SetPixel(x, gy, self.c_shadow.red, self.c_shadow.green, self.c_shadow.blue)

        # Eggs (behind chickens)
        for e in self.eggs:
            # tiny wobble: shift by +/-1 px occasionally
            wobble = int(round(0.8 * (random.random() - 0.5))) if (e.ttl < 1.2) else int(round(0.7 * (0.5 * (1 + (random.random() - 0.5)))))
            ex = int(e.x + 0 * wobble)
            ey = int(e.y)
            draw_sprite(canvas, ex, ey, EGG_SPRITE, self.c_egg)

        # Chickens
        for c in self.chickens:
            c.render(canvas)

        # Tiny HUD (optional)
        # graphics.DrawText(canvas, _FONT, 1, self.h - 1, self.c_text, f"{len(self.chickens)}c {len(self.eggs)}e")


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--width", type=int, default=128)
    parser.add_argument("--height", type=int, default=32)
    parser.add_argument("--fps", type=int, default=60)
    parser.add_argument("--chickens", type=int, default=4, help="Number of chickens in the flock")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    matrix, off = load_matrix()

    world = ChickenWorld(args.width, args.height, chicken_count=max(1, args.chickens), seed=args.seed)

    target_dt = 1.0 / max(1.0, args.fps)
    last = now_s()

    try:
        while True:
            t = now_s()
            dt = t - last
            last = t
            dt = min(dt, 0.05)

            world.update(dt)
            world.render(off)
            off = matrix.SwapOnVSync(off)

            elapsed = now_s() - t
            sleep_for = target_dt - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
