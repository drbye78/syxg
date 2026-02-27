"""
Vibexg MIDI Inputs - MIDI input interface implementations

This module provides various MIDI input interfaces including:
- Physical MIDI ports via RtMidi
- Virtual MIDI ports for inter-process communication
- Network MIDI (RTP-MIDI)
- Computer keyboard input
- MIDI file playback
- Stdin MIDI input for scripting
"""
from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from collections.abc import Callable

from synth.midi import MIDIMessage, RealtimeParser, get_input_names, open_input, open_output, RTMIDI_AVAILABLE

from .types import MIDIInputConfig, InputInterfaceType
from .backends.network import NetworkMIDIHandler

logger = logging.getLogger(__name__)


class MIDIInputInterface:
    """
    Base class for MIDI input interfaces.

    All MIDI input interfaces inherit from this class and implement
    the _start_interface() and _stop_interface() methods.
    """

    def __init__(self, config: MIDIInputConfig, message_callback: Callable[[MIDIMessage], None]):
        """
        Initialize the MIDI input interface.

        Args:
            config: Configuration for this input interface
            message_callback: Function to call with received MIDIMessage objects
        """
        self.config = config
        self.message_callback = message_callback
        self.parser = RealtimeParser()
        self.running = False
        self.thread: threading.Thread | None = None

    def start(self):
        """Start the MIDI input interface."""
        self.running = True
        self._start_interface()

    def stop(self):
        """Stop the MIDI input interface."""
        self.running = False
        self._stop_interface()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

    def _start_interface(self):
        """Override to start specific interface."""
        pass

    def _stop_interface(self):
        """Override to stop specific interface."""
        pass

    def _send_message(self, message: MIDIMessage):
        """
        Apply transformations and send message to callback.

        Args:
            message: MIDIMessage to process and send
        """
        if message.channel is not None:
            # Apply channel filter
            if self.config.channel_filter and message.channel not in self.config.channel_filter:
                return

            # Apply transpose
            if self.config.transpose and message.note is not None:
                message.data['note'] = max(0, min(127, message.note + self.config.transpose))

            # Apply velocity offset
            if self.config.velocity_offset and message.velocity is not None:
                message.data['velocity'] = max(0, min(127, message.velocity + self.config.velocity_offset))

        self.message_callback(message)


class MidoPortInput(MIDIInputInterface):
    """
    MIDI input from physical/virtual MIDI ports using synth.midi ports.

    This class provides access to physical MIDI interfaces connected to
    the system via RtMidi.
    """

    def __init__(self, config: MIDIInputConfig, message_callback: Callable[[MIDIMessage], None]):
        super().__init__(config, message_callback)
        self.port = None

    def _start_interface(self):
        if not RTMIDI_AVAILABLE:
            logger.error("rtmidi not available for MIDI port input. Install with: pip install rtmidi")
            return

        try:
            # Get available input ports
            ports = get_input_names()
            port_name = self.config.port_name or (ports[0] if ports else None)

            if not port_name:
                logger.error("No MIDI input ports available")
                return

            self.port = open_input(port_name, callback=self._midimessage_callback)
            logger.info(f"MIDI port opened: {port_name}")
        except Exception as e:
            logger.error(f"Failed to open MIDI port: {e}")

    def _stop_interface(self):
        if self.port:
            self.port.close()
            self.port = None

    def _midimessage_callback(self, msg: MIDIMessage):
        """Callback for MIDIMessage objects (already in correct format)."""
        if not self.running:
            return
        self._send_message(msg)  # Already a MIDIMessage, no conversion needed!


class VirtualPortInput(MIDIInputInterface):
    """
    Virtual MIDI port for inter-process communication.

    Creates a virtual MIDI port that other applications can connect to,
    enabling MIDI communication between processes.
    """

    def _start_interface(self):
        if not RTMIDI_AVAILABLE:
            logger.error("rtmidi not available for virtual port creation. Install with: pip install rtmidi")
            return

        try:
            port_name = self.config.port_name or "XG-Workstation-Virtual"
            self.port = open_output(port_name, virtual=True)
            logger.info(f"Virtual MIDI port created: {port_name}")
        except Exception as e:
            logger.error(f"Failed to create virtual MIDI port: {e}")

    def _stop_interface(self):
        if hasattr(self, 'port') and self.port:
            self.port.close()


class NetworkMIDIInput(MIDIInputInterface):
    """
    Network MIDI input (RTP-MIDI / AppleMIDI).

    Receives MIDI messages over the network using the RTP-MIDI protocol,
    enabling wireless MIDI connections.
    """

    def __init__(self, config: MIDIInputConfig, message_callback: Callable[[MIDIMessage], None]):
        super().__init__(config, message_callback)
        self.network_handler = NetworkMIDIHandler(
            host=config.options.get('host', '0.0.0.0'),
            port=config.options.get('port', 5004)
        )

    def _start_interface(self):
        self.network_handler.start(self.message_callback)

    def _stop_interface(self):
        self.network_handler.stop()


