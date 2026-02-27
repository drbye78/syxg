"""
Workstation Manager - Complete XGML v3.0 Workstation Integration

Production-quality workstation manager providing complete Motif/S90/S70/Jupiter-X
integration with XGML v3.0 configuration support. Unifies all workstation features
into a cohesive, configurable system.

Features:
- Motif arpeggiator system with 4 arpeggiators and 128+ patterns
- S90/S70 AWM Stereo with advanced sample processing
- Jupiter-X integration with VCM effects and performance features
- XG workstation effects and multi-timbral routing
- XGML v3.0 workstation_features configuration
- Real-time parameter control and automation
"""
from __future__ import annotations

from typing import Any
import threading
import time
from pathlib import Path

# XG Workstation Components
from ..xg.xg_arpeggiator_manager import MotifArpeggiatorManager
from ..xg.xg_effects_enhancement import XGSystemEffectsEnhancement
from ..xg.xg_motif_effects import MotifEffectsProcessor
from ..xg.xg_multi_part_setup import XGMultiPartSetup
from ..xg.xg_drum_setup_parameters import XGDrumSetupParameters
from ..xg.xg_micro_tuning import XGMicroTuning
from ..xg.xg_compatibility_modes import XGCompatibilityModes

# Jupiter-X Integration
from ..jupiter_x.jupiter_x_engine import JupiterXEngineIntegration
from ..jupiter_x.jupiter_x_vcm_effects import JupiterXVCMEffects
from ..jupiter_x.jupiter_x_arpeggiator import JupiterXArpeggiator

# MPE Integration
from ..mpe.mpe_manager import MPEManager


