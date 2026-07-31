"""HarmonicsProcessor, PedalProcessor, CompositeProcessor — stubs and composition."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..processor import ArticulationProcessor
from ..context import ArticulationContext


class HarmonicsProcessor(ArticulationProcessor):
    """Pitch shift to harmonic partial."""

    def __init__(self, sample_rate: int):
        super().__init__(sample_rate)

    def process(self, buf: np.ndarray, context: ArticulationContext, params: dict[str, Any]) -> None:
        partial = params.get("partial", 2)
        # Simple: multiply frequency by partial number
        # Full implementation uses resampling (deferred)
        pass

    def reset(self) -> None:
        pass


class PedalProcessor(ArticulationProcessor):
    """Pedal state effects (sustain, soft, sostenuto)."""

    def __init__(self, sample_rate: int):
        super().__init__(sample_rate)

    def process(self, buf: np.ndarray, context: ArticulationContext, params: dict[str, Any]) -> None:
        atype = params.get("type", "sustain")
        n = buf.shape[0]
        if n < 1:
            return
        if atype == "sustain":
            # Extend release: gentle fade on last portion of buffer
            level = params.get("level", 0.8)
            release_rate = params.get("release_rate", 0.5)
            sustain_start = int(n * 0.3)
            if sustain_start < n:
                tail_len = n - sustain_start
                t = np.arange(tail_len, dtype=np.float32) / self.sample_rate
                decay = np.exp(-t * release_rate)
                env = np.ones(n, dtype=np.float32)
                env[sustain_start:] = level + (1.0 - level) * decay
                buf[:, 0] *= env
                buf[:, 1] *= env

    def reset(self) -> None:
        pass


class CompositeProcessor(ArticulationProcessor):
    """Chains multiple articulation processors sequentially."""

    def __init__(self, sample_rate: int, engine: Any | None = None):
        super().__init__(sample_rate)
        self._engine = engine

    def set_engine(self, engine: Any) -> None:
        self._engine = engine

    def process(self, buf: np.ndarray, context: ArticulationContext, params: dict[str, Any]) -> None:
        chain = params.get("chain", [])
        if self._engine is None:
            return
        for proc_type, proc_params in chain:
            processor = self._engine.get_processor(proc_type)
            processor.process(buf, context, proc_params)

    def reset(self) -> None:
        pass
