"""
SPECTRAL ANALYSIS TESTS FOR FILTER PRIMITIVES
Verifies actual filter behavior using numpy FFT and audio-domain measurements.
"""

from __future__ import annotations

import numpy as np
import pytest

from synth.primitives.filter import (
    BiquadFilter,
    FilterPool,
    UltraFastResonantFilter,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sine(freq_hz: float, num_samples: int, sample_rate: int = 48000) -> np.ndarray:
    """Return a float32 numpy array of a sine wave."""
    t = np.arange(num_samples, dtype=np.float64) / sample_rate
    return np.sin(2.0 * np.pi * freq_hz * t).astype(np.float32)


def _process_mono(f: UltraFastResonantFilter, signal: np.ndarray) -> np.ndarray:
    """Process a mono signal through the filter one sample at a time, return left channel."""
    out = np.empty_like(signal)
    for i in range(len(signal)):
        left, _ = f.process(float(signal[i]), is_stereo=False)
        out[i] = left
    return out


def _rms(x: np.ndarray) -> float:
    """RMS of a signal."""
    return float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))


def _warmup(f: UltraFastResonantFilter, n: int = 200) -> None:
    """Run a few samples through the filter so transients settle."""
    for _ in range(n):
        f.process(0.0, is_stereo=False)


# ---------------------------------------------------------------------------
# UltraFastResonantFilter — LPF Response
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUltraFastResonantFilterLPF:
    """Verify low-pass filter behaviour."""

    SAMPLE_RATE = 48000

    def test_lpf_passes_dc(self):
        """LPF at 500 Hz: DC (constant 1.0) converges to ≈1.0 after settling."""
        f = UltraFastResonantFilter(
            cutoff=500.0,
            resonance=0.707,
            filter_type="lowpass",
            sample_rate=self.SAMPLE_RATE,
        )
        # Feed DC directly (state starts at zero, filter converges)
        vals = np.empty(2000, dtype=np.float64)
        for i in range(2000):
            left, _ = f.process(1.0, is_stereo=False)
            vals[i] = left
        steady = np.mean(vals[1500:])  # last 500 after full settling
        assert steady == pytest.approx(1.0, abs=0.05), f"DC gain {steady:.4f} too far from 1.0"

    def test_lpf_attenuates_high_frequencies(self):
        """LPF at 500 Hz: 5 kHz sine should be ≥ 20 dB down."""
        f = UltraFastResonantFilter(
            cutoff=500.0,
            resonance=0.707,
            filter_type="lowpass",
            sample_rate=self.SAMPLE_RATE,
        )
        signal = _sine(5000.0, 2000, self.SAMPLE_RATE)
        inp_rms = _rms(signal)
        out = _process_mono(f, signal)
        out_rms = _rms(out[500:])  # skip transient
        attenuation_db = 20.0 * np.log10(out_rms / inp_rms)
        assert attenuation_db <= -20.0, (
            f"Attenuation only {attenuation_db:.1f} dB (expected ≤ -20 dB)"
        )

    def test_lpf_passes_low_frequencies(self):
        """LPF at 5 kHz: 100 Hz sine should pass with < 10 % amplitude error."""
        f = UltraFastResonantFilter(
            cutoff=5000.0,
            resonance=0.707,
            filter_type="lowpass",
            sample_rate=self.SAMPLE_RATE,
        )
        signal = _sine(100.0, 2000, self.SAMPLE_RATE)
        inp_rms = _rms(signal)
        out = _process_mono(f, signal)
        out_rms = _rms(out[500:])
        ratio = out_rms / inp_rms
        assert 0.90 <= ratio <= 1.10, f"Passband ratio {ratio:.4f} outside [0.90, 1.10]"

    def test_lpf_approximate_cutoff(self):
        """LPF at 1 kHz, Q=0.707: 1 kHz output is attenuated but not extremely."""
        f = UltraFastResonantFilter(
            cutoff=1000.0,
            resonance=0.707,
            filter_type="lowpass",
            sample_rate=self.SAMPLE_RATE,
        )
        signal = _sine(1000.0, 3000, self.SAMPLE_RATE)
        inp_rms = _rms(signal)
        out = _process_mono(f, signal)
        out_rms = _rms(out[1000:])  # skip transient
        ratio = out_rms / inp_rms
        assert 0.40 <= ratio <= 0.95, (
            f"Cutoff gain ratio {ratio:.4f} outside expected range (0.40, 0.95)"
        )

    def test_lpf_resonance_peak(self):
        """LPF at 500 Hz: higher resonance yields stronger response at cutoff."""
        def _gain_at(q: float) -> float:
            f = UltraFastResonantFilter(
                cutoff=500.0,
                resonance=q,
                filter_type="lowpass",
                sample_rate=self.SAMPLE_RATE,
            )
            signal = _sine(500.0, 4000, self.SAMPLE_RATE)
            out = _process_mono(f, signal)
            inp_rms = _rms(signal)
            out_rms = _rms(out[2000:])
            return out_rms / inp_rms

        gain_low = _gain_at(0.5)
        gain_high = _gain_at(2.0)
        assert gain_high > gain_low, (
            f"Q=2.0 gain ({gain_high:.4f}) ≤ Q=0.5 gain ({gain_low:.4f})"
        )


