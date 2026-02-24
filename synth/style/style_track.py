"""
Style Track - Individual Track Data Structure

Represents a single track within a style (Rhythm, Bass, Chord, Pad, Phrase).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum

from .style import TrackType, NoteEvent, CCEvent, StyleTrackData


@dataclass
class StyleTrack:
    """
    A single style track with note data and parameters.

    Tracks are the main data carriers for style playback.
    Each track type has specific behavior:
    - Rhythm: Drum/percussion sounds (channel 9)
    - Bass: Follows chord root
    - Chord: Chordal accompaniment
    - Pad: Sustained pad
    - Phrase: Melodic phrases
    """

    track_type: TrackType = TrackType.RHYTHM_1
    name: str = ""
    data: StyleTrackData = field(default_factory=StyleTrackData)

    midi_channel: int = 0
    program_change: int = 0
    bank_msb: int = 0
    bank_lsb: int = 0

    mute: bool = False
    solo: bool = False
    volume: float = 1.0
    pan: int = 64
    reverb_send: int = 0
    chorus_send: int = 0
    variation_send: int = 0

    quantize: int = 480
    swing: float = 0.0
    groove: str = ""
    humanize: float = 0.0
    velocity_offset: int = 0
    velocity_curve: str = "linear"

    variations: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if not self.name:
            self.name = self.track_type.value

    @property
    def is_drum_track(self) -> bool:
        return self.track_type.is_drum

    @property
    def is_chordal_track(self) -> bool:
        return self.track_type.is_chordal

    @property
    def default_channel(self) -> int:
        if self.midi_channel > 0:
            return self.midi_channel
        return self.track_type.default_midi_channel

    def get_data_for_section(self, section_name: str) -> StyleTrackData:
        """Get track data for a specific section"""
        return self.data

    def set_notes(self, notes: List[NoteEvent]):
        """Set note events"""
        self.data.notes = notes

    def add_note(self, note: NoteEvent):
        """Add a note event"""
        self.data.notes.append(note)

    def set_cc_events(self, events: List[CCEvent]):
        """Set CC events"""
        self.data.cc_events = events

    def add_cc_event(self, event: CCEvent):
        """Add a CC event"""
        self.data.cc_events.append(event)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_type": self.track_type.value,
            "name": self.name,
            "midi_channel": self.midi_channel,
            "program_change": self.program_change,
            "bank_msb": self.bank_msb,
            "bank_lsb": self.bank_lsb,
            "mute": self.mute,
            "solo": self.solo,
            "volume": self.volume,
            "pan": self.pan,
            "reverb_send": self.reverb_send,
            "chorus_send": self.chorus_send,
            "variation_send": self.variation_send,
            "quantize": self.quantize,
            "swing": self.swing,
            "groove": self.groove,
            "humanize": self.humanize,
            "velocity_offset": self.velocity_offset,
            "velocity_curve": self.velocity_curve,
            "data": self.data.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StyleTrack":
        track_type = TrackType(data.get("track_type", "rhythm_1"))
        return cls(
            track_type=track_type,
            name=data.get("name", ""),
            midi_channel=data.get("midi_channel", 0),
            program_change=data.get("program_change", 0),
            bank_msb=data.get("bank_msb", 0),
            bank_lsb=data.get("bank_lsb", 0),
            mute=data.get("mute", False),
            solo=data.get("solo", False),
            volume=data.get("volume", 1.0),
            pan=data.get("pan", 64),
            reverb_send=data.get("reverb_send", 0),
            chorus_send=data.get("chorus_send", 0),
            variation_send=data.get("variation_send", 0),
            quantize=data.get("quantize", 480),
            swing=data.get("swing", 0.0),
            groove=data.get("groove", ""),
            humanize=data.get("humanize", 0.0),
            velocity_offset=data.get("velocity_offset", 0),
            velocity_curve=data.get("velocity_curve", "linear"),
            data=StyleTrackData.from_dict(data.get("data", {})),
        )


@dataclass
class TrackVariation:
    """A variation of a track with different note data"""

    variation_id: int = 0
    name: str = ""
    data: StyleTrackData = field(default_factory=StyleTrackData)
    probability: float = 1.0
    conditions: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variation_id": self.variation_id,
            "name": self.name,
            "data": self.data.to_dict(),
            "probability": self.probability,
            "conditions": self.conditions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrackVariation":
        return cls(
            variation_id=data.get("variation_id", 0),
            name=data.get("name", ""),
            data=StyleTrackData.from_dict(data.get("data", {})),
            probability=data.get("probability", 1.0),
            conditions=data.get("conditions", {}),
        )
