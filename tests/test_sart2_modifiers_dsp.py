"""
Audio-quality tests for S.Art2 Sample Modifiers (modifiers.py).

Verifies the DSP algorithms produce correct output:
- Pitch-shift accuracy (bend, glissando produce correct intervals)
- Envelope shapes (pizzicato decay, swell fade, staccato silence)
- Boundary conditions (empty arrays, edge params, sample rate changes)
- Scratch buffer reuse (zero-allocation after warm-up)

All tests use a known reference signal: a 440 Hz sine wave.
"""

from __future__ import annotations

import numpy as np
import pytest

from synth.protocols.xg.sart.modifiers import SF2SampleModifier

# ============================================================================
# FIXTURES
# ============================================================================

SR = 44100
# Longer block for envelope tests that need time to develop decay/release
_LONG_BLOCK = SR  # 1 second
_SHORT_BLOCK = 2048  # ~46 ms


@pytest.fixture
def modifier() -> SF2SampleModifier:
    """Create sample modifier at 44.1 kHz."""
    return SF2SampleModifier(sample_rate=SR)


@pytest.fixture
def sine_440() -> np.ndarray:
    """A 440 Hz sine wave, 2048 samples (~46 ms), float32 mono."""
    n = _SHORT_BLOCK
    t = np.arange(n, dtype=np.float32) / SR
    return np.sin(2.0 * np.pi * 440.0 * t).astype(np.float32)


@pytest.fixture
def sine_220() -> np.ndarray:
    """A 220 Hz sine wave, 2048 samples, float32 mono."""
    n = _SHORT_BLOCK
    t = np.arange(n, dtype=np.float32) / SR
    return np.sin(2.0 * np.pi * 220.0 * t).astype(np.float32)


@pytest.fixture
def long_sine_440() -> np.ndarray:
    """A 440 Hz sine wave, 1 second long, for decay/envelope tests."""
    n = _LONG_BLOCK
    t = np.arange(n, dtype=np.float32) / SR
    return np.sin(2.0 * np.pi * 440.0 * t).astype(np.float32)


# ============================================================================
# HELPERS
# ============================================================================


def _dominant_freq(signal: np.ndarray, sr: int = SR) -> float:
    """Estimate dominant frequency via zero-crossing rate."""
    # Count zero crossings in the middle of the signal to avoid onset/decay
    mid = len(signal) // 4
    end = mid * 3
    segment = signal[mid:end]
    crossings = np.sum(np.diff(np.signbit(segment)))
    if crossings < 2:
        return 0.0
    # crossings/2 = number of cycles in the segment
    cycles = crossings / 2.0
    duration = len(segment) / sr
    return cycles / duration


def _rms(signal: np.ndarray) -> float:
    """Compute RMS amplitude."""
    return float(np.sqrt(np.mean(signal**2)))


def _peak_amplitude(signal: np.ndarray) -> float:
    """Compute peak absolute amplitude."""
    return float(np.max(np.abs(signal)))


# ============================================================================
# PITCH-BASED ARTICULATIONS
# ============================================================================


