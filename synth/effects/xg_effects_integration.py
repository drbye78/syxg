"""
XG Effects Integration System

Integrates XG-specific effects with MIDI 2.0 parameter resolution and per-note control.
Provides comprehensive support for XG system effects, insertion effects, and variation effects
with 32-bit parameter precision.
"""

from __future__ import annotations

import math
from enum import IntEnum

import numpy as np

from .midi_2_effects_processor import (
    EffectParameter,
    EffectProcessor,
    EffectType,
    ParameterResolution,
)


class XGEffectType(IntEnum):
    """XG-specific effect types"""

    # System Effects (applied globally)
    REVERB_PLATE = 0x00
    REVERB_HALL = 0x01
    REVERB_ROOM = 0x02
    REVERB_STUDIO = 0x03
    REVERB_GATED = 0x04
    REVERB_REVERSE = 0x05
    REVERB_SHORT = 0x06
    REVERB_LONG = 0x07

    CHORUS_STANDARD = 0x10
    CHORUS_FLANGER = 0x11
    CHORUS_CELESTE = 0x12
    CHORUS_DETUNE = 0x13
    CHORUS_DIMENSION = 0x14

    # Variation Effects (multi-function)
    VARIATION_MULTI_CHORUS = 0x20
    VARIATION_STEREO_DELAY = 0x21
    VARIATION_TREMOLO = 0x22
    VARIATION_AUTO_PANNER = 0x23
    VARIATION_PHASER = 0x24
    VARIATION_FLANGER = 0x25
    VARIATION_ROTARY_SPEAKER = 0x26
    VARIATION_DISTORTION = 0x27
    VARIATION_COMPRESSOR = 0x28
    VARIATION_GATE = 0x29
    VARIATION_EQ = 0x2A
    VARIATION_FILTER = 0x2B
    VARIATION_OCTAVE = 0x2C
    VARIATION_PITCH_SHIFTER = 0x2D
    VARIATION_FEEDBACK_DELAY = 0x2E
    VARIATION_LOFI = 0x2F

    # Insertion Effects (per-part)
    INSERT_DUAL_DELAY = 0x40
    INSERT_STEREO_DELAY = 0x41
    INSERT_MULTI_TAP_DELAY = 0x42
    INSERT_CROSS_DELAY = 0x43
    INSERT_MOD_DELAY = 0x44
    INSERT_STEREO_CHORUS = 0x45
    INSERT_MONO_CHORUS = 0x46
    INSERT_MULTI_CHORUS = 0x47
    INSERT_STEREO_FLANGER = 0x48
    INSERT_MONO_FLANGER = 0x49
    INSERT_STEREO_PHASER = 0x4A
    INSERT_MONO_PHASER = 0x4B
    INSERT_STEREO_TREMOLO = 0x4C
    INSERT_MONO_TREMOLO = 0x4D
    INSERT_AUTO_PANNER = 0x4E
    INSERT_ROTARY_SPEAKER = 0x4F
    INSERT_DISTORTION = 0x50
    INSERT_OVERDRIVE = 0x51
    INSERT_AMP_SIMULATOR = 0x52
    INSERT_COMPRESSOR = 0x53
    INSERT_LIMITER = 0x54
    INSERT_GATE = 0x55
    INSERT_EXPANDER = 0x56
    INSERT_EQ_3_BAND = 0x57
    INSERT_EQ_5_BAND = 0x58
    INSERT_EQ_7_BAND = 0x59
    INSERT_EQ_15_BAND = 0x5A
    INSERT_EQ_PARAMETRIC = 0x5B
    INSERT_FILTER_LOW_PASS = 0x5C
    INSERT_FILTER_HIGH_PASS = 0x5D
    INSERT_FILTER_BAND_PASS = 0x5E
    INSERT_FILTER_NOTCH = 0x5F
    INSERT_FILTER_FORMANT = 0x60
    INSERT_FILTER_WOW_FLUTTER = 0x61
    INSERT_PITCH_SHIFTER = 0x62
    INSERT_MONO_TO_STEREO = 0x63
    INSERT_SIX_BAND_EQ = 0x64
    INSERT_DRIVE = 0x65
    INSERT_TALK_MODULATOR = 0x66
    INSERT_ENSEMBLE = 0x67
    INSERT_HARMONIZER = 0x68
    INSERT_ACOUSTIC_SIMULATOR = 0x69
    INSERT_CROSSOVER = 0x6A
    INSERT_LOFI = 0x6B
    INSERT_VOCODER = 0x6C
    INSERT_GRANULAR = 0x6D
    INSERT_SPECTRAL = 0x6E
    INSERT_CONVOLUTION_REVERB = 0x6F


