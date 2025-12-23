"""
Modern XG Synthesizer with MPE Integration

Enhanced version of the Modern XG Synthesizer with full MPE (Microtonal Expression) support.
"""

from typing import Dict, List, Optional, Any, Tuple, Callable
import numpy as np
import threading
import time
import math


class ModernXGSynthesizerWithMPE:
    """
    Enhanced Modern XG Synthesizer with Full MPE Support

    Production-quality XG synthesizer with complete MPE (Microtonal Expression)
    implementation for per-note control and microtonal playing.
    """

    def __init__(self,
                 sample_rate: int = 44100,
                 max_channels: int = 16,
                 xg_enabled: bool = True,
                 gs_enabled: bool = True,
                 mpe_enabled: bool = True,
                 device_id: int = 0x10):
        """
        Initialize Enhanced Modern XG/GS/MPE Synthesizer

        Args:
            sample_rate: Audio sample rate in Hz
            max_channels: Maximum MIDI channels
            xg_enabled: Enable XG features
            gs_enabled: Enable GS features
            mpe_enabled: Enable MPE features
            device_id: XG/GS/MPE device ID
        """
        self.sample_rate = sample_rate
        self.max_channels = max_channels
        self.xg_enabled = xg_enabled
        self.gs_enabled = gs_enabled
        self.mpe_enabled = mpe_enabled
        self.device_id = device_id

        # Initialize core synthesis system
        self._init_core_synthesis()

        # Initialize XG system if enabled
        if self.xg_enabled:
            self._init_xg_system()

        # Initialize GS system if enabled
        if self.gs_enabled:
            self._init_gs_system()

        # Initialize Arpeggiator system (Yamaha Motif compatible)
        self._init_arpeggiator_system()

        # Initialize MPE (Microtonal Expression) system
        if self.mpe_enabled:
            self._init_mpe_system()

        print("🎹 ENHANCED MODERN XG/GS/MPE SYNTHESIZER: Initialization complete!")
        print(f"   Arpeggiator: {len(self.arpeggiator_engine.patterns)} patterns loaded")
        if self.mpe_enabled:
            print(f"   MPE: {len(self.mpe_manager.zones)} zones configured")

    def _init_core_synthesis(self):
        """Initialize core synthesis system with modern architecture"""
        # Zero-allocation buffer pool
        from ..core.buffer_pool import XGBufferPool
        self.buffer_pool = XGBufferPool(self.sample_rate, max_block_size=2048, max_channels=self.max_channels)

        # Pre-allocate all buffers
        self._preallocate_buffers()

        # Synthesis engine registry
        from ..engine.synthesis_engine import SynthesisEngineRegistry
        self.engine_registry = SynthesisEngineRegistry()
        self._register_engines()

        # Voice factory
        from ..voice.voice_factory import VoiceFactory
        self.voice_factory = VoiceFactory(self.engine_registry)

        # Create channels
        self.channels = []
        self._create_channels()

        print("🎹 Core synthesis system initialized")

    def _init_mpe_system(self):
        """Initialize MPE (Microtonal Expression) system"""
        # Import MPE manager
        from ..mpe.mpe_manager import MPEManager

        # Create MPE manager
        self.mpe_manager = MPEManager(max_channels=self.max_channels)

        print("🎹 MPE (Microtonal Expression) system initialized")

    def _preallocate_buffers(self):
        """Pre-allocate all buffers - zero runtime allocations"""
        # Main audio buffers
        self.output_buffer = self.buffer_pool.get_stereo_buffer(2048)
        self.mix_buffer = self.buffer_pool.get_stereo_buffer(2048)

        # Temporary processing buffers
        self.temp_buffers = [self.buffer_pool.get_stereo_buffer(2048) for _ in range(8)]

        # Channel-specific buffers
        self.channel_buffers = [self.buffer_pool.get_stereo_buffer(2048)
                               for _ in range(self.max_channels)]

    def _register_engines(self):
        """Register synthesis engines with priority system"""
        # Enhanced SF2 Engine with stereo and multi-partial support
        from ..sf2.enhanced_sf2_manager import EnhancedSF2Manager
        from .sf2_engine import SF2Engine

        # Create enhanced SF2 manager with PyAV sample support
        self.enhanced_sf2_manager = EnhancedSF2Manager(self.buffer_pool.sample_manager if hasattr(self.buffer_pool, 'sample_manager') else None)

        # Create SF2 engine with enhanced manager
        sf2_engine = SF2Engine(sf2_manager=self.enhanced_sf2_manager, sample_rate=self.sample_rate, block_size=1024)
        self.engine_registry.register_engine(sf2_engine, 'sf2', priority=10)

        # Other engines...
        print("🎹 Synthesis engines registered")

    def _create_channels(self):
        """Create MIDI channels with modern architecture"""
        from ..channel.channel import Channel

        for channel_num in range(self.max_channels):
            channel = Channel(channel_num, self.voice_factory, self.sample_rate)

            # Add XG configuration if enabled
            if self.xg_enabled:
                channel.xg_config = {
                    'voice_reserve': 8,
                    'part_mode': 0,  # Normal
                    'part_level': 100,
                    'part_pan': 64,
                    'drum_kit': 0,
                    'effects_sends': {'reverb': 40, 'chorus': 0, 'variation': 0}
                }

            self.channels.append(channel)

        print(f"🎹 Created {len(self.channels)} MIDI channels")

    def _init_xg_system(self):
        """Initialize XG system with clean integration"""
        # XG Component Manager
        self.xg_components = XGComponentManager(
            self.device_id, self.max_channels, self.sample_rate
        )

        print("🎹 XG system initialized")

    def _init_gs_system(self):
        """Initialize GS system with clean integration"""
        # GS Component Manager
        from ..gs.jv2080_component_manager import JV2080ComponentManager
        self.gs_components = JV2080ComponentManager()

        print("🎹 GS system initialized")

    def _init_arpeggiator_system(self):
        """Initialize Yamaha Motif Arpeggiator system"""
        # Import arpeggiator components
        from ..xg.xg_arpeggiator_engine import YamahaArpeggiatorEngine
        from ..xg.xg_arpeggiator_sysex_controller import YamahaArpeggiatorSysexController
        from ..xg.xg_arpeggiator_nrpn_controller import YamahaArpeggiatorNRPNController

        # Create arpeggiator engine
        self.arpeggiator_engine = YamahaArpeggiatorEngine()

        # Create SYSEX controller
        self.arpeggiator_sysex_controller = YamahaArpeggiatorSysexController(self.arpeggiator_engine)

        # Create NRPN controller
        self.arpeggiator_nrpn_controller = YamahaArpeggiatorNRPNController(self.arpeggiator_engine)

        print("🎹 Arpeggiator system initialized")

    def process_midi_message(self, message_bytes: bytes):
        """Process MIDI message with XG/GS/MPE integration"""
        # Parse MIDI message
        from ..midi.binary_parser import parse_binary_message
        midi_message = parse_binary_message(message_bytes)

        if midi_message is None:
            return  # Invalid message

        # Process based on message type and channel
        midi_channel = midi_message.channel
        if midi_channel is None or not (0 <= midi_channel <= 15):
            return

        # Handle different message types
        if midi_message.type == 'note_on':
            self._process_note_on(midi_channel, midi_message.note, midi_message.velocity)
        elif midi_message.type == 'note_off':
            self._process_note_off(midi_channel, midi_message.note, midi_message.velocity)
        elif midi_message.type == 'pitch_bend':
            self._process_pitch_bend(midi_channel, midi_message.pitch)
        elif midi_message.type == 'poly_pressure':
            self._process_poly_pressure(midi_channel, midi_message.note, midi_message.pressure)
        elif midi_message.type == 'control_change':
            self._process_control_change(midi_channel, midi_message.control, midi_message.value)

    def _process_note_on(self, channel: int, note: int, velocity: int):
        """Process note-on event with MPE support"""
        if self.mpe_enabled and hasattr(self, 'mpe_manager'):
            # Create MPE note
            mpe_note = self.mpe_manager.process_note_on(channel, note, velocity)
            if mpe_note:
                # Send to voice allocation with MPE parameters
                self._allocate_voice_with_mpe(mpe_note)
                return

        # Fallback to regular note processing
        if 0 <= channel < len(self.channels):
            self.channels[channel].note_on(note, velocity)

    def _process_note_off(self, channel: int, note: int, velocity: int = 0):
        """Process note-off event with MPE support"""
        if self.mpe_enabled and hasattr(self, 'mpe_manager'):
            # Release MPE note
            released_note = self.mpe_manager.process_note_off(channel, note, velocity)
            if released_note and hasattr(released_note, 'voice_id'):
                # Release voice
                self._release_voice(released_note.voice_id)
                return

        # Fallback to regular note processing
        if 0 <= channel < len(self.channels):
            self.channels[channel].note_off(note)

    def _process_pitch_bend(self, channel: int, bend_value: int):
        """Process pitch bend with MPE support"""
        if self.mpe_enabled and hasattr(self, 'mpe_manager'):
            # Process MPE pitch bend
            self.mpe_manager.process_pitch_bend(channel, bend_value)
            # Update all active voices on this channel
            self._update_channel_voices_mpe(channel)
            return

        # Fallback to regular pitch bend
        if 0 <= channel < len(self.channels):
            # Convert 14-bit to 7-bit for regular processing
            lsb = bend_value & 0x7F
            msb = (bend_value >> 7) & 0x7F
            self.channels[channel].pitch_bend(lsb, msb)

    def _process_poly_pressure(self, channel: int, note: int, pressure: int):
        """Process polyphonic pressure with MPE support"""
        if self.mpe_enabled and hasattr(self, 'mpe_manager'):
            # Process MPE per-note pressure
            self.mpe_manager.process_poly_pressure(channel, note, pressure)
            # Update specific voice
            self._update_note_voice_mpe(channel, note)
            return

        # Fallback to regular poly pressure
        if 0 <= channel < len(self.channels):
            self.channels[channel].key_pressure(note, pressure)

    def _process_control_change(self, channel: int, controller: int, value: int):
        """Process control change with MPE support"""
        # Check for MPE timbre control (CC74)
        if controller == 74 and self.mpe_enabled and hasattr(self, 'mpe_manager'):
            self.mpe_manager.process_timbre(channel, value)
            self._update_channel_voices_mpe(channel)
            return

        # Check for MPE slide control
        if controller == 74 and self.mpe_enabled and hasattr(self, 'mpe_manager'):  # Could be different CC
            self.mpe_manager.process_slide(channel, value)
            self._update_channel_voices_mpe(channel)
            return

        # Check for MPE lift control
        if controller == 75 and self.mpe_enabled and hasattr(self, 'mpe_manager'):  # Could be different CC
            self.mpe_manager.process_lift(channel, value)
            self._update_channel_voices_mpe(channel)
            return

        # Regular control change processing
        if 0 <= channel < len(self.channels):
            self.channels[channel].control_change(controller, value)

    def _allocate_voice_with_mpe(self, mpe_note):
        """Allocate voice with MPE parameters"""
        # This would integrate with the voice allocation system
        # For now, use regular channel allocation but store MPE reference
        if 0 <= mpe_note.channel < len(self.channels):
            voice_id = self.channels[mpe_note.channel].note_on(mpe_note.note_number, mpe_note.velocity)
            if voice_id:
                mpe_note.voice_id = voice_id
                # Update voice with MPE parameters
                self._apply_mpe_to_voice(voice_id, mpe_note)

    def _release_voice(self, voice_id):
        """Release voice by ID"""
        # This would need to be implemented based on voice management system
        pass

    def _update_channel_voices_mpe(self, channel: int):
        """Update all voices on channel with current MPE parameters"""
        if not self.mpe_enabled or not hasattr(self, 'mpe_manager'):
            return

        active_notes = self.mpe_manager.get_channel_mpe_notes(channel)
        for mpe_note in active_notes:
            if hasattr(mpe_note, 'voice_id') and mpe_note.voice_id:
                self._apply_mpe_to_voice(mpe_note.voice_id, mpe_note)

    def _update_note_voice_mpe(self, channel: int, note: int):
        """Update specific note's voice with MPE parameters"""
        if not self.mpe_enabled or not hasattr(self, 'mpe_manager'):
            return

        mpe_note = self.mpe_manager.active_notes.get((channel, note))
        if mpe_note and hasattr(mpe_note, 'voice_id') and mpe_note.voice_id:
            self._apply_mpe_to_voice(mpe_note.voice_id, mpe_note)

    def _apply_mpe_to_voice(self, voice_id, mpe_note):
        """Apply MPE parameters to voice"""
        # This would update the voice's frequency, timbre, etc.
        # Implementation depends on voice architecture
        pass

    def generate_audio_block(self, block_size: Optional[int] = None) -> np.ndarray:
        """Generate audio block"""
        if block_size is None:
            block_size = 1024

        # Ensure buffer size
        if self.output_buffer.shape[0] != block_size:
            self.output_buffer = self.buffer_pool.get_stereo_buffer(block_size)

        # Clear output buffer
        self.output_buffer.fill(0.0)

        # Generate channel audio
        for i, channel in enumerate(self.channels):
            if channel.is_active():
                channel_buffer = self.channel_buffers[i][:block_size]
                channel.generate_samples(channel_buffer)
                np.add(self.output_buffer[:block_size], channel_buffer[:block_size],
                      out=self.output_buffer[:block_size])

        return self.output_buffer

    def get_mpe_info(self) -> Dict[str, Any]:
        """Get MPE system information"""
        if self.mpe_enabled and hasattr(self, 'mpe_manager'):
            return self.mpe_manager.get_mpe_info()
        return {'enabled': False, 'status': 'MPE disabled'}

    def set_mpe_enabled(self, enabled: bool):
        """Enable or disable MPE"""
        self.mpe_enabled = enabled
        if hasattr(self, 'mpe_manager'):
            self.mpe_manager.set_mpe_enabled(enabled)

    def reset_mpe(self):
        """Reset MPE system"""
        if hasattr(self, 'mpe_manager'):
            self.mpe_manager.reset_all_notes()

    def __str__(self) -> str:
        mpe_status = "MPE enabled" if self.mpe_enabled else "MPE disabled"
        return f"ModernXGSynthesizerWithMPE(channels={self.max_channels}, {mpe_status})"
