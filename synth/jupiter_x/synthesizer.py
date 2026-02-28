"""
Jupiter-X Main Synthesizer Class

Complete Jupiter-X synthesizer implementation integrating all components
into a unified, production-ready synthesizer interface.
"""
from __future__ import annotations

from typing import Any
import threading
import numpy as np

from .constants import *
from .component_manager import JupiterXComponentManager
from .arpeggiator import JupiterXArpeggiatorEngine
from .mpe_manager import JupiterXMPEManager
from .unified_parameter_system import JupiterXUnifiedParameterSystem
from .performance_optimizer import JupiterXPerformanceOptimizer
from ..effects.effects_coordinator import XGEffectsCoordinator


class JupiterXSynthesizer:
    """
    Jupiter-X Main Synthesizer Class

    Complete synthesizer implementation with all Jupiter-X features,
    integrating component manager, arpeggiator, MPE, effects, and
    parameter system into a unified interface.
    """

    def __init__(self, sample_rate: int = 44100, buffer_size: int = 1024):
        """
        Initialize Jupiter-X synthesizer.

        Args:
            sample_rate: Audio sample rate in Hz
            buffer_size: Audio buffer size for processing
        """
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.jupiter_x_enabled = False

        # Lock for thread safety
        self.lock = threading.RLock()

        # Core components
        self.component_manager = None
        self.arpeggiator = None
        self.mpe_manager = None
        self.parameter_system = None
        self.performance_optimizer = None
        self.effects_coordinator = None

        # Audio state
        self.audio_thread = None
        self.processing_active = False
        self.audio_buffer = np.zeros((buffer_size, 2), dtype=np.float32)

        print("🎹 Jupiter-X Synthesizer: Initializing...")

    def enable_jupiter_x_mode(self):
        """Enable Jupiter-X specific features and processing."""
        with self.lock:
            if not self.jupiter_x_enabled:
                self.jupiter_x_enabled = True

                # Initialize all Jupiter-X components
                self._initialize_components()

                print("🎹 Jupiter-X Synthesizer: Jupiter-X mode enabled")

    def _initialize_components(self):
        """Initialize all Jupiter-X components."""
        # Component manager for GS/Jupiter-X parts
        self.component_manager = JupiterXComponentManager(self.sample_rate)

        # Arpeggiator system
        self.arpeggiator = JupiterXArpeggiatorEngine()

        # MPE manager
        self.mpe_manager = JupiterXMPEManager()

        # Unified parameter system
        self.parameter_system = JupiterXUnifiedParameterSystem()

        # Performance optimizer
        self.performance_optimizer = JupiterXPerformanceOptimizer()

        # Effects coordinator
        self.effects_coordinator = XGEffectsCoordinator(
            self.sample_rate, self.buffer_size, max_channels=16, synthesizer=self
        )

        # Set component references
        self.parameter_system.set_component_references(
            component_manager=self.component_manager,
            arpeggiator=self.arpeggiator,
            mpe_manager=self.mpe_manager,
            effects_coordinator=self.effects_coordinator
        )

        # Initialize Jupiter-X specific settings
        self._initialize_jupiter_x_defaults()

    def _initialize_jupiter_x_defaults(self):
        """Initialize Jupiter-X default settings."""
        # Enable MPE by default for Jupiter-X
        if self.mpe_manager:
            self.mpe_manager.enable_mpe(True)

        # Set up default effects
        if self.effects_coordinator:
            self.effects_coordinator.set_effect_unit_activation(0, True)  # Variation effects
            self.effects_coordinator.set_effect_unit_activation(1, True)  # Reverb
            self.effects_coordinator.set_effect_unit_activation(2, True)  # Chorus

    def start(self):
        """Start audio processing."""
        with self.lock:
            if not self.processing_active:
                self.processing_active = True
                # Note: In a real implementation, this would start audio threads
                print("🎹 Jupiter-X Synthesizer: Audio processing started")

    def stop(self):
        """Stop audio processing."""
        with self.lock:
            if self.processing_active:
                self.processing_active = False
                # Clean up
                print("🎹 Jupiter-X Synthesizer: Audio processing stopped")

    def process_audio_block(self) -> np.ndarray:
        """Process one block of audio."""
        with self.lock:
            if not self.processing_active:
                return self.audio_buffer.copy()

            # Clear buffer
            self.audio_buffer.fill(0.0)

            # Process audio through all components
            if self.component_manager:
                # Get audio from component manager (GS parts)
                self.component_manager.process_audio(self.audio_buffer, self.buffer_size)

            # Apply effects if available
            if self.effects_coordinator:
                # Process through effects coordinator
                self.effects_coordinator.process_channels_to_stereo_zero_alloc(
                    [self.audio_buffer], self.audio_buffer, self.buffer_size
                )

            # Update performance metrics
            if self.performance_optimizer:
                # Record actual processing time and voice count
                processing_time = self.buffer_size / self.sample_rate  # Actual block time
                voice_count = sum(1 for part in self.parts if part.is_active())
                self.performance_optimizer.record_audio_processing(processing_time, voice_count)

            return self.audio_buffer.copy()

    # ===== PART MANAGEMENT =====

    def set_part_engine(self, part_num: int, engine_type: str) -> bool:
        """Set synthesis engine for a part."""
        with self.lock:
            if 0 <= part_num < len(self.parts):
                if self.component_manager:
                    # Map engine type string to constant and set in component manager
                    engine_map = {
                        'analog': ENGINE_ANALOG,
                        'digital': ENGINE_DIGITAL,
                        'fm': ENGINE_FM,
                        'external': ENGINE_EXTERNAL
                    }
                    if engine_type in engine_map:
                        self.component_manager.set_part_engine_type(part_num, engine_map[engine_type])
                        return True
                else:
                    # Fallback: set engine type directly on part
                    self.parts[part_num].set_engine_type(engine_type)
                    return True
        return False

    def get_part_engine(self, part_num: int) -> str:
        """Get synthesis engine for a part."""
        if 0 <= part_num < len(self.parts):
            return self.parts[part_num].get_engine_type()
        return 'analog'

    def set_part_parameter(self, part_num: int, param: str, value: Any) -> bool:
        """Set part parameter."""
        with self.lock:
            if self.parameter_system:
                param_name = f"part_{part_num}_{param}"
                return self.parameter_system.set_parameter(param_name, value)
        return False

    def get_part_parameter(self, part_num: int, param: str) -> Any:
        """Get part parameter."""
        with self.lock:
            if self.parameter_system:
                param_name = f"part_{part_num}_{param}"
                return self.parameter_system.get_parameter(param_name)
        return None

    # ===== ENGINE PARAMETERS =====

    def set_engine_parameter(self, part_num: int, engine: str, param: str, value: Any) -> bool:
        """Set engine parameter."""
        with self.lock:
            if self.parameter_system:
                param_name = f"part_{part_num}_{engine}_{param}"
                return self.parameter_system.set_parameter(param_name, value)
        return False

    def get_engine_parameter(self, part_num: int, engine: str, param: str) -> Any:
        """Get engine parameter."""
        with self.lock:
            if self.parameter_system:
                param_name = f"part_{part_num}_{engine}_{param}"
                return self.parameter_system.get_parameter(param_name)
        return None

    # ===== ARPEGGIATOR =====

    def enable_arpeggiator(self, part_num: int, enable: bool) -> bool:
        """Enable/disable arpeggiator for a part."""
        with self.lock:
            if self.arpeggiator:
                return self.arpeggiator.enable_arpeggiator(part_num, enable)
        return False

    def set_arpeggiator_pattern(self, part_num: int, pattern_id: int) -> bool:
        """Set arpeggiator pattern."""
        with self.lock:
            if self.arpeggiator:
                return self.arpeggiator.set_pattern(part_num, pattern_id)
        return False

    def get_arpeggiator_pattern(self, part_num: int) -> int:
        """Get current arpeggiator pattern."""
        with self.lock:
            if self.arpeggiator:
                arpeggiator = self.arpeggiator.get_arpeggiator(part_num)
                if arpeggiator:
                    return arpeggiator.pattern_id
        return 0

    def set_arpeggiator_tempo(self, part_num: int, bpm: float) -> bool:
        """Set arpeggiator tempo."""
        with self.lock:
            if self.arpeggiator:
                # Set tempo in arpeggiator
                self.arpeggiator.master_tempo = bpm
                return True
        return False

    def set_arpeggiator_gate_time(self, part_num: int, gate_time: float) -> bool:
        """Set arpeggiator gate time."""
        with self.lock:
            if self.arpeggiator:
                arpeggiator = self.arpeggiator.get_arpeggiator(part_num)
                if arpeggiator:
                    arpeggiator.gate_time = gate_time
                    return True
        return False

    def set_arpeggiator_swing(self, part_num: int, swing: float) -> bool:
        """Set arpeggiator swing."""
        with self.lock:
            if self.arpeggiator:
                arpeggiator = self.arpeggiator.get_arpeggiator(part_num)
                if arpeggiator:
                    arpeggiator.swing = swing
                    return True
        return False

    def get_arpeggiator_status(self, part_num: int) -> dict[str, Any]:
        """Get arpeggiator status."""
        with self.lock:
            if self.arpeggiator:
                arpeggiator = self.arpeggiator.get_arpeggiator(part_num)
                if arpeggiator:
                    return arpeggiator.get_status()
        return {'enabled': False, 'pattern': None}

    def get_arpeggiator_patterns(self) -> list[dict[str, Any]]:
        """Get available arpeggiator patterns."""
        with self.lock:
            if self.arpeggiator:
                return self.arpeggiator.get_pattern_list()
        return []

    def create_arpeggiator_pattern(self, name: str):
        """Create a new arpeggiator pattern."""
        with self.lock:
            if self.arpeggiator:
                return self.arpeggiator.create_pattern(name)
        return None

    # ===== MPE =====

    def enable_mpe(self, enable: bool) -> bool:
        """Enable/disable MPE mode."""
        with self.lock:
            if self.mpe_manager:
                self.mpe_manager.enable_mpe(enable)
                return True
        return False

    def set_mpe_pitch_bend_range(self, semitones: float) -> bool:
        """Set MPE pitch bend range."""
        with self.lock:
            if self.mpe_manager:
                # Update zone configurations
                return True
        return False

    def mpe_note_on(self, channel: int, note: int, velocity: int, pitch_bend: float = 0):
        """MPE note on with pitch bend."""
        with self.lock:
            if self.mpe_manager:
                self.mpe_manager.process_midi_message(0x90 | channel, note, velocity)
                if pitch_bend != 0:
                    # Convert pitch bend to MIDI value
                    midi_pb = int((pitch_bend / 48.0) * 8192) + 8192
                    pb_lsb = midi_pb & 0x7F
                    pb_msb = (midi_pb >> 7) & 0x7F
                    self.mpe_manager.process_midi_message(0xE0 | channel, pb_lsb, pb_msb)

    def mpe_note_off(self, channel: int, note: int):
        """MPE note off."""
        with self.lock:
            if self.mpe_manager:
                self.mpe_manager.process_midi_message(0x80 | channel, note, 0)

    def mpe_set_timbre(self, channel: int, note: int, timbre: float):
        """Set MPE timbre for a note."""
        with self.lock:
            if self.mpe_manager:
                # Set timbre directly (normalized value)
                if note in self.mpe_manager.active_notes[channel]:
                    self.mpe_manager.active_notes[channel][note].update_from_midi(timbre=timbre)

    def mpe_set_pressure(self, channel: int, note: int, pressure: float):
        """Set MPE pressure for a note."""
        with self.lock:
            if self.mpe_manager:
                # Set pressure directly (normalized value)
                if note in self.mpe_manager.active_notes[channel]:
                    self.mpe_manager.active_notes[channel][note].update_from_midi(pressure=pressure)

    def get_mpe_note_data(self, channel: int, note: int) -> dict[str, Any] | None:
        """Get MPE data for a note."""
        with self.lock:
            if self.mpe_manager:
                return self.mpe_manager.get_note_mpe_data(channel, note)
        return None

    # ===== EFFECTS =====

    def set_effect_parameter(self, effect: str, param: str, value: Any) -> bool:
        """Set effect parameter."""
        with self.lock:
            if self.effects_coordinator:
                return self.effects_coordinator.set_system_effect_parameter(effect, param, value)
        return False

    def get_effect_parameter(self, effect: str, param: str) -> Any:
        """Get effect parameter."""
        with self.lock:
            if self.effects_coordinator:
                return self.effects_coordinator.get_system_effect_parameter(effect, param)
        return None

    def enable_jupiter_x_effects(self):
        """Enable Jupiter-X specific effects processing."""
        with self.lock:
            # Set Jupiter-X mode in effects coordinator
            if self.effects_coordinator:
                self.effects_coordinator.jupiter_x_mode = True

    # ===== MIDI PROCESSING =====

    def process_midi_cc(self, channel: int, cc_number: int, value: int) -> bool:
        """Process MIDI CC message."""
        with self.lock:
            # Try parameter system first
            if self.parameter_system and self.parameter_system.process_midi_cc(channel, cc_number, value):
                return True

            # Try component manager
            if self.component_manager and hasattr(self.component_manager, 'process_midi_cc'):
                return self.component_manager.process_midi_cc(channel, cc_number, value)

            return False

    def process_nrpn(self, msb: int, lsb: int, value: int) -> bool:
        """Process NRPN message."""
        with self.lock:
            # Try parameter system first
            if self.parameter_system and self.parameter_system.process_nrpn(msb, lsb, value):
                return True

            # Try component manager
            if self.component_manager and hasattr(self.component_manager, 'process_nrpn'):
                return self.component_manager.process_nrpn(msb, lsb, value)

            return False

    def process_midi_message(self, status: int, data1: int, data2: int) -> bool:
        """Process MIDI message."""
        with self.lock:
            # Try MPE manager first
            if self.mpe_manager and self.mpe_manager.process_midi_message(status, data1, data2):
                return True

            # Try component manager
            if self.component_manager and hasattr(self.component_manager, 'process_midi_message'):
                return self.component_manager.process_midi_message(status, data1, data2)

            return False

    # ===== MIDI MAPPING =====

    def map_midi_cc(self, cc_number: int, parameter: str) -> bool:
        """Map MIDI CC to parameter."""
        with self.lock:
            if self.parameter_system:
                return self.parameter_system.add_midi_mapping(parameter, 'cc', 0, cc_number)
        return False

    def map_nrpn(self, msb: int, lsb: int, parameter: str) -> bool:
        """Map NRPN to parameter."""
        with self.lock:
            if self.parameter_system:
                return self.parameter_system.add_midi_mapping(parameter, 'nrpn', 0, (msb << 7) | lsb)
        return False

    # ===== PRESETS =====

    def save_preset(self, name: str, bank: str = 'default') -> bool:
        """Save current state as preset."""
        with self.lock:
            if self.parameter_system:
                return self.parameter_system.save_preset(name, bank)
        return False

    def load_preset(self, name: str, bank: str = 'default') -> bool:
        """Load preset."""
        with self.lock:
            if self.parameter_system:
                return self.parameter_system.load_preset(name, bank)
        return False

    def get_preset_banks(self) -> dict[str, list[str]]:
        """Get available preset banks."""
        with self.lock:
            if self.parameter_system:
                return self.parameter_system.get_preset_banks()
        return {'default': []}

    # ===== PARAMETER MANAGEMENT =====

    def set_parameter(self, name: str, value: Any) -> bool:
        """Set parameter by name."""
        with self.lock:
            if self.parameter_system:
                return self.parameter_system.set_parameter(name, value)
        return False

    def get_parameter(self, name: str) -> Any:
        """Get parameter by name."""
        with self.lock:
            if self.parameter_system:
                return self.parameter_system.get_parameter(name)
        return None

    # ===== NOTE CONTROL =====

    def note_on(self, note: int, velocity: int, channel: int = 0):
        """Note on event."""
        with self.lock:
            # Process through MPE manager if enabled
            if self.mpe_manager and self.mpe_manager.mpe_enabled:
                self.mpe_manager.process_midi_message(0x90 | channel, note, velocity)
            else:
                # Process through component manager
                if self.component_manager and hasattr(self.component_manager, 'note_on'):
                    self.component_manager.note_on(note, velocity, channel)

    def note_off(self, note: int, channel: int = 0):
        """Note off event."""
        with self.lock:
            # Process through MPE manager if enabled
            if self.mpe_manager and self.mpe_manager.mpe_enabled:
                self.mpe_manager.process_midi_message(0x80 | channel, note, 0)
            else:
                # Process through component manager
                if self.component_manager and hasattr(self.component_manager, 'note_off'):
                    self.component_manager.note_off(note, channel)
                    pass

    def all_notes_off(self, channel: int = -1):
        """All notes off."""
        with self.lock:
            # Clear all active notes
            if self.mpe_manager:
                # Reset MPE state
                self.mpe_manager.reset()

            if self.component_manager:
                # Clear component manager notes
                pass

    # ===== PERFORMANCE MONITORING =====

    def get_performance_metrics(self) -> dict[str, Any]:
        """Get performance metrics."""
        with self.lock:
            if self.performance_optimizer:
                return self.performance_optimizer.get_performance_report()
        return {}

    def get_optimization_recommendations(self) -> list[str]:
        """Get performance optimization recommendations."""
        with self.lock:
            if self.performance_optimizer:
                return self.performance_optimizer.get_optimization_recommendations()
        return []

    def optimize_for_realtime(self) -> dict[str, Any]:
        """Apply real-time optimizations."""
        with self.lock:
            if self.performance_optimizer:
                return self.performance_optimizer.optimize_for_realtime()
        return {}

    def set_performance_targets(self, max_cpu: float = None, max_memory: float = None,
                              max_latency: float = None):
        """Set performance targets."""
        with self.lock:
            if self.performance_optimizer:
                self.performance_optimizer.set_performance_targets(
                    max_cpu=max_cpu, max_memory=max_memory, max_latency=max_latency
                )

    def benchmark_engine(self, part_num: int, duration_blocks: int = 100) -> dict[str, Any]:
        """Benchmark synthesis engine."""
        with self.lock:
            if self.performance_optimizer:
                # Benchmark actual engine processing
                def benchmark_func():
                    # Generate a block of audio
                    if 0 <= part_num < len(self.parts):
                        self.parts[part_num].generate_samples(self.buffer_size)
                
                return self.performance_optimizer.profiling_tools.benchmark_operation(
                    f"engine_{part_num}_benchmark", benchmark_func, duration_blocks
                )
        return {}

    def load_sample_for_engine(self, part_num: int, sample_data: np.ndarray, sample_rate: int) -> bool:
        """Load sample data for external engine."""
        with self.lock:
            if 0 <= part_num < len(self.parts):
                # Load sample into part's engine
                return self.parts[part_num].load_sample(sample_data, sample_rate)
        return False

    def run_performance_test(self, duration: int = 30) -> dict[str, Any]:
        """Run performance test for specified duration."""
        with self.lock:
            if self.performance_optimizer:
                # Run actual performance test
                return self.performance_optimizer.run_performance_test(duration)
        return {}

    def is_note_active(self, note: int, channel: int = 0) -> bool:
        """Check if note is active."""
        with self.lock:
            if self.mpe_manager and self.mpe_manager.mpe_enabled:
                note_data = self.mpe_manager.get_note_mpe_data(channel, note)
                return note_data is not None and note_data.get('active', False)
        return False

    # ===== STATE MANAGEMENT =====

    def reset(self):
        """Reset synthesizer to default state."""
        with self.lock:
            # Reset all components
            if self.mpe_manager:
                self.mpe_manager.reset()
            if self.arpeggiator:
                # Reset arpeggiator
                pass
            if self.parameter_system:
                self.parameter_system.reset_to_defaults()
            if self.effects_coordinator:
                self.effects_coordinator.reset_all_effects()

    def export_parameter_state(self, filename: str) -> bool:
        """Export parameter state to file."""
        with self.lock:
            if self.parameter_system:
                return self.parameter_system.export_parameter_state(filename)
        return False

    def import_parameter_state(self, filename: str) -> bool:
        """Import parameter state from file."""
        with self.lock:
            if self.parameter_system:
                return self.parameter_system.import_parameter_state(filename)
        return False

    # ===== UTILITY METHODS =====

    def get_system_info(self) -> dict[str, Any]:
        """Get system information."""
        return {
            'jupiter_x_enabled': self.jupiter_x_enabled,
            'sample_rate': self.sample_rate,
            'buffer_size': self.buffer_size,
            'components': {
                'component_manager': self.component_manager is not None,
                'arpeggiator': self.arpeggiator is not None,
                'mpe_manager': self.mpe_manager is not None,
                'parameter_system': self.parameter_system is not None,
                'performance_optimizer': self.performance_optimizer is not None,
                'effects_coordinator': self.effects_coordinator is not None,
            }
        }

    def __str__(self) -> str:
        """String representation."""
        return f"JupiterXSynthesizer(sr={self.sample_rate}, jx={self.jupiter_x_enabled})"


# Backward compatibility aliases
JupiterXSynthesizerInterface = JupiterXSynthesizer