class XGSystemReverb(EffectProcessor):
    """XG System Reverb with MIDI 2.0 support"""

    def __init__(
        self, sample_rate: int = 48000, reverb_type: XGEffectType = XGEffectType.REVERB_HALL
    ):
        self.effect_type = EffectType.REVERB
        self.xg_effect_type = reverb_type
        self.sample_rate = sample_rate
        self.enabled = True
        self.bypass = False

        # Effect parameters with XG-specific ranges and MIDI 2.0 support
        self.parameters: dict[str, EffectParameter] = {}
        self._initialize_xg_parameters()

        # Per-note parameter values (for MIDI 2.0 per-note control)
        self.per_note_parameters: dict[int, dict[str, float]] = {}

        # Internal reverb state
        self.comb_buffers: list[np.ndarray] = []
        self.allpass_buffers: list[np.ndarray] = []
        self.allpass_feedback: list[float] = []
        self.late_stage_buffers: list[np.ndarray] = []

        # Setup reverb structure based on type
        self._setup_reverb_structure()

    def _initialize_xg_parameters(self):
        """Initialize XG-specific reverb parameters."""
        # Standard XG reverb parameters
        self.parameters["reverb_type"] = EffectParameter(
            name="reverb_type",
            min_value=0,
            max_value=7,  # 8 reverb types
            default_value=self.xg_effect_type.value,
            resolution=ParameterResolution.MIDI_2_32_BIT,
            unit="enum",
            description="XG reverb type",
        )

        self.parameters["character"] = EffectParameter(
            name="character",
            min_value=0,
            max_value=127,
            default_value=0,  # Hall A for XG Hall Reverb
            resolution=ParameterResolution.MIDI_2_32_BIT,
            unit="",
            description="Reverb character/type variation",
        )

        self.parameters["pre_delay_time"] = EffectParameter(
            name="pre_delay_time",
            min_value=0.0,
            max_value=0.5,  # 500ms max
            default_value=0.0,
            resolution=ParameterResolution.MIDI_2_32_BIT,
            unit="s",
            description="Pre-delay time",
        )

        self.parameters["color"] = EffectParameter(
            name="color",
            min_value=0,
            max_value=127,
            default_value=64,  # Neutral
            resolution=ParameterResolution.MIDI_2_32_BIT,
            unit="",
            description="Reverb coloration",
        )

        self.parameters["time"] = EffectParameter(
            name="time",
            min_value=0.1,
            max_value=60.0,  # Up to 60 seconds
            default_value=5.0,  # 5 seconds default
            resolution=ParameterResolution.MIDI_2_32_BIT,
            unit="s",
            description="Reverb decay time",
        )

        self.parameters["pre_lpf"] = EffectParameter(
            name="pre_lpf",
            min_value=200.0,
            max_value=20000.0,  # 200Hz to 20kHz
            default_value=8000.0,  # 8kHz default
            resolution=ParameterResolution.MIDI_2_32_BIT,
            unit="Hz",
            description="Pre-low pass filter frequency",
        )

        self.parameters["level"] = EffectParameter(
            name="level",
            min_value=0.0,
            max_value=1.0,
            default_value=0.5,  # 50% default
            resolution=ParameterResolution.MIDI_2_32_BIT,
            unit="",
            description="Reverb output level",
        )

        self.parameters["send_level"] = EffectParameter(
            name="send_level",
            min_value=0.0,
            max_value=1.0,
            default_value=0.0,  # No send by default
            resolution=ParameterResolution.MIDI_2_32_BIT,
            unit="",
            description="Reverb send level",
        )

    def _setup_reverb_structure(self):
        """Setup the internal reverb structure based on type."""
        # Create comb filters for early reflections and late reverb
        comb_tunings = [
            0.0297,
            0.0371,
            0.0411,
            0.0437,
            0.0485,
            0.0511,
            0.0539,
            0.0591,
        ]  # In seconds
        for tuning in comb_tunings:
            delay_samples = int(tuning * self.sample_rate)
            delay_line = np.zeros(delay_samples)
            self.comb_buffers.append(delay_line)

        # Create allpass filters for reverb diffusion
        allpass_tunings = [0.005, 0.0067, 0.0083, 0.0091]  # In seconds
        self.allpass_feedback = [0.7, 0.7, 0.7, 0.7]  # Standard allpass feedback values
        for tuning in allpass_tunings:
            delay_samples = int(tuning * self.sample_rate)
            delay_line = np.zeros(delay_samples)
            self.allpass_buffers.append(delay_line)

    def _apply_effect(self, audio_input: np.ndarray, note: int | None = None) -> np.ndarray:
        """Apply XG reverb effect processing."""
        if audio_input.ndim == 1:
            # Convert mono to stereo
            audio_input = np.column_stack([audio_input, audio_input])

        output = np.zeros_like(audio_input, dtype=np.float32)
        input_len = len(audio_input)

        # Get XG-specific parameters (potentially per-note)
        reverb_char = self.get_parameter("character", note)
        pre_delay_time = self.get_parameter("pre_delay_time", note)
        color = self.get_parameter("color", note)
        decay_time = self.get_parameter("time", note)
        pre_lpf_freq = self.get_parameter("pre_lpf", note)
        level = self.get_parameter("level", note)
        send_level = self.get_parameter("send_level", note)

        # Apply pre-delay if specified
        pre_delay_samples = int(pre_delay_time * self.sample_rate)
        if pre_delay_samples > 0:
            delayed_input = np.zeros((input_len + pre_delay_samples, 2), dtype=np.float32)
            delayed_input[pre_delay_samples:, :] = audio_input
            audio_input = delayed_input[:input_len, :]

        # Apply pre-filtering based on color parameter
        filtered_input = self._apply_pre_filter(audio_input, pre_lpf_freq, color)

        # Process through comb filters (early reflections and late reverb)
        comb_output = np.zeros_like(filtered_input, dtype=np.float32)

        for i in range(len(self.comb_buffers)):
            comb_delay = self.comb_buffers[i]
            feedback = 0.85 * (decay_time / 5.0)  # Adjust feedback based on decay time

            for j in range(input_len):
                # Calculate delay index with wraparound
                delay_idx = (j - len(comb_delay)) % len(comb_delay)

                # Get delayed signal
                delayed_signal = comb_delay[delay_idx]

                # Calculate input with feedback
                input_signal = (filtered_input[j, 0] + filtered_input[j, 1]) * 0.5  # Sum to mono
                output_signal = input_signal + delayed_signal * feedback

                # Update delay line
                comb_delay[j % len(comb_delay)] = output_signal

                # Add to comb output
                comb_output[j, 0] += delayed_signal
                comb_output[j, 1] += delayed_signal

        # Normalize comb output
        comb_output /= len(self.comb_buffers)

        # Process through allpass filters for diffusion
        allpass_output = comb_output.copy()

        for i, (delay_line, feedback) in enumerate(
            zip(self.allpass_buffers, self.allpass_feedback)
        ):
            for j in range(input_len):
                delay_idx = (j - len(delay_line)) % len(delay_line)

                # Get delayed signal
                delayed_signal = delay_line[delay_idx]

                # Calculate allpass output
                input_val = allpass_output[j, 0]  # Process left channel
                output_val = -input_val * feedback + delayed_signal
                allpass_output[j, 0] = output_val

                # Update delay line
                delay_line[j % len(delay_line)] = input_val + output_val * feedback

        # Apply stereo spread to right channel
        for j in range(input_len):
            allpass_output[j, 1] = allpass_output[j, 0]  # For simplicity, duplicate to right

        # Mix dry and wet signals based on send level
        wet_signal = allpass_output * level
        output[:, 0] = audio_input[:, 0] * (1.0 - send_level) + wet_signal[:, 0] * send_level
        output[:, 1] = audio_input[:, 1] * (1.0 - send_level) + wet_signal[:, 1] * send_level

        return output

    def _apply_pre_filter(self, audio: np.ndarray, cutoff_freq: float, color: float) -> np.ndarray:
        """Apply pre-filtering to input audio."""
        # Simple low-pass filter implementation
        # In a real implementation, this would be a more sophisticated filter
        if cutoff_freq >= 20000:  # Above audible range, no filtering
            return audio

        # Normalize cutoff frequency
        nyquist = self.sample_rate / 2.0
        normalized_freq = min(cutoff_freq / nyquist, 0.99)  # Keep below Nyquist

        # Apply simple first-order low-pass filter
        output = np.zeros_like(audio)
        a = 1.0 - normalized_freq  # Feedback coefficient
        b = normalized_freq  # Feedforward coefficient

        # Apply filter to each channel
        for ch in range(audio.shape[1]):
            prev_out = 0.0
            for i in range(len(audio)):
                output[i, ch] = b * audio[i, ch] + a * prev_out
                prev_out = output[i, ch]

        return output


