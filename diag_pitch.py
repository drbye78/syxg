#!/usr/bin/env python3
"""Diagnostic: compare synthesizer's actual per-sample increments against
ground-truth values computed from sf2_metadata.jsonl.

Fixes two issues from v1:
  1. SF2 metadata stores generator amounts as unsigned 16-bit; must convert to signed.
  2. Voice hierarchy traversal uses synth.channels[ch].active_voices[vid].active_regions[i].
"""
from __future__ import annotations

import json
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


# ── unsigned → signed conversion for SF2 generator amounts ──────────────

def to_signed16(val: int) -> int:
    """Convert unsigned 16-bit value to signed (SF2 spec uses signed amounts)."""
    return struct.unpack("<h", struct.pack("<H", val & 0xFFFF))[0]


# ── helpers ──────────────────────────────────────────────────────────────

def load_sf2_metadata(path: str) -> dict:
    """Return the single JSON object in sf2_metadata.jsonl."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_preset_lookup(meta: dict) -> dict[tuple[int, int], list[dict]]:
    """Map (bank_msb, program) → list of preset dicts."""
    lookup: dict[tuple[int, int], list[dict]] = {}
    for bank_group in meta.get("presets", []):
        bank_msb = bank_group.get("bank_msb", 0)
        for preset in bank_group.get("presets", []):
            prog = preset.get("preset", 0)
            key = (bank_msb, prog)
            lookup.setdefault(key, []).append(preset)
    return lookup


def effective_pitch_params(
    zone_generators: list[dict], sample_detail: dict
) -> dict:
    """Compute effective root_key, sample_rate, coarse, fine from a zone."""
    gens: dict[int, dict] = {}
    for g in zone_generators:
        gens[g["oper"]] = g

    # Root key: overridingRootKey (gen 58) wins over sample header original_pitch
    gen58 = gens.get(58)
    if gen58 is not None:
        rk_amount = to_signed16(gen58["amount"])
        if rk_amount >= 0:
            root_key = rk_amount
        else:
            root_key = sample_detail.get("original_pitch", 60)
    else:
        root_key = sample_detail.get("original_pitch", 60)

    sample_rate = sample_detail.get("sample_rate", 44100)

    # Coarse tune (gen 51): signed semitones
    gen51 = gens.get(51)
    coarse_tune = to_signed16(gen51["amount"]) if gen51 else 0

    # Fine tune (gen 52): signed cents → semitones
    gen52 = gens.get(52)
    fine_tune = to_signed16(gen52["amount"]) / 100.0 if gen52 else 0.0

    # Sample header pitch_correction (cents → semitones)
    pitch_correction = sample_detail.get("pitch_correction", 0) / 100.0
    fine_tune += pitch_correction

    # Scale tuning (gen 56): percentage (100 = normal chromatic)
    gen56 = gens.get(56)
    scale_tuning = (to_signed16(gen56["amount"]) if gen56 else 100) / 100.0

    return {
        "root_key": root_key,
        "sample_rate": sample_rate,
        "coarse_tune": coarse_tune,
        "fine_tune": fine_tune,
        "scale_tuning": scale_tuning,
    }


def expected_phase_step(
    note: int, params: dict, output_rate: int
) -> tuple[float, str]:
    """Compute expected phase step using the standard SF2 formula.

    Returns (phase_step, warning) where warning is non-empty if clamped.
    """
    note_diff = note - params["root_key"]
    total_semitones = (
        (note_diff + params["coarse_tune"] + params["fine_tune"])
        * params["scale_tuning"]
    )
    warn = ""
    if total_semitones < -48:
        warn = f"clamped from {total_semitones:.1f} to -48"
        total_semitones = -48.0
    elif total_semitones > 48:
        warn = f"clamped from {total_semitones:.1f} to +48"
        total_semitones = 48.0
    pitch_ratio = 2.0 ** (total_semitones / 12.0)
    rate_ratio = params["sample_rate"] / output_rate
    return pitch_ratio * rate_ratio, warn


def midi_note_name(n: int) -> str:
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return f"{names[n % 12]}{(n // 12) - 1}"


# ── parse MIDI to extract notes and programs ────────────────────────────

def parse_midi_info(path: str) -> dict:
    """Return dict with channel→program mapping and note events."""
    from synth.io.midi import FileParser

    parser = FileParser()
    msgs = parser.parse_file(path)

    ch_prog: dict[int, int] = {}
    ch_bank: dict[int, tuple[int, int]] = {}
    note_events: list[dict] = []
    tempo_events: list[dict] = []

    bank_msb: dict[int, int] = {}
    bank_lsb: dict[int, int] = {}

    for msg in msgs:
        ch = msg.channel if msg.channel is not None else 0
        if msg.type == "program_change":
            ch_prog[ch] = msg.data.get("program", 0)
        elif msg.type == "control_change":
            cc = msg.data.get("controller", 0)
            val = msg.data.get("value", 0)
            if cc == 0:
                bank_msb[ch] = val
            elif cc == 32:
                bank_lsb[ch] = val
        elif msg.type == "note_on":
            vel = msg.data.get("velocity", 0)
            if vel > 0:
                note_events.append({
                    "channel": ch,
                    "note": msg.data.get("note", 0),
                    "velocity": vel,
                    "time": msg.timestamp or 0.0,
                })
        elif msg.type == "tempo":
            tempo_events.append({
                "tempo_us": msg.data.get("tempo_us_per_beat", 500000),
                "time": msg.timestamp or 0.0,
            })

    for ch in ch_prog:
        ch_bank[ch] = (bank_msb.get(ch, 0), bank_lsb.get(ch, 0))

    return {
        "channels": ch_prog,
        "banks": ch_bank,
        "note_events": note_events,
        "tempo_events": tempo_events,
        "division": parser.division,
        "messages": msgs,
    }


# ── capture actual phase steps via patched _calculate_phase_step ────────

def capture_actual_phase_steps(
    midi_path: str, sf2_path: str, output_rate: int
) -> dict[tuple[int, int], list[dict]]:
    """Run the synthesizer, capture _base_phase_step via monkey-patch.

    Strategy: patch SF2Region._calculate_phase_step to record all internal
    state (note, root_key, sample_rate, generators, computed step) into a
    thread-local list.  After each note_on, flush the captured entries and
    tag them with the current channel→program mapping.

    Returns dict mapping (program, note) → list of {step, root_key, ...}.
    """
    from synth.synthesizers.rendering import ModernXGSynthesizer
    from synth.io.midi import midimessage_to_bytes, FileParser
    from synth.processing.partial.sf2_region import SF2Region

    synth = ModernXGSynthesizer(
        sample_rate=output_rate, max_channels=16, device_id=0x10
    )
    synth.load_soundfont(sf2_path, priority=0)

    parser = FileParser()
    msgs = parser.parse_file(midi_path)

    ch_prog: dict[int, int] = {}
    bank_msb: dict[int, int] = {}
    results: dict[tuple[int, int], list[dict]] = {}

    # --- capture infrastructure ---
    # Each patch call appends a dict with ALL internal state.
    _pending_captures: list[dict] = []

    original_calc = SF2Region._calculate_phase_step

    def patched_calc(self):
        original_calc(self)
        if getattr(self, "_sample_data", None) is None:
            return
        note = getattr(self, "current_note", None)
        if note is None:
            return
        _pending_captures.append({
            "note": note,
            "step": self._base_phase_step,
            "root_key": self._root_key,
            "sample_rate": self._sample_original_rate,
            "output_rate": self.sample_rate,
            "coarse": self._get_generator_value(51, 0),
            "fine": self._get_generator_value(52, 0),
            "scale": self._get_generator_value(56, 100),
            "overrk": self._get_generator_value(58, -1),
        })

    SF2Region._calculate_phase_step = patched_calc

    try:
        for msg in msgs:
            ch = msg.channel if msg.channel is not None else 0

            if msg.type == "program_change":
                ch_prog[ch] = msg.data.get("program", 0)
            elif msg.type == "control_change":
                cc = msg.data.get("controller", 0)
                val = msg.data.get("value", 0)
                if cc == 0:
                    bank_msb[ch] = val

            raw = midimessage_to_bytes(msg)
            if raw:
                is_note_on = (
                    msg.type == "note_on" and msg.data.get("velocity", 0) > 0
                )
                # Flush captures from PREVIOUS message (if any) before this one
                # (already done at end of loop or before next note_on)

                synth.process_midi_message(raw)

                if is_note_on:
                    prog = ch_prog.get(ch, 0)
                    note = msg.data["note"]
                    key = (prog, note)
                    # All captures generated by this process_midi_message call
                    # belong to this note_on.
                    for cap in _pending_captures:
                        results.setdefault(key, []).append(cap)
                    _pending_captures.clear()
                # For non-note-on messages, discard any captures
                # (e.g. from channel pressure, pitch bend triggering recalc)
                elif _pending_captures:
                    _pending_captures.clear()
    finally:
        SF2Region._calculate_phase_step = original_calc

    return results


# ── main diagnostic ─────────────────────────────────────────────────────

def main():
    sf2_meta_path = "sf2_metadata.jsonl"
    sf2_path = "/mnt/c/Tools/Soundfonts/Timbres Of Heaven GM_GS_XG_SFX V 3.4 Final.sf2"
    midi_path = "tests/test3.mid"
    output_rate = 44100

    print("=" * 120)
    print("PHASE STEP DIAGNOSTIC v2: Synthesizer vs SF2 Ground Truth")
    print("=" * 120)

    # 1. Load SF2 metadata
    print("\n[1] Loading SF2 metadata...")
    meta = load_sf2_metadata(sf2_meta_path)
    preset_lookup = build_preset_lookup(meta)
    print(f"    Loaded {len(preset_lookup)} unique presets from metadata")

    # 2. Parse MIDI
    print("\n[2] Parsing MIDI file...")
    midi_info = parse_midi_info(midi_path)
    print(f"    Division: {midi_info['division']} PPQN")
    print(f"    Channels with programs: {midi_info['channels']}")
    print(f"    Banks: {midi_info['banks']}")
    print(f"    Note events: {len(midi_info['note_events'])}")
    print(f"    Tempo events: {len(midi_info['tempo_events'])}")

    # Unique (program, note) pairs
    unique_notes: set[tuple[int, int]] = set()
    for ev in midi_info["note_events"]:
        ch = ev["channel"]
        prog = midi_info["channels"].get(ch, 0)
        unique_notes.add((prog, ev["note"]))
    print(f"    Unique (program, note) pairs: {len(unique_notes)}")

    # 3. Compute expected phase steps from metadata
    print("\n[3] Computing expected phase steps from SF2 metadata...")
    expected: dict[tuple[int, int], dict] = {}

    for prog, note in sorted(unique_notes):
        presets = preset_lookup.get((0, prog), [])  # bank MSB 0

        if not presets:
            print(
                f"    WARNING: No preset found for bank_msb=0, prog={prog} "
                f"({midi_note_name(note)})"
            )
            continue

        preset = presets[0]
        found = False
        for zone in preset.get("zones", []):
            inst_detail = zone.get("instrument_detail")
            if not inst_detail:
                continue

            # Also check preset-level zone generators for coarse/fine tune
            preset_gens = zone.get("generators", [])
            preset_gens_by_oper = {g["oper"]: g for g in preset_gens}

            inst_zones = inst_detail.get("zones", [])
            for iz in inst_zones:
                kr = iz.get("key_range")
                if kr and len(kr) == 2 and kr[0] <= note <= kr[1]:
                    sample_detail = iz.get("sample_detail")
                    if not sample_detail:
                        continue

                    # Combine instrument-zone and preset-zone generators
                    # Per SF2 spec: preset generators ADD to instrument generators
                    inst_gens = iz.get("generators", [])
                    combined_gens = list(inst_gens)

                    # Add preset-level tune generators (they accumulate)
                    for oper in (51, 52, 56, 58):
                        if oper in preset_gens_by_oper:
                            # Check if instrument zone also has this generator
                            inst_has = any(g["oper"] == oper for g in inst_gens)
                            if not inst_has:
                                combined_gens.append(preset_gens_by_oper[oper])
                            else:
                                # SF2 spec: preset generators ADD to instrument generators
                                # Create a combined entry
                                inst_val = next(
                                    g for g in inst_gens if g["oper"] == oper
                                )
                                preset_val = preset_gens_by_oper[oper]
                                combined_gens.append({
                                    "oper": oper,
                                    "oper_name": inst_val["oper_name"],
                                    "amount": to_signed16(inst_val["amount"])
                                    + to_signed16(preset_val["amount"]),
                                })

                    params = effective_pitch_params(combined_gens, sample_detail)
                    step, warn = expected_phase_step(note, params, output_rate)
                    expected[(prog, note)] = {
                        "params": params,
                        "phase_step": step,
                        "warn": warn,
                        "preset_name": preset.get("name", "?"),
                        "sample_name": sample_detail.get("name", "?"),
                    }
                    found = True
                    break
            if found:
                break

        if not found:
            # Fallback: use any zone with a sample
            for zone in preset.get("zones", []):
                inst_detail = zone.get("instrument_detail")
                if not inst_detail:
                    continue
                inst_zones = inst_detail.get("zones", [])
                for iz in inst_zones:
                    sample_detail = iz.get("sample_detail")
                    if sample_detail:
                        gens = iz.get("generators", [])
                        params = effective_pitch_params(gens, sample_detail)
                        step, warn = expected_phase_step(note, params, output_rate)
                        expected[(prog, note)] = {
                            "params": params,
                            "phase_step": step,
                            "warn": warn,
                            "preset_name": preset.get("name", "?"),
                            "sample_name": sample_detail.get("name", "?"),
                            "note": "fallback (no key range match)",
                        }
                        found = True
                        break
                if found:
                    break

    print(f"    Computed expected values for {len(expected)} (program, note) pairs")

    # Show a few sample params for verification
    print("\n    Sample expected params (first 5):")
    for (prog, note), exp in sorted(expected.items())[:5]:
        p = exp["params"]
        print(
            f"      prog={prog} note={midi_note_name(note)}({note}) "
            f"root={p['root_key']} srate={p['sample_rate']} "
            f"coarse={p['coarse_tune']:+.0f} fine={p['fine_tune']:+.3f} "
            f"→ step={exp['phase_step']:.8f}"
        )

    # 4. Capture actual phase steps from synthesizer
    print("\n[4] Running synthesizer to capture actual phase steps...")
    print(f"    SF2: {sf2_path}")
    print(f"    MIDI: {midi_path}")
    print(f"    Output rate: {output_rate} Hz")

    try:
        actual = capture_actual_phase_steps(midi_path, sf2_path, output_rate)
        print(f"    Captured actual values for {len(actual)} unique (program, note) pairs")

        # Show captured sample info
        if actual:
            print("\n    Sample captured params (first 5):")
            for (prog, note), infos in sorted(actual.items())[:5]:
                info = infos[0]
                print(
                    f"      prog={prog} note={midi_note_name(note)}({note}) "
                    f"root={info['root_key']} srate={info['sample_rate']} "
                    f"coarse={info['coarse']:+.0f} fine={info['fine']:+.0f} "
                    f"overrk={info['overrk']} "
                    f"→ step={info['step']:.8f}"
                )
    except Exception as e:
        print(f"    ERROR capturing actuals: {e}")
        import traceback
        traceback.print_exc()
        actual = {}

    # 5. Comparison table
    print("\n" + "=" * 140)
    print("COMPARISON TABLE")
    print("=" * 140)

    header = (
        f"{'Prog':>4s} {'Note':>5s} {'MIDI#':>5s} | "
        f"{'Preset':<20s} {'Sample':<20s} | "
        f"{'Root':>4s} {'SRate':>6s} {'Coars':>5s} {'Fine':>6s} | "
        f"{'Expected':>12s} {'Actual':>12s} {'Ratio':>10s} {'Err(st)':>8s} | Status"
    )
    print(header)
    print("-" * len(header))

    mismatches = 0
    exact_matches = 0
    for (prog, note) in sorted(expected.keys()):
        exp = expected[(prog, note)]
        params = exp["params"]
        exp_step = exp["phase_step"]
        act_infos = actual.get((prog, note), [])
        act_step = act_infos[0]["step"] if act_infos else None

        note_str = midi_note_name(note)

        if act_step is not None:
            ratio = act_step / exp_step if exp_step != 0 else 0
            semitone_err = 12.0 * math.log2(ratio) if ratio > 0 else 0
            if abs(ratio - 1.0) < 0.0001:
                status = "OK"
                exact_matches += 1
            elif abs(semitone_err) < 0.01:
                status = f"~OK {semitone_err:+.3f}st"
                exact_matches += 1
            else:
                status = f"ERR {semitone_err:+.3f}st"
                mismatches += 1
        else:
            ratio = None
            semitone_err = None
            status = "NOT CAPTURED"

        print(
            f"{prog:4d} {note_str:>5s} {note:5d} | "
            f"{exp['preset_name']:<20s} {exp['sample_name']:<20s} | "
            f"{params['root_key']:4.0f} {params['sample_rate']:6.0f} "
            f"{params['coarse_tune']:+5.0f} {params['fine_tune']:+6.3f} | "
            f"{exp_step:12.8f} "
            f"{f'{act_step:.8f}' if act_step is not None else 'N/A':>12s} "
            f"{f'{ratio:.8f}' if ratio is not None else 'N/A':>10s} "
            f"{f'{semitone_err:+.3f}' if semitone_err is not None else 'N/A':>8s} | "
            f"{status}"
        )

    print("-" * len(header))
    print(
        f"\nResults: {exact_matches} matched, {mismatches} mismatches, "
        f"{len(expected) - exact_matches - mismatches} not captured "
        f"out of {len(expected)} total"
    )

    if mismatches > 0:
        print("\n*** PHASE STEP MISMATCH DETECTED — pitch calculation bug confirmed ***")
        print("    The synthesizer produces different phase steps than the SF2 formula dictates.")
        print("    This causes the reported higher-pitch issue.")
    elif exact_matches == len(expected):
        print("\nAll captured phase steps match expected values. Pitch formula is correct.")
        print("    The higher-pitch issue may be elsewhere (e.g., wrong sample selection,")
        print("    missing generators, or different key range resolution).")

    # 6. Tempo analysis
    print("\n" + "=" * 120)
    print("TEMPO ANALYSIS")
    print("=" * 120)
    for te in midi_info["tempo_events"][:10]:
        bpm = 60_000_000 / te["tempo_us"]
        print(f"  t={te['time']:.4f}s  tempo={te['tempo_us']} us/beat  BPM={bpm:.1f}")

    if len(midi_info["tempo_events"]) > 10:
        print(f"  ... ({len(midi_info['tempo_events'])} total tempo events)")

    return mismatches == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
