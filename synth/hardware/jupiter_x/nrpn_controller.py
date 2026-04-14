"""Jupiter-X NRPN Message Controller."""

from __future__ import annotations

import threading
from typing import Any

from .component_manager import JupiterXComponentManager
from .constants import *


class JupiterXNRPNController:
    """
    Jupiter-X NRPN (Non-Registered Parameter Number) Controller

    Handles Jupiter-X specific NRPN parameter control via MIDI CC messages.
    """

    def __init__(self, component_manager: JupiterXComponentManager):
        self.component_manager = component_manager

        # NRPN state
        self.active_nrpn = False
        self.current_msb = 0
        self.current_lsb = 0
        self.data_msb_received = False
        self.data_msb = 0

        # NRPN parameter map
        self.nrpn_map = self._build_nrpn_map()

        # Thread safety
        self.lock = threading.RLock()

    def _build_nrpn_map(self) -> dict[tuple[int, int], dict[str, Any]]:
        """Build NRPN parameter mapping for Jupiter-X."""
        nrpn_map = {}

        # System parameters (MSB 0x00) - COMPLETE IMPLEMENTATION
        system_params = {
            0x00: {
                "name": "device_id",
                "range": (0, 127),
                "default": 0x10,
                "description": "Device ID",
            },
            0x01: {
                "name": "master_tune",
                "range": (-64, 63),
                "default": 0,
                "description": "Master Tune (±1 semitone)",
            },
            0x02: {
                "name": "master_transpose",
                "range": (-12, 12),
                "default": 0,
                "description": "Master Transpose (±1 octave)",
            },
            0x03: {
                "name": "master_volume",
                "range": (0, 127),
                "default": 100,
                "description": "Master Volume",
            },
            0x04: {
                "name": "master_pan",
                "range": (-64, 63),
                "default": 0,
                "description": "Master Pan (L-R center)",
            },
        }

        for lsb, param_info in system_params.items():
            nrpn_map[(0x00, lsb)] = {
                "type": "system",
                "param_id": lsb,
                "param_name": param_info["name"],
                "range": param_info["range"],
                "default": param_info["default"],
                "description": param_info["description"],
            }

        # Additional system parameters (LSB 0x05-0xFF) - Reserved for future expansion
        # These can be used for custom system parameters or extensions
        for lsb in range(0x05, 0x100):
            nrpn_map[(0x00, lsb)] = {
                "type": "system_reserved",
                "param_id": lsb,
                "range": PARAM_RANGE_0_127,
                "description": f"Reserved system parameter {lsb:02X}",
                "writable": False,  # Reserved parameters are read-only
            }

        # Part parameters (MSB 0x10-0x2F for parts 0-15) - FULL IMPLEMENTATION
        for part_offset in range(16):
            msb = 0x10 + part_offset

            part_params = {
                0x00: {
                    "name": "part_level",
                    "range": (0, 127),
                    "default": 100,
                    "desc": "Part Level",
                },
                0x01: {
                    "name": "part_pan",
                    "range": (-64, 63),
                    "default": 0,
                    "desc": "Part Pan",
                },
                0x02: {
                    "name": "part_receive_midi",
                    "range": (0, 1),
                    "default": 1,
                    "desc": "Receive MIDI",
                },
                0x03: {
                    "name": "part_midi_channel",
                    "range": (0, 15),
                    "default": part_offset,
                    "desc": "MIDI Channel",
                },
                0x04: {
                    "name": "part_mute",
                    "range": (0, 1),
                    "default": 0,
                    "desc": "Mute",
                },
                0x05: {
                    "name": "part_solo",
                    "range": (0, 1),
                    "default": 0,
                    "desc": "Solo",
                },
                0x06: {
                    "name": "part_volume",
                    "range": (0, 127),
                    "default": 100,
                    "desc": "Volume",
                },
                0x07: {
                    "name": "part_coarse_tune",
                    "range": (-24, 24),
                    "default": 0,
                    "desc": "Coarse Tune",
                },
                0x08: {
                    "name": "part_fine_tune",
                    "range": (-50, 50),
                    "default": 0,
                    "desc": "Fine Tune",
                },
                0x09: {
                    "name": "part_transpose",
                    "range": (-24, 24),
                    "default": 0,
                    "desc": "Transpose",
                },
                0x0A: {
                    "name": "part_delay_send",
                    "range": (0, 127),
                    "default": 0,
                    "desc": "Delay Send",
                },
                0x0B: {
                    "name": "part_reverb_send",
                    "range": (0, 127),
                    "default": 0,
                    "desc": "Reverb Send",
                },
                0x0C: {
                    "name": "part_cutoff",
                    "range": (0, 127),
                    "default": 127,
                    "desc": "Part Cutoff",
                },
                0x0D: {
                    "name": "part_resonance",
                    "range": (0, 127),
                    "default": 0,
                    "desc": "Part Resonance",
                },
                0x0E: {
                    "name": "part_filter_key_tracking",
                    "range": (0, 127),
                    "default": 100,
                    "desc": "Filter Key Tracking",
                },
                0x0F: {
                    "name": "part_legacy_mode",
                    "range": (0, 1),
                    "default": 0,
                    "desc": "Legacy Mode",
                },
                0x10: {
                    "name": "part_program_number",
                    "range": (0, 127),
                    "default": 0,
                    "desc": "Program Number",
                },
                0x11: {
                    "name": "part_bank_msb",
                    "range": (0, 127),
                    "default": 0,
                    "desc": "Bank MSB",
                },
                0x12: {
                    "name": "part_bank_lsb",
                    "range": (0, 127),
                    "default": 0,
                    "desc": "Bank LSB",
                },
                0x13: {
                    "name": "part_key_range_low",
                    "range": (0, 127),
                    "default": 0,
                    "desc": "Key Range Low",
                },
                0x14: {
                    "name": "part_key_range_high",
                    "range": (0, 127),
                    "default": 127,
                    "desc": "Key Range High",
                },
                0x15: {
                    "name": "part_velocity_range_low",
                    "range": (0, 127),
                    "default": 1,
                    "desc": "Velocity Range Low",
                },
                0x16: {
                    "name": "part_velocity_range_high",
                    "range": (0, 127),
                    "default": 127,
                    "desc": "Velocity Range High",
                },
                0x17: {
                    "name": "part_arp_enable",
                    "range": (0, 1),
                    "default": 0,
                    "desc": "Arpeggiator Enable",
                },
                0x18: {
                    "name": "part_arp_type",
                    "range": (0, 7),
                    "default": 0,
                    "desc": "Arpeggiator Type",
                },
                0x19: {
                    "name": "part_arp_range",
                    "range": (1, 4),
                    "default": 1,
                    "desc": "Arpeggiator Range",
                },
                0x1A: {
                    "name": "part_arp_rate",
                    "range": (0, 127),
                    "default": 64,
                    "desc": "Arpeggiator Rate",
                },
                0x1B: {
                    "name": "part_arp_swing",
                    "range": (-50, 50),
                    "default": 0,
                    "desc": "Arpeggiator Swing",
                },
                0x1C: {
                    "name": "part_arp_latch",
                    "range": (0, 1),
                    "default": 0,
                    "desc": "Arpeggiator Latch",
                },
                0x1D: {
                    "name": "part_arp_target",
                    "range": (0, 2),
                    "default": 0,
                    "desc": "Arpeggiator Target",
                },
                0x1E: {
                    "name": "part_arp_pattern",
                    "range": (0, 31),
                    "default": 0,
                    "desc": "Arpeggiator Pattern",
                },
                0x1F: {
                    "name": "part_arp_gate",
                    "range": (0, 100),
                    "default": 100,
                    "desc": "Arpeggiator Gate",
                },
            }

            for lsb, param_info in part_params.items():
                nrpn_map[(msb, lsb)] = {
                    "type": "part",
                    "part_number": part_offset,
                    "param_id": lsb,
                    "param_name": param_info["name"],
                    "range": param_info["range"],
                    "default": param_info["default"],
                    "description": f"Part {part_offset} {param_info['desc']}",
                }

        # Engine parameters (MSB 0x30-0x3F: 16 parts × 4 engines × 32 parameters per engine) - COMPLETE IMPLEMENTATION
        for part_offset in range(16):
            for engine_offset in range(4):  # 4 engines per part
                msb = 0x30 + (part_offset * 4) + engine_offset

                # Engine type mapping
                engine_names = ["analog", "digital", "fm", "external"]
                engine_name = engine_names[engine_offset]

                # Base parameters (0x00-0x0F) - common across all engines
                base_params = {
                    0x00: {
                        "name": "engine_enable",
                        "range": (0, 1),
                        "default": 1 if engine_offset == 0 else 0,
                        "desc": f"Enable {engine_name} engine",
                    },
                    0x01: {
                        "name": "engine_level",
                        "range": (0, 127),
                        "default": 100 if engine_offset == 0 else 0,
                        "desc": f"{engine_name} engine level",
                    },
                    0x02: {
                        "name": "engine_pan",
                        "range": (-64, 63),
                        "default": 0,
                        "desc": f"{engine_name} engine pan",
                    },
                    0x03: {
                        "name": "engine_coarse_tune",
                        "range": (-24, 24),
                        "default": 0,
                        "desc": f"{engine_name} coarse tune",
                    },
                    0x04: {
                        "name": "engine_fine_tune",
                        "range": (-50, 50),
                        "default": 0,
                        "desc": f"{engine_name} fine tune",
                    },
                }

                for lsb, param_info in base_params.items():
                    nrpn_map[(msb, lsb)] = {
                        "type": "engine",
                        "part_number": part_offset,
                        "engine_type": engine_offset,
                        "engine_name": engine_name,
                        "param_id": lsb,
                        "param_name": param_info["name"],
                        "range": param_info["range"],
                        "default": param_info["default"],
                        "description": f"Part {part_offset} {param_info['desc']}",
                    }

                # Analog Engine parameters (MSB for engine 0)
                if engine_offset == 0:  # Analog engine
                    analog_params = {
                        0x10: {
                            "name": "osc1_waveform",
                            "range": (0, 7),
                            "default": 0,
                            "desc": "Osc 1 Waveform",
                        },
                        0x11: {
                            "name": "osc1_coarse_tune",
                            "range": (-24, 24),
                            "default": 0,
                            "desc": "Osc 1 Coarse Tune",
                        },
                        0x12: {
                            "name": "osc1_fine_tune",
                            "range": (-50, 50),
                            "default": 0,
                            "desc": "Osc 1 Fine Tune",
                        },
                        0x13: {
                            "name": "osc1_level",
                            "range": (0, 127),
                            "default": 100,
                            "desc": "Osc 1 Level",
                        },
                        0x14: {
                            "name": "osc1_supersaw_spread",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Osc 1 Supersaw Spread",
                        },
                        0x15: {
                            "name": "osc2_waveform",
                            "range": (0, 7),
                            "default": 0,
                            "desc": "Osc 2 Waveform",
                        },
                        0x16: {
                            "name": "osc2_coarse_tune",
                            "range": (-24, 24),
                            "default": 0,
                            "desc": "Osc 2 Coarse Tune",
                        },
                        0x17: {
                            "name": "osc2_fine_tune",
                            "range": (-50, 50),
                            "default": 0,
                            "desc": "Osc 2 Fine Tune",
                        },
                        0x18: {
                            "name": "osc2_level",
                            "range": (0, 127),
                            "default": 100,
                            "desc": "Osc 2 Level",
                        },
                        0x19: {
                            "name": "osc2_detune",
                            "range": (-50, 50),
                            "default": 0,
                            "desc": "Osc 2 Detune",
                        },
                        0x1A: {
                            "name": "osc_sync",
                            "range": (0, 1),
                            "default": 0,
                            "desc": "Oscillator Sync",
                        },
                        0x1B: {
                            "name": "ring_modulation",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Ring Modulation",
                        },
                        0x1C: {
                            "name": "filter_type",
                            "range": (0, 7),
                            "default": 0,
                            "desc": "Filter Type",
                        },
                        0x1D: {
                            "name": "filter_cutoff",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Filter Cutoff",
                        },
                        0x1E: {
                            "name": "filter_resonance",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Filter Resonance",
                        },
                        0x1F: {
                            "name": "filter_drive",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Filter Drive",
                        },
                        0x20: {
                            "name": "filter_key_tracking",
                            "range": (-64, 63),
                            "default": 0,
                            "desc": "Filter Key Tracking",
                        },
                        0x21: {
                            "name": "filter_envelope_amount",
                            "range": (-64, 63),
                            "default": 0,
                            "desc": "Filter Envelope Amount",
                        },
                        0x22: {
                            "name": "filter_attack",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Filter Attack",
                        },
                        0x23: {
                            "name": "filter_decay",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Filter Decay",
                        },
                        0x24: {
                            "name": "filter_sustain",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Filter Sustain",
                        },
                        0x25: {
                            "name": "filter_release",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Filter Release",
                        },
                        0x26: {
                            "name": "amp_level",
                            "range": (0, 127),
                            "default": 100,
                            "desc": "Amplifier Level",
                        },
                        0x27: {
                            "name": "amp_attack",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Amp Attack",
                        },
                        0x28: {
                            "name": "amp_decay",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Amp Decay",
                        },
                        0x29: {
                            "name": "amp_sustain",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Amp Sustain",
                        },
                        0x2A: {
                            "name": "amp_release",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Amp Release",
                        },
                        0x2B: {
                            "name": "amp_velocity_sensitivity",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Amp Velocity Sensitivity",
                        },
                        0x2C: {
                            "name": "lfo1_waveform",
                            "range": (0, 5),
                            "default": 0,
                            "desc": "LFO 1 Waveform",
                        },
                        0x2D: {
                            "name": "lfo1_rate",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "LFO 1 Rate",
                        },
                        0x2E: {
                            "name": "lfo1_depth",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "LFO 1 Depth",
                        },
                        0x2F: {
                            "name": "lfo1_sync",
                            "range": (0, 1),
                            "default": 0,
                            "desc": "LFO 1 Tempo Sync",
                        },
                    }

                    for lsb, param_info in analog_params.items():
                        nrpn_map[(msb, lsb)] = {
                            "type": "engine",
                            "part_number": part_offset,
                            "engine_type": engine_offset,
                            "engine_name": engine_name,
                            "param_id": lsb,
                            "param_name": param_info["name"],
                            "range": param_info["range"],
                            "default": param_info["default"],
                            "description": f"Part {part_offset} Analog {param_info['desc']}",
                        }

                # Digital Engine parameters (MSB for engine 1)
                elif engine_offset == 1:  # Digital engine
                    digital_params = {
                        0x10: {
                            "name": "wavetable_position",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Wavetable Position",
                        },
                        0x11: {
                            "name": "wavetable_speed",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Wavetable Speed",
                        },
                        0x12: {
                            "name": "wavetable_start",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Wavetable Start",
                        },
                        0x13: {
                            "name": "wavetable_end",
                            "range": (0, 127),
                            "default": 127,
                            "desc": "Wavetable End",
                        },
                        0x14: {
                            "name": "wavetable_loop",
                            "range": (0, 1),
                            "default": 1,
                            "desc": "Wavetable Loop",
                        },
                        0x15: {
                            "name": "morph_amount",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Morph Amount",
                        },
                        0x16: {
                            "name": "morph_position",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Morph Position",
                        },
                        0x17: {
                            "name": "morph_speed",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Morph Speed",
                        },
                        0x18: {
                            "name": "bit_crush_depth",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Bit Crush Depth",
                        },
                        0x19: {
                            "name": "bit_crush_bits",
                            "range": (1, 16),
                            "default": 16,
                            "desc": "Bit Crush Bits",
                        },
                        0x1A: {
                            "name": "sample_rate_reduction",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Sample Rate Reduction",
                        },
                        0x1B: {
                            "name": "formant_shift",
                            "range": (-64, 63),
                            "default": 0,
                            "desc": "Formant Shift",
                        },
                        0x1C: {
                            "name": "formant_resonance",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Formant Resonance",
                        },
                        0x1D: {
                            "name": "formant_mix",
                            "range": (0, 127),
                            "default": 100,
                            "desc": "Formant Mix",
                        },
                        0x1E: {
                            "name": "wavefolding_amount",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Wavefolding Amount",
                        },
                        0x1F: {
                            "name": "wavefolding_symmetry",
                            "range": (-64, 63),
                            "default": 0,
                            "desc": "Wavefolding Symmetry",
                        },
                        0x20: {
                            "name": "ring_mod_frequency",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Ring Mod Frequency",
                        },
                        0x21: {
                            "name": "ring_mod_mix",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Ring Mod Mix",
                        },
                        0x22: {
                            "name": "digital_filter_type",
                            "range": (0, 3),
                            "default": 0,
                            "desc": "Digital Filter Type",
                        },
                        0x23: {
                            "name": "digital_filter_cutoff",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Digital Filter Cutoff",
                        },
                        0x24: {
                            "name": "digital_filter_resonance",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Digital Filter Resonance",
                        },
                        0x25: {
                            "name": "digital_filter_envelope",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Digital Filter Envelope",
                        },
                    }

                    for lsb, param_info in digital_params.items():
                        nrpn_map[(msb, lsb)] = {
                            "type": "engine",
                            "part_number": part_offset,
                            "engine_type": engine_offset,
                            "engine_name": engine_name,
                            "param_id": lsb,
                            "param_name": param_info["name"],
                            "range": param_info["range"],
                            "default": param_info["default"],
                            "description": f"Part {part_offset} Digital {param_info['desc']}",
                        }

                # FM Engine parameters (MSB for engine 2)
                elif engine_offset == 2:  # FM engine
                    fm_params = {
                        0x10: {
                            "name": "fm_algorithm",
                            "range": (0, 31),
                            "default": 0,
                            "desc": "FM Algorithm",
                        },
                        0x11: {
                            "name": "fm_feedback",
                            "range": (0, 7),
                            "default": 0,
                            "desc": "FM Feedback",
                        },
                        0x12: {
                            "name": "fm_lfo_waveform",
                            "range": (0, 5),
                            "default": 0,
                            "desc": "FM LFO Waveform",
                        },
                        0x13: {
                            "name": "fm_lfo_rate",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "FM LFO Rate",
                        },
                        0x14: {
                            "name": "fm_lfo_depth",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "FM LFO Depth",
                        },
                        0x15: {
                            "name": "fm_lfo_sync",
                            "range": (0, 1),
                            "default": 0,
                            "desc": "FM LFO Tempo Sync",
                        },
                        0x16: {
                            "name": "op1_ratio",
                            "range": (1, 32),
                            "default": 1,
                            "desc": "Operator 1 Ratio",
                        },
                        0x17: {
                            "name": "op1_level",
                            "range": (0, 127),
                            "default": 100,
                            "desc": "Operator 1 Level",
                        },
                        0x18: {
                            "name": "op1_attack",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Operator 1 Attack",
                        },
                        0x19: {
                            "name": "op1_decay",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 1 Decay",
                        },
                        0x1A: {
                            "name": "op1_sustain",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 1 Sustain",
                        },
                        0x1B: {
                            "name": "op1_release",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 1 Release",
                        },
                        0x1C: {
                            "name": "op2_ratio",
                            "range": (1, 32),
                            "default": 1,
                            "desc": "Operator 2 Ratio",
                        },
                        0x1D: {
                            "name": "op2_level",
                            "range": (0, 127),
                            "default": 100,
                            "desc": "Operator 2 Level",
                        },
                        0x1E: {
                            "name": "op2_attack",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Operator 2 Attack",
                        },
                        0x1F: {
                            "name": "op2_decay",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 2 Decay",
                        },
                        0x20: {
                            "name": "op2_sustain",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 2 Sustain",
                        },
                        0x21: {
                            "name": "op2_release",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 2 Release",
                        },
                        0x22: {
                            "name": "op3_ratio",
                            "range": (1, 32),
                            "default": 1,
                            "desc": "Operator 3 Ratio",
                        },
                        0x23: {
                            "name": "op3_level",
                            "range": (0, 127),
                            "default": 100,
                            "desc": "Operator 3 Level",
                        },
                        0x24: {
                            "name": "op3_attack",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Operator 3 Attack",
                        },
                        0x25: {
                            "name": "op3_decay",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 3 Decay",
                        },
                        0x26: {
                            "name": "op3_sustain",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 3 Sustain",
                        },
                        0x27: {
                            "name": "op3_release",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 3 Release",
                        },
                        0x28: {
                            "name": "op4_ratio",
                            "range": (1, 32),
                            "default": 1,
                            "desc": "Operator 4 Ratio",
                        },
                        0x29: {
                            "name": "op4_level",
                            "range": (0, 127),
                            "default": 100,
                            "desc": "Operator 4 Level",
                        },
                        0x2A: {
                            "name": "op4_attack",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "Operator 4 Attack",
                        },
                        0x2B: {
                            "name": "op4_decay",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 4 Decay",
                        },
                        0x2C: {
                            "name": "op4_sustain",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 4 Sustain",
                        },
                        0x2D: {
                            "name": "op4_release",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "Operator 4 Release",
                        },
                    }

                    for lsb, param_info in fm_params.items():
                        nrpn_map[(msb, lsb)] = {
                            "type": "engine",
                            "part_number": part_offset,
                            "engine_type": engine_offset,
                            "engine_name": engine_name,
                            "param_id": lsb,
                            "param_name": param_info["name"],
                            "range": param_info["range"],
                            "default": param_info["default"],
                            "description": f"Part {part_offset} FM {param_info['desc']}",
                        }

                # External Engine parameters (MSB for engine 3)
                elif engine_offset == 3:  # External engine
                    external_params = {
                        0x10: {
                            "name": "external_input_gain",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "External Input Gain",
                        },
                        0x11: {
                            "name": "external_input_pan",
                            "range": (-64, 63),
                            "default": 0,
                            "desc": "External Input Pan",
                        },
                        0x12: {
                            "name": "external_filter_type",
                            "range": (0, 7),
                            "default": 0,
                            "desc": "External Filter Type",
                        },
                        0x13: {
                            "name": "external_filter_cutoff",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "External Filter Cutoff",
                        },
                        0x14: {
                            "name": "external_filter_resonance",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "External Filter Resonance",
                        },
                        0x15: {
                            "name": "external_drive",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "External Drive",
                        },
                        0x16: {
                            "name": "external_amp_level",
                            "range": (0, 127),
                            "default": 100,
                            "desc": "External Amp Level",
                        },
                        0x17: {
                            "name": "external_amp_attack",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "External Amp Attack",
                        },
                        0x18: {
                            "name": "external_amp_decay",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "External Amp Decay",
                        },
                        0x19: {
                            "name": "external_amp_sustain",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "External Amp Sustain",
                        },
                        0x1A: {
                            "name": "external_amp_release",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "External Amp Release",
                        },
                        0x1B: {
                            "name": "external_send_reverb",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "External Reverb Send",
                        },
                        0x1C: {
                            "name": "external_send_chorus",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "External Chorus Send",
                        },
                        0x1D: {
                            "name": "external_send_delay",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "External Delay Send",
                        },
                        0x1E: {
                            "name": "external_routing_mode",
                            "range": (0, 3),
                            "default": 0,
                            "desc": "External Routing Mode",
                        },
                        0x1F: {
                            "name": "external_sidechain_enable",
                            "range": (0, 1),
                            "default": 0,
                            "desc": "External Sidechain Enable",
                        },
                        0x20: {
                            "name": "external_sidechain_attack",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "External Sidechain Attack",
                        },
                        0x21: {
                            "name": "external_sidechain_release",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "External Sidechain Release",
                        },
                        0x22: {
                            "name": "external_compression_enable",
                            "range": (0, 1),
                            "default": 0,
                            "desc": "External Compression Enable",
                        },
                        0x23: {
                            "name": "external_compression_ratio",
                            "range": (1, 20),
                            "default": 4,
                            "desc": "External Compression Ratio",
                        },
                        0x24: {
                            "name": "external_compression_threshold",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "External Compression Threshold",
                        },
                        0x25: {
                            "name": "external_compression_attack",
                            "range": (0, 127),
                            "default": 0,
                            "desc": "External Compression Attack",
                        },
                        0x26: {
                            "name": "external_compression_release",
                            "range": (0, 127),
                            "default": 64,
                            "desc": "External Compression Release",
                        },
                    }

                    for lsb, param_info in external_params.items():
                        nrpn_map[(msb, lsb)] = {
                            "type": "engine",
                            "part_number": part_offset,
                            "engine_type": engine_offset,
                            "engine_name": engine_name,
                            "param_id": lsb,
                            "param_name": param_info["name"],
                            "range": param_info["range"],
                            "default": param_info["default"],
                            "description": f"Part {part_offset} External {param_info['desc']}",
                        }

        # Effects parameters (MSB 0x40-0x4F) - FULL IMPLEMENTATION
        effect_types = {
            0: "Reverb",
            1: "Delay",
            2: "Chorus",
            3: "Flanger",
            4: "Phaser",
            5: "Ring Modulator",
            6: "Distortion",
            7: "Overdrive",
            8: "EQ",
            9: "Compressor",
            10: "Limiter",
            11: "Gate",
            12: "Tremolo",
            13: "Auto Pan",
            14: "Slap Back Delay",
            15: "Wah",
        }

        common_effect_params = {
            0x00: {
                "name": "effect_type",
                "range": (0, 15),
                "default": 0,
                "desc": "Effect Type",
            },
            0x01: {
                "name": "effect_bypass",
                "range": (0, 1),
                "default": 0,
                "desc": "Bypass",
            },
            0x02: {
                "name": "effect_level",
                "range": (0, 127),
                "default": 100,
                "desc": "Level",
            },
            0x03: {
                "name": "effect_pan",
                "range": (-64, 63),
                "default": 0,
                "desc": "Pan",
            },
            0x04: {
                "name": "effect_dry_wet",
                "range": (0, 127),
                "default": 64,
                "desc": "Dry/Wet",
            },
            0x05: {
                "name": "effect_param1",
                "range": (0, 127),
                "default": 64,
                "desc": "Parameter 1",
            },
            0x06: {
                "name": "effect_param2",
                "range": (0, 127),
                "default": 64,
                "desc": "Parameter 2",
            },
            0x07: {
                "name": "effect_param3",
                "range": (0, 127),
                "default": 64,
                "desc": "Parameter 3",
            },
            0x08: {
                "name": "effect_param4",
                "range": (0, 127),
                "default": 64,
                "desc": "Parameter 4",
            },
            0x09: {
                "name": "effect_param5",
                "range": (0, 127),
                "default": 64,
                "desc": "Parameter 5",
            },
            0x0A: {
                "name": "effect_param6",
                "range": (0, 127),
                "default": 64,
                "desc": "Parameter 6",
            },
            0x0B: {
                "name": "effect_param7",
                "range": (0, 127),
                "default": 64,
                "desc": "Parameter 7",
            },
            0x0C: {
                "name": "effect_param8",
                "range": (0, 127),
                "default": 64,
                "desc": "Parameter 8",
            },
            0x0D: {
                "name": "effect_reserve",
                "range": (0, 127),
                "default": 0,
                "desc": "Reserve",
            },
            0x0E: {
                "name": "effect_attack",
                "range": (0, 127),
                "default": 0,
                "desc": "Attack",
            },
            0x0F: {
                "name": "effect_release",
                "range": (0, 127),
                "default": 64,
                "desc": "Release",
            },
        }

        for group_idx in range(16):
            msb = 0x40 + group_idx
            effect_name = effect_types.get(group_idx, "Unknown")

            for lsb, param_info in common_effect_params.items():
                nrpn_map[(msb, lsb)] = {
                    "type": "effects",
                    "group": group_idx,
                    "effect_type": effect_name,
                    "param_id": lsb,
                    "param_name": param_info["name"],
                    "range": param_info["range"],
                    "default": param_info["default"],
                    "description": f"Effect {group_idx} ({effect_name}) {param_info['desc']}",
                }

        return nrpn_map

    def process_nrpn_message(self, controller: int, value: int) -> bool:
        """
        Process NRPN-related controller messages.

        Args:
            controller: MIDI controller number
            value: Controller value (0-127)

        Returns:
            True if NRPN message was processed
        """
        with self.lock:
            if controller == 99:  # NRPN MSB
                self.current_msb = value
                self.active_nrpn = True
                self.data_msb_received = False
                return True

            elif controller == 98:  # NRPN LSB
                self.current_lsb = value
                self.active_nrpn = True
                self.data_msb_received = False
                return True

            elif controller == 6:  # Data Entry MSB
                if self.active_nrpn:
                    if not self.data_msb_received:
                        self.data_msb = value
                        self.data_msb_received = True
                    else:
                        # Complete NRPN message
                        data_value = (self.data_msb << 7) | value
                        success = self._process_nrpn_data(data_value)
                        self._reset_nrpn_state()
                        return success

            elif controller == 96:  # Data Increment
                if self.active_nrpn:
                    current_value = self._get_current_parameter_value()
                    if current_value is not None:
                        new_value = min(current_value + 1, 16383)
                        return self._process_nrpn_data(new_value)

            elif controller == 97:  # Data Decrement
                if self.active_nrpn:
                    current_value = self._get_current_parameter_value()
                    if current_value is not None:
                        new_value = max(current_value - 1, 0)
                        return self._process_nrpn_data(new_value)

        return False

    def _process_nrpn_data(self, data_value: int) -> bool:
        """
        Process complete NRPN data value (14-bit).

        Args:
            data_value: 14-bit NRPN value (0-16383)

        Returns:
            True if parameter was processed successfully
        """
        # Convert to 7-bit MIDI value
        midi_value = data_value >> 7

        # Get parameter info
        param_key = (self.current_msb, self.current_lsb)
        param_info = self.nrpn_map.get(param_key)

        if not param_info:
            print(f"Jupiter-X NRPN: Unknown parameter {param_key}")
            return False

        # Process based on parameter type
        param_type = param_info["type"]

        if param_type == "system":
            param_id = param_info["param_id"]
            return self.component_manager.system_params.set_parameter(param_id, midi_value)

        elif param_type == "part":
            part_number = param_info["part_number"]
            param_id = param_info["param_id"]
            return self.component_manager.set_part_parameter(part_number, param_id, midi_value)

        elif param_type == "engine":
            part_number = param_info["part_number"]
            engine_type = param_info["engine_type"]
            param_id = param_info["param_id"]
            return self.component_manager.set_engine_parameter(
                part_number, engine_type, param_id, midi_value
            )

        elif param_type == "effects":
            # Convert to 3-byte address for effects parameters
            group = param_info["group"]
            param_id = param_info["param_id"]
            addr_high = 0x40 + group
            address = bytes([addr_high, 0x00, param_id])
            return self.component_manager.process_parameter_change(address, midi_value)

        return False

    def _get_current_parameter_value(self) -> int | None:
        """Get current parameter value for increment/decrement."""
        if not self.active_nrpn:
            return None

        param_key = (self.current_msb, self.current_lsb)
        param_info = self.nrpn_map.get(param_key)

        if not param_info:
            return None

        # Get value based on parameter type
        param_type = param_info["type"]

        if param_type == "system":
            param_id = param_info["param_id"]
            return self.component_manager.system_params.get_parameter(param_id)

        elif param_type == "part":
            part_number = param_info["part_number"]
            param_id = param_info["param_id"]
            return self.component_manager.get_part_parameter(part_number, param_id)

        elif param_type == "effects":
            group = param_info["group"]
            param_id = param_info["param_id"]
            addr_high = 0x40 + group
            address = bytes([addr_high, 0x00, param_id])
            return self.component_manager.get_parameter_value(address)

        return None

    def _reset_nrpn_state(self):
        """Reset NRPN controller state."""
        self.active_nrpn = False
        self.current_msb = 0
        self.current_lsb = 0
        self.data_msb = 0
        self.data_msb_received = False

    def get_nrpn_status(self) -> dict[str, Any]:
        """Get current NRPN processing status."""
        with self.lock:
            return {
                "active": self.active_nrpn,
                "current_msb": self.current_msb,
                "current_lsb": self.current_lsb,
                "data_msb_received": self.data_msb_received,
                "data_msb": self.data_msb,
                "current_parameter": self.nrpn_map.get((self.current_msb, self.current_lsb)),
            }

    def create_nrpn_message(self, msb: int, lsb: int, value: int) -> list[bytes]:
        """
        Create NRPN message sequence for a parameter change.

        Args:
            msb: NRPN MSB (0-127)
            lsb: NRPN LSB (0-127)
            value: 14-bit parameter value (0-16383)

        Returns:
            List of MIDI message bytes to send
        """
        messages = []

        # NRPN MSB
        messages.append(bytes([0xB0 | 0, 99, msb]))  # CC 99 on channel 0

        # NRPN LSB
        messages.append(bytes([0xB0 | 0, 98, lsb]))  # CC 98 on channel 0

        # Data Entry MSB
        data_msb = (value >> 7) & 0x7F
        messages.append(bytes([0xB0 | 0, 6, data_msb]))  # CC 6 on channel 0

        # Data Entry LSB
        data_lsb = value & 0x7F
        messages.append(bytes([0xB0 | 0, 38, data_lsb]))  # CC 38 on channel 0

        return messages