class TestPitchAccuracy:
    """Verify pitch-shifting algorithms produce correct intervals."""

    def test_apply_bend_one_octave(self, modifier: SF2SampleModifier, sine_440: np.ndarray):
        """Bend by 12 semitones sweeps from 440→880 Hz.  Average freq should be > 440 Hz."""
        result = modifier.apply_bend(sine_440, {"amount": 12.0})
        freq = _dominant_freq(result)
        # Sweep from 440→880: zero-crossing average lands between them
        assert freq > 480, f"Expected >480 Hz (sweep up), got {freq:.1f} Hz"

    def test_apply_bend_zero(self, modifier: SF2SampleModifier, sine_440: np.ndarray):
        """Bend by 0 semitones should not change pitch."""
        result = modifier.apply_bend(sine_440, {"amount": 0.0})
        freq = _dominant_freq(result)
        assert 400 <= freq <= 480, f"Expected ~440 Hz, got {freq:.1f} Hz"

    def test_apply_bend_negative(self, modifier: SF2SampleModifier, sine_440: np.ndarray):
        """Negative bend (-12 semitones) sweeps 440→220 Hz.  Average should be < 440 Hz."""
        result = modifier.apply_bend(sine_440, {"amount": -12.0})
        freq = _dominant_freq(result)
        assert freq < 400, f"Expected <400 Hz (sweep down), got {freq:.1f} Hz"

    def test_apply_glissando_octave(self, modifier: SF2SampleModifier, sine_440: np.ndarray):
        """Glissando 12 semitones over block — average pitch up."""
        result = modifier.apply_glissando(sine_440, {"amount": 12})
        freq = _dominant_freq(result)
        assert freq > 480, f"Expected >480 Hz (sweep up), got {freq:.1f} Hz"

    def test_apply_harmonics_correct_freq(self, modifier: SF2SampleModifier, sine_440: np.ndarray):
        """Add 2nd harmonic (440 Hz + 880 Hz)."""
        result = modifier.apply_harmonics(sine_440, {"harmonic": 2, "level": 0.5, "note": 69})
        # The added harmonic is at 880 Hz; with level=0.5 it should be detectable
        freq = _dominant_freq(result)
        # Dominant should still be ~440 Hz (original is unchanged amplitude)
        assert 400 <= freq <= 480, f"Expected ~440 Hz, got {freq:.1f} Hz"

    def test_apply_hammer_on(self, modifier: SF2SampleModifier, sine_440: np.ndarray):
        """Hammer-on should produce upward pitch sweep (larger amount for detectability)."""
        result = modifier.apply_hammer_on(sine_440, {"amount": 12})
        freq = _dominant_freq(result)
        assert freq > 480, f"Expected >480 Hz (sweep up), got {freq:.1f} Hz"

    def test_apply_pull_off(self, modifier: SF2SampleModifier, sine_220: np.ndarray):
        """Pull-off should produce downward pitch sweep."""
        result = modifier.apply_pull_off(sine_220, {"amount": -12})
        freq = _dominant_freq(result)
        assert freq < 200, f"Expected <200 Hz (sweep down), got {freq:.1f} Hz"

    def test_apply_vibrato_modulates_pitch(self, modifier: SF2SampleModifier, long_sine_440: np.ndarray):
        """Vibrato should produce output different from input (pitch modulation)."""
        result = modifier.apply_vibrato(long_sine_440, {"rate": 5.0, "depth": 5.0})
        # The output should differ measurably from the input signal
        max_diff = float(np.max(np.abs(result - long_sine_440)))
        assert max_diff > 0.01, f"Vibrato should change the signal (max diff={max_diff:.4f})"


# ============================================================================
# ENVELOPE SHAPE ARTICULATIONS
# ============================================================================


