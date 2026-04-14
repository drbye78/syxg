"""XG Effect Factory - creates effect instances."""

from __future__ import annotations

import logging
import threading
from typing import Any

from .types import XGEffectCategory

logger = logging.getLogger(__name__)

class XGEffectFactory:
    """
    XG Effect Factory

    Factory class for creating effect processor instances with proper parameterization.
    Provides memory-efficient instance management and configuration.
    """

    def __init__(self, sample_rate: int):
        """
        Initialize effect factory.

        Args:
            sample_rate: Sample rate in Hz for all created effects
        """
        self.sample_rate = sample_rate
        self.registry = XGEffectRegistry()

        # Instance pooling for performance
        self._instance_pool: dict[str, list[Any]] = {}
        self._max_pool_size = 8  # Maximum instances to keep in pool

        # Thread safety
        self.lock = threading.RLock()

    def create_system_effect(self, effect_type: XGReverbType, **params) -> Any | None:
        """
        Create a system effect processor.

        Args:
            effect_type: XG reverb or chorus type
            **params: Effect parameters

        Returns:
            Effect processor instance or None if creation failed
        """
        with self.lock:
            if isinstance(effect_type, XGReverbType):
                return self._create_system_reverb()
            elif isinstance(effect_type, XGChorusType):
                return self._create_system_chorus(**params)
            return None

    def create_variation_effect(
        self, effect_type: int, max_delay_samples: int = 22050
    ) -> XGVariationEffectsProcessor | None:
        """
        Create a variation effect processor.

        Args:
            effect_type: XG variation effect type (0-83)
            max_delay_samples: Maximum delay buffer size

        Returns:
            Variation effects processor instance
        """
        with self.lock:
            if not self.registry.is_valid_effect_type(XGEffectCategory.VARIATION, effect_type):
                return None

            pool_key = f"variation_{effect_type}"
            if self._instance_pool.get(pool_key):
                # Reuse from pool
                instance = self._instance_pool[pool_key].pop()
                instance.reset_state()
                return instance

            # Create new instance
            try:
                processor = XGVariationEffectsProcessor(self.sample_rate, max_delay_samples)
                # Convert integer to enum value if needed
                if isinstance(effect_type, int):
                    # Map integer to XGVariationType enum
                    try:
                        enum_value = XGVariationType(effect_type)
                        processor.set_variation_type(enum_value)
                    except ValueError:
                        # If integer doesn't map to enum, use default
                        processor.set_variation_type(XGVariationType.DELAY_LCR)
                else:
                    # Assume it's already an enum
                    processor.set_variation_type(effect_type)
                return processor
            except Exception as e:
                print(f"Failed to create variation effect {effect_type}: {e}")
                return None

    def create_insertion_effect(
        self, effect_type: int, max_delay_samples: int = 22050
    ) -> XGInsertionEffectsProcessor | None:
        """
        Create an insertion effect processor.

        Args:
            effect_type: XG insertion effect type (0-17)
            max_delay_samples: Maximum delay buffer size

        Returns:
            Insertion effects processor instance
        """
        with self.lock:
            if not self.registry.is_valid_effect_type(XGEffectCategory.INSERTION, effect_type):
                return None

            pool_key = f"insertion_{effect_type}"
            if self._instance_pool.get(pool_key):
                # Reuse from pool
                instance = self._instance_pool[pool_key].pop()
                instance.reset_state()
                return instance

            # Create new instance
            try:
                processor = XGInsertionEffectsProcessor(self.sample_rate, max_delay_samples)
                # Set effect types for all slots to the requested type
                for slot in range(3):  # XG supports 3 insertion slots
                    processor.set_insertion_effect_type(slot, effect_type)
                return processor
            except Exception:
                return None

    def create_channel_eq(self, eq_type: int) -> XGMultiBandEqualizer | None:
        """
        Create a channel EQ processor using XGMultiBandEqualizer.

        Args:
            eq_type: XG EQ type (0-9)

        Returns:
            XGMultiBandEqualizer instance configured for channel use
        """
        with self.lock:
            if not (0 <= eq_type <= 9):
                return None

            pool_key = f"channel_eq_{eq_type}"
            if self._instance_pool.get(pool_key):
                # Reuse from pool
                instance = self._instance_pool[pool_key].pop()
                instance.reset()
                return instance

            # Create new instance
            try:
                processor = XGMultiBandEqualizer(self.sample_rate)
                processor.set_eq_type(eq_type)
                return processor
            except Exception:
                return None

    def create_master_eq(self) -> XGMultiBandEqualizer | None:
        """
        Create a master EQ processor using XGMultiBandEqualizer.

        Returns:
            XGMultiBandEqualizer instance configured for master use
        """
        with self.lock:
            pool_key = "master_eq"
            if self._instance_pool.get(pool_key):
                # Reuse from pool
                instance = self._instance_pool[pool_key].pop()
                instance.reset()
                return instance

            # Create new instance
            try:
                return XGMultiBandEqualizer(self.sample_rate)
            except Exception:
                return None

    def return_to_pool(self, processor: Any, processor_type: str, effect_id: int = 0) -> None:
        """
        Return a processor instance to the pool for reuse.

        Args:
            processor: Effect processor instance
            processor_type: Type identifier ('variation', 'insertion', 'eq', etc.)
            effect_id: Effect type identifier
        """
        with self.lock:
            pool_key = f"{processor_type}_{effect_id}"

            if pool_key not in self._instance_pool:
                self._instance_pool[pool_key] = []

            # Only keep up to max pool size
            if len(self._instance_pool[pool_key]) < self._max_pool_size:
                # Reset processor state before pooling
                if hasattr(processor, "reset_state"):
                    processor.reset_state()
                self._instance_pool[pool_key].append(processor)

    def get_pool_stats(self) -> dict[str, Any]:
        """Get statistics about the instance pool."""
        with self.lock:
            total_instances = sum(len(pool) for pool in self._instance_pool.values())
            return {
                "total_pooled_instances": total_instances,
                "pool_types": len(self._instance_pool),
                "pools": {key: len(instances) for key, instances in self._instance_pool.items()},
            }

    def clear_pool(self) -> None:
        """Clear all instances from the pool."""
        with self.lock:
            self._instance_pool.clear()

    def _create_system_reverb(self) -> XGSystemReverbProcessor:
        """Create system reverb processor with XG defaults."""
        max_ir_length = 44100 * 2  # 2 seconds max at 44.1kHz
        return XGSystemReverbProcessor(self.sample_rate, max_ir_length)

    def _create_system_chorus(self, **params) -> XGSystemChorusProcessor | None:
        """
        Create system chorus processor with XG-compliant parameters.

        Args:
            **params: XG chorus parameters (rate, depth, feedback, delay, level)

        Returns:
            Configured XGSystemChorusProcessor or None if creation failed
        """
        try:
            max_delay_samples = int(0.05 * self.sample_rate)  # 50ms max delay
            processor = XGSystemChorusProcessor(self.sample_rate, max_delay_samples)

            # Apply XG default parameters if not specified
            chorus_params = {
                "rate": params.get("rate", 1.0),  # 1 Hz default
                "depth": params.get("depth", 0.5),  # 50% depth
                "feedback": params.get("feedback", 0.3),  # 30% feedback
                "delay": params.get("delay", 0.012),  # 12ms delay
                "level": params.get("level", 0.4),  # 40% level
            }

            # Configure processor with parameters
            if hasattr(processor, "set_parameters"):
                processor.set_parameters(chorus_params)

            return processor

        except Exception as e:
            print(f"Failed to create system chorus processor: {e}")
            return None


