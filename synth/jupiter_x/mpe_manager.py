"""
Jupiter-X MPE (MIDI Polyphonic Expression) Manager

Complete MPE implementation for microtonal expression and per-note control,
enabling advanced performance capabilities with independent pitch bend,
timbre, and expression per note.
"""

from __future__ import annotations

from typing import Any
import threading
import time
import numpy as np

from .constants import *


class MPENoteData:
    """
    Advanced per-note MPE data structure for microtonal expression.

    Each active note can have independent pitch bend, timbre modulation,
    and expression control within the MPE specification with advanced features.
    """

    def __init__(self, note: int, channel: int, velocity: int):
        self.note = note
        self.channel = channel
        self.velocity = velocity
        self.active = True

        # MPE Parameters (within MPE specification ranges)
        self.pitch_bend = 0.0  # -48 to +48 semitones (MPE standard)
        self.timbre = 0.0  # 0.0 to 1.0 (normalized for compatibility)
        self.pressure = 0.0  # 0.0 to 1.0 (aftertouch)

        # Extended Jupiter-X parameters
        self.slide_time = 0.0  # Portamento time for this note
        self.vibrato_depth = 0.0  # Per-note vibrato
        self.vibrato_rate = 5.0  # Per-note vibrato rate
        self.formant_shift = 0.0  # Per-note formant adjustment

        # Advanced MPE features
        self.per_note_lfo_phase = 0.0  # LFO phase for per-note vibrato
        self.harmonic_content = None  # Harmonic series for this note
        self.slide_source_note = None  # Source note for portamento
        self.slide_progress = 0.0  # Portamento progress (0.0-1.0)

        # Internal state
        self.start_time = time.time()
        self.last_update = time.time()
        self.timestamp = time.time()
        self.envelope_value = 0.0

        # Voice assignment (for voice stealing)
        self.voice_id = None

    def update_from_midi(self, pitch_bend: int = None, timbre: int = None, pressure: int = None):
        """Update MPE parameters from MIDI data with advanced processing."""
        if pitch_bend is not None:
            # Convert MIDI pitch bend (-8192 to +8191) to semitones
            # MIDI pitch bend is 14-bit: -8192 (0x2000) to +8191 (0x3FFF)
            self.pitch_bend = ((pitch_bend - 8192) / 8192.0) * 48.0

        if timbre is not None:
            # timbre parameter can be either MIDI CC value (0-127) or normalized value (0.0-1.0)
            # Detect based on range and store as normalized (0.0-1.0)
            if 0 <= timbre <= 1.0:
                # Already normalized (0.0-1.0)
                self.timbre = timbre
            else:
                # MIDI CC value (0-127) -> convert to normalized (0.0-1.0)
                self.timbre = timbre / 127.0

        if pressure is not None:
            # Convert MIDI aftertouch (0-127) to normalized (0.0-1.0)
            self.pressure = pressure / 127.0

        self.last_update = time.time()

    def update_per_note_lfo(self, delta_time: float):
        """Update per-note LFO for vibrato with phase accumulation."""
        if self.vibrato_depth > 0.0:
            # Advance LFO phase based on vibrato rate
            self.per_note_lfo_phase += self.vibrato_rate * delta_time * 2.0 * np.pi
            # Keep phase in 0-2π range
            self.per_note_lfo_phase = self.per_note_lfo_phase % (2.0 * np.pi)

    def get_vibrato_offset(self) -> float:
        """Get current vibrato offset in semitones based on LFO phase."""
        if self.vibrato_depth <= 0.0:
            return 0.0
        # Sine wave LFO for smooth vibrato
        return np.sin(self.per_note_lfo_phase) * self.vibrato_depth

    def start_slide_to(self, target_note: int, slide_time: float = 0.1):
        """Start portamento slide to target note."""
        self.slide_source_note = self.note
        self.slide_time = slide_time
        self.slide_progress = 0.0

    def update_slide(self, delta_time: float) -> float:
        """
        Update portamento slide and return current interpolated note.

        Returns:
            Current note value with slide interpolation
        """
        if self.slide_source_note is None or self.slide_time <= 0:
            return float(self.note)

        # Update slide progress
        self.slide_progress += delta_time / self.slide_time
        self.slide_progress = min(1.0, self.slide_progress)

        # Linear interpolation between source and target note
        current_note = (
            self.slide_source_note * (1.0 - self.slide_progress) + self.note * self.slide_progress
        )

        # Complete slide when progress reaches 1.0
        if self.slide_progress >= 1.0:
            self.slide_source_note = None
            self.slide_time = 0.0

        return current_note

    def set_harmonic_content(self, harmonics: list[float]):
        """Set harmonic content for this note from tuning system."""
        self.harmonic_content = harmonics

    def get_effective_pitch(self, base_note: int) -> float:
        """Get effective pitch including MPE pitch bend."""
        return base_note + self.pitch_bend

    def get_mpe_info(self) -> dict[str, Any]:
        """Get comprehensive MPE note information."""
        return {
            "note": self.note,
            "channel": self.channel,
            "velocity": self.velocity,
            "active": self.active,
            "pitch_bend": self.pitch_bend,
            "timbre": self.timbre,
            "pressure": self.pressure,
            "slide_time": self.slide_time,
            "vibrato_depth": self.vibrato_depth,
            "vibrato_rate": self.vibrato_rate,
            "formant_shift": self.formant_shift,
            "voice_id": self.voice_id,
            "age": time.time() - self.start_time,
        }


