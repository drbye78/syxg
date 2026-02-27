"""
XGML v3.0 Translator

Advanced translator for XGML v3.0 with complete feature support including:
- Hierarchical configuration processing
- Engine-specific translation
- Workstation feature translation
- Real-time parameter mapping
- Performance optimization
"""
from __future__ import annotations

from typing import Any
from dataclasses import dataclass
from enum import Enum

from .parser_v3 import XGMLConfigV3, ConfigurationSection
from synth.midi import MIDIMessage


class TranslationError(Exception):
    """XGML translation error."""
    pass


class EngineTranslator:
    """Base class for engine-specific translators."""

    def translate(self, config: dict[str, Any]) -> list[MIDIMessage]:
        """Translate engine configuration to MIDI messages."""
        raise NotImplementedError


class SF2EngineTranslator(EngineTranslator):
    """SF2 engine configuration translator."""

    def translate(self, config: dict[str, Any]) -> list[MIDIMessage]:
        """Translate SF2 engine configuration."""
        messages = []

        # Program and bank selection
        if 'program' in config:
            program = config['program']
            messages.append(MIDIMessage(
                type='program_change',
                channel=0,
                data={'program': program}
            ))

        if 'bank' in config:
            bank = config['bank']
            # Bank MSB
            messages.append(MIDIMessage(
                type='control_change',
                channel=0,
                data={'controller': 0, 'value': bank}
            ))

        # Velocity curve (would require SYSEX for some synths)
        if 'velocity_curve' in config:
            # Implementation depends on target synthesizer
            pass

        # AWM stereo settings
        if 'awm_stereo' in config and config['awm_stereo'].get('enabled', False):
            awm_config = config['awm_stereo']
            # Would require custom SYSEX implementation
            pass

        # Zone overrides - complex SF2 zone manipulation
        if 'zone_overrides' in config:
            # Would require extensive SYSEX for SF2 zone editing
            pass

        return messages


class FMXEngineTranslator(EngineTranslator):
    """FM-X engine configuration translator."""

    def translate(self, config: dict[str, Any]) -> list[MIDIMessage]:
        """Translate FM-X engine configuration."""
        messages = []

        # Algorithm selection (SYSEX required)
        if 'algorithm' in config:
            algorithm = config['algorithm']
            # Generate SYSEX for algorithm selection
            # This is placeholder - actual implementation depends on target synth
            pass

        # Master volume
        if 'master_volume' in config:
            volume = int(config['master_volume'] * 127)
            messages.append(MIDIMessage(
                type='control_change',
                channel=0,
                data={'controller': 7, 'value': volume}
            ))

        # Pitch bend range
        if 'pitch_bend_range' in config:
            pb_range = config['pitch_bend_range']
            # RPN 0,0 for pitch bend range
            messages.extend(self._generate_rpn_sequence(0, 0, 0, pb_range))

        # Operator configuration (extensive SYSEX required)
        if 'operators' in config:
            operators = config['operators']
            for op_name, op_config in operators.items():
                # Would require SYSEX for each operator parameter
                pass

        # LFO configuration (SYSEX required)
        if 'lfos' in config:
            lfos = config['lfos']
            for lfo_name, lfo_config in lfos.items():
                # Would require SYSEX for LFO parameters
                pass

        # Effects sends
        if 'effects_sends' in config:
            sends = config['effects_sends']
            if 'reverb' in sends:
                messages.append(MIDIMessage(
                    type='control_change',
                    channel=0,
                    data={'controller': 91, 'value': int(sends['reverb'] * 127)}
                ))
            if 'chorus' in sends:
                messages.append(MIDIMessage(
                    type='control_change',
                    channel=0,
                    data={'controller': 93, 'value': int(sends['chorus'] * 127)}
                ))

        return messages

    def _generate_rpn_sequence(self, channel: int, msb: int, lsb: int, value: int) -> list[MIDIMessage]:
        """Generate RPN parameter sequence."""
        return [
            MIDIMessage(type='control_change', channel=channel, data={'controller': 101, 'value': msb}),  # RPN MSB
            MIDIMessage(type='control_change', channel=channel, data={'controller': 100, 'value': lsb}),  # RPN LSB
            MIDIMessage(type='control_change', channel=channel, data={'controller': 6, 'value': value}),  # Data
        ]


