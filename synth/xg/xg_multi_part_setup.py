"""
XG Multi-Part Setup (NRPN MSB 42-45)

Implements XG multi-part parameters for voice reserve, part mode, part level, and part pan.
Handles NRPN MSB 42-45 for complete multi-timbral XG compliance.

XG Specification Compliance:
- MSB 42: Voice Reserve (voice allocation per part: 0-128 voices)
- MSB 43: Part Mode (Single/Multi mode per part)
- MSB 44: Part Level (individual part output levels: 0-127)
- MSB 45: Part Pan (individual part stereo positioning: L64-R63)

Copyright (c) 2025
"""
from __future__ import annotations

from typing import Any
import threading
import math


class XGMultiPartSetup:
    """
    XG Multi-Part Setup (NRPN MSB 42-45)

    Handles XG multi-part parameters for complete multi-timbral operation.
    Provides voice reserve management, part mode control, and individual
    part level/pan for professional XG synthesizer operation.

    Key Features:
    - Voice reserve allocation per part (0-128 voices)
    - Part mode control (Single/Multi mode)
    - Individual part output levels (0-127)
    - Individual part stereo positioning (-64 to +63)
    - Real-time parameter updates during playback
    - Thread-safe operation for live performance
    """

    # XG Part Mode Constants
    PART_MODE_SINGLE = 0   # Single mode (mono)
    PART_MODE_MULTI = 1    # Multi mode (polyphonic)

    # XG Voice Reserve Limits
    MAX_VOICES_PER_PART = 128
    TOTAL_VOICES_AVAILABLE = 128  # Total voices in synthesizer

    def __init__(self, num_parts: int = 16):
        """
        Initialize XG Multi-Part Setup.

        Args:
            num_parts: Number of XG parts (default 16)
        """
        self.num_parts = num_parts
        self.lock = threading.RLock()

        # Voice reserve per part (MSB 42)
        self.voice_reserve = [8] * num_parts  # Default 8 voices per part

        # Part mode per part (MSB 43)
        self.part_mode = [self.PART_MODE_MULTI] * num_parts  # Default multi mode

        # Part level per part (MSB 44)
        self.part_level = [127] * num_parts  # Default max level (0-127)

        # Part pan per part (MSB 45)
        self.part_pan = [64] * num_parts  # Default center (0-127, 64=center)

        # Parameter change callback
        self.parameter_change_callback = None

        # Validate initial setup
        self._validate_voice_allocation()

        print("🎹 XG MULTI-PART SETUP: Initialized")
        print(f"   {num_parts} parts configured for XG multi-timbral operation")
        print(f"   Total voice reserve: {sum(self.voice_reserve)}/{self.TOTAL_VOICES_AVAILABLE}")

    def handle_nrpn_msb42(self, lsb: int, data_value: int) -> bool:
        """
        Handle NRPN MSB 42 (Voice Reserve) messages.

        Args:
            lsb: NRPN LSB value (0-15 for parts 0-15)
            data_value: 14-bit data value (0-16383)

        Returns:
            True if parameter was handled
        """
        with self.lock:
            if not (0 <= lsb < self.num_parts):
                return False

            # Convert 14-bit value to voice count (0-128)
            voice_count = min(data_value >> 7, self.MAX_VOICES_PER_PART)

            # Check if we exceed total available voices
            current_total = sum(self.voice_reserve)
            new_total = current_total - self.voice_reserve[lsb] + voice_count

            if new_total > self.TOTAL_VOICES_AVAILABLE:
                # Reduce allocation to fit within limits
                available_voices = self.TOTAL_VOICES_AVAILABLE - (current_total - self.voice_reserve[lsb])
                voice_count = min(voice_count, available_voices)

            self.voice_reserve[lsb] = voice_count
            self._notify_parameter_change(f'voice_reserve_part_{lsb}', voice_count)

            # Re-validate allocation
            self._validate_voice_allocation()

            return True

    def handle_nrpn_msb43(self, lsb: int, data_value: int) -> bool:
        """
        Handle NRPN MSB 43 (Part Mode) messages.

        Args:
            lsb: NRPN LSB value (0-15 for parts 0-15)
            data_value: 14-bit data value

        Returns:
            True if parameter was handled
        """
        with self.lock:
            if not (0 <= lsb < self.num_parts):
                return False

            # Convert 14-bit value to part mode (0=Single, 1=Multi)
            part_mode = 1 if (data_value >> 7) > 0 else 0

            self.part_mode[lsb] = part_mode
            mode_name = 'Single' if part_mode == self.PART_MODE_SINGLE else 'Multi'
            self._notify_parameter_change(f'part_mode_part_{lsb}', part_mode)

            return True

    def handle_nrpn_msb44(self, lsb: int, data_value: int) -> bool:
        """
        Handle NRPN MSB 44 (Part Level) messages.

        Args:
            lsb: NRPN LSB value (0-15 for parts 0-15)
            data_value: 14-bit data value (0-16383)

        Returns:
            True if parameter was handled
        """
        with self.lock:
            if not (0 <= lsb < self.num_parts):
                return False

            # Convert 14-bit value to part level (0-127)
            part_level = data_value >> 7  # Take upper 7 bits

            self.part_level[lsb] = part_level
            self._notify_parameter_change(f'part_level_part_{lsb}', part_level)

            return True

    def handle_nrpn_msb45(self, lsb: int, data_value: int) -> bool:
        """
        Handle NRPN MSB 45 (Part Pan) messages.

        Args:
            lsb: NRPN LSB value (0-15 for parts 0-15)
            data_value: 14-bit data value (0-16383)

        Returns:
            True if parameter was handled
        """
        with self.lock:
            if not (0 <= lsb < self.num_parts):
                return False

            # Convert 14-bit value to part pan (0-127, 64=center)
            part_pan = data_value >> 7  # Take upper 7 bits

            self.part_pan[lsb] = part_pan
            self._notify_parameter_change(f'part_pan_part_{lsb}', part_pan)

            return True

    def _notify_parameter_change(self, parameter_name: str, value: Any):
        """Notify parameter change callback."""
        if self.parameter_change_callback:
            self.parameter_change_callback(parameter_name, value)

    def set_parameter_change_callback(self, callback):
        """Set parameter change callback."""
        self.parameter_change_callback = callback

    def get_voice_reserve(self, part: int) -> int:
        """
        Get voice reserve for a specific part.

        Args:
            part: Part number (0-15)

        Returns:
            Voice reserve count (0-128)
        """
        with self.lock:
            if 0 <= part < self.num_parts:
                return self.voice_reserve[part]
        return 0

    def get_part_mode(self, part: int) -> int:
        """
        Get part mode for a specific part.

        Args:
            part: Part number (0-15)

        Returns:
            Part mode (0=Single, 1=Multi)
        """
        with self.lock:
            if 0 <= part < self.num_parts:
                return self.part_mode[part]
        return self.PART_MODE_MULTI

    def get_part_level(self, part: int) -> int:
        """
        Get part level for a specific part.

        Args:
            part: Part number (0-15)

        Returns:
            Part level (0-127)
        """
        with self.lock:
            if 0 <= part < self.num_parts:
                return self.part_level[part]
        return 127

    def get_part_pan(self, part: int) -> int:
        """
        Get part pan for a specific part.

        Args:
            part: Part number (0-15)

        Returns:
            Part pan (0-127, 64=center)
        """
        with self.lock:
            if 0 <= part < self.num_parts:
                return self.part_pan[part]
        return 64

    def set_voice_reserve(self, part: int, voices: int) -> bool:
        """
        Set voice reserve for a specific part.

        Args:
            part: Part number (0-15)
            voices: Number of voices to reserve (0-128)

        Returns:
            True if set successfully
        """
        voices = max(0, min(voices, self.MAX_VOICES_PER_PART))

        with self.lock:
            if not (0 <= part < self.num_parts):
                return False

            # Check total allocation
            current_total = sum(self.voice_reserve)
            new_total = current_total - self.voice_reserve[part] + voices

            if new_total > self.TOTAL_VOICES_AVAILABLE:
                return False  # Would exceed total available voices

            self.voice_reserve[part] = voices
            self._notify_parameter_change(f'voice_reserve_part_{part}', voices)
            self._validate_voice_allocation()

            return True

    def set_part_mode(self, part: int, mode: int) -> bool:
        """
        Set part mode for a specific part.

        Args:
            part: Part number (0-15)
            mode: Part mode (0=Single, 1=Multi)

        Returns:
            True if set successfully
        """
        if mode not in [self.PART_MODE_SINGLE, self.PART_MODE_MULTI]:
            return False

        with self.lock:
            if 0 <= part < self.num_parts:
                self.part_mode[part] = mode
                self._notify_parameter_change(f'part_mode_part_{part}', mode)
                return True

        return False

    def set_part_level(self, part: int, level: int) -> bool:
        """
        Set part level for a specific part.

        Args:
            part: Part number (0-15)
            level: Part level (0-127)

        Returns:
            True if set successfully
        """
        level = max(0, min(level, 127))

        with self.lock:
            if 0 <= part < self.num_parts:
                self.part_level[part] = level
                self._notify_parameter_change(f'part_level_part_{part}', level)
                return True

        return False

    def set_part_pan(self, part: int, pan: int) -> bool:
        """
        Set part pan for a specific part.

        Args:
            part: Part number (0-15)
            pan: Part pan (0-127, 64=center)

        Returns:
            True if set successfully
        """
        pan = max(0, min(pan, 127))

        with self.lock:
            if 0 <= part < self.num_parts:
                self.part_pan[part] = pan
                self._notify_parameter_change(f'part_pan_part_{part}', pan)
                return True

        return False

    def get_multi_part_status(self) -> dict[str, Any]:
        """
        Get comprehensive multi-part setup status.

        Returns:
            Dictionary with multi-part status information
        """
        with self.lock:
            status = {
                'total_parts': self.num_parts,
                'total_voice_reserve': sum(self.voice_reserve),
                'max_voice_reserve': self.TOTAL_VOICES_AVAILABLE,
                'voice_reserve_utilization': sum(self.voice_reserve) / self.TOTAL_VOICES_AVAILABLE,
                'parts': []
            }

            for part in range(self.num_parts):
                part_info = {
                    'part_number': part,
                    'voice_reserve': self.voice_reserve[part],
                    'part_mode': 'Single' if self.part_mode[part] == self.PART_MODE_SINGLE else 'Multi',
                    'part_level': self.part_level[part],
                    'part_pan': self.part_pan[part] - 64,  # Convert to -64 to +63 range
                    'part_level_db': self._level_to_db(self.part_level[part]),
                    'part_pan_position': self._pan_to_position(self.part_pan[part])
                }
                status['parts'].append(part_info)

            return status

    def _level_to_db(self, level: int) -> float:
        """Convert XG level (0-127) to dB."""
        if level == 0:
            return -float('inf')  # -∞ dB
        # Approximate conversion: 127 = 0dB, 0 = -∞dB
        return 20.0 * math.log10(level / 127.0)

    def _pan_to_position(self, pan: int) -> str:
        """Convert XG pan (0-127) to position description."""
        if pan < 32:
            return 'Hard Left'
        elif pan < 48:
            return 'Left'
        elif pan < 80:
            return 'Center'
        elif pan < 96:
            return 'Right'
        else:
            return 'Hard Right'

    def _validate_voice_allocation(self):
        """Validate and adjust voice allocation if necessary."""
        total_allocated = sum(self.voice_reserve)

        if total_allocated > self.TOTAL_VOICES_AVAILABLE:
            print(f"⚠️ XG MULTI-PART: Voice allocation exceeds total available ({total_allocated}/{self.TOTAL_VOICES_AVAILABLE})")
            print("   Reducing allocations to fit within limits...")

            # Reduce allocations proportionally
            reduction_factor = self.TOTAL_VOICES_AVAILABLE / total_allocated

            for i in range(self.num_parts):
                original = self.voice_reserve[i]
                reduced = int(original * reduction_factor)
                self.voice_reserve[i] = max(1, reduced)  # Minimum 1 voice per part

            print(f"   Adjusted allocations: {sum(self.voice_reserve)} total voices")

    def allocate_voices_for_part(self, part: int, requested_voices: int) -> int:
        """
        Allocate voices for a part based on reserve and availability.

        Args:
            part: Part number (0-15)
            requested_voices: Number of voices requested

        Returns:
            Number of voices actually allocated
        """
        with self.lock:
            if not (0 <= part < self.num_parts):
                return 0

            reserved_voices = self.voice_reserve[part]

            # In Single mode, only 1 voice is allowed regardless of reserve
            if self.part_mode[part] == self.PART_MODE_SINGLE:
                return 1

            # In Multi mode, allocate up to reserved amount
            allocated = min(requested_voices, reserved_voices)

            # Check if we have enough total voices available
            current_allocation = sum(self.voice_reserve[:part] + self.voice_reserve[part+1:])
            available_voices = self.TOTAL_VOICES_AVAILABLE - current_allocation

            allocated = min(allocated, available_voices)

            return max(1, allocated)  # Always allocate at least 1 voice

    def get_part_synthesis_parameters(self, part: int) -> dict[str, Any]:
        """
        Get synthesis-relevant parameters for a part.

        Args:
            part: Part number (0-15)

        Returns:
            Dictionary with synthesis parameters
        """
        with self.lock:
            if not (0 <= part < self.num_parts):
                return {}

            return {
                'voice_reserve': self.voice_reserve[part],
                'part_mode': self.part_mode[part],
                'part_level': self.part_level[part] / 127.0,  # Normalize to 0.0-1.0
                'part_pan': (self.part_pan[part] - 64) / 64.0,  # Normalize to -1.0 to +1.0
                'allocated_voices': self.allocate_voices_for_part(part, self.voice_reserve[part])
            }

    def reset_to_xg_defaults(self):
        """Reset all multi-part parameters to XG defaults."""
        with self.lock:
            self.voice_reserve = [8] * self.num_parts
            self.part_mode = [self.PART_MODE_MULTI] * self.num_parts
            self.part_level = [127] * self.num_parts
            self.part_pan = [64] * self.num_parts

            self._validate_voice_allocation()

        print("🎹 XG MULTI-PART SETUP: Reset to XG defaults")

    def export_setup(self) -> dict[str, Any]:
        """Export multi-part setup for serialization."""
        with self.lock:
            return {
                'voice_reserve': self.voice_reserve.copy(),
                'part_mode': self.part_mode.copy(),
                'part_level': self.part_level.copy(),
                'part_pan': self.part_pan.copy(),
                'version': '1.0'
            }

    def import_setup(self, setup_data: dict[str, Any]) -> bool:
        """Import multi-part setup from serialized data."""
        try:
            with self.lock:
                if 'voice_reserve' in setup_data and len(setup_data['voice_reserve']) == self.num_parts:
                    self.voice_reserve = setup_data['voice_reserve'].copy()
                if 'part_mode' in setup_data and len(setup_data['part_mode']) == self.num_parts:
                    self.part_mode = setup_data['part_mode'].copy()
                if 'part_level' in setup_data and len(setup_data['part_level']) == self.num_parts:
                    self.part_level = setup_data['part_level'].copy()
                if 'part_pan' in setup_data and len(setup_data['part_pan']) == self.num_parts:
                    self.part_pan = setup_data['part_pan'].copy()

                self._validate_voice_allocation()
                return True
        except Exception as e:
            print(f"❌ XG MULTI-PART: Import failed - {e}")
            return False

    def __str__(self) -> str:
        """String representation of multi-part setup."""
        status = self.get_multi_part_status()

        lines = [f"XG Multi-Part Setup ({status['total_parts']} parts):"]
        lines.append(f"Voice Reserve: {status['total_voice_reserve']}/{status['max_voice_reserve']} total")

        for part_info in status['parts'][:8]:  # Show first 8 parts
            mode = part_info['part_mode']
            reserve = part_info['voice_reserve']
            level_db = '.1f' if part_info['part_level_db'] != float('-inf') else '-∞'
            pan_pos = part_info['part_pan_position']
            lines.append(f"  Part {part_info['part_number']:2d}: {reserve:2d} voices, {mode:6}, {level_db:5}dB, {pan_pos}")

        if status['total_parts'] > 8:
            lines.append(f"  ... and {status['total_parts'] - 8} more parts")

        return '\n'.join(lines)

    def __repr__(self) -> str:
        return f"XGMultiPartSetup(parts={self.num_parts}, voices={sum(self.voice_reserve)}/{self.TOTAL_VOICES_AVAILABLE})"
