"""
XGML Parser — unified YAML → XGMLConfig with validation and defaults.

Accepts both v3 and v2/v1 formats; produces typed XGMLConfig dataclass.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .errors import ParseError, SchemaValidationError, UnsupportedVersionError
from .schema import XGML_SCHEMA
from .types import (
    AmpEnvelope,
    BasicMessages,
    ChannelConfig,
    ChannelSetup,
    ChorusConfig,
    DrumConfig,
    DrumNoteParams,
    EffectSends,
    EffectsConfig,
    EQConfig,
    FilterParams,
    GSChorusConfig,
    GSConfig,
    GSDrumPartConfig,
    GSEffectsConfig,
    GSPartConfig,
    GSReverbConfig,
    GSSystemConfig,
    InsertionSlot,
    JupiterXArpConfig,
    JupiterXConfig,
    JupiterXEngineConfig,
    JupiterXPartConfig,
    JupiterXPartEnvelope,
    JupiterXPartLFO,
    JupiterXPartModulation,
    JupiterXSystemConfig,
    JupiterXVCMConfig,
    LFOParams,
    Meta,
    ControlEvent,
    NRPNEvent,
    NoteEvent,
    PitchParams,
    ReverbConfig,
    ScaleTuning,
    Sequence,
    SequenceEvent,
    SynthesizerCore,
    SystemExclusive,
    Track,
    VariationConfig,
    XGMLConfig,
)

logger = logging.getLogger(__name__)

_SUPPORTED_VERSIONS = {"1.0", "2.0", "2.1", "3.0"}


def _signed(val: Any) -> int | None:
    """Return None if val is None, otherwise return int(val) — no offset applied."""
    if val is None:
        return None
    return int(val)


def _parse_version(version_str: str) -> tuple[int, int]:
    """Parse '3.0' → (3, 0). Raises UnsupportedVersionError."""
    try:
        parts = version_str.strip().split(".")
        return (int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        raise UnsupportedVersionError(f"Invalid version format: {version_str!r}")


# ---------------------------------------------------------------------------
# Section-level parsers
# ---------------------------------------------------------------------------


def _parse_meta(data: dict[str, Any]) -> Meta | None:
    if not data:
        return None
    return Meta(
        description=data.get("description"),
        author=data.get("author"),
        created=data.get("created"),
        modified=data.get("modified"),
        tags=data.get("tags"),
        source=data.get("source"),
        custom={k: v for k, v in data.items() if k not in ("description", "author", "created", "modified", "tags", "source")} or None,
    )


def _parse_channel_setup(data: dict[str, Any]) -> ChannelSetup:
    return ChannelSetup(
        program=data.get("program"),
        volume=data.get("volume"),
        pan=data.get("pan"),
        expression=data.get("expression"),
        reverb_send=data.get("reverb_send"),
        chorus_send=data.get("chorus_send"),
        variation_send=data.get("variation_send"),
        pitch_bend_range=data.get("pitch_bend_range"),
        master_tune=data.get("master_tune"),
        fine_tune=data.get("fine_tune"),
        coarse_tune=data.get("coarse_tune"),
        bank_msb=data.get("bank_msb"),
        bank_lsb=data.get("bank_lsb"),
        portamento_time=data.get("portamento_time"),
        portamento=data.get("portamento"),
        sostenuto=data.get("sostenuto"),
        soft_pedal=data.get("soft_pedal"),
        hold=data.get("hold"),
        part_mode=data.get("part_mode"),
        voice_reserve=data.get("voice_reserve"),
        port=int(data.get("port", 0)),
    )


def _parse_basic_messages(section: dict[str, Any]) -> BasicMessages | None:
    if not section:
        return None
    channels_data = section.get("channels")
    if not isinstance(channels_data, dict):
        return None
    channels: dict[int, ChannelSetup] = {}
    for ch_str, setup in channels_data.items():
        try:
            ch = int(ch_str)
        except (ValueError, TypeError):
            continue
        if isinstance(setup, dict):
            channels[ch] = _parse_channel_setup(setup)
    return BasicMessages(channels=channels) if channels else None


def _parse_filter_params(data: dict[str, Any]) -> FilterParams | None:
    if not data:
        return None
    return FilterParams(
        cutoff=data.get("cutoff"),
        resonance=data.get("resonance"),
        type=data.get("type"),
        envelope_attack=data.get("envelope_attack"),
        envelope_decay=data.get("envelope_decay"),
        envelope_sustain=data.get("envelope_sustain"),
        envelope_release=data.get("envelope_release"),
        envelope_depth=data.get("envelope_depth"),
        velocity_sensitivity=data.get("velocity_sensitivity"),
        key_scaling=data.get("key_scaling"),
    )


def _parse_lfo_params(data: dict[str, Any]) -> LFOParams | None:
    if not data:
        return None
    return LFOParams(
        waveform=data.get("waveform"),
        speed=data.get("speed"),
        delay=data.get("delay"),
        fade=data.get("fade"),
        pitch_depth=data.get("pitch_depth"),
        filter_depth=data.get("filter_depth"),
        amp_depth=data.get("amp_depth"),
        key_sync=data.get("key_sync"),
    )


def _parse_amp_envelope(data: dict[str, Any]) -> AmpEnvelope | None:
    if not data:
        return None
    return AmpEnvelope(
        attack=data.get("attack"),
        decay=data.get("decay"),
        sustain=data.get("sustain"),
        release=data.get("release"),
        velocity_sensitivity=data.get("velocity_sensitivity"),
        key_scaling=data.get("key_scaling"),
    )


def _parse_pitch_params(data: dict[str, Any]) -> PitchParams | None:
    if not data:
        return None
    return PitchParams(
        coarse=data.get("coarse"),
        fine=data.get("fine"),
        random=data.get("random"),
        key_scaling=data.get("key_scaling"),
        envelope_attack=data.get("envelope_attack"),
        envelope_decay=data.get("envelope_decay"),
        envelope_depth=data.get("envelope_depth"),
    )


def _parse_effect_sends(data: dict[str, Any]) -> EffectSends | None:
    if not data:
        return None
    return EffectSends(
        reverb=data.get("reverb"),
        chorus=data.get("chorus"),
        variation=data.get("variation"),
        dry_level=data.get("dry_level"),
        insertion_l=data.get("insertion_l"),
        insertion_r=data.get("insertion_r"),
    )


def _parse_channel_config(ch: int, data: dict[str, Any]) -> ChannelConfig | None:
    if not data:
        return None

    lfo_data = data.get("lfo")
    lfos: dict[str, LFOParams] | None = None
    if isinstance(lfo_data, dict):
        parsed = {}
        for key, val in lfo_data.items():
            if isinstance(val, dict):
                p = _parse_lfo_params(val)
                if p is not None:
                    parsed[key] = p
        if parsed:
            lfos = parsed

    return ChannelConfig(
        filter=_parse_filter_params(data.get("filter")),
        lfo=lfos,
        amp_envelope=_parse_amp_envelope(data.get("amp_envelope")),
        pitch=_parse_pitch_params(data.get("pitch")),
        effects_sends=_parse_effect_sends(data.get("effects_sends")),
        element_reserve=data.get("element_reserve"),
        velocity_response=data.get("velocity_response"),
        velocity_offset=data.get("velocity_offset"),
        velocity_range_low=data.get("velocity_range_low"),
        velocity_range_high=data.get("velocity_range_high"),
        note_shift=data.get("note_shift"),
        mono_poly=data.get("mono_poly"),
        legato=data.get("legato"),
    )


def _parse_channel_parameters(section: dict[str, Any]) -> dict[int, ChannelConfig] | None:
    if not section:
        return None
    result: dict[int, ChannelConfig] = {}
    for ch_str, data in section.items():
        try:
            ch = int(ch_str)
        except (ValueError, TypeError):
            continue
        if isinstance(data, dict):
            cfg = _parse_channel_config(ch, data)
            if cfg is not None:
                result[ch] = cfg
    return result if result else None


def _parse_drum_note_params(data: dict[str, Any]) -> DrumNoteParams:
    return DrumNoteParams(
        pitch_coarse=data.get("pitch_coarse"),
        pitch_fine=data.get("pitch_fine"),
        level=data.get("level"),
        pan=data.get("pan"),
        reverb_send=data.get("reverb_send"),
        chorus_send=data.get("chorus_send"),
        variation_send=data.get("variation_send"),
        filter_cutoff=data.get("filter_cutoff"),
        filter_resonance=data.get("filter_resonance"),
        decay=data.get("decay"),
        decay_1=data.get("decay_1"),
        decay_2=data.get("decay_2"),
        attack=data.get("attack"),
        alternate_group=data.get("alternate_group"),
        mute_group=data.get("mute_group"),
    )


def _parse_drum_parameters(section: dict[str, Any]) -> DrumConfig | None:
    if not section:
        return None
    notes_data = section.get("notes")
    notes: dict[int, DrumNoteParams] | None = None
    if isinstance(notes_data, dict):
        parsed = {}
        for note_str, data in notes_data.items():
            try:
                note = int(note_str)
            except (ValueError, TypeError):
                continue
            if isinstance(data, dict):
                parsed[note] = _parse_drum_note_params(data)
        if parsed:
            notes = parsed
    return DrumConfig(
        kit_number=section.get("kit_number"),
        channel=section.get("channel", 10),
        notes=notes,
    )


def _parse_reverb(data: dict[str, Any]) -> ReverbConfig | None:
    if not data:
        return None
    return ReverbConfig(
        type=data.get("type"),
        time=data.get("time"),
        level=data.get("level"),
        hf_damping=data.get("hf_damping"),
        pre_delay=data.get("pre_delay"),
        density=data.get("density"),
        balance=data.get("balance"),
    )


def _parse_chorus(data: dict[str, Any]) -> ChorusConfig | None:
    if not data:
        return None
    return ChorusConfig(
        type=data.get("type"),
        rate=data.get("rate"),
        depth=data.get("depth"),
        feedback=data.get("feedback"),
        level=data.get("level"),
        delay=data.get("delay"),
        cross_feedback=data.get("cross_feedback"),
        lfo_waveform=data.get("lfo_waveform"),
        phase_diff=data.get("phase_diff"),
    )


def _parse_variation(data: dict[str, Any]) -> VariationConfig | None:
    if not data:
        return None
    return VariationConfig(
        type=data.get("type"),
        level=data.get("level"),
        params=data.get("params"),
    )


def _parse_insertion(raw: dict[str, Any] | None) -> dict[int, InsertionSlot] | None:
    """Parse insertion effects from dict of channel → slot data."""
    if not raw:
        return None
    slots: dict[int, InsertionSlot] = {}
    for ch_str, data in raw.items():
        try:
            ch = int(ch_str)
        except (ValueError, TypeError):
            continue
        if not isinstance(data, dict):
            continue
        slots[ch] = InsertionSlot(
            type=data.get("type"),
            bypass=bool(data.get("bypass", False)),
            params=data.get("params"),
        )
    return slots if slots else None


def _parse_master_eq(raw: dict[str, Any] | None) -> EQConfig | None:
    """Parse master EQ config."""
    if not raw:
        return None
    return EQConfig(
        type=raw.get("type"),
        low_gain=raw.get("low_gain"),
        low_mid_gain=raw.get("low_mid_gain"),
        mid_gain=raw.get("mid_gain"),
        mid_freq=raw.get("mid_freq"),
        high_mid_gain=raw.get("high_mid_gain"),
        high_gain=raw.get("high_gain"),
        q_factor=raw.get("q_factor"),
    )


def _parse_effects(section: dict[str, Any]) -> EffectsConfig | None:
    if not section:
        return None
    return EffectsConfig(
        reverb=_parse_reverb(section.get("reverb")),
        chorus=_parse_chorus(section.get("chorus")),
        variation=_parse_variation(section.get("variation")),
        insertion=_parse_insertion(section.get("insertion")),
        master_eq=_parse_master_eq(section.get("master_eq")),
    )


def _parse_sequence_event(data: dict[str, Any]) -> SequenceEvent | None:
    if not isinstance(data, dict):
        return None
    event = SequenceEvent(at=float(data.get("at", 0)))

    note_on_data = data.get("note_on")
    if isinstance(note_on_data, dict):
        event.note_on = NoteEvent(
            note=note_on_data["note"],
            velocity=note_on_data.get("velocity", 100),
            duration=note_on_data.get("duration"),
            release_velocity=note_on_data.get("release_velocity", 64),
        )

    note_off_data = data.get("note_off")
    if isinstance(note_off_data, dict):
        event.note_off = NoteEvent(
            note=note_off_data["note"],
            velocity=note_off_data.get("velocity", 64),
            duration=note_off_data.get("duration"),
            release_velocity=note_off_data.get("release_velocity", 64),
        )

    control_data = data.get("control")
    if isinstance(control_data, dict):
        event.control = ControlEvent(
            controller=control_data["controller"],
            value=control_data["value"],
        )

    nrpn_data = data.get("nrpn")
    if isinstance(nrpn_data, dict):
        event.nrpn = NRPNEvent(
            msb=nrpn_data["msb"],
            lsb=nrpn_data["lsb"],
            value=nrpn_data["value"],
        )

    event.program = data.get("program")
    tempo_val = data.get("tempo")
    if tempo_val is not None:
        event.tempo = float(tempo_val)
    event.text = data.get("text")
    pb = data.get("pitch_bend")
    if pb is not None:
        event.pitch_bend = int(pb)

    cp = data.get("channel_pressure")
    if cp is not None:
        event.channel_pressure = int(cp)

    pp_data = data.get("poly_pressure")
    if isinstance(pp_data, list):
        pairs: list[tuple[int, int]] = []
        for item in pp_data:
            if isinstance(item, dict) and "note" in item and "pressure" in item:
                pairs.append((int(item["note"]), int(item["pressure"])))
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                pairs.append((int(item[0]), int(item[1])))
        if pairs:
            event.poly_pressure = pairs
    elif isinstance(pp_data, dict):
        # Also accept dict form: {note: pressure, ...}
        pairs = [(int(k), int(v)) for k, v in pp_data.items()]
        event.poly_pressure = pairs

    sx_data = data.get("sysex")
    if isinstance(sx_data, list):
        event.sysex = [int(b) & 0x7F for b in sx_data]

    return event


def _parse_track(data: dict[str, Any]) -> Track | None:
    if not isinstance(data, dict):
        return None
    events_data = data.get("events")
    events: list[SequenceEvent] = []
    if isinstance(events_data, list):
        for ed in events_data:
            ev = _parse_sequence_event(ed)
            if ev is not None:
                events.append(ev)

    return Track(
        name=data.get("name"),
        channel=data.get("channel"),
        port=int(data.get("port", 0)),
        program=data.get("program"),
        volume=data.get("volume", 100),
        pan=data.get("pan"),
        events=events,
    )


def _parse_sequence(name: str, data: dict[str, Any]) -> Sequence:
    tracks_data = data.get("tracks", [])
    tracks: list[Track] = []
    if isinstance(tracks_data, list):
        for td in tracks_data:
            t = _parse_track(td)
            if t is not None:
                tracks.append(t)

    ts = data.get("time_signature")
    time_sig: tuple[int, int] | None = None
    if isinstance(ts, (list, tuple)) and len(ts) == 2:
        time_sig = (int(ts[0]), int(ts[1]))

    return Sequence(
        name=name,
        tempo=float(data.get("tempo", 120)),
        time_signature=time_sig,
        tracks=tracks,
    )


def _parse_sequences(section: dict[str, Any]) -> dict[str, Sequence] | None:
    if not section:
        return None
    result: dict[str, Sequence] = {}
    for name, data in section.items():
        if isinstance(data, dict):
            result[name] = _parse_sequence(name, data)
    return result if result else None


def _parse_synthesizer_core(raw: dict[str, Any] | None) -> SynthesizerCore | None:
    """Parse synthesizer core configuration."""
    if not raw:
        return None
    channel_engines_raw = raw.get("channel_engines")
    channel_engines: dict[int, str] | None = None
    if isinstance(channel_engines_raw, dict):
        channel_engines = {}
        for k, v in channel_engines_raw.items():
            try:
                channel_engines[int(k)] = str(v)
            except (ValueError, TypeError):
                pass
    return SynthesizerCore(
        sample_rate=raw.get("sample_rate"),
        block_size=raw.get("block_size"),
        polyphony=raw.get("polyphony"),
        audio_channels=raw.get("audio_channels", 2),
        buffer_pool_size=raw.get("buffer_pool_size"),
        engine_registry=raw.get("engine_registry"),
        channel_engines=channel_engines,
    )


def _parse_gs_system(raw: dict[str, Any] | None) -> GSSystemConfig | None:
    """Parse Roland GS system parameters."""
    if not raw:
        return None
    return GSSystemConfig(
        master_tune=raw.get("master_tune"),
        master_volume=raw.get("master_volume"),
        master_transpose=raw.get("master_transpose"),
    )


def _parse_gs_part(raw: dict[str, Any]) -> GSPartConfig:
    """Parse a single Roland GS part configuration."""
    return GSPartConfig(
        program=raw.get("program"),
        bank_msb=raw.get("bank_msb"),
        bank_lsb=raw.get("bank_lsb"),
        volume=raw.get("volume"),
        pan=raw.get("pan"),
        coarse_tune=_signed(raw.get("coarse_tune")),
        fine_tune=_signed(raw.get("fine_tune")),
        key_shift=_signed(raw.get("key_shift")),
        key_range_low=raw.get("key_range_low"),
        key_range_high=raw.get("key_range_high"),
        velocity_range_low=raw.get("velocity_range_low"),
        velocity_range_high=raw.get("velocity_range_high"),
        portamento=raw.get("portamento"),
        portamento_time=raw.get("portamento_time"),
        bend_range=raw.get("bend_range"),
        filter_cutoff=raw.get("filter_cutoff"),
        filter_resonance=raw.get("filter_resonance"),
        attack_time=raw.get("attack_time"),
        decay_time=raw.get("decay_time"),
        release_time=raw.get("release_time"),
        vibrato_rate=raw.get("vibrato_rate"),
        vibrato_depth=raw.get("vibrato_depth"),
        vibrato_delay=raw.get("vibrato_delay"),
        reverb_send=raw.get("reverb_send"),
        chorus_send=raw.get("chorus_send"),
        delay_send=raw.get("delay_send"),
        mfx_send=raw.get("mfx_send"),
        rx_note=raw.get("rx_note"),
        rx_pitch_bend=raw.get("rx_pitch_bend"),
        rx_channel_pressure=raw.get("rx_channel_pressure"),
        rx_poly_pressure=raw.get("rx_poly_pressure"),
    )


def _parse_gs_effects(raw: dict[str, Any] | None) -> GSEffectsConfig | None:
    """Parse Roland GS effects configuration."""
    if not raw:
        return None
    rv_raw = raw.get("reverb")
    ch_raw = raw.get("chorus")
    rv = None
    if isinstance(rv_raw, dict):
        rv = GSReverbConfig(
            type=rv_raw.get("type"),
            level=rv_raw.get("level"),
            time=rv_raw.get("time"),
            feedback=rv_raw.get("feedback"),
            pre_delay=rv_raw.get("pre_delay"),
        )
    ch = None
    if isinstance(ch_raw, dict):
        ch = GSChorusConfig(
            type=ch_raw.get("type"),
            level=ch_raw.get("level"),
            rate=ch_raw.get("rate"),
            depth=ch_raw.get("depth"),
            feedback=ch_raw.get("feedback"),
        )
    return GSEffectsConfig(reverb=rv, chorus=ch)


def _parse_gs_drum_part(raw: dict[str, Any]) -> GSDrumPartConfig:
    """Parse a single GS drum part configuration."""
    return GSDrumPartConfig(
        map_low_note=raw.get("map_low_note"),
        map_high_note=raw.get("map_high_note"),
        pitch_offset=_signed(raw.get("pitch_offset")),
        level_offset=_signed(raw.get("level_offset")),
        pan_random=raw.get("pan_random"),
        key_group=raw.get("key_group"),
    )


def _parse_gs_config(raw: dict[str, Any] | None) -> GSConfig | None:
    """Parse Roland GS configuration section."""
    if not raw:
        return None
    # System
    system = _parse_gs_system(raw.get("system"))
    # Parts
    parts = None
    parts_raw = raw.get("parts")
    if isinstance(parts_raw, dict):
        parts = {}
        for ch_str, part_data in parts_raw.items():
            try:
                ch = int(ch_str)
            except (ValueError, TypeError):
                continue
            if isinstance(part_data, dict):
                parts[ch] = _parse_gs_part(part_data)
    # Effects
    effects = _parse_gs_effects(raw.get("effects"))
    # Drum parts
    drum_parts = None
    drum_raw = raw.get("drum_parts")
    if isinstance(drum_raw, dict):
        drum_parts = {}
        for ch_str, dp_data in drum_raw.items():
            try:
                ch = int(ch_str)
            except (ValueError, TypeError):
                continue
            if isinstance(dp_data, dict):
                drum_parts[ch] = _parse_gs_drum_part(dp_data)
    return GSConfig(system=system, parts=parts, effects=effects, drum_parts=drum_parts)


# ---------------------------------------------------------------------------
# Jupiter-X parsers
# ---------------------------------------------------------------------------


def _parse_jupiter_x_system(raw: dict[str, Any] | None) -> JupiterXSystemConfig | None:
    """Parse Jupiter-X system parameters."""
    if not raw:
        return None
    return JupiterXSystemConfig(
        master_volume=raw.get("master_volume"),
        master_tune=raw.get("master_tune"),
        master_transpose=raw.get("master_transpose"),
        master_pan=raw.get("master_pan"),
    )


def _parse_jupiter_x_engine(raw: dict[str, Any]) -> JupiterXEngineConfig:
    """Parse a single Jupiter-X engine configuration."""
    return JupiterXEngineConfig(
        enable=raw.get("enable"),
        level=raw.get("level"),
        pan=raw.get("pan"),
        coarse_tune=raw.get("coarse_tune"),
        fine_tune=raw.get("fine_tune"),
        parameters=raw.get("parameters"),
    )


def _parse_jupiter_x_lfo(raw: dict[str, Any] | None) -> JupiterXPartLFO | None:
    """Parse Jupiter-X LFO parameters."""
    if not raw:
        return None
    return JupiterXPartLFO(
        waveform=raw.get("waveform"),
        rate=raw.get("rate"),
        depth=raw.get("depth"),
        fade=raw.get("fade"),
        key_trigger=raw.get("key_trigger"),
        delay=raw.get("delay"),
    )


def _parse_jupiter_x_envelope(raw: dict[str, Any] | None) -> JupiterXPartEnvelope | None:
    """Parse Jupiter-X envelope parameters."""
    if not raw:
        return None
    return JupiterXPartEnvelope(
        attack=raw.get("attack"),
        decay=raw.get("decay"),
        sustain=raw.get("sustain"),
        release=raw.get("release"),
        attack_curve=raw.get("attack_curve"),
        decay_curve=raw.get("decay_curve"),
        release_curve=raw.get("release_curve"),
        velocity_sensitivity=raw.get("velocity_sensitivity"),
    )


def _parse_jupiter_x_modulation(raw: dict[str, Any] | None) -> JupiterXPartModulation | None:
    """Parse Jupiter-X modulation routing parameters."""
    if not raw:
        return None
    return JupiterXPartModulation(
        mod_wheel_depth=raw.get("mod_wheel_depth"),
        aftertouch_depth=raw.get("aftertouch_depth"),
        velocity_depth=raw.get("velocity_depth"),
        key_tracking_depth=raw.get("key_tracking_depth"),
        super_knob_depth=raw.get("super_knob_depth"),
    )


def _parse_jupiter_x_part(raw: dict[str, Any]) -> JupiterXPartConfig:
    """Parse a single Jupiter-X part configuration."""
    engines_raw = raw.get("engines")
    engines = None
    if isinstance(engines_raw, dict):
        engines = {}
        for eng_name in ("analog", "digital", "fm", "external"):
            eng_data = engines_raw.get(eng_name)
            if isinstance(eng_data, dict):
                engines[eng_name] = _parse_jupiter_x_engine(eng_data)
        if not engines:
            engines = None

    return JupiterXPartConfig(
        level=raw.get("level"),
        pan=raw.get("pan"),
        volume=raw.get("volume"),
        coarse_tune=raw.get("coarse_tune"),
        fine_tune=raw.get("fine_tune"),
        key_range_low=raw.get("key_range_low"),
        key_range_high=raw.get("key_range_high"),
        reverb_send=raw.get("reverb_send"),
        chorus_send=raw.get("chorus_send"),
        delay_send=raw.get("delay_send"),
        engine_mode=raw.get("engine_mode"),
        active_engine=raw.get("active_engine"),
        engines=engines,
        lfo=_parse_jupiter_x_lfo(raw.get("lfo")),
        envelope=_parse_jupiter_x_envelope(raw.get("envelope")),
        modulation=_parse_jupiter_x_modulation(raw.get("modulation")),
    )


def _parse_jupiter_x_vcm(raw: dict[str, Any] | None) -> JupiterXVCMConfig | None:
    """Parse Jupiter-X VCM effects chain."""
    if not raw:
        return None
    return JupiterXVCMConfig(
        distortion_type=raw.get("distortion_type"),
        distortion_drive=raw.get("distortion_drive"),
        distortion_level=raw.get("distortion_level"),
        phaser_polarity=raw.get("phaser_polarity"),
        phaser_rate=raw.get("phaser_rate"),
        phaser_depth=raw.get("phaser_depth"),
        phaser_level=raw.get("phaser_level"),
        chorus_type=raw.get("chorus_type"),
        chorus_rate=raw.get("chorus_rate"),
        chorus_depth=raw.get("chorus_depth"),
        chorus_level=raw.get("chorus_level"),
        delay_type=raw.get("delay_type"),
        delay_time=raw.get("delay_time"),
        delay_feedback=raw.get("delay_feedback"),
        delay_level=raw.get("delay_level"),
        reverb_type=raw.get("reverb_type"),
        reverb_time=raw.get("reverb_time"),
        reverb_level=raw.get("reverb_level"),
        reverb_density=raw.get("reverb_density"),
    )


def _parse_jupiter_x_arp(raw: dict[str, Any] | None) -> JupiterXArpConfig | None:
    """Parse Jupiter-X arpeggiator configuration."""
    if not raw:
        return None
    return JupiterXArpConfig(
        enable=raw.get("enable"),
        style=raw.get("style"),
        type=raw.get("type"),
        range=raw.get("range"),
        rate=raw.get("rate"),
        swing=raw.get("swing"),
        latch=raw.get("latch"),
        target=raw.get("target"),
        tempo=raw.get("tempo"),
        gate_time=raw.get("gate_time"),
        pattern_length=raw.get("pattern_length"),
    )


def _parse_jupiter_x_config(raw: dict[str, Any] | None) -> JupiterXConfig | None:
    """Parse complete Jupiter-X configuration section."""
    if not raw:
        return None
    system = _parse_jupiter_x_system(raw.get("system"))
    parts = None
    parts_raw = raw.get("parts")
    if isinstance(parts_raw, dict):
        parts = {}
        for ch_str, part_data in parts_raw.items():
            try:
                ch = int(ch_str)
            except (ValueError, TypeError):
                continue
            if isinstance(part_data, dict):
                parts[ch] = _parse_jupiter_x_part(part_data)
    effects = _parse_jupiter_x_vcm(raw.get("effects"))
    arpeggiator = _parse_jupiter_x_arp(raw.get("arpeggiator"))
    return JupiterXConfig(
        system=system,
        parts=parts,
        effects=effects,
        arpeggiator=arpeggiator,
    )


def _parse_scale_tuning(raw: dict[str, Any] | None) -> ScaleTuning | None:
    """Parse scale/micro-tuning section."""
    if not raw:
        return None
    return ScaleTuning(
        c=raw.get("c"),
        c_sharp=raw.get("c_sharp"),
        d=raw.get("d"),
        d_sharp=raw.get("d_sharp"),
        e=raw.get("e"),
        f=raw.get("f"),
        f_sharp=raw.get("f_sharp"),
        g=raw.get("g"),
        g_sharp=raw.get("g_sharp"),
        a=raw.get("a"),
        a_sharp=raw.get("a_sharp"),
        b=raw.get("b"),
        master_tune=raw.get("master_tune"),
        transpose=raw.get("transpose"),
        temperament=raw.get("temperament"),
        octave_tune=raw.get("octave_tune"),
    )


def _parse_system_exclusive(raw: list[dict[str, Any]] | None) -> list[SystemExclusive] | None:
    """Parse system exclusive messages."""
    if not raw:
        return None
    messages: list[SystemExclusive] = []
    for item in raw:
        if isinstance(item, dict):
            messages.append(SystemExclusive(
                manufacturer=int(item["manufacturer"]),
                device=int(item.get("device", 0)),
                data=list(item.get("data", [])),
                description=item.get("description"),
            ))
    return messages if messages else None


# ---------------------------------------------------------------------------
# Backward-compatibility helpers
# ---------------------------------------------------------------------------

def _normalize_keys(obj: Any) -> Any:
    """Recursively convert all integer keys to strings (for JSON Schema compatibility).

    YAML parses keys like ``0:`` as integers, but JSON Schema patternProperties
    expects string keys.
    """
    if isinstance(obj, dict):
        return {str(k): _normalize_keys(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_normalize_keys(item) for item in obj]
    return obj


def _coerce_v1_v2_to_v3(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert legacy v1/v2 format keys to v3 section names where different."""
    # v1/v2 uses "xg_dsl_version", "description", "timestamp" — same in v3
    # v2 sections: basic_messages, channel_parameters, drum_parameters,
    #              effects, sequences, gs_parameters, mpe_settings, ...
    # These mostly map 1:1 to the v3 structure.
    # The main differences are:
    #   - v2 has "gs_parameters" as section — v3 nests it under basic_messages
    #   - v2 has "mpe_settings" — v3 omits (handled by synth bridge)
    #   - v2 timestamp is a string at root; v3 has meta.created
    # No coercion needed for most fields — just parse what's there.
    raw.setdefault("xg_dsl_version", "2.0")

    # Promote root-level description into meta if not already in meta
    if "description" in raw and "meta" not in raw:
        raw["meta"] = raw.get("meta", {})
        if isinstance(raw["meta"], dict):
            raw["meta"].setdefault("description", raw["description"])

    # Normalize integer keys to strings for JSON Schema compatibility
    return _normalize_keys(raw)


