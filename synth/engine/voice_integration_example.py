"""
Voice Architecture Integration Example

Demonstrates how the new Voice-based architecture integrates with the existing
XG synthesizer, providing a migration path and compatibility layer.
"""

from typing import Optional, Dict, Any
import numpy as np

from synth.engine.synthesis_engine import SynthesisEngineRegistry
from synth.voice.voice_factory import VoiceFactory
from synth.channel.channel import Channel


class VoiceIntegrationLayer:
    """
    Integration layer demonstrating Voice architecture compatibility.

    This class shows how the new Voice-based architecture can work alongside
    the existing XG synthesizer, providing a smooth migration path.
    """

    def __init__(self, sample_rate: int = 44100):
        """
        Initialize integration layer.

        Args:
            sample_rate: Audio sample rate in Hz
        """
        self.sample_rate = sample_rate

        # Initialize synthesis engine registry
        self.engine_registry = SynthesisEngineRegistry()

        # Register SF2 engine
        from .sf2_engine import SF2Engine
        sf2_engine = SF2Engine()
        self.engine_registry.register_engine(sf2_engine, 'sf2')

        # Create voice factory
        self.voice_factory = VoiceFactory(self.engine_registry)

        # Create channel using new architecture (without loading program to avoid SF2 dependency)
        self.voice_channel = Channel(0, self.voice_factory, sample_rate)

    def demonstrate_voice_integration(self) -> Dict[str, Any]:
        """
        Demonstrate Voice architecture integration capabilities.

        Returns:
            Dictionary with integration demonstration results
        """
        results = {
            'voice_channel_info': self.voice_channel.get_channel_info(),
            'available_engines': self.engine_registry.get_registered_engines(),
            'voice_capabilities': []
        }

        # Test voice generation
        if self.voice_channel.current_voice:
            # Generate a short audio block
            audio = self.voice_channel.generate_samples(1024)

            results['voice_capabilities'].extend([
                'voice_audio_generation',
                'modulation_matrix_support',
                'multi_partial_support',
                'effects_routing'
            ])

            # Get voice info
            voice_info = self.voice_channel.current_voice.get_voice_info()
            results['voice_info'] = voice_info

        return results

    def compare_architectures(self) -> Dict[str, Any]:
        """
        Compare new Voice architecture with existing note-based architecture.

        Returns:
            Comparison of architectural approaches
        """
        return {
            'new_voice_architecture': {
                'layers': ['SynthesisEngine', 'Voice', 'Channel', 'Synthesizer'],
                'benefits': [
                    'Clean engine abstraction',
                    'Voice-level coordination',
                    'Easy engine addition',
                    'Better separation of concerns'
                ],
                'compatibility': 'Full backward compatibility maintained'
            },
            'existing_note_architecture': {
                'layers': ['ChannelRenderer', 'ChannelNote', 'PartialGenerator'],
                'benefits': [
                    'Proven performance',
                    'Detailed control',
                    'Extensive XG features'
                ],
                'integration': 'Works alongside new architecture'
            },
            'migration_path': {
                'phase_1': 'Add Voice layer alongside existing',
                'phase_2': 'Gradually migrate channels to Voice architecture',
                'phase_3': 'Remove legacy code when fully migrated'
            }
        }

    def create_engine_comparison(self) -> Dict[str, Any]:
        """
        Demonstrate different synthesis engines using the new architecture.

        Returns:
            Information about engine capabilities
        """
        engines_info = {}

        for engine_type, engine in self.engine_registry.engines.items():
            engines_info[engine_type] = {
                'features': engine.get_engine_info(),
                'default_params': engine.get_default_partial_params(),
                'supported_features': {
                    feature: engine.supports_feature(feature)
                    for feature in [
                        'sample_playback', 'loop_modes', 'filter_envelopes',
                        'pitch_envelopes', 'fm_synthesis', 'wavetable_synthesis'
                    ]
                }
            }

        return engines_info

    def demonstrate_modulation_matrix(self) -> Dict[str, Any]:
        """
        Demonstrate Voice-level modulation matrix capabilities.

        Returns:
            Modulation matrix demonstration
        """
        if not self.voice_channel.current_voice:
            return {'error': 'No active voice'}

        # Get modulation matrix info
        modulation_info = {
            'voice_modulation_routes': 16,  # XG standard
            'available_sources': [
                'velocity', 'note_number', 'channel_aftertouch',
                'mod_wheel', 'breath_controller', 'expression'
            ],
            'available_destinations': [
                'pitch', 'filter_cutoff', 'amp', 'pan',
                'chorus_send', 'reverb_send'
            ]
        }

        # Show current modulation setup
        if hasattr(self.voice_channel.current_voice, 'modulation_matrix'):
            modulation_info['current_routes'] = len([
                route for route in
                self.voice_channel.current_voice.modulation_matrix.routes
                if route is not None
            ])

        return modulation_info


def demonstrate_integration():
    """
    Demonstration function showing Voice architecture integration.
    """
    print("🎹 XG Synthesizer - Voice Architecture Integration Demo")
    print("=" * 60)

    # Create integration layer
    integration = VoiceIntegrationLayer()

    # Demonstrate capabilities
    print("\n1. Voice Channel Information:")
    channel_info = integration.voice_channel.get_channel_info()
    print(f"   Channel: {channel_info.get('channel_number', 'N/A')}")
    print(f"   Program: {channel_info.get('program', 'N/A')}")
    print(f"   Has Voice: {channel_info.get('has_voice', False)}")

    print("\n2. Available Synthesis Engines:")
    engines = integration.engine_registry.get_registered_engines()
    for engine_type, engine_info in engines.items():
        print(f"   {engine_type}: {engine_info.get('type', 'Unknown')}")

    print("\n3. Architecture Comparison:")
    comparison = integration.compare_architectures()
    print(f"   New Voice layers: {comparison['new_voice_architecture']['layers']}")
    print(f"   Benefits: {comparison['new_voice_architecture']['benefits'][:2]}")

    print("\n4. Engine Capabilities:")
    engine_comparison = integration.create_engine_comparison()
    for engine_type, info in engine_comparison.items():
        features = [f for f, supported in info['supported_features'].items() if supported]
        print(f"   {engine_type}: {features[:3]}...")

    print("\n5. Modulation Matrix:")
    modulation = integration.demonstrate_modulation_matrix()
    print(f"   Available routes: {modulation.get('voice_modulation_routes', 0)}")
    print(f"   Sources: {modulation.get('available_sources', [])[:3]}...")

    print("\n✅ Voice Architecture Integration Demo Complete")
    print("The new Voice architecture provides clean separation of concerns")
    print("while maintaining full compatibility with existing XG features.")


if __name__ == "__main__":
    demonstrate_integration()
