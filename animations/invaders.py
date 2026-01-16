#!/usr/bin/env python3
import argparse
import os
import random
import sys
import time
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.matrix import load_matrix, import_matrix

# Graphics module needed at module level for Color definitions in class
_, _, graphics = import_matrix()

# Asset paths
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "../../assets")

default_font = graphics.Font()
default_font.LoadFont(os.path.join(ASSETS_DIR, "fonts/4x6.bdf"))

def now_s():
    return time.monotonic()


def sprite_size(sprite):
    return len(sprite[0]), len(sprite)


def draw_sprite_scaled(canvas, x, y, sprite, color, scale: float):
    """
    Draw sprite at logical (x,y) with scaling.
    - scale >= 1: blocky upsample
    - scale < 1 : nearest-neighbor downsample
    """
    if scale <= 0:
        return

    sx0 = int(round(x * scale))
    sy0 = int(round(y * scale))
    sw, sh = sprite_size(sprite)

    if scale >= 1.0:
        block = max(1, int(round(scale)))
        for row, line in enumerate(sprite):
            for col, ch in enumerate(line):
                if ch != "1":
                    continue
                px = sx0 + col * block
                py = sy0 + row * block
                for yy in range(block):
                    for xx in range(block):
                        canvas.SetPixel(px + xx, py + yy, color.red, color.green, color.blue)
        return

    out_w = max(1, int(round(sw * scale)))
    out_h = max(1, int(round(sh * scale)))

    for oy in range(out_h):
        sy = min(sh - 1, int(oy / scale))
        line = sprite[sy]
        for ox in range(out_w):
            sx = min(sw - 1, int(ox / scale))
            if line[sx] == "1":
                canvas.SetPixel(sx0 + ox, sy0 + oy, color.red, color.green, color.blue)


@dataclass
class Bullet:
    x: float
    y: float
    dy: float
    alive: bool = True


# ------------------------------
# Sprites
# ------------------------------
# Player: 6x4 (reads well at 0.5)
PLAYER_SPRITE = [
    "001100",
    "011110",
    "010010",
]  # 6x4

# Invaders: MUST be <= 5x5, grid is 5x3
INVADER_A = [
    "01110",
    "11111",
    "10101",
    "01010",
]  # 5x5

INVADER_B = [
    "01110",
    "11111",
    "11011",
    "10101",
]  # 5x5

# UFO: small, optional
UFO = [
    "01111110",
    "11111111",
    "01011010",
]  # 8x3


