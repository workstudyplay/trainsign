#!/usr/bin/env python3
"""
Animation runner that executes animations using a shared matrix instance.
Animations are imported and run in-process to avoid port conflicts.
"""

import importlib.util
import os
import sys
import threading
import time
from typing import Optional, Callable


class AnimationRunner:
    """Runs animation scripts using a shared matrix instance"""

    def __init__(self, matrix, canvas):
        self.matrix = matrix
        self.canvas = canvas
        self.running = False
        self.current_animation: Optional[str] = None
        self._stop_evt = threading.Event()

    def run_animation(self, script_name: str, duration: float) -> bool:
        """
        Run an animation script for the specified duration.

        Args:
            script_name: Name of the script file (e.g., 'pong.py')
            duration: How long to run the animation in seconds

        Returns:
            True if animation ran successfully, False otherwise
        """
        animations_dir = os.path.join(os.path.dirname(__file__), 'animations')
        script_path = os.path.join(animations_dir, script_name)

        if not os.path.exists(script_path):
            print(f"Animation not found: {script_path}")
            return False

        self.current_animation = script_name
        self._stop_evt.clear()

        try:
            # Load the animation module
            spec = importlib.util.spec_from_file_location(
                script_name.replace('.py', ''),
                script_path
            )
            if spec is None or spec.loader is None:
                print(f"Failed to load animation spec: {script_name}")
                return False

            module = importlib.util.module_from_spec(spec)

            # Inject our matrix/canvas into the module's namespace
            # This allows animations to use our shared instance
            module.__dict__['_shared_matrix'] = self.matrix
            module.__dict__['_shared_canvas'] = self.canvas

            # Execute the module
            spec.loader.exec_module(module)

            # Look for a run function that accepts matrix/canvas
            if hasattr(module, 'run_with_matrix'):
                # Preferred: animation has a function that accepts matrix/canvas
                self._run_with_timeout(
                    lambda: module.run_with_matrix(self.matrix, self.canvas, self._stop_evt),
                    duration
                )
            elif hasattr(module, 'Game') or hasattr(module, 'Animation'):
                # Animation has a Game/Animation class
                game_class = getattr(module, 'Game', None) or getattr(module, 'Animation', None)
                if game_class:
                    self._run_game_class(game_class, duration)
            else:
                # Fallback: just sleep for duration (animation runs in module load)
                print(f"Animation {script_name} has no run_with_matrix function")
                time.sleep(duration)

            return True

        except Exception as e:
            print(f"Error running animation {script_name}: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.current_animation = None

    def _run_with_timeout(self, func: Callable, duration: float):
        """Run a function with a timeout"""
        start_time = time.time()

        # Run in a thread so we can interrupt it
        thread = threading.Thread(target=func, daemon=True)
        thread.start()

        # Wait for duration or stop event
        while thread.is_alive() and (time.time() - start_time) < duration:
            if self._stop_evt.wait(0.1):
                break

        self._stop_evt.set()  # Signal animation to stop
        thread.join(timeout=2)

    def _run_game_class(self, game_class, duration: float):
        """Run a game class that follows a standard pattern"""
        try:
            # Try to instantiate with matrix dimensions
            game = game_class(self.matrix.width, self.matrix.height)

            start_time = time.time()
            target_dt = 1.0 / 60  # 60 FPS

            while (time.time() - start_time) < duration and not self._stop_evt.is_set():
                t0 = time.time()

                # Update game state
                if hasattr(game, 'update'):
                    game.update(target_dt)
                elif hasattr(game, 'step'):
                    game.step(target_dt)

                # Render
                if hasattr(game, 'render'):
                    game.render(self.canvas)
                elif hasattr(game, 'draw'):
                    game.draw(self.canvas)

                # Swap buffers
                self.canvas = self.matrix.SwapOnVSync(self.canvas)

                # Frame timing
                elapsed = time.time() - t0
                if elapsed < target_dt:
                    time.sleep(target_dt - elapsed)

        except Exception as e:
            print(f"Error running game class: {e}")
            import traceback
            traceback.print_exc()

    def stop(self):
        """Stop the currently running animation"""
        self._stop_evt.set()
