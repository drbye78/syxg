"""
XG Effects - Individual Effect Implementations

This module contains implementations of individual XG effects
including distortion, delay, reverb, chorus, phaser, flanger, etc.
"""

from .base import BaseEffect
from .distortion import DistortionEffect
from .delay import DelayEffect
from .reverb import ReverbEffect
from .chorus import ChorusEffect
from .phaser import PhaserEffect
from .flanger import FlangerEffect
from .compressor import CompressorEffect
from .tremolo import TremoloEffect
from .auto_wah import AutoWahEffect
from .pitch_shifter import PitchShifterEffect
from .ring_mod import RingModEffect
from .gate import Gate
from .envelope_filter import EnvelopeFilterEffect
from .rotary_speaker import RotarySpeaker
from .echo import Echo
from .harmonizer import HarmonizerEffect
from .vocoder import VocoderEffect
from .octave import OctaveEffect
from .detune import DetuneEffect
from .guitar_amp_sim import GuitarAmpSimEffect
from .leslie import LeslieEffect
from .enhancer import EnhancerEffect
from .limiter import Limiter
from .expander import Expander
from .vibrato import VibratoEffect
from .auto_pan import AutoPan
from .slicer import Slicer
from .talk_wah import TalkWahEffect
from .dual_delay import DualDelay
from .pan_delay import PanDelay
from .multi_tap_delay import MultiTapDelay
from .reverse_delay import ReverseDelay
from .cross_delay import CrossDelay
from .step_phaser import StepPhaser
from .step_flanger import StepFlanger
from .step_delay import StepDelay
from .stereo_imager import StereoImagerEffect
from .chorus_reverb import ChorusReverbEffect
from .acoustic_simulator import AcousticSimulatorEffect
from .ambience import AmbienceEffect
from .doubler import DoublerEffect
from .spectral import SpectralEffect
from .resonator import ResonatorEffect
from .degrader import DegraderEffect
from .vinyl import VinylEffect
from .looper import LooperEffect
from .auto_filter import AutoFilterEffect
from .enhancer_reverb import EnhancerReverbEffect
from .step_compressor import StepCompressorEffect
from .step_cross_delay import StepCrossDelayEffect
from .step_distortion import StepDistortionEffect
from .step_echo import StepEchoEffect
from .step_expander import StepExpanderEffect
from .step_filter import StepFilterEffect
from .step_gate import StepGateEffect
from .step_limiter import StepLimiterEffect
from .step_multi_tap import StepMultiTapEffect
from .step_overdrive import StepOverdriveEffect
from .step_pan import StepPanEffect
from .step_pan_delay import StepPanDelayEffect
from .step_pitch_shifter import StepPitchShifterEffect
from .step_reverse_delay import StepReverseDelayEffect
from .step_ring_mod import StepRingModEffect
from .step_rotary_speaker import StepRotarySpeakerEffect
from .step_tremolo import StepTremoloEffect

# New missing effects implemented
from .talk_wah_variation import TalkWahVariationEffect
from .harmonizer_variation import HarmonizerVariationEffect
from .octave_variation import OctaveVariationEffect
from .detune_variation import DetuneVariationEffect

__all__ = [
    "BaseEffect",
    "DistortionEffect",
    "DelayEffect",
    "ReverbEffect",
    "ChorusEffect",
    "PhaserEffect",
    "FlangerEffect",
    "CompressorEffect",
    "TremoloEffect",
    "AutoWahEffect",
    "PitchShifterEffect",
    "RingModEffect",
    "Gate",
    "EnvelopeFilterEffect",
    "RotarySpeaker",
    "Echo",
    "HarmonizerEffect",
    "VocoderEffect",
    "OctaveEffect",
    "DetuneEffect",
    "GuitarAmpSimEffect",
    "LeslieEffect",
    "EnhancerEffect",
    "Limiter",
    "Expander",
    "VibratoEffect",
    "AutoPan",
    "Slicer",
    "TalkWahEffect",
    "DualDelay",
    "PanDelay",
    "MultiTapDelay",
    "ReverseDelay",
    "CrossDelay",
    "StepPhaser",
    "StepFlanger",
    "StepDelay",
    "StereoImagerEffect",
    "ChorusReverbEffect",
    "AcousticSimulatorEffect",
    "AmbienceEffect",
    "DoublerEffect",
    "SpectralEffect",
    "ResonatorEffect",
    "DegraderEffect",
    "VinylEffect",
    "LooperEffect",
    "AutoFilterEffect",
    "EnhancerReverbEffect",
    "StepCompressorEffect",
    "StepCrossDelayEffect",
    "StepDistortionEffect",
    "StepEchoEffect",
    "StepExpanderEffect",
    "StepFilterEffect",
    "StepGateEffect",
    "StepLimiterEffect",
    "StepMultiTapEffect",
    "StepOverdriveEffect",
    "StepPanEffect",
    "StepPanDelayEffect",
    "StepPitchShifterEffect",
    "StepReverseDelayEffect",
    "StepRingModEffect",
    "StepRotarySpeakerEffect",
    "StepTremoloEffect",
    # New missing effects implemented
    "TalkWahVariationEffect",
    "HarmonizerVariationEffect",
    "OctaveVariationEffect",
    "DetuneVariationEffect",
]
