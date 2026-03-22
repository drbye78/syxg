"""
Vibexg Demo Mode - Demo patterns for testing audio output

This module provides demo patterns to test the audio output and
synthesizer functionality without requiring external MIDI input.
"""

from __future__ import annotations

import logging
import threading
import time

from synth.core.synthesizer import Synthesizer
from synth.midi import MIDIMessage

from .utils import midimessage_to_bytes

logger = logging.getLogger(__name__)


class DemoMode:
    """
    Demo mode for testing audio output.

    Provides several demo patterns (scale, chords, arpeggio) that can
    be used to test the audio output and synthesizer functionality.
    """

    def __init__(self, synthesizer: Synthesizer):
        """
        Initialize demo mode.

        Args:
            synthesizer: Synthesizer instance to send notes to
        """
        self.synthesizer = synthesizer
        self.running = False
        self.thread: threading.Thread | None = None

    def start(self, pattern: str = "scale"):
        """
        Start demo pattern.

        Args:
            pattern: Pattern to play ("scale", "chords", or "arpeggio")
        """
        self.running = True
        self.thread = threading.Thread(target=self._demo_thread, args=(pattern,), daemon=True)
        self.thread.start()
        logger.info(f"Demo mode started: {pattern}")

    def stop(self):
        """Stop demo mode."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)

    def _demo_thread(self, pattern: str):
        """
        Run demo pattern.

        Args:
            pattern: Pattern name to execute
        """
        match pattern:
            case "scale":
                self._play_scale()

            case "chords":
                self._play_chords()

            case "arpeggio":
                self._play_arpeggio()

            case _:
                logger.warning(f"Unknown demo pattern: {pattern}")
                self._play_scale()  # Default to scale

    def _send_note_on(self, note: int, velocity: int = 80, channel: int = 0):
        """
        Send note on to synthesizer.

        Args:
            note: MIDI note number (0-127)
            velocity: Note velocity (0-127)
            channel: MIDI channel (0-15)
        """
        msg = MIDIMessage(
            type="note_on",
            channel=channel,
            data={"note": note, "velocity": velocity},
            timestamp=time.time(),
        )
        self.synthesizer.midi_parser.parse_bytes(midimessage_to_bytes(msg))

    def _send_note_off(self, note: int, velocity: int = 64, channel: int = 0):
        """
        Send note off to synthesizer.

        Args:
            note: MIDI note number (0-127)
            velocity: Note-off velocity (0-127)
            channel: MIDI channel (0-15)
        """
        msg = MIDIMessage(
            type="note_off",
            channel=channel,
            data={"note": note, "velocity": velocity},
            timestamp=time.time(),
        )
        self.synthesizer.midi_parser.parse_bytes(midimessage_to_bytes(msg))

    def _play_scale(self):
        """Play a C major scale."""
        scale_notes = [60, 62, 64, 65, 67, 69, 71, 72]  # C4 to C5

        for note in scale_notes:
            if not self.running:
                break
            self._send_note_on(note, 80)
            time.sleep(0.3)
            self._send_note_off(note, 64)
            time.sleep(0.1)

        # Play descending
        for note in reversed(scale_notes):
            if not self.running:
                break
            self._send_note_on(note, 80)
            time.sleep(0.3)
            self._send_note_off(note, 64)
            time.sleep(0.1)

        logger.info("Demo scale complete")

    def _play_chords(self):
        """Play chord progression."""
        chords = [
            [60, 64, 67],  # C major
            [67, 71, 74],  # G major
            [72, 76, 79],  # C major (higher)
            [65, 69, 72],  # F major
        ]

        for chord in chords:
            if not self.running:
                break

            # Play chord
            for note in chord:
                self._send_note_on(note, 70)

            time.sleep(0.5)

            # Release chord
            for note in chord:
                self._send_note_off(note, 64)

            time.sleep(0.2)

        logger.info("Demo chords complete")

    def _play_arpeggio(self):
        """Play arpeggio pattern."""
        root = 60  # C4
        pattern = [0, 4, 7, 12, 7, 4]  # Arpeggio intervals

        for _ in range(2):  # Repeat twice
            for interval in pattern:
                if not self.running:
                    break
                note = root + interval
                self._send_note_on(note, 75)
                time.sleep(0.15)
                self._send_note_off(note, 64)

        logger.info("Demo arpeggio complete")
