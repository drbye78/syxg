# S.Art2 Enhancement Plan
## Bringing S.Art2 to Yamaha Genos2 Parity

**Document Version:** 1.0  
**Date:** 2026-02-23  
**Goal:** Expand S.Art2 articulation system to match Yamaha Genos2 capabilities

---

## Executive Summary

This plan outlines the enhancement of the S.Art2 articulation system to achieve parity with Yamaha Genos2's Super Articulation 2 technology. The enhancement includes:

- **Expansion from 35+ to 100+ articulations**
- **Advanced NRPN mapping (200+ mappings)**
- **Full SYSEX implementation for parameter control**
- **Instrument-specific articulation sets**
- **Articulation chaining and transitions**
- **Performance articulation control**

**Timeline:** 8-10 weeks  
**Effort:** ~400 hours  
**Files to Create/Modify:** ~15 files

---

## 1. Current State Assessment

### **1.1 Current S.Art2 Capabilities**

| Feature | Current Status | Genos2 Target |
|---------|---------------|---------------|
| **Articulations** | 35+ | 100+ |
| **NRPN Mappings** | 70+ | 200+ |
| **SYSEX Support** | Basic parsing | Full parameter control |
| **Instrument Sets** | 6 categories | 15+ instrument families |
| **Articulation Chaining** | ❌ No | ✅ Yes |
| **Velocity Switching** | ⚠️ Basic | ✅ Advanced |
| **Key Splits** | ❌ No | ✅ Yes |
| **Legato Transitions** | ⚠️ Basic | ✅ Advanced |
| **Round-Robin** | ❌ No | ✅ Yes |
| **MPE Support** | ❌ No | ⚠️ Partial |

### **1.2 Current Articulation Categories**

```
synth/xg/sart/articulation_controller.py:
├── Common (MSB 1) - 36 articulations
├── Dynamics (MSB 2) - 12 articulations
├── Wind (MSB 3) - 10 articulations
├── Strings (MSB 4) - 10 articulations
├── Guitar (MSB 5) - 10 articulations
└── Brass (MSB 6) - 6 articulations

Total: 84 NRPN mappings → 35+ unique articulations
```

---

## 2. Yamaha Genos2 Articulation Analysis

### **2.1 Genos2 Articulation Categories**

Based on Yamaha Genos2 documentation and S.Art2 voice analysis:

| Category | Articulations | NRPN Range |
|----------|---------------|------------|
| **Common** | 50 | MSB 1, LSB 0-49 |
| **Dynamics** | 15 | MSB 2, LSB 0-14 |
| **Wind - Saxophone** | 25 | MSB 3, LSB 0-24 |
| **Wind - Brass** | 20 | MSB 4, LSB 0-19 |
| **Wind - Woodwind** | 18 | MSB 5, LSB 0-17 |
| **Strings - Bow** | 22 | MSB 6, LSB 0-21 |
| **Strings - Pluck** | 15 | MSB 7, LSB 0-14 |
| **Guitar** | 25 | MSB 8, LSB 0-24 |
| **Vocal** | 20 | MSB 9, LSB 0-19 |
| **Synth** | 15 | MSB 10, LSB 0-14 |
| **Percussion** | 20 | MSB 11, LSB 0-19 |
| **Ethnic** | 18 | MSB 12, LSB 0-17 |
| **Effects** | 12 | MSB 13, LSB 0-11 |

**Total: 270+ NRPN mappings → 100+ unique articulations**

### **2.2 Genos2-Specific Articulations**

#### **Saxophone (S.Art2 Voices)**
```
- Fall (quick pitch drop at note end)
- Doit (quick pitch rise at note start)
- Scoop (glide into note)
- Growl (rough texture)
- Sub-tone (breathy, intimate sound)
- Key Click (mechanical key noise)
- Breath Noise (air sound)
- Flutter Tongue (rapid tongue tremolo)
- Double Tongue (articulation technique)
- Triple Tongue (advanced articulation)
- Lip Trill (embouchure trill)
- Bend Up/Down (pitch bend)
- Glissando Up/Down (pitch glide)
```