# ---------------------------------------------------------------------------
# UltraFastResonantFilter — HPF Response
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUltraFastResonantFilterHPF:
    """Verify high-pass filter behaviour."""

    SAMPLE_RATE = 48000

    def test_hpf_blocks_dc(self):
        """HPF at 500 Hz: DC (constant 1.0) should settle to ≈ 0."""
        f = UltraFastResonantFilter(
            cutoff=500.0,
            resonance=0.707,
            filter_type="highpass",
            sample_rate=self.SAMPLE_RATE,
        )
        # Feed DC directly and let it settle (HPF blocks DC)
        vals = np.empty(2000, dtype=np.float64)
        for i in range(2000):
            left, _ = f.process(1.0, is_stereo=False)
            vals[i] = left
        steady = np.mean(np.abs(vals[1500:]))
        assert steady < 0.05, f"DC leak {steady:.4f} (expected < 0.05)"

    def test_hpf_passes_high_frequencies(self):
        """HPF at 100 Hz: 5 kHz sine should pass with < 10 % error."""
        f = UltraFastResonantFilter(
            cutoff=100.0,
            resonance=0.707,
            filter_type="highpass",
            sample_rate=self.SAMPLE_RATE,
        )
        signal = _sine(5000.0, 2000, self.SAMPLE_RATE)
        inp_rms = _rms(signal)
        out = _process_mono(f, signal)
        out_rms = _rms(out[500:])
        ratio = out_rms / inp_rms
        assert 0.90 <= ratio <= 1.10, f"HPF passband ratio {ratio:.4f}"

    def test_hpf_attenuates_low_frequencies(self):
        """HPF at 1 kHz: 100 Hz sine should be > 10 dB down."""
        f = UltraFastResonantFilter(
            cutoff=1000.0,
            resonance=0.707,
            filter_type="highpass",
            sample_rate=self.SAMPLE_RATE,
        )
        signal = _sine(100.0, 3000, self.SAMPLE_RATE)
        inp_rms = _rms(signal)
        out = _process_mono(f, signal)
        out_rms = _rms(out[1000:])
        atten_db = 20.0 * np.log10(max(1e-12, out_rms) / max(1e-12, inp_rms))
        assert atten_db <= -10.0, f"HPF low-freq attenuation only {atten_db:.1f} dB"


