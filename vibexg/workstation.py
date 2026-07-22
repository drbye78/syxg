"""
Vibexg Workstation - Main XG Synthesizer Workstation orchestration

Provides the XGWorkstation class, which coordinates MIDI inputs, audio
outputs, recording, playback, metronome, demo mode, presets, MIDI Learn,
and the optional TUI. Implements MidiMessageSink for typed MIDI routing.
"""

from __future__ import annotations

import logging
import os
import queue
import sys
import threading
import time
from pathlib import Path
from typing import Any

from synth.io.midi import MIDIMessage
from synth.primitives.config_manager import ConfigManager
from synth.synthesizers.realtime import Synthesizer

from .audio_outputs import AudioOutputEngine, FileAudioOutput, SoundDeviceOutput
from .config import WorkstationConfig
from .demo import DemoMode
from .managers import MIDILearnManager, PresetManager, StyleEngineIntegration
from .metronome import Metronome
from .midi_inputs import (
    FileMIDIInput,
    KeyboardInput,
    MIDIInputInterface,
    MidoPortInput,
    NetworkMIDIInput,
    StdinMIDIInput,
    VirtualPortInput,
)
from .recorder import Recorder
from .threading import ThreadManager
from .tui import TUIControlSurface
from .types import (
    AudioOutputType,
    InputInterfaceType,
    MIDIInputConfig,
    PresetData,
    WorkstationState,
)
from .utils import midimessage_to_bytes

logger = logging.getLogger(__name__)

try:
    RICH_AVAILABLE = True
    from rich.console import Console  # noqa: F401
except ImportError:
    RICH_AVAILABLE = False

try:
    from .tui_textual import XGSynthApp

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    XGSynthApp = None  # type: ignore[assignment]