class XGVariationEffect(EffectProcessor):
    """XG Variation Effect with MIDI 2.0 support"""

    def __init__(
        self, sample_rate: int = 48000, var_type: XGEffectType = XGEffectType.VARIATION_MULTI_CHORUS
    ):
        self.effect_type = EffectType.CHORUS  # Variations can be chorus-like
        self.xg_effect_type = var_type
        self.sample_rate = sample_rate
        self.enabled = True
        self.bypass = False

        # Effect parameters with XG-specific ranges and MIDI 2.0 support
        self.parameters: dict[str, EffectParameter] = {}
        self._initialize_xg_variation_parameters()

        # Per-note parameter values (for MIDI 2.0 per-note control)
        self.per_note_parameters: dict[int, dict[str, float]] = {}

        # Internal effect state
        self.lfo_phase = 0.0
        self.delay_buffer = np.zeros(int(0.1 * sample_rate))  # 100ms buffer
        self.buffer_index = 0
        self.feedback_buffer = np.zeros(2)  # For stereo feedback

    def _initialize_xg_variation_parameters(self):
        """Initialize XG-specific variation effect parameters."""
        self.parameters["var_type"] = EffectParameter(
            name="var_type",
            min_value=0,
            max_value=63,  # XG defines 64 variation types
            default_value=self.xg_effect_type.value,
            resolution=ParameterResolution.MIDI_2_32_BIT,
            unit="enum",
            description="XG variation effect type",
        )

        self.parameters["character1"] = EffectParameter(
            name="character1",
            min_value=0,
            max_value=127,
            default_value=64,  # Center/default
            resolution=ParameterResolution.MIDI_2_32_BIT,
            unit="",
            description="Variation character parameter 1",
        )

        self.parameters["character2"] = EffectParameter(
            name="character2",
            min_value=0,
            max_value=127,
            default_value=64,  # Center/default
            resolution=ParameterResolution.MIDI_2_32_BIT,
            unit="",
            description="Variation character parameter 2",
        )

        self.parameters["rate"] = EffectParameter(
            name="rate",
            min_value=0.01,
            max_value=10.0,
            default_value=1.0,
            resolution=ParameterResolution.MIDI_2_32_BIT,
            unit="Hz",
            description="LFO rate",
        )

        self.parameters["depth"] = EffectParameter(
            name="depth",
            min_value=0.0,
            max_value=0.1,  # 100ms max
            default_value=0.005,  # 5ms default
            resolution=ParameterResolution.MIDI_2_32_BIT,
            unit="s",
            description="Modulation depth",
        )

        self.parameters["feedback"] = EffectParameter(
            name="feedback",
            min_value=-0.99,
            max_value=0.99,
            default_value=0.0,
            resolution=ParameterResolution.MIDI_2_32_BIT,
            unit="",
            description="Feedback amount",
        )

        self.parameters["level"] = EffectParameter(
            name="level",
            min_value=0.0,
            max_value=1.0,
            default_value=0.5,
            resolution=ParameterResolution.MIDI_2_32_BIT,
            unit="",
            description="Effect output level",
        )

        self.parameters["send_level"] = EffectParameter(
            name="send_level",
            min_value=0.0,
            max_value=1.0,
            default_value=0.0,  # No send by default
            resolution=ParameterResolution.MIDI_2_32_BIT,
            unit="",
            description="Variation send level",
        )

    def _apply_effect(self, audio_input: np.ndarray, note: int | None = None) -> np.ndarray:
        """Apply XG variation effect processing."""
        if audio_input.ndim == 1:
            # Convert mono to stereo
            audio_input = np.column_stack([audio_input, audio_input])

        output = np.zeros_like(audio_input, dtype=np.float32)
        input_len = len(audio_input)

        # Get XG-specific parameters (potentially per-note)
        var_type = self.get_parameter("var_type", note)
        char1 = self.get_parameter("character1", note)
        char2 = self.get_parameter("character2", note)
        rate = self.get_parameter("rate", note)
        depth = self.get_parameter("depth", note)
        feedback = self.get_parameter("feedback", note)
        level = self.get_parameter("level", note)
        send_level = self.get_parameter("send_level", note)

        # Calculate modulation parameters based on effect type
        lfo_inc = 2.0 * math.pi * rate / self.sample_rate

        for i in range(input_len):
            # Update LFO phase
            self.lfo_phase += lfo_inc
            if self.lfo_phase > 2.0 * math.pi:
                self.lfo_phase -= 2.0 * math.pi

            # Calculate modulation based on effect type
            if var_type in [
                XGEffectType.VARIATION_MULTI_CHORUS,
                XGEffectType.VARIATION_STEREO_CHORUS,
            ]:
                # Chorus-like modulation
                modulation = math.sin(self.lfo_phase) * depth * self.sample_rate
            elif var_type in [
                XGEffectType.VARIATION_TREMOLO,
                XGEffectType.VARIATION_STEREO_TREMOLO,
            ]:
                # Tremolo-like modulation (amplitude)
                modulation = 0  # Tremolo affects amplitude, not delay
                tremolo_depth = math.sin(self.lfo_phase) * (char1 / 127.0)
            elif var_type in [XGEffectType.VARIATION_PHASER, XGEffectType.VARIATION_STEREO_PHASER]:
                # Phaser-like modulation (for simplicity, treat as delay modulation)
                modulation = math.sin(self.lfo_phase) * depth * self.sample_rate * (char1 / 127.0)
            elif var_type in [
                XGEffectType.VARIATION_FLANGER,
                XGEffectType.VARIATION_STEREO_FLANGER,
            ]:
                # Flanger-like modulation (short delay)
                modulation = (
                    math.sin(self.lfo_phase) * depth * self.sample_rate * 0.2
                )  # Shorter delays for flanger
            elif var_type == XGEffectType.VARIATION_AUTO_PANNER:
                # Auto-panner (affects stereo positioning)
                modulation = 0  # Handled separately
            else:
                # Default modulation for other effects
                modulation = math.sin(self.lfo_phase) * depth * self.sample_rate * (char2 / 127.0)

            # Calculate delay with modulation
            mod_delay = int(abs(modulation))
            mod_frac = abs(modulation) - mod_delay

            # Calculate delay line indices with interpolation
            read_idx1 = (self.buffer_index - mod_delay) % len(self.delay_buffer)
            read_idx2 = (self.buffer_index - mod_delay - 1) % len(self.delay_buffer)

            # Get delayed signal with linear interpolation
            delayed_l = (
                self.delay_buffer[read_idx1] * (1.0 - mod_frac)
                + self.delay_buffer[read_idx2] * mod_frac
            )

            # Average input for mono processing
            input_mono = (audio_input[i, 0] + audio_input[i, 1]) * 0.5

            # Apply feedback
            delayed_with_feedback = delayed_l + input_mono * feedback

            # Update delay buffer
            self.delay_buffer[self.buffer_index] = input_mono
            self.buffer_index = (self.buffer_index + 1) % len(self.delay_buffer)

            # Handle auto-panner separately
            if var_type == XGEffectType.VARIATION_AUTO_PANNER:
                # Calculate pan position based on LFO
                pan_pos = math.sin(self.lfo_phase)  # -1 to 1
                left_gain = math.sqrt(0.5 * (1 - pan_pos))  # Constant power panning
                right_gain = math.sqrt(0.5 * (1 + pan_pos))

                output[i, 0] = (
                    audio_input[i, 0] * (1.0 - send_level)
                    + delayed_with_feedback * send_level * left_gain
                )
                output[i, 1] = (
                    audio_input[i, 1] * (1.0 - send_level)
                    + delayed_with_feedback * send_level * right_gain
                )
            else:
                # Apply standard variation effect
                output[i, 0] = (
                    audio_input[i, 0] * (1.0 - send_level) + delayed_with_feedback * send_level
                )
                output[i, 1] = (
                    audio_input[i, 1] * (1.0 - send_level) + delayed_with_feedback * send_level
                )

        return output


