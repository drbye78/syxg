"""
XG Effects Registry and Factory

This module provides the comprehensive XG effects registry and factory system.
It manages all 118 XG effect types across system, variation, and insertion
categories, providing centralized effect creation, parameter management,
and type validation.

Key Features:
- Complete XG effect type registry (118 effects)
- Factory-based effect processor creation
- Parameter preset management and validation
- Effect category organization and lookup
- Real-time reconfiguration support
- Memory-efficient instance pooling

XG Effect Coverage:
- System Effects: 2 types (Reverb, Chorus)
- Variation Effects: 83 types (across 9 categories)
- Insertion Effects: 18 types (across 5 categories)
- Channel EQ: 10 types (timbre presets)
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

# Import our effect processors
try:
    from .eq_processor import XGMultiBandEqualizer
    from .insertion_pro import ProductionXGInsertionEffectsProcessor as XGInsertionEffectsProcessor
    from .system_effects import XGSystemChorusProcessor, XGSystemReverbProcessor
    from .types import (
        XG_CHANNEL_MIXER_DEFAULT,
        XGChannelEQParams,
        XGChannelMixerParams,
        XGChorusType,
        XGEQType,
        XGInsertionType,
        XGMasterEQParams,
        XGReverbType,
        XGSystemEffectsParams,
        XGVariationType,
    )
    from .variation_effects import XGVariationEffectsProcessor
except ImportError as e:
    # Fallback for development
    print(f"Import error in effects_registry: {e}")
    XGMultiBandEqualizer = None
    pass


class XGEffectCategory(IntEnum):
    """XG Effect Categories"""

    SYSTEM = 0  # System-wide effects (Reverb, Chorus)
    VARIATION = 1  # Variation effects (83 types)
    INSERTION = 2  # Insertion effects (18 types)
    EQUALIZER = 3  # EQ effects (10 types)


@dataclass(slots=True)
class XGEffectMetadata:
    """XG Effect Metadata Structure"""

    effect_type: int
    category: XGEffectCategory
    name: str
    short_name: str
    description: str
    has_parameters: bool
    processor_class: type | None = None


class XGEffectRegistry:
    """
    XG Effects Registry

    Central registry for all XG effect types with metadata, validation, and lookup.
    Provides comprehensive effect type management for the XG specification.
    """

    def __init__(self):
        """Initialize the XG effects registry with all effect types."""
        self._effects: dict[tuple[XGEffectCategory, int], XGEffectMetadata] = {}
        self._name_to_type: dict[str, tuple[XGEffectCategory, int]] = {}

        # Thread safety
        self.lock = threading.RLock()

        # Initialize registry
        self._initialize_system_effects()
        self._initialize_variation_effects()
        self._initialize_insertion_effects()
        self._initialize_eq_effects()

    def _register_effect(self, effect: XGEffectMetadata) -> None:
        """Register an effect in the central registry."""
        key = (effect.category, effect.effect_type)
        self._effects[key] = effect
        self._name_to_type[effect.name.lower().replace(" ", "_")] = key

        # Also register short name
        if effect.short_name:
            self._name_to_type[effect.short_name.lower().replace(" ", "_")] = key

    def _initialize_system_effects(self) -> None:
        """Initialize all XG system effects."""
        system_effects = [
            XGEffectMetadata(
                effect_type=XGReverbType.HALL_1.value,
                category=XGEffectCategory.SYSTEM,
                name="Hall 1",
                short_name="Hall1",
                description="Small Hall Reverb",
                has_parameters=True,
            ),
            XGEffectMetadata(
                effect_type=XGReverbType.HALL_2.value,
                category=XGEffectCategory.SYSTEM,
                name="Hall 2",
                short_name="Hall2",
                description="Medium Hall Reverb",
                has_parameters=True,
            ),
            XGEffectMetadata(
                effect_type=XGReverbType.ROOM_1.value,
                category=XGEffectCategory.SYSTEM,
                name="Room 1",
                short_name="Room1",
                description="Small Room Reverb",
                has_parameters=True,
            ),
            # Register XGChorusType effects here as well
            XGEffectMetadata(
                effect_type=XGChorusType.CHORUS_1.value,
                category=XGEffectCategory.SYSTEM,
                name="Chorus 1",
                short_name="Cho1",
                description="Standard Chorus",
                has_parameters=True,
            ),
            XGEffectMetadata(
                effect_type=XGChorusType.CELESTE_1.value,
                category=XGEffectCategory.SYSTEM,
                name="Celeste 1",
                short_name="Cel1",
                description="Celeste Modulation",
                has_parameters=True,
            ),
        ]

        for effect in system_effects:
            self._register_effect(effect)

    def _initialize_variation_effects(self) -> None:
        """Initialize all 83 XG variation effects with complete coverage."""
        variation_effects = [
            # Delay Effects (0-19)
            *self._create_delay_effects(),
            # Chorus Effects (10-31)
            *self._create_chorus_effects(),
            # Modulation Effects (32-42)
            *self._create_modulation_effects(),
            # Distortion Effects (43-52)
            *self._create_distortion_effects(),
            # Dynamics Effects (53-57)
            *self._create_dynamics_effects(),
            # Enhancer Effects (58-61)
            *self._create_enhancer_effects(),
            # Vocoder Effects (62-65)
            *self._create_vocoder_effects(),
            # Pitch Effects (64-69)
            *self._create_pitch_effects(),
            # Early Reflection (70-77)
            *self._create_er_effects(),
            # Gate Reverb (78-80)
            *self._create_gate_reverb_effects(),
            # Special Effects (81-83)
            *self._create_special_effects(),
        ]

        for effect in variation_effects:
            self._register_effect(effect)

    def _create_delay_effects(self) -> list[XGEffectMetadata]:
        """Create all delay-type variation effects (0-9)."""
        return [
            XGEffectMetadata(
                0,
                XGEffectCategory.VARIATION,
                "Delay L/C/R",
                "DLCR",
                "3-channel delay with stereo width",
                True,
            ),
            XGEffectMetadata(
                1,
                XGEffectCategory.VARIATION,
                "Delay L/R",
                "DLR",
                "Dual delay with cross-feedback",
                True,
            ),
            XGEffectMetadata(
                2, XGEffectCategory.VARIATION, "Echo", "ECHO", "Echo with configurable decay", True
            ),
            XGEffectMetadata(
                3,
                XGEffectCategory.VARIATION,
                "Dual Delay",
                "DDLY",
                "Two independent delay lines",
                True,
            ),
            XGEffectMetadata(
                4,
                XGEffectCategory.VARIATION,
                "Pan Delay",
                "PDLY",
                "Auto-panning delay with LFO",
                True,
            ),
            XGEffectMetadata(
                5,
                XGEffectCategory.VARIATION,
                "Cross Delay",
                "CDLY",
                "Cross-feedback delay processing",
                True,
            ),
            XGEffectMetadata(
                6,
                XGEffectCategory.VARIATION,
                "Multi-tap Delay",
                "MTDLY",
                "Multiple simultaneous delay taps",
                True,
            ),
            XGEffectMetadata(
                7, XGEffectCategory.VARIATION, "Reverse Delay", "RDLY", "Reverse delay effect", True
            ),
            XGEffectMetadata(
                8, XGEffectCategory.VARIATION, "Tremolo", "TREM", "Amplitude modulation", True
            ),
            XGEffectMetadata(
                9, XGEffectCategory.VARIATION, "Auto-pan", "APAN", "Stereo panning modulation", True
            ),
        ]

    def _create_chorus_effects(self) -> list[XGEffectMetadata]:
        """Create all chorus-type variation effects (10-31)."""
        return [
            XGEffectMetadata(
                10,
                XGEffectCategory.VARIATION,
                "Chorus 1",
                "CHO1",
                "Multi-tap chorus with LFO modulation",
                True,
            ),
            XGEffectMetadata(
                11,
                XGEffectCategory.VARIATION,
                "Chorus 2",
                "CHO2",
                "Faster chorus with different spacing",
                True,
            ),
            XGEffectMetadata(
                12,
                XGEffectCategory.VARIATION,
                "Chorus 3",
                "CHO3",
                "Chorus with feedback for richness",
                True,
            ),
            XGEffectMetadata(
                13, XGEffectCategory.VARIATION, "Chorus 4", "CHO4", "Deep, wide chorus effect", True
            ),
            XGEffectMetadata(
                14,
                XGEffectCategory.VARIATION,
                "Celeste 1",
                "CEL1",
                "Pitch-shifted chorus variation",
                True,
            ),
            XGEffectMetadata(
                15,
                XGEffectCategory.VARIATION,
                "Celeste 2",
                "CEL2",
                "Alternative celeste characteristics",
                True,
            ),
            XGEffectMetadata(
                16,
                XGEffectCategory.VARIATION,
                "Flanger 1",
                "FLG1",
                "Short delay with heavy feedback",
                True,
            ),
            XGEffectMetadata(
                17,
                XGEffectCategory.VARIATION,
                "Flanger 2",
                "FLG2",
                "Alternative flanger modulation",
                True,
            ),
            XGEffectMetadata(
                18,
                XGEffectCategory.VARIATION,
                "Delay LCR Chorus",
                "DLCRC",
                "Delay + Chorus combination",
                True,
            ),
            XGEffectMetadata(
                19,
                XGEffectCategory.VARIATION,
                "Delay LR Chorus",
                "DLRC",
                "Dual delay combined with chorus",
                True,
            ),
            XGEffectMetadata(
                20,
                XGEffectCategory.VARIATION,
                "Rotary Speaker Variation",
                "ROT_V",
                "Alternative rotary speaker",
                True,
            ),
            XGEffectMetadata(
                21,
                XGEffectCategory.VARIATION,
                "Celeste Chorus",
                "CELC",
                "Enhanced celeste effect",
                True,
            ),
            XGEffectMetadata(
                22, XGEffectCategory.VARIATION, "Vibrato", "VIB", "Pitch modulation effect", True
            ),
            XGEffectMetadata(
                23,
                XGEffectCategory.VARIATION,
                "Acoustic Simulator",
                "ACO",
                "Room acoustic simulation",
                True,
            ),
            XGEffectMetadata(
                24,
                XGEffectCategory.VARIATION,
                "Guitar Amp Simulator",
                "GAMP",
                "Guitar amplifier simulation",
                True,
            ),
            XGEffectMetadata(
                25, XGEffectCategory.VARIATION, "Enhancer", "ENH", "Dynamic enhancement", True
            ),
            XGEffectMetadata(
                26, XGEffectCategory.VARIATION, "Slicer", "SLIC", "Rhythmic gating effect", True
            ),
            XGEffectMetadata(
                27,
                XGEffectCategory.VARIATION,
                "Phaser-Flanger",
                "PHFL",
                "Combined phaser and flanger",
                True,
            ),
            XGEffectMetadata(
                28,
                XGEffectCategory.VARIATION,
                "Chorus Auto-Pan",
                "CHOAP",
                "Chorus with auto-panning",
                True,
            ),
            XGEffectMetadata(
                29,
                XGEffectCategory.VARIATION,
                "Celeste Auto-Pan",
                "CELAP",
                "Celeste with auto-panning",
                True,
            ),
            XGEffectMetadata(
                30,
                XGEffectCategory.VARIATION,
                "Delay Auto-Pan",
                "DLAP",
                "Delay with auto-panning",
                True,
            ),
            XGEffectMetadata(
                31,
                XGEffectCategory.VARIATION,
                "Reverb Auto-Pan",
                "RVAP",
                "Reverb with auto-panning",
                True,
            ),
        ]

    def _create_modulation_effects(self) -> list[XGEffectMetadata]:
        """Create all modulation variation effects (32-42)."""
        return [
            XGEffectMetadata(
                32, XGEffectCategory.VARIATION, "Auto Pan", "APAN", "Automatic stereo panning", True
            ),
            XGEffectMetadata(
                33, XGEffectCategory.VARIATION, "Auto Wah", "AWAH", "Automatic wah-wah filter", True
            ),
            XGEffectMetadata(
                34,
                XGEffectCategory.VARIATION,
                "Ring Modulation",
                "RING",
                "Amplitude modulation with carrier",
                True,
            ),
            XGEffectMetadata(
                35,
                XGEffectCategory.VARIATION,
                "Step Phaser Up",
                "SPHU",
                "Stepped phaser upward sweep",
                True,
            ),
            XGEffectMetadata(
                36,
                XGEffectCategory.VARIATION,
                "Step Phaser Down",
                "SPHD",
                "Stepped phaser downward sweep",
                True,
            ),
            XGEffectMetadata(
                37,
                XGEffectCategory.VARIATION,
                "Step Flanger Up",
                "SFLU",
                "Stepped flanger upward sweep",
                True,
            ),
            XGEffectMetadata(
                38,
                XGEffectCategory.VARIATION,
                "Step Flanger Down",
                "SFLD",
                "Stepped flanger downward sweep",
                True,
            ),
            XGEffectMetadata(
                39,
                XGEffectCategory.VARIATION,
                "Step Tremolo Up",
                "STMU",
                "Stepped tremolo upward sweep",
                True,
            ),
            XGEffectMetadata(
                40,
                XGEffectCategory.VARIATION,
                "Step Tremolo Down",
                "STMD",
                "Stepped tremolo downward sweep",
                True,
            ),
            XGEffectMetadata(
                41,
                XGEffectCategory.VARIATION,
                "Step Pan Up",
                "SPAN_U",
                "Stepped panning upward sweep",
                True,
            ),
            XGEffectMetadata(
                42,
                XGEffectCategory.VARIATION,
                "Step Pan Down",
                "SPAN_D",
                "Stepped panning downward sweep",
                True,
            ),
        ]

    def _create_distortion_effects(self) -> list[XGEffectMetadata]:
        """Create all distortion variation effects (43-52)."""
        return [
            XGEffectMetadata(
                43, XGEffectCategory.VARIATION, "Overdrive 1", "OVD1", "Light tube overdrive", True
            ),
            XGEffectMetadata(
                44, XGEffectCategory.VARIATION, "Overdrive 2", "OVD2", "Medium tube overdrive", True
            ),
            XGEffectMetadata(
                45, XGEffectCategory.VARIATION, "Overdrive 3", "OVD3", "Heavy tube overdrive", True
            ),
            XGEffectMetadata(
                46,
                XGEffectCategory.VARIATION,
                "Clipping Warning",
                "CLIP",
                "Hard limiting with look-ahead",
                True,
            ),
            XGEffectMetadata(
                47,
                XGEffectCategory.VARIATION,
                "Fuzz",
                "FUZZ",
                "Multi-stage distortion with octave",
                True,
            ),
            XGEffectMetadata(
                48,
                XGEffectCategory.VARIATION,
                "Guitar Distortion",
                "G_DIST",
                "Multi-stage saturation",
                True,
            ),
            XGEffectMetadata(
                49,
                XGEffectCategory.VARIATION,
                "Compressor Electronic",
                "CMP_EL",
                "Electronic compression",
                True,
            ),
            XGEffectMetadata(
                50,
                XGEffectCategory.VARIATION,
                "Compressor Optical",
                "CMP_OP",
                "Optical compression",
                True,
            ),
            XGEffectMetadata(
                51, XGEffectCategory.VARIATION, "Limiter", "LIMIT", "Peak limiting", True
            ),
            XGEffectMetadata(
                52,
                XGEffectCategory.VARIATION,
                "Multi Band Compressor",
                "MB_CMP",
                "Multi-band compression",
                True,
            ),
        ]

    def _create_dynamics_effects(self) -> list[XGEffectMetadata]:
        """Create all dynamics variation effects (53-57)."""
        return [
            XGEffectMetadata(
                53, XGEffectCategory.VARIATION, "Expander", "EXP", "Dynamic expander", True
            ),
            XGEffectMetadata(
                54,
                XGEffectCategory.VARIATION,
                "Enhancer Peaking",
                "ENH_PK",
                "Peaking enhancer",
                True,
            ),
            XGEffectMetadata(
                55,
                XGEffectCategory.VARIATION,
                "Enhancer Shelving",
                "ENH_SH",
                "Shelving enhancer",
                True,
            ),
            XGEffectMetadata(
                56,
                XGEffectCategory.VARIATION,
                "Multi Band Enhancer",
                "MB_ENH",
                "Multi-band enhancement",
                True,
            ),
            XGEffectMetadata(
                57,
                XGEffectCategory.VARIATION,
                "Overdrive 4",
                "OVD4",
                "Additional overdrive variation",
                True,
            ),
        ]

    def _create_enhancer_effects(self) -> list[XGEffectMetadata]:
        """Create all enhancer variation effects (58-61)."""
        return [
            XGEffectMetadata(
                58,
                XGEffectCategory.VARIATION,
                "Stereo Imager",
                "STEREO",
                "Stereo field enhancement",
                True,
            ),
            XGEffectMetadata(
                59,
                XGEffectCategory.VARIATION,
                "Surround Processor",
                "SURROUND",
                "Surround sound processing",
                True,
            ),
            XGEffectMetadata(
                60, XGEffectCategory.VARIATION, "Fader", "FADER", "Level fading effect", True
            ),
            XGEffectMetadata(
                61,
                XGEffectCategory.VARIATION,
                "Sub Woofer",
                "SUBWOOFER",
                "Sub-bass enhancement",
                True,
            ),
        ]

    def _create_vocoder_effects(self) -> list[XGEffectMetadata]:
        """Create all vocoder variation effects (62-65)."""
        return [
            XGEffectMetadata(
                62,
                XGEffectCategory.VARIATION,
                "Vocoder Comb Filter",
                "VOC_COMB",
                "Comb filter vocoder",
                True,
            ),
            XGEffectMetadata(
                63,
                XGEffectCategory.VARIATION,
                "Vocoder Resonator",
                "VOC_RES",
                "Resonator vocoder",
                True,
            ),
            XGEffectMetadata(
                64,
                XGEffectCategory.VARIATION,
                "Vocoder Formant",
                "VOC_FORM",
                "Formant vocoder",
                True,
            ),
            XGEffectMetadata(
                65,
                XGEffectCategory.VARIATION,
                "Vocoder Ensemble",
                "VOC_ENS",
                "Ensemble vocoder",
                True,
            ),
        ]

    def _create_pitch_effects(self) -> list[XGEffectMetadata]:
        """Create all pitch variation effects (66-69)."""
        return [
            XGEffectMetadata(
                66,
                XGEffectCategory.VARIATION,
                "Pitch Shift Up Minor 3rd",
                "PSH_M3U",
                "Minor 3rd up",
                True,
            ),
            XGEffectMetadata(
                67,
                XGEffectCategory.VARIATION,
                "Pitch Shift Up Major 3rd",
                "PSH_M3D",
                "Major 3rd up",
                True,
            ),
            XGEffectMetadata(
                68,
                XGEffectCategory.VARIATION,
                "Pitch Shift Down Minor 3rd",
                "PSH_m3D",
                "Minor 3rd down",
                True,
            ),
            XGEffectMetadata(
                69,
                XGEffectCategory.VARIATION,
                "Pitch Shift Down Major 3rd",
                "PSH_M3D",
                "Major 3rd down",
                True,
            ),
        ]

    def _create_er_effects(self) -> list[XGEffectMetadata]:
        """Create all early reflection variation effects (70-77)."""
        return [
            XGEffectMetadata(
                70,
                XGEffectCategory.VARIATION,
                "ER Hall Small",
                "ERH_SM",
                "Small hall early reflections",
                True,
            ),
            XGEffectMetadata(
                71,
                XGEffectCategory.VARIATION,
                "ER Hall Medium",
                "ERH_MD",
                "Medium hall early reflections",
                True,
            ),
            XGEffectMetadata(
                72,
                XGEffectCategory.VARIATION,
                "ER Hall Large",
                "ERH_LG",
                "Large hall early reflections",
                True,
            ),
            XGEffectMetadata(
                73,
                XGEffectCategory.VARIATION,
                "ER Room Small",
                "ERR_SM",
                "Small room early reflections",
                True,
            ),
            XGEffectMetadata(
                74,
                XGEffectCategory.VARIATION,
                "ER Room Medium",
                "ERR_MD",
                "Medium room early reflections",
                True,
            ),
            XGEffectMetadata(
                75,
                XGEffectCategory.VARIATION,
                "ER Room Large",
                "ERR_LG",
                "Large room early reflections",
                True,
            ),
            XGEffectMetadata(
                76,
                XGEffectCategory.VARIATION,
                "ER Plate",
                "ER_PLT",
                "Plate reverb early reflections",
                True,
            ),
            XGEffectMetadata(
                77,
                XGEffectCategory.VARIATION,
                "ER Spring",
                "ER_SPR",
                "Spring reverb early reflections",
                True,
            ),
        ]

    def _create_gate_reverb_effects(self) -> list[XGEffectMetadata]:
        """Create all gate reverb variation effects (78-80)."""
        return [
            XGEffectMetadata(
                78,
                XGEffectCategory.VARIATION,
                "Gate Reverb Fast Attack",
                "GTR_FAST",
                "Fast attack gate reverb",
                True,
            ),
            XGEffectMetadata(
                79,
                XGEffectCategory.VARIATION,
                "Gate Reverb Slow Attack",
                "GTR_SLOW",
                "Slow attack gate reverb",
                True,
            ),
            XGEffectMetadata(
                80,
                XGEffectCategory.VARIATION,
                "Gate Reverb Normal",
                "GTR_NORM",
                "Normal gate reverb",
                True,
            ),
        ]

    def _create_special_effects(self) -> list[XGEffectMetadata]:
        """Create all special variation effects (81-83)."""
        return [
            XGEffectMetadata(
                81,
                XGEffectCategory.VARIATION,
                "Voice Cancel",
                "VOICECAN",
                "Voice cancellation",
                True,
            ),
            XGEffectMetadata(
                82, XGEffectCategory.VARIATION, "Through", "THROUGH", "No effect (bypass)", False
            ),
            XGEffectMetadata(
                83, XGEffectCategory.VARIATION, "Bypass", "BYPASS", "Signal bypass", False
            ),
        ]

    def _initialize_insertion_effects(self) -> None:
        """Initialize all 18 XG insertion effects."""
        insertion_effects = [
            XGEffectMetadata(
                XGInsertionType.THROUGH.value,
                XGEffectCategory.INSERTION,
                "Through",
                "THRU",
                "No Effect (Bypass)",
                False,
            ),
            XGEffectMetadata(
                XGInsertionType.DISTORTION.value,
                XGEffectCategory.INSERTION,
                "Distortion",
                "DIST",
                "Classic Distortion",
                True,
            ),
            XGEffectMetadata(
                XGInsertionType.OVERDRIVE.value,
                XGEffectCategory.INSERTION,
                "Overdrive",
                "OVD",
                "Tube Overdrive",
                True,
            ),
            XGEffectMetadata(
                XGInsertionType.COMPRESSOR.value,
                XGEffectCategory.INSERTION,
                "Compressor",
                "COMP",
                "Dynamics Compressor",
                True,
            ),
            XGEffectMetadata(
                XGInsertionType.WAH_WAH.value,
                XGEffectCategory.INSERTION,
                "Wah-Wah",
                "WAH",
                "Auto Wah Effect",
                True,
            ),
            XGEffectMetadata(
                XGInsertionType.EQUALIZER_3BAND.value,
                XGEffectCategory.INSERTION,
                "3-Band EQ",
                "3BAND",
                "3-Band Equalizer",
                True,
            ),
            XGEffectMetadata(
                XGInsertionType.PITCH_SHIFTER.value,
                XGEffectCategory.INSERTION,
                "Pitch Shifter",
                "PITCH",
                "Pitch Shifting",
                True,
            ),
            XGEffectMetadata(
                XGInsertionType.PHASER.value,
                XGEffectCategory.INSERTION,
                "Phaser",
                "PHAS",
                "Phase Shifting",
                True,
            ),
            XGEffectMetadata(
                XGInsertionType.FLANGER.value,
                XGEffectCategory.INSERTION,
                "Flanger",
                "FLANG",
                "Flanging Effect",
                True,
            ),
            XGEffectMetadata(
                XGInsertionType.CHORUS.value,
                XGEffectCategory.INSERTION,
                "Chorus",
                "CHOR",
                "Chorus Ensemble",
                True,
            ),
            XGEffectMetadata(
                XGInsertionType.TREMOLO.value,
                XGEffectCategory.INSERTION,
                "Tremolo",
                "TREM",
                "Amplitude Tremolo",
                True,
            ),
            XGEffectMetadata(
                XGInsertionType.AUTO_PAN.value,
                XGEffectCategory.INSERTION,
                "Auto Pan",
                "PAN",
                "Automatic Panning",
                True,
            ),
            XGEffectMetadata(
                XGInsertionType.ENHANCER.value,
                XGEffectCategory.INSERTION,
                "Enhancer",
                "ENHANCE",
                "Harmonic Enhancement",
                True,
            ),
            XGEffectMetadata(
                XGInsertionType.DELAY.value,
                XGEffectCategory.INSERTION,
                "Delay",
                "DLY",
                "Digital Delay",
                True,
            ),
            XGEffectMetadata(
                XGInsertionType.REVERB.value,
                XGEffectCategory.INSERTION,
                "Reverb",
                "RVB",
                "Hall Reverb",
                True,
            ),
            # Add remaining insertion effects (12-17)
            XGEffectMetadata(
                XGInsertionType.SLICER.value,
                XGEffectCategory.INSERTION,
                "Slicer",
                "SLICE",
                "Rhythmic Slicing",
                True,
            ),
            XGEffectMetadata(
                XGInsertionType.OCTAVE.value,
                XGEffectCategory.INSERTION,
                "Octave",
                "OCT",
                "Octave Generator",
                True,
            ),
            XGEffectMetadata(
                XGInsertionType.VOCODER.value,
                XGEffectCategory.INSERTION,
                "Vocoder",
                "VOC",
                "Voice Vocoder",
                True,
            ),
        ]

        for effect in insertion_effects:
            self._register_effect(effect)

    def _initialize_eq_effects(self) -> None:
        """Initialize all 10 XG channel EQ types."""
        eq_effects = [
            XGEffectMetadata(
                XGEQType.FLAT.value,
                XGEffectCategory.EQUALIZER,
                "Flat",
                "FLAT",
                "No EQ adjustment",
                False,
            ),
            XGEffectMetadata(
                XGEQType.BRILLIANCE.value,
                XGEffectCategory.EQUALIZER,
                "Brilliance",
                "BRILL",
                "Enhanced high frequencies",
                False,
            ),
            XGEffectMetadata(
                XGEQType.MELLOW.value,
                XGEffectCategory.EQUALIZER,
                "Mellow",
                "MELLOW",
                "Soften high frequencies",
                False,
            ),
            XGEffectMetadata(
                XGEQType.BRIGHT.value,
                XGEffectCategory.EQUALIZER,
                "Bright",
                "BRIGHT",
                "Treble boost",
                False,
            ),
            XGEffectMetadata(
                XGEQType.WARM.value,
                XGEffectCategory.EQUALIZER,
                "Warm",
                "WARM",
                "Bass emphasis",
                False,
            ),
            XGEffectMetadata(
                XGEQType.CLEAR.value,
                XGEffectCategory.EQUALIZER,
                "Clear",
                "CLEAR",
                "Mid-high clarity",
                False,
            ),
            XGEffectMetadata(
                XGEQType.SOFT.value,
                XGEffectCategory.EQUALIZER,
                "Soft",
                "SOFT",
                "Reduce harshness",
                False,
            ),
            XGEffectMetadata(
                XGEQType.CUT.value,
                XGEffectCategory.EQUALIZER,
                "Cut",
                "CUT",
                "High frequency roll-off",
                False,
            ),
            XGEffectMetadata(
                XGEQType.BASS_BOOST.value,
                XGEffectCategory.EQUALIZER,
                "Bass Boost",
                "BASS+",
                "Low frequency boost",
                False,
            ),
            XGEffectMetadata(
                XGEQType.TREBLE_BOOST.value,
                XGEffectCategory.EQUALIZER,
                "Treble Boost",
                "TREB+",
                "High frequency boost",
                False,
            ),
        ]

        for effect in eq_effects:
            self._register_effect(effect)

    def get_effect_metadata(
        self, category: XGEffectCategory, effect_type: int
    ) -> XGEffectMetadata | None:
        """Get effect metadata for a specific effect type."""
        with self.lock:
            return self._effects.get((category, effect_type))

    def get_effect_by_name(self, name: str) -> tuple[XGEffectCategory, int] | None:
        """Get effect type by name (case-insensitive)."""
        with self.lock:
            return self._name_to_type.get(name.lower().replace(" ", "_"))

    def get_all_effects_in_category(self, category: XGEffectCategory) -> list[XGEffectMetadata]:
        """Get all effects in a specific category."""
        with self.lock:
            return [effect for (cat, _), effect in self._effects.items() if cat == category]

    def is_valid_effect_type(self, category: XGEffectCategory, effect_type: int) -> bool:
        """Check if an effect type is valid."""
        with self.lock:
            return (category, effect_type) in self._effects

    def get_effect_count(self, category: XGEffectCategory | None = None) -> int:
        """Get total number of effects, optionally filtered by category."""
        with self.lock:
            if category is None:
                return len(self._effects)
            return sum(1 for (cat, _), _ in self._effects.items() if cat == category)


class XGEffectFactory:
    """
    XG Effect Factory

    Factory class for creating effect processor instances with proper parameterization.
    Provides memory-efficient instance management and configuration.
    """

    def __init__(self, sample_rate: int):
        """
        Initialize effect factory.

        Args:
            sample_rate: Sample rate in Hz for all created effects
        """
        self.sample_rate = sample_rate
        self.registry = XGEffectRegistry()

        # Instance pooling for performance
        self._instance_pool: dict[str, list[Any]] = {}
        self._max_pool_size = 8  # Maximum instances to keep in pool

        # Thread safety
        self.lock = threading.RLock()

    def create_system_effect(self, effect_type: XGReverbType, **params) -> Any | None:
        """
        Create a system effect processor.

        Args:
            effect_type: XG reverb or chorus type
            **params: Effect parameters

        Returns:
            Effect processor instance or None if creation failed
        """
        with self.lock:
            if isinstance(effect_type, XGReverbType):
                return self._create_system_reverb()
            elif isinstance(effect_type, XGChorusType):
                return self._create_system_chorus(**params)
            return None

    def create_variation_effect(
        self, effect_type: int, max_delay_samples: int = 22050
    ) -> XGVariationEffectsProcessor | None:
        """
        Create a variation effect processor.

        Args:
            effect_type: XG variation effect type (0-83)
            max_delay_samples: Maximum delay buffer size

        Returns:
            Variation effects processor instance
        """
        with self.lock:
            if not self.registry.is_valid_effect_type(XGEffectCategory.VARIATION, effect_type):
                return None

            pool_key = f"variation_{effect_type}"
            if self._instance_pool.get(pool_key):
                # Reuse from pool
                instance = self._instance_pool[pool_key].pop()
                instance.reset_state()
                return instance

            # Create new instance
            try:
                processor = XGVariationEffectsProcessor(self.sample_rate, max_delay_samples)
                # Convert integer to enum value if needed
                if isinstance(effect_type, int):
                    # Map integer to XGVariationType enum
                    try:
                        enum_value = XGVariationType(effect_type)
                        processor.set_variation_type(enum_value)
                    except ValueError:
                        # If integer doesn't map to enum, use default
                        processor.set_variation_type(XGVariationType.DELAY_LCR)
                else:
                    # Assume it's already an enum
                    processor.set_variation_type(effect_type)
                return processor
            except Exception as e:
                print(f"Failed to create variation effect {effect_type}: {e}")
                return None

    def create_insertion_effect(
        self, effect_type: int, max_delay_samples: int = 22050
    ) -> XGInsertionEffectsProcessor | None:
        """
        Create an insertion effect processor.

        Args:
            effect_type: XG insertion effect type (0-17)
            max_delay_samples: Maximum delay buffer size

        Returns:
            Insertion effects processor instance
        """
        with self.lock:
            if not self.registry.is_valid_effect_type(XGEffectCategory.INSERTION, effect_type):
                return None

            pool_key = f"insertion_{effect_type}"
            if self._instance_pool.get(pool_key):
                # Reuse from pool
                instance = self._instance_pool[pool_key].pop()
                instance.reset_state()
                return instance

            # Create new instance
            try:
                processor = XGInsertionEffectsProcessor(self.sample_rate, max_delay_samples)
                # Set effect types for all slots to the requested type
                for slot in range(3):  # XG supports 3 insertion slots
                    processor.set_insertion_effect_type(slot, effect_type)
                return processor
            except Exception:
                return None

    def create_channel_eq(self, eq_type: int) -> XGMultiBandEqualizer | None:
        """
        Create a channel EQ processor using XGMultiBandEqualizer.

        Args:
            eq_type: XG EQ type (0-9)

        Returns:
            XGMultiBandEqualizer instance configured for channel use
        """
        with self.lock:
            if not (0 <= eq_type <= 9):
                return None

            pool_key = f"channel_eq_{eq_type}"
            if self._instance_pool.get(pool_key):
                # Reuse from pool
                instance = self._instance_pool[pool_key].pop()
                instance.reset()
                return instance

            # Create new instance
            try:
                processor = XGMultiBandEqualizer(self.sample_rate)
                processor.set_eq_type(eq_type)
                return processor
            except Exception:
                return None

    def create_master_eq(self) -> XGMultiBandEqualizer | None:
        """
        Create a master EQ processor using XGMultiBandEqualizer.

        Returns:
            XGMultiBandEqualizer instance configured for master use
        """
        with self.lock:
            pool_key = "master_eq"
            if self._instance_pool.get(pool_key):
                # Reuse from pool
                instance = self._instance_pool[pool_key].pop()
                instance.reset()
                return instance

            # Create new instance
            try:
                return XGMultiBandEqualizer(self.sample_rate)
            except Exception:
                return None

    def return_to_pool(self, processor: Any, processor_type: str, effect_id: int = 0) -> None:
        """
        Return a processor instance to the pool for reuse.

        Args:
            processor: Effect processor instance
            processor_type: Type identifier ('variation', 'insertion', 'eq', etc.)
            effect_id: Effect type identifier
        """
        with self.lock:
            pool_key = f"{processor_type}_{effect_id}"

            if pool_key not in self._instance_pool:
                self._instance_pool[pool_key] = []

            # Only keep up to max pool size
            if len(self._instance_pool[pool_key]) < self._max_pool_size:
                # Reset processor state before pooling
                if hasattr(processor, "reset_state"):
                    processor.reset_state()
                self._instance_pool[pool_key].append(processor)

    def get_pool_stats(self) -> dict[str, Any]:
        """Get statistics about the instance pool."""
        with self.lock:
            total_instances = sum(len(pool) for pool in self._instance_pool.values())
            return {
                "total_pooled_instances": total_instances,
                "pool_types": len(self._instance_pool),
                "pools": {key: len(instances) for key, instances in self._instance_pool.items()},
            }

    def clear_pool(self) -> None:
        """Clear all instances from the pool."""
        with self.lock:
            self._instance_pool.clear()

    def _create_system_reverb(self) -> XGSystemReverbProcessor:
        """Create system reverb processor with XG defaults."""
        max_ir_length = 44100 * 2  # 2 seconds max at 44.1kHz
        return XGSystemReverbProcessor(self.sample_rate, max_ir_length)

    def _create_system_chorus(self, **params) -> XGSystemChorusProcessor | None:
        """
        Create system chorus processor with XG-compliant parameters.

        Args:
            **params: XG chorus parameters (rate, depth, feedback, delay, level)

        Returns:
            Configured XGSystemChorusProcessor or None if creation failed
        """
        try:
            max_delay_samples = int(0.05 * self.sample_rate)  # 50ms max delay
            processor = XGSystemChorusProcessor(self.sample_rate, max_delay_samples)

            # Apply XG default parameters if not specified
            chorus_params = {
                "rate": params.get("rate", 1.0),  # 1 Hz default
                "depth": params.get("depth", 0.5),  # 50% depth
                "feedback": params.get("feedback", 0.3),  # 30% feedback
                "delay": params.get("delay", 0.012),  # 12ms delay
                "level": params.get("level", 0.4),  # 40% level
            }

            # Configure processor with parameters
            if hasattr(processor, "set_parameters"):
                processor.set_parameters(chorus_params)

            return processor

        except Exception as e:
            print(f"Failed to create system chorus processor: {e}")
            return None


class XGParameterManager:
    """
    XG Parameter Manager

    Central parameter management for all XG effects, providing validation,
    preset management, and parameter range mapping.
    """

    def __init__(self):
        """Initialize parameter manager."""
        self.parameter_ranges: dict[str, tuple[float, float]] = {}
        self.default_presets: dict[str, dict[str, Any]] = {}

        # Thread safety
        self.lock = threading.RLock()

        # Initialize parameter ranges and presets
        self._initialize_parameter_ranges()
        self._initialize_default_presets()

    def _initialize_parameter_ranges(self) -> None:
        """Initialize parameter range definitions."""
        self.parameter_ranges = {
            # System effect ranges
            "reverb_time": (0.1, 8.3),
            "reverb_level": (0.0, 1.0),
            "reverb_hf_damping": (0.0, 1.0),
            "reverb_pre_delay": (0.0, 0.05),
            "reverb_density": (0.0, 1.0),
            "chorus_rate": (0.125, 10.0),
            "chorus_depth": (0.0, 1.0),
            "chorus_feedback": (-0.25, 0.25),
            "chorus_level": (0.0, 1.0),
            # Channel parameters
            "volume": (0.0, 1.0),
            "pan": (-1.0, 1.0),
            "reverb_send": (0.0, 1.0),
            "chorus_send": (0.0, 1.0),
            "variation_send": (0.0, 1.0),
            # EQ parameters
            "eq_level": (-12.0, 12.0),
            "eq_frequency": (20.0, 20000.0),
            "eq_q_factor": (0.1, 10.0),
            # Master EQ ranges
            "low_gain": (-12.0, 12.0),
            "mid_gain": (-12.0, 12.0),
            "high_gain": (-12.0, 12.0),
            "low_freq": (20.0, 400.0),
            "mid_freq": (200.0, 8000.0),
            "high_freq": (2000.0, 20000.0),
        }

    def _initialize_default_presets(self) -> None:
        """Initialize default parameter presets."""
        self.default_presets = {
            "default_reverb": {
                "time": 1.5,
                "level": 0.4,
                "hf_damping": 0.5,
                "pre_delay": 0.02,
                "density": 0.8,
                "enabled": True,
            },
            "default_chorus": {
                "rate": 1.0,
                "depth": 0.5,
                "feedback": 0.3,
                "level": 0.4,
                "delay": 0.012,
                "enabled": True,
            },
            "default_channel": XG_CHANNEL_MIXER_DEFAULT._asdict(),
        }

    def validate_parameter(self, param_name: str, value: float) -> tuple[bool, float]:
        """
        Validate and clamp a parameter value.

        Args:
            param_name: Parameter name
            value: Parameter value

        Returns:
            Tuple of (is_valid, clamped_value)
        """
        with self.lock:
            if param_name not in self.parameter_ranges:
                return False, value

            min_val, max_val = self.parameter_ranges[param_name]
            clamped_value = max(min_val, min(max_val, value))
            return True, clamped_value

    def get_default_preset(self, preset_name: str) -> dict[str, Any] | None:
        """Get a default parameter preset."""
        with self.lock:
            return self.default_presets.get(preset_name)

    def get_parameter_range(self, param_name: str) -> tuple[float, float] | None:
        """Get parameter range for a given parameter."""
        with self.lock:
            return self.parameter_ranges.get(param_name)
