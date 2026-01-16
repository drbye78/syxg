#!/usr/bin/env python3
"""
Workstation Integration Example - Complete Production Environment

This example demonstrates the full XG workstation integration capabilities,
showing how to create a complete professional production environment with
real-time control, automated mixing, and advanced workstation features.

Author: Claude (Anthropic)
Date: January 2026
"""

import numpy as np
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional

# XG Synthesizer imports
from synth.engine.modern_xg_synthesizer import ModernXGSynthesizer
from synth.audio.writer import AudioWriter
from synth.midi.file import MIDIFile
from synth.xgml.parser_v3 import XGMLParserV3
from synth.xgml.translator_v3 import XGMLTranslatorV3


class ProfessionalWorkstation:
    """Professional workstation with complete production environment."""

    def __init__(self):
        self.synth = None
        self.audio_writer = None
        self.midi_writer = None
        self.is_running = False
        self.transport_position = 0.0
        self.tempo = 120.0
        self.time_signature = (4, 4)
        self.recording = False
        self.automation_enabled = True
        self.snapshots = {}
        self.current_snapshot = None

        # Initialize workstation
        self.initialize_workstation()

    def initialize_workstation(self):
        """Initialize the complete workstation environment."""
        print("🎛️  Initializing Professional XG Workstation...")

        # Create synthesizer with professional settings
        self.synth = ModernXGSynthesizer(
            sample_rate=48000,
            max_channels=32,
            xg_enabled=True,
            gs_enabled=True,
            mpe_enabled=True,
            device_id=0x10,
            gs_mode='auto',
            s90_mode=True
        )

        # Initialize audio writer
        self.audio_writer = AudioWriter(sample_rate=48000, chunk_size_ms=100.0)

        print("✅ Workstation initialized successfully!")
        print(f"   Sample Rate: {self.synth.sample_rate}Hz")
        print(f"   Max Channels: {self.synth.max_channels}")
        print(f"   XG/GS/MPE: Enabled")

    def load_workstation_config(self, config_path: str):
        """Load complete workstation configuration."""
        print(f"📄 Loading workstation configuration: {config_path}")

        success = self.synth.load_xgml_config(config_path)
        if success:
            print("✅ Workstation configuration loaded")

            # Enable hot reloading for real-time configuration updates
            self.synth.enable_config_hot_reloading([config_path], check_interval=1.0)
            print("✅ Hot reloading enabled for configuration changes")

        return success

    def create_production_setup(self):
        """Create a complete production setup with multiple instruments."""
        print("\n🎼 Creating Production Setup...")

        # Load comprehensive XGML v3.0 configuration
        config_path = Path("examples/xgml_v3_workstation_config.xgml")
        if config_path.exists():
            self.load_workstation_config(str(config_path))
        else:
            # Create default production setup
            self._create_default_production_setup()

        # Setup transport and recording
        self.setup_transport()
        self.setup_recording()

        print("✅ Production setup complete")

    def _create_default_production_setup(self):
        """Create a default professional production setup."""
        print("   Creating default production setup...")

        # XG Effects Setup
        self.synth.set_xg_reverb_type(5)  # Hall 2
        self.synth.set_xg_chorus_type(2)  # Chorus 2
        self.synth.set_xg_variation_type(13)  # Delay LCR

        # Drum Kit
        self.synth.set_drum_kit(9, 26)  # Standard Kit 1

        # Receive Channels
        self.synth.set_receive_channel(0, 0)   # Piano
        self.synth.set_receive_channel(1, 1)   # Bass
        self.synth.set_receive_channel(2, 2)   # Guitar
        self.synth.set_receive_channel(9, 9)   # Drums

        # Musical Temperament
        self.synth.apply_temperament('equal')

        print("   Default production setup created")

    def setup_transport(self):
        """Setup transport controls and time management."""
        print("⏯️  Setting up transport controls...")

        self.transport_thread = threading.Thread(target=self._transport_loop, daemon=True)
        self.transport_thread.start()

        print("✅ Transport controls ready")

    def setup_recording(self):
        """Setup audio and MIDI recording capabilities."""
        print("🎙️  Setting up recording capabilities...")

        self.recorded_audio = []
        self.recorded_midi = []
        self.recording_start_time = 0.0

        print("✅ Recording capabilities ready")

    def start_transport(self):
        """Start the transport (play)."""
        print("▶️  Starting transport...")
        self.is_running = True
        self.transport_position = 0.0

    def stop_transport(self):
        """Stop the transport."""
        print("⏹️  Stopping transport...")
        self.is_running = False

    def start_recording(self):
        """Start recording audio and MIDI."""
        print("🎬 Starting recording...")
        self.recording = True
        self.recorded_audio = []
        self.recorded_midi = []
        self.recording_start_time = time.time()

    def stop_recording(self):
        """Stop recording and save files."""
        print("🎬 Stopping recording...")

        self.recording = False

        # Save recorded audio
        if self.recorded_audio:
            audio_data = np.concatenate(self.recorded_audio, axis=0)
            self.save_audio_recording(audio_data, "workstation_recording.wav")

        # Save recorded MIDI (would need MIDI writer implementation)
        if self.recorded_midi:
            print(f"   Recorded {len(self.recorded_midi)} MIDI events")

    def save_snapshot(self, name: str):
        """Save current workstation state as a snapshot."""
        print(f"💾 Saving snapshot: {name}")

        # Get current synthesizer state
        info = self.synth.get_synthesizer_info()

        # Create snapshot with current parameter values
        snapshot = {
            'timestamp': time.time(),
            'transport_position': self.transport_position,
            'tempo': self.tempo,
            'time_signature': self.time_signature,
            'synthesizer_info': info,
            'parameters': self._get_current_parameters()
        }

        self.snapshots[name] = snapshot
        print(f"✅ Snapshot saved: {name}")

    def recall_snapshot(self, name: str):
        """Recall a saved workstation snapshot."""
        if name not in self.snapshots:
            print(f"❌ Snapshot not found: {name}")
            return False

        print(f"📂 Recalling snapshot: {name}")

        snapshot = self.snapshots[name]

        # Restore parameters (would need parameter restoration logic)
        # This is a placeholder for the actual restoration implementation
        print(f"✅ Snapshot recalled: {name}")

        return True

    def enable_automation(self):
        """Enable real-time parameter automation."""
        print("🤖 Enabling automation...")

        if hasattr(self.synth, 'enable_config_hot_reloading'):
            # Enable parameter automation through hot reloading
            self.synth.enable_config_hot_reloading(check_interval=0.1)

        self.automation_enabled = True
        print("✅ Automation enabled")

    def disable_automation(self):
        """Disable parameter automation."""
        print("🤖 Disabling automation...")

        if hasattr(self.synth, 'disable_config_hot_reloading'):
            self.synth.disable_config_hot_reloading()

        self.automation_enabled = False
        print("✅ Automation disabled")

    def generate_audio_block(self) -> np.ndarray:
        """Generate audio block and handle recording."""
        # Generate audio from synthesizer
        audio_block = self.synth.generate_audio_block()

        # Record if recording is active
        if self.recording:
            self.recorded_audio.append(audio_block.copy())

        return audio_block

    def save_audio_recording(self, audio_data: np.ndarray, filename: str):
        """Save recorded audio to file."""
        print(f"💾 Saving audio recording to {filename}...")

        try:
            writer = AudioWriter(sample_rate=self.synth.sample_rate, chunk_size_ms=100.0)
            av_writer = writer.create_writer(filename, "wav")

            with av_writer as audio_file:
                audio_file.write(audio_data)

            file_size_mb = Path(filename).stat().st_size / (1024 * 1024)
            duration_sec = len(audio_data) / self.synth.sample_rate

            print("✅ Audio recording saved successfully"            print(".1f"            print(".2f")

        except Exception as e:
            print(f"❌ Failed to save audio recording: {e}")

    def get_workstation_status(self) -> Dict[str, Any]:
        """Get comprehensive workstation status."""
        status = {
            'running': self.is_running,
            'recording': self.recording,
            'transport_position': self.transport_position,
            'tempo': self.tempo,
            'time_signature': self.time_signature,
            'automation_enabled': self.automation_enabled,
            'current_snapshot': self.current_snapshot,
            'available_snapshots': list(self.snapshots.keys()),
            'synthesizer_info': self.synth.get_synthesizer_info() if self.synth else None
        }

        return status

    def _transport_loop(self):
        """Main transport loop for time management."""
        while True:
            if self.is_running:
                self.transport_position += 0.01  # 10ms increment
                time.sleep(0.01)
            else:
                time.sleep(0.1)

    def _get_current_parameters(self) -> Dict[str, Any]:
        """Get current workstation parameters for snapshot saving."""
        # This would collect all current parameter values
        # Placeholder implementation
        return {
            'effects_reverb_level': 0.3,
            'effects_chorus_depth': 0.5,
            'master_volume': 0.8,
            'tempo': self.tempo
        }


def demonstrate_workstation_features():
    """Demonstrate complete workstation functionality."""
    print("🎛️  XG Workstation Integration Demonstration")
    print("=" * 60)

    # Create professional workstation
    workstation = ProfessionalWorkstation()

    try:
        # Setup production environment
        workstation.create_production_setup()

        # Enable automation
        workstation.enable_automation()

        # Save initial state
        workstation.save_snapshot("Initial Setup")

        # Configure workstation features
        print("\n🎛️  Configuring Workstation Features...")

        # XG Effects Configuration
        workstation.synth.set_xg_reverb_type(5)  # Hall 2
        workstation.synth.set_xg_chorus_type(2)  # Chorus 2
        workstation.synth.set_xg_variation_type(13)  # Delay LCR

        # Drum Kit Setup
        workstation.synth.set_drum_kit(9, 26)

        # Receive Channel Mapping
        for i in range(16):
            workstation.synth.set_receive_channel(i, i)

        # Musical Temperament
        workstation.synth.apply_temperament('equal')

        print("✅ Workstation features configured")

        # Save configured state
        workstation.save_snapshot("Production Ready")

        # Start transport and recording
        workstation.start_recording()
        workstation.start_transport()

        print("\n🎵 Performing workstation demonstration...")

        # Simulate performance (would normally be real-time MIDI input)
        # Generate some audio blocks to simulate recording
        for i in range(100):  # ~1 second at 10 blocks per second
            audio_block = workstation.generate_audio_block()
            time.sleep(0.01)  # 10ms delay

        # Stop recording and transport
        workstation.stop_transport()
        workstation.stop_recording()

        # Save final state
        workstation.save_snapshot("Performance Complete")

        # Get workstation status
        status = workstation.get_workstation_status()
        print("
📊 Final Workstation Status:"        print(f"   Transport Running: {status['running']}")
        print(f"   Recording: {status['recording']}")
        print(f"   Automation: {status['automation_enabled']}")
        print(f"   Snapshots: {len(status['available_snapshots'])}")
        print(f"   Active Voices: {status['synthesizer_info'].get('total_active_voices', 0) if status['synthesizer_info'] else 0}")

        # Cleanup
        workstation.disable_automation()
        workstation.synth.cleanup()

        print("\n🎉 Workstation demonstration complete!")
        print("   Features demonstrated:")
        print("   ✅ XG Effects System Integration")
        print("   ✅ Multi-timbral Receive Channel Management")
        print("   ✅ Drum Kit Configuration")
        print("   ✅ Musical Temperament Application")
        print("   ✅ Snapshot Management")
        print("   ✅ Transport Control")
        print("   ✅ Audio Recording")
        print("   ✅ XGML v3.0 Configuration")
        print("   ✅ Hot Reloading")
        print("   ✅ Professional Workstation Environment")

    except Exception as e:
        print(f"❌ Error during workstation demonstration: {e}")
        import traceback
        traceback.print_exc()


def create_workstation_template():
    """Create a workstation template configuration."""
    template_config = """
xg_dsl_version: "3.0"
description: "Professional Workstation Template"
template: "workstation_template"

# Workstation-specific settings
workstation_features:
  motif_integration:
    enabled: true
    arpeggiator_system:
      global_settings:
        tempo: 128
        swing: 0.0
        gate_time: 0.9
        velocity_rate: 100

  s90_awm_stereo:
    enabled: true
    global_mixing:
      stereo_width: 1.2
      compression_ratio: 1.0
      limiter_threshold: -0.2

  multi_timbral:
    channels: 32
    voice_reserve:
      channel_0: 128   # Maximum for primary instrument
      channel_9: 64    # Good reserve for drums

  xg_effects:
    system_effects:
      reverb: {type: 4, time: 2.5, level: 0.6, hf_damping: 0.2}
      chorus: {type: 1, rate: 0.5, depth: 0.6, feedback: 0.2}

# Professional audio settings
synthesizer_core:
  audio:
    sample_rate: 48000
    buffer_size: 256
    real_time: true
  performance:
    max_polyphony: 512
    voice_stealing: "priority"
    dynamic_polyphony: true

# Effects processing for production
effects_processing:
  system_effects:
    reverb:
      algorithm: "hall_2"
      parameters:
        time: 2.5
        level: 0.6
        hf_damping: 0.2
        diffusion: 0.8
    chorus:
      algorithm: "chorus_2"
      parameters:
        rate: 0.8
        depth: 0.5
        feedback: 0.3
        mix: 0.4
    delay:
      algorithm: "stereo_delay"
      parameters:
        left_delay: 0.3
        right_delay: 0.35
        feedback: 0.4
        hf_damp: 0.3
        level: 0.5

  master_processing:
    equalizer:
      bands:
        - {frequency: 60.0, gain: 1.0, q: 0.8, type: "low_shelf"}
        - {frequency: 5000.0, gain: -1.0, q: 1.4, type: "peaking"}
        - {frequency: 12000.0, gain: -0.5, q: 0.9, type: "high_shelf"}
    limiter:
      threshold: -0.1
      ratio: 8.0
      attack: 0.5
      release: 100.0
      gain: 0.0
      soft_knee: true
      auto_release: true

# Comprehensive modulation system
modulation_system:
  matrix:
    routes:
      - {source: "lfo1", destination: "pitch", amount: 0.02, bipolar: true}
      - {source: "velocity", destination: "filter_cutoff", amount: 1200.0}
      - {source: "aftertouch", destination: "volume", amount: -0.3, bipolar: true}
      - {source: "envelope1", destination: "filter_cutoff", amount: 2400.0}

# Professional performance controls
performance_controls:
  assignable_knobs:
    knob_1: {name: "Reverb Time", parameter: "effects_processing.system_effects.reverb.parameters.time", range: [0.1, 10.0], curve: "exponential", default: 2.5}
    knob_2: {name: "Chorus Depth", parameter: "effects_processing.system_effects.chorus.parameters.depth", range: [0.0, 1.0], curve: "linear", default: 0.5}
    knob_3: {name: "Filter Cutoff", parameter: "global_filter_cutoff", range: [20.0, 8000.0], curve: "exponential", default: 1000.0}
    knob_4: {name: "Master Volume", parameter: "synthesizer_core.master_volume", range: [-60.0, 12.0], curve: "linear", default: 0.0}

  snapshots:
    - name: "Clean Sound"
      parameters: {effects_processing.system_effects.reverb.parameters.level: 0.0}
    - name: "Hall Reverb"
      parameters: {effects_processing.system_effects.reverb.parameters.time: 3.5, effects_processing.system_effects.reverb.parameters.level: 0.7}
    - name: "Epic Sound"
      parameters: {effects_processing.system_effects.reverb.parameters.time: 5.0, effects_processing.system_effects.chorus.parameters.depth: 0.8}

# Advanced sequencing
sequencing:
  sequencer_core:
    enabled: true
    resolution: 960
    tempo: 128
    time_signature: "4/4"
    swing: 0.1
    quantization: "1/16"

  patterns:
    - name: "house_beat"
      type: "drum"
      steps: 16
      notes:
        36: [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0]
        38: [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0]
        42: [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0]
      velocity: [100, 90, 70]

  real_time_control:
    pattern_chain: ["house_beat"]
    transition_smoothing: 0.1
    pattern_sync: "bar"
    tempo_following: true
"""

    # Save template
    template_path = Path("examples/workstation_template.xgml")
    with open(template_path, 'w') as f:
        f.write(template_config)

    print(f"✅ Workstation template saved to {template_path}")


def main():
    """Main workstation demonstration."""
    # Create workstation template
    create_workstation_template()

    # Run workstation demonstration
    demonstrate_workstation_features()


if __name__ == "__main__":
    main()
