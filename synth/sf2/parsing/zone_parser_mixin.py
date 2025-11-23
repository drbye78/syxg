"""
Zone Parser Mixin

Common functionality for parsing SF2 zones (generators and modulators)
shared between PresetParser and InstrumentParser.
"""

from typing import Dict, List, Tuple
from abc import ABC, abstractmethod
import struct


class ZoneParserMixin(ABC):
    """
    Mixin providing common zone parsing methods for SF2 presets and instruments.
    """

    @abstractmethod
    def _get_instrument_gen_type(self) -> int:
        """
        Return the generator type for linking to instruments (preset) or samples (instrument).

        Returns:
            Generator type (41 for instrument, 53 for sample)
        """
        pass

    @abstractmethod
    def _set_zone_link_index(self, zone, gen_amount: int, sample_headers=None):
        """
        Set the appropriate link index on the zone.

        Args:
            zone: Zone object to modify
            gen_amount: Generator amount (the index)
            sample_headers: Optional list of sample headers for name lookup
        """
        pass

    def _clamp_generator_value(self, gen_type: int, value: int) -> int:
        """
        Apply bounds checking to generator values according to SF2 specification.

        Args:
            gen_type: Generator type (0-59)
            value: Raw generator value

        Returns:
            Clamped value within valid range
        """
        # SF2 generator ranges from the specification
        ranges = {
            # Sample addressing (0-7)
            0: (-32768, 32767),  # startAddrsOffset
            1: (-32768, 32767),  # endAddrsOffset
            2: (-32768, 32767),  # startloopAddrsOffset
            3: (-32768, 32767),  # endloopAddrsOffset
            4: (-32768, 32767),  # startAddrsCoarseOffset
            5: (-12000, 12000), # modLfoToPitch (cents)
            6: (-12000, 12000), # vibLfoToPitch (cents)
            7: (-12000, 12000), # modEnvToPitch (cents)

            # Filter (8-11)
            8: (1500, 13500),   # initialFilterFc (cents)
            9: (0, 960),        # initialFilterQ (cB)
            10: (-12000, 12000), # modLfoToFilterFc (cents)
            11: (-12000, 12000), # modEnvToFilterFc (cents)

            # Volume envelope (12-20)
            12: (-960, 960),    # modLfoToVolume (cB)
            13: (0, 0),         # unused1
            14: (0, 1000),      # chorusEffectsSend (0.1%)
            15: (0, 1000),      # reverbEffectsSend (0.1%)
            16: (-500, 500),    # pan (0.1%)
            17: (0, 0),         # unused2
            18: (0, 0),         # unused3
            19: (0, 0),         # unused4
            20: (-12000, 5000), # delayModLFO (timecent)

            # LFO (21-27)
            21: (-16000, 4500), # freqModLFO (cent)
            22: (-12000, 5000), # delayVibLFO (timecent)
            23: (-16000, 4500), # freqVibLFO (cent)
            24: (-12000, 5000), # delayModEnv (timecent)
            25: (-12000, 8000), # attackModEnv (timecent)
            26: (-12000, 5000), # holdModEnv (timecent)
            27: (-12000, 8000), # decayModEnv (timecent)

            # More envelope (28-35)
            28: (0, 1000),      # sustainModEnv (0.1%)
            29: (-12000, 8000), # releaseModEnv (timecent)
            30: (-1200, 1200),  # keynumToModEnvHold (tcent/key)
            31: (-1200, 1200),  # keynumToModEnvDecay (tcent/key)
            32: (-12000, 5000), # delayVolEnv (timecent)
            33: (-12000, 8000), # attackVolEnv (timecent)
            34: (-12000, 5000), # holdVolEnv (timecent)
            35: (-12000, 8000), # decayVolEnv (timecent)

            # Volume envelope completion (36-43)
            36: (0, 1440),      # sustainVolEnv (cB)
            37: (-12000, 8000), # releaseVolEnv (timecent)
            38: (-1200, 1200),  # keynumToVolEnvHold (tcent/key)
            39: (-1200, 1200),  # keynumToVolEnvDecay (tcent/key)
            40: (-1, 65535),    # instrument (preset level only)
            41: (-1, 65535),    # reserved1 (used for instrument linking in this implementation)
            42: (0, 0x7F7F),    # keyRange (special handling)
            43: (0, 0x7F7F),    # velRange (special handling)

            # Sample manipulation (44-51)
            44: (-32768, 32767), # startloopAddrsCoarse
            45: (0, 127),       # keynum
            46: (0, 127),       # velocity
            47: (0, 1440),      # initialAttenuation (cB)
            48: (0, 0),         # reserved2
            49: (-32768, 32767), # endloopAddrsCoarse
            50: (-120, 120),    # coarseTune (semitones)
            51: (-99, 99),      # fineTune (cents)

            # More tuning and effects (52-59)
            52: (-1, 65535),    # sampleID (instrument level only)
            53: (-1, 65535),    # sampleModes (used for sample linking in this implementation)
            54: (0, 0),         # reserved3
            55: (0, 1200),      # scaleTuning (cent/key)
            56: (0, 127),       # exclusiveClass
            57: (-1, 127),      # overridingRootKey
            58: (0, 0),         # unused5
            59: (-32768, 32767), # endAddrsCoarseOffset
        }

        if gen_type in ranges:
            min_val, max_val = ranges[gen_type]
            return max(min_val, min(max_val, value))
        else:
            # Unknown generator - clamp to reasonable range
            return max(-32768, min(32767, value))

    def _set_zone_generator_field(self, zone, gen_type: int, gen_amount: int):
        """
        Set the appropriate field on the zone object for this generator.

        Args:
            zone: Zone object to modify
            gen_type: Generator type
            gen_amount: Generator amount (already bounds-checked)
        """
        # Map generator types to zone fields
        generator_field_map = {
            # Sample addressing generators (0-7)
            0: 'startAddrsOffset',
            1: 'endAddrsOffset',
            2: 'startloopAddrsOffset',
            3: 'endloopAddrsOffset',
            4: 'startAddrsCoarseOffset',
            5: 'modLfoToPitch',
            6: 'vibLfoToPitch',
            7: 'modEnvToPitch',

            # Filter generators (8-11)
            8: 'initialFilterFc',
            9: 'initialFilterQ',
            10: 'modLfoToFilterFc',
            11: 'modEnvToFilterFc',

            # Volume envelope generators (12-20)
            12: 'modLfoToVolume',
            13: 'unused1',
            14: 'chorusEffectsSend',
            15: 'reverbEffectsSend',
            16: 'pan',
            17: 'unused2',
            18: 'unused3',
            19: 'unused4',
            20: 'delayModLFO',

            # LFO generators (21-27)
            21: 'freqModLFO',
            22: 'delayVibLFO',
            23: 'freqVibLFO',
            24: 'delayModEnv',
            25: 'attackModEnv',
            26: 'holdModEnv',
            27: 'decayModEnv',

            # More envelope generators (28-35)
            28: 'sustainModEnv',
            29: 'releaseModEnv',
            30: 'keynumToModEnvHold',
            31: 'keynumToModEnvDecay',
            32: 'delayVolEnv',
            33: 'attackVolEnv',
            34: 'holdVolEnv',
            35: 'decayVolEnv',

            # Volume envelope completion (36-43)
            36: 'sustainVolEnv',
            37: 'releaseVolEnv',
            38: 'keynumToVolEnvHold',
            39: 'keynumToVolEnvDecay',
            40: 'instrument',
            41: 'reserved1',

            # Sample manipulation (44-51)
            44: 'startloopAddrsCoarse',
            45: 'keynum',
            46: 'velocity',
            47: 'initialAttenuation',
            48: 'reserved2',
            49: 'endloopAddrsCoarse',
            50: 'coarseTune',
            51: 'fineTune',

            # More tuning and effects (52-59)
            52: 'sampleID',
            53: 'sampleModes',
            54: 'reserved3',
            55: 'scaleTuning',
            56: 'exclusiveClass',
            57: 'overridingRootKey',
            58: 'unused5',
            59: 'endAddrsCoarseOffset',
        }

        if gen_type in generator_field_map:
            field_name = generator_field_map[gen_type]
            if hasattr(zone, field_name):
                setattr(zone, field_name, gen_amount)

                # Synchronize sampleID and sample_index fields
                if field_name == 'sampleID':
                    if hasattr(zone, 'sample_index'):
                        zone.sample_index = gen_amount  # Synchronize with sample_index
                elif field_name == 'sampleModes':
                    # sampleModes is used for sample linking, synchronize both fields
                    if hasattr(zone, 'sampleID'):
                        zone.sampleID = gen_amount
                    if hasattr(zone, 'sample_index'):
                        zone.sample_index = gen_amount

        # Special handling for range generators
        if gen_type == 42:  # keyRange
            zone.keyRange = gen_amount
            zone.lokey = gen_amount & 0xFF
            zone.hikey = (gen_amount >> 8) & 0xFF
        elif gen_type == 43:  # velRange
            zone.velRange = gen_amount
            zone.lovel = gen_amount & 0xFF
            zone.hivel = (gen_amount >> 8) & 0xFF

    def parse_zone_generators(self, zone, gen_data: List[Tuple[int, int]], start_idx: int, end_idx: int):
        """
        Parse generators for a specific zone according to SF2 specification.

        Args:
            zone: The zone to populate
            gen_data: List of generator data [(gen_type, gen_amount), ...]
            start_idx: Starting index in generator data
            end_idx: Ending index (next zone's start or len(gen_data))
        """
        # Configure zone boundaries within the allocated range
        zone_start = start_idx
        zone_end = min(end_idx, len(gen_data))

        # Process generators until terminal or end of allocated range
        for i in range(zone_start, zone_end):
            gen_type, gen_amount = gen_data[i]

            # Terminal generator found - zone ends here
            if gen_type == 0:
                break

            # Apply bounds checking
            clamped_amount = self._clamp_generator_value(gen_type, gen_amount)

            # Store in generators dict
            zone.generators[gen_type] = clamped_amount

            # Set individual zone field
            self._set_zone_generator_field(zone, gen_type, clamped_amount)

            # Handle zone linking (instrument/sample references)
            if gen_type == self._get_instrument_gen_type():
                self._set_zone_link_index(zone, clamped_amount, getattr(self, '_sample_headers', None))

    def _validate_modulator(self, modulator) -> bool:
        """
        Validate a modulator according to SF2 specification.

        Args:
            modulator: SF2Modulator object to validate

        Returns:
            True if modulator is valid, False otherwise
        """
        # Check for terminal modulator (all zeros)
        if (modulator.source_oper == 0 and
            modulator.destination == 0 and
            modulator.amount == 0 and
            modulator.amount_source_oper == 0 and
            modulator.transform == 0):
            return False  # Terminal - valid but indicates end

        # Validate source operator
        source_op = modulator.source_oper

        # Check if CC bit is set (bit 7)
        is_cc = (source_op & 0x80) != 0
        index = source_op & 0x7F

        if is_cc:
            # MIDI CC controller palette
            # Illegal CC numbers: 0, 6, 32, 38, 98-101, 120-127
            illegal_ccs = {0, 6, 32, 38, 98, 99, 100, 101, 120, 121, 122, 123, 124, 125, 126, 127}
            if index in illegal_ccs:
                return False
            # CC numbers 33-63 are LSB for 1-31, which are legal
        else:
            # General controller palette
            # Valid indices: 0, 2, 3, 10, 13, 14, 16
            valid_general = {0, 2, 3, 10, 13, 14, 16}
            if index not in valid_general:
                return False

        # Validate destination
        dest = modulator.destination
        # Destination can be a generator (0-59) or a link (0x8000 + index)
        if dest < 0x8000:
            # Direct generator destination
            if dest > 59:  # Max valid generator
                return False
        else:
            # Linked destination - will be validated during linking
            pass

        # Validate amount source (same rules as source)
        amount_source_op = modulator.amount_source_oper
        if amount_source_op != 0:  # 0 means no amount source
            is_cc_amount = (amount_source_op & 0x80) != 0
            amount_index = amount_source_op & 0x7F

            if is_cc_amount:
                illegal_ccs = {0, 6, 32, 38, 98, 99, 100, 101, 120, 121, 122, 123, 124, 125, 126, 127}
                if amount_index in illegal_ccs:
                    return False
            else:
                valid_general = {0, 2, 3, 10, 13, 14, 16}
                if amount_index not in valid_general:
                    return False

        # Validate transform (0=linear, 2=absolute)
        if modulator.transform not in {0, 2}:
            return False

        # Validate amount range (-32768 to 32767)
        if not (-32768 <= modulator.amount <= 32767):
            return False

        return True

    def _resolve_modulator_cc_numbers(self, modulator):
        """
        Resolve CC controller numbers for modulator sources.

        Args:
            modulator: SF2Modulator object to update
        """
        # Resolve primary source CC
        source_op = modulator.source_oper
        if (source_op & 0x80):  # CC bit set
            cc_num = source_op & 0x7F
            modulator.source_cc = cc_num
        else:
            # General controller palette
            general_to_cc = {
                0: -1,   # No controller
                2: 2,    # Note-on velocity -> velocity CC (but actually from note-on)
                3: 3,    # Note-on key -> key number (but actually from note-on)
                10: 10,  # Poly pressure -> poly pressure CC
                13: 13,  # Channel pressure -> channel pressure CC
                14: 14,  # Pitch wheel -> pitch wheel CC
                16: 16,  # Pitch wheel sensitivity -> RPN parameter
            }
            modulator.source_cc = general_to_cc.get(source_op & 0x7F, -1)

        # Resolve amount source CC
        amount_source_op = modulator.amount_source_oper
        if amount_source_op != 0:
            if (amount_source_op & 0x80):  # CC bit set
                cc_num = amount_source_op & 0x7F
                modulator.amount_cc = cc_num
            else:
                # General controller palette
                general_to_cc = {
                    0: -1,   # No controller
                    2: 2,    # Note-on velocity
                    3: 3,    # Note-on key
                    10: 10,  # Poly pressure
                    13: 13,  # Channel pressure
                    14: 14,  # Pitch wheel
                    16: 16,  # Pitch wheel sensitivity
                }
                modulator.amount_cc = general_to_cc.get(amount_source_op & 0x7F, -1)
        else:
            modulator.amount_cc = -1

    def _process_modulator_linking(self, modulators: List):
        """
        Process linked modulators and resolve circular references.

        Args:
            modulators: List of validated SF2Modulator objects

        Returns:
            List of modulators with invalid links removed
        """
        valid_modulators = []
        link_targets = {}  # dest_index -> source_modulator_index

        for i, mod in enumerate(modulators):
            dest = mod.destination

            if dest >= 0x8000:
                # This is a link to another modulator
                link_index = dest & 0x7FFF  # Remove link bit

                # Validate link index is within bounds
                if link_index >= len(modulators):
                    continue  # Invalid link, skip this modulator

                # Check for circular reference (simplified check)
                if link_index in link_targets and link_targets[link_index] == i:
                    continue  # Circular reference, skip

                # Valid link
                link_targets[i] = link_index

            valid_modulators.append(mod)

        return valid_modulators

    def parse_zone_modulators(self, zone, mod_data: List, start_idx: int, end_idx: int):
        """
        Parse and validate modulators for a specific zone according to SF2 specification.

        Args:
            zone: The zone to populate
            mod_data: List of SF2Modulator objects
            start_idx: Starting index in modulator data
            end_idx: Ending index (next zone's start or len(mod_data))
        """
        # Configure zone boundaries within the allocated range
        zone_start = start_idx
        zone_end = min(end_idx, len(mod_data))

        # Collect valid modulators for this zone
        zone_modulators = []

        # Process modulators until terminal or end of allocated range
        for i in range(zone_start, zone_end):
            modulator = mod_data[i]

            # Check for terminal modulator
            if (modulator.source_oper == 0 and
                modulator.destination == 0 and
                modulator.amount == 0 and
                modulator.amount_source_oper == 0 and
                modulator.transform == 0):
                break

            # Validate modulator
            if not self._validate_modulator(modulator):
                continue  # Skip invalid modulators

            # Resolve CC numbers
            self._resolve_modulator_cc_numbers(modulator)

            # Add to zone modulators
            zone_modulators.append(modulator)

        # Process linking and remove invalid links
        zone_modulators = self._process_modulator_linking(zone_modulators)

        # Add validated modulators to zone
        zone.modulators.extend(zone_modulators)
