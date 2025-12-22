"""
Enhanced SF2 Modulation System

Handles advanced SF2 modulation with real-time processing, LFO modulation,
envelope modulation, and controller-based routing.
"""

from typing import Dict, List, Any, Optional, Callable
import math
import time
import numpy as np
from ..types import SF2Modulator, SF2InstrumentZone


class AdvancedModulator:
    """
    Advanced modulation processor with real-time capabilities.

    Supports LFO, envelope, and controller-based modulation with
    sophisticated routing and transform options.
    """

    def __init__(self, modulator_data: Dict[str, Any]):
        """
        Initialize advanced modulator.

        Args:
            modulator_data: Modulator configuration dictionary
        """
        self.source = modulator_data.get('source', 'velocity')
        self.destination = modulator_data.get('destination', 'amplitude')
        self.amount = modulator_data.get('amount', 0.0)
        self.polarity = modulator_data.get('polarity', 1.0)
        self.transform = modulator_data.get('transform', 'linear')

        # Advanced modulation parameters
        self.velocity_sensitivity = modulator_data.get('velocity_sensitivity', 0.0)
        self.key_scaling = modulator_data.get('key_scaling', 0.0)
        self.bipolar = modulator_data.get('bipolar', False)

        # LFO parameters (if LFO source)
        self.lfo_rate = modulator_data.get('lfo_rate', 5.0)  # Hz
        self.lfo_depth = modulator_data.get('lfo_depth', 1.0)
        self.lfo_waveform = modulator_data.get('lfo_waveform', 'sine')
        self.lfo_phase = modulator_data.get('lfo_phase', 0.0)

        # Envelope parameters (if envelope source)
        self.env_attack = modulator_data.get('env_attack', 0.01)
        self.env_decay = modulator_data.get('env_decay', 0.3)
        self.env_sustain = modulator_data.get('env_sustain', 0.7)
        self.env_release = modulator_data.get('env_release', 0.5)

        # State variables
        self.lfo_phase_accumulator = 0.0
        self.env_state = 'idle'
        self.env_value = 0.0
        self.env_time = 0.0
        self.last_note_on_time = 0.0
        self.last_note_off_time = 0.0

        # Controller state
        self.controller_value = 0.0
        self.controller_last_value = 0.0
        self.controller_smoothing = 0.0

    def process_sample(self, dt: float, note: int = 60, velocity: int = 100,
                      controllers: Dict[str, float] = None) -> float:
        """
        Process one sample of modulation.

        Args:
            dt: Time delta in seconds
            note: MIDI note number
            velocity: MIDI velocity
            controllers: Current controller values

        Returns:
            Modulation output value (-1.0 to 1.0)
        """
        controllers = controllers or {}

        # Get base modulation value
        base_value = self._get_source_value(note, velocity, controllers)

        # Apply velocity sensitivity
        if self.velocity_sensitivity > 0.0:
            velocity_factor = velocity / 127.0
            base_value *= (1.0 - self.velocity_sensitivity) + (self.velocity_sensitivity * velocity_factor)

        # Apply key scaling
        if self.key_scaling != 0.0:
            # Scale based on distance from middle C (note 60)
            key_offset = (note - 60) / 60.0  # Normalize to ±1 range
            key_factor = 1.0 + (key_offset * self.key_scaling)
            base_value *= key_factor

        # Apply transform
        transformed_value = self._apply_transform(base_value)

        # Apply polarity and amount
        output = transformed_value * self.amount * self.polarity

        # Convert to bipolar if needed
        if not self.bipolar and output < 0:
            output = 0.0

        return output

    def note_on(self, note: int, velocity: int):
        """Handle note-on event."""
        self.last_note_on_time = time.time()
        self.env_state = 'attack'
        self.env_time = 0.0
        self.env_value = 0.0

        # Reset LFO phase if needed
        if self.source.startswith('lfo'):
            self.lfo_phase_accumulator = self.lfo_phase

    def note_off(self):
        """Handle note-off event."""
        self.last_note_off_time = time.time()
        self.env_state = 'release'

    def set_controller(self, controller: str, value: float):
        """Set controller value with smoothing."""
        self.controller_last_value = self.controller_value
        self.controller_value = value

        # Simple smoothing
        self.controller_smoothing = (self.controller_last_value + self.controller_value) * 0.5

    def _get_source_value(self, note: int, velocity: int, controllers: Dict[str, float]) -> float:
        """Get modulation source value."""
        if self.source == 'velocity':
            return velocity / 127.0
        elif self.source == 'note':
            return note / 127.0
        elif self.source == 'aftertouch':
            return controllers.get('aftertouch', 0.0) / 127.0
        elif self.source == 'pitch_wheel':
            return controllers.get('pitch_wheel', 0.0) / 16384.0
        elif self.source.startswith('cc_'):
            cc_num = int(self.source.split('_')[1])
            return controllers.get(f'cc_{cc_num}', 0.0) / 127.0
        elif self.source.startswith('lfo'):
            return self._process_lfo(1.0 / 44100.0)  # Assume 44.1kHz
        elif self.source == 'amp_env':
            return self._process_envelope(1.0 / 44100.0)
        elif self.source == 'filter_env':
            return self._process_envelope(1.0 / 44100.0)
        elif self.source == 'pitch_env':
            return self._process_envelope(1.0 / 44100.0)
        else:
            return 0.0

    def _process_lfo(self, dt: float) -> float:
        """Process LFO modulation."""
        # Update phase
        self.lfo_phase_accumulator += self.lfo_rate * dt * 2.0 * math.pi

        # Generate waveform
        if self.lfo_waveform == 'sine':
            return math.sin(self.lfo_phase_accumulator)
        elif self.lfo_waveform == 'triangle':
            phase = self.lfo_phase_accumulator / (2.0 * math.pi)
            return 2.0 * abs(2.0 * (phase - math.floor(phase + 0.5))) - 1.0
        elif self.lfo_waveform == 'square':
            return 1.0 if math.sin(self.lfo_phase_accumulator) >= 0 else -1.0
        elif self.lfo_waveform == 'sawtooth':
            phase = self.lfo_phase_accumulator / (2.0 * math.pi)
            return 2.0 * (phase - math.floor(phase + 0.5))
        else:
            return math.sin(self.lfo_phase_accumulator)

    def _process_envelope(self, dt: float) -> float:
        """Process envelope modulation."""
        self.env_time += dt

        if self.env_state == 'attack':
            if self.env_time >= self.env_attack:
                self.env_value = 1.0
                self.env_state = 'decay'
                self.env_time = 0.0
            else:
                self.env_value = self.env_time / self.env_attack

        elif self.env_state == 'decay':
            if self.env_time >= self.env_decay:
                self.env_value = self.env_sustain
                self.env_state = 'sustain'
            else:
                decay_progress = self.env_time / self.env_decay
                self.env_value = 1.0 - decay_progress * (1.0 - self.env_sustain)

        elif self.env_state == 'sustain':
            self.env_value = self.env_sustain

        elif self.env_state == 'release':
            if self.env_time >= self.env_release:
                self.env_value = 0.0
                self.env_state = 'idle'
            else:
                release_progress = self.env_time / self.env_release
                self.env_value = self.env_sustain * (1.0 - release_progress)

        elif self.env_state == 'idle':
            self.env_value = 0.0

        return self.env_value

    def _apply_transform(self, value: float) -> float:
        """Apply modulation transform."""
        if self.transform == 'linear':
            return value
        elif self.transform == 'concave':
            # Exponential curve (softer at low values)
            return math.pow(value, 0.5) if value >= 0 else -math.pow(-value, 0.5)
        elif self.transform == 'convex':
            # Logarithmic curve (softer at high values)
            sign = 1.0 if value >= 0 else -1.0
            abs_value = abs(value)
            return sign * math.pow(abs_value, 2.0)
        elif self.transform == 'switch':
            # Hard switch at 0.5
            return 1.0 if value >= 0.5 else 0.0
        else:
            return value