#### **Strings (S.Art2 Voices)**
```
- Spiccato (bounced bow)
- Sautillé (fast spiccato)
- Martelé (hammered bow)
- Ricochet (thrown bow)
- Flautando (flute-like)
- Sul G (play on G string)
- Con Sordino (with mute)
- Senza Sordino (without mute)
- Pizzicato Snap (snap pizzicato)
- Pizzicato Left Hand (left hand pizzicato)
- Pizzicato Right Hand (right hand pizzicato)
- Pizzicato Chord (chord pizzicato)
- Tremolo (rapid bow oscillation)
- Tremolo Sordino (muted tremolo)
- Portamento (pitch glide between notes)
```

#### **Guitar (S.Art2 Voices)**
```
- Hammer-On
- Pull-Off
- Slide Up
- Slide Down
- Bend
- Bend Release
- Pre-Bend
- Vibrato
- Palm Mute
- Harmonics (Natural)
- Harmonics (Artificial)
- Harmonics (Pinch)
- Tapping
- Slap (Bass)
- Pop (Bass)
- Mute
- Cut Noise
- Fret Noise
- String Noise
- Body Hit
```

---

## 3. Enhancement Plan

### **Phase 1: Core Expansion (Weeks 1-3)**

#### **3.1.1 Expand Articulation Definitions**

**File:** `synth/xg/sart/articulation_controller.py`

**Changes:**
```python
# Add new articulation categories
NRPN_ARTICULATION_MAP = {
    # ... existing mappings ...
    
    # Wind - Saxophone (MSB 3)
    (3, 10): 'sub_tone',
    (3, 11): 'key_click',
    (3, 12): 'breath_noise',
    (3, 13): 'double_tongue',
    (3, 14): 'triple_tongue',
    (3, 15): 'lip_trill',
    (3, 16): 'bend_up',
    (3, 17): 'bend_down',
    (3, 18): 'glissando_up',
    (3, 19): 'glissando_down',
    
    # Wind - Brass (MSB 4)
    (4, 10): 'shake',
    (4, 11): 'drop',
    (4, 12): 'doit',
    (4, 13): 'fall',
    (4, 14): 'scoop',
    (4, 15): 'plop',
    (4, 16): 'lift',
    (4, 17): 'smooth_fall',
    (4, 18): 'rough_fall',
    (4, 19): 'long_fall',
    
    # Strings - Bow (MSB 6)
    (6, 10): 'spiccato',
    (6, 11): 'sautillé',
    (6, 12): 'martelé',
    (6, 13): 'ricochet',
    (6, 14): 'flautando',
    (6, 15): 'sul_g',
    (6, 16): 'con_sordino',
    (6, 17): 'senza_sordino',
    (6, 18): 'tremolo',
    (6, 19): 'tremolo_sordino',
    (6, 20): 'portamento',
    (6, 21): 'portamento_fast',
    
    # Guitar (MSB 8)
    (8, 10): 'slide_up',
    (8, 11): 'slide_down',
    (8, 12): 'bend',
    (8, 13): 'bend_release',
    (8, 14): 'pre_bend',
    (8, 15): 'harmonics_natural',
    (8, 16): 'harmonics_artificial',
    (8, 17): 'harmonics_pinch',
    (8, 18): 'tapping',
    (8, 19): 'slap',
    (8, 20): 'pop',
    (8, 21): 'mute',
    (8, 22): 'cut_noise',
    (8, 23): 'fret_noise',
    (8, 24): 'string_noise',
    (8, 25): 'body_hit',
}
```

**Lines to Add:** ~200

---

#### **3.1.2 Add Articulation Parameters**

**File:** `synth/xg/sart/articulation_controller.py`

