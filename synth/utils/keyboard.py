from __future__ import annotations

import platform
import sys
import threading
import time
from collections.abc import Callable


class KeyboardListener:
    """Cross-platform keyboard listener with separate MIDI and command callbacks."""

    def __init__(self):
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._press_callbacks: list[Callable[[str], None]] = []
        self._release_callbacks: list[Callable[[str], None]] = []
        self._command_callback: Callable[[str], None] | None = None

    def add_callback(
        self,
        press: Callable[[str], None],
        release: Callable[[str], None] | None = None,
    ):
        self._press_callbacks.append(press)
        if release:
            self._release_callbacks.append(release)

    def set_command_callback(self, callback: Callable[[str], None]):
        self._command_callback = callback

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
        try:
            if platform.system() == "Windows":
                self._windows_listen()
            else:
                self._unix_listen()
        except Exception:
            pass

    def _dispatch_press(self, char: str):
        """Route Ctrl+letter to command callback, regular keys to press callbacks.

        - Ctrl+letter (ASCII 1-26) → command callback only (decoded to letter)
        - Letter keys (a-z, A-Z) → press callbacks only (MIDI notes)
        - Non-letter keys (+, -, etc.) → both press callbacks and command callback
        """
        code = ord(char) if len(char) == 1 else 0
        if 1 <= code <= 26:  # Ctrl+A through Ctrl+Z (ASCII 1-26)
            # Convert Ctrl+letter back to the letter for command dispatch
            letter = chr(code + 96)
            if self._command_callback:
                self._command_callback(letter)
        else:
            # Send to press callbacks (MIDI notes)
            for cb in self._press_callbacks:
                cb(char)
            # Non-letter keys go to command callback too (+, -, etc.)
            if self._command_callback and not char.isalpha():
                self._command_callback(char)

    def _dispatch_release(self, char: str):
        for cb in self._release_callbacks:
            cb(char)

    def _windows_listen(self):
        import msvcrt

        while not self._stop_event.is_set():
            if msvcrt.kbhit():
                char = msvcrt.getch()
                if isinstance(char, bytes):
                    char = char.decode("utf-8", errors="ignore")
                safe_char = str(char)
                self._dispatch_press(safe_char)
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
                    self._dispatch_press(char)
        finally:
            termios.tcsetattr(  # type: ignore
                sys.stdin,
                termios.TCSADRAIN,  # type: ignore
                old_settings,
            )