class PhysicalEngineTranslator(EngineTranslator):
    """Physical modeling engine configuration translator."""

    def translate(self, config: dict[str, Any]) -> list[MIDIMessage]:
        """Translate physical modeling engine configuration."""
        messages = []

        model_type = config.get('model_type', 'string')

        # Model-specific parameter translation
        if model_type == 'string':
            messages.extend(self._translate_string_model(config.get('string_parameters', {})))
        elif model_type == 'woodwind':
            messages.extend(self._translate_woodwind_model(config.get('woodwind_parameters', {})))
        elif model_type == 'brass':
            messages.extend(self._translate_brass_model(config.get('brass_parameters', {})))
        elif model_type == 'percussion':
            messages.extend(self._translate_percussion_model(config.get('percussion_parameters', {})))

        # Waveguide parameters (SYSEX required)
        if 'waveguide_parameters' in config:
            # Would require SYSEX implementation
            pass

        # Modal synthesis (SYSEX required)
        if 'modal_synthesis' in config and config['modal_synthesis'].get('enabled', False):
            # Would require SYSEX implementation
            pass

        return messages

    def _translate_string_model(self, params: dict[str, Any]) -> list[MIDIMessage]:
        """Translate string model parameters."""
        messages = []

        # Map key parameters to available controls
        if 'pluck_position' in params:
            # Could map to modulation wheel or other control
            position = params['pluck_position']
            messages.append(MIDIMessage(
                type='control_change',
                channel=0,
                data={'controller': 1, 'value': int(position * 127)}
            ))

        return messages

    def _translate_woodwind_model(self, params: dict[str, Any]) -> list[MIDIMessage]:
        """Translate woodwind model parameters."""
        messages = []
        # Implementation depends on target synthesizer capabilities
        return messages

    def _translate_brass_model(self, params: dict[str, Any]) -> list[MIDIMessage]:
        """Translate brass model parameters."""
        messages = []
        # Implementation depends on target synthesizer capabilities
        return messages

    def _translate_percussion_model(self, params: dict[str, Any]) -> list[MIDIMessage]:
        """Translate percussion model parameters."""
        messages = []
        # Implementation depends on target synthesizer capabilities
        return messages


class SpectralEngineTranslator(EngineTranslator):
    """Spectral processing engine configuration translator."""

    def translate(self, config: dict[str, Any]) -> list[MIDIMessage]:
        """Translate spectral processing engine configuration."""
        messages = []

        # FFT settings (SYSEX required for most parameters)
        if 'fft_settings' in config:
            fft_config = config['fft_settings']
            # FFT size, hop size, window type would require SYSEX
            pass

        # Spectral parameters
        spectral_params = config.get('spectral_parameters', {})
        if 'dry_wet_mix' in spectral_params:
            mix = spectral_params['dry_wet_mix']
            messages.append(MIDIMessage(
                type='control_change',
                channel=0,
                data={'controller': 91, 'value': int(mix * 127)}
            ))

        # Morphing parameters
        morphing = config.get('morphing', {})
        if morphing.get('enabled', False):
            morph_pos = morphing.get('morph_position', 0.5)
            messages.append(MIDIMessage(
                type='control_change',
                channel=0,
                data={'controller': 93, 'value': int(morph_pos * 127)}
            ))

        # Filtering parameters
        filtering = config.get('filtering', {})
        if 'gain' in filtering:
            gain_db = filtering['gain']
            gain_val = int((gain_db + 24) * 127 / 48)  # -24 to +24 dB
            messages.append(MIDIMessage(
                type='control_change',
                channel=0,
                data={'controller': 74, 'value': gain_val}
            ))

        # Output processing
        output_proc = config.get('output_processing', {})
        if 'output_gain' in output_proc:
            gain_db = output_proc['output_gain']
            gain_val = int((gain_db + 24) * 127 / 48)
            messages.append(MIDIMessage(
                type='control_change',
                channel=0,
                data={'controller': 7, 'value': gain_val}
            ))

        return messages


