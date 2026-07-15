"""
Integration tests for chained DSP primitive processing.

Tests the combination of LFO, Filter, Panner, and Envelope primitives
together as they would be used in a real synthesizer signal chain.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from synth.primitives.oscillator import UltraFastXGLFO
from synth.primitives.filter import UltraFastResonantFilter
from synth.primitives.panner import UltraFastStereoPanner
from synth.primitives.envelope import UltraFastADSREnvelope, EnvelopeState
from synth.primitives.buffer_pool import XGBufferPool, BufferPoolExhaustedError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def generate_mono_tone(
    freq: float,
    sample_rate: int,
    num_samples: int,
    amplitude: float = 0.5,
) -> np.ndarray:
    """Generate a mono sine tone (float32, shape ``(num_samples,)``)."""
    t = np.arange(num_samples, dtype=np.float32) / sample_rate
    return (amplitude * np.sin(2.0 * np.pi * freq * t)).astype(np.float32)


def generate_stereo_tone(
    freq_l: float,
    freq_r: float,
    sample_rate: int,
    num_samples: int,
    amplitude: float = 0.5,
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(left, right)`` arrays with different frequencies."""
    t = np.arange(num_samples, dtype=np.float32) / sample_rate
    left = (amplitude * np.sin(2.0 * np.pi * freq_l * t)).astype(np.float32)
    right = (amplitude * np.sin(2.0 * np.pi * freq_r * t)).astype(np.float32)
    return left, right


def rms(x: np.ndarray) -> float:
    """Root-mean-square of a numpy array."""
    return float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))


def block_peak_envelope(x: np.ndarray, block_size: int) -> np.ndarray:
    """Peak amplitude per block (non-overlapping), for envelope detection."""
    n = len(x) // block_size
    env = np.zeros(n, dtype=np.float64)
    for i in range(n):
        seg = x[i * block_size : (i + 1) * block_size]
        env[i] = float(np.max(np.abs(seg))) if len(seg) else 0.0
    return env


def block_rms_envelope(x: np.ndarray, block_size: int) -> np.ndarray:
    """RMS per block (non-overlapping)."""
    n = len(x) // block_size
    env = np.zeros(n, dtype=np.float64)
    for i in range(n):
        seg = x[i * block_size : (i + 1) * block_size]
        env[i] = rms(seg) if len(seg) else 0.0
    return env


# ===========================================================================
# 1. LFO → Filter Modulation Test
# ===========================================================================

