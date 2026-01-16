#!/usr/bin/env python3
"""
XG/GS/MPE Workstation Example - Complete XG/GS/MPE Demonstration

This example demonstrates the full XG workstation synthesizer capabilities,
including XG specification compliance, GS compatibility, and MPE support.
Shows professional workstation features for music production.

Author: Claude (Anthropic)
Date: January 2026
"""

import numpy as np
import time
from pathlib import Path
from typing import Dict, Any

# XG Synthesizer imports
from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer
from synth.audio.writer import AudioWriter


def create_workstation_synthesizer() -> ModernXGSynthesizer:
    """Create a fully configured XG workstation synthesizer."""
    print("🎹 Creating XG/GS/MPE Workstation Synthesizer...")

    # Initialize with professional settings
    synth = ModernXGSynthesizer(
        sample_rate=48000,        # Professional sample rate
        max_channels=32,          # S90/S70 expanded channel support
        xg_enabled=True,          # XG specification compliance
        gs_enabled=True,          # GS backward compatibility
        mpe_enabled=True,         # Microtonal expression support
        device_id=0x10,           # Standard XG device ID
        gs_mode='auto',           # Auto-detect XG/GS mode
        s90_mode=True             # S90/S70 workstation features
    )

    print("✅ XG/GS/MPE Workstation initialized successfully!")
    print(f"   Sample Rate: {synth.sample_rate}Hz")
    print(f"   Max Channels: {synth.max_channels}")
    print(f"   XG Enabled: {synth.xg_enabled}")
    print(f"   GS Enabled: {synth.gs_enabled}")
    print(f"   MPE Enabled: {synth.mpe_enabled}")
    print(f"   S90 Mode: {synth.s90_mode}")

    return synth


def demonstrate_xg_effects_system(synth: ModernXGSynthesizer):
    """Demonstrate XG effects system with professional settings."""
    print("\n🎛️  Configuring XG Effects System...")

    # System Reverb (XG Hall 2)
    success = synth.set_xg_reverb_type(5)  # Hall 2
    if success:
        print("✅ XG Reverb: Hall 2 configured")

    # System Chorus (XG Chorus 2)
    success = synth.set_xg_chorus_type(2)  # Chorus 2
    if success:
        print("✅ XG Chorus: Chorus 2 configured")

    # Variation Effect (XG Delay LCR)
    success = synth.set_xg_variation_type(13)  # Delay LCR
    if success:
        print("✅ XG Variation: Delay LCR configured")

    # Get XG compliance report
    compliance = synth.get_xg_compliance_report()
    print(f"🎯 XG Compliance: {compliance.get('overall_compliance', 'Unknown')}")
    print(f"   Effects Types: {compliance.get('effect_types', 0)}")
    print(f"   Drum Parameters: {compliance.get('drum_parameters', 0)}")


def demonstrate_gs_compatibility(synth: ModernXGSynthesizer):
    """Demonstrate GS compatibility and mode switching."""
    print("\n🎼 Demonstrating GS Compatibility...")

    # Set GS mode explicitly
    synth.set_gs_mode('gs')
    print("✅ Switched to GS mode")

    # Get GS system information
    gs_info = synth.get_gs_system_info()
    if gs_info:
        print(f"✅ GS System Info: {gs_info.get('status', 'Unknown')}")

    # Switch back to XG mode
    synth.set_gs_mode('xg')
    print("✅ Switched back to XG mode")

    # Demonstrate GS part parameters
    success = synth.set_gs_part_parameter(0, 0x18, 100)  # Part Level
    if success:
        print("✅ GS Part Parameter: Level set successfully")

    # Reset GS system
    synth.reset_gs_system()
    print("✅ GS System reset to defaults")


def demonstrate_mpe_support(synth: ModernXGSynthesizer):
    """Demonstrate MPE (Microtonal Pitch Expression) support."""
    print("\n🎹 Demonstrating MPE Support...")

    # Enable MPE
    synth.set_mpe_enabled(True)
    print("✅ MPE enabled")

    # Get MPE information
    mpe_info = synth.get_mpe_info()
    if mpe_info.get('enabled', False):
        print("✅ MPE Status: Enabled")
        print(f"   Zones: {mpe_info.get('zones', 0)}")
        print(f"   Active Notes: {mpe_info.get('active_notes', 0)}")
        print(f"   Pitch Bend Range: {mpe_info.get('pitch_bend_range', 48)}")

    # MPE note events (would normally come from MPE controller)
    print("🎵 MPE note events would be processed here...")

    # Reset MPE system
    synth.reset_mpe()
    print("✅ MPE system reset")


