"""
MIDI Port I/O - Physical and Virtual MIDI Device Support

Cross-platform MIDI port enumeration and communication.
Uses RtMidi backend by default with platform-specific fallbacks.

Example:
    >>> from synth.midi import get_input_names, open_input
    
    # List available ports
    ports = get_input_names()
    print(f"Available ports: {ports}")
    
    # Open port with callback
    def on_midi_message(msg):
        print(f"Received: {msg.type} on channel {msg.channel}")
    
    port = open_input(ports[0], callback=on_midi_message)
    
    # Keep running
    import time
    while True:
        time.sleep(1)
"""
from __future__ import annotations

from typing import Any
from collections.abc import Callable
import threading
import time
import logging

from .message import MIDIMessage
from .realtime import RealtimeParser

logger = logging.getLogger(__name__)

# Try to import rtmidi
try:
    import rtmidi
    RTMIDI_AVAILABLE = True
except ImportError:
    RTMIDI_AVAILABLE = False
    rtmidi = None
    logger.warning("rtmidi not installed - MIDI port I/O disabled. Install with: pip install rtmidi")


class MIDIBackend:
    """Abstract base class for MIDI backends."""
    
    def get_input_names(self) -> list[str]:
        raise NotImplementedError
    
    def get_output_names(self) -> list[str]:
        raise NotImplementedError
    
    def open_input(self, name: str, callback: Callable[[MIDIMessage], None]) -> MIDIInputPort:
        raise NotImplementedError
    
    def open_output(self, name: str, virtual: bool = False) -> MIDIOutputPort:
        raise NotImplementedError


class RtMidiBackend(MIDIBackend):
    """RtMidi-based backend for cross-platform MIDI I/O."""
    
    def __init__(self):
        if not RTMIDI_AVAILABLE:
            raise RuntimeError("rtmidi not installed")
        self.midi_in = rtmidi.MidiIn()
        self.midi_out = rtmidi.MidiOut()
        self._input_ports = {}  # Keep references to prevent GC
    
    def get_input_names(self) -> list[str]:
        """Get list of available MIDI input port names."""
        try:
            return list(self.midi_in.get_ports())
        except Exception as e:
            logger.error(f"Failed to get MIDI input ports: {e}")
            return []
    
    def get_output_names(self) -> list[str]:
        """Get list of available MIDI output port names."""
        try:
            return list(self.midi_out.get_ports())
        except Exception as e:
            logger.error(f"Failed to get MIDI output ports: {e}")
            return []
    
    def open_input(self, name: str, callback: Callable[[MIDIMessage], None]) -> MIDIInputPort:
        """Open a MIDI input port."""
        port = MIDIInputPort(name, self, callback)
        self._input_ports[name] = port
        return port
    
    def open_output(self, name: str, virtual: bool = False) -> MIDIOutputPort:
        """Open or create a MIDI output port."""
        return MIDIOutputPort(name, self, virtual)


class MIDIInputPort:
    """
    Represents an open MIDI input port.
    
    Receives MIDI messages from physical or virtual MIDI devices.
    Messages are delivered via callback function.
    """
    
    def __init__(self, name: str, backend: MIDIBackend, callback: Callable[[MIDIMessage], None]):
        self.name = name
        self.backend = backend
        self.callback = callback
        self.closed = False
        self._port = None
        self._parser = RealtimeParser()
        self._open()
    
    def _open(self):
        """Open the physical MIDI port."""
        if not isinstance(self.backend, RtMidiBackend):
            raise RuntimeError("Invalid backend type")
        
        # Find port index by name
        port_names = self.backend.midi_in.get_ports()
        try:
            port_index = port_names.index(self.name)
        except ValueError:
            raise ValueError(f"MIDI port not found: {self.name}. Available ports: {port_names}")
        
        # Create callback wrapper
        def rtmidi_callback(delta_time, data):
            if self.closed or not self.callback:
                return
            
            try:
                # Convert RtMidi bytes to MIDIMessage
                messages = self._parser.parse_bytes(bytes(data))
                
                for msg in messages:
                    # Add delta time to timestamp
                    if msg.timestamp is None:
                        msg.timestamp = time.time()
                    else:
                        msg.timestamp += delta_time
                    
                    self.callback(msg)
            except Exception as e:
                logger.error(f"Error processing MIDI input: {e}")
        
        # Open port and set callback
        try:
            self._port = self.backend.midi_in.open_port(port_index)
            self._port.set_callback(rtmidi_callback)
            logger.info(f"MIDI input opened: {self.name}")
        except Exception as e:
            raise RuntimeError(f"Failed to open MIDI port '{self.name}': {e}")
    
    def close(self):
        """Close the MIDI port."""
        if self._port and not self.closed:
            try:
                self._port.cancel_callback()
                self._port.close()
                logger.info(f"MIDI input closed: {self.name}")
            except Exception as e:
                logger.warning(f"Error closing MIDI port: {e}")
            finally:
                self.closed = True
                self.callback = None


