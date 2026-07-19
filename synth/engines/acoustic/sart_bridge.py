"""Adapter exposing the existing S.Art2 modifier set to the acoustic layer.

The S.Art2 ``SF2SampleModifier.apply_articulation`` operates on a MONO 1-D
array (latent stereo-contract bug: it indexes ``sample[i]`` as a scalar and
fancy-indexes in ``_pitch_resample``). This bridge runs each modifier
PER-CHANNEL on the ``(block_size, 2)`` stereo buffer so the existing
pitch/envelope/LFO/filter/noise/timbre modifiers are reused without
rewriting them, while remaining correct for stereo output.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class SArt2Bridge:
    """Reuses S.Art2 modifiers on stereo buffers, channel-by-channel."""

    # Modifiers safe to apply per-channel (all operate sample-wise / per-index)
    _SUPPORTED = frozenset(
        {
            "vibrato",
            "trill",
            "glissando",
            "bend",
            "hammer_on",
            "pull_off",
            "ethnic_bend",
            "pizzicato",
            "swell",
            "marcato",
            "crescendo",
            "diminuendo",
            "staccato",
            "legato",
            "sustain_pedal",
            "tremolo",
            "flutter",
            "growl",
            "soft_pedal",
            "sub_bass",
            "dead_note",
            "fret_noise",
            "organ_click",
            "palm_mute",
            "rim_shot",
            "open_rim",
            "harmonics",
        }
    )

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate
        self._modifier: Any | None = None
        try:
            from ...protocols.xg.sart.modifiers import SF2SampleModifier

            self._modifier = SF2SampleModifier(sample_rate)
        except Exception as exc:  # pragma: no cover - optional dependency
            logger.warning(f"S.Art2 modifier unavailable for acoustic bridge: {exc}")

    @property
    def available(self) -> bool:
        return self._modifier is not None

    def apply(
        self, buf: np.ndarray, articulation: str, params: dict[str, Any] | None = None
    ) -> np.ndarray:
        """Apply an S.Art2 articulation to a stereo ``(n, 2)`` buffer in place.

        Runs the modifier on each channel independently to respect the
        mono-only contract of ``SF2SampleModifier``.
        """
        if (
            not self.available
            or articulation in ("normal", "")
            or articulation not in self._SUPPORTED
        ):
            return buf
        params = params or {}
        # Operate on channel views; modifiers return a new 1-D array.
        modifier = self._modifier
        if modifier is None:
            return buf
        left = buf[:, 0]
        right = buf[:, 1]
        buf[:, 0] = modifier.apply_articulation(left, articulation, params)
        buf[:, 1] = modifier.apply_articulation(right, articulation, params)
        # Ensure dtype/shape preserved
        if buf.dtype != np.float32:
            buf = buf.astype(np.float32)
        return buf

    def supports(self, articulation: str) -> bool:
        return articulation in self._SUPPORTED