def demonstrate_workstation_features(synth: ModernXGSynthesizer):
    """Demonstrate workstation-specific features."""
    print("\n🎛️  Demonstrating Workstation Features...")

    # XG Drum Kit Setup
    success = synth.set_drum_kit(9, 26)  # Standard Kit 1
    if success:
        print("✅ XG Drum Kit: Standard Kit 1 assigned to channel 9")

    # XG Receive Channel Management
    success = synth.set_receive_channel(0, 0)  # Part 0 receives from MIDI channel 0
    if success:
        print("✅ XG Receive Channel: Part 0 → MIDI Channel 0")

    success = synth.set_receive_channel(1, 1)  # Part 1 receives from MIDI channel 1
    if success:
        print("✅ XG Receive Channel: Part 1 → MIDI Channel 1")

    # Check receive channel mapping
    mapping = synth.get_receive_channel_mapping()
    if mapping:
        print(f"✅ Receive Channel Mapping: {len(mapping.get('parts', {}))} parts configured")

    # Apply musical temperament
    success = synth.apply_temperament('equal')  # Equal temperament
    if success:
        print("✅ Musical Temperament: Equal temperament applied")

    # Get comprehensive synthesizer information
    info = synth.get_synthesizer_info()
    print("📊 Synthesizer Status:")
    print(f"   Active Channels: {info.get('active_channels', 0)}")
    print(f"   Active Voices: {info.get('total_active_voices', 0)}")
    print(f"   Engines: {len(info.get('engines', {}))}")
    print(f"   XG Compliance: {info.get('xg_compliance', 'Unknown')}")


def demonstrate_xgml_v3_integration(synth: ModernXGSynthesizer):
    """Demonstrate XGML v3.0 configuration integration."""
    print("\n📄 Demonstrating XGML v3.0 Integration...")

    # Create a sample XGML v3.0 configuration
    xgml_config = """
xg_dsl_version: "3.0"
description: "XG Workstation Demo Configuration"

synthesizer_core:
  audio:
    sample_rate: 48000
    buffer_size: 512
  performance:
    max_polyphony: 256

basic_messages:
  channels:
    channel_1:
      program_change: "acoustic_grand_piano"
      volume: 100
      pan: "center"
      reverb_send: 40
      chorus_send: 20

effects_processing:
  system_effects:
    reverb:
      algorithm: "hall_2"
      parameters:
        time: 2.5
        level: 0.8
        hf_damping: 0.3
    chorus:
      algorithm: "chorus_2"
      parameters:
        rate: 1.0
        depth: 0.6
        feedback: 0.2

workstation_features:
  multi_timbral:
    channels: 16
    voice_reserve:
      channel_0: 64
      channel_9: 32
"""

    # Save to temporary file
    config_path = Path("temp_workstation_config.xgml")
    with open(config_path, 'w') as f:
        f.write(xgml_config)

    # Load XGML configuration
    success = synth.load_xgml_config(str(config_path))
    if success:
        print("✅ XGML v3.0 Configuration loaded successfully")

        # Demonstrate hot reloading (enable)
        success = synth.enable_config_hot_reloading([config_path], check_interval=2.0)
        if success:
            print("✅ Hot reloading enabled for XGML configuration")

            # Get hot reload status
            status = synth.get_hot_reload_status()
            print(f"✅ Hot reload status: {status.get('enabled', False)}")

            # Disable hot reloading
            synth.disable_config_hot_reloading()
            print("✅ Hot reloading disabled")

    # Clean up
    config_path.unlink(missing_ok=True)