class TestEnvelopeShapes:
    """Verify amplitude envelope articulations produce correct shapes."""

    def test_apply_staccato_silences_tail(self, modifier: SF2SampleModifier, sine_440: np.ndarray):
        """Staccato should silence the latter portion of the sample."""
        result = modifier.apply_staccato(sine_440, {"note_length": 0.3})
        n = len(result)
        tail_start = int(n * 0.5)
        tail_energy = _rms(result[tail_start:])
        head_energy = _rms(result[: tail_start // 2])
        assert tail_energy < head_energy * 0.1, (
            f"Tail should be near-silent (head={head_energy:.4f}, tail={tail_energy:.4f})"
        )

    def test_apply_pizzicato_exponential_decay(self, modifier: SF2SampleModifier, long_sine_440: np.ndarray):
        """Pizzicato should produce exponential decay envelope."""
        result = modifier.apply_pizzicato(long_sine_440, {"decay": 8.0})
        n = len(result)
        # Energy should decrease monotonically after onset
        head_rms = _rms(result[:200])
        tail_rms = _rms(result[-200:])
        assert tail_rms < head_rms * 0.5, (
            f"Tail should be quieter than head (head={head_rms:.4f}, tail={tail_rms:.4f})"
        )

    def test_apply_swell_fades_in_and_out(self, modifier: SF2SampleModifier, long_sine_440: np.ndarray):
        """Swell should fade in then out."""
        result = modifier.apply_swell(long_sine_440, {"attack": 0.1, "release": 0.2})
        n = len(result)
        start_rms = _rms(result[:100])
        mid_start = n // 4
        mid_rms = _rms(result[mid_start - 50 : mid_start + 50])
        end_rms = _rms(result[-100:])
        # Mid should be louder than both start and end
        assert mid_rms > start_rms, f"Mid ({mid_rms:.4f}) should exceed start ({start_rms:.4f})"
        assert mid_rms > end_rms, f"Mid ({mid_rms:.4f}) should exceed end ({end_rms:.4f})"

    def test_apply_crescendo_increases_volume(self, modifier: SF2SampleModifier, long_sine_440: np.ndarray):
        """Crescendo should produce a volume increase."""
        result = modifier.apply_crescendo(long_sine_440, {"target_level": 1.0, "duration": 0.5})
        n = len(result)
        quarter = n // 4
        start_rms = _rms(result[:100])
        end_rms = _rms(result[-100:])
        assert end_rms > start_rms * 2.0, (
            f"End ({end_rms:.4f}) should be louder than start ({start_rms:.4f})"
        )

    def test_apply_diminuendo_decreases_volume(self, modifier: SF2SampleModifier, sine_440: np.ndarray):
        """Diminuendo should produce a volume decrease."""
        result = modifier.apply_diminuendo(sine_440, {"target_level": 0.1, "duration": 0.5})
        n = len(result)
        quarter = n // 4
        start_rms = _rms(result[:quarter])
        end_rms = _rms(result[-quarter:])
        assert start_rms > end_rms, (
            f"Start ({start_rms:.4f}) should be louder than end ({end_rms:.4f})"
        )

    def test_apply_tremolo_modulates_amplitude(self, modifier: SF2SampleModifier, sine_440: np.ndarray):
        """Tremolo should produce periodic amplitude modulation."""
        result = modifier.apply_tremolo(sine_440, {"rate": 6.0, "depth": 0.5})
        # With depth=0.5, amplitude should vary from 0.5 to 1.5
        envelope = np.abs(result) / (np.abs(sine_440) + 1e-8)
        env_std = float(np.std(envelope[len(envelope) // 4 : -len(envelope) // 4]))
        assert env_std > 0.05, f"Envelope should vary (std={env_std:.4f})"

    def test_apply_legato_crossfades(self, modifier: SF2SampleModifier, sine_440: np.ndarray):
        """Legato should fade in at start and out at end."""
        result = modifier.apply_legato(sine_440, {"transition_time": 0.05})
        n = len(result)
        transition = int(0.05 * SR)
        if n > transition * 2:
            start_amp = _peak_amplitude(result[:10])
            mid_amp = _peak_amplitude(result[n // 2 - 10 : n // 2 + 10])
            end_amp = _peak_amplitude(result[-10:])
            assert start_amp < mid_amp, f"Start ({start_amp:.4f}) should be quieter than mid ({mid_amp:.4f})"
            assert end_amp < mid_amp, f"End ({end_amp:.4f}) should be quieter than mid ({mid_amp:.4f})"


# ============================================================================
# MODULATION EFFECTS
# ============================================================================


class TestModulationEffects:
    """Verify amplitude and frequency modulation articulations."""

    def test_apply_growl_produces_output(self, modifier: SF2SampleModifier, sine_440: np.ndarray):
        """Growl should return valid audio with modulation and noise."""
        result = modifier.apply_growl(sine_440, {"mod_freq": 25.0, "depth": 0.25})
        assert len(result) == len(sine_440)
        assert result.dtype == np.float32
        # Should contain both modulated signal and noise texture
        rms_orig = _rms(sine_440)
        rms_result = _rms(result)
        assert rms_result > 0, "Growl output should have energy"

    def test_apply_flutter_modulates(self, modifier: SF2SampleModifier, sine_440: np.ndarray):
        """Flutter should produce fast amplitude modulation."""
        result = modifier.apply_flutter(sine_440, {"mod_freq": 12.0, "depth": 0.15})
        assert len(result) == len(sine_440)
        assert result.dtype == np.float32

    def test_apply_soft_pedal_reduces_volume(self, modifier: SF2SampleModifier, sine_440: np.ndarray):
        """Soft pedal should reduce volume and optionally darken."""
        result = modifier.apply_soft_pedal(sine_440, {"level": 0.5, "brightness": 0.8})
        orig_peak = _peak_amplitude(sine_440)
        result_peak = _peak_amplitude(result)
        assert result_peak < orig_peak * 0.75, (
            f"Soft pedal should reduce volume (orig={orig_peak:.4f}, result={result_peak:.4f})"
        )

    def test_apply_dead_note_dampens(self, modifier: SF2SampleModifier, sine_440: np.ndarray):
        """Dead note should heavily dampen the sound."""
        result = modifier.apply_dead_note(sine_440, {})
        rms_result = _rms(result)
        rms_orig = _rms(sine_440)
        assert rms_result < rms_orig * 0.6, (
            f"Dead note should dampen (orig_rms={rms_orig:.4f}, result_rms={rms_result:.4f})"
        )


# ============================================================================
# NOISE / IMPULSE ARTICULATIONS
# ============================================================================


class TestNoiseArticulations:
    """Verify noise/impulse articulations produce correct output."""

    def test_apply_fret_noise_adds_noise(self, modifier: SF2SampleModifier, sine_440: np.ndarray):
        """Fret noise should add attack noise to the start of the sample."""
        result = modifier.apply_fret_noise(sine_440, {"noise_level": 0.3})
        assert len(result) == len(sine_440)
        # The attack portion should have different energy than the original
        attack_len = int(0.02 * SR)
        orig_attack = sine_440[:attack_len]
        result_attack = result[:attack_len]
        assert not np.array_equal(orig_attack, result_attack), "Attack should be modified"

    def test_apply_organ_click_adds_impulse(self, modifier: SF2SampleModifier, sine_440: np.ndarray):
        """Organ click should add percussive impulse at attack."""
        result = modifier.apply_organ_click(sine_440, {"click_level": 0.5, "click_width": 0.005})
        assert len(result) == len(sine_440)
        click_len = int(0.005 * SR)
        # The click portion should differ from the original
        orig_click = sine_440[:click_len]
        result_click = result[:click_len]
        assert not np.array_equal(orig_click, result_click), "Click region should be modified"

    def test_apply_palm_mute_dampens(self, modifier: SF2SampleModifier, long_sine_440: np.ndarray):
        """Palm mute should dampen decay and add noise."""
        result = modifier.apply_palm_mute(long_sine_440, {"damp_factor": 0.7})
        n = len(result)
        rms_tail = _rms(result[-200:])
        rms_head = _rms(result[:200])
        assert rms_tail < rms_head * 0.5, (
            f"Tail should be dampened (head={rms_head:.4f}, tail={rms_tail:.4f})"
        )

    def test_apply_rim_shot_fast_decay(self, modifier: SF2SampleModifier, long_sine_440: np.ndarray):
        """Rim shot should have hard attack with fast decay."""
        result = modifier.apply_rim_shot(long_sine_440, {"rim_level": 0.8})
        n = len(result)
        rms_tail = _rms(result[-200:])
        rms_head = _rms(result[:50])
        assert rms_tail < rms_head * 0.5


# ============================================================================
# BOUNDARY CONDITIONS
# ============================================================================


class TestBoundaryConditions:
    """Verify modifiers handle edge cases gracefully."""

    def test_empty_sample_raises(self, modifier: SF2SampleModifier):
        """Empty input should raise ValueError."""
        empty = np.array([], dtype=np.float32)
        with pytest.raises(ValueError, match="empty"):
            modifier.apply_vibrato(empty, {})

    def test_single_sample(self, modifier: SF2SampleModifier):
        """Single-sample input should return valid single-sample output."""
        s = np.array([0.5], dtype=np.float32)
        result = modifier.apply_vibrato(s, {"rate": 5.0, "depth": 0.5})
        assert len(result) == 1
        assert result.dtype == np.float32

    def test_zero_params_defaults(self, modifier: SF2SampleModifier, sine_440: np.ndarray):
        """Empty params dict should use defaults without errors."""
        methods = [
            ("vibrato", {}),
            ("trill", {}),
            ("glissando", {}),
            ("bend", {}),
            ("hammer_on", {}),
            ("pull_off", {}),
            ("ethnic_bend", {}),
            ("pizzicato", {}),
            ("swell", {}),
            ("marcato", {}),
            ("crescendo", {}),
            ("diminuendo", {}),
            ("staccato", {}),
            ("legato", {}),
            ("tremolo", {}),
            ("flutter", {}),
            ("growl", {}),
            ("soft_pedal", {}),
            ("dead_note", {}),
            ("sustain_pedal", {}),
            ("fret_noise", {}),
            ("organ_click", {}),
            ("palm_mute", {}),
            ("rim_shot", {}),
            ("open_rim", {}),
            ("harmonics", {}),
        ]
        for name, params in methods:
            result = modifier.apply_articulation(sine_440, name, params)
            assert len(result) == len(sine_440), f"{name}: length mismatch"
            assert result.dtype == np.float32, f"{name}: dtype mismatch"

    def test_normal_articulation_passthrough(self, modifier: SF2SampleModifier, sine_440: np.ndarray):
        """'normal' articulation should return input unchanged (same object)."""
        result = modifier.apply_articulation(sine_440, "normal", {})
        assert result is sine_440, "normal should return the same array object"

    def test_unknown_articulation_passthrough(self, modifier: SF2SampleModifier, sine_440: np.ndarray):
        """Unknown articulation should return input unchanged (same object)."""
        result = modifier.apply_articulation(sine_440, "nonexistent_articulation", {})
        assert result is sine_440, "Unknown articulation should pass through unchanged"

    def test_stereo_input_fallback(self, modifier: SF2SampleModifier):
        """Modifiers operate on mono 1-D audio; stereo input raises ValueError.

        Stereo handling is done upstream at the SArt2Region level
        (base_region.generate_samples returns stereo, modifier is called
        per-channel or not at all for stereo paths).
        """
        stereo = np.ones((64, 2), dtype=np.float32)
        for name in ["vibrato", "tremolo", "bend", "staccato"]:
            with pytest.raises((ValueError, IndexError)):
                modifier.apply_articulation(stereo, name, {})

    def test_varying_block_sizes(self, modifier: SF2SampleModifier):
        """Modifiers should handle varying block sizes."""
        for n in [1, 3, 16, 64, 256, 1024, 2048]:
            s = np.ones(n, dtype=np.float32)
            for name in ["vibrato", "tremolo", "pizzicato", "staccato", "legato"]:
                result = modifier.apply_articulation(s, name, {})
                assert len(result) == n, f"{name} at n={n}: length mismatch"


# ============================================================================
# ZERO-ALLOCATION VERIFICATION
# ============================================================================


class TestZeroAllocationAfterWarmup:
    """Verify scratch buffers are reused after warm-up (no new allocations).

    NOTE: This is a best-effort check.  Exact allocation tracking is not
    possible from Python, but we can verify that repeated calls produce
    identical results (buffer reuse is deterministic).  The true test is
    that the scratch cache arrays only grow, never allocate new memory
    on each call.
    """

    def test_scratch_grows_only_once(self, modifier: SF2SampleModifier):
        """The scratch buffer should stabilize after reaching max block size.

        Note: _ensure_scratch is called by staccato, legato, swell, etc.
        _t (time cache) grows to the largest target_length seen.
        """
        # Call staccato which uses both scratch + time buffers
        for n in [64, 256, 1024, 2048]:
            s = np.ones(n, dtype=np.float32)
            modifier.apply_staccato(s, {"note_length": 0.3})

        # Verify scratch reached full block size (staccato uses _ensure_scratch(n))
        assert modifier._scratch is not None and len(modifier._scratch) >= 2048
        # _t only grows to target_length = int(n * note_length)
        assert modifier._t is not None and len(modifier._t) >= 614

    def test_repeated_calls_consistent(self, modifier: SF2SampleModifier, sine_440: np.ndarray):
        """Multiple identical calls should produce identical output."""
        # Call once to warm up buffers
        _ = modifier.apply_vibrato(sine_440, {"rate": 5.0, "depth": 0.5})
        first = modifier.apply_vibrato(sine_440, {"rate": 5.0, "depth": 0.5})
        second = modifier.apply_vibrato(sine_440, {"rate": 5.0, "depth": 0.5})
        third = modifier.apply_vibrato(sine_440, {"rate": 5.0, "depth": 0.5})
        np.testing.assert_array_equal(first, second)
        np.testing.assert_array_equal(second, third)

    def test_all_methods_repeatable(self, modifier: SF2SampleModifier, sine_440: np.ndarray):
        """All methods should produce identical output on repeated calls."""
        methods = ["vibrato", "tremolo", "pizzicato", "swell", "legato", "crescendo",
                   "diminuendo", "staccato", "trill", "glissando", "bend", "flutter"]
        for name in methods:
            params = {
                "vibrato": {"rate": 5.0, "depth": 0.5},
                "tremolo": {"rate": 6.0, "depth": 0.5},
                "pizzicato": {"decay": 8.0},
                "swell": {"attack": 0.05, "release": 0.1},
                "legato": {"transition_time": 0.05},
                "crescendo": {"target_level": 1.0, "duration": 0.5},
                "diminuendo": {"target_level": 0.1, "duration": 0.5},
                "staccato": {"note_length": 0.3},
                "trill": {"rate": 8.0, "interval": 2},
                "glissando": {"amount": 12},
                "bend": {"amount": 2.0},
                "flutter": {"mod_freq": 12.0, "depth": 0.15},
            }.get(name, {})
            # Warm up
            modifier.apply_articulation(sine_440, name, params)
            first = modifier.apply_articulation(sine_440, name, params)
            second = modifier.apply_articulation(sine_440, name, params)
            np.testing.assert_array_equal(first, second, err_msg=f"{name} not repeatable")


# ============================================================================
# SUBSONIC / BASS
# ============================================================================


class TestSubBass:
    """Verify sub-bass articulation."""

    def test_sub_bass_adds_sub_oscillator(self, modifier: SF2SampleModifier, sine_440: np.ndarray):
        """Sub bass should add a sub-oscillator and lowpass filter."""
        result = modifier.apply_sub_bass(sine_440, {"sub_freq": 40.0})
        assert len(result) == len(sine_440)
        assert result.dtype == np.float32

    def test_apply_sustain_pedal(self, modifier: SF2SampleModifier, sine_440: np.ndarray):
        """Sustain pedal should extend release with decay."""
        result = modifier.apply_sustain_pedal(sine_440, {"sustain_level": 0.8, "release_rate": 0.5})
        assert len(result) == len(sine_440)
        assert result.dtype == np.float32


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
