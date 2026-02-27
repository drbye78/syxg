"""
SF2 Module Test Suite

Test coverage for SF2 synthesis engine components:
- File loading and parsing
- SoundFont management
- Region matching and creation
- Partial synthesis
- Engine integration
- Generator mappings
- Modulation

Run tests:
    pytest synth/sf2/tests/ -v

Run with coverage:
    pytest synth/sf2/tests/ --cov=synth/sf2 --cov-report=html
"""
from __future__ import annotations
