"""
Wavetable Region - Production-grade wavetable synthesis region.

Part of the unified region-based synthesis architecture.
WavetableRegion implements wavetable synthesis with:
- Real-time wavetable morphing
- Multi-oscillator unison with detuning
- Filter with envelope modulation
- Wavetable position modulation
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from ..engine.region_descriptor import RegionDescriptor
from ..partial.region import IRegion, RegionState

logger = logging.getLogger(__name__)


class WavetableRegion(IRegion):
    """
    Production-grade wavetable region with morphing and unison support.

    Features:
    - Real-time wavetable scanning and morphing
    - Up to 8 unison voices with detuning
    - Lowpass/highpass filter with resonance
    - Velocity-based filter modulation
    - Aftertouch-based morph control

    Attributes:
        descriptor: Region metadata with wavetable parameters
        sample_rate: Audio sample rate
        wavetable_bank: Shared wavetable bank for sample access
    """

    __slots__ = [
        "_aftertouch_to_morph",
        "_detune_amount",
        "_envelope",
        "_filter",
        "_filter_cutoff",
        "_filter_envelope_amount",
        "_filter_resonance",
        "_morph_speed",
        "_oscillators",
        "_unison_voices",
        "_velocity_to_filter",
        "_wavetable_name",
        "_wavetable_position",
        "wavetable_bank",
    ]

    def __init__(
        self,
        descriptor: RegionDescriptor,
        sample_rate: int = 44100,
        wavetable_bank: Any | None = None,
    ):
        """
        Initialize wavetable region.

        Args:
            descriptor: Region metadata with wavetable parameters
            sample_rate: Audio sample rate in Hz
            wavetable_bank: Optional wavetable bank for loading wavetables
        """
        super().__init__(descriptor, sample_rate)
        self.wavetable_bank = wavetable_bank

        # Get parameters from descriptor
        algo_params = descriptor.algorithm_params or {}

        # Wavetable parameters
        self._wavetable_name = algo_params.get("wavetable", "default")
        self._wavetable_position = algo_params.get("wavetable_position", 0.0)
        self._morph_speed = algo_params.get("morph_speed", 0.0)

        # Unison parameters
        self._unison_voices = algo_params.get("unison_voices", 1)
        self._detune_amount = algo_params.get("detune_amount", 0.0)

        # Filter parameters
        self._filter_cutoff = algo_params.get("filter_cutoff", 20000.0)
        self._filter_resonance = algo_params.get("filter_resonance", 0.0)
        self._filter_envelope_amount = algo_params.get("filter_envelope_amount", 0.0)

        # Modulation parameters
        self._velocity_to_filter = algo_params.get("velocity_to_filter", 0.0)
        self._aftertouch_to_morph = algo_params.get("aftertouch_to_morph", 0.0)

        # Runtime state (initialized on demand)
        self._oscillators: list[Any] = []
        self._filter: Any | None = None
        self._envelope: Any | None = None

    def _load_sample_data(self) -> np.ndarray | None:
        """No sample data for wavetable (uses wavetable bank)."""
        return None

    def _create_partial(self) -> Any | None:
        """
        Create wavetable oscillator bank.

        Returns:
            WavetablePartial instance or None if creation failed
        """
        try:
            # Get wavetable from bank
            wavetable = self._load_wavetable()
            if wavetable is None:
                logger.warning(f"Wavetable '{self._wavetable_name}' not found")
                return None

            # Calculate frequency for current note
            frequency = self._calculate_frequency()

            # Create unison oscillators
            oscillator_params = self._create_unison_oscillators(wavetable, frequency)

            # Create filter
            self._create_filter()

            # Create envelope
            self._create_envelope()

            # Build partial parameters
            partial_params = {
                "oscillators": oscillator_params,
                "wavetable": wavetable,
                "wavetable_position": self._wavetable_position,
                "morph_speed": self._morph_speed,
                "unison_voices": self._unison_voices,
                "detune_amount": self._detune_amount,
                "filter": self._filter,
                "envelope": self._envelope,
                "note": self.current_note,
                "velocity": self.current_velocity,
            }

            # Import and create wavetable partial
            from ..partial.wavetable_partial import WavetablePartial

            partial = WavetablePartial(partial_params, self.sample_rate)

            return partial

        except Exception as e:
            logger.error(f"Failed to create wavetable partial: {e}")
            return None

    def _load_wavetable(self) -> Any | None:
        """
        Load wavetable from bank.

        Returns:
            Wavetable instance or None if not found
        """
        if self.wavetable_bank is None:
            # Create default wavetable if no bank available
            from ..engine.wavetable_engine import Wavetable

            # Generate simple sine wavetable as fallback
            samples = np.sin(np.linspace(0, 2 * np.pi, 2048)).astype(np.float32)
            return Wavetable(samples, self.sample_rate, "default")

        # Load from bank
        return self.wavetable_bank.get_wavetable(self._wavetable_name)

    def _calculate_frequency(self) -> float:
        """
        Calculate frequency for current note.

        Returns:
            Frequency in Hz
        """
        # MIDI note to frequency
        frequency = 440.0 * (2.0 ** ((self.current_note - 69) / 12.0))

        # Apply fine tuning from descriptor
        fine_tune = self.descriptor.generator_params.get("fine_tune", 0.0)
        frequency *= 2.0 ** (fine_tune / 1200.0)

        return frequency

    def _create_unison_oscillators(
        self, wavetable: Any, base_frequency: float
    ) -> list[dict[str, Any]]:
        """
        Create unison oscillator parameters.

        Args:
            wavetable: Wavetable instance
            base_frequency: Base frequency in Hz

        Returns:
            List of oscillator parameter dictionaries
        """
        oscillators = []

        # Calculate detune steps in cents
        if self._unison_voices > 1 and self._detune_amount > 0:
            detune_step = self._detune_amount / (self._unison_voices - 1)
        else:
            detune_step = 0

        for i in range(self._unison_voices):
            # Calculate detune for this voice
            if self._unison_voices % 2 == 1 and i == self._unison_voices // 2:
                # Center voice (no detune)
                detune_cents = 0.0
            else:
                # Calculate position from center
                voice_index = i - (self._unison_voices // 2)
                detune_cents = voice_index * detune_step

            # Calculate frequency with detune
            voice_frequency = base_frequency * (2.0 ** (detune_cents / 1200.0))

            # Calculate pan for stereo spread
            if self._unison_voices > 1:
                pan = (2.0 * i / (self._unison_voices - 1) - 1.0) * 0.5
            else:
                pan = 0.0

            # Calculate amplitude (reduce for more voices to prevent clipping)
            amplitude = 1.0 / np.sqrt(self._unison_voices)

            oscillator_params = {
                "wavetable": wavetable,
                "frequency": voice_frequency,
                "detune_cents": detune_cents,
                "pan": pan,
                "amplitude": amplitude,
                "wavetable_position": self._wavetable_position,
            }

            oscillators.append(oscillator_params)

        return oscillators

    def _create_filter(self) -> None:
        """Create filter for this region."""
        try:
            from ..core.filter import UltraFastResonantFilter

            # Apply velocity to filter cutoff
            velocity_cutoff_mod = self._velocity_to_filter * (self.current_velocity / 127.0)
            effective_cutoff = self._filter_cutoff * (2.0**velocity_cutoff_mod)

            self._filter = UltraFastResonantFilter(
                cutoff=effective_cutoff,
                resonance=self._filter_resonance,
                filter_type="lowpass",
                sample_rate=self.sample_rate,
            )

        except Exception as e:
            logger.error(f"Failed to create filter: {e}")
            self._filter = None

    def _create_envelope(self) -> None:
        """Create amplitude envelope for this region."""
        try:
            from ..core.envelope import UltraFastADSREnvelope

            # Get envelope parameters from descriptor
            env_params = self.descriptor.generator_params

            self._envelope = UltraFastADSREnvelope(
                delay=env_params.get("amp_delay", 0.0),
                attack=env_params.get("amp_attack", 0.01),
                hold=env_params.get("amp_hold", 0.0),
                decay=env_params.get("amp_decay", 0.3),
                sustain=env_params.get("amp_sustain", 0.7),
                release=env_params.get("amp_release", 0.5),
                sample_rate=self.sample_rate,
            )

        except Exception as e:
            logger.error(f"Failed to create envelope: {e}")
            self._envelope = None

    def _init_envelopes(self) -> None:
        """Initialize envelopes (already done in _create_partial)."""
        # Envelopes are created in _create_partial
        pass

    def _init_filters(self) -> None:
        """Initialize filters (already done in _create_partial)."""
        # Filters are created in _create_partial
        pass

    def note_on(self, velocity: int, note: int) -> bool:
        """
        Trigger note-on for this wavetable region.

        Args:
            velocity: MIDI velocity
            note: MIDI note number

        Returns:
            True if region should play
        """
        if not super().note_on(velocity, note):
            return False

        # Recreate filter with velocity-based modulation
        self._create_filter()

        return True

    def generate_samples(self, block_size: int, modulation: dict[str, float]) -> np.ndarray:
        """
        Generate samples from wavetable partial.

        Args:
            block_size: Number of samples to generate
            modulation: Current modulation values

        Returns:
            Stereo audio buffer (block_size, 2) as float32
        """
        if not self._partial:
            return np.zeros((block_size, 2), dtype=np.float32)

        try:
            # Apply modulation
            self._apply_modulation(modulation)

            # Generate samples from partial
            samples = self._partial.generate_samples(block_size, modulation)

            # Apply filter if present
            if self._filter:
                try:
                    filtered = self._filter.process_block(samples)
                    if filtered is not None:
                        samples = filtered
                except Exception as e:
                    logger.error(f"Wavetable filter processing failed: {e}")

            return samples

        except Exception as e:
            logger.error(f"Wavetable sample generation failed: {e}")
            return np.zeros((block_size, 2), dtype=np.float32)

    def _apply_modulation(self, modulation: dict[str, float]) -> None:
        """
        Apply modulation to wavetable parameters.

        Args:
            modulation: Modulation values dictionary
        """
        # Aftertouch to wavetable morph
        aftertouch = modulation.get("channel_aftertouch", 0.0)
        if aftertouch > 0 and self._aftertouch_to_morph > 0:
            morph_offset = aftertouch * self._aftertouch_to_morph
            self._wavetable_position = min(1.0, self._wavetable_position + morph_offset)

        # Update partial wavetable position if available
        if self._partial and hasattr(self._partial, "set_wavetable_position"):
            self._partial.set_wavetable_position(self._wavetable_position)

    def update_modulation(self, modulation: dict[str, float]) -> None:
        """
        Update modulation state.

        Args:
            modulation: Modulation parameter updates
        """
        super().update_modulation(modulation)
        self._apply_modulation(modulation)

    def is_active(self) -> bool:
        """Check if wavetable region is still producing sound."""
        if self.state == RegionState.RELEASED:
            return False

        if self._partial:
            return self._partial.is_active()

        return self.state in (RegionState.ACTIVE, RegionState.INITIALIZED)

    def get_region_info(self) -> dict[str, Any]:
        """Get region information."""
        info = super().get_region_info()
        info.update(
            {
                "wavetable_name": self._wavetable_name,
                "wavetable_position": self._wavetable_position,
                "unison_voices": self._unison_voices,
                "detune_amount": self._detune_amount,
                "filter_cutoff": self._filter_cutoff,
                "filter_resonance": self._filter_resonance,
            }
        )
        return info

    def __str__(self) -> str:
        """String representation."""
        return (
            f"WavetableRegion(name={self._wavetable_name}, "
            f"unison={self._unison_voices}, pos={self._wavetable_position:.2f})"
        )
