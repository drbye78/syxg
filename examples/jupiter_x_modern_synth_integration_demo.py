#!/usr/bin/env python3
"""
Jupiter-X Modern Synthesizer Integration Demo

This script demonstrates the complete integration of the Jupiter-X synthesizer
with the modern synthesizer framework, showcasing:

1. Jupiter-X engine registration with the synthesizer
2. Multi-engine synthesis (Jupiter-X + SF2 + FM + others)
3. XG/GS/MPE parameter control through Jupiter-X
4. Arpeggiator integration across engines
5. Effects processing with Jupiter-X enhancements
6. Real-time performance monitoring

Usage:
    python examples/jupiter_x_modern_synth_integration_demo.py
"""

import time

import numpy as np

# Import the integrated synthesizer
from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer

# Note: binary_parser was removed in refactoring, using new unified MIDI system
# from synth.midi import RealtimeParser


def create_demo_midi_sequence() -> list[bytes]:
    """Create a demo MIDI sequence showcasing Jupiter-X features."""
    midi_events = []

    # Time counter (in seconds)
    current_time = 0.0

    # Jupiter-X Part 0: Analog bass with arpeggiator
    # Enable arpeggiator on channel 0
    midi_events.append(
        create_midi_sysex(current_time, 0xF0, [0x43, 0x10, 0x4C, 0x08, 0x00, 0x00, 0xF7])
    )  # Part 0 receives channel 0

    # Note sequence for bass arpeggio
    bass_notes = [36, 39, 43, 46]  # C2, Eb2, G2, Bb2 (Cm7)
    for i, note in enumerate(bass_notes * 4):  # Repeat pattern 4 times
        # Note on
        midi_events.append(create_midi_message(current_time, 0x90, 0, note, 100))
        current_time += 0.25  # 16th notes

        # Note off
        midi_events.append(create_midi_message(current_time, 0x80, 0, note, 0))

    # Jupiter-X Part 1: Digital pad on channel 1
    current_time = 2.0  # Start at 2 seconds
    midi_events.append(
        create_midi_sysex(current_time, 0xF0, [0x43, 0x10, 0x4C, 0x08, 0x01, 0x01, 0xF7])
    )  # Part 1 receives channel 1

    # Pad chord progression
    pad_chords = [
        [60, 64, 67, 71],  # C major 7
        [62, 66, 69, 73],  # D minor 7
        [64, 68, 71, 74],  # Eb major 7
        [65, 69, 72, 76],  # F major 7
    ]

    for chord in pad_chords:
        for note in chord:
            midi_events.append(create_midi_message(current_time, 0x90, 1, note, 80))
        current_time += 1.0  # Hold each chord for 1 second

        for note in chord:
            midi_events.append(create_midi_message(current_time, 0x80, 1, note, 0))

    # Jupiter-X Part 2: FM lead on channel 2
    current_time = 6.0
    midi_events.append(
        create_midi_sysex(current_time, 0xF0, [0x43, 0x10, 0x4C, 0x08, 0x02, 0x02, 0xF7])
    )  # Part 2 receives channel 2

    # Lead melody
    lead_melody = [72, 74, 76, 77, 79, 81, 83, 84, 83, 81, 79, 77, 76, 74, 72]
    for note in lead_melody:
        midi_events.append(create_midi_message(current_time, 0x90, 2, note, 90))
        current_time += 0.15  # Fast melody

        midi_events.append(create_midi_message(current_time, 0x80, 2, note, 0))
        current_time += 0.05  # Short release

    # Jupiter-X Part 3: External/samples on channel 3
    current_time = 8.0
    midi_events.append(
        create_midi_sysex(current_time, 0xF0, [0x43, 0x10, 0x4C, 0x08, 0x03, 0x03, 0xF7])
    )  # Part 3 receives channel 3

    # Percussion hits
    percussion_notes = [36, 38, 42, 46, 36, 38]  # Kick, Snare, Hi-hat variations
    for note in percussion_notes:
        midi_events.append(
            create_midi_message(current_time, 0x99, 3, note, 120)
        )  # Note on channel 9 (percussion)
        current_time += 0.25
        midi_events.append(create_midi_message(current_time, 0x89, 3, note, 0))  # Note off

    return midi_events


def create_midi_message(time: float, status: int, channel: int, data1: int, data2: int) -> bytes:
    """Create a MIDI message with timestamp."""
    # For this demo, we'll store time in the message data
    # In a real implementation, you'd use a proper MIDI event structure
    return bytes([status | channel, data1, data2])


def create_midi_sysex(time: float, start_byte: int, data: list[int]) -> bytes:
    """Create a MIDI SysEx message."""
    return bytes([start_byte] + data)


