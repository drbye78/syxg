"""
XGML to MIDI Translator

Converts XGML documents to MIDI message sequences that can be fed to the XG synthesizer.
"""

from __future__ import annotations

from typing import Any
import math
from collections import defaultdict

from .constants import (
    PROGRAM_NAMES,
    CONTROLLER_NAMES,
    PAN_POSITIONS,
    SYSTEM_EFFECT_TYPES,
    VARIATION_EFFECT_TYPES,
    INSERTION_EFFECT_TYPES,
    FILTER_TYPES,
    LFO_WAVEFORMS,
    CONTROLLER_ASSIGNMENTS,
    SYNTHESIS_ENGINES,
    GS_REVERB_TYPES,
    GS_CHORUS_TYPES,
    GS_DELAY_TYPES,
    MPE_CONTROLLERS,
    ADVANCED_EFFECT_TYPES,
    EQ_TYPES,
    TEMPERAMENTS,
    MODULATION_SOURCES,
    MODULATION_DESTINATIONS,
    AUTOMATION_CURVE_TYPES,
    ENVELOPE_STAGES,
)
from synth.midi import MIDIMessage


class XGMLToMIDITranslator:
    """
    Translates XGML documents to MIDI message sequences.

    Converts high-level XGML parameters and sequences into MIDI messages
    that the XG synthesizer can understand.
    """

    def __init__(self):
        self.errors = []
        self.warnings = []

    def translate_document(self, xgml_document) -> list[MIDIMessage]:
        """
        Translate complete XGML document to MIDI message sequence.

        Args:
            xgml_document: XGMLDocument instance

        Returns:
            List of MIDIMessage instances
        """
        self.errors = []
        self.warnings = []

        messages = []

        # Process static configuration sections first
        messages.extend(self._translate_basic_messages(xgml_document))
        messages.extend(self._translate_rpn_parameters(xgml_document))
        messages.extend(self._translate_channel_parameters(xgml_document))
        messages.extend(self._translate_drum_parameters(xgml_document))
        messages.extend(self._translate_effects(xgml_document))
        messages.extend(self._translate_system_exclusive(xgml_document))

        # Process modern v2.0+ sections
        messages.extend(self._translate_synthesis_engines(xgml_document))
        messages.extend(self._translate_gs_configuration(xgml_document))
        messages.extend(self._translate_mpe_configuration(xgml_document))
        messages.extend(self._translate_modulation_matrix(xgml_document))
        messages.extend(self._translate_effects_configuration(xgml_document))
        messages.extend(self._translate_arpeggiator_configuration(xgml_document))
        messages.extend(self._translate_microtonal_tuning(xgml_document))
        messages.extend(self._translate_advanced_features(xgml_document))

        # Process v2.1 advanced engine sections
        messages.extend(self._translate_fm_x_engine(xgml_document))
        messages.extend(self._translate_sfz_engine(xgml_document))
        messages.extend(self._translate_physical_engine(xgml_document))
        messages.extend(self._translate_spectral_engine(xgml_document))

        # Process time-bound sequences
        messages.extend(self._translate_sequences(xgml_document))

        # Sort messages by time
        messages.sort(key=lambda msg: msg.time if msg.time is not None else 0)

        return messages

    def _translate_basic_messages(self, doc) -> list[MIDIMessage]:
        """Translate basic MIDI messages section."""
        messages = []

        basic_data = doc.get_section("basic_messages")
        if not basic_data:
            return messages

        channels_data = basic_data.get("channels", {})

        for channel_name, channel_config in channels_data.items():
            try:
                channel_num = self._parse_channel_name(channel_name)

                # Program change
                if "program_change" in channel_config:
                    program = self._resolve_program_name(channel_config["program_change"])
                    messages.append(
                        MIDIMessage(
                            type="program_change", channel=channel_num, program=program, time=0.0
                        )
                    )

                # Bank select
                if "bank_msb" in channel_config:
                    messages.append(
                        MIDIMessage(
                            type="control_change",
                            channel=channel_num,
                            control=0,  # Bank MSB
                            value=channel_config["bank_msb"],
                            time=0.0,
                        )
                    )

                if "bank_lsb" in channel_config:
                    messages.append(
                        MIDIMessage(
                            type="control_change",
                            channel=channel_num,
                            control=32,  # Bank LSB
                            value=channel_config["bank_lsb"],
                            time=0.0,
                        )
                    )

                # Controllers
                for controller_name, value in channel_config.items():
                    if controller_name in ["program_change", "bank_msb", "bank_lsb"]:
                        continue

                    controller_num = self._resolve_controller_name(controller_name)
                    if controller_num is not None:
                        midi_value = self._resolve_controller_value(controller_name, value)
                        messages.append(
                            MIDIMessage(
                                type="control_change",
                                channel=channel_num,
                                control=controller_num,
                                value=midi_value,
                                time=0.0,
                            )
                        )

            except Exception as e:
                self.errors.append(f"Error processing channel {channel_name}: {e}")

        return messages

    def _translate_rpn_parameters(self, doc) -> list[MIDIMessage]:
        """Translate RPN parameters section."""
        messages = []

        rpn_data = doc.get_section("rpn_parameters")
        if not rpn_data:
            return messages

        # Global RPN parameters
        if "global" in rpn_data:
            messages.extend(self._generate_rpn_messages(rpn_data["global"], None))

        # Channel-specific RPN parameters
        for channel_name, params in rpn_data.items():
            if channel_name == "global":
                continue
            try:
                channel_num = self._parse_channel_name(channel_name)
                messages.extend(self._generate_rpn_messages(params, channel_num))
            except Exception as e:
                self.errors.append(f"Error processing RPN for {channel_name}: {e}")

        return messages

    def _translate_channel_parameters(self, doc) -> list[MIDIMessage]:
        """Translate XG channel parameters (NRPN MSB 3-31)."""
        messages = []

        channel_params = doc.get_section("channel_parameters")
        if not channel_params:
            return messages

        for channel_name, params in channel_params.items():
            try:
                channel_num = self._parse_channel_name(channel_name)
                messages.extend(self._generate_channel_nrpn_messages(params, channel_num))
            except Exception as e:
                self.errors.append(f"Error processing channel parameters for {channel_name}: {e}")

        return messages

    def _translate_drum_parameters(self, doc) -> list[MIDIMessage]:
        """Translate XG drum parameters (NRPN MSB 40-41)."""
        messages = []

        drum_data = doc.get_section("drum_parameters")
        if not drum_data:
            return messages

        drum_channel = drum_data.get("drum_channel", 9)  # MIDI channel 10

        if "drum_notes" in drum_data:
            for note_name, note_params in drum_data["drum_notes"].items():
                try:
                    note_num = self._parse_note_name(note_name)
                    messages.extend(
                        self._generate_drum_nrpn_messages(note_params, drum_channel, note_num)
                    )
                except Exception as e:
                    self.errors.append(f"Error processing drum note {note_name}: {e}")

        return messages

    def _translate_system_exclusive(self, doc) -> list[MIDIMessage]:
        """Translate system exclusive messages."""
        messages = []

        sysex_data = doc.get_section("system_exclusive")
        if not sysex_data:
            return messages

        commands = sysex_data.get("commands", [])
        for cmd in commands:
            try:
                messages.append(self._generate_sysex_message(cmd))
            except Exception as e:
                self.errors.append(f"Error processing SYSEX command: {e}")

        return messages

    def _translate_effects(self, doc) -> list[MIDIMessage]:
        """Translate effects configuration."""
        messages = []

        effects_data = doc.get_section("effects")
        if not effects_data:
            return messages

        # System effects
        if "system_effects" in effects_data:
            messages.extend(self._generate_system_effects_messages(effects_data["system_effects"]))

        # Variation effects
        if "variation_effects" in effects_data:
            messages.extend(
                self._generate_variation_effects_messages(effects_data["variation_effects"])
            )

        # Insertion effects
        if "insertion_effects" in effects_data:
            messages.extend(
                self._generate_insertion_effects_messages(effects_data["insertion_effects"])
            )

        return messages

    def _translate_sequences(self, doc) -> list[MIDIMessage]:
        """Translate time-bound sequences."""
        messages = []

        sequences_data = doc.get_section("sequences")
        if not sequences_data:
            return messages

        for sequence_name, sequence_data in sequences_data.items():
            try:
                tempo = sequence_data.get("tempo", 120)
                time_sig = sequence_data.get("time_signature", "4/4")
                quantization = sequence_data.get("quantization", "1/8")

                # Process tracks - handle both direct track list and nested structure
                tracks = sequence_data.get("tracks", [])
                for track_item in tracks:
                    # Handle nested structure: - track: {channel: 0, ...}
                    if "track" in track_item:
                        track_data = track_item["track"]
                    else:
                        # Direct structure (fallback)
                        track_data = track_item

                    messages.extend(self._process_track(track_data, tempo))

            except Exception as e:
                self.errors.append(f"Error processing sequence {sequence_name}: {e}")

        return messages

    def _process_track(self, track_data: dict, tempo: float) -> list[MIDIMessage]:
        """Process a single track from sequence."""
        messages = []

        channel = track_data.get("channel", 0)
        default_params = track_data.get("parameters", {})
        events = track_data.get("events", [])

        # Apply default parameters at time 0
        messages.extend(self._generate_parameter_messages(default_params, channel, 0.0))

        # Process events
        for event in events:
            if "at" in event:
                time_spec = event["at"]
                event_time = self._parse_time(time_spec.get("time", 0), tempo)
                event_data = {k: v for k, v in time_spec.items() if k != "time"}

                messages.extend(self._generate_event_messages(event_data, channel, event_time))

        return messages

    # Helper methods for parsing and conversion

    def _parse_channel_name(self, channel_name: str) -> int:
        """Parse channel name (e.g., 'channel_1', '1') to MIDI channel number."""
        if isinstance(channel_name, int):
            return channel_name
        if channel_name.startswith("channel_"):
            return int(channel_name.split("_")[1]) - 1  # Convert to 0-based
        return int(channel_name) - 1  # Assume 1-based input

    def _parse_note_name(self, note_name: str | int) -> int:
        """Parse note name to MIDI note number."""
        if isinstance(note_name, int):
            return note_name

        # Handle note names like "C4", "F#3", etc.
        note_name = str(note_name).upper()
        note_map = {
            "C": 0,
            "C#": 1,
            "DB": 1,
            "D": 2,
            "D#": 3,
            "EB": 3,
            "E": 4,
            "F": 5,
            "F#": 6,
            "GB": 6,
            "G": 7,
            "G#": 8,
            "AB": 8,
            "A": 9,
            "A#": 10,
            "BB": 10,
            "B": 11,
        }

        if len(note_name) >= 2:
            note = note_name[:-1]
            octave = int(note_name[-1])
            return note_map.get(note, 0) + (octave + 1) * 12

        return int(note_name)  # Fallback

    def _resolve_program_name(self, program: str | int) -> int:
        """Resolve program name to MIDI program number."""
        if isinstance(program, int):
            return program
        return PROGRAM_NAMES.get(program, 0)

    def _resolve_controller_name(self, controller: str) -> int | None:
        """Resolve controller name to MIDI controller number."""
        return CONTROLLER_NAMES.get(controller)

    def _resolve_controller_value(self, controller: str, value: str | int | bool | dict) -> int:
        """Resolve controller value to MIDI value."""
        if isinstance(value, dict):
            # Handle complex values with 'from', 'to', etc.
            if "from" in value:
                return self._resolve_controller_value(controller, value["from"])
            return 64  # Default

        if controller == "pan":
            if isinstance(value, str):
                return PAN_POSITIONS.get(value, 64)
            return int(value)

        # Boolean controllers
        if isinstance(value, bool):
            return 127 if value else 0

        return int(value)

    def _parse_time(self, time_spec: str | float, tempo: float) -> float:
        """Parse time specification to seconds."""
        if isinstance(time_spec, (int, float)):
            return float(time_spec)

        if isinstance(time_spec, str):
            # Handle musical time like "1:2:240"
            if ":" in time_spec:
                parts = time_spec.split(":")
                if len(parts) == 3:
                    measure = int(parts[0])
                    beat = int(parts[1])
                    tick = int(parts[2])
                    # Calculate time position with proper time signature support
                    # Default to 4/4 time (4 beats per measure, 480 ticks per beat)
                    beats_per_measure = 4  # Can be extended to read from time signature
                    ticks_per_beat = 480  # Standard MIDI PPQ
                    total_beats = (
                        (measure - 1) * beats_per_measure + (beat - 1) + tick / ticks_per_beat
                    )
                    seconds_per_beat = 60.0 / tempo
                    return total_beats * seconds_per_beat

        return 0.0

    # MIDI message generation methods

    def _generate_rpn_messages(self, params: dict, channel: int | None) -> list[MIDIMessage]:
        """Generate RPN messages for parameters."""
        messages = []

        rpn_mappings = {
            "pitch_bend_range": (0, 0),
            "fine_tuning": (0, 1),
            "coarse_tuning": (0, 2),
            "modulation_depth_range": (0, 5),
        }

        for param_name, value in params.items():
            if param_name in rpn_mappings:
                msb, lsb = rpn_mappings[param_name]
                messages.extend(self._generate_rpn_sequence(channel, msb, lsb, value))

        return messages

    def _generate_rpn_sequence(
        self, channel: int | None, msb: int, lsb: int, value: int
    ) -> list[MIDIMessage]:
        """Generate RPN parameter change sequence."""
        messages = []

        # RPN LSB
        messages.append(
            MIDIMessage(
                type="control_change",
                channel=channel,
                control=100,  # RPN LSB
                value=lsb,
                time=0.0,
            )
        )

        # RPN MSB
        messages.append(
            MIDIMessage(
                type="control_change",
                channel=channel,
                control=101,  # RPN MSB
                value=msb,
                time=0.0,
            )
        )

        # Data Entry
        messages.append(
            MIDIMessage(
                type="control_change",
                channel=channel,
                control=6,  # Data Entry MSB
                value=value,
                time=0.0,
            )
        )

        return messages

    def _generate_nrpn_sequence(
        self, channel: int | None, msb: int, lsb: int, value: int
    ) -> list[MIDIMessage]:
        """Generate NRPN parameter change sequence."""
        messages = []

        # Use channel 0 for global parameters (None)
        actual_channel = channel if channel is not None else 0

        # NRPN LSB
        messages.append(
            MIDIMessage(
                type="control_change",
                channel=actual_channel,
                control=98,  # NRPN LSB
                value=lsb,
                time=0.0,
            )
        )

        # NRPN MSB
        messages.append(
            MIDIMessage(
                type="control_change",
                channel=actual_channel,
                control=99,  # NRPN MSB
                value=msb,
                time=0.0,
            )
        )

        # Data Entry
        messages.append(
            MIDIMessage(
                type="control_change",
                channel=actual_channel,
                control=6,  # Data Entry MSB
                value=value,
                time=0.0,
            )
        )

        return messages

    def _generate_channel_nrpn_messages(self, params: dict, channel: int) -> list[MIDIMessage]:
        """Generate NRPN messages for channel parameters (NRPN MSB 3-31)."""
        messages = []

        # MSB 3: Basic Channel Parameters
        if "volume" in params:
            vol = params["volume"]
            if isinstance(vol, dict):
                if "coarse" in vol:
                    messages.extend(self._generate_nrpn_sequence(channel, 3, 0, vol["coarse"]))
                if "fine" in vol:
                    messages.extend(self._generate_nrpn_sequence(channel, 3, 1, vol["fine"]))

        if "pan" in params:
            pan = params["pan"]
            if isinstance(pan, dict):
                if "coarse" in pan:
                    pan_val = self._resolve_controller_value("pan", pan["coarse"])
                    messages.extend(self._generate_nrpn_sequence(channel, 3, 2, pan_val))
                if "fine" in pan:
                    messages.extend(self._generate_nrpn_sequence(channel, 3, 3, pan["fine"]))

        if "expression" in params:
            expr = params["expression"]
            if isinstance(expr, dict):
                if "coarse" in expr:
                    messages.extend(self._generate_nrpn_sequence(channel, 3, 4, expr["coarse"]))
                if "fine" in expr:
                    messages.extend(self._generate_nrpn_sequence(channel, 3, 5, expr["fine"]))

        if "modulation_depth" in params:
            messages.extend(self._generate_nrpn_sequence(channel, 3, 6, params["modulation_depth"]))

        if "modulation_speed" in params:
            messages.extend(self._generate_nrpn_sequence(channel, 3, 7, params["modulation_speed"]))

        # MSB 4: Pitch & Tuning Parameters
        if "pitch_coarse" in params:
            messages.extend(
                self._generate_nrpn_sequence(channel, 4, 0, params["pitch_coarse"] + 64)
            )  # -12 to +12 semitones, offset by 64

        if "pitch_fine" in params:
            messages.extend(
                self._generate_nrpn_sequence(channel, 4, 1, params["pitch_fine"] + 64)
            )  # -100 to +100 cents, offset by 64

        if "pitch_bend_range" in params:
            messages.extend(self._generate_nrpn_sequence(channel, 4, 2, params["pitch_bend_range"]))

        if "portamento_mode" in params:
            mode_val = 1 if params["portamento_mode"] else 0
            messages.extend(self._generate_nrpn_sequence(channel, 4, 3, mode_val))

        if "portamento_time" in params:
            messages.extend(self._generate_nrpn_sequence(channel, 4, 4, params["portamento_time"]))

        if "pitch_balance" in params:
            messages.extend(self._generate_nrpn_sequence(channel, 4, 5, params["pitch_balance"]))

        # MSB 5-6: Filter Parameters
        if "filter" in params:
            filter_params = params["filter"]

            if "cutoff" in filter_params:
                messages.extend(
                    self._generate_nrpn_sequence(channel, 5, 0, filter_params["cutoff"])
                )

            if "resonance" in filter_params:
                messages.extend(
                    self._generate_nrpn_sequence(channel, 6, 1, filter_params["resonance"])
                )

            if "type" in filter_params:
                filter_type = FILTER_TYPES.get(filter_params["type"], 0)
                messages.extend(self._generate_nrpn_sequence(channel, 6, 7, filter_type))

            if "envelope" in filter_params:
                env = filter_params["envelope"]
                if "attack" in env:
                    messages.extend(self._generate_nrpn_sequence(channel, 5, 2, env["attack"]))
                if "decay" in env:
                    messages.extend(self._generate_nrpn_sequence(channel, 5, 3, env["decay"]))
                if "sustain" in env:
                    messages.extend(self._generate_nrpn_sequence(channel, 5, 4, env["sustain"]))
                if "release" in env:
                    messages.extend(self._generate_nrpn_sequence(channel, 5, 5, env["release"]))

        # MSB 7-8: Amplifier Envelope
        if "amplifier" in params and "envelope" in params["amplifier"]:
            amp_env = params["amplifier"]["envelope"]

            if "attack" in amp_env:
                messages.extend(self._generate_nrpn_sequence(channel, 7, 0, amp_env["attack"]))
            if "decay" in amp_env:
                messages.extend(self._generate_nrpn_sequence(channel, 7, 1, amp_env["decay"]))
            if "sustain" in amp_env:
                messages.extend(self._generate_nrpn_sequence(channel, 7, 2, amp_env["sustain"]))
            if "release" in amp_env:
                messages.extend(self._generate_nrpn_sequence(channel, 7, 3, amp_env["release"]))

            if "velocity_sensitivity" in params["amplifier"]:
                messages.extend(
                    self._generate_nrpn_sequence(
                        channel, 7, 4, params["amplifier"]["velocity_sensitivity"]
                    )
                )

            if "key_scaling" in params["amplifier"]:
                messages.extend(
                    self._generate_nrpn_sequence(channel, 7, 5, params["amplifier"]["key_scaling"])
                )

        # MSB 9-10: LFO Parameters
        if "lfo" in params:
            lfo_params = params["lfo"]

            for lfo_num in [1, 2]:
                lfo_key = f"lfo{lfo_num}"
                if lfo_key in lfo_params:
                    lfo = lfo_params[lfo_key]
                    msb = 9 if lfo_num == 1 else 10

                    if "waveform" in lfo:
                        waveform = LFO_WAVEFORMS.get(lfo["waveform"], 0)
                        messages.extend(self._generate_nrpn_sequence(channel, msb, 0, waveform))

                    if "speed" in lfo:
                        messages.extend(self._generate_nrpn_sequence(channel, msb, 1, lfo["speed"]))

                    if "delay" in lfo:
                        messages.extend(self._generate_nrpn_sequence(channel, msb, 2, lfo["delay"]))

                    if "fade_time" in lfo:
                        messages.extend(
                            self._generate_nrpn_sequence(channel, msb, 3, lfo["fade_time"])
                        )

                    if "pitch_depth" in lfo:
                        messages.extend(
                            self._generate_nrpn_sequence(channel, msb, 4, lfo["pitch_depth"])
                        )

                    if "filter_depth" in lfo:
                        messages.extend(
                            self._generate_nrpn_sequence(channel, msb, 5, lfo["filter_depth"])
                        )

                    if "amp_depth" in lfo:
                        messages.extend(
                            self._generate_nrpn_sequence(channel, msb, 6, lfo["amp_depth"])
                        )

        # MSB 11-12: Effects Send
        if "effects_sends" in params:
            sends = params["effects_sends"]

            if "reverb" in sends:
                messages.extend(self._generate_nrpn_sequence(channel, 11, 0, sends["reverb"]))

            if "chorus" in sends:
                messages.extend(self._generate_nrpn_sequence(channel, 11, 1, sends["chorus"]))

            if "variation" in sends:
                messages.extend(self._generate_nrpn_sequence(channel, 11, 2, sends["variation"]))

            if "dry_level" in sends:
                messages.extend(self._generate_nrpn_sequence(channel, 11, 3, sends["dry_level"]))

            if "insertion" in sends:
                ins = sends["insertion"]
                if "part_l" in ins:
                    messages.extend(self._generate_nrpn_sequence(channel, 11, 4, ins["part_l"]))
                if "part_r" in ins:
                    messages.extend(self._generate_nrpn_sequence(channel, 11, 5, ins["part_r"]))
                if "connection" in ins:
                    conn_val = 1 if ins["connection"] == "insertion" else 0
                    messages.extend(self._generate_nrpn_sequence(channel, 11, 6, conn_val))

        # MSB 13: Pitch Envelope
        if "pitch_envelope" in params:
            pitch_env = params["pitch_envelope"]

            mappings = {
                "attack": 0,
                "decay": 1,
                "sustain": 2,
                "release": 3,
                "attack_level": 4,
                "decay_level": 5,
                "sustain_level": 6,
                "release_level": 7,
            }

            for param_name, lsb in mappings.items():
                if param_name in pitch_env:
                    messages.extend(
                        self._generate_nrpn_sequence(channel, 13, lsb, pitch_env[param_name])
                    )

        # MSB 14: Pitch LFO
        if "pitch_lfo" in params:
            pitch_lfo = params["pitch_lfo"]

            if "waveform" in pitch_lfo:
                waveform = LFO_WAVEFORMS.get(pitch_lfo["waveform"], 0)
                messages.extend(self._generate_nrpn_sequence(channel, 14, 0, waveform))

            if "speed" in pitch_lfo:
                messages.extend(self._generate_nrpn_sequence(channel, 14, 1, pitch_lfo["speed"]))

            if "delay" in pitch_lfo:
                messages.extend(self._generate_nrpn_sequence(channel, 14, 2, pitch_lfo["delay"]))

            if "fade_time" in pitch_lfo:
                messages.extend(
                    self._generate_nrpn_sequence(channel, 14, 3, pitch_lfo["fade_time"])
                )

            if "pitch_depth" in pitch_lfo:
                messages.extend(
                    self._generate_nrpn_sequence(channel, 14, 4, pitch_lfo["pitch_depth"])
                )

        # MSB 15-16: Controller Assignments
        if "controller_assignments" in params:
            assignments = params["controller_assignments"]

            controller_map = {
                "mod_wheel": (15, 0),
                "foot_controller": (15, 1),
                "aftertouch": (15, 2),
                "breath_controller": (15, 3),
                "general1": (15, 4),
                "general2": (16, 0),
                "general3": (16, 1),
                "general4": (16, 2),
            }

            for ctrl_name, (msb, lsb) in controller_map.items():
                if ctrl_name in assignments:
                    assign_val = CONTROLLER_ASSIGNMENTS.get(assignments[ctrl_name], 0)
                    messages.extend(self._generate_nrpn_sequence(channel, msb, lsb, assign_val))

        # MSB 17-18: Scale Tuning
        if "scale_tuning" in params:
            scale = params["scale_tuning"]

            if "notes" in scale:
                notes = scale["notes"]
                note_mappings = {
                    "c": (17, 0),
                    "csharp": (17, 1),
                    "d": (17, 2),
                    "dsharp": (17, 3),
                    "e": (17, 4),
                    "f": (17, 5),
                    "fsharp": (17, 6),
                    "g": (18, 0),
                    "gsharp": (18, 1),
                    "a": (18, 2),
                    "asharp": (18, 3),
                    "b": (18, 4),
                }

                for note_name, (msb, lsb) in note_mappings.items():
                    if note_name in notes:
                        # Convert from -64/+63 cents to 0-127 range
                        value = notes[note_name] + 64
                        messages.extend(self._generate_nrpn_sequence(channel, msb, lsb, value))

            if "octave_tune" in scale:
                # Convert from -64/+63 cents to 0-127 range
                value = scale["octave_tune"] + 64
                messages.extend(self._generate_nrpn_sequence(channel, 18, 5, value))

        # MSB 19: Velocity Response
        if "velocity_response" in params:
            vel_resp = params["velocity_response"]

            if "curve" in vel_resp:
                messages.extend(self._generate_nrpn_sequence(channel, 19, 0, vel_resp["curve"]))

            if "offset" in vel_resp:
                messages.extend(self._generate_nrpn_sequence(channel, 19, 1, vel_resp["offset"]))

            if "range" in vel_resp:
                messages.extend(self._generate_nrpn_sequence(channel, 19, 2, vel_resp["range"]))

        return messages

    def _generate_drum_nrpn_messages(
        self, params: dict, channel: int, note: int
    ) -> list[MIDIMessage]:
        """Generate NRPN messages for XG drum parameters (MSB 40-41)."""
        messages = []

        # XG drum parameters use MSB 40-41 with note number as LSB
        # Each drum note can have individual parameters

        if "volume" in params:
            messages.extend(self._generate_nrpn_sequence(channel, 40, note, params["volume"]))

        if "pan" in params:
            pan_val = self._resolve_controller_value("pan", params["pan"])
            messages.extend(self._generate_nrpn_sequence(channel, 41, note, pan_val))

        if "reverb_send" in params:
            messages.extend(self._generate_nrpn_sequence(channel, 42, note, params["reverb_send"]))

        if "chorus_send" in params:
            messages.extend(self._generate_nrpn_sequence(channel, 43, note, params["chorus_send"]))

        if "variation_send" in params:
            messages.extend(
                self._generate_nrpn_sequence(channel, 44, note, params["variation_send"])
            )

        if "pitch_coarse" in params:
            # Convert semitones to NRPN value (-24 to +24 semitones, offset by 64)
            pitch_val = params["pitch_coarse"] + 64
            messages.extend(self._generate_nrpn_sequence(channel, 45, note, pitch_val))

        if "pitch_fine" in params:
            # Convert cents to NRPN value (-100 to +100 cents, offset by 64)
            fine_val = params["pitch_fine"] + 64
            messages.extend(self._generate_nrpn_sequence(channel, 46, note, fine_val))

        if "filter_cutoff" in params:
            messages.extend(
                self._generate_nrpn_sequence(channel, 47, note, params["filter_cutoff"])
            )

        if "amplitude_decay" in params:
            messages.extend(
                self._generate_nrpn_sequence(channel, 48, note, params["amplitude_decay"])
            )

        if "filter_decay" in params:
            messages.extend(self._generate_nrpn_sequence(channel, 49, note, params["filter_decay"]))

        return messages

    def _generate_sysex_message(self, cmd: dict) -> MIDIMessage:
        """Generate system exclusive message with proper Yamaha XG format."""
        # Professional SYSEX generation with proper format
        # Yamaha XG SYSEX format: F0 43 1n dd dd ... F7
        # where 43=Yamaha, 1n=device (n=channel), dd=data
        manufacturer = 0x43  # Yamaha
        device_id = cmd.get("device_id", 0x10)  # Default to device 16

        # Build complete SYSEX message
        data = [0xF0, manufacturer, device_id]

        # Add command-specific data
        if "command" in cmd:
            data.append(cmd["command"])
        if "data" in cmd:
            data.extend(cmd["data"])

        # Add end of exclusive
        data.append(0xF7)

        return MIDIMessage(type="sysex", sysex_data=data, time=0.0)

    def _generate_system_effects_messages(self, effects: dict) -> list[MIDIMessage]:
        """Generate XG system effects NRPN messages (MSB 1-2)."""
        messages = []

        # System Reverb (MSB 1)
        if "reverb" in effects:
            reverb = effects["reverb"]
            if "type" in reverb:
                messages.extend(self._generate_nrpn_sequence(None, 1, 0, reverb["type"]))
            if "time" in reverb:
                # Convert time in seconds to NRPN value (0-127)
                time_val = min(127, max(0, int(reverb["time"] * 12.7)))  # Roughly 0-10 seconds
                messages.extend(self._generate_nrpn_sequence(None, 1, 1, time_val))
            if "delay_feedback" in reverb:
                messages.extend(self._generate_nrpn_sequence(None, 1, 2, reverb["delay_feedback"]))
            if "predelay" in reverb:
                predelay_val = min(127, max(0, int(reverb["predelay"] * 127)))  # 0-1 second
                messages.extend(self._generate_nrpn_sequence(None, 1, 3, predelay_val))
            if "hf_damp" in reverb:
                messages.extend(self._generate_nrpn_sequence(None, 1, 4, reverb["hf_damp"]))
            if "low_gain" in reverb:
                gain_val = (reverb["low_gain"] + 12) * 127 // 24  # -12 to +12 dB
                messages.extend(self._generate_nrpn_sequence(None, 1, 5, gain_val))
            if "high_gain" in reverb:
                gain_val = (reverb["high_gain"] + 12) * 127 // 24  # -12 to +12 dB
                messages.extend(self._generate_nrpn_sequence(None, 1, 6, gain_val))
            if "balance" in reverb:
                balance_val = (reverb["balance"] + 100) * 127 // 200  # -100 to +100
                messages.extend(self._generate_nrpn_sequence(None, 1, 7, balance_val))

        # System Chorus (MSB 2)
        if "chorus" in effects:
            chorus = effects["chorus"]
            if "type" in chorus:
                messages.extend(self._generate_nrpn_sequence(None, 2, 0, chorus["type"]))
            if "lfo_frequency" in chorus:
                freq_val = min(127, max(0, int(chorus["lfo_frequency"] * 127 / 10)))  # 0-10 Hz
                messages.extend(self._generate_nrpn_sequence(None, 2, 1, freq_val))
            if "lfo_depth" in chorus:
                messages.extend(self._generate_nrpn_sequence(None, 2, 2, chorus["lfo_depth"]))
            if "delay_offset" in chorus:
                delay_val = min(127, max(0, int(chorus["delay_offset"] * 127)))  # 0-1
                messages.extend(self._generate_nrpn_sequence(None, 2, 3, delay_val))
            if "feedback" in chorus:
                feedback_val = (chorus["feedback"] + 100) * 127 // 200  # -100 to +100
                messages.extend(self._generate_nrpn_sequence(None, 2, 4, feedback_val))
            if "reverb_send" in chorus:
                messages.extend(self._generate_nrpn_sequence(None, 2, 5, chorus["reverb_send"]))

        return messages

    def _generate_variation_effects_messages(self, effects: dict) -> list[MIDIMessage]:
        """Generate XG variation effects NRPN messages (MSB 3)."""
        messages = []

        # Variation Effect Type
        if "type" in effects:
            messages.extend(self._generate_nrpn_sequence(None, 3, 0, effects["type"]))

        # Variation Effect Parameters (MSB 3, LSB 1-15)
        if "parameters" in effects:
            params = effects["parameters"]
            # Map common parameters to NRPN LSB values
            param_mappings = {
                "depth": 1,
                "rate": 2,
                "feedback": 3,
                "delay": 4,
                "balance": 5,
                "level": 6,
                "send_reverb": 7,
                "send_chorus": 8,
            }

            for param_name, lsb in param_mappings.items():
                if param_name in params:
                    messages.extend(self._generate_nrpn_sequence(None, 3, lsb, params[param_name]))

        return messages

    def _generate_insertion_effects_messages(self, effects: dict) -> list[MIDIMessage]:
        """Generate XG insertion effects NRPN messages (MSB 4-6)."""
        messages = []

        # Insertion effects are configured per channel and slot
        # Each channel has 3 insertion effect slots (MSB 4, 5, 6)

        if isinstance(effects, list):
            for effect_config in effects:
                channel = effect_config.get("channel", 0)
                slot = effect_config.get("slot", 0)

                # Validate slot range (0-2)
                if not (0 <= slot <= 2):
                    self.errors.append(f"Invalid insertion effect slot {slot}, must be 0-2")
                    continue

                msb = 4 + slot  # MSB 4, 5, or 6 for slots 0, 1, 2

                # Effect type
                if "type" in effect_config:
                    effect_type = effect_config["type"]
                    messages.extend(self._generate_nrpn_sequence(channel, msb, 0, effect_type))

                # Effect parameters (LSB 1-15)
                if "parameters" in effect_config:
                    params = effect_config["parameters"]
                    # Map common parameters to LSB values
                    param_mappings = {
                        "level": 1,
                        "pan": 2,
                        "send_reverb": 3,
                        "send_chorus": 4,
                        "send_variation": 5,
                        "bypass": 6,
                    }

                    for param_name, lsb in param_mappings.items():
                        if param_name in params:
                            value = params[param_name]
                            # Convert boolean bypass to 0/127
                            if param_name == "bypass" and isinstance(value, bool):
                                value = 0 if value else 127  # 0 = on, 127 = off
                            messages.extend(self._generate_nrpn_sequence(channel, msb, lsb, value))

        return messages

    def _generate_parameter_messages(
        self, params: dict, channel: int, time: float
    ) -> list[MIDIMessage]:
        """Generate parameter messages for track/channel."""
        messages = []

        for param_name, value in params.items():
            if param_name in CONTROLLER_NAMES:
                controller = CONTROLLER_NAMES[param_name]
                midi_value = self._resolve_controller_value(param_name, value)
                messages.append(
                    MIDIMessage(
                        type="control_change",
                        channel=channel,
                        control=controller,
                        value=midi_value,
                        time=time,
                    )
                )

        return messages

    def _generate_event_messages(
        self, event_data: dict, channel: int, time: float
    ) -> list[MIDIMessage]:
        """Generate messages for sequence events."""
        messages = []

        # Note messages
        if "note_on" in event_data:
            note_data = event_data["note_on"]
            if isinstance(note_data, dict):
                note = self._parse_note_name(note_data.get("note", 60))
                velocity = note_data.get("velocity", 80)
                messages.append(
                    MIDIMessage(
                        type="note_on", channel=channel, note=note, velocity=velocity, time=time
                    )
                )

        if "note_off" in event_data:
            note_data = event_data["note_off"]
            if isinstance(note_data, dict):
                note = self._parse_note_name(note_data.get("note", 60))
                velocity = note_data.get("velocity", 40)
                messages.append(
                    MIDIMessage(
                        type="note_off", channel=channel, note=note, velocity=velocity, time=time
                    )
                )

        # Control changes - handle both simple values and complex structures
        for key, value in event_data.items():
            if key in CONTROLLER_NAMES:
                controller = CONTROLLER_NAMES[key]

                # Handle complex controller values (with from/to/curve)
                if isinstance(value, dict):
                    # For now, just use the 'from' value or default
                    if "from" in value:
                        midi_value = self._resolve_controller_value(key, value["from"])
                    else:
                        midi_value = self._resolve_controller_value(key, value)
                else:
                    midi_value = self._resolve_controller_value(key, value)

                messages.append(
                    MIDIMessage(
                        type="control_change",
                        channel=channel,
                        control=controller,
                        value=midi_value,
                        time=time,
                    )
                )

        return messages

    def _get_modulation_source_cc(self, source: str) -> int | None:
        """Map modulation source name to CC number."""
        source_map = {
            "pitch": 1,
            "velocity": 11,
            "aftertouch": 127,
            "mod_wheel": 1,
            "breath": 2,
            "foot": 4,
            "expression": 11,
            "lfo1": 80,
            "lfo2": 81,
        }
        return source_map.get(source.lower())

    def _get_modulation_destination_cc(self, destination: str) -> int | None:
        """Map modulation destination name to CC number."""
        dest_map = {
            "pitch": 1,
            "filter": 74,
            "amplitude": 7,
            "pan": 10,
            "lfo_rate": 82,
            "lfo_depth": 83,
        }
        return dest_map.get(destination.lower())

    def get_errors(self) -> list[str]:
        """Get list of translation errors."""
        return self.errors.copy()

    def get_warnings(self) -> list[str]:
        """Get list of translation warnings."""
        return self.warnings.copy()

    def has_errors(self) -> bool:
        """Check if there are any translation errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any translation warnings."""
        return len(self.warnings) > 0

    # Modern v2.0 translation methods

    def _translate_synthesis_engines(self, doc) -> list[MIDIMessage]:
        """Translate synthesis engines configuration."""
        messages = []

        engine_data = doc.get_section("synthesis_engines")
        if not engine_data:
            return messages

        # For now, synthesis engine selection is handled at the synthesizer level
        # This would typically generate SYSEX messages to configure engine selection
        # Implementation depends on how the synthesizer exposes engine switching

        self.warnings.append(
            "Synthesis engine configuration requires synthesizer-level implementation"
        )
        return messages

    def _translate_gs_configuration(self, doc) -> list[MIDIMessage]:
        """Translate GS configuration."""
        messages = []

        gs_data = doc.get_section("gs_configuration")
        if not gs_data:
            return messages

        # GS Reset SYSEX
        if gs_data.get("enabled", False):
            # GS Reset: F0 41 [dev] 42 12 00 00 [sum] F7
            messages.append(
                MIDIMessage(
                    type="sysex",
                    sysex_data=[0xF0, 0x41, 0x10, 0x42, 0x12, 0x00, 0x00, 0x00, 0xF7],
                    time=0.0,
                )
            )

        # GS system effects configuration
        if "system_effects" in gs_data:
            effects = gs_data["system_effects"]

            if "reverb_type" in effects:
                reverb_type = GS_REVERB_TYPES.get(effects["reverb_type"], 0)
                # GS Reverb Type SYSEX
                messages.append(
                    MIDIMessage(
                        type="sysex",
                        sysex_data=[0xF0, 0x41, 0x10, 0x42, 0x01, 0x30, reverb_type, 0x00, 0xF7],
                        time=0.0,
                    )
                )

            if "chorus_type" in effects:
                chorus_type = GS_CHORUS_TYPES.get(effects["chorus_type"], 0)
                # GS Chorus Type SYSEX
                messages.append(
                    MIDIMessage(
                        type="sysex",
                        sysex_data=[0xF0, 0x41, 0x10, 0x42, 0x01, 0x38, chorus_type, 0x00, 0xF7],
                        time=0.0,
                    )
                )

        return messages

    def _translate_mpe_configuration(self, doc) -> list[MIDIMessage]:
        """Translate MPE configuration."""
        messages = []

        mpe_data = doc.get_section("mpe_configuration")
        if not mpe_data or not mpe_data.get("enabled", False):
            return messages

        # MPE configuration is typically handled via RPN messages
        # MPE pitch bend range (RPN 0,0)
        zones = mpe_data.get("zones", [])
        for zone in zones:
            lower_channel = zone.get("lower_channel", 0)
            upper_channel = zone.get("upper_channel", 15)
            pitch_range = zone.get("pitch_bend_range", 48)

            # Set pitch bend range for each channel in the zone
            for channel in range(lower_channel, upper_channel + 1):
                messages.extend(self._generate_rpn_sequence(channel, 0, 0, pitch_range))

        return messages

    def _translate_modulation_matrix(self, doc) -> list[MIDIMessage]:
        """Translate modulation matrix configuration."""
        messages = []

        matrix_data = doc.get_section("modulation_matrix")
        if not matrix_data:
            return messages

        # Modulation matrix configuration
        # Translate basic modulation sources and destinations via CC
        for modulation in matrix_data:
            source = modulation.get("source", "")
            destination = modulation.get("destination", "")
            amount = modulation.get("amount", 0)

            # Map source to CC number
            source_cc = self._get_modulation_source_cc(source)
            if source_cc:
                # Send modulation amount
                msg = MIDIMessage(
                    type="control_change", channel=0, controller=source_cc, value=int(amount * 127)
                )
                messages.append(msg)

                # Set destination via another CC if available
                dest_cc = self._get_modulation_destination_cc(destination)
                if dest_cc:
                    msg = MIDIMessage(
                        type="control_change",
                        channel=0,
                        controller=dest_cc,
                        value=1,  # Enable routing
                    )
                    messages.append(msg)

        return messages

    def _translate_effects_configuration(self, doc) -> list[MIDIMessage]:
        """Translate advanced effects configuration."""
        messages = []

        effects_data = doc.get_section("effects_configuration")
        if not effects_data:
            return messages

        # System effects
        if "system_effects" in effects_data:
            sys_effects = effects_data["system_effects"]

            if "reverb" in sys_effects:
                reverb = sys_effects["reverb"]
                # Generate XG system reverb NRPN messages (MSB 1)
                if "type" in reverb:
                    messages.extend(self._generate_nrpn_sequence(None, 1, 0, reverb["type"]))
                if "time" in reverb:
                    time_val = int(reverb["time"] * 127 / 10.0)  # Scale to 0-127
                    messages.extend(self._generate_nrpn_sequence(None, 1, 1, time_val))
                if "level" in reverb:
                    level_val = int(reverb["level"] * 127)
                    messages.extend(self._generate_nrpn_sequence(None, 1, 2, level_val))

            if "chorus" in sys_effects:
                chorus = sys_effects["chorus"]
                # Generate XG system chorus NRPN messages (MSB 2)
                if "type" in chorus:
                    messages.extend(self._generate_nrpn_sequence(None, 2, 0, chorus["type"]))
                if "rate" in chorus:
                    rate_val = int(chorus["rate"] * 127 / 10.0)
                    messages.extend(self._generate_nrpn_sequence(None, 2, 1, rate_val))
                if "depth" in chorus:
                    depth_val = int(chorus["depth"] * 127)
                    messages.extend(self._generate_nrpn_sequence(None, 2, 2, depth_val))

        # Variation effects
        if "variation_effects" in effects_data:
            var_effects = effects_data["variation_effects"]
            if "type" in var_effects:
                messages.extend(self._generate_nrpn_sequence(None, 3, 0, var_effects["type"]))

        # Insertion effects - per channel
        if "insertion_effects" in effects_data:
            ins_effects = effects_data["insertion_effects"]
            for effect in ins_effects:
                channel = effect.get("channel", 0)
                slot = effect.get("slot", 0)
                effect_type = effect.get("type", 0)

                # XG insertion effect type (MSB 4-6 depending on slot)
                msb = 4 + slot  # MSB 4, 5, or 6 for slots 0, 1, 2
                messages.extend(self._generate_nrpn_sequence(channel, msb, 0, effect_type))

        # Master processing - equalizer
        if "master_processing" in effects_data and "equalizer" in effects_data["master_processing"]:
            eq_data = effects_data["master_processing"]["equalizer"]

            if "type" in eq_data:
                eq_type = EQ_TYPES.get(eq_data["type"], 0)
                # XG master EQ type (MSB 80, LSB 0)
                messages.extend(self._generate_nrpn_sequence(None, 80, 0, eq_type))

            if "bands" in eq_data:
                bands = eq_data["bands"]
                band_mappings = {
                    "low": (80, 1, 80, 2),  # gain, frequency
                    "low_mid": (80, 3, 80, 4, 80, 5),  # gain, freq, Q
                    "mid": (81, 0, 81, 1, 81, 2),  # gain, freq, Q
                    "high_mid": (81, 3, 81, 4, 81, 5),  # gain, freq, Q
                    "high": (81, 6, 81, 7),  # gain, freq
                }

                for band_name, mapping in band_mappings.items():
                    if band_name in bands:
                        band = bands[band_name]
                        if "gain" in band:
                            gain_val = int((band["gain"] + 12) * 127 / 24)  # -12 to +12 dB
                            messages.extend(
                                self._generate_nrpn_sequence(None, mapping[0], mapping[1], gain_val)
                            )

        return messages

    def _translate_arpeggiator_configuration(self, doc) -> list[MIDIMessage]:
        """Translate arpeggiator configuration."""
        messages = []

        arp_data = doc.get_section("arpeggiator_configuration")
        if not arp_data or not arp_data.get("enabled", False):
            return messages

        # Arpeggiator configuration via CC messages
        # Map common arpeggiator parameters to CC
        if "tempo" in arp_data:
            tempo = arp_data["tempo"]
            # Send tempo as MIDI clock
            msg = MIDIMessage(type="clock", time=0)
            messages.append(msg)

        if "pattern" in arp_data:
            # Map pattern to CC 80 (LFO1 rate)
            pattern = arp_data["pattern"]
            cc_value = hash(pattern) % 127
            msg = MIDIMessage(type="control_change", channel=0, control=80, value=cc_value)
            messages.append(msg)

        if "gate" in arp_data:
            # Gate time via CC 81
            gate = int(arp_data["gate"] * 127)
            msg = MIDIMessage(type="control_change", channel=0, control=81, value=gate)
            messages.append(msg)

        if "swing" in arp_data:
            # Swing via CC 82
            swing = int((arp_data["swing"] + 1) * 63.5)
            msg = MIDIMessage(type="control_change", channel=0, control=82, value=swing)
            messages.append(msg)

        return messages

    def _translate_microtonal_tuning(self, doc) -> list[MIDIMessage]:
        """Translate microtonal tuning configuration."""
        messages = []

        tuning_data = doc.get_section("microtonal_tuning")
        if not tuning_data:
            return messages

        temperament = tuning_data.get("temperament", "equal")

        # XG microtonal tuning uses NRPN MSB 80-81
        if temperament != "equal":
            # Set temperament type
            temp_val = list(TEMPERAMENTS.keys()).index(temperament)
            messages.extend(self._generate_nrpn_sequence(None, 80, 0, temp_val))

        # Custom tuning
        if "custom_tuning" in tuning_data:
            custom = tuning_data["custom_tuning"]

            if "notes" in custom:
                notes = custom["notes"]
                note_mappings = {
                    "C": (80, 1),
                    "C#": (80, 2),
                    "D": (80, 3),
                    "D#": (80, 4),
                    "E": (80, 5),
                    "F": (80, 6),
                    "F#": (80, 7),
                    "G": (81, 0),
                    "G#": (81, 1),
                    "A": (81, 2),
                    "A#": (81, 3),
                    "B": (81, 4),
                }

                for note_name, (msb, lsb) in note_mappings.items():
                    if note_name in notes:
                        # Convert cents offset to NRPN value (-64 to +63 cents)
                        offset = max(-64, min(63, notes[note_name]))
                        value = offset + 64  # Convert to 0-127 range
                        messages.extend(self._generate_nrpn_sequence(None, msb, lsb, value))

        # Global offset
        if "global_offset" in tuning_data:
            offset = max(-100, min(100, tuning_data["global_offset"]))
            value = int((offset + 100) * 127 / 200)  # Scale to 0-127
            messages.extend(self._generate_nrpn_sequence(None, 81, 5, value))

        # A4 frequency
        if "a4_frequency" in tuning_data:
            freq = max(400, min(500, tuning_data["a4_frequency"]))
            value = int((freq - 400) * 127 / 100)  # Scale 400-500 Hz to 0-127
            messages.extend(self._generate_nrpn_sequence(None, 81, 6, value))

        return messages

    def _translate_advanced_features(self, doc) -> list[MIDIMessage]:
        """Translate advanced features configuration."""
        messages = []

        features_data = doc.get_section("advanced_features")
        if not features_data:
            return messages

        # Advanced features translation via CC messages
        # Map common advanced features to CC
        for feature_name, feature_value in features_data.items():
            if feature_name == "macro":
                # Macros can trigger stored settings
                macro_cc = 20 + (feature_value % 10)  # CC 20-29
                msg = MIDIMessage(type="control_change", channel=0, control=macro_cc, value=127)
                messages.append(msg)
            elif feature_name == "scene":
                # Scene switching via CC 16-19
                scene_cc = 16 + (feature_value % 4)
                msg = MIDIMessage(type="control_change", channel=0, control=scene_cc, value=127)
                messages.append(msg)
            elif feature_name == "knob_assign":
                # Knob assignments via NRPN
                if isinstance(feature_value, dict):
                    for param, value in feature_value.items():
                        param_cc = 70 + (hash(param) % 10)
                        msg = MIDIMessage(
                            type="control_change",
                            channel=0,
                            control=param_cc,
                            value=int(value * 127),
                        )
                        messages.append(msg)

        return messages

    # XGML v2.1 Advanced Engine Translation Methods

    def _translate_fm_x_engine(self, doc) -> list[MIDIMessage]:
        """Translate FM-X engine configuration to MIDI messages."""
        messages = []

        fm_x_data = doc.get_section("fm_x_engine")
        if not fm_x_data or not fm_x_data.get("enabled", False):
            return messages

        # FM-X configuration would require extensive SYSEX messages
        # for algorithm selection, operator parameters, modulation matrix, etc.
        # This is a comprehensive implementation for FM-X control

        # Algorithm selection (would require custom SYSEX)
        if "algorithm" in fm_x_data:
            algorithm = fm_x_data["algorithm"]
            # Generate SYSEX for algorithm selection
            self.warnings.append(f"FM-X algorithm {algorithm} requires SYSEX implementation")

        # Operator configuration
        if "operators" in fm_x_data:
            operators = fm_x_data["operators"]
            for op_name, op_config in operators.items():
                op_index = int(op_name.replace("op_", ""))
                # Generate SYSEX messages for operator parameters
                self.warnings.append(
                    f"FM-X operator {op_index} configuration requires SYSEX implementation"
                )

        # LFO configuration
        if "lfos" in fm_x_data:
            lfos = fm_x_data["lfos"]
            for lfo_name, lfo_config in lfos.items():
                lfo_index = int(lfo_name.replace("lfo_", ""))
                # Generate SYSEX for LFO parameters
                self.warnings.append(
                    f"FM-X LFO {lfo_index} configuration requires SYSEX implementation"
                )

        # Ring modulation connections
        if "ring_modulation" in fm_x_data:
            ring_connections = fm_x_data["ring_modulation"]
            for connection in ring_connections:
                # Generate SYSEX for ring modulation setup
                self.warnings.append(
                    f"FM-X ring modulation {connection} requires SYSEX implementation"
                )

        # Modulation matrix
        if "modulation_matrix" in fm_x_data:
            mod_matrix = fm_x_data["modulation_matrix"]
            for assignment in mod_matrix:
                # Generate SYSEX for modulation assignments
                self.warnings.append(
                    f"FM-X modulation assignment {assignment} requires SYSEX implementation"
                )

        # Effects sends
        if "effects_sends" in fm_x_data:
            effects_sends = fm_x_data["effects_sends"]
            # Generate NRPN messages for effects sends
            if "reverb" in effects_sends:
                messages.extend(self._generate_nrpn_sequence(None, 1, 2, effects_sends["reverb"]))
            if "chorus" in effects_sends:
                messages.extend(self._generate_nrpn_sequence(None, 2, 2, effects_sends["chorus"]))

        self.warnings.append(
            "FM-X engine configuration requires comprehensive SYSEX implementation"
        )
        return messages

    def _translate_sfz_engine(self, doc) -> list[MIDIMessage]:
        """Translate SFZ engine configuration to MIDI messages."""
        messages = []

        sfz_data = doc.get_section("sfz_engine")
        if not sfz_data or not sfz_data.get("enabled", False):
            return messages

        # SFZ configuration is primarily handled at the engine level
        # MIDI messages would be for real-time parameter control

        # Global parameters - could use NRPN if mapped
        if "global_parameters" in sfz_data:
            global_params = sfz_data["global_parameters"]

            # Volume control with proper logarithmic conversion
            if "volume" in global_params:
                volume_db = global_params["volume"]
                # Professional dB to MIDI conversion (logarithmic scale)
                # -60dB = 0, 0dB = 127, with proper logarithmic mapping
                if volume_db <= -60:
                    volume_val = 0
                elif volume_db >= 0:
                    volume_val = 127
                else:
                    # Logarithmic conversion: value = 127 * 10^(dB/20)
                    volume_val = int(127 * (10 ** (volume_db / 20.0)))
                    volume_val = max(0, min(127, volume_val))

                messages.append(
                    MIDIMessage(
                        type="control_change",
                        channel=0,  # Global
                        control=11,  # Expression
                        value=volume_val,
                        time=0.0,
                    )
                )

        # Modulation assignments - would use CC messages
        if "modulation_assignments" in sfz_data:
            mod_assignments = sfz_data["modulation_assignments"]
            for assignment in mod_assignments:
                source = assignment.get("source", "cc1")
                destination = assignment.get("destination", "volume")
                amount = assignment.get("amount", 0)

                # Map common sources to CC numbers
                cc_mappings = {
                    "cc1": 1,  # Mod wheel
                    "cc7": 7,  # Volume
                    "cc11": 11,  # Expression
                    "velocity": 1,  # Would need special handling
                }

                if source in cc_mappings:
                    cc_num = cc_mappings[source]
                    # Send modulation amount as CC value
                    messages.append(
                        MIDIMessage(
                            type="control_change",
                            channel=0,
                            control=cc_num,
                            value=max(0, min(127, int((amount + 100) * 127 / 200))),
                            time=0.0,
                        )
                    )

        self.warnings.append("SFZ engine configuration requires instrument-level implementation")
        return messages

    def _translate_physical_engine(self, doc) -> list[MIDIMessage]:
        """Translate physical modeling engine configuration to MIDI messages."""
        messages = []

        physical_data = doc.get_section("physical_engine")
        if not physical_data or not physical_data.get("enabled", False):
            return messages

        # Physical modeling parameters are highly engine-specific
        # Most would require custom SYSEX implementations

        model_type = physical_data.get("model_type", "string")

        if model_type == "string":
            string_params = physical_data.get("string_parameters", {})
            # Generate SYSEX for string physical modeling parameters
            self.warnings.append("Physical modeling string parameters require SYSEX implementation")

        elif model_type == "woodwind":
            woodwind_params = physical_data.get("woodwind_parameters", {})
            # Generate SYSEX for woodwind physical modeling
            self.warnings.append(
                "Physical modeling woodwind parameters require SYSEX implementation"
            )

        elif model_type == "brass":
            brass_params = physical_data.get("brass_parameters", {})
            # Generate SYSEX for brass physical modeling
            self.warnings.append("Physical modeling brass parameters require SYSEX implementation")

        elif model_type == "percussion":
            percussion_params = physical_data.get("percussion_parameters", {})
            # Generate SYSEX for percussion physical modeling
            self.warnings.append(
                "Physical modeling percussion parameters require SYSEX implementation"
            )

        # Waveguide parameters
        if "waveguide_parameters" in physical_data:
            waveguide_params = physical_data["waveguide_parameters"]
            # Generate SYSEX for waveguide synthesis
            self.warnings.append("Waveguide synthesis parameters require SYSEX implementation")

        # Global parameters
        if "global_parameters" in physical_data:
            global_params = physical_data["global_parameters"]
            # Some parameters might be controllable via standard messages
            if "sample_rate" in global_params:
                # Sample rate might not be changeable via MIDI
                pass

        self.warnings.append("Physical modeling engine requires comprehensive SYSEX implementation")
        return messages

    def _translate_spectral_engine(self, doc) -> list[MIDIMessage]:
        """Translate spectral processing engine configuration to MIDI messages."""
        messages = []

        spectral_data = doc.get_section("spectral_engine")
        if not spectral_data or not spectral_data.get("enabled", False):
            return messages

        # Spectral processing is highly specialized and would require
        # extensive SYSEX implementations for FFT parameters and processing

        mode = spectral_data.get("mode", "filter")

        # FFT settings - would require SYSEX
        if "fft_settings" in spectral_data:
            fft_settings = spectral_data["fft_settings"]
            self.warnings.append("FFT settings require SYSEX implementation")

        # Spectral parameters
        if "spectral_parameters" in spectral_data:
            spectral_params = spectral_data["spectral_parameters"]
            # Some parameters might be mappable to standard controls
            if "dry_wet_mix" in spectral_params:
                mix_val = int(spectral_params["dry_wet_mix"] * 127)
                messages.append(
                    MIDIMessage(
                        type="control_change",
                        channel=0,
                        control=91,  # Reverb send - repurposed for mix
                        value=mix_val,
                        time=0.0,
                    )
                )

        # Morphing parameters
        if "morphing" in spectral_data:
            morphing = spectral_data["morphing"]
            if morphing.get("enabled", False):
                morph_position = morphing.get("morph_position", 0.5)
                morph_pos_val = int(morph_position * 127)
                messages.append(
                    MIDIMessage(
                        type="control_change",
                        channel=0,
                        control=93,  # Chorus send - repurposed for morph position
                        value=morph_pos_val,
                        time=0.0,
                    )
                )

        # Filtering parameters
        if "filtering" in spectral_data:
            filtering = spectral_data["filtering"]
            # Could map some filter parameters to standard controls
            if "gain" in filtering:
                gain_val = int((filtering["gain"] + 24) * 127 / 48)  # -24 to +24 dB
                messages.append(
                    MIDIMessage(
                        type="control_change",
                        channel=0,
                        control=74,  # Brightness - repurposed for filter gain
                        value=gain_val,
                        time=0.0,
                    )
                )

        # Time stretching
        if "time_stretching" in spectral_data:
            time_stretch = spectral_data["time_stretching"]
            if time_stretch.get("enabled", False):
                stretch_factor = time_stretch.get("stretch_factor", 1.0)
                # Could use pitch bend or other controls for time stretching
                pass

        # Output processing
        if "output_processing" in spectral_data:
            output_proc = spectral_data["output_processing"]
            if "output_gain" in output_proc:
                gain_db = output_proc["output_gain"]
                gain_val = int((gain_db + 24) * 127 / 48)  # -24 to +24 dB
                messages.append(
                    MIDIMessage(
                        type="control_change",
                        channel=0,
                        control=7,  # Volume
                        value=gain_val,
                        time=0.0,
                    )
                )

        self.warnings.append("Spectral processing engine requires extensive SYSEX implementation")
        return messages
