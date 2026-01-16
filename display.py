#!/usr/bin/env python3
"""
Display renderer for the RGB matrix.
Uses workers' buffers to render train arrivals to the display.
Also supports running animations.
"""

import importlib.util
import os
import subprocess
import sys
import threading
import time
from typing import Dict, Optional, List, Callable

from core.matrix import load_matrix, import_matrix
from transit.worker import DataBuffers

# Import graphics for drawing
_, _, graphics = import_matrix()

# Colors
DARK_RED = graphics.Color(110, 0, 0)
GRAY = graphics.Color(90, 90, 90)
BLACK = graphics.Color(0, 0, 0)
WHITE = graphics.Color(95, 95, 95)
GREEN = graphics.Color(0, 110, 0)
BLUE = graphics.Color(0, 10, 155)
DARK_GREEN = graphics.Color(6, 64, 43)
PURPLE = graphics.Color(200, 0, 200)
DARK_PURPLE = graphics.Color(200, 100, 200)
ORANGE = graphics.Color(255, 140, 0)
YELLOW = graphics.Color(155, 155, 0)
BROWN = graphics.Color(59, 29, 12)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "../assets")


def get_route_color(route: str):
    """Get color for a subway route"""
    if route in ("A", "C", "E"):
        return BLUE
    if route in ("1", "2", "3"):
        return DARK_RED
    if route == "7X":
        return DARK_PURPLE
    if route == "7":
        return PURPLE
    if route in ("B", "D", "F", "M"):
        return ORANGE
    if route in ("N", "Q", "R", "W"):
        return YELLOW
    if route in ("J", "Z"):
        return BROWN
    if route in ("4", "5", "6"):
        return DARK_GREEN
    if route == "L":
        return GRAY
    if route == "G":
        return GREEN
    return GRAY


def draw_circle(canvas, x: int, y: int, color):
    """Draw a filled circle (subway line indicator)"""
    graphics.DrawLine(canvas, x + 2, y + 0, x + 6, y + 0, color)
    graphics.DrawLine(canvas, x + 1, y + 1, x + 7, y + 1, color)
    graphics.DrawLine(canvas, x + 0, y + 2, x + 8, y + 2, color)
    graphics.DrawLine(canvas, x + 0, y + 3, x + 8, y + 3, color)
    graphics.DrawLine(canvas, x + 0, y + 4, x + 8, y + 4, color)
    graphics.DrawLine(canvas, x + 0, y + 5, x + 8, y + 5, color)
    graphics.DrawLine(canvas, x + 0, y + 6, x + 8, y + 6, color)
    graphics.DrawLine(canvas, x + 1, y + 7, x + 7, y + 7, color)
    graphics.DrawLine(canvas, x + 2, y + 8, x + 6, y + 8, color)


