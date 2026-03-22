from __future__ import annotations

import platform
import sys
import threading
import time
from collections.abc import Callable


class KeyboardListener:
    """Sexy cross-platform keyboard listener with event callbacks"""

    def __init__(self):
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._callbacks: list[Callable[[str], None]] = []

    def add_callback(self, callback: Callable[[str], None]):
        """Add a callback function to be called on key press"""
        self._callbacks.append(callback)

    def start(self):
        """Start listening for keyboard input"""
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop listening for keyboard input"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)

    def _listen_loop(self):
        """Main listening loop with platform-specific implementations"""
        try:
            if platform.system() == "Windows":
                self._windows_listen()
            else:
                self._unix_listen()
        except Exception:
            pass  # Silently handle any listener errors

    def _windows_listen(self):
        import msvcrt

        while not self._stop_event.is_set():
            if msvcrt.kbhit():
                char = msvcrt.getch()
                # Ensure char is always a string
                if isinstance(char, bytes):
                    char = char.decode("utf-8", errors="ignore")
                safe_char = str(char)
                for callback in self._callbacks:
                    callback(safe_char)
            time.sleep(0.1)

    def _unix_listen(self):
        import select
        import termios  # type: ignore
        import tty  # type: ignore

        old_settings = termios.tcgetattr(sys.stdin)  # type: ignore
        try:
            tty.setraw(sys.stdin.fileno())  # type: ignore
            while not self._stop_event.is_set():
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    char = sys.stdin.read(1)
                    for callback in self._callbacks:
                        callback(char)
        finally:
            termios.tcsetattr(  # type: ignore
                sys.stdin,
                termios.TCSADRAIN,  # type: ignore
                old_settings,
            )