def generate_workstation_demo_audio(synth: ModernXGSynthesizer) -> np.ndarray:
    """Generate demonstration audio showcasing workstation features."""
    print("\n🎵 Generating Workstation Demo Audio...")

    # MIDI sequence demonstrating XG/GS/MPE features
    midi_events = [
        # XG System Setup (time 0.0)
        {'time': 0.0, 'type': 'control_change', 'channel': 0, 'controller': 91, 'value': 40},  # Reverb Send
        {'time': 0.0, 'type': 'control_change', 'channel': 0, 'controller': 93, 'value': 20},  # Chorus Send

        # Piano melody (XG channel 0)
        {'time': 0.0, 'type': 'note_on', 'channel': 0, 'note': 60, 'velocity': 80},   # C4
        {'time': 0.5, 'type': 'note_off', 'channel': 0, 'note': 60, 'velocity': 40},
        {'time': 0.5, 'type': 'note_on', 'channel': 0, 'note': 64, 'velocity': 75},   # E4
        {'time': 1.0, 'type': 'note_off', 'channel': 0, 'note': 64, 'velocity': 40},
        {'time': 1.0, 'type': 'note_on', 'channel': 0, 'note': 67, 'velocity': 85},   # G4
        {'time': 1.5, 'type': 'note_off', 'channel': 0, 'note': 67, 'velocity': 40},
        {'time': 1.5, 'type': 'note_on', 'channel': 0, 'note': 72, 'velocity': 90},   # C5
        {'time': 2.5, 'type': 'note_off', 'channel': 0, 'note': 72, 'velocity': 40},

        # Drum pattern (XG channel 9)
        {'time': 0.0, 'type': 'note_on', 'channel': 9, 'note': 36, 'velocity': 100},   # Kick
        {'time': 0.5, 'type': 'note_off', 'channel': 9, 'note': 36, 'velocity': 40},
        {'time': 0.25, 'type': 'note_on', 'channel': 9, 'note': 38, 'velocity': 95},   # Snare
        {'time': 0.75, 'type': 'note_off', 'channel': 9, 'note': 38, 'velocity': 40},
        {'time': 1.0, 'type': 'note_on', 'channel': 9, 'note': 36, 'velocity': 90},    # Kick
        {'time': 1.5, 'type': 'note_off', 'channel': 9, 'note': 36, 'velocity': 40},
        {'time': 1.25, 'type': 'note_on', 'channel': 9, 'note': 38, 'velocity': 85},   # Snare
        {'time': 1.75, 'type': 'note_off', 'channel': 9, 'note': 38, 'velocity': 40},
    ]

    # Send MIDI message block
    synth.send_midi_message_block(midi_events)

    # Generate audio
    total_samples = int(3.0 * synth.sample_rate)  # 3 seconds
    audio_data = []

    block_size = 1024
    for i in range(0, total_samples, block_size):
        block = synth.generate_audio_block(block_size)
        audio_data.append(block)

    # Concatenate all blocks
    full_audio = np.concatenate(audio_data, axis=0)

    print(f"✅ Generated {len(full_audio)} samples ({len(full_audio)/synth.sample_rate:.1f} seconds)")

    return full_audio


def save_demo_audio(audio: np.ndarray, filename: str = "xg_workstation_demo.wav"):
    """Save demonstration audio to file."""
    print(f"\n💾 Saving demo audio to {filename}...")

    try:
        # Create audio writer with proper parameters
        writer = AudioWriter(sample_rate=48000, chunk_size_ms=100.0)
        av_writer = writer.create_writer(filename, "wav")

        # Write audio data using context manager
        with av_writer as audio_file:
            audio_file.write(audio)

        print(f"✅ Audio saved successfully to {filename}")
        file_size_mb = Path(filename).stat().st_size / (1024 * 1024)
        print(".1f")

    except Exception as e:
        print(f"❌ Failed to save audio to {filename}: {e}")


def main():
    """Main demonstration function."""
    print("🎼 XG/GS/MPE Workstation Synthesizer Demonstration")
    print("=" * 60)

    try:
        # Create workstation synthesizer
        synth = create_workstation_synthesizer()

        # Demonstrate XG effects system
        demonstrate_xg_effects_system(synth)

        # Demonstrate GS compatibility
        demonstrate_gs_compatibility(synth)

        # Demonstrate MPE support
        demonstrate_mpe_support(synth)

        # Demonstrate workstation features
        demonstrate_workstation_features(synth)

        # Demonstrate XGML v3.0 integration
        demonstrate_xgml_v3_integration(synth)

        # Generate demonstration audio
        demo_audio = generate_workstation_demo_audio(synth)

        # Save demo audio
        save_demo_audio(demo_audio)

        # Cleanup
        synth.cleanup()

        print("\n🎉 XG/GS/MPE Workstation Demonstration Complete!")
        print("   Features demonstrated:")
        print("   ✅ XG Effects System (Reverb, Chorus, Variation)")
        print("   ✅ GS Compatibility Mode")
        print("   ✅ MPE Support")
        print("   ✅ Workstation Features (Drum Kits, Receive Channels)")
        print("   ✅ XGML v3.0 Configuration Integration")
        print("   ✅ Professional Audio Generation")

    except Exception as e:
        print(f"❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
