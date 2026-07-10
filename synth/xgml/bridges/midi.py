"""
MIDI Bridge — XGMLConfig → list[MIDIMessage].

Translates typed XGMLConfig into a sequence of MIDIMessage objects suitable
for feeding to ModernXGSynthesizer or sending over MIDI.

NRPN parameter addresses are imported from synth/protocols/xg/xg_nrpn_definitions,
the single source of truth for (MSB, LSB) mappings.
"""

from __future__ import annotations

import logging
from typing import Any

from synth.io.midi import MIDIMessage
from synth.protocols.xg.xg_nrpn_definitions import (
    AMP_ENV_ATTACK,
    AMP_ENV_DECAY,
    AMP_ENV_KEY_SCALING,
    AMP_ENV_RELEASE,
    AMP_ENV_SUSTAIN,
    AMP_ENV_VELOCITY_SENSE,
    CHANNEL_PAN_COARSE,
    CHANNEL_PITCH_BEND_RANGE,
    CHANNEL_PITCH_COARSE,
    CHANNEL_PITCH_FINE,
    CHANNEL_VOLUME_COARSE,
    CHORUS_DEPTH,
    CHORUS_FEEDBACK,
    CHORUS_LEVEL,
    CHORUS_RATE,
    CHORUS_TYPE,
    DrumNoteParam,
    FILTER_CUTOFF,
    FILTER_ENV_ATTACK,
    FILTER_ENV_DECAY,
    FILTER_ENV_RELEASE,
    FILTER_ENV_SUSTAIN,
    FILTER_KEY_SCALING,
    FILTER_RESONANCE,
    FILTER_TYPE,
    FILTER_VELOCITY_SENSITIVITY,
    INSERTION_CONNECTION,
    LFO1_AMP_DEPTH,
    LFO1_DELAY,
    LFO1_FILTER_DEPTH,
    LFO1_PITCH_DEPTH,
    LFO1_SPEED,
    LFO1_WAVEFORM,
    LFO2_AMP_DEPTH,
    LFO2_DELAY,
    LFO2_FILTER_DEPTH,
    LFO2_PITCH_DEPTH,
    LFO2_SPEED,
    LFO2_WAVEFORM,
    MASTER_TUNE,
    MASTER_TRANSPOSE,
    REVERB_HF_DAMPING,
    REVERB_LEVEL,
    REVERB_PRE_DELAY,
    REVERB_TIME,
    REVERB_TYPE,
    SCALE_TUNE_A,
    SCALE_TUNE_AS,
    SCALE_TUNE_B,
    SCALE_TUNE_C,
    SCALE_TUNE_CS,
    SCALE_TUNE_D,
    SCALE_TUNE_DS,
    SCALE_TUNE_E,
    SCALE_TUNE_F,
    SCALE_TUNE_FS,
    SCALE_TUNE_G,
    SCALE_TUNE_GS,
    SEND_CHORUS,
    SEND_DRY_LEVEL,
    SEND_REVERB,
    SEND_VARIATION,
    TEMPERAMENT_SELECT,
    VARIATION_PARAM_1,
    VARIATION_PARAM_2,
    VARIATION_PARAM_3,
    VARIATION_PARAM_4,
    VARIATION_PARAM_5,
    VARIATION_TYPE,
    drum_note_address,
    float_to_nrpn_value,
    midi_note_to_name,
    note_name_to_midi,
    part_mode,
    part_reverb_send,
    part_chorus_send,
    part_variation_send,
    part_voice_reserve,
)
from synth.xgml.types import (
    BasicMessages,
    ChannelConfig,
    ChannelSetup,
    ChorusConfig,
    DrumConfig,
    DrumNoteParams,
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
    ReverbConfig,
    ScaleTuning,
    Sequence,
    SequenceEvent,
    SystemExclusive,
    Track,
    VariationConfig,
    XGMLConfig,
)

logger = logging.getLogger(__name__)

# NRPN requires three CC messages per value: NRPN MSB (CC 99), NRPN LSB (CC 98), Data Entry (CC 6)
MIDI_CHANNELS_PER_PORT = 16


def flat_channel(port: int, channel: int) -> int:
    """Convert (port, channel) pair to a flat synthesizer channel index.

    Port 0, channel 0-15 → 0-15
    Port 1, channel 0-15 → 16-31
    etc.
    """
    return port * MIDI_CHANNELS_PER_PORT + channel


CC_NRPN_MSB = 99
CC_NRPN_LSB = 98
CC_DATA_ENTRY = 6
CC_DATA_ENTRY_LSB = 38  # Fine adjustment (rarely used for XG)
RPN_COARSE = 101  # RPN MSB
RPN_LSB = 100  # RPN LSB


# ---------------------------------------------------------------------------
# Helper: emit a single NRPN value as three control_change messages
# ---------------------------------------------------------------------------

def _nrpn(msb: int, lsb: int, value: int, channel: int, ts: float) -> list[MIDIMessage]:
    return [
        MIDIMessage("control_change", channel, {"controller": CC_NRPN_MSB, "value": msb}, timestamp=ts),
        MIDIMessage("control_change", channel, {"controller": CC_NRPN_LSB, "value": lsb}, timestamp=ts),
        MIDIMessage("control_change", channel, {"controller": CC_DATA_ENTRY, "value": max(0, min(127, value))}, timestamp=ts),
    ]


def _nrpn_jx(msb: int, lsb: int, value: int, ts: float) -> list[MIDIMessage]:
    """Emit Jupiter-X NRPN message sequence (channel 0, global).

    Jupiter-X uses standard NRPN CCs (CC 99=NRPN MSB, CC 98=NRPN LSB,
    CC 6=Data Entry MSB) on channel 0 for global/part parameter access.
    The part number is encoded in the MSB itself.
    """
    return [
        MIDIMessage("control_change", 0, {"controller": CC_NRPN_MSB, "value": msb}, timestamp=ts),
        MIDIMessage("control_change", 0, {"controller": CC_NRPN_LSB, "value": lsb}, timestamp=ts),
        MIDIMessage("control_change", 0, {"controller": CC_DATA_ENTRY, "value": max(0, min(127, value))}, timestamp=ts),
    ]


def _rpn(msb: int, lsb: int, value: int, channel: int, ts: float) -> list[MIDIMessage]:
    return [
        MIDIMessage("control_change", channel, {"controller": RPN_COARSE, "value": msb}, timestamp=ts),
        MIDIMessage("control_change", channel, {"controller": RPN_LSB, "value": lsb}, timestamp=ts),
        MIDIMessage("control_change", channel, {"controller": CC_DATA_ENTRY, "value": max(0, min(127, value))}, timestamp=ts),
    ]


def _cc(controller: int, value: int, channel: int, ts: float) -> MIDIMessage:
    return MIDIMessage("control_change", channel, {"controller": controller, "value": max(0, min(127, value))}, timestamp=ts)


def _program_change(program: int, channel: int, ts: float) -> MIDIMessage:
    return MIDIMessage("program_change", channel, {"program": max(0, min(127, program))}, timestamp=ts)


def _pitch_bend(value: int, channel: int, ts: float) -> MIDIMessage:
    return MIDIMessage("pitch_bend", channel, {"value": max(0, min(16383, value + 8192))}, timestamp=ts)


# ---------------------------------------------------------------------------
# GS SysEx helpers
# ---------------------------------------------------------------------------

GS_MANUFACTURER = 0x41  # Roland
GS_MODEL_ID = 0x42  # GS
GS_CMD_DATA_SET = 0x12  # Data Set (GS Reset)


def _gs_sysex(addr_high: int, addr_mid: int, addr_low: int, value: int, ts: float) -> MIDIMessage:
    """Build a Roland GS SysEx data set message.

    Format: F0 41 <device_id> 42 12 <addr_high> <addr_mid> <addr_low> <value> <checksum> F7
    Returns a MIDIMessage with the full byte array.
    """
    device_id = 0x00  # All devices
    data = [GS_MANUFACTURER, device_id, GS_MODEL_ID, GS_CMD_DATA_SET,
            addr_high & 0x7F, addr_mid & 0x7F, addr_low & 0x7F, value & 0x7F]
    # Calculate Roland checksum: sum of address + data bytes, & 0x7F, then 128 - that
    checksum = 128 - (sum(data[4:]) & 0x7F)
    if checksum == 128:
        checksum = 0
    data.append(checksum & 0x7F)
    return MIDIMessage("system_exclusive", 0, {"data": data}, timestamp=ts)


def _gs_part_sysex(part_num: int, param_offset: int, value: int, ts: float) -> MIDIMessage:
    """Build a GS part parameter SysEx message.

    Address: 0x01 nn xx where nn=part_num+1, xx=param_offset
    """
    return _gs_sysex(0x01, part_num + 1, param_offset, value, ts)


def _note_on(note: int, velocity: int, channel: int, ts: float) -> MIDIMessage:
    return MIDIMessage("note_on", channel, {"note": note, "velocity": velocity}, timestamp=ts)


def _note_off(note: int, velocity: int, channel: int, ts: float) -> MIDIMessage:
    return MIDIMessage("note_off", channel, {"note": note, "velocity": velocity}, timestamp=ts)


# ---------------------------------------------------------------------------
# Default MIDI CC numbers for common XG controllers
# ---------------------------------------------------------------------------

CC_VOLUME = 7
CC_PAN = 10
CC_EXPRESSION = 11
CC_REVERB_SEND = 91
CC_CHORUS_SEND = 93
CC_VARIATION_SEND = 94
CC_MODULATION = 1
CC_BANK_MSB = 0
CC_BANK_LSB = 32
CC_HOLD = 64
CC_PORTAMENTO = 65
CC_SOSTENUTO = 66
CC_SOFT_PEDAL = 67


