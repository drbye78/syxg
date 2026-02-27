"""
Groove Quantizer - Rhythm Correction and Groove Processing

Provides advanced quantization and groove processing capabilities
for the built-in sequencer, including swing, shuffle, and custom
groove templates.
"""
from __future__ import annotations

import numpy as np
from typing import Any
import math

from .sequencer_types import QuantizeMode, GrooveTemplate, NoteEvent


class GrooveTemplateData:
    """Container for groove template data"""

    def __init__(self, name: str, timing_offsets: list[float],
                 velocity_multipliers: list[float] | None = None):
        """
        Initialize groove template.

        Args:
            name: Template name
            timing_offsets: Timing offsets for each 16th note position (in beats)
            velocity_multipliers: Velocity multipliers (optional)
        """
        self.name = name
        self.timing_offsets = np.array(timing_offsets, dtype=np.float32)

        if velocity_multipliers:
            self.velocity_multipliers = np.array(velocity_multipliers, dtype=np.float32)
        else:
            self.velocity_multipliers = np.ones(len(timing_offsets), dtype=np.float32)

    def get_offset_for_position(self, position: int) -> float:
        """Get timing offset for a given 16th note position"""
        if 0 <= position < len(self.timing_offsets):
            return self.timing_offsets[position]
        return 0.0

    def get_velocity_multiplier(self, position: int) -> float:
        """Get velocity multiplier for a given 16th note position"""
        if 0 <= position < len(self.velocity_multipliers):
            return self.velocity_multipliers[position]
        return 1.0


