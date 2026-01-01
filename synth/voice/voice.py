"""
XG Voice implementation for synthesizer.

Provides the Voice class that coordinates multiple synthesis partials and handles
voice-level XG parameters, modulation, and audio mixing.
"""

from typing import Dict, List, Any
import numpy as np

from ..engine.synthesis_engine import SynthesisEngine
from ..partial.partial import SynthesisPartial
from ..modulation.matrix import ModulationMatrix
from ..effects.system_effects import XGSystemEffectsProcessor


class VoicePartialRegion:
    """
    Simple region wrapper for Voice partials.

    Adapts a SynthesisPartial to work as a region for VoiceInstance compatibility.
    """

    def __init__(self, partial: SynthesisPartial, note: int, velocity: int):
        self.partial = partial
        self.note = note
        self.velocity = velocity

    def generate_samples(self, block_size: int, modulation: Dict = None) -> np.ndarray:
        """Generate samples from the wrapped partial."""
        if modulation is None:
            modulation = {}

        # The partial's generate_samples method expects (block_size, modulation_dict)
        # but we need to return the audio data
        return self.partial.generate_samples(block_size, modulation)

    def note_on(self, velocity: int, note: int):
        """Handle note-on for the partial."""
        self.velocity = velocity
        self.note = note
        self.partial.note_on(velocity, note)

    def note_off(self):
        """Handle note-off for the partial."""
        self.partial.note_off()

    def is_active(self) -> bool:
        """Check if the partial is active."""
        return self.partial.is_active()