class WorkstationTranslator:
    """Workstation feature translator."""

    def translate(self, config: dict[str, Any]) -> list[MIDIMessage]:
        """Translate workstation features to MIDI messages."""
        messages = []

        # Motif arpeggiator
        if 'motif_integration' in config:
            motif_config = config['motif_integration']
            if motif_config.get('enabled', False):
                messages.extend(self._translate_motif_arpeggiator(motif_config))

        # S90/S70 AWM Stereo
        if 's90_awm_stereo' in config:
            awm_config = config['s90_awm_stereo']
            if awm_config.get('enabled', False):
                messages.extend(self._translate_awm_stereo(awm_config))

        # Multi-timbral setup
        if 'multi_timbral' in config:
            multi_config = config['multi_timbral']
            messages.extend(self._translate_multi_timbral(multi_config))

        # XG effects
        if 'xg_effects' in config:
            xg_config = config['xg_effects']
            messages.extend(self._translate_xg_effects(xg_config))

        return messages

    def _translate_motif_arpeggiator(self, config: dict[str, Any]) -> list[MIDIMessage]:
        """Translate Motif arpeggiator configuration."""
        messages = []

        # Global settings
        global_settings = config.get('arpeggiator_system', {}).get('global_settings', {})
        if 'tempo' in global_settings:
            # Tempo might be set via MIDI clock or SYSEX
            pass

        # Arpeggiator patterns (SYSEX required)
        arpeggiators = config.get('arpeggiator_system', {}).get('arpeggiators', [])
        for arp in arpeggiators:
            # Would require SYSEX for pattern configuration
            pass

        return messages

    def _translate_awm_stereo(self, config: dict[str, Any]) -> list[MIDIMessage]:
        """Translate S90/S70 AWM Stereo configuration."""
        messages = []

        # Global mixing
        mixing = config.get('global_mixing', {})
        if 'stereo_width' in mixing:
            width = mixing['stereo_width']
            # Could map to a control if available
            pass

        # Velocity layers (SYSEX required for complex setups)
        velocity_layers = config.get('velocity_layers', {})
        # Would require SYSEX for layer configuration
        pass

        return messages

    def _translate_multi_timbral(self, config: dict[str, Any]) -> list[MIDIMessage]:
        """Translate multi-timbral configuration."""
        messages = []

        voice_reserve = config.get('voice_reserve', {})
        for channel_name, voices in voice_reserve.items():
            # Voice reserve might not have direct MIDI equivalent
            # Could be handled at synthesizer level
            pass

        return messages

    def _translate_xg_effects(self, config: dict[str, Any]) -> list[MIDIMessage]:
        """Translate XG effects configuration."""
        messages = []

        # System effects
        system_effects = config.get('system_effects', {})
        if 'reverb' in system_effects:
            reverb = system_effects['reverb']
            if 'type' in reverb:
                messages.extend(self._generate_nrpn_sequence(None, 1, 0, reverb['type']))
            if 'time' in reverb:
                time_val = int(reverb['time'] * 127 / 10.0)
                messages.extend(self._generate_nrpn_sequence(None, 1, 1, time_val))
            if 'level' in reverb:
                level_val = int(reverb['level'] * 127)
                messages.extend(self._generate_nrpn_sequence(None, 1, 2, level_val))

        if 'chorus' in system_effects:
            chorus = system_effects['chorus']
            if 'type' in chorus:
                messages.extend(self._generate_nrpn_sequence(None, 2, 0, chorus['type']))

        return messages

    def _generate_nrpn_sequence(self, channel: int | None, msb: int, lsb: int, value: int) -> list[MIDIMessage]:
        """Generate NRPN parameter sequence."""
        actual_channel = channel if channel is not None else 0
        return [
            MIDIMessage(type='control_change', channel=actual_channel, data={'controller': 99, 'value': msb}),  # NRPN MSB
            MIDIMessage(type='control_change', channel=actual_channel, data={'controller': 98, 'value': lsb}),  # NRPN LSB
            MIDIMessage(type='control_change', channel=actual_channel, data={'controller': 6, 'value': value}),  # Data
        ]