class XGInsertionEffect(EffectProcessor):
    """XG Insertion Effect with MIDI 2.0 support"""

    def __init__(
        self, sample_rate: int = 48000, ins_type: XGEffectType = XGEffectType.INSERT_DUAL_DELAY
    ):
        self.effect_type = EffectType.DELAY  # Many insertion effects are delay-based
        self.xg_effect_type = ins_type
        self.sample_rate = sample_rate
        self.enabled = True
        self.bypass = False

        # Effect parameters with XG-specific ranges and MIDI 2.0 support
        self.parameters: dict[str, EffectParameter] = {}
        self._initialize_xg_insertion_parameters()

        # Per-note parameter values (for MIDI 2.0 per-note control)
        self.per_note_parameters: dict[int, dict[str, float]] = {}

        # Internal effect state
        self.left_delay_buffer = np.zeros(int(2.0 * sample_rate))  # 2 sec max delay
        self.right_delay_buffer = np.zeros(int(2.0 * sample_rate))  # 2 sec max delay
        self.left_delay_index = 0
        self.right_delay_index = 0

    def _initialize_xg_insertion_parameters(self):
        """Initialize XG-specific insertion effect parameters."""
        self.parameters["ins_type"] = EffectParameter(
            name="ins_type",
            min_value=0,
            max_value=127,
            default_value=self.xg_effect_type.value,
            resolution=ParameterResolution.MIDI_2_32_BIT,
            unit="enum",
            description="XG insertion effect type",
        )

        self.parameters["return_level"] = EffectParameter(
            name="return_level",
            min_value=0.0,
            max_value=1.0,
            default_value=0.5,
            resolution=ParameterResolution.MIDI_2_32_BIT,
            unit="",
            description="Effect return level",
        )

        self.parameters["effect_level"] = EffectParameter(
            name="effect_level",
            min_value=0.0,
            max_value=1.0,
            default_value=0.5,
            resolution=ParameterResolution.MIDI_2_32_BIT,
            unit="",
            description="Effect level",
        )

        self.parameters["param1"] = EffectParameter(
            name="param1",
            min_value=0,
            max_value=127,
            default_value=64,
            resolution=ParameterResolution.MIDI_2_32_BIT,
            unit="",
            description="Effect parameter 1",
        )

        self.parameters["param2"] = EffectParameter(
            name="param2",
            min_value=0,
            max_value=127,
            default_value=64,
            resolution=ParameterResolution.MIDI_2_32_BIT,
            unit="",
            description="Effect parameter 2",
        )

        self.parameters["param3"] = EffectParameter(
            name="param3",
            min_value=0,
            max_value=127,
            default_value=64,
            resolution=ParameterResolution.MIDI_2_32_BIT,
            unit="",
            description="Effect parameter 3",
        )

        self.parameters["param4"] = EffectParameter(
            name="param4",
            min_value=0,
            max_value=127,
            default_value=64,
            resolution=ParameterResolution.MIDI_2_32_BIT,
            unit="",
            description="Effect parameter 4",
        )

    def _apply_effect(self, audio_input: np.ndarray, note: int | None = None) -> np.ndarray:
        """Apply XG insertion effect processing."""
        if audio_input.ndim == 1:
            # Convert mono to stereo
            audio_input = np.column_stack([audio_input, audio_input])

        output = np.zeros_like(audio_input, dtype=np.float32)
        input_len = len(audio_input)

        # Get XG-specific parameters (potentially per-note)
        ins_type = self.get_parameter("ins_type", note)
        return_level = self.get_parameter("return_level", note)
        effect_level = self.get_parameter("effect_level", note)
        param1 = self.get_parameter("param1", note)
        param2 = self.get_parameter("param2", note)
        param3 = self.get_parameter("param3", note)
        param4 = self.get_parameter("param4", note)

        # Process based on insertion effect type
        if ins_type in [XGEffectType.INSERT_DUAL_DELAY, XGEffectType.INSERT_STEREO_DELAY]:
            # Dual/Stereo delay effect
            left_delay_time = (param1 / 127.0) * 2.0  # Up to 2 seconds
            right_delay_time = (param2 / 127.0) * 2.0  # Up to 2 seconds
            feedback = (param3 / 127.0) * 0.9  # Up to 0.9 feedback
            cross_feedback = (param4 / 127.0) * 0.5  # Cross feedback

            left_delay_samples = int(left_delay_time * self.sample_rate)
            right_delay_samples = int(right_delay_time * self.sample_rate)

            for i in range(input_len):
                # Read from delay buffers
                left_delay_read_idx = (self.left_delay_index - left_delay_samples) % len(
                    self.left_delay_buffer
                )
                right_delay_read_idx = (self.right_delay_index - right_delay_samples) % len(
                    self.right_delay_buffer
                )

                left_delayed = self.left_delay_buffer[left_delay_read_idx]
                right_delayed = self.right_delay_buffer[right_delay_read_idx]

                # Apply feedback and cross-feedback
                left_in = (
                    audio_input[i, 0] + left_delayed * feedback + right_delayed * cross_feedback
                )
                right_in = (
                    audio_input[i, 1] + right_delayed * feedback + left_delayed * cross_feedback
                )

                # Write to delay buffers
                self.left_delay_buffer[self.left_delay_index] = left_in
                self.right_delay_buffer[self.right_delay_index] = right_in

                # Update indices
                self.left_delay_index = (self.left_delay_index + 1) % len(self.left_delay_buffer)
                self.right_delay_index = (self.right_delay_index + 1) % len(self.right_delay_buffer)

                # Mix dry and wet signals
                output[i, 0] = (
                    audio_input[i, 0] * (1.0 - effect_level)
                    + left_delayed * effect_level * return_level
                )
                output[i, 1] = (
                    audio_input[i, 1] * (1.0 - effect_level)
                    + right_delayed * effect_level * return_level
                )

        elif ins_type in [XGEffectType.INSERT_STEREO_CHORUS, XGEffectType.INSERT_MONO_CHORUS]:
            # Chorus effect
            rate = 0.1 + (param1 / 127.0) * 9.9  # 0.1 to 10 Hz
            depth = (param2 / 127.0) * 0.05  # Up to 50ms
            feedback = (param3 / 127.0) * 0.9
            lfo_phase_offset = (param4 / 127.0) * math.pi  # Phase offset for stereo chorus

            lfo_inc = 2.0 * math.pi * rate / self.sample_rate

            for i in range(input_len):
                # Update LFO phases
                lfo_phase_l = self.lfo_phase
                lfo_phase_r = self.lfo_phase + lfo_phase_offset

                # Calculate modulation for left and right
                left_mod = math.sin(lfo_phase_l) * depth * self.sample_rate
                right_mod = math.sin(lfo_phase_r) * depth * self.sample_rate

                # Calculate delay indices
                left_delay_idx = int(self.left_delay_index - abs(left_mod)) % len(
                    self.left_delay_buffer
                )
                right_delay_idx = int(self.right_delay_index - abs(right_mod)) % len(
                    self.right_delay_buffer
                )

                # Get delayed signals
                left_delayed = self.left_delay_buffer[left_delay_idx]
                right_delayed = self.right_delay_buffer[right_delay_idx]

                # Apply feedback
                left_in = audio_input[i, 0] + left_delayed * feedback
                right_in = audio_input[i, 1] + right_delayed * feedback

                # Write to delay buffers
                self.left_delay_buffer[self.left_delay_index] = left_in
                self.right_delay_buffer[self.right_delay_index] = right_in

                # Update indices and phase
                self.left_delay_index = (self.left_delay_index + 1) % len(self.left_delay_buffer)
                self.right_delay_index = (self.right_delay_index + 1) % len(self.right_delay_buffer)
                self.lfo_phase += lfo_inc
                if self.lfo_phase > 2.0 * math.pi:
                    self.lfo_phase -= 2.0 * math.pi

                # Mix output
                output[i, 0] = (
                    audio_input[i, 0] * (1.0 - effect_level)
                    + left_delayed * effect_level * return_level
                )
                output[i, 1] = (
                    audio_input[i, 1] * (1.0 - effect_level)
                    + right_delayed * effect_level * return_level
                )

        else:
            # For other effect types, just apply basic processing
            for i in range(input_len):
                output[i, 0] = (
                    audio_input[i, 0] * (1.0 - effect_level)
                    + audio_input[i, 0] * effect_level * return_level
                )
                output[i, 1] = (
                    audio_input[i, 1] * (1.0 - effect_level)
                    + audio_input[i, 1] * effect_level * return_level
                )

        return output


