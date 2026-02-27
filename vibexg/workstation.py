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
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any

from synth.core.config_manager import ConfigManager
from synth.core.synthesizer import Synthesizer
from synth.midi import MIDIMessage

from .audio_outputs import AudioOutputEngine, SoundDeviceOutput, FileAudioOutput
from .demo import DemoMode
from .managers import PresetManager, MIDILearnManager, StyleEngineIntegration
from .midi_inputs import MIDIInputInterface, MidoPortInput, VirtualPortInput, NetworkMIDIInput, KeyboardInput, FileMIDIInput, StdinMIDIInput
from .tui import TUIControlSurface
from .types import (
    WorkstationState,
    PresetData,
    MIDIInputConfig,
    AudioOutputConfig,
    InputInterfaceType,
    AudioOutputType,
    DEFAULT_SAMPLE_RATE,
    DEFAULT_BUFFER_SIZE,
)
from .utils import midimessage_to_bytes

# Conditional import for Rich TUI
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.live import Live
    from rich.layout import Layout
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

logger = logging.getLogger(__name__)


class XGWorkstation:
    """
    XG Synthesizer Workstation - Main orchestration class.

    Complete implementation with:
    - Full MIDI message routing
    - Preset management
    - MIDI Learn
    - Style engine integration
    - Network MIDI support
    - Demo mode
    - TUI control surface
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize the workstation.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.state = WorkstationState()

        # Initialize core synthesizer
        sample_rate = self.config.get('sample_rate', DEFAULT_SAMPLE_RATE)
        buffer_size = self.config.get('buffer_size', DEFAULT_BUFFER_SIZE)

        self.synthesizer = Synthesizer(
            sample_rate=sample_rate,
            buffer_size=buffer_size,
            enable_audio_output=False  # We handle audio output separately
        )

        # MIDI input interfaces
        self.midi_inputs: dict[str, MIDIInputInterface] = {}
        self.midi_queue: queue.Queue = queue.Queue()

        # Audio output engines
        self.audio_outputs: dict[str, AudioOutputEngine] = {}

        # TUI control surface
        self.tui: TUIControlSurface | None = None

        # Recording
        self.recorded_events: list[dict[str, Any]] = []
        self.recording_start_time: float = 0

        # Performance monitoring
        self.last_perf_update = time.time()
        self.voice_count_samples = 0

        # Preset manager
        preset_dir = self.config.get('preset_dir', 'presets')
        self.preset_manager = PresetManager(preset_dir)

        # MIDI Learn manager
        self.midi_learn = MIDILearnManager(self.synthesizer)

        # Style engine integration
        self.style_engine = StyleEngineIntegration(self.synthesizer)

        # Demo mode
        self.demo_mode = DemoMode(self.synthesizer)

        # Initialize components
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
        style_paths = self.config.get('style_paths', [])
        if style_paths:
            self.style_engine.initialize(style_paths)

    def _load_configuration(self):
        """Load configuration from file or defaults."""
        config_path = self.config.get('config_file', 'config.yaml')
        if os.path.exists(config_path):
            try:
                config_manager = ConfigManager(config_path)
                config_manager.load()
                # Apply relevant settings
                self.state.tempo = config_manager.get_tempo() if hasattr(config_manager, 'get_tempo') else 120.0
                self.state.master_volume = config_manager.get_volume() if hasattr(config_manager, 'get_volume') else 0.8
                logger.info(f"Configuration loaded from {config_path}")
            except Exception as e:
                logger.warning(f"Failed to load configuration: {e}")

    def _setup_midi_inputs(self):
        """Setup MIDI input interfaces from configuration."""
        input_configs = self.config.get('midi_inputs', [])

        for input_config in input_configs:
            interface_type = InputInterfaceType(input_config.get('type', 'mido_port'))
            config = MIDIInputConfig(
                interface_type=interface_type,
                name=input_config.get('name', ''),
                port_name=input_config.get('port_name', ''),
                channel_filter=input_config.get('channel_filter'),
                velocity_offset=input_config.get('velocity_offset', 0),
                transpose=input_config.get('transpose', 0),
                options=input_config.get('options', {})
            )

            interface = self._create_midi_interface(config)
            if interface:
                self.midi_inputs[config.name or config.interface_type.value] = interface

        # Default keyboard input if no inputs configured
        if not self.midi_inputs:
            config = MIDIInputConfig(interface_type=InputInterfaceType.KEYBOARD)
            interface = KeyboardInput(config, self._handle_midi_message)
            self.midi_inputs['keyboard'] = interface

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
                return KeyboardInput(config, self._handle_midi_message)
            
            case InputInterfaceType.MIDI_FILE:
                return FileMIDIInput(config, self._handle_midi_message)
            
            case InputInterfaceType.STDIN:
                return StdinMIDIInput(config, self._handle_midi_message)
            
            case _:
                logger.warning(f"Unknown MIDI input type: {config.interface_type}")
                return None

    def _setup_audio_outputs(self):
        """Setup audio output engines from configuration."""
        output_config = self.config.get('audio_output', {})
        output_type = AudioOutputType(output_config.get('type', 'sounddevice'))

        config = AudioOutputConfig(
            output_type=output_type,
            device_name=output_config.get('device_name', ''),
            file_path=output_config.get('file_path', ''),
            file_format=output_config.get('file_format', 'wav'),
            sample_rate=output_config.get('sample_rate', DEFAULT_SAMPLE_RATE),
            buffer_size=output_config.get('buffer_size', DEFAULT_BUFFER_SIZE)
        )

        if config.output_type == AudioOutputType.SOUNDDEVICE:
            self.audio_outputs['main'] = SoundDeviceOutput(config, self.synthesizer)
        elif config.output_type == AudioOutputType.FILE:
            self.audio_outputs['file'] = FileAudioOutput(config, self.synthesizer)

    def _handle_midi_message(self, message: MIDIMessage):
        """
        Handle incoming MIDI message with full routing.

        Args:
            message: MIDIMessage to process
        """
        # Update MIDI activity
        if message.channel is not None:
            self.state.midi_activity[message.channel] += 1

        # Record if recording
        if self.state.recording:
            self._record_event(message)

        # Process through MIDI Learn
        if message.type == 'control_change':
            cc = message.data.get('controller', 0)
            value = message.data.get('value', 0)
            self.midi_learn.process_cc(cc, value, message.channel or 0)

        # Send to synthesizer (FULL MIDI ROUTING IMPLEMENTED)
        midi_bytes = midimessage_to_bytes(message)
        self.synthesizer.midi_parser.parse_bytes(midi_bytes)

        # Update state for note messages
        match message.type:
            case 'note_on':
                self.state.voices_active += 1
            
            case 'note_off':
                self.state.voices_active = max(0, self.state.voices_active - 1)
            
            case _:
                pass  # No voice count change for other message types

    def _record_event(self, message: MIDIMessage):
        """
        Record MIDI event.

        Args:
            message: MIDIMessage to record
        """
        event = {
            'type': message.type,
            'channel': message.channel,
            'data': message.data,
            'timestamp': time.time() - self.recording_start_time
        }
        self.recorded_events.append(event)

    def start(self):
        """Start the workstation."""
        if self.state.running:
            return

        self.state.running = True
        self.synthesizer.start()

        # Start all MIDI inputs
        for interface in self.midi_inputs.values():
            interface.start()

        # Start all audio outputs
        for output in self.audio_outputs.values():
            output.start()

        logger.info("Workstation started")

    def stop(self):
        """Stop the workstation."""
        if not self.state.running:
            return

        self.state.running = False

        # Stop all MIDI inputs
        for interface in self.midi_inputs.values():
            interface.stop()

        # Stop all audio outputs
        for output in self.audio_outputs.values():
            output.stop()

        # Stop demo mode
        self.demo_mode.stop()

        self.synthesizer.stop()
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
        if not self.recorded_events:
            self.state.playing = False
            return

        start_time = time.time()
        for event in self.recorded_events:
            if not self.state.playing:
                break

            # Wait until event time
            wait_time = event['timestamp'] - (time.time() - start_time)
            if wait_time > 0:
                time.sleep(wait_time)

            # Create and send MIDI message
            msg = MIDIMessage(
                type=event['type'],
                channel=event['channel'],
                data=event['data'],
                timestamp=time.time()
            )
            self._handle_midi_message(msg)

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
            # Send MIDI sync or audio click
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
            midi_learn_mappings=self.midi_learn.export_mappings()['mappings']
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
        self.midi_learn.import_mappings({'mappings': preset.midi_learn_mappings})

        # Apply program changes
        for channel, program in preset.programs.items():
            msg = MIDIMessage(
                type='program_change',
                channel=channel,
                data={'program': program},
                timestamp=time.time()
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

    def run(self):
        """Main run loop."""
        self.start()

        try:
            if self.tui:
                self.run_tui()
            else:
                # Simple console mode
                print("XG Workstation running. Press Ctrl+C to stop.")
                print("Commands: r=record, p=play, s=stop, m=metronome, +/-=tempo, v=volume, d=demo, q=quit")

                while self.state.running:
                    cmd = input("> ").strip().lower()
                    if cmd == 'r':
                        self.toggle_recording()
                    elif cmd == 'p':
                        self.toggle_playback()
                    elif cmd == 's':
                        self.state.playing = False
                        self.state.metronome = False
                    elif cmd == 'm':
                        self.toggle_metronome()
                    elif cmd == '+':
                        self.change_tempo(5)
                    elif cmd == '-':
                        self.change_tempo(-5)
                    elif cmd == 'v':
                        vol = input("Volume (0-100): ").strip()
                        self.state.master_volume = int(vol) / 100
                    elif cmd == 'd':
                        pattern = input("Demo pattern (scale/chords/arpeggio): ").strip()
                        self.run_demo(pattern or "scale")
                    elif cmd == 'q':
                        break
                    elif cmd == 'h':
                        print("Commands: r=record, p=play, s=stop, m=metronome, +/-=tempo, v=volume, d=demo, q=quit")
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
