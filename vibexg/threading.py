"""
Vibexg Threading — Centralized thread lifecycle management

Replaces ad-hoc daemon thread spawning with a ThreadManager that tracks
all background threads, enforces single-spawn guards, and provides clean
shutdown via stop_all().
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

logger = logging.getLogger(__name__)


class ThreadManager:
    """Centralized lifecycle for all background threads.

    Tracks threads by name, provides single-spawn guarantees, and
    enables clean coordinated shutdown.

    Usage:
        tm = ThreadManager()
        tm.start("activity_decay", target=self._decay_loop)
        tm.start("metronome", target=self._click_loop)
        ...
        tm.stop_all(timeout=2.0)
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._threads: dict[str, threading.Thread] = {}
        self._stop_events: dict[str, threading.Event] = {}

    def create_event(self, name: str) -> threading.Event:
        """Create or retrieve a named stop event.

        Args:
            name: Event name (typically matches the thread name)

        Returns:
            Existing or new threading.Event
        """
        with self._lock:
            if name not in self._stop_events:
                self._stop_events[name] = threading.Event()
            return self._stop_events[name]

    def start(
        self,
        name: str,
        target: Callable[[], None],
        daemon: bool = True,
    ) -> bool:
        """Start a named background thread.

        If a thread with this name is already running, it is NOT
        replaced (single-spawn guard that prevents thread leaks).

        Args:
            name: Unique thread name
            target: Callable to run in the thread
            daemon: Whether the thread should be a daemon thread

        Returns:
            True if thread was started, False if already running
        """
        with self._lock:
            existing = self._threads.get(name)
            if existing and existing.is_alive():
                logger.debug("Thread '%s' already running, skipping", name)
                return False

            # Ensure a stop event exists
            if name not in self._stop_events:
                self._stop_events[name] = threading.Event()

            thread = threading.Thread(target=target, name=name, daemon=daemon)
            thread.start()
            self._threads[name] = thread
            logger.debug("Thread '%s' started", name)
            return True

    def stop(self, name: str, timeout: float = 1.0) -> bool:
        """Signal a named thread to stop and wait for it.

        Args:
            name: Thread name to stop
            timeout: Maximum seconds to wait for the thread to finish

        Returns:
            True if the thread was stopped, False if not found
        """
        event = self._stop_events.get(name)
        if event:
            event.set()

        thread = self._threads.get(name)
        if thread and thread.is_alive():
            thread.join(timeout=timeout)
            return True
        return bool(name in self._threads)

    def stop_all(self, timeout: float = 2.0) -> None:
        """Signal all tracked threads to stop and wait for them.

        Sets all stop events and joins all threads with the given timeout.

        Args:
            timeout: Maximum seconds per thread to wait for it to finish
        """
        # Set all stop events first
        for event in self._stop_events.values():
            event.set()

        # Then join all threads
        for name, thread in list(self._threads.items()):
            if thread.is_alive():
                thread.join(timeout=timeout)
                logger.debug("Thread '%s' joined", name)

    def is_alive(self, name: str) -> bool:
        """Check if a named thread is currently running.

        Args:
            name: Thread name to check

        Returns:
            True if the thread exists and is alive
        """
        thread = self._threads.get(name)
        return thread is not None and thread.is_alive()

    @property
    def active_count(self) -> int:
        """Number of currently alive tracked threads."""
        return sum(1 for t in self._threads.values() if t.is_alive())
