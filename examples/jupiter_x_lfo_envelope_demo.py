#!/usr/bin/env python3
"""
Jupiter-X LFO & Envelope Enhancement Demo

This example demonstrates the advanced LFO and envelope features
implemented for the Jupiter-X synthesizer, including:

- Jupiter-X specific LFO waveforms
- Audio-rate LFO capability
- Per-engine LFO architecture
- Advanced envelope curves and velocity sensitivity
- Legato and triggering modes
- MIDI parameter control

Run with: python examples/jupiter_x_lfo_envelope_demo.py
"""

import numpy as np
import time
from synth.jupiter_x import JupiterXComponentManager, JupiterXMIDIController
from synth.core.oscillator import UltraFastXGLFO


def demo_jupiter_x_lfo_waveforms():
    """Demonstrate Jupiter-X LFO waveforms."""
    print("🎵 Jupiter-X LFO Waveforms Demo")
    print("-" * 40)

    # Create LFO instances for each Jupiter-X waveform
    waveforms = [
        ("sine", "Classic smooth modulation"),
        ("triangle", "Linear rise/fall modulation"),
        ("square", "Abrupt on/off modulation"),
        ("random_sh", "Jupiter-X Random Sample & Hold"),
        ("trapezoid", "Jupiter-X Trapezoid wave")
    ]

    lfos = []
    for waveform, description in waveforms:
        lfo = UltraFastXGLFO(id=len(lfos), waveform=waveform, rate=5.0, depth=0.8)
        lfos.append((lfo, waveform, description))

    # Generate and display waveform characteristics
    for lfo, name, desc in lfos:
        buffer = np.zeros(1024, dtype=np.float32)
        lfo.generate_block(buffer, 1024)

        # Analyze waveform
        mean_val = np.mean(buffer)
        std_val = np.std(buffer)
        min_val = np.min(buffer)
        max_val = np.max(buffer)

        print(f"{name:12}: {desc}")
        print(".3f"
              f"              Range: [{min_val:.2f}, {max_val:.2f}]")
        print()


def demo_audio_rate_lfo():
    """Demonstrate audio-rate LFO capability."""
    print("🎵 Audio-Rate LFO Demo")
    print("-" * 40)

    # Test different LFO frequencies
    frequencies = [1.0, 10.0, 50.0, 100.0, 150.0, 200.0]

    for freq in frequencies:
        lfo = UltraFastXGLFO(id=0, waveform="sine", rate=freq, depth=1.0)

        # Time generation of 1 second of audio at 44.1kHz
        num_samples = 44100
        buffer = np.zeros(num_samples, dtype=np.float32)

        start_time = time.time()
        lfo.generate_block(buffer, num_samples)
        end_time = time.time()

        processing_time = end_time - start_time
        latency_ms = processing_time * 1000

        print("6.1f"
              f"              Latency: {latency_ms:.2f}ms")
        print()


def demo_per_engine_lfo():
    """Demonstrate per-engine LFO architecture."""
    print("🎵 Per-Engine LFO Architecture Demo")
    print("-" * 40)

    # Create Jupiter-X synthesizer
    synth = JupiterXComponentManager(sample_rate=44100)

    # Configure multiple engines with different LFO settings
    engines_config = [
        (0, "Analog", "sine", 5.0, ["pitch"]),
        (2, "FM", "triangle", 12.0, ["amplitude", "pan"]),
        (1, "Digital", "random_sh", 8.0, ["filter"])
    ]

    for engine_type, engine_name, waveform, rate, destinations in engines_config:
        # Enable engine
        synth.set_engine_level(0, engine_type, 0.5)

        # Access engine LFO
        part = synth.get_part(0)
        engine = part.engines[engine_type]
        lfo = engine.lfo

        # Configure LFO
        lfo.set_parameters(waveform=waveform, rate=rate, depth=0.6)

        # Set modulation routing
        routing_kwargs = {dest: True for dest in destinations}
        lfo.set_modulation_routing(**routing_kwargs)

        # Configure Jupiter-X features
        lfo.set_phase_offset(engine_type * 45.0)  # Different phase for each engine
        lfo.set_fade_in_time(1.0)
        lfo.set_key_sync(True)

        print(f"{engine_name:8} Engine: {waveform} wave @ {rate}Hz")
        print(f"              Modulation: {', '.join(destinations)}")
        print(f"              Phase offset: {engine_type * 45}°")
        print()

    return synth


def demo_advanced_envelopes():
    """Demonstrate advanced envelope features."""
    print("🎵 Advanced Envelope Features Demo")
    print("-" * 40)

    # Create Jupiter-X synthesizer
    synth = JupiterXComponentManager()

    # Access analog engine envelope
    part = synth.get_part(0)
    engine = part.engines[0]  # Analog engine
    envelope = engine.amp_envelope

    # Configure envelope with advanced features
    envelope.set_parameters(attack=0.1, decay=0.3, sustain=0.7, release=0.5)

    # Set non-linear curves
    envelope.set_curves(attack_curve=1, decay_curve=0, release_curve=2)  # Convex, Linear, Concave

    # Enable velocity sensitivity
    envelope.set_velocity_sensitivity(
        attack_sens=0.5,    # 50% velocity influence on attack
        decay_sens=0.3,     # 30% on decay
        sustain_sens=0.8,   # 80% on sustain
        release_sens=0.2    # 20% on release
    )

    # Test different triggering modes
    print("Envelope Configuration:")
    print("- Attack: 0.1s (Convex curve, 50% velocity sensitivity)")
    print("- Decay: 0.3s (Linear curve, 30% velocity sensitivity)")
    print("- Sustain: 0.7 (80% velocity sensitivity)")
    print("- Release: 0.5s (Concave curve, 20% velocity sensitivity)")
    print()

    # Test legato mode
    envelope.legato_mode = True
    print("Legato mode enabled - envelopes won't retrigger on overlapping notes")
    print()

    return synth