def configure_jupiter_x_synth(synth: ModernXGSynthesizer):
    """Configure the Jupiter-X synthesizer with demo settings."""

    print("🎛️  Configuring Jupiter-X synthesizer...")

    # Enable Jupiter-X features
    if hasattr(synth, "jupiter_x_engine"):
        jupiter_x = synth.jupiter_x_engine

        # Configure Part 0: Analog Bass with Arpeggiator
        jupiter_x.set_engine_type(0, "analog")
        jupiter_x.set_jupiter_x_parameter(0, "analog", "osc1_waveform", 1)  # Sawtooth
        jupiter_x.set_jupiter_x_parameter(0, "analog", "filter_cutoff", 0.3)
        jupiter_x.enable_arpeggiator(0, True)
        jupiter_x.set_arpeggiator_pattern(0, 0)  # Up pattern

        # Configure Part 1: Digital Pad
        jupiter_x.set_engine_type(1, "digital")
        jupiter_x.set_jupiter_x_parameter(1, "digital", "morph_amount", 0.7)
        jupiter_x.set_jupiter_x_parameter(1, "digital", "filter_cutoff", 0.8)

        # Configure Part 2: FM Lead
        jupiter_x.set_engine_type(2, "fm")
        jupiter_x.set_jupiter_x_parameter(2, "fm", "algorithm", 5)
        jupiter_x.set_jupiter_x_parameter(2, "fm", "feedback", 0.3)

        # Configure Part 3: External Samples (Percussion)
        jupiter_x.set_engine_type(3, "external")
        # Load a sample (placeholder - would load actual WAV file)
        sample_data = np.random.uniform(-1, 1, 44100)  # 1 second noise
        jupiter_x.load_sample_for_engine(3, sample_data, 44100)

        print(
            "✅ Jupiter-X parts configured: Analog Bass, Digital Pad, FM Lead, External Percussion"
        )

    # Configure XG effects for Jupiter-X enhancement
    synth.set_xg_reverb_type(4)  # Hall reverb
    synth.set_xg_chorus_type(2)  # Chorus
    synth.set_xg_variation_type(8)  # Delay

    # Set drum kit for percussion channel
    synth.set_drum_kit(9, 0)  # Standard kit

    print("✅ XG effects configured for Jupiter-X enhancement")


def demonstrate_engine_switching(synth: ModernXGSynthesizer):
    """Demonstrate switching between different synthesis engines."""

    print("\n🔄 Demonstrating engine switching...")

    # Show available engines
    engines = synth.engine_registry.get_registered_engines()
    print(f"Available engines: {list(engines.keys())}")

    # Test Jupiter-X engine specifically
    jupiter_x_info = synth.jupiter_x_engine.get_engine_info()
    print(f"Jupiter-X engine: {jupiter_x_info['name']}")
    print(f"  - Parts: {jupiter_x_info['capabilities']['polyphony']}")
    print(f"  - Engines: {jupiter_x_info['capabilities']['engines']}")
    print(f"  - Effects: {jupiter_x_info['capabilities']['effects']}")
    print(f"  - Arpeggiator: {jupiter_x_info['capabilities']['arpeggiator']}")
    print(f"  - MPE: {jupiter_x_info['capabilities']['mpe']}")


def run_performance_test(synth: ModernXGSynthesizer):
    """Run a performance test with Jupiter-X synthesis."""

    print("\n⚡ Running Jupiter-X performance test...")

    # Start timing
    start_time = time.time()

    # Generate audio blocks while processing MIDI
    midi_sequence = create_demo_midi_sequence()
    synth.send_midi_message_block(midi_sequence)

    # Generate several seconds of audio
    total_samples = 44100 * 5  # 5 seconds
    block_size = 1024
    blocks = total_samples // block_size

    print(f"Generating {blocks} audio blocks ({total_samples} samples)...")

    for i in range(min(blocks, 100)):  # Limit for demo
        audio_block = synth.generate_audio_block(block_size)

        # Check for audio content
        if np.max(np.abs(audio_block)) > 0.01:
            print(f"  Block {i}: Audio detected (peak: {np.max(np.abs(audio_block)):.3f})")
        else:
            print(f"  Block {i}: Silent")

        if i % 20 == 0:
            print(f"  Progress: {i}/{min(blocks, 100)} blocks")

    end_time = time.time()
    duration = end_time - start_time

    # Get performance metrics
    metrics = synth.get_performance_metrics()

    print(f"  - Processing time: {duration:.2f} seconds")
    print(f"  - Audio blocks: {min(blocks, 100)}")
    print(f"  - CPU Usage: {metrics.get('cpu', {}).get('current', 'N/A')}%")
    print(f"  - Memory Usage: {metrics.get('memory', {}).get('current', 'N/A')} MB")
    print(f"  - Active Voices: {metrics.get('synthesis', {}).get('voices_current', 'N/A')}")

    return duration