def _resolve_pan(pan: str | int | None) -> int | None:
    """Resolve pan value: 'center' → 64, 'left' → 0, 'right' → 127, int → int."""
    if pan is None:
        return None
    if isinstance(pan, int):
        return max(0, min(127, pan))
    name = pan.lower()
    if name == "center":
        return 64
    elif name == "left":
        return 0
    elif name == "right":
        return 127
    elif name == "left_center":
        return 32
    elif name == "right_center":
        return 96
    # Try to parse numeric string
    try:
        return max(0, min(127, int(pan)))
    except (ValueError, TypeError):
        return 64  # default center


# ===========================================================================
# Main bridge
# ===========================================================================


class XGMLMIDIBridge:
    """Converts XGMLConfig → list[MIDIMessage].

    Handles both preset configuration (Goal 1, all at time 0) and
    sequences (Goal 2, time-bound events).

    Usage:
        bridge = XGMLMIDIBridge()
        messages = bridge.translate(config, base_timestamp=0.0)
    """

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def translate(self, config: XGMLConfig, base_timestamp: float = 0.0) -> list[MIDIMessage]:
        """Translate XGMLConfig into a sorted list of MIDI messages.

        Args:
            config: The XGMLConfig to translate.
            base_timestamp: Starting timestamp for all messages (0.0 for preset).

        Returns:
            Sorted list of MIDIMessage objects.
        """
        self.errors.clear()
        self.warnings.clear()

        messages: list[MIDIMessage] = []
        ts = base_timestamp

        try:
            # Goal 1: Preset configuration (all at base_timestamp)
            if config.basic_messages is not None:
                messages.extend(self._translate_basic_messages(config.basic_messages, ts))

            if config.channel_parameters is not None:
                for ch, cfg in config.channel_parameters.items():
                    messages.extend(self._translate_channel_config(ch, cfg, ts))

            if config.drum_parameters is not None:
                messages.extend(self._translate_drum_config(config.drum_parameters, ts))

            if config.effects is not None:
                messages.extend(self._translate_effects(config.effects, ts))

            if config.gs is not None:
                messages.extend(self._translate_gs_config(config.gs, ts))

            if config.jupiter_x is not None:
                messages.extend(self._translate_jupiter_x_config(config.jupiter_x, ts))

            if config.scale_tuning is not None:
                messages.extend(self._translate_scale_tuning(config.scale_tuning, ts))

            if config.system_exclusive is not None:
                messages.extend(self._translate_system_exclusive(config.system_exclusive, ts))

            # Goal 2: Sequences (time-bound)
            if config.sequences is not None:
                for seq in config.sequences.values():
                    messages.extend(self._translate_sequence(seq, ts))

        except Exception as e:
            self.errors.append(f"Translation error: {e}")
            logger.exception("XGML MIDI bridge translation failed")

        messages.sort(key=lambda m: m.timestamp)
        return messages

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    # ------------------------------------------------------------------
    # Basic Messages (program change, CC, pitch bend)
    # ------------------------------------------------------------------

    def _translate_basic_messages(self, basic: BasicMessages, ts: float) -> list[MIDIMessage]:
        msgs: list[MIDIMessage] = []
        for ch, setup in basic.channels.items():
            msgs.extend(self._translate_channel_setup(ch, setup, ts))
        return msgs

    def _translate_channel_setup(self, ch: int, setup: ChannelSetup, ts: float) -> list[MIDIMessage]:
        msgs: list[MIDIMessage] = []

        # Bank select (must come before program change)
        if setup.bank_msb is not None:
            msgs.append(_cc(CC_BANK_MSB, setup.bank_msb, ch, ts))
        if setup.bank_lsb is not None:
            msgs.append(_cc(CC_BANK_LSB, setup.bank_lsb, ch, ts))

        # Program change
        if setup.program is not None:
            prog = self._resolve_program(setup.program)
            if prog is not None:
                msgs.append(_program_change(prog, ch, ts))

        # Volume
        if setup.volume is not None:
            msgs.append(_cc(CC_VOLUME, setup.volume, ch, ts))

        # Pan
        pan = _resolve_pan(setup.pan)
        if pan is not None:
            msgs.append(_cc(CC_PAN, pan, ch, ts))

        # Expression
        if setup.expression is not None:
            msgs.append(_cc(CC_EXPRESSION, setup.expression, ch, ts))

        # Effects sends (XG-specific CCs)
        if setup.reverb_send is not None:
            msgs.append(_cc(CC_REVERB_SEND, setup.reverb_send, ch, ts))
        if setup.chorus_send is not None:
            msgs.append(_cc(CC_CHORUS_SEND, setup.chorus_send, ch, ts))
        if setup.variation_send is not None:
            msgs.append(_cc(CC_VARIATION_SEND, setup.variation_send, ch, ts))

        # RPN: Pitch bend range
        if setup.pitch_bend_range is not None:
            msgs.extend(_rpn(0, 0, setup.pitch_bend_range, ch, ts))

        # RPN: Tuning
        if setup.master_tune is not None:
            msgs.extend(_rpn(0, 1, setup.master_tune + 64, ch, ts))  # -64..63 → 0..127
        if setup.fine_tune is not None:
            msgs.extend(_rpn(0, 1, setup.fine_tune + 64, ch, ts))
        if setup.coarse_tune is not None:
            msgs.extend(_rpn(0, 2, setup.coarse_tune + 64, ch, ts))

        # CC: Switches
        if setup.hold is not None:
            msgs.append(_cc(CC_HOLD, setup.hold, ch, ts))
        if setup.portamento is not None:
            msgs.append(_cc(CC_PORTAMENTO, 127 if setup.portamento else 0, ch, ts))
        if setup.sostenuto is not None:
            msgs.append(_cc(CC_SOSTENUTO, 127 if setup.sostenuto else 0, ch, ts))
        if setup.soft_pedal is not None:
            msgs.append(_cc(CC_SOFT_PEDAL, 127 if setup.soft_pedal else 0, ch, ts))

        # Portamento time
        if setup.portamento_time is not None:
            msgs.append(_cc(5, setup.portamento_time, ch, ts))

        # Voice reserve (NRPN MSB 42)
        if setup.voice_reserve is not None:
            addr = part_voice_reserve(ch)
            msgs.extend(_nrpn(addr.msb, addr.lsb, setup.voice_reserve, ch, ts))

        # Part mode (NRPN MSB 43)
        if setup.part_mode is not None:
            addr = part_mode(ch)
            val = 0 if setup.part_mode.lower() == "single" else 1
            msgs.extend(_nrpn(addr.msb, addr.lsb, val, ch, ts))

        return msgs

    # ------------------------------------------------------------------
    # Channel Configuration (XG NRPN MSB 3-19)
    # ------------------------------------------------------------------

    def _translate_channel_config(self, ch: int, cfg: ChannelConfig, ts: float) -> list[MIDIMessage]:
        msgs: list[MIDIMessage] = []

        # Filter (MSB 5-6)
        if cfg.filter is not None:
            msgs.extend(self._translate_filter(cfg.filter, ch, ts))

        # LFO (MSB 9-10)
        if cfg.lfo is not None:
            if "lfo1" in cfg.lfo:
                msgs.extend(self._translate_lfo(cfg.lfo["lfo1"], 9, ch, ts))
            if "lfo2" in cfg.lfo:
                msgs.extend(self._translate_lfo(cfg.lfo["lfo2"], 10, ch, ts))

        # Amp Envelope (MSB 7-8)
        if cfg.amp_envelope is not None:
            ae = cfg.amp_envelope
            if ae.attack is not None:
                msgs.extend(_nrpn(AMP_ENV_ATTACK.msb, AMP_ENV_ATTACK.lsb, ae.attack, ch, ts))
            if ae.decay is not None:
                msgs.extend(_nrpn(AMP_ENV_DECAY.msb, AMP_ENV_DECAY.lsb, ae.decay, ch, ts))
            if ae.sustain is not None:
                msgs.extend(_nrpn(AMP_ENV_SUSTAIN.msb, AMP_ENV_SUSTAIN.lsb, ae.sustain, ch, ts))
            if ae.release is not None:
                msgs.extend(_nrpn(AMP_ENV_RELEASE.msb, AMP_ENV_RELEASE.lsb, ae.release, ch, ts))
            if ae.velocity_sensitivity is not None:
                msgs.extend(_nrpn(AMP_ENV_VELOCITY_SENSE.msb, AMP_ENV_VELOCITY_SENSE.lsb, ae.velocity_sensitivity, ch, ts))
            if ae.key_scaling is not None:
                msgs.extend(_nrpn(AMP_ENV_KEY_SCALING.msb, AMP_ENV_KEY_SCALING.lsb, ae.key_scaling, ch, ts))

        # Pitch (MSB 4)
        if cfg.pitch is not None:
            p = cfg.pitch
            if p.coarse is not None:
                msgs.extend(_nrpn(CHANNEL_PITCH_COARSE.msb, CHANNEL_PITCH_COARSE.lsb, p.coarse + 64, ch, ts))
            if p.fine is not None:
                msgs.extend(_nrpn(CHANNEL_PITCH_FINE.msb, CHANNEL_PITCH_FINE.lsb, p.fine + 64, ch, ts))

        # Effects sends (MSB 11)
        if cfg.effects_sends is not None:
            es = cfg.effects_sends
            if es.reverb is not None:
                msgs.extend(_nrpn(SEND_REVERB.msb, SEND_REVERB.lsb, es.reverb, ch, ts))
            if es.chorus is not None:
                msgs.extend(_nrpn(SEND_CHORUS.msb, SEND_CHORUS.lsb, es.chorus, ch, ts))
            if es.variation is not None:
                msgs.extend(_nrpn(SEND_VARIATION.msb, SEND_VARIATION.lsb, es.variation, ch, ts))
            if es.dry_level is not None:
                msgs.extend(_nrpn(SEND_DRY_LEVEL.msb, SEND_DRY_LEVEL.lsb, es.dry_level, ch, ts))

        # Mono/poly
        if cfg.mono_poly is not None:
            msgs.extend(_nrpn(CHANNEL_PITCH_COARSE.msb, 7, 0 if cfg.mono_poly == "poly" else 1, ch, ts))

        return msgs

    def _translate_filter(self, f: FilterParams, ch: int, ts: float) -> list[MIDIMessage]:
        msgs: list[MIDIMessage] = []
        if f.cutoff is not None:
            msgs.extend(_nrpn(FILTER_CUTOFF.msb, FILTER_CUTOFF.lsb, f.cutoff, ch, ts))
        if f.resonance is not None:
            msgs.extend(_nrpn(FILTER_RESONANCE.msb, FILTER_RESONANCE.lsb, f.resonance, ch, ts))
        if f.type is not None:
            ft_val = self._resolve_filter_type(f.type)
            if ft_val is not None:
                msgs.extend(_nrpn(FILTER_TYPE.msb, FILTER_TYPE.lsb, ft_val, ch, ts))
        if f.envelope_attack is not None:
            msgs.extend(_nrpn(FILTER_ENV_ATTACK.msb, FILTER_ENV_ATTACK.lsb, f.envelope_attack, ch, ts))
        if f.envelope_decay is not None:
            msgs.extend(_nrpn(FILTER_ENV_DECAY.msb, FILTER_ENV_DECAY.lsb, f.envelope_decay, ch, ts))
        if f.envelope_sustain is not None:
            msgs.extend(_nrpn(FILTER_ENV_SUSTAIN.msb, FILTER_ENV_SUSTAIN.lsb, f.envelope_sustain, ch, ts))
        if f.envelope_release is not None:
            msgs.extend(_nrpn(FILTER_ENV_RELEASE.msb, FILTER_ENV_RELEASE.lsb, f.envelope_release, ch, ts))
        if f.velocity_sensitivity is not None:
            msgs.extend(_nrpn(FILTER_VELOCITY_SENSITIVITY.msb, FILTER_VELOCITY_SENSITIVITY.lsb, f.velocity_sensitivity, ch, ts))
        if f.key_scaling is not None:
            msgs.extend(_nrpn(FILTER_KEY_SCALING.msb, FILTER_KEY_SCALING.lsb, f.key_scaling, ch, ts))
        return msgs

    def _translate_lfo(self, lfo: LFOParams, base_msb: int, ch: int, ts: float) -> list[MIDIMessage]:
        """Translate an LFO section. base_msb = 9 for LFO1, 10 for LFO2."""
        msgs: list[MIDIMessage] = []
        waveform = LFO1_WAVEFORM if base_msb == 9 else LFO2_WAVEFORM
        speed = LFO1_SPEED if base_msb == 9 else LFO2_SPEED
        delay = LFO1_DELAY if base_msb == 9 else LFO2_DELAY
        pitch_depth = LFO1_PITCH_DEPTH if base_msb == 9 else LFO2_PITCH_DEPTH
        filter_depth = LFO1_FILTER_DEPTH if base_msb == 9 else LFO2_FILTER_DEPTH
        amp_depth = LFO1_AMP_DEPTH if base_msb == 9 else LFO2_AMP_DEPTH

        if lfo.waveform is not None:
            wf_val = self._resolve_lfo_waveform(lfo.waveform)
            if wf_val is not None:
                msgs.extend(_nrpn(waveform.msb, waveform.lsb, wf_val, ch, ts))
        if lfo.speed is not None:
            msgs.extend(_nrpn(speed.msb, speed.lsb, lfo.speed, ch, ts))
        if lfo.delay is not None:
            msgs.extend(_nrpn(delay.msb, delay.lsb, lfo.delay, ch, ts))
        if lfo.pitch_depth is not None:
            msgs.extend(_nrpn(pitch_depth.msb, pitch_depth.lsb, lfo.pitch_depth, ch, ts))
        if lfo.filter_depth is not None:
            msgs.extend(_nrpn(filter_depth.msb, filter_depth.lsb, lfo.filter_depth, ch, ts))
        if lfo.amp_depth is not None:
            msgs.extend(_nrpn(amp_depth.msb, amp_depth.lsb, lfo.amp_depth, ch, ts))
        return msgs

    # ------------------------------------------------------------------
    # Drum Configuration (NRPN MSB 40-63)
    # ------------------------------------------------------------------

    def _translate_drum_config(self, drum: DrumConfig, ts: float) -> list[MIDIMessage]:
        msgs: list[MIDIMessage] = []
        ch = drum.channel if drum.channel is not None else 9  # default to channel 10

        # Kit number (MSB 40, LSB 0)
        if drum.kit_number is not None:
            msgs.extend(_nrpn(40, 0, drum.kit_number, ch, ts))

        # Per-note parameters (MSB 48-63)
        if drum.notes is not None:
            for note_num, note_params in drum.notes.items():
                msgs.extend(self._translate_drum_note(note_num, note_params, ch, ts))

        return msgs

    def _translate_drum_note(self, note_num: int, np: DrumNoteParams, ch: int, ts: float) -> list[MIDIMessage]:
        msgs: list[MIDIMessage] = []

        if np.pitch_coarse is not None:
            addr = drum_note_address(DrumNoteParam.PITCH_COARSE, note_num)
            msgs.extend(_nrpn(addr.msb, addr.lsb, np.pitch_coarse + 64, ch, ts))
        if np.pitch_fine is not None:
            addr = drum_note_address(DrumNoteParam.PITCH_FINE, note_num)
            msgs.extend(_nrpn(addr.msb, addr.lsb, np.pitch_fine + 64, ch, ts))
        if np.level is not None:
            addr = drum_note_address(DrumNoteParam.LEVEL, note_num)
            msgs.extend(_nrpn(addr.msb, addr.lsb, np.level, ch, ts))
        if np.pan is not None:
            addr = drum_note_address(DrumNoteParam.PAN, note_num)
            msgs.extend(_nrpn(addr.msb, addr.lsb, np.pan, ch, ts))
        if np.reverb_send is not None:
            addr = drum_note_address(DrumNoteParam.REVERB_SEND, note_num)
            msgs.extend(_nrpn(addr.msb, addr.lsb, np.reverb_send, ch, ts))
        if np.chorus_send is not None:
            addr = drum_note_address(DrumNoteParam.CHORUS_SEND, note_num)
            msgs.extend(_nrpn(addr.msb, addr.lsb, np.chorus_send, ch, ts))
        if np.variation_send is not None:
            addr = drum_note_address(DrumNoteParam.VARIATION_SEND, note_num)
            msgs.extend(_nrpn(addr.msb, addr.lsb, np.variation_send, ch, ts))
        if np.filter_cutoff is not None:
            addr = drum_note_address(DrumNoteParam.FILTER_CUTOFF, note_num)
            msgs.extend(_nrpn(addr.msb, addr.lsb, np.filter_cutoff, ch, ts))
        if np.filter_resonance is not None:
            addr = drum_note_address(DrumNoteParam.FILTER_RESONANCE, note_num)
            msgs.extend(_nrpn(addr.msb, addr.lsb, np.filter_resonance, ch, ts))
        if np.decay is not None:
            addr = drum_note_address(DrumNoteParam.DECAY_TIME, note_num)
            msgs.extend(_nrpn(addr.msb, addr.lsb, np.decay, ch, ts))
        if np.attack is not None:
            addr = drum_note_address(DrumNoteParam.ATTACK_TIME, note_num)
            msgs.extend(_nrpn(addr.msb, addr.lsb, np.attack, ch, ts))
        if np.alternate_group is not None:
            addr = drum_note_address(DrumNoteParam.ALTERNATE_GROUP, note_num)
            msgs.extend(_nrpn(addr.msb, addr.lsb, np.alternate_group, ch, ts))
        if np.mute_group is not None:
            addr = drum_note_address(DrumNoteParam.MUTE_GROUP, note_num)
            msgs.extend(_nrpn(addr.msb, addr.lsb, np.mute_group, ch, ts))

        return msgs

    # ------------------------------------------------------------------
    # Effects Configuration (MSB 1-2)
    # ------------------------------------------------------------------

    def _translate_effects(self, fx: EffectsConfig, ts: float) -> list[MIDIMessage]:
        msgs: list[MIDIMessage] = []
        if fx.reverb is not None:
            msgs.extend(self._translate_reverb(fx.reverb, ts))
        if fx.chorus is not None:
            msgs.extend(self._translate_chorus(fx.chorus, ts))
        if fx.variation is not None:
            msgs.extend(self._translate_variation(fx.variation, ts))
        if fx.insertion is not None:
            msgs.extend(self._translate_insertion(fx.insertion, ts))
        if fx.master_eq is not None:
            msgs.extend(self._translate_master_eq(fx.master_eq, ts))
        return msgs

    def _translate_reverb(self, rv: ReverbConfig, ts: float) -> list[MIDIMessage]:
        msgs: list[MIDIMessage] = []
        if rv.type is not None:
            t = self._resolve_reverb_type(rv.type)
            if t is not None:
                msgs.extend(_nrpn(REVERB_TYPE.msb, REVERB_TYPE.lsb, t, 0, ts))
        if rv.time is not None:
            val = float_to_nrpn_value(rv.time, 0.3, 30.0)
            msgs.extend(_nrpn(REVERB_TIME.msb, REVERB_TIME.lsb, val, 0, ts))
        if rv.level is not None:
            val = float_to_nrpn_value(rv.level, 0.0, 1.0)
            msgs.extend(_nrpn(REVERB_LEVEL.msb, REVERB_LEVEL.lsb, val, 0, ts))
        if rv.hf_damping is not None:
            val = float_to_nrpn_value(rv.hf_damping, 0.0, 1.0)
            msgs.extend(_nrpn(REVERB_HF_DAMPING.msb, REVERB_HF_DAMPING.lsb, val, 0, ts))
        if rv.pre_delay is not None:
            val = float_to_nrpn_value(rv.pre_delay, 0.0, 50.0)
            msgs.extend(_nrpn(REVERB_PRE_DELAY.msb, REVERB_PRE_DELAY.lsb, val, 0, ts))
        return msgs

    def _translate_chorus(self, ch: ChorusConfig, ts: float) -> list[MIDIMessage]:
        msgs: list[MIDIMessage] = []
        if ch.type is not None:
            t = self._resolve_chorus_type(ch.type)
            if t is not None:
                msgs.extend(_nrpn(CHORUS_TYPE.msb, CHORUS_TYPE.lsb, t + 0x40, 0, ts))  # chorus types 0x40-0x51
        if ch.rate is not None:
            val = float_to_nrpn_value(ch.rate, 0.0, 39.7)
            msgs.extend(_nrpn(CHORUS_RATE.msb, CHORUS_RATE.lsb, val, 0, ts))
        if ch.depth is not None:
            val = float_to_nrpn_value(ch.depth, 0.0, 1.0)
            msgs.extend(_nrpn(CHORUS_DEPTH.msb, CHORUS_DEPTH.lsb, val, 0, ts))
        if ch.feedback is not None:
            val = float_to_nrpn_value(ch.feedback, -1.0, 1.0)
            msgs.extend(_nrpn(CHORUS_FEEDBACK.msb, CHORUS_FEEDBACK.lsb, val, 0, ts))
        if ch.level is not None:
            val = float_to_nrpn_value(ch.level, 0.0, 1.0)
            msgs.extend(_nrpn(CHORUS_LEVEL.msb, CHORUS_LEVEL.lsb, val, 0, ts))
        return msgs

    def _translate_variation(self, var: VariationConfig, ts: float) -> list[MIDIMessage]:
        msgs: list[MIDIMessage] = []
        if var.type is not None:
            msgs.extend(_nrpn(VARIATION_TYPE.msb, VARIATION_TYPE.lsb, max(0, min(127, var.type)), 0, ts))
        if var.level is not None:
            val = float_to_nrpn_value(var.level, 0.0, 1.0)
            msgs.extend(_nrpn(VARIATION_PARAM_1.msb, VARIATION_PARAM_1.lsb, val, 0, ts))
        if var.params:
            # Generic parameter passthrough (params are effect-specific)
            for i, (key, pval) in enumerate(sorted(var.params.items())):
                if i >= 5:
                    break
                addr = [VARIATION_PARAM_1, VARIATION_PARAM_2, VARIATION_PARAM_3, VARIATION_PARAM_4, VARIATION_PARAM_5][i]
                v = float_to_nrpn_value(float(pval), 0.0, 1.0) if isinstance(pval, float) and 0.0 <= pval <= 1.0 else int(pval)
                msgs.extend(_nrpn(addr.msb, addr.lsb, max(0, min(127, v)), 0, ts))
        return msgs

    def _translate_insertion(self, insertion: dict[int, InsertionSlot], ts: float) -> list[MIDIMessage]:
        """Translate insertion effect slots to NRPN messages.

        Each channel can have an insertion effect connected.
        Uses INSERTION_CONNECTION (MSB 11, LSB 6) to enable/disable per channel,
        and system-level NRPN for effect type/parameters.
        """
        msgs: list[MIDIMessage] = []
        for ch, slot in insertion.items():
            # Connection on/off (0 = through/off, 1 = insertion on)
            msgs.extend(_nrpn(INSERTION_CONNECTION.msb, INSERTION_CONNECTION.lsb, 0 if slot.bypass else 1, ch, ts))
            if slot.type is not None:
                t = slot.type if isinstance(slot.type, int) else 0
                msgs.extend(_nrpn(31, 0, max(0, min(127, t)), ch, ts))
            if slot.params:
                # Up to 5 parameters mapped to MSB 33-35
                for i, (key, pval) in enumerate(sorted(slot.params.items())):
                    if i >= 5:
                        break
                    # Parameters 1-2 use MSB 33, 3-4 use MSB 34, 5 uses MSB 35
                    addr_msb = 33 + (i // 2)
                    addr_lsb = i % 2
                    v = float_to_nrpn_value(float(pval), 0.0, 1.0) if isinstance(pval, float) and 0.0 <= pval <= 1.0 else int(pval)
                    msgs.extend(_nrpn(addr_msb, addr_lsb, max(0, min(127, v)), ch, ts))
        return msgs

    def _translate_master_eq(self, eq: EQConfig, ts: float) -> list[MIDIMessage]:
        """Translate master EQ to NRPN messages.

        XG master EQ uses NRPN with specific MSB/LSB for each band.
        """
        msgs: list[MIDIMessage] = []
        if eq.low_gain is not None:
            v = float_to_nrpn_value(eq.low_gain, -12.0, 12.0)
            msgs.extend(_nrpn(4, 10, v, 0, ts))
        if eq.low_mid_gain is not None:
            v = float_to_nrpn_value(eq.low_mid_gain, -12.0, 12.0)
            msgs.extend(_nrpn(4, 11, v, 0, ts))
        if eq.mid_gain is not None:
            v = float_to_nrpn_value(eq.mid_gain, -12.0, 12.0)
            msgs.extend(_nrpn(4, 12, v, 0, ts))
        if eq.mid_freq is not None:
            v = float_to_nrpn_value(eq.mid_freq, 100.0, 10000.0)
            msgs.extend(_nrpn(4, 13, v, 0, ts))
        if eq.high_mid_gain is not None:
            v = float_to_nrpn_value(eq.high_mid_gain, -12.0, 12.0)
            msgs.extend(_nrpn(4, 14, v, 0, ts))
        if eq.high_gain is not None:
            v = float_to_nrpn_value(eq.high_gain, -12.0, 12.0)
            msgs.extend(_nrpn(4, 15, v, 0, ts))
        if eq.q_factor is not None:
            v = float_to_nrpn_value(eq.q_factor, 0.1, 10.0)
            msgs.extend(_nrpn(4, 16, v, 0, ts))
        return msgs

    def _translate_scale_tuning(self, st: ScaleTuning, ts: float) -> list[MIDIMessage]:
        """Translate scale/micro-tuning to NRPN messages.

        MSB 17: C through F# (notes 0-6)
        MSB 18: G through B (notes 7-11) + master tune + transpose + temperament
        """
        msgs: list[MIDIMessage] = []
        # MSB 17: C, C#, D, D#, E, F, F#
        note_addrs_17 = [
            (SCALE_TUNE_C, st.c), (SCALE_TUNE_CS, st.c_sharp), (SCALE_TUNE_D, st.d),
            (SCALE_TUNE_DS, st.d_sharp), (SCALE_TUNE_E, st.e), (SCALE_TUNE_F, st.f),
            (SCALE_TUNE_FS, st.f_sharp),
        ]
        for addr, val in note_addrs_17:
            if val is not None:
                msgs.extend(_nrpn(addr.msb, addr.lsb, max(0, min(127, val + 64)), 0, ts))

        # MSB 18: G, G#, A, A#, B
        note_addrs_18 = [
            (SCALE_TUNE_G, st.g), (SCALE_TUNE_GS, st.g_sharp), (SCALE_TUNE_A, st.a),
            (SCALE_TUNE_AS, st.a_sharp), (SCALE_TUNE_B, st.b),
        ]
        for addr, val in note_addrs_18:
            if val is not None:
                msgs.extend(_nrpn(addr.msb, addr.lsb, max(0, min(127, val + 64)), 0, ts))

        # Master tune (MSB 18, LSB 4)
        if st.master_tune is not None:
            msgs.extend(_nrpn(MASTER_TUNE.msb, MASTER_TUNE.lsb, max(0, min(127, st.master_tune + 64)), 0, ts))

        # Transpose (MSB 18, LSB 5)
        if st.transpose is not None:
            msgs.extend(_nrpn(MASTER_TRANSPOSE.msb, MASTER_TRANSPOSE.lsb, max(0, min(127, st.transpose + 64)), 0, ts))

        # Temperament select (MSB 18, LSB 6)
        if st.temperament is not None:
            t_val = st.temperament if isinstance(st.temperament, int) else 0
            msgs.extend(_nrpn(TEMPERAMENT_SELECT.msb, TEMPERAMENT_SELECT.lsb, max(0, min(127, t_val)), 0, ts))

        return msgs

    def _translate_system_exclusive(self, sysex: list[SystemExclusive], ts: float) -> list[MIDIMessage]:
        """Translate system exclusive messages."""
        msgs: list[MIDIMessage] = []
        for msg in sysex:
            data = [msg.manufacturer, msg.device] + msg.data
            msgs.append(MIDIMessage("system_exclusive", 0, {"data": data}, timestamp=ts))
        return msgs

    # ------------------------------------------------------------------
    # GS Configuration (Roland)
    # ------------------------------------------------------------------

    def _translate_gs_config(self, gs: GSConfig, ts: float) -> list[MIDIMessage]:
        """Translate GS configuration to MIDI SysEx messages."""
        msgs: list[MIDIMessage] = []

        if gs.system is not None:
            msgs.extend(self._translate_gs_system(gs.system, ts))

        if gs.parts is not None:
            for part_num, part_cfg in gs.parts.items():
                msgs.extend(self._translate_gs_part(part_num, part_cfg, ts))

        if gs.effects is not None:
            msgs.extend(self._translate_gs_effects(gs.effects, ts))

        if gs.drum_parts is not None:
            for part_num, drum_cfg in gs.drum_parts.items():
                msgs.extend(self._translate_gs_drum_part(part_num, drum_cfg, ts))

        return msgs

    def _translate_gs_system(self, sys: GSSystemConfig, ts: float) -> list[MIDIMessage]:
        """Translate GS system parameters to SysEx."""
        msgs: list[MIDIMessage] = []
        if sys.master_tune is not None:
            msgs.append(_gs_sysex(0x00, 0x00, 0x00, sys.master_tune + 64, ts))
        if sys.master_volume is not None:
            msgs.append(_gs_sysex(0x00, 0x00, 0x01, sys.master_volume, ts))
        if sys.master_transpose is not None:
            msgs.append(_gs_sysex(0x00, 0x00, 0x02, sys.master_transpose + 24, ts))
        return msgs

    def _translate_gs_part(self, part_num: int, part: GSPartConfig, ts: float) -> list[MIDIMessage]:
        """Translate a single GS part configuration to SysEx and CC messages."""
        msgs: list[MIDIMessage] = []
        ch = part_num  # GS part number = MIDI channel

        # GS uses both SysEx and standard MIDI messages
        if part.program is not None:
            msgs.append(_program_change(part.program, ch, ts))
        if part.volume is not None:
            msgs.append(_cc(CC_VOLUME, part.volume, ch, ts))
        if part.pan is not None:
            msgs.append(_cc(CC_PAN, part.pan, ch, ts))

        # GS SysEx part parameters (address 0x01 nn xx)
        if part.bank_msb is not None:
            msgs.append(_gs_part_sysex(ch, 0x00, part.bank_msb, ts))
        if part.bank_lsb is not None:
            msgs.append(_gs_part_sysex(ch, 0x01, part.bank_lsb, ts))
        if part.coarse_tune is not None:
            msgs.append(_gs_part_sysex(ch, 0x05, part.coarse_tune + 64, ts))
        if part.fine_tune is not None:
            msgs.append(_gs_part_sysex(ch, 0x06, part.fine_tune + 64, ts))
        if part.key_shift is not None:
            msgs.append(_gs_part_sysex(ch, 0x07, part.key_shift + 64, ts))
        if part.key_range_low is not None:
            msgs.append(_gs_part_sysex(ch, 0x08, part.key_range_low, ts))
        if part.key_range_high is not None:
            msgs.append(_gs_part_sysex(ch, 0x09, part.key_range_high, ts))
        if part.velocity_range_low is not None:
            msgs.append(_gs_part_sysex(ch, 0x0A, part.velocity_range_low, ts))
        if part.velocity_range_high is not None:
            msgs.append(_gs_part_sysex(ch, 0x0B, part.velocity_range_high, ts))
        if part.portamento is not None:
            msgs.append(_gs_part_sysex(ch, 0x0D, 1 if part.portamento else 0, ts))
        if part.portamento_time is not None:
            msgs.append(_gs_part_sysex(ch, 0x0E, part.portamento_time, ts))
        if part.bend_range is not None:
            msgs.append(_gs_part_sysex(ch, 0x0F, part.bend_range, ts))
        if part.filter_cutoff is not None:
            msgs.append(_gs_part_sysex(ch, 0x10, part.filter_cutoff, ts))
        if part.filter_resonance is not None:
            msgs.append(_gs_part_sysex(ch, 0x11, part.filter_resonance, ts))
        if part.attack_time is not None:
            msgs.append(_gs_part_sysex(ch, 0x12, part.attack_time, ts))
        if part.decay_time is not None:
            msgs.append(_gs_part_sysex(ch, 0x13, part.decay_time, ts))
        if part.release_time is not None:
            msgs.append(_gs_part_sysex(ch, 0x14, part.release_time, ts))
        if part.vibrato_rate is not None:
            msgs.append(_gs_part_sysex(ch, 0x15, part.vibrato_rate, ts))
        if part.vibrato_depth is not None:
            msgs.append(_gs_part_sysex(ch, 0x16, part.vibrato_depth, ts))
        if part.vibrato_delay is not None:
            msgs.append(_gs_part_sysex(ch, 0x17, part.vibrato_delay, ts))
        if part.reverb_send is not None:
            msgs.append(_gs_part_sysex(ch, 0x18, part.reverb_send, ts))
        if part.chorus_send is not None:
            msgs.append(_gs_part_sysex(ch, 0x19, part.chorus_send, ts))
        if part.rx_note is not None:
            msgs.append(_gs_part_sysex(ch, 0x1A, 1 if part.rx_note else 0, ts))
        if part.rx_pitch_bend is not None:
            msgs.append(_gs_part_sysex(ch, 0x1B, 1 if part.rx_pitch_bend else 0, ts))
        if part.rx_channel_pressure is not None:
            msgs.append(_gs_part_sysex(ch, 0x1C, 1 if part.rx_channel_pressure else 0, ts))
        if part.rx_poly_pressure is not None:
            msgs.append(_gs_part_sysex(ch, 0x1D, 1 if part.rx_poly_pressure else 0, ts))

        return msgs

    def _translate_gs_reverb_type(self, rt: str | int) -> int:
        """Resolve GS reverb type to 0-7 value."""
        if isinstance(rt, int):
            return max(0, min(7, rt))
        names = {
            "room1": 0, "room2": 1, "room3": 2, "hall1": 3,
            "hall2": 4, "plate": 5, "delay": 6, "panning_delay": 7,
        }
        return names.get(rt.lower(), 0)

    def _translate_gs_chorus_type(self, ct: str | int) -> int:
        """Resolve GS chorus type to 0-5 value."""
        if isinstance(ct, int):
            return max(0, min(5, ct))
        names = {
            "chorus1": 0, "chorus2": 1, "chorus3": 2,
            "chorus4": 3, "feedback": 4, "flanger": 5,
        }
        return names.get(ct.lower(), 0)

    def _translate_gs_effects(self, fx: GSEffectsConfig, ts: float) -> list[MIDIMessage]:
        """Translate GS effects to SysEx."""
        msgs: list[MIDIMessage] = []
        if fx.reverb is not None:
            rv = fx.reverb
            if rv.type is not None:
                msgs.append(_gs_sysex(0x05, 0x00, 0x00, self._translate_gs_reverb_type(rv.type), ts))
            if rv.level is not None:
                msgs.append(_gs_sysex(0x05, 0x00, 0x01, rv.level, ts))
            if rv.time is not None:
                msgs.append(_gs_sysex(0x05, 0x00, 0x02, rv.time, ts))
            if rv.feedback is not None:
                msgs.append(_gs_sysex(0x05, 0x00, 0x03, rv.feedback, ts))
            if rv.pre_delay is not None:
                msgs.append(_gs_sysex(0x05, 0x00, 0x04, rv.pre_delay, ts))
        if fx.chorus is not None:
            ch = fx.chorus
            if ch.type is not None:
                msgs.append(_gs_sysex(0x04, 0x00, 0x00, self._translate_gs_chorus_type(ch.type), ts))
            if ch.level is not None:
                msgs.append(_gs_sysex(0x04, 0x00, 0x01, ch.level, ts))
            if ch.rate is not None:
                msgs.append(_gs_sysex(0x04, 0x00, 0x02, ch.rate, ts))
            if ch.depth is not None:
                msgs.append(_gs_sysex(0x04, 0x00, 0x03, ch.depth, ts))
            if ch.feedback is not None:
                msgs.append(_gs_sysex(0x04, 0x00, 0x04, ch.feedback, ts))
        return msgs

    def _translate_gs_drum_part(self, part_num: int, drum: GSDrumPartConfig, ts: float) -> list[MIDIMessage]:
        """Translate GS drum part to SysEx."""
        msgs: list[MIDIMessage] = []
        if drum.map_low_note is not None:
            msgs.append(_gs_sysex(0x10, part_num + 1, 0x00, drum.map_low_note, ts))
        if drum.map_high_note is not None:
            msgs.append(_gs_sysex(0x10, part_num + 1, 0x01, drum.map_high_note, ts))
        if drum.pitch_offset is not None:
            msgs.append(_gs_sysex(0x10, part_num + 1, 0x02, drum.pitch_offset + 24, ts))
        if drum.level_offset is not None:
            msgs.append(_gs_sysex(0x10, part_num + 1, 0x03, drum.level_offset + 64, ts))
        if drum.pan_random is not None:
            msgs.append(_gs_sysex(0x10, part_num + 1, 0x04, drum.pan_random, ts))
        if drum.key_group is not None:
            msgs.append(_gs_sysex(0x10, part_num + 1, 0x05, drum.key_group + 1 if drum.key_group >= 0 else 0, ts))
        return msgs

    # ------------------------------------------------------------------
    # Jupiter-X Configuration (NRPN + SysEx)
    # ------------------------------------------------------------------

    def _translate_jupiter_x_config(self, jx: JupiterXConfig, ts: float) -> list[MIDIMessage]:
        """Translate complete Jupiter-X configuration to MIDI messages."""
        msgs: list[MIDIMessage] = []

        if jx.system is not None:
            msgs.extend(self._translate_jupiter_x_system(jx.system, ts))

        if jx.parts is not None:
            for part_num, part_cfg in jx.parts.items():
                msgs.extend(self._translate_jupiter_x_part(part_num, part_cfg, ts))

        if jx.effects is not None:
            msgs.extend(self._translate_jupiter_x_vcm(jx.effects, ts))

        if jx.arpeggiator is not None:
            msgs.extend(self._translate_jupiter_x_arp(jx.arpeggiator, ts))

        return msgs

    def _translate_jupiter_x_system(self, sys: JupiterXSystemConfig, ts: float) -> list[MIDIMessage]:
        """Translate Jupiter-X system parameters to NRPN (MSB 0x00).

        Mapping:
          LSB 0x01 = master_tune, 0x02 = master_transpose,
          0x03 = master_volume, 0x04 = master_pan
        """
        msgs: list[MIDIMessage] = []
        if sys.master_volume is not None:
            msgs.extend(_nrpn_jx(0x00, 0x03, sys.master_volume, ts))
        if sys.master_tune is not None:
            msgs.extend(_nrpn_jx(0x00, 0x01, sys.master_tune + 64, ts))
        if sys.master_transpose is not None:
            msgs.extend(_nrpn_jx(0x00, 0x02, sys.master_transpose + 64, ts))
        if sys.master_pan is not None:
            msgs.extend(_nrpn_jx(0x00, 0x04, sys.master_pan + 64, ts))
        return msgs

    def _translate_jupiter_x_part(self, part_num: int, part: JupiterXPartConfig, ts: float) -> list[MIDIMessage]:
        """Translate Jupiter-X part parameters to NRPN (MSB 0x10+part_num).

        Part-level NRPN LSBs:
          0x00 = level, 0x01 = pan, 0x06 = volume,
          0x07 = coarse_tune, 0x08 = fine_tune,
          0x0A = delay_send, 0x0B = reverb_send, 0x0C = chorus_send,
          0x13 = key_range_low, 0x14 = key_range_high
        """
        msgs: list[MIDIMessage] = []
        msb = 0x10 + part_num

        if part.level is not None:
            msgs.extend(_nrpn_jx(msb, 0x00, part.level, ts))
        if part.pan is not None:
            msgs.extend(_nrpn_jx(msb, 0x01, part.pan + 64, ts))
        if part.volume is not None:
            msgs.extend(_nrpn_jx(msb, 0x06, part.volume, ts))
        if part.coarse_tune is not None:
            msgs.extend(_nrpn_jx(msb, 0x07, part.coarse_tune + 64, ts))
        if part.fine_tune is not None:
            msgs.extend(_nrpn_jx(msb, 0x08, part.fine_tune + 64, ts))
        if part.key_range_low is not None:
            msgs.extend(_nrpn_jx(msb, 0x13, part.key_range_low, ts))
        if part.key_range_high is not None:
            msgs.extend(_nrpn_jx(msb, 0x14, part.key_range_high, ts))
        if part.reverb_send is not None:
            msgs.extend(_nrpn_jx(msb, 0x0B, part.reverb_send, ts))
        if part.chorus_send is not None:
            msgs.extend(_nrpn_jx(msb, 0x0C, part.chorus_send, ts))
        if part.delay_send is not None:
            msgs.extend(_nrpn_jx(msb, 0x0A, part.delay_send, ts))

        # Engine configurations per part
        if part.engines is not None:
            for engine_name, engine_cfg in part.engines.items():
                msgs.extend(self._translate_jupiter_x_engine(part_num, engine_name, engine_cfg, ts))

        # Per-part modulation blocks
        if part.lfo is not None:
            msgs.extend(self._translate_jupiter_x_lfo(part_num, part.lfo, ts))
        if part.envelope is not None:
            msgs.extend(self._translate_jupiter_x_envelope(part_num, part.envelope, ts))
        if part.modulation is not None:
            msgs.extend(self._translate_jupiter_x_modulation(part_num, part.modulation, ts))

        return msgs

    def _translate_jupiter_x_engine(
        self, part_num: int, engine_name: str, engine: JupiterXEngineConfig, ts: float
    ) -> list[MIDIMessage]:
        """Translate Jupiter-X engine parameters to NRPN (MSB 0x30-0x3F).

        Engine offset mapping:
          analog=0, digital=1, fm=2, external=3
        MSB = 0x30 + (part_num * 4) + engine_offset

        Common NRPN LSBs:
          0x00 = enable, 0x01 = level, 0x02 = pan, 0x03 = coarse_tune, 0x04 = fine_tune
        """
        engine_name_map = {"analog": 0, "digital": 1, "fm": 2, "external": 3}
        engine_offset = engine_name_map.get(engine_name.lower(), 0)
        msb = 0x30 + (part_num * 4) + engine_offset
        msgs: list[MIDIMessage] = []

        if engine.enable is not None:
            msgs.extend(_nrpn_jx(msb, 0x00, 1 if engine.enable else 0, ts))
        if engine.level is not None:
            msgs.extend(_nrpn_jx(msb, 0x01, engine.level, ts))
        if engine.pan is not None:
            msgs.extend(_nrpn_jx(msb, 0x02, engine.pan + 64, ts))
        if engine.coarse_tune is not None:
            msgs.extend(_nrpn_jx(msb, 0x03, engine.coarse_tune + 64, ts))
        if engine.fine_tune is not None:
            msgs.extend(_nrpn_jx(msb, 0x04, engine.fine_tune + 64, ts))

        # Additional engine-specific named parameters
        if engine.parameters is not None:
            for param_name, param_value in engine.parameters.items():
                # Pass through raw NRPN values for engine-specific params
                # Engine sub-classes define their own LSB mappings (> 0x04)
                pass

        return msgs

    def _translate_jupiter_x_lfo(self, part_num: int, lfo: JupiterXPartLFO, ts: float) -> list[MIDIMessage]:
        """Translate Jupiter-X LFO parameters to NRPN (MSB 0x60+part_num).

        LSB mapping:
          0x00 = waveform, 0x01 = rate, 0x02 = depth,
          0x03 = fade, 0x04 = key_trigger, 0x05 = delay
        """
        msb = 0x60 + part_num
        msgs: list[MIDIMessage] = []

        if lfo.waveform is not None:
            msgs.extend(_nrpn_jx(msb, 0x00, lfo.waveform, ts))
        if lfo.rate is not None:
            msgs.extend(_nrpn_jx(msb, 0x01, lfo.rate, ts))
        if lfo.depth is not None:
            msgs.extend(_nrpn_jx(msb, 0x02, lfo.depth, ts))
        if lfo.fade is not None:
            msgs.extend(_nrpn_jx(msb, 0x03, lfo.fade, ts))
        if lfo.key_trigger is not None:
            msgs.extend(_nrpn_jx(msb, 0x04, 1 if lfo.key_trigger else 0, ts))
        if lfo.delay is not None:
            msgs.extend(_nrpn_jx(msb, 0x05, lfo.delay, ts))

        return msgs

    def _translate_jupiter_x_envelope(self, part_num: int, env: JupiterXPartEnvelope, ts: float) -> list[MIDIMessage]:
        """Translate Jupiter-X envelope parameters to NRPN (MSB 0x70+part_num).

        LSB mapping:
          0x00 = attack, 0x01 = decay, 0x02 = sustain, 0x03 = release,
          0x04 = attack_curve, 0x05 = decay_curve, 0x06 = release_curve,
          0x07 = velocity_sensitivity
        """
        msb = 0x70 + part_num
        msgs: list[MIDIMessage] = []

        if env.attack is not None:
            msgs.extend(_nrpn_jx(msb, 0x00, env.attack, ts))
        if env.decay is not None:
            msgs.extend(_nrpn_jx(msb, 0x01, env.decay, ts))
        if env.sustain is not None:
            msgs.extend(_nrpn_jx(msb, 0x02, env.sustain, ts))
        if env.release is not None:
            msgs.extend(_nrpn_jx(msb, 0x03, env.release, ts))
        if env.attack_curve is not None:
            msgs.extend(_nrpn_jx(msb, 0x04, env.attack_curve, ts))
        if env.decay_curve is not None:
            msgs.extend(_nrpn_jx(msb, 0x05, env.decay_curve, ts))
        if env.release_curve is not None:
            msgs.extend(_nrpn_jx(msb, 0x06, env.release_curve, ts))
        if env.velocity_sensitivity is not None:
            msgs.extend(_nrpn_jx(msb, 0x07, env.velocity_sensitivity, ts))

        return msgs

    def _translate_jupiter_x_modulation(self, part_num: int, mod: JupiterXPartModulation, ts: float) -> list[MIDIMessage]:
        """Translate Jupiter-X modulation routing to NRPN (MSB 0x80+part_num).

        LSB mapping:
          0x00 = mod_wheel_depth, 0x01 = aftertouch_depth,
          0x02 = velocity_depth, 0x03 = key_tracking_depth,
          0x04 = super_knob_depth
        """
        msb = 0x80 + part_num
        msgs: list[MIDIMessage] = []

        if mod.mod_wheel_depth is not None:
            msgs.extend(_nrpn_jx(msb, 0x00, mod.mod_wheel_depth, ts))
        if mod.aftertouch_depth is not None:
            msgs.extend(_nrpn_jx(msb, 0x01, mod.aftertouch_depth, ts))
        if mod.velocity_depth is not None:
            msgs.extend(_nrpn_jx(msb, 0x02, mod.velocity_depth, ts))
        if mod.key_tracking_depth is not None:
            msgs.extend(_nrpn_jx(msb, 0x03, mod.key_tracking_depth, ts))
        if mod.super_knob_depth is not None:
            msgs.extend(_nrpn_jx(msb, 0x04, mod.super_knob_depth, ts))

        return msgs

    def _translate_jupiter_x_vcm(self, vcm: JupiterXVCMConfig, ts: float) -> list[MIDIMessage]:
        """Translate Jupiter-X VCM effects to SysEx (addresses 0x40-0x43).

        Uses the existing _gs_sysex helper since Jupiter-X uses Roland GS-style
        SysEx addresses for its VCM effects chain.

        Address mapping:
          0x40 0x00 = Reverb (type/level/time/density)
          0x40 0x01 = Chorus (type/level/rate/depth)
          0x40 0x02 = Delay (type/level/time/feedback)
          0x40 0x03 = Distortion (type/level/drive)
          0x40 0x04 = Phaser (polarity/rate/depth/level)
        """
        msgs: list[MIDIMessage] = []

        # Distortion (0x40 0x03)
        if vcm.distortion_type is not None:
            dtype = self._resolve_jx_vcm_type(vcm.distortion_type)
            msgs.append(_gs_sysex(0x40, 0x03, 0x00, dtype, ts))
        if vcm.distortion_drive is not None:
            msgs.append(_gs_sysex(0x40, 0x03, 0x02, vcm.distortion_drive, ts))
        if vcm.distortion_level is not None:
            msgs.append(_gs_sysex(0x40, 0x03, 0x01, vcm.distortion_level, ts))

        # Chorus (0x40 0x01)
        if vcm.chorus_type is not None:
            ctype = self._resolve_jx_vcm_type(vcm.chorus_type)
            msgs.append(_gs_sysex(0x40, 0x01, 0x00, ctype, ts))
        if vcm.chorus_rate is not None:
            msgs.append(_gs_sysex(0x40, 0x01, 0x02, vcm.chorus_rate, ts))
        if vcm.chorus_depth is not None:
            msgs.append(_gs_sysex(0x40, 0x01, 0x03, vcm.chorus_depth, ts))
        if vcm.chorus_level is not None:
            msgs.append(_gs_sysex(0x40, 0x01, 0x01, vcm.chorus_level, ts))

        # Delay (0x40 0x02)
        if vcm.delay_type is not None:
            dtype = self._resolve_jx_vcm_type(vcm.delay_type)
            msgs.append(_gs_sysex(0x40, 0x02, 0x00, dtype, ts))
        if vcm.delay_time is not None:
            msgs.append(_gs_sysex(0x40, 0x02, 0x02, vcm.delay_time, ts))
        if vcm.delay_feedback is not None:
            msgs.append(_gs_sysex(0x40, 0x02, 0x03, vcm.delay_feedback, ts))
        if vcm.delay_level is not None:
            msgs.append(_gs_sysex(0x40, 0x02, 0x01, vcm.delay_level, ts))

        # Reverb (0x40 0x00)
        if vcm.reverb_type is not None:
            rtype = self._resolve_jx_vcm_type(vcm.reverb_type)
            msgs.append(_gs_sysex(0x40, 0x00, 0x00, rtype, ts))
        if vcm.reverb_time is not None:
            msgs.append(_gs_sysex(0x40, 0x00, 0x02, vcm.reverb_time, ts))
        if vcm.reverb_level is not None:
            msgs.append(_gs_sysex(0x40, 0x00, 0x01, vcm.reverb_level, ts))
        if vcm.reverb_density is not None:
            msgs.append(_gs_sysex(0x40, 0x00, 0x03, vcm.reverb_density, ts))

        # Phaser (0x40 0x04)
        if vcm.phaser_polarity is not None:
            msgs.append(_gs_sysex(0x40, 0x04, 0x00, vcm.phaser_polarity, ts))
        if vcm.phaser_rate is not None:
            msgs.append(_gs_sysex(0x40, 0x04, 0x01, vcm.phaser_rate, ts))
        if vcm.phaser_depth is not None:
            msgs.append(_gs_sysex(0x40, 0x04, 0x02, vcm.phaser_depth, ts))
        if vcm.phaser_level is not None:
            msgs.append(_gs_sysex(0x40, 0x04, 0x03, vcm.phaser_level, ts))

        return msgs

    def _translate_jupiter_x_arp(
        self, arp: JupiterXArpConfig, ts: float, channel: int | None = None
    ) -> list[MIDIMessage]:
        """Translate Jupiter-X arpeggiator configuration to NRPN (MSB 0x50).

        NRPN LSB mapping:
          0x00 = enable, 0x01 = style, 0x02 = type, 0x03 = range,
          0x04 = rate, 0x05 = swing, 0x06 = latch, 0x07 = target,
          0x08 = tempo, 0x09 = gate_time, 0x0A = pattern_length
        """
        msgs: list[MIDIMessage] = []
        msb = 0x50  # Arpeggiator NRPN MSB base

        if arp.enable is not None:
            msgs.extend(_nrpn_jx(msb, 0x00, 1 if arp.enable else 0, ts))
        if arp.style is not None:
            msgs.extend(_nrpn_jx(msb, 0x01, arp.style, ts))
        if arp.type is not None:
            msgs.extend(_nrpn_jx(msb, 0x02, arp.type, ts))
        if arp.range is not None:
            msgs.extend(_nrpn_jx(msb, 0x03, arp.range, ts))
        if arp.rate is not None:
            msgs.extend(_nrpn_jx(msb, 0x04, arp.rate, ts))
        if arp.swing is not None:
            msgs.extend(_nrpn_jx(msb, 0x05, arp.swing + 64, ts))
        if arp.latch is not None:
            msgs.extend(_nrpn_jx(msb, 0x06, 1 if arp.latch else 0, ts))
        if arp.target is not None:
            msgs.extend(_nrpn_jx(msb, 0x07, arp.target, ts))
        if arp.tempo is not None:
            msgs.extend(_nrpn_jx(msb, 0x08, arp.tempo, ts))
        if arp.gate_time is not None:
            msgs.extend(_nrpn_jx(msb, 0x09, arp.gate_time, ts))
        if arp.pattern_length is not None:
            msgs.extend(_nrpn_jx(msb, 0x0A, arp.pattern_length, ts))

        return msgs

    def _resolve_jx_vcm_type(self, t: str | int) -> int:
        """Resolve Jupiter-X VCM effect type name to 0-7 integer value."""
        if isinstance(t, int):
            return max(0, min(7, t))
        names = {
            "off": 0,
            "type1": 1,
            "type2": 2,
            "type3": 3,
            "type4": 4,
            "type5": 5,
            "type6": 6,
            "type7": 7,
        }
        return names.get(t.lower(), 0)

    # ------------------------------------------------------------------
    # Sequences (Goal 2: time-bound events)
    # ------------------------------------------------------------------

    def _translate_sequence(self, seq: Sequence, base_ts: float) -> list[MIDIMessage]:
        msgs: list[MIDIMessage] = []
        for track in seq.tracks:
            msgs.extend(self._translate_track(track, seq.tempo or 120, base_ts))
        return msgs

    def _translate_track(self, track: Track, tempo: float, base_ts: float) -> list[MIDIMessage]:
        msgs: list[MIDIMessage] = []
        ch = track.channel if track.channel is not None else 0
        port = track.port

        # Initial track setup
        if track.program is not None:
            prog = self._resolve_program(track.program)
            if prog is not None:
                msgs.append(_program_change(prog, ch, base_ts))
        if track.volume is not None:
            msgs.append(_cc(CC_VOLUME, track.volume, ch, base_ts))
        pan = _resolve_pan(track.pan)
        if pan is not None:
            msgs.append(_cc(CC_PAN, pan, ch, base_ts))

        # Convert beat-relative timestamps to seconds
        sec_per_beat = 60.0 / tempo if tempo > 0 else 0.5

        for event in track.events:
            ts = base_ts + event.at * sec_per_beat

            if event.tempo is not None:
                # Tempo change as MIDI meta event: FF 51 03 tt tt tt
                us_per_qnote = int(60000000.0 / event.tempo)
                tempo_data = [(us_per_qnote >> 16) & 0xFF, (us_per_qnote >> 8) & 0xFF, us_per_qnote & 0xFF]
                msgs.append(MIDIMessage(
                    "meta_event", None,
                    {"meta_type": 0x51, "data": tempo_data},
                    timestamp=ts,
                ))

            if event.text is not None:
                # Text meta event: FF 01 len text_bytes
                text_bytes = [ord(c) & 0x7F if ord(c) < 128 else 0x20 for c in str(event.text)]
                msgs.append(MIDIMessage(
                    "meta_event", None,
                    {"meta_type": 0x01, "data": text_bytes},
                    timestamp=ts,
                ))

            if event.note_on is not None:
                note = self._resolve_note(event.note_on.note)
                if note is not None:
                    msgs.append(_note_on(note, event.note_on.velocity, ch, ts))
                    # If duration is specified, emit note-off
                    if event.note_on.duration is not None:
                        off_ts = ts + event.note_on.duration * sec_per_beat
                        msgs.append(_note_off(note, 64, ch, off_ts))

            if event.program is not None:
                prog = self._resolve_program(event.program)
                if prog is not None:
                    msgs.append(_program_change(prog, ch, ts))

            if event.control is not None:
                ctrl = event.control.controller
                val = int(event.control.value)
                # Resolve named controller
                if isinstance(ctrl, str):
                    resolved = self._resolve_controller_number(ctrl)
                    if resolved is not None:
                        ctrl = resolved
                    else:
                        continue
                msgs.append(_cc(int(ctrl), val, ch, ts))

            if event.pitch_bend is not None:
                msgs.append(_pitch_bend(event.pitch_bend, ch, ts))

            # Explicit note-off (overrides duration-based note-off from note_on)
            if event.note_off is not None:
                note = self._resolve_note(event.note_off.note)
                if note is not None:
                    msgs.append(_note_off(note, event.note_off.velocity or 64, ch, ts))

            # NRPN parameter change
            if event.nrpn is not None:
                val = int(event.nrpn.value)
                msgs.extend(_nrpn(event.nrpn.msb, event.nrpn.lsb, max(0, min(127, val)), ch, ts))

            # Channel pressure (aftertouch)
            if event.channel_pressure is not None:
                msgs.append(MIDIMessage(
                    "channel_pressure", ch,
                    {"pressure": max(0, min(127, event.channel_pressure))},
                    timestamp=ts,
                ))

            # Polyphonic pressure
            if event.poly_pressure is not None:
                for note, pressure in event.poly_pressure:
                    msgs.append(MIDIMessage(
                        "poly_pressure", ch,
                        {"note": max(0, min(127, note)), "pressure": max(0, min(127, pressure))},
                        timestamp=ts,
                    ))

            # System Exclusive
            if event.sysex is not None:
                msgs.append(MIDIMessage(
                    "system_exclusive", None,
                    {"data": [int(b) & 0x7F for b in event.sysex]},
                    timestamp=ts,
                ))

        # Stamp port onto all messages for downstream routing
        for m in msgs:
            m.data["port"] = port
        return msgs

    # ------------------------------------------------------------------
    # Value resolution helpers
    # ------------------------------------------------------------------

    _PROGRAM_NAMES: dict[str, int] = {
        "acoustic_grand_piano": 0, "bright_acoustic_piano": 1, "electric_grand_piano": 2,
        "honky_tonk_piano": 3, "electric_piano_1": 4, "electric_piano_2": 5,
        "harpsichord": 6, "clavinet": 7, "celesta": 8, "glockenspiel": 9,
        "music_box": 10, "vibraphone": 11, "marimba": 12, "xylophone": 13,
        "tubular_bells": 14, "dulcimer": 15, "drawbar_organ": 16, "percussive_organ": 17,
        "rock_organ": 18, "church_organ": 19, "reed_organ": 20, "accordion": 21,
        "harmonica": 22, "tango_accordion": 23, "nylon_string_guitar": 24,
        "steel_string_guitar": 25, "jazz_electric_guitar": 26, "clean_electric_guitar": 27,
        "muted_electric_guitar": 28, "overdriven_guitar": 29, "distortion_guitar": 30,
        "guitar_harmonics": 31, "acoustic_bass": 32, "fingered_electric_bass": 33,
        "picked_electric_bass": 34, "fretless_bass": 35, "slap_bass_1": 36,
        "slap_bass_2": 37, "synth_bass_1": 38, "synth_bass_2": 39,
        "violin": 40, "viola": 41, "cello": 42, "contrabass": 43,
        "tremolo_strings": 44, "pizzicato_strings": 45, "orchestral_harp": 46,
        "timpani": 47, "string_ensemble_1": 48, "string_ensemble_2": 49,
        "synth_strings_1": 50, "synth_strings_2": 51, "choir_aahs": 52,
        "voice_oohs": 53, "synth_voice": 54, "orchestra_hit": 55,
        "trumpet": 56, "trombone": 57, "tuba": 58, "muted_trumpet": 59,
        "french_horn": 60, "brass_section": 61, "synth_brass_1": 62,
        "synth_brass_2": 63, "soprano_sax": 64, "alto_sax": 65,
        "tenor_sax": 66, "baritone_sax": 67, "oboe": 68, "english_horn": 69,
        "bassoon": 70, "clarinet": 71, "piccolo": 72, "flute": 73,
        "recorder": 74, "pan_flute": 75, "blown_bottle": 76, "shakuhachi": 77,
        "whistle": 78, "ocarina": 79, "lead_1_square": 80, "lead_2_sawtooth": 81,
        "lead_3_calliope": 82, "lead_4_chiff": 83, "lead_5_charang": 84,
        "lead_6_voice": 85, "lead_7_fifths": 86, "lead_8_bass_lead": 87,
        "pad_1_new_age": 88, "pad_2_warm": 89, "pad_3_polysynth": 90,
        "pad_4_choir": 91, "pad_5_bowed": 92, "pad_6_metallic": 93,
        "pad_7_halo": 94, "pad_8_sweep": 95, "fx_1_rain": 96,
        "fx_2_soundtrack": 97, "fx_3_crystal": 98, "fx_4_atmosphere": 99,
        "fx_5_brightness": 100, "fx_6_goblins": 101, "fx_7_echoes": 102,
        "fx_8_sci_fi": 103, "sitar": 104, "banjo": 105, "shamisen": 106,
        "koto": 107, "kalimba": 108, "bagpipe": 109, "fiddle": 110,
        "shanai": 111, "tinkle_bell": 112, "agogo": 113, "steel_drums": 114,
        "woodblock": 115, "taiko_drum": 116, "melodic_tom": 117,
        "synth_drum": 118, "reverse_cymbal": 119,
        "guitar_fret_noise": 120, "breath_noise": 121, "seashore": 122,
        "bird_tweet": 123, "telephone_ring": 124, "helicopter": 125,
        "applause": 126, "gunshot": 127,
    }

    _CONTROLLER_NAMES: dict[str, int] = {
        "modulation": 1, "breath": 2, "foot": 4, "portamento_time": 5,
        "volume": 7, "balance": 8, "pan": 10, "expression": 11,
        "effect_control_1": 12, "effect_control_2": 13,
        "general_purpose_1": 16, "general_purpose_2": 17,
        "general_purpose_3": 18, "general_purpose_4": 19,
        "bank_msb": 0, "bank_lsb": 32,
        "modulation_lsb": 33, "breath_lsb": 34, "foot_lsb": 36,
        "pan_lsb": 42, "expression_lsb": 43,
        "hold": 64, "portamento": 65, "sostenuto": 66, "soft_pedal": 67,
        "legato": 68, "hold_2": 69,
        "sound_controller_1": 70, "sound_controller_2": 71,
        "sound_controller_3": 72, "sound_controller_4": 73,
        "general_purpose_5": 80, "general_purpose_6": 81,
        "general_purpose_7": 82, "general_purpose_8": 83,
        "portamento_control": 84,
        "reverb_send": 91, "chorus_send": 93, "variation_send": 94,
        "all_sound_off": 120, "all_controllers_off": 121,
        "local_control": 122, "all_notes_off": 123,
        "omni_off": 124, "omni_on": 125, "mono": 126, "poly": 127,
    }

    def _resolve_program(self, program: str | int) -> int | None:
        if isinstance(program, int):
            return max(0, min(127, program))
        name = program.lower().strip()
        return self._PROGRAM_NAMES.get(name)

    def _resolve_controller_number(self, name: str) -> int | None:
        return self._CONTROLLER_NAMES.get(name.lower().strip())

    def _resolve_note(self, note: str | int) -> int | None:
        if isinstance(note, int):
            return max(0, min(127, note))
        try:
            return note_name_to_midi(note)
        except (KeyError, ValueError):
            self.warnings.append(f"Unknown note name: {note}")
            return None

    def _resolve_filter_type(self, ft: str | int) -> int | None:
        if isinstance(ft, int):
            return max(0, min(3, ft))
        names = {"through": 0, "lowpass": 1, "highpass": 2, "bandpass": 3}
        return names.get(ft.lower())

    def _resolve_lfo_waveform(self, wf: str | int) -> int | None:
        if isinstance(wf, int):
            return max(0, min(5, wf))
        names = {"sine": 0, "triangle": 1, "saw_up": 2, "saw_down": 3, "square": 4, "sample_and_hold": 5}
        return names.get(wf.lower())

    def _resolve_reverb_type(self, rt: str | int) -> int | None:
        if isinstance(rt, int):
            return max(0, min(26, rt))
        names = {
            "no_effect": 0, "hall1": 1, "hall2": 2, "room1": 3, "room2": 4,
            "room3": 5, "stage1": 6, "stage2": 7, "plate": 8, "white_room": 9,
            "tunnel": 10, "canyon": 11, "basement": 12,
        }
        return names.get(rt.lower())

    def _resolve_chorus_type(self, ct: str | int) -> int | None:
        if isinstance(ct, int):
            return max(0, min(17, ct))
        names = {
            "chorus1": 0, "chorus2": 1, "chorus3": 2, "chorus4": 3, "chorus5": 4,
            "celeste1": 5, "celeste2": 6, "celeste3": 7, "celeste4": 8, "celeste5": 9,
            "flanger1": 10, "flanger2": 11, "flanger3": 12, "flanger4": 13,
            "flanger5": 14, "flanger6": 15, "symphonic1": 16, "symphonic2": 17,
        }
        return names.get(ct.lower())
