#!/usr/bin/env python3
"""
Example usage of the enhanced Super Articulation 2 synthesizer.
"""

from synth.xg.sart import SuperArticulation2Synthesizer


def main():
    # Create a synthesizer instance
    synth = SuperArticulation2Synthesizer(instrument='violin')

    # Synthesize a sequence with various articulations
    notes = [
        {'freq': 440.0, 'duration': 1.0, 'articulation': 'tasto', 'velocity': 90},
        {'freq': 554.37, 'duration': 1.0, 'articulation': 'pizzicato_strict', 'velocity': 100},
        {'freq': 659.25, 'duration': 1.0, 'articulation': 'flageolet', 'velocity': 85},
        {'freq': 554.37, 'duration': 1.0, 'articulation': 'vibrato', 'velocity': 95},
        {'freq': 440.0, 'duration': 1.0, 'articulation': 'legato', 'velocity': 80},
    ]
    
    print("Generating audio sequence...")
    audio = synth.synthesize_note_sequence(notes)
    
    # Save to WAV file
    synth.save_to_wav(audio, 'enhanced_example.wav')
    print("Audio saved to 'enhanced_example.wav'")
    
    # Show available instruments and articulations
    print(f"\nAvailable instruments: {len(synth.get_available_instruments_list())}")
    print(f"Available articulations: {len(synth.get_available_articulations_list())}")
    
    # Demonstrate changing instruments
    synth.set_current_instrument('saxophone')
    sax_note = synth.synthesize_note(523.25, 1.0, 100, 'bend')
    synth.save_to_wav(sax_note, 'saxophone_bend.wav')
    print("Saxophone bend note saved to 'saxophone_bend.wav'")


if __name__ == "__main__":
    main()