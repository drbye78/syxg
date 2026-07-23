"""SF2 Modulator Evaluator — per-zone modulation matrix processor.

Evaluates SF2 file-sourced + default modulators against current
controller/key/velocity state, producing modulation values for each
affected generator. Designed as a standalone lightweght object owned
by SF2Region — one instance per region, updated per-block.

Architecture:
    SF2Region.note_on()
      → creates SF2ModulatorEvaluator(merged_modulators)
    SF2Region.generate_samples()
      → evaluator.evaluate(controllers, velocity, keynum)
      → returns {gen_type: modulation_value}
      → applied to pitch, filter, attenuation, vibrato, etc.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .sf2_default_modulators import (
    DEFAULT_MODULATORS,
    NONE,
    TRANSFORM_LINEAR,
    TRANSFORM_ABSOLUTE,
    TRANSFORM_BIPOLAR_TO_UNIPOLAR,
    # Destinations
    GEN_COARSE_TUNE,
    GEN_FINE_TUNE,
    GEN_INITIAL_ATTENUATION,
    GEN_INITIAL_FILTER_FC,
    GEN_INITIAL_FILTER_Q,
    GEN_VIB_LFO_TO_PITCH,
    GEN_MOD_LFO_TO_PITCH,
    GEN_MOD_LFO_TO_VOLUME,
    GEN_MOD_LFO_TO_FILTER_FC,
    GEN_PAN,
    GEN_REVERB_EFFECTS_SEND,
    GEN_CHORUS_EFFECTS_SEND,
    GEN_RELEASE_VOL_ENV,
    GEN_FREQ_MOD_LFO,
    GEN_FREQ_VIB_LFO,
    GEN_DECAY_VOL_ENV,
    GEN_SUSTAIN_VOL_ENV,
    GEN_ATTACK_VOL_ENV,
    GEN_HOLD_VOL_ENV,
    GEN_DELAY_VOL_ENV,
)


class SF2ModulatorEvaluator:
    """Evaluates SF2 modulators against current controller state.

    Stores a merged list of (default_modulators + file_modulators),
    evaluates source values, applies transforms and amounts, and
    sums per-destination modulation contributions.

    Source operator decoding:
        bits 0-6:  index (0=none, 2=velocity, 3=keynum, 4-126=CC, 128=link)
        bit 7:     bipolar flag
        bit 8:     direction (invert)
        bit 9:     type (0=linear, 1=concave)
        bits 10-14: poles (=127 for center bipolar)
        bit 15:    continuation
    """

    __slots__ = (
        "_modulators",
        "_cc_cache",
    )

    def __init__(self, zone_modulators: list[dict] | None = None) -> None:
        """Create evaluator with default + file-sourced modulators.

        File-sourced modulators override defaults for the same
        (src_operator, dest_operator) pair.
        """
        # Merge: defaults first, then overlay file modulators for the
        # same (src, dest) pair. The overlay model matches SF2 spec
        # where file modulators replace (not add to) defaults.
        merged: list[dict] = []
        seen: set[tuple[int, int]] = set()

        # File modulators take priority — add them first so they
        # shadow any matching default
        if zone_modulators:
            for mod in zone_modulators:
                key = (mod.get("src_operator", 0), mod.get("dest_operator", 0))
                seen.add(key)
                merged.append(mod)

        # Default modulators fill in gaps
        for mod in DEFAULT_MODULATORS:
            key = (mod["src_operator"], mod["dest_operator"])
            if key not in seen:
                merged.append(mod)

        self._modulators = merged

        # Per-block CC cache: dict[CC_number → normalized_value].
        # Built once per evaluate() call from the controllers dict.
        # Normalized to SF2 range: 0..127 → 0.0..1.0.
        self._cc_cache: dict[int, float] = {}

    # ── Per-block evaluation ───────────────────────────────────────────

    def evaluate(
        self,
        controllers: dict[int, float],
        velocity: int,
        keynum: int,
    ) -> dict[int, float]:
        """Evaluate all modulators against current state.

        Args:
            controllers: Dict of CC_number → value (both XG-normalized 0.0-1.0
                         and raw 0-127). The method handles normalisation.
            velocity: MIDI note-on velocity (0-127).
            keynum: MIDI note number (0-127).

        Returns:
            Dict of gen_type → modulation_value. Units match SF2 generator
            conventions (cents for pitch/filter, centibels for attenuation,
            0-1000 range for sends).
        """
        self._build_cc_cache(controllers)
        results: dict[int, float] = {}

        for mod in self._modulators:
            src = mod["src_operator"]
            dest = mod["dest_operator"]
            amount = mod.get("mod_amount", 0)
            amt_src = mod.get("amt_src_operator", 0)
            transform = mod.get("mod_trans_operator", TRANSFORM_LINEAR)

            # Decode primary source
            primary = self._decode_source(src, velocity, keynum)
            if primary is None:
                continue

            # Apply amount source (secondary modulation depth)
            if amt_src and amt_src != NONE:
                amt_val = self._decode_source(amt_src, velocity, keynum)
                if amt_val is not None:
                    amount = amount * amt_val

            # Apply transform
            transformed = self._apply_transform(primary, transform)

            # Accumulate to destination
            modulation = transformed * amount
            if dest in results:
                results[dest] += modulation
            else:
                results[dest] = modulation

        return results

    # ── Source decoding ────────────────────────────────────────────────

    def _decode_source(
        self,
        src_operator: int,
        velocity: int,
        keynum: int,
    ) -> float | None:
        """Decode an SF2 source operator bitfield into a normalised value.

        Returns:
            Normalised float (range varies by source type), or None
            if the source is NONE (index 0).
        """
        if src_operator == NONE:
            return None

        index = src_operator & 0x7F  # bits 0-6
        is_bipolar = bool(src_operator & 0x0080)
        invert = bool(src_operator & 0x0100)
        is_concave = bool(src_operator & 0x0200)

        raw = self._get_raw_source_value(index, velocity, keynum)

        # Apply concavity for Velocity source only (per SF2 spec)
        if index == 2 and is_concave and raw <= 1.0 and raw >= 0.0:
            raw = raw * raw  # Square for concave velocity curve

        # Normalise to [-1, 1] range
        if is_bipolar:
            normalised = 2.0 * raw - 1.0
        else:
            normalised = raw

        if invert:
            normalised = -normalised

        return normalised

    def _get_raw_source_value(
        self,
        index: int,
        velocity: int,
        keynum: int,
    ) -> float:
        """Get the raw unipolar [0, 1] source value from its index."""
        if index == 0:
            return 0.0
        elif index == 2:
            # Velocity — note-on velocity 0..127
            return velocity / 127.0
        elif index == 3:
            # Key number — MIDI note 0..127
            return keynum / 127.0
        elif index >= 4 and index <= 126:
            # MIDI CC controller — CC number = index * 128 + sub
            controller_num = index & 0x7F
            return self._cc_cache.get(controller_num, 0.0)
        elif index == 0x0E:
            # Pitch wheel
            return self._cc_cache.get(0x0E, 0.5)
        elif index == 0x0D:
            # Channel pressure (aftertouch)
            return self._cc_cache.get(0x0D, 0.0)
        elif index == 0x0B:
            # Poly pressure (per-note aftertouch) — not tracked per-note
            return 0.0
        elif index == 128:
            # Link — secondary source, handled by amt_src_operator
            return 0.0
        else:
            return 0.0

    def _build_cc_cache(self, controllers: dict[int, float]) -> None:
        """Build CC cache from the controllers dict.

        Handles both XG-normalised (0.0-1.0) format and raw MIDI 0-127
        values. Also caches pitch wheel and channel pressure under their
        SF2 special indices.
        """
        self._cc_cache.clear()

        for cc, val in controllers.items():
            if isinstance(val, (int, float)):
                # Normalise to 0.0-1.0
                if val > 1.0:
                    val = val / 127.0
                self._cc_cache[cc] = val

        # — pitch wheel (SF2 source index 14) —
        if isinstance(controllers.get("pitch"), (int, float)):
            pw = controllers["pitch"]
            if abs(pw) > 1.0:
                pw = (pw - 8192) / 8192.0
            self._cc_cache[0x0E] = (pw + 1.0) * 0.5  # [-1,+1] → [0,1]

        # — channel pressure (SF2 source index 13) —
        if isinstance(controllers.get("channel_aftertouch"), (int, float)):
            at = controllers["channel_aftertouch"]
            if at > 1.0:
                at = at / 127.0
            self._cc_cache[0x0D] = at
        if isinstance(controllers.get("aftertouch"), (int, float)):
            at = controllers["aftertouch"]
            if at > 1.0:
                at = at / 127.0
            self._cc_cache[0x0D] = at

    # ── Transform application ──────────────────────────────────────────

    def _apply_transform(self, value: float, transform: int) -> float:
        """Apply SF2 transform to a normalised source value.

        Transform types per SF2 spec §7.4:
            0 = linear (pass-through)
            1 = absolute value
            2 = bipolar → unipolar: (-1..+1) → (0..+1)
        """
        if transform == TRANSFORM_ABSOLUTE:
            return abs(value)
        elif transform == TRANSFORM_BIPOLAR_TO_UNIPOLAR:
            return (value + 1.0) * 0.5
        else:
            return value


# ── Generator modulation → SF2Region parameter application ────────────

def apply_modulation_to_params(
    params: dict[str, Any],
    modulation: dict[int, float],
    note: int,
) -> dict[str, Any]:
    """Apply per-generator modulation values to SF2 region parameters.

    Args:
        params: Param dict with SF2 generator values in their native units:
            initial_filter_fc (cents), initial_filter_q (centibels),
            initial_attenuation (centibels), coarse_tune (semitones),
            fine_tune (cents), pan (SF2 units), reverb_send (SF2 units),
            chorus_send (SF2 units), vib_lfo_to_pitch (cents),
            mod_lfo_to_pitch (cents), mod_lfo_to_volume (dB),
            mod_lfo_to_filter_fc (cents), release_vol_env (timecents),
            freq_mod_lfo (cents→Hz mapping), freq_vib_lfo (cents→Hz mapping).

        modulation: Gen → offset dict from SF2ModulatorEvaluator.evaluate().
            Units match SF2 generator conventions.

        note: MIDI note number for key→filter tracking calc.

    Returns:
        Modified params dict (same object, mutated in place).
    """
    # ── Filter ──
    if GEN_INITIAL_FILTER_FC in modulation:
        fc_cents = params.get("initial_filter_fc", 13500)
        params["initial_filter_fc"] = max(0, fc_cents + modulation[GEN_INITIAL_FILTER_FC])

    if GEN_INITIAL_FILTER_Q in modulation:
        q_ceb = params.get("initial_filter_q", 0)
        params["initial_filter_q"] = max(0, q_ceb + modulation[GEN_INITIAL_FILTER_Q])

    # ── Attenuation ──
    if GEN_INITIAL_ATTENUATION in modulation:
        att_ceb = params.get("initial_attenuation", 0)
        params["initial_attenuation"] = max(0, att_ceb + modulation[GEN_INITIAL_ATTENUATION])

    # ── Pitch ──
    if GEN_COARSE_TUNE in modulation:
        ct = params.get("coarse_tune", 0)
        params["coarse_tune"] = ct + int(modulation[GEN_COARSE_TUNE])

    if GEN_FINE_TUNE in modulation:
        ft = params.get("fine_tune", 0)
        params["fine_tune"] = ft + int(modulation[GEN_FINE_TUNE])

    # ── Vibrato / Mod LFO ──
    if GEN_VIB_LFO_TO_PITCH in modulation:
        vp = params.get("vib_lfo_to_pitch", 0)
        params["vib_lfo_to_pitch"] = max(0, vp + int(modulation[GEN_VIB_LFO_TO_PITCH]))

    if GEN_MOD_LFO_TO_PITCH in modulation:
        mp = params.get("mod_lfo_to_pitch", 0)
        params["mod_lfo_to_pitch"] = max(0, mp + int(modulation[GEN_MOD_LFO_TO_PITCH]))

    if GEN_MOD_LFO_TO_VOLUME in modulation:
        mv = params.get("mod_lfo_to_volume", 0)
        params["mod_lfo_to_volume"] = mv + modulation[GEN_MOD_LFO_TO_VOLUME]

    if GEN_MOD_LFO_TO_FILTER_FC in modulation:
        mlf = params.get("mod_lfo_to_filter_fc", 0)
        params["mod_lfo_to_filter_fc"] = mlf + int(modulation[GEN_MOD_LFO_TO_FILTER_FC])

    # ── Pan ──
    if GEN_PAN in modulation:
        pan_val = params.get("pan", 0)
        params["pan"] = max(-500, min(500, pan_val + int(modulation[GEN_PAN])))

    # ── Effect sends ──
    if GEN_REVERB_EFFECTS_SEND in modulation:
        rv = params.get("reverb_effects_send", 0)
        params["reverb_effects_send"] = max(0, min(1000, rv + int(modulation[GEN_REVERB_EFFECTS_SEND])))

    if GEN_CHORUS_EFFECTS_SEND in modulation:
        ch = params.get("chorus_effects_send", 0)
        params["chorus_effects_send"] = max(0, min(1000, ch + int(modulation[GEN_CHORUS_EFFECTS_SEND])))

    # ── Release override (sustain pedal) ──
    if GEN_RELEASE_VOL_ENV in modulation:
        rel = params.get("release_vol_env", 0)
        # SF2 uses timecents. Negative values = faster release.
        params["release_vol_env"] = max(-12000, min(rel, rel + int(modulation[GEN_RELEASE_VOL_ENV])))

    # ── LFO Frequencies ──
    if GEN_FREQ_MOD_LFO in modulation:
        fml = params.get("freq_mod_lfo", 0)
        params["freq_mod_lfo"] = max(0, fml + int(modulation[GEN_FREQ_MOD_LFO]))

    if GEN_FREQ_VIB_LFO in modulation:
        fvl = params.get("freq_vib_lfo", 0)
        params["freq_vib_lfo"] = max(0, fvl + int(modulation[GEN_FREQ_VIB_LFO]))

    return params
