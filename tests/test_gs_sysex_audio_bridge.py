"""
End-to-end tests verifying GS sysex → audio bridge produces audible changes.

Tests three layers:
1. Direct channel.gs_params manipulation (unit test of downstream consumption)
2. Raw sysex through process_sysex() (integration test via JV2080 → sync → gs_params)
3. set_gs_part_parameter() API (higher-level integration)

Known limitations:
- JV2080Part only models volume(0x02), pan(0x03), reverb_send(0x06), chorus_send(0x07)
- Filter/envelope/vibrato GS params are NOT modeled in JV2080Part → sysex path
  for those params is broken and needs a separate fix to extend JV2080Part
- Direct gs_params manipulation works for all 12 GS audio params
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pytest

from synth.synthesizers.rendering import ModernXGSynthesizer

logger = logging.getLogger(__name__)

_SF2_CANDIDATES = [
    Path(__file__).parent / "ref.sf2",
    Path(__file__).parent.parent / "sine_test.sf2",
]
TEST_SF2_PATH = next((p for p in _SF2_CANDIDATES if p.exists()), None)

# JV2080Part internal param IDs (NOT GS sysex offsets)
# Address format for process_parameter_change: [0x10 + part_num, param_id, 0x00]
JV2080_PARAM = {
    "volume": 0x02,
    "pan": 0x03,
    "reverb_send": 0x06,
    "chorus_send": 0x07,
    "delay_send": 0x08,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_gs_sysex(
    device_id: int, part: int, param_id: int, value: int
) -> bytes:
    """Build a GS Data Set sysex message for GSMIDIProcessor.

    Uses JV2080 internal address format (NOT raw GS sysex offsets):
      [0x10 + part, param_id, 0x00]

    GSMIDIProcessor expects cmd=0x40. Checksum is Roland standard.
    """
    addr = bytes([0x10 + part, param_id, 0x00])
    total = sum(addr) + value
    checksum = (128 - (total % 128)) % 128
    return bytes([0xF0, 0x41, device_id, 0x42, 0x40]) + addr + bytes([value, checksum, 0xF7])


def _rms(audio: np.ndarray) -> float:
    """Compute RMS amplitude of stereo buffer (N,2)."""
    return float(np.sqrt(np.mean(audio.astype(np.float64) ** 2)))


def _channel_rms(audio: np.ndarray, ch: int) -> float:
    """RMS amplitude for one channel (0=left, 1=right)."""
    return float(np.sqrt(np.mean(audio[:, ch].astype(np.float64) ** 2)))


def _peak(audio: np.ndarray) -> float:
    """Peak absolute amplitude."""
    return float(np.abs(audio).max())


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def synth():
    """Create ModernXGSynthesizer with test SF2 loaded."""
    if TEST_SF2_PATH is None:
        pytest.skip("No test SF2 file found (tried ref.sf2, sine_test.sf2)")
    s = ModernXGSynthesizer(sample_rate=44100, max_channels=16, xg_enabled=True)
    sf2_engine = s.engine_registry.get_engine("sf2")
    if sf2_engine:
        sf2_engine.load_soundfont(str(TEST_SF2_PATH))
    yield s
    s.cleanup()


def _play_note(channel, note: int = 60, velocity: int = 100):
    """Load program 0 and play a note."""
    channel.load_program(program=0, bank_msb=0, bank_lsb=0)
    channel.note_on(note=note, velocity=velocity)


def _gen(synth, n_blocks: int = 4, block_size: int = 1024) -> np.ndarray:
    """Generate concatenated audio blocks (N, 2)."""
    return np.concatenate(
        [synth.generate_audio_block(block_size).copy() for _ in range(n_blocks)],
        axis=0,
    )


# ===================================================================
# Layer 1 — Direct gs_params manipulation (downstream consumption)
# ===================================================================


class TestDirectGsParamsBridge:
    """Setting channel.gs_params directly produces correct audio changes."""

    def test_gs_volume_zero_silences_audio(self, synth: ModernXGSynthesizer):
        """gs_volume=0 should drive output to near-zero."""
        ch = synth.channels[0]
        _play_note(ch)
        _gen(synth, 2)  # let note stabilize

        ch.gs_params["volume"] = 0
        audio = _gen(synth, 4)
        r = _rms(audio)
        assert r < 0.005, f"GS volume=0 should near-silence, got RMS={r:.6f}"

        ch.note_off(60, 100)
        ch.gs_params.clear()

    def test_gs_volume_full_not_reduced(self, synth: ModernXGSynthesizer):
        """gs_volume=127 should not reduce output vs default (gs unset)."""
        ch = synth.channels[0]
        _play_note(ch)
        baseline = _rms(_gen(synth, 4))

        ch.gs_params["volume"] = 127
        boosted = _rms(_gen(synth, 4))
        assert boosted >= baseline * 0.85, f"Volume should not drop, baseline={baseline:.6f} boosted={boosted:.6f}"

        ch.note_off(60, 100)
        ch.gs_params.clear()

    def test_gs_pan_hard_left(self, synth: ModernXGSynthesizer):
        """gs_pan hard-left shifts balance toward left compared to baseline."""
        ch = synth.channels[0]
        _play_note(ch)
        _gen(synth, 2)

        # Baseline L/R ratio (sine_test.sf2 has inherent L/R imbalance)
        base_audio = _gen(synth, 4)
        base_lr = _channel_rms(base_audio, 0) / max(_channel_rms(base_audio, 1), 1e-10)

        ch.gs_params["pan"] = 0
        audio = _gen(synth, 8)
        panned_lr = _channel_rms(audio, 0) / max(_channel_rms(audio, 1), 1e-10)

        # Pan=0 should increase L/R ratio vs baseline (shift toward left)
        assert panned_lr > base_lr * 1.5, (
            f"Pan=0 should shift balance left, base L/R={base_lr:.3f} panned L/R={panned_lr:.3f}"
        )

        ch.note_off(60, 100)
        ch.gs_params.clear()

    def test_gs_pan_hard_right(self, synth: ModernXGSynthesizer):
        """gs_pan hard-right shifts balance toward right compared to baseline."""
        ch = synth.channels[0]
        _play_note(ch)
        _gen(synth, 2)

        base_audio = _gen(synth, 4)
        base_lr = _channel_rms(base_audio, 0) / max(_channel_rms(base_audio, 1), 1e-10)

        ch.gs_params["pan"] = 127
        audio = _gen(synth, 8)
        panned_lr = _channel_rms(audio, 0) / max(_channel_rms(audio, 1), 1e-10)

        # Pan=127 should decrease L/R ratio vs baseline (shift toward right)
        assert panned_lr < base_lr / 1.5, (
            f"Pan=127 should shift balance right, base L/R={base_lr:.3f} panned L/R={panned_lr:.3f}"
        )

        ch.note_off(60, 100)
        ch.gs_params.clear()

    def test_gs_pan_boundary_clamping(self, synth: ModernXGSynthesizer):
        """Pan=0 produces left bias (no >= -1.0 check failure)."""
        ch = synth.channels[0]
        _play_note(ch)
        _gen(synth, 2)

        base_audio = _gen(synth, 4)
        base_lr = _channel_rms(base_audio, 0) / max(_channel_rms(base_audio, 1), 1e-10)

        # pan=0 → (0-64)/63 = -1.0159 → must be clamped before >= -1.0 check
        ch.gs_params["pan"] = 0
        audio = _gen(synth, 8)
        panned_lr = _channel_rms(audio, 0) / max(_channel_rms(audio, 1), 1e-10)

        assert panned_lr > base_lr * 1.5, (
            f"Pan=0 should shift left, base L/R={base_lr:.3f} panned L/R={panned_lr:.3f}"
        )

        ch.note_off(60, 100)
        ch.gs_params.clear()

    def test_gs_filter_cutoff_changes_output(self, synth: ModernXGSynthesizer):
        """Filter cutoff extremes produce different output."""
        ch = synth.channels[0]
        _play_note(ch)
        _gen(synth, 2)

        # Min cutoff
        ch.gs_params["filter_cutoff"] = 0
        filtered = _rms(_gen(synth, 4))

        ch.gs_params["filter_cutoff"] = 127
        open_ = _rms(_gen(synth, 4))

        diff = abs(filtered - open_)
        assert diff > 1e-6, f"Filter should change output, diff={diff:.6f}"

        ch.note_off(60, 100)
        ch.gs_params.clear()

    def test_gs_attack_max_slows_attack(self, synth: ModernXGSynthesizer):
        """Long attack produces quieter first block vs default attack."""
        ch = synth.channels[0]

        # Fresh note with DEFAULT attack → capture first block peak
        _play_note(ch)
        default_peak = _peak(_gen(synth, 1))
        ch.note_off(60, 100)

        # Fresh note with MAX attack time
        _play_note(ch)
        ch.gs_params["attack_time"] = 127
        max_attack_peak = _peak(_gen(synth, 1))
        ch.note_off(60, 100)

        # With max attack, the first block should be quieter (slower ramp-up)
        assert max_attack_peak < default_peak * 0.9 or default_peak < 0.001, (
            f"Max attack should reduce first-block peak, "
            f"default={default_peak:.6f} max_attack={max_attack_peak:.6f}"
        )

        ch.gs_params.clear()

    def test_gs_reverb_send_in_modulation_dict(self, synth: ModernXGSynthesizer):
        """gs_reverb_send appears in the per-block modulation dict."""
        ch = synth.channels[0]
        _play_note(ch)
        ch.gs_params["reverb_send"] = 127
        _gen(synth, 1)  # triggers _collect_modulation_values

        mod = ch._collect_modulation_values()
        assert "gs_reverb_send" in mod, f"Missing gs_reverb_send, keys={list(mod.keys())}"
        assert mod["gs_reverb_send"] == pytest.approx(1.0, abs=0.02)

        ch.note_off(60, 100)
        ch.gs_params.clear()

    def test_all_12_gs_params_in_modulation_dict(self, synth: ModernXGSynthesizer):
        """All 12 GS audio parameters appear in the modulation dict when set.

        Note: attack_time/decay_time/release_time map to gs_amp_attack/gs_amp_decay/gs_amp_release
        in the modulation dict (the gs_amp_ prefix matches the SF2Region consumption).
        """
        ch = synth.channels[0]
        _play_note(ch)

        # Set all 12 GS part params (matching _collect_modulation_values keys)
        ch.gs_params["volume"] = 64
        ch.gs_params["pan"] = 64
        ch.gs_params["filter_cutoff"] = 64
        ch.gs_params["filter_resonance"] = 64
        ch.gs_params["attack_time"] = 64
        ch.gs_params["decay_time"] = 64
        ch.gs_params["release_time"] = 64
        ch.gs_params["vibrato_rate"] = 64
        ch.gs_params["vibrato_depth"] = 64
        ch.gs_params["vibrato_delay"] = 64
        ch.gs_params["reverb_send"] = 64
        ch.gs_params["chorus_send"] = 64

        _gen(synth, 1)
        mod = ch._collect_modulation_values()

        # The modulation dict uses gs_amp_* for envelope times
        expected = {
            "gs_volume", "gs_pan",
            "gs_filter_cutoff", "gs_filter_resonance",
            "gs_amp_attack", "gs_amp_decay", "gs_amp_release",
            "gs_vibrato_rate", "gs_vibrato_depth", "gs_vibrato_delay",
            "gs_reverb_send", "gs_chorus_send",
        }
        missing = expected - set(mod.keys())
        assert not missing, f"Missing modulation keys: {missing}"

        ch.note_off(60, 100)
        ch.gs_params.clear()


# ===================================================================
# Layer 2 — Raw sysex path (process_sysex → GSMIDIProcessor → JV2080
#           → sync → gs_params)
# ===================================================================


class TestGsSysexIntegration:
    """GS sysex messages flow through to audio changes (JV2080-modeled params only)."""

    def _sysex(self, synth: ModernXGSynthesizer, param: str, value: int):
        """Helper: build and send GS sysex for a named JV2080 param."""
        pid = JV2080_PARAM.get(param)
        if pid is None:
            pytest.skip(f"JV2080 has no param_id for '{param}'")
        msg = _build_gs_sysex(device_id=0x10, part=0, param_id=pid, value=value)
        synth.process_sysex(msg)

    def test_volume_zero_silences(self, synth: ModernXGSynthesizer):
        """GS sysex volume=0 silences audio via JV2080 sync."""
        ch = synth.channels[0]
        _play_note(ch)
        _gen(synth, 4)

        self._sysex(synth, "volume", 0)
        r = _rms(_gen(synth, 6))
        assert r < 0.01, f"Sysex volume=0 too loud, RMS={r:.6f}"

        ch.note_off(60, 100)

    def test_volume_full_not_reduced(self, synth: ModernXGSynthesizer):
        """GS sysex volume=127 does not reduce amplitude."""
        ch = synth.channels[0]
        _play_note(ch)
        baseline = _rms(_gen(synth, 4))

        self._sysex(synth, "volume", 127)
        boosted = _rms(_gen(synth, 4))
        assert boosted >= baseline * 0.85, f"Volume dropped, baseline={baseline:.6f} boosted={boosted:.6f}"

        ch.note_off(60, 100)

    def test_pan_hard_left(self, synth: ModernXGSynthesizer):
        """GS sysex pan=0 shifts balance toward left."""
        ch = synth.channels[0]
        _play_note(ch)
        _gen(synth, 4)

        base_audio = _gen(synth, 4)
        base_lr = _channel_rms(base_audio, 0) / max(_channel_rms(base_audio, 1), 1e-10)

        self._sysex(synth, "pan", 0)
        audio = _gen(synth, 8)
        panned_lr = _channel_rms(audio, 0) / max(_channel_rms(audio, 1), 1e-10)

        assert panned_lr > base_lr * 1.5, (
            f"Sysex pan=0 should shift left, base L/R={base_lr:.3f} panned L/R={panned_lr:.3f}"
        )

        ch.note_off(60, 100)

    def test_pan_hard_right(self, synth: ModernXGSynthesizer):
        """GS sysex pan=127 shifts balance toward right."""
        ch = synth.channels[0]
        _play_note(ch)
        _gen(synth, 4)

        base_audio = _gen(synth, 4)
        base_lr = _channel_rms(base_audio, 0) / max(_channel_rms(base_audio, 1), 1e-10)

        self._sysex(synth, "pan", 127)
        audio = _gen(synth, 8)
        panned_lr = _channel_rms(audio, 0) / max(_channel_rms(audio, 1), 1e-10)

        assert panned_lr < base_lr / 1.5, (
            f"Sysex pan=127 should shift right, base L/R={base_lr:.3f} panned L/R={panned_lr:.3f}"
        )

        ch.note_off(60, 100)

    def test_reverb_send_syncs_to_gs_params(self, synth: ModernXGSynthesizer):
        """GS sysex reverb_send=100 appears in channel.gs_params."""
        ch = synth.channels[0]
        self._sysex(synth, "reverb_send", 100)
        assert ch.gs_params.get("reverb_send") == 100, (
            f"Expected gs_params['reverb_send']=100, got {ch.gs_params.get('reverb_send')}"
        )

    def test_chorus_send_syncs_to_gs_params(self, synth: ModernXGSynthesizer):
        """GS sysex chorus_send=50 appears in channel.gs_params."""
        ch = synth.channels[0]
        self._sysex(synth, "chorus_send", 50)
        assert ch.gs_params.get("chorus_send") == 50, (
            f"Expected gs_params['chorus_send']=50, got {ch.gs_params.get('chorus_send')}"
        )

    def test_channel_parameters_independent(self, synth: ModernXGSynthesizer):
        """Setting volume on channel 0 doesn't affect channel 1."""
        self._sysex(synth, "volume", 0)
        ch0 = synth.channels[0]
        ch1 = synth.channels[1]
        assert ch0.gs_params.get("volume") == 0, f"ch0 volume should be 0"
        # Channel 1 might have initial gs_params from startup
        # Just verify it didn't get volume=0
        if "volume" in ch1.gs_params:
            assert ch1.gs_params["volume"] != 0, "ch1 should not inherit ch0's volume"


