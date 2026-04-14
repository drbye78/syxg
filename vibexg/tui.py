"""
Vibexg TUI - Text User Interface control surface

This module provides a Rich-based terminal user interface for the
workstation, displaying real-time status and providing visual feedback.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from .types import WorkstationState

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

logger = logging.getLogger(__name__)

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

        status = "● REC" if state.recording else "○ REC"
        status += "  |  ● PLAY" if state.playing else "  |  ○ PLAY"

        return Panel(
            Text(f"{title.plain}  |  {status}", justify="center"),
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
        keys = "[R]ecord  [P]lay  [S]top  [M]etronome  [+/-] Tempo  [V]olume  [D]emo  [Q]uit"
        return Panel(Text(keys, justify="center"), border_style="dim")

    def run(self):
        """Run the TUI main loop."""
        if not RICH_AVAILABLE:
            logger.warning("Rich not available - TUI disabled")
            return

        self.running = True
        try:
            with Live(self.render_layout(self.workstation.state), refresh_per_second=4) as live:
                while self.running:
                    time.sleep(0.25)
                    live.update(self.render_layout(self.workstation.state))
        except KeyboardInterrupt:
            pass
        self.running = False
