"""SF2 Default Modulators — from SoundFont 2.01 §8.4.11.

Default modulators apply system-wide when a zone has no explicit modulator
for a given destination. They implement velocity→attenuation, key→filter,
CC1→vibrato, and all other standard SF2 modulation routings.

Each entry is a dict with keys matching the SF2 modulator binary format:
    src_operator    — SF2 source operator bitfield (Controller, MIDIController,
                      Velocity, KeyNumber, ChannelPressure, PolyPressure, PitchWheel)
    dest_operator   — generator type to modulate
    mod_amount      — modulation depth in SF2 units
    amt_src_operator— secondary source controlling depth (0=constant)
    mod_trans_operator — transform: 0=linear, 1=absolute, 2=bipolar→unipolar

SF2 source operator encoding (16-bit):
    bits 0-6:  source index (0=none, 2=velocity, 3=keynum, 4-126=CC, 128=link)
    bit 7:     bipolar flag (source range [-1,+1] vs [0,+1])
    bit 8:     direction flag (invert)
    bit 9:     type flag (0=linear, 1=concave, only for Velocity source)
    bits 10-14:poles (14=center unipolar, 127=center bipolar)
    bit 15:    continuation (secondary source follows)
"""

# ── SF2 Source Operators (bitfield encoded) ───────────────────────────

NONE = 0x0000

# Modulation sources: index 2 (Velocity) with various flag combinations
# Bit 7=bipolar, bit 8=direction(invert), bit 9=type(concave)
KEYNUM = 0x0003  # index 3, unipolar
PITCH_WHEEL = 0x008E  # index 0x0E (14), bipolar

# Unipolar sources (range [0, 1])
NOTEON_VELOCITY = 0x0002  # index 2, unipolar, positive direction
NOTEON_VELOCITY_INV = 0x0102  # index 2, unipolar, inverted (1 - vel/127)

# MIDI CC sources -- controller number in bits 0-6, flag bits 7-14
CC1_MODWHEEL = 0x0081  # CC1, bipolar (bit 7=1), not inverted
CC7_VOLUME = 0x0107  # CC7, unipolar, inverted (bit 8=1)
CC10_PAN = 0x008A  # CC10, bipolar (bit 7=1), not inverted
CC11_EXPRESSION = 0x010B  # CC11, unipolar, inverted (bit 8=1)
CC64_SUSTAIN = 0x0140  # CC64, unipolar, inverted (bit 8=1)
CC91_REVERB = 0x00DB  # CC91 = 0xDB = 219
CC93_CHORUS = 0x00DD  # CC93 = 0xDD = 221

# ── SF2 Generator Destinations ────────────────────────────────────────
# From SF2 spec §8.1.2 — generator types
GEN_START_ADDRS_OFFSET = 0
GEN_END_ADDRS_OFFSET = 1
GEN_STARTLOOP_ADDRS_OFFSET = 2
GEN_ENDLOOP_ADDRS_OFFSET = 3
GEN_START_ADDRS_COARSE = 4
GEN_MOD_LFO_TO_PITCH = 5
GEN_VIB_LFO_TO_PITCH = 6
GEN_MOD_ENV_TO_PITCH = 7
GEN_INITIAL_FILTER_FC = 8
GEN_INITIAL_FILTER_Q = 9
GEN_MOD_LFO_TO_FILTER_FC = 10
GEN_MOD_ENV_TO_FILTER_FC = 11
GEN_MOD_LFO_TO_VOLUME = 13
GEN_CHORUS_EFFECTS_SEND = 15
GEN_REVERB_EFFECTS_SEND = 16
GEN_PAN = 17
GEN_DELAY_MOD_LFO = 21
GEN_FREQ_MOD_LFO = 22
GEN_DELAY_VIB_LFO = 23
GEN_FREQ_VIB_LFO = 24
GEN_DELAY_MOD_ENV = 25
GEN_ATTACK_MOD_ENV = 26
GEN_HOLD_MOD_ENV = 27
GEN_DECAY_MOD_ENV = 28
GEN_SUSTAIN_MOD_ENV = 29
GEN_RELEASE_MOD_ENV = 30
GEN_DELAY_VOL_ENV = 33
GEN_ATTACK_VOL_ENV = 34
GEN_HOLD_VOL_ENV = 35
GEN_DECAY_VOL_ENV = 36
GEN_SUSTAIN_VOL_ENV = 37
GEN_RELEASE_VOL_ENV = 38
GEN_INSTRUMENT = 41
GEN_KEY_RANGE = 43
GEN_VELOCITY_RANGE = 44
GEN_INITIAL_ATTENUATION = 48
GEN_COARSE_TUNE = 51
GEN_FINE_TUNE = 52
GEN_SAMPLE_ID = 53
GEN_SAMPLE_MODES = 54
GEN_SCALE_TUNING = 56
GEN_EXCLUSIVE_CLASS = 57
GEN_OVERRIDING_ROOT_KEY = 58