class MPEZone:
    """
    MPE Zone configuration for upper and lower zones.

    MPE allows configuration of separate zones for different controllers,
    enabling complex multi-instrument setups.
    """

    def __init__(self, zone_type: str = "lower"):
        self.zone_type = zone_type  # "lower" or "upper"

        # Zone boundaries
        self.master_channel = 0  # Master channel for this zone
        self.member_channels_start = 1  # Start of member channels
        self.member_channels_end = 15  # End of member channels

        # Zone-specific settings
        self.pitch_bend_range = 48.0  # Semitones (MPE standard: 0-96)
        self.timbre_cc = 74  # CC number for timbre (default: 74)

        # Zone status
        self.enabled = False
        self.active_channels = set()

    def is_channel_in_zone(self, channel: int) -> bool:
        """Check if channel belongs to this zone."""
        if channel == self.master_channel:
            return True
        return self.member_channels_start <= channel <= self.member_channels_end

    def get_zone_channels(self) -> list[int]:
        """Get all channels in this zone."""
        channels = [self.master_channel]
        channels.extend(range(self.member_channels_start, self.member_channels_end + 1))
        return channels

    def get_zone_info(self) -> dict[str, Any]:
        """Get zone configuration information."""
        return {
            "zone_type": self.zone_type,
            "enabled": self.enabled,
            "master_channel": self.master_channel,
            "member_channels": f"{self.member_channels_start}-{self.member_channels_end}",
            "pitch_bend_range": self.pitch_bend_range,
            "timbre_cc": self.timbre_cc,
            "active_channels": len(self.active_channels),
        }


