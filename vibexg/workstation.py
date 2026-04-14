"""
Vibexg Workstation - Main XG Synthesizer Workstation orchestration

This module provides the XGWorkstation class, which is the main
orchestration class that coordinates all components of the virtual
XG synthesizer workstation.
"""

from __future__ import annotations

import logging
import os
import queue
import threading
import time
from pathlib import Path
from typing import Any

from synth.io.midi import MIDIMessage
from synth.primitives.config_manager import ConfigManager
from synth.synthesizers.realtime import Synthesizer

from .audio_outputs import AudioOutputEngine, FileAudioOutput, SoundDeviceOutput
from .demo import DemoMode
from .managers import MIDILearnManager, PresetManager, StyleEngineIntegration
from .midi_inputs import (
    FileMIDIInput,
    KeyboardInput,
    MIDIInputInterface,
    MidoPortInput,
    NetworkMIDIInput,
    StdinMIDIInput,
    VirtualPortInput,
)
from .tui import TUIControlSurface
from .types import (
    DEFAULT_BUFFER_SIZE,
    DEFAULT_SAMPLE_RATE,
    AudioOutputConfig,
    AudioOutputType,
    InputInterfaceType,
    MIDIInputConfig,
    PresetData,
    WorkstationState,
)
from .utils import midimessage_to_bytes

try:
    RICH_AVAILABLE = True
    from rich.console import Console  # noqa: F401
except ImportError:
    RICH_AVAILABLE = False

logger = logging.getLogger(__name__)


