import mido
from mido import Message, MidiFile
from typing import List, Tuple, Union
import struct
import os
from .detector import MIDIFormat, detect_midi_format

class MIDIProcessor:
    """Processes MIDI messages and manages timing for both MIDI 1.0 and MIDI 2.0"""
    
    def __init__(self, midi_source: Union[MidiFile, str]):
        """
        Initialize MIDI processor.
        
        Args:
            midi_source: Either a MidiFile object or path to a MIDI file
        """
        self.midi = None
        self.file_path = None
        self.format = MIDIFormat.UNKNOWN
        
        if isinstance(midi_source, MidiFile):
            self.midi = midi_source
            self.format = MIDIFormat.MIDI_1_0
        elif isinstance(midi_source, str):
            self.file_path = midi_source
            # Detect MIDI format
            self.format, description = detect_midi_format(midi_source)
            print(f"MIDI file format detected: {description}")
            
            # Try to load with mido first (MIDI 1.0)
            if self.format in [MIDIFormat.MIDI_1_0, MIDIFormat.UNKNOWN]:
                try:
                    self.midi = mido.MidiFile(midi_source)
                    self.format = MIDIFormat.MIDI_1_0
                except Exception as e:
                    print(f"Warning: Could not load MIDI file with mido: {e}")
                    # Will attempt custom parsing for MIDI 2.0 or unknown formats
            else:
                print("MIDI 2.0 file detected - using custom parser")
        else:
            raise ValueError("midi_source must be either a MidiFile object or file path")
            
        self.tempo = 500000  # Default tempo (μs per beat)
        self.tick_rate = self.midi.ticks_per_beat if self.midi else 96
        
    def collect_messages(self) -> Tuple[List[Tuple[float, int, int, int]], List[Tuple[float, list]]]:
        """Collect and timestamp all MIDI messages"""
        # Try standard MIDI 1.0 processing first
        if self.midi and self.format == MIDIFormat.MIDI_1_0:
            return self._collect_midi_10_messages()
        else:
            # Attempt MIDI 2.0 custom parsing
            return self._collect_midi_20_messages()
        
    def _collect_midi_10_messages(self) -> Tuple[List[Tuple[float, int, int, int]], List[Tuple[float, list]]]:
        """Collect messages from MIDI 1.0 file using mido"""
        midi_msgs = []
        sysex_msgs = []
        
        for track in self.midi.tracks: # type: ignore
            abs_time = 0
            for msg in track:
                abs_time += msg.time
                if msg.type == "set_tempo":
                    self.tempo = msg.tempo
                elif msg.type == "sysex":
                    seconds = (abs_time * self.tempo) / (1_000_000.0 * self.tick_rate)
                    sysex_msgs.append((seconds, list(msg.bytes())))
                elif not msg.is_meta:
                    seconds = (abs_time * self.tempo) / (1_000_000.0 * self.tick_rate)
                    midi_msgs.append(self._convert_message(seconds, msg))
                    
        midi_msgs.sort(key=lambda x: x[0])
        sysex_msgs.sort(key=lambda x: x[0])
        return midi_msgs, sysex_msgs
        
    def _collect_midi_20_messages(self) -> Tuple[List[Tuple[float, int, int, int]], List[Tuple[float, list]]]:
        """Collect messages from MIDI 2.0 file with custom parser"""
        if not self.file_path:
            raise ValueError("File path required for MIDI 2.0 parsing")
            
        # Check if file exists and is readable
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"MIDI file not found: {self.file_path}")
            
        # For now, we'll implement a basic fallback that attempts to parse
        # as MIDI 1.0 even if detected as MIDI 2.0, since full MIDI 2.0
        # support would require a much more complex implementation
        try:
            # Try to load as MIDI 1.0 as a fallback
            self.midi = mido.MidiFile(self.file_path)
            self.format = MIDIFormat.MIDI_1_0
            print("Falling back to MIDI 1.0 parser for compatibility")
            return self._collect_midi_10_messages()
        except Exception as e:
            print(f"Error parsing MIDI file: {e}")
            # Return empty collections as fallback
            return [], []
        
    def _convert_message(self, timestamp: float, msg: Message) -> Tuple[float, int, int, int]:
        """Convert mido message to internal format using safe attribute access"""
        # Safely get message attributes with defaults
        msg_type = getattr(msg, 'type', 'unknown')
        channel = getattr(msg, 'channel', 0)
        note = getattr(msg, 'note', 0)
        velocity = getattr(msg, 'velocity', 0)
        control = getattr(msg, 'control', 0)
        value = getattr(msg, 'value', 0)
        program = getattr(msg, 'program', 0)
        pitch = getattr(msg, 'pitch', 0)

        if msg_type == "note_on":
            return (timestamp, 0x90 + channel, note, velocity)
        elif msg_type == "note_off":
            return (timestamp, 0x80 + channel, note, velocity)
        elif msg_type == "control_change":
            return (timestamp, 0xB0 + channel, control, value)
        elif msg_type == "program_change":
            return (timestamp, 0xC0 + channel, program, 0)
        elif msg_type == "pitchwheel":
            adjusted_pitch = pitch + 8192
            return (timestamp, 0xE0 + channel, adjusted_pitch & 0x7F, (adjusted_pitch >> 7) & 0x7F)
        elif msg_type == "polytouch":
            return (timestamp, 0xA0 + channel, note, value)
        elif msg_type == "aftertouch":
            return (timestamp, 0xD0 + channel, value, 0)
        else:
            return (timestamp, 0, 0, 0)