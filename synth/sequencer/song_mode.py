"""
Song Mode - Advanced Sequencer Capabilities

Provides song mode functionality for multi-track sequencing and arrangement.
"""

from typing import Dict, List, Any, Optional
import threading


class SongMode:
    """
    Song mode sequencer for advanced multi-track composition.

    Provides song-level sequencing with multiple tracks, tempo changes,
    time signatures, and complex arrangements.
    """

    def __init__(self, max_tracks=64, ppq=960):
        """
        Initialize song mode sequencer.

        Args:
            max_tracks: Maximum number of tracks
            ppq: Pulses per quarter note
        """
        self.max_tracks = max_tracks
        self.ppq = ppq

        # Song structure
        self.tracks: Dict[int, Dict[str, Any]] = {}
        self.tempo_events: List[Dict[str, Any]] = []
        self.time_signature_events: List[Dict[str, Any]] = []
        self.marker_events: List[Dict[str, Any]] = []

        # Playback state
        self.current_position = 0  # In ticks
        self.is_playing = False
        self.loop_start = 0
        self.loop_end = 0
        self.loop_enabled = False

        # Song metadata
        self.song_name = "Untitled Song"
        self.song_length_ticks = 0
        self.tempo = 120.0
        self.time_signature = (4, 4)  # numerator, denominator

        # Threading
        self.lock = threading.RLock()

    def create_track(self, track_number: int, track_name: str = None) -> bool:
        """
        Create a new track.

        Args:
            track_number: Track number (0-based)
            track_name: Optional track name

        Returns:
            Success status
        """
        with self.lock:
            if track_number >= self.max_tracks:
                return False

            if track_number not in self.tracks:
                self.tracks[track_number] = {
                    'name': track_name or f'Track {track_number + 1}',
                    'events': [],
                    'muted': False,
                    'solo': False,
                    'volume': 100,
                    'pan': 64,  # 0-127, 64 = center
                    'midi_channel': track_number % 16,
                    'program': 0,
                    'bank': 0
                }
                return True
            return False

    def add_note_event(self, track_number: int, start_tick: int, duration_ticks: int,
                      note_number: int, velocity: int) -> bool:
        """
        Add a note event to a track.

        Args:
            track_number: Track number
            start_tick: Start position in ticks
            duration_ticks: Note duration in ticks
            note_number: MIDI note number (0-127)
            velocity: Note velocity (0-127)

        Returns:
            Success status
        """
        with self.lock:
            if track_number not in self.tracks:
                return False

            event = {
                'type': 'note_on',
                'tick': start_tick,
                'note': note_number,
                'velocity': velocity,
                'channel': self.tracks[track_number]['midi_channel']
            }

            # Add note on
            self.tracks[track_number]['events'].append(event)

            # Add note off
            note_off_event = {
                'type': 'note_off',
                'tick': start_tick + duration_ticks,
                'note': note_number,
                'velocity': 0,
                'channel': self.tracks[track_number]['midi_channel']
            }

            self.tracks[track_number]['events'].append(note_off_event)

            # Sort events by tick
            self.tracks[track_number]['events'].sort(key=lambda x: x['tick'])

            # Update song length
            self._update_song_length()

            return True

    def add_control_change(self, track_number: int, tick: int, controller: int, value: int) -> bool:
        """
        Add a control change event.

        Args:
            track_number: Track number
            tick: Position in ticks
            controller: Controller number (0-127)
            value: Controller value (0-127)

        Returns:
            Success status
        """
        with self.lock:
            if track_number not in self.tracks:
                return False

            event = {
                'type': 'control_change',
                'tick': tick,
                'controller': controller,
                'value': value,
                'channel': self.tracks[track_number]['midi_channel']
            }

            self.tracks[track_number]['events'].append(event)
            self.tracks[track_number]['events'].sort(key=lambda x: x['tick'])

            return True

    def add_tempo_change(self, tick: int, tempo: float) -> bool:
        """
        Add a tempo change event.

        Args:
            tick: Position in ticks
            tempo: New tempo in BPM

        Returns:
            Success status
        """
        with self.lock:
            event = {
                'tick': tick,
                'tempo': tempo
            }

            self.tempo_events.append(event)
            self.tempo_events.sort(key=lambda x: x['tick'])

            return True

    def add_time_signature_change(self, tick: int, numerator: int, denominator: int) -> bool:
        """
        Add a time signature change.

        Args:
            tick: Position in ticks
            numerator: Time signature numerator
            denominator: Time signature denominator

        Returns:
            Success status
        """
        with self.lock:
            event = {
                'tick': tick,
                'numerator': numerator,
                'denominator': denominator
            }

            self.time_signature_events.append(event)
            self.time_signature_events.sort(key=lambda x: x['tick'])

            return True

    def get_events_at_position(self, tick: int) -> List[Dict[str, Any]]:
        """
        Get all events at a specific tick position.

        Args:
            tick: Tick position

        Returns:
            List of events at that position
        """
        events = []

        with self.lock:
            # Check tempo events
            for tempo_event in self.tempo_events:
                if tempo_event['tick'] == tick:
                    events.append({
                        'type': 'tempo_change',
                        'tick': tick,
                        'tempo': tempo_event['tempo']
                    })

            # Check time signature events
            for ts_event in self.time_signature_events:
                if ts_event['tick'] == tick:
                    events.append({
                        'type': 'time_signature_change',
                        'tick': tick,
                        'numerator': ts_event['numerator'],
                        'denominator': ts_event['denominator']
                    })

            # Check track events
            for track_num, track_data in self.tracks.items():
                for event in track_data['events']:
                    if event['tick'] == tick and not track_data['muted']:
                        events.append(event.copy())

        return events

    def get_tempo_at_tick(self, tick: int) -> float:
        """
        Get tempo at a specific tick.

        Args:
            tick: Tick position

        Returns:
            Tempo in BPM
        """
        with self.lock:
            # Find the most recent tempo event before or at this tick
            current_tempo = self.tempo
            for tempo_event in self.tempo_events:
                if tempo_event['tick'] <= tick:
                    current_tempo = tempo_event['tempo']
                else:
                    break
            return current_tempo

    def get_time_signature_at_tick(self, tick: int) -> tuple:
        """
        Get time signature at a specific tick.

        Args:
            tick: Tick position

        Returns:
            Tuple of (numerator, denominator)
        """
        with self.lock:
            # Find the most recent time signature event before or at this tick
            current_ts = self.time_signature
            for ts_event in self.time_signature_events:
                if ts_event['tick'] <= tick:
                    current_ts = (ts_event['numerator'], ts_event['denominator'])
                else:
                    break
            return current_ts

    def _update_song_length(self):
        """Update the total song length based on events."""
        max_tick = 0

        with self.lock:
            # Check track events
            for track_data in self.tracks.values():
                if track_data['events']:
                    max_tick = max(max_tick, max(event['tick'] for event in track_data['events']))

            # Check tempo and time signature events
            if self.tempo_events:
                max_tick = max(max_tick, max(event['tick'] for event in self.tempo_events))
            if self.time_signature_events:
                max_tick = max(max_tick, max(event['tick'] for event in self.time_signature_events))

            self.song_length_ticks = max_tick

    def start_playback(self, start_tick: int = 0) -> bool:
        """
        Start playback from a specific position.

        Args:
            start_tick: Starting tick position

        Returns:
            Success status
        """
        with self.lock:
            self.current_position = start_tick
            self.is_playing = True
            return True

    def stop_playback(self) -> bool:
        """
        Stop playback.

        Returns:
            Success status
        """
        with self.lock:
            self.is_playing = False
            return True

    def get_playback_info(self) -> Dict[str, Any]:
        """
        Get current playback information.

        Returns:
            Dictionary with playback status
        """
        with self.lock:
            return {
                'is_playing': self.is_playing,
                'current_position': self.current_position,
                'song_length': self.song_length_ticks,
                'tempo': self.get_tempo_at_tick(self.current_position),
                'time_signature': self.get_time_signature_at_tick(self.current_position),
                'loop_enabled': self.loop_enabled,
                'loop_start': self.loop_start,
                'loop_end': self.loop_end,
                'active_tracks': len([t for t in self.tracks.values() if not t['muted']])
            }

    def clear_track(self, track_number: int) -> bool:
        """
        Clear all events from a track.

        Args:
            track_number: Track number to clear

        Returns:
            Success status
        """
        with self.lock:
            if track_number in self.tracks:
                self.tracks[track_number]['events'] = []
                self._update_song_length()
                return True
            return False

    def delete_track(self, track_number: int) -> bool:
        """
        Delete a track completely.

        Args:
            track_number: Track number to delete

        Returns:
            Success status
        """
        with self.lock:
            if track_number in self.tracks:
                del self.tracks[track_number]
                self._update_song_length()
                return True
            return False

    def get_track_info(self, track_number: int) -> Optional[Dict[str, Any]]:
        """
        Get information about a track.

        Args:
            track_number: Track number

        Returns:
            Track information or None if track doesn't exist
        """
        with self.lock:
            if track_number in self.tracks:
                track_info = self.tracks[track_number].copy()
                track_info['event_count'] = len(track_info['events'])
                return track_info
            return None

    def export_midi_file(self, filename: str) -> bool:
        """
        Export song as MIDI file.

        Args:
            filename: Output filename

        Returns:
            Success status
        """
        # TODO: Implement MIDI file export
        # This would require MIDI file format implementation
        return False

    def import_midi_file(self, filename: str) -> bool:
        """
        Import MIDI file into song.

        Args:
            filename: Input filename

        Returns:
            Success status
        """
        # TODO: Implement MIDI file import
        # This would require MIDI file parsing
        return False