# ---------------------------------------------------------------------------
# UltraFastResonantFilter — BPF Response
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUltraFastResonantFilterBPF:
    """Verify band-pass filter behaviour."""

    SAMPLE_RATE = 48000

    def test_bpf_passes_center(self):
        """BPF at 1 kHz: 1 kHz sine yields non-zero output."""
        f = UltraFastResonantFilter(
            cutoff=1000.0,
            resonance=1.0,
            filter_type="bandpass",
            sample_rate=self.SAMPLE_RATE,
        )
        signal = _sine(1000.0, 2000, self.SAMPLE_RATE)
        out = _process_mono(f, signal)
        out_rms = _rms(out[500:])
        assert out_rms > 0.05, f"BPF center output too low ({out_rms:.6f})"

    def test_bpf_attenuates_off_center(self):
        """BPF at 1 kHz: 1 kHz > 100 Hz and 1 kHz > 8 kHz output RMS."""
        f = UltraFastResonantFilter(
            cutoff=1000.0,
            resonance=1.0,
            filter_type="bandpass",
            sample_rate=self.SAMPLE_RATE,
        )

        def _rms_at(freq: float) -> float:
            f.reset()
            signal = _sine(freq, 2000, self.SAMPLE_RATE)
            out = _process_mono(f, signal)
            return _rms(out[500:])

        rms_center = _rms_at(1000.0)
        rms_low = _rms_at(100.0)
        rms_high = _rms_at(8000.0)
        assert rms_center > rms_low, f"Center {rms_center:.4f} ≤ low {rms_low:.4f}"
        assert rms_center > rms_high, f"Center {rms_center:.4f} ≤ high {rms_high:.4f}"


# ---------------------------------------------------------------------------
# UltraFastResonantFilter — Stability
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUltraFastResonantFilterStability:
    """Filter must remain numerically stable under extreme conditions."""

    SAMPLE_RATE = 48000

    def test_filter_self_oscillation(self):
        """High resonance impulse response rings and decays without explosion."""
        f = UltraFastResonantFilter(
            cutoff=500.0,
            resonance=2.0,
            filter_type="lowpass",
            sample_rate=self.SAMPLE_RATE,
        )
        # Impulse: single 1.0 sample followed by zeros
        out = np.empty(10000, dtype=np.float64)
        for i in range(len(out)):
            inp = 1.0 if i == 0 else 0.0
            left, _ = f.process(inp, is_stereo=False)
            out[i] = left

        assert not np.any(np.isnan(out)), "NaN in filter output"
        assert not np.any(np.isinf(out)), "Inf in filter output"

        # The tail (last 5000 samples) should be decaying toward zero
        tail_peak = float(np.max(np.abs(out[5000:])))
        assert tail_peak < 0.1, f"Tail peak {tail_peak:.4f} too large (not decaying)"

    def test_filter_stable_at_extreme_cutoff(self):
        """Cutoff near Nyquist produces no NaN/Inf."""
        f = UltraFastResonantFilter(
            cutoff=20000.0,
            resonance=0.707,
            filter_type="lowpass",
            sample_rate=self.SAMPLE_RATE,
        )
        signal = _sine(1000.0, 2000, self.SAMPLE_RATE)
        out = _process_mono(f, signal)
        assert not np.any(np.isnan(out)), "NaN at extreme cutoff"
        assert not np.any(np.isinf(out)), "Inf at extreme cutoff"


# ---------------------------------------------------------------------------
# UltraFastResonantFilter — Spectral Shape (FFT)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUltraFastResonantFilterSpectral:
    """FFT-based spectral analysis."""

    SAMPLE_RATE = 48000
    BLOCK = 8192

    def test_lpf_spectral_content(self):
        """LPF at 2 kHz: energy above 2 kHz drops > 6 dB vs input."""
        f = UltraFastResonantFilter(
            cutoff=2000.0,
            resonance=0.707,
            filter_type="lowpass",
            sample_rate=self.SAMPLE_RATE,
            block_size=self.BLOCK,
        )
        # White noise
        rng = np.random.default_rng(42)
        noise = rng.uniform(-1.0, 1.0, self.BLOCK).astype(np.float32)
        inp = noise.copy()
        out_left = np.empty_like(inp)
        out_right = np.empty_like(inp)
        f.process_block(inp, inp, out_left, out_right)

        # FFT
        inp_fft = np.fft.rfft(inp.astype(np.float64))
        out_fft = np.fft.rfft(out_left.astype(np.float64))
        freqs = np.fft.rfftfreq(self.BLOCK, 1.0 / self.SAMPLE_RATE)

        above_mask = freqs > 2000.0
        inp_energy_above = np.sum(np.abs(inp_fft[above_mask]) ** 2)
        out_energy_above = np.sum(np.abs(out_fft[above_mask]) ** 2)

        inp_energy_above = max(inp_energy_above, 1e-30)
        out_energy_above = max(out_energy_above, 1e-30)

        atten_db = 10.0 * np.log10(out_energy_above / inp_energy_above)
        assert atten_db <= -6.0, (
            f"Spectral attenuation above 2 kHz only {atten_db:.1f} dB (expected ≤ -6 dB)"
        )


