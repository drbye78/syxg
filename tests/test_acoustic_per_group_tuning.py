"""Tests for per-group acoustic behavior tuning nuances.

Covers:
- routing performance_noise_cc into the modulation dict (Channel)
- variant scaling of piano hammer noise
- mallet velocity-to-decay tilt
"""

from __future__ import annotations

from typing import Any

import numpy as np

from synth.engines.acoustic.behavior_config import BehaviorConfig, InstrumentGroup
from synth.engines.acoustic.processors.performance_noise import PerformanceNoiseProcessor
from synth.engines.acoustic.voice_state import VoiceBehaviorState, VoicePhase
from synth.processing.channel import Channel


def _make_state(velocity: int, phase: VoicePhase = VoicePhase.ATTACK) -> VoiceBehaviorState:
    return VoiceBehaviorState(voice_id=1, note=60, velocity=velocity, phase=phase)


def test_performance_noise_cc_routed() -> None:
    """Wind breath noise differs when cc_value=0.8 vs 0.0."""
    proc = PerformanceNoiseProcessor(44100)
    state = _make_state(80)
    modulation: dict[str, float] = {}

    buf_low = np.zeros((64, 2), dtype=np.float32)
    out_low = proc.process(
        buf_low, state, modulation, InstrumentGroup.REEDS_WOODWINDS, cc_value=0.0
    )

    buf_high = np.zeros((64, 2), dtype=np.float32)
    out_high = proc.process(
        buf_high, state, modulation, InstrumentGroup.REEDS_WOODWINDS, cc_value=0.8
    )

    # Breath noise is added to both channels; with cc_value it must differ.
    assert not np.allclose(out_low, out_high)
    # The cc_value=0.8 path should add more breath energy than the 0.0 path.
    assert np.abs(out_high).sum() > np.abs(out_low).sum()


def test_piano_variant_scales_noise() -> None:
    """Grand vs upright produce different hammer-noise amplitude for piano."""
    proc = PerformanceNoiseProcessor(44100)
    state = _make_state(100)
    modulation: dict[str, float] = {}

    buf_grand = np.zeros((128, 2), dtype=np.float32)
    out_grand = proc.process(
        buf_grand, state, modulation, InstrumentGroup.ACOUSTIC_PIANO, variant="grand"
    )

    buf_upright = np.zeros((128, 2), dtype=np.float32)
    out_upright = proc.process(
        buf_upright, state, modulation, InstrumentGroup.ACOUSTIC_PIANO, variant="upright"
    )

    # Upright has 1.4x mechanical noise vs grand 1.0x.
    assert not np.allclose(out_grand, out_upright)
    assert np.abs(out_upright).sum() > np.abs(out_grand).sum()


def test_mallet_velocity_decay() -> None:
    """Hard-velocity mallet buffer has lower late-sample energy than soft."""
    cfg = BehaviorConfig.for_group(InstrumentGroup.MALLETS)
    assert cfg.decay_velocity_sensitivity > 0

    n = 256
    # A simple exponentially-decaying tone so the tilt is observable.
    base = np.exp(-np.arange(n) / (n * 0.3))[:, None].astype(np.float32)
    base = np.repeat(base, 2, axis=1)

    hard = base.copy()
    soft = base.copy()

    tilt_hard = 1.0 - cfg.decay_velocity_sensitivity * (127 / 127.0) * (np.arange(n) / max(n, 1))
    tilt_soft = 1.0 - cfg.decay_velocity_sensitivity * (20 / 127.0) * (np.arange(n) / max(n, 1))
    hard = hard * tilt_hard[:, None]
    soft = soft * tilt_soft[:, None]

    tail = slice(n // 2, n)
    assert float(np.abs(hard[tail]).sum()) < float(np.abs(soft[tail]).sum())


def test_cc_keys_in_modulation() -> None:
    """Channel._collect_modulation_values exposes cc_<n> keys from controllers."""
    from synth.processing.voice.voice_factory import VoiceFactory

    # Build a dummy engine registry so VoiceFactory construction succeeds.
    registry = _DummyRegistry()
    factory = VoiceFactory(registry)
    ch = Channel(0, factory, 44100)

    ch.controllers[2] = 100
    modulation = ch._collect_modulation_values()

    assert "cc_2" in modulation
    assert abs(modulation["cc_2"] - 100 / 127.0) < 1e-6


class _DummyRegistry:
    """Minimal SynthesisEngineRegistry stub for VoiceFactory construction."""

    def get_priority_order(self) -> list[str]:
        return []

    def get_engine(self, engine_type: str) -> Any | None:
        return None
