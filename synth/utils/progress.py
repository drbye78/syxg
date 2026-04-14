from __future__ import annotations

import time


class ProgressReporter:
    """Elegant progress reporting with timing and formatting"""

    def __init__(self, silent: bool = False):
        self.silent = silent
        self.start_time: float | None = None
        self.total: float = 0
        self.processed: float = 0

    def start(self, total: float):
        """Begin tracking progress"""
        if self.silent:
            return
        self.start_time = time.time()
        self.total = total
        self.processed = 0

    def update(self, increment: float = 1):
        """Update progress"""
        if self.silent or not self.start_time:
            return
        self.processed += increment
        self._display()

    def progress(self, processed: float):
        if self.silent or not self.start_time:
            return
        self.processed = processed
        self._display()

    def _display(self):
        """Display current progress"""
        if self.start_time is None:
            return

        elapsed = time.time() - self.start_time
        percent = min(100.0, (self.processed / self.total) * 100) if self.total > 0 else 0

        # Calculate ETA if possible
        if self.processed > 0 and elapsed > 0:
            eta = (self.total - self.processed) * elapsed / self.processed
        else:
            eta = 0

        # Format times
        processed_str = self._format_time(self.processed)
        total_str = self._format_time(self.total)
        elapsed_str = self._format_time(elapsed)
        eta_str = self._format_time(eta)

        # Print progress
        print(
            f"\rProgress: {percent:5.1f}% | {processed_str}/{total_str} | "
            f"Elapsed: {elapsed_str} | ETA: {eta_str}",
            end="",
            flush=True,
        )

    def _format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS"""
        return f"{int(seconds // 60):02d}:{int(seconds % 60):02d}"
