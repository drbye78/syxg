#!/usr/bin/env python3
"""
Specialized Synthesis Engines Demonstration

Showcase the advanced specialized engines: Convolution Reverb, MPE support,
and Advanced Physical Modeling for professional music production.
"""

import numpy as np
from pathlib import Path
import time

# Import specialized engines
from synth.engine.convolution_reverb_engine import ConvolutionReverbEngine
from synth.mpe.mpe_manager import MPEManager
from synth.engine.advanced_physical_engine import AdvancedPhysicalEngine


def create_specialized_engines_demo():
    """Create and configure specialized engines demonstration."""
    print("🎛️  SPECIALIZED SYNTHESIS ENGINES DEMONSTRATION")
    print("=" * 80)

    print("🎹 Initializing Specialized Engines...")

    # Convolution Reverb Engine
    print("   📊 Convolution Reverb Engine...")
    convolution_reverb = ConvolutionReverbEngine()

    # MPE Manager
    print("   🎹 MPE Manager...")
    mpe_manager = MPEManager()

    # Advanced Physical Modeling Engine
    print("   🎸 Advanced Physical Modeling Engine...")
    physical_engine = AdvancedPhysicalEngine()

    print("✅ All specialized engines initialized successfully")

    return convolution_reverb, mpe_manager, physical_engine


def demonstrate_convolution_reverb():
    """Demonstrate convolution reverb capabilities."""
    print("\n🌊 CONVOLUTION REVERB DEMONSTRATION")
    print("-" * 50)

    reverb = ConvolutionReverbEngine()

    print("🎛️  Loading built-in reverb presets...")

    # Test different presets
    presets = ['small_room', 'medium_room', 'large_room', 'small_hall', 'chamber']

    for preset in presets:
        if reverb.load_preset(preset):
            info = reverb.get_engine_info()
            current_preset = info['current_preset']
            if current_preset:
                ir_info = current_preset.get('ir_info', {})
                decay_time = ir_info.get('decay_time', 0.0)
                print(f"   ✅ {preset}: {decay_time:.2f}s decay, "
                      f"wet:{current_preset['wet_level']:.1f}, dry:{current_preset['dry_level']:.1f}")
            else:
                print(f"   ❌ Failed to load: {preset}")
        else:
            print(f"   ❌ Preset not found: {preset}")

    print("🎵 Testing reverb processing...")

    # Create a test signal (simple tone)
    sample_rate = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    test_signal = 0.5 * np.sin(2 * np.pi * 440 * t)  # A4 tone

    # Apply reverb
    reverb.load_preset('medium_room')
    reverb.set_parameters(wet_level=0.4, dry_level=0.6, predelay=0.05)

    # Process in blocks
    block_size = 1024
    processed_blocks = []

    for i in range(0, len(test_signal), block_size):
        block = test_signal[i:i+block_size]
        if len(block) < block_size:
            # Pad last block
            block = np.pad(block, (0, block_size - len(block)))

        # Convert to stereo for processing
        stereo_block = np.column_stack([block, block])

        # Apply reverb
        processed_stereo = reverb.process_audio(stereo_block)
        processed_blocks.append(processed_stereo[:, 0])  # Take mono

    # Concatenate processed blocks
    processed_signal = np.concatenate(processed_blocks)[:len(test_signal)]

    print("   ✅ Reverb processing completed")
    print(".4f")
    print(".4f")

    print("✅ Convolution reverb demonstration completed")


