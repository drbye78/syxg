"""
Jupiter-X Component Manager

Central hub for all Jupiter-X components, managing the 16-part multitimbral
system, global parameters, and integration with the modern synthesizer.
"""
from __future__ import annotations

from typing import Any
import threading
import numpy as np

from .constants import *
from .part import JupiterXPart, ENGINE_ANALOG, ENGINE_DIGITAL, ENGINE_FM, ENGINE_EXTERNAL


class JupiterXSystemParameters:
    """
    Jupiter-X Global System Parameters

    Manages master controls, system settings, and global effects parameters.
    """

    def __init__(self):
        # Master Controls
        self.master_volume = DEFAULT_MASTER_VOLUME
        self.master_tune = DEFAULT_MASTER_TUNE
        self.master_transpose = DEFAULT_MASTER_TRANSPOSE
        self.master_pan = 0  # -64 to +63 (center = 0)
        self.system_clock = 120  # BPM

        # System Configuration
        self.device_id = JUPITER_X_DEVICE_ID_DEFAULT
        self.local_control = True
        self.program_change_mode = True
        self.midi_channel = 0

        # LCD/LED settings
        self.lcd_contrast = 8
        self.led_brightness = 8

        # Thread safety
        self.lock = threading.RLock()

    def set_parameter(self, param_id: int, value: int) -> bool:
        """Set system parameter by ID (matches NRPN MSB 0x00 mapping)."""
        with self.lock:
            if param_id == 0x00:  # Device ID
                self.device_id = max(0, min(31, value))
            elif param_id == 0x01:  # Master Tune (-64 to +63 semitones)
                self.master_tune = max(-64, min(63, value - 64))
            elif param_id == 0x02:  # Master Transpose (-12 to +12 semitones)
                self.master_transpose = max(-12, min(12, value - 64))
            elif param_id == 0x03:  # Master Volume
                self.master_volume = max(0, min(127, value))
            elif param_id == 0x04:  # Master Pan (-64 to +63, center = 0)
                self.master_pan = max(-64, min(63, value - 64))
            else:
                # Handle additional system parameters (future expansion)
                return False
            return True

    def get_parameter(self, param_id: int) -> int:
        """Get system parameter by ID."""
        with self.lock:
            if param_id == 0x00:  # Master Volume
                return self.master_volume
            elif param_id == 0x01:  # Master Tune
                return self.master_tune + 64
            elif param_id == 0x02:  # Master Transpose
                return self.master_transpose + 64
            elif param_id == 0x03:  # System Clock
                return self.system_clock
            elif param_id == 0x09:  # Device ID
                return self.device_id
            elif param_id == 0x0A:  # MIDI Channel
                return self.midi_channel
            elif param_id == 0x0B:  # Local Control
                return 1 if self.local_control else 0
            elif param_id == 0x0C:  # Program Change Mode
                return 1 if self.program_change_mode else 0
            elif param_id == 0x0D:  # LCD Contrast
                return self.lcd_contrast
            elif param_id == 0x0E:  # LED Brightness
                return self.led_brightness
            else:
                return 0

    def reset_to_defaults(self):
        """Reset all system parameters to defaults."""
        with self.lock:
            self.master_volume = DEFAULT_MASTER_VOLUME
            self.master_tune = DEFAULT_MASTER_TUNE
            self.master_transpose = DEFAULT_MASTER_TRANSPOSE
            self.system_clock = 120
            self.device_id = JUPITER_X_DEVICE_ID_DEFAULT
            self.local_control = True
            self.program_change_mode = True
            self.midi_channel = 0
            self.lcd_contrast = 8
            self.led_brightness = 8


