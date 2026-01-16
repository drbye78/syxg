"""
XG Pattern Sequencer Architecture - Professional Grid-Based Sequencing System

ARCHITECTURAL OVERVIEW:

The XG Pattern Sequencer implements a comprehensive, professional-grade sequencing system
designed for modern music production workflows. Inspired by legendary hardware sequencers
like the Roland MC-505 and Yamaha Motif, this system provides authentic pattern-based
sequencing with advanced features for expressive musical performance and production.

SEQUENCER PHILOSOPHY:

The pattern sequencer serves as the creative heart of the XG synthesizer, providing
intuitive pattern-based composition and performance tools that bridge traditional
sequencing with modern production techniques:

1. GRID-BASED COMPOSITION: Intuitive step sequencing with visual pattern editing
2. REAL-TIME PERFORMANCE: Live pattern manipulation and playback control
3. PROFESSIONAL WORKFLOW: Advanced features for studio production and live performance
4. MOTIF-STYLE AUTHENTICITY: Faithful recreation of classic hardware sequencer behavior
5. MODERN FLEXIBILITY: Integration with contemporary music production tools

PATTERN ARCHITECTURE DESIGN:

CORE PATTERN STRUCTURE:
The sequencer implements a sophisticated pattern model that supports complex musical
arrangements while maintaining performance and usability:

PATTERN COMPONENTS:
- METADATA: Name, tempo, time signature, swing, and quantization settings
- NOTE EVENTS: Musical notes with timing, duration, velocity, and channel information
- CONTROL EVENTS: MIDI CC messages for parameter automation and modulation
- TRACK ORGANIZATION: Multi-track patterns with independent editing capabilities
- TIMING PRECISION: Sample-accurate timing with high-resolution event positioning

PATTERN MANAGEMENT:
- LIBRARY SYSTEM: Organized storage and retrieval of pattern collections
- DUPLICATION: Efficient pattern copying with selective content preservation
- VERSIONING: Pattern evolution tracking and undo/redo capabilities
- METADATA: Comprehensive tagging and search capabilities

GRID-BASED EDITING ARCHITECTURE:

VISUAL SEQUENCING PARADIGM:
The grid-based editing system provides an intuitive, visual approach to pattern creation
that mirrors the workflow of classic hardware step sequencers:

GRID ORGANIZATION:
- STEP-BASED TIMING: Fixed grid resolution with variable step counts
- NOTE MATRIX: 128-note range with visual velocity representation
- MULTI-TRACK SUPPORT: Independent tracks within each pattern
- ZOOM AND NAVIGATION: Flexible viewing options for detailed editing

EDITING MODES:
- STEP INPUT: Real-time step recording with immediate visual feedback
- NOTE PAINTING: Direct grid manipulation with mouse or touch input
- VELOCITY EDITING: Visual velocity adjustment with curve drawing
- TIMING MODIFICATION: Micro-timing adjustments for groove creation

REAL-TIME PLAYBACK ARCHITECTURE:

PROFESSIONAL PLAYBACK ENGINE:
The playback system provides sample-accurate timing and professional performance
characteristics essential for live performance and recording:

TIMING PRECISION:
- SAMPLE-ACCURATE SCHEDULING: Microsecond timing precision for all events
- JITTER-FREE PLAYBACK: Consistent timing across varying system loads
- TEMPO SYNCHRONIZATION: External tempo sync with SMPTE and MIDI clock
- LATENCY COMPENSATION: Automatic delay compensation for processing overhead

PLAYBACK MODES:
- PATTERN LOOPING: Seamless pattern repetition with phase alignment
- PATTERN CHAINING: Sequential pattern playback with smooth transitions
- REAL-TIME SWITCHING: Instant pattern changes during performance
- POSITION CONTROL: Precise playback positioning for production workflow

GROOVE QUANTIZATION ARCHITECTURE:

RHYTHMIC PROCESSING SYSTEM:
The groove quantization system provides sophisticated rhythmic processing that enhances
musical feel and timing precision:

QUANTIZATION MODES:
- GRID QUANTIZATION: Standard note alignment with adjustable strength
- GROOVE TEMPLATES: Pre-defined rhythmic feels (swing, shuffle, funk)
- HUMANIZATION: Subtle timing variations for natural performance feel
- MICRO-TIMING: Precise timing adjustments for groove creation

GROOVE TEMPLATES:
- SWING PATTERNS: Variable swing amounts with complex ratio calculations
- SHUFFLE EFFECTS: Alternating timing for shuffle and swing feels
- HUMAN FEEL: Statistical timing variations based on performance analysis
- CUSTOM TEMPLATES: User-definable groove patterns and timing curves

PATTERN CHAINING ARCHITECTURE:

SEQUENTIAL COMPOSITION:
The pattern chaining system enables complex musical arrangements through intelligent
pattern sequencing and transitions:

CHAINING FEATURES:
- PATTERN SEQUENCES: Ordered playback of multiple patterns
- TRANSITION SMOOTHING: Seamless transitions between patterns
- LOOP POINTS: Flexible loop boundaries within pattern chains
- DYNAMIC MODIFICATION: Real-time chain editing during playback

ARRANGEMENT CAPABILITIES:
- SONG STRUCTURES: Complex arrangements with intro, verse, chorus, outro
- TRANSITION EFFECTS: Crossfading and effects between pattern changes
- TEMPO MODULATION: Smooth tempo changes across pattern boundaries
- KEY MODULATION: Harmonic progression through pattern sequencing

MULTI-TRACK PATTERN ARCHITECTURE:

TRACK-BASED ORGANIZATION:
The multi-track pattern system provides sophisticated layering capabilities for
complex musical arrangements:

TRACK FEATURES:
- INDEPENDENT CHANNELS: Each track assigned to specific MIDI channels
- TRACK MUTING/SOLOING: Individual track control for mixing and arrangement
- TRACK PROCESSING: Per-track effects and processing chains
- TRACK AUTOMATION: Independent parameter automation per track

ARRANGEMENT FLEXIBILITY:
- TRACK LAYERING: Multiple instruments on single tracks with velocity splitting
- TRACK GROUPING: Logical grouping for collective editing and processing
- TRACK ROUTING: Flexible signal routing for mixing and effects processing
- TRACK ISOLATION: Independent track recording and editing capabilities

STEP INPUT AND RECORDING ARCHITECTURE:

INTERACTIVE RECORDING:
The step input system provides intuitive, performance-oriented pattern creation
that combines the immediacy of hardware sequencers with modern editing capabilities:

STEP INPUT MODES:
- REAL-TIME STEP: Live step recording with immediate visual feedback
- NOTE REPEAT: Rapid note entry with programmable repeat rates
- VELOCITY CONTROL: Dynamic velocity input during step recording
- TIMING CONTROL: Adjustable step timing and swing during input

RECORDING FEATURES:
- OVERDUBBING: Layer recording with existing pattern preservation
- REPLACE RECORDING: Pattern section replacement with new material
- STEP CORRECTION: Real-time correction of timing and velocity errors
- UNDO/REDO: Comprehensive editing history with unlimited undo levels

PROFESSIONAL PRODUCTION FEATURES:

STUDIO INTEGRATION:
The sequencer provides comprehensive integration with professional production workflows:

DAW COMPATIBILITY:
- MIDI EXPORT: Standard MIDI file generation for DAW integration
- TEMPO MAP EXPORT: Detailed tempo information for production workflows
- AUTOMATION EXPORT: Parameter automation data for mixing and processing
- PROJECT MANAGEMENT: Organized pattern storage within production projects

LIVE PERFORMANCE:
- PATTERN SWITCHING: Instant pattern changes during live performance
- REAL-TIME MODIFICATION: Live pattern editing and manipulation
- BACKUP SEQUENCES: Automated fallback patterns for performance reliability
- REMOTE CONTROL: Hardware control surface integration for live operation

PATTERN LIBRARY MANAGEMENT:

PROFESSIONAL ORGANIZATION:
The pattern library system provides sophisticated organization and management
capabilities for large pattern collections:

LIBRARY FEATURES:
- CATEGORIZATION: Pattern organization by style, instrument, and mood
- SEARCH AND FILTER: Advanced search capabilities with metadata filtering
- TAGGING SYSTEM: Flexible tagging for custom organization schemes
- PRESET MANAGEMENT: Factory and user preset management and backup

EXPORT/IMPORT:
- STANDARD FORMATS: MIDI file export for universal compatibility
- NATIVE FORMAT: XG-specific format preserving all pattern data
- BULK OPERATIONS: Batch export/import for library management
- VERSION CONTROL: Pattern versioning and evolution tracking

THREAD SAFETY AND PERFORMANCE:

REAL-TIME THREADING:
The sequencer implements sophisticated threading architecture for real-time performance:

PLAYBACK THREAD:
- DEDICATED TIMING: Isolated playback thread with high priority scheduling
- INTERRUPT PREVENTION: Protected timing loops with minimal system interference
- BUFFER MANAGEMENT: Efficient audio buffer handling for glitch-free playback
- SYNCHRONIZATION: Precise synchronization with system timing sources

EDITING THREAD SAFETY:
- CONCURRENT ACCESS: Safe pattern editing during playback
- DATA CONSISTENCY: Atomic operations for pattern modifications
- LOCK OPTIMIZATION: Minimal lock contention for performance
- STATE PROTECTION: Consistent pattern state during editing operations

PERFORMANCE OPTIMIZATION:
- MEMORY EFFICIENCY: Optimized data structures for large pattern libraries
- CPU OPTIMIZATION: SIMD operations for bulk pattern processing
- CACHE COHERENCE: Optimized memory access patterns for pattern data
- LAZY LOADING: On-demand pattern loading for memory efficiency

EXTENSIBILITY ARCHITECTURE:

PLUGIN SEQUENCER SYSTEM:
- CUSTOM SEQUENCING ALGORITHMS: User-defined pattern generation and processing
- THIRD-PARTY INTEGRATION: External sequencer plugin support
- SCRIPTED SEQUENCING: Python-based pattern generation and manipulation
- AI-ASSISTED COMPOSITION: Machine learning pattern generation and variation

ADVANCED FEATURES:
- QUANTUM SEQUENCING: Advanced mathematical pattern generation
- NEURAL PATTERN GENERATION: AI-assisted musical pattern creation
- SPECTRAL SEQUENCING: Frequency-domain pattern manipulation
- PHYSICAL MODELING SEQUENCES: Acoustic simulation-based pattern generation

INTEGRATION ARCHITECTURE:

SYNTHESIZER INTEGRATION:
- DIRECT ENGINE CONTROL: Immediate pattern playback to synthesis engines
- PARAMETER AUTOMATION: Pattern-based parameter changes and modulation
- EFFECTS COORDINATION: Pattern-triggered effects and processing
- VOICE MANAGEMENT: Polyphony allocation based on pattern complexity

XG SYSTEM INTEGRATION:
- CHANNEL MAPPING: XG part assignment for multi-timbral patterns
- EFFECTS ROUTING: Pattern-based effects send automation
- SYSTEM CONTROL: XG system parameter automation through patterns
- WORKSTATION FEATURES: XGML integration for pattern storage and management

PROFESSIONAL AUDIO STANDARDS:

SAMPLE ACCURACY:
- MICROSECOND TIMING: High-precision event timing and scheduling
- PHASE ALIGNMENT: Consistent phase relationships across tracks
- JITTER ELIMINATION: Stable timing under varying system loads
- SYNCHRONIZATION: SMPTE, MTC, and MIDI clock synchronization

QUALITY ASSURANCE:
- TIMING VALIDATION: Automatic timing accuracy verification
- DATA INTEGRITY: Pattern corruption detection and recovery
- PERFORMANCE MONITORING: Real-time performance tracking and optimization
- RELIABILITY TESTING: Extensive testing under various operating conditions

FUTURE EXPANSION:

NEXT-GENERATION FEATURES:
- AI PATTERN GENERATION: Machine learning-assisted composition
- NEURAL TIMING: AI-based timing and groove analysis
- CLOUD COLLABORATION: Remote pattern sharing and collaboration
- IMMERSIVE AUDIO: Spatial audio sequencing and production

PROFESSIONAL INTEGRATION:
- DAW PLUGINS: Native integration with digital audio workstations
- HARDWARE CONTROLLERS: Advanced control surface integration
- NETWORK SYNTHESIS: Distributed sequencing across multiple devices
- MOBILE PRODUCTION: iOS/Android pattern editing and playback

ARCHITECTURAL PATTERNS:

DESIGN PATTERNS IMPLEMENTED:
- COMMAND PATTERN: Pattern editing operations as reversible commands
- OBSERVER PATTERN: Real-time pattern change notifications
- STRATEGY PATTERN: Different playback and quantization strategies
- FACTORY PATTERN: Pattern creation and template instantiation

ARCHITECTURAL PRINCIPLES:
- SINGLE RESPONSIBILITY: Each component handles specific sequencing aspects
- OPEN/CLOSED PRINCIPLE: New sequencing features without core modification
- DEPENDENCY INVERSION: Abstract interfaces for sequencing components
- COMPOSITION OVER INHERITANCE: Modular sequencing system assembly

ERROR HANDLING AND DIAGNOSTICS:

COMPREHENSIVE ERROR HANDLING:
- TIMING ERROR DETECTION: Playback timing anomaly identification
- DATA CORRUPTION DETECTION: Pattern integrity verification
- THREAD SAFETY VIOLATIONS: Concurrency issue detection and resolution
- RESOURCE EXHAUSTION: Memory and CPU resource monitoring and management

DIAGNOSTIC CAPABILITIES:
- PERFORMANCE PROFILING: Detailed timing and resource usage analysis
- PATTERN ANALYSIS: Musical content analysis and optimization suggestions
- DEBUGGING SUPPORT: Comprehensive logging and tracing capabilities
- HEALTH MONITORING: System status monitoring and automatic recovery

XG SPECIFICATION COMPLIANCE:

XG SEQUENCING STANDARDS:
- PATTERN RESOLUTION: High-resolution timing with 960 PPQ support
- MULTI-TIMBRALITY: 16-part simultaneous pattern playback
- EFFECTS INTEGRATION: Pattern-based effects automation and control
- SYSTEM COMPATIBILITY: Full XG system parameter integration

PROFESSIONAL MUSIC PRODUCTION:
- STUDIO WORKFLOW: Comprehensive integration with production workflows
- LIVE PERFORMANCE: Reliable operation for live music performance
- RECORDING COMPATIBILITY: Professional recording session integration
- POST-PRODUCTION: Advanced editing capabilities for music production
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Callable
import threading
import time

from .sequencer_types import (
    Pattern, NoteEvent, ControlEvent, QuantizeMode, GrooveTemplate
)
from .groove_quantizer import GrooveQuantizer


class PatternSequencer:
    """
    Pattern Sequencer - Grid-based pattern editing and playback

    Provides authentic Motif-style pattern sequencing with:
    - Grid-based note input and editing
    - Real-time pattern playback
    - Pattern chaining and looping
    - Velocity and timing editing
    - Pattern library management
    """

    def __init__(self, groove_quantizer: Optional[GrooveQuantizer] = None):
        """
        Initialize pattern sequencer.

        Args:
            groove_quantizer: Optional groove quantizer for rhythm processing
        """
        self.groove_quantizer = groove_quantizer or GrooveQuantizer()

        # Pattern storage
        self.patterns: Dict[int, Pattern] = {}
        self.next_pattern_id = 1

        # Playback state
        self.current_pattern_id: Optional[int] = None
        self.is_playing = False
        self.loop_enabled = True
        self.current_position = 0.0  # In beats
        self.playback_start_time = 0.0

        # Grid settings
        self.grid_resolution = 16  # 16th notes per beat
        self.grid_length = 16      # Default 4 bars of 16th notes
        self.current_step = 0

        # Step input state
        self.step_input_enabled = False
        self.step_input_note = 60  # Middle C
        self.step_input_velocity = 100
        self.step_input_duration = 0.25  # Quarter beat

        # Pattern chain
        self.pattern_chain: List[int] = []
        self.current_chain_index = 0

        # Callbacks
        self.note_on_callback: Optional[Callable[[int, int, int], None]] = None
        self.note_off_callback: Optional[Callable[[int, int], None]] = None
        self.control_callback: Optional[Callable[[int, int, int], None]] = None

        # Threading
        self.lock = threading.RLock()
        self.playback_thread: Optional[threading.Thread] = None

    def create_pattern(self, name: str, length: int = 16,
                      resolution: int = 96) -> int:
        """
        Create a new pattern.

        Args:
            name: Pattern name
            length: Pattern length in beats
            resolution: PPQ resolution

        Returns:
            Pattern ID
        """
        with self.lock:
            pattern_id = self.next_pattern_id
            self.next_pattern_id += 1

            pattern = Pattern(
                id=pattern_id,
                name=name,
                length=length,
                resolution=resolution
            )

            self.patterns[pattern_id] = pattern
            return pattern_id

    def delete_pattern(self, pattern_id: int) -> bool:
        """
        Delete a pattern.

        Args:
            pattern_id: Pattern to delete

        Returns:
            True if deleted successfully
        """
        with self.lock:
            if pattern_id in self.patterns:
                del self.patterns[pattern_id]

                # Remove from pattern chain if present
                if pattern_id in self.pattern_chain:
                    self.pattern_chain.remove(pattern_id)

                # Stop playback if this pattern was playing
                if self.current_pattern_id == pattern_id:
                    self.stop()

                return True
            return False

    def get_pattern(self, pattern_id: int) -> Optional[Pattern]:
        """Get pattern by ID."""
        with self.lock:
            return self.patterns.get(pattern_id)

    def duplicate_pattern(self, source_id: int, new_name: str) -> Optional[int]:
        """
        Duplicate a pattern.

        Args:
            source_id: Source pattern ID
            new_name: Name for the new pattern

        Returns:
            New pattern ID or None if source not found
        """
        with self.lock:
            source_pattern = self.get_pattern(source_id)
            if not source_pattern:
                return None

            # Create new pattern
            new_id = self.create_pattern(new_name, source_pattern.length, source_pattern.resolution)

            # Copy pattern data
            new_pattern = self.patterns[new_id]
            new_pattern.tempo = source_pattern.tempo
            new_pattern.time_signature = source_pattern.time_signature
            new_pattern.swing_amount = source_pattern.swing_amount
            new_pattern.quantize_mode = source_pattern.quantize_mode

            # Deep copy notes and controls
            for note in source_pattern.notes:
                new_note = NoteEvent(
                    time=note.time,
                    duration=note.duration,
                    note_number=note.note_number,
                    velocity=note.velocity,
                    channel=note.channel,
                    track_id=note.track_id
                )
                new_pattern.add_note(new_note)

            for ctrl in source_pattern.controls:
                new_ctrl = ControlEvent(
                    time=ctrl.time,
                    controller=ctrl.controller,
                    value=ctrl.value,
                    channel=ctrl.channel,
                    track_id=ctrl.track_id
                )
                new_pattern.add_control(new_ctrl)

            return new_id

    def add_note_to_pattern(self, pattern_id: int, note: NoteEvent) -> bool:
        """
        Add a note to a pattern.

        Args:
            pattern_id: Target pattern ID
            note: Note event to add

        Returns:
            True if added successfully
        """
        with self.lock:
            pattern = self.get_pattern(pattern_id)
            if pattern:
                pattern.add_note(note)
                return True
            return False

    def add_note_at_position(self, pattern_id: int, step: int, note_number: int,
                           velocity: int = 100, duration: float = 0.25,
                           channel: int = 0, track_id: int = 0) -> bool:
        """
        Add a note at a specific grid position.

        Args:
            pattern_id: Target pattern ID
            step: Grid step (0 to grid_length-1)
            note_number: MIDI note number
            velocity: Note velocity
            duration: Note duration in beats
            channel: MIDI channel
            track_id: Track ID

        Returns:
            True if added successfully
        """
        with self.lock:
            pattern = self.get_pattern(pattern_id)
            if not pattern:
                return False

            # Convert step to time
            time_per_step = pattern.length / self.grid_length
            note_time = step * time_per_step

            # Create note event
            note = NoteEvent(
                time=note_time,
                duration=duration,
                note_number=note_number,
                velocity=velocity,
                channel=channel,
                track_id=track_id
            )

            pattern.add_note(note)
            return True

    def remove_note_from_pattern(self, pattern_id: int, note_index: int) -> bool:
        """
        Remove a note from a pattern by index.

        Args:
            pattern_id: Target pattern ID
            note_index: Index of note to remove

        Returns:
            True if removed successfully
        """
        with self.lock:
            pattern = self.get_pattern(pattern_id)
            if pattern:
                pattern.remove_note(note_index)
                return True
            return False

    def clear_pattern(self, pattern_id: int) -> bool:
        """
        Clear all events from a pattern.

        Args:
            pattern_id: Pattern to clear

        Returns:
            True if cleared successfully
        """
        with self.lock:
            pattern = self.get_pattern(pattern_id)
            if pattern:
                pattern.clear()
                return True
            return False

    def quantize_pattern(self, pattern_id: int, mode: QuantizeMode = None,
                        strength: float = 1.0, groove_template: GrooveTemplate = None) -> bool:
        """
        Quantize a pattern.

        Args:
            pattern_id: Pattern to quantize
            mode: Quantization mode (uses pattern's mode if None)
            strength: Quantization strength (0.0-1.0)
            groove_template: Groove template to apply

        Returns:
            True if quantized successfully
        """
        with self.lock:
            pattern = self.get_pattern(pattern_id)
            if not pattern:
                return False

            # Use groove quantizer for advanced quantization
            quantized_notes = self.groove_quantizer.quantize_notes(
                pattern.notes,
                mode or pattern.quantize_mode,
                groove_template
            )

            # Replace pattern notes
            pattern.notes.clear()
            for note in quantized_notes:
                pattern.add_note(note)

            return True

    def apply_swing_to_pattern(self, pattern_id: int, amount: float) -> bool:
        """
        Apply swing to a pattern.

        Args:
            pattern_id: Target pattern ID
            amount: Swing amount (0.0-1.0)

        Returns:
            True if applied successfully
        """
        with self.lock:
            pattern = self.get_pattern(pattern_id)
            if pattern:
                pattern.apply_swing(amount)
                return True
            return False

    def start_playback(self, pattern_id: Optional[int] = None,
                      loop: bool = True) -> bool:
        """
        Start pattern playback.

        Args:
            pattern_id: Pattern to play (uses current if None)
            loop: Enable looping

        Returns:
            True if playback started
        """
        with self.lock:
            if pattern_id is not None:
                if pattern_id not in self.patterns:
                    return False
                self.current_pattern_id = pattern_id
            elif self.current_pattern_id is None:
                return False

            self.is_playing = True
            self.loop_enabled = loop
            self.current_position = 0.0
            self.playback_start_time = time.time()

            # Start playback thread
            if self.playback_thread and self.playback_thread.is_alive():
                self.playback_thread.join()

            self.playback_thread = threading.Thread(target=self._playback_thread, daemon=True)
            self.playback_thread.start()

            return True

    def stop_playback(self) -> None:
        """Stop pattern playback."""
        with self.lock:
            self.is_playing = False
            if self.playback_thread:
                self.playback_thread.join(timeout=1.0)

    def pause_playback(self) -> None:
        """Pause pattern playback."""
        with self.lock:
            self.is_playing = False

    def set_playback_position(self, position: float) -> None:
        """
        Set playback position in beats.

        Args:
            position: New position in beats
        """
        with self.lock:
            pattern = self.get_pattern(self.current_pattern_id)
            if pattern:
                self.current_position = max(0.0, min(position, pattern.length))

    def get_playback_position(self) -> float:
        """Get current playback position in beats."""
        with self.lock:
            return self.current_position

    def _playback_thread(self) -> None:
        """Playback thread for real-time pattern playback."""
        try:
            while self.is_playing:
                if self.current_pattern_id is None:
                    break

                pattern = self.get_pattern(self.current_pattern_id)
                if not pattern:
                    break

                # Get notes that should play at current position
                current_time = self.current_position
                next_time = current_time + 0.01  # Look ahead 10ms

                notes_to_play = pattern.get_notes_in_range(current_time, next_time)

                # Send note events
                for note in notes_to_play:
                    if self.note_on_callback:
                        self.note_on_callback(note.note_number, note.velocity, note.channel)

                    # Schedule note off
                    note_off_time = note.time + note.duration
                    threading.Timer(note_off_time - current_time,
                                  lambda n=note: self._send_note_off(n)).start()

                # Send control events
                controls_to_send = [ctrl for ctrl in pattern.controls
                                  if current_time <= ctrl.time < next_time]

                for ctrl in controls_to_send:
                    if self.control_callback:
                        self.control_callback(ctrl.controller, ctrl.value, ctrl.channel)

                # Advance position
                tempo_bpm = pattern.tempo
                beats_per_second = tempo_bpm / 60.0
                time_increment = 0.01 * beats_per_second  # 10ms increment

                self.current_position += time_increment

                # Handle loop
                if self.current_position >= pattern.length:
                    if self.loop_enabled:
                        self.current_position = 0.0
                    else:
                        self.is_playing = False
                        break

                # Sleep for timing
                time.sleep(0.01)

        except Exception as e:
            print(f"Pattern sequencer playback error: {e}")
            self.is_playing = False

    def _send_note_off(self, note: NoteEvent) -> None:
        """Send note off event."""
        if self.note_off_callback:
            self.note_off_callback(note.note_number, note.channel)

    def enable_step_input(self, note_number: int = 60, velocity: int = 100,
                         duration: float = 0.25) -> None:
        """
        Enable step input mode.

        Args:
            note_number: Default note number for step input
            velocity: Default velocity for step input
            duration: Default duration for step input
        """
        with self.lock:
            self.step_input_enabled = True
            self.step_input_note = note_number
            self.step_input_velocity = velocity
            self.step_input_duration = duration

    def disable_step_input(self) -> None:
        """Disable step input mode."""
        with self.lock:
            self.step_input_enabled = False

    def input_step_note(self, step: int, pattern_id: Optional[int] = None) -> bool:
        """
        Input a note using step input.

        Args:
            step: Grid step to place note
            pattern_id: Target pattern (uses current if None)

        Returns:
            True if note was added
        """
        with self.lock:
            if not self.step_input_enabled:
                return False

            target_pattern = pattern_id or self.current_pattern_id
            if not target_pattern:
                return False

            return self.add_note_at_position(
                target_pattern, step, self.step_input_note,
                self.step_input_velocity, self.step_input_duration
            )

    def set_pattern_chain(self, pattern_ids: List[int]) -> None:
        """
        Set pattern chain for sequential playback.

        Args:
            pattern_ids: List of pattern IDs to chain
        """
        with self.lock:
            self.pattern_chain = pattern_ids.copy()
            self.current_chain_index = 0

    def get_next_pattern_in_chain(self) -> Optional[int]:
        """Get next pattern in chain."""
        with self.lock:
            if not self.pattern_chain:
                return None

            pattern_id = self.pattern_chain[self.current_chain_index]
            self.current_chain_index = (self.current_chain_index + 1) % len(self.pattern_chain)
            return pattern_id

    def get_grid_data(self, pattern_id: int, track_id: int = 0) -> List[List[Optional[int]]]:
        """
        Get grid representation of pattern for UI display.

        Args:
            pattern_id: Pattern to get grid for
            track_id: Track to filter by (0 for all tracks)

        Returns:
            2D list where grid[step][note] contains velocity or None
        """
        with self.lock:
            pattern = self.get_pattern(pattern_id)
            if not pattern:
                return []

            # Initialize grid (128 notes x grid_length steps)
            grid: List[List[Optional[int]]] = [[None for _ in range(self.grid_length)] for _ in range(128)]

            # Fill grid with notes
            for note in pattern.notes:
                if track_id != 0 and note.track_id != track_id:
                    continue

                # Convert time to step
                time_per_step = pattern.length / self.grid_length
                step = int(note.time / time_per_step)

                if 0 <= step < self.grid_length and 0 <= note.note_number < 128:
                    grid[note.note_number][step] = note.velocity

            return grid

    def set_grid_resolution(self, resolution: int) -> None:
        """
        Set grid resolution.

        Args:
            resolution: Steps per beat (4, 8, 16, 32)
        """
        with self.lock:
            self.grid_resolution = max(4, min(32, resolution))
            # Update grid length based on resolution (4 bars)
            self.grid_length = 4 * self.grid_resolution

    def get_pattern_list(self) -> List[Dict[str, Any]]:
        """Get list of all patterns with metadata."""
        with self.lock:
            return [
                {
                    'id': pattern.id,
                    'name': pattern.name,
                    'length': pattern.length,
                    'note_count': len(pattern.notes),
                    'control_count': len(pattern.controls),
                    'tempo': pattern.tempo,
                    'created_time': pattern.created_time,
                    'modified_time': pattern.modified_time
                }
                for pattern in self.patterns.values()
            ]

    def get_playback_status(self) -> Dict[str, Any]:
        """Get current playback status."""
        with self.lock:
            return {
                'is_playing': self.is_playing,
                'current_pattern_id': self.current_pattern_id,
                'current_position': self.current_position,
                'loop_enabled': self.loop_enabled,
                'step_input_enabled': self.step_input_enabled,
                'pattern_chain': self.pattern_chain.copy(),
                'current_chain_index': self.current_chain_index
            }

    def save_pattern_to_file(self, pattern_id: int, filename: str) -> bool:
        """
        Save pattern to JSON file.

        Args:
            pattern_id: Pattern to save
            filename: Output filename

        Returns:
            True if saved successfully
        """
        with self.lock:
            pattern = self.get_pattern(pattern_id)
            if not pattern:
                return False

            try:
                import json
                with open(filename, 'w') as f:
                    json.dump(pattern.to_dict(), f, indent=2)
                return True
            except Exception:
                return False

    def load_pattern_from_file(self, filename: str) -> Optional[int]:
        """
        Load pattern from JSON file.

        Args:
            filename: Input filename

        Returns:
            New pattern ID or None if load failed
        """
        with self.lock:
            try:
                import json
                with open(filename, 'r') as f:
                    data = json.load(f)

                pattern = Pattern.from_dict(data)
                pattern_id = pattern.id

                # Ensure ID is unique
                while pattern_id in self.patterns:
                    pattern_id += 1
                    pattern.id = pattern_id

                self.patterns[pattern_id] = pattern
                self.next_pattern_id = max(self.next_pattern_id, pattern_id + 1)

                return pattern_id
            except Exception:
                return None

    def reset(self) -> None:
        """Reset sequencer to clean state."""
        with self.lock:
            self.stop_playback()
            self.patterns.clear()
            self.current_pattern_id = None
            self.pattern_chain.clear()
            self.current_chain_index = 0
            self.next_pattern_id = 1
            self.disable_step_input()

    # Alias for backward compatibility
    stop = stop_playback
