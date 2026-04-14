"""
Enhanced NRPN Mapper for Yamaha S.Art2 with Genos2 compatibility.

Provides category-based NRPN mapping, reverse lookup, and parameter control
for advanced articulation management.
"""

from __future__ import annotations

from typing import Any


def midi_note_to_frequency(note: int) -> float:
    """Convert MIDI note number to frequency (A4 = 440Hz at note 69)."""
    SEMITONE_RATIO = 1.059463359
    return 440.0 * (SEMITONE_RATIO ** (note - 69))


class YamahaNRPNMapper:
    """
    Enhanced NRPN mapper for Yamaha S.Art2 articulations with Genos2 compatibility.

    Features:
    - Category-based NRPN mapping (13 categories, 275+ articulations)
    - Reverse lookup (articulation → NRPN)
    - Category hints for disambiguation
    - Backward compatible with simplified map

    Usage:
        mapper = YamahaNRPNMapper()

        # Get articulation from NRPN
        art = mapper.get_articulation(1, 1)  # 'legato'
        art = mapper.get_articulation(3, 10, 'wind_sax')  # 'key_click_sax'

        # Get NRPN from articulation (reverse lookup)
        msb, lsb = mapper.get_nrpn_for_articulation('legato')  # (1, 1)
        msb, lsb = mapper.get_nrpn_for_articulation('spiccato', 'strings_bow')
    """

    # Category names for each MSB
    MSB_CATEGORIES = {
        1: "common",
        2: "dynamics",
        3: "wind_sax",
        4: "wind_brass",
        5: "wind_woodwind",
        6: "strings_bow",
        7: "strings_pluck",
        8: "guitar",
        9: "vocal",
        10: "synth",
        11: "percussion",
        12: "ethnic",
        13: "effects",
    }

    def __init__(self):
        # Category-based NRPN mappings (275+ articulations)
        self.nrpn_to_articulation: dict[tuple[int, int, str], str] = {}

        # Reverse mapping: articulation → (msb, lsb, category)
        self.articulation_to_nrpn: dict[str, tuple[int, int, str]] = {}

        # Simplified lookup for backward compatibility
        self._simplified_map: dict[tuple[int, int], str] = {}

        # Category mappings for quick access
        self.category_maps: dict[str, dict[tuple[int, int], str]] = {
            "common": {},
            "dynamics": {},
            "wind_sax": {},
            "wind_brass": {},
            "wind_woodwind": {},
            "strings_bow": {},
            "strings_pluck": {},
            "guitar": {},
            "vocal": {},
            "synth": {},
            "percussion": {},
            "ethnic": {},
            "effects": {},
        }

        # Initialize all mappings
        self._initialize_mappings()

    def _initialize_mappings(self) -> None:
        """Initialize all NRPN mappings from articulation_controller."""
        # Import articulation map from controller
        from .articulation_controller import ArticulationController

        for (msb, lsb), articulation in ArticulationController.NRPN_ARTICULATION_MAP.items():
            # Get category for this MSB
            category = self.MSB_CATEGORIES.get(msb, "common")

            # Add to category-based map
            key = (msb, lsb, category)
            self.nrpn_to_articulation[key] = articulation

            # Add to reverse map
            self.articulation_to_nrpn[articulation] = key

            # Add to category-specific map
            self.category_maps[category][(msb, lsb)] = articulation

            # Add to simplified map (first occurrence wins)
            if (msb, lsb) not in self._simplified_map:
                self._simplified_map[(msb, lsb)] = articulation

    def get_articulation(self, msb: int, lsb: int, category: str | None = None) -> str:
        """
        Get articulation from NRPN MSB/LSB values.

        Args:
            msb: NRPN MSB (0-127)
            lsb: NRPN LSB (0-127)
            category: Optional category hint for disambiguation

        Returns:
            Articulation name

        Examples:
            >>> mapper = YamahaNRPNMapper()
            >>> mapper.get_articulation(1, 1)
            'legato'
            >>> mapper.get_articulation(3, 10, 'wind_sax')
            'key_click_sax'
            >>> mapper.get_articulation(6, 7, 'strings_bow')
            'spiccato'
        """
        # Validate input range
        msb = max(0, min(127, msb))
        lsb = max(0, min(127, lsb))

        # Try category-specific lookup first if provided
        if category and category in self.category_maps:
            if (msb, lsb) in self.category_maps[category]:
                return self.category_maps[category][(msb, lsb)]

        # Try to infer category from MSB
        if msb in self.MSB_CATEGORIES:
            inferred_category = self.MSB_CATEGORIES[msb]
            if (msb, lsb) in self.category_maps.get(inferred_category, {}):
                return self.category_maps[inferred_category][(msb, lsb)]

        # Fall back to simplified map
        return self._simplified_map.get((msb, lsb), "normal")

    def get_nrpn_for_articulation(
        self, articulation: str, category: str | None = None
    ) -> tuple[int, int]:
        """
        Get NRPN MSB/LSB for articulation (reverse lookup).

        Args:
            articulation: Articulation name
            category: Optional category hint for disambiguation

        Returns:
            Tuple of (msb, lsb)

        Examples:
            >>> mapper = YamahaNRPNMapper()
            >>> mapper.get_nrpn_for_articulation('legato')
            (1, 1)
            >>> mapper.get_nrpn_for_articulation('spiccato', 'strings_bow')
            (6, 7)
        """
        if articulation not in self.articulation_to_nrpn:
            return (1, 0)  # Default to normal

        msb, lsb, art_category = self.articulation_to_nrpn[articulation]

        # If category hint provided and matches, use it
        if category and category != art_category:
            # Search in specified category
            if category in self.category_maps:
                for (m, l), art in self.category_maps[category].items():
                    if art == articulation:
                        return (m, l)

        return (msb, lsb)

    def get_category_for_msb(self, msb: int) -> str:
        """
        Get category name for MSB value.

        Args:
            msb: NRPN MSB value

        Returns:
            Category name
        """
        return self.MSB_CATEGORIES.get(msb, "common")

    def get_msb_for_category(self, category: str) -> int | None:
        """
        Get MSB value for category name.

        Args:
            category: Category name

        Returns:
            MSB value or None if not found
        """
        for msb, cat in self.MSB_CATEGORIES.items():
            if cat == category:
                return msb
        return None

    def get_articulations_by_category(self, category: str) -> list[str]:
        """
        Get all articulations in a category.

        Args:
            category: Category name

        Returns:
            List of articulation names
        """
        if category not in self.category_maps:
            return []

        return list(self.category_maps[category].values())

    def get_all_categories(self) -> list[str]:
        """Get list of all available categories."""
        return list(self.MSB_CATEGORIES.values())

    def get_articulation_count(self) -> int:
        """Get total number of articulations."""
        return len(self.articulation_to_nrpn)

    def get_category_count(self, category: str) -> int:
        """Get number of articulations in a category."""
        if category not in self.category_maps:
            return 0
        return len(self.category_maps[category])

    def search_articulations(self, pattern: str) -> list[tuple[str, int, int]]:
        """
        Search for articulations matching a pattern.

        Args:
            pattern: Search pattern (case-insensitive substring)

        Returns:
            List of (articulation, msb, lsb) tuples

        Examples:
            >>> mapper.search_articulations('vibrato')
            [('vibrato', 1, 4), ('molto_vibrato', 1, 38), ...]
        """
        pattern_lower = pattern.lower()
        results = []

        for articulation, (msb, lsb, _) in self.articulation_to_nrpn.items():
            if pattern_lower in articulation.lower():
                results.append((articulation, msb, lsb))

        return sorted(results, key=lambda x: x[0])