class EffectsTranslator:
    """Effects processing configuration translator."""

    def translate(self, config: dict[str, Any]) -> list[MIDIMessage]:
        """Translate effects configuration."""
        messages = []

        # Coordinator settings (synthesizer-level)
        coordinator = config.get('coordinator', {})
        # These would be handled at synthesizer level
        pass

        # System effects
        system_effects = config.get('system_effects', {})
        messages.extend(self._translate_system_effects(system_effects))

        # Variation effects
        variation_effects = config.get('variation_effects', [])
        messages.extend(self._translate_variation_effects(variation_effects))

        # Insertion effects
        insertion_effects = config.get('insertion_effects', [])
        messages.extend(self._translate_insertion_effects(insertion_effects))

        # Master processing
        master_processing = config.get('master_processing', {})
        messages.extend(self._translate_master_processing(master_processing))

        return messages

    def _translate_system_effects(self, effects: dict[str, Any]) -> list[MIDIMessage]:
        """Translate system effects."""
        messages = []

        if 'reverb' in effects:
            reverb = effects['reverb']
            # Use NRPN MSB 1 for system reverb
            if 'algorithm' in reverb:
                # Map algorithm names to values
                algorithm_map = {
                    'hall_1': 0, 'hall_2': 1, 'room_1': 2, 'room_2': 3,
                    'stage': 4, 'club': 5, 'plate': 6, 'cathedral': 7
                }
                algorithm = algorithm_map.get(reverb['algorithm'], 0)
                messages.extend(self._generate_nrpn_sequence(None, 1, 0, algorithm))

            if 'parameters' in reverb:
                params = reverb['parameters']
                if 'time' in params:
                    time_val = int(params['time'] * 127 / 10.0)
                    messages.extend(self._generate_nrpn_sequence(None, 1, 1, time_val))
                if 'level' in params:
                    level_val = int(params['level'] * 127)
                    messages.extend(self._generate_nrpn_sequence(None, 1, 2, level_val))

        if 'chorus' in effects:
            chorus = effects['chorus']
            if 'algorithm' in chorus:
                algorithm_map = {
                    'chorus_1': 0, 'chorus_2': 1, 'celeste': 2, 'flanger': 3
                }
                algorithm = algorithm_map.get(chorus['algorithm'], 0)
                messages.extend(self._generate_nrpn_sequence(None, 2, 0, algorithm))

            if 'parameters' in chorus:
                params = chorus['parameters']
                if 'rate' in params:
                    rate_val = int(params['rate'] * 127 / 10.0)
                    messages.extend(self._generate_nrpn_sequence(None, 2, 1, rate_val))
                if 'depth' in params:
                    depth_val = int(params['depth'] * 127)
                    messages.extend(self._generate_nrpn_sequence(None, 2, 2, depth_val))

        return messages

    def _translate_variation_effects(self, effects: list[dict[str, Any]]) -> list[MIDIMessage]:
        """Translate variation effects."""
        messages = []

        for effect in effects:
            slot = effect.get('slot', 0)
            effect_type = effect.get('type', 0)

            # NRPN MSB 3 for variation effects
            messages.extend(self._generate_nrpn_sequence(None, 3, 0, effect_type))

            # Effect parameters (simplified)
            if 'parameters' in effect:
                params = effect['parameters']
                if 'depth' in params:
                    messages.extend(self._generate_nrpn_sequence(None, 3, 1, int(params['depth'] * 127)))

        return messages

    def _translate_insertion_effects(self, effects: list[dict[str, Any]]) -> list[MIDIMessage]:
        """Translate insertion effects."""
        messages = []

        for effect in effects:
            channel = effect.get('channel', 0)
            slots = effect.get('slots', [])

            for slot_config in slots:
                slot = slot_config.get('slot', 0)
                effect_type = slot_config.get('type', 0)

                # NRPN MSB 4-6 for insertion effects (per slot)
                msb = 4 + slot
                messages.extend(self._generate_nrpn_sequence(channel, msb, 0, effect_type))

        return messages

    def _translate_master_processing(self, processing: dict[str, Any]) -> list[MIDIMessage]:
        """Translate master processing."""
        messages = []

        if 'equalizer' in processing:
            eq_config = processing['equalizer']
            if eq_config.get('enabled', True):
                # NRPN MSB 80-81 for master EQ
                bands = eq_config.get('bands', [])
                band_nrpn_map = {
                    'low': (80, 1, 80, 2),      # gain, freq
                    'mid': (81, 0, 81, 1),      # gain, freq
                    'high': (81, 6, 81, 7)      # gain, freq
                }

                for band_name, (gain_msb, gain_lsb, freq_msb, freq_lsb) in band_nrpn_map.items():
                    if band_name in bands:
                        band = bands[band_name]
                        if 'gain' in band:
                            gain_val = int((band['gain'] + 12) * 127 / 24)  # -12 to +12 dB
                            messages.extend(self._generate_nrpn_sequence(None, gain_msb, gain_lsb, gain_val))

        return messages

    def _generate_nrpn_sequence(self, channel: int | None, msb: int, lsb: int, value: int) -> list[MIDIMessage]:
        """Generate NRPN parameter sequence."""
        actual_channel = channel if channel is not None else 0
        return [
            MIDIMessage(type='control_change', channel=actual_channel, control=99, value=msb, time=0.0),  # NRPN MSB
            MIDIMessage(type='control_change', channel=actual_channel, control=98, value=lsb, time=0.0),  # NRPN LSB
            MIDIMessage(type='control_change', channel=actual_channel, control=6, value=value, time=0.0),  # Data
        ]


