"""Acoustic behavior layer — feature descriptor and enable/disable control.

The acoustic behavior layer is NOT a SynthesisEngine (it wraps existing sampler
regions rather than generating audio itself). It is exposed here as a named,
discoverable feature that can be enabled/disabled per synthesizer and per
channel, and registered in the engine registry's feature namespace so tooling
can discover it alongside real engines.

NOTE: ``SynthesisEngineRegistry`` does not provide a ``register_feature``
method, so the feature is tracked in a module-level registry instead. The
``AcousticBehaviorFeature`` descriptor remains the single source of truth for
the layer's metadata.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..synthesis_engine import SynthesisEngineRegistry

ACOUSTIC_BEHAVIOR_FEATURE = "acoustic_behavior"

# Module-level feature registry (registry has no register_feature method).
_FEATURE_REGISTRY: dict[str, AcousticBehaviorFeature] = {}


@dataclass(slots=True)
class AcousticBehaviorFeature:
    """Discoverable descriptor for the acoustic behavior layer."""

    name: str = ACOUSTIC_BEHAVIOR_FEATURE
    version: str = "1.1.0"
    description: str = (
        "SuperNATURAL-Acoustic alike cross-note behavior: velocity timbre, "
        "performance noise, sympathetic/damper resonance, ensemble detune."
    )
    wraps_regions: bool = True

    def register(self, registry: SynthesisEngineRegistry | None = None) -> None:
        """Register this layer as a discoverable feature (not an engine).

        The ``registry`` argument is accepted for API symmetry but the feature
        is stored in the module-level feature registry, since
        ``SynthesisEngineRegistry`` has no ``register_feature`` method.
        """
        _FEATURE_REGISTRY[self.name] = self


def get_acoustic_behavior_feature() -> AcousticBehaviorFeature:
    """Return the registered acoustic behavior feature descriptor."""
    return _FEATURE_REGISTRY.get(ACOUSTIC_BEHAVIOR_FEATURE, AcousticBehaviorFeature())


def is_acoustic_behavior_registered() -> bool:
    """Return True if the acoustic behavior feature has been registered."""
    return ACOUSTIC_BEHAVIOR_FEATURE in _FEATURE_REGISTRY