# ── SF2 Transforms ────────────────────────────────────────────────────
TRANSFORM_LINEAR = 0
TRANSFORM_ABSOLUTE = 1
TRANSFORM_BIPOLAR_TO_UNIPOLAR = 2

# ── Default Modulator Table (SF2 §8.4.11) ────────────────────────────
# Ordered from highest priority to lowest — later entries override earlier
# ones within the same destination. File-sourced modulators override defaults.

DEFAULT_MODULATORS: list[dict] = [
    # ── Velocity → Attenuation (SF2 IDs 001-002) ───────────────────────
    # Inverted unipolar velocity: quieter notes get more attenuation.
    # Single linear modulator replaces the spec's two-modulator pattern
    # because the second (concave, amt -960) cancels out after max(0, …) clamping.
    {
        "src_operator": NOTEON_VELOCITY_INV,
        "dest_operator": GEN_INITIAL_ATTENUATION,
        "mod_amount": 960,  # 960 centibels = 96 dB at velocity 0
        "amt_src_operator": NONE,
        "mod_trans_operator": TRANSFORM_LINEAR,
    },
    # ── Velocity → Filter Cutoff (SF2 IDs 003-004) ─────────────────────
    # Higher velocity = higher cutoff (brighter). Uses inverted velocity.
    {
        "src_operator": NOTEON_VELOCITY_INV,
        "dest_operator": GEN_INITIAL_FILTER_FC,
        "mod_amount": -2400,  # base offset
        "amt_src_operator": NONE,
        "mod_trans_operator": TRANSFORM_LINEAR,
    },
    {
        "src_operator": NOTEON_VELOCITY_INV,
        "dest_operator": GEN_INITIAL_FILTER_FC,
        "mod_amount": 2400,   # combined gives 1200·v net (0 at vel=0, 1200 at vel=127)
        "amt_src_operator": NONE,
        "mod_trans_operator": TRANSFORM_BIPOLAR_TO_UNIPOLAR,
    },
    # ── Key Number → Filter Cutoff (medium: ID 4, SF2 ID 004) ─────────
    # Higher note = higher cutoff (tracking)
    {
        "src_operator": KEYNUM,
        "dest_operator": GEN_INITIAL_FILTER_FC,
        "mod_amount": 1200,  # 1200 cents = 1 octave per octave of key
        "amt_src_operator": NONE,
        "mod_trans_operator": TRANSFORM_LINEAR,
    },
    # ── CC1 (Mod Wheel) → Vibrato Depth (medium: ID 5, SF2 ID 005) ────
    {
        "src_operator": CC1_MODWHEEL,
        "dest_operator": GEN_VIB_LFO_TO_PITCH,
        "mod_amount": 50,  # 50 cents at full mod wheel
        "amt_src_operator": NONE,
        "mod_trans_operator": TRANSFORM_LINEAR,
    },
    # ── CC1 (Mod Wheel) → Filter Cutoff (medium: ID 6, SF2 ID 006) ────
    {
        "src_operator": CC1_MODWHEEL,
        "dest_operator": GEN_INITIAL_FILTER_FC,
        "mod_amount": 1200,  # 1200 cents = 1 octave
        "amt_src_operator": NONE,
        "mod_trans_operator": TRANSFORM_LINEAR,
    },
    # ── CC7 (Volume) → Attenuation (SF2 ID 007) ────────────────────────
    # Inverted unipolar: CC7=0 (off) adds 960 cB attenuation, CC7=127 adds none.
    {
        "src_operator": CC7_VOLUME,
        "dest_operator": GEN_INITIAL_ATTENUATION,
        "mod_amount": 960,
        "amt_src_operator": NONE,
        "mod_trans_operator": TRANSFORM_LINEAR,
    },
    # ── CC10 (Pan) → Pan Position (SF2 ID 008) ─────────────────────────
    # Bipolar CC10 source: centre=0, left=-500, right=+500 (SF2 pan units).
    {
        "src_operator": CC10_PAN,
        "dest_operator": GEN_PAN,
        "mod_amount": 500,
        "amt_src_operator": NONE,
        "mod_trans_operator": TRANSFORM_LINEAR,
    },
    # ── CC11 (Expression) → Attenuation (SF2 ID 009) ───────────────────
    # Inverted unipolar: CC11=0 adds 960 cB, CC11=127 adds none.
    {
        "src_operator": CC11_EXPRESSION,
        "dest_operator": GEN_INITIAL_ATTENUATION,
        "mod_amount": 960,
        "amt_src_operator": NONE,
        "mod_trans_operator": TRANSFORM_LINEAR,
    },
    # ── CC64 (Sustain) → Release Time Override (SF2 ID 010) ────────────
    # Inverted unipolar: pedal off (CC64=0) forces minimum release (sharp cutoff).
    # Pedal on (CC64=127) leaves release unchanged.
    {
        "src_operator": CC64_SUSTAIN,
        "dest_operator": GEN_RELEASE_VOL_ENV,
        "mod_amount": -12000,
        "amt_src_operator": NONE,
        "mod_trans_operator": TRANSFORM_ABSOLUTE,
    },
    # ── CC91 (Reverb Send) → Reverb Effects Send (SF2 ID 011) ──────────
    {
        "src_operator": CC91_REVERB,
        "dest_operator": GEN_REVERB_EFFECTS_SEND,
        "mod_amount": 200,  # 0.2% per unit addition
        "amt_src_operator": NONE,
        "mod_trans_operator": TRANSFORM_LINEAR,
    },
    # ── CC93 (Chorus Send) → Chorus Effects Send (SF2 ID 012) ──────────
    {
        "src_operator": CC93_CHORUS,
        "dest_operator": GEN_CHORUS_EFFECTS_SEND,
        "mod_amount": 200,
        "amt_src_operator": NONE,
        "mod_trans_operator": TRANSFORM_LINEAR,
    },
    # ── Pitch Wheel → Pitch (SF2 ID 013) ───────────────────────────────
    # Bipolar pitch wheel source: -1 … +1 → fineTune offset.
    # Default range = 200 cents (2 semitones). Override via Pitch Wheel
    # Sensitivity RPN at the channel level.
    {
        "src_operator": PITCH_WHEEL,
        "dest_operator": GEN_FINE_TUNE,
        "mod_amount": 200,  # 200 cents = 2 semitones default bend range
        "amt_src_operator": NONE,
        "mod_trans_operator": TRANSFORM_LINEAR,
    },
    # ── Key Number → Mod LFO Frequency (medium: ID 15, SF2 ID 015) ─────
    {
        "src_operator": KEYNUM,
        "dest_operator": GEN_FREQ_MOD_LFO,
        "mod_amount": 0,  # No key tracking for mod LFO by default
        "amt_src_operator": NONE,
        "mod_trans_operator": TRANSFORM_LINEAR,
    },
    # ── Key Number → Vib LFO Frequency (medium: ID 16, SF2 ID 016) ────
    {
        "src_operator": KEYNUM,
        "dest_operator": GEN_FREQ_VIB_LFO,
        "mod_amount": 0,  # No key tracking for vib LFO by default
        "amt_src_operator": NONE,
        "mod_trans_operator": TRANSFORM_LINEAR,
    },
    # ── Velocity → Mod LFO Frequency (medium: ID 17, SF2 ID 017) ─────
    {
        "src_operator": NOTEON_VELOCITY,
        "dest_operator": GEN_FREQ_MOD_LFO,
        "mod_amount": 0,
        "amt_src_operator": NONE,
        "mod_trans_operator": TRANSFORM_LINEAR,
    },
]