# ---------------------------------------------------------------------------
# UltraFastResonantFilter — Brightness / Harmonic Content Modulation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUltraFastResonantFilterModulation:
    """Brightness and harmonic-content modulation."""

    SAMPLE_RATE = 48000

    def test_brightness_modulation_affects_cutoff(self):
        """Higher brightness → less attenuation at 2 kHz (effective cutoff rises)."""
        f = UltraFastResonantFilter(
            cutoff=1000.0,
            resonance=0.707,
            filter_type="lowpass",
            sample_rate=self.SAMPLE_RATE,
        )
        signal = _sine(2000.0, 2000, self.SAMPLE_RATE)

        # Brightness = 0
        f.set_brightness(0)
        out0 = _process_mono(f, signal)
        rms0 = _rms(out0[500:])

        # Brightness = 127
        f.reset()
        f.set_brightness(127)
        out127 = _process_mono(f, signal)
        rms127 = _rms(out127[500:])

        assert rms127 > rms0 * 1.1, (
            f"Brightness 127 RMS ({rms127:.6f}) not clearly > brightness 0 RMS ({rms0:.6f})"
        )

    def test_harmonic_content_modulation_affects_resonance(self):
        """Higher harmonic_content → stronger resonance peak at cutoff."""
        f = UltraFastResonantFilter(
            cutoff=500.0,
            resonance=0.5,
            filter_type="lowpass",
            sample_rate=self.SAMPLE_RATE,
        )
        signal = _sine(500.0, 3000, self.SAMPLE_RATE)

        # Harmonic content = 0
        f.set_harmonic_content(0)
        out0 = _process_mono(f, signal)
        rms0 = _rms(out0[1000:])

        # Harmonic content = 127
        f.reset()
        f.set_harmonic_content(127)
        out127 = _process_mono(f, signal)
        rms127 = _rms(out127[1000:])

        assert rms127 > rms0 * 1.02, (
            f"Harmonic 127 RMS ({rms127:.6f}) not > harmonic 0 RMS ({rms0:.6f})"
        )


# ---------------------------------------------------------------------------
# UltraFastResonantFilter — Stereo Width
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUltraFastResonantFilterStereo:
    """Stereo width coefficient verification."""

    SAMPLE_RATE = 48000

    def test_stereo_width_different_coefficients(self):
        """Stereo_width=1.0 → L/R coefs differ; stereo_width=0.0 → L/R coefs equal."""
        # Wide stereo
        f_wide = UltraFastResonantFilter(
            cutoff=1000.0,
            resonance=0.707,
            filter_type="lowpass",
            stereo_width=1.0,
            sample_rate=self.SAMPLE_RATE,
        )
        left_coefs = (f_wide.b0_l, f_wide.b1_l, f_wide.b2_l, f_wide.a1_l, f_wide.a2_l)
        right_coefs = (f_wide.b0_r, f_wide.b1_r, f_wide.b2_r, f_wide.a1_r, f_wide.a2_r)
        assert left_coefs != right_coefs, "Wide stereo: L/R coefficients should differ"

        # Mono
        f_mono = UltraFastResonantFilter(
            cutoff=1000.0,
            resonance=0.707,
            filter_type="lowpass",
            stereo_width=0.0,
            sample_rate=self.SAMPLE_RATE,
        )
        left_coefs_m = (f_mono.b0_l, f_mono.b1_l, f_mono.b2_l, f_mono.a1_l, f_mono.a2_l)
        right_coefs_m = (f_mono.b0_r, f_mono.b1_r, f_mono.b2_r, f_mono.a1_r, f_mono.a2_r)
        assert left_coefs_m == right_coefs_m, "Mono: L/R coefficients should be equal"