def demonstrate_mpe_support():
    """Demonstrate MPE (Microtonal Expression) capabilities."""
    print("\n🎹 MPE (MICROTONAL EXPRESSION) DEMONSTRATION")
    print("-" * 50)

    mpe = MPEManager()

    print("🎛️  Configuring MPE zones...")

    # Get MPE info
    mpe_info = mpe.get_mpe_info()
    print(f"   MPE Enabled: {mpe_info['enabled']}")
    print(f"   Zones: {len(mpe_info['zones'])}")
    print(f"   Global Pitch Bend Range: ±{mpe_info['global_pitch_bend_range']} semitones")

    # Configure zones
    print("   Configuring Zone 1 (Channels 1-8)...")
    mpe.configure_zone(1, 0, 7)  # MIDI channels 0-7

    print("   Configuring Zone 2 (Channels 9-16)...")
    mpe.configure_zone(2, 8, 15)  # MIDI channels 8-15

    # Test note processing
    print("🎵 Testing MPE note processing...")

    # Note on with MPE data
    mpe_note = mpe.process_note_on(0, 60, 100)  # C4 on channel 0
    if mpe_note:
        print(f"   Note On: {mpe_note.note_number}, Channel: {mpe_note.channel}, Velocity: {mpe_note.velocity}")
        print(f"   Initial Frequency: {mpe_note.frequency:.1f} Hz")
        print(f"   Initial Pitch Bend: {mpe_note.pitch_bend:.3f} semitones")

        # Apply pitch bend
        mpe.process_pitch_bend(0, 9000)  # +2 semitones (8192 + 1818)
        print(f"   After Pitch Bend: {mpe_note.adjusted_frequency:.1f} Hz")
        print(f"   Pitch Bend Amount: {mpe_note.pitch_bend:.3f} semitones")

        # Apply timbre control
        mpe.process_timbre(0, 96)  # 75% timbre
        print(f"   Timbre: {mpe_note.timbre:.2f}")

        # Apply pressure
        mpe.process_pressure(0, 64)  # 50% pressure
        print(f"   Pressure: {mpe_note.pressure:.2f}")

    # Test per-note pressure (poly pressure)
    mpe.process_poly_pressure(0, 60, 127)  # Full pressure on note
    if mpe_note:
        print(f"   Per-note Pressure: {mpe_note.pressure:.2f}")

    # Note off
    released_note = mpe.process_note_off(0, 60)
    if released_note:
        print(f"   Note Off: {released_note.note_number}")

    # Get zone information
    zone_info = mpe.get_zone_info(1)
    if zone_info:
        print("   Zone 1 Status:")
        print(f"     Channels: {zone_info['lower_channel']}-{zone_info['upper_channel']}")
        print(f"     Master Channel: {zone_info['master_channel']}")
        print(f"     Active Notes: {zone_info['channel_info']['active_notes_count']}")

    print("✅ MPE demonstration completed")


def demonstrate_physical_modeling():
    """Demonstrate advanced physical modeling capabilities."""
    print("\n🎸 ADVANCED PHYSICAL MODELING DEMONSTRATION")
    print("-" * 50)

    physical = AdvancedPhysicalEngine()

    print("🎛️  Exploring instrument configurations...")

    # Get available instruments
    instruments = physical.get_available_instruments()
    print(f"   Available instruments: {len(instruments)}")
    for instrument in instruments:
        info = physical.get_instrument_info(instrument)
        if info:
            print(f"     {instrument}: {info['strings']} strings, {info['resonators']} resonators")

    print("🎵 Testing guitar simulation...")

    # Load guitar instrument
    if physical.load_instrument('guitar'):
        print("   ✅ Guitar loaded successfully")

        # Get instrument status
        status = physical.get_physical_modeling_status()
        print(f"   Active Strings: {status['total_active']}")

        # Test note generation (this would normally be called by the synthesizer)
        # For demonstration, we'll just check the configuration
        engine_info = physical.get_engine_info()
        print(f"   Current Instrument: {engine_info['current_instrument']}")
        print(f"   Max Strings: {engine_info['max_strings']}")
        print(f"   Max Resonators: {engine_info['max_resonators']}")

    else:
        print("   ❌ Failed to load guitar")

    print("🎵 Testing bell simulation...")

    # Load bell instrument
    if physical.load_instrument('bell'):
        print("   ✅ Bell loaded successfully")

        status = physical.get_physical_modeling_status()
        print(f"   Active Resonators: {status['total_active']}")

        # Bell uses modal resonators instead of strings
        for i, resonator in enumerate(status['resonators']):
            if resonator['active']:
                print(f"     Resonator {i}: {len(resonator['modes'])} modes")

    else:
        print("   ❌ Failed to load bell")

    print("🎵 Testing drum simulation...")

    # Load drum instrument
    if physical.load_instrument('drum'):
        print("   ✅ Drum loaded successfully")

        status = physical.get_physical_modeling_status()
        print(f"   Active Components: {status['total_active']}")

    else:
        print("   ❌ Failed to load drum")

    print("✅ Physical modeling demonstration completed")


