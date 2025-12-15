"""
XGML to MIDI Translator

Converts XGML documents to MIDI message sequences that can be fed to the XG synthesizer.
"""

from typing import List, Dict, Any, Optional, Union, Tuple
import math
from collections import defaultdict

from .constants import (
    PROGRAM_NAMES, CONTROLLER_NAMES, PAN_POSITIONS,
    SYSTEM_EFFECT_TYPES, VARIATION_EFFECT_TYPES, INSERTION_EFFECT_TYPES,
    FILTER_TYPES, LFO_WAVEFORMS, CONTROLLER_ASSIGNMENTS
)
from ..midi.parser import MIDIMessage


class XGMLToMIDITranslator:
    """
    Translates XGML documents to MIDI message sequences.

    Converts high-level XGML parameters and sequences into MIDI messages
    that the XG synthesizer can understand.
    """

    def __init__(self):
        self.errors = []
        self.warnings = []

    def translate_document(self, xgml_document) -> List[MIDIMessage]:
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

        # Process time-bound sequences
        messages.extend(self._translate_sequences(xgml_document))

        # Sort messages by time
        messages.sort(key=lambda msg: msg.time if msg.time is not None else 0)

        return messages

    def _translate_basic_messages(self, doc) -> List[MIDIMessage]:
        """Translate basic MIDI messages section."""
        messages = []

        basic_data = doc.get_section('basic_messages')
        if not basic_data:
            return messages

        channels_data = basic_data.get('channels', {})

        for channel_name, channel_config in channels_data.items():
            try:
                channel_num = self._parse_channel_name(channel_name)

                # Program change
                if 'program_change' in channel_config:
                    program = self._resolve_program_name(channel_config['program_change'])
                    messages.append(MIDIMessage(
                        type='program_change',
                        channel=channel_num,
                        program=program,
                        time=0.0
                    ))

                # Bank select
                if 'bank_msb' in channel_config:
                    messages.append(MIDIMessage(
                        type='control_change',
                        channel=channel_num,
                        control=0,  # Bank MSB
                        value=channel_config['bank_msb'],
                        time=0.0
                    ))

                if 'bank_lsb' in channel_config:
                    messages.append(MIDIMessage(
                        type='control_change',
                        channel=channel_num,
                        control=32,  # Bank LSB
                        value=channel_config['bank_lsb'],
                        time=0.0
                    ))

                # Controllers
                for controller_name, value in channel_config.items():
                    if controller_name in ['program_change', 'bank_msb', 'bank_lsb']:
                        continue

                    controller_num = self._resolve_controller_name(controller_name)
                    if controller_num is not None:
                        midi_value = self._resolve_controller_value(controller_name, value)
                        messages.append(MIDIMessage(
                            type='control_change',
                            channel=channel_num,
                            control=controller_num,
                            value=midi_value,
                            time=0.0
                        ))

            except Exception as e:
                self.errors.append(f"Error processing channel {channel_name}: {e}")

        return messages

    def _translate_rpn_parameters(self, doc) -> List[MIDIMessage]:
        """Translate RPN parameters section."""
        messages = []

        rpn_data = doc.get_section('rpn_parameters')
        if not rpn_data:
            return messages

        # Global RPN parameters
        if 'global' in rpn_data:
            messages.extend(self._generate_rpn_messages(rpn_data['global'], None))

        # Channel-specific RPN parameters
        for channel_name, params in rpn_data.items():
            if channel_name == 'global':
                continue
            try:
                channel_num = self._parse_channel_name(channel_name)
                messages.extend(self._generate_rpn_messages(params, channel_num))
            except Exception as e:
                self.errors.append(f"Error processing RPN for {channel_name}: {e}")

        return messages

    def _translate_channel_parameters(self, doc) -> List[MIDIMessage]:
        """Translate XG channel parameters (NRPN MSB 3-31)."""
        messages = []

        channel_params = doc.get_section('channel_parameters')
        if not channel_params:
            return messages

        for channel_name, params in channel_params.items():
            try:
                channel_num = self._parse_channel_name(channel_name)
                messages.extend(self._generate_channel_nrpn_messages(params, channel_num))
            except Exception as e:
                self.errors.append(f"Error processing channel parameters for {channel_name}: {e}")

        return messages

    def _translate_drum_parameters(self, doc) -> List[MIDIMessage]:
        """Translate XG drum parameters (NRPN MSB 40-41)."""
        messages = []

        drum_data = doc.get_section('drum_parameters')
        if not drum_data:
            return messages

        drum_channel = drum_data.get('drum_channel', 9)  # MIDI channel 10

        if 'drum_notes' in drum_data:
            for note_name, note_params in drum_data['drum_notes'].items():
                try:
                    note_num = self._parse_note_name(note_name)
                    messages.extend(self._generate_drum_nrpn_messages(note_params, drum_channel, note_num))
                except Exception as e:
                    self.errors.append(f"Error processing drum note {note_name}: {e}")

        return messages

    def _translate_system_exclusive(self, doc) -> List[MIDIMessage]:
        """Translate system exclusive messages."""
        messages = []

        sysex_data = doc.get_section('system_exclusive')
        if not sysex_data:
            return messages

        commands = sysex_data.get('commands', [])
        for cmd in commands:
            try:
                messages.append(self._generate_sysex_message(cmd))
            except Exception as e:
                self.errors.append(f"Error processing SYSEX command: {e}")

        return messages

    def _translate_effects(self, doc) -> List[MIDIMessage]:
        """Translate effects configuration."""
        messages = []

        effects_data = doc.get_section('effects')
        if not effects_data:
            return messages

        # System effects
        if 'system_effects' in effects_data:
            messages.extend(self._generate_system_effects_messages(effects_data['system_effects']))

        # Variation effects
        if 'variation_effects' in effects_data:
            messages.extend(self._generate_variation_effects_messages(effects_data['variation_effects']))

        # Insertion effects
        if 'insertion_effects' in effects_data:
            messages.extend(self._generate_insertion_effects_messages(effects_data['insertion_effects']))

        return messages

    def _translate_sequences(self, doc) -> List[MIDIMessage]:
        """Translate time-bound sequences."""
        messages = []

        sequences_data = doc.get_section('sequences')
        if not sequences_data:
            return messages

        for sequence_name, sequence_data in sequences_data.items():
            try:
                tempo = sequence_data.get('tempo', 120)
                time_sig = sequence_data.get('time_signature', '4/4')
                quantization = sequence_data.get('quantization', '1/8')

                # Process tracks - handle both direct track list and nested structure
                tracks = sequence_data.get('tracks', [])
                for track_item in tracks:
                    # Handle nested structure: - track: {channel: 0, ...}
                    if 'track' in track_item:
                        track_data = track_item['track']
                    else:
                        # Direct structure (fallback)
                        track_data = track_item

                    messages.extend(self._process_track(track_data, tempo))

            except Exception as e:
                self.errors.append(f"Error processing sequence {sequence_name}: {e}")

        return messages

    def _process_track(self, track_data: Dict, tempo: float) -> List[MIDIMessage]:
        """Process a single track from sequence."""
        messages = []

        channel = track_data.get('channel', 0)
        default_params = track_data.get('parameters', {})
        events = track_data.get('events', [])

        # Apply default parameters at time 0
        messages.extend(self._generate_parameter_messages(default_params, channel, 0.0))

        # Process events
        for event in events:
            if 'at' in event:
                time_spec = event['at']
                event_time = self._parse_time(time_spec.get('time', 0), tempo)
                event_data = {k: v for k, v in time_spec.items() if k != 'time'}

                messages.extend(self._generate_event_messages(event_data, channel, event_time))

        return messages

    # Helper methods for parsing and conversion

    def _parse_channel_name(self, channel_name: str) -> int:
        """Parse channel name (e.g., 'channel_1', '1') to MIDI channel number."""
        if isinstance(channel_name, int):
            return channel_name
        if channel_name.startswith('channel_'):
            return int(channel_name.split('_')[1]) - 1  # Convert to 0-based
        return int(channel_name) - 1  # Assume 1-based input

    def _parse_note_name(self, note_name: Union[str, int]) -> int:
        """Parse note name to MIDI note number."""
        if isinstance(note_name, int):
            return note_name

        # Handle note names like "C4", "F#3", etc.
        note_name = str(note_name).upper()
        note_map = {'C': 0, 'C#': 1, 'DB': 1, 'D': 2, 'D#': 3, 'EB': 3,
                   'E': 4, 'F': 5, 'F#': 6, 'GB': 6, 'G': 7, 'G#': 8, 'AB': 8,
                   'A': 9, 'A#': 10, 'BB': 10, 'B': 11}

        if len(note_name) >= 2:
            note = note_name[:-1]
            octave = int(note_name[-1])
            return note_map.get(note, 0) + (octave + 1) * 12

        return int(note_name)  # Fallback

    def _resolve_program_name(self, program: Union[str, int]) -> int:
        """Resolve program name to MIDI program number."""
        if isinstance(program, int):
            return program
        return PROGRAM_NAMES.get(program, 0)

    def _resolve_controller_name(self, controller: str) -> Optional[int]:
        """Resolve controller name to MIDI controller number."""
        return CONTROLLER_NAMES.get(controller)

    def _resolve_controller_value(self, controller: str, value: Union[str, int, bool, Dict]) -> int:
        """Resolve controller value to MIDI value."""
        if isinstance(value, dict):
            # Handle complex values with 'from', 'to', etc.
            if 'from' in value:
                return self._resolve_controller_value(controller, value['from'])
            return 64  # Default

        if controller == 'pan':
            if isinstance(value, str):
                return PAN_POSITIONS.get(value, 64)
            return int(value)

        # Boolean controllers
        if isinstance(value, bool):
            return 127 if value else 0

        return int(value)

    def _parse_time(self, time_spec: Union[str, float], tempo: float) -> float:
        """Parse time specification to seconds."""
        if isinstance(time_spec, (int, float)):
            return float(time_spec)

        if isinstance(time_spec, str):
            # Handle musical time like "1:2:240"
            if ':' in time_spec:
                parts = time_spec.split(':')
                if len(parts) == 3:
                    measure = int(parts[0])
                    beat = int(parts[1])
                    tick = int(parts[2])
                    # Simplified: assume 4/4 time, 480 ticks per beat
                    beats_per_measure = 4
                    total_beats = (measure - 1) * beats_per_measure + (beat - 1) + tick / 480.0
                    seconds_per_beat = 60.0 / tempo
                    return total_beats * seconds_per_beat

        return 0.0

    # MIDI message generation methods

    def _generate_rpn_messages(self, params: Dict, channel: Optional[int]) -> List[MIDIMessage]:
        """Generate RPN messages for parameters."""
        messages = []

        rpn_mappings = {
            'pitch_bend_range': (0, 0),
            'fine_tuning': (0, 1),
            'coarse_tuning': (0, 2),
            'modulation_depth_range': (0, 5)
        }

        for param_name, value in params.items():
            if param_name in rpn_mappings:
                msb, lsb = rpn_mappings[param_name]
                messages.extend(self._generate_rpn_sequence(channel, msb, lsb, value))

        return messages

    def _generate_rpn_sequence(self, channel: Optional[int], msb: int, lsb: int, value: int) -> List[MIDIMessage]:
        """Generate RPN parameter change sequence."""
        messages = []

        # RPN LSB
        messages.append(MIDIMessage(
            type='control_change',
            channel=channel,
            control=100,  # RPN LSB
            value=lsb,
            time=0.0
        ))

        # RPN MSB
        messages.append(MIDIMessage(
            type='control_change',
            channel=channel,
            control=101,  # RPN MSB
            value=msb,
            time=0.0
        ))

        # Data Entry
        messages.append(MIDIMessage(
            type='control_change',
            channel=channel,
            control=6,  # Data Entry MSB
            value=value,
            time=0.0
        ))

        return messages

    def _generate_nrpn_sequence(self, channel: int, msb: int, lsb: int, value: int) -> List[MIDIMessage]:
        """Generate NRPN parameter change sequence."""
        messages = []

        # NRPN LSB
        messages.append(MIDIMessage(
            type='control_change',
            channel=channel,
            control=98,  # NRPN LSB
            value=lsb,
            time=0.0
        ))

        # NRPN MSB
        messages.append(MIDIMessage(
            type='control_change',
            channel=channel,
            control=99,  # NRPN MSB
            value=msb,
            time=0.0
        ))

        # Data Entry
        messages.append(MIDIMessage(
            type='control_change',
            channel=channel,
            control=6,  # Data Entry MSB
            value=value,
            time=0.0
        ))

        return messages

    def _generate_channel_nrpn_messages(self, params: Dict, channel: int) -> List[MIDIMessage]:
        """Generate NRPN messages for channel parameters (NRPN MSB 3-31)."""
        messages = []

        # MSB 3: Basic Channel Parameters
        if 'volume' in params:
            vol = params['volume']
            if isinstance(vol, dict):
                if 'coarse' in vol:
                    messages.extend(self._generate_nrpn_sequence(channel, 3, 0, vol['coarse']))
                if 'fine' in vol:
                    messages.extend(self._generate_nrpn_sequence(channel, 3, 1, vol['fine']))

        if 'pan' in params:
            pan = params['pan']
            if isinstance(pan, dict):
                if 'coarse' in pan:
                    pan_val = self._resolve_controller_value('pan', pan['coarse'])
                    messages.extend(self._generate_nrpn_sequence(channel, 3, 2, pan_val))
                if 'fine' in pan:
                    messages.extend(self._generate_nrpn_sequence(channel, 3, 3, pan['fine']))

        if 'expression' in params:
            expr = params['expression']
            if isinstance(expr, dict):
                if 'coarse' in expr:
                    messages.extend(self._generate_nrpn_sequence(channel, 3, 4, expr['coarse']))
                if 'fine' in expr:
                    messages.extend(self._generate_nrpn_sequence(channel, 3, 5, expr['fine']))

        if 'modulation_depth' in params:
            messages.extend(self._generate_nrpn_sequence(channel, 3, 6, params['modulation_depth']))

        if 'modulation_speed' in params:
            messages.extend(self._generate_nrpn_sequence(channel, 3, 7, params['modulation_speed']))

        # MSB 4: Pitch & Tuning Parameters
        if 'pitch_coarse' in params:
            messages.extend(self._generate_nrpn_sequence(channel, 4, 0, params['pitch_coarse'] + 64))  # -12 to +12 semitones, offset by 64

        if 'pitch_fine' in params:
            messages.extend(self._generate_nrpn_sequence(channel, 4, 1, params['pitch_fine'] + 64))  # -100 to +100 cents, offset by 64

        if 'pitch_bend_range' in params:
            messages.extend(self._generate_nrpn_sequence(channel, 4, 2, params['pitch_bend_range']))

        if 'portamento_mode' in params:
            mode_val = 1 if params['portamento_mode'] else 0
            messages.extend(self._generate_nrpn_sequence(channel, 4, 3, mode_val))

        if 'portamento_time' in params:
            messages.extend(self._generate_nrpn_sequence(channel, 4, 4, params['portamento_time']))

        if 'pitch_balance' in params:
            messages.extend(self._generate_nrpn_sequence(channel, 4, 5, params['pitch_balance']))

        # MSB 5-6: Filter Parameters
        if 'filter' in params:
            filter_params = params['filter']

            if 'cutoff' in filter_params:
                messages.extend(self._generate_nrpn_sequence(channel, 5, 0, filter_params['cutoff']))

            if 'resonance' in filter_params:
                messages.extend(self._generate_nrpn_sequence(channel, 6, 1, filter_params['resonance']))

            if 'type' in filter_params:
                filter_type = FILTER_TYPES.get(filter_params['type'], 0)
                messages.extend(self._generate_nrpn_sequence(channel, 6, 7, filter_type))

            if 'envelope' in filter_params:
                env = filter_params['envelope']
                if 'attack' in env:
                    messages.extend(self._generate_nrpn_sequence(channel, 5, 2, env['attack']))
                if 'decay' in env:
                    messages.extend(self._generate_nrpn_sequence(channel, 5, 3, env['decay']))
                if 'sustain' in env:
                    messages.extend(self._generate_nrpn_sequence(channel, 5, 4, env['sustain']))
                if 'release' in env:
                    messages.extend(self._generate_nrpn_sequence(channel, 5, 5, env['release']))

        # MSB 7-8: Amplifier Envelope
        if 'amplifier' in params and 'envelope' in params['amplifier']:
            amp_env = params['amplifier']['envelope']

            if 'attack' in amp_env:
                messages.extend(self._generate_nrpn_sequence(channel, 7, 0, amp_env['attack']))
            if 'decay' in amp_env:
                messages.extend(self._generate_nrpn_sequence(channel, 7, 1, amp_env['decay']))
            if 'sustain' in amp_env:
                messages.extend(self._generate_nrpn_sequence(channel, 7, 2, amp_env['sustain']))
            if 'release' in amp_env:
                messages.extend(self._generate_nrpn_sequence(channel, 7, 3, amp_env['release']))

            if 'velocity_sensitivity' in params['amplifier']:
                messages.extend(self._generate_nrpn_sequence(channel, 7, 4, params['amplifier']['velocity_sensitivity']))

            if 'key_scaling' in params['amplifier']:
                messages.extend(self._generate_nrpn_sequence(channel, 7, 5, params['amplifier']['key_scaling']))

        # MSB 9-10: LFO Parameters
        if 'lfo' in params:
            lfo_params = params['lfo']

            for lfo_num in [1, 2]:
                lfo_key = f'lfo{lfo_num}'
                if lfo_key in lfo_params:
                    lfo = lfo_params[lfo_key]
                    msb = 9 if lfo_num == 1 else 10

                    if 'waveform' in lfo:
                        waveform = LFO_WAVEFORMS.get(lfo['waveform'], 0)
                        messages.extend(self._generate_nrpn_sequence(channel, msb, 0, waveform))

                    if 'speed' in lfo:
                        messages.extend(self._generate_nrpn_sequence(channel, msb, 1, lfo['speed']))

                    if 'delay' in lfo:
                        messages.extend(self._generate_nrpn_sequence(channel, msb, 2, lfo['delay']))

                    if 'fade_time' in lfo:
                        messages.extend(self._generate_nrpn_sequence(channel, msb, 3, lfo['fade_time']))

                    if 'pitch_depth' in lfo:
                        messages.extend(self._generate_nrpn_sequence(channel, msb, 4, lfo['pitch_depth']))

                    if 'filter_depth' in lfo:
                        messages.extend(self._generate_nrpn_sequence(channel, msb, 5, lfo['filter_depth']))

                    if 'amp_depth' in lfo:
                        messages.extend(self._generate_nrpn_sequence(channel, msb, 6, lfo['amp_depth']))

        # MSB 11-12: Effects Send
        if 'effects_sends' in params:
            sends = params['effects_sends']

            if 'reverb' in sends:
                messages.extend(self._generate_nrpn_sequence(channel, 11, 0, sends['reverb']))

            if 'chorus' in sends:
                messages.extend(self._generate_nrpn_sequence(channel, 11, 1, sends['chorus']))

            if 'variation' in sends:
                messages.extend(self._generate_nrpn_sequence(channel, 11, 2, sends['variation']))

            if 'dry_level' in sends:
                messages.extend(self._generate_nrpn_sequence(channel, 11, 3, sends['dry_level']))

            if 'insertion' in sends:
                ins = sends['insertion']
                if 'part_l' in ins:
                    messages.extend(self._generate_nrpn_sequence(channel, 11, 4, ins['part_l']))
                if 'part_r' in ins:
                    messages.extend(self._generate_nrpn_sequence(channel, 11, 5, ins['part_r']))
                if 'connection' in ins:
                    conn_val = 1 if ins['connection'] == 'insertion' else 0
                    messages.extend(self._generate_nrpn_sequence(channel, 11, 6, conn_val))

        # MSB 13: Pitch Envelope
        if 'pitch_envelope' in params:
            pitch_env = params['pitch_envelope']

            mappings = {
                'attack': 0, 'decay': 1, 'sustain': 2, 'release': 3,
                'attack_level': 4, 'decay_level': 5, 'sustain_level': 6, 'release_level': 7
            }

            for param_name, lsb in mappings.items():
                if param_name in pitch_env:
                    messages.extend(self._generate_nrpn_sequence(channel, 13, lsb, pitch_env[param_name]))

        # MSB 14: Pitch LFO
        if 'pitch_lfo' in params:
            pitch_lfo = params['pitch_lfo']

            if 'waveform' in pitch_lfo:
                waveform = LFO_WAVEFORMS.get(pitch_lfo['waveform'], 0)
                messages.extend(self._generate_nrpn_sequence(channel, 14, 0, waveform))

            if 'speed' in pitch_lfo:
                messages.extend(self._generate_nrpn_sequence(channel, 14, 1, pitch_lfo['speed']))

            if 'delay' in pitch_lfo:
                messages.extend(self._generate_nrpn_sequence(channel, 14, 2, pitch_lfo['delay']))

            if 'fade_time' in pitch_lfo:
                messages.extend(self._generate_nrpn_sequence(channel, 14, 3, pitch_lfo['fade_time']))

            if 'pitch_depth' in pitch_lfo:
                messages.extend(self._generate_nrpn_sequence(channel, 14, 4, pitch_lfo['pitch_depth']))

        # MSB 15-16: Controller Assignments
        if 'controller_assignments' in params:
            assignments = params['controller_assignments']

            controller_map = {
                'mod_wheel': (15, 0),
                'foot_controller': (15, 1),
                'aftertouch': (15, 2),
                'breath_controller': (15, 3),
                'general1': (15, 4),
                'general2': (16, 0),
                'general3': (16, 1),
                'general4': (16, 2)
            }

            for ctrl_name, (msb, lsb) in controller_map.items():
                if ctrl_name in assignments:
                    assign_val = CONTROLLER_ASSIGNMENTS.get(assignments[ctrl_name], 0)
                    messages.extend(self._generate_nrpn_sequence(channel, msb, lsb, assign_val))

        # MSB 17-18: Scale Tuning
        if 'scale_tuning' in params:
            scale = params['scale_tuning']

            if 'notes' in scale:
                notes = scale['notes']
                note_mappings = {
                    'c': (17, 0), 'csharp': (17, 1), 'd': (17, 2), 'dsharp': (17, 3),
                    'e': (17, 4), 'f': (17, 5), 'fsharp': (17, 6), 'g': (18, 0),
                    'gsharp': (18, 1), 'a': (18, 2), 'asharp': (18, 3), 'b': (18, 4)
                }

                for note_name, (msb, lsb) in note_mappings.items():
                    if note_name in notes:
                        # Convert from -64/+63 cents to 0-127 range
                        value = notes[note_name] + 64
                        messages.extend(self._generate_nrpn_sequence(channel, msb, lsb, value))

            if 'octave_tune' in scale:
                # Convert from -64/+63 cents to 0-127 range
                value = scale['octave_tune'] + 64
                messages.extend(self._generate_nrpn_sequence(channel, 18, 5, value))

        # MSB 19: Velocity Response
        if 'velocity_response' in params:
            vel_resp = params['velocity_response']

            if 'curve' in vel_resp:
                messages.extend(self._generate_nrpn_sequence(channel, 19, 0, vel_resp['curve']))

            if 'offset' in vel_resp:
                messages.extend(self._generate_nrpn_sequence(channel, 19, 1, vel_resp['offset']))

            if 'range' in vel_resp:
                messages.extend(self._generate_nrpn_sequence(channel, 19, 2, vel_resp['range']))

        return messages

    def _generate_drum_nrpn_messages(self, params: Dict, channel: int, note: int) -> List[MIDIMessage]:
        """Generate NRPN messages for drum parameters."""
        messages = []

        # Implement mapping for MSB 40-41 drum parameters
        # This is a simplified implementation

        return messages

    def _generate_sysex_message(self, cmd: Dict) -> MIDIMessage:
        """Generate system exclusive message."""
        # Simplified SYSEX generation
        manufacturer = 0x43  # Yamaha
        data = [0xF0, manufacturer]  # Add full SYSEX data here

        return MIDIMessage(
            type='sysex',
            sysex_data=data,
            time=0.0
        )

    def _generate_system_effects_messages(self, effects: Dict) -> List[MIDIMessage]:
        """Generate system effects messages."""
        messages = []

        # Implement system effects NRPN generation (MSB 1-2)

        return messages

    def _generate_variation_effects_messages(self, effects: Dict) -> List[MIDIMessage]:
        """Generate variation effects messages."""
        messages = []

        # Implement variation effects NRPN generation (MSB 3)

        return messages

    def _generate_insertion_effects_messages(self, effects: Dict) -> List[MIDIMessage]:
        """Generate insertion effects messages."""
        messages = []

        # Implement insertion effects NRPN generation (MSB 4-6)

        return messages

    def _generate_parameter_messages(self, params: Dict, channel: int, time: float) -> List[MIDIMessage]:
        """Generate parameter messages for track/channel."""
        messages = []

        for param_name, value in params.items():
            if param_name in CONTROLLER_NAMES:
                controller = CONTROLLER_NAMES[param_name]
                midi_value = self._resolve_controller_value(param_name, value)
                messages.append(MIDIMessage(
                    type='control_change',
                    channel=channel,
                    control=controller,
                    value=midi_value,
                    time=time
                ))

        return messages

    def _generate_event_messages(self, event_data: Dict, channel: int, time: float) -> List[MIDIMessage]:
        """Generate messages for sequence events."""
        messages = []

        # Note messages
        if 'note_on' in event_data:
            note_data = event_data['note_on']
            if isinstance(note_data, dict):
                note = self._parse_note_name(note_data.get('note', 60))
                velocity = note_data.get('velocity', 80)
                messages.append(MIDIMessage(
                    type='note_on',
                    channel=channel,
                    note=note,
                    velocity=velocity,
                    time=time
                ))

        if 'note_off' in event_data:
            note_data = event_data['note_off']
            if isinstance(note_data, dict):
                note = self._parse_note_name(note_data.get('note', 60))
                velocity = note_data.get('velocity', 40)
                messages.append(MIDIMessage(
                    type='note_off',
                    channel=channel,
                    note=note,
                    velocity=velocity,
                    time=time
                ))

        # Control changes - handle both simple values and complex structures
        for key, value in event_data.items():
            if key in CONTROLLER_NAMES:
                controller = CONTROLLER_NAMES[key]

                # Handle complex controller values (with from/to/curve)
                if isinstance(value, dict):
                    # For now, just use the 'from' value or default
                    if 'from' in value:
                        midi_value = self._resolve_controller_value(key, value['from'])
                    else:
                        midi_value = self._resolve_controller_value(key, value)
                else:
                    midi_value = self._resolve_controller_value(key, value)

                messages.append(MIDIMessage(
                    type='control_change',
                    channel=channel,
                    control=controller,
                    value=midi_value,
                    time=time
                ))

        return messages

    def get_errors(self) -> List[str]:
        """Get list of translation errors."""
        return self.errors.copy()

    def get_warnings(self) -> List[str]:
        """Get list of translation warnings."""
        return self.warnings.copy()

    def has_errors(self) -> bool:
        """Check if there are any translation errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are any translation warnings."""
        return len(self.warnings) > 0