**Changes:**
```python
# Enhanced articulation parameters
self.articulation_params = {
    # ... existing params ...
    
    # Saxophone-specific
    'sub_tone': {
        'breath_level': 0.3,
        'tone_darkness': 0.5,
        'volume_reduction': 0.7
    },
    'key_click': {
        'click_level': 0.4,
        'click_timing': -0.05,  # Before note
        'click_duration': 0.02
    },
    'breath_noise': {
        'noise_level': 0.2,
        'noise_filter': 2000.0,  # Hz
        'breath_timing': 0.0     # Continuous
    },
    'double_tongue': {
        'speed': 8.0,            # Articulations per second
        'accent_pattern': [1, 0.5],
        'duration': 0.1
    },
    
    # Strings-specific
    'spiccato': {
        'bounce_height': 0.5,
        'bounce_speed': 6.0,
        'bow_pressure': 0.6
    },
    'sautillé': {
        'speed': 12.0,           # Very fast
        'bow_division': 0.3,
        'pressure': 0.4
    },
    'martelé': {
        'attack_force': 0.9,
        'release_speed': 0.2,
        'accent': 1.0
    },
    'con_sordino': {
        'mute_level': 0.7,
        'tone_color': 0.4,
        'volume_reduction': 0.6
    },
    
    # Guitar-specific
    'harmonics_natural': {
        'harmonic_position': 0.5,  # 12th fret
        'harmonic_type': 'octave',
        'pluck_position': 0.8
    },
    'harmonics_artificial': {
        'fret_offset': 12,         # Octave harmonic
        'touch_pressure': 0.3,
        'pluck_force': 0.7
    },
    'tapping': {
        'tap_force': 0.8,
        'tap_position': 0.5,
        'pull_off_force': 0.5
    },
    'slap': {
        'slap_force': 0.9,
        'slap_position': 0.2,
        'pop_follow': 0.3
    },
}
```

**Lines to Add:** ~150

---

### **Phase 2: Advanced NRPN Implementation (Weeks 3-5)**

#### **3.2.1 Enhanced NRPN Mapper**

**File:** `synth/xg/sart/nrpn.py`

**Changes:**
```python
class YamahaNRPNMapper:
    """Enhanced NRPN mapper with Genos2 compatibility."""
    
    def __init__(self):
        # Expanded NRPN mappings
        self.nrpn_to_articulation = {
            # Category-based organization
            'common': {
                (1, 0): 'normal',
                # ... 0-49
            },
            'dynamics': {
                (2, 0): 'ppp',
                # ... 0-14
            },
            'wind_sax': {
                (3, 0): 'growl_wind',
                # ... 0-24
            },
            'wind_brass': {
                (4, 0): 'muted_brass',
                # ... 0-19
            },
            'strings_bow': {
                (6, 0): 'pizzicato_strings',
                # ... 0-21
            },
            'guitar': {
                (8, 0): 'hammer_on_guitar',
                # ... 0-24
            },
            'vocal': {
                (9, 0): 'vocal_breath',
                # ... 0-19
            },
            'synth': {
                (10, 0): 'synth_attack',
                # ... 0-14
            },
        }
    
    def get_articulation(self, msb: int, lsb: int, 
                        category: Optional[str] = None) -> str:
        """
        Get articulation from NRPN with category support.
        
        Args:
            msb: NRPN MSB
            lsb: NRPN LSB
            category: Optional category hint for disambiguation
        
        Returns:
            Articulation name
        """
        # Try category-specific lookup first
        if category and category in self.nrpn_to_articulation:
            key = (msb, lsb)
            if key in self.nrpn_to_articulation[category]:
                return self.nrpn_to_articulation[category][key]
        
        # Fall back to global lookup
        return self._simplified_map.get((msb, lsb), 'normal')
    
    def get_nrpn_for_articulation(self, articulation: str, 
                                  category: Optional[str] = None) -> Tuple[int, int]:
        """
        Get NRPN MSB/LSB for articulation (reverse lookup).
        
        Args:
            articulation: Articulation name
            category: Optional category hint
        
        Returns:
            Tuple of (msb, lsb)
        """
        # Search through categories
        for cat_name, mappings in self.nrpn_to_articulation.items():
            if category and cat_name != category:
                continue
            
            for (msb, lsb), art in mappings.items():
                if art == articulation:
                    return (msb, lsb)
        
        return (1, 0)  # Default to normal
```

**Lines to Add:** ~200

---

#### **3.2.2 NRPN Parameter Control**

