"""
Test script to create a simple MIDI file for testing the converter
"""

import mido
import os


def create_test_midi(filename):
    """Create a simple test MIDI file"""
    # Create a new MIDI file with one track
    midi = mido.MidiFile()
    track = mido.MidiTrack()
    midi.tracks.append(track)
    
    # Add some notes (C major scale)
    notes = [60, 62, 64, 65, 67, 69, 71, 72]  # C major scale
    
    # Set tempo (microseconds per beat)
    track.append(mido.MetaMessage('set_tempo', tempo=500000, time=0))
    
    # Add program change (piano)
    track.append(mido.Message('program_change', channel=0, program=0, time=0))
    
    # Add notes
    for note in notes:
        track.append(mido.Message('note_on', channel=0, note=note, velocity=64, time=0))
        track.append(mido.Message('note_off', channel=0, note=note, velocity=64, time=480))
    
    # Add a chord (C major)
    track.append(mido.Message('note_on', channel=0, note=60, velocity=64, time=0))
    track.append(mido.Message('note_on', channel=0, note=64, velocity=64, time=0))
    track.append(mido.Message('note_on', channel=0, note=67, velocity=64, time=0))
    track.append(mido.Message('note_off', channel=0, note=60, velocity=64, time=960))
    track.append(mido.Message('note_off', channel=0, note=64, velocity=64, time=0))
    track.append(mido.Message('note_off', channel=0, note=67, velocity=64, time=0))
    
    # Save the MIDI file
    midi.save(filename)
    print(f"Created test MIDI file: {filename}")


if __name__ == "__main__":
    # Create test MIDI file
    create_test_midi("test.mid")