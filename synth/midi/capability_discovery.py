"""
MIDI 2.0 Capability Discovery System

Advanced system for discovering and negotiating device capabilities in MIDI 2.0 environments.
Implements comprehensive device interrogation and capability reporting with profile negotiation.
"""
from __future__ import annotations

from typing import Any
import struct
import json
from enum import IntEnum


class CapabilityType(IntEnum):
    """Types of capabilities that can be discovered"""
    MIDI_VERSION = 0x01
    MAX_CHANNELS = 0x02
    MAX_POLYPHONY = 0x03
    PARAMETER_RESOLUTION = 0x04
    PER_NOTE_CONTROLLERS = 0x05
    MPE_SUPPORT = 0x06
    SYSEX_7_SUPPORT = 0x07
    PROPERTY_EXCHANGE = 0x08
    PROFILE_CONFIG = 0x09
    UMP_STREAMS = 0x0A
    JITTER_REDUCTION = 0x0B
    MIXED_DATA_SETS = 0x0C
    SUPPORTED_MESSAGES = 0x0D
    EFFECTS_CAPABILITIES = 0x0E
    VOICE_ARCHITECTURE = 0x0F
    SAMPLE_LIBRARY = 0x10
    MAX_SIMULTANEOUS_PROFILES = 0x11
    DYNAMIC_PROFILE_SWITCHING = 0x12
    PROFILE_INHERITANCE = 0x13
    PROFILE_SPECIFIC_PARAMS = 0x14
    MIDI_CI_SUPPORT = 0x15
    MIDI_MCN_SUPPORT = 0x16
    MIDI_PROPRIETARY_SUPPORT = 0x17
    MPE_PLUS_SUPPORT = 0x18
    PER_NOTE_EXPRESSIONS = 0x19
    PER_NOTE_MODULATION = 0x1A
    PER_NOTE_PITCH_BEND = 0x1B
    PER_NOTE_TUNING = 0x1C
    PER_NOTE_MANAGEMENT = 0x1D
    PER_NOTE_HARMONIC_CONTENT = 0x1E
    PER_NOTE_BRIGHTNESS = 0x1F
    PER_NOTE_TIMBRE = 0x20
    PER_NOTE_PAN = 0x21
    PER_NOTE_REVERB_SEND = 0x22
    PER_NOTE_CHORUS_SEND = 0x23
    PER_NOTE_VARIATION_SEND = 0x24
    PER_NOTE_TREMOLO = 0x25
    PER_NOTE_VIBRATO = 0x26
    PER_NOTE_PHASING = 0x27
    PER_NOTE_FLANGING = 0x28
    PER_NOTE_FILTER_CUTOFF = 0x29
    PER_NOTE_FILTER_RESONANCE = 0x2A
    PER_NOTE_ATTACK_TIME = 0x2B
    PER_NOTE_DECAY_TIME = 0x2C
    PER_NOTE_RELEASE_TIME = 0x2D
    PER_NOTE_SUSTAIN_LEVEL = 0x2E
    PER_NOTE_AMPLITUDE = 0x2F
    PER_NOTE_FREQUENCY = 0x30
    PER_NOTE_WAVEFORM = 0x31
    PER_NOTE_ENVELOPE_SHAPE = 0x32
    PER_NOTE_LFO_RATE = 0x33
    PER_NOTE_LFO_DEPTH = 0x34
    PER_NOTE_LFO_SHAPE = 0x35
    PER_NOTE_LFO_PHASE = 0x36
    PER_NOTE_EG_BIAS = 0x37
    PER_NOTE_EG_DEPTH = 0x38
    PER_NOTE_EG_SHAPE = 0x39
    PER_NOTE_EG_TIME = 0x3A
    PER_NOTE_EG_LEVEL = 0x3B
    PER_NOTE_EG_RATE = 0x3C
    PER_NOTE_EG_ATTACK = 0x3D
    PER_NOTE_EG_DECAY = 0x3E
    PER_NOTE_EG_SUSTAIN = 0x3F
    PER_NOTE_EG_RELEASE = 0x40
    PER_NOTE_EG_HOLD = 0x41
    PER_NOTE_EG_DELAY = 0x42
    PER_NOTE_EG_START = 0x43
    PER_NOTE_EG_PEAK = 0x44
    PER_NOTE_EG_INITIAL = 0x45
    PER_NOTE_EG_FINAL = 0x46
    PER_NOTE_EG_OFFSET = 0x47
    PER_NOTE_EG_INVERT = 0x48
    PER_NOTE_EG_LOOP = 0x49
    PER_NOTE_EG_CYCLE = 0x4A
    PER_NOTE_EG_STEP = 0x4B
    PER_NOTE_EG_SMOOTH = 0x4C
    PER_NOTE_EG_RANDOM = 0x4D
    PER_NOTE_EG_SHUFFLE = 0x4E
    PER_NOTE_EG_SYNC = 0x4F
    PER_NOTE_EG_RESET = 0x50
    PER_NOTE_EG_REPEAT = 0x51
    PER_NOTE_EG_SKIP = 0x52
    PER_NOTE_EG_JUMP = 0x53
    PER_NOTE_EG_TURN = 0x54
    PER_NOTE_EG_GLISSANDO = 0x55
    PER_NOTE_EG_PORTAMENTO = 0x56
    PER_NOTE_EG_SLIDE = 0x57
    PER_NOTE_EG_BEND = 0x58
    PER_NOTE_EG_VIBRATO = 0x59
    PER_NOTE_EG_TREMOLO = 0x5A
    PER_NOTE_EG_AUTO_PAN = 0x5B
    PER_NOTE_EG_ROTARY = 0x5C
    PER_NOTE_EG_WAH = 0x5D
    PER_NOTE_EG_FILTER = 0x5E
    PER_NOTE_EG_DISTORTION = 0x5F
    PER_NOTE_EG_OVERDRIVE = 0x60
    PER_NOTE_EG_COMPRESSION = 0x61
    PER_NOTE_EG_GATE = 0x62
    PER_NOTE_EG_EXPANDER = 0x63
    PER_NOTE_EG_EXCITER = 0x64
    PER_NOTE_EG_ENHANCER = 0x65
    PER_NOTE_EG_IMAGER = 0x66
    PER_NOTE_EG_REVERB = 0x67
    PER_NOTE_EG_CHORUS = 0x68
    PER_NOTE_EG_DELAY = 0x69
    PER_NOTE_EG_ECHO = 0x6A
    PER_NOTE_EG_FLANGER = 0x6B
    PER_NOTE_EG_PHASER = 0x6C
    PER_NOTE_EG_PITCH_SHIFT = 0x6D
    PER_NOTE_EG_FORMANT = 0x6E
    PER_NOTE_EG_VOCODER = 0x6F
    PER_NOTE_EG_RING_MOD = 0x70
    PER_NOTE_EG_TALK_MOD = 0x71
    PER_NOTE_EG_AUTO_WAH = 0x72
    PER_NOTE_EG_AUTO_FILTER = 0x73
    PER_NOTE_EG_AUTO_PAN = 0x74
    PER_NOTE_EG_AUTO_ROTARY = 0x75
    PER_NOTE_EG_AUTO_TREMOLO = 0x76
    PER_NOTE_EG_AUTO_VIBRATO = 0x77
    PER_NOTE_EG_AUTO_WOBBLE = 0x78
    PER_NOTE_EG_AUTO_SHIMMER = 0x79
    PER_NOTE_EG_AUTO_SWELL = 0x7A
    PER_NOTE_EG_AUTO_HARMONIZER = 0x7B
    PER_NOTE_EG_AUTO_PITCH_SHIFT = 0x7C
    PER_NOTE_EG_AUTO_FORMANT = 0x7D
    PER_NOTE_EG_AUTO_VOCODER = 0x7E
    PER_NOTE_EG_AUTO_RING_MOD = 0x7F
    PER_NOTE_EG_AUTO_TALK_MOD = 0x80
    PER_NOTE_EG_AUTO_EXCITER = 0x81
    PER_NOTE_EG_AUTO_ENHANCER = 0x82
    PER_NOTE_EG_AUTO_IMAGER = 0x83
    PER_NOTE_EG_AUTO_REVERB = 0x84
    PER_NOTE_EG_AUTO_CHORUS = 0x85
    PER_NOTE_EG_AUTO_DELAY = 0x86
    PER_NOTE_EG_AUTO_ECHO = 0x87
    PER_NOTE_EG_AUTO_FLANGER = 0x88
    PER_NOTE_EG_AUTO_PHASER = 0x89
    PER_NOTE_EG_AUTO_PITCH_SHIFT = 0x8A
    PER_NOTE_EG_AUTO_FORMANT = 0x8B
    PER_NOTE_EG_AUTO_VOCODER = 0x8C
    PER_NOTE_EG_AUTO_RING_MOD = 0x8D
    PER_NOTE_EG_AUTO_TALK_MOD = 0x8E
    PER_NOTE_EG_AUTO_EXCITER = 0x8F
    PER_NOTE_EG_AUTO_ENHANCER = 0x90
    PER_NOTE_EG_AUTO_IMAGER = 0x91


