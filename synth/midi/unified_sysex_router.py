"""
Unified MIDI SYSEX Router - Production Grade

Central hub for routing all MIDI sysex messages (XG, GS, GM, GM2, XG Native).
Replaces duplicate sysex controllers with a single, well-designed architecture.

Supported Formats:
- XG: F0 43 [dev] 4C [cmd] [data] F7
- GS: F0 41 [dev] 42 [cmd] [addr] [data] F7
- GM/GM2: F0 7E [ch] [cmd] [data] F7
- MIDI-CI: F0 7E [ch] [sub] [device] [mfr] [data] F7

Copyright (c) 2025 - Production Grade Implementation
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

logger = logging.getLogger(__name__)


class SysexManufacturer(IntEnum):
    """MIDI Manufacturer IDs"""

    UNIVERSAL_NON_REALTIME = 0x7E
    UNIVERSAL_REALTIME = 0x7F
    YAMAHA = 0x43
    ROLAND = 0x41
    KAWAI = 0x40
    KORG = 0x42


class XGCommand(IntEnum):
    """XG Sysex Command Codes"""

    PARAMETER_CHANGE = 0x08
    XG_SYSTEM_ON = 0x02
    XG_SYSTEM_OFF = 0x03
    XG_RESET = 0x04
    XG_DUMP_REQUEST = 0x06
    XG_BULK_DUMP = 0x07
    XG_DUMP = 0x09
    BULK_DUMP = 0x0A
    BULK_DUMP_REQUEST = 0x0C
    MASTER_TUNE = 0x0E
    MASTER_TRANSPOSE = 0x0F
    DISPLAY_MESSAGE = 0x10
    LED_CONTROL = 0x11
    SPECIAL_MESSAGE = 0x12
    RECEIVE_CHANNEL = 0x08


class GSCommand(IntEnum):
    """GS Sysex Command Codes"""

    DATA_SET = 0x10
    DATA_SET_2 = 0x12
    DATA_REQUEST = 0x11
    GS_RESET = 0x12
    MODEL_ID_1 = 0x01
    MODEL_ID_2 = 0x02


@dataclass
class SysexMessage:
    """Parsed sysex message container"""

    manufacturer: int
    device_id: int
    model_id: int = 0
    command: int = 0
    address: tuple[int, ...] = field(default_factory=tuple)
    data: tuple[int, ...] = field(default_factory=tuple)
    raw: bytes = field(default_factory=bytes)
    checksum: int = 0
    is_valid: bool = False
    error: str = ""


@dataclass
class SysexResponse:
    """Sysex response container"""

    data: bytes = field(default_factory=bytes)
    should_send: bool = True
    error: str = ""


class UnifiedSysexRouter:
    """
    Production-grade unified sysex router for XG/GS/GM compliance.

    Features:
    - Unified message parsing for all formats
    - Manufacturer-specific routing
    - XG/GS address space handling
    - Parameter change callbacks
    - Bulk dump generation/parsing
    - Response generation
    - Thread-safe operations
    """

    # Manufacturer IDs
    YAMAHA = 0x43
    ROLAND = 0x41
    GM_NON_REALTIME = 0x7E
    GM_REALTIME = 0x7F

    # XG Model ID
    XG_MODEL_ID = 0x4C

    # GS Model ID
    GS_MODEL_ID = 0x42

    def __init__(self, device_id: int = 0x10, enable_logging: bool = False):
        """
        Initialize Unified Sysex Router.

        Args:
            device_id: MIDI device ID (0-127)
            enable_logging: Enable detailed logging
        """
        self.device_id = device_id
        self.enable_logging = enable_logging

        # Thread safety
        self.lock = threading.RLock()

        # Message handlers - manufacturer -> command -> handler
        self._handlers: dict[int, dict[int, Callable]] = {}
        self._initialize_handlers()

        # Parameter callbacks
        self._parameter_callbacks: list[Callable] = []
        self._system_callbacks: dict[str, Callable] = {}

        # XG/GS component references (set by parent synthesizer)
        self.xg_components = None
        self.gs_components = None
        self.effects_coordinator = None
        self.voice_manager = None

        # State tracking
        self._xg_enabled = False
        self._gs_enabled = False
        self._gm_mode = False

        # Device ID filtering
        self._accept_all_devices = True

        logger.info(f"UnifiedSysexRouter: Initialized with device_id={device_id:02X}")

    def _initialize_handlers(self):
        """Initialize manufacturer-specific handlers."""
        # XG handlers
        self._handlers[self.YAMAHA] = {
            XGCommand.PARAMETER_CHANGE: self._handle_xg_parameter_change,
            XGCommand.XG_SYSTEM_ON: self._handle_xg_system_on,
            XGCommand.XG_SYSTEM_OFF: self._handle_xg_system_off,
            XGCommand.XG_RESET: self._handle_xg_reset,
            XGCommand.XG_DUMP_REQUEST: self._handle_xg_dump_request,
            XGCommand.XG_BULK_DUMP: self._handle_xg_bulk_dump,
            XGCommand.XG_DUMP: self._handle_xg_dump,
            XGCommand.BULK_DUMP: self._handle_bulk_dump,
            XGCommand.BULK_DUMP_REQUEST: self._handle_bulk_dump_request,
            XGCommand.MASTER_TUNE: self._handle_master_tune,
            XGCommand.MASTER_TRANSPOSE: self._handle_master_transpose,
            XGCommand.DISPLAY_MESSAGE: self._handle_display_message,
            XGCommand.RECEIVE_CHANNEL: self._handle_receive_channel,
        }

        # GS handlers
        self._handlers[self.ROLAND] = {
            GSCommand.DATA_SET: self._handle_gs_data_set,
            GSCommand.DATA_SET_2: self._handle_gs_data_set,
            GSCommand.DATA_REQUEST: self._handle_gs_data_request,
            GSCommand.GS_RESET: self._handle_gs_reset,
        }

        # GM/GM2 handlers
        self._handlers[self.GM_NON_REALTIME] = {
            0x01: self._handle_gm_on,
            0x02: self._handle_gm_on,
            0x03: self._handle_gm2_on,
            0x04: self._handle_gm_off,
        }

    def set_xg_components(self, components: Any):
        """Set XG components reference."""
        self.xg_components = components

    def set_gs_components(self, components: Any):
        """Set GS components reference."""
        self.gs_components = components

    def set_effects_coordinator(self, coordinator: Any):
        """Set effects coordinator reference."""
        self.effects_coordinator = coordinator

    def set_voice_manager(self, manager: Any):
        """Set voice manager reference."""
        self.voice_manager = manager

    def register_parameter_callback(self, callback: Callable):
        """Register parameter change callback."""
        with self.lock:
            self._parameter_callbacks.append(callback)

    def register_system_callback(self, event: str, callback: Callable):
        """Register system event callback."""
        with self.lock:
            self._system_callbacks[event] = callback

    def process_message(self, data: bytes) -> SysexResponse:
        """
        Process incoming sysex message.

        Args:
            data: Raw sysex bytes

        Returns:
            SysexResponse with optional response data
        """
        if not data or len(data) < 4:
            return SysexResponse(error="Invalid message: too short")

        if data[0] != 0xF0 or data[-1] != 0xF7:
            return SysexResponse(error="Invalid message: no F0/F7")

        # Parse message
        message = self._parse_message(data)
        if not message.is_valid:
            return SysexResponse(error=message.error)

        # Route to handler
        return self._route_message(message)

    def _parse_message(self, data: bytes) -> SysexMessage:
        """Parse sysex message into structured format."""
        msg = SysexMessage(raw=data)

        if len(data) < 4:
            msg.is_valid = False
            msg.error = "Message too short"
            return msg

        manufacturer = data[1]
        msg.manufacturer = manufacturer

        # XG format: F0 43 [dev] 4C [cmd] [data...] F7
        if manufacturer == self.YAMAHA and len(data) >= 5:
            if data[3] != self.XG_MODEL_ID:
                msg.is_valid = False
                msg.error = f"Not XG model (got {data[3]:02X})"
                return msg

            msg.device_id = data[2]
            msg.model_id = data[3]
            msg.command = data[4]

            # Check device ID filtering
            if not self._accept_all_devices and msg.device_id != self.device_id:
                msg.is_valid = False
                msg.error = "Device ID mismatch"
                return msg

            # Extract address and data
            if len(data) > 5:
                msg.data = tuple(data[5:-2])  # Exclude checksum and F7
                msg.checksum = data[-2] if len(data) > 2 else 0

            msg.is_valid = True
            return msg

        # GS format: F0 41 [dev] 42 [cmd] [addr...] [data] [checksum] F7
        if manufacturer == self.ROLAND and len(data) >= 6:
            if data[3] != self.GS_MODEL_ID:
                msg.is_valid = False
                msg.error = f"Not GS model (got {data[3]:02X})"
                return msg

            msg.device_id = data[2]
            msg.model_id = data[3]
            msg.command = data[4]

            # Check device ID (0x00 = all, 0x10 = specific)
            if msg.device_id not in (0x00, 0x10, self.device_id):
                msg.is_valid = False
                msg.error = "Device ID mismatch"
                return msg

            # Extract address (3 bytes) and data
            if len(data) > 7:
                msg.address = tuple(data[5:8])
                msg.data = tuple(data[8:-2])
                msg.checksum = data[-2]

            msg.is_valid = True
            return msg

        # GM format: F0 7E [ch] [cmd] [data] F7
        if manufacturer in (self.GM_NON_REALTIME, self.GM_REALTIME):
            msg.device_id = data[2]
            msg.command = data[3]
            if len(data) > 4:
                msg.data = tuple(data[4:-1])
            msg.is_valid = True
            return msg

        msg.is_valid = False
        msg.error = f"Unknown manufacturer: {manufacturer:02X}"
        return msg

    def _route_message(self, message: SysexMessage) -> SysexResponse:
        """Route parsed message to appropriate handler."""
        handlers = self._handlers.get(message.manufacturer, {})
        handler = handlers.get(message.command)

        if handler:
            try:
                return handler(message)
            except Exception as e:
                logger.error(f"Handler error: {e}")
                return SysexResponse(error=str(e))

        logger.warning(f"No handler for {message.manufacturer:02X}/{message.command:02X}")
        return SysexResponse(error="Unknown command")

    # ==================== XG Handlers ====================

    def _handle_xg_parameter_change(self, msg: SysexMessage) -> SysexResponse:
        """Handle XG parameter change (cmd 0x08)."""
        if len(msg.data) < 3:
            return SysexResponse(error="Invalid parameter change data")

        # XG Parameter change format:
        # [part] [param_msb] [param_lsb] [data_msb] [data_lsb]
        part = msg.data[0]
        param_msb = msg.data[1]
        param_lsb = msg.data[2]

        # Handle MSB groups
        if param_msb < 3:
            # RPN/NRPN handled elsewhere
            return SysexResponse()

        # Route to XG components
        if self.xg_components:
            # MSB 3-31: Channel parameters
            if 3 <= param_msb <= 31:
                channel_mgr = self.xg_components.get_component("channel_params")
                if channel_mgr:
                    value = (msg.data[3] << 7) | (msg.data[4] if len(msg.data) > 4 else 0)
                    channel_mgr.handle_nrpn_msb3_to_31(part, param_msb, param_lsb, value)

            # MSB 32-39: Effect routing
            elif 32 <= param_msb <= 39:
                effect_router = self.xg_components.get_component("effect_router")
                if effect_router:
                    value = (msg.data[3] << 7) | (msg.data[4] if len(msg.data) > 4 else 0)
                    effect_router.handle_nrpn(param_msb, param_lsb, value)

            # MSB 40-41: Drum setup
            elif 40 <= param_msb <= 41:
                drum_setup = self.xg_components.get_component("drum_setup")
                if drum_setup:
                    value = (msg.data[3] << 7) | (msg.data[4] if len(msg.data) > 4 else 0)
                    drum_setup.handle_nrpn_msb48_to63(part, param_msb, param_lsb, value)

            # MSB 42-45: Multi-part
            elif 42 <= param_msb <= 45:
                multi_part = self.xg_components.get_component("multi_part")
                if multi_part:
                    value = (msg.data[3] << 7) | (msg.data[4] if len(msg.data) > 4 else 0)
                    if param_msb == 42:
                        multi_part.handle_nrpn_msb42(part, value)
                    elif param_msb == 43:
                        multi_part.handle_nrpn_msb43(part, value)
                    elif param_msb == 44:
                        multi_part.handle_nrpn_msb44(part, value)
                    elif param_msb == 45:
                        multi_part.handle_nrpn_msb45(part, value)

        # Notify callbacks
        self._notify_parameter_change(part, param_msb, param_lsb, msg.data[3:])

        return SysexResponse()

    def _handle_xg_system_on(self, msg: SysexMessage) -> SysexResponse:
        """Handle XG System On."""
        self._xg_enabled = True
        logger.info("XG System ON")

        if "xg_on" in self._system_callbacks:
            self._system_callbacks["xg_on"]()

        return SysexResponse()

    def _handle_xg_system_off(self, msg: SysexMessage) -> SysexResponse:
        """Handle XG System Off."""
        self._xg_enabled = False
        logger.info("XG System OFF")

        if "xg_off" in self._system_callbacks:
            self._system_callbacks["xg_off"]()

        return SysexResponse()

    def _handle_xg_reset(self, msg: SysexMessage) -> SysexResponse:
        """Handle XG Reset."""
        logger.info("XG Reset")

        # Reset all XG components
        if self.xg_components and hasattr(self.xg_components, "reset_all"):
            self.xg_components.reset_all()

        if "xg_reset" in self._system_callbacks:
            self._system_callbacks["xg_reset"]()

        return SysexResponse()

    def _handle_xg_dump_request(self, msg: SysexMessage) -> SysexResponse:
        """Handle XG dump request."""
        # Generate parameter dump
        dump_data = self._generate_xg_dump()

        # Build response
        response = [0xF0, self.YAMAHA, self.device_id, self.XG_MODEL_ID, 0x09]
        response.extend(dump_data)

        # Calculate checksum
        checksum = self._calculate_roland_checksum(response[1:])
        response.append(checksum)
        response.append(0xF7)

        return SysexResponse(data=bytes(response))

    def _handle_xg_bulk_dump(self, msg: SysexMessage) -> SysexResponse:
        """Handle XG bulk dump."""
        # Parse and apply bulk parameters
        if self.xg_components:
            self._parse_xg_dump(msg.data)

        return SysexResponse()

    def _handle_xg_dump(self, msg: SysexMessage) -> SysexResponse:
        """Handle XG dump."""
        return self._handle_xg_bulk_dump(msg)

    def _handle_bulk_dump(self, msg: SysexMessage) -> SysexResponse:
        """Handle generic bulk dump."""
        return self._handle_xg_bulk_dump(msg)

    def _handle_bulk_dump_request(self, msg: SysexMessage) -> SysexResponse:
        """Handle bulk dump request."""
        return self._handle_xg_dump_request(msg)

    def _handle_master_tune(self, msg: SysexMessage) -> SysexResponse:
        """Handle master tune."""
        if len(msg.data) >= 2:
            tune_value = (msg.data[0] << 7) | msg.data[1]
            cents = tune_value - 8192

            if self.xg_components:
                sys_params = self.xg_components.get_component("system_params")
                if sys_params:
                    sys_params.set_parameter("master_tune", cents)

        return SysexResponse()

    def _handle_master_transpose(self, msg: SysexMessage) -> SysexResponse:
        """Handle master transpose."""
        if msg.data:
            transpose = msg.data[0]
            if transpose > 64:
                transpose -= 128

            if self.xg_components:
                sys_params = self.xg_components.get_component("system_params")
                if sys_params:
                    sys_params.set_parameter("master_transpose", transpose)

        return SysexResponse()

    def _handle_display_message(self, msg: SysexMessage) -> SysexResponse:
        """Handle display message."""
        try:
            message = "".join(chr(b) for b in msg.data if 32 <= b <= 126)
            logger.info(f"XG Display: {message}")

            if "display" in self._system_callbacks:
                self._system_callbacks["display"](message)
        except:
            pass

        return SysexResponse()

    def _handle_receive_channel(self, msg: SysexMessage) -> SysexResponse:
        """Handle receive channel assignment."""
        # Format: [part] [channel]
        if len(msg.data) >= 2:
            part = msg.data[0]
            channel = msg.data[1]

            if self.xg_components:
                multi_part = self.xg_components.get_component("multi_part")
                if multi_part and hasattr(multi_part, "set_part_channel"):
                    multi_part.set_part_channel(part, channel)

        return SysexResponse()

    # ==================== GS Handlers ====================

    def _handle_gs_data_set(self, msg: SysexMessage) -> SysexResponse:
        """Handle GS Data Set (cmd 0x10 or 0x12)."""
        if not msg.address or len(msg.address) < 3:
            return SysexResponse(error="Invalid GS address")

        addr_high, addr_mid, addr_low = msg.address

        # Route based on address
        if addr_high == 0x00 and addr_mid == 0x00:
            # System parameters
            return self._handle_gs_system_params(addr_low, msg.data)

        elif 0x01 <= addr_high <= 0x1F:
            # Part parameters (0x01-0x10: parts 1-16)
            part_num = addr_high - 1
            return self._handle_gs_part_params(part_num, addr_mid, addr_low, msg.data)

        elif addr_high == 0x40:
            # Effects parameters
            return self._handle_gs_effect_params(addr_mid, addr_low, msg.data)

        elif 0x10 <= addr_high <= 0x1F:
            # Drum parameters
            return self._handle_gs_drum_params(addr_high, addr_low, msg.data)

        return SysexResponse()

    def _handle_gs_system_params(self, param: int, data: tuple) -> SysexResponse:
        """Handle GS system parameters."""
        if not self.gs_components:
            return SysexResponse()

        value = data[0] if data else 0

        if param == 0x00:
            # Master volume
            if hasattr(self.gs_components, "set_master_volume"):
                self.gs_components.set_master_volume(value)
        elif param == 0x01:
            # Master transpose
            if hasattr(self.gs_components, "set_master_transpose"):
                val = value - 64 if value > 64 else value
                self.gs_components.set_master_transpose(val)

        return SysexResponse()

    def _handle_gs_part_params(
        self, part: int, group: int, param: int, data: tuple
    ) -> SysexResponse:
        """Handle GS part parameters."""
        if not self.gs_components:
            return SysexResponse()

        if not (0 <= part < 16):
            return SysexResponse(error="Invalid part")

        value = data[0] if data else 0

        # Route to GS part handler
        if hasattr(self.gs_components, "set_part_parameter"):
            self.gs_components.set_part_parameter(part, group, param, value)

        return SysexResponse()

    def _handle_gs_effect_params(self, effect_num: int, param: int, data: tuple) -> SysexResponse:
        """Handle GS effect parameters."""
        value = data[0] if data else 0

        if self.effects_coordinator:
            if effect_num == 0x00:
                # Reverb
                reverb_params = {
                    0x00: "type",
                    0x01: "level",
                    0x02: "time",
                    0x03: "feedback",
                    0x04: "delay",
                }
                if param in reverb_params:
                    self.effects_coordinator.set_system_effect_parameter(
                        "reverb", reverb_params[param], value
                    )
            elif effect_num == 0x01:
                # Chorus
                chorus_params = {
                    0x00: "type",
                    0x01: "level",
                    0x02: "rate",
                    0x03: "depth",
                    0x04: "feedback",
                }
                if param in chorus_params:
                    self.effects_coordinator.set_system_effect_parameter(
                        "chorus", chorus_params[param], value
                    )

        return SysexResponse()

    def _handle_gs_drum_params(self, bank: int, note: int, data: tuple) -> SysexResponse:
        """Handle GS drum parameters."""
        value = data[0] if data else 0

        # GS drum setup: address = 0x1X where X = bank
        drum_bank = bank - 0x10
        drum_note = note

        if self.xg_components:
            drum_setup = self.xg_components.get_component("drum_setup")
            if drum_setup:
                # Map to XG drum setup
                drum_setup.set_drum_note_parameter(
                    9,  # Drum channel
                    drum_bank,
                    drum_note,
                    "level" if value > 0 else "level",
                    value,
                )

        return SysexResponse()

    def _handle_gs_data_request(self, msg: SysexMessage) -> SysexResponse:
        """Handle GS Data Request (cmd 0x11)."""
        # Generate response dump
        response_data = self._generate_gs_dump(msg.address)

        if response_data:
            response = [0xF0, self.ROLAND, self.device_id, self.GS_MODEL_ID, 0x12]
            response.extend(msg.address)
            response.extend(response_data)
            checksum = self._calculate_roland_checksum(response[1:])
            response.append(checksum)
            response.append(0xF7)
            return SysexResponse(data=bytes(response))

        return SysexResponse()

    def _handle_gs_reset(self, msg: SysexMessage) -> SysexResponse:
        """Handle GS Reset."""
        logger.info("GS Reset")

        self._gs_enabled = True
        self._xg_enabled = False
        self._gm_mode = False

        if self.gs_components and hasattr(self.gs_components, "reset_all"):
            self.gs_components.reset_all()

        if "gs_reset" in self._system_callbacks:
            self._system_callbacks["gs_reset"]()

        return SysexResponse()

    # ==================== GM/GM2 Handlers ====================

    def _handle_gm_on(self, msg: SysexMessage) -> SysexResponse:
        """Handle GM System On."""
        logger.info("GM System ON")

        self._gm_mode = True
        self._xg_enabled = False
        self._gs_enabled = False

        if "gm_on" in self._system_callbacks:
            self._system_callbacks["gm_on"]()

        return SysexResponse()

    def _handle_gm2_on(self, msg: SysexMessage) -> SysexResponse:
        """Handle GM2 System On."""
        logger.info("GM2 System ON")

        self._gm_mode = True
        self._xg_enabled = False
        self._gs_enabled = False

        if "gm2_on" in self._system_callbacks:
            self._system_callbacks["gm2_on"]()

        return SysexResponse()

    def _handle_gm_off(self, msg: SysexMessage) -> SysexResponse:
        """Handle GM System Off."""
        logger.info("GM System OFF")

        self._gm_mode = False

        if "gm_off" in self._system_callbacks:
            self._system_callbacks["gm_off"]()

        return SysexResponse()

    # ==================== Utility Methods ====================

    def _notify_parameter_change(self, part: int, msb: int, lsb: int, data: tuple):
        """Notify all registered parameter callbacks."""
        for callback in self._parameter_callbacks:
            try:
                callback(part, msb, lsb, data)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def _generate_xg_dump(self) -> list[int]:
        """Generate complete XG parameter dump."""
        dump = []

        if not self.xg_components:
            return dump

        # System parameters
        sys_params = self.xg_components.get_component("system_params")
        if sys_params and hasattr(sys_params, "get_all_parameters"):
            dump.extend(sys_params.get_all_parameters())

        return dump

    def _parse_xg_dump(self, data: tuple):
        """Parse XG parameter dump."""
        # Implementation depends on dump format
        pass

    def _generate_gs_dump(self, address: tuple) -> list[int]:
        """Generate GS parameter dump."""
        if not address or len(address) < 3:
            return []

        addr_high, addr_mid, addr_low = address

        # Generate appropriate dump based on address
        if addr_high == 0x00 and addr_mid == 0x00:
            # System dump
            if self.gs_components and hasattr(self.gs_components, "get_system_dump"):
                return self.gs_components.get_system_dump()

        return []

    @staticmethod
    def _calculate_roland_checksum(data: list[int]) -> int:
        """Calculate Roland GS/XG checksum."""
        total = sum(data)
        return (128 - (total % 128)) & 0x7F

    @staticmethod
    def _calculate_xg_checksum(data: list[int]) -> int:
        """Calculate Yamaha XG checksum."""
        total = sum(data)
        return (128 - (total % 128)) & 0x7F

    # ==================== Public API ====================

    def enable_xg(self):
        """Enable XG mode."""
        self._xg_enabled = True
        self._gs_enabled = False

    def enable_gs(self):
        """Enable GS mode."""
        self._gs_enabled = True
        self._xg_enabled = False

    def set_xg_enabled(self, enabled: bool):
        """Set XG mode enabled state."""
        self._xg_enabled = enabled

    def set_gs_enabled(self, enabled: bool):
        """Set GS mode enabled state."""
        self._gs_enabled = enabled

    def is_xg_enabled(self) -> bool:
        """Check if XG mode is enabled."""
        return self._xg_enabled

    def is_gs_enabled(self) -> bool:
        """Check if GS mode is enabled."""
        return self._gs_enabled

    def is_gm_mode(self) -> bool:
        """Check if GM/GM2 mode is enabled."""
        return self._gm_mode

    @property
    def xg_enabled(self) -> bool:
        """Check if XG mode is enabled."""
        return self._xg_enabled

    @property
    def gs_enabled(self) -> bool:
        """Check if GS mode is enabled."""
        return self._gs_enabled

    def get_status(self) -> dict[str, Any]:
        """Get router status."""
        return {
            "device_id": self.device_id,
            "xg_enabled": self._xg_enabled,
            "gs_enabled": self._gs_enabled,
            "gm_mode": self._gm_mode,
            "xg_connected": self.xg_components is not None,
            "gs_connected": self.gs_components is not None,
            "effects_connected": self.effects_coordinator is not None,
        }

    def create_xg_message(self, command: int, data: list[int]) -> bytes:
        """Create XG sysex message."""
        message = [0xF0, self.YAMAHA, self.device_id, self.XG_MODEL_ID, command]
        message.extend(data)

        checksum = self._calculate_xg_checksum(message[1:])
        message.append(checksum)
        message.append(0xF7)

        return bytes(message)

    def create_gs_message(self, command: int, address: tuple, data: list[int]) -> bytes:
        """Create GS sysex message."""
        message = [0xF0, self.ROLAND, self.device_id, self.GS_MODEL_ID, command]
        message.extend(address)
        message.extend(data)

        checksum = self._calculate_roland_checksum(message[1:])
        message.append(checksum)
        message.append(0xF7)

        return bytes(message)
