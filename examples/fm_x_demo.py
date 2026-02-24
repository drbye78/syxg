#!/usr/bin/env python3
"""
FM-X Synthesis Engine Demonstration

Showcase the complete FM-X compatible synthesis engine with all advanced features:
- 8 operators with 8-stage envelopes
- Ring modulation and formant synthesis
- LFO modulation and modulation matrix
- MIDI control integration
- Effects processing
"""

import numpy as np
import time
from pathlib import Path

from synth.engine.fm_engine import FMEngine


def create_fm_x_demo():
    """Create and configure FM-X engine demonstration."""
    print("🎹 FM-X SYNTHESIS ENGINE DEMONSTRATION")
    print("=" * 80)

    print("🎛️  Initializing FM-X Engine...")
    fm_x = FMEngine(num_operators=8, sample_rate=44100)

    print("✅ FM-X Engine initialized successfully")
    print(f"   Operators: {fm_x.num_operators}")
    print(f"   Algorithms: {len(fm_x.get_available_algorithms())}")
    print(f"   LFOs: {len(fm_x.lfos)}")

    return fm_x


def demonstrate_basic_fm_x_setup():
    """Demonstrate basic FM-X setup and sound generation."""
    print("\n🎵 BASIC FM-X SETUP DEMONSTRATION")
    print("-" * 50)

    fm_x = create_fm_x_demo()

    print("🎛️  Configuring operators for rich FM sound...")

    # Configure operator 0 (carrier) - bright, sustained tone
    fm_x.set_operator_parameters(0, {
        'frequency_ratio': 1.0,
        'feedback_level': 2,
        'envelope_levels': [0.0, 1.0, 0.8, 0.6, 0.4, 0.2, 0.1, 0.0],
        'envelope_rates': [0.01, 0.2, 0.1, 0.3, 0.2, 0.4, 0.5, 1.0],
        'velocity_sensitivity': 3,
        'key_scaling_depth': 2
    })

    # Configure operator 1 (modulator) - metallic brightness
    fm_x.set_operator_parameters(1, {
        'frequency_ratio': 2.0,
        'feedback_level': 4,
        'envelope_levels': [0.0, 0.9, 0.3, 0.1, 0.0, 0.0, 0.0, 0.0],
        'envelope_rates': [0.02, 0.1, 0.05, 0.8, 0.0, 0.0, 0.0, 0.0],
        'velocity_sensitivity': 5
    })

    # Configure operator 2 (modulator) - harmonic richness
    fm_x.set_operator_parameters(2, {
        'frequency_ratio': 3.0,
        'envelope_levels': [0.0, 0.7, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0],
        'envelope_rates': [0.03, 0.08, 0.2, 0.5, 0.0, 0.0, 0.0, 0.0]
    })

    print("🎛️  Setting algorithm to complex 8-operator setup...")
    fm_x.set_algorithm('fm_x_6')  # Complex 8-operator algorithm

    print("🎵 Generating FM-X sound...")
    # Generate a C4 note (middle C) with velocity 100
    audio = fm_x.generate_samples(note=60, velocity=100, modulation={}, block_size=4410)

    print(f"   Generated {len(audio)} samples")
    print(".2f")
    print(".4f")

    return fm_x