class AdvancedModulationProcessor:
    """
    Advanced modulation processor with multiple modulators and routing.

    Handles complex modulation scenarios with multiple sources, destinations,
    and real-time processing capabilities.
    """

    def __init__(self):
        """Initialize advanced modulation processor."""
        self.modulators: List[AdvancedModulator] = []
        self.modulation_matrix: Dict[str, List[Dict[str, Any]]] = {}
        self.sample_rate = 44100
        self.block_size = 1024

    def add_modulator(self, modulator_config: Dict[str, Any]) -> int:
        """
        Add a modulator to the processor.

        Args:
            modulator_config: Modulator configuration

        Returns:
            Modulator ID
        """
        modulator = AdvancedModulator(modulator_config)
        self.modulators.append(modulator)

        # Update modulation matrix
        destination = modulator_config.get('destination', 'amplitude')
        if destination not in self.modulation_matrix:
            self.modulation_matrix[destination] = []

        self.modulation_matrix[destination].append({
            'modulator_id': len(self.modulators) - 1,
            'amount': modulator_config.get('amount', 1.0),
            'polarity': modulator_config.get('polarity', 1.0)
        })

        return len(self.modulators) - 1

    def process_block(self, block_size: int, note: int = 60, velocity: int = 100,
                     controllers: Dict[str, float] = None) -> Dict[str, np.ndarray]:
        """
        Process a block of modulation.

        Args:
            block_size: Number of samples to process
            note: MIDI note number
            velocity: MIDI velocity
            controllers: Controller values

        Returns:
            Dictionary of modulation outputs by destination
        """
        import numpy as np

        controllers = controllers or {}
        dt = 1.0 / self.sample_rate

        # Initialize output buffers
        outputs = {}
        for dest in self.modulation_matrix.keys():
            outputs[dest] = np.zeros(block_size, dtype=np.float32)

        # Process each sample
        for i in range(block_size):
            for dest, modulators in self.modulation_matrix.items():
                sample_value = 0.0

                for mod_info in modulators:
                    mod_id = mod_info['modulator_id']
                    if mod_id < len(self.modulators):
                        mod_value = self.modulators[mod_id].process_sample(
                            dt, note, velocity, controllers
                        )
                        sample_value += mod_value * mod_info['amount'] * mod_info['polarity']

                outputs[dest][i] = sample_value

        return outputs

    def note_on(self, note: int, velocity: int):
        """Handle note-on for all modulators."""
        for modulator in self.modulators:
            modulator.note_on(note, velocity)

    def note_off(self):
        """Handle note-off for all modulators."""
        for modulator in self.modulators:
            modulator.note_off()

    def set_controller(self, controller: str, value: float):
        """Set controller value for all modulators."""
        for modulator in self.modulators:
            if modulator.source == controller or modulator.source.startswith(f'{controller}_'):
                modulator.set_controller(controller, value)

    def get_modulator_info(self, mod_id: int) -> Optional[Dict[str, Any]]:
        """Get information about a specific modulator."""
        if 0 <= mod_id < len(self.modulators):
            mod = self.modulators[mod_id]
            return {
                'source': mod.source,
                'destination': mod.destination,
                'amount': mod.amount,
                'polarity': mod.polarity,
                'transform': mod.transform,
                'velocity_sensitivity': mod.velocity_sensitivity,
                'key_scaling': mod.key_scaling,
                'bipolar': mod.bipolar
            }
        return None

    def remove_modulator(self, mod_id: int):
        """Remove a modulator."""
        if 0 <= mod_id < len(self.modulators):
            del self.modulators[mod_id]

            # Update modulation matrix
            for dest in self.modulation_matrix:
                self.modulation_matrix[dest] = [
                    m for m in self.modulation_matrix[dest]
                    if m['modulator_id'] != mod_id
                ]

                # Update remaining modulator IDs
                for m in self.modulation_matrix[dest]:
                    if m['modulator_id'] > mod_id:
                        m['modulator_id'] -= 1


