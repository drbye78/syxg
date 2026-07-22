"""

Vibexg Textual TUI - Modern flicker-free terminal interface

Replaces the Rich-based ``tui.py`` with a Textual application that provides
reactive partial rendering (zero flicker) and built-in keyboard handling.

Textual handles all terminal I/O internally — no tty.setraw() conflict, no
manual SIGWINCH handling, no polling loops.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.reactive import reactive
from textual.widgets import Footer, Static

from synth.io.midi import MIDIMessage

if TYPE_CHECKING:
    from .workstation import XGWorkstation

logger = logging.getLogger(__name__)

# 16 MIDI channels
MIDI_CHANNELS = 16


class ChannelBar(Static):
    """A single MIDI channel activity bar with level indicator."""

    channel: reactive[int] = reactive(0)  # type: ignore[assignment]
    activity: reactive[int] = reactive(0)  # type: ignore[assignment]

    def render(self) -> str:
        level = min(20, self.activity // 5) if self.activity else 0
        bar = "█" * level + "░" * (20 - level)
        return f"  [cyan]Ch {self.channel:>2d}[/] {bar} [white]{self.activity}[/]"


class StatusPanel(Static):
    """System status panel — voices, CPU, volume, recording, transport."""

    voices: reactive[int] = reactive(0)  # type: ignore[assignment]
    cpu: reactive[float] = reactive(0.0)  # type: ignore[assignment]
    volume: reactive[float] = reactive(0.0)  # type: ignore[assignment]
    recording: reactive[bool] = reactive(False)  # type: ignore[assignment]
    playing: reactive[bool] = reactive(False)  # type: ignore[assignment]
    metronome: reactive[bool] = reactive(False)  # type: ignore[assignment]
    tempo: reactive[float] = reactive(120.0)  # type: ignore[assignment]
    preset: reactive[str] = reactive("Init")  # type: ignore[assignment]

    def render(self) -> str:
        rec = "[red]● REC[/]" if self.recording else "[dim]○ REC[/]"
        play = "[green]● PLAY[/]" if self.playing else "[dim]○ PLAY[/]"
        metro = "[yellow]●[/]" if self.metronome else "[dim]○[/]"
        lines = [
            "[bold cyan]XG Workstation[/]",
            "",
            f"  Preset:       [white]{self.preset}[/]",
            f"  Tempo:        [yellow]{self.tempo:.1f} BPM[/]",
            f"  Voices:       {self.voices}",
            f"  CPU:          {self.cpu:.1f}%",
            f"  Volume:       {self.volume * 100:.0f}%",
            "",
            f"  {rec}   {play}   Metro: {metro}",
        ]
        return "\n".join(lines)


class XGSynthApp(App):
    """Textual-based TUI for the XG Workstation synthesizer.

    Provides a flicker-free real-time display of MIDI channel activity,
    system status, and keyboard-controlled transport commands.
    """

    CSS = """
    Screen {
        background: $surface;
    }

    #content {
        height: 1fr;
    }

    #channels-panel {
        width: 40%;
        border: solid $primary;
        overflow-y: auto;
    }

    #channels-title {
        padding: 0 1;
        text-style: bold;
        color: $text;
    }

    #controls-panel {
        width: 60%;
        border: solid $secondary;
        padding: 0 1;
    }

    #status-title {
        padding: 0 1;
        text-style: bold;
        color: $text;
    }

    ChannelBar {
        height: 1;
        padding: 0 1;
    }

    StatusPanel {
        height: auto;
        margin: 0 1;
    }

    Footer {
        background: $panel;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("ctrl+r", "toggle_recording", "Rec"),
        Binding("ctrl+p", "toggle_playback", "Play"),
        Binding("ctrl+s", "stop", "Stop"),
        Binding("ctrl+m", "toggle_metronome", "Metro"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+d", "demo", "Demo"),
        Binding("ctrl+e", "export", "Export"),
        Binding("ctrl+v", "volume_down", "Vol-"),
        Binding("ctrl+u", "volume_up", "Vol+"),
    ]

    def __init__(self, workstation: XGWorkstation) -> None:
        super().__init__()
        self.workstation = workstation
        self._channel_bars: list[ChannelBar] = []
        self._key_map = self._create_key_map()
        self._held_notes: dict[str, float] = {}

    # ------------------------------------------------------------------
    # MIDI key mapping (mirrors KeyboardInput in midi_inputs.py)
    # ------------------------------------------------------------------

    @staticmethod
    def _create_key_map() -> dict[str, int]:
        """Create keyboard-to-MIDI-note mapping.

        White keys (bottom row): ``zsxdcvgbhnjm,l.;/'`` -> C3-C5
        Black keys (top row):    ``edcftgyhujko``       -> C#3-A#4
        """
        white_keys = "zsxdcvgbhnjm,l.;/'"
        black_keys = "edcftgyhujko"
        note_map: dict[str, int] = {}
        notes_white = [60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79, 81, 83, 84]
        for i, key in enumerate(white_keys[: len(notes_white)]):
            note_map[key] = notes_white[i]
        notes_black = [61, 63, 66, 68, 70, 73, 75, 78, 80, 82]
        for i, key in enumerate(black_keys[: len(notes_black)]):
            note_map[key] = notes_black[i]
        return note_map

    # ------------------------------------------------------------------
    # App lifecycle
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        logger.debug("XGSynthApp: compose() called")
        self._channel_bars = [ChannelBar() for _ in range(MIDI_CHANNELS)]
        for i, bar in enumerate(self._channel_bars):
            bar.channel = i + 1

        status = StatusPanel()

        with Horizontal(id="content"):
            with Vertical(id="channels-panel"):
                yield Static("[bold magenta]MIDI Channels[/]", id="channels-title")
                for bar in self._channel_bars:
                    yield bar
            with Vertical(id="controls-panel"):
                yield Static("[bold green]System Status[/]", id="status-title")
                yield status

        yield Footer()
        logger.debug("XGSynthApp: compose() done")

    def on_mount(self) -> None:
        """Start state polling once the app is mounted."""
        logger.debug("XGSynthApp: on_mount() called")
        self.set_interval(0.2, self._poll_state)
        self._poll_state()
        logger.debug("XGSynthApp: on_mount() done")

    def _poll_state(self) -> None:
        """Poll ``workstation.state`` and update reactive attributes.

        Textual's reactive system automatically re-renders only the widgets
        whose watched values changed — no full-screen redraw.
        """
        state = self.workstation.state
        if not state:
            return

        # Update channel bars
        for i, bar in enumerate(self._channel_bars):
            bar.activity = state.midi_activity.get(i, 0)

        # Update status panel
        status = self.query_one(StatusPanel)
        status.voices = state.voices_active
        status.cpu = state.cpu_usage
        status.volume = state.master_volume
        status.recording = state.recording
        status.playing = state.playing
        status.metronome = state.metronome
        status.tempo = state.tempo
        status.preset = state.current_preset

    # ------------------------------------------------------------------
    # Actions (called by BINDINGS)
    # ------------------------------------------------------------------

    def _force_update(self) -> None:
        """Immediately poll state after a user action (no 200ms delay)."""
        self._poll_state()

    def action_toggle_recording(self) -> None:
        self.workstation.toggle_recording()
        self._force_update()

    def action_toggle_playback(self) -> None:
        self.workstation.toggle_playback()
        self._force_update()

    def action_stop(self) -> None:
        self.workstation.recorder.stop_playback()
        self.workstation.metronome.stop()
        self.workstation.state.metronome = False
        self._force_update()

    def action_toggle_metronome(self) -> None:
        self.workstation.toggle_metronome()
        self._force_update()

    def action_demo(self) -> None:
        self.workstation.run_demo("scale")

    def action_export(self) -> None:
        self.workstation.export_midi()

    def action_volume_down(self) -> None:
        self.workstation.change_volume(-0.1)
        self._force_update()

    def action_volume_up(self) -> None:
        self.workstation.change_volume(0.1)
        self._force_update()

    # ------------------------------------------------------------------
    # Key events: MIDI notes and tempo changes
    # ------------------------------------------------------------------

    def on_key(self, event: Key) -> None:
        """Handle non-binding key events (MIDI notes, tempo +/-).

        Ctrl+letter and Ctrl+key combos are handled by :attr:`BINDINGS`.
        All other keys come through here.
        """
        key = event.key

        # Modifier keys are handled by BINDINGS — never dispatch as MIDI
        if key.startswith("ctrl+") or key.startswith("alt+"):
            return

        # +/- for tempo
        if key in ("+", "plus"):
            self.workstation.change_tempo(5)
            return
        if key in ("-", "minus"):
            self.workstation.change_tempo(-5)
            return

        # Single letter keys → MIDI notes (PC keyboard as controller)
        if len(key) == 1 and key.isalpha():
            k = key.lower()
            if k in self._key_map:
                note = self._key_map[k]
                msg = MIDIMessage(
                    type="note_on",
                    channel=0,
                    data={"note": note, "velocity": 80},
                    timestamp=time.time(),
                )
                self.workstation.send(msg)
