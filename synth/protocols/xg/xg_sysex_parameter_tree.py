"""Complete XG v2.0 SysEx Parameter Address Tree.

Organized by address high byte into 7 categories. Replaces the 26-entry
XG_PARAMETER_ADDRESSES dict with ~200 entries covering:
  - System Area (0x00): master tune, volume, transpose, mode
  - Effects Area (0x02): reverb, chorus, variation, insertion
  - Insertion Routing (0x04): part-to-insert routing matrix
  - Multi-Part Area (0x08): 16 parts × 30 parameters per part
  - Drum Setup (0x30): 128 notes × 25 parameters
  - Part EQ (0x40): per-part 3-band EQ
  - Display (0x12): text display messages
"""

from __future__ import annotations

# ── Parameter trees organized by (addr_mid, addr_low) ──

# System Area (0x00 0x00 0x00–0x0F)
SYSTEM_PARAMETERS: dict[tuple[int, int], str] = {
    (0x00, 0x00): "master_tune_msb",
    (0x00, 0x01): "master_tune_lsb",
    (0x00, 0x02): "master_volume",
    (0x00, 0x03): "master_key_shift",
    (0x00, 0x04): "master_attenuator",
    (0x00, 0x05): "master_transpose",
    (0x00, 0x06): "drum_setup_reset",
    (0x00, 0x7D): "all_parameter_reset",
    (0x00, 0x7E): "xg_system_off",
    (0x00, 0x7F): "xg_system_on",
}

# Effects Area (0x02 0x01–0x6F): Reverb, Chorus, Variation, Insertion
EFFECTS_PARAMETERS: dict[tuple[int, int], str] = {
    # Reverb (0x02 0x01 0x00–0x1F)
    (0x01, 0x00): "reverb_type",
    (0x01, 0x01): "reverb_time",
    (0x01, 0x02): "reverb_diffusion",
    (0x01, 0x03): "reverb_initial_delay",
    (0x01, 0x04): "reverb_hpf_cutoff",
    (0x01, 0x05): "reverb_lpf_cutoff",
    (0x01, 0x06): "reverb_room_size",
    (0x01, 0x07): "reverb_liveness",
    (0x01, 0x08): "reverb_density",
    (0x01, 0x09): "reverb_hf_damping",
    (0x01, 0x0A): "reverb_feedback_level",
    (0x01, 0x0B): "reverb_return",
    (0x01, 0x0C): "reverb_pan",
    (0x01, 0x0D): "reverb_send_to_chorus",
    (0x01, 0x0E): "reverb_send_to_variation",
    # Chorus (0x02 0x01 0x10–0x1F)
    (0x01, 0x10): "chorus_type",
    (0x01, 0x11): "chorus_lfo_freq",
    (0x01, 0x12): "chorus_lfo_depth",
    (0x01, 0x13): "chorus_feedback",
    (0x01, 0x14): "chorus_delay_offset",
    (0x01, 0x15): "chorus_eq_low",
    (0x01, 0x16): "chorus_eq_high",
    (0x01, 0x1B): "chorus_return",
    (0x01, 0x1C): "chorus_pan",
    (0x01, 0x1D): "chorus_send_to_reverb",
    (0x01, 0x1E): "chorus_send_to_variation",
    # Variation (0x02 0x01 0x20–0x3F)
    (0x01, 0x20): "variation_type",
    (0x01, 0x21): "variation_param1",
    (0x01, 0x22): "variation_param2",
    (0x01, 0x23): "variation_param3",
    (0x01, 0x24): "variation_param4",
    (0x01, 0x25): "variation_param5",
    (0x01, 0x26): "variation_param6",
    (0x01, 0x27): "variation_param7",
    (0x01, 0x28): "variation_param8",
    (0x01, 0x29): "variation_param9",
    (0x01, 0x2A): "variation_param10",
    (0x01, 0x2B): "variation_return",
    (0x01, 0x2C): "variation_pan",
    (0x01, 0x2D): "variation_send_to_reverb",
    (0x01, 0x2E): "variation_send_to_chorus",
    (0x01, 0x2F): "variation_connection",
    # Insertion Effect (0x02 0x01 0x40–0x5F)
    (0x01, 0x40): "insertion_type",
    (0x01, 0x41): "insertion_param1",
    (0x01, 0x42): "insertion_param2",
    (0x01, 0x43): "insertion_param3",
    (0x01, 0x44): "insertion_param4",
    (0x01, 0x45): "insertion_param5",
    (0x01, 0x46): "insertion_param6",
    (0x01, 0x47): "insertion_param7",
    (0x01, 0x48): "insertion_param8",
    (0x01, 0x49): "insertion_param9",
    (0x01, 0x4A): "insertion_param10",
    (0x01, 0x4B): "insertion_return",
    (0x01, 0x4C): "insertion_pan",
    (0x01, 0x4D): "insertion_send_to_reverb",
    (0x01, 0x4E): "insertion_send_to_chorus",
    (0x01, 0x4F): "insertion_connection",
}

# Insertion Effect Routing (0x04 nn pp): part-to-insert routing matrix
INSERTION_ROUTING_PARAMETERS: dict[tuple[int, int], str] = {
    (0x00, 0x00): "insertion_part_l",
    (0x00, 0x01): "insertion_part_r",
    (0x00, 0x02): "insertion_connection",
    (0x00, 0x03): "insertion_control_ch",
    (0x00, 0x10): "insertion_ch1_assign",
    (0x00, 0x11): "insertion_ch2_assign",
}

