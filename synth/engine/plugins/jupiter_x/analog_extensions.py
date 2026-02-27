"""
Jupiter-X Analog Engine Extensions

Plugin that adds Jupiter-X specific analog synthesis features to the base analog engine.
Eliminates duplication by extending the existing analog synthesis rather than creating
a parallel implementation.
"""
from __future__ import annotations

from typing import Any
import numpy as np

from ..base_plugin import (
    SynthesisFeaturePlugin, PluginMetadata, PluginLoadContext,
    PluginType, PluginCompatibility
)


class JupiterXAnalogPlugin(SynthesisFeaturePlugin):
    """
    Jupiter-X Analog Synthesis Extensions

    Adds Jupiter-X specific analog features to the base analog engine:
    - Dual oscillator architecture with Jupiter-X specific waveforms
    - Advanced filter combinations and routing
    - Enhanced envelope shapes and modulation
    - Jupiter-X style oscillator sync and ring modulation
    - Multi-mode filter configurations
    """

    def __init__(self):
        metadata = PluginMetadata(
            name="Jupiter-X Analog Extensions",
            version="1.0.0",
            description="Advanced analog synthesis from Roland Jupiter-X",
            author="Jupiter-X Development Team",
            plugin_type=PluginType.SYNTHESIS_FEATURE,
            compatibility=PluginCompatibility.EXCLUSIVE,
            target_engines=["analog"],
            dependencies=[],
            parameters={
                "dual_oscillator_mode": {
                    "type": "bool",
                    "default": True,
                    "description": "Enable dual oscillator Jupiter-X mode"
                },
                "oscillator_sync": {
                    "type": "bool",
                    "default": False,
                    "description": "Enable oscillator hard sync"
                },
                "ring_modulation": {
                    "type": "bool",
                    "default": False,
                    "description": "Enable oscillator ring modulation"
                },
                "filter_configuration": {
                    "type": "enum",
                    "default": "series",
                    "options": ["series", "parallel", "dual"],
                    "description": "Filter routing configuration"
                },
                "envelope_shape": {
                    "type": "enum",
                    "default": "analog",
                    "options": ["analog", "digital", "exponential"],
                    "description": "Envelope curve shape"
                }
            }
        )
        super().__init__(metadata)

        # Jupiter-X specific analog features - Phase 2 Enhancement
        self.dual_oscillator_mode = True
        self.oscillator_sync_enabled = False
        self.ring_modulation_enabled = False
        self.filter_configuration = "series"
        self.envelope_shape = "analog"

        # ===== PHASE 2: ADVANCED OSCILLATOR FEATURES =====
        # Oscillator sync and modulation
        self.hard_sync_enabled = False
        self.soft_sync_enabled = False
        self.cross_modulation_enabled = False
        self.cross_modulation_amount = 0.0

        # Pulse Width Modulation (PWM)
        self.pwm_enabled = False
        self.pwm_amount = 0.0
        self.pwm_lfo_depth = 0.0

        # Sub-oscillator
        self.sub_oscillator_enabled = False
        self.sub_oscillator_octave = -1  # -2, -1 octaves below
        self.sub_oscillator_waveform = 'square'
        self.sub_oscillator_level = 0.0

        # Waveform morphing and mixing
        self.waveform_morphing_enabled = False
        self.osc1_morph_position = 0.0  # 0.0-1.0
        self.osc2_morph_position = 0.0

        # Advanced noise generation
        self.noise_color = 'white'  # white, pink, blue, brown
        self.noise_level = 0.0

        # Oscillator state for advanced features
        self.osc1_phase = 0.0
        self.osc2_phase = 0.0
        self.sub_osc_phase = 0.0
        self.pwm_phase = 0.0
        self.sync_triggered = False

        # Jupiter-X specific waveforms
        self.jupiter_x_waveforms = {
            'sawtooth': self._generate_jupiter_x_sawtooth,
            'square': self._generate_jupiter_x_square,
            'triangle': self._generate_jupiter_x_triangle,
            'sine': self._generate_jupiter_x_sine,
            'noise': self._generate_jupiter_x_noise
        }

        # Dual oscillator state
        self.osc1_waveform = 'sawtooth'
        self.osc2_waveform = 'square'
        self.osc1_level = 1.0
        self.osc2_level = 0.5
        self.osc2_detune = 0.0  # In semitones

        # ===== PHASE 2.2: ADVANCED FILTER FEATURES =====
        # Multi-mode filter system
        self.filter1_type = 'lpf'  # lpf, hpf, bpf, notch, comb
        self.filter1_cutoff = 1000.0
        self.filter1_resonance = 0.0
        self.filter1_drive = 1.0
        self.filter1_slope = 12  # dB/octave (12, 24)

        self.filter2_type = 'lpf'
        self.filter2_cutoff = 2000.0
        self.filter2_resonance = 0.0
        self.filter2_drive = 1.0
        self.filter2_slope = 12

        # Filter envelope integration
        self.filter_envelope_amount = 0.0  # -1.0 to +1.0
        self.filter_envelope_polarity = 1  # 1 = positive, -1 = negative
        self.filter_envelope_velocity_sens = 0.0

        # Key tracking system
        self.filter_key_tracking = 0.0  # -1.0 to +1.0
        self.filter_key_tracking_base = 60  # MIDI note (middle C)
        self.filter_key_center = 60  # Center note for tracking

        # Velocity sensitivity
        self.velocity_to_cutoff = 0.0  # -1.0 to +1.0
        self.velocity_to_resonance = 0.0
        self.velocity_curve = 'linear'  # linear, convex, concave

        # Filter saturation and drive
        self.input_drive = 1.0  # 1.0 = no drive, >1.0 = saturation
        self.saturation_type = 'soft'  # soft, hard, vintage, tape

        # Parallel filter routing
        self.parallel_filter_mix = 0.0  # 0.0 = series, 1.0 = parallel
        self.filter_separation = 0.0  # Stereo separation for parallel mode

        # Filter state for processing
        self.filter1_z1 = 0.0  # Filter history for IIR
        self.filter1_z2 = 0.0
        self.filter2_z1 = 0.0
        self.filter2_z2 = 0.0

        # ===== PHASE 2.3: ADVANCED ENVELOPE FEATURES =====
        # Multi-stage envelope system (up to 8 stages)
        self.envelope_stages = 4  # ADSR default, expandable to 8
        self.envelope_loop_enabled = False
        self.envelope_loop_start = 2  # Start looping from sustain
        self.envelope_loop_end = 3    # Loop to release
        self.envelope_sustain_mode = 'normal'  # normal, loop, gated

        # Envelope curves per stage
        self.attack_curve = 'convex'   # convex, concave, linear, exponential, logarithmic
        self.decay_curve = 'exponential'
        self.sustain_curve = 'linear'
        self.release_curve = 'exponential'

        # Velocity sensitivity per stage
        self.velocity_to_attack = 0.0      # -1.0 to +1.0
        self.velocity_to_decay = 0.0
        self.velocity_to_sustain = 0.0
        self.velocity_to_release = 0.0

        # Envelope retrigger modes
        self.envelope_retrigger_mode = 'single'  # single, multi, alternate
        self.envelope_legato_mode = False
        self.envelope_reset_on_note_off = True

        # Keyboard scaling and tracking
        self.envelope_key_tracking = 0.0    # -1.0 to +1.0
        self.envelope_key_center = 60       # MIDI note center
        self.envelope_velocity_curve = 'linear'  # linear, convex, concave

        # Advanced envelope state
        self.envelope_current_stage = 0
        self.envelope_stage_time = 0.0
        self.envelope_loop_count = 0
        self.envelope_last_velocity = 64
        self.envelope_last_note = 60

        # Multi-stage envelope levels and times
        self.envelope_levels = [0.0, 1.0, 0.7, 0.0, 0.0, 0.0, 0.0, 0.0]  # Up to 8 stages
        self.envelope_times = [0.01, 0.1, 0.2, 0.3, 0.0, 0.0, 0.0, 0.0]  # Times for each stage

        # ===== PHASE 2.3: ADVANCED ENVELOPE METHODS =====

    def configure_multi_stage_envelope(self, stages: int = 4, loop_enabled: bool = False,
                                      loop_start: int = 2, loop_end: int = 3,
                                      sustain_mode: str = 'normal'):
        """Configure multi-stage envelope system."""
        self.envelope_stages = max(2, min(8, stages))  # 2-8 stages
        self.envelope_loop_enabled = loop_enabled
        self.envelope_loop_start = max(0, min(self.envelope_stages - 1, loop_start))
        self.envelope_loop_end = max(0, min(self.envelope_stages - 1, loop_end))

        valid_modes = ['normal', 'loop', 'gated']
        self.envelope_sustain_mode = sustain_mode if sustain_mode in valid_modes else 'normal'

        print(f"🎛️ Multi-stage envelope: {self.envelope_stages} stages, loop {'enabled' if self.envelope_loop_enabled else 'disabled'} ({self.envelope_sustain_mode} mode)")

    def set_envelope_curves(self, attack_curve: str = 'convex', decay_curve: str = 'exponential',
                           sustain_curve: str = 'linear', release_curve: str = 'exponential'):
        """Set envelope curve shapes per stage."""
        valid_curves = ['linear', 'convex', 'concave', 'exponential', 'logarithmic']
        self.attack_curve = attack_curve if attack_curve in valid_curves else 'convex'
        self.decay_curve = decay_curve if decay_curve in valid_curves else 'exponential'
        self.sustain_curve = sustain_curve if sustain_curve in valid_curves else 'linear'
        self.release_curve = release_curve if release_curve in valid_curves else 'exponential'

        print(f"🎛️ Envelope curves: A={self.attack_curve}, D={self.decay_curve}, S={self.sustain_curve}, R={self.release_curve}")

    def set_envelope_levels_times(self, levels: list[float] | None = None, times: list[float] | None = None):
        """Set envelope level and time values for all stages."""
        if levels is None:
            levels = [0.0, 1.0, 0.7, 0.0]  # Default ADSR
        if times is None:
            times = [0.01, 0.1, 0.2, 0.3]  # Default times

        # Ensure we have the right number of values
        max_stages = len(self.envelope_levels)
        self.envelope_levels[:len(levels)] = [max(0.0, min(1.0, lvl)) for lvl in levels[:max_stages]]
        self.envelope_times[:len(times)] = [max(0.0, min(10.0, t)) for t in times[:max_stages]]

        print(f"🎛️ Envelope levels: {self.envelope_levels[:self.envelope_stages]}")
        print(f"🎛️ Envelope times: {self.envelope_times[:self.envelope_stages]}")

    def set_velocity_sensitivity_per_stage(self, attack_sens: float = 0.0, decay_sens: float = 0.0,
                                         sustain_sens: float = 0.0, release_sens: float = 0.0):
        """Set velocity sensitivity for each envelope stage."""
        self.velocity_to_attack = max(-1.0, min(1.0, attack_sens))
        self.velocity_to_decay = max(-1.0, min(1.0, decay_sens))
        self.velocity_to_sustain = max(-1.0, min(1.0, sustain_sens))
        self.velocity_to_release = max(-1.0, min(1.0, release_sens))

        print(f"🎛️ Velocity sensitivity per stage: A{self.velocity_to_attack:.2f}, D{self.velocity_to_decay:.2f}, S{self.velocity_to_sustain:.2f}, R{self.velocity_to_release:.2f}")

    def set_envelope_retrigger_mode(self, mode: str = 'single', legato: bool = False, reset_on_note_off: bool = True):
        """Configure envelope retrigger behavior."""
        valid_modes = ['single', 'multi', 'alternate']
        self.envelope_retrigger_mode = mode if mode in valid_modes else 'single'
        self.envelope_legato_mode = legato
        self.envelope_reset_on_note_off = reset_on_note_off

        print(f"🎛️ Envelope retrigger: {self.envelope_retrigger_mode} mode, legato {'enabled' if self.envelope_legato_mode else 'disabled'}")

    def set_envelope_key_tracking(self, amount: float = 0.0, center_note: int = 60, velocity_curve: str = 'linear'):
        """Configure envelope keyboard tracking and velocity curve."""
        self.envelope_key_tracking = max(-1.0, min(1.0, amount))
        self.envelope_key_center = max(0, min(127, center_note))

        valid_curves = ['linear', 'convex', 'concave']
        self.envelope_velocity_curve = velocity_curve if velocity_curve in valid_curves else 'linear'

        print(f"🎛️ Envelope key tracking: {self.envelope_key_tracking:.2f} (center: {self.envelope_key_center}), velocity curve: {self.envelope_velocity_curve}")

    def process_envelope(self, delta_time: float, note: int, velocity: int, note_on: bool, note_off: bool) -> float:
        """
        Process multi-stage envelope and return current envelope value.

        Args:
            delta_time: Time elapsed since last process call
            note: MIDI note number
            velocity: MIDI velocity
            note_on: True if note is being triggered
            note_off: True if note is being released

        Returns:
            Current envelope value (0.0-1.0)
        """
        # Store note and velocity for key tracking and velocity sensitivity
        if note_on:
            self.envelope_last_note = note
            self.envelope_last_velocity = velocity

        # Handle envelope retrigger
        if note_on and self._should_retrigger_envelope(note_on):
            self._retrigger_envelope()

        # Handle note off
        if note_off and self.envelope_reset_on_note_off:
            self.envelope_current_stage = self.envelope_stages - 1  # Go to release stage

        # Update envelope time
        self.envelope_stage_time += delta_time

        # Process current stage
        current_level = self._process_envelope_stage(delta_time, note, velocity)

        # Handle stage transitions
        if self._should_advance_stage():
            self._advance_envelope_stage()

        return current_level

    def _should_retrigger_envelope(self, note_on: bool) -> bool:
        """Determine if envelope should retrigger."""
        if not note_on:
            return False

        if self.envelope_retrigger_mode == 'single':
            return self.envelope_current_stage == self.envelope_stages - 1  # Only retrigger when finished
        elif self.envelope_retrigger_mode == 'multi':
            return True  # Always retrigger
        elif self.envelope_retrigger_mode == 'alternate':
            return self.envelope_current_stage >= self.envelope_loop_end if self.envelope_loop_enabled else True

        return False

    def _retrigger_envelope(self):
        """Retrigger envelope from start."""
        self.envelope_current_stage = 0
        self.envelope_stage_time = 0.0
        self.envelope_loop_count = 0

    def _process_envelope_stage(self, delta_time: float, note: int, velocity: int) -> float:
        """Process the current envelope stage."""
        stage = self.envelope_current_stage
        if stage >= self.envelope_stages:
            return self.envelope_levels[-1]  # Stay at final level

        # Get stage parameters
        start_level = self.envelope_levels[stage]
        end_level = self.envelope_levels[stage + 1] if stage + 1 < len(self.envelope_levels) else start_level
        stage_time = self.envelope_times[stage]

        # Apply velocity sensitivity to levels
        start_level = self._apply_velocity_to_level(start_level, velocity, stage, 'start')
        end_level = self._apply_velocity_to_level(end_level, velocity, stage, 'end')

        # Apply key tracking to time
        stage_time = self._apply_key_tracking_to_time(stage_time, note)

        # Calculate interpolation factor
        if stage_time > 0:
            factor = min(1.0, self.envelope_stage_time / stage_time)
        else:
            factor = 1.0  # Instant stage

        # Apply curve to interpolation
        curve_factor = self._apply_envelope_curve(factor, stage)

        # Interpolate between levels
        current_level = start_level + (end_level - start_level) * curve_factor

        return max(0.0, min(1.0, current_level))

    def _apply_velocity_to_level(self, base_level: float, velocity: int, stage: int, level_type: str) -> float:
        """Apply velocity sensitivity to envelope level."""
        sens = 0.0

        # Get sensitivity for this stage
        if stage == 0:  # Attack
            sens = self.velocity_to_attack
        elif stage == 1:  # Decay
            sens = self.velocity_to_decay
        elif stage == 2:  # Sustain
            sens = self.velocity_to_sustain
        elif stage >= 3:  # Release
            sens = self.velocity_to_release

        if abs(sens) < 0.01:
            return base_level

        # Calculate velocity factor
        vel_norm = velocity / 127.0
        vel_factor = self._calculate_envelope_velocity_factor(vel_norm)

        # Apply sensitivity
        if sens > 0:
            # Higher velocity = higher level
            return base_level * (1.0 + vel_factor * sens)
        else:
            # Higher velocity = lower level
            return base_level * (1.0 + vel_factor * sens)

    def _apply_key_tracking_to_time(self, base_time: float, note: int) -> float:
        """Apply key tracking to envelope time."""
        if abs(self.envelope_key_tracking) < 0.01:
            return base_time

        # Calculate note offset from center
        note_offset = note - self.envelope_key_center

        # Apply key tracking (higher notes = shorter times)
        time_factor = 1.0 - (note_offset / 12.0) * self.envelope_key_tracking

        return max(0.001, base_time * time_factor)

    def _calculate_envelope_velocity_factor(self, vel_norm: float) -> float:
        """Calculate velocity factor based on envelope velocity curve."""
        if self.envelope_velocity_curve == 'linear':
            return vel_norm
        elif self.envelope_velocity_curve == 'convex':
            return vel_norm * vel_norm
        elif self.envelope_velocity_curve == 'concave':
            return 1.0 - (1.0 - vel_norm) * (1.0 - vel_norm)
        else:
            return vel_norm

    def _apply_envelope_curve(self, factor: float, stage: int) -> float:
        """Apply curve shaping to envelope interpolation factor."""
        curve_type = 'linear'

        # Get curve type for this stage
        if stage == 0:  # Attack
            curve_type = self.attack_curve
        elif stage == 1:  # Decay
            curve_type = self.decay_curve
        elif stage == 2:  # Sustain
            curve_type = self.sustain_curve
        elif stage >= 3:  # Release
            curve_type = self.release_curve

        # Apply curve
        if curve_type == 'linear':
            return factor
        elif curve_type == 'convex':
            return factor * factor
        elif curve_type == 'concave':
            return 1.0 - (1.0 - factor) * (1.0 - factor)
        elif curve_type == 'exponential':
            return 1.0 - np.exp(-factor * 5.0) if factor < 1.0 else 1.0
        elif curve_type == 'logarithmic':
            return np.log(1.0 + factor * 9.0) / np.log(10.0) if factor > 0 else 0.0
        else:
            return factor

    def _should_advance_stage(self) -> bool:
        """Check if envelope should advance to next stage."""
        if self.envelope_current_stage >= self.envelope_stages - 1:
            return False  # Already at final stage

        stage_time = self.envelope_times[self.envelope_current_stage]
        return self.envelope_stage_time >= stage_time

    def _advance_envelope_stage(self):
        """Advance envelope to next stage."""
        self.envelope_current_stage += 1
        self.envelope_stage_time = 0.0

        # Handle looping
        if self.envelope_loop_enabled and self.envelope_current_stage > self.envelope_loop_end:
            self.envelope_current_stage = self.envelope_loop_start
            self.envelope_loop_count += 1

            # Prevent infinite loops
            if self.envelope_loop_count > 1000:  # Emergency stop
                self.envelope_loop_enabled = False
                self.envelope_current_stage = self.envelope_stages - 1

    def reset_envelope(self):
        """Reset envelope to initial state."""
        self.envelope_current_stage = 0
        self.envelope_stage_time = 0.0
        self.envelope_loop_count = 0

    def get_advanced_envelope_features(self) -> dict[str, Any]:
        """Get status of all advanced envelope features."""
        return {
            'multi_stage_config': {
                'stages': self.envelope_stages,
                'loop_enabled': self.envelope_loop_enabled,
                'loop_start': self.envelope_loop_start,
                'loop_end': self.envelope_loop_end,
                'sustain_mode': self.envelope_sustain_mode
            },
            'curves': {
                'attack': self.attack_curve,
                'decay': self.decay_curve,
                'sustain': self.sustain_curve,
                'release': self.release_curve
            },
            'velocity_sensitivity': {
                'attack': self.velocity_to_attack,
                'decay': self.velocity_to_decay,
                'sustain': self.velocity_to_sustain,
                'release': self.velocity_to_release
            },
            'retrigger_config': {
                'mode': self.envelope_retrigger_mode,
                'legato': self.envelope_legato_mode,
                'reset_on_note_off': self.envelope_reset_on_note_off
            },
            'key_tracking': {
                'amount': self.envelope_key_tracking,
                'center_note': self.envelope_key_center,
                'velocity_curve': self.envelope_velocity_curve
            },
            'envelope_state': {
                'current_stage': self.envelope_current_stage,
                'stage_time': self.envelope_stage_time,
                'loop_count': self.envelope_loop_count,
                'last_velocity': self.envelope_last_velocity,
                'last_note': self.envelope_last_note
            },
            'levels_times': {
                'levels': self.envelope_levels[:self.envelope_stages],
                'times': self.envelope_times[:self.envelope_stages]
            }
        }

        # Envelope state
        self.amp_envelope_shape = "analog"
        self.filter_envelope_shape = "analog"

    def get_metadata(self) -> PluginMetadata:
        return self.metadata

    def check_compatibility(self, engine_type: str, engine_version: str) -> bool:
        """Check compatibility with analog engines."""
        return engine_type == "analog" and engine_version.startswith("1.")

    def load(self, context: PluginLoadContext) -> bool:
        """Load the Jupiter-X analog extensions."""
        try:
            self.load_context = context

            # Get reference to the base analog engine
            self.analog_engine = context.engine_instance
            if not self.analog_engine:
                return False

            # Initialize Jupiter-X specific features
            self._initialize_jupiter_x_analog_features()

            print("🎹 Jupiter-X Analog Extensions loaded")
            return True

        except Exception as e:
            print(f"Failed to load Jupiter-X analog extensions: {e}")
            return False

    def unload(self) -> bool:
        """Unload the Jupiter-X analog extensions."""
        try:
            # Clean up Jupiter-X specific resources
            self.oscillator_sync_enabled = False
            self.ring_modulation_enabled = False

            print("🎹 Jupiter-X Analog Extensions unloaded")
            return True

        except Exception as e:
            print(f"Error unloading Jupiter-X analog extensions: {e}")
            return False

    def _initialize_jupiter_x_analog_features(self):
        """Initialize Jupiter-X specific analog features."""
        # Set up dual oscillator architecture
        if hasattr(self.analog_engine, 'enable_dual_oscillators'):
            self.analog_engine.enable_dual_oscillators(self.dual_oscillator_mode)

        # Configure Jupiter-X specific filter routing
        self._setup_filter_configuration()

        # Set up envelope shapes
        self._configure_envelope_shapes()

    def _setup_filter_configuration(self):
        """Set up Jupiter-X filter configuration."""
        if not self.analog_engine:
            return

        if hasattr(self.analog_engine, 'set_filter_configuration'):
            if self.filter_configuration == "series":
                self.analog_engine.set_filter_configuration("series")
            elif self.filter_configuration == "parallel":
                self.analog_engine.set_filter_configuration("parallel")
            elif self.filter_configuration == "dual":
                # Jupiter-X dual filter mode - separate filters for each oscillator
                self.analog_engine.set_filter_configuration("dual")

    def _configure_envelope_shapes(self):
        """Configure Jupiter-X envelope shapes."""
        if not self.analog_engine:
            return

        # Set envelope curve shapes
        if hasattr(self.analog_engine, 'set_envelope_shape'):
            self.analog_engine.set_envelope_shape('amplitude', self.envelope_shape)
            self.analog_engine.set_envelope_shape('filter', self.envelope_shape)

    def get_synthesis_features(self) -> dict[str, Any]:
        """Get Jupiter-X analog synthesis features."""
        return {
            'dual_oscillator': {
                'enabled': self.dual_oscillator_mode,
                'osc1_waveform': self.osc1_waveform,
                'osc2_waveform': self.osc2_waveform,
                'osc1_level': self.osc1_level,
                'osc2_level': self.osc2_level,
                'osc2_detune': self.osc2_detune
            },
            'oscillator_modulation': {
                'sync': self.oscillator_sync_enabled,
                'ring_modulation': self.ring_modulation_enabled
            },
            'filter_system': {
                'configuration': self.filter_configuration,
                'dual_filters': self.filter_configuration == "dual",
                'filter1_cutoff': self.filter1_cutoff,
                'filter1_resonance': self.filter1_resonance,
                'filter2_cutoff': self.filter2_cutoff,
                'filter2_resonance': self.filter2_resonance
            },
            'envelope_system': {
                'shape': self.envelope_shape,
                'amp_envelope_shape': self.amp_envelope_shape,
                'filter_envelope_shape': self.filter_envelope_shape
            },
            'waveforms': {
                'available': list(self.jupiter_x_waveforms.keys()),
                'jupiter_x_specific': True
            }
        }

    def set_parameter(self, name: str, value: Any) -> bool:
        """Set plugin parameter."""
        if name == "dual_oscillator_mode":
            self.dual_oscillator_mode = bool(value)
            self._update_dual_oscillator_mode()
            return True
        elif name == "oscillator_sync":
            self.oscillator_sync_enabled = bool(value)
            self._update_oscillator_sync()
            return True
        elif name == "ring_modulation":
            self.ring_modulation_enabled = bool(value)
            self._update_ring_modulation()
            return True
        elif name == "filter_configuration":
            if value in ["series", "parallel", "dual"]:
                self.filter_configuration = value
                self._setup_filter_configuration()
                return True
        elif name == "envelope_shape":
            if value in ["analog", "digital", "exponential"]:
                self.envelope_shape = value
                self._configure_envelope_shapes()
                return True

        return False

    def get_parameters(self) -> dict[str, Any]:
        """Get current parameter values."""
        return {
            "dual_oscillator_mode": self.dual_oscillator_mode,
            "oscillator_sync": self.oscillator_sync_enabled,
            "ring_modulation": self.ring_modulation_enabled,
            "filter_configuration": self.filter_configuration,
            "envelope_shape": self.envelope_shape
        }

    def _update_dual_oscillator_mode(self):
        """Update dual oscillator mode."""
        if self.analog_engine and hasattr(self.analog_engine, 'enable_dual_oscillators'):
            self.analog_engine.enable_dual_oscillators(self.dual_oscillator_mode)

    def _update_oscillator_sync(self):
        """Update oscillator sync settings."""
        if self.analog_engine and hasattr(self.analog_engine, 'enable_oscillator_sync'):
            self.analog_engine.enable_oscillator_sync(self.oscillator_sync_enabled)

    def _update_ring_modulation(self):
        """Update ring modulation settings."""
        if self.analog_engine and hasattr(self.analog_engine, 'enable_ring_modulation'):
            self.analog_engine.enable_ring_modulation(self.ring_modulation_enabled)

    def process_midi_message(self, status: int, data1: int, data2: int) -> bool:
        """Process MIDI messages for Jupiter-X analog features."""
        # Handle Jupiter-X specific MIDI messages for analog engine
        if status >> 4 == 0xB:  # Control Change
            cc_number = data1
            value = data2

            # CC 79: Oscillator 2 level (0-127)
            if cc_number == 79:
                self.osc2_level = value / 127.0
                self._update_oscillator_levels()
                return True

            # CC 80: Oscillator 2 detune (-64 to +63 centered on 64)
            if cc_number == 80:
                self.osc2_detune = (value - 64) / 64.0 * 12.0  # ±12 semitones
                self._update_oscillator_detune()
                return True

            # CC 81: Filter 1 cutoff (0-127 -> frequency range)
            if cc_number == 81:
                self.filter1_cutoff = self._midi_to_frequency(value)
                self._update_filter_cutoff(1, self.filter1_cutoff)
                return True

            # CC 82: Filter 1 resonance (0-127 -> 0.0-1.0)
            if cc_number == 82:
                self.filter1_resonance = value / 127.0
                self._update_filter_resonance(1, self.filter1_resonance)
                return True

        return False

    def _midi_to_frequency(self, midi_value: int) -> float:
        """Convert MIDI value to frequency in Hz."""
        # Jupiter-X filter frequency range: ~20Hz to ~20kHz
        # Use exponential mapping for better control
        if midi_value == 0:
            return 20.0
        elif midi_value == 127:
            return 20000.0
        else:
            # Exponential mapping
            return 20.0 * (20000.0 / 20.0) ** (midi_value / 127.0)

    def _update_oscillator_levels(self):
        """Update oscillator levels."""
        if self.analog_engine and hasattr(self.analog_engine, 'set_oscillator_levels'):
            self.analog_engine.set_oscillator_levels(self.osc1_level, self.osc2_level)

    def _update_oscillator_detune(self):
        """Update oscillator detune."""
        if self.analog_engine and hasattr(self.analog_engine, 'set_oscillator_detune'):
            self.analog_engine.set_oscillator_detune(self.osc2_detune)

    def _update_filter_cutoff(self, filter_num: int, cutoff: float):
        """Update filter cutoff frequency."""
        if self.analog_engine and hasattr(self.analog_engine, 'set_filter_cutoff'):
            self.analog_engine.set_filter_cutoff(filter_num, cutoff)

    def _update_filter_resonance(self, filter_num: int, resonance: float):
        """Update filter resonance."""
        if self.analog_engine and hasattr(self.analog_engine, 'set_filter_resonance'):
            self.analog_engine.set_filter_resonance(filter_num, resonance)

    def set_oscillator_waveform(self, osc_num: int, waveform: str) -> bool:
        """Set oscillator waveform."""
        if osc_num == 1:
            if waveform in self.jupiter_x_waveforms:
                self.osc1_waveform = waveform
                if self.analog_engine and hasattr(self.analog_engine, 'set_oscillator_waveform'):
                    self.analog_engine.set_oscillator_waveform(1, waveform)
                return True
        elif osc_num == 2:
            if waveform in self.jupiter_x_waveforms:
                self.osc2_waveform = waveform
                if self.analog_engine and hasattr(self.analog_engine, 'set_oscillator_waveform'):
                    self.analog_engine.set_oscillator_waveform(2, waveform)
                return True

        return False

    def get_available_waveforms(self) -> list[str]:
        """Get available Jupiter-X waveforms."""
        return list(self.jupiter_x_waveforms.keys())

    # Jupiter-X specific waveform generators
    def _generate_jupiter_x_sawtooth(self, phase: float) -> float:
        """Generate Jupiter-X style sawtooth wave."""
        # Jupiter-X sawtooth has slight curvature for warmth
        return 2.0 * phase - 1.0 + 0.01 * np.sin(2 * np.pi * phase)

    def _generate_jupiter_x_square(self, phase: float) -> float:
        """Generate Jupiter-X style square wave."""
        # Jupiter-X square waves have rounded edges
        if phase < 0.5:
            return 0.95  # Slightly rounded
        else:
            return -0.95

    def _generate_jupiter_x_triangle(self, phase: float) -> float:
        """Generate Jupiter-X style triangle wave."""
        # Jupiter-X triangle waves are slightly asymmetric
        if phase < 0.5:
            return 4.0 * phase - 1.0
        else:
            return 3.0 - 4.0 * phase

    def _generate_jupiter_x_sine(self, phase: float) -> float:
        """Generate Jupiter-X style sine wave."""
        # Pure sine wave
        return np.sin(2 * np.pi * phase)

    def _generate_jupiter_x_noise(self, phase: float) -> float:
        """Generate Jupiter-X style noise."""
        # Filtered noise for better sound
        return np.random.uniform(-1.0, 1.0)

    def generate_samples(self, note: int, velocity: int, modulation: dict[str, float],
                        block_size: int) -> np.ndarray | None:
        """
        Generate additional analog samples with Jupiter-X features.

        This is called by the base analog engine to add Jupiter-X specific processing.
        """
        if not self.is_active() or not self.analog_engine:
            return None

        # Apply Jupiter-X specific processing to the base analog output
        # This could include additional filtering, modulation, etc.

        # For now, return None to indicate no additional samples
        # In a full implementation, this would return processed samples
        return None

    # ===== PHASE 2: ADVANCED OSCILLATOR METHODS =====

    def enable_hard_sync(self, enabled: bool = True):
        """Enable/disable hard oscillator sync."""
        self.hard_sync_enabled = enabled
        if self.soft_sync_enabled and enabled:
            self.soft_sync_enabled = False  # Can't have both
        print(f"🎛️ Hard sync {'enabled' if enabled else 'disabled'}")

    def enable_soft_sync(self, enabled: bool = True):
        """Enable/disable soft oscillator sync."""
        self.soft_sync_enabled = enabled
        if self.hard_sync_enabled and enabled:
            self.hard_sync_enabled = False  # Can't have both
        print(f"🎛️ Soft sync {'enabled' if enabled else 'disabled'}")

    def set_cross_modulation(self, amount: float):
        """Set oscillator cross-modulation amount (0.0-1.0)."""
        self.cross_modulation_amount = max(0.0, min(1.0, amount))
        self.cross_modulation_enabled = amount > 0.0
        print(f"🎛️ Cross-modulation set to {self.cross_modulation_amount:.2f}")

    def enable_pwm(self, enabled: bool = True, amount: float = 0.5, lfo_depth: float = 0.0):
        """Enable Pulse Width Modulation."""
        self.pwm_enabled = enabled
        self.pwm_amount = max(0.0, min(1.0, amount))
        self.pwm_lfo_depth = max(0.0, min(1.0, lfo_depth))
        print(f"🎛️ PWM {'enabled' if enabled else 'disabled'} (amount: {self.pwm_amount:.2f}, LFO: {self.pwm_lfo_depth:.2f})")

    def enable_sub_oscillator(self, enabled: bool = True, octave: int = -1, waveform: str = 'square', level: float = 0.5):
        """Enable sub-oscillator."""
        self.sub_oscillator_enabled = enabled
        self.sub_oscillator_octave = octave if octave in [-2, -1] else -1
        self.sub_oscillator_waveform = waveform if waveform in ['square', 'sine'] else 'square'
        self.sub_oscillator_level = max(0.0, min(1.0, level))
        print(f"🎛️ Sub-oscillator {'enabled' if enabled else 'disabled'} (octave: {self.sub_oscillator_octave}, waveform: {self.sub_oscillator_waveform})")

    def set_waveform_morphing(self, enabled: bool = True, osc1_position: float = 0.0, osc2_position: float = 0.0):
        """Enable waveform morphing between oscillator types."""
        self.waveform_morphing_enabled = enabled
        self.osc1_morph_position = max(0.0, min(1.0, osc1_position))
        self.osc2_morph_position = max(0.0, min(1.0, osc2_position))
        print(f"🎛️ Waveform morphing {'enabled' if enabled else 'disabled'}")

    def set_noise_color(self, color: str = 'white', level: float = 0.0):
        """Set noise color and level."""
        valid_colors = ['white', 'pink', 'blue', 'brown']
        self.noise_color = color if color in valid_colors else 'white'
        self.noise_level = max(0.0, min(1.0, level))
        print(f"🎛️ Noise: {self.noise_color} color, level {self.noise_level:.2f}")

    def _apply_oscillator_sync(self, osc1_freq: float, osc2_freq: float, sample_rate: float) -> tuple[float, float]:
        """
        Apply oscillator sync effects.

        Returns modified frequencies for oscillator sync.
        """
        if not (self.hard_sync_enabled or self.soft_sync_enabled):
            return osc1_freq, osc2_freq

        # Hard sync: OSC2 is reset when OSC1 completes a cycle
        if self.hard_sync_enabled:
            # In hard sync, OSC2 frequency is effectively multiplied
            # This is handled in the sample generation loop
            pass

        # Soft sync: Similar to hard sync but smoother
        elif self.soft_sync_enabled:
            # Similar implementation to hard sync but with phase smoothing
            pass

        return osc1_freq, osc2_freq

    def _apply_cross_modulation(self, osc1_sample: float, osc2_sample: float) -> tuple[float, float]:
        """Apply cross-modulation between oscillators."""
        if not self.cross_modulation_enabled or self.cross_modulation_amount <= 0.0:
            return osc1_sample, osc2_sample

        # FM cross-modulation: OSC1 modulates OSC2 frequency, OSC2 modulates OSC1 amplitude
        mod_amount = self.cross_modulation_amount * 2.0  # Scale for effect

        # OSC2 modulates OSC1 amplitude
        osc1_modulated = osc1_sample * (1.0 + osc2_sample * mod_amount * 0.5)

        # OSC1 modulates OSC2 frequency (phase)
        osc2_freq_mod = 1.0 + osc1_sample * mod_amount * 0.1
        # This would affect the phase increment in the sample generation

        return osc1_modulated, osc2_sample

    def _generate_pwm_sample(self, base_sample: float, lfo_value: float = 0.0) -> float:
        """Generate PWM-modulated sample."""
        if not self.pwm_enabled:
            return base_sample

        # PWM amount controlled by parameter + LFO
        pwm_mod = self.pwm_amount + (lfo_value * self.pwm_lfo_depth * 0.5)
        pwm_mod = max(0.1, min(0.9, pwm_mod))  # Keep within reasonable range

        # Simple PWM implementation - adjust duty cycle
        # For square waves, this affects the pulse width
        if abs(base_sample) > pwm_mod:
            return base_sample
        else:
            return base_sample * 0.1  # Reduce amplitude in the "off" portion

    def _generate_sub_osc_sample(self, frequency: float, sample_rate: float) -> float:
        """Generate sub-oscillator sample."""
        if not self.sub_oscillator_enabled or self.sub_oscillator_level <= 0.0:
            return 0.0

        # Calculate sub-oscillator frequency
        sub_freq = frequency * (2.0 ** self.sub_oscillator_octave)  # Octave below

        # Update phase
        phase_increment = sub_freq / sample_rate
        self.sub_osc_phase = (self.sub_osc_phase + phase_increment) % 1.0

        # Generate waveform
        if self.sub_oscillator_waveform == 'square':
            sample = 1.0 if self.sub_osc_phase < 0.5 else -1.0
        elif self.sub_oscillator_waveform == 'sine':
            sample = np.sin(2 * np.pi * self.sub_osc_phase)
        else:
            sample = 1.0 if self.sub_osc_phase < 0.5 else -1.0  # Default to square

        return sample * self.sub_oscillator_level

    def _generate_morphed_waveform(self, osc_num: int, phase: float) -> float:
        """Generate morphed waveform between oscillator types."""
        if not self.waveform_morphing_enabled:
            return 0.0  # No morphing

        morph_pos = self.osc1_morph_position if osc_num == 1 else self.osc2_morph_position

        # Generate samples from different waveforms
        sawtooth = self._generate_jupiter_x_sawtooth(phase)
        square = self._generate_jupiter_x_square(phase)
        triangle = self._generate_jupiter_x_triangle(phase)

        # Morph between waveforms based on position
        if morph_pos < 0.33:
            # Sawtooth to Square
            blend = morph_pos / 0.33
            return sawtooth * (1.0 - blend) + square * blend
        elif morph_pos < 0.66:
            # Square to Triangle
            blend = (morph_pos - 0.33) / 0.33
            return square * (1.0 - blend) + triangle * blend
        else:
            # Triangle to Sawtooth
            blend = (morph_pos - 0.66) / 0.34
            return triangle * (1.0 - blend) + sawtooth * blend

    def _generate_colored_noise(self) -> float:
        """Generate colored noise based on selected color."""
        if self.noise_level <= 0.0:
            return 0.0

        if self.noise_color == 'white':
            # Standard white noise
            return np.random.uniform(-1.0, 1.0) * self.noise_level

        elif self.noise_color == 'pink':
            # Pink noise (1/f) - simplified approximation
            white = np.random.uniform(-1.0, 1.0)
            # Very basic pink noise approximation
            return (white * 0.5 + np.random.uniform(-1.0, 1.0) * 0.3) * self.noise_level

        elif self.noise_color == 'blue':
            # Blue noise (higher frequencies) - simplified
            white = np.random.uniform(-1.0, 1.0)
            # Amplify high frequencies
            return white * self.noise_level * 1.2

        elif self.noise_color == 'brown':
            # Brown noise (1/f^2) - very low frequency
            white = np.random.uniform(-1.0, 1.0)
            # Low-pass filtered approximation
            return (white * 0.3) * self.noise_level

        return 0.0

    def get_advanced_oscillator_features(self) -> dict[str, Any]:
        """Get status of all advanced oscillator features."""
        return {
            'sync_modes': {
                'hard_sync': self.hard_sync_enabled,
                'soft_sync': self.soft_sync_enabled,
                'cross_modulation': {
                    'enabled': self.cross_modulation_enabled,
                    'amount': self.cross_modulation_amount
                }
            },
            'pwm': {
                'enabled': self.pwm_enabled,
                'amount': self.pwm_amount,
                'lfo_depth': self.pwm_lfo_depth
            },
            'sub_oscillator': {
                'enabled': self.sub_oscillator_enabled,
                'octave': self.sub_oscillator_octave,
                'waveform': self.sub_oscillator_waveform,
                'level': self.sub_oscillator_level
            },
            'waveform_morphing': {
                'enabled': self.waveform_morphing_enabled,
                'osc1_position': self.osc1_morph_position,
                'osc2_position': self.osc2_morph_position
            },
            'noise': {
                'color': self.noise_color,
                'level': self.noise_level
            },
            'oscillator_state': {
                'osc1_phase': self.osc1_phase,
                'osc2_phase': self.osc2_phase,
                'sub_osc_phase': self.sub_osc_phase,
                'pwm_phase': self.pwm_phase,
                'sync_triggered': self.sync_triggered
            }
        }

    # ===== PHASE 2.2: ADVANCED FILTER METHODS =====

    def set_filter_type(self, filter_num: int, filter_type: str):
        """Set filter type for specified filter (1 or 2)."""
        valid_types = ['lpf', 'hpf', 'bpf', 'notch', 'comb']
        if filter_type not in valid_types:
            filter_type = 'lpf'

        if filter_num == 1:
            self.filter1_type = filter_type
        elif filter_num == 2:
            self.filter2_type = filter_type

        self._reset_filter_state(filter_num)
        print(f"🎛️ Filter {filter_num} type set to {filter_type.upper()}")

    def set_filter_slope(self, filter_num: int, slope: int):
        """Set filter slope in dB/octave (12 or 24)."""
        slope = 12 if slope < 18 else 24  # 12 or 24 dB/octave

        if filter_num == 1:
            self.filter1_slope = slope
        elif filter_num == 2:
            self.filter2_slope = slope

        print(f"🎛️ Filter {filter_num} slope set to {slope}dB/octave")

    def set_filter_drive(self, filter_num: int, drive: float):
        """Set filter input drive (1.0 = no drive, >1.0 = saturation)."""
        drive = max(1.0, min(4.0, drive))  # 1.0 to 4.0 range

        if filter_num == 1:
            self.filter1_drive = drive
        elif filter_num == 2:
            self.filter2_drive = drive

        print(f"🎛️ Filter {filter_num} drive set to {drive:.1f}x")

    def configure_filter_envelope(self, amount: float = 0.0, polarity: int = 1, velocity_sens: float = 0.0):
        """Configure filter envelope integration."""
        self.filter_envelope_amount = max(-1.0, min(1.0, amount))
        self.filter_envelope_polarity = 1 if polarity >= 0 else -1
        self.filter_envelope_velocity_sens = max(0.0, min(1.0, velocity_sens))
        print(f"🎛️ Filter envelope: amount {self.filter_envelope_amount:.2f}, polarity {'positive' if self.filter_envelope_polarity > 0 else 'negative'}")

    def set_key_tracking(self, amount: float = 0.0, center_note: int = 60):
        """Configure filter key tracking."""
        self.filter_key_tracking = max(-1.0, min(1.0, amount))
        self.filter_key_center = max(0, min(127, center_note))
        print(f"🎛️ Filter key tracking: {self.filter_key_tracking:.2f} (center: {self.filter_key_center})")

    def set_velocity_sensitivity(self, cutoff_sens: float = 0.0, resonance_sens: float = 0.0, curve: str = 'linear'):
        """Configure velocity sensitivity for filter parameters."""
        self.velocity_to_cutoff = max(-1.0, min(1.0, cutoff_sens))
        self.velocity_to_resonance = max(-1.0, min(1.0, resonance_sens))
        valid_curves = ['linear', 'convex', 'concave']
        self.velocity_curve = curve if curve in valid_curves else 'linear'
        print(f"🎛️ Velocity sensitivity: cutoff {self.velocity_to_cutoff:.2f}, resonance {self.velocity_to_resonance:.2f} ({self.velocity_curve})")

    def set_input_drive(self, drive: float = 1.0, saturation_type: str = 'soft'):
        """Configure input drive and saturation."""
        self.input_drive = max(1.0, min(4.0, drive))
        valid_types = ['soft', 'hard', 'vintage', 'tape']
        self.saturation_type = saturation_type if saturation_type in valid_types else 'soft'
        print(f"🎛️ Input drive: {self.input_drive:.1f}x ({self.saturation_type} saturation)")

    def set_parallel_routing(self, mix: float = 0.0, separation: float = 0.0):
        """Configure parallel filter routing."""
        self.parallel_filter_mix = max(0.0, min(1.0, mix))
        self.filter_separation = max(0.0, min(1.0, separation))
        print(f"🎛️ Parallel routing: mix {self.parallel_filter_mix:.2f}, separation {self.filter_separation:.2f}")

    def _apply_input_drive(self, sample: float) -> float:
        """Apply input drive and saturation to sample."""
        if self.input_drive <= 1.0:
            return sample

        # Apply drive
        driven = sample * self.input_drive

        # Apply saturation based on type
        if self.saturation_type == 'soft':
            # Soft clipping
            driven = np.tanh(driven)
        elif self.saturation_type == 'hard':
            # Hard clipping
            driven = max(-1.0, min(1.0, driven))
        elif self.saturation_type == 'vintage':
            # Asymmetric soft clipping (common in analog gear)
            if driven > 0:
                driven = np.tanh(driven * 0.8)
            else:
                driven = np.tanh(driven * 1.2)
        elif self.saturation_type == 'tape':
            # Tape saturation approximation
            driven = driven * (1.0 + driven * driven * 0.1)

        return driven

    def _apply_filter_envelope(self, base_cutoff: float, envelope_value: float, velocity: int) -> float:
        """Apply filter envelope modulation."""
        if abs(self.filter_envelope_amount) < 0.01:
            return base_cutoff

        # Apply envelope amount and polarity
        env_mod = envelope_value * self.filter_envelope_amount * self.filter_envelope_polarity

        # Apply velocity sensitivity
        vel_factor = self._calculate_velocity_factor(velocity, self.filter_envelope_velocity_sens)

        # Calculate final cutoff
        cutoff_mod = base_cutoff * (1.0 + env_mod * vel_factor)

        # Clamp to reasonable range
        return max(20.0, min(20000.0, cutoff_mod))

    def _apply_key_tracking(self, base_cutoff: float, note: int) -> float:
        """Apply key tracking to filter cutoff."""
        if abs(self.filter_key_tracking) < 0.01:
            return base_cutoff

        # Calculate note offset from center
        note_offset = note - self.filter_key_center

        # Apply key tracking
        tracking_factor = 1.0 + (note_offset / 12.0) * self.filter_key_tracking

        return max(20.0, min(20000.0, base_cutoff * tracking_factor))

    def _apply_velocity_to_filter(self, base_cutoff: float, base_resonance: float, velocity: int) -> tuple[float, float]:
        """Apply velocity sensitivity to filter parameters."""
        cutoff = base_cutoff
        resonance = base_resonance

        if abs(self.velocity_to_cutoff) > 0.01:
            vel_factor = self._calculate_velocity_factor(velocity, abs(self.velocity_to_cutoff))
            if self.velocity_to_cutoff > 0:
                cutoff *= vel_factor  # Higher velocity = higher cutoff
            else:
                cutoff /= vel_factor  # Higher velocity = lower cutoff

        if abs(self.velocity_to_resonance) > 0.01:
            vel_factor = self._calculate_velocity_factor(velocity, abs(self.velocity_to_resonance))
            if self.velocity_to_resonance > 0:
                resonance *= vel_factor  # Higher velocity = more resonance
            else:
                resonance /= vel_factor  # Higher velocity = less resonance

        return max(20.0, min(20000.0, cutoff)), max(0.0, min(1.0, resonance))

    def _calculate_velocity_factor(self, velocity: int, sensitivity: float) -> float:
        """Calculate velocity factor based on curve type."""
        vel_norm = velocity / 127.0  # 0.0 to 1.0

        if self.velocity_curve == 'linear':
            factor = vel_norm
        elif self.velocity_curve == 'convex':
            # Convex curve (more sensitive at low velocities)
            factor = vel_norm * vel_norm
        elif self.velocity_curve == 'concave':
            # Concave curve (more sensitive at high velocities)
            factor = 1.0 - (1.0 - vel_norm) * (1.0 - vel_norm)
        else:
            factor = vel_norm

        # Apply sensitivity
        return 1.0 + (factor - 0.5) * sensitivity * 2.0

    def _process_filter(self, filter_num: int, sample: float, cutoff: float, resonance: float, sample_rate: float) -> float:
        """Process sample through specified filter."""
        if filter_num == 1:
            filter_type = self.filter1_type
            slope = self.filter1_slope
            z1 = self.filter1_z1
            z2 = self.filter1_z2
        else:
            filter_type = self.filter2_type
            slope = self.filter2_slope
            z1 = self.filter2_z1
            z2 = self.filter2_z2

        # Initialize variables
        filtered = sample
        new_z1 = z1
        new_z2 = z2

        # Calculate filter coefficients
        if filter_type in ['lpf', 'hpf', 'bpf', 'notch']:
            # State variable filter implementation
            f = 2.0 * np.sin(np.pi * cutoff / sample_rate)  # Pre-warped frequency
            q = 1.0 / (2.0 * resonance + 0.5)  # Quality factor

            # State variable filter equations
            if filter_type == 'lpf':
                # Low pass
                filtered = z2 + f * z1
                new_z1 = z1 + f * (sample - filtered) * q
                new_z2 = filtered + f * new_z1
            elif filter_type == 'hpf':
                # High pass
                filtered = sample - z2 - q * z1
                new_z1 = z1 + f * filtered
                new_z2 = new_z1 + f * filtered
            elif filter_type == 'bpf':
                # Band pass
                filtered = q * z1
                new_z1 = z1 + f * (sample - filtered)
                new_z2 = filtered + f * new_z1
            elif filter_type == 'notch':
                # Notch
                filtered = sample - q * z1
                new_z1 = z1 + f * filtered
                new_z2 = filtered + f * new_z1

        elif filter_type == 'comb':
            # Comb filter (simple implementation)
            delay_samples = int(sample_rate / cutoff)
            # Simplified comb filter - would need delay buffer in real implementation
            filtered = sample + resonance * z1
            new_z1 = sample
            new_z2 = z2  # Not used in comb filter

        else:
            # Default to low pass
            filtered = sample
            new_z1 = z1
            new_z2 = z2

        # Update filter state
        if filter_num == 1:
            self.filter1_z1 = new_z1
            self.filter1_z2 = new_z2
        else:
            self.filter2_z1 = new_z1
            self.filter2_z2 = new_z2

        return filtered

    def _apply_parallel_routing(self, series_output: float, filter1_output: float, filter2_output: float) -> float:
        """Apply parallel filter routing."""
        if self.parallel_filter_mix <= 0.0:
            return series_output  # Pure series
        elif self.parallel_filter_mix >= 1.0:
            # Pure parallel - mix filter outputs
            parallel_mix = (filter1_output + filter2_output) * 0.5
            # Apply stereo separation if needed (simplified)
            return parallel_mix
        else:
            # Blend series and parallel
            parallel_mix = (filter1_output + filter2_output) * 0.5
            return series_output * (1.0 - self.parallel_filter_mix) + parallel_mix * self.parallel_filter_mix

    def _reset_filter_state(self, filter_num: int):
        """Reset filter state for specified filter."""
        if filter_num == 1:
            self.filter1_z1 = 0.0
            self.filter1_z2 = 0.0
        elif filter_num == 2:
            self.filter2_z1 = 0.0
            self.filter2_z2 = 0.0

    def get_advanced_filter_features(self) -> dict[str, Any]:
        """Get status of all advanced filter features."""
        return {
            'multi_mode_filters': {
                'filter1': {
                    'type': self.filter1_type,
                    'cutoff': self.filter1_cutoff,
                    'resonance': self.filter1_resonance,
                    'drive': self.filter1_drive,
                    'slope': self.filter1_slope
                },
                'filter2': {
                    'type': self.filter2_type,
                    'cutoff': self.filter2_cutoff,
                    'resonance': self.filter2_resonance,
                    'drive': self.filter2_drive,
                    'slope': self.filter2_slope
                }
            },
            'filter_envelope': {
                'amount': self.filter_envelope_amount,
                'polarity': 'positive' if self.filter_envelope_polarity > 0 else 'negative',
                'velocity_sensitivity': self.filter_envelope_velocity_sens
            },
            'key_tracking': {
                'amount': self.filter_key_tracking,
                'center_note': self.filter_key_center
            },
            'velocity_sensitivity': {
                'cutoff': self.velocity_to_cutoff,
                'resonance': self.velocity_to_resonance,
                'curve': self.velocity_curve
            },
            'drive_saturation': {
                'input_drive': self.input_drive,
                'saturation_type': self.saturation_type
            },
            'parallel_routing': {
                'mix': self.parallel_filter_mix,
                'separation': self.filter_separation
            }
        }

    def get_analog_engine_status(self) -> dict[str, Any]:
        """Get Jupiter-X analog engine status."""
        return {
            'dual_oscillator_mode': self.dual_oscillator_mode,
            'oscillator_sync': self.oscillator_sync_enabled,
            'ring_modulation': self.ring_modulation_enabled,
            'filter_configuration': self.filter_configuration,
            'envelope_shape': self.envelope_shape,
            'osc1_waveform': self.osc1_waveform,
            'osc2_waveform': self.osc2_waveform,
            'available_waveforms': self.get_available_waveforms(),
            'advanced_oscillator_features': self.get_advanced_oscillator_features(),
            'advanced_filter_features': self.get_advanced_filter_features(),
            'features_active': self.is_active()
        }