class MIDIOutputPort:
    """
    Represents an open MIDI output port.
    
    Sends MIDI messages to physical or virtual MIDI devices.
    Supports both physical ports and virtual ports.
    """
    
    def __init__(self, name: str, backend: MIDIBackend, virtual: bool = False):
        self.name = name
        self.backend = backend
        self.virtual = virtual
        self.closed = False
        self._port = None
        self._open()
    
    def _open(self):
        """Open or create the MIDI port."""
        if not isinstance(self.backend, RtMidiBackend):
            raise RuntimeError("Invalid backend type")
        
        try:
            if self.virtual:
                # Create virtual port (appears as input to other apps)
                self._port = self.backend.midi_out.open_virtual_port(self.name)
                logger.info(f"Virtual MIDI output created: {self.name}")
            else:
                # Open physical port
                port_names = self.backend.midi_out.get_ports()
                try:
                    port_index = port_names.index(self.name)
                except ValueError:
                    raise ValueError(f"MIDI output port not found: {self.name}. Available ports: {port_names}")
                
                self._port = self.backend.midi_out.open_port(port_index)
                logger.info(f"MIDI output opened: {self.name}")
        except Exception as e:
            raise RuntimeError(f"Failed to open MIDI port '{self.name}': {e}")
    
    def send(self, message: MIDIMessage):
        """
        Send a MIDIMessage to the port.
        
        Args:
            message: MIDIMessage to send
        """
        if self.closed or not self._port:
            return
        
        try:
            # Convert MIDIMessage to bytes
            from .message import midimessage_to_bytes
            data = midimessage_to_bytes(message)
            
            # Send via RtMidi
            self._port.send_message(bytes(data))
        except Exception as e:
            logger.error(f"Failed to send MIDI message: {e}")
    
    def send_bytes(self, data: bytes):
        """
        Send raw MIDI bytes to the port.
        
        Args:
            data: Raw MIDI bytes
        """
        if self.closed or not self._port:
            return
        
        try:
            self._port.send_message(data)
        except Exception as e:
            logger.error(f"Failed to send MIDI bytes: {e}")
    
    def close(self):
        """Close the MIDI port."""
        if self._port and not self.closed:
            try:
                self._port.close()
                logger.info(f"MIDI output closed: {self.name}")
            except Exception as e:
                logger.warning(f"Error closing MIDI port: {e}")
            finally:
                self.closed = True


# Global backend instance
_default_backend: MIDIBackend | None = None


def _get_backend() -> MIDIBackend:
    """Get or create the default backend."""
    global _default_backend
    if _default_backend is None:
        if RTMIDI_AVAILABLE:
            _default_backend = RtMidiBackend()
        else:
            raise RuntimeError(
                "No MIDI backend available. Install rtmidi: pip install rtmidi"
            )
    return _default_backend


def _reset_backend():
    """Reset the default backend (for testing)."""
    global _default_backend
    if _default_backend:
        _default_backend = None


# High-level API (mido-compatible)
def get_input_names() -> list[str]:
    """
    Get list of available MIDI input port names.
    
    Returns:
        List of port names
    
    Raises:
        RuntimeError: If no MIDI backend is available
    
    Example:
        >>> ports = get_input_names()
        >>> print(f"Available ports: {ports}")
    """
    return _get_backend().get_input_names()


def get_output_names() -> list[str]:
    """
    Get list of available MIDI output port names.
    
    Returns:
        List of port names
    
    Raises:
        RuntimeError: If no MIDI backend is available
    
    Example:
        >>> ports = get_output_names()
        >>> print(f"Available ports: {ports}")
    """
    return _get_backend().get_output_names()


def open_input(name: str | None = None, callback: Callable[[MIDIMessage], None] | None = None) -> MIDIInputPort:
    """
    Open a MIDI input port.
    
    Args:
        name: Port name (uses first available if None)
        callback: Function to call with incoming MIDIMessage objects
    
    Returns:
        MIDIInputPort object
    
    Raises:
        RuntimeError: If no MIDI backend is available or no ports found
        ValueError: If callback is None
    
    Example:
        >>> def on_message(msg):
        ...     print(f"Received: {msg.type}")
        >>> port = open_input("USB MIDI", callback=on_message)
    """
    backend = _get_backend()
    port_names = backend.get_input_names()
    
    if name is None:
        if not port_names:
            raise RuntimeError("No MIDI input ports available")
        name = port_names[0]
        logger.info(f"No port specified, using first available: {name}")
    
    if callback is None:
        raise ValueError("callback is required for MIDI input")
    
    return backend.open_input(name, callback)


def open_output(name: str | None = None, virtual: bool = False) -> MIDIOutputPort:
    """
    Open a MIDI output port.
    
    Args:
        name: Port name (uses first available if None, ignored if virtual=True)
        virtual: If True, create a virtual port instead of opening physical port
    
    Returns:
        MIDIOutputPort object
    
    Raises:
        RuntimeError: If no MIDI backend is available or no ports found
    
    Example:
        >>> # Open physical port
        >>> port = open_output("USB MIDI")
        >>> port.send(MIDIMessage(type='note_on', channel=0, data={'note': 60, 'velocity': 80}))
        
        >>> # Create virtual port
        >>> vport = open_output("My Virtual Port", virtual=True)
    """
    backend = _get_backend()
    
    if virtual:
        if name is None:
            name = "Virtual MIDI Port"
        return backend.open_output(name, virtual=True)
    
    port_names = backend.get_output_names()
    
    if name is None:
        if not port_names:
            raise RuntimeError("No MIDI output ports available")
        name = port_names[0]
        logger.info(f"No port specified, using first available: {name}")
    
    return backend.open_output(name, virtual=False)