class Voice:
    """
    XG Voice - coordinates multiple partials and handles voice-level parameters.

    A Voice represents a complete instrument sound that can be assigned to
    a MIDI channel. It manages multiple synthesis partials, applies voice-level
    modulation and effects, and provides the audio output for all notes played
    with this voice.

    XG Specification Compliance:
    - Voice-level parameters (key range, master level, pan, assign mode)
    - Partial coordination and mixing
    - Voice-level modulation matrix
    - Multi-timbral operation support
    """

    def __init__(self, synthesis_engine: SynthesisEngine,
                 voice_params: Dict, channel: int, sample_rate: int):
        """
        Initialize XG Voice.

        Args:
            synthesis_engine: Engine providing synthesis implementation
            voice_params: Voice definition parameters
            channel: MIDI channel number (0-15)
            sample_rate: Audio sample rate in Hz
        """
        self.synthesis_engine = synthesis_engine
        self.channel = channel
        self.sample_rate = sample_rate

        # Voice-level XG parameters
        self.name = voice_params.get('name', 'Untitled Voice')
        self.key_range_low = voice_params.get('key_range_low', 0)
        self.key_range_high = voice_params.get('key_range_high', 127)
        self.master_level = voice_params.get('master_level', 1.0)
        self.pan = voice_params.get('pan', 0.0)
        self.assign_mode = voice_params.get('assign_mode', 1)  # Polyphonic

        # Voice state
        self.active = True
        self.partials: List[SynthesisPartial] = []

        # Create partials from voice definition
        self._create_partials(voice_params)

        # Voice-level modulation
        self.modulation_matrix = ModulationMatrix(num_routes=16)
        self._setup_voice_modulation(voice_params)

        # Voice-level effects sends (XG compliant)
        self.chorus_send = voice_params.get('chorus_send', 0.0)
        self.reverb_send = voice_params.get('reverb_send', 0.0)
        self.delay_send = voice_params.get('delay_send', 0.0)

        # Voice-level effect processors
        self._voice_effects = self._initialize_voice_effects()

    def _initialize_voice_effects(self) -> Dict[str, Any]:
        """
        Initialize voice-level effect processors.

        Returns:
            Dictionary of voice effect processors
        """
        # Create dedicated voice-level effect processors
        # These are separate from global system effects for per-voice processing
        voice_effects = {}

        try:
            # Voice-level chorus processor (scaled down for per-voice use)
            voice_effects['chorus'] = XGSystemEffectsProcessor(
                sample_rate=self.sample_rate,
                block_size=1024,
                dsp_units=None,
                max_reverb_delay=int(0.5 * self.sample_rate),  # Shorter for voice-level
                max_chorus_delay=int(0.05 * self.sample_rate)
            )

            # Configure chorus for voice-level use
            voice_effects['chorus'].set_system_effect_parameter('chorus', 'level', 0.3)

            # Voice-level reverb processor (scaled down)
            voice_effects['reverb'] = XGSystemEffectsProcessor(
                sample_rate=self.sample_rate,
                block_size=1024,
                dsp_units=None,
                max_reverb_delay=int(0.5 * self.sample_rate),  # Shorter reverb
                max_chorus_delay=int(0.05 * self.sample_rate)
            )

            # Configure reverb for voice-level use
            voice_effects['reverb'].set_system_effect_parameter('reverb', 'level', 0.2)
            voice_effects['reverb'].set_system_effect_parameter('reverb', 'time', 0.5)

        except Exception as e:
            print(f"Warning: Failed to initialize voice effects: {e}")
            # Continue without voice effects

        return voice_effects

    def _create_partials(self, voice_params: Dict) -> None:
        """
        Create synthesis partials for this voice.

        Args:
            voice_params: Voice parameters containing partial definitions
        """
        partials_config = voice_params.get('partials', [])

        # Ensure at least one partial exists
        if not partials_config:
            # Create a default partial configuration
            partials_config = [{
                'level': 1.0,
                'waveform': 'sine',
                'frequency': 440.0,
                'amplitude': 1.0
            }]

        for i, partial_config in enumerate(partials_config):
            # Only create partials with non-zero level
            if partial_config.get('level', 0.0) > 0.0:
                # Merge voice and partial parameters
                merged_params = {**voice_params, **partial_config}
                merged_params['partial_id'] = i

                # Create partial using synthesis engine
                partial = self.synthesis_engine.create_partial(merged_params, self.sample_rate)
                self.partials.append(partial)

    def _setup_voice_modulation(self, voice_params: Dict) -> None:
        """
        Set up voice-level modulation matrix.

        Args:
            voice_params: Voice parameters containing modulation settings
        """
        modulation_params = voice_params.get('modulation', {})

        # Clear existing routes
        for i in range(16):
            self.modulation_matrix.clear_route(i)

        # Set up basic XG voice modulation routes
        # These are voice-level routes that can affect all partials

        # Velocity -> Master Level
        self.modulation_matrix.set_route(
            0, "velocity", "master_level",
            amount=modulation_params.get("velocity_to_level", 0.0),
            polarity=1.0
        )

        # Aftertouch -> Pan
        self.modulation_matrix.set_route(
            1, "after_touch", "pan",
            amount=modulation_params.get("aftertouch_to_pan", 0.0),
            polarity=1.0
        )

        # Mod Wheel -> Chorus Send
        self.modulation_matrix.set_route(
            2, "mod_wheel", "chorus_send",
            amount=modulation_params.get("modwheel_to_chorus", 0.0),
            polarity=1.0
        )

        # Breath Controller -> Reverb Send
        self.modulation_matrix.set_route(
            3, "breath_controller", "reverb_send",
            amount=modulation_params.get("breath_to_reverb", 0.0),
            polarity=1.0
        )

    def is_note_supported(self, note: int) -> bool:
        """
        Check if this voice responds to the given note.

        Args:
            note: MIDI note number (0-127)

        Returns:
            True if voice can play this note
        """
        return self.key_range_low <= note <= self.key_range_high

    def get_regions_for_note(self, note: int, velocity: int) -> List[Any]:
        """
        Get regions for a specific note and velocity.

        Creates regions from partials for compatibility with VoiceInstance system.

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)

        Returns:
            List of regions (one per partial)
        """
        if not self.is_note_supported(note):
            return []

        regions = []
        for partial in self.partials:
            # Create a simple region wrapper for each partial
            region = VoicePartialRegion(partial, note, velocity)
            regions.append(region)

        return regions

    def generate_samples(self, note: int, velocity: int,
                        modulation: Dict, block_size: int) -> np.ndarray:
        """
        Generate voice audio for a note.

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)
            modulation: Current modulation values
            block_size: Number of samples to generate

        Returns:
            Stereo audio buffer (block_size * 2,)
        """
        if not self.active or not self.partials:
            return np.zeros(block_size * 2, dtype=np.float32)

        # Process voice-level modulation
        voice_modulation = self._process_voice_modulation(modulation, velocity, note)

        # Generate samples from all partials
        output = np.zeros(block_size * 2, dtype=np.float32)
        active_partials = 0

        for partial in self.partials:
            if partial.is_active():
                # Apply voice modulation to partial modulation
                partial_mod = {**voice_modulation, **modulation}

                # Generate partial samples - each partial should use the same note/velocity
                # since they are all part of the same voice playing the same note
                partial_samples = partial.generate_samples(block_size, partial_mod)

                # Mix partial into voice output
                output += partial_samples
                active_partials += 1

        # Apply voice-level processing
        if active_partials > 0:
            output = self._apply_voice_processing(output, block_size, voice_modulation)

        return output

    def _process_voice_modulation(self, modulation: Dict, velocity: int, note: int) -> Dict:
        """
        Process voice-level modulation matrix.

        Args:
            modulation: Incoming modulation values
            velocity: Current note velocity
            note: Current note number

        Returns:
            Processed modulation values
        """
        # Prepare modulation sources
        sources = {
            "velocity": velocity / 127.0,
            "note_number": note / 127.0,
            **modulation
        }

        # Process through modulation matrix
        processed_modulation = self.modulation_matrix.process(sources, velocity, note)

        # Apply voice-level parameter modulation
        if "master_level" in processed_modulation:
            self.master_level = processed_modulation["master_level"]

        if "pan" in processed_modulation:
            self.pan = processed_modulation["pan"]

        if "chorus_send" in processed_modulation:
            self.chorus_send = processed_modulation["chorus_send"]

        if "reverb_send" in processed_modulation:
            self.reverb_send = processed_modulation["reverb_send"]

        return processed_modulation

    def _apply_voice_processing(self, audio: np.ndarray, block_size: int,
                               modulation: Dict) -> np.ndarray:
        """
        Apply voice-level audio processing.

        Args:
            audio: Input audio buffer
            block_size: Number of samples
            modulation: Current modulation values

        Returns:
            Processed audio buffer
        """
        # Apply master level
        audio *= self.master_level

        # Apply pan (simplified - could be enhanced with pan law)
        if self.pan != 0.0:
            pan_left = 1.0 - max(0.0, self.pan)  # pan > 0 reduces left
            pan_right = 1.0 - max(0.0, -self.pan)  # pan < 0 reduces right
            audio[0::2] *= pan_left   # Left channel
            audio[1::2] *= pan_right  # Right channel

        # Apply voice-level effects based on send levels
        processed_audio = audio.copy()

        # Apply chorus send
        if self.chorus_send > 0.0 and 'chorus' in self._voice_effects:
            try:
                # Create wet/dry mix based on send level
                dry_level = 1.0 - self.chorus_send
                wet_level = self.chorus_send

                # Apply chorus effect
                chorus_wet = processed_audio.copy()
                self._voice_effects['chorus'].apply_system_effects_to_mix_zero_alloc(
                    chorus_wet, block_size
                )

                # Mix dry and wet signals
                processed_audio = (processed_audio * dry_level +
                                 chorus_wet * wet_level)

            except Exception as e:
                print(f"Warning: Voice chorus processing failed: {e}")

        # Apply reverb send
        if self.reverb_send > 0.0 and 'reverb' in self._voice_effects:
            try:
                # Create wet/dry mix based on send level
                dry_level = 1.0 - self.reverb_send
                wet_level = self.reverb_send

                # Apply reverb effect
                reverb_wet = processed_audio.copy()
                self._voice_effects['reverb'].apply_system_effects_to_mix_zero_alloc(
                    reverb_wet, block_size
                )

                # Mix dry and wet signals
                processed_audio = (processed_audio * dry_level +
                                 reverb_wet * wet_level)

            except Exception as e:
                print(f"Warning: Voice reverb processing failed: {e}")

        # Note: Delay send could be implemented similarly if a delay processor is added

        return processed_audio

    def note_on(self, note: int, velocity: int) -> None:
        """
        Handle note-on event for this voice.

        Args:
            note: MIDI note number
            velocity: MIDI velocity
        """
        for partial in self.partials:
            partial.note_on(velocity, note)

    def note_off(self, note: int) -> None:
        """
        Handle note-off event for this voice.

        Args:
            note: MIDI note number
        """
        for partial in self.partials:
            partial.note_off()

    def is_active(self) -> bool:
        """
        Check if voice is still active.

        Returns:
            True if any partial is still producing sound
        """
        return self.active and any(partial.is_active() for partial in self.partials)

    def get_voice_info(self) -> Dict[str, Any]:
        """
        Get voice information and status.

        Returns:
            Dictionary with voice metadata
        """
        return {
            'name': self.name,
            'channel': self.channel,
            'key_range': (self.key_range_low, self.key_range_high),
            'master_level': self.master_level,
            'pan': self.pan,
            'assign_mode': self.assign_mode,
            'active': self.is_active(),
            'num_partials': len(self.partials),
            'active_partials': sum(1 for p in self.partials if p.is_active()),
            'engine_type': self.synthesis_engine.get_engine_type(),
            'effects_sends': {
                'chorus': self.chorus_send,
                'reverb': self.reverb_send,
                'delay': self.delay_send
            }
        }

    def update_parameter(self, param_name: str, value: Any) -> None:
        """
        Update a voice parameter.

        Args:
            param_name: Parameter name
            value: New parameter value
        """
        if hasattr(self, param_name):
            setattr(self, param_name, value)
        else:
            # Try to update in voice parameters
            # This allows dynamic parameter updates
            pass

    def apply_global_parameters(self, global_params: Dict) -> None:
        """
        Apply global synthesizer parameters to this voice.

        Args:
            global_params: Global synthesizer parameters
        """
        # Apply global parameters to voice-level settings
        if 'master_volume' in global_params:
            master_volume = global_params['master_volume']
            self.master_level *= master_volume

        if 'master_tune' in global_params:
            # This would affect pitch, but voice-level tuning is usually handled per-partial
            pass

        if 'master_transpose' in global_params:
            # This would affect transposition, but usually handled per-partial
            pass

        # Apply global parameters to all partials
        for partial in self.partials:
            if hasattr(partial, 'apply_global_parameters'):
                partial.apply_global_parameters(global_params)

    def apply_channel_parameters(self, channel_params: Dict) -> None:
        """
        Apply XG channel parameters to this voice.

        Args:
            channel_params: XG channel parameters
        """
        # Apply channel parameters to voice-level settings
        if 'part_level' in channel_params:
            part_level = channel_params['part_level'] / 100.0  # Convert from 0-100 to 0.0-1.0
            self.master_level *= part_level

        if 'part_pan' in channel_params:
            # XG pan is -64 to +63, convert to -1.0 to +1.0
            xg_pan = channel_params['part_pan']
            self.pan = xg_pan / 63.0  # Normalize to -1.0 to +1.0

        if 'effects_sends' in channel_params:
            channel_sends = channel_params['effects_sends']
            self.reverb_send = channel_sends.get('reverb', 40) / 127.0
            self.chorus_send = channel_sends.get('chorus', 0) / 127.0
            # Note: delay_send not used in current implementation

        if 'drum_kit' in channel_params:
            # Store drum kit info for drum channel (channel 9)
            self._drum_kit = channel_params['drum_kit']

        # Apply channel parameters to all partials
        for partial in self.partials:
            if hasattr(partial, 'apply_channel_parameters'):
                partial.apply_channel_parameters(channel_params)

    def reset(self) -> None:
        """Reset voice to initial state."""
        self.active = True
        for partial in self.partials:
            partial.reset()
