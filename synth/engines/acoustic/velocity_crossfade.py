"""Velocity-layer crossfade — multi-sample blending for richer dynamics.

When multiple velocity layers exist for the same note, crossfade between
the two nearest layers to produce continuous timbre variation with velocity.
More layers = smoother transition from pianissimo to fortissimo.

Architecture: SF2/SFZ provides discrete velocity layers (pp, mf, ff).
This module blends them into a continuous spectrum by crossfading the
attack segments of the two nearest layers.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(slots=True)
class VelocityLayer:
    """A single velocity layer with its sample data and velocity range."""

    velocity: int           # Nominal velocity (center of range)
    sample: np.ndarray      # Attack sample data
    attack_length: int = 0  # Attack segment length (0=use full sample)
    crossfade_length: int = 1323  # ~30ms at 44.1kHz


class VelocityLayerSelector:
    """Select and crossfade between velocity layers for a given velocity.

    Usage:
        selector = VelocityLayerSelector()
        selector.add_layer(30, sample_pp, attack_len=4410)
        selector.add_layer(80, sample_mf, attack_len=4410)
        selector.add_layer(110, sample_ff, attack_len=4410)

        blended, vel_factor = selector.get_blended_attack(velocity=72)
    """

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self._layers: list[VelocityLayer] = []

    def add_layer(self, velocity: int, sample: np.ndarray,
                  attack_length: int = 0, crossfade_region: int = 0) -> None:
        """Add a velocity layer.

        Args:
            velocity: Nominal velocity (center of this layer's range).
            sample: Attack sample data (should be pre-segmented).
            attack_length: Attack segment end sample index.
            crossfade_region: Crossfade region length for inter-layer blending.
        """
        self._layers.append(VelocityLayer(
            velocity=velocity,
            sample=sample.astype(np.float32) if sample.dtype != np.float32 else sample,
            attack_length=attack_length if attack_length > 0 else len(sample),
            crossfade_length=crossfade_region if crossfade_region > 0 else 1323,
        ))
        self._layers.sort(key=lambda l: l.velocity)

    def get_blended_attack(
        self, velocity: int
    ) -> tuple[np.ndarray, int, float, float]:
        """Get velocity-blended attack sample.

        Returns:
            (blended_attack, attack_length, velocity_factor, crossfade_alpha)
            - blended_attack: Crossfaded PCM attack buffer
            - attack_length: Length of the blended attack segment
            - velocity_factor: Normalized velocity (0-1) for excitation level
            - crossfade_alpha: Blend ratio between layers (0=lower, 1=upper)
        """
        if not self._layers:
            return np.zeros(1024, dtype=np.float32), 0, 0.0, 0.0

        if len(self._layers) == 1:
            layer = self._layers[0]
            return layer.sample, layer.attack_length, velocity / 127.0, 0.0

        # Find two nearest layers
        lower = None
        upper = None
        for layer in self._layers:
            if layer.velocity <= velocity:
                lower = layer
            elif layer.velocity > velocity:
                upper = layer
                break

        if lower is None:
            # Velocity below lowest layer — use lowest layer only
            layer = self._layers[0]
            return layer.sample, layer.attack_length, velocity / 127.0, 0.0

        if upper is None:
            # Velocity above highest layer — use highest layer only
            layer = self._layers[-1]
            return layer.sample, layer.attack_length, velocity / 127.0, 1.0

        # Crossfade between lower and upper layers
        vel_range = upper.velocity - lower.velocity
        alpha = (velocity - lower.velocity) / max(vel_range, 1)  # 0=lower, 1=upper

        # Crossfade the attack segments
        lower_attack = lower.sample[:lower.attack_length] if lower.attack_length > 0 else lower.sample
        upper_attack = upper.sample[:upper.attack_length] if upper.attack_length > 0 else upper.sample

        # Match lengths: use the shorter attack segment
        attack_len = min(len(lower_attack), len(upper_attack))
        if attack_len < 256:
            return lower_attack, len(lower_attack), velocity / 127.0, alpha

        # Equal-power crossfade
        t = np.linspace(0, np.pi / 2, attack_len, dtype=np.float32)
        fade_lower = np.cos(t * alpha).astype(np.float32)
        fade_upper = np.sin(t * alpha).astype(np.float32)

        blended = lower_attack[:attack_len] * fade_lower + upper_attack[:attack_len] * fade_upper
        vel_factor = velocity / 127.0

        return blended.astype(np.float32), attack_len, vel_factor, alpha

    def has_layers(self) -> bool:
        return len(self._layers) > 0

    def layer_count(self) -> int:
        return len(self._layers)

    def reset(self) -> None:
        self._layers.clear()
