"""
Synth Package - Restructured synthesizer implementation with clean separation of concerns.
"""

__version__ = "1.0.0"
__author__ = "Synth Team"

# Core synthesis building blocks
from .core import *

# Synthesis engine
from .engine import *

# I/O and format handling
from .audio import *
from .midi import *

# Sound sources
from .sf2 import *
from .voice import *

# Digital signal processing
from .dsp import *

# Effects processing
from .effects import *
from .modulation import *

# XG specific components
from .xg import *

# Utilities
from .utils import *
from .math import *
from .memory import *