class KeyboardInput(MIDIInputInterface):
    """
    Computer keyboard as MIDI input.

    Maps computer keyboard keys to MIDI notes, allowing the user to
    play notes using their computer keyboard.

    Key mapping:
    - Z to M = C3 to B3 (white keys)
    - Q to U = C4 to B4 (white keys)
    - Black keys on upper row
    """

    def __init__(self, config: MIDIInputConfig, message_callback: Callable[[MIDIMessage], None]):
        super().__init__(config, message_callback)
        self.key_map = self._create_key_map()

    def _create_key_map(self) -> dict[str, int]:
        """
        Create keyboard to MIDI note mapping.

        Returns:
            Dictionary mapping keyboard characters to MIDI note numbers
        """
        # Z to M = C3 to B3, Q to U = C4 to B4
        white_keys = "zsxdcvgbhnjm,l.;/'"
        black_keys = "edcftgyhujko"
        note_map = {}

        # White keys (C3 to C4)
        notes_white = [60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79, 81, 83, 84]
        for i, key in enumerate(white_keys[:len(notes_white)]):
            note_map[key] = notes_white[i]

        # Black keys
        notes_black = [61, 63, 66, 68, 70, 73, 75, 78, 80, 82]
        for i, key in enumerate(black_keys[:len(notes_black)]):
            note_map[key] = notes_black[i]

        return note_map

    def _start_interface(self):
        try:
            from synth.utils.keyboard import KeyboardListener

            self.keyboard_listener = KeyboardListener()

            def on_key_press(key: str):
                if key.lower() in self.key_map:
                    note = self.key_map[key.lower()]
                    msg = MIDIMessage(
                        type='note_on',
                        channel=0,
                        data={'note': note, 'velocity': 80},
                        timestamp=time.time()
                    )
                    self._send_message(msg)

            def on_key_release(key: str):
                if key.lower() in self.key_map:
                    note = self.key_map[key.lower()]
                    msg = MIDIMessage(
                        type='note_off',
                        channel=0,
                        data={'note': note, 'velocity': 64},
                        timestamp=time.time()
                    )
                    self._send_message(msg)

            self.keyboard_listener.add_callback(on_key_press, on_key_release)
            self.keyboard_listener.start()
            logger.info("Keyboard MIDI input started")
        except Exception as e:
            logger.error(f"Failed to start keyboard input: {e}")

    def _stop_interface(self):
        if hasattr(self, 'keyboard_listener') and self.keyboard_listener:
            self.keyboard_listener.stop()


class FileMIDIInput(MIDIInputInterface):
    """
    MIDI file input for playback.

    Plays back MIDI files in real-time, with support for tempo adjustment
    and looping.
    """

    def __init__(self, config: MIDIInputConfig, message_callback: Callable[[MIDIMessage], None]):
        super().__init__(config, message_callback)
        self.file_path = config.options.get('file_path', '')
        self.tempo_multiplier = config.options.get('tempo', 1.0)
        self.loop = config.options.get('loop', False)

    def _start_interface(self):
        self.thread = threading.Thread(target=self._playback_thread, daemon=True)
        self.thread.start()

    def _stop_interface(self):
        self.running = False

    def _playback_thread(self):
        """Playback MIDI file in real-time."""
        from synth.midi import FileParser

        if not os.path.exists(self.file_path):
            logger.error(f"MIDI file not found: {self.file_path}")
            return

        try:
            # Use FileParser from synth.midi
            parser = FileParser()
            messages = parser.parse_file(self.file_path)

            while self.running:
                for midimsg in messages:
                    if not self.running:
                        return

                    # Apply tempo adjustment
                    adjusted_timestamp = time.time() + (midimsg.timestamp / self.tempo_multiplier)
                    midimsg.timestamp = adjusted_timestamp
                    self._send_message(midimsg)

                if not self.loop:
                    break

                time.sleep(0.1)

        except Exception as e:
            logger.error(f"MIDI file playback error: {e}")


class StdinMIDIInput(MIDIInputInterface):
    """
    MIDI input from stdin (for scripting/automation).

    Reads JSON-formatted MIDI messages from stdin, enabling script-based
    control and automation of the workstation.
    """

    def _start_interface(self):
        self.thread = threading.Thread(target=self._read_thread, daemon=True)
        self.thread.start()

    def _stop_interface(self):
        self.running = False

    def _read_thread(self):
        """Read MIDI messages from stdin."""
        try:
            while self.running:
                line = sys.stdin.readline()
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                # Parse JSON MIDI message
                try:
                    data = json.loads(line)
                    msg = MIDIMessage(
                        type=data.get('type', 'note_on'),
                        channel=data.get('channel', 0),
                        data=data.get('data', {}),
                        timestamp=time.time()
                    )
                    self._send_message(msg)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON MIDI message: {line}")

        except Exception as e:
            logger.error(f"Stdin MIDI input error: {e}")