**File:** `synth/xg/sart/nrpn.py`

**New Class:**
```python
class NRPNParameterController:
    """
    Advanced NRPN controller for articulation parameters.
    
    Supports:
    - Multi-parameter NRPN sequences
    - Parameter value ranges
    - Relative parameter changes
    - Parameter groups
    """
    
    def __init__(self):
        # Parameter NRPN mappings
        self.param_mappings = {
            # Format: (msb, lsb): (articulation, param_name, scale)
            (99, 0): ('vibrato', 'rate', 0.01),      # 0-127 → 0-1.27 Hz
            (99, 1): ('vibrato', 'depth', 0.01),     # 0-127 → 0-1.27
            (99, 2): ('vibrato', 'delay', 0.01),     # 0-127 → 0-1.27 sec
            (99, 10): ('legato', 'blend', 0.01),     # 0-127 → 0-1.27
            (99, 11): ('legato', 'transition_time', 0.01),
            (99, 20): ('growl', 'mod_freq', 1.0),    # 0-127 → 0-127 Hz
            (99, 21): ('growl', 'depth', 0.01),
            # ... 200+ parameter mappings
        }
    
    def process_parameter_nrpn(self, msb: int, lsb: int, 
                               value: int) -> Optional[Dict[str, Any]]:
        """
        Process NRPN parameter change.
        
        Args:
            msb: NRPN MSB (99 for parameters)
            lsb: NRPN LSB (parameter index)
            value: Parameter value (0-127)
        
        Returns:
            Parameter update dict or None
        """
        key = (msb, lsb)
        
        if key not in self.param_mappings:
            return None
        
        articulation, param_name, scale = self.param_mappings[key]
        
        return {
            'articulation': articulation,
            'param_name': param_name,
            'value': value * scale,
            'raw_value': value
        }
```

**Lines to Add:** ~150

---

### **Phase 3: Full SYSEX Implementation (Weeks 5-7)**

#### **3.3.1 SYSEX Message Parser**

**File:** `synth/xg/sart/articulation_controller.py`

