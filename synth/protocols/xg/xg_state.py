"""Unified XG State — single lock, single source of truth.

Replaces 15 independent threading.RLock() instances across the XG subsystem
with one XGState object holding all mutable protocol state under one lock.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass(slots=True)
class XGPartState:
    """Per-part XG parameter state. 16 instances in XGState.parts."""

    bank_msb: int = 0
    bank_lsb: int = 0
    program: int = 0
    volume: int = 100
    pan: int = 64
    reverb_send: int = 40
    chorus_send: int = 0
    variation_send: int = 0
    filter_cutoff: int = 64
    filter_resonance: int = 64
    eg_attack: int = 64
    eg_decay1: int = 64
    eg_decay2: int = 64
    eg_release: int = 64
    vibrato_rate: int = 64
    vibrato_depth: int = 64
    vibrato_delay: int = 64
    portamento_time: int = 0
    note_shift: int = 0
    detune: int = 0
    mono_poly_mode: int = 0
    part_mode: int = 0
    dry_level: int = 127


@dataclass(slots=True)
class XGEffectsState:
    """System-wide effects parameters."""

    reverb_type: int = 0
    reverb_time: int = 64
    reverb_return: int = 64
    chorus_type: int = 0
    chorus_lfo_freq: int = 0
    chorus_lfo_depth: int = 0
    chorus_return: int = 0
    variation_type: int = 0
    variation_return: int = 0
    insertion_type: int = 0
    insertion_return: int = 0


@dataclass(slots=True)
class XGSystemState:
    """System-level XG parameters."""

    master_volume: int = 127
    master_tune: int = 0  # cents, ±100
    master_transpose: int = 0  # semitones, ±24
    master_attenuator: int = 0
    xg_enabled: bool = False
    gs_enabled: bool = False
    gm_enabled: bool = False
    gm2_enabled: bool = False
    device_id: int = 0x10
    drum_setup_reset: int = 0


@dataclass(slots=True)
class XGDrumParams:
    """Per-note drum parameters."""

    pitch_coarse: int = 64
    pitch_fine: int = 64
    level: int = 100
    pan: int = 64
    reverb_send: int = 40
    chorus_send: int = 0
    variation_send: int = 0
    filter_cutoff: int = 64
    filter_resonance: int = 64
    eg_attack: int = 64
    eg_decay1: int = 64
    eg_decay2: int = 64
    eg_release: int = 64


@dataclass(slots=True)
class XGState:
    """Unified XG protocol state with single lock.

    Replaces 15+ independent RLocks across the XG subsystem.
    All state mutations must hold self.lock.
    """

    lock: threading.RLock = field(default_factory=threading.RLock)

    # 16 XG parts
    parts: list[XGPartState] = field(
        default_factory=lambda: [XGPartState() for _ in range(16)]
    )

    # System parameters
    system: XGSystemState = field(default_factory=XGSystemState)

    # Effects
    effects: XGEffectsState = field(default_factory=XGEffectsState)

    # Drum setup: 128 notes × per-note parameters
    drum: list[XGDrumParams] = field(
        default_factory=lambda: [XGDrumParams() for _ in range(128)]
    )

    # Controller assignments (slot → (controller, curve, range))
    controller_assignments: list[dict] = field(
        default_factory=lambda: [{} for _ in range(12)]
    )

    # Voice reserve per part
    voice_reserve: list[int] = field(
        default_factory=lambda: [128] * 16
    )

    # Channel-to-part mapping for O(1) lookup
    channel_to_part: dict[int, int] = field(default_factory=dict)