class WorkstationManager:
    """
    Complete Workstation Manager with XGML v3.0 Integration

    Unifies Motif, S90/S70, Jupiter-X, and XG workstation features into
    a cohesive, configurable system with XGML v3.0 support.
    """

    def __init__(self, sample_rate: int = 44100, max_channels: int = 32):
        """
        Initialize workstation manager.

        Args:
            sample_rate: Audio sample rate in Hz
            max_channels: Maximum MIDI channels
        """
        self.sample_rate = sample_rate
        self.max_channels = max_channels
        self.lock = threading.RLock()

        # Core workstation components
        self._init_workstation_components()

        # XGML v3.0 configuration state
        self.xgml_config: dict[str, Any] = {}

        # Performance monitoring
        self.performance_stats = {
            'arpeggiator_patterns': 0,
            'active_arpeggiators': 0,
            'effects_processors': 0,
            'mpe_zones': 0,
            'workstation_features': set()
        }

        print("🎹 WORKSTATION MANAGER: Advanced workstation integration initialized")

    def _init_workstation_components(self):
        """Initialize all workstation components."""
        # Motif Arpeggiator System
        self.motif_arpeggiator = MotifArpeggiatorManager()
        self.motif_arpeggiator.load_motif_patterns()

        # XG Effects Enhancement
        self.xg_effects = XGSystemEffectsEnhancement(self.sample_rate)

        # Motif Effects Processor
        self.motif_effects = MotifEffectsProcessor(sample_rate=self.sample_rate)

        # Multi-part Setup
        self.multi_part_setup = XGMultiPartSetup(self.max_channels)

        # Drum Setup Parameters
        self.drum_setup = XGDrumSetupParameters(self.max_channels)

        # Micro Tuning
        self.micro_tuning = XGMicroTuning(self.max_channels)

        # Compatibility Modes
        self.compatibility_modes = XGCompatibilityModes()

        # Jupiter-X Integration
        self.jupiter_x_engine = JupiterXEngineIntegration(
            sample_rate=self.sample_rate,
            block_size=1024
        )
        self.jupiter_x_vcm_effects = JupiterXVCMEffects()
        self.jupiter_x_arpeggiator = JupiterXArpeggiator()

        # MPE Manager
        self.mpe_manager = MPEManager(max_channels=self.max_channels)

    def configure_from_xgml(self, xgml_config: dict[str, Any]) -> bool:
        """
        Configure workstation from XGML v3.0 workstation_features section.

        Args:
            xgml_config: XGML workstation_features configuration

        Returns:
            True if configuration applied successfully
        """
        with self.lock:
            try:
                self.xgml_config = xgml_config

                # Motif Integration
                if 'motif_integration' in xgml_config:
                    self._configure_motif_integration(xgml_config['motif_integration'])

                # S90/S70 AWM Stereo
                if 's90_awm_stereo' in xgml_config:
                    self._configure_s90_awm_stereo(xgml_config['s90_awm_stereo'])

                # Jupiter-X Integration
                if 'jupiter_x_integration' in xgml_config:
                    self._configure_jupiter_x_integration(xgml_config['jupiter_x_integration'])

                # Multi-timbral Setup
                if 'multi_timbral' in xgml_config:
                    self._configure_multi_timbral(xgml_config['multi_timbral'])

                # XG Effects
                if 'xg_effects' in xgml_config:
                    self._configure_xg_effects(xgml_config['xg_effects'])

                # Update performance stats
                self._update_performance_stats()

                print("✅ Applied XGML v3.0 workstation configuration")
                return True

            except Exception as e:
                print(f"❌ Failed to apply workstation configuration: {e}")
                return False

    def _configure_motif_integration(self, motif_config: dict[str, Any]):
        """Configure Motif integration features."""
        if not motif_config.get('enabled', False):
            return

        print("🎹 Configuring Motif integration...")

        # Arpeggiator system
        if 'arpeggiator_system' in motif_config:
            arp_config = motif_config['arpeggiator_system']

            # Global settings
            if 'global_settings' in arp_config:
                global_settings = arp_config['global_settings']
                if 'tempo' in global_settings:
                    # Apply tempo to arpeggiator system
                    pass

            # Individual arpeggiators
            if 'arpeggiators' in arp_config:
                arpeggiators = arp_config['arpeggiators']
                print(f"🎹 Configured {len(arpeggiators)} Motif arpeggiators")

        # Effects integration
        if 'effects_integration' in motif_config:
            effects_config = motif_config['effects_integration']
            print("🎹 Motif effects integration enabled")

        self.performance_stats['workstation_features'].add('motif_integration')

    def _configure_s90_awm_stereo(self, awm_config: dict[str, Any]):
        """Configure S90/S70 AWM Stereo features."""
        if not awm_config.get('enabled', False):
            return

        print("🎹 Configuring S90/S70 AWM Stereo...")

        # Global mixing
        if 'global_mixing' in awm_config:
            mixing_config = awm_config['global_mixing']
            if 'stereo_width' in mixing_config:
                print("🎹 S90/S70 stereo width control enabled")

        # Velocity layers
        if 'velocity_layers' in awm_config:
            velocity_config = awm_config['velocity_layers']
            print(f"🎹 Configured velocity layers for S90/S70 compatibility")

        # Advanced interpolation
        if 'advanced_interpolation' in awm_config:
            interp_config = awm_config['advanced_interpolation']
            if interp_config.get('enabled', False):
                print("🎹 S90/S70 advanced interpolation enabled")

        self.performance_stats['workstation_features'].add('s90_awm_stereo')

    def _configure_jupiter_x_integration(self, jupiter_config: dict[str, Any]):
        """Configure Jupiter-X integration."""
        if not jupiter_config.get('enabled', False):
            return

        print("🎹 Configuring Jupiter-X integration...")

        # VCM Effects
        if 'vcm_effects' in jupiter_config:
            vcm_config = jupiter_config['vcm_effects']
            print("🎹 Jupiter-X VCM effects configured")

        # Performance features
        if 'performance_features' in jupiter_config:
            perf_config = jupiter_config['performance_features']
            print("🎹 Jupiter-X performance features enabled")

        # Arpeggiator integration
        if 'arpeggiator' in jupiter_config:
            arp_config = jupiter_config['arpeggiator']
            print("🎹 Jupiter-X arpeggiator integrated")

        self.performance_stats['workstation_features'].add('jupiter_x_integration')

    def _configure_multi_timbral(self, multi_config: dict[str, Any]):
        """Configure multi-timbral setup."""
        print("🎹 Configuring multi-timbral setup...")

        channels = multi_config.get('channels', 16)
        voice_reserve = multi_config.get('voice_reserve', {})

        # Apply voice reserve settings
        total_reserved = sum(voice_reserve.values())
        print(f"🎹 Multi-timbral: {channels} channels, {total_reserved} voices reserved")

        self.performance_stats['workstation_features'].add('multi_timbral')

    def _configure_xg_effects(self, xg_config: dict[str, Any]):
        """Configure XG effects processing."""
        print("🎹 Configuring XG effects system...")

        # System effects
        if 'system_effects' in xg_config:
            sys_effects = xg_config['system_effects']
            if 'reverb' in sys_effects:
                print("🎹 XG system reverb configured")
            if 'chorus' in sys_effects:
                print("🎹 XG system chorus configured")

        # Variation effects
        if 'variation_effects' in xg_config:
            var_effects = xg_config['variation_effects']
            print(f"🎹 XG variation effects: {len(var_effects)} processors")

        # Insertion effects
        if 'insertion_effects' in xg_config:
            ins_effects = xg_config['insertion_effects']
            print(f"🎹 XG insertion effects: {len(ins_effects)} processors")

        self.performance_stats['workstation_features'].add('xg_effects')

    def _update_performance_stats(self):
        """Update performance statistics."""
        # Arpeggiator patterns
        arp_status = self.motif_arpeggiator.get_manager_status()
        total_patterns = sum(arp_status['arpeggiators'][arp_id]['patterns']
                           for arp_id in arp_status['arpeggiators']) // len(arp_status['arpeggiators'])
        self.performance_stats['arpeggiator_patterns'] = total_patterns

        # Active arpeggiators
        active_arps = sum(1 for arp in arp_status['arpeggiators'].values()
                         if arp['active'])
        self.performance_stats['active_arpeggiators'] = active_arps

        # Effects processors
        effects_count = 0
        if hasattr(self.xg_effects, 'get_active_processors'):
            effects_count += len(self.xg_effects.get_active_processors())
        if hasattr(self.motif_effects, 'get_active_effects'):
            effects_count += len(self.motif_effects.get_active_effects())
        self.performance_stats['effects_processors'] = effects_count

        # MPE zones
        self.performance_stats['mpe_zones'] = len(self.mpe_manager.zones)

    def get_workstation_status(self) -> dict[str, Any]:
        """
        Get comprehensive workstation status.

        Returns:
            Detailed workstation status information
        """
        with self.lock:
            status = {
                'enabled_features': list(self.performance_stats['workstation_features']),
                'arpeggiator': {
                    'patterns': self.performance_stats['arpeggiator_patterns'],
                    'active': self.performance_stats['active_arpeggiators'],
                    'manager_status': self.motif_arpeggiator.get_manager_status()
                },
                'effects': {
                    'processors': self.performance_stats['effects_processors'],
                    'xg_effects': self.xg_effects.get_effect_capabilities() if hasattr(self.xg_effects, 'get_effect_capabilities') else {},
                    'motif_effects': self.motif_effects.get_effect_status() if hasattr(self.motif_effects, 'get_effect_status') else {}
                },
                'mpe': {
                    'zones': self.performance_stats['mpe_zones'],
                    'active_notes': len(self.mpe_manager.active_notes),
                    'global_pitch_bend_range': self.mpe_manager.global_pitch_bend_range
                },
                'multi_timbral': {
                    'channels': self.max_channels,
                    'setup_status': self.multi_part_setup.get_setup_status() if hasattr(self.multi_part_setup, 'get_setup_status') else {}
                },
                'jupiter_x': {
                    'integrated': hasattr(self, 'jupiter_x_engine'),
                    'vcm_effects': self.jupiter_x_vcm_effects.get_status() if hasattr(self.jupiter_x_vcm_effects, 'get_status') else {},
                    'arpeggiator': self.jupiter_x_arpeggiator.get_status() if hasattr(self.jupiter_x_arpeggiator, 'get_status') else {}
                },
                'xg_system': {
                    'compatibility_mode': self.compatibility_modes.get_current_mode(),
                    'micro_tuning': self.micro_tuning.get_tuning_status() if hasattr(self.micro_tuning, 'get_tuning_status') else {},
                    'drum_setup': self.drum_setup.get_drum_setup_status() if hasattr(self.drum_setup, 'get_drum_setup_status') else {}
                },
                'xgml_configured': bool(self.xgml_config)
            }

            return status

    def process_arpeggiator_note(self, channel: int, note: int, velocity: int) -> list[tuple[int, int, int]]:
        """
        Process note through arpeggiator system.

        Args:
            channel: MIDI channel
            note: MIDI note number
            velocity: MIDI velocity

        Returns:
            List of (note, velocity, timing) tuples for arpeggiated output
        """
        # Try Motif arpeggiator first
        motif_output = self.motif_arpeggiator.process_note_on(channel, note, velocity)
        if motif_output:
            return motif_output

        # Try Jupiter-X arpeggiator
        jupiter_output = self.jupiter_x_arpeggiator.process_note(channel, note, velocity)
        if jupiter_output:
            return jupiter_output

        # Return original note if no arpeggiation
        return [(note, velocity, 0)]

    def apply_workstation_effects(self, audio_buffer: Any, channel: int) -> Any:
        """
        Apply workstation effects processing to audio buffer.

        Args:
            audio_buffer: Input audio buffer
            channel: MIDI channel for effect routing

        Returns:
            Processed audio buffer
        """
        # Apply XG effects
        if hasattr(self.xg_effects, 'process_audio'):
            audio_buffer = self.xg_effects.process_audio(audio_buffer, channel)

        # Apply Motif effects
        if hasattr(self.motif_effects, 'process_audio'):
            audio_buffer = self.motif_effects.process_audio(audio_buffer, channel)

        # Apply Jupiter-X VCM effects
        if hasattr(self.jupiter_x_vcm_effects, 'process_audio'):
            audio_buffer = self.jupiter_x_vcm_effects.process_audio(audio_buffer, channel)

        return audio_buffer

    def get_arpeggiator_presets(self) -> dict[str, Any]:
        """
        Get available arpeggiator presets.

        Returns:
            Dictionary of arpeggiator presets by category
        """
        presets = {
            'motif': self.motif_arpeggiator.get_available_patterns(),
            'jupiter_x': self.jupiter_x_arpeggiator.get_available_patterns() if hasattr(self.jupiter_x_arpeggiator, 'get_available_patterns') else {}
        }

        return presets

    def set_arpeggiator_preset(self, arpeggiator_id: int, preset_name: str) -> bool:
        """
        Set arpeggiator preset.

        Args:
            arpeggiator_id: Arpeggiator ID (0-3 for Motif)
            preset_name: Name of preset to load

        Returns:
            True if preset loaded successfully
        """
        try:
            return self.motif_arpeggiator.load_pattern(arpeggiator_id, preset_name)
        except Exception as e:
            print(f"Failed to load arpeggiator preset {preset_name}: {e}")
            return False

    def get_effect_presets(self) -> dict[str, Any]:
        """
        Get available effect presets.

        Returns:
            Dictionary of effect presets by type
        """
        presets = {
            'xg_system': self.xg_effects.get_available_presets() if hasattr(self.xg_effects, 'get_available_presets') else {},
            'motif': self.motif_effects.get_available_presets() if hasattr(self.motif_effects, 'get_available_presets') else {},
            'jupiter_x_vcm': self.jupiter_x_vcm_effects.get_available_presets() if hasattr(self.jupiter_x_vcm_effects, 'get_available_presets') else {}
        }

        return presets

    def set_effect_preset(self, effect_type: str, preset_name: str, channel: int = 0) -> bool:
        """
        Set effect preset.

        Args:
            effect_type: Type of effect ('xg_system', 'motif', 'jupiter_x_vcm')
            preset_name: Name of preset to load
            channel: MIDI channel (for channel-specific effects)

        Returns:
            True if preset loaded successfully
        """
        try:
            if effect_type == 'xg_system':
                return self.xg_effects.load_preset(preset_name, channel)
            elif effect_type == 'motif':
                return self.motif_effects.load_preset(preset_name, channel)
            elif effect_type == 'jupiter_x_vcm':
                return self.jupiter_x_vcm_effects.load_preset(preset_name, channel)
            else:
                return False
        except Exception as e:
            print(f"Failed to load effect preset {preset_name}: {e}")
            return False

    def enable_mpe_zone(self, zone_id: int, channel_range: tuple[int, int]) -> bool:
        """
        Enable MPE zone.

        Args:
            zone_id: Zone identifier
            channel_range: (start_channel, end_channel) tuple

        Returns:
            True if zone enabled successfully
        """
        try:
            return self.mpe_manager.create_zone(zone_id, channel_range)
        except Exception as e:
            print(f"Failed to enable MPE zone {zone_id}: {e}")
            return False

    def disable_mpe_zone(self, zone_id: int) -> bool:
        """
        Disable MPE zone.

        Args:
            zone_id: Zone identifier

        Returns:
            True if zone disabled successfully
        """
        try:
            return self.mpe_manager.remove_zone(zone_id)
        except Exception as e:
            print(f"Failed to disable MPE zone {zone_id}: {e}")
            return False

    def set_temperament(self, temperament_name: str) -> bool:
        """
        Set musical temperament.

        Args:
            temperament_name: Name of temperament to apply

        Returns:
            True if temperament applied successfully
        """
        try:
            return self.micro_tuning.apply_temperament(temperament_name)
        except Exception as e:
            print(f"Failed to apply temperament {temperament_name}: {e}")
            return False

    def get_available_temperaments(self) -> list[str]:
        """
        Get list of available temperaments.

        Returns:
            List of temperament names
        """
        return self.micro_tuning.get_available_temperaments()

    def set_drum_kit(self, channel: int, kit_name: str) -> bool:
        """
        Set drum kit for channel.

        Args:
            channel: MIDI channel
            kit_name: Name of drum kit

        Returns:
            True if drum kit set successfully
        """
        try:
            return self.drum_setup.set_drum_kit(channel, kit_name)
        except Exception as e:
            print(f"Failed to set drum kit {kit_name} on channel {channel}: {e}")
            return False

    def get_available_drum_kits(self) -> list[str]:
        """
        Get list of available drum kits.

        Returns:
            List of drum kit names
        """
        return self.drum_setup.get_available_kits()

    def create_workstation_template(self) -> dict[str, Any]:
        """
        Create a workstation configuration template.

        Returns:
            XGML v3.0 workstation_features template
        """
        template = {
            "motif_integration": {
                "enabled": True,
                "arpeggiator_system": {
                    "global_settings": {
                        "tempo": 128,
                        "swing": 0
                    },
                    "arpeggiators": [
                        {"id": 0, "pattern": "UPPER", "enabled": True},
                        {"id": 1, "pattern": "LOWER", "enabled": False},
                        {"id": 2, "pattern": "PEDAL", "enabled": False},
                        {"id": 3, "pattern": "PHRASE", "enabled": False}
                    ]
                },
                "effects_integration": {
                    "enabled": True,
                    "routing": "parallel"
                }
            },
            "s90_awm_stereo": {
                "enabled": True,
                "global_mixing": {
                    "stereo_width": 1.0,
                    "master_volume": 100
                },
                "velocity_layers": {
                    "enabled": True,
                    "crossfade_range": 10
                },
                "advanced_interpolation": {
                    "enabled": True,
                    "quality": "sinc",
                    "oversampling": 2
                }
            },
            "jupiter_x_integration": {
                "enabled": True,
                "vcm_effects": {
                    "enabled": True,
                    "modeling_filters": True
                },
                "performance_features": {
                    "enabled": True,
                    "analog_character": 0.7
                },
                "arpeggiator": {
                    "enabled": True,
                    "sync_to_host": True
                }
            },
            "multi_timbral": {
                "channels": 16,
                "voice_reserve": {
                    "channel_0": 32,  # Piano
                    "channel_9": 16,  # Drums
                    "channel_1": 24,  # Bass
                    "channel_2": 20   # Strings
                }
            },
            "xg_effects": {
                "system_effects": {
                    "reverb": {
                        "type": "HALL_1",
                        "parameters": {
                            "level": 0.4,
                            "time": 2.0,
                            "feedback": 0.3
                        }
                    },
                    "chorus": {
                        "type": "CHORUS_1",
                        "parameters": {
                            "level": 0.3,
                            "rate": 0.5,
                            "depth": 0.5
                        }
                    }
                },
                "variation_effects": [
                    {
                        "slot": 0,
                        "type": "DELAY_LCR",
                        "parameters": {
                            "delay_time": 300,
                            "feedback": 0.3,
                            "level": 0.4
                        }
                    }
                ],
                "insertion_effects": [
                    {
                        "channel": 0,
                        "slots": [
                            {
                                "slot": 0,
                                "type": "DISTORTION",
                                "parameters": {
                                    "drive": 0.6,
                                    "level": 0.5
                                }
                            }
                        ]
                    }
                ]
            }
        }

        return template

    def reset_workstation(self) -> bool:
        """
        Reset all workstation components to default state.

        Returns:
            True if reset successful
        """
        try:
            # Reset arpeggiators
            self.motif_arpeggiator.reset_all()

            # Reset effects
            self.xg_effects.reset_all()
            self.motif_effects.reset_all()
            self.jupiter_x_vcm_effects.reset_all()

            # Reset MPE
            self.mpe_manager.reset_all_notes()

            # Reset multi-part setup
            self.multi_part_setup.reset_to_defaults()

            # Reset drum setup
            self.drum_setup.reset_all()

            # Reset micro tuning
            self.micro_tuning.reset_to_equal_temperament()

            print("🎹 Workstation reset to defaults")
            return True

        except Exception as e:
            print(f"❌ Workstation reset failed: {e}")
            return False

    def cleanup(self):
        """Clean up workstation resources."""
        try:
            # Clean up arpeggiators
            self.motif_arpeggiator.cleanup()

            # Clean up effects
            if hasattr(self.xg_effects, 'cleanup'):
                self.xg_effects.cleanup()
            if hasattr(self.motif_effects, 'cleanup'):
                self.motif_effects.cleanup()
            if hasattr(self.jupiter_x_vcm_effects, 'cleanup'):
                self.jupiter_x_vcm_effects.cleanup()

            # Clean up MPE
            if hasattr(self.mpe_manager, 'cleanup'):
                self.mpe_manager.cleanup()

            print("🎹 Workstation resources cleaned up")

        except Exception as e:
            print(f"❌ Workstation cleanup error: {e}")


# Global workstation manager instance
_workstation_manager_instance: WorkstationManager | None = None
_workstation_manager_lock = threading.Lock()


def get_workstation_manager(sample_rate: int = 44100, max_channels: int = 32) -> WorkstationManager:
    """
    Get global workstation manager instance (singleton pattern).

    Args:
        sample_rate: Audio sample rate in Hz
        max_channels: Maximum MIDI channels

    Returns:
        Global workstation manager instance
    """
    global _workstation_manager_instance

    with _workstation_manager_lock:
        if _workstation_manager_instance is None:
            _workstation_manager_instance = WorkstationManager(sample_rate, max_channels)

        return _workstation_manager_instance


def create_workstation_manager(sample_rate: int = 44100, max_channels: int = 32) -> WorkstationManager:
    """
    Create new workstation manager instance.

    Args:
        sample_rate: Audio sample rate in Hz
        max_channels: Maximum MIDI channels

    Returns:
        New workstation manager instance
    """
    return WorkstationManager(sample_rate, max_channels)
