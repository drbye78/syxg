"""
Vibexg Metronome — Isolated metronome click track

Extracted from XGWorkstation. Manages an interruptible metronome
click thread with proper note duration for audible ticks.
"""

from __future__ import annotations

import logging

from synth.io.midi import MIDIMessage

from .midi_sink import MidiMessageSink
from .threading import ThreadManager

logger = logging.getLogger(__name__)


class Metronome:
    """Isolated metronome click track.

    Provides an audible click on MIDI channel 9 (percussion) at the
    configured tempo. Uses ThreadManager for thread lifecycle, ensuring
    no thread leaks on rapid toggle.
    """

    def __init__(
        self,
        sink: MidiMessageSink,
        thread_manager: ThreadManager,
    ) -> None:
        """Initialize Metronome.

        Args:
            sink: Message sink to send click events through
            thread_manager: Centralized thread manager for the click thread
        """
        self._sink = sink
        self._thread_manager = thread_manager
        self._tempo: float = 120.0
        self._active = False

    @property
    def is_active(self) -> bool:
        """Check if metronome is currently playing."""
        return self._active

    @property
    def tempo(self) -> float:
        """Current tempo in BPM."""
        return self._tempo

    def set_tempo(self, bpm: float) -> None:
        """Update metronome tempo.

        Args:
            bpm: Tempo in beats per minute (40-300)
        """
        self._tempo = max(40.0, min(300.0, bpm))

    def start(self) -> None:
        """Start the metronome click track.

        Uses ThreadManager's single-spawn guard to prevent thread leaks.
        """
        if self._active:
            return
        self._active = True
        self._thread_manager.start("metronome", target=self._click_loop)
        logger.info("Metronome started at %d BPM", int(self._tempo))

    def stop(self) -> None:
        """Stop the metronome click track."""
        self._active = False
        self._thread_manager.stop("metronome", timeout=1.0)
        logger.info("Metronome stopped")

    def _click_loop(self) -> None:
        """Background click loop.

        Sends a short percussive click on channel 9 (standard MIDI
        percussion channel) at the configured beat interval.
        """
        stop_event = self._thread_manager.create_event("metronome")
        note = 37  # Standard click (rimshot)
        velocity = 80
        note_duration = min(0.05, (60.0 / self._tempo) * 0.1)

        while self._active and not stop_event.is_set():
            beat_interval = 60.0 / self._tempo
            try:
                # Note on
                on_msg = MIDIMessage(
                    type="note_on",
                    channel=9,
                    data={"note": note, "velocity": velocity},
                    timestamp=0,
                )
                self._sink.send(on_msg)

                # Brief note duration for audible click
                if stop_event.wait(note_duration):
                    break

                # Note off
                off_msg = MIDIMessage(
                    type="note_off",
                    channel=9,
                    data={"note": note, "velocity": 0},
                    timestamp=0,
                )
                self._sink.send(off_msg)

            except Exception as e:
                logger.error("Metronome click error: %s", e)

            # Wait for remainder of beat
            remaining = beat_interval - note_duration
            if remaining > 0 and not stop_event.is_set():
                if stop_event.wait(remaining):
                    break