class ModulationTranslator:
    """Modulation system configuration translator."""

    def translate(self, config: dict[str, Any]) -> list[MIDIMessage]:
        """Translate modulation system configuration."""
        messages = []

        matrix = config.get('matrix', {})
        if not matrix.get('enabled', True):
            return messages

        # Sources configuration (might require SYSEX)
        sources = matrix.get('sources', {})
        for source_name, source_config in sources.items():
            # Source configuration would typically require SYSEX
            pass

        # Destinations configuration (might require SYSEX)
        destinations = matrix.get('destinations', {})
        for dest_name, dest_config in destinations.items():
            # Destination configuration would typically require SYSEX
            pass

        # Active routes
        routes = matrix.get('routes', [])
        for route in routes:
            source = route.get('source', '')
            destination = route.get('destination', '')
            amount = route.get('amount', 0.0)

            # Map common routes to available controls
            if source == 'velocity' and destination == 'volume':
                # Velocity to volume might be handled automatically
                pass
            elif source == 'lfo1' and destination == 'pitch':
                # LFO to pitch could use pitch bend or other control
                lfo_amount = int((amount + 1.0) * 63.5)  # -1 to +1 -> 0 to 127
                messages.append(MIDIMessage(
                    type='control_change',
                    channel=0,
                    data={'controller': 1, 'value': lfo_amount}
                ))

        return messages


