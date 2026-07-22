"""
Vibexg Recorder — Recording and playback subsystem

Extracted from XGWorkstation. Manages recording state, event storage,
playback with precision timing, and MIDI file export.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from synth.io.midi import MIDIMessage

from .midi_sink import MidiMessageSink
from .threading import ThreadManager

logger = logging.getLogger(__name__)


class Recorder:
    """Recording and playback subsystem.

    Manages recording of incoming MIDI events, timed playback of
    recorded material, and export to standard MIDI file format.

    Thread-safe: recording state and event list are protected by a lock.
    """

    def __init__(
        self,
        sink: MidiMessageSink,
        thread_manager: ThreadManager,
    ) -> None:
        """Initialize Recorder.

        Args:
            sink: Message sink to send playback events through
            thread_manager: Centralized thread manager for playback thread
        """
        self._sink = sink
        self._thread_manager = thread_manager
        self._lock = threading.Lock()
        self._recorded_events: list[dict[str, Any]] = []
        self._recording_start_time: float = 0.0
        self._playing = False
        self._recording = False

    # --- Recording ---

    @property
    def is_recording(self) -> bool:
        """Check if recording is active (thread-safe)."""
        with self._lock:
            return self._recording

    @property
    def is_playing(self) -> bool:
        """Check if playback is active."""
        return self._playing

    @property
    def event_count(self) -> int:
        """Number of recorded events (thread-safe)."""
        with self._lock:
            return len(self._recorded_events)

    @property
    def events(self) -> list[dict[str, Any]]:
        """Get a snapshot of recorded events (thread-safe)."""
        with self._lock:
            return list(self._recorded_events)

    def start_recording(self) -> None:
        """Begin recording MIDI events.

        Clears any previously recorded events.
        """
        with self._lock:
            self._recording = True
            self._recording_start_time = time.time()
            self._recorded_events.clear()
        logger.info("Recording started")

    def stop_recording(self) -> int:
        """Stop recording MIDI events.

        Returns:
            Number of events recorded
        """
        with self._lock:
            self._recording = False
            count = len(self._recorded_events)
        logger.info("Recording stopped: %d events", count)
        return count

    def record_event(self, message: MIDIMessage) -> None:
        """Record a single MIDI event if recording is active.

        Thread-safe: acquires lock to append event with timestamp.

        Args:
            message: MIDI message to record
        """
        with self._lock:
            if not self._recording:
                return
            event = {
                "type": message.type,
                "channel": message.channel,
                "data": message.data.copy(),
                "timestamp": time.time() - self._recording_start_time,
            }
            self._recorded_events.append(event)

    # --- Playback ---

    def start_playback(self) -> bool:
        """Start playback of recorded events in a background thread.

        Returns:
            True if playback started, False if no events or already playing
        """
        with self._lock:
            if self._playing or not self._recorded_events:
                return False
            self._playing = True
            events_snapshot = list(self._recorded_events)

        logger.info("Playback started: %d events", len(events_snapshot))
        self._thread_manager.start(
            "playback",
            target=lambda: self._playback_loop(events_snapshot),
        )
        return True

    def stop_playback(self) -> None:
        """Stop playback."""
        self._playing = False
        self._thread_manager.stop("playback", timeout=1.0)

    def _playback_loop(self, events: list[dict[str, Any]]) -> None:
        """Background playback loop.

        Replays recorded events with original timing. Uses the
        thread manager's stop event for interruptible waits.

        Args:
            events: Snapshot of events to replay
        """
        stop_event = self._thread_manager.create_event("playback")
        try:
            start_time = time.time()
            for event in events:
                if not self._playing or stop_event.is_set():
                    break

                elapsed = time.time() - start_time
                wait_time = event["timestamp"] - elapsed
                if wait_time > 0:
                    if stop_event.wait(wait_time):
                        break

                msg = MIDIMessage(
                    type=event["type"],
                    channel=event["channel"],
                    data=event["data"],
                    timestamp=time.time(),
                )
                self._sink.send(msg)
        except Exception as e:
            logger.error("Playback error: %s", e)
        finally:
            self._playing = False
            logger.info("Playback complete")

    # --- MIDI File Export ---

    def export_midi(self, filepath: str) -> bool:
        """Export recorded events to a standard MIDI file (type 0).

        Uses synth.io.midi.MIDIFileWriter if available.

        Args:
            filepath: Output file path (.mid extension)

        Returns:
            True if export succeeded, False otherwise
        """
        try:
            from synth.io.midi.file_writer import MIDIFileWriter
        except ImportError:
            logger.warning("MIDI file export not available (MIDIFileWriter not found)")
            return False

        events = self.events
        if not events:
            logger.warning("No events to export")
            return False

        try:
            writer = MIDIFileWriter()
            for event in events:
                msg = MIDIMessage(
                    type=event["type"],
                    channel=event["channel"],
                    data=event["data"],
                    timestamp=event["timestamp"],
                )
                writer.add_event(msg)

            writer.save(filepath)
            logger.info("MIDI file exported: %s (%d events)", filepath, len(events))
            return True
        except Exception as e:
            logger.error("MIDI export failed: %s", e)
            return False
