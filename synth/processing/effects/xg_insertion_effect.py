from __future__ import annotations

import math
import threading
from typing import Any

import numpy as np

from .midi_2_effects_processor import (
    EffectParameter,
    EffectProcessor,
    EffectType,
    ParameterResolution,
)