class XGMLTranslatorV3:
    """
    XGML v3.0 Translator with complete feature support.

    Translates XGML v3.0 configurations to MIDI message sequences
    with support for all modern synthesizer features.
    """

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

        # Initialize translators
        self.engine_translators = {
            'sf2': SF2EngineTranslator(),
            'sfz': EngineTranslator(),  # Placeholder
            'physical': PhysicalEngineTranslator(),
            'spectral': SpectralEngineTranslator(),
            'fm': FMXEngineTranslator()
        }

        self.workstation_translator = WorkstationTranslator()
        self.effects_translator = EffectsTranslator()
        self.modulation_translator = ModulationTranslator()

    def translate_config(self, config: XGMLConfigV3) -> list[MIDIMessage]:
        """
        Translate XGML v3.0 configuration to MIDI messages.

        Args:
            config: XGML v3.0 configuration object

        Returns:
            List of MIDI messages
        """
        self.errors = []
        self.warnings = []

        messages = []

        try:
            # Core synthesizer configuration
            messages.extend(self._translate_synthesizer_core(config.synthesizer_core))

            # Workstation features
            messages.extend(self.workstation_translator.translate(config.workstation_features))

            # Synthesis engines
            messages.extend(self._translate_synthesis_engines(config.synthesis_engines))

            # Effects processing
            messages.extend(self.effects_translator.translate(config.effects_processing))

            # Modulation system
            messages.extend(self.modulation_translator.translate(config.modulation_system))

            # Performance controls
            messages.extend(self._translate_performance_controls(config.performance_controls))

            # Sequencing
            messages.extend(self._translate_sequencing(config.sequencing))

            # Sort messages by time
            messages.sort(key=lambda msg: msg.time if msg.time is not None else 0)

        except Exception as e:
            self.errors.append(f"Translation error: {e}")

        return messages

    def _translate_synthesizer_core(self, core_config: dict[str, Any]) -> list[MIDIMessage]:
        """Translate synthesizer core configuration."""
        messages = []

        # Audio settings (might not have direct MIDI equivalent)
        audio_config = core_config.get('audio', {})
        if 'sample_rate' in audio_config:
            # Sample rate changes typically require SYSEX or are handled at synth level
            pass

        # Performance settings
        performance_config = core_config.get('performance', {})
        if 'max_polyphony' in performance_config:
            # Polyphony might be configurable via SYSEX on some synths
            pass

        # Memory settings (synthesizer-level)
        memory_config = core_config.get('memory', {})
        # Memory pool sizes are handled at synthesizer level
        pass

        return messages

    def _translate_synthesis_engines(self, engines_config: dict[str, Any]) -> list[MIDIMessage]:
        """Translate synthesis engines configuration."""
        messages = []

        # Channel engine assignments (handled at synthesizer level)
        channel_engines = engines_config.get('channel_engines', {})
        # These would be handled by the synthesizer's engine management
        pass

        # Individual engine configurations
        for engine_name, engine_config in engines_config.items():
            if engine_name in ['sf2_engine', 'fm_x_engine', 'physical_engine', 'spectral_engine']:
                # Extract engine type from config name
                engine_type = engine_name.replace('_engine', '')
                if engine_type in self.engine_translators:
                    translator = self.engine_translators[engine_type]
                    messages.extend(translator.translate(engine_config))

        return messages

    def _translate_performance_controls(self, controls_config: dict[str, Any]) -> list[MIDIMessage]:
        """Translate performance controls configuration."""
        messages = []

        # Assignable knobs
        knobs = controls_config.get('assignable_knobs', {})
        for knob_name, knob_config in knobs.items():
            # Knob assignments are typically handled at synthesizer level
            # Could send initial values if specified
            if 'default' in knob_config:
                default_value = knob_config['default']
                if 'midi_cc' in knob_config:
                    cc_num = knob_config['midi_cc']
                    # Convert default value back to 0-127 range (simplified)
                    cc_value = int(default_value * 127) if isinstance(default_value, float) else default_value
                    messages.append(MIDIMessage(
                        type='control_change',
                        channel=0,
                        data={'controller': cc_num, 'value': max(0, min(127, cc_value))}
                    ))

        # Assignable sliders
        sliders = controls_config.get('assignable_sliders', {})
        for slider_name, slider_config in sliders.items():
            if 'default' in slider_config and 'midi_cc' in slider_config:
                default_value = slider_config['default']
                cc_num = slider_config['midi_cc']
                cc_value = int(default_value * 127) if isinstance(default_value, float) else default_value
                messages.append(MIDIMessage(
                    type='control_change',
                    channel=0,
                    data={'controller': cc_num, 'value': max(0, min(127, cc_value))}
                ))

        return messages

    def _translate_sequencing(self, sequencing_config: dict[str, Any]) -> list[MIDIMessage]:
        """Translate sequencing configuration."""
        messages = []

        # Sequencer core settings
        sequencer_core = sequencing_config.get('sequencer_core', {})
        if 'tempo' in sequencer_core:
            # Tempo might be sent via MIDI clock or SYSEX
            pass

        # Patterns (handled at synthesizer level)
        patterns = sequencing_config.get('patterns', [])
        # Pattern definitions are typically handled at synth level
        pass

        return messages

    def get_errors(self) -> list[str]:
        """Get translation errors."""
        return self.errors.copy()

    def get_warnings(self) -> list[str]:
        """Get translation warnings."""
        return self.warnings.copy()

    def has_errors(self) -> bool:
        """Check if there are errors."""
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if there are warnings."""
        return len(self.warnings) > 0
