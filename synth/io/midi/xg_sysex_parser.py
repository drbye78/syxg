"""
Spec-Correct XG/GS SysEx Parser — per Yamaha XG Specification v2.0.

Real XG SysEx format (address-based, no "command byte"):
    F0 43 1n 4C aa aa aa [dd ...] cc F7
         │  │  │  └─ 3-byte address (high, mid, low)
         │  │  └──── Model ID (0x4C = XG)
         │  └─────── Device ID (0x1n, n=0-15)
         └────────── Manufacturer ID (0x43 = Yamaha)

Real GS SysEx format:
    F0 41 [dev] 42 aa aa aa [dd ...] cc F7

Checksum: 128 - (sum(address) + sum(data)) % 128
    Covers address + data only, NOT manufacturer/device/model ID.

Replaces the previous UnifiedSysexRouter which used an invented
"command byte" format and calculated checksums incorrectly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# Manufacturer and Model IDs
# ============================================================================


class SysexManufacturer(IntEnum):
    UNIVERSAL_NON_REALTIME = 0x7E
    UNIVERSAL_REALTIME = 0x7F
    YAMAHA = 0x43
    ROLAND = 0x41
    KAWAI = 0x40
    KORG = 0x42


XG_MODEL_ID = 0x4C
GS_MODEL_ID = 0x42


# ============================================================================
# Message types
# ============================================================================


@dataclass(slots=True)
class SysexMessage:
    """Parsed SysEx message with spec-correct address and checksum."""

    manufacturer: int = 0
    device_id: int = 0
    model_id: int = 0
    address: tuple[int, int, int] = field(default_factory=lambda: (0, 0, 0))
    data: tuple[int, ...] = field(default_factory=tuple)
    raw: bytes = field(default_factory=bytes)
    checksum: int = 0
    is_valid: bool = False
    error: str = ""


# ============================================================================
# Address routing — maps address patterns to semantic operations
# ============================================================================


# Address prefix → routing destination
ADDRESS_ROUTING = {
    # System parameters (0x00 0x00 xx)
    (0x00, 0x00): "system",
    # Multi-part parameters (0x08 nn pp): part nn, parameter pp
    (0x08,): "part",
    # Drum setup (0x30 nn dd): note nn, parameter dd
    (0x30,): "drum",
    # Multi EQ (0x02 0x01 xx)
    (0x02, 0x01): "eq",
    # Effect 1 (0x02 0x10 xx)
    (0x02, 0x10): "effect1",
    # Effect 2 (0x02 0x11 xx)
    (0x02, 0x11): "effect2",
    # Effect 3 (0x02 0x12 xx)
    (0x02, 0x12): "effect3",
}

# Known system addresses
SYSTEM_ADDRESSES: dict[tuple[int, int, int], str] = {
    (0x00, 0x00, 0x00): "master_tune_msb",
    (0x00, 0x00, 0x01): "master_tune_lsb",
    (0x00, 0x00, 0x02): "master_volume",
    (0x00, 0x00, 0x04): "master_attenuator",
    (0x00, 0x00, 0x05): "master_transpose",
    (0x00, 0x00, 0x06): "drum_setup_reset",
    (0x00, 0x00, 0x7D): "all_parameter_reset",
    (0x00, 0x00, 0x7E): "xg_system_off",
    (0x00, 0x00, 0x7F): "xg_system_on",
}


# ============================================================================
# Parser
# ============================================================================


class XGSysexParser:
    """Spec-correct XG/GS SysEx parser.

    Parses messages according to Yamaha XG Specification v2.0:
    - Uses 3-byte address format (no invented "command byte")
    - Validates checksums over address + data only
    - Routes messages based on address prefix
    """

    def __init__(self, device_id: int = 0x10):
        """Initialize the parser.

        Args:
            device_id: MIDI device ID (0-127).
        """
        self.device_id = device_id
        self._accept_all_devices = True
        self._parameter_callbacks: list = []
        self._system_callbacks: dict[str, list] = {}

        # Component references
        self.xg_components: Any = None
        self.gs_components: Any = None

    # ── Parsing ──

    def parse(self, message: bytes) -> SysexMessage:
        """Parse a SysEx message into a SysexMessage.

        Returns a SysexMessage with is_valid=False for unparseable messages.
        """
        msg = SysexMessage(raw=message)

        if len(message) < 6:
            msg.error = "Message too short for SysEx"
            return msg

        if message[0] != 0xF0 or message[-1] != 0xF7:
            msg.error = "Missing SysEx start/end markers"
            return msg

        msg.manufacturer = message[1]

        # Universal SysEx (0x7E / 0x7F)
        if msg.manufacturer in (SysexManufacturer.UNIVERSAL_NON_REALTIME,
                                 SysexManufacturer.UNIVERSAL_REALTIME):
            return self._parse_universal(message, msg)

        # Yamaha XG: F0 43 1n 4C ...
        if msg.manufacturer == SysexManufacturer.YAMAHA and len(message) >= 7:
            msg.device_id = message[2]
            msg.model_id = message[3]
            if msg.model_id == XG_MODEL_ID:
                return self._parse_xg(message, msg)

        # Roland GS: F0 41 xx 42 ...
        if msg.manufacturer == SysexManufacturer.ROLAND and len(message) >= 7:
            msg.device_id = message[2]
            msg.model_id = message[3]
            if msg.model_id == GS_MODEL_ID:
                return self._parse_gs(message, msg)

        msg.error = f"Unknown manufacturer/model: {msg.manufacturer:02X}/{msg.model_id:02X}"
        return msg

    def _parse_xg(self, raw: bytes, msg: SysexMessage) -> SysexMessage:
        """Parse XG SysEx message: F0 43 [dev] 4C [addr_H] [addr_M] [addr_L] [data...] [cksum] F7"""
        if len(raw) < 9:  # need at least address (3) + checksum (1) + F7 (1) = no data
            msg.error = "XG message too short"
            return msg

        # Address: bytes 4,5,6
        addr_h = raw[4]
        addr_m = raw[5]
        addr_l = raw[6]
        msg.address = (addr_h, addr_m, addr_l)

        # Data: bytes 7 to -2 (exclude checksum and F7)
        if len(raw) > 9:
            msg.data = tuple(raw[7:-2])
        else:
            msg.data = ()

        # Checksum: second-to-last byte
        msg.checksum = raw[-2]

        # Validate checksum
        expected = self.calculate_checksum(msg.address, msg.data)
        if msg.checksum != expected:
            msg.error = f"Checksum mismatch: got {msg.checksum:02X}, expected {expected:02X}"
            return msg

        msg.is_valid = True
        return msg

    def _parse_gs(self, raw: bytes, msg: SysexMessage) -> SysexMessage:
        """Parse GS SysEx message: F0 41 [dev] 42 [addr_H] [addr_M] [addr_L] [data...] [cksum] F7"""
        # Same address format as XG
        return self._parse_xg(raw, msg)

    def _parse_universal(self, raw: bytes, msg: SysexMessage) -> SysexMessage:
        """Parse universal SysEx (GM/GM2/MIDI-CI)."""
        msg.is_valid = True
        if len(raw) >= 6:
            msg.device_id = raw[2] if len(raw) > 2 else 0
            msg.model_id = raw[3] if len(raw) > 3 else 0
            if len(raw) > 5:
                msg.data = tuple(raw[4:-1])
        return msg

    # ── Building ──

    @staticmethod
    def build_xg(address: tuple[int, int, int], data: bytes = b"",
                  device_id: int = 0x10) -> bytes:
        """Build a spec-correct XG SysEx message."""
        addr_h, addr_m, addr_l = address
        message = bytearray([0xF0, 0x43, device_id, XG_MODEL_ID,
                              addr_h, addr_m, addr_l])
        message.extend(data)
        checksum = XGSysexParser.calculate_checksum(address, data)
        message.append(checksum)
        message.append(0xF7)
        return bytes(message)

    # ── Checksum ──

    @staticmethod
    def calculate_checksum(address: tuple[int, int, int] | tuple,
                           data: bytes | tuple) -> int:
        """Calculate XG/GS checksum: 128 - (sum(address) + sum(data)) % 128."""
        total = sum(address) + sum(data)
        return (128 - (total % 128)) & 0x7F

    # ── Routing ──

    def get_address_route(self, address: tuple[int, int, int]) -> str | None:
        """Route an address to a semantic destination.

        Returns:
            "system", "part", "drum", "eq", "effect1/2/3", or None.
        """
        # Exact match for system addresses
        if address in SYSTEM_ADDRESSES:
            return "system"

        # Prefix match for routed categories
        prefix = (address[0],)
        if prefix in ADDRESS_ROUTING:
            return ADDRESS_ROUTING[prefix]

        prefix = (address[0], address[1])
        if prefix in ADDRESS_ROUTING:
            return ADDRESS_ROUTING[prefix]

        return None

    # ── Callback dispatch ──

    def on_parameter_change(self, callback) -> None:
        """Register a callback for parameter changes."""
        self._parameter_callbacks.append(callback)

    def on_system_message(self, msg_type: str, callback) -> None:
        """Register a callback for system messages (xg_system_on, xg_system_off, etc.)."""
        if msg_type not in self._system_callbacks:
            self._system_callbacks[msg_type] = []
        self._system_callbacks[msg_type].append(callback)

    def dispatch(self, msg: SysexMessage) -> None:
        """Dispatch a parsed message to registered callbacks."""
        if not msg.is_valid:
            return

        route = self.get_address_route(msg.address)
        if route == "system":
            msg_type = SYSTEM_ADDRESSES.get(msg.address, "unknown")
            for cb in self._system_callbacks.get(msg_type, []):
                cb(msg)
            for cb in self._system_callbacks.get("system", []):
                cb(msg)

        for cb in self._parameter_callbacks:
            cb(msg)