# ---------------------------------------------------------------------------
# UltraFastResonantFilter — Key Follow
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUltraFastResonantFilterKeyFollow:
    """apply_note_pitch behaviour."""

    SAMPLE_RATE = 48000

    def test_apply_note_pitch(self):
        """Higher note ⇒ higher cutoff when key_follow > 0."""
        f = UltraFastResonantFilter(
            cutoff=1000.0,
            key_follow=0.5,
            filter_type="lowpass",
            sample_rate=self.SAMPLE_RATE,
        )
        c72 = f.apply_note_pitch(72)  # one octave above middle C
        c48 = f.apply_note_pitch(48)  # one octave below middle C
        assert c72 > c48, f"apply_note_pitch(72)={c72:.2f} ≤ apply_note_pitch(48)={c48:.2f}"

    def test_apply_note_pitch_no_key_follow(self):
        """key_follow=0 ⇒ apply_note_pitch returns base cutoff regardless of note."""
        f = UltraFastResonantFilter(
            cutoff=1000.0,
            key_follow=0.0,
            filter_type="lowpass",
            sample_rate=self.SAMPLE_RATE,
        )
        assert f.apply_note_pitch(72) == pytest.approx(1000.0)
        assert f.apply_note_pitch(48) == pytest.approx(1000.0)


# ---------------------------------------------------------------------------
# UltraFastResonantFilter — Reset
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUltraFastResonantFilterReset:
    """Reset must clear state carry-over."""

    SAMPLE_RATE = 48000

    def test_reset_zeros_state(self):
        """After reset, processing the same input yields the same output as initially."""
        f = UltraFastResonantFilter(
            cutoff=500.0,
            resonance=0.707,
            filter_type="lowpass",
            sample_rate=self.SAMPLE_RATE,
        )
        rng = np.random.default_rng(123)
        signal = rng.uniform(-0.5, 0.5, 500).astype(np.float32)

        # First pass
        out1 = _process_mono(f, signal)

        # Reset & second pass
        f.reset()
        out2 = _process_mono(f, signal)

        np.testing.assert_allclose(out2, out1, atol=1e-6, err_msg="State not properly reset")