**Changes:**
```python
class ArticulationController:
    """Enhanced with full SYSEX support."""
    
    # Yamaha S.Art2 SYSEX format
    # F0 43 10 4C [cmd] [data...] F7
    
    SYSEX_COMMANDS = {
        0x10: 'articulation_set',      # Set articulation
        0x11: 'articulation_param',    # Set articulation parameter
        0x12: 'articulation_release',  # Release articulation
        0x13: 'articulation_query',    # Query current articulation
        0x14: 'articulation_chain',    # Set articulation chain
        0x15: 'bulk_dump',             # Bulk articulation dump
        0x16: 'bulk_load',             # Bulk articulation load
        0x17: 'system_config',         # System configuration
    }
    
    def parse_sysex(self, sysex_data: bytes) -> Dict[str, Any]:
        """
        Parse SYSEX message with full Genos2 compatibility.
        
        Supported formats:
        
        1. Articulation Set:
           F0 43 10 4C 10 [channel] [art_msb] [art_lsb] F7
        
        2. Parameter Set:
           F0 43 10 4C 11 [channel] [param_msb] [param_lsb] [value_msb] [value_lsb] F7
        
        3. Articulation Chain:
           F0 43 10 4C 14 [channel] [count] [art1_msb] [art1_lsb] ... F7
        
        4. Bulk Dump:
           F0 43 10 4C 15 [channel] [data...] checksum F7
        
        Args:
            sysex_data: SYSEX byte data (including F0 and F7)
        
        Returns:
            Parsed SYSEX result dictionary
        """
        # Validate SYSEX format
        if len(sysex_data) < 8:
            return {'error': 'SYSEX too short'}
        
        if sysex_data[0] != 0xF0 or sysex_data[-1] != 0xF7:
            return {'error': 'Invalid SYSEX format'}
        
        # Validate Yamaha manufacturer ID
        if sysex_data[1:4] != bytes([0x43, 0x10, 0x4C]):
            return {'error': 'Not a Yamaha SYSEX'}
        
        # Get command
        cmd = sysex_data[4]
        cmd_name = self.SYSEX_COMMANDS.get(cmd, 'unknown')
        
        # Parse based on command
        if cmd == 0x10:  # Articulation Set
            return self._parse_sysex_articulation_set(sysex_data)
        elif cmd == 0x11:  # Parameter Set
            return self._parse_sysex_parameter_set(sysex_data)
        elif cmd == 0x14:  # Articulation Chain
            return self._parse_sysex_articulation_chain(sysex_data)
        elif cmd == 0x15:  # Bulk Dump
            return self._parse_sysex_bulk_dump(sysex_data)
        else:
            return {
                'command': cmd_name,
                'raw_data': sysex_data.hex()
            }
    
    def _parse_sysex_articulation_set(self, sysex_data: bytes) -> Dict[str, Any]:
        """Parse articulation set SYSEX."""
        if len(sysex_data) < 8:
            return {'error': 'Invalid articulation set SYSEX'}
        
        channel = sysex_data[5]
        art_msb = sysex_data[6]
        art_lsb = sysex_data[7]
        
        articulation = self.nrpn_mapper.get_articulation(art_msb, art_lsb)
        
        return {
            'command': 'set_articulation',
            'channel': channel,
            'articulation': articulation,
            'nrpn_msb': art_msb,
            'nrpn_lsb': art_lsb
        }
    
    def _parse_sysex_parameter_set(self, sysex_data: bytes) -> Dict[str, Any]:
        """Parse parameter set SYSEX."""
        if len(sysex_data) < 10:
            return {'error': 'Invalid parameter set SYSEX'}
        
        channel = sysex_data[5]
        param_msb = sysex_data[6]
        param_lsb = sysex_data[7]
        value = (sysex_data[8] << 7) | sysex_data[9]
        
        return {
            'command': 'set_parameter',
            'channel': channel,
            'param_msb': param_msb,
            'param_lsb': param_lsb,
            'value': value
        }
    
    def _parse_sysex_articulation_chain(self, sysex_data: bytes) -> Dict[str, Any]:
        """Parse articulation chain SYSEX."""
        if len(sysex_data) < 8:
            return {'error': 'Invalid articulation chain SYSEX'}
        
        channel = sysex_data[5]
        count = sysex_data[6]
        
        articulations = []
        offset = 7
        
        for i in range(count):
            if offset + 2 >= len(sysex_data):
                break
            
            art_msb = sysex_data[offset]
            art_lsb = sysex_data[offset + 1]
            articulation = self.nrpn_mapper.get_articulation(art_msb, art_lsb)
            articulations.append(articulation)
            offset += 2
        
        return {
            'command': 'set_articulation_chain',
            'channel': channel,
            'articulations': articulations
        }
    
    def build_sysex_articulation_set(self, channel: int, 
                                     art_msb: int, art_lsb: int) -> bytes:
        """
        Build SYSEX message for articulation set.
        
        Args:
            channel: MIDI channel (0-15)
            art_msb: Articulation MSB
            art_lsb: Articulation LSB
        
        Returns:
            SYSEX byte sequence
        """
        return bytes([
            0xF0, 0x43, 0x10, 0x4C, 0x10,
            channel & 0x0F,
            art_msb & 0x7F,
            art_lsb & 0x7F,
            0xF7
        ])
    
    def build_sysex_parameter_set(self, channel: int, param_msb: int,
                                  param_lsb: int, value: int) -> bytes:
        """
        Build SYSEX message for parameter set.
        
        Args:
            channel: MIDI channel
            param_msb: Parameter MSB
            param_lsb: Parameter LSB
            value: Parameter value (0-16383)
        
        Returns:
            SYSEX byte sequence
        """
        return bytes([
            0xF0, 0x43, 0x10, 0x4C, 0x11,
            channel & 0x0F,
            param_msb & 0x7F,
            param_lsb & 0x7F,
            (value >> 7) & 0x7F,
            value & 0x7F,
            0xF7
        ])
```

**Lines to Add:** ~300

---

#### **3.3.2 SYSEX Bulk Operations**

