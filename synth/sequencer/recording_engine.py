"""
Recording Engine - Real-time MIDI and Audio Recording

Provides comprehensive recording capabilities for the XG sequencer,
including MIDI sequence recording, audio recording, and overdub features.
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import threading
import time


class RecordingEngine:
    """
    Real-time recording engine for MIDI and audio.

    Provides professional recording capabilities with punch-in/punch-out,
    overdubbing, and real-time monitoring for the XG workstation.
    """

    def __init__(self, sample_rate: int = 44100, max_tracks: int = 64):
        """
        Initialize recording engine.

        Args:
            sample_rate: Audio sample rate
            max_tracks: Maximum number of tracks
        """
        self.sample_rate = sample_rate
        self.max_tracks = max_tracks

        # Recording state
        self.is_recording = False
        self.is_playing = False
        self.current_position = 0
        self.recording_start_time = 0

        # Track management
        self.tracks: Dict[int, Dict[str, Any]] = {}
        self.active_record_tracks: set = set()

        # Recording parameters
        self.ppq = 960  # Pulses per quarter note
        self.tempo = 120.0
        self.time_signature = (4, 4)

        # Punch-in/punch-out
        self.punch_in_enabled = False
        self.punch_out_enabled = False
        self.punch_in_position = 0
        self.punch_out_position = 0

        # Overdub settings
        self.overdub_enabled = False
        self.replace_enabled = True

        # Monitoring
        self.input_monitoring = True
        self.record_monitoring = True

        # Audio recording buffers
        self.audio_buffers: Dict[int, List[np.ndarray]] = {}
        self.current_audio_buffer: Optional[np.ndarray] = None

        # Threading
        self.lock = threading.RLock()
        self.recording_thread: Optional[threading.Thread] = None

    def start_recording(self, track_number: int, record_type: str = 'midi',
                       start_position: int = 0) -> bool:
        """
        Start recording on a specific track.

        Args:
            track_number: Track to record on
            record_type: 'midi' or 'audio'
            start_position: Starting position in ticks

        Returns:
            Success status
        """
        with self.lock:
            if track_number >= self.max_tracks:
                return False

            if track_number not in self.tracks:
                self.tracks[track_number] = {
                    'type': record_type,
                    'events': [],
                    'audio_data': [],
                    'start_position': start_position,
                    'length': 0
                }

            self.active_record_tracks.add(track_number)
            self.is_recording = True
            self.recording_start_time = time.time()
            self.current_position = start_position

            # Initialize audio buffer if recording audio
            if record_type == 'audio':
                self.current_audio_buffer = np.zeros((self.sample_rate * 60, 2), dtype=np.float32)  # 60 seconds max
                self.audio_buffers[track_number] = []

            print(f"🎙️  Started recording on track {track_number} ({record_type})")
            return True

    def stop_recording(self) -> bool:
        """
        Stop recording on all tracks.

        Returns:
            Success status
        """
        with self.lock:
            if not self.is_recording:
                return False

            self.is_recording = False
            self.active_record_tracks.clear()

            # Process recorded data
            self._process_recorded_data()

            print("⏹️  Recording stopped")
            return True

    def record_midi_event(self, track_number: int, event_data: Dict[str, Any]) -> bool:
        """
        Record a MIDI event on a track.

        Args:
            event_data: MIDI event data

        Returns:
            Success status
        """
        with self.lock:
            if not self.is_recording or track_number not in self.active_record_tracks:
                return False

            if self.tracks[track_number]['type'] != 'midi':
                return False

            # Add timestamp
            event_with_time = event_data.copy()
            event_with_time['timestamp'] = time.time() - self.recording_start_time
            event_with_time['tick'] = self.current_position

            self.tracks[track_number]['events'].append(event_with_time)

            # Update track length
            self.tracks[track_number]['length'] = max(
                self.tracks[track_number]['length'],
                self.current_position
            )

            return True

    def record_audio_block(self, track_number: int, audio_block: np.ndarray,
                          block_position: int) -> bool:
        """
        Record an audio block on a track.

        Args:
            track_number: Track number
            audio_block: Audio data block
            block_position: Position in samples

        Returns:
            Success status
        """
        with self.lock:
            if not self.is_recording or track_number not in self.active_record_tracks:
                return False

            if self.tracks[track_number]['type'] != 'audio':
                return False

            # Store audio block
            if track_number not in self.audio_buffers:
                self.audio_buffers[track_number] = []

            self.audio_buffers[track_number].append((block_position, audio_block.copy()))

            # Update track length
            end_position = block_position + len(audio_block)
            self.tracks[track_number]['length'] = max(
                self.tracks[track_number]['length'],
                end_position
            )

            return True

    def _process_recorded_data(self):
        """Process and finalize recorded data."""
        for track_num in self.tracks:
            track = self.tracks[track_num]

            if track['type'] == 'midi':
                # Sort MIDI events by tick
                track['events'].sort(key=lambda x: x['tick'])

                # Quantize if enabled
                if hasattr(self, 'quantize_enabled') and self.quantize_enabled:
                    self._quantize_track(track_num)

            elif track['type'] == 'audio':
                # Concatenate audio blocks
                if track_num in self.audio_buffers:
                    self._concatenate_audio_blocks(track_num)

    def _quantize_track(self, track_number: int, grid_size: int = 480):  # 1/8 note
        """Quantize MIDI events on a track."""
        track = self.tracks[track_number]

        for event in track['events']:
            if 'tick' in event:
                quantized_tick = round(event['tick'] / grid_size) * grid_size
                event['tick'] = quantized_tick

        # Re-sort after quantization
        track['events'].sort(key=lambda x: x['tick'])

    def _concatenate_audio_blocks(self, track_number: int):
        """Concatenate recorded audio blocks into continuous audio."""
        if track_number not in self.audio_buffers:
            return

        blocks = self.audio_buffers[track_number]
        if not blocks:
            return

        # Sort blocks by position
        blocks.sort(key=lambda x: x[0])

        # Find total length
        max_end = 0
        for pos, block in blocks:
            max_end = max(max_end, pos + len(block))

        # Create output buffer
        output_buffer = np.zeros((max_end, 2), dtype=np.float32)

        # Mix blocks into output buffer
        for pos, block in blocks:
            end_pos = pos + len(block)
            if end_pos <= len(output_buffer):
                if self.replace_enabled:
                    output_buffer[pos:end_pos] = block
                else:
                    # Overdub (mix)
                    output_buffer[pos:end_pos] += block

        # Store in track
        self.tracks[track_number]['audio_data'] = output_buffer

        # Clean up
        del self.audio_buffers[track_number]

    def enable_punch_in_out(self, punch_in: int, punch_out: int) -> bool:
        """
        Enable punch-in/punch-out recording.

        Args:
            punch_in: Punch-in position in ticks
            punch_out: Punch-out position in ticks

        Returns:
            Success status
        """
        with self.lock:
            self.punch_in_enabled = True
            self.punch_out_enabled = True
            self.punch_in_position = punch_in
            self.punch_out_position = punch_out
            return True

    def disable_punch_in_out(self) -> bool:
        """
        Disable punch-in/punch-out recording.

        Returns:
            Success status
        """
        with self.lock:
            self.punch_in_enabled = False
            self.punch_out_enabled = False
            return True

    def set_overdub_mode(self, enabled: bool) -> bool:
        """
        Set overdub mode.

        Args:
            enabled: True for overdub, False for replace

        Returns:
            Success status
        """
        with self.lock:
            self.overdub_enabled = enabled
            self.replace_enabled = not enabled
            return True

    def get_recording_status(self) -> Dict[str, Any]:
        """
        Get current recording status.

        Returns:
            Recording status information
        """
        with self.lock:
            return {
                'is_recording': self.is_recording,
                'is_playing': self.is_playing,
                'active_tracks': list(self.active_record_tracks),
                'current_position': self.current_position,
                'punch_in_enabled': self.punch_in_enabled,
                'punch_out_enabled': self.punch_out_enabled,
                'punch_in_position': self.punch_in_position,
                'punch_out_position': self.punch_out_position,
                'overdub_enabled': self.overdub_enabled,
                'replace_enabled': self.replace_enabled,
                'tempo': self.tempo,
                'time_signature': self.time_signature
            }

    def get_track_data(self, track_number: int) -> Optional[Dict[str, Any]]:
        """
        Get recorded data for a track.

        Args:
            track_number: Track number

        Returns:
            Track data or None if track doesn't exist
        """
        with self.lock:
            return self.tracks.get(track_number)

    def clear_track(self, track_number: int) -> bool:
        """
        Clear all recorded data from a track.

        Args:
            track_number: Track number

        Returns:
            Success status
        """
        with self.lock:
            if track_number in self.tracks:
                self.tracks[track_number] = {
                    'type': self.tracks[track_number]['type'],
                    'events': [],
                    'audio_data': [],
                    'start_position': 0,
                    'length': 0
                }
                return True
            return False

    def export_track(self, track_number: int, filename: str, format_type: str = 'midi') -> bool:
        """
        Export track data to file.

        Args:
            track_number: Track to export
            filename: Output filename
            format_type: Export format ('midi' or 'wav')

        Returns:
            Success status
        """
        # TODO: Implement file export
        # This would require MIDI file writing and WAV file writing
        return False

    def import_track(self, track_number: int, filename: str) -> bool:
        """
        Import track data from file.

        Args:
            track_number: Track to import to
            filename: Input filename

        Returns:
            Success status
        """
        # TODO: Implement file import
        # This would require MIDI file parsing and WAV file reading
        return False

    def set_quantize_settings(self, enabled: bool, grid_size: int = 480) -> bool:
        """
        Set quantization settings.

        Args:
            enabled: Enable/disable quantization
            grid_size: Quantization grid size in ticks

        Returns:
            Success status
        """
        with self.lock:
            self.quantize_enabled = enabled
            self.quantize_grid = grid_size
            return True

    def get_recording_stats(self) -> Dict[str, Any]:
        """
        Get recording statistics.

        Returns:
            Recording statistics
        """
        with self.lock:
            total_events = sum(len(track.get('events', [])) for track in self.tracks.values())
            total_tracks = len(self.tracks)

            return {
                'total_tracks': total_tracks,
                'total_events': total_events,
                'recording_time': time.time() - self.recording_start_time if self.is_recording else 0,
                'average_events_per_track': total_events / max(1, total_tracks)
            }
