#!/usr/bin/env python3
"""
Basic Mario-style platformer for 128x32 RGB matrix (single file)

Changes per request:
- 3 lives
- When hit by an enemy: lose 1 life AND restart level from spawn
- Breakable bricks + platforms
- "Bricks / blocks" are 9x9 pixels as the basic size (drawn as 9x9 tiles)
  NOTE: 128x32 can only fit 3 tiles vertically (27px) + some HUD. This game uses:
    - Tile size = 9
    - Playfield height = 27px (3 tiles tall)
    - HUD uses the remaining 5px (top), with tiny indicators

Controls (RGBMatrixEmulator when events work):
- Left/Right arrows: move
- Space: jump
- R: reset
- Q / Esc: quit

If no event loop is available, it runs in demo mode.

This is intentionally minimal but playable and looks good at 9x9 blocks.
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
matrix, canvas = load_matrix()

def now_s():
    return time.monotonic()


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


TILE = 9  # requested basic size


# ---------------------------
# Tiny 5px HUD font substitute (we'll just draw pixels)
# ---------------------------
def draw_lives(canvas, x, y, lives, color):
    # Draw up to 3 tiny hearts/blocks
    for i in range(3):
        xx = x + i * 4
        if i < lives:
            canvas.SetPixel(xx + 0, y + 1, color.red, color.green, color.blue)
            canvas.SetPixel(xx + 1, y + 0, color.red, color.green, color.blue)
            canvas.SetPixel(xx + 2, y + 0, color.red, color.green, color.blue)
            canvas.SetPixel(xx + 3, y + 1, color.red, color.green, color.blue)
            canvas.SetPixel(xx + 1, y + 2, color.red, color.green, color.blue)
            canvas.SetPixel(xx + 2, y + 2, color.red, color.green, color.blue)
        else:
            # outline
            canvas.SetPixel(xx + 1, y + 1, 40, 40, 40)
            canvas.SetPixel(xx + 2, y + 1, 40, 40, 40)


def draw_digit_3x5(canvas, x, y, d, color):
    # Minimal 3x5 digits (0-9)
    DIG = {
        0: ["111","101","101","101","111"],
        1: ["010","110","010","010","111"],
        2: ["111","001","111","100","111"],
        3: ["111","001","111","001","111"],
        4: ["101","101","111","001","001"],
        5: ["111","100","111","001","111"],
        6: ["111","100","111","101","111"],
        7: ["111","001","001","001","001"],
        8: ["111","101","111","101","111"],
        9: ["111","101","111","001","111"],
    }
    mask = DIG.get(int(d), DIG[0])
    for ry, row in enumerate(mask):
        for rx, ch in enumerate(row):
            if ch == "1":
                canvas.SetPixel(x + rx, y + ry, color.red, color.green, color.blue)


def draw_number(canvas, x, y, n, color):
    s = str(max(0, int(n)))
    for i, ch in enumerate(s[-4:]):  # last 4 digits
        draw_digit_3x5(canvas, x + i * 4, y, int(ch), color)


# ---------------------------
# Tiles
# ---------------------------
EMPTY = 0
SOLID = 1       # platform (unbreakable)
BRICK = 2       # breakable
COIN = 3        # collectible coin (tile cell)
ENEMY = 4       # enemy spawn marker


@dataclass
class Brick:
    tx: int
    ty: int
    kind: int  # SOLID or BRICK
    alive: bool = True


@dataclass
class Coin:
    tx: int
    ty: int
    taken: bool = False


@dataclass
class Goomba:
    x: float  # pixel space within playfield
    y: float
    vx: float
    alive: bool = True


class Mario9:
    def __init__(self, screen_w=128, screen_h=32, seed=None):
        if seed is not None:
            random.seed(seed)

        self.sw = screen_w
        self.sh = screen_h

        # Layout:
        # HUD: top 5px
        # Playfield: remaining 27px (3 tiles tall)
        self.hud_h = 5
        self.pf_y0 = self.hud_h
        self.pf_h = self.sh - self.hud_h  # should be 27 on 32px tall
        self.pf_w = self.sw

        # Tile grid
        self.grid_w = self.pf_w // TILE  # 128//9 = 14 tiles (126px), we leave 2px slack on right
        self.grid_h = self.pf_h // TILE  # 27//9 = 3 tiles

        # Pixel slack (center the tile area inside playfield)
        self.tile_area_w = self.grid_w * TILE
        self.tile_area_h = self.grid_h * TILE
        self.tile_x0 = (self.pf_w - self.tile_area_w) // 2
        self.tile_y0 = self.pf_y0 + (self.pf_h - self.tile_area_h) // 2

        # Colors
        self.c_bg = graphics.Color(0, 0, 0)
        self.c_solid = graphics.Color(60, 120, 255)    # platforms
        self.c_brick = graphics.Color(170, 90, 30)     # breakable bricks
        self.c_brick_hi = graphics.Color(220, 140, 60) # highlights
        self.c_coin = graphics.Color(255, 220, 0)
        self.c_enemy = graphics.Color(200, 120, 40)
        self.c_mario_red = graphics.Color(255, 40, 40)
        self.c_mario_blue = graphics.Color(60, 120, 255)
        self.c_mario_skin = graphics.Color(255, 200, 160)
        self.c_mario_brown = graphics.Color(140, 80, 30)
        self.c_hud = graphics.Color(180, 180, 180)
        self.c_hud_dim = graphics.Color(60, 60, 60)

        # Player size (in pixels) – small relative to 9x9
        self.pw = 6
        self.ph = 8

        # Physics
        self.gravity = 260.0
        self.jump_v = -120.0
        self.move_speed = 75.0
        self.max_fall = 220.0

        # Input
        self.in_left = False
        self.in_right = False
        self.in_jump = False
        self._jump_edge = False

        # Lives + score
        self.lives = 3
        self.score = 0

        # World (1 screen, no scroll) because 3 tiles tall is tight; keep it clean.
        self.reset_level(full_reset=True)

    # ---------------------------
    # Level building
    # ---------------------------
    def reset_level(self, full_reset=False):
        if full_reset:
            self.lives = 3
            self.score = 0

        self.game_over = False
        self.win = False

        # Build a 14x3 tile grid
        # Rows: 0 top, 2 bottom
        # Bottom row mostly solid ground, with gaps for little challenge.
        self.tiles = [[EMPTY for _ in range(self.grid_w)] for _ in range(self.grid_h)]

        # Ground (row 2)
        for x in range(self.grid_w):
            self.tiles[2][x] = SOLID

        # Create two small holes (gaps) in ground
        for x in [4, 5, 10]:
            if 0 <= x < self.grid_w:
                self.tiles[2][x] = EMPTY

        # Floating platforms/bricks on row 1 and row 0
        # Unbreakable platforms
        for x in [2, 3]:
            self.tiles[1][x] = SOLID
        for x in [7, 8]:
            self.tiles[1][x] = SOLID

        # Breakable brick line near top
        for x in [5, 6, 9]:
            self.tiles[0][x] = BRICK

        # Coins on top of some platforms
        self.coins = []
        for (cx, cy) in [(2, 0), (3, 0), (7, 0), (8, 0), (12, 1)]:
            if 0 <= cx < self.grid_w and 0 <= cy < self.grid_h:
                self.coins.append(Coin(cx, cy))

        # Bricks list (so we can "destroy" them)
        self.bricks = []
        for ty in range(self.grid_h):
            for tx in range(self.grid_w):
                if self.tiles[ty][tx] in (SOLID, BRICK):
                    self.bricks.append(Brick(tx, ty, self.tiles[ty][tx], alive=True))

        # Enemies
        self.goombas = [
            Goomba(self.tile_to_px_x(11) + 1, self.tile_to_px_y(2) - 4, vx=-28.0),
        ]

        # Player spawn (above ground)
        self.spawn_x = self.tile_to_px_x(1) + 2
        self.spawn_y = self.tile_to_px_y(2) - self.ph - 1
        self.x = float(self.spawn_x)
        self.y = float(self.spawn_y)
        self.vx = 0.0
        self.vy = 0.0
        self.facing = 1
        self.on_ground = False

    # ---------------------------
    # Coordinate helpers
    # ---------------------------
    def tile_to_px_x(self, tx):
        return self.tile_x0 + tx * TILE

    def tile_to_px_y(self, ty):
        return self.tile_y0 + ty * TILE

    def px_to_tile(self, px, py):
        tx = (px - self.tile_x0) // TILE
        ty = (py - self.tile_y0) // TILE
        return int(tx), int(ty)

    # ---------------------------
    # Input hooks
    # ---------------------------
    def on_left(self, down: bool):
        self.in_left = down

    def on_right(self, down: bool):
        self.in_right = down

    def on_jump(self, down: bool):
        self.in_jump = down

    # ---------------------------
    # Collision helpers
    # ---------------------------
    def aabb(self, ax, ay, aw, ah, bx, by, bw, bh):
        return (ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by)

    def _solid_at_tile(self, tx, ty):
        if tx < 0 or tx >= self.grid_w or ty < 0 or ty >= self.grid_h:
            return True  # outside -> solid
        # Need to consider destroyed bricks
        t = self.tiles[ty][tx]
        if t in (SOLID, BRICK):
            # verify alive brick
            for b in self.bricks:
                if b.tx == tx and b.ty == ty and b.alive:
                    return True
            return False
        return False

    def _resolve_axis(self, ox, oy, nx, ny):
        """
        Resolve collisions vs 9x9 tile solids using axis separation.
        """
        x = nx
        y = oy
        # X axis
        if nx != ox:
            # sample points along player's vertical span
            for sy in [0, self.ph - 1]:
                tx, ty = self.px_to_tile(int(nx + (0 if nx < ox else self.pw - 1)), int(oy + sy))
                if self._solid_at_tile(tx, ty):
                    if nx > ox:
                        # hit right side of tile
                        tile_px = self.tile_to_px_x(tx)
                        x = tile_px - self.pw
                    else:
                        tile_px = self.tile_to_px_x(tx) + TILE
                        x = tile_px
                    self.vx = 0.0
                    break

        # Y axis
        y = ny
        self.on_ground = False
        if ny != oy:
            dir_down = ny > oy
            # sample points along player's horizontal span
            for sx in [0, self.pw - 1]:
                tx, ty = self.px_to_tile(int(x + sx), int(ny + (self.ph - 1 if dir_down else 0)))
                if self._solid_at_tile(tx, ty):
                    if dir_down:
                        tile_py = self.tile_to_px_y(ty)
                        y = tile_py - self.ph
                        self.vy = 0.0
                        self.on_ground = True
                    else:
                        # head bump
                        tile_py = self.tile_to_px_y(ty) + TILE
                        y = tile_py
                        # attempt to break brick if it's breakable
                        self._bump_tile(tx, ty)
                        self.vy = 0.0
                    break

        return x, y

    def _bump_tile(self, tx, ty):
        # If tile is BRICK and alive, destroy it
        # Only break bricks (not SOLID)
        if tx < 0 or tx >= self.grid_w or ty < 0 or ty >= self.grid_h:
            return
        if self.tiles[ty][tx] != BRICK:
            return
        for b in self.bricks:
            if b.tx == tx and b.ty == ty and b.alive and b.kind == BRICK:
                b.alive = False
                self.score += 25
                break

    def _restart_from_hit(self):
        self.lives -= 1
        if self.lives <= 0:
            self.game_over = True
        else:
            # restart level state (bricks reset too, as requested "start over")
            self.reset_level(full_reset=False)

    # ---------------------------
    # Update
    # ---------------------------
    def update(self, dt):
        if self.game_over or self.win:
            return
        dt = min(dt, 0.05)

        # Input -> velocity
        self.vx = 0.0
        if self.in_left:
            self.vx -= self.move_speed
            self.facing = -1
        if self.in_right:
            self.vx += self.move_speed
            self.facing = 1

        # Jump edge trigger
        if self.in_jump and not self._jump_edge:
            self._jump_edge = True
            if self.on_ground:
                self.vy = self.jump_v
                self.on_ground = False
        if not self.in_jump:
            self._jump_edge = False

        # Gravity
        self.vy += self.gravity * dt
        self.vy = min(self.vy, self.max_fall)

        # Integrate & resolve
        ox, oy = self.x, self.y
        nx = self.x + self.vx * dt
        ny = self.y + self.vy * dt

        # Keep inside tile area bounds
        min_x = self.tile_x0 + 1
        max_x = self.tile_x0 + self.tile_area_w - self.pw - 1
        min_y = self.tile_y0 - 2
        max_y = self.tile_y0 + self.tile_area_h - self.ph - 1
        nx = clamp(nx, min_x, max_x)
        ny = clamp(ny, min_y, max_y + 50)  # allow falling into pit a bit

        self.x, self.y = self._resolve_axis(ox, oy, nx, ny)

        # Falling into a hole -> lose life + restart
        if self.y > (self.tile_y0 + self.tile_area_h + 5):
            self._restart_from_hit()
            return

        # Coins
        px_c = int(self.x + self.pw // 2)
        py_c = int(self.y + self.ph // 2)
        tx, ty = self.px_to_tile(px_c, py_c)
        for c in self.coins:
            if not c.taken and c.tx == tx and c.ty == ty:
                c.taken = True
                self.score += 10

        # Enemies
        for g in self.goombas:
            if not g.alive:
                continue

            # Move goomba on ground line (simple)
            g.x += g.vx * dt

            # Bounce at solid tiles / edges
            gx_left = int(g.x)
            gx_right = int(g.x + 3)
            gy_feet = int(g.y + 3)

            # If walking into wall, reverse
            look_dx = -1 if g.vx < 0 else 1
            look_x = gx_left - 1 if look_dx < 0 else gx_right + 1
            ltx, lty = self.px_to_tile(look_x, gy_feet)
            if self._solid_at_tile(ltx, lty):
                g.vx *= -1

            # If stepping into hole (no ground tile under next step), reverse
            under_x = gx_left - 1 if look_dx < 0 else gx_right + 1
            utx, uty = self.px_to_tile(under_x, gy_feet + 1)
            if not self._solid_at_tile(utx, uty):
                g.vx *= -1

            # Player collision with enemy
            if self.aabb(int(self.x), int(self.y), self.pw, self.ph, int(g.x), int(g.y), 4, 4):
                # stomp if falling and above
                if self.vy > 30 and (self.y + self.ph - 1) <= g.y + 1:
                    g.alive = False
                    self.vy = self.jump_v * 0.6
                    self.score += 100
                else:
                    self._restart_from_hit()
                    return

        # Win when all coins collected and goomba dead (simple goal)
        if all(c.taken for c in self.coins) and all(not e.alive for e in self.goombas):
            self.win = True

    # ---------------------------
    # Render
    # ---------------------------
    def render(self, canvas):
        canvas.Clear()

        # HUD (top 5px)
        draw_lives(canvas, 1, 0, self.lives, self.c_hud)
        draw_number(canvas, 18, 0, self.score, self.c_hud)

        if self.win:
            # tiny "W" indicator
            canvas.SetPixel(110, 1, 80, 255, 120)
            canvas.SetPixel(111, 2, 80, 255, 120)
            canvas.SetPixel(112, 1, 80, 255, 120)
        if self.game_over:
            canvas.SetPixel(110, 1, 255, 80, 80)
            canvas.SetPixel(111, 1, 255, 80, 80)
            canvas.SetPixel(112, 1, 255, 80, 80)

        # Tile area border (optional subtle)
        # (kept off to save pixels)

        # Draw bricks/platforms as 9x9 blocks
        for b in self.bricks:
            if not b.alive:
                continue
            px = self.tile_to_px_x(b.tx)
            py = self.tile_to_px_y(b.ty)
            if b.kind == SOLID:
                c = self.c_solid
                for yy in range(TILE):
                    for xx in range(TILE):
                        canvas.SetPixel(px + xx, py + yy, c.red, c.green, c.blue)
            else:
                # Brick with simple outline/highlight so it reads as "brick"
                for yy in range(TILE):
                    for xx in range(TILE):
                        if xx == 0 or yy == 0 or xx == TILE - 1 or yy == TILE - 1:
                            canvas.SetPixel(px + xx, py + yy, self.c_brick_hi.red, self.c_brick_hi.green, self.c_brick_hi.blue)
                        else:
                            canvas.SetPixel(px + xx, py + yy, self.c_brick.red, self.c_brick.green, self.c_brick.blue)
                # mortar line
                if TILE >= 9:
                    for xx in range(1, TILE - 1):
                        canvas.SetPixel(px + xx, py + 4, 120, 60, 20)

        # Coins (4x4-ish centered in tile)
        for c in self.coins:
            if c.taken:
                continue
            px = self.tile_to_px_x(c.tx) + (TILE // 2) - 2
            py = self.tile_to_px_y(c.ty) + (TILE // 2) - 2
            for yy in range(4):
                for xx in range(4):
                    if (xx in (1,2) and yy in (0,3)) or (yy in (1,2) and xx in (0,3)) or (xx in (1,2) and yy in (1,2)):
                        canvas.SetPixel(px + xx, py + yy, self.c_coin.red, self.c_coin.green, self.c_coin.blue)

        # Enemies (goomba) 4x4
        for g in self.goombas:
            if not g.alive:
                continue
            gx = int(g.x)
            gy = int(g.y)
            for yy in range(4):
                for xx in range(4):
                    canvas.SetPixel(gx + xx, gy + yy, self.c_enemy.red, self.c_enemy.green, self.c_enemy.blue)
            # little eyes
            canvas.SetPixel(gx + 1, gy + 1, 0, 0, 0)
            canvas.SetPixel(gx + 2, gy + 1, 0, 0, 0)

        # Mario (6x8) simple colored blocks for readability
        mx = int(self.x)
        my = int(self.y)

        # Hat/head
        for yy in range(2):
            for xx in range(6):
                canvas.SetPixel(mx + xx, my + yy, self.c_mario_red.red, self.c_mario_red.green, self.c_mario_red.blue)
        # Face
        for yy in range(2, 4):
            for xx in range(6):
                canvas.SetPixel(mx + xx, my + yy, self.c_mario_skin.red, self.c_mario_skin.green, self.c_mario_skin.blue)
        # Shirt/arms
        for yy in range(4, 5):
            for xx in range(6):
                canvas.SetPixel(mx + xx, my + yy, self.c_mario_red.red, self.c_mario_red.green, self.c_mario_red.blue)
        # Overalls
        for yy in range(5, 7):
            for xx in range(6):
                canvas.SetPixel(mx + xx, my + yy, self.c_mario_blue.red, self.c_mario_blue.green, self.c_mario_blue.blue)
        # Shoes
        for yy in range(7, 8):
            for xx in range(6):
                canvas.SetPixel(mx + xx, my + yy, self.c_mario_brown.red, self.c_mario_brown.green, self.c_mario_brown.blue)

        # Indicate facing by a single pixel "nose"
        if self.facing >= 0:
            canvas.SetPixel(mx + 5, my + 3, 0, 0, 0)
        else:
            canvas.SetPixel(mx + 0, my + 3, 0, 0, 0)


# ------------------------------------------------------------
# Main loop + input (emulator)
# ------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--width", type=int, default=128)
    parser.add_argument("--height", type=int, default=32)
    parser.add_argument("--fps", type=int, default=60)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    game = Mario9(args.width, args.height, seed=args.seed)

    off = matrix.CreateFrameCanvas()
    target_dt = 1.0 / max(1.0, args.fps)
    last = now_s()

    have_events = hasattr(matrix, "process")

    # Demo behavior
    demo_t = 0.0
    demo_jump_cd = 0.0

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

                        # pygame KEYDOWN=2 KEYUP=3
                        if et == 2:
                            if key == 276:      # left
                                game.on_left(True)
                            elif key == 275:    # right
                                game.on_right(True)
                            elif key == 32:     # space
                                game.on_jump(True)
                            elif key in (114, 82):  # r/R
                                game.reset_level(full_reset=True)
                            elif key in (113, 27):  # q/esc
                                raise KeyboardInterrupt
                        elif et == 3:
                            if key == 276:
                                game.on_left(False)
                            elif key == 275:
                                game.on_right(False)
                            elif key == 32:
                                game.on_jump(False)
                except Exception:
                    pass
            else:
                # Demo: wander right/left and jump sometimes
                demo_t += dt
                demo_jump_cd = max(0.0, demo_jump_cd - dt)

                # switch direction periodically
                if int(demo_t) % 6 < 3:
                    game.on_right(True)
                    game.on_left(False)
                else:
                    game.on_left(True)
                    game.on_right(False)

                if demo_jump_cd <= 0 and random.random() < 0.08:
                    game.on_jump(True)
                    demo_jump_cd = 0.6
                else:
                    game.on_jump(False)

                if demo_t > 30:
                    demo_t = 0.0

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