class ModulationConverter:
    """
    Converts SF2 modulation parameters to XG synthesizer format.
    """

    # Complete SF2 to XG destination mapping (all 61 generators)
    SF2_TO_XG_DESTINATIONS = {
        # Sample addressing (0-7)
        0: "start_offset",  # startAddrsOffset
        1: "end_offset",  # endAddrsOffset
        2: "start_loop_offset",  # startloopAddrsOffset
        3: "end_loop_offset",  # endloopAddrsOffset
        4: "start_coarse_offset",  # startAddrsCoarseOffset
        5: "pitch",  # modLfoToPitch
        6: "pitch",  # vibLfoToPitch
        7: "pitch",  # modEnvToPitch

        # Filter parameters (8-11)
        8: "filter_cutoff",  # initialFilterFc
        9: "filter_resonance",  # initialFilterQ
        10: "filter_cutoff",  # modLfoToFilterFc
        11: "filter_cutoff",  # modEnvToFilterFc

        # Volume envelope (12-20)
        12: "amplitude",  # modLfoToVolume
        15: "reverb_send",  # reverbEffectsSend
        16: "chorus_send",  # chorusEffectsSend
        17: "pan",  # pan
        21: "lfo1_delay",  # delayModLFO

        # LFO parameters (21-27)
        22: "lfo1_rate",  # freqModLFO
        23: "lfo2_delay",  # delayVibLFO
        24: "lfo2_rate",  # freqVibLFO
        25: "filter_delay",  # delayModEnv
        26: "filter_attack",  # attackModEnv
        27: "filter_hold",  # holdModEnv

        # More envelope parameters (28-35)
        28: "filter_decay",  # decayModEnv
        29: "filter_sustain",  # sustainModEnv
        30: "filter_release",  # releaseModEnv
        31: "filter_hold",  # keynumToModEnvHold
        32: "filter_decay",  # keynumToModEnvDecay
        33: "amp_delay",  # delayVolEnv
        34: "amp_attack",  # attackVolEnv
        35: "amp_hold",  # holdVolEnv

        # Volume envelope completion (36-43)
        36: "amp_decay",  # decayVolEnv
        37: "amp_sustain",  # sustainVolEnv
        38: "amp_release",  # releaseVolEnv
        39: "amp_hold",  # keynumToVolEnvHold
        40: "amp_decay",  # keynumToVolEnvDecay
        41: "instrument",  # instrument (not used in zones)
        44: "start_loop_coarse",  # startloopAddrsCoarse
        43: "key_range",  # keyRange
        44: "vel_range",  # velRange

        # Sample manipulation (45-52)
        45: "start_loop_coarse",  # startloopAddrsCoarse
        46: "key_number",  # keynum
        47: "velocity",  # velocity
        48: "amplitude",  # initialAttenuation
        50: "end_loop_coarse",  # endloopAddrsCoarse
        51: "coarse_tune",  # coarseTune
        52: "fine_tune",  # fineTune

        # More parameters (53-60)
        53: "sample_id",  # sampleID
        54: "sample_modes",  # sampleModes
        55: "scale_tuning",  # scaleTuning
        56: "exclusive_class",  # exclusiveClass
        57: "root_key",  # overridingRootKey
        58: "end_coarse_offset",  # endAddrsCoarseOffset

        # Legacy CC destinations (for backward compatibility)
        77: "tremolo_depth",  # cc_tremolo_depth
        78: "tremolo_rate"  # cc_tremolo_rate
    }

    # SF2 to XG source mapping
    SF2_TO_XG_SOURCES = {
        "note_on_velocity": "velocity",
        "channel_aftertouch": "after_touch",
        "cc_mod_wheel": "mod_wheel",
        "modLFO": "lfo1",
        "vibLFO": "lfo2",
        "modEnv": "amp_env",
        "pitch_wheel": "pitch_wheel",
        "cc_brightness": "brightness",
        "cc_tremolo_depth": "tremolo_depth",
        "cc_tremolo_rate": "tremolo_rate",
        "cc_portamento_control": "portamento"
    }

    def __init__(self):
        """Initialize modulation converter."""
        pass

    def convert_modulator(self, modulator: SF2Modulator) -> Optional[Dict[str, Any]]:
        """
        Convert complete SF2 modulator to XG modulation route with all advanced features.

        Args:
            modulator: SF2 modulator with full feature set

        Returns:
            XG modulation route dictionary or None if unsupported
        """
        # Get source name with advanced source resolution
        source_name = self._get_modulator_source_name_advanced(modulator)
        if not source_name:
            return None

        # Get destination name
        destination_name = self._get_modulator_destination_name(modulator.destination)
        if not destination_name:
            return None

        # Convert amount with proper SF2 scaling
        amount = self._normalize_modulator_amount_advanced(modulator.amount, modulator.destination)

        # Handle polarity and direction
        polarity = 1.0 if modulator.source_polarity == 0 else -1.0
        if modulator.source_direction == 1:  # Reverse direction
            polarity *= -1.0

        # Handle transform
        transform_type = "linear"
        if modulator.transform == 1:
            transform_type = "absolute"

        # Create comprehensive modulation route
        route = {
            "source": source_name,
            "destination": destination_name,
            "amount": amount * polarity,
            "velocity_sensitivity": 0.0,
            "key_scaling": 0.0,
            "transform": transform_type,
            "source_type": self._source_type_to_name(modulator.source_type),
            "control_source": None,
            "amount_source": None
        }

        # Add secondary control source if present
        if modulator.control_oper != 0:
            control_name = self._get_control_source_name(modulator)
            if control_name:
                route["control_source"] = control_name
                route["control_polarity"] = 1.0 if modulator.control_polarity == 0 else -1.0
                route["control_type"] = self._source_type_to_name(modulator.control_type)
                if modulator.control_direction == 1:
                    route["control_polarity"] *= -1.0

        # Add amount modulation source if present
        if modulator.amount_source_oper != 0:
            amount_name = self._get_amount_source_name(modulator)
            if amount_name:
                route["amount_source"] = amount_name
                route["amount_polarity"] = 1.0 if modulator.amount_source_polarity == 0 else -1.0
                route["amount_type"] = self._source_type_to_name(modulator.amount_source_type)
                if modulator.amount_source_direction == 1:
                    route["amount_polarity"] *= -1.0

        return route

    def process_zone_modulators(self, zone: SF2InstrumentZone) -> Dict[str, Any]:
        """
        Process all modulators in a zone and extract useful parameters.

        Args:
            zone: SF2 instrument zone

        Returns:
            Dictionary with extracted modulation parameters
        """
        params = {
            "lfo1_to_pitch": 0.0,
            "lfo2_to_pitch": 0.0,
            "env_to_pitch": 0.0,
            "aftertouch_to_pitch": 0.0,
            "lfo_to_filter": 0.0,
            "env_to_filter": 0.0,
            "aftertouch_to_filter": 0.0,
            "tremolo_depth": 0.0,
            "vibrato_depth": 0.0,
            "vibrato_rate": 5.0,
            "vibrato_delay": 0.0
        }

        for modulator in zone.modulators:
            self._process_single_modulator(zone, modulator, params)

        return params

    def calculate_modulation_params(self, zones: List[SF2InstrumentZone]) -> Dict[str, Any]:
        """
        Calculate modulation parameters from multiple zones.

        Args:
            zones: List of SF2 instrument zones

        Returns:
            Dictionary with modulation parameters
        """
        # Start with default values
        params = {
            "lfo1_to_pitch": 0.0,
            "lfo2_to_pitch": 0.0,
            "env_to_pitch": 0.0,
            "aftertouch_to_pitch": 0.0,
            "lfo_to_filter": 0.0,
            "env_to_filter": 0.0,
            "aftertouch_to_filter": 0.0,
            "tremolo_depth": 0.0,
            "vibrato_depth": 0.0,
            "vibrato_rate": 5.0,
            "vibrato_delay": 0.0
        }

        # Accumulate values from all zones
        for zone in zones:
            zone_params = self.process_zone_modulators(zone)
            for key in params:
                params[key] += zone_params[key]

        # Average values across zones
        num_zones = len(zones)
        if num_zones > 0:
            for key in params:
                if key not in ["vibrato_rate", "vibrato_delay"]:  # Don't average these
                    params[key] /= num_zones
                # Clamp to reasonable ranges
                if key not in ["vibrato_rate", "vibrato_delay"]:
                    params[key] = max(0.0, min(1.0, params[key]))

        return params

    def _get_modulator_source_name(self, modulator: SF2Modulator) -> Optional[str]:
        """
        Get modulation source name from SF2 modulator.

        Args:
            modulator: SF2 modulator

        Returns:
            Source name or None if unsupported
        """
        # Check main source
        if modulator.source_oper in [0, 1, 2, 3, 4, 5, 16, 17, 18, 19, 20, 21, 22, 23, 32, 33, 34, 35, 36, 37, 38, 39, 40, 74, 77, 78, 84]:
            source_name = self._source_oper_to_name(modulator.source_oper)

            # Add index for CC controllers
            if source_name.startswith("cc_") and modulator.source_index > 0:
                source_name = f"{source_name}_{modulator.source_index}"

            return source_name

        # Check for LFO sources
        if modulator.source_oper == 5:
            return "modLFO"
        elif modulator.source_oper == 6:
            return "vibLFO"
        elif modulator.source_oper == 7:
            return "modEnv"
        elif modulator.source_oper == 13:
            return "channel_aftertouch"

        return None

    def _get_modulator_destination_name(self, destination: int) -> Optional[str]:
        """
        Get modulation destination name from SF2 destination code.

        Args:
            destination: SF2 destination code

        Returns:
            Destination name or None if unsupported
        """
        return self.SF2_TO_XG_DESTINATIONS.get(destination)

    def _normalize_modulator_amount(self, amount: int, destination: int) -> float:
        """
        Normalize modulation amount based on destination.

        Args:
            amount: Raw modulation amount
            destination: Modulation destination

        Returns:
            Normalized amount
        """
        abs_amount = abs(amount)

        # Pitch modulation (in cents)
        if destination in [5, 6, 7]:
            return abs_amount / 100.0  # 100 = 1 cent

        # Filter cutoff
        elif destination in [8, 10, 11]:
            return abs_amount / 1000.0  # Normalize to 0-1

        # Amplitude
        elif destination in [13, 31, 33, 34, 35]:
            return abs_amount / 1000.0  # Normalize to 0-1

        # Pan
        elif destination == 17:
            return abs_amount / 100.0  # 0-100 in SF2 -> 0-1

        # Tremolo
        elif destination in [77, 78]:
            return abs_amount / 1000.0  # Normalize to 0-1

        # Default normalization
        else:
            return abs_amount / 1000.0

    def _process_single_modulator(self, zone: SF2InstrumentZone, modulator: SF2Modulator, params: Dict[str, Any]):
        """
        Process a single modulator and update zone parameters.

        Args:
            zone: SF2 instrument zone
            modulator: SF2 modulator
            params: Parameters dictionary to update
        """
        source_name = self._get_modulator_source_name(modulator)
        if not source_name:
            return

        destination = modulator.destination
        amount = self._normalize_modulator_amount(modulator.amount, destination)
        polarity = 1.0 if modulator.source_polarity == 0 else -1.0

        # Update zone attributes and params dictionary
        if destination == 5:  # modLfoToPitch
            zone.mod_lfo_to_pitch = amount * polarity
            params["lfo1_to_pitch"] += amount * polarity
        elif destination == 6:  # vibLfoToPitch
            zone.vib_lfo_to_pitch = amount * polarity
            params["lfo2_to_pitch"] += amount * polarity
            params["vibrato_depth"] += amount * polarity
        elif destination == 7:  # modEnvToPitch
            zone.mod_env_to_pitch = amount * polarity
            params["env_to_pitch"] += amount * polarity
        elif destination == 10:  # modLfoToFilterFc
            zone.mod_lfo_to_filter = amount * polarity
            params["lfo_to_filter"] += amount * polarity
        elif destination == 11:  # modEnvToFilterFc
            zone.mod_env_to_filter = amount * polarity
            params["env_to_filter"] += amount * polarity
        elif destination == 13:  # modLfoToVolume
            zone.mod_lfo_to_volume = amount * polarity
            params["tremolo_depth"] += amount * polarity
        elif destination == 77:  # cc_tremolo_depth
            zone.tremolo_depth = amount * polarity
            params["tremolo_depth"] += amount * polarity
        elif destination == 84:  # cc_portamento_control
            zone.portamento_to_pitch = amount * polarity

    def _get_modulator_source_name_advanced(self, modulator: SF2Modulator) -> Optional[str]:
        """
        Get advanced modulator source name with full SF2 support.

        Args:
            modulator: SF2 modulator

        Returns:
            Source name or None if unsupported
        """
        # Resolve CC number for source
        if modulator.source_oper >= 16 and modulator.source_oper <= 95:
            cc_number = (modulator.source_oper - 16) % 32
            if modulator.source_index > 0:
                cc_number = modulator.source_index  # Use explicit index if provided
            modulator.source_cc = cc_number
            return f"cc_{cc_number}"
        elif modulator.source_oper == 0:
            return "no_controller"
        elif modulator.source_oper == 1:
            return "note_on_velocity"
        elif modulator.source_oper == 2:
            return "note_on_key_number"
        elif modulator.source_oper == 3:
            return "polyphonic_aftertouch"
        elif modulator.source_oper == 4:
            return "channel_aftertouch"
        elif modulator.source_oper == 5:
            return "pitch_wheel"
        elif modulator.source_oper == 7:
            return "channel_aftertouch"  # Alternative aftertouch
        elif modulator.source_oper == 10:
            return "polyphonic_aftertouch"  # Alternative poly aftertouch
        elif modulator.source_oper == 13:
            return "channel_aftertouch"  # Another aftertouch variant
        else:
            return None

    def _get_control_source_name(self, modulator: SF2Modulator) -> Optional[str]:
        """
        Get control source name for secondary modulation.

        Args:
            modulator: SF2 modulator

        Returns:
            Control source name or None
        """
        # Similar logic to source name but for control
        if modulator.control_oper >= 16 and modulator.control_oper <= 95:
            cc_number = (modulator.control_oper - 16) % 32
            if modulator.control_index > 0:
                cc_number = modulator.control_index
            modulator.control_cc = cc_number
            return f"cc_{cc_number}"
        elif modulator.control_oper == 1:
            return "note_on_velocity"
        elif modulator.control_oper == 2:
            return "note_on_key_number"
        elif modulator.control_oper == 3:
            return "polyphonic_aftertouch"
        elif modulator.control_oper == 4:
            return "channel_aftertouch"
        elif modulator.control_oper == 5:
            return "pitch_wheel"
        else:
            return None

    def _get_amount_source_name(self, modulator: SF2Modulator) -> Optional[str]:
        """
        Get amount source name for depth modulation.

        Args:
            modulator: SF2 modulator

        Returns:
            Amount source name or None
        """
        # Similar logic for amount source
        if modulator.amount_source_oper >= 16 and modulator.amount_source_oper <= 95:
            cc_number = (modulator.amount_source_oper - 16) % 32
            if modulator.amount_source_index > 0:
                cc_number = modulator.amount_source_index
            modulator.amount_cc = cc_number
            return f"cc_{cc_number}"
        elif modulator.amount_source_oper == 1:
            return "note_on_velocity"
        elif modulator.amount_source_oper == 2:
            return "note_on_key_number"
        elif modulator.amount_source_oper == 3:
            return "polyphonic_aftertouch"
        elif modulator.amount_source_oper == 4:
            return "channel_aftertouch"
        elif modulator.amount_source_oper == 5:
            return "pitch_wheel"
        else:
            return None

    def _source_type_to_name(self, source_type: int) -> str:
        """
        Convert SF2 source type to name.

        Args:
            source_type: SF2 source type (0=linear, 1=concave, 2=convex, 3=switch)

        Returns:
            Source type name
        """
        type_map = {
            0: "linear",
            1: "concave",
            2: "convex",
            3: "switch"
        }
        return type_map.get(source_type, "linear")

    def _normalize_modulator_amount_advanced(self, amount: int, destination: int) -> float:
        """
        Normalize modulation amount with advanced SF2 scaling.

        Args:
            amount: Raw modulation amount
            destination: Modulation destination

        Returns:
            Normalized amount (-1.0 to +1.0)
        """
        # SF2 amounts are 16-bit signed integers (-32768 to +32767)
        # Convert to float and normalize based on destination
        float_amount = amount / 32768.0

        # Scale based on destination type
        if destination in [5, 6, 7]:  # Pitch modulation (in cents)
            return float_amount * 1200.0  # ±1200 cents range
        elif destination in [8, 10, 11]:  # Filter cutoff
            return float_amount * 9600.0  # ±9600 cents range
        elif destination in [12, 13]:  # Volume
            return float_amount * 1440.0  # ±1440 centibels range
        elif destination == 17:  # Pan
            return float_amount * 500.0  # ±500 pan units
        elif destination in [51, 52]:  # Tuning
            return float_amount * 100.0  # ±100 cents
        else:
            return float_amount  # Default ±1.0 range

    def _source_oper_to_name(self, source_oper: int) -> str:
        """
        Convert SF2 source operator to source name (legacy method).

        Args:
            source_oper: SF2 source operator code

        Returns:
            Source name
        """
        source_map = {
            0: "no_controller",
            1: "note_on_velocity",
            2: "note_on_key_number",
            3: "polyphonic_aftertouch",
            4: "channel_aftertouch",
            5: "pitch_wheel",
            16: "cc_mod_wheel",
            17: "cc_breath_controller",
            18: "cc_unknown_18",
            19: "cc_foot_controller",
            20: "cc_portamento_time",
            21: "cc_data_entry",
            22: "cc_volume",
            23: "cc_balance",
            32: "cc_bank_select_lsb",
            33: "cc_mod_wheel_lsb",
            34: "cc_breath_controller_lsb",
            35: "cc_unknown_35_lsb",
            36: "cc_foot_controller_lsb",
            37: "cc_portamento_time_lsb",
            38: "cc_data_entry_lsb",
            39: "cc_volume_lsb",
            40: "cc_balance_lsb",
            74: "cc_brightness",
            77: "cc_tremolo_depth",
            78: "cc_tremolo_rate",
            84: "cc_portamento_control"
        }

        return source_map.get(source_oper, "unknown_source")
