"""
Style Dynamics Control

Implements the Style Dynamics Control feature that adjusts
the intensity/energy of accompaniment playback.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DynamicsParameter(Enum):
    """Parameters affected by dynamics control"""

    VELOCITY = "velocity"
    VOLUME = "volume"
    FILTER_CUTOFF = "filter_cutoff"
    FILTER_RESONANCE = "filter_resonance"
    REVERB_MIX = "reverb_mix"
    CHORUS_MIX = "chorus_mix"
    TEMPO = "tempo"
    INTRO_LENGTH = "intro_length"
    ENDING_LENGTH = "ending_length"


@dataclass(slots=True)
class DynamicsCurve:
    """Defines how dynamics affect a parameter"""

    parameter: DynamicsParameter
    min_value: float = 0.0
    max_value: float = 1.0
    curve: str = "linear"

    def apply(self, dynamics_value: float) -> float:
        """Apply dynamics curve to get parameter value"""
        normalized = dynamics_value / 127.0

        if self.curve == "linear":
            return self.min_value + (self.max_value - self.min_value) * normalized

        elif self.curve == "exponential":
            return self.min_value + (self.max_value - self.min_value) * (normalized**2)

        elif self.curve == "logarithmic":
            if normalized == 0:
                return self.min_value
            return self.min_value + (self.max_value - self.min_value) * (normalized**0.5)

        elif self.curve == "s_curve":
            return self.min_value + (self.max_value - self.min_value) * (
                normalized * normalized * (3 - 2 * normalized)
            )

        return self.min_value + (self.max_value - self.min_value) * normalized


@dataclass(slots=True)
class StyleDynamics:
    """
    Style Dynamics Control - Controls the energy/intensity of accompaniment.

    Yamaha's Style Dynamics Control allows adjusting the overall
    "energy" of a style from soft (0) to loud (127), affecting:
    - Velocity of notes
    - Volume levels
    - Filter settings
    - Reverb/chorus mix
    - And more
    """

    _dynamics_value: int = 64
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    _curves: dict[DynamicsParameter, DynamicsCurve] = field(default_factory=dict)
    _callbacks: list[Callable[[int, dict[DynamicsParameter, float]], None]] = field(
        default_factory=list, repr=False
    )

    def __post_init__(self):
        self._init_default_curves()

    def _init_default_curves(self):
        """Initialize default dynamics curves for each parameter"""
        self._curves = {
            DynamicsParameter.VELOCITY: DynamicsCurve(
                DynamicsParameter.VELOCITY, 0.5, 1.0, "linear"
            ),
            DynamicsParameter.VOLUME: DynamicsCurve(DynamicsParameter.VOLUME, 0.3, 1.0, "linear"),
            DynamicsParameter.FILTER_CUTOFF: DynamicsCurve(
                DynamicsParameter.FILTER_CUTOFF, 0.5, 1.0, "exponential"
            ),
            DynamicsParameter.FILTER_RESONANCE: DynamicsCurve(
                DynamicsParameter.FILTER_RESONANCE, 0.0, 0.5, "linear"
            ),
            DynamicsParameter.REVERB_MIX: DynamicsCurve(
                DynamicsParameter.REVERB_MIX, 0.2, 0.8, "linear"
            ),
            DynamicsParameter.CHORUS_MIX: DynamicsCurve(
                DynamicsParameter.CHORUS_MIX, 0.2, 0.8, "linear"
            ),
            DynamicsParameter.TEMPO: DynamicsCurve(DynamicsParameter.TEMPO, 0.8, 1.2, "linear"),
        }

    @property
    def dynamics_value(self) -> int:
        """Get current dynamics value (0-127)"""
        with self._lock:
            return self._dynamics_value

    def set_dynamics(self, value: int):
        """Set dynamics value (0-127)"""
        with self._lock:
            self._dynamics_value = max(0, min(127, value))

            params = self.get_all_parameters()

            for callback in self._callbacks:
                callback(self._dynamics_value, params)

    def adjust(self, delta: int):
        """Adjust dynamics by delta"""
        with self._lock:
            new_value = self._dynamics_value + delta
            self.set_dynamics(new_value)

    def increment(self):
        """Increment dynamics by 1"""
        self.adjust(1)

    def decrement(self):
        """Decrement dynamics by 1"""
        self.adjust(-1)

    def reset(self):
        """Reset to default dynamics value"""
        self.set_dynamics(64)

    def set_curve(
        self,
        parameter: DynamicsParameter,
        curve: str,
        min_value: float = None,
        max_value: float = None,
    ):
        """Set dynamics curve for a parameter"""
        with self._lock:
            if parameter in self._curves:
                existing = self._curves[parameter]
                self._curves[parameter] = DynamicsCurve(
                    parameter,
                    min_value if min_value is not None else existing.min_value,
                    max_value if max_value is not None else existing.max_value,
                    curve,
                )
            else:
                self._curves[parameter] = DynamicsCurve(parameter, 0.0, 1.0, curve)

    def get_parameter(self, parameter: DynamicsParameter) -> float:
        """Get current value for a specific parameter"""
        with self._lock:
            if parameter in self._curves:
                return self._curves[parameter].apply(self._dynamics_value)
            return 0.5

    def get_all_parameters(self) -> dict[DynamicsParameter, float]:
        """Get all parameter values affected by dynamics"""
        with self._lock:
            return {
                param: curve.apply(self._dynamics_value) for param, curve in self._curves.items()
            }

    def add_callback(self, callback: Callable[[int, dict[DynamicsParameter, float]], None]):
        """Add callback for dynamics changes"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[int, dict[DynamicsParameter, float]], None]):
        """Remove callback"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def get_velocity_scale(self) -> float:
        """Get velocity scaling factor"""
        return self.get_parameter(DynamicsParameter.VELOCITY)

    def get_volume_scale(self) -> float:
        """Get volume scaling factor"""
        return self.get_parameter(DynamicsParameter.VOLUME)

    def get_filter_cutoff(self) -> float:
        """Get filter cutoff scaling factor"""
        return self.get_parameter(DynamicsParameter.FILTER_CUTOFF)

    def get_reverb_mix(self) -> float:
        """Get reverb mix level"""
        return self.get_parameter(DynamicsParameter.REVERB_MIX)

    def get_chorus_mix(self) -> float:
        """Get chorus mix level"""
        return self.get_parameter(DynamicsParameter.CHORUS_MIX)

    def get_tempo_scale(self) -> float:
        """Get tempo scaling factor"""
        return self.get_parameter(DynamicsParameter.TEMPO)

    def get_status(self) -> dict[str, Any]:
        """Get dynamics status"""
        with self._lock:
            params = {
                param.name: curve.apply(self._dynamics_value)
                for param, curve in self._curves.items()
            }

            return {
                "dynamics_value": self._dynamics_value,
                "parameters": params,
            }

    def to_dict(self) -> dict[str, Any]:
        """Export to dictionary"""
        return {
            "dynamics_value": self._dynamics_value,
            "curves": {
                param.name: {
                    "curve": curve.curve,
                    "min_value": curve.min_value,
                    "max_value": curve.max_value,
                }
                for param, curve in self._curves.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StyleDynamics:
        """Create from dictionary"""
        dynamics = cls()

        dynamics.set_dynamics(data.get("dynamics_value", 64))

        curves_data = data.get("curves", {})
        for param_name, curve_data in curves_data.items():
            try:
                param = DynamicsParameter[param_name]
                dynamics.set_curve(
                    param,
                    curve_data.get("curve", "linear"),
                    curve_data.get("min_value"),
                    curve_data.get("max_value"),
                )
            except KeyError:
                continue

        return dynamics