# ---------------------------------------------------------------------------
# BiquadFilter — Frequency Characteristic
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBiquadFilter:
    """Verify BiquadFilter class behaviour."""

    SAMPLE_RATE = 48000

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _process_mono(bf: BiquadFilter, signal: np.ndarray) -> np.ndarray:
        out = np.empty_like(signal)
        for i in range(len(signal)):
            out[i] = bf.process(float(signal[i]))
        return out

    def _warmup(self, bf: BiquadFilter, n: int = 200) -> None:
        for _ in range(n):
            bf.process(0.0)

    # -- tests -------------------------------------------------------------

    def test_biquad_lowpass_2p(self):
        """Lowpass_2p at 1 kHz: 100 Hz passes with less attenuation than 5 kHz."""
        bf = BiquadFilter("lowpass_2p", cutoff=1000.0, resonance=0.707, sample_rate=self.SAMPLE_RATE)

        def _rms_at(freq: float) -> float:
            bf.reset()
            sig = _sine(freq, 2000, self.SAMPLE_RATE)
            out = self._process_mono(bf, sig)
            return _rms(out[500:])

        rms_low = _rms_at(100.0)
        rms_high = _rms_at(5000.0)
        assert rms_low > rms_high * 1.5, (
            f"LPF 100 Hz ({rms_low:.4f}) not clearly > 5 kHz ({rms_high:.4f})"
        )

    def test_biquad_highpass_2p(self):
        """Highpass_2p at 1 kHz: 5 kHz passes better than 100 Hz."""
        bf = BiquadFilter("highpass_2p", cutoff=1000.0, resonance=0.707, sample_rate=self.SAMPLE_RATE)

        def _rms_at(freq: float) -> float:
            bf.reset()
            sig = _sine(freq, 2000, self.SAMPLE_RATE)
            out = self._process_mono(bf, sig)
            return _rms(out[500:])

        rms_low = _rms_at(100.0)
        rms_high = _rms_at(5000.0)
        assert rms_high > rms_low * 1.5, (
            f"HPF 5 kHz ({rms_high:.4f}) not clearly > 100 Hz ({rms_low:.4f})"
        )

    def test_biquad_bandpass(self):
        """Bandpass at 1 kHz: center passes better than off-center."""
        bf = BiquadFilter("bandpass", cutoff=1000.0, resonance=1.0, sample_rate=self.SAMPLE_RATE)

        def _rms_at(freq: float) -> float:
            bf.reset()
            sig = _sine(freq, 2000, self.SAMPLE_RATE)
            out = self._process_mono(bf, sig)
            return _rms(out[500:])

        rms_center = _rms_at(1000.0)
        rms_low = _rms_at(100.0)
        rms_high = _rms_at(8000.0)
        assert rms_center > rms_low, f"Center {rms_center:.4f} ≤ low {rms_low:.4f}"
        assert rms_center > rms_high, f"Center {rms_center:.4f} ≤ high {rms_high:.4f}"

    def test_biquad_notch(self):
        """Notch at 1 kHz: 1 kHz strongly attenuated; 100 Hz / 8 kHz pass."""
        bf = BiquadFilter("notch", cutoff=1000.0, resonance=1.0, sample_rate=self.SAMPLE_RATE)

        def _rms_at(freq: float) -> float:
            bf.reset()
            sig = _sine(freq, 2000, self.SAMPLE_RATE)
            out = self._process_mono(bf, sig)
            return _rms(out[500:])

        rms_center = _rms_at(1000.0)
        rms_low = _rms_at(100.0)
        rms_high = _rms_at(8000.0)
        assert rms_center < rms_low * 0.3, (
            f"Notch center {rms_center:.4f} not strongly attenuated vs low {rms_low:.4f}"
        )
        assert rms_center < rms_high * 0.3, (
            f"Notch center {rms_center:.4f} not strongly attenuated vs high {rms_high:.4f}"
        )

    def test_biquad_first_order(self):
        """1-pole should have shallower rolloff than 2-pole at same cutoff."""
        sig_high = _sine(5000.0, 2000, self.SAMPLE_RATE)
        sig_low = _sine(100.0, 2000, self.SAMPLE_RATE)

        bf1 = BiquadFilter("lowpass_1p", cutoff=1000.0, resonance=0.707, sample_rate=self.SAMPLE_RATE)
        bf2 = BiquadFilter("lowpass_2p", cutoff=1000.0, resonance=0.707, sample_rate=self.SAMPLE_RATE)

        out1 = self._process_mono(bf1, sig_high)
        out2 = self._process_mono(bf2, sig_high)
        rms1 = _rms(out1[500:])
        rms2 = _rms(out2[500:])
        assert rms1 > rms2, (
            f"1-pole RMS ({rms1:.4f}) ≤ 2-pole RMS ({rms2:.4f}) at high freq"
        )

    def test_biquad_reset(self):
        """Reset zeros the state."""
        bf = BiquadFilter("lowpass_2p", cutoff=1000.0, resonance=0.707, sample_rate=self.SAMPLE_RATE)
        # Process some signal
        sig = _sine(500.0, 100, self.SAMPLE_RATE)
        for s in sig:
            bf.process(float(s))
        # State should be non-zero now
        assert bf.z1 != 0.0 or bf.z2 != 0.0, "State should be non-zero after processing"
        bf.reset()
        assert bf.z1 == 0.0, f"z1 not reset ({bf.z1})"
        assert bf.z2 == 0.0, f"z2 not reset ({bf.z2})"