class JupiterXEffectsParameters:
    """
    Jupiter-X Effects Parameters

    Manages global effects settings (reverb, chorus, delay, distortion)
    that can be shared across parts or applied globally.
    """

    def __init__(self):
        # Reverb
        self.reverb_type = DEFAULT_REVERB_TYPE
        self.reverb_level = DEFAULT_REVERB_LEVEL
        self.reverb_time = DEFAULT_REVERB_TIME

        # Chorus
        self.chorus_type = DEFAULT_CHORUS_TYPE
        self.chorus_level = DEFAULT_CHORUS_LEVEL
        self.chorus_rate = DEFAULT_CHORUS_RATE

        # Delay
        self.delay_type = 1  # Digital delay
        self.delay_level = 0
        self.delay_time = 64

        # Distortion
        self.distortion_type = 1  # Overdrive
        self.distortion_level = 0
        self.distortion_drive = 32

        # Thread safety
        self.lock = threading.RLock()

    def set_parameter(self, addr_high: int, addr_mid: int, addr_low: int, value: int) -> bool:
        """Set effects parameter by address."""
        with self.lock:
            # Reverb parameters (0x40, 0x00, XX)
            if addr_high == 0x40 and addr_mid == 0x00:
                if addr_low == 0x00:  # Reverb Type
                    self.reverb_type = max(0, min(7, value))
                elif addr_low == 0x01:  # Reverb Level
                    self.reverb_level = max(0, min(127, value))
                elif addr_low == 0x02:  # Reverb Time
                    self.reverb_time = max(0, min(127, value))
                else:
                    return False

            # Chorus parameters (0x40, 0x01, XX)
            elif addr_high == 0x40 and addr_mid == 0x01:
                if addr_low == 0x00:  # Chorus Type
                    self.chorus_type = max(0, min(7, value))
                elif addr_low == 0x01:  # Chorus Level
                    self.chorus_level = max(0, min(127, value))
                elif addr_low == 0x02:  # Chorus Rate
                    self.chorus_rate = max(0, min(127, value))
                else:
                    return False

            # Delay parameters (0x40, 0x02, XX)
            elif addr_high == 0x40 and addr_mid == 0x02:
                if addr_low == 0x00:  # Delay Type
                    self.delay_type = max(0, min(7, value))
                elif addr_low == 0x01:  # Delay Level
                    self.delay_level = max(0, min(127, value))
                elif addr_low == 0x02:  # Delay Time
                    self.delay_time = max(0, min(127, value))
                else:
                    return False

            # Distortion parameters (0x40, 0x03, XX)
            elif addr_high == 0x40 and addr_mid == 0x03:
                if addr_low == 0x00:  # Distortion Type
                    self.distortion_type = max(0, min(7, value))
                elif addr_low == 0x01:  # Distortion Level
                    self.distortion_level = max(0, min(127, value))
                elif addr_low == 0x02:  # Distortion Drive
                    self.distortion_drive = max(0, min(127, value))
                else:
                    return False

            else:
                return False

            return True

    def get_parameter(self, addr_high: int, addr_mid: int, addr_low: int) -> int | None:
        """Get effects parameter by address."""
        with self.lock:
            # Reverb parameters
            if addr_high == 0x40 and addr_mid == 0x00:
                if addr_low == 0x00:  # Reverb Type
                    return self.reverb_type
                elif addr_low == 0x01:  # Reverb Level
                    return self.reverb_level
                elif addr_low == 0x02:  # Reverb Time
                    return self.reverb_time

            # Chorus parameters
            elif addr_high == 0x40 and addr_mid == 0x01:
                if addr_low == 0x00:  # Chorus Type
                    return self.chorus_type
                elif addr_low == 0x01:  # Chorus Level
                    return self.chorus_level
                elif addr_low == 0x02:  # Chorus Rate
                    return self.chorus_rate

            # Delay parameters
            elif addr_high == 0x40 and addr_mid == 0x02:
                if addr_low == 0x00:  # Delay Type
                    return self.delay_type
                elif addr_low == 0x01:  # Delay Level
                    return self.delay_level
                elif addr_low == 0x02:  # Delay Time
                    return self.delay_time

            # Distortion parameters
            elif addr_high == 0x40 and addr_mid == 0x03:
                if addr_low == 0x00:  # Distortion Type
                    return self.distortion_type
                elif addr_low == 0x01:  # Distortion Level
                    return self.distortion_level
                elif addr_low == 0x02:  # Distortion Drive
                    return self.distortion_drive

            return None

    def reset_to_defaults(self):
        """Reset effects parameters to defaults."""
        with self.lock:
            self.reverb_type = DEFAULT_REVERB_TYPE
            self.reverb_level = DEFAULT_REVERB_LEVEL
            self.reverb_time = DEFAULT_REVERB_TIME
            self.chorus_type = DEFAULT_CHORUS_TYPE
            self.chorus_level = DEFAULT_CHORUS_LEVEL
            self.chorus_rate = DEFAULT_CHORUS_RATE
            self.delay_type = 1
            self.delay_level = 0
            self.delay_time = 64
            self.distortion_type = 1
            self.distortion_level = 0
            self.distortion_drive = 32


