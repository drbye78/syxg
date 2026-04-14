"""
Vibexg Module Entry Point

This module enables running vibexg as a module:
    python -m vibexg [arguments]
"""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