class NRPNParameterController:
    """
    Advanced NRPN controller for articulation parameters.

    Supports:
    - Multi-parameter NRPN sequences
    - Parameter value ranges (0-16383)
    - Relative parameter changes
    - Parameter groups by articulation

    NRPN Parameter Format:
        MSB 99: Parameter number MSB
        LSB 98: Parameter number LSB
        MSB 6:  Value MSB (0-127)
        LSB 38: Value LSB (0-127)

        Value = (MSB6 << 7) | LSB38  (0-16383)

    Usage:
        controller = NRPNParameterController()

        # Set vibrato rate
        result = controller.process_parameter_nrpn(99, 0, 64)
        # Returns: {'articulation': 'vibrato', 'param': 'rate', 'value': 0.64}

        # Build parameter NRPN message
        msb, lsb = controller.get_nrpn_for_parameter('vibrato', 'rate')
    """

    # Parameter NRPN mappings
    # Format: (param_msb, param_lsb): (articulation, param_name, scale, offset)
    PARAMETER_MAPPINGS = {
        # Vibrato parameters (param MSB 0)
        (0, 0): ("vibrato", "rate", 0.01, 0.0),  # 0-127 → 0.0-1.27 Hz
        (0, 1): ("vibrato", "depth", 0.001, 0.0),  # 0-16383 → 0.0-16.38
        (0, 2): ("vibrato", "delay", 0.001, 0.0),  # 0-16383 → 0.0-16.38 sec
        # Legato parameters (param MSB 1)
        (1, 0): ("legato", "blend", 0.0001, 0.0),  # 0-16383 → 0.0-1.638
        (1, 1): ("legato", "transition_time", 0.00001, 0.0),  # 0-16383 → 0.0-0.16 sec
        # Growl parameters (param MSB 2)
        (2, 0): ("growl", "mod_freq", 1.0, 0.0),  # 0-127 → 0-127 Hz
        (2, 1): ("growl", "depth", 0.0001, 0.0),  # 0-16383 → 0.0-1.638
        # Dynamics parameters (param MSB 3)
        (3, 0): ("dynamics", "volume", 0.0001, 0.0),  # 0-16383 → 0.0-1.638
        (3, 1): ("dynamics", "tone_darkness", 0.0001, 0.0),
        (3, 2): ("dynamics", "tone_brightness", 0.0001, 0.0),
        # Saxophone parameters (param MSB 4)
        (4, 0): ("sub_tone_sax", "breath_level", 0.0001, 0.0),
        (4, 1): ("key_click_sax", "click_level", 0.0001, 0.0),
        (4, 2): ("key_click_sax", "timing", 0.00001, -0.1),  # -0.1 to +0.06 sec
        # Brass parameters (param MSB 5)
        (5, 0): ("straight_mute", "mute_level", 0.0001, 0.0),
        (5, 1): ("plunger_mute", "wah_freq", 10.0, 100.0),  # 100-163930 Hz
        # Strings parameters (param MSB 6)
        (6, 0): ("con_sordino", "mute_level", 0.0001, 0.0),
        (6, 1): ("tremolo", "speed", 0.1, 0.0),  # 0-127 → 0-12.7 Hz
        (6, 2): ("portamento_fast", "speed", 0.001, 0.0),
        # Guitar parameters (param MSB 7)
        (7, 0): ("bend_gtr", "semitones", 0.01, 0.0),  # 0-127 → 0-1.27 semitones
        (7, 1): ("bend_gtr", "speed", 0.001, 0.0),  # 0-16383 → 0-16.38 sec
        (7, 2): ("palm_mute_gtr", "pressure", 0.0001, 0.0),
        # Vocal parameters (param MSB 8)
        (8, 0): ("vocal_breath", "breath_level", 0.0001, 0.0),
        (8, 1): ("vocal_attack", "hardness", 0.0001, 0.0),
        (8, 2): ("falsetto", "brightness", 0.0001, 0.0),
        # Synth parameters (param MSB 9)
        (9, 0): ("filter_sweep", "cutoff_start", 10.0, 20.0),  # 20-163850 Hz
        (9, 1): ("filter_sweep", "cutoff_end", 10.0, 20.0),
        (9, 2): ("lfo_sync", "rate", 0.01, 0.0),  # 0-127 → 0-1.27 Hz
        # Effects parameters (param MSB 10)
        (10, 0): ("fx_sweep_up", "duration", 0.01, 0.0),  # 0-127 → 0-1.27 sec
        (10, 1): ("fx_noise", "level", 0.0001, 0.0),
        (10, 2): ("fx_hit", "impact", 0.0001, 0.0),
    }

    def __init__(self):
        """Initialize NRPN parameter controller."""
        self.current_param_msb = 0
        self.current_param_lsb = 0
        self.pending_value_msb = None
        self.pending_value_lsb = None

    def process_parameter_nrpn(
        self, param_msb: int, param_lsb: int, value: int
    ) -> dict[str, Any] | None:
        """
        Process NRPN parameter change.

        Args:
            param_msb: Parameter MSB (0-127)
            param_lsb: Parameter LSB (0-127)
            value: Parameter value (0-16383)

        Returns:
            Parameter update dict or None if not recognized

        Example:
            >>> controller = NRPNParameterController()
            >>> result = controller.process_parameter_nrpn(0, 0, 64)
            >>> result
            {'articulation': 'vibrato', 'param_name': 'rate', 'value': 0.64, 'raw_value': 64}
        """
        key = (param_msb, param_lsb)

        if key not in self.PARAMETER_MAPPINGS:
            return None

        articulation, param_name, scale, offset = self.PARAMETER_MAPPINGS[key]

        return {
            "articulation": articulation,
            "param_name": param_name,
            "value": value * scale + offset,
            "raw_value": value,
            "param_msb": param_msb,
            "param_lsb": param_lsb,
        }

    def get_nrpn_for_parameter(self, articulation: str, param_name: str) -> tuple[int, int] | None:
        """
        Get NRPN MSB/LSB for a parameter (reverse lookup).

        Args:
            articulation: Articulation name
            param_name: Parameter name

        Returns:
            Tuple of (param_msb, param_lsb) or None

        Example:
            >>> controller = NRPNParameterController()
            >>> controller.get_nrpn_for_parameter('vibrato', 'rate')
            (0, 0)
        """
        for (param_msb, param_lsb), (art, param, _, _) in self.PARAMETER_MAPPINGS.items():
            if art == articulation and param == param_name:
                return (param_msb, param_lsb)

        return None

    def build_parameter_value(self, value_msb: int, value_lsb: int) -> int:
        """
        Build 14-bit parameter value from MSB/LSB.

        Args:
            value_msb: Value MSB (0-127)
            value_lsb: Value LSB (0-127)

        Returns:
            14-bit value (0-16383)
        """
        return (value_msb << 7) | value_lsb

    def split_parameter_value(self, value: int) -> tuple[int, int]:
        """
        Split 14-bit value into MSB/LSB.

        Args:
            value: 14-bit value (0-16383)

        Returns:
            Tuple of (value_msb, value_lsb)
        """
        value = max(0, min(16383, value))
        return (value >> 7, value & 0x7F)

    def get_parameter_range(self, param_msb: int, param_lsb: int) -> dict[str, float] | None:
        """
        Get valid range for a parameter.

        Args:
            param_msb: Parameter MSB
            param_lsb: Parameter LSB

        Returns:
            Dict with min_value, max_value, scale, offset
        """
        key = (param_msb, param_lsb)

        if key not in self.PARAMETER_MAPPINGS:
            return None

        articulation, param_name, scale, offset = self.PARAMETER_MAPPINGS[key]

        return {
            "articulation": articulation,
            "param_name": param_name,
            "min_value": 0 * scale + offset,
            "max_value": 16383 * scale + offset,
            "scale": scale,
            "offset": offset,
        }

    def get_all_parameters(self) -> list[dict[str, Any]]:
        """
        Get all available parameters.

        Returns:
            List of parameter info dicts
        """
        params = []

        for (param_msb, param_lsb), (
            articulation,
            param_name,
            scale,
            offset,
        ) in self.PARAMETER_MAPPINGS.items():
            params.append(
                {
                    "param_msb": param_msb,
                    "param_lsb": param_lsb,
                    "articulation": articulation,
                    "param_name": param_name,
                    "scale": scale,
                    "offset": offset,
                    "min_value": 0 * scale + offset,
                    "max_value": 16383 * scale + offset,
                }
            )

        return params
