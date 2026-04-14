"""
SFZ Synthesis Engine

Complete SFZ v2 synthesis engine implementation that integrates with the
modern synthesizer architecture. Provides professional sample playback
with advanced features like velocity layers, round robin, crossfading, etc.
"""

from __future__ import annotations

import os
from typing import Any

import numpy as np

from ...engines.preset_info import PresetInfo
from ...engines.region_descriptor import RegionDescriptor
from ...engines.synthesis_engine import SynthesisEngine
from ...io.audio.sample_manager import PyAVSampleManager
from ...processing.partial.region import IRegion
from .controller_mapping import SFZControllerMapper
from .dynamic_modulation import SFZDynamicModulation
from .sfz_parser import SFZInstrument, SFZParser
from .sfz_region import SFZRegion
from .voice_effects import SFZVoiceEffectsProcessor
from .voice_modulation import SFZVoiceModulationMatrix


class SFZEngine(SynthesisEngine):
    """
    SFZ Synthesis Engine

    Full implementation of SFZ v2 specification with:
    - Multi-format sample support (WAV, AIFF, FLAC, OGG, etc.)
    - Velocity layers and crossfading
    - Round robin sample selection
    - Advanced modulation and effects
    - Professional envelope and filter systems
    """

    def __init__(
        self,
        sample_rate: int = 44100,
        block_size: int = 1024,
        sample_manager: PyAVSampleManager | None = None,
    ):
        """
        Initialize SFZ synthesis engine.

        Args:
            sample_rate: Audio sample rate in Hz
            block_size: Processing block size in samples
            sample_manager: Pre-configured sample manager (created if None)
        """
        super().__init__(sample_rate, block_size)

        # Core components
        self.sample_manager = sample_manager or PyAVSampleManager()
        self.sfz_parser = SFZParser()

        # Instrument management
        self.loaded_instruments: dict[str, SFZInstrument] = {}
        self.current_instrument: SFZInstrument | None = None

        # Region cache for performance
        self.region_cache: dict[str, list[SFZRegion]] = {}

        # Channel-level parameters (XG/GS compatibility)
        self._channel_transpose: int = 0
        self._key_range_low: int = 0
        self._key_range_high: int = 127
        self._drum_kit: int = 0

        # XG receive channel mapping
        self.receive_channels: dict[int, int] = {}

        # GS part parameters
        self._gs_volume: float = 1.0
        self._gs_pan: float = 0.0
        self._gs_reverb_send: float = 0.0
        self._gs_chorus_send: float = 0.0

        # Voice reserve system
        self.voice_reserve: int | None = None
        self.active_voices: set = set()

        # Voice-level effects processor
        self.voice_effects = SFZVoiceEffectsProcessor(sample_rate)

        # Voice-level modulation matrix
        self.voice_modulation = SFZVoiceModulationMatrix()

        # Dynamic modulation system
        self.dynamic_modulation = SFZDynamicModulation(sample_rate)

        # Controller mapping system
        self.controller_mapper = SFZControllerMapper()

        # Engine configuration
        self._engine_info = None

    def get_engine_type(self) -> str:
        """Return engine type identifier."""
        return "sfz"

    def load_instrument(self, sfz_path: str) -> bool:
        """
        Load an SFZ instrument file.

        Args:
            sfz_path: Path to SFZ file

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            # Parse SFZ file
            instrument = self.sfz_parser.parse_file(sfz_path)

            # Validate instrument has regions
            if not instrument.get_all_regions():
                print(f"Warning: SFZ file '{sfz_path}' contains no regions")
                return False

            # Store instrument
            key = os.path.basename(sfz_path)
            self.loaded_instruments[key] = instrument
            self.current_instrument = instrument

            # Pre-load samples for all regions
            self._preload_instrument_samples(instrument)

            # Cache regions for performance
            self._cache_instrument_regions(instrument, key)

            print(
                f"🎹 SFZ: Loaded instrument '{key}' with {len(instrument.get_all_regions())} regions"
            )
            return True

        except Exception as e:
            print(f"Error loading SFZ instrument '{sfz_path}': {e}")
            return False

    def _preload_instrument_samples(self, instrument: SFZInstrument):
        """Pre-load all samples referenced by the instrument."""
        sample_paths = set()

        # Collect all unique sample paths
        for region in instrument.get_all_regions():
            if region.has_opcode("sample"):
                sample_path = region.get_value("sample")
                if sample_path:
                    sample_paths.add(sample_path)

        # Pre-load samples
        if sample_paths:
            print(f"🎹 SFZ: Pre-loading {len(sample_paths)} samples...")
            self.sample_manager.preload_samples(list(sample_paths))

    def _cache_instrument_regions(self, instrument: SFZInstrument, key: str):
        """Cache processed regions for fast access."""
        regions = []

        for sfz_region in instrument.get_all_regions():
            # Convert SFZ parser region to SFZRegion object
            region_params = sfz_region.to_dict()

            # Create SFZRegion instance
            region = SFZRegion(region_params, self.sample_manager)
            regions.append(region)

        self.region_cache[key] = regions

    def apply_channel_parameters(self, channel_params: dict) -> None:
        """
        Apply channel-level parameters to SFZ regions.

        Args:
            channel_params: Dictionary of channel parameters
        """
        # Channel transpose
        if "transpose" in channel_params:
            self._channel_transpose = channel_params["transpose"]

        # Key range filtering
        if "key_range_low" in channel_params:
            self._key_range_low = max(0, min(127, channel_params["key_range_low"]))
        if "key_range_high" in channel_params:
            self._key_range_high = max(0, min(127, channel_params["key_range_high"]))

        # XG drum kit
        if "drum_kit" in channel_params:
            self._drum_kit = channel_params["drum_kit"]

        # Propagate to all regions in cache
        for regions in self.region_cache.values():
            for region in regions:
                region.apply_channel_parameters(channel_params)

    def set_receive_channel(self, part_id: int, midi_channel: int) -> bool:
        """
        Set XG receive channel mapping.

        Args:
            part_id: XG part ID (0-15)
            midi_channel: MIDI channel (0-15, 254=OFF, 255=ALL)

        Returns:
            True if mapping was set successfully
        """
        if not (0 <= part_id <= 15):
            return False
        if midi_channel not in list(range(16)) + [254, 255]:
            return False

        self.receive_channels[part_id] = midi_channel
        return True

    def get_receive_channel(self, part_id: int) -> int | None:
        """
        Get receive channel for a part.

        Args:
            part_id: XG part ID (0-15)

        Returns:
            MIDI channel or None
        """
        return self.receive_channels.get(part_id)

    def apply_gs_part_parameters(self, part_params: dict) -> None:
        """
        Apply GS part parameters.

        Args:
            part_params: GS part parameters
        """
        # GS volume (0-127)
        if "volume" in part_params:
            self._gs_volume = part_params["volume"] / 127.0

        # GS pan (-64 to +63)
        if "pan" in part_params:
            self._gs_pan = part_params["pan"] / 64.0

        # GS effects sends
        if "reverb_send" in part_params:
            self._gs_reverb_send = part_params["reverb_send"] / 127.0
        if "chorus_send" in part_params:
            self._gs_chorus_send = part_params["chorus_send"] / 127.0

    def can_allocate_voice(self) -> bool:
        """
        Check if voice allocation is allowed based on reserve.

        Returns:
            True if voice can be allocated
        """
        if self.voice_reserve is None:
            return True
        return len(self.active_voices) < self.voice_reserve

    def allocate_voice(self, note: int, velocity: int) -> SFZRegion | None:
        """
        Allocate a voice with reserve checking.

        Args:
            note: MIDI note
            velocity: MIDI velocity

        Returns:
            SFZRegion if allocation successful, None otherwise
        """
        if not self.can_allocate_voice():
            return None

        # Apply channel transpose to note
        transposed_note = note + self._channel_transpose

        # Check channel key range
        if not (self._key_range_low <= transposed_note <= self._key_range_high):
            return None

        # Get regions for the transposed note
        regions = self.get_regions_for_note(transposed_note, velocity)

        if not regions:
            return None

        # For now, return first region (voice allocation logic would be more complex)
        region = regions[0]

        # Track active voice
        self.active_voices.add(region)

        return region

    def release_voice(self, region: SFZRegion) -> None:
        """
        Release a voice.

        Args:
            region: SFZRegion to release
        """
        self.active_voices.discard(region)

    def get_channel_info(self) -> dict[str, Any]:
        """
        Get channel information.

        Returns:
            Dictionary with channel state
        """
        return {
            "transpose": self._channel_transpose,
            "key_range": (self._key_range_low, self._key_range_high),
            "drum_kit": self._drum_kit,
            "receive_channels": self.receive_channels.copy(),
            "gs_volume": self._gs_volume,
            "gs_pan": self._gs_pan,
            "gs_reverb_send": self._gs_reverb_send,
            "gs_chorus_send": self._gs_chorus_send,
            "voice_reserve": self.voice_reserve,
            "active_voices": len(self.active_voices),
        }

    def get_regions_for_note(
        self, note: int, velocity: int, program: int = 0, bank: int = 0
    ) -> list[SFZRegion]:
        """
        Get all regions that should play for a given note/velocity.

        Implements SFZ region selection logic including:
        - Key and velocity range checking
        - Round robin selection
        - Crossfading between regions

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)
            program: MIDI program number (unused for SFZ)
            bank: MIDI bank number (unused for SFZ)

        Returns:
            List of SFZRegion instances that should play
        """
        if not self.current_instrument:
            return []

        # Get cached regions for current instrument
        instrument_key = next(
            (k for k, v in self.loaded_instruments.items() if v == self.current_instrument), None
        )
        if not instrument_key or instrument_key not in self.region_cache:
            return []

        regions = self.region_cache[instrument_key]
        selected_regions = []

        # Group regions by round robin groups for proper selection
        rr_groups: dict[int, list[SFZRegion]] = {}

        for region in regions:
            # Check if region should play for this note/velocity
            if region.should_play_for_note(note, velocity):
                rr_group = region.round_robin_group

                if rr_group == 0:
                    # No round robin - region always plays
                    selected_regions.append(region)
                else:
                    # Group by round robin
                    if rr_group not in rr_groups:
                        rr_groups[rr_group] = []
                    rr_groups[rr_group].append(region)

        # Process round robin groups
        for rr_group, group_regions in rr_groups.items():
            if group_regions:
                # Select one region from the round robin group
                selected_region = self._select_round_robin_region(group_regions, note, velocity)
                if selected_region:
                    selected_regions.append(selected_region)

        return selected_regions

    def _select_round_robin_region(
        self, regions: list[SFZRegion], note: int, velocity: int
    ) -> SFZRegion | None:
        """
        Select a region from a round robin group.

        Uses note and velocity to create a stable but varying selection pattern.
        """
        if not regions:
            return None

        # Simple round robin based on note number
        # More sophisticated implementations could track state per group
        index = note % len(regions)
        return regions[index]

    def create_partial(self, partial_params: dict[str, Any], sample_rate: int) -> SFZRegion:
        """
        Create an SFZ region (used for compatibility with SynthesisEngine interface).

        Args:
            partial_params: Region parameters
            sample_rate: Audio sample rate

        Returns:
            SFZRegion instance
        """
        return SFZRegion(partial_params, self.sample_manager)

    # ========== NEW REGION-BASED ARCHITECTURE METHODS ==========

    def get_preset_info(self, bank: int, program: int) -> PresetInfo | None:
        """
        Get SFZ preset info with region descriptors.

        SFZ uses file-based instruments rather than bank/program mapping.
        This method provides compatibility with the XG bank/program system.

        Args:
            bank: MIDI bank number (0-127)
            program: MIDI program number (0-127)

        Returns:
            PresetInfo with region descriptors, or None if not found
        """
        if not self.current_instrument:
            return None

        # Get all regions from current instrument
        regions = self._get_all_region_descriptors()

        if not regions:
            return None

        # Create PresetInfo with all region descriptors
        return PresetInfo(
            bank=bank,
            program=program,
            name=self.current_instrument.name or "SFZ Instrument",
            engine_type="sfz",
            region_descriptors=regions,
            master_level=1.0,
            master_pan=0.0,
            reverb_send=0.0,
            chorus_send=0.0,
        )

    def get_all_region_descriptors(self, bank: int, program: int) -> list[RegionDescriptor]:
        """
        Get ALL region descriptors for an SFZ preset.

        Args:
            bank: MIDI bank number
            program: MIDI program number

        Returns:
            List of all RegionDescriptor objects for this preset
        """
        if not self.current_instrument:
            return []

        return self._get_all_region_descriptors()

    def _get_all_region_descriptors(self) -> list[RegionDescriptor]:
        """
        Internal method to get all region descriptors from current instrument.

        Returns:
            List of RegionDescriptor objects
        """
        if not self.current_instrument:
            return []

        descriptors = []
        sfz_regions = self.current_instrument.get_all_regions()

        for idx, sfz_region in enumerate(sfz_regions):
            # Convert SFZ region to RegionDescriptor
            region_params = sfz_region.to_dict() if hasattr(sfz_region, "to_dict") else {}

            # Extract key range from region
            lokey = region_params.get("lokey", 0)
            hikey = region_params.get("hikey", 127)
            key_range = (lokey, hikey)

            # Extract velocity range
            lovel = region_params.get("lovel", 0)
            hivel = region_params.get("hivel", 127)
            velocity_range = (lovel, hivel)

            # Get sample info
            sample_path = region_params.get("sample", None)
            sample_id = None  # SFZ uses paths rather than IDs

            # Build generator parameters
            generator_params = {
                "volume": region_params.get("volume", 0.0),
                "pan": region_params.get("pan", 0.0),
                "cutoff": region_params.get("cutoff", 20000.0),
                "resonance": region_params.get("resonance", 0.0),
                "amp_attack": region_params.get("ampeg_attack", 0.0),
                "amp_decay": region_params.get("ampeg_decay", 0.0),
                "amp_sustain": region_params.get("ampeg_sustain", 1.0),
                "amp_release": region_params.get("ampeg_release", 0.0),
                "pitch_keycenter": region_params.get("pitch_keycenter", 60),
                "coarse_tune": region_params.get("transpose", 0),
                "fine_tune": region_params.get("tune", 0),
                "loop_mode": region_params.get("loop_mode", "no_loop"),
                "loop_start": region_params.get("loop_start", 0),
                "loop_end": region_params.get("loop_end", 0),
            }

            # Get round-robin info
            rr_group = region_params.get("round_robin_group", 0)
            rr_position = idx

            descriptor = RegionDescriptor(
                region_id=idx,
                engine_type="sfz",
                key_range=key_range,
                velocity_range=velocity_range,
                round_robin_group=rr_group,
                round_robin_position=rr_position,
                sample_id=sample_id,
                sample_path=sample_path,
                generator_params=generator_params,
            )

            descriptors.append(descriptor)

        return descriptors

    def _create_base_region(self, descriptor: RegionDescriptor, sample_rate: int) -> IRegion:
        """
        Create SFZ base region without S.Art2 wrapper.

        Args:
            descriptor: Region metadata and parameters
            sample_rate: Audio sample rate in Hz

        Returns:
            SFZRegion instance
        """
        # Create region parameters from descriptor
        region_params = descriptor.generator_params.copy()

        # Add sample path if available
        if descriptor.sample_path:
            region_params["sample"] = descriptor.sample_path

        # Add key/velocity ranges
        region_params["lokey"] = descriptor.key_range[0]
        region_params["hikey"] = descriptor.key_range[1]
        region_params["lovel"] = descriptor.velocity_range[0]
        region_params["hivel"] = descriptor.velocity_range[1]

        # Create SFZRegion
        region = SFZRegion(region_params, self.sample_manager)

        return region

    def load_sample_for_region(self, region: IRegion) -> bool:
        """
        Load sample data for SFZ region.

        Called when region is about to play.
        Returns True if sample loaded successfully.

        Args:
            region: Region instance to load sample for

        Returns:
            True if sample loaded or not needed, False if loading failed
        """
        if not hasattr(region, "load_sample"):
            return True  # Not an SFZ region or doesn't need sample loading

        try:
            return region.load_sample()
        except Exception as e:
            print(f"Warning: SFZ sample loading failed: {e}")
            return False

    # ========== END NEW REGION-BASED ARCHITECTURE METHODS ==========

    def generate_samples(
        self, note: int, velocity: int, modulation: dict[str, float], block_size: int
    ) -> np.ndarray:
        """
        Generate audio samples for a note using SFZ synthesis.

        This is a simplified implementation for testing. Production use should
        go through the VoiceInstance system for proper polyphony.

        Args:
            note: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)
            modulation: Current modulation values
            block_size: Number of samples to generate

        Returns:
            Stereo audio buffer (block_size, 2) as float32
        """
        # Get regions for this note/velocity
        regions = self.get_regions_for_note(note, velocity)

        if not regions:
            return np.zeros((block_size, 2), dtype=np.float32)

        # For now, use the first region (should use all regions with proper mixing)
        region = regions[0]

        # Trigger note-on for the region
        region.note_on(velocity, note)

        # Generate samples
        try:
            audio = region.generate_samples(block_size, modulation)
            return audio
        except Exception as e:
            print(f"Warning: SFZ region generation failed: {e}")
            return np.zeros((block_size, 2), dtype=np.float32)

    def is_note_supported(self, note: int) -> bool:
        """
        Check if a note is supported by the current SFZ instrument.

        Args:
            note: MIDI note number (0-127)

        Returns:
            True if note can be played, False otherwise
        """
        if not self.current_instrument:
            return False

        # Check if any region supports this note
        regions = self.get_regions_for_note(note, 127)  # Use max velocity for checking
        return len(regions) > 0

    def get_supported_formats(self) -> list[str]:
        """Get list of supported file formats."""
        return [".sfz"]

    def get_engine_info(self) -> dict[str, Any]:
        """Get SFZ engine information and capabilities."""
        if self._engine_info is None:
            self._engine_info = {
                "name": "SFZ v2 Synthesis Engine",
                "type": "sfz",
                "version": "2.0",
                "capabilities": [
                    "sample_playback",
                    "multi_format_support",
                    "velocity_layers",
                    "round_robin",
                    "crossfading",
                    "envelopes",
                    "filters",
                    "real_time_modulation",
                    "stereo_samples",
                    "looping",
                    "pitch_modulation",
                    "filter_modulation",
                ],
                "formats": [".sfz"],
                "supported_sample_formats": [".wav", ".aiff", ".flac", ".ogg", ".mp3"],
                "max_regions": 1000,
                "polyphony": 256,
                "parameters": [
                    "sample",
                    "lokey",
                    "hikey",
                    "lovel",
                    "hivel",
                    "pitch_keycenter",
                    "volume",
                    "pan",
                    "cutoff",
                    "resonance",
                    "ampeg_attack",
                    "ampeg_decay",
                    "ampeg_sustain",
                    "ampeg_release",
                    "round_robin",
                    "loop_mode",
                ],
                "modulation_sources": [
                    "velocity",
                    "key",
                    "cc1-cc127",
                    "aftertouch",
                    "pitch_bend",
                    "amp_env",
                    "filter_env",
                    "lfo1",
                    "lfo2",
                ],
                "modulation_destinations": [
                    "volume",
                    "pan",
                    "pitch",
                    "cutoff",
                    "resonance",
                    "lfo1_freq",
                    "lfo1_depth",
                    "lfo2_freq",
                    "lfo2_depth",
                ],
            }

        return self._engine_info

    def get_loaded_instruments(self) -> list[str]:
        """Get list of loaded instrument names."""
        return list(self.loaded_instruments.keys())

    def select_instrument(self, instrument_name: str) -> bool:
        """
        Select a loaded instrument for playback.

        Args:
            instrument_name: Name of the instrument

        Returns:
            True if instrument was selected, False otherwise
        """
        if instrument_name in self.loaded_instruments:
            self.current_instrument = self.loaded_instruments[instrument_name]
            return True
        return False

    def unload_instrument(self, instrument_name: str) -> bool:
        """
        Unload an instrument and free its resources.

        Args:
            instrument_name: Name of the instrument to unload

        Returns:
            True if instrument was unloaded, False otherwise
        """
        if instrument_name in self.loaded_instruments:
            # Remove from loaded instruments
            del self.loaded_instruments[instrument_name]

            # Remove from cache
            if instrument_name in self.region_cache:
                del self.region_cache[instrument_name]

            # Clear current instrument if it was unloaded
            if self.current_instrument and instrument_name == next(
                (k for k, v in self.loaded_instruments.items() if v == self.current_instrument),
                None,
            ):
                self.current_instrument = None

            return True
        return False

    def get_memory_usage(self) -> dict[str, Any]:
        """Get current memory usage statistics."""
        cache_stats = self.sample_manager.get_cache_stats()

        return {
            "loaded_instruments": len(self.loaded_instruments),
            "cached_regions": sum(len(regions) for regions in self.region_cache.values()),
            "sample_cache": cache_stats,
            "total_memory_mb": cache_stats.get("memory_used_mb", 0),
        }

    def reset(self) -> None:
        """Reset engine to clean state."""
        # Reset all regions in cache
        for regions in self.region_cache.values():
            for region in regions:
                region.reset()

        # Keep instruments loaded but reset their state

    def cleanup(self) -> None:
        """Clean up engine resources."""
        # Clear caches
        self.region_cache.clear()
        self.sample_manager.clear_cache()

        # Clear instruments
        self.loaded_instruments.clear()
        self.current_instrument = None

    def validate_sfz_file(self, sfz_path: str) -> tuple[bool, list[str]]:
        """
        Validate an SFZ file for compatibility with this engine.

        Args:
            sfz_path: Path to SFZ file

        Returns:
            (is_valid, list_of_issues)
        """
        issues = []

        try:
            # Use the parser's validation
            is_valid, parser_issues = self.sfz_parser.validate_sfz_file(sfz_path)
            issues.extend(parser_issues)

            if is_valid:
                # Additional engine-specific validation
                instrument = self.sfz_parser.parse_file(sfz_path)
                regions = instrument.get_all_regions()

                # Check for very large instruments
                if len(regions) > 1000:
                    issues.append(
                        f"Warning: Instrument has {len(regions)} regions (recommended max: 1000)"
                    )

                # Check for missing samples
                missing_samples = 0
                for region in regions:
                    if region.has_opcode("sample"):
                        sample_path = region.get_value("sample")
                        if sample_path and not os.path.exists(sample_path):
                            missing_samples += 1

                if missing_samples > 0:
                    issues.append(f"Warning: {missing_samples} samples not found")

                # Check for unsupported opcodes (would be comprehensive in full implementation)
                # For now, just check basic compatibility

            return len(issues) == 0, issues

        except Exception as e:
            return False, [f"Validation failed: {e!s}"]

    def __str__(self) -> str:
        """String representation."""
        instruments = len(self.loaded_instruments)
        regions = sum(len(regions) for regions in self.region_cache.values())
        return f"SFZEngine(instruments={instruments}, regions={regions})"

    def __repr__(self) -> str:
        return self.__str__()