def demo_midi_parameter_control():
    """Demonstrate MIDI parameter control for per-engine parameters."""
    print("🎵 MIDI Parameter Control Demo")
    print("-" * 40)

    # Create synthesizer and MIDI controller
    synth = JupiterXComponentManager()
    midi_ctrl = JupiterXMIDIController(synth)

    # Enable analog engine
    synth.set_engine_level(0, 0, 1.0)

    print("Per-Engine MIDI Parameter Mapping:")
    print("NRPN MSB = 0x30 + (part_number × 4) + engine_type")
    print("NRPN LSB = parameter_id")
    print()

    # Example parameter changes
    parameters = [
        (0x30, 0x00, "OSC1 Waveform", "Select oscillator waveform"),
        (0x30, 0x03, "OSC1 Level", "Set oscillator mix level"),
        (0x30, 0x21, "Filter Cutoff", "Adjust filter cutoff frequency"),
        (0x30, 0x30, "Amp Attack", "Set envelope attack time"),
        (0x30, 0x40, "LFO Waveform", "Select LFO waveform"),
        (0x30, 0x41, "LFO Rate", "Set LFO frequency"),
    ]

    for msb, lsb, param_name, description in parameters:
        # Create NRPN message
        nrpn_messages = midi_ctrl.create_nrpn_messages(msb, lsb, 8192)  # 50% value

        print(f"{param_name:15}: MSB=0x{msb:02X}, LSB=0x{lsb:02X}")
        print(f"{'':15}  {description}")
        print(f"{'':15}  NRPN sequence: {len(nrpn_messages)} messages")
        print()

    return synth, midi_ctrl


def demo_complete_workflow():
    """Demonstrate complete Jupiter-X workflow with all enhancements."""
    print("🎵 Complete Jupiter-X Workflow Demo")
    print("-" * 40)

    # Create synthesizer
    synth = JupiterXComponentManager(sample_rate=44100)

    # Configure multi-engine setup
    print("Setting up multi-engine configuration...")

    # Analog engine with vibrato LFO
    synth.set_engine_level(0, 0, 0.6)  # Analog at 60%
    analog = synth.parts[0].engines[0]
    analog.lfo.set_parameters(waveform="sine", rate=6.0, depth=0.25)
    analog.lfo.set_modulation_routing(pitch=True)
    analog.lfo.set_phase_offset(0.0)
    analog.amp_envelope.set_parameters(attack=0.05, decay=0.1, sustain=0.9, release=0.3)
    analog.amp_envelope.set_curves(attack_curve=1)  # Convex attack

    # FM engine with tremolo LFO
    synth.set_engine_level(0, 2, 0.4)  # FM at 40%
    fm = synth.parts[0].engines[2]
    fm.lfo.set_parameters(waveform="triangle", rate=10.0, depth=0.4)
    fm.lfo.set_modulation_routing(amplitude=True)
    fm.lfo.set_phase_offset(180.0)  # Opposite phase
    fm.amp_envelope.set_parameters(attack=0.08, decay=0.2, sustain=0.6, release=0.4)
    fm.amp_envelope.set_curves(attack_curve=2)  # Concave attack

    print("Configuration complete:")
    print("- Analog Engine: 60%, Sine LFO vibrato @ 6Hz, Convex attack envelope")
    print("- FM Engine: 40%, Triangle LFO tremolo @ 10Hz, Concave attack envelope")
    print()

    # Process MIDI sequence
    print("Processing MIDI sequence...")

    # Note on
    result = synth.process_midi_message(0, 'note_on', note=60, velocity=100)
    print(f"Note On (C4, vel=100): {'Success' if result else 'Failed'}")

    # Generate audio blocks
    total_samples = 0
    for i in range(10):  # Generate 10 blocks
        audio = synth.generate_audio_block(1024)
        total_samples += len(audio)

        # Check audio levels
        if i == 0:
            peak_level = np.max(np.abs(audio))
            print(".3f")

    # Note off
    synth.process_midi_message(0, 'note_off', note=60, velocity=0)
    print("Note Off: Processed")

    # Generate release tail
    for i in range(5):
        audio = synth.generate_audio_block(1024)
        total_samples += len(audio)

    print(f"Total audio generated: {total_samples} samples")
    print("Demo completed successfully!")
    print()


def main():
    """Run all Jupiter-X LFO and envelope demos."""
    print("🎹 Jupiter-X LFO & Envelope Enhancement Demos")
    print("=" * 60)
    print()

    try:
        # Run individual demos
        demo_jupiter_x_lfo_waveforms()
        demo_audio_rate_lfo()
        synth = demo_per_engine_lfo()
        demo_advanced_envelopes()
        demo_midi_parameter_control()
        demo_complete_workflow()

        print("🎹 All Jupiter-X enhancement demos completed successfully!")
        print()
        print("Key Features Demonstrated:")
        print("✓ Jupiter-X specific LFO waveforms (Random S&H, Trapezoid)")
        print("✓ Audio-rate LFO capability (up to 200Hz)")
        print("✓ Per-engine LFO architecture with independent modulation")
        print("✓ Advanced envelope curves (Linear, Convex, Concave)")
        print("✓ Velocity sensitivity per envelope stage")
        print("✓ Legato mode and advanced triggering")
        print("✓ MIDI parameter mapping for per-engine controls")
        print("✓ Performance optimizations for real-time operation")

    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
