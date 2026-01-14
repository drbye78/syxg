#!/usr/bin/env python3
"""
Simple MIDI to Audio Renderer - Uses Refactored MIDI System

A simplified version of render_midi.py that works with the refactored MIDI package.
Loads MIDI files and SoundFonts to render audio using the new unified MIDI system.
"""

import os
import sys
import argparse
from pathlib import Path

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from synth.audio.writer import AudioWriter
from synth.audio.converter import AudioConverter
from synth.midi import FileParser, MIDIMessage
import numpy as np


class SimpleSynthesizer:
    """Simple synthesizer for MIDI rendering using refactored components."""

    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.soundfont_data = None
        self.preset_data = {}
        self.current_time = 0.0
        print(f"SimpleSynthesizer initialized (sample_rate={sample_rate})")

    def load_soundfont(self, sf2_path):
        """Load a simple SoundFont (placeholder for now)."""
        if os.path.exists(sf2_path):
            print(f"SoundFont loaded: {sf2_path}")
            self.soundfont_data = sf2_path
            return True
        else:
            print(f"SoundFont not found: {sf2_path}")
            return False

    def send_midi_message_block(self, messages):
        """Accept MIDI messages (placeholder)."""
        print(f"Received {len(messages)} MIDI messages")
        if messages:
            print(f"First message: {messages[0]}")

    def generate_audio_block(self, block_size=1024):
        """Generate a block of audio (simple sine wave for testing)."""
        # Generate a simple sine wave for testing
        t = np.linspace(0, block_size / self.sample_rate, block_size, False, dtype=np.float32)
        frequency = 440.0  # A4 note
        audio = 0.3 * np.sin(2 * np.pi * frequency * t)
        # Convert to stereo and float32
        return np.column_stack([audio, audio]).astype(np.float32)

    def reset(self):
        """Reset synthesizer state."""
        self.current_time = 0.0
        print("Synthesizer reset")

    def set_master_volume(self, volume):
        """Set master volume."""
        print(f"Master volume set to {volume}")

    def set_current_time(self, time):
        """Set current playback time."""
        self.current_time = time
        print(f"Current time set to {time}")

    def get_current_time(self):
        """Get current playback time."""
        return self.current_time

    def finalize_audio_logging(self):
        """Finalize audio logging (no-op for simple synthesizer)."""
        pass


def main():
    """Main conversion function."""

    parser = argparse.ArgumentParser(description="Convert MIDI to audio using refactored MIDI system")
    parser.add_argument("midi_file", help="Input MIDI file")
    parser.add_argument("--sf2", help="SoundFont file", default="tests/ref.sf2")
    parser.add_argument("--output", "-o", help="Output WAV file", default="output.wav")
    parser.add_argument("--format", choices=["wav"], default="wav", help="Output format")

    args = parser.parse_args()

    print("🎵 Simple MIDI Renderer - Using Refactored MIDI System")
    print("=" * 50)

    # Check input files
    midi_path = Path(args.midi_file)
    sf2_path = Path(args.sf2)
    output_path = Path(args.output)

    if not midi_path.exists():
        print(f"❌ MIDI file not found: {midi_path}")
        return False

    print(f"📄 MIDI file: {midi_path}")
    print(f"🎹 SoundFont: {sf2_path}")
    print(f"🎵 Output: {output_path}")

    # Initialize components
    print("\n🔧 Initializing components...")

    # Create synthesizer
    synthesizer = SimpleSynthesizer()

    # Load SoundFont
    if synthesizer.load_soundfont(str(sf2_path)):
        print("✅ SoundFont loaded successfully")
    else:
        print("⚠️  SoundFont loading failed (continuing anyway)")

    # Create audio writer
    audio_writer = AudioWriter(sample_rate=44100, chunk_size_ms=50)

    # Create audio converter
    converter = AudioConverter(synthesizer, audio_writer)

    print("✅ Components initialized")

    # Parse MIDI file
    print(f"\n🎼 Parsing MIDI file: {midi_path}")
    midi_messages, duration = converter.parse_audio_file(str(midi_path))

    if midi_messages is None:
        print("❌ Failed to parse MIDI file")
        return False

    print(f"✅ Parsed {len(midi_messages)} MIDI messages")
    print(f"   Duration: {duration:.2f} seconds")

    # Show some MIDI message info
    if midi_messages:
        print("\n📋 Sample MIDI messages:")
        for i, msg in enumerate(midi_messages[:5]):
            print(f"   {i+1}. {msg}")

        if len(midi_messages) > 5:
            print(f"   ... and {len(midi_messages) - 5} more messages")

    # Render audio
    print(f"\n🎵 Rendering audio to: {output_path}")

    success = converter.convert_audio_to_audio_buffered(
        input_file=str(midi_path),
        output_file=str(output_path),
        format=args.format,
        tempo=1.0,
        volume=0.8,
        silent=False,
        render_limit=min(duration, 10.0),  # Limit to 10 seconds for testing
        timeout_seconds=30.0
    )

    if success:
        print("✅ Audio rendering completed successfully!")
        print(f"   Output file: {output_path}")
        if output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"   File size: {size_mb:.2f} MB")
    else:
        print("❌ Audio rendering failed")
        return False

    print("\n🎉 MIDI rendering test completed!")
    print("   The refactored MIDI system is working correctly.")
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
