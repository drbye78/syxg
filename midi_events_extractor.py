#!/usr/bin/env python3
"""
MIDI Events Extractor
Takes a MIDI file and prints all MIDI events with their details and event time in seconds
to a text file. All events are merged into a single track and sorted by time.
"""

import sys
import argparse
import mido

def extract_midi_events(midi_file_path):
    """
    Extract all MIDI events from the file, merge into single track, sort by time.
    Returns list of (time_seconds, event_str) tuples.
    """
    midi = mido.MidiFile(midi_file_path)
    merged_track = mido.midifiles.merge_tracks(midi.tracks)

    current_time_ticks = 0
    current_tempo = 500000  # Default tempo: 120 BPM
    events = []

    for msg in merged_track:
        # Update tempo if this is a set_tempo message
        if msg.type == 'set_tempo':
            current_tempo = msg.tempo

        # Add delta time to cumulative ticks
        delta_ticks = msg.time
        current_time_ticks += delta_ticks

        # Convert to seconds: (ticks / ticks_per_beat) * (tempo / 1,000,000)
        seconds = (current_time_ticks / midi.ticks_per_beat) * (current_tempo / 1000000)
        event_str = str(msg)
        events.append((seconds, event_str))

    return events

def main():
    parser = argparse.ArgumentParser(description='Extract MIDI events to text file')
    parser.add_argument('midi_file', help='Input MIDI file path')
    parser.add_argument('output_file', help='Output text file path')
    args = parser.parse_args()

    try:
        events = extract_midi_events(args.midi_file)

        with open(args.output_file, 'w') as f:
            for time_sec, event_str in events:
                f.write(f"{time_sec} {event_str}\n")

        print(f"Extracted {len(events)} events to {args.output_file}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
