"""

Vibexg TUI - Text User Interface control surface

This module provides a Rich-based terminal user interface for the
workstation, displaying real-time status and providing visual feedback.
"""

from __future__ import annotations

import logging
import shutil
import signal
import threading
from typing import TYPE_CHECKING

from .types import WorkstationState

logger = logging.getLogger(__name__)

# Conditional imports for Rich
try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None
    Panel = None
    Table = None
    Live = None
    Layout = None
    Text = None


def _is_wsl2() -> bool:
    """Detect if running under WSL2 (Windows Subsystem for Linux)."""
    try:
        with open("/proc/sys/kernel/osrelease") as f:
            content = f.read().lower()
            return "microsoft" in content or "wsl" in content
    except FileNotFoundError:
        return False


# Import MIDI channel count
MIDI_CHANNELS = 16

# Forward reference to avoid circular import
if TYPE_CHECKING:
    from .workstation import XGWorkstation


class TUIControlSurface:
    """
    Rich-based TUI control surface for the workstation.

    Provides a real-time visual display of workstation status including:
    - MIDI channel activity
    - Voice count and CPU usage
    - Recording/playback status
    - Tempo and volume settings
    """

    def __init__(self, workstation: XGWorkstation):
        """
        Initialize the TUI control surface.

        Args:
            workstation: XGWorkstation instance to display
        """
        self.workstation = workstation
        self.console = Console() if Console else None
        self.running = False
        self._wsl2 = _is_wsl2()
        self._live: Live | None = None
        self._last_state_repr: str = ""
        self._min_term_height = 20
        self._refresh_event = threading.Event()
        self._resize_requested = False
        self._ticks = 0

    def _check_terminal_size(self) -> bool:
        """Check if terminal is large enough for the TUI.

        Returns True if terminal is large enough, False otherwise.
        """
        size = shutil.get_terminal_size((80, 24))
        if size.lines < self._min_term_height:
            logger.warning(
                "Terminal too small for TUI (%d lines, need %d). " "Resize or reduce font size.",
                size.lines,
                self._min_term_height,
            )
            return False
        return True

    def render_layout(self, state: WorkstationState):
        """
        Create the main layout.

        Args:
            state: Current workstation state to display

        Returns:
            Rich Layout object or None if Rich not available
        """
        if not RICH_AVAILABLE or not Layout:
            return None
        layout = Layout()

        layout.split(
            Layout(name="header", size=3), Layout(name="body"), Layout(name="footer", size=3)
        )

        # Header
        layout["header"].update(self._render_header(state))

        # Body - split into channels and controls
        body = layout["body"]
        body.split(Layout(name="channels"), Layout(name="controls", ratio=2))

        layout["body"]["channels"].update(self._render_channels(state))
        layout["body"]["controls"].update(self._render_controls(state))

        # Footer
        layout["footer"].update(self._render_footer(state))

        return layout

    def _render_header(self, state: WorkstationState):
        """
        Render header panel.

        Args:
            state: Current workstation state

        Returns:
            Rich Panel object or None if Rich not available
        """
        if not RICH_AVAILABLE or not Panel or not Text:
            return None
        title = Text()
        title.append("XG Workstation", style="bold cyan")
        title.append(f"  |  Preset: {state.current_preset}", style="white")
        title.append(f"  |  Tempo: {state.tempo:.1f} BPM", style="yellow")

        status = Text()
        if state.recording:
            status.append("  |  ● REC", style="bold red")
        else:
            status.append("  |  ○ REC", style="dim")
        if state.playing:
            status.append("  |  ● PLAY", style="bold green")
        else:
            status.append("  |  ○ PLAY", style="dim")

        header_text = Text(justify="center")
        header_text.append(title)
        header_text.append(status)

        return Panel(
            header_text,
            title="XG SYNTHESIZER WORKSTATION",
            border_style="cyan",
        )

    def _render_channels(self, state: WorkstationState):
        """
        Render channel activity panel.

        Args:
            state: Current workstation state

        Returns:
            Rich Panel object or None if Rich not available
        """
        if not RICH_AVAILABLE or not Table or not Panel:
            return None
        table = Table(title="MIDI Channels", show_header=True, header_style="bold magenta")
        table.add_column("Ch", style="cyan", width=4)
        table.add_column("Activity", style="white")
        table.add_column("Level", justify="right")

        for ch in range(MIDI_CHANNELS):
            activity = state.midi_activity.get(ch, 0)
            level = min(20, activity // 5)
            bar = "█" * level + "░" * (20 - level)
            table.add_row(str(ch + 1), bar, str(activity))

        return Panel(table, border_style="blue")

    def _render_controls(self, state: WorkstationState):
        """
        Render main controls panel.

        Args:
            state: Current workstation state

        Returns:
            Rich Panel object or None if Rich not available
        """
        if not RICH_AVAILABLE or not Table or not Panel:
            return None
        table = Table(title="System Status", show_header=False)
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Voices Active", str(state.voices_active))
        table.add_row("CPU Usage", f"{state.cpu_usage:.1f}%")
        table.add_row("Master Volume", f"{state.master_volume * 100:.0f}%")
        table.add_row("Recording", "Yes" if state.recording else "No")
        table.add_row("Metronome", "On" if state.metronome else "Off")

        return Panel(table, border_style="green")

    def _render_footer(self, state: WorkstationState):
        """
        Render footer with key bindings.

        Args:
            state: Current workstation state (unused)

        Returns:
            Rich Panel object or None if Rich not available
        """
        if not RICH_AVAILABLE or not Panel or not Text:
            return None
        keys = (
            "^R=Rec  ^P=Play  ^S=Stop  ^M=Metro  [+/-]Tempo  [v/V]Vol  ^D=Demo  ^E=Export  ^Q=Quit"
        )
        return Panel(Text(keys, justify="center"), border_style="dim")

    def run(self) -> None:
        """Run the TUI main loop."""
        if not RICH_AVAILABLE:
            logger.warning("Rich not available - TUI disabled")
            return

        if not self._check_terminal_size():
            logger.warning("TUI disabled due to small terminal")
            return

        self.running = True
        self._resize_requested = False
        self._refresh_event.clear()

        refresh_rate = 4  # same rate everywhere; modern terminals handle it

        try:
            with Live(
                self.render_layout(self.workstation.state),
                refresh_per_second=refresh_rate,
                screen=True,
                transient=True,
            ) as live:
                self._live = live
                self._setup_resize_handler()

                while self.running and self.workstation.state.running:
                    # Wait for either a refresh request or the poll interval
                    self._refresh_event.wait(timeout=0.2)
                    self._refresh_event.clear()

                    # Periodic terminal size audit (every ~2s at 0.2s timeout)
                    self._ticks += 1
                    if self._ticks % 10 == 0:
                        size = shutil.get_terminal_size((80, 24))
                        if size.lines < self._min_term_height:
                            logger.warning(
                                "Terminal too small for TUI (%d < %d lines) — disabling TUI",
                                size.lines,
                                self._min_term_height,
                            )
                            break

                    state = self.workstation.state

                    # Check for resize — re-render layout on terminal size change
                    if self._resize_requested:
                        self._resize_requested = False
                        size = shutil.get_terminal_size((80, 24))
                        if size.lines < self._min_term_height:
                            logger.warning("Terminal too small for TUI")
                        # Force a re-render by updating last_state_repr
                        self._last_state_repr = ""

                    state_repr = self._state_repr(state)
                    if state_repr != self._last_state_repr:
                        self._last_state_repr = state_repr
                        live.update(self.render_layout(state))

        except KeyboardInterrupt:
            pass
        finally:
            self._live = None
            self.running = False

    def _state_repr(self, state: WorkstationState) -> str:
        """Create a string representation of state for change detection.

        Args:
            state: Current workstation state

        Returns:
            String hash of state values
        """
        # Only include midi_activity if there's actual activity
        # (avoids re-renders from decay thread when all channels are silent)
        activity = ""
        for ch in range(16):
            val = state.midi_activity.get(ch, 0)
            if val > 0:
                activity = f"{state.midi_activity}"
                break

        return (
            f"{state.recording}{state.playing}{state.metronome}"
            f"{state.voices_active}{state.cpu_usage:.1f}"
            f"{state.master_volume:.2f}{state.tempo:.1f}"
            f"{state.current_preset}{activity}"
        )

    def force_refresh(self) -> None:
        """Request a TUI refresh on the next main-loop cycle (called from any thread)."""
        if self._refresh_event is not None:
            self._refresh_event.set()

    def _setup_resize_handler(self) -> None:
        """Handle terminal resize events."""

        def _on_resize(signum, frame):
            # Signal handler — just set flag, defer all work to main loop
            self._resize_requested = True
            if self._refresh_event is not None:
                self._refresh_event.set()

        signal.signal(signal.SIGWINCH, _on_resize)