# ---------------------------------------------------------------------------
# FilterPool
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFilterPool:
    """FilterPool acquire / release / stats."""

    def test_filter_pool_acquire_release(self):
        """Acquire and release filters from pool."""
        pool = FilterPool(max_filters=50, block_size=256, sample_rate=48000)
        filters = [pool.acquire_filter() for _ in range(10)]
        for f in filters:
            pool.release_filter(f)
        # No error means success

    def test_filter_pool_stats(self):
        """get_pool_stats returns expected keys."""
        pool = FilterPool(max_filters=100, block_size=512, sample_rate=48000)
        stats = pool.get_pool_stats()
        assert "pooled_filters" in stats
        assert "max_filters" in stats
        assert "block_size" in stats
        assert "sample_rate" in stats
        assert stats["max_filters"] == 100
        assert stats["block_size"] == 512

    def test_filter_pool_acquire_with_params(self):
        """Acquire with custom parameters returns correctly configured filter."""
        pool = FilterPool(max_filters=50, block_size=256, sample_rate=48000)
        f = pool.acquire_filter(cutoff=2000.0, resonance=1.0, filter_type="highpass")
        assert f.cutoff == pytest.approx(2000.0)
        assert f.resonance == pytest.approx(1.0)
        assert f.filter_type == "highpass"

    def test_filter_pool_acquire_reuses_preallocated(self):
        """Acquire uses pre-allocated filters from pool first."""
        pool = FilterPool(max_filters=100, block_size=256, sample_rate=48000)
        before = pool.get_pool_stats()["pooled_filters"]
        # Pre-allocated filters exist
        assert before > 0, "Pool should pre-allocate filters"
        f = pool.acquire_filter()
        after = pool.get_pool_stats()["pooled_filters"]
        assert after == before - 1, "Acquire should reduce pool count"
        pool.release_filter(f)
        after_release = pool.get_pool_stats()["pooled_filters"]
        assert after_release == after + 1, "Release should increase pool count"


# ---------------------------------------------------------------------------
# UltraFastResonantFilter — Parameter Clamping
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUltraFastResonantFilterClamping:
    """Parameter clamping on set_parameters."""

    SAMPLE_RATE = 48000

    def test_set_parameters_clamping(self):
        """Out-of-range values are clamped to valid bounds."""
        f = UltraFastResonantFilter(
            cutoff=1000.0,
            resonance=0.7,
            filter_type="lowpass",
            sample_rate=self.SAMPLE_RATE,
        )
        f.set_parameters(cutoff=50000.0, resonance=5.0, key_follow=2.0, stereo_width=3.0)
        assert f.cutoff == 20000.0, f"cutoff {f.cutoff} should be 20000"
        assert f.resonance == 2.0, f"resonance {f.resonance} should be 2.0"
        assert f.key_follow == 1.0, f"key_follow {f.key_follow} should be 1.0"
        assert f.stereo_width == 1.0, f"stereo_width {f.stereo_width} should be 1.0"

    def test_set_parameters_clamping_low(self):
        """Below-minimum values are clamped to valid bounds."""
        f = UltraFastResonantFilter(
            cutoff=1000.0,
            resonance=0.7,
            filter_type="lowpass",
            sample_rate=self.SAMPLE_RATE,
        )
        f.set_parameters(cutoff=0.0, resonance=-1.0, key_follow=-0.5, stereo_width=-2.0)
        assert f.cutoff == 20.0, f"cutoff {f.cutoff} should be 20"
        assert f.resonance == 0.0, f"resonance {f.resonance} should be 0"
        assert f.key_follow == 0.0, f"key_follow {f.key_follow} should be 0"
        assert f.stereo_width == 0.0, f"stereo_width {f.stereo_width} should be 0"