class XGWorkstation:
    """XG Synthesizer Workstation - Main orchestration class."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.state = WorkstationState()

        sample_rate = self.config.get("sample_rate", DEFAULT_SAMPLE_RATE)
        buffer_size = self.config.get("buffer_size", DEFAULT_BUFFER_SIZE)

        self.synthesizer = Synthesizer(
            sample_rate=sample_rate,
            buffer_size=buffer_size,
            enable_audio_output=False,
        )

        self.midi_inputs: dict[str, MIDIInputInterface] = {}
        self.midi_queue: queue.Queue = queue.Queue()

        self.audio_outputs: dict[str, AudioOutputEngine] = {}

        self.tui: TUIControlSurface | None = None

        self.recorded_events: list[dict[str, Any]] = []
        self.recording_start_time: float = 0

        self.last_perf_update = time.time()
        self.voice_count_samples = 0

        preset_dir = self.config.get("preset_dir", "presets")
        self.preset_manager = PresetManager(preset_dir)

        self.midi_learn = MIDILearnManager(self.synthesizer)

        self.style_engine = StyleEngineIntegration(self.synthesizer)

        self.demo_mode = DemoMode(self.synthesizer)

        self._activity_decay_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        self._initialize_components()

    def _initialize_components(self):
        """Initialize all workstation components."""
        # Load configuration
        self._load_configuration()

        # Setup MIDI inputs
        self._setup_midi_inputs()

        # Setup audio outputs
        self._setup_audio_outputs()

        # Initialize style engine
        self._initialize_style_engine()

        # Setup TUI if available
        if RICH_AVAILABLE:
            self.tui = TUIControlSurface(self)

        logger.info("Workstation initialized")

    def _initialize_style_engine(self):
        """Initialize style engine."""
        style_paths = self.config.get("style_paths", [])
        if style_paths:
            self.style_engine.initialize(style_paths)

    def _load_configuration(self):
        """Load configuration from file or defaults."""
        config_path = self.config.get("config_file", "config.yaml")
        if os.path.exists(config_path):
            try:
                config_manager = ConfigManager(config_path)
                config_manager.load()
                # Apply relevant settings
                self.state.tempo = (
                    config_manager.get_tempo() if hasattr(config_manager, "get_tempo") else 120.0
                )
                self.state.master_volume = (
                    config_manager.get_volume() if hasattr(config_manager, "get_volume") else 0.8
                )
                logger.info(f"Configuration loaded from {config_path}")
            except Exception as e:
                logger.warning(f"Failed to load configuration: {e}")

    def _setup_midi_inputs(self):
        """Setup MIDI input interfaces from configuration."""
        input_configs = self.config.get("midi_inputs", [])

        for input_config in input_configs:
            interface_type = InputInterfaceType(input_config.get("type", "mido_port"))
            config = MIDIInputConfig(
                interface_type=interface_type,
                name=input_config.get("name", ""),
                port_name=input_config.get("port_name", ""),
                channel_filter=input_config.get("channel_filter"),
                velocity_offset=input_config.get("velocity_offset", 0),
                transpose=input_config.get("transpose", 0),
                options=input_config.get("options", {}),
            )

            interface = self._create_midi_interface(config)
            if interface:
                self.midi_inputs[config.name or config.interface_type.value] = interface

        # Default keyboard input if no inputs configured
        if not self.midi_inputs:
            config = MIDIInputConfig(interface_type=InputInterfaceType.KEYBOARD)
            interface = KeyboardInput(config, self._handle_midi_message, self._handle_command)
            self.midi_inputs["keyboard"] = interface

    def _create_midi_interface(self, config: MIDIInputConfig) -> MIDIInputInterface | None:
        """
        Create MIDI input interface based on configuration.

        Args:
            config: MIDI input configuration

        Returns:
            MIDIInputInterface instance or None if unknown type
        """
        match config.interface_type:
            case InputInterfaceType.MIDO_PORT:
                return MidoPortInput(config, self._handle_midi_message)

            case InputInterfaceType.VIRTUAL_PORT:
                return VirtualPortInput(config, self._handle_midi_message)

            case InputInterfaceType.NETWORK_MIDI:
                return NetworkMIDIInput(config, self._handle_midi_message)

            case InputInterfaceType.KEYBOARD:
                return KeyboardInput(config, self._handle_midi_message, self._handle_command)

            case InputInterfaceType.MIDI_FILE:
                return FileMIDIInput(config, self._handle_midi_message)

            case InputInterfaceType.STDIN:
                return StdinMIDIInput(config, self._handle_midi_message)

            case _:
                logger.warning(f"Unknown MIDI input type: {config.interface_type}")
                return None

    def _setup_audio_outputs(self):
        """Setup audio output engines from configuration."""
        output_config = self.config.get("audio_output", {})
        output_type = AudioOutputType(output_config.get("type", "sounddevice"))

        config = AudioOutputConfig(
            output_type=output_type,
            device_name=output_config.get("device_name", ""),
            file_path=output_config.get("file_path", ""),
            file_format=output_config.get("file_format", "wav"),
            sample_rate=output_config.get("sample_rate", DEFAULT_SAMPLE_RATE),
            buffer_size=output_config.get("buffer_size", DEFAULT_BUFFER_SIZE),
        )

        if config.output_type == AudioOutputType.SOUNDDEVICE:
            self.audio_outputs["main"] = SoundDeviceOutput(config, self.synthesizer)
        elif config.output_type == AudioOutputType.FILE:
            self.audio_outputs["file"] = FileAudioOutput(config, self.synthesizer)

    def _handle_midi_message(self, message: MIDIMessage):
        if message.channel is not None:
            self.state.increment_midi_activity(message.channel)

        if self.state.recording:
            self._record_event(message)

        if message.type == "control_change":
            cc = message.data.get("controller", 0)
            value = message.data.get("value", 0)
            self.midi_learn.process_cc(cc, value, message.channel or 0)

        midi_bytes = midimessage_to_bytes(message)
        self.synthesizer.midi_parser.parse_bytes(midi_bytes)

        match message.type:
            case "note_on":
                velocity = message.data.get("velocity", 64)
                self.state.adjust_voices_active(1 if velocity > 0 else -1)
            case "note_off":
                self.state.adjust_voices_active(-1)
            case _:
                pass

    def _record_event(self, message: MIDIMessage):
        """
        Record MIDI event.

        Args:
            message: MIDIMessage to record
        """
        event = {
            "type": message.type,
            "channel": message.channel,
            "data": message.data,
            "timestamp": time.time() - self.recording_start_time,
        }
        self.recorded_events.append(event)

    def start(self):
        if self.state.running:
            return

        self.state.running = True
        self._stop_event.clear()
        self.synthesizer.start()

        for interface in self.midi_inputs.values():
            interface.start()

        for output in self.audio_outputs.values():
            output.start()

        self._activity_decay_thread = threading.Thread(
            target=self._activity_decay_loop, daemon=True
        )
        self._activity_decay_thread.start()

        logger.info("Workstation started")

    def _activity_decay_loop(self):
        while not self._stop_event.is_set():
            self._stop_event.wait(0.5)
            self.state.decay_midi_activity(0.85)

    def stop(self):
        if not self.state.running:
            return

        self.state.running = False
        self._stop_event.set()

        for interface in self.midi_inputs.values():
            interface.stop()

        for output in self.audio_outputs.values():
            output.stop()

        self.demo_mode.stop()

        self.synthesizer.stop()
        if self._activity_decay_thread and self._activity_decay_thread.is_alive():
            self._activity_decay_thread.join(timeout=1.0)
        logger.info("Workstation stopped")

    def toggle_recording(self):
        """Toggle recording state."""
        if self.state.recording:
            self.state.recording = False
            logger.info(f"Recording stopped: {len(self.recorded_events)} events")
        else:
            self.state.recording = True
            self.recording_start_time = time.time()
            self.recorded_events.clear()
            logger.info("Recording started")

    def toggle_playback(self):
        """Toggle playback of recorded events."""
        if self.state.playing:
            self.state.playing = False
        else:
            self.state.playing = True
            threading.Thread(target=self._playback_thread, daemon=True).start()

    def _playback_thread(self):
        """Playback recorded MIDI events."""
        try:
            if not self.recorded_events:
                return

            start_time = time.time()
            for event in self.recorded_events:
                if not self.state.playing:
                    break

                try:
                    wait_time = event["timestamp"] - (time.time() - start_time)
                    if wait_time > 0:
                        time.sleep(wait_time)

                    msg = MIDIMessage(
                        type=event["type"],
                        channel=event["channel"],
                        data=event["data"],
                        timestamp=time.time(),
                    )
                    self._handle_midi_message(msg)
                except (KeyError, TypeError) as e:
                    logger.error(f"Playback event error: {e}")
                    continue
        finally:
            self.state.playing = False

    def toggle_metronome(self):
        """Toggle metronome."""
        self.state.metronome = not self.state.metronome
        if self.state.metronome:
            threading.Thread(target=self._metronome_thread, daemon=True).start()

    def _metronome_thread(self):
        """Metronome click track."""
        beat_interval = 60.0 / self.state.tempo
        while self.state.metronome and self.state.running:
            try:
                click_msg = MIDIMessage(
                    type="note_on",
                    channel=9,
                    data={"note": 37, "velocity": 80},
                    timestamp=time.time(),
                )
                self._handle_midi_message(click_msg)
                off_msg = MIDIMessage(
                    type="note_off",
                    channel=9,
                    data={"note": 37, "velocity": 0},
                    timestamp=time.time(),
                )
                self._handle_midi_message(off_msg)
            except Exception as e:
                logger.error(f"Metronome click error: {e}")
            time.sleep(beat_interval)

    def change_tempo(self, delta: float):
        """
        Change tempo.

        Args:
            delta: Tempo change in BPM
        """
        self.state.tempo = max(40.0, min(300.0, self.state.tempo + delta))

    def change_volume(self, delta: float):
        """
        Change master volume.

        Args:
            delta: Volume change (0.0-1.0)
        """
        self.state.master_volume = max(0.0, min(1.0, self.state.master_volume + delta))

    def load_preset(self, filename: str) -> bool:
        """
        Load a preset.

        Args:
            filename: Preset file to load

        Returns:
            True if loaded successfully, False otherwise
        """
        preset = self.preset_manager.load_preset(filename)
        if preset:
            self.state.current_preset = preset.name
            self._apply_preset(preset)
            return True
        return False

    def save_preset(self, filename: str | None = None) -> Path | None:
        """
        Save current preset.

        Args:
            filename: Optional filename

        Returns:
            Path to saved file or None
        """
        preset = self._create_preset_from_state()
        return self.preset_manager.save_preset(preset, filename)

    def _create_preset_from_state(self) -> PresetData:
        """
        Create preset from current state.

        Returns:
            New PresetData instance
        """
        preset = PresetData(
            name=self.state.current_preset,
            master_volume=self.state.master_volume,
            tempo=self.state.tempo,
            midi_learn_mappings=self.midi_learn.export_mappings()["mappings"],
        )
        return preset

    def _apply_preset(self, preset: PresetData):
        """
        Apply preset configuration.

        Args:
            preset: PresetData to apply
        """
        self.state.master_volume = preset.master_volume
        self.state.tempo = preset.tempo

        # Apply MIDI Learn mappings
        self.midi_learn.import_mappings({"mappings": preset.midi_learn_mappings})

        # Apply program changes
        for channel, program in preset.programs.items():
            msg = MIDIMessage(
                type="program_change",
                channel=channel,
                data={"program": program},
                timestamp=time.time(),
            )
            self._handle_midi_message(msg)

        logger.info(f"Preset applied: {preset.name}")

    def run_tui(self):
        """Run the TUI control surface."""
        if self.tui:
            self.tui.run()

    def run_demo(self, pattern: str = "scale"):
        """
        Run demo pattern.

        Args:
            pattern: Demo pattern name
        """
        self.demo_mode.start(pattern)

    def _handle_command(self, key: str):
        key = key.lower()
        match key:
            case "r":
                self.toggle_recording()
            case "p":
                self.toggle_playback()
            case "s":
                self.state.playing = False
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
                    "Commands: r=record, p=play, s=stop, m=metronome, "
                    "+/-=tempo, v=volume, d=demo, q=quit"
                )
            case "d":
                self.run_demo("scale")
            case "v":
                self.state.master_volume = max(0.0, self.state.master_volume - 0.1)
            case _:
                pass

    def run(self):
        self.start()

        try:
            if self.tui:
                self.run_tui()
            else:
                logger.info(
                    "Console mode. Commands: "
                    "r=record, p=play, s=stop, m=metronome, "
                    "+/-=tempo, v=volume, d=demo, q=quit"
                )

                while self.state.running:
                    self._stop_event.wait(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