**File:** `synth/xg/sart/articulation_controller.py`

**New Methods:**
```python
class ArticulationController:
    """Bulk SYSEX operations."""
    
    def build_sysex_bulk_dump(self, channel: int, 
                             articulations: List[str]) -> bytes:
        """
        Build SYSEX bulk dump of articulations.
        
        Args:
            channel: MIDI channel
            articulations: List of articulation names
        
        Returns:
            SYSEX bulk dump message
        """
        data = [0xF0, 0x43, 0x10, 0x4C, 0x15, channel & 0x0F]
        
        for art in articulations:
            msb, lsb = self._find_nrpn_for_articulation(art)
            data.extend([msb & 0x7F, lsb & 0x7F])
        
        # Calculate checksum
        checksum = self._calculate_sysex_checksum(data[1:])  # Exclude F0
        data.append(checksum)
        data.append(0xF7)
        
        return bytes(data)
    
    def build_sysex_articulation_chain(self, channel: int,
                                      chain: List[Tuple[str, float]]) -> bytes:
        """
        Build SYSEX articulation chain with timing.
        
        Args:
            channel: MIDI channel
            chain: List of (articulation, duration) tuples
        
        Returns:
            SYSEX chain message
        """
        data = [0xF0, 0x43, 0x10, 0x4C, 0x14, channel & 0x0F, len(chain)]
        
        for art, duration in chain:
            msb, lsb = self._find_nrpn_for_articulation(art)
            data.extend([msb & 0x7F, lsb & 0x7F])
            # Duration as 2 bytes (0-16383 ms)
            duration_ms = int(duration * 1000)
            data.extend([(duration_ms >> 7) & 0x7F, duration_ms & 0x7F])
        
        data.append(0xF7)
        return bytes(data)
    
    def _calculate_sysex_checksum(self, data: bytes) -> int:
        """
        Calculate Yamaha SYSEX checksum.
        
        Args:
            data: SYSEX data (excluding F0 and F7)
        
        Returns:
            Checksum byte
        """
        checksum = 0
        for byte in data:
            checksum += byte
        
        # Yamaha checksum: invert lower 7 bits
        return (~checksum & 0x7F)
```

**Lines to Add:** ~100

---

### **Phase 4: Advanced Features (Weeks 7-9)**

#### **3.4.1 Articulation Chaining**

**File:** `synth/xg/sart/sart2_region.py`

**New Feature:**
```python
class SArt2Region:
    """Enhanced with articulation chaining."""
    
    def __init__(self, base_region: IRegion, sample_rate: int = 44100,
                 enable_sample_modification: bool = True):
        # ... existing init ...
        
        # Articulation chain support
        self._articulation_chain: List[Tuple[str, float]] = []
        self._chain_index = 0
        self._chain_start_time = 0.0
        self._chain_active = False
    
    def set_articulation_chain(self, chain: List[Tuple[str, float]]) -> None:
        """
        Set articulation chain with timing.
        
        Args:
            chain: List of (articulation, duration) tuples
                   Example: [('attack', 0.1), ('sustain', 0.5), ('release', 0.3)]
        """
        self._articulation_chain = chain
        self._chain_index = 0
        self._chain_active = len(chain) > 0
        
        if self._chain_active:
            self._start_chain()
    
    def _start_chain(self) -> None:
        """Start articulation chain execution."""
        if not self._articulation_chain:
            return
        
        self._chain_start_time = time.time()
        art, duration = self._articulation_chain[0]
        self.set_articulation(art)
        self._chain_duration = duration
    
    def _update_chain(self) -> None:
        """Update articulation chain (call per audio block)."""
        if not self._chain_active:
            return
        
        elapsed = time.time() - self._chain_start_time
        
        if elapsed >= self._chain_duration:
            # Move to next articulation in chain
            self._chain_index += 1
            
            if self._chain_index >= len(self._articulation_chain):
                # Chain complete
                self._chain_active = False
                return
            
            # Start next articulation
            art, duration = self._articulation_chain[self._chain_index]
            self.set_articulation(art)
            self._chain_start_time = time.time()
            self._chain_duration = duration
```

