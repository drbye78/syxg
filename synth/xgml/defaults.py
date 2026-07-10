"""Default values and templates for XGML documents."""

from __future__ import annotations

from .types import (
    AmpEnvelope,
    BasicMessages,
    ChannelConfig,
    ChannelSetup,
    EffectsConfig,
    FilterParams,
    LFOParams,
    PitchParams,
    ReverbConfig,
    ChorusConfig,
    XGMLConfig,
)


# -- Default per-channel setup --


def default_channel_setup() -> ChannelSetup:
    return ChannelSetup(
        volume=100,
        pan="center",
        expression=127,
        reverb_send=40,
        chorus_send=0,
        variation_send=0,
    )


def default_basic_messages() -> BasicMessages:
    """Create a basic messages section with default setup for all 16 channels."""
    return BasicMessages(
        channels={ch: default_channel_setup() for ch in range(16)},
    )


# -- Default per-channel XG parameters --


def default_filter_params() -> FilterParams:
    return FilterParams(
        cutoff=127,
        resonance=0,
        type="through",
    )


def default_lfo_params() -> dict[str, LFOParams]:
    return {
        "lfo1": LFOParams(waveform="sine", speed=0, delay=0, key_sync=True),
        "lfo2": LFOParams(waveform="sine", speed=0, delay=0, key_sync=True),
    }


def default_channel_config() -> ChannelConfig:
    return ChannelConfig(
        filter=default_filter_params(),
        lfo=default_lfo_params(),
        amp_envelope=AmpEnvelope(attack=0, decay=0, sustain=100, release=64),
        pitch=PitchParams(coarse=0, fine=0),
        mono_poly="poly",
    )


# -- Default effects --


def default_reverb_config() -> ReverbConfig:
    return ReverbConfig(
        type=1,
        time=1.5,
        level=0.3,
        hf_damping=0.5,
        pre_delay=0.0,
        density=0.5,
        balance=0.3,
    )


def default_chorus_config() -> ChorusConfig:
    return ChorusConfig(
        type=1,
        rate=0.5,
        depth=0.5,
        feedback=0.1,
        level=0.2,
        delay=0.01,
    )


def default_effects_config() -> EffectsConfig:
    return EffectsConfig(
        reverb=default_reverb_config(),
        chorus=default_chorus_config(),
    )


# -- Default document --


def default_xgml_config() -> XGMLConfig:
    """Create an XGMLConfig with sensible default values."""
    return XGMLConfig(
        version="3.0",
        description="Default XGML configuration",
        basic_messages=default_basic_messages(),
        channel_parameters=None,
        effects=default_effects_config(),
    )


# -- YAML template (for XGMLConfigSystem.get_xgml_config_template replacement) --


XGML_TEMPLATE = """# XGML Configuration Template
xg_dsl_version: "{version}"
description: "New configuration"
meta:
  author: ""
  tags: []

# --- Preset Configuration (Goal 1) ---
basic_messages:
  channels:
    0:
      program: "acoustic_grand_piano"
      volume: 100
      pan: "center"
      expression: 127

channel_parameters:
  0:
    filter:
      cutoff: 127
      resonance: 0
      type: "through"
    lfo:
      lfo1:
        waveform: "sine"
        speed: 0

drum_parameters:
  channel: 10

effects:
  reverb:
    type: 1
    time: 1.5
    level: 0.3
  chorus:
    type: 1
    rate: 0.5
    depth: 0.5
    level: 0.2

# --- Composition (Goal 2) ---
sequences:
  performance:
    tempo: 120
    time_signature: [4, 4]
    tracks:
      - name: "Track 1"
        channel: 0
""".format(version="3.0")