class SpaceInvaders:
    def __init__(self, screen_w, screen_h, scale=0.5, seed=None):
        self.screen_w = int(screen_w)
        self.screen_h = int(screen_h)
        self.scale = float(scale)

        # Logical coordinate space
        self.w = max(1, int(round(self.screen_w / self.scale)))
        self.h = max(1, int(round(self.screen_h / self.scale)))

        if seed is not None:
            random.seed(seed)

        # Colors
        self.c_player = graphics.Color(0, 255, 80)
        self.c_invader = graphics.Color(255, 255, 255)
        self.c_bullet = graphics.Color(255, 60, 60)
        self.c_inv_bullet = graphics.Color(255, 255, 0)
        self.c_ufo = graphics.Color(60, 160, 255)
        self.c_text = graphics.Color(120, 120, 120)

        # Player
        self.player_w, self.player_h = sprite_size(PLAYER_SPRITE)
        self.player_x = (self.w - self.player_w) / 2.0
        self.player_y = self.h - self.player_h - 1
        self.player_dir = 1
        self.player_speed = 18.0  # logical px/s

        # Bullets
        self.player_bullets = []
        self.invader_bullets = []
        self.player_fire_cd = 0.0

        # Invaders (5x5, grid 5x3)
        self.inv_w, self.inv_h = sprite_size(INVADER_A)
        self.invaders = []
        self.inv_dir = 1
        self.inv_speed = 8.5
        self.inv_step_down = 4
        self.inv_anim_t = 0.0
        self.inv_anim_rate = 0.35

        # Score/state
        self.score = 0
        self.game_over = False
        self.win = False

        # UFO
        self.ufo_w, self.ufo_h = sprite_size(UFO)
        self.ufo_alive = False
        self.ufo_x = -999.0
        self.ufo_y = 1.0
        self.ufo_dir = 1
        self.ufo_speed = 22.0
        self.ufo_next_spawn = 4.0 + random.random() * 6.0

        self.reset_wave()

    def reset_wave(self):
        self.invaders.clear()

        # Exactly 5x3 grid
        cols = 7
        rows = 3

        # Spacing tuned for 5x5 invaders
        spacing_x = self.inv_w + 2
        spacing_y = self.inv_h + 1

        # Center the formation
        formation_w = cols * self.inv_w + (cols - 1) * (spacing_x - self.inv_w)
        formation_h = rows * self.inv_h + (rows - 1) * (spacing_y - self.inv_h)

        left = max(0, int((self.w - formation_w) / 2))
        top = max(1, int((self.h * 0.15) - (formation_h / 2)))
        top = max(1, top)

        for r in range(rows):
            for c in range(cols):
                x = float(left + c * spacing_x)
                y = float(top + r * spacing_y)
                self.invaders.append({"x": x, "y": y, "frame": 0, "alive": True})

        self.inv_dir = 1
        self.player_bullets.clear()
        self.invader_bullets.clear()
        self.player_fire_cd = 0.0
        self.game_over = False
        self.win = False

    def aabb_hit(self, ax, ay, aw, ah, bx, by, bw, bh):
        return (ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by)

    def fire_player(self):
        if self.player_fire_cd > 0:
            return
        bx = self.player_x + self.player_w / 2.0
        by = self.player_y - 1.0
        self.player_bullets.append(Bullet(bx, by, dy=-1.0))
        self.player_fire_cd = 0.28

    def fire_invader_random(self):
        alive = [inv for inv in self.invaders if inv["alive"]]
        if not alive:
            return
        shooter = random.choice(alive)
        bx = shooter["x"] + self.inv_w / 2.0
        by = shooter["y"] + self.inv_h
        self.invader_bullets.append(Bullet(bx, by, dy=+1.0))

    def update(self, dt):
        if self.game_over or self.win:
            return

        # Auto-demo player movement
        self.player_x += self.player_dir * self.player_speed * dt
        if self.player_x <= 0:
            self.player_x = 0
            self.player_dir = 1
        if self.player_x + self.player_w >= self.w - 1:
            self.player_x = self.w - self.player_w - 1
            self.player_dir = -1

        # Auto-fire
        self.player_fire_cd = max(0.0, self.player_fire_cd - dt)
        if random.random() < 0.06:
            self.fire_player()

        # Animate invaders
        self.inv_anim_t += dt
        if self.inv_anim_t >= self.inv_anim_rate:
            self.inv_anim_t -= self.inv_anim_rate
            for inv in self.invaders:
                if inv["alive"]:
                    inv["frame"] ^= 1

        # Move invader group
        alive = [inv for inv in self.invaders if inv["alive"]]
        if not alive:
            self.win = True
        else:
            min_x = min(inv["x"] for inv in alive)
            max_x = max(inv["x"] + self.inv_w for inv in alive)

            dx = self.inv_dir * self.inv_speed * dt
            if (max_x + dx >= self.w - 1) or (min_x + dx <= 0):
                self.inv_dir *= -1
                for inv in alive:
                    inv["y"] += self.inv_step_down

                lowest = max(inv["y"] + self.inv_h for inv in alive)
                if lowest >= self.player_y:
                    self.game_over = True
            else:
                for inv in alive:
                    inv["x"] += dx

            if random.random() < 0.10:
                self.fire_invader_random()

        # UFO spawn / move (optional eye-candy)
        self.ufo_next_spawn -= dt
        if (not self.ufo_alive) and self.ufo_next_spawn <= 0:
            self.ufo_alive = True
            self.ufo_dir = random.choice([-1, 1])
            self.ufo_x = float(-self.ufo_w) if self.ufo_dir == 1 else float(self.w + 1)
            self.ufo_y = 1.0
            self.ufo_next_spawn = 6.0 + random.random() * 10.0

        if self.ufo_alive:
            self.ufo_x += self.ufo_dir * self.ufo_speed * dt
            if self.ufo_dir == 1 and self.ufo_x > self.w + 1:
                self.ufo_alive = False
            elif self.ufo_dir == -1 and self.ufo_x < -self.ufo_w - 1:
                self.ufo_alive = False

        # Bullets update
        for b in self.player_bullets:
            if not b.alive:
                continue
            b.y += b.dy
            if b.y < 0:
                b.alive = False

        for b in self.invader_bullets:
            if not b.alive:
                continue
            b.y += b.dy
            if b.y >= self.h:
                b.alive = False

        # Collisions: player bullets vs invaders / ufo
        for b in self.player_bullets:
            if not b.alive:
                continue

            if self.ufo_alive and self.aabb_hit(b.x, b.y, 1, 1, self.ufo_x, self.ufo_y, self.ufo_w, self.ufo_h):
                self.ufo_alive = False
                b.alive = False
                self.score += 50
                continue

            for inv in self.invaders:
                if not inv["alive"]:
                    continue
                if self.aabb_hit(b.x, b.y, 1, 1, inv["x"], inv["y"], self.inv_w, self.inv_h):
                    inv["alive"] = False
                    b.alive = False
                    self.score += 10
                    break

        # Collisions: invader bullets vs player
        for b in self.invader_bullets:
            if not b.alive:
                continue
            if self.aabb_hit(b.x, b.y, 1, 1, self.player_x, self.player_y, self.player_w, self.player_h):
                b.alive = False
                self.game_over = True
                break

        # Cleanup bullets
        self.player_bullets = [b for b in self.player_bullets if b.alive]
        self.invader_bullets = [b for b in self.invader_bullets if b.alive]

    def render(self, canvas):
        canvas.Clear()

        # HUD in screen coords
        graphics.DrawText(canvas, default_font, 1, self.screen_h - 1, self.c_text, f"{self.score}")

        # Player
        draw_sprite_scaled(canvas, self.player_x, self.player_y, PLAYER_SPRITE, self.c_player, self.scale)

        # Invaders
        for inv in self.invaders:
            if not inv["alive"]:
                continue
            sprite = INVADER_A if inv["frame"] == 0 else INVADER_B
            draw_sprite_scaled(canvas, inv["x"], inv["y"], sprite, self.c_invader, self.scale)

        # UFO
        if self.ufo_alive:
            draw_sprite_scaled(canvas, self.ufo_x, self.ufo_y, UFO, self.c_ufo, self.scale)

        # Bullets (ensure visible at small scales)
        bw = max(1, int(round(self.scale)))
        bh = max(1, int(round(self.scale)))

        for b in self.player_bullets:
            sx = int(round(b.x * self.scale))
            sy = int(round(b.y * self.scale))
            for yy in range(bh):
                for xx in range(bw):
                    canvas.SetPixel(sx + xx, sy + yy, self.c_bullet.red, self.c_bullet.green, self.c_bullet.blue)

        for b in self.invader_bullets:
            sx = int(round(b.x * self.scale))
            sy = int(round(b.y * self.scale))
            for yy in range(bh):
                for xx in range(bw):
                    canvas.SetPixel(sx + xx, sy + yy, self.c_inv_bullet.red, self.c_inv_bullet.green, self.c_inv_bullet.blue)

        # End state text
        if self.game_over:
            graphics.DrawText(canvas, default_font, 1, 20, graphics.Color(255, 80, 80), "GAME OVER")
        elif self.win:
            graphics.DrawText(canvas, default_font, 1, 20, graphics.Color(80, 255, 120), "YOU WIN")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--width", type=int, default=96)
    parser.add_argument("--height", type=int, default=32)
    parser.add_argument("--scale", type=float, default=1.0)
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()

    matrix, canvas = load_matrix()
    game = SpaceInvaders(args.width, args.height, scale=args.scale)

    off = matrix.CreateFrameCanvas()
    target_dt = 1.0 / max(1.0, args.fps)
    last = now_s()
    end_timer = 0.0

    try:
        while True:
            t = now_s()
            dt = t - last
            last = t
            dt = min(dt, 0.05)

            if game.game_over or game.win:
                end_timer += dt
                if end_timer >= 2.0:
                    end_timer = 0.0
                    game.reset_wave()
            else:
                end_timer = 0.0
                game.update(dt)

            game.render(off)
            off = matrix.SwapOnVSync(off)

            elapsed = now_s() - t
            sleep_for = target_dt - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)

    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