**Lines to Add:** ~100

---

#### **3.4.2 Velocity-Based Articulation Switching**

**File:** `synth/xg/sart/sart2_region.py`

**New Feature:**
```python
class SArt2Region:
    """Enhanced with velocity-based articulation."""
    
    def __init__(self, base_region: IRegion, sample_rate: int = 44100,
                 enable_sample_modification: bool = True):
        # ... existing init ...
        
        # Velocity-based articulation
        self._velocity_articulations: Dict[Tuple[int, int], str] = {}
        self._velocity_enabled = False
    
    def set_velocity_articulation(self, vel_low: int, vel_high: int,
                                  articulation: str) -> None:
        """
        Set articulation for velocity range.
        
        Args:
            vel_low: Low velocity bound (0-127)
            vel_high: High velocity bound (0-127)
            articulation: Articulation name
        
        Example:
            region.set_velocity_articulation(0, 64, 'soft')
            region.set_velocity_articulation(65, 100, 'medium')
            region.set_velocity_articulation(101, 127, 'hard')
        """
        self._velocity_articulations[(vel_low, vel_high)] = articulation
        self._velocity_enabled = True
    
    def note_on(self, velocity: int, note: int) -> bool:
        """Enhanced note-on with velocity-based articulation."""
        # Apply velocity-based articulation if enabled
        if self._velocity_enabled:
            articulation = self._get_articulation_for_velocity(velocity)
            if articulation:
                self.set_articulation(articulation)
        
        return super().note_on(velocity, note)
    
    def _get_articulation_for_velocity(self, velocity: int) -> Optional[str]:
        """Get articulation for velocity."""
        for (vel_low, vel_high), articulation in self._velocity_articulations.items():
            if vel_low <= velocity <= vel_high:
                return articulation
        return None
```

**Lines to Add:** ~80

---

#### **3.4.3 Key-Based Articulation Switching**

**File:** `synth/xg/sart/sart2_region.py`

**New Feature:**
```python
class SArt2Region:
    """Enhanced with key-based articulation."""
    
    def __init__(self, base_region: IRegion, sample_rate: int = 44100,
                 enable_sample_modification: bool = True):
        # ... existing init ...
        
        # Key-based articulation
        self._key_articulations: Dict[Tuple[int, int], str] = {}
        self._key_enabled = False
    
    def set_key_articulation(self, key_low: int, key_high: int,
                            articulation: str) -> None:
        """
        Set articulation for key range.
        
        Args:
            key_low: Low key bound (0-127)
            key_high: High key bound (0-127)
            articulation: Articulation name
        
        Example:
            region.set_key_articulation(0, 47, 'bass')
            region.set_key_articulation(48, 83, 'mid')
            region.set_key_articulation(84, 127, 'treble')
        """
        self._key_articulations[(key_low, key_high)] = articulation
        self._key_enabled = True
    
    def note_on(self, velocity: int, note: int) -> bool:
        """Enhanced note-on with key-based articulation."""
        # Apply key-based articulation if enabled
        if self._key_enabled:
            articulation = self._get_articulation_for_key(note)
            if articulation:
                self.set_articulation(articulation)
        
        return super().note_on(velocity, note)
    
    def _get_articulation_for_key(self, note: int) -> Optional[str]:
        """Get articulation for key."""
        for (key_low, key_high), articulation in self._key_articulations.items():
            if key_low <= note <= key_high:
                return articulation
        return None
```

**Lines to Add:** ~80

---

### **Phase 5: Testing & Documentation (Weeks 9-10)**

#### **3.5.1 Test Suite Expansion**

**File:** `tests/test_sart2_enhanced.py` (NEW)

