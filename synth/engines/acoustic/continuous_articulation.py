"""Continuous articulation morphing — seamless transitions between playing techniques.

Morphs behavioral voice parameters continuously between articulations
(e.g., staccato→legato, sul tasto→sul ponticello) over configurable
transition times. Replaces discrete articulation switching.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ArticulationDimension(StrEnum):
    """Continuous articulation dimensions for behavioral synthesis."""
    STACCATO_LEGATO = "staccato_legato"    # 0=staccato (short), 1=legato (smooth)
    SUL_TASTO_PONTICELLO = "sul_tasto_ponticello"  # 0=sul tasto (soft), 1=sul ponticello (bright)
    PIANISSIMO_FORTISSIMO = "pianissimo_fortissimo"  # 0=pp, 1=ff
    NORMAL_MARCATO = "normal_marcato"      # 0=normal, 1=marcato (accented)
    NON_VIBRATO_VIBRATO = "non_vibrato_vibrato"  # 0=no vibrato, 1=full vibrato


@dataclass(slots=True)
class ContinuousArticulation:
    """Morph articulation parameters continuously over time.

    Usage:
        art = ContinuousArticulation()
        art.set(ArticulationDimension.STACCATO_LEGATO, 0.8, transition=0.1)
        # Each audio block:
        params = art.get_params(dt=block_time)
        voice.set_excitation_envelope(params["staccato_legato"])
    """

    # Current values (0-1) for each dimension
    _current: dict[str, float] = field(default_factory=lambda: {
        "staccato_legato": 0.5,
        "sul_tasto_ponticello": 0.5,
        "pianissimo_fortissimo": 0.5,
        "normal_marcato": 0.0,
        "non_vibrato_vibrato": 0.3,
    })

    _target: dict[str, float] = field(default_factory=lambda: {
        "staccato_legato": 0.5,
        "sul_tasto_ponticello": 0.5,
        "pianissimo_fortissimo": 0.5,
        "normal_marcato": 0.0,
        "non_vibrato_vibrato": 0.3,
    })

    _transition_time: float = 0.05  # seconds
    _elapsed: float = 0.0

    def set(self, dimension: ArticulationDimension | str, value: float,
            transition: float = 0.05) -> None:
        """Set target value for a dimension with configurable transition time.

        Args:
            dimension: Which articulation dimension to change.
            value: Target value (0.0-1.0).
            transition: Transition duration in seconds.
        """
        dim = dimension if isinstance(dimension, str) else dimension.value
        self._target[dim] = max(0.0, min(1.0, value))
        self._transition_time = max(0.01, transition)
        self._elapsed = 0.0

    def set_velocity_derived(self, velocity: int) -> None:
        """Set velocity-derived dimensions from MIDI velocity."""
        vel_norm = velocity / 127.0
        self.set("pianissimo_fortissimo", vel_norm, transition=0.02)
        if velocity > 100:
            self.set("normal_marcato", min(1.0, (velocity - 100) / 27.0), transition=0.01)

    def get_params(self, dt: float) -> dict[str, float]:
        """Interpolate toward target values and return current blend.

        Args:
            dt: Time since last call in seconds.

        Returns:
            Dict of dimension_name → current_value (0-1).
        """
        if self._elapsed < self._transition_time:
            self._elapsed += dt
            t = min(1.0, self._elapsed / self._transition_time)
            # Smoothstep interpolation (ease-in-out)
            t_smooth = t * t * (3.0 - 2.0 * t)
        else:
            t_smooth = 1.0

        for dim in self._current:
            self._current[dim] += (self._target[dim] - self._current[dim]) * t_smooth

        self._elapsed = self._transition_time  # Clamp after first interpolation
        return dict(self._current)

    def get_legato_factor(self) -> float:
        """Return 0.0 (staccato) to 1.0 (legato)."""
        return self._current["staccato_legato"]

    def get_brightness_factor(self) -> float:
        """Return 0.0 (sul tasto/dark) to 1.0 (sul ponticello/bright)."""
        return self._current["sul_tasto_ponticello"]

    def get_velocity_factor(self) -> float:
        """Return 0.0 (pp) to 1.0 (ff)."""
        return self._current["pianissimo_fortissimo"]

    def get_accent_factor(self) -> float:
        """Return 0.0 (normal) to 1.0 (marcato)."""
        return self._current["normal_marcato"]

    def get_vibrato_factor(self) -> float:
        """Return 0.0 (none) to 1.0 (full)."""
        return self._current["non_vibrato_vibrato"]