class GrooveQuantizer:
    """
    Groove Quantizer - Advanced rhythm correction and groove processing

    Provides sophisticated quantization with groove templates, swing,
    shuffle, and custom timing adjustments.
    """

    def __init__(self):
        """Initialize groove quantizer"""
        self.templates: dict[GrooveTemplate, GrooveTemplateData] = {}
        self._init_builtin_templates()

        # Current settings
        self.current_template = GrooveTemplate.STRAIGHT
        self.quantize_strength = 1.0  # 0.0 to 1.0
        self.humanize_amount = 0.0    # 0.0 to 1.0
        self.swing_amount = 0.0       # 0.0 to 1.0

    def _init_builtin_templates(self):
        """Initialize built-in groove templates"""

        # Straight (no groove)
        straight_offsets = [0.0] * 16
        straight_velocities = [1.0] * 16
        self.templates[GrooveTemplate.STRAIGHT] = GrooveTemplateData(
            "Straight", straight_offsets, straight_velocities
        )

        # 8th note swing
        swing_8th_offsets = []
        swing_8th_velocities = []
        for i in range(16):
            if i % 2 == 0:  # Even positions (on beats)
                offset = 0.0
                velocity = 1.0
            else:  # Odd positions (off beats)
                offset = 0.0625 * 0.67  # 16th note delay * swing factor
                velocity = 0.9  # Slightly softer

            swing_8th_offsets.append(offset)
            swing_8th_velocities.append(velocity)

        self.templates[GrooveTemplate.SWING_8TH] = GrooveTemplateData(
            "Swing 8th", swing_8th_offsets, swing_8th_velocities
        )

        # 16th note swing
        swing_16th_offsets = []
        swing_16th_velocities = []
        for i in range(16):
            if i % 4 == 2:  # 16th note off-beats
                offset = 0.03125 * 0.5  # 32nd note delay * swing factor
                velocity = 0.85
            else:
                offset = 0.0
                velocity = 1.0

            swing_16th_offsets.append(offset)
            swing_16th_velocities.append(velocity)

        self.templates[GrooveTemplate.SWING_16TH] = GrooveTemplateData(
            "Swing 16th", swing_16th_offsets, swing_16th_velocities
        )

        # Triplet feel
        triplet_offsets = []
        triplet_velocities = []
        for i in range(16):
            beat_in_measure = i % 4
            if beat_in_measure == 1:  # Second 16th in triplet
                offset = 0.0208  # Slight delay for triplet feel
                velocity = 0.95
            elif beat_in_measure == 3:  # Second 16th in next triplet
                offset = 0.0208
                velocity = 0.95
            else:
                offset = 0.0
                velocity = 1.0

            triplet_offsets.append(offset)
            triplet_velocities.append(velocity)

        self.templates[GrooveTemplate.TRIPLET] = GrooveTemplateData(
            "Triplet", triplet_offsets, triplet_velocities
        )

        # Shuffle (extreme swing)
        shuffle_offsets = []
        shuffle_velocities = []
        for i in range(16):
            if i % 2 == 0:  # Even positions
                offset = 0.0
                velocity = 1.0
            else:  # Odd positions (heavy swing)
                offset = 0.09375  # 3/32 note delay
                velocity = 0.8

            shuffle_offsets.append(offset)
            shuffle_velocities.append(velocity)

        self.templates[GrooveTemplate.SHUFFLE] = GrooveTemplateData(
            "Shuffle", shuffle_offsets, shuffle_velocities
        )

        # Half-time feel
        halftime_offsets = []
        halftime_velocities = []
        for i in range(16):
            if i % 8 == 4:  # Every other 8th note
                offset = 0.03125  # Small delay
                velocity = 0.9
            elif i % 8 == 0:  # Main beats
                offset = 0.0
                velocity = 1.0
            else:
                offset = 0.0
                velocity = 0.95

            halftime_offsets.append(offset)
            halftime_velocities.append(velocity)

        self.templates[GrooveTemplate.HALF_TIME] = GrooveTemplateData(
            "Half Time", halftime_offsets, halftime_velocities
        )

        # Double-time feel
        doubletime_offsets = []
        doubletime_velocities = []
        for i in range(16):
            if i % 2 == 1:  # Off-beats get anticipation
                offset = -0.015625  # Slight anticipation
                velocity = 1.1
            else:
                offset = 0.0
                velocity = 1.0

            doubletime_offsets.append(offset)
            doubletime_velocities.append(velocity)

        self.templates[GrooveTemplate.DOUBLE_TIME] = GrooveTemplateData(
            "Double Time", doubletime_offsets, doubletime_velocities
        )

    def set_groove_template(self, template: GrooveTemplate):
        """Set the current groove template"""
        if template in self.templates:
            self.current_template = template

    def set_quantize_strength(self, strength: float):
        """Set quantization strength (0.0 = no quantization, 1.0 = full)"""
        self.quantize_strength = max(0.0, min(1.0, strength))

    def set_humanize_amount(self, amount: float):
        """Set humanization amount (0.0 = mechanical, 1.0 = very human)"""
        self.humanize_amount = max(0.0, min(1.0, amount))

    def set_swing_amount(self, amount: float):
        """Set swing amount (0.0 = straight, 1.0 = full swing)"""
        self.swing_amount = max(0.0, min(1.0, amount))

    def quantize_notes(self, notes: list[NoteEvent], mode: QuantizeMode = None,
                      template: GrooveTemplate = None) -> list[NoteEvent]:
        """
        Quantize a list of notes with groove processing.

        Args:
            notes: List of notes to quantize
            mode: Quantization mode (uses self settings if None)
            template: Groove template (uses self settings if None)

        Returns:
            New list of quantized notes
        """
        if not notes:
            return []

        quantized_notes = []

        # Use provided settings or defaults
        quantize_mode = mode if mode is not None else QuantizeMode.Q_16TH
        groove_template = template if template is not None else self.current_template

        template_data = self.templates.get(groove_template, self.templates[GrooveTemplate.STRAIGHT])

        for note in notes:
            quantized_note = NoteEvent(
                time=note.time,
                duration=note.duration,
                note_number=note.note_number,
                velocity=note.velocity,
                channel=note.channel,
                track_id=note.track_id
            )

            # Apply quantization
            if quantize_mode != QuantizeMode.OFF:
                quantized_time = self._quantize_time(note.time, quantize_mode)

                # Apply groove template timing offset
                groove_position = self._get_groove_position(note.time, 16)  # 16th note resolution
                groove_offset = template_data.get_offset_for_position(groove_position)

                # Blend quantized time with groove offset
                groove_influence = 0.7  # Groove has strong influence
                final_time = quantized_time + groove_offset * groove_influence

                # Apply quantization strength
                quantized_note.time = note.time * (1.0 - self.quantize_strength) + final_time * self.quantize_strength

            # Apply groove template velocity adjustment
            if groove_template != GrooveTemplate.STRAIGHT:
                groove_position = self._get_groove_position(quantized_note.time, 16)
                velocity_mult = template_data.get_velocity_multiplier(groove_position)

                # Apply velocity adjustment
                quantized_note.velocity = int(min(127, max(1, note.velocity * velocity_mult)))

            # Apply humanization
            if self.humanize_amount > 0:
                quantized_note = self._humanize_note(quantized_note)

            # Apply swing if enabled
            if self.swing_amount > 0 and quantize_mode in [QuantizeMode.Q_8TH, QuantizeMode.Q_16TH]:
                quantized_note.time = self._apply_swing(quantized_note.time, quantize_mode)

            quantized_notes.append(quantized_note)

        return quantized_notes

    def _quantize_time(self, time: float, mode: QuantizeMode) -> float:
        """Quantize a time value according to the mode"""
        if mode == QuantizeMode.OFF:
            return time
        elif mode == QuantizeMode.Q_8TH:
            grid = 0.5  # Half beats (8th notes)
        elif mode == QuantizeMode.Q_16TH:
            grid = 0.25  # Quarter beats (16th notes)
        elif mode == QuantizeMode.Q_32ND:
            grid = 0.125  # Eighth beats (32nd notes)
        elif mode == QuantizeMode.Q_TRIPLET:
            grid = 1.0 / 3.0  # Triplet grid
        elif mode == QuantizeMode.Q_SWING:
            # Swing quantization (alternate between on-beat and slight delay)
            beat_fraction = time % 1.0  # Position within beat
            if beat_fraction < 0.25:  # First 16th
                grid = 0.0
            elif beat_fraction < 0.75:  # Second 16th (swung)
                grid = 0.25 + 0.0625  # Delayed
            else:  # Third 16th
                grid = 0.5
            return time - (beat_fraction % 0.25) + grid
        else:
            return time

        # Standard quantization
        return round(time / grid) * grid

    def _get_groove_position(self, time: float, resolution: int) -> int:
        """Get groove template position for a given time"""
        # Convert time to position within the groove template
        beats_per_measure = 4.0  # Assume 4/4 time
        positions_per_beat = resolution / 4  # 16th notes = 4 positions per beat

        # Get position within measure
        measure_position = time % beats_per_measure
        position_index = int(measure_position * positions_per_beat)

        return position_index % resolution

    def _humanize_note(self, note: NoteEvent) -> NoteEvent:
        """Apply humanization to a note"""
        # Add small random timing variations
        timing_variation = (np.random.random() - 0.5) * 0.05 * self.humanize_amount  # ±2.5% of beat
        humanized_time = note.time + timing_variation

        # Add small velocity variations
        velocity_variation = (np.random.random() - 0.5) * 20 * self.humanize_amount  # ±10 velocity
        humanized_velocity = int(max(1, min(127, note.velocity + velocity_variation)))

        return NoteEvent(
            time=max(0.0, humanized_time),  # Ensure non-negative time
            duration=note.duration,
            note_number=note.note_number,
            velocity=humanized_velocity,
            channel=note.channel,
            track_id=note.track_id
        )

    def _apply_swing(self, time: float, quantize_mode: QuantizeMode) -> float:
        """Apply swing timing to quantized notes"""
        if self.swing_amount == 0:
            return time

        # Determine swing grid based on quantization mode
        if quantize_mode == QuantizeMode.Q_8TH:
            swing_grid = 0.5  # 8th notes
            swing_offset = 0.125 * self.swing_amount  # Up to 1/8 note delay
        elif quantize_mode == QuantizeMode.Q_16TH:
            swing_grid = 0.25  # 16th notes
            swing_offset = 0.0625 * self.swing_amount  # Up to 1/16 note delay
        else:
            return time

        # Apply swing to off-beats
        beat_position = time % 1.0  # Position within beat
        grid_position = round(beat_position / swing_grid) * swing_grid

        # Apply swing to every other grid position
        grid_index = int(grid_position / swing_grid)
        if grid_index % 2 == 1:  # Odd positions get delayed
            return time + swing_offset

        return time

    def create_custom_template(self, name: str, timing_offsets: list[float],
                             velocity_multipliers: list[float] | None = None) -> GrooveTemplate:
        """
        Create a custom groove template.

        Args:
            name: Template name
            timing_offsets: Timing offsets for each 16th note position
            velocity_multipliers: Optional velocity multipliers

        Returns:
            New GrooveTemplate enum value
        """
        # Create new enum value (this is a simplified approach)
        # In a full implementation, you'd extend the enum dynamically
        template_data = GrooveTemplateData(name, timing_offsets, velocity_multipliers)

        # Add to templates dict with a synthetic key
        synthetic_key = f"CUSTOM_{len(self.templates)}"
        self.templates[synthetic_key] = template_data

        # Return synthetic template identifier
        return synthetic_key

    def get_available_templates(self) -> list[tuple[GrooveTemplate, str]]:
        """Get list of available groove templates"""
        return [(template, data.name) for template, data in self.templates.items()]

    def get_template_info(self, template: GrooveTemplate) -> dict[str, Any] | None:
        """Get information about a groove template"""
        if template in self.templates:
            data = self.templates[template]
            return {
                'name': data.name,
                'timing_offsets': data.timing_offsets.tolist(),
                'velocity_multipliers': data.velocity_multipliers.tolist()
            }
        return None

    def analyze_groove(self, notes: list[NoteEvent]) -> dict[str, Any]:
        """
        Analyze the groove characteristics of a sequence of notes.

        Returns groove analysis including swing amount, timing regularity, etc.
        """
        if len(notes) < 4:
            return {'error': 'Need at least 4 notes for groove analysis'}

        # Extract timing information
        times = [note.time for note in notes]
        velocities = [note.velocity for note in notes]

        # Calculate timing intervals
        intervals = []
        for i in range(1, len(times)):
            intervals.append(times[i] - times[i-1])

        if not intervals:
            return {'error': 'No timing intervals found'}

        # Calculate swing amount (simplified)
        swing_amount = 0.0
        swing_count = 0

        for i in range(0, len(intervals) - 1, 2):
            if i + 1 < len(intervals):
                ratio = intervals[i] / intervals[i + 1] if intervals[i + 1] > 0 else 1.0
                if 0.5 < ratio < 2.0:  # Reasonable swing range
                    swing_amount += abs(ratio - 1.0)
                    swing_count += 1

        avg_swing = swing_amount / swing_count if swing_count > 0 else 0.0

        # Calculate timing regularity
        mean_interval = np.mean(intervals)
        std_interval = np.std(intervals)
        regularity = 1.0 - min(1.0, std_interval / mean_interval) if mean_interval > 0 else 0.0

        # Calculate velocity dynamics
        velocity_mean = np.mean(velocities)
        velocity_std = np.std(velocities)
        dynamics = velocity_std / velocity_mean if velocity_mean > 0 else 0.0

        return {
            'swing_amount': avg_swing,
            'timing_regularity': regularity,
            'velocity_dynamics': dynamics,
            'note_count': len(notes),
            'estimated_tempo': 60.0 / mean_interval if mean_interval > 0 else 120.0
        }

    def reset(self):
        """Reset quantizer to default state"""
        self.current_template = GrooveTemplate.STRAIGHT
        self.quantize_strength = 1.0
        self.humanize_amount = 0.0
        self.swing_amount = 0.0
