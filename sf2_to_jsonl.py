#!/usr/bin/env python3
"""
Export complete SF2 SoundFont metadata to a JSONL document using the `sf2utils`
PyPI package.

For each input SF2 file, one JSON object is written as a single line to the
output file. The object contains the full metadata tree:

    {
      "file": {...},
      "info": {...},
      "presets": [ {preset}, ... ],
      "instruments": [ {instrument}, ... ],
      "samples": [ {sample}, ... ]
    }

Each preset/instrument carries its bags, and each bag carries its generators
and modulators. Generator/modulator opcodes are emitted both as raw numeric
opcodes and as resolved names (see `GENERATOR_NAMES` / `MODULATOR_SOURCES`).

Usage:
    python sf2_to_jsonl.py input.sf2 [input2.sf2 ...] -o output.jsonl
    python sf2_to_jsonl.py -o output.jsonl --directory /path/to/sf2s
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from sf2utils.sf2parse import Sf2File
from sf2utils.generator import Sf2Gen
from sf2utils.sample import Sf2Sample

# Resolved generator opcode names keyed by the numeric `oper` value.
GENERATOR_NAMES: dict[int, str] = {
    value: name
    for name, value in vars(Sf2Gen).items()
    if name.startswith("OPER_") and isinstance(value, int)
}

# Human-readable names for the standard SF2 modulator source enumerators.
# (SF2 spec 7.4 - controller/key/velocity source operands.)
MODULATOR_SOURCES: dict[int, str] = {
    0: "no_source",
    1: "note_on_velocity",
    2: "note_on_key",
    3: "poly_pressure",
    4: "channel_pressure",
    5: "pitch_wheel",
    6: "pitch_wheel_sensitivity",
    127: "link",
    128: "cc1",
    129: "cc2",
    130: "cc3",
    131: "cc4",
    132: "cc5",
    133: "cc6",
    134: "cc7",
    135: "cc8",
    136: "cc9",
    137: "cc10",
    138: "cc11",
    139: "cc12",
    140: "cc13",
    141: "cc14",
    142: "cc15",
    143: "cc16",
    144: "cc17",
    145: "cc18",
    146: "cc19",
    147: "cc20",
    148: "cc21",
    149: "cc22",
    150: "cc23",
    151: "cc24",
    152: "cc25",
    153: "cc26",
    154: "cc27",
    155: "cc28",
    156: "cc29",
    157: "cc30",
    158: "cc31",
    159: "cc32",
    160: "cc33",
    161: "cc34",
    162: "cc35",
    163: "cc36",
    164: "cc37",
    165: "cc38",
    166: "cc39",
    167: "cc40",
    168: "cc41",
    169: "cc42",
    170: "cc43",
    171: "cc44",
    172: "cc45",
    173: "cc46",
    174: "cc47",
    175: "cc48",
    176: "cc49",
    177: "cc50",
    178: "cc51",
    179: "cc52",
    180: "cc53",
    181: "cc54",
    182: "cc55",
    183: "cc56",
    184: "cc57",
    185: "cc58",
    186: "cc59",
    187: "cc60",
    188: "cc61",
    189: "cc62",
    190: "cc63",
    191: "cc64",
    192: "cc65",
    193: "cc66",
    194: "cc67",
    195: "cc68",
    196: "cc69",
    197: "cc70",
    198: "cc71",
    199: "cc72",
    200: "cc73",
    201: "cc74",
    202: "cc75",
    203: "cc76",
    204: "cc77",
    205: "cc78",
    206: "cc79",
    207: "cc80",
    208: "cc81",
    209: "cc82",
    210: "cc83",
    211: "cc84",
    212: "cc85",
    213: "cc86",
    214: "cc87",
    215: "cc88",
    216: "cc89",
    217: "cc90",
    218: "cc91",
    219: "cc92",
    220: "cc93",
    221: "cc94",
    222: "cc95",
    223: "cc96",
    224: "cc97",
    225: "cc98",
    226: "cc99",
    227: "cc100",
    228: "cc101",
    229: "cc102",
    230: "cc103",
    231: "cc104",
    232: "cc105",
    233: "cc106",
    234: "cc107",
    235: "cc108",
    236: "cc109",
    237: "cc110",
    238: "cc111",
    239: "cc112",
    240: "cc113",
    241: "cc114",
    242: "cc115",
    243: "cc116",
    244: "cc117",
    245: "cc118",
    246: "cc119",
    247: "cc120",
    248: "cc121",
    249: "cc122",
    250: "cc123",
    251: "cc124",
    252: "cc125",
    253: "cc126",
    254: "cc127",
}

# Resolved generator destination names keyed by numeric `dest_oper`.
GENERATOR_DESTINATIONS: dict[int, str] = {
    0: "no_destination",
    1: "gain",
    2: "pitch",
    3: "pitch",
    4: "pitch",
    5: "pitch",
    6: "pitch",
    7: "pitch",
    8: "filter_cutoff",
    9: "filter_q",
    10: "filter_cutoff",
    11: "filter_cutoff",
    12: "pitch",
    13: "gain",
    14: "reverb_send",
    15: "chorus_send",
    16: "reverb_send",
    17: "pan",
    18: "gain",
    19: "gain",
    20: "gain",
    21: "lfo_delay",
    22: "lfo_frequency",
    23: "lfo_delay",
    24: "lfo_frequency",
    25: "eg_delay",
    26: "eg_attack",
    27: "eg_hold",
    28: "eg_decay",
    29: "eg_sustain",
    30: "eg_release",
    31: "eg_delay",
    32: "eg_attack",
    33: "eg_delay",
    34: "eg_attack",
    35: "eg_hold",
    36: "eg_decay",
    37: "eg_sustain",
    38: "eg_release",
    39: "eg_hold",
    40: "eg_decay",
    41: "instrument",
    42: "instrument",
    43: "key_range",
    44: "velocity_range",
    45: "pitch",
    46: "gain",
    47: "gain",
    48: "gain",
    49: "pitch",
    50: "pitch",
    51: "pitch",
    52: "pitch",
    53: "sample_id",
    54: "sample_modes",
    55: "sample_id",
    56: "scale_tuning",
    57: "exclusive_class",
    58: "root_key",
}


# Modulator transform enumerators (SF2 spec 8.3).
TRANSFORM_NAMES: dict[int, str] = {
    0: "linear",
    1: "concave",
    2: "convex",
    3: "switch",
}

# Modulator source curve types (SF2 spec 8.2.4, bits 10-15 of a source operand).
SOURCE_TYPE_NAMES: dict[int, str] = {
    0: "linear",
    1: "concave",
    2: "convex",
    3: "switch",
}


# Chunks that some SF2 files omit — ensure they exist as empty lists so the
# sf2utils bag builder doesn't KeyError when looking them up.
_OPTIONAL_PDTA_KEYS = ("Pmod", "Pgen", "Imod", "Igen")


def _ensure_pdta_keys(sf2: Sf2File) -> None:
    """Ensure optional pdta chunks exist before the library builds bags.

    Some SoundFonts (e.g. minimal test banks) omit the ``Pmod``/``Imod``
    chunks entirely. The sf2utils bag builder indexes these by name and would
    otherwise raise ``KeyError``, leaving presets/instruments empty.
    """
    for key in _OPTIONAL_PDTA_KEYS:
        sf2._raw.pdta.setdefault(key, [])


def _decode_source_operand(src_oper: int) -> dict[str, Any]:
    """Decode a packed SF2 modulator source operand (SF2 spec 8.2).

    A source operand is a 16-bit value with this layout:
        bits 0-6  : controller/key index
        bit  7    : polarity   (0 = unipolar, 1 = bipolar)
        bit  8    : direction  (0 = increasing, 1 = decreasing)
        bit  9    : reserved (always 0)
        bits 10-15: curve type (0 = linear, 1 = concave, 2 = convex, 3 = switch)
    """
    index = src_oper & 0x7F
    polarity = "bipolar" if (src_oper & 0x80) else "unipolar"
    direction = "decreasing" if (src_oper & 0x100) else "increasing"
    curve = SOURCE_TYPE_NAMES.get((src_oper >> 10) & 0x3F, f"type_{(src_oper >> 10) & 0x3F}")
    return {
        "raw": src_oper,
        "index": index,
        "name": MODULATOR_SOURCES.get(index, f"cc{index}" if 128 <= src_oper < 256 else f"source_{index}"),
        "polarity": polarity,
        "direction": direction,
        "type": curve,
    }


def _generator_dest_name(dest_oper: int) -> str:
    """Resolve a modulator destination operand to a human-readable name.

    The top bit (0x8000) marks a link to another modulator's source rather than
    a generator destination.
    """
    if dest_oper & 0x8000:
        return f"link_to_modulator_{dest_oper & 0x7FFF}"
    return GENERATOR_DESTINATIONS.get(dest_oper & 0x7FFF, f"dest_{dest_oper}")


def _gen_to_dict(gen: Sf2Gen) -> dict[str, Any]:
    """Serialize a single generator to a JSON-friendly dict."""
    return {
        "oper": gen.oper,
        "oper_name": GENERATOR_NAMES.get(gen.oper, f"unknown_{gen.oper}"),
        "amount": gen.amount,
        "amount_signed": gen.short,
    }


# Semantic decoding of generator amounts: (decoded_value, unit) per SF2 spec.
# Most generators are a signed 16-bit value whose meaning depends on the opcode.
# Envelope times are stored as 2^(cents/1200) time-cent multipliers; attenuation
# as centibels (1/10 dB); filter cutoff as absolute cents; pan/send as fractions.
_GENER_DECODE: dict[int, tuple[str, str]] = {
    Sf2Gen.OPER_MOD_LFO_TO_PITCH: ("cents", "semitone_multiplier"),
    Sf2Gen.OPER_VIB_LFO_TO_PITCH: ("cents", "semitone_multiplier"),
    Sf2Gen.OPER_MOD_ENV_TO_PITCH: ("cents", "semitone_multiplier"),
    Sf2Gen.OPER_INITIAL_FILTER_CUTOFF: ("absolute_cents", "Hz"),
    Sf2Gen.OPER_INITIAL_FILTER_Q: ("filter_q", "dB"),
    Sf2Gen.OPER_MOD_LFO_TO_FILTER_CUTOFF: ("cents", "semitone_multiplier"),
    Sf2Gen.OPER_MOD_ENV_TO_FILTER_CUTOFF: ("cents", "semitone_multiplier"),
    Sf2Gen.OPER_MOD_LFO_TO_VOLUME: ("attenuation", "dB"),
    Sf2Gen.OPER_CHORUS_EFFECTS_SEND: ("send_amount", "percent"),
    Sf2Gen.OPER_REVERB_EFFECTS_SEND: ("send_amount", "percent"),
    Sf2Gen.OPER_PAN: ("pan", "percent"),
    Sf2Gen.OPER_DELAY_MOD_LFO: ("cents", "seconds"),
    Sf2Gen.OPER_FREQ_MOD_LFO: ("absolute_cents", "Hz"),
    Sf2Gen.OPER_DELAY_VIB_LFO: ("cents", "seconds"),
    Sf2Gen.OPER_FREQ_VIB_LFO: ("absolute_cents", "Hz"),
    Sf2Gen.OPER_DELAY_MOD_ENV: ("cents", "seconds"),
    Sf2Gen.OPER_ATTACK_MOD_ENV: ("cents", "seconds"),
    Sf2Gen.OPER_HOLD_MOD_ENV: ("cents", "seconds"),
    Sf2Gen.OPER_DECAY_MOD_ENV: ("cents", "seconds"),
    Sf2Gen.OPER_SUSTAIN_MOD_ENV: ("sustain_mod", "percent"),
    Sf2Gen.OPER_RELEASE_MOD_ENV: ("cents", "seconds"),
    Sf2Gen.OPER_DELAY_VOL_ENV: ("cents", "seconds"),
    Sf2Gen.OPER_ATTACK_VOL_ENV: ("cents", "seconds"),
    Sf2Gen.OPER_HOLD_VOL_ENV: ("cents", "seconds"),
    Sf2Gen.OPER_DECAY_VOL_ENV: ("cents", "seconds"),
    Sf2Gen.OPER_SUSTAIN_VOL_ENV: ("sustain_vol", "dB"),
    Sf2Gen.OPER_RELEASE_VOL_ENV: ("cents", "seconds"),
    Sf2Gen.OPER_KEYNUM_TO_VOL_ENV_HOLD: ("cents", "seconds_per_key"),
    Sf2Gen.OPER_KEYNUM_TO_VOL_ENV_DECAY: ("cents", "seconds_per_key"),
    Sf2Gen.OPER_INITIAL_ATTENUATION: ("attenuation", "dB"),
    Sf2Gen.OPER_COARSE_TUNE: ("short", "semitones"),
    Sf2Gen.OPER_FINE_TUNE: ("short", "cents"),
    Sf2Gen.OPER_SCALE_TUNING: ("word", "percent"),
    Sf2Gen.OPER_EXCLUSIVE_CLASS: ("word", "class"),
    Sf2Gen.OPER_OVERRIDING_ROOT_KEY: ("word", "midi_key"),
}


def _gen_decoded_value(gen: Sf2Gen) -> Any:
    """Return the semantically decoded decimal value of a generator, or None.

    Returns None for opcodes whose raw amount is already meaningful (ranges,
    sample IDs, addresses, instrument links) so the raw value is kept.
    """
    decoder, _unit = _GENER_DECODE.get(gen.oper, (None, ""))
    if decoder is None:
        return None
    if decoder == "filter_q":
        # initialFilterQ is in centibels: dB = amount / 10 (SF2 spec 8.1.3)
        return round(gen.amount / 10.0, 6)
    if decoder == "sustain_mod":
        # sustainModEnv is in per mille (0-1000): percent = amount / 10
        return round(gen.amount / 10.0, 6)
    if decoder == "sustain_vol":
        # sustainVolEnv is in centibels (0-1000): dB = amount / 10
        return round(gen.amount / 10.0, 6)
    return round(getattr(gen, decoder), 6)


def _gen_unit(gen: Sf2Gen) -> str | None:
    """Return the unit string for a generator, or None if not semantically decoded."""
    return _GENER_DECODE.get(gen.oper, (None, None))[1]


def _mod_to_dict(mod: Any) -> dict[str, Any]:
    """Serialize a single modulator to a JSON-friendly dict.

    The ``amount`` field is a signed 16-bit SHORT per the SF2 spec, so it is
    decoded as signed. The source operands (``src_oper`` / ``amount_src_oper``)
    are packed 16-bit values decoded into index/name/polarity/direction/type.
    """
    amount_signed = mod.amount - 0x10000 if mod.amount >= 0x8000 else mod.amount
    return {
        "src": _decode_source_operand(mod.src_oper),
        "dest_oper": mod.dest_oper,
        "dest_name": _generator_dest_name(mod.dest_oper),
        "amount": amount_signed,
        "amount_unsigned": mod.amount,
        "amount_src": _decode_source_operand(mod.amount_src_oper),
        "trans_oper": mod.trans_oper,
        "trans_name": TRANSFORM_NAMES.get(mod.trans_oper, f"transform_{mod.trans_oper}"),
    }


def _bag_to_dict(bag: Any) -> dict[str, Any]:
    """Serialize a preset/instrument bag (zone) to a JSON-friendly dict.

    Accessing ``bag.gens`` / ``bag.mods`` / ``bag.instrument`` / ``bag.sample``
    can raise ``KeyError`` for malformed or partial SoundFonts (e.g. a file that
    is missing the ``Pmod``/``Imod`` chunk). We degrade gracefully and record
    the failure instead of aborting the whole export.
    """
    try:
        gens = [_gen_to_dict(gen) for gen in bag.gens.values()]
    except Exception as exc:  # noqa: BLE001
        gens = []
        logging.warning("Bag %s: failed to read generators: %s", bag.idx, exc)
    try:
        mods = [_mod_to_dict(mod) for mod in bag.mods]
    except Exception as exc:  # noqa: BLE001
        mods = []
        logging.warning("Bag %s: failed to read modulators: %s", bag.idx, exc)

    instrument = None
    sample = None
    key_range = None
    velocity_range = None
    try:
        instrument_obj = bag.instrument
        instrument = instrument_obj.name if instrument_obj is not None else None
    except Exception:  # noqa: BLE001
        pass
    try:
        sample_obj = bag.sample
        sample = sample_obj.name if sample_obj is not None else None
    except Exception:  # noqa: BLE001
        pass
    try:
        key_range = list(bag.key_range) if bag.key_range is not None else None
    except Exception:  # noqa: BLE001
        pass
    try:
        velocity_range = list(bag.velocity_range) if bag.velocity_range is not None else None
    except Exception:  # noqa: BLE001
        pass

    return {
        "idx": bag.idx,
        "mod_size": bag.mod_size,
        "gen_size": bag.gen_size,
        "key_range": key_range,
        "velocity_range": velocity_range,
        "instrument": instrument,
        "sample": sample,
        "generators": gens,
        "modulators": mods,
    }


def _sample_to_dict(sample: Sf2Sample, sf2: Sf2File | None = None) -> dict[str, Any]:
    """Serialize a sample header to a JSON-friendly dict.

    When ``sf2`` is provided, ``sample_link`` is resolved to the linked
    sample's name (mirroring how sf2parse reports "linked to sample N").
    """
    if sample.name == "EOS":
        return {"name": "EOS", "sentinel": True}

    channel = "mono" if sample.is_mono else ("left" if sample.is_left else "right")

    link_name = None
    if sample.sample_link is not None and sf2 is not None:
        try:
            link_name = sf2.samples[sample.sample_link].name
        except Exception:  # noqa: BLE001 - out-of-range or sentinel link
            link_name = None

    return {
        "name": sample.name,
        "start": sample.start,
        "end": sample.end,
        "duration": sample.duration,
        "start_loop": sample.start_loop,
        "end_loop": sample.end_loop,
        "loop_duration": sample.loop_duration,
        "sample_rate": sample.sample_rate,
        "original_pitch": sample.original_pitch,
        "pitch_correction": sample.pitch_correction,
        "in_rom": sample.in_rom,
        "sample_type": sample.sample_type,
        "channel": channel,
        "sample_link": sample.sample_link,
        "sample_link_name": link_name,
        "sample_width": sample.sample_width,
    }


def _info_to_dict(info: Any) -> dict[str, Any]:
    """Serialize the INFO/list chunk metadata to a JSON-friendly dict."""
    return {
        "version": info.version,
        "sound_engine": info.sound_engine,
        "bank_name": info.bank_name,
        "rom_name": info.rom_name,
        "rom_version": info.rom_version,
        "creation_date": info.creation_date,
        "designers": info.designers,
        "intended_product": info.intended_product,
        "copyright": info.copyright,
        "comments": info.comments,
        "tool": info.tool,
    }


def _bank_msb_lsb(bank: int) -> tuple[int, int]:
    """Split a 14-bit SF2 bank number into (MSB, LSB).

    SF2 stores the bank as a 14-bit value where the high 7 bits are the
    Bank MSB (CC#0) and the low 7 bits are the Bank LSB (CC#32).
    """
    return (bank >> 7) & 0x7F, bank & 0x7F


def _build_presets(sf2: Sf2File, bag_fn: Any) -> list[dict[str, Any]]:
    """Build, sort, and group presets by bank (MSB/LSB) then program.

    Returns a list of bank groups, each with its MSB/LSB split and a sorted
    list of presets. Presets within a bank are ordered by program number.
    """
    raw_presets = []
    try:
        preset_iter = list(sf2.presets)
    except Exception as exc:  # noqa: BLE001 - e.g. missing Pmod chunk
        logging.warning("Failed to read presets from %s: %s", getattr(sf2, "name", "?"), exc)
        preset_iter = []
    for preset in preset_iter:
        if preset.name == "EOP":
            continue
        try:
            bags = [bag_fn(bag) for bag in preset.bags]
            key_range = list(preset.key_range)
        except Exception as exc:  # noqa: BLE001 - malformed preset zone
            logging.warning("Preset %s: failed to read zones: %s", preset.name, exc)
            bags = []
            key_range = None
        raw_presets.append(
            {
                "name": preset.name,
                "bank": preset.bank,
                "preset": preset.preset,
                "bag_idx": preset.bag_idx,
                "bag_size": preset.bag_size,
                "key_range": key_range,
                "bags": bags,
            }
        )

    # Sort by (bank, program) for stable, human-friendly ordering.
    raw_presets.sort(key=lambda p: (p["bank"], p["preset"]))

    # Group by bank, preserving sorted bank order.
    groups: dict[int, list[dict[str, Any]]] = {}
    order: list[int] = []
    for preset in raw_presets:
        bank = preset["bank"]
        if bank not in groups:
            groups[bank] = []
            order.append(bank)
        groups[bank].append(preset)

    return [
        {
            "bank": bank,
            "bank_msb": _bank_msb_lsb(bank)[0],
            "bank_lsb": _bank_msb_lsb(bank)[1],
            "presets": groups[bank],
        }
        for bank in order
    ]


def sf2_to_record(sf2_path: Path) -> dict[str, Any]:
    """Parse an SF2 file and return a complete metadata record."""
    with open(sf2_path, "rb") as sf2_file:
        sf2 = Sf2File(sf2_file)
        _ensure_pdta_keys(sf2)

        presets = _build_presets(sf2, _bag_to_dict)

        instruments = []
        try:
            instrument_iter = list(sf2.instruments)
        except Exception as exc:  # noqa: BLE001 - e.g. missing Imod chunk
            logging.warning("Failed to read instruments from %s: %s", sf2_path.name, exc)
            instrument_iter = []
        for instrument in instrument_iter:
            if instrument.is_sentinel():
                continue
            try:
                bags = [_bag_to_dict(bag) for bag in instrument.bags]
                samples = [s.name for s in instrument.samples]
            except Exception as exc:  # noqa: BLE001 - malformed instrument zone
                logging.warning("Instrument %s: failed to read zones: %s", instrument.name, exc)
                bags = []
                samples = []
            instruments.append(
                {
                    "name": instrument.name,
                    "bag_idx": instrument.bag_idx,
                    "bag_size": instrument.bag_size,
                    "samples": samples,
                    "bags": bags,
                }
            )

        samples = [_sample_to_dict(sample, sf2) for sample in sf2.samples]

        return {
            "file": {
                "name": sf2_path.name,
                "path": str(sf2_path.resolve()),
                "size_bytes": sf2_path.stat().st_size,
            },
            "info": _info_to_dict(sf2.info),
            "presets": presets,
            "instruments": instruments,
            "samples": samples,
        }


def _report_gen(gen: Sf2Gen) -> dict[str, Any]:
    """Serialize a generator with its semantically decoded decimal value."""
    decoded = _gen_decoded_value(gen)
    unit = _gen_unit(gen)
    out: dict[str, Any] = {
        "oper": gen.oper,
        "oper_name": GENERATOR_NAMES.get(gen.oper, f"unknown_{gen.oper}"),
        "amount": gen.amount,
    }
    if decoded is not None:
        out["value"] = decoded
        out["unit"] = unit
    return out


def _report_mod(mod: Any) -> dict[str, Any]:
    """Serialize a modulator with decoded source operands and signed amount."""
    amount_signed = mod.amount - 0x10000 if mod.amount >= 0x8000 else mod.amount
    return {
        "src": _decode_source_operand(mod.src_oper),
        "dest_oper": mod.dest_oper,
        "dest_name": _generator_dest_name(mod.dest_oper),
        "amount": amount_signed,
        "amount_src": _decode_source_operand(mod.amount_src_oper),
        "trans_oper": mod.trans_oper,
        "trans_name": TRANSFORM_NAMES.get(mod.trans_oper, f"transform_{mod.trans_oper}"),
    }


def _report_bag(bag: Any) -> dict[str, Any]:
    """Serialize a bag (zone) with resolved instrument/sample names and decoded gens/mods."""
    instrument = None
    sample = None
    try:
        instrument_obj = bag.instrument
        instrument = instrument_obj.name if instrument_obj is not None else None
    except Exception:  # noqa: BLE001
        pass
    try:
        sample_obj = bag.sample
        sample = sample_obj.name if sample_obj is not None else None
    except Exception:  # noqa: BLE001
        pass
    key_range = None
    velocity_range = None
    try:
        key_range = list(bag.key_range) if bag.key_range is not None else None
    except Exception:  # noqa: BLE001
        pass
    try:
        velocity_range = list(bag.velocity_range) if bag.velocity_range is not None else None
    except Exception:  # noqa: BLE001
        pass
    return {
        "key_range": key_range,
        "velocity_range": velocity_range,
        "instrument": instrument,
        "sample": sample,
        "generators": [_report_gen(gen) for gen in bag.gens.values()],
        "modulators": [_report_mod(mod) for mod in bag.mods],
    }


def _report_sample(sample: Sf2Sample) -> dict[str, Any]:
    """Serialize a sample header with resolved link name."""
    if sample.name == "EOS":
        return {"name": "EOS", "sentinel": True}
    channel = "mono" if sample.is_mono else ("left" if sample.is_left else "right")
    link_name = None
    if sample.sample_link is not None:
        try:
            link_name = sample.sf2parser.samples[sample.sample_link].name
        except Exception:  # noqa: BLE001
            link_name = None
    return {
        "name": sample.name,
        "start": sample.start,
        "end": sample.end,
        "duration": sample.duration,
        "start_loop": sample.start_loop,
        "end_loop": sample.end_loop,
        "loop_duration": sample.loop_duration,
        "sample_rate": sample.sample_rate,
        "original_pitch": sample.original_pitch,
        "pitch_correction": sample.pitch_correction,
        "in_rom": sample.in_rom,
        "sample_type": sample.sample_type,
        "channel": channel,
        "sample_link": sample.sample_link,
        "sample_link_name": link_name,
        "sample_width": sample.sample_width,
    }


def _normalize_area(rect: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """Normalize a rectangle, using the 'any' shortcut for a full 0-127 span.

    A span covering the entire 0-127 range is collapsed to (0, 127) so it can
    be merged with other full-span rectangles and rendered as 'any'.
    """
    k_lo, k_hi, v_lo, v_hi = rect
    k_lo = max(0, min(k_lo, 127))
    k_hi = max(0, min(k_hi, 127))
    v_lo = max(0, min(v_lo, 127))
    v_hi = max(0, min(v_hi, 127))
    if k_lo > k_hi:
        k_lo, k_hi = k_hi, k_lo
    if v_lo > v_hi:
        v_lo, v_hi = v_hi, v_lo
    return (k_lo, k_hi, v_lo, v_hi)


def _merge_areas(areas: list[tuple[int, int, int, int]]) -> list[dict[str, Any]]:
    """Merge rectangles in (key, velocity) space into continuous areas.

    Two rectangles belong to the same continuous area when they overlap or
    touch along either axis (adjacency counts as continuous, since a zone
    covering keys 0-63 and another 64-127 form one unbroken strip). The result
    is a minimal set of bounding rectangles. A span covering the full 0-127
    range on an axis is rendered as 'any' for readability.
    """
    rects = [_normalize_area(r) for r in areas]
    merged: list[list[int]] = []  # each: [k_lo, k_hi, v_lo, v_hi]

    def overlaps(a: list[int], b: list[int]) -> bool:
        # Overlap or touch on BOTH axes => continuous.
        k_touch = not (a[1] < b[0] - 1 or b[1] < a[0] - 1)
        v_touch = not (a[3] < b[2] - 1 or b[3] < a[2] - 1)
        return k_touch and v_touch

    for rect in rects:
        r = list(rect)
        changed = True
        while changed:
            changed = False
            for i, other in enumerate(merged):
                if overlaps(r, other):
                    # Expand to the bounding box of the two rectangles.
                    r = [
                        min(r[0], other[0]),
                        max(r[1], other[1]),
                        min(r[2], other[2]),
                        max(r[3], other[3]),
                    ]
                    merged.pop(i)
                    changed = True
                    break
        merged.append(r)

    result: list[dict[str, Any]] = []
    for k_lo, k_hi, v_lo, v_hi in merged:
        result.append(
            {
                "key": "any" if (k_lo == 0 and k_hi == 127) else [k_lo, k_hi],
                "velocity": "any" if (v_lo == 0 and v_hi == 127) else [v_lo, v_hi],
            }
        )
    # Stable ordering: by key span then velocity span.
    result.sort(key=lambda a: (_span_key(a["key"]), _span_key(a["velocity"])))
    return result


def _span_key(span: Any) -> tuple[int, int]:
    """Sort key for a span that may be 'any' or [lo, hi]."""
    if span == "any":
        return (0, 127)
    return (span[0], span[1])


def _preset_stats(preset: dict[str, Any]) -> dict[str, Any]:
    """Compute aggregate statistics for a single report-style preset.

    Walks the resolved preset tree (zones -> instruments -> samples) and
    returns counts/flags derived entirely from the inlined metadata, so no
    cross-section lookup is needed.
    """
    instruments: set[str] = set()
    samples: set[str] = set()
    has_stereo = False
    total_gens = 0
    total_mods = 0
    gen_ids: set[int] = set()
    mod_pairs: set[tuple[int, int]] = set()
    total_sample_bytes = 0
    # Collect covered rectangular areas in (key, velocity) space, one rect per
    # instrument zone. Each rect is (key_lo, key_hi, vel_lo, vel_hi).
    areas: list[tuple[int, int, int, int]] = []

    for zone in preset.get("zones", []):
        for gen in zone.get("generators", []):
            total_gens += 1
            gen_ids.add(gen["oper"])
        for mod in zone.get("modulators", []):
            total_mods += 1
            mod_pairs.add((mod["src"]["index"], mod["dest_oper"]))
        idet = zone.get("instrument_detail")
        if idet is None:
            continue
        instruments.add(idet["name"])
        for izone in idet.get("zones", []):
            for gen in izone.get("generators", []):
                total_gens += 1
                gen_ids.add(gen["oper"])
            for mod in izone.get("modulators", []):
                total_mods += 1
                mod_pairs.add((mod["src"]["index"], mod["dest_oper"]))
            sdet = izone.get("sample_detail")
            if sdet is None:
                continue
            samples.add(sdet["name"])
            if sdet.get("channel") in ("left", "right"):
                has_stereo = True
            # Sample PCM size: duration (in sample frames) * channels * bytes/frame.
            channels = 2 if sdet.get("channel") in ("left", "right") else 1
            total_sample_bytes += sdet["duration"] * channels * sdet.get("sample_width", 2)
            # Accumulate key/velocity coverage as a 2D rectangle.
            kr = izone.get("key_range")
            vr = izone.get("velocity_range")
            if isinstance(kr, (list, tuple)) and len(kr) == 2:
                k_lo, k_hi = kr
            else:
                k_lo, k_hi = 0, 127
            if isinstance(vr, (list, tuple)) and len(vr) == 2:
                v_lo, v_hi = vr
            else:
                v_lo, v_hi = 0, 127
            areas.append((k_lo, k_hi, v_lo, v_hi))

    return {
        "num_instruments": len(instruments),
        "num_samples": len(samples),
        "has_stereo_sample": has_stereo,
        "num_generators": total_gens,
        "num_modulators": total_mods,
        "unique_generator_ids": len(gen_ids),
        "unique_modulator_pairs": len(mod_pairs),
        "total_sample_bytes": total_sample_bytes,
        "key_velocity_areas": _merge_areas(areas),
    }


def sf2_to_report(sf2_path: Path) -> dict[str, Any]:
    """Build a reporting record with fully resolved cross-references.

    Unlike :func:`sf2_to_record`, this reconstructs each preset as a complete
    tree: every preset zone carries its resolved instrument, and every
    instrument zone carries its resolved sample (with full sample metadata
    inlined). Generator and modulator amounts are emitted as decoded decimals
    with units where the opcode has a semantic meaning, so no manual lookup
    across the ``instruments``/``samples`` sections is needed.
    """
    with open(sf2_path, "rb") as sf2_file:
        sf2 = Sf2File(sf2_file)
        _ensure_pdta_keys(sf2)

        return _build_report(sf2, sf2_path)


def _build_report(sf2: Sf2File, sf2_path: Path) -> dict[str, Any]:
    """Build the reporting record from an already-parsed ``Sf2File``."""

    # Pre-build a name -> sample dict for inline sample resolution.
    sample_by_name: dict[str, dict[str, Any]] = {}
    try:
        for sample in sf2.samples:
            if sample.name != "EOS":
                sample_by_name[sample.name] = _report_sample(sample)
    except Exception as exc:  # noqa: BLE001
        logging.warning("Failed to read samples from %s: %s", sf2_path.name, exc)

    def resolve_instrument(instrument: Any) -> dict[str, Any] | None:
        """Resolve an instrument into a tree with inlined sample metadata."""
        if instrument is None or instrument.is_sentinel():
            return None
        zones = []
        try:
            for bag in instrument.bags:
                bag_rep = _report_bag(bag)
                sample_name = bag_rep["sample"]
                bag_rep["sample_detail"] = sample_by_name.get(sample_name) if sample_name else None
                zones.append(bag_rep)
        except Exception as exc:  # noqa: BLE001
            logging.warning("Instrument %s: failed to resolve zones: %s", instrument.name, exc)
        return {
            "name": instrument.name,
            "zones": zones,
        }

    def report_preset_bag_fn(preset: Any) -> dict[str, Any]:
        """Build a report-style preset zone with resolved instrument/sample trees."""
        zones = []
        try:
            for bag in preset.bags:
                bag_rep = _report_bag(bag)
                inst = bag_rep.get("instrument")
                bag_rep["instrument_detail"] = resolve_instrument(bag.instrument) if inst else None
                zones.append(bag_rep)
        except Exception as exc:  # noqa: BLE001
            logging.warning("Preset %s: failed to resolve zones: %s", preset.name, exc)
        try:
            key_range = list(preset.key_range)
        except Exception:  # noqa: BLE001
            key_range = None
        preset_dict = {
            "name": preset.name,
            "bank": preset.bank,
            "preset": preset.preset,
            "key_range": key_range,
            "zones": zones,
        }
        preset_dict["stats"] = _preset_stats(preset_dict)
        return preset_dict

    # Build grouped/sorted presets reusing the shared grouping helper.
    raw_presets = []
    try:
        preset_iter = list(sf2.presets)
    except Exception as exc:  # noqa: BLE001
        logging.warning("Failed to read presets from %s: %s", sf2_path.name, exc)
        preset_iter = []
    for preset in preset_iter:
        if preset.name == "EOP":
            continue
        raw_presets.append(report_preset_bag_fn(preset))

    raw_presets.sort(key=lambda p: (p["bank"], p["preset"]))
    groups: dict[int, list[dict[str, Any]]] = {}
    order: list[int] = []
    for preset in raw_presets:
        bank = preset["bank"]
        if bank not in groups:
            groups[bank] = []
            order.append(bank)
        groups[bank].append(preset)
    presets = [
        {
            "bank": bank,
            "bank_msb": _bank_msb_lsb(bank)[0],
            "bank_lsb": _bank_msb_lsb(bank)[1],
            "presets": groups[bank],
        }
        for bank in order
    ]

    return {
        "file": {
            "name": sf2_path.name,
            "path": str(sf2_path.resolve()),
            "size_bytes": sf2_path.stat().st_size,
        },
        "info": _info_to_dict(sf2.info),
        "presets": presets,
    }


def _is_atomic(value: Any) -> bool:
    """True if ``value`` is a scalar or a container holding only scalars.

    Atomic containers are rendered on a single line so each logical object
    (a generator, modulator, sample, or bag) stays readable as one line.
    """
    if isinstance(value, dict):
        return all(not isinstance(v, (dict, list)) for v in value.values())
    if isinstance(value, list):
        return all(not isinstance(v, (dict, list)) for v in value)
    return True


def _render(value: Any, indent: int, step: int = 2) -> str:
    """Render ``value`` as human-readable JSON.

    Atomic containers (only scalars inside) are emitted on a single line;
    everything else is pretty-printed with ``step``-space indentation so the
    document is easy to scan while keeping leaf objects compact.
    """
    pad = " " * indent
    pad_in = " " * (indent + step)

    if isinstance(value, dict):
        if not value:
            return "{}"
        if _is_atomic(value):
            return json.dumps(value, ensure_ascii=False)
        items = []
        for key, val in value.items():
            items.append(f'{pad_in}"{key}": {_render(val, indent + step, step)}')
        return "{\n" + ",\n".join(items) + "\n" + pad + "}"
    if isinstance(value, list):
        if not value:
            return "[]"
        if _is_atomic(value):
            return json.dumps(value, ensure_ascii=False)
        items = [f"{pad_in}{_render(v, indent + step, step)}" for v in value]
        return "[\n" + ",\n".join(items) + "\n" + pad + "]"
    return json.dumps(value, ensure_ascii=False)


def format_record(record: dict[str, Any]) -> str:
    """Render a metadata record as a single, human-readable JSON line-block.

    The top-level object is pretty-printed, but atomic leaf objects (each
    generator, modulator, sample, and bag) are kept on one line.
    """
    return _render(record, indent=0)


# CSV columns for the per-preset statistics export. Order matters for Excel.
PRESET_STATS_FIELDS: list[str] = [
    "soundfont_file",
    "bank",
    "bank_msb",
    "bank_lsb",
    "program",
    "preset_name",
    "preset_index",
    "num_instruments",
    "num_samples",
    "has_stereo_sample",
    "num_generators",
    "num_modulators",
    "unique_generator_ids",
    "unique_modulator_pairs",
    "total_sample_bytes",
    "key_velocity_areas",
]


def _flatten_areas(areas: list[dict[str, Any]]) -> str:
    """Render the list of (key, velocity) rectangular areas as a compact string.

    Each area is "key:velocity"; a full 0-127 span on an axis is shown as 'any'.
    Multiple areas are separated by ';'.
    """
    if not areas:
        return ""
    parts = []
    for area in areas:
        k = area["key"]
        v = area["velocity"]
        k_str = "any" if k == "any" else (f"{k[0]}-{k[1]}" if k[0] != k[1] else str(k[0]))
        v_str = "any" if v == "any" else (f"{v[0]}-{v[1]}" if v[0] != v[1] else str(v[0]))
        parts.append(f"{k_str}:{v_str}")
    return ";".join(parts)


def preset_stats_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten a report record into one CSV row per preset."""
    soundfont = record["file"]["name"]
    rows = []
    preset_index = 0
    for bank in record["presets"]:
        for preset in bank["presets"]:
            stats = preset.get("stats", {})
            rows.append(
                {
                    "soundfont_file": soundfont,
                    "bank": bank["bank"],
                    "bank_msb": bank["bank_msb"],
                    "bank_lsb": bank["bank_lsb"],
                    "program": preset["preset"],
                    "preset_name": preset["name"],
                    "preset_index": preset_index,
                    "num_instruments": stats.get("num_instruments", 0),
                    "num_samples": stats.get("num_samples", 0),
                    "has_stereo_sample": stats.get("has_stereo_sample", False),
                    "num_generators": stats.get("num_generators", 0),
                    "num_modulators": stats.get("num_modulators", 0),
                    "unique_generator_ids": stats.get("unique_generator_ids", 0),
                    "unique_modulator_pairs": stats.get("unique_modulator_pairs", 0),
                    "total_sample_bytes": stats.get("total_sample_bytes", 0),
                    "key_velocity_areas": _flatten_areas(stats.get("key_velocity_areas", [])),
                }
            )
            preset_index += 1
    return rows


def write_preset_stats_csv(records: list[dict[str, Any]], csv_path: str) -> int:
    """Write per-preset statistics for all records to a CSV file. Returns row count."""
    import csv

    rows: list[dict[str, Any]] = []
    for record in records:
        rows.extend(preset_stats_rows(record))
    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=PRESET_STATS_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def find_sf2_files(directory: Path) -> list[Path]:
    """Return sorted SF2 files in a directory."""
    if not directory.exists():
        logging.warning("Directory does not exist: %s", directory)
        return []
    return sorted(directory.glob("*.sf2"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export complete SF2 SoundFont metadata to a JSONL document"
    )
    parser.add_argument(
        "sf2_files",
        nargs="*",
        help="One or more SF2 files to export",
    )
    parser.add_argument(
        "--directory",
        "-d",
        type=str,
        default=None,
        help="Directory to scan for *.sf2 files",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="sf2_metadata.jsonl",
        help="Output JSONL file path (default: sf2_metadata.jsonl)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        default=False,
        help="Suppress per-file progress messages",
    )
    parser.add_argument(
        "--pretty",
        "-p",
        action="store_true",
        default=False,
        help=(
            "Human-readable multi-line output: the record is pretty-printed but "
            "atomic objects (each generator, modulator, sample, and bag) stay on "
            "a single line. Note: this is NOT strict JSONL (one object per line); "
            "use it for reading, not for line-by-line streaming."
        ),
    )
    parser.add_argument(
        "--report",
        "-r",
        action="store_true",
        default=False,
        help=(
            "Reporting mode: reconstruct each preset as a complete tree with "
            "instrument and sample cross-references resolved inline (no manual "
            "lookup across sections). Generator/modulator amounts are emitted as "
            "decoded decimals with units where semantically meaningful."
        ),
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help=(
            "Write per-preset statistics to this CSV file (Excel-friendly). "
            "Requires --report mode. Columns include bank MSB/LSB, program, "
            "preset name/index, and all computed statistics."
        ),
    )
    args = parser.parse_args()

    if args.csv and not args.report:
        parser.error("--csv requires --report mode")

    files: list[Path] = [Path(p) for p in args.sf2_files]
    if args.directory:
        files.extend(find_sf2_files(Path(args.directory)))

    if not files:
        parser.error("no SF2 files provided (use positional args or --directory)")

    written = 0
    csv_records: list[dict[str, Any]] = []
    with open(args.output, "w", encoding="utf-8") as out:
        for sf2_path in files:
            if not sf2_path.exists():
                logging.warning("Skipping missing file: %s", sf2_path)
                continue
            try:
                if args.report:
                    record = sf2_to_report(sf2_path)
                    n_presets = sum(len(bank["presets"]) for bank in record["presets"])
                    n_instruments = sum(
                        1
                        for bank in record["presets"]
                        for preset in bank["presets"]
                        for zone in preset["zones"]
                        if zone.get("instrument_detail")
                    )
                    n_samples = sum(
                        1
                        for bank in record["presets"]
                        for preset in bank["presets"]
                        for zone in preset["zones"]
                        for izone in (zone.get("instrument_detail") or {}).get("zones", [])
                        if izone.get("sample_detail")
                    )
                    if args.csv:
                        csv_records.append(record)
                else:
                    record = sf2_to_record(sf2_path)
                    n_presets = sum(len(bank["presets"]) for bank in record["presets"])
                    n_instruments = len(record["instruments"])
                    n_samples = len(record["samples"])
            except Exception as exc:  # noqa: BLE001 - report and continue
                logging.error("Failed to parse %s: %s", sf2_path, exc)
                continue
            out.write(
                format_record(record) + "\n" if args.pretty else json.dumps(record, ensure_ascii=False) + "\n"
            )
            written += 1
            if not args.quiet:
                logging.info(
                    "Exported %s (%d presets, %d instruments, %d samples)%s",
                    sf2_path.name,
                    n_presets,
                    n_instruments,
                    n_samples,
                    " [report]" if args.report else "",
                )

    if args.csv:
        try:
            csv_rows = write_preset_stats_csv(csv_records, args.csv)
            if not args.quiet:
                logging.info("Wrote %d preset stat row(s) to %s", csv_rows, args.csv)
        except Exception as exc:  # noqa: BLE001
            logging.error("Failed to write CSV %s: %s", args.csv, exc)

    if not args.quiet:
        logging.info("Wrote %d record(s) to %s", written, args.output)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    sys.exit(main())