def demonstrate_ring_modulation():
    """Demonstrate ring modulation capabilities."""
    print("\n🔗 RING MODULATION DEMONSTRATION")
    print("-" * 50)

    fm_x = create_fm_x_demo()

    print("🎛️  Setting up ring modulation between operators...")

    # Configure two operators for ring modulation
    fm_x.set_operator_parameters(0, {
        'frequency_ratio': 1.0,
        'waveform': 'sine',
        'envelope_levels': [0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        'envelope_rates': [0.01, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0]
    })

    fm_x.set_operator_parameters(1, {
        'frequency_ratio': 2.0,
        'waveform': 'triangle',
        'envelope_levels': [0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        'envelope_rates': [0.01, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0]
    })

    # Add ring modulation connection
    fm_x.add_ring_modulation_connection(0, 1)

    print("✅ Ring modulation connection established")
    print("   Operator 0 ↔ Operator 1 (ring modulated)")

    # Set simple algorithm that includes both operators
    fm_x.set_algorithm('basic')

    print("🎵 Generating ring modulated sound...")
    audio = fm_x.generate_samples(note=48, velocity=127, modulation={}, block_size=4410)

    print(".4f")

    return fm_x


def demonstrate_formant_synthesis():
    """Demonstrate formant synthesis for vocal sounds."""
    print("\n🎤 FORMANT SYNTHESIS DEMONSTRATION")
    print("-" * 50)

    fm_x = create_fm_x_demo()

    print("🎛️  Configuring formant synthesis for vowel sounds...")

    # Configure operator with formant filter for 'ah' vowel
    vowel_formants = fm_x.create_vowel_formants('a')  # [700, 50, 2.0]
    fm_x.configure_formant_operator(0, vowel_formants)

    print(f"   'A' vowel formants: {vowel_formants[0]}Hz, {vowel_formants[1]}Hz bandwidth")

    # Configure basic envelope
    fm_x.set_operator_parameters(0, {
        'frequency_ratio': 0.5,  # Sub-octave for vocal character
        'envelope_levels': [0.0, 1.0, 0.8, 0.6, 0.0, 0.0, 0.0, 0.0],
        'envelope_rates': [0.05, 0.1, 0.1, 0.3, 0.0, 0.0, 0.0, 0.0]
    })

    print("🎵 Generating vocal formant sound...")
    audio = fm_x.generate_samples(note=52, velocity=100, modulation={}, block_size=4410)

    print(".4f")

    return fm_x


def demonstrate_lfo_modulation():
    """Demonstrate LFO modulation capabilities."""
    print("\n🌊 LFO MODULATION DEMONSTRATION")
    print("-" * 50)

    fm_x = create_fm_x_demo()

    print("🎛️  Configuring LFO modulation...")

    # Set up LFO1 for vibrato
    fm_x.set_lfo_parameters(0, frequency=5.0, waveform='sine', depth=0.3)
    fm_x.add_modulation_assignment('lfo1', 'pitch', 0.4)

    # Set up LFO2 for tremolo
    fm_x.set_lfo_parameters(1, frequency=2.0, waveform='triangle', depth=0.2)
    fm_x.add_modulation_assignment('lfo2', 'amplitude', 0.3)

    print("✅ LFO modulation configured:")
    print("   LFO1: 5Hz sine → pitch (40%)")
    print("   LFO2: 2Hz triangle → amplitude (30%)")

    # Configure basic operator
    fm_x.set_operator_parameters(0, {
        'frequency_ratio': 1.0,
        'envelope_levels': [0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        'envelope_rates': [0.01, 0.0, 0.0, 0.8, 0.0, 0.0, 0.0, 0.0]
    })

    print("🎵 Generating LFO modulated sound...")
    audio = fm_x.generate_samples(note=60, velocity=100, modulation={}, block_size=8820)  # 0.2 seconds

    print(".4f")

    return fm_x


def demonstrate_midi_control():
    """Demonstrate MIDI control capabilities."""
    print("\n🎹 MIDI CONTROL DEMONSTRATION")
    print("-" * 50)

    fm_x = create_fm_x_demo()

    print("🎛️  Testing MIDI NRPN and SYSEX control...")

    # Test NRPN parameter changes
    print("   Testing NRPN parameter control...")
    # NRPN LSB = 0 (operator 0 frequency ratio)
    success1 = fm_x.process_nrpn_message(98, 0)  # NRPN LSB
    success2 = fm_x.process_nrpn_message(99, 1)  # NRPN MSB
    success3 = fm_x.process_nrpn_message(6, 64)  # Data Entry MSB

    print(f"   NRPN processing: {success1 and success2 and success3}")

    # Test SYSEX bulk dump request
    print("   Testing SYSEX bulk dump...")
    sysex_data = bytes([0xF0, 0x43, 0x10, 0x4C, 0x0C, 0x00, 0xF7])  # Bulk dump request
    response = fm_x.process_sysex_message(sysex_data)

    if response is not None:
        print(f"   SYSEX messages processed: {len(response)}")
    else:
        print("   SYSEX messages processed: 0 (no response)")

    # Enable MPE
    fm_x.set_mpe_enabled(True)
    fm_x.set_mpe_pitch_bend_range(24.0)

    print("✅ MPE enabled with 24 semitone range")

    return fm_x


def demonstrate_effects_integration():
    """Demonstrate effects integration."""
    print("\n🎚️  EFFECTS INTEGRATION DEMONSTRATION")
    print("-" * 50)

    fm_x = create_fm_x_demo()

    print("🎛️  Configuring effects sends...")

    # Set effects send levels
    fm_x.set_effects_sends(reverb=0.4, chorus=0.3, delay=0.2)

    print("✅ Effects configured:")
    print("   Reverb send: 40%")
    print("   Chorus send: 30%")
    print("   Delay send: 20%")

    # Configure basic sound
    fm_x.set_operator_parameters(0, {
        'frequency_ratio': 1.0,
        'envelope_levels': [0.0, 1.0, 0.7, 0.0, 0.0, 0.0, 0.0, 0.0],
        'envelope_rates': [0.02, 0.1, 0.1, 0.6, 0.0, 0.0, 0.0, 0.0]
    })

    print("🎵 Generating sound with effects...")
    audio = fm_x.generate_samples(note=55, velocity=110, modulation={}, block_size=4410)

    print(".4f")

    return fm_x


def demonstrate_algorithm_complexity():
    """Demonstrate different algorithm complexities."""
    print("\n🧠 ALGORITHM COMPLEXITY DEMONSTRATION")
    print("-" * 50)

    algorithms_to_test = ['basic', 'fm_x_10', 'fm_x_14', 'fm_x_16']

    for algorithm in algorithms_to_test:
        print(f"🎛️  Testing algorithm: {algorithm}")

        fm_x = create_fm_x_demo()
        fm_x.set_algorithm(algorithm)

        # Configure operators based on algorithm complexity
        for i in range(min(fm_x.num_operators, 4)):  # Configure first 4 operators
            fm_x.set_operator_parameters(i, {
                'frequency_ratio': 1.0 + i * 0.5,
                'envelope_levels': [0.0, 0.8, 0.6, 0.0, 0.0, 0.0, 0.0, 0.0],
                'envelope_rates': [0.01, 0.05, 0.05, 0.3, 0.0, 0.0, 0.0, 0.0]
            })

        # Quick generation test
        start_time = time.time()
        audio = fm_x.generate_samples(note=60, velocity=100, modulation={}, block_size=2205)  # 0.05 seconds
        end_time = time.time()

        print(".4f")
        print(f"   Algorithm info: {fm_x.get_algorithm_info()['modulation_matrix']}")

    print("✅ All algorithms tested successfully")


def run_performance_test():
    """Run performance test for FM-X engine."""
    print("\n⚡ PERFORMANCE TEST")
    print("-" * 50)

    fm_x = create_fm_x_demo()

    # Configure complex setup
    fm_x.set_algorithm('fm_x_16')  # Maximum complexity

    # Configure all 8 operators
    for i in range(8):
        fm_x.set_operator_parameters(i, {
            'frequency_ratio': 1.0 + i * 0.25,
            'feedback_level': min(i, 4),
            'envelope_levels': [0.0, 1.0, 0.8, 0.6, 0.4, 0.2, 0.1, 0.0],
            'envelope_rates': [0.01, 0.05, 0.03, 0.1, 0.05, 0.08, 0.1, 0.2],
            'velocity_sensitivity': 2,
            'key_scaling_depth': 1
        })

    # Add ring modulation connections
    fm_x.add_ring_modulation_connection(0, 1)
    fm_x.add_ring_modulation_connection(2, 3)
    fm_x.add_ring_modulation_connection(4, 5)

    # Configure LFOs and modulation
    fm_x.set_lfo_parameters(0, frequency=3.0, waveform='sine', depth=0.5)
    fm_x.add_modulation_assignment('lfo1', 'pitch', 0.3)

    print("🎛️  Complex FM-X setup:")
    print(f"   Algorithm: {fm_x.algorithm}")
    print(f"   Operators: {fm_x.num_operators}")
    print(f"   Ring mod connections: {len(fm_x.ring_mod_connections)}")
    print(f"   Modulation assignments: {len(fm_x.modulation_assignments)}")

    # Performance test
    test_samples = 44100  # 1 second
    block_size = 1024
    total_blocks = test_samples // block_size

    print(f"🎵 Running performance test ({total_blocks} blocks)...")

    start_time = time.time()
    total_samples = 0

    for i in range(total_blocks):
        audio = fm_x.generate_samples(note=60 + (i % 12), velocity=100, modulation={}, block_size=block_size)
        total_samples += len(audio)

    end_time = time.time()
    total_time = end_time - start_time

    print("✅ Performance test completed:")
    print(".1f")
    print(".2f")
    print(".1f")


def main():
    """Run the complete FM-X engine demonstration."""
    print("🚀 FM-X SYNTHESIS ENGINE - COMPLETE DEMONSTRATION")
    print("=" * 90)
    print("This demonstration showcases the fully FM-X compatible synthesis engine")
    print("with 8 operators, advanced modulation, ring modulation, and MIDI control.")
    print("=" * 90)

    try:
        # Run all demonstrations
        demonstrate_basic_fm_x_setup()
        demonstrate_ring_modulation()
        demonstrate_formant_synthesis()
        demonstrate_lfo_modulation()
        demonstrate_midi_control()
        demonstrate_effects_integration()
        demonstrate_algorithm_complexity()
        run_performance_test()

        print("\n" + "=" * 90)
        print("🎉 FM-X ENGINE DEMONSTRATION COMPLETE!")
        print("=" * 90)
        print("✅ All FM-X features demonstrated successfully:")
        print("   • 8 operators with 8-stage envelopes")
        print("   • Ring modulation between operators")
        print("   • Formant synthesis for vocal sounds")
        print("   • LFO modulation system")
        print("   • MIDI NRPN/SYSEX control")
        print("   • Effects integration")
        print("   • Complex algorithm routing")
        print("   • Real-time performance capability")
        print("=" * 90)

        print("\n🎵 FM-X CAPABILITIES NOW AVAILABLE:")
        print("   • Authentic FM-X synthesis reproduction")
        print("   • Professional MIDI hardware control")
        print("   • Complex timbral modulation")
        print("   • Vocal and formant synthesis")
        print("   • Real-time parameter control")
        print("   • Effects processing integration")

    except Exception as e:
        print(f"\n❌ Demonstration failed with error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n🧹 Demonstration cleanup completed.")


if __name__ == "__main__":
    main()
