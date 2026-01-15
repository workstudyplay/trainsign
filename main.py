#!/usr/bin/env python3
"""
main_controller.py

Cycles between these scripts for 10 seconds each:
  - games/pong.py
  - games/mario.py
  - games/invaders.py
  - transit/panel.py

Notes:
- Runs each as a subprocess and terminates it after the time slice.
- Works for emulator or hardware, as long as each script can run standalone.
- If a script exits early, controller moves to the next one.

Usage:
  python3 main.py
  python3 main.py --seconds 10 --order games/pong.py games/mario.py transit/panel.py
"""

import argparse
import os
import signal
import subprocess
import sys
import time
from typing import List


def _terminate_process(proc: subprocess.Popen, grace: float = 1.0) -> None:
    """Try graceful termination, then force kill."""
    if proc.poll() is not None:
        return

    try:
        # Send SIGINT first (lets scripts clean up like KeyboardInterrupt)
        proc.send_signal(signal.SIGINT)
    except Exception:
        pass

    deadline = time.time() + grace
    while time.time() < deadline:
        if proc.poll() is not None:
            return
        time.sleep(0.02)

    if proc.poll() is not None:
        return

    try:
        proc.terminate()
    except Exception:
        pass

    deadline = time.time() + grace
    while time.time() < deadline:
        if proc.poll() is not None:
            return
        time.sleep(0.02)

    if proc.poll() is not None:
        return

    try:
        proc.kill()
    except Exception:
        pass


def run_script_for(script_path: str, seconds: float, extra_args: List[str]) -> None:
    script_path = os.path.abspath(script_path)

    if not os.path.exists(script_path):
        print(f"[controller] missing: {script_path}", file=sys.stderr)
        return

    cmd = [sys.executable, script_path, *extra_args]
    print(f"[controller] running {os.path.basename(script_path)} for {seconds:.1f}s: {' '.join(cmd)}")

    # Put each child in its own process group, so we can stop it reliably.
    # POSIX: start_new_session=True -> new session/process group.
    # Windows: start_new_session also works in py>=3.7 (creates new process group semantics).
    proc = subprocess.Popen(
        cmd,
        stdout=sys.stdout,
        stderr=sys.stderr,
        start_new_session=True,
    )

    t_end = time.time() + seconds
    try:
        while time.time() < t_end:
            if proc.poll() is not None:
                break
            time.sleep(0.05)
    finally:
        _terminate_process(proc)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=10.0, help="Seconds to run each script")
    parser.add_argument(
        "--order",
        nargs="*",
        default=["games/pong.py", "games/invaders.py", "transit/panel.py", "animations/chicken.py"],
        help="Script filenames in the cycle order (relative to src/)",
    )
    parser.add_argument(
        "--pass-args",
        nargs=argparse.REMAINDER,
        default=[],
        help="Args passed to each child script after '--pass-args' (e.g. --pass-args --width 128 --height 32)",
    )
    parser.add_argument("--loop", default=True, action="store_true", help="Loop forever (default runs one full cycle)")
    args = parser.parse_args()

    scripts = args.order
    per = max(0.5, float(args.seconds))
    child_args = args.pass_args

    # Resolve scripts relative to src/ directory (where main.py is located)
    src_dir = os.path.dirname(os.path.abspath(__file__))
    scripts = [os.path.join(src_dir, s) if not os.path.isabs(s) else s for s in scripts]
    if True:
        "transit/panel.py"
        
    while True:
        for s in scripts:
            run_script_for(s, per, child_args)
        if not args.loop:
            break

    print("[controller] done")

if __name__ == "__main__":
    main()