class XGWorkstation:
    """
    XG Synthesizer Workstation - Main orchestration class.

    Implements MidiMessageSink to receive MIDI messages from all input
    interfaces and route them to the synthesizer, MIDI Learn, recorder,
    and voice tracking subsystems.

    Uses Recorder, Metronome, ThreadManager, and typed config for
    clean separation of concerns.
    """

    def __init__(
        self,
        config: WorkstationConfig | dict[str, Any] | None = None,
        synthesizer: Synthesizer | None = None,
    ) -> None:
        """
        Initialize the workstation.

        Args:
            config: WorkstationConfig or raw dict (backward compat)
            synthesizer: Optional injected Synthesizer (for testing)
        """
        # Normalize config
        if isinstance(config, WorkstationConfig):
            self.cfg = config
        elif isinstance(config, dict):
            self.cfg = WorkstationConfig.from_dict(config)
        else:
            self.cfg = WorkstationConfig()

        self.state = WorkstationState()

        # Synthesizer (injectable for testing)
        if synthesizer is not None:
            self.synthesizer = synthesizer
        else:
            self.synthesizer = Synthesizer(
                sample_rate=self.cfg.sample_rate,
                buffer_size=self.cfg.buffer_size,
                enable_audio_output=False,
                xg_enabled=self.cfg.xg_enabled,
                gs_enabled=self.cfg.gs_enabled,
                mpe_enabled=self.cfg.mpe_enabled,
                midi_2_enabled=self.cfg.midi_2_enabled,
                acoustic_behavior=self.cfg.acoustic_behavior,
                s90_mode=self.cfg.s90_mode,
                gs_mode=self.cfg.gs_mode,
                effects_enabled=self.cfg.effects_enabled,
                sart2_enabled=self.cfg.sart2_enabled,
                reverb_enabled=self.cfg.reverb_enabled,
                chorus_enabled=self.cfg.chorus_enabled,
                variation_enabled=self.cfg.variation_enabled,
                insertion_enabled=self.cfg.insertion_enabled,
                master_eq_enabled=self.cfg.master_eq_enabled,
            )

        # Load SoundFont into the SF2 engine
        sf2_path = self.cfg.soundfont
        if sf2_path and os.path.exists(sf2_path):
            self.synthesizer.load_soundfont(sf2_path)
            logger.info("Loaded SoundFont: %s", sf2_path)
        elif sf2_path:
            logger.warning("SoundFont not found: %s (SF2 engine will produce silence)", sf2_path)

        # Thread lifecycle management
        self._thread_manager = ThreadManager()
        self._stop_event = self._thread_manager.create_event("activity_decay")

        # Subsystems (extracted for separation of concerns)
        self.recorder = Recorder(self, self._thread_manager)
        self.metronome = Metronome(self, self._thread_manager)

        # MIDI routing
        self.midi_inputs: dict[str, MIDIInputInterface] = {}
        self.midi_queue: queue.Queue = queue.Queue()
        self.midi_learn = MIDILearnManager(self.synthesizer)

        # Audio outputs
        self.audio_outputs: dict[str, AudioOutputEngine] = {}

        # Presets and styles
        self.preset_manager = PresetManager(self.cfg.preset_dir)
        self.style_engine = StyleEngineIntegration(self.synthesizer)

        # Demo
        self.demo_mode = DemoMode(self.synthesizer)

        # TUI
        self.tui: TUIControlSurface | None = None

        # Backward compat: recording fields kept for any external references
        self.recorded_events: list[dict[str, Any]] = []
        self.recording_start_time: float = 0
        self._recording_lock: threading.Lock = threading.Lock()

        self.last_perf_update = time.time()
        self.voice_count_samples = 0

        self._initialize_components()

    # =========================================================================
    # MidiMessageSink protocol implementation
    # =========================================================================

    def send(self, message: MIDIMessage) -> None:
        """
        Process an incoming MIDI message (MidiMessageSink protocol).

        Routes the message through:
          1. MIDI activity tracking
          2. MIDI Learn (for control_change messages)
          3. Synthesizer MIDI parser
          4. Voice counting (note_on/note_off)
          5. Recording (if active)

        Args:
            message: The MIDI message to process
        """
        if message.channel is not None:
            self.state.increment_midi_activity(message.channel)

        # MIDI Learn: route CC to mapped parameters
        if message.type == "control_change":
            cc = message.data.get("controller", 0)
            value = message.data.get("value", 0)
            self.midi_learn.process_cc(cc, value, message.channel or 0)

        # Send to synthesizer MIDI parser
        self._send_to_synthesizer(message)

        # Track active voices
        match message.type:
            case "note_on":
                velocity = message.data.get("velocity", 64)
                if velocity > 0:
                    self.state.adjust_voices_active(1)
            case "note_off":
                self.state.adjust_voices_active(-1)

        # Record event if recording is active
        self.recorder.record_event(message)

    # =========================================================================
    # Backward compat wrapper
    # =========================================================================

    def _handle_midi_message(self, message: MIDIMessage, record: bool = True) -> None:
        """
        Legacy MIDI handler. Forwards to send().

        Args:
            message: MIDI message to process
            record: Ignored (recording decision is internal to recorder)
        """
        self.send(message)

    # =========================================================================
    # Initialization
    # =========================================================================

    def _initialize_components(self) -> None:
        """Initialize all workstation components."""
        self._load_configuration()
        self._setup_midi_inputs()
        self._setup_audio_outputs()
        self._initialize_style_engine()

        if TEXTUAL_AVAILABLE:
            self.tui = XGSynthApp(self)
        elif RICH_AVAILABLE:
            self.tui = TUIControlSurface(self)
        else:
            self.tui = None

        logger.info("Workstation initialized")

    def _load_configuration(self) -> None:
        """Load configuration from YAML file (tempo, volume overrides)."""
        config_path = self.cfg.config_file
        if not os.path.exists(config_path):
            return
        try:
            config_manager = ConfigManager(config_path)
            config_manager.load()
            self.state.tempo = (
                config_manager.get_tempo() if hasattr(config_manager, "get_tempo") else 120.0
            )
            self.state.master_volume = (
                config_manager.get_volume() if hasattr(config_manager, "get_volume") else 0.8
            )
            logger.info("Configuration loaded from %s", config_path)
        except Exception as e:
            logger.warning("Failed to load configuration: %s", e)

    def _setup_midi_inputs(self) -> None:
        """Setup MIDI input interfaces from configuration.

        Uses self (MidiMessageSink) as the message target.
        """
        for input_cfg in self.cfg.midi_inputs:
            interface = self._create_midi_interface(input_cfg)
            if interface:
                key = input_cfg.name or input_cfg.interface_type.value
                self.midi_inputs[key] = interface

        # Default keyboard input if nothing configured
        # (skipped when Textual TUI is available — it handles keyboard natively)
        if not self.midi_inputs and not TEXTUAL_AVAILABLE:
            default_cfg = MIDIInputConfig(
                interface_type=InputInterfaceType.KEYBOARD,
                name="keyboard",
            )
            self.midi_inputs["keyboard"] = KeyboardInput(default_cfg, self, self._handle_command)

    def _create_midi_interface(self, config: MIDIInputConfig) -> MIDIInputInterface | None:
        """Create MIDI input interface based on configuration.

        Args:
            config: MIDI input configuration

        Returns:
            MIDIInputInterface instance or None if unknown type
        """
        match config.interface_type:
            case InputInterfaceType.MIDO_PORT:
                return MidoPortInput(config, self)
            case InputInterfaceType.VIRTUAL_PORT:
                return VirtualPortInput(config, self)
            case InputInterfaceType.NETWORK_MIDI:
                return NetworkMIDIInput(config, self)
            case InputInterfaceType.KEYBOARD:
                return KeyboardInput(config, self, self._handle_command)
            case InputInterfaceType.MIDI_FILE:
                return FileMIDIInput(config, self)
            case InputInterfaceType.STDIN:
                return StdinMIDIInput(config, self)
            case _:
                logger.warning("Unknown MIDI input type: %s", config.interface_type)
                return None

    def _setup_audio_outputs(self) -> None:
        """Setup audio output engines from configuration."""
        output_cfg = self.cfg.audio_output
        if output_cfg is None:
            logger.info("Audio output disabled (none mode)")
            return

        if output_cfg.output_type == AudioOutputType.SOUNDDEVICE:
            self.audio_outputs["main"] = SoundDeviceOutput(output_cfg, self.synthesizer)
        elif output_cfg.output_type == AudioOutputType.FILE:
            self.audio_outputs["file"] = FileAudioOutput(output_cfg, self.synthesizer)
        elif output_cfg.output_type == AudioOutputType.NONE:
            logger.info("Audio output disabled (none mode)")

    def _initialize_style_engine(self) -> None:
        """Initialize style engine with configured paths."""
        if self.cfg.style_paths:
            self.style_engine.initialize(self.cfg.style_paths)

    # =========================================================================
    # Synthesizer communication
    # =========================================================================

    def _send_to_synthesizer(self, message: MIDIMessage) -> None:
        """Send MIDI message to the synthesizer's MIDI parser.

        Args:
            message: MIDI message to forward
        """
        midi_bytes = midimessage_to_bytes(message)
        self.synthesizer.midi_parser.parse_bytes(midi_bytes)

    # =========================================================================
    # Lifecycle
    # =========================================================================

    def start(self) -> None:
        """Start all workstation components."""
        if self.state.running:
            return

        self.state.running = True
        self._stop_event.clear()
        self.synthesizer.start()

        for interface in self.midi_inputs.values():
            interface.start()

        for output in self.audio_outputs.values():
            output.start()

        self._thread_manager.start("activity_decay", target=self._activity_decay_loop)

        logger.info("Workstation started")

    def _activity_decay_loop(self) -> None:
        """Gradually decay MIDI activity indicators."""
        event = self._stop_event
        while not event.is_set():
            event.wait(0.5)
            self.state.decay_midi_activity(0.85)

    def stop(self) -> None:
        """Stop all workstation components and clean up."""
        if not self.state.running:
            return

        self.state.running = False
        self._stop_event.set()

        self.metronome.stop()

        for interface in self.midi_inputs.values():
            interface.stop()

        for output in self.audio_outputs.values():
            output.stop()

        self.demo_mode.stop()
        self.synthesizer.stop()

        self._thread_manager.stop_all(timeout=1.0)
        logger.info("Workstation stopped")

    # =========================================================================
    # Recording
    # =========================================================================

    def toggle_recording(self) -> None:
        """Toggle recording on/off."""
        if self.recorder.is_recording:
            count = self.recorder.stop_recording()
            logger.info("Recording stopped: %d events", count)
        else:
            self.recorder.start_recording()
            logger.info("Recording started")

    def _is_recording(self) -> bool:
        """Thread-safe check of recording state (backward compat)."""
        return self.recorder.is_recording

    def _record_event(self, message: MIDIMessage) -> None:
        """Record event (backward compat, delegates to recorder)."""
        self.recorder.record_event(message)

    def _set_recording(self, active: bool) -> None:
        """Set recording state (backward compat)."""
        if active:
            self.recorder.start_recording()
        else:
            self.recorder.stop_recording()

    # =========================================================================
    # Playback
    # =========================================================================

    def toggle_playback(self) -> None:
        """Toggle playback of recorded events."""
        if self.recorder.is_playing:
            self.recorder.stop_playback()
        else:
            self.recorder.start_playback()

    # =========================================================================
    # Metronome
    # =========================================================================

    def toggle_metronome(self) -> None:
        """Toggle metronome on/off."""
        if self.metronome.is_active:
            self.metronome.stop()
        else:
            self.metronome.set_tempo(self.state.tempo)
            self.metronome.start()
        self.state.metronome = self.metronome.is_active

    # =========================================================================
    # State changes
    # =========================================================================

    def change_tempo(self, delta: float) -> None:
        """Change tempo by delta, clamped to [40, 300] BPM.

        Args:
            delta: Tempo change in BPM (positive or negative)
        """
        self.state.tempo = max(40.0, min(300.0, self.state.tempo + delta))
        self.metronome.set_tempo(self.state.tempo)

    def change_volume(self, delta: float) -> None:
        """Change master volume by delta, clamped to [0, 1].

        Args:
            delta: Volume change (positive or negative)
        """
        self.state.master_volume = max(0.0, min(1.0, self.state.master_volume + delta))

    # =========================================================================
    # Presets
    # =========================================================================

    def load_preset(self, filename: str) -> bool:
        """Load a preset from file.

        Args:
            filename: Preset file to load

        Returns:
            True if loaded successfully
        """
        preset = self.preset_manager.load_preset(filename)
        if not preset:
            return False
        self.state.current_preset = preset.name
        self._apply_preset(preset)
        return True

    def save_preset(self, filename: str | None = None) -> Path | None:
        """Save current state as a preset.

        Args:
            filename: Optional filename

        Returns:
            Path to saved file or None
        """
        preset = self._create_preset_from_state()
        return self.preset_manager.save_preset(preset, filename)

    def _create_preset_from_state(self) -> PresetData:
        """Create PresetData from current workstation state.

        Captures master volume, tempo, and MIDI Learn mappings.
        Per-channel state (programs, volumes, pans, effects sends) is
        not currently queryable from the real-time Synthesizer API and
        is left at default values.

        Returns:
            New PresetData instance
        """
        return PresetData(
            name=self.state.current_preset,
            master_volume=self.state.master_volume,
            tempo=self.state.tempo,
            midi_learn_mappings=self.midi_learn.export_mappings()["mappings"],
        )

    def _apply_preset(self, preset: PresetData) -> None:
        """Apply preset configuration.

        Args:
            preset: PresetData to apply
        """
        self.state.master_volume = preset.master_volume
        self.state.tempo = preset.tempo
        self.metronome.set_tempo(preset.tempo)

        # Apply MIDI Learn mappings
        self.midi_learn.import_mappings({"mappings": preset.midi_learn_mappings})

        # Apply program changes (synthesizer only, not through full send)
        for channel, program in preset.programs.items():
            msg = MIDIMessage(
                type="program_change",
                channel=channel,
                data={"program": program},
                timestamp=time.time(),
            )
            self._send_to_synthesizer(msg)

        logger.info("Preset applied: %s", preset.name)

    # =========================================================================
    # TUI / Demo
    # =========================================================================

    def run_tui(self) -> None:
        """Run the TUI control surface."""
        if self.tui:
            # Textual's LinuxDriver reads sys.__stderr__ during app.run()
            # and writes all terminal output there. We redirect stderr to
            # the log file for ALSA noise, so swap to stdout for the
            # duration of the TUI run.
            _orig___stderr__ = sys.__stderr__
            sys.__stderr__ = sys.__stdout__
            try:
                self.tui.run()
            except Exception:
                logger.exception("TUI encountered an error")
                raise
            finally:
                sys.__stderr__ = _orig___stderr__

    def run_demo(self, pattern: str = "scale") -> None:
        """Run a demo pattern.

        Args:
            pattern: Demo pattern name ('scale', 'chords', 'arpeggio')
        """
        self.demo_mode.start(pattern)

    # =========================================================================
    # Command dispatch
    # =========================================================================

    def _handle_command(self, key: str) -> None:
        """Handle keyboard command key.

        Args:
            key: Single-character command key
        """
        match key:
            case "r":
                self.toggle_recording()
            case "p":
                self.toggle_playback()
            case "s":
                self.recorder.stop_playback()
                self.metronome.stop()
                self.state.metronome = False
            case "m":
                self.toggle_metronome()
            case "+":
                self.change_tempo(5)
            case "-":
                self.change_tempo(-5)
            case "q":
                self.stop()
            case "h":
                logger.info(
                    "Commands: Ctrl+R=record, Ctrl+P=play, Ctrl+S=stop, Ctrl+M=metronome, "
                    "+/-=tempo, Ctrl+V=vol-, Ctrl+U=vol+, Ctrl+D=demo, Ctrl+E=export, Ctrl+Q=quit"
                )
            case "d":
                self.run_demo("scale")
            case "v":
                self.change_volume(-0.1)
            case "u":
                self.change_volume(0.1)
            case "e":
                self.export_midi()
            case _:
                return  # no op, skip force_refresh
        # Force TUI refresh immediately so keystroke doesn't linger on screen
        if self.tui:
            self.tui.force_refresh()

    def export_midi(self) -> None:
        """Export recorded events to a MIDI file."""
        import datetime

        filename = f"recording_{datetime.datetime.now():%Y%m%d_%H%M%S}.mid"
        self.recorder.export_midi(filename)

    # =========================================================================
    # Main run loop
    # =========================================================================

    def run(self) -> None:
        """Run the workstation: start components, then enter TUI or console loop."""
        self.start()

        try:
            if self.tui:
                self.run_tui()
            else:
                logger.info(
                    "Console mode. Commands: "
                    "Ctrl+R=record, Ctrl+P=play, Ctrl+S=stop, Ctrl+M=metronome, "
                    "+/-=tempo, v=vol-, V=vol+, Ctrl+E=export, Ctrl+D=demo, Ctrl+Q=quit"
                )
                while self.state.running:
                    self._stop_event.wait(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
