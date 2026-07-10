"""
XGML Type System — core typed dataclasses for the XGML document model.

This module defines the complete data model for XGML documents, covering:
  - Goal 1: Preset/configuration (basic messages, channel params, effects)
  - Goal 2: Composition (sequences, tracks, events at MIDI-file fidelity)

The types are pure data — no translation, no encoding, no MIDI generation.
All NRPN/MIDI knowledge lives in synth/protocols/xg/ and is consumed by bridges.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# =============================================================================
# Meta
# =============================================================================


@dataclass
class Meta:
    """Document metadata (not synthesizer state)."""

    description: str | None = None
    author: str | None = None
    created: str | None = None  # ISO 8601
    modified: str | None = None  # ISO 8601
    tags: list[str] | None = None
    source: str | None = None  # e.g. "midi_to_xgml", "hand_written"
    custom: dict[str, Any] | None = None  # extension point


# =============================================================================
# Goal 1: Preset / Configuration
# =============================================================================


# -- Basic Messages (CC, program change, pitch bend — everything at time=0) --


@dataclass
class ChannelSetup:
    """Per-channel initial state: program, volume, pan, expression, sends.

    All values use human-readable names or MIDI-normalized ranges (0-127).
    """

    program: str | int | None = None  # program name (GM) or number 0-127
    volume: int | None = None  # 0-127
    pan: str | int | None = None  # "center"/"left"/"right" or 0-127
    expression: int | None = None  # 0-127
    reverb_send: int | None = None  # 0-127
    chorus_send: int | None = None  # 0-127
    variation_send: int | None = None  # 0-127
    pitch_bend_range: int | None = None  # semitones 0-24
    master_tune: int | None = None  # cents -64..63 via RPN
    fine_tune: int | None = None  # cents -64..63 via RPN
    coarse_tune: int | None = None  # semitones -24..24 via RPN
    bank_msb: int | None = None  # 0-127
    bank_lsb: int | None = None  # 0-127
    portamento_time: int | None = None  # 0-127
    portamento: bool | None = None  # portamento on/off
    sostenuto: bool | None = None
    soft_pedal: bool | None = None
    hold: int | None = None  # hold pedal value 0-127
    part_mode: str | None = None  # "single"/"multi" (NRPN MSB 43)
    voice_reserve: int | None = None  # 0-127 voices reserved for this part (NRPN MSB 42)
    port: int = 0  # MIDI port number (0 = first port). Flat channel = port * 16 + channel.


@dataclass
class BasicMessages:
    """All time-zero channel setup messages."""

    channels: dict[int, ChannelSetup] = field(default_factory=dict)  # 0-15


# -- Per-channel XG Parameters (NRPN MSB 3-31) --


@dataclass
class FilterParams:
    cutoff: int | None = None  # 0-127 (maps to ~20-20000 Hz)
    resonance: int | None = None  # 0-127
    type: str | int | None = None  # "lowpass"/"highpass"/"bandpass"/"through" or 0-3
    envelope_attack: int | None = None  # 0-127
    envelope_decay: int | None = None  # 0-127
    envelope_sustain: int | None = None  # 0-127
    envelope_release: int | None = None  # 0-127
    envelope_depth: int | None = None  # 0-127
    velocity_sensitivity: int | None = None  # 0-127
    key_scaling: int | None = None  # 0-127


@dataclass
class LFOParams:
    waveform: str | int | None = None  # "sine"/"triangle"/"square"/"saw" or 0-3
    speed: int | None = None  # 0-127
    delay: int | None = None  # 0-127
    fade: int | None = None  # 0-127
    pitch_depth: int | None = None  # 0-127
    filter_depth: int | None = None  # 0-127
    amp_depth: int | None = None  # 0-127
    key_sync: bool | None = None


@dataclass
class AmpEnvelope:
    attack: int | None = None  # 0-127
    decay: int | None = None  # 0-127
    sustain: int | None = None  # 0-127
    release: int | None = None  # 0-127
    velocity_sensitivity: int | None = None  # 0-127
    key_scaling: int | None = None  # 0-127


@dataclass
class PitchParams:
    coarse: int | None = None  # -24..24 semitones
    fine: int | None = None  # -64..63 cents
    random: int | None = None  # 0-127
    key_scaling: int | None = None  # 0-127
    envelope_attack: int | None = None  # 0-127
    envelope_decay: int | None = None  # 0-127
    envelope_depth: int | None = None  # -64..63


@dataclass
class EffectSends:
    reverb: int | None = None  # 0-127
    chorus: int | None = None  # 0-127
    variation: int | None = None  # 0-127
    dry_level: int | None = None  # 0-127
    insertion_l: int | None = None  # insertion send L 0-127
    insertion_r: int | None = None  # insertion send R 0-127


@dataclass
class ChannelConfig:
    """Per-channel XG configuration (NRPN MSB 3-19)."""

    filter: FilterParams | None = None
    lfo: dict[str, LFOParams] | None = None  # keys: "lfo1", "lfo2"
    amp_envelope: AmpEnvelope | None = None
    pitch: PitchParams | None = None
    effects_sends: EffectSends | None = None

    # Element reserve (MSB 20+)
    element_reserve: int | None = None  # 0-127 voices reserved
    velocity_response: int | None = None  # 0-127 velocity curve
    velocity_offset: int | None = None  # -64..63
    velocity_range_low: int | None = None  # 0-127
    velocity_range_high: int | None = None  # 0-127

    # Additional parameters
    controller_assignments: dict[str, int] | None = None  # assignable controllers
    note_shift: int | None = None  # -24..24 semitones
    mono_poly: str | None = None  # "mono"/"poly"
    legato: bool | None = None


# -- Drum Parameters (NRPN MSB 40-49, 48-63) --


@dataclass
class DrumNoteParams:
    """Per-note drum configuration."""

    pitch_coarse: int | None = None  # -24..24
    pitch_fine: int | None = None  # -64..63
    level: int | None = None  # 0-127
    pan: int | None = None  # 0-127 (64=center)
    reverb_send: int | None = None  # 0-127
    chorus_send: int | None = None  # 0-127
    variation_send: int | None = None  # 0-127
    filter_cutoff: int | None = None  # 0-127
    filter_resonance: int | None = None  # 0-127
    decay: int | None = None  # 0-127 (amp decay)
    decay_1: int | None = None  # 0-127 (pitch envelope decay)
    decay_2: int | None = None  # 0-127 (filter envelope decay)
    attack: int | None = None  # 0-127
    alternate_group: int | None = None  # 0-127
    mute_group: int | None = None  # 0-127


@dataclass
class DrumConfig:
    """Drum kit configuration."""

    kit_number: int | None = None  # 0-127 XG drum kit
    channel: int | None = 10  # default MIDI channel 10
    notes: dict[int, DrumNoteParams] | None = None  # note 24-107 → params


# -- Effects Configuration --


@dataclass
class ReverbConfig:
    type: int | str | None = None  # XG reverb type 1-26, or name
    time: float | None = None  # seconds 0.1-30.0
    level: float | None = None  # 0.0-1.0
    hf_damping: float | None = None  # 0.0-1.0
    pre_delay: float | None = None  # ms 0-50
    density: float | None = None  # 0.0-1.0
    balance: float | None = None  # 0.0-1.0 wet/dry


@dataclass
class ChorusConfig:
    type: int | str | None = None  # XG chorus type 0-17, or name
    rate: float | None = None  # Hz 0.125-10.0
    depth: float | None = None  # 0.0-1.0
    feedback: float | None = None  # -1.0 to 1.0
    level: float | None = None  # 0.0-1.0
    delay: float | None = None  # seconds 0.001-0.05
    cross_feedback: float | None = None  # 0.0-1.0
    lfo_waveform: int | None = None  # 0-3
    phase_diff: float | None = None  # degrees 0-180


@dataclass
class VariationConfig:
    type: int | None = None  # 0-83 XG variation type
    level: float | None = None  # 0.0-1.0
    params: dict[str, float] | None = None  # effect-specific parameters


@dataclass
class InsertionSlot:
    type: int | str | None = None  # effect type
    bypass: bool = False
    params: dict[str, float] | None = None


@dataclass
class EQBand:
    gain: float | None = None  # dB -12..+12


@dataclass
class EQConfig:
    type: int | None = None  # XG EQ type 0-4
    low_gain: float | None = None
    low_mid_gain: float | None = None
    mid_gain: float | None = None
    mid_freq: float | None = None  # Hz
    high_mid_gain: float | None = None
    high_gain: float | None = None
    q_factor: float | None = None


@dataclass
class EffectsConfig:
    """Complete effects chain configuration."""

    reverb: ReverbConfig | None = None
    chorus: ChorusConfig | None = None
    variation: VariationConfig | None = None
    insertion: dict[int, InsertionSlot] | None = None  # channel 0-15 → slot
    master_eq: EQConfig | None = None


# -- System Exclusive --


@dataclass
class SystemExclusive:
    """Arbitrary SYSEX message."""

    manufacturer: int  # 0x43 = Yamaha, 0x41 = Roland
    device: int = 0  # device ID
    data: list[int] = field(default_factory=list)  # raw bytes (excluding header)
    description: str | None = None


# -- Roland GS Configuration --


@dataclass
class GSSystemConfig:
    """GS system-wide parameters (SysEx addr 0x00)."""

    master_tune: int | None = None  # -64..63 cents
    master_volume: int | None = None  # 0-127
    master_transpose: int | None = None  # -24..24 semitones


@dataclass
class GSPartConfig:
    """Per-part Roland GS configuration.

    Maps to GS SysEx address 0x01 nn xx (nn=1..16, xx=0x00..0x1D).
    """

    program: int | None = None  # 0-127
    bank_msb: int | None = None  # 0-127 (127 = GS drum)
    bank_lsb: int | None = None  # 0-127
    volume: int | None = None  # 0-127
    pan: int | None = None  # 0-127 (64=center)
    coarse_tune: int | None = None  # -24..24 semitones
    fine_tune: int | None = None  # -64..63 cents
    key_shift: int | None = None  # -24..24 semitones
    key_range_low: int | None = None  # 0-127
    key_range_high: int | None = None  # 0-127
    velocity_range_low: int | None = None  # 1-127
    velocity_range_high: int | None = None  # 1-127
    portamento: bool | None = None
    portamento_time: int | None = None  # 0-127
    bend_range: int | None = None  # 0-24 semitones
    filter_cutoff: int | None = None  # 0-127
    filter_resonance: int | None = None  # 0-127
    attack_time: int | None = None  # 0-127
    decay_time: int | None = None  # 0-127
    release_time: int | None = None  # 0-127
    vibrato_rate: int | None = None  # 0-127
    vibrato_depth: int | None = None  # 0-127
    vibrato_delay: int | None = None  # 0-127
    reverb_send: int | None = None  # 0-127
    chorus_send: int | None = None  # 0-127
    delay_send: int | None = None  # 0-127 (JV-2080)
    mfx_send: int | None = None  # 0-127 (JV-2080)
    rx_note: bool | None = None
    rx_pitch_bend: bool | None = None
    rx_channel_pressure: bool | None = None
    rx_poly_pressure: bool | None = None


@dataclass
class GSReverbConfig:
    """GS reverb configuration (SysEx addr 0x05).

    GS reverb types differ from XG — use names or GS type values 0-7.
    """

    type: str | int | None = None  # "room1"/"room2"/"hall1"/"hall2"/"plate"/"delay"/"panning_delay" or 0-7
    level: int | None = None  # 0-127
    time: int | None = None  # 0-127
    feedback: int | None = None  # 0-127
    pre_delay: int | None = None  # 0-127


@dataclass
class GSChorusConfig:
    """GS chorus configuration (SysEx addr 0x04).

    GS chorus types differ from XG — use names or GS type values 0-5.
    """

    type: str | int | None = None  # "chorus1"/"chorus2"/"chorus3"/"chorus4"/"feedback"/"flanger" or 0-5
    level: int | None = None  # 0-127
    rate: int | None = None  # 0-127
    depth: int | None = None  # 0-127
    feedback: int | None = None  # 0-127


@dataclass
class GSEffectsConfig:
    """GS effects chain configuration."""

    reverb: GSReverbConfig | None = None
    chorus: GSChorusConfig | None = None


@dataclass
class GSDrumPartConfig:
    """GS drum part configuration (SysEx addr 0x10-0x1F)."""

    map_low_note: int | None = None  # 0-127
    map_high_note: int | None = None  # 0-127
    pitch_offset: int | None = None  # -24..24
    level_offset: int | None = None  # -64..63
    pan_random: int | None = None  # 0-127
    key_group: int | None = None  # -1..7


@dataclass
class GSConfig:
    """Complete Roland GS configuration section.

    All parameters optional — applies alongside or instead of XG config.
    """

    system: GSSystemConfig | None = None
    parts: dict[int, GSPartConfig] | None = None  # GS part number 0-15 → config
    effects: GSEffectsConfig | None = None
    drum_parts: dict[int, GSDrumPartConfig] | None = None  # GS part number 0-15 → drum config


# =============================================================================
# Roland Jupiter-X configuration (builds on GS)
# =============================================================================


@dataclass
class JupiterXSystemConfig:
    """Jupiter-X global system parameters (NRPN MSB 0x00).

    These sit alongside GS system parameters (GSSystemConfig).
    """

    master_volume: int | None = None  # 0-127
    master_tune: int | None = None  # -64..63 semitones
    master_transpose: int | None = None  # -12..12 semitones
    master_pan: int | None = None  # -64..63


@dataclass
class JupiterXEngineConfig:
    """Per-engine configuration for Jupiter-X (Analog/Digital/FM/External).

    Each of 16 parts has 4 engines, accessed via NRPN MSB 0x30-0x3F
    (MSB = 0x30 + part*4 + engine_offset).
    """

    # Common base parameters (NRPN LSB 0x00-0x04)
    enable: bool | None = None
    level: int | None = None  # 0-127
    pan: int | None = None  # -64..63
    coarse_tune: int | None = None  # -24..24
    fine_tune: int | None = None  # -50..50

    # Engine-specific: use dict for flexible NRPN parameter access
    parameters: dict[str, int] | None = None  # named param → raw value


@dataclass
class JupiterXPartLFO:
    """LFO/modulation parameters per Jupiter-X part (NRPN MSB 0x60-0x6F)."""

    waveform: int | None = None  # 0=sine, 1=tri, 2=saw, 3=sq, 4=random, 5=step
    rate: int | None = None  # 0-127
    depth: int | None = None  # 0-127
    fade: int | None = None  # 0-127 (fade-in time)
    key_trigger: bool | None = None  # key-sync on/off
    delay: int | None = None  # 0-127 (delay time)


@dataclass
class JupiterXPartEnvelope:
    """Envelope parameters per Jupiter-X part/engine (NRPN MSB 0x70-0x7F).

    Shared envelope that can be applied differently per engine.
    """

    attack: int | None = None  # 0-127
    decay: int | None = None  # 0-127
    sustain: int | None = None  # 0-127
    release: int | None = None  # 0-127
    attack_curve: int | None = None  # 0=linear, 1=convex, 2=concave
    decay_curve: int | None = None
    release_curve: int | None = None
    velocity_sensitivity: int | None = None  # 0-127


@dataclass
class JupiterXPartModulation:
    """Modulation routing per Jupiter-X part (NRPN MSB 0x80-0x8F)."""

    mod_wheel_depth: int | None = None  # 0-127
    aftertouch_depth: int | None = None  # 0-127
    velocity_depth: int | None = None  # 0-127
    key_tracking_depth: int | None = None  # 0-127
    super_knob_depth: int | None = None  # 0-127 (Jupiter-X super knob)


@dataclass
class JupiterXPartConfig:
    """A single Jupiter-X part with all 4 engines.

    The part inherits GS part parameters (GSPartConfig) and adds
    Jupiter-X specific engine, LFO, envelope, and modulation config.

    NRPN ranges:
      MSB 0x10-0x1F: Part-level parameters (tune, volume, key range, etc.)
      MSB 0x30-0x3F: Engine parameters (4 MSBs per part, 1 per engine)
      MSB 0x60-0x6F: LFO/modulation
      MSB 0x70-0x7F: Envelope
      MSB 0x80-0x8F: Modulation routing
    """

    # Part-level (shared with GS)
    level: int | None = None  # 0-127
    pan: int | None = None  # -64..63
    volume: int | None = None  # 0-127
    coarse_tune: int | None = None  # -24..24
    fine_tune: int | None = None  # -50..50
    key_range_low: int | None = None  # 0-127
    key_range_high: int | None = None  # 0-127
    reverb_send: int | None = None  # 0-127
    chorus_send: int | None = None  # 0-127
    delay_send: int | None = None  # 0-127 (Jupiter-X specific)

    # Engine selection (which engine is active/primary)
    engine_mode: int | None = None  # 0=GS (single), 1=Jupiter-X (multi-engine)
    active_engine: int | None = None  # 0=Analog, 1=Digital, 2=FM, 3=External

    # Four engines per part (dict keyed by engine name)
    engines: dict[str, JupiterXEngineConfig] | None = None  # {"analog": ..., "digital": ..., "fm": ..., "external": ...}

    # Per-part modulation
    lfo: JupiterXPartLFO | None = None
    envelope: JupiterXPartEnvelope | None = None
    modulation: JupiterXPartModulation | None = None


@dataclass
class JupiterXVCMConfig:
    """VCM (Virtual Circuit Modeling) effects chain configuration.

    Jupiter-X effects chain: Distortion → Phaser → Chorus → Delay → Reverb.
    Mapped via SysEx addresses 0x40 XX XX and NRPN MSB 0x40-0x4F.
    """

    # Distortion
    distortion_type: int | str | None = None  # 0-7 or name
    distortion_drive: int | None = None  # 0-127
    distortion_level: int | None = None  # 0-127

    # Phaser
    phaser_polarity: int | None = None  # 0=normal, 1=inverse
    phaser_rate: int | None = None  # 0-127
    phaser_depth: int | None = None  # 0-127
    phaser_level: int | None = None  # 0-127

    # Chorus
    chorus_type: int | str | None = None  # 0-7 or name
    chorus_rate: int | None = None  # 0-127
    chorus_depth: int | None = None  # 0-127
    chorus_level: int | None = None  # 0-127

    # Delay
    delay_type: int | str | None = None  # 0-7 or name
    delay_time: int | None = None  # 0-127
    delay_feedback: int | None = None  # 0-127
    delay_level: int | None = None  # 0-127

    # Reverb
    reverb_type: int | str | None = None  # 0-7 or name
    reverb_time: int | None = None  # 0-127
    reverb_level: int | None = None  # 0-127
    reverb_density: int | None = None  # 0-127


@dataclass
class JupiterXArpConfig:
    """Jupiter-X arpeggiator configuration.

    NRPN MSB 0x50-0x5F maps to arpeggiator parameters.
    """

    enable: bool | None = None
    style: int | None = None  # 0-7 arpeggiator style
    type: int | None = None  # 0-7 (up, down, random, etc.)
    range: int | None = None  # 1-4 octave range
    rate: int | None = None  # 0-127
    swing: int | None = None  # -50..50
    latch: bool | None = None
    target: int | None = None  # 0=internal, 1=external, 2=both
    tempo: int | None = None  # BPM
    gate_time: int | None = None  # 0-127 (percentage)
    pattern_length: int | None = None  # steps


@dataclass
class JupiterXConfig:
    """Complete Roland Jupiter-X configuration section.

    Jupiter-X builds on GS — it uses the same SysEx and NRPN framework
    (JV-2080 compatible) but adds 4 engines per part, VCM effects,
    arpeggiator, and enhanced modulation.
    """

    system: JupiterXSystemConfig | None = None
    parts: dict[int, JupiterXPartConfig] | None = None  # part 0-15 → config
    effects: JupiterXVCMConfig | None = None
    arpeggiator: JupiterXArpConfig | None = None


# -- Synthesizer Core (v3-style engine config, applied via synth bridge) --


@dataclass
class SynthesizerCore:
    """Low-level synthesizer configuration (sample rate, buffer, polyphony)."""

    sample_rate: int | None = None
    block_size: int | None = None
    polyphony: int | None = None  # max simultaneous voices
    audio_channels: int | None = 2
    buffer_pool_size: int | None = None
    engine_registry: list[str] | None = None  # enabled engine names
    channel_engines: dict[int, str] | None = None  # channel 0-15 → engine name


# -- Scale / Micro Tuning (NRPN MSB 17-18) --


@dataclass
class ScaleTuning:
    """Per-note scale tuning configuration.

    Each note C-B can be tuned ±100 cents from equal temperament.
    NRPN MSB 17 = lower 6 notes (C-F#), MSB 18 = upper 6 notes (G-B) + master.
    """

    # MSB 17: C, C#, D, D#, E, F, F#
    c: int | None = None  # -64..64 cents
    c_sharp: int | None = None  # -64..64 cents
    d: int | None = None  # -64..64 cents
    d_sharp: int | None = None  # -64..64 cents
    e: int | None = None  # -64..64 cents
    f: int | None = None  # -64..64 cents
    f_sharp: int | None = None  # -64..64 cents
    # MSB 18: G, G#, A, A#, B
    g: int | None = None  # -64..64 cents
    g_sharp: int | None = None  # -64..64 cents
    a: int | None = None  # -64..64 cents
    a_sharp: int | None = None  # -64..64 cents
    b: int | None = None  # -64..64 cents

    # MSB 18 extended
    master_tune: int | None = None  # -64..63 cents (offset +64 for NRPN 0-127)
    transpose: int | None = None  # -24..24 semitones
    temperament: str | int | None = None  # name or 0=equal, 1=just, 2=...
    octave_tune: list[int] | None = None  # per-octave tuning ±100 cents × 11 octaves


# =============================================================================
# Goal 2: Composition (sequences at MIDI-file fidelity)
# =============================================================================


@dataclass
class NoteEvent:
    """A single note-on/off pair."""

    note: str | int  # note name ("C#4") or MIDI number (0-127)
    velocity: int = 100  # 0-127
    duration: float | None = None  # beats (if not provided, note-off timestamp)
    release_velocity: int = 64  # 0-127


@dataclass
class ControlEvent:
    """A control change or parameter change."""

    controller: int | str  # CC number or name
    value: int | float  # 0-127 or float 0.0-1.0


@dataclass
class NRPNEvent:
    """An NRPN parameter change in the sequence."""

    msb: int
    lsb: int
    value: int | float  # raw value or float (bridge normalizes)


@dataclass
class TempoEvent:
    """Tempo change at a specific time."""

    bpm: float


@dataclass
class SequenceEvent:
    """A single event in a track at a specific time."""

    at: float  # time in beats from track start
    note_on: NoteEvent | None = None
    note_off: NoteEvent | None = None  # explicit note-off with time
    control: ControlEvent | None = None
    nrpn: NRPNEvent | None = None
    program: str | int | None = None
    tempo: float | None = None  # bpm (global, on first track)
    text: str | None = None  # lyric, marker, etc.
    pitch_bend: int | None = None  # -8192..8191 (14-bit, 0=center)
    channel_pressure: int | None = None  # 0-127 channel aftertouch
    poly_pressure: list[tuple[int, int]] | None = None  # [(note, pressure), ...]
    sysex: list[int] | None = None  # raw SysEx bytes (without F0/F7 envelope)


@dataclass
class Track:
    """A sequence track (analogous to a MIDI track)."""

    name: str | None = None
    channel: int | None = None  # MIDI channel 0-15
    port: int = 0  # MIDI port (flat channel = port * 16 + channel)
    program: str | int | None = None  # initial program
    volume: int | None = 100  # initial volume
    pan: str | int | None = None  # initial pan
    events: list[SequenceEvent] = field(default_factory=list)


@dataclass
class Sequence:
    """A named composition (analogous to a MIDI file's single sequence)."""

    name: str | None = None
    tempo: float | None = 120.0  # default BPM
    time_signature: tuple[int, int] | None = None  # (4, 4)
    tracks: list[Track] = field(default_factory=list)


# =============================================================================
# Root Document
# =============================================================================


@dataclass
class XGMLConfig:
    """Complete XGML document — the root data model.

    Both presets (goal 1) and compositions (goal 2) use the same document
    structure; sections are independently optional.
    """

    version: str = "3.0"
    description: str | None = None
    meta: Meta | None = None

    # Goal 1: Synthesizer configuration
    basic_messages: BasicMessages | None = None
    channel_parameters: dict[int, ChannelConfig] | None = None  # channel → config
    drum_parameters: DrumConfig | None = None
    effects: EffectsConfig | None = None
    system_exclusive: list[SystemExclusive] | None = None
    synthesizer_core: SynthesizerCore | None = None
    scale_tuning: ScaleTuning | None = None

    # Roland GS configuration
    gs: GSConfig | None = None

    # Roland Jupiter-X configuration
    jupiter_x: JupiterXConfig | None = None

    # Goal 2: Musical composition
    sequences: dict[str, Sequence] | None = None  # name → sequence
