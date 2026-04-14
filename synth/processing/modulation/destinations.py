"""
Modulation destinations for XG synthesizer.
Defines all available modulation destinations.
"""

from __future__ import annotations


class ModulationDestination:
    """Class for representing modulation destination"""

    FILTER_CUTOFF = "filter_cutoff"
    PITCH = "pitch"
    FILTER_RESONANCE = "filter_resonance"
    AMP = "amp"
    PAN = "pan"
    LFO1_RATE = "lfo1_rate"
    LFO2_RATE = "lfo2_rate"
    LFO3_RATE = "lfo3_rate"
    LFO1_DEPTH = "lfo1_depth"
    LFO2_DEPTH = "lfo2_depth"
    LFO3_DEPTH = "lfo3_depth"
    VELOCITY_CROSSFADE = "velocity_crossfade"
    NOTE_CROSSFADE = "note_crossfade"

    # New destinations from SoundFont
    FILTER_ATTACK = "filter_attack"
    FILTER_DECAY = "filter_decay"
    FILTER_DELAY = "filter_delay"
    FILTER_SUSTAIN = "filter_sustain"
    FILTER_RELEASE = "filter_release"
    FILTER_HOLD = "filter_hold"
    AMP_ATTACK = "amp_attack"
    AMP_DECAY = "amp_decay"
    AMP_DELAY = "amp_delay"
    AMP_SUSTAIN = "amp_sustain"
    AMP_RELEASE = "amp_release"
    AMP_HOLD = "amp_hold"
    PITCH_ATTACK = "pitch_attack"
    PITCH_DECAY = "pitch_decay"
    PITCH_SUSTAIN = "pitch_sustain"
    PITCH_RELEASE = "pitch_release"
    PITCH_HOLD = "pitch_hold"
    STEREO_WIDTH = "stereo_width"
    TREMOLO_DEPTH = "tremolo_depth"
    TREMOLO_RATE = "tremolo_rate"
    COARSE_TUNE = "coarse_tune"
    FINE_TUNE = "fine_tune"
    DETUNE = "detune"
    PHASER_DEPTH = "phaser_depth"

    @staticmethod
    def get_all_destinations():
        return [
            ModulationDestination.PITCH,
            ModulationDestination.FILTER_CUTOFF,
            ModulationDestination.FILTER_RESONANCE,
            ModulationDestination.AMP,
            ModulationDestination.PAN,
            ModulationDestination.LFO1_RATE,
            ModulationDestination.LFO2_RATE,
            ModulationDestination.LFO3_RATE,
            ModulationDestination.LFO1_DEPTH,
            ModulationDestination.LFO2_DEPTH,
            ModulationDestination.LFO3_DEPTH,
            ModulationDestination.VELOCITY_CROSSFADE,
            ModulationDestination.NOTE_CROSSFADE,
            ModulationDestination.FILTER_ATTACK,
            ModulationDestination.FILTER_DECAY,
            ModulationDestination.FILTER_SUSTAIN,
            ModulationDestination.FILTER_RELEASE,
            ModulationDestination.FILTER_HOLD,
            ModulationDestination.AMP_ATTACK,
            ModulationDestination.AMP_DECAY,
            ModulationDestination.AMP_SUSTAIN,
            ModulationDestination.AMP_RELEASE,
            ModulationDestination.AMP_HOLD,
            ModulationDestination.PITCH_ATTACK,
            ModulationDestination.PITCH_DECAY,
            ModulationDestination.PITCH_SUSTAIN,
            ModulationDestination.PITCH_RELEASE,
            ModulationDestination.PITCH_HOLD,
            ModulationDestination.STEREO_WIDTH,
            ModulationDestination.TREMOLO_DEPTH,
            ModulationDestination.TREMOLO_RATE,
            ModulationDestination.COARSE_TUNE,
            ModulationDestination.FINE_TUNE,
            ModulationDestination.DETUNE,
            ModulationDestination.PHASER_DEPTH,
        ]
