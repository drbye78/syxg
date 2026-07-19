"""Acoustic behavior wrapper region (SuperNATURAL-Acoustic alike).

Wraps ANY base IRegion (SF2/SFZ sampler) and adds MIDI-driven single-note
AND cross-note (multi-voice) dynamics, reusing the S.Art2 modifier set.

Pipeline per block (on the stereo ``(block_size, 2)`` buffer):

    base.generate_samples()            # raw sampler output
      -> velocity_timbre               # [A] single-note brightness/body
      -> sart_bridge.apply(articulation)  # reuse S.Art2 per-channel
      -> performance_noise             # [A] key-off / hammer / breath
      -> sympathetic_resonance         # [B] shared bus fed by all voices
      -> damper_resonance              # [B] pedal-up coupling
      -> ensemble_detune               # [B] inter-voice detune + vibrato

The wrapper is stateless w.r.t. cross-note data: it reads the shared
``ChannelAcousticContext`` (owned by the Channel) and its own
``VoiceBehaviorState`` (set at note-on).
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from ...processing.partial.region import IRegion, RegionState
from .behavior_config import BehaviorConfig, InstrumentGroup
from .channel_context import ChannelAcousticContext
from .sart_bridge import SArt2Bridge
from .voice_state import VoiceBehaviorState

logger = logging.getLogger(__name__)


class AcousticBehaviorRegion(IRegion):
    """Wraps a base sampler region with acoustic behavior modeling."""

    __slots__ = [
        "_bridge",
        "_dsp",
        "_state",
        "base_region",
        "config",
        "context",
        "group",
    ]

    def __init__(
        self,
        base_region: IRegion,
        context: ChannelAcousticContext,
        group: InstrumentGroup = InstrumentGroup.ACOUSTIC_PIANO,
        config: BehaviorConfig | None = None,
        sample_rate: int = 44100,
    ):
        super().__init__(descriptor=base_region.descriptor, sample_rate=sample_rate)
        self.base_region = base_region
        self.context = context
        self.group = group
        self.config = config or context.config
        self._bridge = SArt2Bridge(sample_rate)
        self._state: VoiceBehaviorState | None = None
        self._dsp: dict[str, Any] = {}

    # ========== ATTRIBUTE DELEGATION ==========
    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attribute access to the wrapped base region.

        This keeps the wrapper transparent to callers that read base-region
        attributes directly (e.g. ``Channel.note_on`` reading ``_exclusive_class``
        for SF2 exclusive-class voice stealing). ``__getattr__`` only fires for
        names not found on the wrapper itself, so declared slots and methods are
        unaffected.
        """
        return getattr(self.base_region, name)

    # ========== LIFECYCLE (delegate to base) ==========
    def _load_sample_data(self) -> np.ndarray | None:
        loader = getattr(self.base_region, "_load_sample_data", None)
        if loader is not None:
            result = loader()
            return result if isinstance(result, np.ndarray) else None
        return None

    def _create_partial(self) -> Any | None:
        creator = getattr(self.base_region, "_create_partial", None)
        if creator is not None:
            return creator()
        return None

    def _init_envelopes(self) -> None:
        initializer = getattr(self.base_region, "_init_envelopes", None)
        if initializer is not None:
            initializer()

    def _init_filters(self) -> None:
        initializer = getattr(self.base_region, "_init_filters", None)
        if initializer is not None:
            initializer()

    # ========== NOTE ON / OFF ==========
    def note_on(self, velocity: int, note: int) -> bool:
        # Classify from shared context FIRST so behavior state is always set,
        # independent of whether the base region accepts the note.
        phrase = self.context.get_phrase_state()
        detune = self.context.claim_detune_offset(id(self))
        self._state = VoiceBehaviorState(voice_id=id(self), note=note, velocity=velocity)
        self._state.classify(phrase, detune_offset=detune, legato=self.config.legato_enabled)

        ok = self.base_region.note_on(velocity, note)
        if not ok:
            # Base declined (e.g. out of range); still keep behavior state for
            # cross-note context but report failure.
            return False
        self.state = RegionState.ACTIVE
        self.current_note = note
        self.current_velocity = velocity
        return True

    def note_off(self) -> None:
        self.base_region.note_off()
        if self._state is not None:
            self._state.note_off()
        self.context.release_detune_offset(id(self))
        self.state = RegionState.RELEASING

    # ========== DSP LAZY LOADING ==========
    def _get_dsp(self, name: str) -> Any:
        if name not in self._dsp:
            if name == "velocity_timbre":
                from .processors.velocity_timbre import VelocityTimbreProcessor

                self._dsp[name] = VelocityTimbreProcessor(self.sample_rate)
            elif name == "performance_noise":
                from .processors.performance_noise import PerformanceNoiseProcessor

                self._dsp[name] = PerformanceNoiseProcessor(self.sample_rate)
            elif name == "saturation":
                from .processors.saturation import SaturationProcessor

                self._dsp[name] = SaturationProcessor(self.sample_rate)
            elif name == "legato":
                from .processors.legato import LegatoProcessor

                self._dsp[name] = LegatoProcessor(self.sample_rate)
            elif name == "ensemble_detune":
                from .processors.ensemble_detune import EnsembleDetuneProcessor

                self._dsp[name] = EnsembleDetuneProcessor(self.sample_rate)
        return self._dsp[name]

    # ========== SAMPLE GENERATION ==========
    def generate_samples(self, block_size: int, modulation: dict[str, float]) -> np.ndarray:
        # 1. Base sampler output
        buf = self.base_region.generate_samples(block_size, modulation)
        if buf is None or buf.shape[0] == 0:
            return self._get_silence(block_size)

        cfg = self.config
        state = self._state

        # 2. [A] Single-note velocity timbre (brightness/body from velocity)
        if cfg.velocity_to_brightness and state is not None:
            vt = self._get_dsp("velocity_timbre")
            buf = vt.process(buf, state.velocity, self.group)

        # 3. Reuse S.Art2 articulation per-channel (stereo-safe)
        articulation = str(modulation.get("articulation", "normal"))
        if articulation not in ("normal", ""):
            art_params = modulation.get("articulation_params")
            art_params = art_params if isinstance(art_params, dict) else None
            buf = self._bridge.apply(buf, articulation, params=art_params)

        # 3b. [A] Mallet velocity-to-decay tilt (harder hits decay faster)
        if (
            cfg.decay_velocity_sensitivity > 0
            and self.group == InstrumentGroup.MALLETS
            and state is not None
        ):
            n = buf.shape[0]
            tilt = 1.0 - cfg.decay_velocity_sensitivity * (state.velocity / 127.0) * (
                np.arange(n) / max(n, 1)
            )
            buf = buf * tilt[:, None]

        # 4. [A] Performance noise (key-off / hammer / breath)
        if cfg.key_off_noise and state is not None:
            pn = self._get_dsp("performance_noise")
            pn_cc = cfg.performance_noise_cc
            cc_val = modulation.get(f"cc_{pn_cc}", 0.0) if pn_cc is not None else 0.0
            buf = pn.process(
                buf, state, modulation, self.group, cc_value=cc_val, variant=cfg.variant
            )

        # 5. [B] Shared sympathetic resonance bus (fed by ALL voices)
        if cfg.sympathetic_resonance:
            bank = self.context.get_resonance_bank()
            bank.feed(buf, state.note if state else 60)
            buf = bank.mix(buf, amount=self.context.resonance_amount)

        # 6. [B] Damper resonance (pedal-up coupling)
        if cfg.damper_resonance and not self.context.sustain_pedal:
            damper = self.context.get_damper()
            buf = damper.process(buf, note=state.note if state else 60)

        # 7. [B] Ensemble detune + shared vibrato
        if cfg.ensemble_detune and state is not None:
            ed = self._get_dsp("ensemble_detune")
            buf = ed.process(
                buf,
                detune_cents=state.detune_offset_cents,
                vibrato_phase=self.context.shared_vibrato_phase(),
                group=self.group,
            )

        # 8. Saturation (gentle, optional — not in config, default off)
        if getattr(cfg, "saturation_enabled", False):
            sat = self._get_dsp("saturation")
            buf = sat.process(buf, drive=getattr(cfg, "saturation_drive", 0.15))

        return buf.astype(np.float32, copy=False)

    # ========== DELEGATED STATE ==========
    def is_active(self) -> bool:
        return self.base_region.is_active()

    def reset(self) -> None:
        self.base_region.reset()
        self._state = None
        self.state = RegionState.CREATED

    def dispose(self) -> None:
        self.base_region.dispose()
        self._dsp.clear()
        self.state = RegionState.RELEASED

    def update_modulation(self, modulation: dict[str, float]) -> None:
        self.base_region.update_modulation(modulation)
        # Advance shared vibrato phase for ensemble
        rate = modulation.get("vibrato_rate", self.config.ensemble.vibrato_rate_hz)
        self.context.advance_vibrato(rate, self.block_size)