# ---------------------------------------------------------------------------
# Main Parser
# ---------------------------------------------------------------------------


class XGMLConfigParser:
    """Unified XGML parser: YAML → typed XGMLConfig.

    Supports XGML v1.0, v2.0, v2.1, and v3.0 formats.
    Validates against JSON Schema; parses every section into typed dataclasses.
    """

    def __init__(self, validate_schema: bool = True):
        self.validate_schema = validate_schema
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def parse_file(self, path: str | Path) -> XGMLConfig | None:
        """Parse XGML from a file path."""
        path = Path(path)
        if not path.exists():
            self.errors.append(f"File not found: {path}")
            return None
        try:
            raw = path.read_text(encoding="utf-8")
        except Exception as e:
            self.errors.append(f"Error reading {path}: {e}")
            return None
        return self.parse_string(raw)

    def parse_string(self, text: str) -> XGMLConfig | None:
        """Parse XGML from a YAML string."""
        try:
            raw = yaml.safe_load(text)
        except yaml.YAMLError as e:
            self.errors.append(f"YAML parse error: {e}")
            return None

        if not isinstance(raw, dict):
            self.errors.append("XGML document must be a YAML mapping (dict)")
            return None

        return self.parse_data(raw)

    def parse_data(self, data: dict[str, Any]) -> XGMLConfig | None:
        """Parse pre-loaded YAML data into XGMLConfig."""
        self.errors = []
        self.warnings = []

        raw = _coerce_v1_v2_to_v3(data)

        # Validate version
        version_str = str(raw.get("xg_dsl_version", "3.0"))
        if version_str not in _SUPPORTED_VERSIONS:
            self.warnings.append(
                f"Unsupported XGML version {version_str!r}; "
                f"supported: {', '.join(sorted(_SUPPORTED_VERSIONS))}"
            )

        # Optional JSON Schema validation
        if self.validate_schema:
            try:
                self._validate_schema(raw)
            except SchemaValidationError as e:
                self.errors.append(str(e))
                return None

        # Build the typed config
        try:
            return self._build_config(raw)
        except Exception as e:
            self.errors.append(f"Error building config: {e}")
            logger.exception("XGML config build failed")
            return None

    # ------------------------------------------------------------------
    # Schema validation
    # ------------------------------------------------------------------

    def _validate_schema(self, data: dict[str, Any]) -> None:
        """Validate against JSON Schema. Raises SchemaValidationError."""
        try:
            import jsonschema
        except ImportError:
            self.warnings.append("jsonschema not installed — skipping schema validation")
            return

        try:
            jsonschema.validate(instance=data, schema=XGML_SCHEMA)
        except jsonschema.ValidationError as e:
            msg = f"Schema validation failed: {e.message}"
            if e.path:
                msg += f" (path: {'/'.join(str(p) for p in e.path)})"
            raise SchemaValidationError(msg) from e

    # ------------------------------------------------------------------
    # Config builder
    # ------------------------------------------------------------------

    def _build_config(self, raw: dict[str, Any]) -> XGMLConfig:
        """Convert validated raw YAML dict into typed XGMLConfig."""
        version_str = str(raw.get("xg_dsl_version", "3.0"))

        meta_data = raw.get("meta", {})
        if isinstance(raw.get("metadata"), dict):
            meta_data = raw["metadata"]
        if isinstance(meta_data, dict):
            # Merge root-level description into meta
            meta_desc = meta_data.get("description") or raw.get("description")
            meta_data["description"] = meta_desc

        cfg = XGMLConfig(
            version=version_str,
            description=raw.get("description"),
            meta=_parse_meta(meta_data),
            basic_messages=_parse_basic_messages(raw.get("basic_messages")),
            channel_parameters=_parse_channel_parameters(raw.get("channel_parameters")),
            drum_parameters=_parse_drum_parameters(raw.get("drum_parameters")),
            effects=_parse_effects(raw.get("effects")),
            sequences=_parse_sequences(raw.get("sequences")),
            scale_tuning=_parse_scale_tuning(raw.get("scale_tuning")),
            gs=_parse_gs_config(raw.get("gs")),
            jupiter_x=_parse_jupiter_x_config(raw.get("jupiter_x")),
            system_exclusive=_parse_system_exclusive(raw.get("system_exclusive")),
            synthesizer_core=_parse_synthesizer_core(raw.get("synthesizer_core")),
        )

        return cfg

    # ------------------------------------------------------------------
    # Error tracking
    # ------------------------------------------------------------------

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def get_errors(self) -> list[str]:
        return self.errors.copy()

    def get_warnings(self) -> list[str]:
        return self.warnings.copy()


