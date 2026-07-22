"""
Vibexg MIDI Sink — Message sink protocol for MIDI input routing

Defines a MidiMessageSink protocol that decouples MIDI input interfaces
from the workstation, enabling testability via RecordingSink.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Protocol, runtime_checkable

from synth.io.midi import MIDIMessage


@runtime_checkable
class MidiMessageSink(Protocol):
    """Protocol for objects that consume MIDI messages.

    Implemented by XGWorkstation. Can be replaced by RecordingSink in tests.
    """

    def send(self, message: MIDIMessage) -> None:
        """Process an incoming MIDI message.

        Args:
            message: The MIDI message to process
        """
        ...

    def start(self) -> None:
        """Start the sink (prepare for message processing)."""
        ...

    def stop(self) -> None:
        """Stop the sink (clean up resources)."""
        ...


class CallbackSink:
    """Adapter that wraps a plain callback as a MidiMessageSink.

    Useful for backward compatibility when a Callable[[MIDIMessage], None]
    is the only available handler.
    """

    def __init__(self, callback: Callable[[MIDIMessage], None]) -> None:
        """Initialize CallbackSink.

        Args:
            callback: Function to call with each MIDI message
        """
        self._callback = callback

    def send(self, message: MIDIMessage) -> None:
        """Forward message to wrapped callback.

        Args:
            message: MIDI message to forward
        """
        self._callback(message)

    def start(self) -> None:
        """No-op (callback has no lifecycle)."""
        pass

    def stop(self) -> None:
        """No-op (callback has no lifecycle)."""
        pass


class RecordingSink:
    """Test-friendly sink that records all received messages.

    Records all messages sent via send() for later inspection.
    Thread-safe recording via lock.
    """

    def __init__(self) -> None:
        self.messages: list[MIDIMessage] = []
        self._lock = threading.Lock()
        self._started = False

    def send(self, message: MIDIMessage) -> None:
        """Record a received message.

        Args:
            message: MIDI message to record
        """
        with self._lock:
            self.messages.append(message)

    def start(self) -> None:
        """Mark sink as started."""
        self._started = True

    def stop(self) -> None:
        """Mark sink as stopped."""
        self._started = False

    @property
    def is_started(self) -> bool:
        """Check if sink has been started."""
        return self._started

    def get_messages(self) -> list[MIDIMessage]:
        """Get a snapshot of all recorded messages.

        Returns:
            Copy of the messages list
        """
        with self._lock:
            return list(self.messages)

    def clear(self) -> None:
        """Clear all recorded messages."""
        with self._lock:
            self.messages.clear()