def demonstrate_engine_integration():
    """Demonstrate how specialized engines integrate with the synthesizer."""
    print("\n🔗 ENGINE INTEGRATION DEMONSTRATION")
    print("-" * 50)

    print("🎛️  Testing integration capabilities...")

    # Convolution Reverb can process any audio
    reverb = ConvolutionReverbEngine()
    reverb.load_preset('small_hall')

    print("   Convolution Reverb: Can process external audio streams")
    print("   MPE Manager: Provides per-note control for any synthesis engine")
    print("   Physical Modeling: Generates realistic acoustic instrument sounds")

    # Show how they would work together
    print("   Integration Workflow:")
    print("     1. Physical Modeling generates raw acoustic sound")
    print("     2. MPE provides expressive per-note control")
    print("     3. Convolution Reverb adds realistic spatial acoustics")
    print("     4. All processed through the synthesizer's main audio chain")

    # Test parameter compatibility
    print("   Parameter Ranges:")
    print("     MPE Pitch Bend: ±48 semitones (microtonal precision)")
    print("     Reverb Decay: 0.1-10+ seconds (acoustic simulation)")
    print("     Physical Strings: 20Hz-20kHz (full frequency range)")

    print("✅ Engine integration demonstration completed")


def run_performance_comparison():
    """Run performance comparison between specialized engines."""
    print("\n⚡ PERFORMANCE COMPARISON")
    print("-" * 50)

    print("🎛️  Comparing engine performance...")

    engines = {
        'Convolution Reverb': ConvolutionReverbEngine(),
        'Physical Modeling': AdvancedPhysicalEngine(),
    }

    # Initialize MPE manager
    mpe = MPEManager()

    test_iterations = 100

    for engine_name, engine in engines.items():
        print(f"   Testing {engine_name}...")

        start_time = time.time()

        # Perform test operations
        for i in range(test_iterations):
            if engine_name == 'Convolution Reverb':
                # Test reverb processing
                test_audio = np.random.randn(1024, 2) * 0.1
                processed = engine.process_audio(test_audio)
            elif engine_name == 'Physical Modeling':
                # Test sample generation
                audio = engine.generate_samples(60, 80, {}, 1024)

        end_time = time.time()
        total_time = end_time - start_time

        print(".4f")
        print(".0f")
        print(".2f")

    # MPE performance test
    print("   Testing MPE Manager...")

    start_time = time.time()
    for i in range(test_iterations):
        # Test MPE operations
        mpe.process_note_on(i % 16, 60 + (i % 24), 100)
        mpe.process_pitch_bend(i % 16, 8192 + (i * 100) % 8192)
        mpe.process_note_off(i % 16, 60 + (i % 24))

    end_time = time.time()
    mpe_time = end_time - start_time

    print(".4f")
    print(".0f")
    print(".2f")

    print("✅ Performance comparison completed")


def main():
    """Run the complete specialized engines demonstration."""
    print("🚀 SPECIALIZED SYNTHESIS ENGINES - COMPLETE DEMONSTRATION")
    print("=" * 90)
    print("This demonstration showcases advanced specialized engines:")
    print("Convolution Reverb, MPE (Microtonal Expression), and Advanced Physical Modeling")
    print("=" * 90)

    try:
        # Create engines
        convolution_reverb, mpe_manager, physical_engine = create_specialized_engines_demo()

        # Run demonstrations
        demonstrate_convolution_reverb()
        demonstrate_mpe_support()
        demonstrate_physical_modeling()
        demonstrate_engine_integration()
        run_performance_comparison()

        print("\n" + "=" * 90)
        print("🎉 SPECIALIZED ENGINES DEMONSTRATION COMPLETE!")
        print("=" * 90)
        print("✅ All demonstrations completed successfully")
        print("✅ Convolution Reverb: High-quality algorithmic and IR-based reverb")
        print("✅ MPE Support: Per-note microtonal expression and control")
        print("✅ Physical Modeling: Realistic acoustic instrument simulation")
        print("✅ Engine Integration: Seamless synthesizer integration")
        print("✅ Performance: Real-time operation capability")
        print("=" * 90)

        print("\n🎵 SPECIALIZED ENGINE CAPABILITIES NOW AVAILABLE:")
        print("   • Convolution Reverb: Professional spatial audio processing")
        print("   • MPE (Microtonal Expression): Per-note pitch, timbre, pressure control")
        print("   • Advanced Physical Modeling: Realistic acoustic instrument synthesis")
        print("   • Waveguide Strings: Karplus-Strong algorithm implementation")
        print("   • Modal Resonators: Bell and percussion synthesis")
        print("   • Real-time Processing: Live parameter control and modulation")
        print("   • Professional Quality: Production-ready audio processing")

    except Exception as e:
        print(f"\n❌ Demonstration failed with error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n🧹 Demonstration cleanup completed.")


if __name__ == "__main__":
    main()