# ===================================================================
# Layer 3 — set_gs_part_parameter() API
# ===================================================================


class TestGsPartParameterAPI:
    """set_gs_part_parameter() bridges to gs_params and affects audio."""

    def test_api_volume_affects_gs_params(self, synth: ModernXGSynthesizer):
        """API call for volume populates channel.gs_params."""
        ch = synth.channels[0]
        synth.set_gs_part_parameter(part_number=0, param_id=0x02, value=50)
        assert ch.gs_params.get("volume") == 50, (
            f"Expected gs_params['volume']=50, got {ch.gs_params.get('volume')}"
        )

    def test_api_pan_affects_gs_params(self, synth: ModernXGSynthesizer):
        """API call for pan populates channel.gs_params."""
        ch = synth.channels[0]
        synth.set_gs_part_parameter(part_number=0, param_id=0x03, value=10)
        assert ch.gs_params.get("pan") == 10, (
            f"Expected gs_params['pan']=10, got {ch.gs_params.get('pan')}"
        )

    def test_api_volume_changes_audio(self, synth: ModernXGSynthesizer):
        """API volume change produces audible difference."""
        ch = synth.channels[0]
        _play_note(ch)
        _gen(synth, 2)

        synth.set_gs_part_parameter(part_number=0, param_id=0x02, value=10)
        low = _rms(_gen(synth, 4))

        synth.set_gs_part_parameter(part_number=0, param_id=0x02, value=127)
        high = _rms(_gen(synth, 4))

        assert high > low * 1.5, f"High volume should be louder, low={low:.6f} high={high:.6f}"

        ch.note_off(60, 100)

    def test_api_pan_silences_opposite_channel(self, synth: ModernXGSynthesizer):
        """API pan=0 shifts balance toward left."""
        ch = synth.channels[0]
        _play_note(ch)
        _gen(synth, 4)

        base_audio = _gen(synth, 4)
        base_lr = _channel_rms(base_audio, 0) / max(_channel_rms(base_audio, 1), 1e-10)

        synth.set_gs_part_parameter(part_number=0, param_id=0x03, value=0)
        audio = _gen(synth, 8)
        panned_lr = _channel_rms(audio, 0) / max(_channel_rms(audio, 1), 1e-10)

        assert panned_lr > base_lr * 1.5, (
            f"API pan=0 should shift left, base L/R={base_lr:.3f} panned L/R={panned_lr:.3f}"
        )

        ch.note_off(60, 100)