class JupiterXMPEManager:
    """
    Jupiter-X MPE Manager

    Complete MPE implementation with microtonal pitch control,
    per-note expression, and advanced performance features.
    Supports both lower and upper MPE zones.
    """

    def __init__(self):
        self.lock = threading.RLock()

        # MPE State
        self.mpe_enabled = False
        self.global_pitch_bend_range = 2.0  # Traditional pitch bend range

        # MPE Zones
        self.lower_zone = MPEZone("lower")
        self.upper_zone = MPEZone("upper")

        # Active notes (channel -> note -> MPENoteData)
        self.active_notes: dict[int, dict[int, MPENoteData]] = {}
        for ch in range(16):
            self.active_notes[ch] = {}

        # MPE Configuration
        self.pitch_bend_resolution = 8192  # 14-bit pitch bend
        self.timbre_resolution = 128  # 7-bit timbre
        self.pressure_resolution = 128  # 7-bit pressure

        # Jupiter-X specific MPE features
        self.microtonal_tuning = "equal"  # equal, just, pythagorean, custom
        self.vibrato_per_note = True  # Enable per-note vibrato
        self.formant_per_note = True  # Enable per-note formant control

        # Voice management
        self.max_voices_per_channel = 8
        self.voice_stealing = "last"  # last, quietest, oldest

        # Callbacks
        self.note_on_callback: Callable | None = None
        self.note_off_callback: Callable | None = None
        self.pitch_bend_callback: Callable | None = None
        self.timbre_callback: Callable | None = None
        self.pressure_callback: Callable | None = None

        print("🎹 Jupiter-X MPE: Initialized with dual-zone support")

    def enable_mpe(self, enable: bool = True):
        """Enable or disable MPE mode."""
        with self.lock:
            self.mpe_enabled = enable
            if enable:
                # Configure default zones
                self._configure_default_zones()
            else:
                # Clear all zones and active notes
                self._clear_all_zones()

    def configure_zone(
        self,
        zone_type: str,
        master_channel: int,
        member_start: int,
        member_end: int,
        pitch_bend_range: float = 48.0,
    ):
        """Configure an MPE zone."""
        with self.lock:
            zone = self.lower_zone if zone_type == "lower" else self.upper_zone

            zone.master_channel = master_channel
            zone.member_channels_start = member_start
            zone.member_channels_end = member_end
            zone.pitch_bend_range = pitch_bend_range
            zone.enabled = True

    def get_mpe_zone(self, channel: int) -> MPEZone | None:
        """Get MPE zone for a given channel."""
        with self.lock:
            if self.lower_zone.is_channel_in_zone(channel):
                return self.lower_zone
            if self.upper_zone.is_channel_in_zone(channel):
                return self.upper_zone
            return None

    def _configure_default_zones(self):
        """Configure default MPE zones."""
        # Lower zone: channels 1-8 (master=0, members=1-8)
        self.configure_zone("lower", 0, 1, 8, 48.0)

        # Upper zone: channels 10-15 (master=9, members=10-15)
        self.configure_zone("upper", 9, 10, 15, 48.0)

    def _clear_all_zones(self):
        """Clear all zone configurations and active notes."""
        self.lower_zone.enabled = False
        self.upper_zone.enabled = False

        # Clear all active notes
        for channel_notes in self.active_notes.values():
            channel_notes.clear()

    def process_midi_message(self, status: int, data1: int, data2: int) -> bool:
        """
        Process MIDI message for MPE handling.

        Returns True if message was handled by MPE system.
        """
        if not self.mpe_enabled:
            return False

        with self.lock:
            msg_type = status >> 4
            channel = status & 0x0F

            if msg_type == 0x9:  # Note On
                if data2 > 0:  # Velocity > 0
                    self._handle_note_on(channel, data1, data2)
                    return True
                else:  # Note On with velocity 0 = Note Off
                    self._handle_note_off(channel, data1)
                    return True

            elif msg_type == 0x8:  # Note Off
                self._handle_note_off(channel, data1)
                return True

            elif msg_type == 0xE:  # Pitch Bend
                pitch_bend_value = (data2 << 7) | data1  # 14-bit value
                self._handle_pitch_bend(channel, pitch_bend_value)
                return True

            elif msg_type == 0xD:  # Aftertouch (Polyphonic)
                self._handle_pressure(channel, data1, data2)
                return True

            elif msg_type == 0xB:  # Control Change
                if data1 == 74:  # Timbre (MPE standard)
                    self._handle_timbre(channel, data2)
                    return True

        return False

    def _allocate_voice_for_mpe(self, channel: int, note: int, velocity: int) -> int:
        """Allocate voice for MPE note with proper polyphony tracking."""
        active_count = len(self.active_notes[channel])

        if active_count == 0:
            return 0

        # Use oldest note's voice position + 1 for proper voice assignment
        oldest_note = min(self.active_notes[channel].values(), key=lambda n: n.timestamp)

        # Cycle through voices based on note count
        return (oldest_note.voice_id + 1) % 128

    def _handle_note_on(self, channel: int, note: int, velocity: int):
        """Handle MPE note-on event."""
        # Create new MPE note data
        mpe_note = MPENoteData(note, channel, velocity)

        # Assign voice using MPE zone policy
        # In MPE, the pitch bend range defines the zone, so we use note-based assignment
        zone = self.get_mpe_zone(channel)

        if zone:
            # Use voice manager for proper polyphony tracking
            voice_id = self._allocate_voice_for_mpe(channel, note, velocity)
        else:
            # Fallback to simple assignment
            voice_id = len(self.active_notes[channel])

        mpe_note.voice_id = voice_id

        # Store active note
        self.active_notes[channel][note] = mpe_note

        # Update zone activity
        self._update_zone_activity(channel, True)

        # Call note-on callback with MPE data
        if self.note_on_callback:
            self.note_on_callback(channel, note, velocity, mpe_note)

    def _handle_note_off(self, channel: int, note: int):
        """Handle MPE note-off event."""
        if note in self.active_notes[channel]:
            mpe_note = self.active_notes[channel][note]
            mpe_note.active = False

            # Call note-off callback
            if self.note_off_callback:
                self.note_off_callback(channel, note, mpe_note)

            # Remove from active notes
            del self.active_notes[channel][note]

            # Update zone activity
            self._update_zone_activity(channel, False)

    def _handle_pitch_bend(self, channel: int, value: int):
        """Handle MPE pitch bend."""
        # Apply to all active notes on this channel
        for mpe_note in self.active_notes[channel].values():
            mpe_note.update_from_midi(pitch_bend=value)

        # Call pitch bend callback
        if self.pitch_bend_callback:
            self.pitch_bend_callback(channel, value)

    def _handle_timbre(self, channel: int, value: int):
        """Handle MPE timbre control."""
        # Apply to all active notes on this channel
        for mpe_note in self.active_notes[channel].values():
            mpe_note.update_from_midi(timbre=value)

        # Call timbre callback
        if self.timbre_callback:
            self.timbre_callback(channel, value)

    def _handle_pressure(self, channel: int, note: int, pressure: int):
        """Handle MPE polyphonic aftertouch."""
        if note in self.active_notes[channel]:
            self.active_notes[channel][note].update_from_midi(pressure=pressure)

        # Call pressure callback
        if self.pressure_callback:
            self.pressure_callback(channel, note, pressure)

    def _update_zone_activity(self, channel: int, active: bool):
        """Update zone activity tracking."""
        if self.lower_zone.is_channel_in_zone(channel):
            if active:
                self.lower_zone.active_channels.add(channel)
            elif channel in self.lower_zone.active_channels:
                self.lower_zone.active_channels.discard(channel)

        if self.upper_zone.is_channel_in_zone(channel):
            if active:
                self.upper_zone.active_channels.add(channel)
            elif channel in self.upper_zone.active_channels:
                self.upper_zone.active_channels.discard(channel)

    def get_channel_mpe_data(self, channel: int) -> dict[int, dict[str, Any]]:
        """Get all MPE data for a channel."""
        with self.lock:
            return {
                note: mpe_note.get_mpe_info()
                for note, mpe_note in self.active_notes[channel].items()
            }

    def get_note_mpe_data(self, channel: int, note: int) -> dict[str, Any] | None:
        """Get MPE data for a specific note."""
        with self.lock:
            if note in self.active_notes[channel]:
                return self.active_notes[channel][note].get_mpe_info()
        return None

    def set_note_parameter(self, channel: int, note: int, param: str, value: Any) -> bool:
        """Set per-note MPE parameter."""
        with self.lock:
            if note in self.active_notes[channel]:
                mpe_note = self.active_notes[channel][note]

                if param == "vibrato_depth":
                    mpe_note.vibrato_depth = max(0.0, min(1.0, value))
                elif param == "vibrato_rate":
                    mpe_note.vibrato_rate = max(0.1, min(20.0, value))
                elif param == "slide_time":
                    mpe_note.slide_time = max(0.0, value)
                elif param == "formant_shift":
                    mpe_note.formant_shift = max(-2.0, min(2.0, value))
                else:
                    return False
                return True
        return False

    def get_mpe_statistics(self) -> dict[str, Any]:
        """Get MPE system statistics."""
        with self.lock:
            total_active_notes = sum(
                len(channel_notes) for channel_notes in self.active_notes.values()
            )

            return {
                "mpe_enabled": self.mpe_enabled,
                "total_active_notes": total_active_notes,
                "lower_zone": self.lower_zone.get_zone_info(),
                "upper_zone": self.upper_zone.get_zone_info(),
                "channels_with_notes": [ch for ch, notes in self.active_notes.items() if notes],
                "microtonal_tuning": self.microtonal_tuning,
                "vibrato_per_note": self.vibrato_per_note,
                "formant_per_note": self.formant_per_note,
            }

    def set_microtonal_tuning(self, tuning_system: str, custom_ratios: list[float] = None):
        """Set microtonal tuning system with professional scale support."""
        with self.lock:
            self.microtonal_tuning = tuning_system

            if tuning_system == "custom" and custom_ratios:
                # Store custom tuning ratios for microtonal scales
                self.custom_tuning_ratios = custom_ratios.copy()
                self._apply_custom_tuning(custom_ratios)
            elif tuning_system == "just_intonation":
                # Just intonation ratios for pure harmonic intervals
                just_ratios = [1.0, 9 / 8, 5 / 4, 4 / 3, 3 / 2, 5 / 3, 15 / 8, 2.0]
                self._apply_custom_tuning(just_ratios)
            elif tuning_system == "meantone":
                # Quarter-comma meantone temperament
                meantone_ratios = [1.0, 1.118, 1.25, 1.337, 1.495, 1.672, 1.869, 2.0]
                self._apply_custom_tuning(meantone_ratios)
            elif tuning_system == "pythagorean":
                # Pythagorean tuning based on perfect fifths
                pythag_ratios = [1.0, 1.125, 1.266, 1.333, 1.5, 1.688, 1.898, 2.0]
                self._apply_custom_tuning(pythag_ratios)

    def _apply_custom_tuning(self, ratios: list[float]):
        """Apply custom tuning ratios to MPE zones with interpolation."""
        # Apply custom ratios to both zones
        self.lower_zone.set_custom_tuning_ratios(ratios)
        self.upper_zone.set_custom_tuning_ratios(ratios)

        # Store harmonic series for advanced synthesis
        self.harmonic_series = self._calculate_harmonic_series(ratios)

    def _calculate_harmonic_series(self, ratios: list[float]) -> list[list[float]]:
        """Calculate harmonic series from tuning ratios for advanced synthesis."""
        harmonic_series = []
        for ratio in ratios:
            # Calculate first 8 harmonics for each ratio
            harmonics = [ratio * (i + 1) for i in range(8)]
            harmonic_series.append(harmonics)
        return harmonic_series

    def get_harmonic_content(self, note: int) -> list[float]:
        """Get harmonic content for a specific note based on current tuning."""
        if not hasattr(self, "harmonic_series"):
            return [1.0, 0.5, 0.33, 0.25, 0.2, 0.17, 0.14, 0.125]  # Default harmonic series

        # Find closest ratio in tuning system
        note_in_scale = note % 12
        if note_in_scale < len(self.harmonic_series):
            return self.harmonic_series[note_in_scale]
        return self.harmonic_series[0]

    def reset(self):
        """Reset MPE system to default state."""
        with self.lock:
            self._clear_all_zones()
            self.mpe_enabled = False

    def get_mpe_info(self) -> dict[str, Any]:
        """Get comprehensive MPE system information with harmonic analysis."""
        return {
            "enabled": self.mpe_enabled,
            "global_pitch_bend_range": self.global_pitch_bend_range,
            "zones": {
                "lower": self.lower_zone.get_zone_info(),
                "upper": self.upper_zone.get_zone_info(),
            },
            "statistics": self.get_mpe_statistics(),
            "capabilities": {
                "pitch_bend_resolution": self.pitch_bend_resolution,
                "timbre_resolution": self.timbre_resolution,
                "pressure_resolution": self.pressure_resolution,
                "max_voices_per_channel": self.max_voices_per_channel,
                "microtonal_support": True,
                "per_note_vibrato": self.vibrato_per_note,
                "per_note_formant": self.formant_per_note,
                "harmonic_series_support": hasattr(self, "harmonic_series"),
            },
            "tuning_system": self.microtonal_tuning,
            "harmonic_content": self.get_harmonic_content(60)
            if hasattr(self, "harmonic_series")
            else None,
        }


# Export the MPE manager class
__all__ = ["JupiterXMPEManager", "MPENoteData", "MPEZone"]
