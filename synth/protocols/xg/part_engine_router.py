"""PartEngineRouter — explicit per-part engine routing with bank+program fallback."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class EngineRoutingMode(Enum):
    """Engine routing mode."""

    EXPLICIT = "explicit"  # Part has an explicit engine assignment
    FULL_BANK_PROGRAM = "full"  # Engine selected by iterating engines for bank+program match


@dataclass(slots=True)
class PartEngineRouter:
    """Maps parts to synthesis engines.

    Two modes:
    - EXPLICIT: part → engine is directly assigned
    - FULL_BANK_PROGRAM: engine is selected by trying engines in priority order
      to find one that handles the part's bank_msb + bank_lsb + program tuple.
      This matches the VoiceFactory offline logic.

    Drum parts are detected via per-part part_mode, not hardcoded channel 9.
    """

    num_parts: int = 16
    mode: EngineRoutingMode = EngineRoutingMode.FULL_BANK_PROGRAM
    _explicit_engines: dict[int, str] = field(default_factory=dict)
    _engine_registry: Any = field(default=None)

    def set_engine_registry(self, registry) -> None:
        """Set engine registry for bank+program lookup."""
        self._engine_registry = registry

    def set_mode(self, mode: EngineRoutingMode) -> None:
        """Set the routing mode."""
        self.mode = mode

    def set_part_engine(self, part_num: int, engine_type: str) -> None:
        """Explicitly assign an engine to a part (EXPLICIT mode)."""
        self._explicit_engines[part_num] = engine_type

    def get_part_engine(self, part_num: int, part_data: dict[str, Any]) -> str:
        """Get the engine type for a part.

        Args:
            part_num: Part number (0-15)
            part_data: Dict with bank_msb, bank_lsb, program_num, part_mode, etc.

        Returns:
            Engine type string (e.g., 'xg', 'sf2', 'fm', 'an', 'fdsp')
        """
        if self.mode == EngineRoutingMode.EXPLICIT and part_num in self._explicit_engines:
            return self._explicit_engines[part_num]

        # FULL_BANK_PROGRAM: iterate engine registry by priority
        if self._engine_registry is not None:
            bank = part_data.get("bank_msb", 0) << 7 | part_data.get("bank_lsb", 0)
            program = part_data.get("program_num", 0)
            try:
                engine = self._engine_registry.get_engine_for_program(bank, program)
                if engine:
                    return engine
            except Exception:
                logger.warning("Engine registry lookup failed", exc_info=True)

        # Fallback: bank-MSB-based routing
        bank_msb = part_data.get("bank_msb", 0)
        if bank_msb == 121:
            return "fdsp"  # Formant Dynamic Synthesis Processor (S90/S70)
        elif bank_msb == 126:
            return "an"  # Analog Physical Modeling (S90/S70)
        return "xg"  # Default: ModernXGSynthesizer

    def is_drum_part(self, part_data: dict[str, Any]) -> bool:
        """Check if a part is in drum mode.

        Uses explicit part_mode field rather than hardcoded channel 9.
        """
        return part_data.get("part_mode", 0) >= 1 or part_data.get("bank_msb", 0) == 127