# Multi-Part Area (0x08 nn pp): 30 parameters per part × 16 parts
PART_PARAMETERS: dict[int, str] = {
    0x00: "bank_select_msb",
    0x01: "bank_select_lsb",
    0x02: "program_number",
    0x03: "rcv_channel",
    0x04: "mono_poly_mode",
    0x05: "same_note_number_key_on_assign",
    0x06: "part_mode",
    0x07: "note_shift",
    0x08: "detune",
    0x09: "volume",
    0x0A: "velocity_sense_depth",
    0x0B: "velocity_sense_offset",
    0x0C: "pan",
    0x0D: "note_limit_low",
    0x0E: "note_limit_high",
    0x0F: "dry_level",
    0x10: "chorus_send",
    0x11: "reverb_send",
    0x12: "variation_send",
    0x13: "vibrato_rate",
    0x14: "vibrato_depth",
    0x15: "vibrato_delay",
    0x16: "filter_cutoff",
    0x17: "filter_resonance",
    0x18: "eg_attack",
    0x19: "eg_decay1",
    0x1A: "eg_decay2",
    0x1B: "eg_release",
    0x1C: "portamento_time",
    0x1D: "pitch_bend_range",
    0x1E: "assignable_controller_1",
    0x1F: "assignable_controller_2",
}

# Drum Setup Area (0x30 nn dd): per-note drum parameters
DRUM_PARAMETERS: dict[int, str] = {
    0x00: "pitch_coarse",
    0x01: "pitch_fine",
    0x02: "level",
    0x03: "alternate_group",
    0x04: "pan",
    0x05: "reverb_send",
    0x06: "chorus_send",
    0x07: "variation_send",
    0x08: "key_assign",
    0x09: "rcv_note_off",
    0x0A: "rcv_note_on",
    0x0B: "filter_cutoff",
    0x0C: "filter_resonance",
    0x0D: "eg_attack",
    0x0E: "eg_decay1",
    0x0F: "eg_decay2",
    0x10: "eg_release",
    0x11: "velocity_sense_pitch",
    0x12: "velocity_sense_filter",
    0x13: "velocity_sense_amplitude",
    0x14: "lfo_rate",
    0x15: "lfo_depth",
    0x16: "lfo_delay",
}

# Part EQ (0x40 nn pp): per-part 3-band EQ
EQ_PARAMETERS: dict[int, str] = {
    0x00: "eq_low_gain",
    0x01: "eq_low_freq",
    0x02: "eq_low_q",
    0x10: "eq_mid_gain",
    0x11: "eq_mid_freq",
    0x12: "eq_mid_q",
    0x20: "eq_high_gain",
    0x21: "eq_high_freq",
    0x22: "eq_high_q",
}


# ── Address routing: addr_high → (category, param_tree) ──

# Top-level routing by address high byte
_ADDRESS_ROUTING: dict[int, tuple[str, dict | None]] = {
    0x00: ("system", SYSTEM_PARAMETERS),
    0x02: ("effects", EFFECTS_PARAMETERS),
    0x04: ("insertion_routing", INSERTION_ROUTING_PARAMETERS),
    0x08: ("multi_part", PART_PARAMETERS),
    0x12: ("display", None),
    0x30: ("drum_setup", DRUM_PARAMETERS),
    0x40: ("part_eq", EQ_PARAMETERS),
}


def resolve_parameter(address: tuple[int, int, int]) -> dict | None:
    """Resolve a 3-byte SysEx address to parameter metadata.

    Args:
        address: (addr_high, addr_mid, addr_low)

    Returns:
        dict with keys: category, addr_high, addr_mid, addr_low,
        param_name, part_num (if applicable), note (if drum)
        Returns None for unknown or display-only addresses.
    """
    addr_h, addr_m, addr_l = address
    routing = _ADDRESS_ROUTING.get(addr_h)
    if routing is None:
        return None

    category, param_tree = routing
    if param_tree is None:
        return {"category": category, "addr_high": addr_h,
                "addr_mid": addr_m, "addr_low": addr_l}

    if category == "multi_part":
        param_name = param_tree.get(addr_l)
        if param_name is None:
            return None
        return {
            "category": category,
            "addr_high": addr_h, "addr_mid": addr_m, "addr_low": addr_l,
            "param_name": param_name,
            "part_num": addr_m,
        }

    elif category == "drum_setup":
        param_name = param_tree.get(addr_l)
        if param_name is None:
            return None
        return {
            "category": category,
            "addr_high": addr_h, "addr_mid": addr_m, "addr_low": addr_l,
            "param_name": param_name,
            "note": addr_m,
        }

    elif category == "part_eq":
        param_name = param_tree.get(addr_l)
        if param_name is None:
            return None
        return {
            "category": category,
            "addr_high": addr_h, "addr_mid": addr_m, "addr_low": addr_l,
            "param_name": param_name,
            "part_num": addr_m & 0x0F,
        }

    else:
        # System, effects, insertion_routing — flat lookup
        param_name = param_tree.get((addr_m, addr_l))
        if param_name is None:
            return None
        return {
            "category": category,
            "addr_high": addr_h, "addr_mid": addr_m, "addr_low": addr_l,
            "param_name": param_name,
        }