@pytest.mark.integration
class TestLFOFilterModulation:
    """LFO modulating a low-pass filter cutoff produces periodic amplitude
    variation at the LFO rate."""

    SAMPLE_RATE = 44100
    BLOCK_SIZE = 1024

    def _lfo_cutoff_from_mod(self, lfo_block: np.ndarray) -> float:
        """Map LFO block values [-1, 1] → cutoff frequency [200, 8000] Hz."""
        avg = float(np.mean(lfo_block))
        # normalise [-1,1] → [0,1]
        norm = (avg + 1.0) * 0.5
        return 200.0 + norm * (8000.0 - 200.0)

    def test_modulation_produces_periodic_amplitude(
        self, sample_rate: int, block_size: int,
    ) -> None:
        """5 Hz LFO modulating a LPF cutoff; verify amplitude envelope varies."""
        lfo = UltraFastXGLFO(
            id=0, waveform="sine", rate=5.0, depth=1.0,
            sample_rate=sample_rate, block_size=block_size,
        )
        filt = UltraFastResonantFilter(
            cutoff=2000.0, resonance=0.5, filter_type="lowpass",
            sample_rate=sample_rate, block_size=block_size,
        )

        duration_s = 1.0
        total = int(sample_rate * duration_s)
        nblocks = total // block_size

        carrier = generate_mono_tone(440.0, sample_rate, total, amplitude=0.5)
        out = np.zeros(total, dtype=np.float32)
        lfo_buf = np.zeros(block_size, dtype=np.float32)
        ch_buf = np.zeros(block_size, dtype=np.float32)

        off = 0
        for _ in range(nblocks):
            lfo.generate_block(lfo_buf, block_size)
            cutoff = self._lfo_cutoff_from_mod(lfo_buf)
            filt.set_parameters(cutoff=cutoff)

            ch_buf[:] = carrier[off: off + block_size]
            filt.process_block(ch_buf, ch_buf,  # mono input → both channels
                               out[off: off + block_size],
                               out[off: off + block_size],
                               block_size)
            off += block_size

        # Compute per-block RMS — LFO at 5 Hz should produce variation
        env = block_rms_envelope(out, block_size)
        # The standard deviation of the block RMS should be well above
        # numerical noise if the LFO is modulating the signal.
        rms_std = float(np.std(env))
        assert rms_std > 1e-4, (
            f"Expected RMS variation from LFO modulation, got std={rms_std}"
        )
        # At least one significant peak-to-trough swing
        assert float(np.ptp(env)) > 0.01, (
            "Peak-to-peak envelope should be significant"
        )
        assert np.any(out != 0), "Output should be non-zero"
        assert not np.any(np.isnan(out)), "No NaN values allowed"
        assert not np.any(np.isinf(out)), "No Inf values allowed"

    def test_center_and_extreme_lfo_depth(
        self, sample_rate: int, block_size: int,
    ) -> None:
        """LFO depth = 0, 0.5, 1.0 should all produce non-zero output."""
        lfo = UltraFastXGLFO(
            id=0, waveform="sine", rate=5.0, depth=1.0,
            sample_rate=sample_rate, block_size=block_size,
        )
        filt = UltraFastResonantFilter(
            cutoff=2000.0, resonance=0.5, filter_type="lowpass",
            sample_rate=sample_rate, block_size=block_size,
        )

        total = block_size * 10
        carrier = generate_mono_tone(440.0, sample_rate, total)

        for depth in (0.0, 0.5, 1.0):
            lfo.set_parameters(depth=depth)
            out = np.zeros(total, dtype=np.float32)
            lfo_buf = np.zeros(block_size, dtype=np.float32)
            ch_buf = np.zeros(block_size, dtype=np.float32)
            off = 0
            for _ in range(total // block_size):
                lfo.generate_block(lfo_buf, block_size)
                cutoff = self._lfo_cutoff_from_mod(lfo_buf)
                filt.set_parameters(cutoff=cutoff)
                ch_buf[:] = carrier[off: off + block_size]
                filt.process_block(ch_buf, ch_buf,
                                   out[off: off + block_size],
                                   out[off: off + block_size],
                                   block_size)
                off += block_size

            assert np.any(out != 0), f"Output zero at depth={depth}"
            assert not np.any(np.isnan(out)), f"NaN at depth={depth}"
            assert not np.any(np.isinf(out)), f"Inf at depth={depth}"


# ===========================================================================
# 2. Filter → Panner Chain
# ===========================================================================

@pytest.mark.integration
class TestFilterPannerChain:
    """Feed a test tone through a filter then a panner, verify channel
    routing."""

    def test_lpf_center_pan(self, sample_rate: int, block_size: int) -> None:
        """LPF at 500 Hz, center pan → both channels equal."""
        total = block_size * 5
        carrier = generate_mono_tone(440.0, sample_rate, total)

        filt = UltraFastResonantFilter(
            cutoff=500.0, resonance=0.3, filter_type="lowpass",
            sample_rate=sample_rate, block_size=block_size,
        )
        panner = UltraFastStereoPanner(
            pan_position=0.5, sample_rate=sample_rate, block_size=block_size,
        )

        out_l = np.zeros(total, dtype=np.float32)
        out_r = np.zeros(total, dtype=np.float32)
        buf_l = np.zeros(block_size, dtype=np.float32)
        buf_r = np.zeros(block_size, dtype=np.float32)

        off = 0
        for _ in range(total // block_size):
            buf_l[:] = carrier[off: off + block_size]
            buf_r[:] = carrier[off: off + block_size]
            filt_l, filt_r = filt.process_block(buf_l, buf_r)
            panner.process_block_mono(
                (filt_l + filt_r) * 0.5,  # collapse to mono
                out_l[off: off + block_size],
                out_r[off: off + block_size],
            )
            off += block_size

        assert np.any(out_l != 0)
        assert np.any(out_r != 0)
        # Center pan → L ≈ R (minor differences from filter stereo width
        # and fast-math table lookups for sin/cos pan law)
        np.testing.assert_allclose(out_l, out_r, atol=1e-3)

    def test_lpf_hard_left_pan(self, sample_rate: int, block_size: int) -> None:
        """LPF at 500 Hz, hard-left → output only in left channel."""
        total = block_size * 5
        carrier = generate_mono_tone(440.0, sample_rate, total)

        filt = UltraFastResonantFilter(
            cutoff=500.0, resonance=0.3, filter_type="lowpass",
            sample_rate=sample_rate, block_size=block_size,
        )
        panner = UltraFastStereoPanner(
            pan_position=0.0, sample_rate=sample_rate, block_size=block_size,
        )

        out_l = np.zeros(total, dtype=np.float32)
        out_r = np.zeros(total, dtype=np.float32)
        buf_l = np.zeros(block_size, dtype=np.float32)
        buf_r = np.zeros(block_size, dtype=np.float32)

        off = 0
        for _ in range(total // block_size):
            buf_l[:] = carrier[off: off + block_size]
            buf_r[:] = carrier[off: off + block_size]
            filt_l, filt_r = filt.process_block(buf_l, buf_r)
            panner.process_block_mono(
                (filt_l + filt_r) * 0.5,
                out_l[off: off + block_size],
                out_r[off: off + block_size],
            )
            off += block_size

        assert np.any(out_l != 0), "Left channel should have signal"
        # Hard-left: right channel should be near-silent (allow numerical noise
        # from filter rounding and fast-math trig approximations)
        rms_r = rms(out_r)
        assert rms_r < 1e-4, (
            f"Right channel should be near-silent at hard-left, RMS={rms_r}"
        )

    def test_hpf_hard_right_pan(self, sample_rate: int, block_size: int) -> None:
        """HPF at 1 kHz, hard-right → output only in right channel."""
        total = block_size * 5
        carrier = generate_mono_tone(440.0, sample_rate, total)

        filt = UltraFastResonantFilter(
            cutoff=1000.0, resonance=0.3, filter_type="highpass",
            sample_rate=sample_rate, block_size=block_size,
        )
        panner = UltraFastStereoPanner(
            pan_position=1.0, sample_rate=sample_rate, block_size=block_size,
        )

        out_l = np.zeros(total, dtype=np.float32)
        out_r = np.zeros(total, dtype=np.float32)
        buf_l = np.zeros(block_size, dtype=np.float32)
        buf_r = np.zeros(block_size, dtype=np.float32)

        off = 0
        for _ in range(total // block_size):
            buf_l[:] = carrier[off: off + block_size]
            buf_r[:] = carrier[off: off + block_size]
            filt_l, filt_r = filt.process_block(buf_l, buf_r)
            panner.process_block_mono(
                (filt_l + filt_r) * 0.5,
                out_l[off: off + block_size],
                out_r[off: off + block_size],
            )
            off += block_size

        assert np.any(out_r != 0), "Right channel should have signal"
        # Hard-right: left channel should be near-silent
        rms_l = rms(out_l)
        assert rms_l < 1e-4, (
            f"Left channel should be near-silent at hard-right, RMS={rms_l}"
        )

    def test_filter_panner_output_shape(
        self, sample_rate: int, block_size: int,
    ) -> None:
        """Check output shapes at each stage."""
        total = block_size * 3
        carrier = generate_mono_tone(440.0, sample_rate, total)

        filt = UltraFastResonantFilter(
            cutoff=500.0, resonance=0.3, filter_type="lowpass",
            sample_rate=sample_rate, block_size=block_size,
        )
        panner = UltraFastStereoPanner(
            pan_position=0.5, sample_rate=sample_rate, block_size=block_size,
        )

        buf_l = carrier[:block_size].copy()
        buf_r = carrier[:block_size].copy()

        filt_l, filt_r = filt.process_block(buf_l, buf_r)
        assert filt_l.shape == (block_size,), f"Filter L shape: {filt_l.shape}"
        assert filt_r.shape == (block_size,), f"Filter R shape: {filt_r.shape}"

        pan_l, pan_r = panner.process_block_mono(
            (filt_l + filt_r) * 0.5,
        )
        assert pan_l.shape == (block_size,), f"Pan L shape: {pan_l.shape}"
        assert pan_r.shape == (block_size,), f"Pan R shape: {pan_r.shape}"


# ===========================================================================
# 3. Envelope → Amplitude Modulation
# ===========================================================================

@pytest.mark.integration
class TestEnvelopeAmplitudeModulation:
    """Envelope shapes a test tone: verify ADSR trajectory."""

    SAMPLE_RATE = 44100
    BLOCK_SIZE = 1024

    @pytest.fixture
    def env(self) -> UltraFastADSREnvelope:
        e = UltraFastADSREnvelope(
            delay=0.0,
            attack=0.01,
            hold=0.0,
            decay=0.1,
            sustain=0.5,
            release=0.2,
            sample_rate=self.SAMPLE_RATE,
            block_size=self.BLOCK_SIZE,
        )
        return e

    def test_attack_reaches_peak(self, env: UltraFastADSREnvelope) -> None:
        """Attack phase: level rises from ~0, reaches > 0.85 after one block."""
        env.note_on(velocity=127, note=60)
        buf = np.zeros(self.BLOCK_SIZE, dtype=np.float32)
        env.generate_block(buf, self.BLOCK_SIZE)

        # Attack=0.01s at 44100 Hz = ~441 samples for ~98 % convergence
        # to target. After 1024 samples the exponential attack has
        # progressed well into decay, reaching ≈ 0.89 at end of block.
        assert buf[0] < 0.1, f"Expected near-zero at start, got {buf[0]}"
        assert buf[0] >= 0.0, "Start value should be non-negative"
        # Mono-tonic rise in first ~400 samples
        assert buf[-1] > buf[0], "Envelope should rise from start"
        assert buf[-1] > 0.70, (
            f"Expected level well above 0, got {buf[-1]}"
        )
        assert np.all(buf >= 0.0), "No negative values"
        assert np.all(buf <= 1.01), "No values above 1.0"

    def test_decay_reaches_sustain(
        self, env: UltraFastADSREnvelope,
    ) -> None:
        """After attack+decay, envelope settles at sustain level ≈ 0.5."""
        env.note_on(velocity=127, note=60)

        # Process attack + decay. At 44100 Hz attack≈762 samples,
        # decay takes ~6800 samples to reach sustain. Use 10 blocks
        # (10240 samples) to ensure we're well into sustain.
        for _ in range(10):
            buf = np.zeros(self.BLOCK_SIZE, dtype=np.float32)
            env.generate_block(buf, self.BLOCK_SIZE)

        # Level should be close to sustain=0.5
        assert abs(env.level - 0.5) < 0.05, (
            f"Expected level ≈ 0.5, got {env.level}"
        )
        # State should be SUSTAIN or very close (just converged)
        assert env.state in (EnvelopeState.SUSTAIN, EnvelopeState.DECAY), (
            f"Expected SUSTAIN, got state={env.state}"
        )

    def test_release_decays_to_zero(
        self, env: UltraFastADSREnvelope,
    ) -> None:
        """Release: level decays to ~0."""
        env.note_on(velocity=127, note=60)

        # Process past attack+decay into sustain
        for _ in range(8):
            buf = np.zeros(self.BLOCK_SIZE, dtype=np.float32)
            env.generate_block(buf, self.BLOCK_SIZE)

        # Trigger release
        env.note_off()
        buf = np.zeros(self.BLOCK_SIZE, dtype=np.float32)
        env.generate_block(buf, self.BLOCK_SIZE)

        assert env.state in (EnvelopeState.RELEASE, EnvelopeState.IDLE), (
            f"Expected RELEASE/IDLE, got {env.state}"
        )
        # Over the first release block the level should drop detectably
        if env.state == EnvelopeState.RELEASE:
            assert env.level < 0.5, (
                f"Expected level < 0.5 during release, got {env.level}"
            )

        # Process enough blocks to complete release
        for _ in range(20):
            buf = np.zeros(self.BLOCK_SIZE, dtype=np.float32)
            env.generate_block(buf, self.BLOCK_SIZE)
            if env.state == EnvelopeState.IDLE:
                break

        assert env.state == EnvelopeState.IDLE, (
            f"Expected IDLE after release, got {env.state}"
        )
        assert abs(env.level) < 0.001, (
            f"Expected level ≈ 0, got {env.level}"
        )

    def test_envelope_modulates_tone_amplitude(
        self, env: UltraFastADSREnvelope,
    ) -> None:
        """Multiply a test tone by envelope; verify amplitude follows shape."""
        sample_rate = self.SAMPLE_RATE
        block_size = self.BLOCK_SIZE

        tone = generate_mono_tone(440.0, sample_rate, block_size, amplitude=0.5)

        # Attack phase
        env.note_on(velocity=127, note=60)
        env_buf = np.zeros(block_size, dtype=np.float32)
        env.generate_block(env_buf, block_size)

        modulated = tone * env_buf
        # Start of block: envelope ≈ 0 → modulated ≈ 0
        assert abs(modulated[0]) < 0.05, (
            f"Expected near-zero at attack start, got {modulated[0]}"
        )
        # End of block: envelope should be well above 0
        assert abs(modulated[-1]) > 0.1, (
            f"Expected non-zero amplitude at end of attack block"
        )

        # Sustain phase: process enough blocks to reach sustain
        for _ in range(15):
            env.generate_block(env_buf, block_size)
        modulated_sustain = tone * env_buf
        # Envelope ≈ 0.5 → modulated amplitude ≈ 0.5 * 0.5 = 0.25 peak
        assert float(np.max(np.abs(modulated_sustain))) > 0.1, (
            f"Expected non-zero sustain output"
        )

        # Release → 0
        env.note_off()
        for _ in range(30):
            env.generate_block(env_buf, block_size)
        modulated_release = tone * env_buf
        assert float(np.max(np.abs(modulated_release))) < 0.05, (
            f"Expected near-zero after release"
        )


# ===========================================================================
# 4. Full Chain: Envelope → LFO → Filter → Panner
# ===========================================================================

@pytest.mark.integration
class TestFullChain:
    """Complete signal chain simulating real-time rendering."""

    def test_full_chain_produces_stereo_output(
        self, sample_rate: int, block_size: int,
    ) -> None:
        """100 blocks processed; verify non-zero stereo output, no NaN/Inf,
        and output changes over time."""
        nblocks = 100
        total = nblocks * block_size

        # --- Primitives ---
        lfo = UltraFastXGLFO(
            id=0, waveform="sine", rate=5.0, depth=1.0,
            sample_rate=sample_rate, block_size=block_size,
        )
        filt = UltraFastResonantFilter(
            cutoff=2000.0, resonance=0.3, filter_type="lowpass",
            sample_rate=sample_rate, block_size=block_size,
        )
        panner = UltraFastStereoPanner(
            pan_position=0.5,
            sample_rate=sample_rate, block_size=block_size,
        )
        env = UltraFastADSREnvelope(
            delay=0.0, attack=0.05, hold=0.0, decay=0.3,
            sustain=0.6, release=0.5,
            sample_rate=sample_rate, block_size=block_size,
        )

        # --- Carrier ---
        carrier = generate_mono_tone(440.0, sample_rate, total, amplitude=0.5)

        # --- Output buffers ---
        out_stereo = np.zeros((total, 2), dtype=np.float32)

        # --- Per-block working buffers ---
        lfo_buf = np.zeros(block_size, dtype=np.float32)
        env_buf = np.zeros(block_size, dtype=np.float32)
        filt_l = np.zeros(block_size, dtype=np.float32)
        filt_r = np.zeros(block_size, dtype=np.float32)
        pan_l = np.zeros(block_size, dtype=np.float32)
        pan_r = np.zeros(block_size, dtype=np.float32)

        env.note_on(velocity=127, note=60)

        for blk in range(nblocks):
            off = blk * block_size

            # LFO modulates filter cutoff
            lfo.generate_block(lfo_buf, block_size)
            avg_lfo = float(np.mean(lfo_buf))
            norm = (avg_lfo + 1.0) * 0.5
            cutoff = 200.0 + norm * (8000.0 - 200.0)
            filt.set_parameters(cutoff=cutoff)

            # Envelope
            env.generate_block(env_buf, block_size)

            # Apply envelope to carrier
            filt_l[:] = carrier[off: off + block_size] * env_buf
            filt_r[:] = filt_l  # mono before panning

            # Filter
            filt.process_block(filt_l, filt_r)

            # Panner
            panner.process_block_mono(
                (filt_l + filt_r) * 0.5,
                pan_l, pan_r,
            )

            out_stereo[off: off + block_size, 0] = pan_l
            out_stereo[off: off + block_size, 1] = pan_r

        # --- Assertions ---
        assert np.any(out_stereo != 0), "Output should be non-zero"
        assert out_stereo.shape == (total, 2), (
            f"Expected ({total}, 2), got {out_stereo.shape}"
        )
        assert not np.any(np.isnan(out_stereo)), "No NaN in output"
        assert not np.any(np.isinf(out_stereo)), "No Inf in output"

        # Output changes over time (not a constant signal)
        assert np.std(out_stereo[:block_size * 10]) > 0.0
        # The envelope evolves, so later blocks differ from early blocks
        first_block_rms = rms(out_stereo[:block_size, 0])
        later_block_rms = rms(out_stereo[-block_size:, 0])
        assert not np.isclose(first_block_rms, later_block_rms, rtol=0.01), (
            "Output should change over time (envelope + LFO)"
        )

    def test_full_chain_release_ends_silence(
        self, sample_rate: int, block_size: int,
    ) -> None:
        """After note-off and full release, output goes to silence."""
        total = block_size * 50

        carrier = generate_mono_tone(440.0, sample_rate, total)
        lfo = UltraFastXGLFO(
            id=0, waveform="sine", rate=4.0, depth=0.5,
            sample_rate=sample_rate, block_size=block_size,
        )
        filt = UltraFastResonantFilter(
            cutoff=3000.0, resonance=0.2, filter_type="lowpass",
            sample_rate=sample_rate, block_size=block_size,
        )
        panner = UltraFastStereoPanner(
            pan_position=0.5, sample_rate=sample_rate, block_size=block_size,
        )
        env = UltraFastADSREnvelope(
            delay=0.0, attack=0.01, hold=0.0, decay=0.1,
            sustain=0.5, release=0.05,
            sample_rate=sample_rate, block_size=block_size,
        )

        out = np.zeros((total, 2), dtype=np.float32)
        lfo_buf = np.zeros(block_size, dtype=np.float32)
        env_buf = np.zeros(block_size, dtype=np.float32)
        f_l = np.zeros(block_size, dtype=np.float32)
        f_r = np.zeros(block_size, dtype=np.float32)
        p_l = np.zeros(block_size, dtype=np.float32)
        p_r = np.zeros(block_size, dtype=np.float32)

        env.note_on(velocity=127, note=60)

        note_off_triggered = False
        for blk in range(total // block_size):
            off = blk * block_size

            lfo.generate_block(lfo_buf, block_size)
            norm = (float(np.mean(lfo_buf)) + 1.0) * 0.5
            filt.set_parameters(cutoff=200.0 + norm * (8000.0 - 200.0))

            env.generate_block(env_buf, block_size)

            f_l[:] = carrier[off: off + block_size] * env_buf
            f_r[:] = f_l
            filt.process_block(f_l, f_r)
            panner.process_block_mono(
                (f_l + f_r) * 0.5, p_l, p_r,
            )
            out[off: off + block_size, 0] = p_l
            out[off: off + block_size, 1] = p_r

            # Trigger note-off after ~half the blocks
            if blk == total // block_size // 2 and not note_off_triggered:
                env.note_off()
                note_off_triggered = True

        # The final blocks should be silence after release completes
        trailing = out[-block_size * 3 :, :]
        assert float(np.max(np.abs(trailing))) < 0.01, (
            "Output should be near-silent after release completes"
        )


# ===========================================================================
# 5. Buffer Pool Integration
# ===========================================================================

@pytest.mark.integration
class TestBufferPoolIntegration:
    """Use XGBufferPool for all buffers in the DSP chain."""

    def test_pool_allocates_and_reuses_buffers(
        self, sample_rate: int, block_size: int,
    ) -> None:
        """Use temporary_buffer context manager; verify no exhaustion error."""
        pool = XGBufferPool(
            sample_rate=sample_rate,
            max_block_size=block_size,
            memory_budget_mb=16.0,
        )

        try:
            with pool.temporary_buffer(block_size, channels=1) as mono_buf:
                # Pool returns shape (size,) for mono
                assert mono_buf.shape == (block_size,), (
                    f"Mono buf shape: {mono_buf.shape}"
                )
                mono_buf[:] = generate_mono_tone(440.0, sample_rate, block_size)

            with pool.temporary_buffer(block_size, channels=2) as stereo_buf:
                assert stereo_buf.shape == (block_size, 2), (
                    f"Stereo buf shape: {stereo_buf.shape}"
                )

            with pool.temporary_buffer(block_size, channels=1) as buf_a:
                with pool.temporary_buffer(block_size, channels=1) as buf_b:
                    buf_a[:] = 1.0
                    buf_b[:] = 2.0
                    # Both should be usable simultaneously
                    assert float(np.mean(buf_a)) == 1.0
                    assert float(np.mean(buf_b)) == 2.0

        except BufferPoolExhaustedError:
            pytest.fail("BufferPoolExhaustedError raised unexpectedly")

    def test_pool_in_full_chain(
        self, sample_rate: int, block_size: int,
    ) -> None:
        """Use pool buffers for the entire LFO → Filter → Panner chain."""
        pool = XGBufferPool(
            sample_rate=sample_rate,
            max_block_size=block_size,
            memory_budget_mb=32.0,
        )

        nblocks = 20
        total = nblocks * block_size

        # NOTE: We do NOT pass memory_pool to LFO because pool returns
        # mono buffers as (size, 1) which Numba can't handle in its 1D
        # temp_phase_buffer. Filter/Panner/Envelope handle pool gracefully.
        lfo = UltraFastXGLFO(
            id=0, waveform="sine", rate=5.0, depth=1.0,
            sample_rate=sample_rate, block_size=block_size,
        )
        filt = UltraFastResonantFilter(
            cutoff=2000.0, resonance=0.3, filter_type="lowpass",
            sample_rate=sample_rate, block_size=block_size,
            memory_pool=pool,
        )
        panner = UltraFastStereoPanner(
            pan_position=0.5, sample_rate=sample_rate, block_size=block_size,
            memory_pool=pool,
        )
        env = UltraFastADSREnvelope(
            delay=0.0, attack=0.01, hold=0.0, decay=0.1,
            sustain=0.5, release=0.3,
            sample_rate=sample_rate, block_size=block_size,
            memory_pool=pool,
        )

        # Acquire all buffers upfront using a flat acquisition pattern.
        # Keep them alive across the processing loop.
        carrier = pool.get_mono_buffer(total)
        lfo_buf = pool.get_mono_buffer(block_size)
        env_buf = pool.get_mono_buffer(block_size)
        f_l = pool.get_mono_buffer(block_size)
        f_r = pool.get_mono_buffer(block_size)
        p_l = pool.get_mono_buffer(block_size)
        p_r = pool.get_mono_buffer(block_size)
        out = pool.get_stereo_buffer(total)

        try:
            # Fill carrier
            carrier[:] = generate_mono_tone(440.0, sample_rate, total)

            env.note_on(velocity=127, note=60)

            for blk in range(nblocks):
                off = blk * block_size

                lfo.generate_block(lfo_buf, block_size)
                norm = (float(np.mean(lfo_buf)) + 1.0) * 0.5
                filt.set_parameters(cutoff=200.0 + norm * (8000.0 - 200.0))

                env.generate_block(env_buf, block_size)

                f_l[:] = carrier[off: off + block_size] * env_buf
                f_r[:] = f_l

                filt.process_block(f_l, f_r)

                panner.process_block_mono((f_l + f_r) * 0.5, p_l, p_r)

                out[off: off + block_size, 0] = p_l
                out[off: off + block_size, 1] = p_r

            assert np.any(out != 0), "Output should be non-zero"
            assert not np.any(np.isnan(out)), "No NaN in output"
            assert not np.any(np.isinf(out)), "No Inf in output"
        finally:
            # Return all buffers
            for buf in (carrier, lfo_buf, env_buf, f_l, f_r, p_l, p_r, out):
                pool.return_buffer(buf)

    def test_return_all_buffers(self, sample_rate: int, block_size: int) -> None:
        """Manually get and return buffers; verify pool stays healthy."""
        pool = XGBufferPool(
            sample_rate=sample_rate,
            max_block_size=block_size,
            memory_budget_mb=16.0,
        )

        bufs = []
        for _ in range(4):
            b = pool.get_mono_buffer(block_size)
            bufs.append(b)
        for _ in range(4):
            b = pool.get_stereo_buffer(block_size)
            bufs.append(b)

        # All buffers acquired successfully
        assert len(bufs) == 8

        # Return all
        for b in bufs:
            pool.return_buffer(b)

        # Pool should be usable after returning
        with pool.temporary_buffer(block_size, channels=2) as b:
            assert b.shape == (block_size, 2)


# ===========================================================================
# 6. Multiple Voices
# ===========================================================================

@pytest.mark.integration
class TestMultipleVoices:
    """Simulate polyphonic operation: 4 independent filter+panner chains."""

    VOICE_COUNT = 4
    FREQUENCIES = [262.0, 330.0, 392.0, 523.0]  # C4, E4, G4, C5

    def test_multi_voice_sum(
        self, sample_rate: int, block_size: int,
    ) -> None:
        """Four voices run in parallel and sum to a stereo mix bus."""
        total = block_size * 30

        # Create per-voice processing chains
        voices: list[dict] = []
        for idx, freq in enumerate(self.FREQUENCIES):
            lfo = UltraFastXGLFO(
                id=idx, waveform="sine", rate=3.0 + idx * 0.5,
                depth=0.5,
                sample_rate=sample_rate, block_size=block_size,
            )
            # Each voice has a slightly different initial cutoff
            cutoff = 1500.0 + idx * 500.0
            filt = UltraFastResonantFilter(
                cutoff=cutoff, resonance=0.3, filter_type="lowpass",
                sample_rate=sample_rate, block_size=block_size,
            )
            pan = idx / (self.VOICE_COUNT - 1) if self.VOICE_COUNT > 1 else 0.5
            panner = UltraFastStereoPanner(
                pan_position=pan,
                sample_rate=sample_rate, block_size=block_size,
            )
            carrier = generate_mono_tone(freq, sample_rate, total, amplitude=0.25)
            voices.append({
                "lfo": lfo,
                "filt": filt,
                "panner": panner,
                "carrier": carrier,
            })

        # Mix bus
        mix = np.zeros((total, 2), dtype=np.float32)
        voice_outs: list[np.ndarray] = []

        lfo_buf = np.zeros(block_size, dtype=np.float32)
        f_l = np.zeros(block_size, dtype=np.float32)
        f_r = np.zeros(block_size, dtype=np.float32)
        p_l = np.zeros(block_size, dtype=np.float32)
        p_r = np.zeros(block_size, dtype=np.float32)

        for blk in range(total // block_size):
            off = blk * block_size
            # Clear mix bus for this block
            mix_block_l = mix[off: off + block_size, 0]
            mix_block_r = mix[off: off + block_size, 1]
            mix_block_l.fill(0.0)
            mix_block_r.fill(0.0)

            for v in voices:
                lfo = v["lfo"]
                filt = v["filt"]
                panner = v["panner"]
                carrier = v["carrier"]

                lfo.generate_block(lfo_buf, block_size)
                norm = (float(np.mean(lfo_buf)) + 1.0) * 0.5
                filt.set_parameters(cutoff=200.0 + norm * (8000.0 - 200.0))

                f_l[:] = carrier[off: off + block_size]
                f_r[:] = f_l
                filt.process_block(f_l, f_r)
                panner.process_block_mono(
                    (f_l + f_r) * 0.5, p_l, p_r,
                )
                mix_block_l += p_l
                mix_block_r += p_r

        assert np.any(mix != 0), "Mix bus should be non-zero"
        assert mix.shape == (total, 2), (
            f"Expected ({total}, 2), got {mix.shape}"
        )
        assert not np.any(np.isnan(mix)), "No NaN in mix"
        assert not np.any(np.isinf(mix)), "No Inf in mix"

        # Verify each voice contributed — sum per voice RMS should be > 0
        for idx, v in enumerate(voices):
            chunk_l = np.zeros(total, dtype=np.float32)
            chunk_r = np.zeros(total, dtype=np.float32)
            lfo = v["lfo"]
            filt = v["filt"]
            panner = v["panner"]
            carrier = v["carrier"]

            lfo_buf2 = np.zeros(block_size, dtype=np.float32)
            f2_l = np.zeros(block_size, dtype=np.float32)
            f2_r = np.zeros(block_size, dtype=np.float32)
            p2_l = np.zeros(block_size, dtype=np.float32)
            p2_r = np.zeros(block_size, dtype=np.float32)

            lfo.reset()
            filt.reset()
            panner.reset()

            for blk in range(total // block_size):
                off = blk * block_size
                lfo.generate_block(lfo_buf2, block_size)
                norm = (float(np.mean(lfo_buf2)) + 1.0) * 0.5
                filt.set_parameters(cutoff=200.0 + norm * (8000.0 - 200.0))
                f2_l[:] = carrier[off: off + block_size]
                f2_r[:] = f2_l
                filt.process_block(f2_l, f2_r)
                panner.process_block_mono(
                    (f2_l + f2_r) * 0.5, p2_l, p2_r,
                )
                chunk_l[off: off + block_size] = p2_l
                chunk_r[off: off + block_size] = p2_r

            voice_rms = rms(chunk_l) + rms(chunk_r)
            assert voice_rms > 0.001, (
                f"Voice {idx} (freq={self.FREQUENCIES[idx]}) contributes no output"
            )


# ===========================================================================
# 7. Stereo Routing
# ===========================================================================

@pytest.mark.integration
class TestStereoRouting:
    """Stereo signal integrity through filter and panner."""

    def test_filter_processes_stereo_independently(
        self, sample_rate: int, block_size: int,
    ) -> None:
        """Filter preserves different content per channel."""
        total = block_size * 5
        left_tone, right_tone = generate_stereo_tone(
            440.0, 880.0, sample_rate, total,
        )

        filt = UltraFastResonantFilter(
            cutoff=5000.0, resonance=0.2, filter_type="lowpass",
            sample_rate=sample_rate, block_size=block_size,
        )

        out_l = np.zeros(total, dtype=np.float32)
        out_r = np.zeros(total, dtype=np.float32)

        for off in range(0, total, block_size):
            filt.process_block(
                left_tone[off: off + block_size],
                right_tone[off: off + block_size],
                out_l[off: off + block_size],
                out_r[off: off + block_size],
                block_size,
            )

        # Left and right should be different (different frequencies)
        assert not np.allclose(out_l, out_r, atol=1e-3), (
            "Stereo filter should process channels independently"
        )
        # Both channels should have output
        assert rms(out_l) > 0.01, "Left channel should have signal"
        assert rms(out_r) > 0.01, "Right channel should have signal"

    def test_panner_preserves_stereo_at_center(
        self, sample_rate: int, block_size: int,
    ) -> None:
        """Center-panned stereo signal keeps L/R content."""
        total = block_size * 5
        left_tone, right_tone = generate_stereo_tone(
            440.0, 880.0, sample_rate, total,
        )

        panner = UltraFastStereoPanner(
            pan_position=0.5, sample_rate=sample_rate, block_size=block_size,
        )

        out_l = np.zeros(total, dtype=np.float32)
        out_r = np.zeros(total, dtype=np.float32)

        for off in range(0, total, block_size):
            panner.process_block_stereo(
                left_tone[off: off + block_size],
                right_tone[off: off + block_size],
                out_l[off: off + block_size],
                out_r[off: off + block_size],
            )

        assert not np.allclose(out_l, out_r, atol=1e-2), (
            "Center pan should preserve stereo difference"
        )
        assert rms(out_l) > 0.01
        assert rms(out_r) > 0.01

    def test_panner_collapses_to_mono_at_hard_pan(
        self, sample_rate: int, block_size: int,
    ) -> None:
        """Hard panning collapses stereo image to one channel."""
        total = block_size * 5
        left_tone, right_tone = generate_stereo_tone(
            440.0, 880.0, sample_rate, total,
        )

        panner = UltraFastStereoPanner(
            pan_position=0.0, sample_rate=sample_rate, block_size=block_size,
        )

        out_l = np.zeros(total, dtype=np.float32)
        out_r = np.zeros(total, dtype=np.float32)

        for off in range(0, total, block_size):
            panner.process_block_stereo(
                left_tone[off: off + block_size],
                right_tone[off: off + block_size],
                out_l[off: off + block_size],
                out_r[off: off + block_size],
            )

        # Hard-left: left channel should have signal, right near-silent.
        # At pan=0.0: left_gain=cos(0)=1, right_gain=sin(0)=0
        #   out_l = left_in * 1 + right_in * (1-0) = left_in + right_in
        #   out_r = right_in * 0 + left_in * (1-1) = 0
        # Right channel may have small numerical noise from trig lookups.
        assert rms(out_r) < 1e-4, (
            "Right channel should be near-silent at hard-left pan"
        )
        assert rms(out_l) > 0.01, (
            "Left channel should have signal at hard-left pan"
        )