**Test Categories:**
```python
# New articulations
class TestNewArticulations:
    def test_saxophone_articulations(self): ...
    def test_strings_bow_articulations(self): ...
    def test_guitar_techniques(self): ...

# NRPN enhancements
class TestNRPNEnhanced:
    def test_category_based_nrpn(self): ...
    def test_reverse_nrpn_lookup(self): ...
    def test_parameter_nrpn(self): ...

# SYSEX implementation
class TestSYSEXEnhanced:
    def test_sysex_parameter_set(self): ...
    def test_sysex_articulation_chain(self): ...
    def test_sysex_bulk_dump(self): ...
    def test_sysex_checksum(self): ...

# Advanced features
class TestAdvancedFeatures:
    def test_articulation_chain(self): ...
    def test_velocity_articulation(self): ...
    def test_key_articulation(self): ...
    def test_articulation_transitions(self): ...
```

**Lines to Add:** ~500

---

#### **3.5.2 Documentation Updates**

**Files to Create/Update:**
```
docs/
├── SART2_ENHANCEMENT_GUIDE.md      # NEW - Enhancement overview
├── SART2_NRPN_REFERENCE.md         # NEW - Complete NRPN mapping
├── SART2_SYSEX_REFERENCE.md        # NEW - SYSEX format reference
├── SART2_API.md                    # UPDATE - New articulations
├── SART2_USER_GUIDE.md             # UPDATE - Advanced features
└── SART2_GENOS2_COMPATIBILITY.md   # NEW - Genos2 compatibility guide
```

---

## 4. Implementation Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1: Core Expansion** | Weeks 1-3 | 100+ articulations, 200+ NRPN mappings |
| **Phase 2: Advanced NRPN** | Weeks 3-5 | Category-based NRPN, parameter control |
| **Phase 3: Full SYSEX** | Weeks 5-7 | Complete SYSEX parser/builder |
| **Phase 4: Advanced Features** | Weeks 7-9 | Chaining, velocity/key switching |
| **Phase 5: Testing & Docs** | Weeks 9-10 | Test suite, documentation |

**Total: 10 weeks (~400 hours)**

---

## 5. Files Summary

### **Files to Create (5)**
1. `tests/test_sart2_enhanced.py` - Enhanced test suite
2. `docs/SART2_ENHANCEMENT_GUIDE.md` - Enhancement guide
3. `docs/SART2_NRPN_REFERENCE.md` - NRPN reference
4. `docs/SART2_SYSEX_REFERENCE.md` - SYSEX reference
5. `docs/SART2_GENOS2_COMPATIBILITY.md` - Genos2 compatibility

### **Files to Modify (5)**
1. `synth/xg/sart/articulation_controller.py` (+500 lines)
2. `synth/xg/sart/nrpn.py` (+350 lines)
3. `synth/xg/sart/sart2_region.py` (+260 lines)
4. `synth/xg/sart/__init__.py` (exports update)
5. `synth/engine/modern_xg_synthesizer.py` (integration)

**Total Lines to Add:** ~2,110 lines

---

## 6. Success Criteria

| Criteria | Target | Measurement |
|----------|--------|-------------|
| **Articulations** | 100+ | Count in articulation_controller.py |
| **NRPN Mappings** | 200+ | Count in nrpn.py |
| **SYSEX Commands** | 8+ | SYSEX_COMMANDS dict size |
| **Test Coverage** | >85% | pytest coverage report |
| **Genos2 Compatibility** | 90%+ | Feature comparison matrix |
| **Performance** | <10% overhead | Benchmark comparison |

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **NRPN conflicts** | Medium | High | Careful mapping, testing |
| **SYSEX compatibility** | Medium | Medium | Test with Genos2 |
| **Performance regression** | Low | High | Continuous benchmarking |
| **Documentation gaps** | Medium | Low | Iterative documentation |
| **Testing coverage** | Low | Medium | Comprehensive test suite |

---

## 8. Conclusion

This enhancement plan will bring S.Art2 to Genos2 parity with:

- ✅ **100+ articulations** (vs. 35+ current)
- ✅ **200+ NRPN mappings** (vs. 70+ current)
- ✅ **Full SYSEX support** (vs. basic current)
- ✅ **Advanced features** (chaining, velocity/key switching)
- ✅ **Genos2 compatibility** (90%+ feature parity)

**Estimated Effort:** 400 hours over 10 weeks  
**Priority:** High for professional music production use  
**Recommendation:** **PROCEED** with phased implementation

---

**Plan Complete** ✅
