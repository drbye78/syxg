"""
Style Engine Integration Module

This module provides integration between the style engine and other synth subsystems:
1. Effects Coordinator ↔ Style Dynamics
2. Voice Manager ↔ OTS Presets
3. Modulation Matrix ↔ MIDI Learn
4. Pattern Sequencer ↔ Style Sections
5. MPE System ↔ Scale Detection

Usage:
    from synth.style.integrations import StyleIntegrations

    integrations = StyleIntegrations(
        effects_coordinator=effects,
        voice_manager=voice_mgr,
        modulation_matrix=mod_matrix,
        pattern_sequencer=sequencer,
        mpe_manager=mpe,
        style_player=style_player,
    )
    integrations.enable_all()
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .dynamics import DynamicsParameter, StyleDynamics
    from .midi_learn import MIDILearn
    from .scale import ScaleDetector
    from .style_player import StylePlayer


class StyleEffectsIntegration:
    """
    Integration 1: Effects Coordinator ↔ Style Dynamics

    Syncs effect parameters with style dynamics for cohesive mix control.

    When style dynamics change, this integration automatically adjusts:
    - Reverb level and time
    - Chorus depth and rate
    - Master EQ settings
    - Compressor threshold
    - Delay feedback
    """

    def __init__(self, effects_coordinator: Any, style_dynamics: StyleDynamics):
        self.effects = effects_coordinator
        self.dynamics = style_dynamics

        # Scaling curves for each effect parameter
        self.reverb_scale = 1.0
        self.chorus_scale = 1.0
        self.delay_scale = 1.0
        self.eq_scale = 1.0
        self.compressor_scale = 1.0

        # Callback registration
        self.dynamics.add_callback(self._on_dynamics_change)

    def _on_dynamics_change(self, value: int, params: dict[DynamicsParameter, float]):
        """Handle dynamics parameter changes."""
        from .dynamics import DynamicsParameter

        # Get scaling factors from dynamics
        self.reverb_scale = params.get(DynamicsParameter.REVERB_MIX, 0.5)
        self.chorus_scale = params.get(DynamicsParameter.CHORUS_MIX, 0.5)

        # Apply to effects
        self._apply_reverb_scaling()
        self._apply_chorus_scaling()
        self._apply_eq_scaling()
        self._apply_compressor_scaling()

    def _apply_reverb_scaling(self):
        """Apply reverb scaling based on dynamics."""
        if not hasattr(self.effects, "set_reverb_parameter"):
            return

        # Scale reverb time and level
        base_time = 2.5  # seconds
        base_level = 0.8

        new_time = base_time * (0.5 + self.reverb_scale * 0.5)
        new_level = base_level * self.reverb_scale

        try:
            self.effects.set_reverb_parameter("time", new_time)
            self.effects.set_reverb_parameter("level", new_level)
        except Exception:
            pass

    def _apply_chorus_scaling(self):
        """Apply chorus scaling based on dynamics."""
        if not hasattr(self.effects, "set_chorus_parameter"):
            return

        # Scale chorus depth and rate
        base_depth = 0.6
        base_rate = 0.5

        new_depth = base_depth * (0.5 + self.chorus_scale * 0.5)
        new_rate = base_rate * (0.5 + self.chorus_scale * 0.5)

        try:
            self.effects.set_chorus_parameter("depth", new_depth)
            self.effects.set_chorus_parameter("rate", new_rate)
        except Exception:
            pass

    def _apply_eq_scaling(self):
        """Apply EQ scaling based on dynamics."""
        if not hasattr(self.effects, "set_eq_parameter"):
            return

        # Adjust EQ based on dynamics
        # Higher dynamics = brighter sound
        high_gain = -3.0 + self.eq_scale * 6.0  # -3 to +3 dB

        try:
            self.effects.set_eq_parameter("high_gain", high_gain)
        except Exception:
            pass

    def _apply_compressor_scaling(self):
        """Apply compressor scaling based on dynamics."""
        if not hasattr(self.effects, "set_compressor_parameter"):
            return

        # Adjust compressor threshold based on dynamics
        # Higher dynamics = higher threshold (less compression)
        base_threshold = -20.0
        threshold = base_threshold + self.compressor_scale * 10.0

        try:
            self.effects.set_compressor_parameter("threshold", threshold)
        except Exception:
            pass

    def enable(self):
        """Enable effects-dynamics integration."""
        self.dynamics.add_callback(self._on_dynamics_change)

    def disable(self):
        """Disable effects-dynamics integration."""
        try:
            self.dynamics.remove_callback(self._on_dynamics_change)
        except Exception:
            pass


class StyleVoiceIntegration:
    """
    Integration 2: Voice Manager ↔ OTS Presets

    Optimizes voice allocation for different OTS preset types.

    Different instrument types need different voice configurations:
    - Piano: High polyphony, natural decay
    - Bass: Monophonic, fast attack
    - Pad: High polyphony, long sustain
    - Strings: Legato, moderate polyphony
    - Brass: Strong attack, moderate release
    """

    # Voice configuration presets for different instrument types
    VOICE_CONFIGS = {
        "piano": {
            "polyphony": 16,
            "attack": 0.001,
            "decay": 0.3,
            "sustain": 0.7,
            "release": 0.5,
            "legato": False,
        },
        "bass": {
            "polyphony": 4,
            "attack": 0.001,
            "decay": 0.2,
            "sustain": 0.8,
            "release": 0.1,
            "legato": True,
            "mono": True,
        },
        "pad": {
            "polyphony": 12,
            "attack": 0.05,
            "decay": 0.3,
            "sustain": 0.9,
            "release": 1.0,
            "legato": True,
        },
        "strings": {
            "polyphony": 8,
            "attack": 0.02,
            "decay": 0.3,
            "sustain": 0.8,
            "release": 0.4,
            "legato": True,
        },
        "brass": {
            "polyphony": 6,
            "attack": 0.01,
            "decay": 0.2,
            "sustain": 0.7,
            "release": 0.2,
            "legato": False,
        },
        "organ": {
            "polyphony": 16,
            "attack": 0.001,
            "decay": 0.0,
            "sustain": 1.0,
            "release": 0.05,
            "legato": False,
        },
        "synth_lead": {
            "polyphony": 4,
            "attack": 0.001,
            "decay": 0.2,
            "sustain": 0.8,
            "release": 0.1,
            "legato": True,
            "mono": True,
        },
        "synth_pad": {
            "polyphony": 12,
            "attack": 0.1,
            "decay": 0.3,
            "sustain": 0.9,
            "release": 1.5,
            "legato": True,
        },
    }

    def __init__(self, voice_manager: Any, ots: Any):
        self.voice_manager = voice_manager
        self.ots = ots

        # Track current OTS preset
        self._current_preset_id = -1

    def apply_ots_voice_optimization(self, preset_id: int):
        """
        Optimize voice allocation for OTS preset.

        Args:
            preset_id: OTS preset ID to optimize for
        """
        if not self.ots:
            return

        preset = self.ots.get_preset(preset_id)
        if not preset:
            return

        # Analyze preset to determine instrument type
        instrument_type = self._analyze_preset_instrument_type(preset)

        # Get voice configuration
        voice_config = self.VOICE_CONFIGS.get(instrument_type, self.VOICE_CONFIGS["piano"])

        # Apply to voice manager
        self._apply_voice_config(voice_config, preset)

        self._current_preset_id = preset_id

    def _analyze_preset_instrument_type(self, preset: Any) -> str:
        """
        Analyze OTS preset to determine instrument type.

        Uses program change numbers and metadata to classify.
        """
        # Check preset name for keywords
        name = preset.name.lower()

        if "bass" in name:
            return "bass"
        elif "pad" in name:
            return "pad"
        elif "strings" in name or "string" in name:
            return "strings"
        elif "brass" in name or "horn" in name:
            return "brass"
        elif "organ" in name:
            return "organ"
        elif "lead" in name:
            return "synth_lead"
        elif "piano" in name or "keys" in name or "ep" in name:
            return "piano"

        # Check program change numbers
        for part in preset.parts:
            if not part.enabled:
                continue

            program = part.program_change

            # GM program ranges
            if 0 <= program <= 7:  # Piano
                return "piano"
            elif 16 <= program <= 23:  # Organ
                return "organ"
            elif 32 <= program <= 39:  # Bass
                return "bass"
            elif 40 <= program <= 47:  # Strings
                return "strings"
            elif 56 <= program <= 63:  # Brass
                return "brass"
            elif 80 <= program <= 87:  # Synth Lead
                return "synth_lead"
            elif 88 <= program <= 95:  # Synth Pad
                return "synth_pad"

        return "piano"  # Default

    def _apply_voice_config(self, config: dict, preset: Any):
        """Apply voice configuration to voice manager."""
        if not hasattr(self.voice_manager, "configure_voice"):
            return

        for part in preset.parts:
            if not part.enabled:
                continue

            channel = part.part_id

            try:
                # Configure voice for this channel
                self.voice_manager.configure_voice(
                    channel=channel,
                    polyphony=config["polyphony"],
                    attack=config["attack"],
                    decay=config["decay"],
                    sustain=config["sustain"],
                    release=config["release"],
                    legato=config.get("legato", False),
                    mono=config.get("mono", False),
                )
            except Exception:
                pass

    def enable(self):
        """Enable voice-OTS integration."""
        if self.ots:
            self.ots.set_change_callback(self.apply_ots_voice_optimization)

    def disable(self):
        """Disable voice-OTS integration."""
        pass


class StyleModulationIntegration:
    """
    Integration 3: Modulation Matrix ↔ MIDI Learn

    Allows MIDI Learn to control modulation routing.

    Mappable modulation targets:
    - LFO rate and depth
    - Filter cutoff and resonance
    - Envelope times
    - Effect parameters
    - Oscillator detune
    """

    # Default MIDI CC mappings for modulation
    DEFAULT_MODULATION_MAPPINGS = {
        # LFO Controls
        "lfo_rate": {"cc": 75, "min": 0.1, "max": 20.0, "curve": "logarithmic"},
        "lfo_depth": {"cc": 76, "min": 0.0, "max": 1.0, "curve": "linear"},
        # Filter Controls
        "filter_cutoff": {"cc": 74, "min": 20.0, "max": 20000.0, "curve": "logarithmic"},
        "filter_resonance": {"cc": 71, "min": 0.0, "max": 10.0, "curve": "linear"},
        # Envelope Controls
        "env_attack": {"cc": 73, "min": 0.001, "max": 2.0, "curve": "logarithmic"},
        "env_release": {"cc": 72, "min": 0.01, "max": 5.0, "curve": "logarithmic"},
        # Effect Controls
        "effect_param1": {"cc": 77, "min": 0.0, "max": 1.0, "curve": "linear"},
        "effect_param2": {"cc": 78, "min": 0.0, "max": 1.0, "curve": "linear"},
    }

    def __init__(self, modulation_matrix: Any, midi_learn: MIDILearn):
        self.mod_matrix = modulation_matrix
        self.midi_learn = midi_learn

        self._registered_callbacks: dict[str, Callable] = {}

    def bind_modulation_to_midi_learn(self):
        """Bind modulation parameters to MIDI Learn."""
        from .midi_learn import LearnTargetType

        for param_name, mapping in self.DEFAULT_MODULATION_MAPPINGS.items():
            # Create learn target
            target_type = LearnTargetType.STYLE_INTENSITY  # Generic target

            # Register callback
            def create_callback(param: str, min_val: float, max_val: float):
                def callback(value: float, raw_value: int):
                    self._on_modulation_cc(param, value, min_val, max_val)

                return callback

            callback = create_callback(param_name, mapping["min"], mapping["max"])
            self._registered_callbacks[param_name] = callback

            # Register with MIDI learn
            self.midi_learn.register_callback(target_type, callback)

    def _on_modulation_cc(
        self, param: str, normalized_value: float, min_val: float, max_val: float
    ):
        """Handle modulation CC messages."""
        # Scale value
        value = min_val + normalized_value * (max_val - min_val)

        # Route to modulation matrix
        if hasattr(self.mod_matrix, "set_parameter"):
            try:
                self.mod_matrix.set_parameter(param, value)
            except Exception:
                pass

    def add_modulation_mapping(
        self, param_name: str, cc_number: int, min_val: float, max_val: float, curve: str = "linear"
    ):
        """Add custom modulation mapping."""
        from .midi_learn import LearnTargetType, MIDILearnMapping

        mapping = MIDILearnMapping(
            cc_number=cc_number,
            channel=0,
            target_type=LearnTargetType.STYLE_INTENSITY,
            target_param=param_name,
            min_val=min_val,
            max_val=max_val,
            curve=curve,
            label=param_name,
        )

        self.midi_learn.add_mapping(mapping)

    def enable(self):
        """Enable modulation-MIDI learn integration."""
        self.bind_modulation_to_midi_learn()

    def disable(self):
        """Disable modulation-MIDI learn integration."""
        self._registered_callbacks.clear()


class StyleSequencerIntegration:
    """
    Integration 4: Pattern Sequencer ↔ Style Sections

    Syncs pattern playback with style sections for seamless integration.

    Features:
    - Automatic pattern transitions on style section changes
    - Tempo synchronization
    - Bar/beat position sync
    - Pattern chain integration with style progression
    """

    # Pattern mappings for style sections
    SECTION_PATTERN_MAP = {
        "intro_1": "intro_short",
        "intro_2": "intro_medium",
        "intro_3": "intro_long",
        "main_a": "pattern_a",
        "main_b": "pattern_b",
        "main_c": "pattern_c",
        "main_d": "pattern_d",
        "fill_in_aa": "fill_a",
        "fill_in_bb": "fill_b",
        "fill_in_cc": "fill_c",
        "fill_in_dd": "fill_d",
        "break": "break",
        "ending_1": "ending_short",
        "ending_2": "ending_medium",
        "ending_3": "ending_long",
    }

    def __init__(self, pattern_sequencer: Any, style_player: StylePlayer):
        self.sequencer = pattern_sequencer
        self.style_player = style_player

        self._sync_enabled = False

    def sync_with_style_section(self):
        """Sync pattern playback with style sections."""
        if not self.style_player:
            return

        # Register section change callback
        self.style_player.set_section_change_callback(self._on_style_section_change)

        # Sync tempo
        self._sync_tempo()

        self._sync_enabled = True

    def _on_style_section_change(self, old_section, new_section):
        """Handle style section changes."""
        if not self._sync_enabled:
            return

        old_name = old_section.value if old_section else "none"
        new_name = new_section.value if new_section else "none"

        # Get pattern for new section
        pattern_name = self.SECTION_PATTERN_MAP.get(new_name)

        if pattern_name and hasattr(self.sequencer, "play_pattern"):
            # Smooth transition to new pattern
            self._transition_to_pattern(pattern_name)

    def _transition_to_pattern(self, pattern_name: str):
        """Transition to new pattern smoothly."""
        # Wait for next bar boundary
        if hasattr(self.sequencer, "queue_pattern"):
            self.sequencer.queue_pattern(pattern_name)
        elif hasattr(self.sequencer, "play_pattern"):
            self.sequencer.play_pattern(pattern_name)

    def _sync_tempo(self):
        """Sync sequencer tempo with style tempo."""
        if not self.style_player or not hasattr(self.sequencer, "set_tempo"):
            return

        style_tempo = self.style_player.tempo
        self.sequencer.set_tempo(style_tempo)

    def set_pattern_for_section(self, section_name: str, pattern_name: str):
        """Set custom pattern mapping for a section."""
        self.SECTION_PATTERN_MAP[section_name] = pattern_name

    def enable(self):
        """Enable sequencer-style integration."""
        self.sync_with_style_section()

    def disable(self):
        """Disable sequencer-style integration."""
        self._sync_enabled = False


class StyleMPEIntegration:
    """
    Integration 5: MPE System ↔ Scale Detection

    Constrains MPE pitch bending to detected scale for musical expression.

    Features:
    - Scale-aware pitch bending
    - Diatonic transposition
    - Microtonal adjustments based on scale
    - Per-note pitch constraints
    """

    def __init__(self, mpe_manager: Any, scale_detector: ScaleDetector):
        self.mpe = mpe_manager
        self.scale_detector = scale_detector

        self._scale_constraint_enabled = False
        self._last_scale = None

    def apply_scale_constraint(self):
        """Apply scale constraint to MPE pitch bending."""
        if not self.mpe or not self.scale_detector:
            return

        scale = self.scale_detector.get_current_scale()

        if scale and scale.confidence > 0.5:
            self._last_scale = scale
            self._apply_scale_to_mpe(scale)
            self._scale_constraint_enabled = True

    def _apply_scale_to_mpe(self, scale: DetectedScale):
        """Apply scale constraints to MPE system."""
        if not hasattr(self.mpe, "set_scale_constraint"):
            return

        # Get scale notes
        scale_notes = scale.get_scale_notes(root_midi=60, octaves=2)

        try:
            self.mpe.set_scale_constraint(
                root=scale.root,
                scale_type=scale.scale_type.value,
                notes=scale_notes,
            )
        except Exception:
            pass

    def set_diatonic_bend_range(self, semitones: int = 2):
        """
        Set diatonic pitch bend range.

        Instead of chromatic bending, bends to next scale degree.
        """
        if hasattr(self.mpe, "set_bend_mode"):
            self.mpe.set_bend_mode("diatonic")

        if hasattr(self.mpe, "set_bend_range"):
            self.mpe.set_bend_range(semitones)

    def enable_microtonal_adjustment(self):
        """Enable microtonal adjustments based on scale temperament."""
        if not self._last_scale:
            return

        # Get scale temperament adjustments
        temperament = self._get_temperament_adjustments(self._last_scale.scale_type)

        if hasattr(self.mpe, "set_temperament"):
            self.mpe.set_temperament(temperament)

    def _get_temperament_adjustments(self, scale_type) -> dict[int, float]:
        """Get microtonal adjustments for scale type."""
        # Common temperament adjustments in cents
        temperaments = {
            "just_intonation": {
                0: 0,  # Root
                2: -4,  # Major 2nd
                4: -14,  # Major 3rd
                5: 2,  # Perfect 4th
                7: 2,  # Perfect 5th
                9: -16,  # Major 6th
                11: -12,  # Major 7th
            },
            "pythagorean": {
                0: 0,
                2: 0,
                4: 8,
                5: 0,
                7: 0,
                9: 8,
                11: 8,
            },
        }

        return temperaments.get("just_intonation", {})

    def enable(self):
        """Enable MPE-scale integration."""
        self._scale_constraint_enabled = True

        # Register for scale updates
        if self.scale_detector:
            # Poll for scale changes
            pass

    def disable(self):
        """Disable MPE-scale integration."""
        self._scale_constraint_enabled = False

        if hasattr(self.mpe, "set_bend_mode"):
            self.mpe.set_bend_mode("chromatic")


class StyleIntegrations:
    """
    Master integration class that manages all style engine integrations.

    Usage:
        integrations = StyleIntegrations(
            effects_coordinator=effects,
            voice_manager=voice_mgr,
            modulation_matrix=mod_matrix,
            pattern_sequencer=sequencer,
            mpe_manager=mpe,
            style_player=style_player,
            style_dynamics=dynamics,
            ots=ots,
            midi_learn=midi_learn,
            scale_detector=scale_det,
        )
        integrations.enable_all()
    """

    def __init__(
        self,
        effects_coordinator: Any = None,
        voice_manager: Any = None,
        modulation_matrix: Any = None,
        pattern_sequencer: Any = None,
        mpe_manager: Any = None,
        style_player: Any = None,
        style_dynamics: Any = None,
        ots: Any = None,
        midi_learn: Any = None,
        scale_detector: Any = None,
    ):
        self.effects = effects_coordinator
        self.voice_manager = voice_manager
        self.mod_matrix = modulation_matrix
        self.sequencer = pattern_sequencer
        self.mpe = mpe_manager
        self.style_player = style_player
        self.dynamics = style_dynamics
        self.ots = ots
        self.midi_learn = midi_learn
        self.scale_detector = scale_detector

        self.integrations: dict[str, Any] = {}

        self._initialize_integrations()

    def _initialize_integrations(self):
        """Initialize all available integrations."""
        # 1. Effects ↔ Dynamics
        if self.effects and self.dynamics:
            self.integrations["effects"] = StyleEffectsIntegration(self.effects, self.dynamics)

        # 2. Voice ↔ OTS
        if self.voice_manager and self.ots:
            self.integrations["voice"] = StyleVoiceIntegration(self.voice_manager, self.ots)

        # 3. Modulation ↔ MIDI Learn
        if self.mod_matrix and self.midi_learn:
            self.integrations["modulation"] = StyleModulationIntegration(
                self.mod_matrix, self.midi_learn
            )

        # 4. Sequencer ↔ Style
        if self.sequencer and self.style_player:
            self.integrations["sequencer"] = StyleSequencerIntegration(
                self.sequencer, self.style_player
            )

        # 5. MPE ↔ Scale
        if self.mpe and self.scale_detector:
            self.integrations["mpe"] = StyleMPEIntegration(self.mpe, self.scale_detector)

    def enable_all(self):
        """Enable all integrations."""
        for name, integration in self.integrations.items():
            try:
                integration.enable()
                print(f"Enabled integration: {name}")
            except Exception as e:
                print(f"Failed to enable {name}: {e}")

    def disable_all(self):
        """Disable all integrations."""
        for name, integration in self.integrations.items():
            try:
                integration.disable()
            except Exception:
                pass

    def enable(self, name: str):
        """Enable specific integration by name."""
        if name in self.integrations:
            self.integrations[name].enable()

    def disable(self, name: str):
        """Disable specific integration by name."""
        if name in self.integrations:
            self.integrations[name].disable()

    def get_integration(self, name: str) -> Any | None:
        """Get integration by name."""
        return self.integrations.get(name)

    def get_status(self) -> dict[str, bool]:
        """Get status of all integrations."""
        return dict.fromkeys(self.integrations.keys(), True)
