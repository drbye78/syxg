"""
Jupiter-X Engine Integration

Provides a synthesis engine interface that integrates the Jupiter-X synthesizer
with the modern synthesizer framework, allowing Jupiter-X to be used as a
drop-in synthesis engine within the larger synthesizer architecture.
"""

from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import threading

from ..engine.synthesis_engine import SynthesisEngine
from .synthesizer import JupiterXSynthesizer
from ..core.buffer_pool import XGBufferPool


class JupiterXEngineIntegration(SynthesisEngine):
    """
    Jupiter-X Engine Integration

    Wraps the Jupiter-X synthesizer as a synthesis engine that can be
    registered with the modern synthesizer's engine registry, allowing
    Jupiter-X to be used alongside other synthesis engines.
    """

    def __init__(self, sample_rate: int = 44100, block_size: int = 1024):
        """
        Initialize Jupiter-X engine integration.

        Args:
            sample_rate: Audio sample rate in Hz
            block_size: Processing block size
        """
        super().__init__(sample_rate, block_size)

        # Initialize Jupiter-X synthesizer backend
        self.jupiter_x_synth = JupiterXSynthesizer(
            sample_rate=sample_rate,
            buffer_size=block_size
        )

        # Enable Jupiter-X mode
        self.jupiter_x_synth.enable_jupiter_x_mode()

        # Thread safety
        self.lock = threading.RLock()

        # Engine metadata
        self.name = "Jupiter-X"
        self.description = "Roland Jupiter-X synthesizer with 4-engine architecture"
        self.version = "1.0.0"

        # Capabilities
        self.capabilities = {
            'polyphony': 16,  # 16 monophonic parts
            'engines': ['analog', 'digital', 'fm', 'external'],
            'effects': True,
            'arpeggiator': True,
            'mpe': True,
            'parameters': 500,  # Approximate parameter count
        }

        print("🎹 Jupiter-X Engine: Integrated with modern synthesizer framework")

    def is_note_supported(self, note: int) -> bool:
        """Check if a note is supported by this engine."""
        # Jupiter-X supports full MIDI note range
        return 0 <= note <= 127

    def get_engine_info(self) -> Dict[str, Any]:
        """Get engine information."""
        return {
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'capabilities': self.capabilities,
            'jupiter_x_info': self.jupiter_x_synth.get_system_info(),
        }

    def create_partial(self, partial_params: Dict[str, Any], sample_rate: int):
        """Create a partial instance for this engine."""
        # Jupiter-X doesn't use the traditional partial system
        # Instead, it uses its own internal synthesis architecture
        # Return a dummy partial that delegates to Jupiter-X synthesis
        from ..partial.partial import SynthesisPartial

        class JupiterXPartial(SynthesisPartial):
            def __init__(self, engine, params, sample_rate):
                super().__init__(params, sample_rate)
                self.jupiter_x_engine = engine

            def generate_samples(self, note, velocity, modulation, block_size):
                return self.jupiter_x_engine.generate_samples(note, velocity, modulation, block_size)

            def note_on(self, velocity):
                self.jupiter_x_engine.note_on(self.note, velocity)

            def note_off(self):
                self.jupiter_x_engine.note_off(self.note)

        return JupiterXPartial(self, partial_params, sample_rate)

    def set_sample_rate(self, sample_rate: int):
        """Set sample rate (not supported - Jupiter-X must be recreated)."""
        print("⚠️  Jupiter-X Engine: Sample rate changes require engine recreation")

    def generate_samples(self, note: int, velocity: int, modulation: Dict[str, float],
                        block_size: int) -> np.ndarray:
        """
        Generate audio samples using Jupiter-X synthesis.

        Args:
            note: MIDI note number
            velocity: MIDI velocity
            modulation: Modulation parameters
            block_size: Number of samples to generate

        Returns:
            Stereo audio buffer (block_size, 2)
        """
        with self.lock:
            # Process note through Jupiter-X
            # Note: Jupiter-X uses part-based architecture, so we route to part 0 by default
            # In a full integration, this would be configurable per channel/part

            # Send note on to Jupiter-X (part 0, channel 0)
            self.jupiter_x_synth.note_on(note, velocity, channel=0)

            # Generate audio block
            audio_block = self.jupiter_x_synth.process_audio_block()

            # Send note off (for single-shot generation)
            self.jupiter_x_synth.note_off(note, channel=0)

            # Ensure correct block size (in case Jupiter-X returns different size)
            if audio_block.shape[0] != block_size:
                # Pad or truncate as needed
                if audio_block.shape[0] < block_size:
                    # Pad with zeros
                    padding = np.zeros((block_size - audio_block.shape[0], 2), dtype=audio_block.dtype)
                    audio_block = np.vstack([audio_block, padding])
                else:
                    # Truncate
                    audio_block = audio_block[:block_size]

            return audio_block

    def note_on(self, note: int, velocity: int):
        """Handle note-on event."""
        with self.lock:
            self.jupiter_x_synth.note_on(note, velocity, channel=0)

    def note_off(self, note: int):
        """Handle note-off event."""
        with self.lock:
            self.jupiter_x_synth.note_off(note, channel=0)

    def all_notes_off(self):
        """Turn off all notes."""
        with self.lock:
            self.jupiter_x_synth.all_notes_off()

    def set_parameter(self, param_name: str, value: Any) -> bool:
        """
        Set engine parameter.

        Args:
            param_name: Parameter name (supports Jupiter-X parameter mapping)
            value: Parameter value

        Returns:
            True if parameter was set successfully
        """
        with self.lock:
            # Map common parameter names to Jupiter-X parameters
            param_mapping = {
                'volume': lambda v: self.jupiter_x_synth.set_parameter('master_volume', v),
                'pan': lambda v: self.jupiter_x_synth.set_parameter('master_pan', v),
                'cutoff': lambda v: self.jupiter_x_synth.set_engine_parameter(0, 'analog', 'filter_cutoff', v),
                'resonance': lambda v: self.jupiter_x_synth.set_engine_parameter(0, 'analog', 'filter_resonance', v),
                'attack': lambda v: self.jupiter_x_synth.set_engine_parameter(0, 'analog', 'amp_attack', v),
                'decay': lambda v: self.jupiter_x_synth.set_engine_parameter(0, 'analog', 'amp_decay', v),
                'sustain': lambda v: self.jupiter_x_synth.set_engine_parameter(0, 'analog', 'amp_sustain', v),
                'release': lambda v: self.jupiter_x_synth.set_engine_parameter(0, 'analog', 'amp_release', v),
            }

            if param_name in param_mapping:
                return param_mapping[param_name](value)

            # Try direct parameter setting
            return self.jupiter_x_synth.set_parameter(param_name, value)

    def get_parameter(self, param_name: str) -> Any:
        """Get engine parameter."""
        with self.lock:
            # Try direct parameter access
            return self.jupiter_x_synth.get_parameter(param_name)

    def process_midi_cc(self, cc_number: int, value: int) -> bool:
        """Process MIDI CC message."""
        with self.lock:
            return self.jupiter_x_synth.process_midi_cc(0, cc_number, value)

    def process_pitch_bend(self, value: int):
        """Process pitch bend message."""
        with self.lock:
            # Convert 14-bit pitch bend to MIDI message format
            lsb = value & 0x7F
            msb = (value >> 7) & 0x7F
            self.jupiter_x_synth.process_midi_message(0xE0, lsb, msb)

    def process_aftertouch(self, pressure: int):
        """Process aftertouch message."""
        with self.lock:
            self.jupiter_x_synth.process_midi_message(0xD0, pressure, 0)

    def load_program(self, program_number: int, bank_msb: int = 0, bank_lsb: int = 0) -> bool:
        """
        Load program/preset.

        Args:
            program_number: Program number
            bank_msb: Bank MSB
            bank_lsb: Bank LSB

        Returns:
            True if program was loaded successfully
        """
        with self.lock:
            # Jupiter-X uses preset system
            preset_name = f"program_{program_number}"
            return self.jupiter_x_synth.load_preset(preset_name)

    def save_program(self, program_number: int, bank_msb: int = 0, bank_lsb: int = 0) -> bool:
        """Save current state as program/preset."""
        with self.lock:
            preset_name = f"program_{program_number}"
            return self.jupiter_x_synth.save_preset(preset_name)

    def get_program_info(self, program_number: int) -> Optional[Dict[str, Any]]:
        """Get program information."""
        with self.lock:
            # Jupiter-X preset system doesn't have detailed program info
            return {
                'program_number': program_number,
                'name': f"Jupiter-X Program {program_number}",
                'type': 'synthesizer',
                'engines': ['analog', 'digital', 'fm', 'external'],
            }

    def reset(self):
        """Reset engine to default state."""
        with self.lock:
            self.jupiter_x_synth.reset()

    def cleanup(self):
        """Clean up engine resources."""
        with self.lock:
            if hasattr(self.jupiter_x_synth, 'cleanup'):
                self.jupiter_x_synth.cleanup()

    # Jupiter-X specific methods
    def set_engine_type(self, part_num: int, engine_type: str) -> bool:
        """Set synthesis engine type for a part."""
        with self.lock:
            return self.jupiter_x_synth.set_part_engine(part_num, engine_type)

    def get_engine_type(self, part_num: int) -> str:
        """Get synthesis engine type for a part."""
        with self.lock:
            return self.jupiter_x_synth.get_part_engine(part_num)

    def set_jupiter_x_parameter(self, part_num: int, engine: str,
                               param: str, value: Any) -> bool:
        """Set Jupiter-X specific parameter."""
        with self.lock:
            return self.jupiter_x_synth.set_engine_parameter(part_num, engine, param, value)

    def get_jupiter_x_parameter(self, part_num: int, engine: str, param: str) -> Any:
        """Get Jupiter-X specific parameter."""
        with self.lock:
            return self.jupiter_x_synth.get_engine_parameter(part_num, engine, param)

    def enable_arpeggiator(self, part_num: int, enable: bool) -> bool:
        """Enable/disable arpeggiator for a part."""
        with self.lock:
            return self.jupiter_x_synth.enable_arpeggiator(part_num, enable)

    def set_arpeggiator_pattern(self, part_num: int, pattern_id: int) -> bool:
        """Set arpeggiator pattern."""
        with self.lock:
            return self.jupiter_x_synth.set_arpeggiator_pattern(part_num, pattern_id)

    def enable_mpe(self, enable: bool) -> bool:
        """Enable/disable MPE mode."""
        with self.lock:
            return self.jupiter_x_synth.enable_mpe(enable)

    def get_jupiter_x_status(self) -> Dict[str, Any]:
        """Get Jupiter-X system status."""
        with self.lock:
            return self.jupiter_x_synth.get_system_info()

    def __str__(self) -> str:
        """String representation."""
        return f"JupiterXEngineIntegration({self.jupiter_x_synth})"


# Factory function for easy integration
def create_jupiter_x_engine(sample_rate: int = 44100, block_size: int = 1024) -> JupiterXEngineIntegration:
    """
    Create a Jupiter-X engine integration instance.

    Args:
        sample_rate: Audio sample rate in Hz
        block_size: Processing block size

    Returns:
        Configured Jupiter-X engine integration
    """
    return JupiterXEngineIntegration(sample_rate, block_size)