class DisplayRenderer:
    """Renders train arrivals to the RGB matrix display"""

    def __init__(self, display_duration: float = 5.0):
        self.display_duration = display_duration
        self.running = False
        self.mode = 'arrivals'  # 'arrivals' or 'animations'
        self.thread: Optional[threading.Thread] = None
        self.buffers: Dict[str, DataBuffers] = {}
        self.stop_names: Dict[str, str] = {}
        self._stop_evt = threading.Event()
        self._broadcast_message: Optional[str] = None
        self._broadcast_lock = threading.Lock()

        # Animation state
        self.animations: List[Dict] = []
        self.current_animation: Optional[str] = None
        self._animation_process: Optional[subprocess.Popen] = None

        # Initialize display
        self.matrix, self.canvas, _ = load_matrix()

        # Load fonts
        self.icon_font = graphics.Font()
        self.icon_font.LoadFont(os.path.join(ASSETS_DIR, "fonts/6x10.bdf"))

        # Load larger font for broadcast messages
        self.broadcast_font = graphics.Font()
        self.broadcast_font.LoadFont(os.path.join(ASSETS_DIR, "fonts/6x10.bdf"))

    def set_buffers(self, buffers: Dict[str, DataBuffers], stop_names: Dict[str, str]):
        """Update the buffers to render from"""
        self.buffers = buffers
        self.stop_names = stop_names

    def show_broadcast(self, message: str, duration: float = 10.0):
        """Show a scrolling broadcast message for the specified duration"""
        with self._broadcast_lock:
            self._broadcast_message = message
            self._broadcast_duration = duration
        # Wake up the render loop to show the message immediately
        self._stop_evt.set()

    def start(self):
        """Start the display rendering loop"""
        if self.running:
            return

        self.running = True
        self._stop_evt.clear()
        self.thread = threading.Thread(target=self._render_loop, daemon=True)
        self.thread.start()
        print("Display renderer started")

    def stop(self):
        """Stop the display rendering loop"""
        if not self.running:
            return

        self.running = False
        self._stop_evt.set()
        if self.thread:
            self.thread.join(timeout=5)
        self._clear_display()
        print("Display renderer stopped")

    def _clear_display(self):
        """Clear the display"""
        self.canvas.Fill(0, 0, 0)
        self.matrix.SwapOnVSync(self.canvas)

    def _render_loop(self):
        """Main rendering loop"""
        while self.running:
            # Check for broadcast message
            with self._broadcast_lock:
                if self._broadcast_message:
                    message = self._broadcast_message
                    duration = getattr(self, '_broadcast_duration', 10.0)
                    self._broadcast_message = None
                    self._stop_evt.clear()
                    self._scroll_message(message, duration)
                    continue

            stop_ids = list(self.buffers.keys())

            if not stop_ids:
                self._clear_display()
                self._stop_evt.wait(1.0)
                self._stop_evt.clear()
                continue

            for stop_id in stop_ids:
                if not self.running:
                    break

                # Check for broadcast interruption
                with self._broadcast_lock:
                    if self._broadcast_message:
                        break

                self._render_stop(stop_id)
                self._stop_evt.wait(self.display_duration)
                self._stop_evt.clear()

    def _render_stop(self, stop_id: str):
        """Render a single stop's arrivals to the display"""
        if stop_id not in self.buffers:
            return

        buffers = self.buffers[stop_id]
        _, data = buffers.snapshot()
        stop_name = self.stop_names.get(stop_id, stop_id)

        print(f"Rendering {stop_id}: {stop_name}")

        # Clear canvas
        self.canvas.Fill(0, 0, 0)

        WIDTH = 64
        x_pos = 0

        for row_id in range(min(3, len(data))):
            row = data[row_id]
            route = row.get("route_id", "")
            txt = row.get("text", "")
            status = row.get("status", "")

            if not route:
                continue

            # Draw route circle
            draw_circle(self.canvas, 0, x_pos + 1, get_route_color(route))

            # Draw route letter
            graphics.DrawText(self.canvas, self.icon_font, 2, x_pos + 9, BLACK, route)

            # Choose text color (green for arriving now)
            text_color = WHITE
            if status.strip() == "0m":
                text_color = GREEN

            # Draw destination and time
            graphics.DrawText(self.canvas, self.icon_font, 13, x_pos + 9, text_color, txt)
            graphics.DrawText(self.canvas, self.icon_font, WIDTH + 7, x_pos + 9, text_color, status)

            x_pos += 10

        # Swap buffer to display
        self.canvas = self.matrix.SwapOnVSync(self.canvas)

    def _scroll_message(self, message: str, duration: float):
        """Scroll a message across the display for the specified duration"""
        print(f"Broadcasting message: {message}")

        # Get display dimensions
        width = self.matrix.width
        height = self.matrix.height

        # Calculate text width (approximate: 6 pixels per character)
        text_width = len(message) * 6

        # Starting position (off screen right)
        x_pos = width

        # Calculate scroll speed to complete in duration
        # Total distance = width + text_width (to scroll completely off left side)
        total_distance = width + text_width
        scroll_speed = total_distance / duration  # pixels per second
        frame_delay = 0.03  # ~33 FPS
        pixels_per_frame = scroll_speed * frame_delay

        # Vertical center
        y_pos = (height // 2) + 4  # Adjust for font baseline

        # Scroll color (bright yellow for visibility)
        text_color = graphics.Color(255, 200, 0)

        start_time = time.time()

        while self.running and (time.time() - start_time) < duration:
            # Clear canvas
            self.canvas.Fill(0, 0, 0)

            # Draw the scrolling text
            graphics.DrawText(self.canvas, self.broadcast_font, int(x_pos), y_pos, text_color, message)

            # Swap buffer
            self.canvas = self.matrix.SwapOnVSync(self.canvas)

            # Move text left
            x_pos -= pixels_per_frame

            # Small delay for smooth animation
            time.sleep(frame_delay)

        print("Broadcast complete")