def demonstrate_mpe_integration(synth: ModernXGSynthesizer):
    """Demonstrate MPE integration with Jupiter-X."""

    print("\n🎹 Demonstrating MPE integration...")

    # Enable MPE
    if hasattr(synth, "set_mpe_enabled"):
        synth.set_mpe_enabled(True)
        print("✅ MPE enabled")

    # Configure MPE zones (if available)
    mpe_info = synth.get_mpe_info()
    if mpe_info.get("enabled"):
        print(f"  - MPE Zones: {mpe_info.get('mpe_zones', 0)}")
        print(f"  - Active Notes: {mpe_info.get('mpe_active_notes', 0)}")
        print(f"  - Pitch Bend Range: {mpe_info.get('mpe_pitch_bend_range', 0)} semitones")
    else:
        print("  - MPE not available")

    # Demonstrate Jupiter-X MPE support
    if hasattr(synth, "jupiter_x_engine"):
        jupiter_x = synth.jupiter_x_engine
        jupiter_x.enable_mpe(True)
        print("✅ Jupiter-X MPE enabled")


def demonstrate_arpeggiator_integration(synth: ModernXGSynthesizer):
    """Demonstrate arpeggiator integration with Jupiter-X."""

    print("\n🎵 Demonstrating arpeggiator integration...")

    # Configure Jupiter-X arpeggiator
    if hasattr(synth, "jupiter_x_engine"):
        jupiter_x = synth.jupiter_x_engine

        # Enable arpeggiator on part 0
        jupiter_x.enable_arpeggiator(0, True)
        jupiter_x.set_arpeggiator_pattern(0, 0)  # Up pattern
        jupiter_x.set_arpeggiator_tempo(0, 120)

        print("✅ Jupiter-X arpeggiator configured: Part 0, Up pattern, 120 BPM")

        # Get arpeggiator status
        arpeggiator_status = jupiter_x.get_arpeggiator_status(0)
        print(f"  - Pattern: {arpeggiator_status.get('pattern', 'None')}")
        print(f"  - Enabled: {arpeggiator_status.get('enabled', False)}")


def demonstrate_effects_integration(synth: ModernXGSynthesizer):
    """Demonstrate effects integration with Jupiter-X enhancements."""

    print("\n🎛️  Demonstrating effects integration...")

    # Configure XG effects
    synth.set_xg_reverb_type(4)  # Hall reverb
    synth.set_xg_chorus_type(2)  # Chorus
    synth.set_xg_variation_type(8)  # Stereo delay

    print("✅ XG effects configured: Hall Reverb, Chorus, Stereo Delay")

    # Jupiter-X effects enhancements
    if hasattr(synth, "jupiter_x_engine"):
        jupiter_x = synth.jupiter_x_engine
        jupiter_x.enable_jupiter_x_effects()
        print("✅ Jupiter-X effects enhancements enabled")


def main():
    """Main demonstration function."""

    print("🎹 JUPITER-X MODERN SYNTHESIZER INTEGRATION DEMO")
    print("=" * 60)

    # Create the integrated synthesizer
    print("\n🏗️  Creating Modern XG Synthesizer with Jupiter-X integration...")
    synth = ModernXGSynthesizer(
        sample_rate=44100,
        max_channels=16,
        xg_enabled=True,
        gs_enabled=True,
        mpe_enabled=True,
        device_id=0x10,
    )

    # Configure Jupiter-X synthesizer
    configure_jupiter_x_synth(synth)

    # Demonstrate engine integration
    demonstrate_engine_switching(synth)

    # Demonstrate MPE integration
    demonstrate_mpe_integration(synth)

    # Demonstrate arpeggiator integration
    demonstrate_arpeggiator_integration(synth)

    # Demonstrate effects integration
    demonstrate_effects_integration(synth)

    # Run performance test
    performance_duration = run_performance_test(synth)

    # Get final synthesizer status
    synth_info = synth.get_synthesizer_info()
    print("\n📊 Final Synthesizer Status:")
    print(f"  - Sample Rate: {synth_info.get('sample_rate', 'N/A')} Hz")
    print(f"  - Active Channels: {synth_info.get('active_channels', 'N/A')}")
    print(f"  - Active Voices: {synth_info.get('total_active_voices', 'N/A')}")
    print(f"  - Available Engines: {len(synth_info.get('engines', {}))}")
    print(f"  - XG Compliance: {synth_info.get('xg_compliance', 'N/A')}")
    print(f"  - MPE Zones: {synth_info.get('mpe_zones', 'N/A')}")

    # Jupiter-X specific status
    if hasattr(synth, "jupiter_x_engine"):
        jx_status = synth.jupiter_x_engine.get_jupiter_x_status()
        print(
            f"  - Jupiter-X Parts: {jx_status.get('components', {}).get('component_manager', 'N/A')}"
        )

    # Clean up
    print("\n🧹 Cleaning up...")
    synth.cleanup()

    print(f"\n✅ Demo completed successfully in {performance_duration:.2f} seconds!")
    print(
        "\n🎹 Jupiter-X synthesizer is now fully integrated with the modern synthesizer framework!"
    )
    print("   - Multi-engine synthesis with Jupiter-X, SF2, FM, and more")
    print("   - XG/GS/MPE parameter control through Jupiter-X")
    print("   - Arpeggiator integration across all engines")
    print("   - Effects processing with Jupiter-X enhancements")
    print("   - Real-time performance monitoring and optimization")


if __name__ == "__main__":
    main()