class XGMIDIEffectsProcessor:
    """
    XG MIDI Effects Processor with Full MIDI 2.0 Integration

    Manages XG system, variation, and insertion effects with 32-bit parameter
    resolution and per-note control capabilities.
    """

    def __init__(self, sample_rate: int = 48000):
        """
        Initialize XG MIDI effects processor.

        Args:
            sample_rate: Audio sample rate in Hz
        """
        self.sample_rate = sample_rate
        self.enabled = True

        # XG effect slots
        self.system_reverb: XGSystemReverb | None = None
        self.system_chorus: EffectProcessor | None = None
        self.variation_effect: XGVariationEffect | None = None
        self.insertion_effects: list[XGInsertionEffect] = []

        # Initialize default XG effects
        self._initialize_xg_effects()

    def _initialize_xg_effects(self):
        """Initialize default XG effects."""
        self.system_reverb = XGSystemReverb(self.sample_rate, XGEffectType.REVERB_HALL)
        self.variation_effect = XGVariationEffect(
            self.sample_rate, XGEffectType.VARIATION_MULTI_CHORUS
        )

        # Add default insertion effect
        default_insertion = XGInsertionEffect(self.sample_rate, XGEffectType.INSERT_DUAL_DELAY)
        self.insertion_effects.append(default_insertion)

    def set_system_reverb_type(self, reverb_type: XGEffectType):
        """Set system reverb type."""
        if self.system_reverb:
            self.system_reverb.xg_effect_type = reverb_type
            # Reinitialize parameters for the new type
            self.system_reverb._initialize_xg_parameters()

    def set_variation_type(self, var_type: XGEffectType):
        """Set variation effect type."""
        if self.variation_effect:
            self.variation_effect.xg_effect_type = var_type
            # Reinitialize parameters for the new type
            self.variation_effect._initialize_xg_variation_parameters()

    def add_insertion_effect(self, effect_type: XGEffectType) -> int:
        """
        Add an insertion effect.

        Args:
            effect_type: Type of insertion effect to add

        Returns:
            Index of the added effect
        """
        effect = XGInsertionEffect(self.sample_rate, effect_type)
        self.insertion_effects.append(effect)
        return len(self.insertion_effects) - 1

    def remove_insertion_effect(self, index: int) -> bool:
        """
        Remove an insertion effect.

        Args:
            index: Index of effect to remove

        Returns:
            True if removed successfully
        """
        if 0 <= index < len(self.insertion_effects):
            del self.insertion_effects[index]
            return True
        return False

    def process_audio_with_xg_effects(
        self, audio_input: np.ndarray, part: int = 0, note: int | None = None
    ) -> np.ndarray:
        """
        Process audio through XG effects chain.

        Args:
            audio_input: Input audio as numpy array
            part: Part number for part-specific processing
            note: Note number for per-note processing

        Returns:
            Processed audio as numpy array
        """
        if not self.enabled:
            return audio_input

        # Start with input audio
        processed_audio = audio_input.copy()

        # Apply insertion effects first (they're part-specific)
        for insertion_effect in self.insertion_effects:
            if insertion_effect.enabled and not insertion_effect.bypass:
                processed_audio = insertion_effect.process_audio(processed_audio, note)

        # Apply system effects
        if self.system_reverb and self.system_reverb.enabled and not self.system_reverb.bypass:
            processed_audio = self.system_reverb.process_audio(processed_audio, note)

        # Apply variation effect
        if (
            self.variation_effect
            and self.variation_effect.enabled
            and not self.variation_effect.bypass
        ):
            processed_audio = self.variation_effect.process_audio(processed_audio, note)

        return processed_audio

    def set_xg_parameter(
        self,
        effect_slot: str,
        param_name: str,
        value: float,
        resolution: ParameterResolution = ParameterResolution.MIDI_2_32_BIT,
    ):
        """
        Set an XG parameter with specified resolution.

        Args:
            effect_slot: 'system_reverb', 'system_chorus', 'variation', or 'insertion_N' where N is index
            param_name: Parameter name
            value: Parameter value
            resolution: Parameter resolution
        """
        if effect_slot.startswith("insertion_"):
            # Parse insertion effect index
            try:
                idx = int(effect_slot.split("_")[1])
                if 0 <= idx < len(self.insertion_effects):
                    effect = self.insertion_effects[idx]
                    effect.set_parameter(param_name, value, resolution)
            except (ValueError, IndexError):
                pass
        elif effect_slot == "system_reverb" and self.system_reverb:
            self.system_reverb.set_parameter(param_name, value, resolution)
        elif effect_slot == "variation" and self.variation_effect:
            self.variation_effect.set_parameter(param_name, value, resolution)

    def set_per_note_xg_parameter(
        self,
        note: int,
        effect_slot: str,
        param_name: str,
        value: float,
        resolution: ParameterResolution = ParameterResolution.MIDI_2_32_BIT,
    ):
        """
        Set a per-note XG parameter.

        Args:
            note: MIDI note number
            effect_slot: Effect slot identifier
            param_name: Parameter name
            value: Parameter value
            resolution: Parameter resolution
        """
        if effect_slot.startswith("insertion_"):
            # Parse insertion effect index
            try:
                idx = int(effect_slot.split("_")[1])
                if 0 <= idx < len(self.insertion_effects):
                    effect = self.insertion_effects[idx]
                    effect.set_per_note_parameter(note, param_name, value, resolution)
            except (ValueError, IndexError):
                pass
        elif effect_slot == "system_reverb" and self.system_reverb:
            self.system_reverb.set_per_note_parameter(note, param_name, value, resolution)
        elif effect_slot == "variation" and self.variation_effect:
            self.variation_effect.set_per_note_parameter(note, param_name, value, resolution)


# Global instance for XG effects
xg_midi_effects_processor = XGMIDIEffectsProcessor()


def get_xg_midi_effects_processor() -> XGMIDIEffectsProcessor:
    """
    Get the global XG MIDI effects processor instance.

    Returns:
        XGMIDIEffectsProcessor instance
    """
    return xg_midi_effects_processor
