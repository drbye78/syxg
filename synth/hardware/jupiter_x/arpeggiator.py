"""
Jupiter-X Arpeggiator Implementation

Grid-based arpeggiator system for Jupiter-X with pattern sequencing,
velocity control, and real-time parameter modulation.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

from .constants import *


class JupiterXArpeggiatorPattern:
    """
    Jupiter-X Arpeggiator Pattern

    Grid-based pattern definition supporting up to 8x8 note grid
    with velocity, gate time, and swing controls.
    """

    def __init__(self, pattern_id: int, name: str):
        self.pattern_id = pattern_id
        self.name = name

        # Grid dimensions
        self.grid_width = ARPEGGIATOR_GRID_WIDTH  # 8
        self.grid_height = ARPEGGIATOR_GRID_HEIGHT  # 8

        # Pattern grid: 1 = note on, 0 = note off
        self.grid: list[list[int]] = [
            [0 for _ in range(self.grid_width)] for _ in range(self.grid_height)
        ]

        # ===== PHASE 3: ADVANCED 64-STEP PATTERNS =====
        # Enhanced grid for 64-step patterns (16x8 for 128 steps)
        self.grid_width = 16  # 16 steps per beat (was 8)
        self.grid_height = 8  # 8 rows for notes (was 8)

        # Reinitialize grid for 128 steps (16 beats x 8 steps per beat)
        self.grid: list[list[int]] = [
            [0 for _ in range(self.grid_width)] for _ in range(self.grid_height)
        ]

        # Pattern parameters - enhanced for 64-step support
        self.length_beats = 4.0  # Pattern length in beats (was 1.0)
        self.gate_time = DEFAULT_ARPEGGIATOR_GATE_TIME / 127.0  # 0.0-1.0
        self.swing_amount = DEFAULT_ARPEGGIATOR_SWING / 100.0  # -1.0 to 1.0
        self.octave_range = DEFAULT_ARPEGGIATOR_OCTAVE_RANGE  # 1-4

        # Advanced triggering modes (Phase 3)
        self.trigger_mode = "normal"  # normal, retrigger, legato, alternate
        self.note_order = "up"  # up, down, up-down, random, chord
        self.velocity_mode = "original"  # original, fixed, accent, scale
        self.accent_pattern: list[float] = [1.0] * 64  # Per-step accent (was 16)

        # Pattern looping and sequencing
        self.loop_enabled = True
        self.loop_start = 0
        self.loop_end = 63  # Full 64 steps
        self.current_loop_count = 0
        self.max_loops = -1  # -1 = infinite

        # Advanced timing controls
        self.step_length = 1.0 / 16.0  # 16th notes (was fixed)
        self.humanize_amount = 0.0  # 0.0-1.0 timing randomization
        self.velocity_humanize = 0.0  # 0.0-1.0 velocity randomization

        # Real-time pattern editing
        self.real_time_editing = False
        self.edit_position = 0
        self.edit_velocity = 100

        # Pattern morphing (blend between patterns)
        self.morph_target_pattern = None
        self.morph_factor = 0.0
        self.morph_speed = 0.1

        # Jupiter-X specific features
        self.jx_pattern_type = "melodic"  # melodic, chord, bass, percussion
        self.jx_complexity = "simple"  # simple, complex, evolving
        self.jx_style = "classic"  # classic, modern, experimental

        # Velocity settings
        self.velocity_mode = 0  # 0=Original, 1=Fixed, 2=Accent pattern
        self.fixed_velocity = 100
        # accent_pattern is already initialized above with 64 elements

    def set_grid_cell(self, x: int, y: int, value: int):
        """Set grid cell value (0=off, 1=on)."""
        if 0 <= x < self.grid_width and 0 <= y < self.grid_height:
            self.grid[y][x] = 1 if value > 0 else 0

    def get_grid_cell(self, x: int, y: int) -> int:
        """Get grid cell value."""
        if 0 <= x < self.grid_width and 0 <= y < self.grid_height:
            return self.grid[y][x]
        return 0

    def clear_grid(self):
        """Clear entire grid."""
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                self.grid[y][x] = 0

    def get_active_steps(self, chord_notes: list[int]) -> list[dict[str, Any]]:
        """
        Get all active steps for the current chord.

        Args:
            chord_notes: List of MIDI note numbers in the current chord

        Returns:
            List of step dictionaries with timing and note information
        """
        active_steps = []

        for step in range(self.grid_width):
            step_notes = []

            # Check each grid row for active notes
            for row in range(self.grid_height):
                if self.grid[row][step]:
                    # Convert grid position to note offset
                    note_offset = self._grid_row_to_note_offset(row)
                    step_notes.append(note_offset)

            if step_notes:  # This step has active notes
                # Calculate timing with swing
                base_time = step / self.grid_width
                swing_offset = self._calculate_swing_offset(step)
                step_time = base_time + swing_offset

                # Calculate gate time
                gate_duration = self.gate_time / self.grid_width

                # Generate notes for each active row
                for note_offset in step_notes:
                    # Apply octave range
                    for octave in range(self.octave_range):
                        octave_offset = octave * 12

                        # Calculate velocity
                        velocity = self._calculate_step_velocity(step)

                        step_info = {
                            "step": step_time + (octave * self.length_beats),
                            "note_offset": note_offset + octave_offset,
                            "velocity": velocity,
                            "gate_time": gate_duration,
                            "original_step": step,
                            "octave": octave,
                        }
                        active_steps.append(step_info)

        return sorted(active_steps, key=lambda x: x["step"])

    def _grid_row_to_note_offset(self, row: int) -> int:
        """Convert grid row to note offset from root."""
        # Row 0 = root, Row 1 = +1 semitone, etc.
        return row

    def _calculate_swing_offset(self, step: int) -> float:
        """Calculate swing timing offset for a step."""
        if self.swing_amount == 0:
            return 0.0

        # Apply swing to even-numbered steps (1, 3, 5, 7...)
        if step % 2 == 1:  # Odd steps get delayed
            return self.swing_amount * (1.0 / self.grid_width)
        else:  # Even steps get early
            return -self.swing_amount * (1.0 / self.grid_width) * 0.5

        return 0.0

    def _calculate_step_velocity(self, step: int) -> int:
        """Calculate velocity for a step based on velocity mode."""
        if self.velocity_mode == 0:  # Original
            return 100  # Will be scaled by input velocity
        elif self.velocity_mode == 1:  # Fixed
            return self.fixed_velocity
        else:  # Accent pattern
            pattern_index = step % len(self.accent_pattern)
            return int(self.fixed_velocity * self.accent_pattern[pattern_index])

    def get_pattern_info(self) -> dict[str, Any]:
        """Get comprehensive pattern information."""
        active_cells = sum(sum(row) for row in self.grid)

        return {
            "id": self.pattern_id,
            "name": self.name,
            "grid_size": (self.grid_width, self.grid_height),
            "active_cells": active_cells,
            "length_beats": self.length_beats,
            "gate_time": self.gate_time,
            "swing_amount": self.swing_amount,
            "octave_range": self.octave_range,
            "velocity_mode": self.velocity_mode,
            "fixed_velocity": self.fixed_velocity,
        }


class JupiterXArpeggiatorEngine:
    """
    Jupiter-X Arpeggiator Engine

    Main arpeggiator processing engine with 16 independent arpeggiators,
    pattern library, and real-time control.
    """

    def __init__(self):
        self.lock = threading.RLock()

        # Pattern library
        self.patterns: dict[int, JupiterXArpeggiatorPattern] = {}
        self._initialize_builtin_patterns()

        # Arpeggiator instances (one per part)
        self.arpeggiators: dict[int, JupiterXArpeggiatorInstance] = {}

        # Global settings
        self.master_tempo = DEFAULT_ARPEGGIATOR_TEMPO
        self.tempo_sync = True

        # Callbacks
        self.note_on_callback: Callable | None = None
        self.note_off_callback: Callable | None = None

        print("🎹 Jupiter-X Arpeggiator: Initialized with pattern library")

    def _initialize_builtin_patterns(self):
        """Initialize comprehensive built-in arpeggio patterns (32 total like Jupiter-X)."""
        pattern_id = 0

        # ===== BASIC SEQUENTIAL PATTERNS =====
        basic_patterns = [
            (
                "Up",
                [
                    [1, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                ],
            ),
            (
                "Down",
                [
                    [0, 0, 0, 0, 0, 0, 0, 1],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                ],
            ),
            (
                "Up-Down",
                [
                    [1, 0, 0, 0, 0, 0, 0, 1],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                ],
            ),
            (
                "Random",
                [
                    [1, 0, 1, 0, 0, 1, 0, 0],
                    [0, 1, 0, 0, 1, 0, 0, 1],
                    [0, 0, 0, 1, 0, 0, 1, 0],
                    [1, 0, 0, 0, 0, 1, 0, 1],
                    [0, 1, 0, 1, 0, 0, 0, 0],
                    [0, 0, 1, 0, 1, 0, 1, 0],
                    [1, 0, 0, 1, 0, 1, 0, 0],
                    [0, 1, 0, 0, 1, 0, 0, 1],
                ],
            ),
        ]

        # ===== CHORD-BASED PATTERNS =====
        chord_patterns = [
            (
                "Major Chord",
                [
                    [1, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 1, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 1, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                ],
            ),
            (
                "Minor Chord",
                [
                    [1, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 1, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 1, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                ],
            ),
            (
                "7th Chord",
                [
                    [1, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 1, 0, 0, 0, 0, 0, 0],
                    [0, 0, 1, 0, 0, 0, 0, 0],
                    [0, 0, 0, 1, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                ],
            ),
            (
                "Sus4 Chord",
                [
                    [1, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 1, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 1, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                ],
            ),
        ]

        # ===== RHYTHMIC PATTERNS =====
        rhythmic_patterns = [
            (
                "16th Notes",
                [
                    [1, 1, 1, 1, 1, 1, 1, 1],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                ],
            ),
            (
                "8th Notes",
                [
                    [1, 0, 1, 0, 1, 0, 1, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                ],
            ),
            (
                "Triplet",
                [
                    [1, 0, 0, 1, 0, 0, 1, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                ],
            ),
            (
                "Dotted",
                [
                    [1, 0, 0, 1, 0, 1, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                ],
            ),
        ]

        # ===== COMPLEX POLYRHYTHMIC PATTERNS =====
        complex_patterns = [
            (
                "Polyrhythm 3:4",
                [
                    [1, 0, 1, 0, 1, 0, 0, 0],
                    [0, 1, 0, 1, 0, 0, 1, 0],
                    [0, 0, 0, 0, 0, 1, 0, 1],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                ],
            ),
            (
                "Euclidean 5:8",
                [
                    [1, 0, 1, 0, 1, 0, 1, 0],
                    [0, 1, 0, 1, 0, 1, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 1],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                ],
            ),
            (
                "Broken Chords",
                [
                    [1, 0, 0, 0, 0, 1, 0, 0],
                    [0, 0, 1, 0, 0, 0, 0, 1],
                    [0, 1, 0, 0, 1, 0, 0, 0],
                    [0, 0, 0, 1, 0, 0, 1, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 0],
                ],
            ),
            (
                "Arpeggiated Bass",
                [
                    [1, 0, 0, 0, 0, 0, 1, 0],
                    [0, 1, 0, 0, 0, 0, 0, 0],
                    [0, 0, 1, 0, 0, 0, 0, 0],
                    [0, 0, 0, 1, 0, 0, 0, 0],
                    [0, 0, 0, 0, 1, 0, 0, 0],
                    [0, 0, 0, 0, 0, 1, 0, 0],
                    [0, 0, 0, 0, 0, 0, 1, 0],
                    [0, 0, 0, 0, 0, 0, 0, 1],
                ],
            ),
        ]

        # Combine all pattern categories
        all_patterns = basic_patterns + chord_patterns + rhythmic_patterns + complex_patterns

        # Create patterns with additional variations to reach 32 total
        for name, grid_data in all_patterns:
            pattern = JupiterXArpeggiatorPattern(pattern_id, name)
            for y, row in enumerate(grid_data):
                for x, cell in enumerate(row):
                    pattern.set_grid_cell(x, y, cell)
            self.patterns[pattern_id] = pattern
            pattern_id += 1

        # Add variations of existing patterns to reach 32 total
        base_patterns = list(self.patterns.values())[:4]  # Use first 4 as bases
        variation_names = [
            "Variation 1",
            "Variation 2",
            "Variation 3",
            "Variation 4",
            "Alt 1",
            "Alt 2",
            "Alt 3",
            "Alt 4",
            "Mod 1",
            "Mod 2",
            "Mod 3",
            "Mod 4",
        ]

        for i, base_pattern in enumerate(base_patterns):
            for j, var_name in enumerate(variation_names):
                if pattern_id >= 32:  # Limit to 32 patterns
                    break

                # Create variation by shifting or inverting the pattern
                pattern = JupiterXArpeggiatorPattern(pattern_id, f"{base_pattern.name} {var_name}")

                for y in range(pattern.grid_height):
                    for x in range(pattern.grid_width):
                        original = base_pattern.get_grid_cell(x, y)

                        # Apply variations
                        if "Variation" in var_name:
                            # Shift pattern
                            shift_x = j % 4
                            new_x = (x + shift_x) % pattern.grid_width
                            pattern.set_grid_cell(new_x, y, original)
                        elif "Alt" in var_name:
                            # Invert pattern
                            pattern.set_grid_cell(x, y, 1 - original)
                        elif "Mod" in var_name:
                            # Sparse variation
                            if (x + y + j) % 3 == 0:
                                pattern.set_grid_cell(x, y, original)

                self.patterns[pattern_id] = pattern
                pattern_id += 1

    def get_arpeggiator(self, part_number: int) -> JupiterXArpeggiatorInstance | None:
        """Get or create arpeggiator instance for a part."""
        with self.lock:
            if part_number not in self.arpeggiators:
                arpeggiator = JupiterXArpeggiatorInstance(part_number, self)
                # Set default pattern to "Up" (pattern 0)
                if 0 in self.patterns:
                    arpeggiator.set_pattern(self.patterns[0])
                self.arpeggiators[part_number] = arpeggiator
            return self.arpeggiators[part_number]

    def set_pattern(self, part_number: int, pattern_id: int) -> bool:
        """Set arpeggiator pattern for a part."""
        with self.lock:
            arpeggiator = self.get_arpeggiator(part_number)
            if arpeggiator and pattern_id in self.patterns:
                arpeggiator.set_pattern(self.patterns[pattern_id])
                return True
        return False

    def enable_arpeggiator(self, part_number: int, enabled: bool) -> bool:
        """Enable/disable arpeggiator for a part."""
        with self.lock:
            arpeggiator = self.get_arpeggiator(part_number)
            if arpeggiator:
                arpeggiator.enabled = enabled
                if not enabled:
                    arpeggiator.stop()
                return True
        return False

    def process_note_on(self, part_number: int, note: int, velocity: int):
        """Process note-on event through arpeggiator."""
        with self.lock:
            arpeggiator = self.get_arpeggiator(part_number)
            if arpeggiator:
                arpeggiator.note_on(note, velocity)

    def process_note_off(self, part_number: int, note: int):
        """Process note-off event through arpeggiator."""
        with self.lock:
            arpeggiator = self.get_arpeggiator(part_number)
            if arpeggiator:
                arpeggiator.note_off(note)

    def get_pattern_list(self) -> list[dict[str, Any]]:
        """Get list of available patterns."""
        with self.lock:
            return [pattern.get_pattern_info() for pattern in self.patterns.values()]

    def create_pattern(self, name: str) -> JupiterXArpeggiatorPattern:
        """Create a new empty pattern."""
        with self.lock:
            pattern_id = max(self.patterns.keys()) + 1 if self.patterns else 0
            pattern = JupiterXArpeggiatorPattern(pattern_id, name)
            self.patterns[pattern_id] = pattern
            return pattern

    def __str__(self) -> str:
        """String representation."""
        return f"JupiterXArpeggiatorEngine(patterns={len(self.patterns)}, active={len(self.arpeggiators)})"


class JupiterXArpeggiatorInstance:
    """
    Individual Jupiter-X Arpeggiator Instance

    Manages pattern playback, timing, and note scheduling for one part.
    """

    def __init__(self, part_number: int, engine: JupiterXArpeggiatorEngine):
        self.part_number = part_number
        self.engine = engine

        # State
        self.enabled = False
        self.current_pattern: JupiterXArpeggiatorPattern | None = None

        # Chord detection
        self.active_notes: dict[int, int] = {}  # note -> velocity
        self.current_root_note = None

        # Playback state
        self.current_step = 0.0
        self.pattern_start_time = 0.0
        self.active_arpeggio_notes: list[dict[str, Any]] = []

        # Timing
        self.step_duration = 0.125  # 16th notes at 120 BPM
        self.last_step_time = 0.0

        # Thread safety
        self.lock = threading.RLock()

    def set_pattern(self, pattern: JupiterXArpeggiatorPattern):
        """Set the current arpeggio pattern."""
        with self.lock:
            self.current_pattern = pattern

    def note_on(self, note: int, velocity: int):
        """Handle note-on event."""
        with self.lock:
            self.active_notes[note] = velocity

            if not self.enabled or not self.current_pattern:
                # Pass through to normal synthesis
                if self.engine.note_on_callback:
                    self.engine.note_on_callback(self.part_number, note, velocity)
                return

            # Update chord and restart pattern
            self._update_chord()
            self._start_pattern()

    def note_off(self, note: int):
        """Handle note-off event."""
        with self.lock:
            if note in self.active_notes:
                del self.active_notes[note]

            if not self.active_notes:
                # No notes left, stop arpeggio
                self._stop_pattern()
            else:
                # Update chord with remaining notes
                self._update_chord()

    def _update_chord(self):
        """Update current chord from active notes."""
        if not self.active_notes:
            self.current_root_note = None
            return

        # Find root note (lowest active note)
        self.current_root_note = min(self.active_notes.keys())

    def _start_pattern(self):
        """Start pattern playback."""
        if not self.current_pattern or not self.current_root_note:
            return

        self.pattern_start_time = time.time()
        self.current_step = 0.0
        self.last_step_time = 0.0

        # Generate initial arpeggio notes
        self._generate_arpeggio_notes()

    def _stop_pattern(self):
        """Stop pattern playback."""
        self.current_step = 0.0
        self.active_arpeggio_notes.clear()

    def _generate_arpeggio_notes(self):
        """Generate arpeggio note sequence."""
        if not self.current_pattern or self.current_root_note is None:
            return

        # Get all notes in current chord
        chord_notes = list(self.active_notes.keys())

        # Get active steps from pattern
        active_steps = self.current_pattern.get_active_steps(chord_notes)

        # Convert to absolute notes and schedule
        self.active_arpeggio_notes = []
        for step_info in active_steps:
            absolute_note = self.current_root_note + step_info["note_offset"]

            # Ensure note is in valid MIDI range
            if 0 <= absolute_note <= 127:
                arpeggio_note = {
                    "note": absolute_note,
                    "velocity": step_info["velocity"],
                    "step_time": step_info["step"],
                    "gate_time": step_info["gate_time"],
                    "scheduled": False,
                }
                self.active_arpeggio_notes.append(arpeggio_note)

    def process_timing(self, current_time: float):
        """Process timing for arpeggio playback."""
        with self.lock:
            if not self.enabled or not self.current_pattern or not self.active_arpeggio_notes:
                return

            # Calculate step duration based on tempo
            tempo_bpm = self.engine.master_tempo
            self.step_duration = 60.0 / tempo_bpm / 4.0  # 16th note duration

            # Process each scheduled note
            for arpeggio_note in self.active_arpeggio_notes:
                if not arpeggio_note["scheduled"]:
                    note_time = self.pattern_start_time + (
                        arpeggio_note["step_time"] * self.step_duration * 4
                    )

                    if current_time >= note_time:
                        # Trigger note
                        velocity = arpeggio_note["velocity"]
                        if self.engine.note_on_callback:
                            self.engine.note_on_callback(
                                self.part_number, arpeggio_note["note"], velocity
                            )

                        arpeggio_note["scheduled"] = True
                        arpeggio_note["trigger_time"] = current_time

                        # Schedule note-off
                        gate_duration = arpeggio_note["gate_time"] * self.step_duration * 4
                        arpeggio_note["off_time"] = current_time + gate_duration

                elif "off_time" in arpeggio_note and current_time >= arpeggio_note["off_time"]:
                    # Trigger note-off
                    if self.engine.note_off_callback:
                        self.engine.note_off_callback(self.part_number, arpeggio_note["note"])

                    # Remove from active notes
                    arpeggio_note["completed"] = True

            # Remove completed notes
            self.active_arpeggio_notes = [
                n for n in self.active_arpeggio_notes if not n.get("completed", False)
            ]

            # Check if pattern should loop
            pattern_duration = self.current_pattern.length_beats * self.step_duration * 4
            if current_time - self.pattern_start_time >= pattern_duration:
                # Loop pattern
                self._start_pattern()

    def stop(self):
        """Stop the arpeggiator and clear all active notes."""
        with self.lock:
            self.enabled = False
            self._stop_pattern()

    def get_status(self) -> dict[str, Any]:
        """Get arpeggiator status."""
        with self.lock:
            return {
                "enabled": self.enabled,
                "pattern": self.current_pattern.name if self.current_pattern else None,
                "active_notes": len(self.active_notes),
                "current_root": self.current_root_note,
                "active_arpeggio_notes": len(self.active_arpeggio_notes),
                "current_step": self.current_step,
            }