# =============================================================================
# Backward compatibility: old v1/v2 API preserved for Phase 3 migration
# =============================================================================

XGML_SECTIONS = [
    "basic_messages",
    "channel_parameters",
    "drum_parameters",
    "effects",
    "system_exclusive",
    "sequences",
    "gs_parameters",
    "mpe_settings",
    "modulation_matrix",
    "engine_configs",
    "synthesis_engines",
]

XGML_VERSION = "2.0"


class XGMLDocument:
    """Legacy XGML document (v1/v2) — preserved for backward compatibility."""

    def __init__(self, data: dict[str, Any]):
        self.version = data.get("xg_dsl_version", XGML_VERSION)
        self.description = data.get("description", "")
        self.timestamp = data.get("timestamp")
        self.sections = {}

        for section_name in XGML_SECTIONS:
            if section_name in data:
                self.sections[section_name] = data[section_name]

    def has_section(self, section_name: str) -> bool:
        return section_name in self.sections

    def get_section(self, section_name: str) -> Any | None:
        return self.sections.get(section_name)

    def get_sections(self) -> list[str]:
        return list(self.sections.keys())


class XGMLParser:
    """Legacy v1/v2 XGML parser — preserved for backward compatibility.

    Import XGMLConfigParser for the new typed parser.
    """

    def __init__(self):
        self.errors = []
        self.warnings = []

    def parse_file(self, file_path: str | Path) -> XGMLDocument | None:
        try:
            path = Path(file_path)
            if not path.exists():
                self.errors.append(f"File not found: {file_path}")
                return None
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return self.parse_data(data)
        except yaml.YAMLError as e:
            self.errors.append(f"YAML parsing error: {e}")
            return None
        except Exception as e:
            self.errors.append(f"Error reading file: {e}")
            return None

    def parse_string(self, yaml_string: str) -> XGMLDocument | None:
        try:
            data = yaml.safe_load(yaml_string)
            return self.parse_data(data)
        except yaml.YAMLError as e:
            self.errors.append(f"YAML parsing error: {e}")
            return None

    def parse_data(self, data: dict[str, Any]) -> XGMLDocument | None:
        self.errors = []
        self.warnings = []
        if not isinstance(data, dict):
            self.errors.append("XGML document must be a dictionary")
            return None
        version = data.get("xg_dsl_version", XGML_VERSION)
        if version not in [XGML_VERSION, "1.0"]:
            self.warnings.append(
                f"XGML version {version} may not be fully compatible with parser version {XGML_VERSION}"
            )
        has_content = any(
            section in data
            for section in XGML_SECTIONS
            if section not in ("xg_dsl_version", "description", "timestamp")
        )
        if not has_content:
            self.warnings.append("No XGML content sections found in document")
        timestamp = data.get("timestamp")
        if timestamp:
            try:
                datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                self.warnings.append(f"Invalid timestamp format: {timestamp}")
        try:
            return XGMLDocument(data)
        except Exception as e:
            self.errors.append(f"Error creating XGML document: {e}")
            return None

    def get_errors(self) -> list[str]:
        return self.errors.copy()

    def get_warnings(self) -> list[str]:
        return self.warnings.copy()

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        return len(self.warnings) > 0