class CapabilityDiscoverySystem:
    """
    MIDI 2.0 Capability Discovery System
    
    Discovers and reports device capabilities with comprehensive interrogation
    and profile negotiation functionality.
    """
    
    def __init__(self):
        """Initialize the capability discovery system."""
        self.device_capabilities: dict[str, dict[CapabilityType, Any]] = {}
        self.profile_negotiation_enabled = True
        self.property_exchange_enabled = True
        self.discovery_callbacks: list[callable] = []
        self.device_identifiers: set[str] = set()
        
        # Initialize with default capabilities for common device types
        self._initialize_default_capabilities()
    
    def _initialize_default_capabilities(self):
        """Initialize default capabilities for common device types."""
        # Default capabilities for a typical XG-compatible device
        xg_caps = {
            CapabilityType.MIDI_VERSION: 2.0,
            CapabilityType.MAX_CHANNELS: 32,  # Extended XG channels
            CapabilityType.MAX_POLYPHONY: 128,
            CapabilityType.PARAMETER_RESOLUTION: 32,  # 32-bit resolution
            CapabilityType.PER_NOTE_CONTROLLERS: True,
            CapabilityType.MPE_SUPPORT: True,
            CapabilityType.SYSEX_7_SUPPORT: True,
            CapabilityType.PROPERTY_EXCHANGE: True,
            CapabilityType.PROFILE_CONFIG: True,
            CapabilityType.UMP_STREAMS: 4,
            CapabilityType.JITTER_REDUCTION: True,
            CapabilityType.MIXED_DATA_SETS: True,
            CapabilityType.SUPPORTED_MESSAGES: {
                'note_on', 'note_off', 'control_change', 'program_change',
                'pitch_bend', 'channel_pressure', 'poly_pressure', 'sysex',
                'per_note_controller', 'per_note_pitch_bend', 'per_note_management',
                'per_note_tuning', 'per_note_expression', 'per_note_modulation',
                'ump_stream', 'property_exchange', 'profile_configuration'
            },
            CapabilityType.EFFECTS_CAPABILITIES: {
                'reverb_units': 4,
                'chorus_units': 2,
                'delay_units': 8,
                'distortion_units': 2,
                'filter_units': 16,
                'modulation_units': 12,
                'dynamics_units': 8,
                'eq_units': 6
            },
            CapabilityType.VOICE_ARCHITECTURE: {
                'voice_engine_types': ['xg', 'an', 'fdsp', 'sf2'],
                'max_voices': 128,
                'voice_stealing_enabled': True,
                'voice_priority_system': True
            },
            CapabilityType.SAMPLE_LIBRARY: {
                'has_internal_samples': True,
                'max_sample_memory_mb': 512,
                'supports_sf2': True,
                'supports_sfz': True,
                'sample_formats': ['wav', 'aiff', 'sf2', 'sfz']
            },
            CapabilityType.MAX_SIMULTANEOUS_PROFILES: 4,
            CapabilityType.DYNAMIC_PROFILE_SWITCHING: True,
            CapabilityType.PROFILE_INHERITANCE: True,
            CapabilityType.PROFILE_SPECIFIC_PARAMS: True,
            CapabilityType.MIDI_CI_SUPPORT: True,
            CapabilityType.MPE_PLUS_SUPPORT: True,
            CapabilityType.PER_NOTE_EXPRESSIONS: True,
            CapabilityType.PER_NOTE_MODULATION: True,
            CapabilityType.PER_NOTE_PITCH_BEND: True,
            CapabilityType.PER_NOTE_TUNING: True,
            CapabilityType.PER_NOTE_MANAGEMENT: True,
        }
        
        self.device_capabilities['default_xg_device'] = xg_caps
        
        # Default capabilities for a typical GM device
        gm_caps = {
            CapabilityType.MIDI_VERSION: 1.0,
            CapabilityType.MAX_CHANNELS: 16,
            CapabilityType.MAX_POLYPHONY: 64,
            CapabilityType.PARAMETER_RESOLUTION: 7,  # 7-bit resolution
            CapabilityType.PER_NOTE_CONTROLLERS: False,
            CapabilityType.MPE_SUPPORT: False,
            CapabilityType.SYSEX_7_SUPPORT: False,
            CapabilityType.PROPERTY_EXCHANGE: False,
            CapabilityType.PROFILE_CONFIG: False,
            CapabilityType.UMP_STREAMS: 1,
            CapabilityType.JITTER_REDUCTION: False,
            CapabilityType.MIXED_DATA_SETS: False,
            CapabilityType.SUPPORTED_MESSAGES: {
                'note_on', 'note_off', 'control_change', 'program_change',
                'pitch_bend', 'channel_pressure', 'poly_pressure'
            },
            CapabilityType.EFFECTS_CAPABILITIES: {
                'reverb_units': 1,
                'chorus_units': 1,
                'delay_units': 0,
                'distortion_units': 0
            },
            CapabilityType.VOICE_ARCHITECTURE: {
                'voice_engine_types': ['gm'],
                'max_voices': 64,
                'voice_stealing_enabled': True,
                'voice_priority_system': False
            },
            CapabilityType.SAMPLE_LIBRARY: {
                'has_internal_samples': True,
                'max_sample_memory_mb': 16,
                'supports_sf2': False,
                'supports_sfz': False,
                'sample_formats': ['wav', 'aiff']
            },
            CapabilityType.MAX_SIMULTANEOUS_PROFILES: 1,
            CapabilityType.DYNAMIC_PROFILE_SWITCHING: False,
            CapabilityType.PROFILE_INHERITANCE: False,
            CapabilityType.PROFILE_SPECIFIC_PARAMS: False,
            CapabilityType.MIDI_CI_SUPPORT: False,
            CapabilityType.MPE_PLUS_SUPPORT: False,
            CapabilityType.PER_NOTE_EXPRESSIONS: False,
        }
        
        self.device_capabilities['default_gm_device'] = gm_caps
    
    def discover_device_capabilities(self, device_id: str, device_type: str = 'auto') -> dict[CapabilityType, Any]:
        """
        Discover capabilities of a MIDI device.

        Args:
            device_id: Unique identifier for the device
            device_type: Type of device ('xg', 'gm', 'gs', 'mpe', 'auto')

        Returns:
            Dictionary of discovered capabilities
        """
        if device_id in self.device_capabilities:
            # Return cached capabilities
            return self.device_capabilities[device_id]
        
        # Determine device type if auto-detect
        if device_type == 'auto':
            device_type = self._detect_device_type(device_id)
        
        # Create capabilities based on device type
        if device_type == 'xg':
            capabilities = self._create_xg_capabilities()
        elif device_type == 'gm':
            capabilities = self._create_gm_capabilities()
        elif device_type == 'gs':
            capabilities = self._create_gs_capabilities()
        elif device_type == 'mpe':
            capabilities = self._create_mpe_capabilities()
        else:
            # Default to XG capabilities
            capabilities = self._create_xg_capabilities()
        
        # Cache the capabilities
        self.device_capabilities[device_id] = capabilities
        self.device_identifiers.add(device_id)
        
        # Notify callbacks
        for callback in self.discovery_callbacks:
            try:
                callback(device_id, capabilities)
            except Exception:
                pass  # Continue with other callbacks
        
        return capabilities
    
    def _detect_device_type(self, device_id: str) -> str:
        """
        Auto-detect device type based on device ID or connection properties.

        Args:
            device_id: Device identifier

        Returns:
            Detected device type
        """
        # In a real implementation, this would query the device for its identity
        # For now, we'll use a simple heuristic based on the device ID
        device_lower = device_id.lower()
        
        if 'xg' in device_lower or 'yamaha' in device_lower:
            return 'xg'
        elif 'gm' in device_lower or 'general' in device_lower:
            return 'gm'
        elif 'gs' in device_lower or 'roland' in device_lower:
            return 'gs'
        elif 'mpe' in device_lower:
            return 'mpe'
        else:
            # Default to XG for modern implementations
            return 'xg'
    
    def _create_xg_capabilities(self) -> dict[CapabilityType, Any]:
        """Create XG-specific capabilities."""
        return {
            CapabilityType.MIDI_VERSION: 2.0,
            CapabilityType.MAX_CHANNELS: 32,
            CapabilityType.MAX_POLYPHONY: 256,
            CapabilityType.PARAMETER_RESOLUTION: 32,
            CapabilityType.PER_NOTE_CONTROLLERS: True,
            CapabilityType.MPE_SUPPORT: True,
            CapabilityType.SYSEX_7_SUPPORT: True,
            CapabilityType.PROPERTY_EXCHANGE: True,
            CapabilityType.PROFILE_CONFIG: True,
            CapabilityType.UMP_STREAMS: 8,
            CapabilityType.JITTER_REDUCTION: True,
            CapabilityType.MIXED_DATA_SETS: True,
            CapabilityType.SUPPORTED_MESSAGES: {
                'note_on', 'note_off', 'control_change', 'program_change',
                'pitch_bend', 'channel_pressure', 'poly_pressure', 'sysex',
                'per_note_controller', 'per_note_pitch_bend', 'per_note_management',
                'per_note_tuning', 'per_note_expression', 'per_note_modulation',
                'ump_stream', 'property_exchange', 'profile_configuration',
                'xg_parameter_change', 'xg_bulk_dump', 'xg_data_set'
            },
            CapabilityType.EFFECTS_CAPABILITIES: {
                'reverb_units': 8,
                'chorus_units': 4,
                'delay_units': 16,
                'distortion_units': 4,
                'filter_units': 32,
                'modulation_units': 24,
                'dynamics_units': 16,
                'eq_units': 12,
                'insertion_effects': 8,
                'system_effects': 4
            },
            CapabilityType.VOICE_ARCHITECTURE: {
                'voice_engine_types': ['xg', 'an', 'fdsp', 'sf2', 'fm', 'additive', 'wavetable'],
                'max_voices': 256,
                'voice_stealing_enabled': True,
                'voice_priority_system': True,
                'voice_reservation': True,
                'voice_grouping': True
            },
            CapabilityType.SAMPLE_LIBRARY: {
                'has_internal_samples': True,
                'max_sample_memory_mb': 1024,
                'supports_sf2': True,
                'supports_sfz': True,
                'supports_dls': True,
                'sample_formats': ['wav', 'aiff', 'sf2', 'sfz', 'dls', 'flac', 'ogg'],
                'max_samples': 10000,
                'sample_quality': '24bit_48khz'
            },
            CapabilityType.MAX_SIMULTANEOUS_PROFILES: 8,
            CapabilityType.DYNAMIC_PROFILE_SWITCHING: True,
            CapabilityType.PROFILE_INHERITANCE: True,
            CapabilityType.PROFILE_SPECIFIC_PARAMS: True,
            CapabilityType.MIDI_CI_SUPPORT: True,
            CapabilityType.MPE_PLUS_SUPPORT: True,
            CapabilityType.PER_NOTE_EXPRESSIONS: True,
            CapabilityType.PER_NOTE_MODULATION: True,
            CapabilityType.PER_NOTE_PITCH_BEND: True,
            CapabilityType.PER_NOTE_TUNING: True,
            CapabilityType.PER_NOTE_MANAGEMENT: True,
            CapabilityType.PER_NOTE_HARMONIC_CONTENT: True,
            CapabilityType.PER_NOTE_BRIGHTNESS: True,
            CapabilityType.PER_NOTE_TIMBRE: True,
            CapabilityType.PER_NOTE_PAN: True,
            CapabilityType.PER_NOTE_REVERB_SEND: True,
            CapabilityType.PER_NOTE_CHORUS_SEND: True,
            CapabilityType.PER_NOTE_VARIATION_SEND: True,
            CapabilityType.PER_NOTE_TREMOLO: True,
            CapabilityType.PER_NOTE_VIBRATO: True,
            CapabilityType.PER_NOTE_PHASING: True,
            CapabilityType.PER_NOTE_FLANGING: True,
            CapabilityType.PER_NOTE_FILTER_CUTOFF: True,
            CapabilityType.PER_NOTE_FILTER_RESONANCE: True,
            CapabilityType.PER_NOTE_ATTACK_TIME: True,
            CapabilityType.PER_NOTE_DECAY_TIME: True,
            CapabilityType.PER_NOTE_RELEASE_TIME: True,
            CapabilityType.PER_NOTE_SUSTAIN_LEVEL: True,
            CapabilityType.PER_NOTE_AMPLITUDE: True,
            CapabilityType.PER_NOTE_FREQUENCY: True,
            CapabilityType.PER_NOTE_WAVEFORM: True,
            CapabilityType.PER_NOTE_ENVELOPE_SHAPE: True,
            CapabilityType.PER_NOTE_LFO_RATE: True,
            CapabilityType.PER_NOTE_LFO_DEPTH: True,
            CapabilityType.PER_NOTE_LFO_SHAPE: True,
            CapabilityType.PER_NOTE_LFO_PHASE: True,
            CapabilityType.PER_NOTE_EG_BIAS: True,
            CapabilityType.PER_NOTE_EG_DEPTH: True,
            CapabilityType.PER_NOTE_EG_SHAPE: True,
            CapabilityType.PER_NOTE_EG_TIME: True,
            CapabilityType.PER_NOTE_EG_LEVEL: True,
            CapabilityType.PER_NOTE_EG_RATE: True,
            CapabilityType.PER_NOTE_EG_ATTACK: True,
            CapabilityType.PER_NOTE_EG_DECAY: True,
            CapabilityType.PER_NOTE_EG_SUSTAIN: True,
            CapabilityType.PER_NOTE_EG_RELEASE: True,
            CapabilityType.PER_NOTE_EG_HOLD: True,
            CapabilityType.PER_NOTE_EG_DELAY: True,
            CapabilityType.PER_NOTE_EG_START: True,
            CapabilityType.PER_NOTE_EG_PEAK: True,
            CapabilityType.PER_NOTE_EG_INITIAL: True,
            CapabilityType.PER_NOTE_EG_FINAL: True,
            CapabilityType.PER_NOTE_EG_OFFSET: True,
            CapabilityType.PER_NOTE_EG_INVERT: True,
            CapabilityType.PER_NOTE_EG_LOOP: True,
            CapabilityType.PER_NOTE_EG_CYCLE: True,
            CapabilityType.PER_NOTE_EG_STEP: True,
            CapabilityType.PER_NOTE_EG_SMOOTH: True,
            CapabilityType.PER_NOTE_EG_RANDOM: True,
            CapabilityType.PER_NOTE_EG_SHUFFLE: True,
            CapabilityType.PER_NOTE_EG_SYNC: True,
            CapabilityType.PER_NOTE_EG_RESET: True,
            CapabilityType.PER_NOTE_EG_REPEAT: True,
            CapabilityType.PER_NOTE_EG_SKIP: True,
            CapabilityType.PER_NOTE_EG_JUMP: True,
            CapabilityType.PER_NOTE_EG_TURN: True,
            CapabilityType.PER_NOTE_EG_GLISSANDO: True,
            CapabilityType.PER_NOTE_EG_PORTAMENTO: True,
            CapabilityType.PER_NOTE_EG_SLIDE: True,
            CapabilityType.PER_NOTE_EG_BEND: True,
            CapabilityType.PER_NOTE_EG_VIBRATO: True,
            CapabilityType.PER_NOTE_EG_TREMOLO: True,
            CapabilityType.PER_NOTE_EG_AUTO_PAN: True,
            CapabilityType.PER_NOTE_EG_ROTARY: True,
            CapabilityType.PER_NOTE_EG_WAH: True,
            CapabilityType.PER_NOTE_EG_FILTER: True,
            CapabilityType.PER_NOTE_EG_DISTORTION: True,
            CapabilityType.PER_NOTE_EG_OVERDRIVE: True,
            CapabilityType.PER_NOTE_EG_COMPRESSION: True,
            CapabilityType.PER_NOTE_EG_GATE: True,
            CapabilityType.PER_NOTE_EG_EXPANDER: True,
            CapabilityType.PER_NOTE_EG_EXCITER: True,
            CapabilityType.PER_NOTE_EG_ENHANCER: True,
            CapabilityType.PER_NOTE_EG_IMAGER: True,
            CapabilityType.PER_NOTE_EG_REVERB: True,
            CapabilityType.PER_NOTE_EG_CHORUS: True,
            CapabilityType.PER_NOTE_EG_DELAY: True,
            CapabilityType.PER_NOTE_EG_ECHO: True,
            CapabilityType.PER_NOTE_EG_FLANGER: True,
            CapabilityType.PER_NOTE_EG_PHASER: True,
            CapabilityType.PER_NOTE_EG_PITCH_SHIFT: True,
            CapabilityType.PER_NOTE_EG_FORMANT: True,
            CapabilityType.PER_NOTE_EG_VOCODER: True,
            CapabilityType.PER_NOTE_EG_RING_MOD: True,
            CapabilityType.PER_NOTE_EG_TALK_MOD: True,
            CapabilityType.PER_NOTE_EG_AUTO_WAH: True,
            CapabilityType.PER_NOTE_EG_AUTO_FILTER: True,
            CapabilityType.PER_NOTE_EG_AUTO_PAN: True,
            CapabilityType.PER_NOTE_EG_AUTO_ROTARY: True,
            CapabilityType.PER_NOTE_EG_AUTO_TREMOLO: True,
            CapabilityType.PER_NOTE_EG_AUTO_VIBRATO: True,
            CapabilityType.PER_NOTE_EG_AUTO_WOBBLE: True,
            CapabilityType.PER_NOTE_EG_AUTO_SHIMMER: True,
            CapabilityType.PER_NOTE_EG_AUTO_SWELL: True,
            CapabilityType.PER_NOTE_EG_AUTO_HARMONIZER: True,
            CapabilityType.PER_NOTE_EG_AUTO_PITCH_SHIFT: True,
            CapabilityType.PER_NOTE_EG_AUTO_FORMANT: True,
            CapabilityType.PER_NOTE_EG_AUTO_VOCODER: True,
            CapabilityType.PER_NOTE_EG_AUTO_RING_MOD: True,
            CapabilityType.PER_NOTE_EG_AUTO_TALK_MOD: True,
            CapabilityType.PER_NOTE_EG_AUTO_EXCITER: True,
            CapabilityType.PER_NOTE_EG_AUTO_ENHANCER: True,
            CapabilityType.PER_NOTE_EG_AUTO_IMAGER: True,
            CapabilityType.PER_NOTE_EG_AUTO_REVERB: True,
            CapabilityType.PER_NOTE_EG_AUTO_CHORUS: True,
            CapabilityType.PER_NOTE_EG_AUTO_DELAY: True,
            CapabilityType.PER_NOTE_EG_AUTO_ECHO: True,
            CapabilityType.PER_NOTE_EG_AUTO_FLANGER: True,
            CapabilityType.PER_NOTE_EG_AUTO_PHASER: True,
            CapabilityType.PER_NOTE_EG_AUTO_PITCH_SHIFT: True,
            CapabilityType.PER_NOTE_EG_AUTO_FORMANT: True,
            CapabilityType.PER_NOTE_EG_AUTO_VOCODER: True,
            CapabilityType.PER_NOTE_EG_AUTO_RING_MOD: True,
            CapabilityType.PER_NOTE_EG_AUTO_TALK_MOD: True,
            CapabilityType.PER_NOTE_EG_AUTO_EXCITER: True,
            CapabilityType.PER_NOTE_EG_AUTO_ENHANCER: True,
            CapabilityType.PER_NOTE_EG_AUTO_IMAGER: True,
        }
    
    def _create_gm_capabilities(self) -> dict[CapabilityType, Any]:
        """Create GM-specific capabilities."""
        return {
            CapabilityType.MIDI_VERSION: 1.0,
            CapabilityType.MAX_CHANNELS: 16,
            CapabilityType.MAX_POLYPHONY: 64,
            CapabilityType.PARAMETER_RESOLUTION: 7,
            CapabilityType.PER_NOTE_CONTROLLERS: False,
            CapabilityType.MPE_SUPPORT: False,
            CapabilityType.SYSEX_7_SUPPORT: False,
            CapabilityType.PROPERTY_EXCHANGE: False,
            CapabilityType.PROFILE_CONFIG: False,
            CapabilityType.UMP_STREAMS: 1,
            CapabilityType.JITTER_REDUCTION: False,
            CapabilityType.MIXED_DATA_SETS: False,
            CapabilityType.SUPPORTED_MESSAGES: {
                'note_on', 'note_off', 'control_change', 'program_change',
                'pitch_bend', 'channel_pressure', 'poly_pressure'
            },
            CapabilityType.EFFECTS_CAPABILITIES: {
                'reverb_units': 1,
                'chorus_units': 1,
                'delay_units': 0,
                'distortion_units': 0
            },
            CapabilityType.VOICE_ARCHITECTURE: {
                'voice_engine_types': ['gm'],
                'max_voices': 64,
                'voice_stealing_enabled': True,
                'voice_priority_system': False
            },
            CapabilityType.SAMPLE_LIBRARY: {
                'has_internal_samples': True,
                'max_sample_memory_mb': 16,
                'supports_sf2': False,
                'supports_sfz': False,
                'sample_formats': ['wav', 'aiff']
            },
            CapabilityType.MAX_SIMULTANEOUS_PROFILES: 1,
            CapabilityType.DYNAMIC_PROFILE_SWITCHING: False,
            CapabilityType.PROFILE_INHERITANCE: False,
            CapabilityType.PROFILE_SPECIFIC_PARAMS: False,
            CapabilityType.MIDI_CI_SUPPORT: False,
            CapabilityType.MPE_PLUS_SUPPORT: False,
            CapabilityType.PER_NOTE_EXPRESSIONS: False,
        }
    
    def _create_gs_capabilities(self) -> dict[CapabilityType, Any]:
        """Create GS-specific capabilities."""
        caps = self._create_gm_capabilities()
        caps.update({
            CapabilityType.MIDI_VERSION: 1.0,
            CapabilityType.MAX_CHANNELS: 16,
            CapabilityType.MAX_POLYPHONY: 128,
            CapabilityType.PARAMETER_RESOLUTION: 14,
            CapabilityType.PER_NOTE_CONTROLLERS: False,
            CapabilityType.MPE_SUPPORT: False,
            CapabilityType.SYSEX_7_SUPPORT: True,
            CapabilityType.PROPERTY_EXCHANGE: True,
            CapabilityType.PROFILE_CONFIG: True,
            CapabilityType.UMP_STREAMS: 1,
            CapabilityType.JITTER_REDUCTION: False,
            CapabilityType.MIXED_DATA_SETS: False,
            CapabilityType.SUPPORTED_MESSAGES: caps[CapabilityType.SUPPORTED_MESSAGES].union({
                'gs_sysex', 'gs_parameter_change', 'gs_bulk_dump'
            }),
            CapabilityType.EFFECTS_CAPABILITIES: {
                'reverb_units': 2,
                'chorus_units': 2,
                'delay_units': 2,
                'distortion_units': 1
            },
            CapabilityType.VOICE_ARCHITECTURE: {
                'voice_engine_types': ['gs', 'gm'],
                'max_voices': 128,
                'voice_stealing_enabled': True,
                'voice_priority_system': True
            },
            CapabilityType.SAMPLE_LIBRARY: {
                'has_internal_samples': True,
                'max_sample_memory_mb': 32,
                'supports_sf2': True,
                'supports_sfz': False,
                'sample_formats': ['wav', 'aiff', 'sf2']
            },
            CapabilityType.MAX_SIMULTANEOUS_PROFILES: 2,
            CapabilityType.DYNAMIC_PROFILE_SWITCHING: True,
            CapabilityType.PROFILE_INHERITANCE: False,
            CapabilityType.PROFILE_SPECIFIC_PARAMS: True,
            CapabilityType.MIDI_CI_SUPPORT: False,
            CapabilityType.MPE_PLUS_SUPPORT: False,
            CapabilityType.PER_NOTE_EXPRESSIONS: False,
        })
        return caps
    
    def _create_mpe_capabilities(self) -> dict[CapabilityType, Any]:
        """Create MPE-specific capabilities."""
        caps = self._create_gm_capabilities()
        caps.update({
            CapabilityType.MIDI_VERSION: 1.0,
            CapabilityType.MAX_CHANNELS: 16,  # MPE uses multiple channels for polyphony
            CapabilityType.MAX_POLYPHONY: 15,  # MPE typically uses 15 note channels + 1 controller
            CapabilityType.PARAMETER_RESOLUTION: 14,
            CapabilityType.PER_NOTE_CONTROLLERS: True,
            CapabilityType.MPE_SUPPORT: True,
            CapabilityType.SYSEX_7_SUPPORT: False,
            CapabilityType.PROPERTY_EXCHANGE: False,
            CapabilityType.PROFILE_CONFIG: False,
            CapabilityType.UMP_STREAMS: 1,
            CapabilityType.JITTER_REDUCTION: False,
            CapabilityType.MIXED_DATA_SETS: False,
            CapabilityType.SUPPORTED_MESSAGES: caps[CapabilityType.SUPPORTED_MESSAGES].union({
                'mpe_configuration', 'per_note_controller', 'per_note_pitch_bend'
            }),
            CapabilityType.EFFECTS_CAPABILITIES: {
                'reverb_units': 1,
                'chorus_units': 1,
                'delay_units': 0,
                'distortion_units': 0
            },
            CapabilityType.VOICE_ARCHITECTURE: {
                'voice_engine_types': ['mpe', 'gm'],
                'max_voices': 15,  # MPE limitation
                'voice_stealing_enabled': False,  # MPE doesn't steal voices
                'voice_priority_system': False
            },
            CapabilityType.SAMPLE_LIBRARY: {
                'has_internal_samples': True,
                'max_sample_memory_mb': 16,
                'supports_sf2': False,
                'supports_sfz': False,
                'sample_formats': ['wav', 'aiff']
            },
            CapabilityType.MAX_SIMULTANEOUS_PROFILES: 1,
            CapabilityType.DYNAMIC_PROFILE_SWITCHING: False,
            CapabilityType.PROFILE_INHERITANCE: False,
            CapabilityType.PROFILE_SPECIFIC_PARAMS: False,
            CapabilityType.MIDI_CI_SUPPORT: False,
            CapabilityType.MPE_PLUS_SUPPORT: True,  # MPE+ extensions
            CapabilityType.PER_NOTE_EXPRESSIONS: True,
            CapabilityType.PER_NOTE_MODULATION: True,
            CapabilityType.PER_NOTE_PITCH_BEND: True,
            CapabilityType.PER_NOTE_MANAGEMENT: False,
        })
        return caps
    
    def query_capability(self, device_id: str, capability_type: CapabilityType) -> Any | None:
        """
        Query a specific capability of a device.

        Args:
            device_id: Device identifier
            capability_type: Type of capability to query

        Returns:
            Capability value or None if not supported/discovered
        """
        if device_id not in self.device_capabilities:
            # Try to discover capabilities first
            self.discover_device_capabilities(device_id)
        
        device_caps = self.device_capabilities.get(device_id, {})
        return device_caps.get(capability_type)
    
    def get_device_summary(self, device_id: str) -> dict[str, Any]:
        """
        Get a summary of device capabilities.

        Args:
            device_id: Device identifier

        Returns:
            Summary dictionary of key capabilities
        """
        caps = self.discover_device_capabilities(device_id)
        
        return {
            'midi_version': caps.get(CapabilityType.MIDI_VERSION, 1.0),
            'max_channels': caps.get(CapabilityType.MAX_CHANNELS, 16),
            'max_polyphony': caps.get(CapabilityType.MAX_POLYPHONY, 64),
            'parameter_resolution_bits': caps.get(CapabilityType.PARAMETER_RESOLUTION, 7),
            'supports_per_note_controllers': caps.get(CapabilityType.PER_NOTE_CONTROLLERS, False),
            'supports_mpe': caps.get(CapabilityType.MPE_SUPPORT, False),
            'supports_sysex_7': caps.get(CapabilityType.SYSEX_7_SUPPORT, False),
            'supports_property_exchange': caps.get(CapabilityType.PROPERTY_EXCHANGE, False),
            'supports_profile_configuration': caps.get(CapabilityType.PROFILE_CONFIG, False),
            'max_ump_streams': caps.get(CapabilityType.UMP_STREAMS, 1),
            'supports_jitter_reduction': caps.get(CapabilityType.JITTER_REDUCTION, False),
            'supports_mixed_data_sets': caps.get(CapabilityType.MIXED_DATA_SETS, False),
            'supports_mpe_plus': caps.get(CapabilityType.MPE_PLUS_SUPPORT, False),
            'supports_per_note_expressions': caps.get(CapabilityType.PER_NOTE_EXPRESSIONS, False),
            'supports_per_note_modulation': caps.get(CapabilityType.PER_NOTE_MODULATION, False),
            'supports_per_note_pitch_bend': caps.get(CapabilityType.PER_NOTE_PITCH_BEND, False),
            'supports_per_note_tuning': caps.get(CapabilityType.PER_NOTE_TUNING, False),
            'supports_per_note_management': caps.get(CapabilityType.PER_NOTE_MANAGEMENT, False),
            'total_supported_message_types': len(caps.get(CapabilityType.SUPPORTED_MESSAGES, set())),
            'effect_units_available': sum(caps.get(CapabilityType.EFFECTS_CAPABILITIES, {}).values()) if caps.get(CapabilityType.EFFECTS_CAPABILITIES) else 0,
            'max_simultaneous_profiles': caps.get(CapabilityType.MAX_SIMULTANEOUS_PROFILES, 1),
            'supports_dynamic_profile_switching': caps.get(CapabilityType.DYNAMIC_PROFILE_SWITCHING, False),
            'supports_profile_inheritance': caps.get(CapabilityType.PROFILE_INHERITANCE, False),
            'supports_midi_ci': caps.get(CapabilityType.MIDI_CI_SUPPORT, False),
        }
    
    def add_discovery_callback(self, callback: callable):
        """
        Add a callback for capability discovery events.

        Args:
            callback: Function to call when capabilities are discovered
        """
        self.discovery_callbacks.append(callback)
    
    def remove_discovery_callback(self, callback: callable):
        """
        Remove a discovery callback.

        Args:
            callback: Callback function to remove
        """
        if callback in self.discovery_callbacks:
            self.discovery_callbacks.remove(callback)
    
    def serialize_capabilities(self, device_id: str) -> str:
        """
        Serialize device capabilities to JSON format.

        Args:
            device_id: Device identifier

        Returns:
            JSON string representation of capabilities
        """
        if device_id not in self.device_capabilities:
            return "{}"
        
        # Convert CapabilityType enums to string representations
        caps = self.device_capabilities[device_id]
        serializable_caps = {}
        
        for cap_type, value in caps.items():
            if isinstance(cap_type, CapabilityType):
                serializable_caps[cap_type.name] = value
            else:
                serializable_caps[str(cap_type)] = value
        
        return json.dumps(serializable_caps, indent=2)
    
    def deserialize_capabilities(self, device_id: str, caps_json: str) -> bool:
        """
        Deserialize device capabilities from JSON format.

        Args:
            device_id: Device identifier
            caps_json: JSON string of capabilities

        Returns:
            True if deserialization successful
        """
        try:
            caps_dict = json.loads(caps_json)
            
            # Convert string keys back to CapabilityType enums
            deserialized_caps = {}
            for key, value in caps_dict.items():
                try:
                    # Try to convert string key back to CapabilityType
                    cap_type = CapabilityType[key]
                    deserialized_caps[cap_type] = value
                except KeyError:
                    # If it's not a known CapabilityType, keep as string
                    deserialized_caps[key] = value
            
            self.device_capabilities[device_id] = deserialized_caps
            self.device_identifiers.add(device_id)
            return True
            
        except (json.JSONDecodeError, TypeError):
            return False
    
    def clear_device_cache(self, device_id: str | None = None):
        """
        Clear device capability cache.

        Args:
            device_id: Specific device to clear, or None for all devices
        """
        if device_id:
            if device_id in self.device_capabilities:
                del self.device_capabilities[device_id]
            if device_id in self.device_identifiers:
                self.device_identifiers.remove(device_id)
        else:
            self.device_capabilities.clear()
            self.device_identifiers.clear()
    
    def get_all_known_devices(self) -> list[str]:
        """
        Get list of all known device IDs.

        Returns:
            List of device identifiers
        """
        return list(self.device_identifiers)


# Global instance
capability_discoverer = CapabilityDiscoverySystem()


def get_capability_discoverer() -> CapabilityDiscoverySystem:
    """
    Get the global capability discovery system instance.

    Returns:
        CapabilityDiscoverySystem instance
    """
    return capability_discoverer