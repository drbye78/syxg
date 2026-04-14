#!/usr/bin/env python3
"""
Vibexg - Vibe XG Real-Time MIDI Workstation

This is a thin wrapper script that imports from the vibexg package.
For programmatic use, import from the vibexg package directly:

    from vibexg import XGWorkstation
    from vibexg.cli import main

Author: Roger
License: MIT
"""

import sys

# Import main entry point from the package
from vibexg.cli import main

if __name__ == "__main__":
    sys.exit(main())