class JupiterXComponentManager:
    """
    Jupiter-X Component Manager

    Central hub managing all Jupiter-X components including 16 parts,
    system parameters, effects, and integration with the modern synthesizer.
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

        # Core components
        self.system_params = JupiterXSystemParameters()
        self.effects_params = JupiterXEffectsParameters()

        # 16 multitimbral parts
        self.parts = [JupiterXPart(i, sample_rate) for i in range(16)]

        # Voice allocation (monophonic per part)
        self.active_parts: dict[int, bool] = {i: False for i in range(16)}

        # Thread safety
        self.lock = threading.RLock()

        print("🎹 Jupiter-X Component Manager: Initialized with 16 parts")

    def process_parameter_change(self, address: bytes, value: int) -> bool:
        """
        Process parameter change via address.

        Args:
            address: 3-byte parameter address
            value: Parameter value (0-127)

        Returns:
            True if parameter was processed successfully
        """
        with self.lock:
            if len(address) < 3:
                return False

            addr_high, addr_mid, addr_low = address[0], address[1], address[2]

            # System parameters (0x00, XX, XX)
            if addr_high == 0x00:
                return self.system_params.set_parameter(addr_mid, value)

            # Part parameters (0x10-0x2F, XX, XX)
            elif 0x10 <= addr_high <= 0x2F:
                part_num = addr_high - 0x10
                if 0 <= part_num < 16:
                    return self.parts[part_num].set_parameter(addr_mid, value)

            # Effects parameters (0x40-0x4F, XX, XX)
            elif 0x40 <= addr_high <= 0x4F:
                return self.effects_params.set_parameter(addr_high, addr_mid, addr_low, value)

            # Engine parameters would be handled here for specific parts/engines
            # This would be more complex and is simplified for this implementation

            return False

    def get_parameter_value(self, address: bytes) -> int | None:
        """
        Get parameter value by address.

        Args:
            address: 3-byte parameter address

        Returns:
            Parameter value or None if not found
        """
        with self.lock:
            if len(address) < 3:
                return None

            addr_high, addr_mid, addr_low = address[0], address[1], address[2]

            # System parameters
            if addr_high == 0x00:
                return self.system_params.get_parameter(addr_mid)

            # Part parameters
            elif 0x10 <= addr_high <= 0x2F:
                part_num = addr_high - 0x10
                if 0 <= part_num < 16:
                    return self.parts[part_num].get_parameter(addr_mid)

            # Effects parameters
            elif 0x40 <= addr_high <= 0x4F:
                return self.effects_params.get_parameter(addr_high, addr_mid, addr_low)

            return None

    def process_midi_message(self, channel: int, message_type: str, note: int = None,
                           velocity: int = None, controller: int = None, value: int = None) -> bool:
        """
        Process MIDI message and route to appropriate parts.

        Args:
            channel: MIDI channel (0-15)
            message_type: Type of MIDI message
            note: Note number (for note messages)
            velocity: Velocity (for note messages)
            controller: Controller number (for CC messages)
            value: Controller value (for CC messages)

        Returns:
            True if message was processed by at least one part
        """
        with self.lock:
            processed = False

            # Route to all parts that should receive on this channel
            for part in self.parts:
                if part.should_receive_midi(channel):
                    if message_type == 'note_on' and note is not None and velocity is not None:
                        if part.note_on(note, velocity):
                            self.active_parts[part.part_number] = True
                            processed = True
                    elif message_type == 'note_off' and note is not None:
                        part.note_off(note)
                        processed = True
                    elif message_type == 'control_change' and controller is not None and value is not None:
                        # Handle control changes (would route to appropriate parameters)
                        processed = True

            return processed

    def generate_audio_block(self, block_size: int) -> np.ndarray:
        """
        Generate audio block from all active parts.

        Args:
            block_size: Number of samples to generate

        Returns:
            Stereo audio buffer (block_size, 2)
        """
        with self.lock:
            # Initialize output buffer
            output = np.zeros((block_size, 2), dtype=np.float32)

            # Mix audio from all active parts
            for part in self.parts:
                if self.active_parts.get(part.part_number, False) and part.current_note is not None:
                    part_audio = part.generate_samples(block_size)
                    output += part_audio

            # Apply master volume
            master_volume = self.system_params.master_volume / 127.0
            output *= master_volume

            return output

    def get_part(self, part_number: int) -> JupiterXPart | None:
        """Get part by number."""
        with self.lock:
            if 0 <= part_number < 16:
                return self.parts[part_number]
        return None

    def set_part_parameter(self, part_number: int, param_id: int, value: int) -> bool:
        """Set parameter for a specific part by parameter ID."""
        with self.lock:
            part = self.get_part(part_number)
            if part:
                # Map NRPN parameter ID to part parameter name
                param_name = self._map_nrpn_to_part_param(param_id)
                if param_name:
                    return part.set_parameter_by_name(param_name, value)
                else:
                    # Fallback to direct parameter ID
                    return part.set_parameter(param_id, value)
        return False

    def _map_nrpn_to_part_param(self, param_id: int) -> str | None:
        """Map NRPN parameter ID to part parameter name."""
        # Oscillator parameters (0x00-0x0B)
        if param_id == 0x00:
            return 'osc1_waveform'
        elif param_id == 0x01:
            return 'osc1_coarse_tune'
        elif param_id == 0x02:
            return 'osc1_fine_tune'
        elif param_id == 0x03:
            return 'osc1_level'
        elif param_id == 0x04:
            return 'osc1_supersaw_spread'
        elif param_id == 0x05:
            return 'osc2_waveform'
        elif param_id == 0x06:
            return 'osc2_coarse_tune'
        elif param_id == 0x07:
            return 'osc2_fine_tune'
        elif param_id == 0x08:
            return 'osc2_level'
        elif param_id == 0x09:
            return 'osc2_detune'
        elif param_id == 0x0A:
            return 'osc_sync'
        elif param_id == 0x0B:
            return 'ring_modulation'

        # Filter parameters (0x10-0x19)
        elif param_id == 0x10:
            return 'filter_type'
        elif param_id == 0x11:
            return 'filter_cutoff'
        elif param_id == 0x12:
            return 'filter_resonance'
        elif param_id == 0x13:
            return 'filter_drive'
        elif param_id == 0x14:
            return 'filter_key_tracking'
        elif param_id == 0x15:
            return 'filter_envelope_amount'
        elif param_id == 0x16:
            return 'filter_attack'
        elif param_id == 0x17:
            return 'filter_decay'
        elif param_id == 0x18:
            return 'filter_sustain'
        elif param_id == 0x19:
            return 'filter_release'

        # Amplifier parameters (0x20-0x25)
        elif param_id == 0x20:
            return 'amp_level'
        elif param_id == 0x21:
            return 'amp_attack'
        elif param_id == 0x22:
            return 'amp_decay'
        elif param_id == 0x23:
            return 'amp_sustain'
        elif param_id == 0x24:
            return 'amp_release'
        elif param_id == 0x25:
            return 'amp_velocity_sensitivity'

        # LFO parameters (0x28-0x2F)
        elif param_id == 0x28:
            return 'lfo1_waveform'
        elif param_id == 0x29:
            return 'lfo1_rate'
        elif param_id == 0x2A:
            return 'lfo1_depth'
        elif param_id == 0x2B:
            return 'lfo1_sync'
        elif param_id == 0x2C:
            return 'lfo2_waveform'
        elif param_id == 0x2D:
            return 'lfo2_rate'
        elif param_id == 0x2E:
            return 'lfo2_depth'
        elif param_id == 0x2F:
            return 'lfo2_sync'

        return None

    def get_part_parameter(self, part_number: int, param_id: int) -> int | None:
        """Get parameter from a specific part."""
        with self.lock:
            part = self.get_part(part_number)
            if part:
                return part.get_parameter(param_id)
        return None

    def set_engine_level(self, part_number: int, engine_type: int, level: float) -> bool:
        """Set engine mix level for a part."""
        with self.lock:
            part = self.get_part(part_number)
            if part:
                part.set_engine_level(engine_type, level)
                return True
        return False

    def set_engine_parameter(self, part_number: int, engine_type: int,
                           param_id: int, value: int) -> bool:
        """Set parameter for a specific engine in a part by parameter ID."""
        with self.lock:
            part = self.get_part(part_number)
            if part and 0 <= engine_type < len(part.engines):
                # Handle base parameters (0x00-0x0F) - common across all engines
                if param_id == 0x00:  # engine_enable
                    level = 1.0 if value > 0 else 0.0
                    return part.set_engine_level(engine_type, level)
                elif param_id == 0x01:  # engine_level
                    level = value / 127.0
                    return part.set_engine_level(engine_type, level)
                elif param_id == 0x02:  # engine_pan
                    # Pan is handled at part level, not engine level
                    return True  # Accept but don't process
                elif param_id == 0x03:  # engine_coarse_tune
                    # Coarse tune is handled at part level, not engine level
                    return True  # Accept but don't process
                elif param_id == 0x04:  # engine_fine_tune
                    # Fine tune is handled at part level, not engine level
                    return True  # Accept but don't process

                # Handle engine-specific parameters
                else:
                    # Map parameter ID to parameter name based on engine type
                    param_name = self._map_engine_param_id_to_name(engine_type, param_id)
                    if param_name:
                        # For analog engine (AdditiveEngine), route through part.set_parameter_by_name
                        if engine_type == 0:  # Analog engine
                            return part.set_parameter_by_name(param_name, value)
                        else:
                            # For other engines, set directly on engine object
                            engine = part.engines[engine_type]
                            return engine.set_parameter(param_name, value)
        return False

    def _map_engine_param_id_to_name(self, engine_type: int, param_id: int) -> str | None:
        """Map engine parameter ID to parameter name based on engine type."""
        # Import here to avoid circular imports
        from .constants import (ENGINE_ANALOG, ANALOG_OSC1_WAVEFORM, ANALOG_OSC1_COARSE_TUNE,
                               ANALOG_OSC1_FINE_TUNE, ANALOG_OSC1_LEVEL, ANALOG_OSC1_SUPERSAW_SPREAD,
                               ANALOG_OSC2_WAVEFORM, ANALOG_OSC2_COARSE_TUNE, ANALOG_OSC2_FINE_TUNE,
                               ANALOG_OSC2_LEVEL, ANALOG_OSC2_DETUNE, ANALOG_OSC2_RING_MOD,
                               ANALOG_FILTER_TYPE, ANALOG_FILTER_CUTOFF, ANALOG_FILTER_RESONANCE,
                               ANALOG_FILTER_ENVELOPE_AMOUNT, ANALOG_AMP_ATTACK, ANALOG_AMP_DECAY,
                               ANALOG_AMP_SUSTAIN, ANALOG_AMP_RELEASE, ANALOG_FILTER_ATTACK,
                               ANALOG_FILTER_DECAY, ANALOG_FILTER_SUSTAIN, ANALOG_FILTER_RELEASE)

        if engine_type == ENGINE_ANALOG:
            param_map = {
                ANALOG_OSC1_WAVEFORM: 'osc1_waveform',
                ANALOG_OSC1_COARSE_TUNE: 'osc1_coarse_tune',
                ANALOG_OSC1_FINE_TUNE: 'osc1_fine_tune',
                ANALOG_OSC1_LEVEL: 'osc1_level',
                ANALOG_OSC1_SUPERSAW_SPREAD: 'osc1_supersaw_spread',
                ANALOG_OSC2_WAVEFORM: 'osc2_waveform',
                ANALOG_OSC2_COARSE_TUNE: 'osc2_coarse_tune',
                ANALOG_OSC2_FINE_TUNE: 'osc2_fine_tune',
                ANALOG_OSC2_LEVEL: 'osc2_level',
                ANALOG_OSC2_DETUNE: 'osc2_detune',
                ANALOG_OSC2_RING_MOD: 'osc2_ring_mod',
                ANALOG_FILTER_TYPE: 'filter_type',
                ANALOG_FILTER_CUTOFF: 'filter_cutoff',
                ANALOG_FILTER_RESONANCE: 'filter_resonance',
                ANALOG_FILTER_ENVELOPE_AMOUNT: 'filter_envelope_amount',
                ANALOG_AMP_ATTACK: 'amp_attack',
                ANALOG_AMP_DECAY: 'amp_decay',
                ANALOG_AMP_SUSTAIN: 'amp_sustain',
                ANALOG_AMP_RELEASE: 'amp_release',
                ANALOG_FILTER_ATTACK: 'filter_attack',
                ANALOG_FILTER_DECAY: 'filter_decay',
                ANALOG_FILTER_SUSTAIN: 'filter_sustain',
                ANALOG_FILTER_RELEASE: 'filter_release',
            }
            return param_map.get(param_id)

        # For other engine types, return None for now (they would need their own mappings)
        return None

    def reset_all_parts(self):
        """Reset all parts to default state."""
        with self.lock:
            for part in self.parts:
                part.reset()
            self.active_parts = {i: False for i in range(16)}

    def reset_system_parameters(self):
        """Reset system parameters to defaults."""
        with self.lock:
            self.system_params.reset_to_defaults()
            self.effects_params.reset_to_defaults()

    def get_system_info(self) -> dict[str, Any]:
        """Get comprehensive Jupiter-X system information."""
        with self.lock:
            return {
                'system_params': {
                    'master_volume': self.system_params.master_volume,
                    'master_tune': self.system_params.master_tune,
                    'master_transpose': self.system_params.master_transpose,
                    'system_clock': self.system_params.system_clock,
                    'device_id': self.system_params.device_id,
                    'local_control': self.system_params.local_control,
                    'program_change_mode': self.system_params.program_change_mode,
                    'midi_channel': self.system_params.midi_channel,
                    'lcd_contrast': self.system_params.lcd_contrast,
                    'led_brightness': self.system_params.led_brightness,
                },
                'effects_params': {
                    'reverb': {
                        'type': self.effects_params.reverb_type,
                        'level': self.effects_params.reverb_level,
                        'time': self.effects_params.reverb_time,
                    },
                    'chorus': {
                        'type': self.effects_params.chorus_type,
                        'level': self.effects_params.chorus_level,
                        'rate': self.effects_params.chorus_rate,
                    },
                    'delay': {
                        'type': self.effects_params.delay_type,
                        'level': self.effects_params.delay_level,
                        'time': self.effects_params.delay_time,
                    },
                    'distortion': {
                        'type': self.effects_params.distortion_type,
                        'level': self.effects_params.distortion_level,
                        'drive': self.effects_params.distortion_drive,
                    },
                },
                'parts': [part.get_part_info() for part in self.parts],
                'active_parts': self.active_parts.copy(),
                'sample_rate': self.sample_rate,
                'total_parts': 16,
            }

    def cleanup(self):
        """Clean up resources."""
        with self.lock:
            for part in self.parts:
                part.reset()

    def __str__(self) -> str:
        """String representation."""
        active_count = sum(1 for active in self.active_parts.values() if active)
        return f"JupiterXComponentManager(parts=16, active={active_count}, sample_rate={self.sample_rate})"

    def __repr__(self) -> str:
        return self.__str__()
