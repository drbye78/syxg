# SF2 Implementation Refactor

This document describes the refactor of the SF2 implementation to support on-demand parsing of SoundFont presets.

## Overview

The original implementation had a deferred parsing approach but was still atomic - all presets and their details were parsed at once when needed. This refactor implements true on-demand parsing where:

1. Only essential details (bank & program) of all SoundFont presets are parsed during initialization
2. Detailed parsing of preset generators, modulators, and their instruments is performed only upon request
3. A new `Sf2SoundFont` class was created to represent a single SoundFont file
4. Data classes were moved to a separate file to avoid circular imports

## Files

- `sf2_dataclasses.py` - Contains all the data classes (SF2Modulator, SF2InstrumentZone, etc.)
- `sf2_soundfont.py` - Contains the Sf2SoundFont class for individual SoundFont files
- `sf2.py` - Contains the Sf2WavetableManager class that manages multiple SoundFont files

## Key Features

### On-Demand Parsing

The new implementation supports on-demand parsing of SF2 presets:

1. **Header Parsing**: During initialization, only the preset headers (name, bank, program) are parsed for fast startup
2. **Deferred Full Parsing**: Detailed preset data (generators, modulators, instruments) is parsed only when a preset is requested
3. **Per-File Management**: Each SoundFont file is managed by its own Sf2SoundFont instance

### Sf2SoundFont Class

The new `Sf2SoundFont` class represents a single SoundFont file and provides:

- `get_preset(program, bank)` - Gets a preset with on-demand parsing
- `get_instrument(index)` - Gets an instrument with on-demand parsing
- `get_sample_header(index)` - Gets a sample header with on-demand parsing
- Internal methods for parsing different parts of the SF2 file only when needed

### Data Classes

All data structures have been converted to dataclasses for better type safety and cleaner code:

- `SF2Modulator` - Represents a SoundFont modulator
- `SF2InstrumentZone` - Represents an instrument zone
- `SF2PresetZone` - Represents a preset zone
- `SF2SampleHeader` - Represents a sample header
- `SF2Preset` - Represents a preset (instrument)
- `SF2Instrument` - Represents an instrument

## Usage

```python
from sf2 import Sf2WavetableManager

# Initialize with one or more SF2 files
manager = Sf2WavetableManager(["path/to/soundfont1.sf2", "path/to/soundfont2.sf2"])

# Get parameters for a specific program/bank (on-demand parsing happens here)
params = manager.get_program_parameters(program=0, bank=0)

# The parsing is deferred until the actual data is needed
```

## Benefits

1. **Faster Startup**: Only essential information is parsed during initialization
2. **Memory Efficiency**: Only the data that is actually used is loaded into memory
3. **Scalability**: Works well with large SoundFont files that contain many presets
4. **Modularity**: Cleaner separation of concerns with dedicated classes for each SoundFont file

## Implementation Details

The refactor maintains backward compatibility with the existing API while improving performance through on-demand parsing. The `Sf2WavetableManager` class now manages a list of `Sf2SoundFont` instances, each responsible for parsing its own file only when data is requested.