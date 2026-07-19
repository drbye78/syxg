"""Acoustic behavior DSP processors (Phase 3).

Each processor operates on stereo ``(block_size, 2)`` float32 buffers and
avoids hot-path allocation by reusing pre-allocated scratch buffers. They
implement the single-note ([A]) and cross-note ([B]) behavior layers.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
