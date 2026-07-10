"""
Synth Bridge — XGMLConfig → synthesizer API calls.

Applies XGMLConfig directly to ModernXGSynthesizer (or compatible orchestrator
objects), bypassing MIDI entirely. This is the real implementation behind
XGMLConfigSystem's currently-stubbed _apply_*_config methods.

Usage:
    bridge = XGMLSynthBridge(synthesizer)
    bridge.apply(config)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from synth.protocols.xg.xg_nrpn_definitions import float_to_nrpn_value, note_name_to_midi
from synth.xgml.types import (
    XGMLConfig,
    ChannelSetup,
    ChannelConfig,
    ChorusConfig,
    DrumConfig,
    EffectsConfig,
    EQConfig,
    GSChorusConfig,
    GSConfig,
    GSDrumPartConfig,
    GSEffectsConfig,
    GSPartConfig,
    GSReverbConfig,
    GSSystemConfig,
    FilterParams,
    InsertionSlot,
    JupiterXArpConfig,
    JupiterXConfig,
    JupiterXEngineConfig,
    JupiterXPartConfig,
    JupiterXPartEnvelope,
    JupiterXPartLFO,
    JupiterXPartModulation,
    JupiterXSystemConfig,
    JupiterXVCMConfig,
    ReverbConfig,
    ScaleTuning,
    SystemExclusive,
    VariationConfig,
)

if TYPE_CHECKING:
    from synth.hardware.jupiter_x.component_manager import JupiterXComponentManager
    from synth.hardware.jupiter_x.constants import ENGINE_ANALOG, ENGINE_DIGITAL, ENGINE_FM, ENGINE_EXTERNAL
    from synth.synthesizers.rendering import ModernXGSynthesizer

logger = logging.getLogger(__name__)

MIDI_CHANNELS_PER_PORT = 16


def flat_channel(port: int, channel: int) -> int:
    """Convert (port, channel) pair to a flat synthesizer channel index.

    Port 0, channel 0-15 → 0-15
    Port 1, channel 0-15 → 16-31
    etc.
    """
    return port * MIDI_CHANNELS_PER_PORT + channel


class XGMLSynthBridge:
    """Applies XGMLConfig directly to a ModernXGSynthesizer instance.

    This bridge navigates synthesizer subsystems (effects coordinator,
    voice manager, engine registry) and calls their APIs directly,
    mapping from typed XGML values to the expected API parameter ranges.
    """

    def __init__(self, synthesizer: ModernXGSynthesizer) -> None:
        self.synth = synthesizer
        self.errors: list[str] = []
        self.warnings: list[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply(self, config: XGMLConfig, *, section: str | None = None) -> bool:
        """Apply an XGMLConfig (or a single section) to the synthesizer.

        Args:
            config: The configuration to apply.
            section: If set, apply only this section ('effects', 'channel_parameters',
                     'drum_parameters', 'basic_messages', 'synthesizer_core', 'gs').

        Returns:
            True on success (warnings may still be emitted).
        """
        self.errors.clear()
        self.warnings.clear()

        try:
            if section is None or section == "synthesizer_core":
                if config.synthesizer_core is not None:
                    self._apply_synthesizer_core(config.synthesizer_core)

            if section is None or section == "basic_messages":
                if config.basic_messages is not None:
                    self._apply_basic_messages(config.basic_messages)

            if section is None or section == "channel_parameters":
                if config.channel_parameters is not None:
                    for ch, cfg in config.channel_parameters.items():
                        self._apply_channel_config(ch, cfg)

            if section is None or section == "drum_parameters":
                if config.drum_parameters is not None:
                    self._apply_drum_config(config.drum_parameters)

            if section is None or section == "effects":
                if config.effects is not None:
                    self._apply_effects(config.effects)

            if section is None or section == "sequences":
                if config.sequences is not None:
                    self.warnings.append(
                        "Sequence playback is not supported via synth bridge. "
                        "Use XGMLMIDIBridge for sequences."
                    )

            if section is None or section == "scale_tuning":
                if config.scale_tuning is not None:
                    self._apply_scale_tuning(config.scale_tuning)

            if section is None or section == "system_exclusive":
                if config.system_exclusive is not None:
                    self._apply_system_exclusive(config.system_exclusive)

            if section is None or section == "gs":
                if config.gs is not None:
                    self._apply_gs_config(config.gs)

            if section is None or section == "jupiter_x":
                if config.jupiter_x is not None:
                    self._apply_jupiter_x_config(config.jupiter_x)

        except Exception as e:
            self.errors.append(f"Failed to apply config: {e}")
            logger.exception("XGML synth bridge apply failed")
            return False

        return True

    # ------------------------------------------------------------------
    # Synthesizer Core
    # ------------------------------------------------------------------

    def _apply_synthesizer_core(self, core: Any) -> None:
        synth = self.synth

        # Sample rate
        if hasattr(synth, "sample_rate") and core.sample_rate is not None:
            if synth.sample_rate != core.sample_rate:
                self.warnings.append(
                    f"Sample rate mismatch: synth={synth.sample_rate}, "
                    f"config={core.sample_rate}. Restart required to change."
                )

        # Polyphony
        if hasattr(synth, "max_polyphony") and core.polyphony is not None:
            synth.max_polyphony = core.polyphony
            logger.info("Set max polyphony to %d", core.polyphony)

        # Block size
        if hasattr(synth, "audio_processor") and core.block_size is not None:
            ap = synth.audio_processor
            if hasattr(ap, "block_size"):
                ap.block_size = core.block_size
                logger.info("Set block size to %d", core.block_size)

    # ------------------------------------------------------------------
    # Basic Messages (per-channel setup via engine API)
    # ------------------------------------------------------------------

    def _apply_basic_messages(self, basic: Any) -> None:
        synth = self.synth
        for ch, setup in (basic.channels or {}).items():
            # Compute flat channel index with port awareness
            flat_ch = flat_channel(setup.port, ch)
            # Program change
            if setup.program is not None:
                if hasattr(synth, "set_channel_program"):
                    synth.set_channel_program(flat_ch, self._resolve_program(setup.program))
            # Volume
            if setup.volume is not None:
                if hasattr(synth, "set_channel_volume"):
                    synth.set_channel_volume(flat_ch, setup.volume)
            # Pan
            if setup.pan is not None:
                pan = self._resolve_pan(setup.pan)
                if pan is not None and hasattr(synth, "set_channel_pan"):
                    synth.set_channel_pan(flat_ch, pan)
            # Expression
            if setup.expression is not None:
                if hasattr(synth, "set_channel_expression"):
                    synth.set_channel_expression(flat_ch, setup.expression)
            # Reverb/chorus/variation sends
            if setup.reverb_send is not None and hasattr(synth, "set_reverb_send"):
                synth.set_reverb_send(flat_ch, setup.reverb_send)
            if setup.chorus_send is not None and hasattr(synth, "set_chorus_send"):
                synth.set_chorus_send(flat_ch, setup.chorus_send)
            if setup.variation_send is not None and hasattr(synth, "set_variation_send"):
                synth.set_variation_send(flat_ch, setup.variation_send)
            # Part mode (single/multi)
            if setup.part_mode is not None and hasattr(synth, "set_part_mode"):
                val = 0 if setup.part_mode.lower() == "single" else 1
                synth.set_part_mode(flat_ch, val)
            # Voice reserve
            if setup.voice_reserve is not None and hasattr(synth, "set_voice_reserve"):
                synth.set_voice_reserve(flat_ch, setup.voice_reserve)

    # ------------------------------------------------------------------
    # Channel Configuration
    # ------------------------------------------------------------------

    def _apply_channel_config(self, ch: int, cfg: ChannelConfig) -> None:
        synth = self.synth
        if not hasattr(synth, "set_channel_parameter"):
            self.warnings.append("set_channel_parameter not available on synthesizer")
            return

        # Filter
        if cfg.filter is not None:
            self._apply_filter(ch, cfg.filter)

        # Amp envelope
        if cfg.amp_envelope is not None:
            ae = cfg.amp_envelope
            if ae.attack is not None:
                synth.set_channel_parameter(ch, "amp_attack", ae.attack)
            if ae.decay is not None:
                synth.set_channel_parameter(ch, "amp_decay", ae.decay)
            if ae.sustain is not None:
                synth.set_channel_parameter(ch, "amp_sustain", ae.sustain)
            if ae.release is not None:
                synth.set_channel_parameter(ch, "amp_release", ae.release)

        # LFO
        if cfg.lfo is not None:
            for lfo_name, lfo_params in cfg.lfo.items():
                idx = 1 if lfo_name == "lfo1" else 2
                if lfo_params.speed is not None:
                    synth.set_channel_parameter(ch, f"lfo{idx}_speed", lfo_params.speed)
                if lfo_params.delay is not None:
                    synth.set_channel_parameter(ch, f"lfo{idx}_delay", lfo_params.delay)
                if lfo_params.waveform is not None:
                    synth.set_channel_parameter(ch, f"lfo{idx}_waveform", lfo_params.waveform)

        # Effect sends
        if cfg.effects_sends is not None:
            es = cfg.effects_sends
            if es.reverb is not None:
                synth.set_channel_parameter(ch, "reverb_send", es.reverb)
            if es.chorus is not None:
                synth.set_channel_parameter(ch, "chorus_send", es.chorus)
            if es.variation is not None:
                synth.set_channel_parameter(ch, "variation_send", es.variation)

        # Mono/poly
        if cfg.mono_poly is not None:
            val = 0 if cfg.mono_poly == "poly" else 1
            synth.set_channel_parameter(ch, "mono_poly", val)

        # Element reserve
        if cfg.element_reserve is not None:
            synth.set_channel_parameter(ch, "element_reserve", cfg.element_reserve)

        # Note shift
        if cfg.note_shift is not None:
            synth.set_channel_parameter(ch, "note_shift", cfg.note_shift)

        # Velocity parameters
        if cfg.velocity_response is not None:
            synth.set_channel_parameter(ch, "velocity_response", cfg.velocity_response)
        if cfg.velocity_offset is not None:
            synth.set_channel_parameter(ch, "velocity_offset", cfg.velocity_offset + 64)
        if cfg.velocity_range_low is not None:
            synth.set_channel_parameter(ch, "velocity_range_low", cfg.velocity_range_low)
        if cfg.velocity_range_high is not None:
            synth.set_channel_parameter(ch, "velocity_range_high", cfg.velocity_range_high)

        # Controller assignments
        if cfg.controller_assignments is not None:
            if hasattr(synth, "set_controller_assignment"):
                for ctrl_name, ctrl_num in cfg.controller_assignments.items():
                    synth.set_controller_assignment(ch, ctrl_name, ctrl_num)
            else:
                synth.set_channel_parameter(ch, "controller_assignments", str(cfg.controller_assignments))

        # Legato
        if cfg.legato is not None:
            synth.set_channel_parameter(ch, "legato", 1 if cfg.legato else 0)

    def _apply_filter(self, ch: int, f: FilterParams) -> None:
        synth = self.synth
        if f.cutoff is not None:
            synth.set_channel_parameter(ch, "filter_cutoff", f.cutoff)
        if f.resonance is not None:
            synth.set_channel_parameter(ch, "filter_resonance", f.resonance)
        if f.type is not None:
            t = self._resolve_filter_type(f.type)
            if t is not None:
                synth.set_channel_parameter(ch, "filter_type", t)
        if f.envelope_attack is not None:
            synth.set_channel_parameter(ch, "filter_env_attack", f.envelope_attack)
        if f.envelope_decay is not None:
            synth.set_channel_parameter(ch, "filter_env_decay", f.envelope_decay)
        if f.envelope_sustain is not None:
            synth.set_channel_parameter(ch, "filter_env_sustain", f.envelope_sustain)
        if f.envelope_release is not None:
            synth.set_channel_parameter(ch, "filter_env_release", f.envelope_release)

    # ------------------------------------------------------------------
    # Drum Configuration
    # ------------------------------------------------------------------

    def _apply_drum_config(self, drum: DrumConfig) -> None:
        synth = self.synth
        if hasattr(synth, "set_drum_kit") and drum.kit_number is not None:
            ch = drum.channel if drum.channel is not None else 9
            synth.set_drum_kit(ch, drum.kit_number)

        if drum.notes is not None and hasattr(synth, "set_drum_note_parameter"):
            for note_num, params in drum.notes.items():
                if params.level is not None:
                    synth.set_drum_note_parameter(note_num, "level", params.level)
                if params.pan is not None:
                    synth.set_drum_note_parameter(note_num, "pan", params.pan)
                if params.reverb_send is not None:
                    synth.set_drum_note_parameter(note_num, "reverb_send", params.reverb_send)
                if params.chorus_send is not None:
                    synth.set_drum_note_parameter(note_num, "chorus_send", params.chorus_send)
                if params.filter_cutoff is not None:
                    synth.set_drum_note_parameter(note_num, "filter_cutoff", params.filter_cutoff)
                if params.filter_resonance is not None:
                    synth.set_drum_note_parameter(note_num, "filter_resonance", params.filter_resonance)

    # ------------------------------------------------------------------
    # Effects Configuration (apply to effects coordinator)
    # ------------------------------------------------------------------

    def _apply_effects(self, fx: EffectsConfig) -> None:
        synth = self.synth

        # Find the effects coordinator
        coordinator = getattr(synth, "effects_coordinator", None)
        if coordinator is None:
            # Try voice_manager → processing_chain
            vm = getattr(synth, "voice_manager", None)
            if vm is not None:
                coordinator = getattr(vm, "effects_coordinator", None)
        if coordinator is None:
            self.warnings.append("No effects coordinator found on synthesizer")
            return

        # Reverb
        if fx.reverb is not None:
            self._apply_reverb(coordinator, fx.reverb)

        # Chorus
        if fx.chorus is not None:
            self._apply_chorus(coordinator, fx.chorus)

        # Variation
        if fx.variation is not None:
            self._apply_variation(coordinator, fx.variation)

        # Insertion effects
        if fx.insertion is not None:
            self._apply_insertion(channel=None, coordinator=coordinator, insertion=fx.insertion)

        # Master EQ
        if fx.master_eq is not None:
            self._apply_master_eq(coordinator, fx.master_eq)

    def _apply_reverb(self, coordinator: Any, rv: ReverbConfig) -> None:
        if not hasattr(coordinator, "set_reverb"):
            self.warnings.append("effects_coordinator.set_reverb not available")
            return
        try:
            # Convert typed config to dict for the coordinator API
            params: dict[str, Any] = {}
            if rv.type is not None:
                params["type"] = rv.type
            if rv.time is not None:
                params["time"] = rv.time
            if rv.level is not None:
                params["level"] = rv.level
            if rv.hf_damping is not None:
                params["hf_damping"] = rv.hf_damping
            if rv.pre_delay is not None:
                params["pre_delay"] = rv.pre_delay
            coordinator.set_reverb(params)
        except Exception as e:
            self.warnings.append(f"Failed to set reverb: {e}")

    def _apply_chorus(self, coordinator: Any, ch: ChorusConfig) -> None:
        if not hasattr(coordinator, "set_chorus"):
            self.warnings.append("effects_coordinator.set_chorus not available")
            return
        try:
            params: dict[str, Any] = {}
            if ch.type is not None:
                params["type"] = ch.type
            if ch.rate is not None:
                params["rate"] = ch.rate
            if ch.depth is not None:
                params["depth"] = ch.depth
            if ch.feedback is not None:
                params["feedback"] = ch.feedback
            if ch.level is not None:
                params["level"] = ch.level
            coordinator.set_chorus(params)
        except Exception as e:
            self.warnings.append(f"Failed to set chorus: {e}")

    def _apply_variation(self, coordinator: Any, var: VariationConfig) -> None:
        if not hasattr(coordinator, "set_variation"):
            self.warnings.append("effects_coordinator.set_variation not available")
            return
        try:
            params: dict[str, Any] = {}
            if var.type is not None:
                params["type"] = var.type
            if var.level is not None:
                params["level"] = var.level
            if var.params:
                params.update(var.params)
            coordinator.set_variation(params)
        except Exception as e:
            self.warnings.append(f"Failed to set variation: {e}")

    def _apply_insertion(
        self, channel: int | None, coordinator: Any, insertion: dict[int, InsertionSlot]
    ) -> None:
        """Apply insertion effect configuration per channel."""
        # Check for motif-style set_part_insertion_effect
        if hasattr(coordinator, "set_part_insertion_effect"):
            for ch, slot in insertion.items():
                try:
                    params: dict[str, Any] = {"bypass": slot.bypass}
                    if slot.params:
                        params.update(slot.params)
                    t = slot.type if isinstance(slot.type, int) else 0
                    coordinator.set_part_insertion_effect(ch, t, params)
                except Exception as e:
                    self.warnings.append(f"Failed to set insertion effect on ch {ch}: {e}")
        else:
            # Fallback: try per-channel insertion connection
            synth = self.synth
            if hasattr(synth, "set_channel_parameter"):
                for ch, slot in insertion.items():
                    try:
                        synth.set_channel_parameter(ch, "insertion_bypass", 1 if slot.bypass else 0)
                        if slot.type is not None:
                            t = slot.type if isinstance(slot.type, int) else 0
                            synth.set_channel_parameter(ch, "insertion_effect_type", t)
                    except Exception as e:
                        self.warnings.append(f"Failed to set insertion param on ch {ch}: {e}")

    def _apply_master_eq(self, coordinator: Any, eq: EQConfig) -> None:
        """Apply master EQ configuration."""
        if hasattr(coordinator, "set_master_eq"):
            try:
                params: dict[str, Any] = {}
                if eq.low_gain is not None:
                    params["low_gain"] = eq.low_gain
                if eq.low_mid_gain is not None:
                    params["low_mid_gain"] = eq.low_mid_gain
                if eq.mid_gain is not None:
                    params["mid_gain"] = eq.mid_gain
                if eq.mid_freq is not None:
                    params["mid_freq"] = eq.mid_freq
                if eq.high_mid_gain is not None:
                    params["high_mid_gain"] = eq.high_mid_gain
                if eq.high_gain is not None:
                    params["high_gain"] = eq.high_gain
                if eq.q_factor is not None:
                    params["q_factor"] = eq.q_factor
                coordinator.set_master_eq(params)
            except Exception as e:
                self.warnings.append(f"Failed to set master EQ: {e}")
        else:
            self.warnings.append("effects_coordinator.set_master_eq not available")

    # ------------------------------------------------------------------
    # Roland GS Configuration
    # ------------------------------------------------------------------

    def _apply_gs_config(self, gs: GSConfig) -> None:
        """Apply Roland GS configuration to the synthesizer."""
        if gs.system is not None:
            self._apply_gs_system(gs.system)

        if gs.parts is not None:
            for part_num, part_cfg in gs.parts.items():
                self._apply_gs_part(part_num, part_cfg)

        if gs.effects is not None:
            self._apply_gs_effects(gs.effects)

        if gs.drum_parts is not None:
            for part_num, drum_cfg in gs.drum_parts.items():
                self._apply_gs_drum_part(part_num, drum_cfg)

    def _apply_gs_system(self, sys: GSSystemConfig) -> None:
        """Apply GS system parameters."""
        synth = self.synth
        if sys.master_tune is not None and hasattr(synth, "set_master_tune"):
            synth.set_master_tune(sys.master_tune)
        if sys.master_volume is not None and hasattr(synth, "set_master_volume"):
            synth.set_master_volume(sys.master_volume)
        if sys.master_transpose is not None and hasattr(synth, "set_master_transpose"):
            synth.set_master_transpose(sys.master_transpose)

    def _apply_gs_part(self, part_num: int, part: GSPartConfig) -> None:
        """Apply GS part parameters via synthesizer API or GSSysexHandler."""
        synth = self.synth

        # Try JV2080ComponentManager first, then fallback
        gs_components = getattr(synth, "gs_components", None)
        if gs_components is not None and hasattr(gs_components, "set_part_parameter"):
            # Rich JV-2080 API
            params: dict[str, Any] = {}
            if part.program is not None:
                params["instrument_number"] = part.program
            if part.volume is not None:
                params["volume"] = part.volume
            if part.pan is not None:
                params["pan"] = part.pan
            if part.coarse_tune is not None:
                params["coarse_tune"] = part.coarse_tune
            if part.fine_tune is not None:
                params["fine_tune"] = part.fine_tune
            if part.reverb_send is not None:
                params["reverb_send"] = part.reverb_send
            if part.chorus_send is not None:
                params["chorus_send"] = part.chorus_send
            if part.key_range_low is not None:
                params["key_range_low"] = part.key_range_low
            if part.key_range_high is not None:
                params["key_range_high"] = part.key_range_high
            if part.velocity_range_low is not None:
                params["velocity_range_low"] = part.velocity_range_low
            if part.velocity_range_high is not None:
                params["velocity_range_high"] = part.velocity_range_high
            try:
                gs_components.set_part_parameter(part_num, params)
            except Exception as e:
                self.warnings.append(f"Failed to set GS part {part_num}: {e}")
            return

        # Fallback: use existing channel API
        if hasattr(synth, "set_channel_program") and part.program is not None:
            synth.set_channel_program(part_num, part.program)
        if hasattr(synth, "set_channel_volume") and part.volume is not None:
            synth.set_channel_volume(part_num, part.volume)
        if hasattr(synth, "set_channel_pan") and part.pan is not None:
            synth.set_channel_pan(part_num, part.pan)
        if hasattr(synth, "set_channel_parameter"):
            for param_name, val in [
                ("filter_cutoff", part.filter_cutoff),
                ("filter_resonance", part.filter_resonance),
                ("amp_attack", part.attack_time),
                ("amp_decay", part.decay_time),
                ("amp_release", part.release_time),
                ("reverb_send", part.reverb_send),
                ("chorus_send", part.chorus_send),
            ]:
                if val is not None:
                    synth.set_channel_parameter(part_num, param_name, val)
            if part.portamento is not None:
                synth.set_channel_parameter(part_num, "portamento", 1 if part.portamento else 0)

    def _apply_gs_effects(self, fx: GSEffectsConfig) -> None:
        """Apply GS effects via coordinator."""
        coordinator = getattr(self.synth, "effects_coordinator", None)
        if coordinator is None:
            vm = getattr(self.synth, "voice_manager", None)
            if vm is not None:
                coordinator = getattr(vm, "effects_coordinator", None)
        if coordinator is None:
            self.warnings.append("No effects coordinator found for GS effects")
            return

        if fx.reverb is not None and hasattr(coordinator, "set_reverb"):
            rv = fx.reverb
            try:
                params: dict[str, Any] = {}
                if rv.type is not None:
                    params["type"] = rv.type
                if rv.level is not None:
                    params["level"] = rv.level / 127.0
                if rv.time is not None:
                    params["time"] = rv.time / 127.0
                if rv.feedback is not None:
                    params["feedback"] = rv.feedback / 127.0
                coordinator.set_reverb(params)
            except Exception as e:
                self.warnings.append(f"Failed to set GS reverb: {e}")

        if fx.chorus is not None and hasattr(coordinator, "set_chorus"):
            ch = fx.chorus
            try:
                params: dict[str, Any] = {}
                if ch.type is not None:
                    params["type"] = ch.type
                if ch.level is not None:
                    params["level"] = ch.level / 127.0
                if ch.rate is not None:
                    params["rate"] = ch.rate / 127.0
                if ch.depth is not None:
                    params["depth"] = ch.depth / 127.0
                coordinator.set_chorus(params)
            except Exception as e:
                self.warnings.append(f"Failed to set GS chorus: {e}")

    def _apply_gs_drum_part(self, part_num: int, drum: GSDrumPartConfig) -> None:
        """Apply GS drum part configuration."""
        synth = self.synth
        if not hasattr(synth, "set_drum_kit"):
            self.warnings.append("set_drum_kit not available for GS drums")
            return
        try:
            params: dict[str, Any] = {}
            if drum.map_low_note is not None:
                params["map_low_note"] = drum.map_low_note
            if drum.map_high_note is not None:
                params["map_high_note"] = drum.map_high_note
            if drum.pitch_offset is not None:
                params["pitch_offset"] = drum.pitch_offset
            if drum.level_offset is not None:
                params["level_offset"] = drum.level_offset
            if drum.pan_random is not None:
                params["pan_random"] = drum.pan_random
            if drum.key_group is not None:
                params["key_group"] = drum.key_group
            synth.set_drum_kit(part_num, params)
        except Exception as e:
            self.warnings.append(f"Failed to set GS drum part {part_num}: {e}")

    # ------------------------------------------------------------------
    # Roland Jupiter-X Configuration
    # ------------------------------------------------------------------

    # Engine name → engine type constant mapping
    _ENGINE_NAME_MAP: ClassVar[dict[str, int]] = {
        "analog": 0,
        "digital": 1,
        "fm": 2,
        "external": 3,
    }

    # Engine base parameter → param_id mapping (for set_engine_parameter)
    _ENGINE_BASE_PARAMS: ClassVar[dict[str, int]] = {
        "enable": 0x00,
        "level": 0x01,
        "pan": 0x02,
        "coarse_tune": 0x03,
        "fine_tune": 0x04,
    }

    def _get_jupiter_x_manager(self) -> JupiterXComponentManager | None:
        """Get Jupiter-X component manager from the synthesizer.

        Tries multiple discovery paths:
          1. self.synth.jupiter_x_engine → jupiter_x_synth → component_manager
          2. self.synth.hardware (dict) → "jupiter_x" → component_manager
        """
        # Path 1: jupiter_x_engine (the standard ModernXGSynthesizer path)
        engine = getattr(self.synth, "jupiter_x_engine", None)
        if engine is not None:
            jx_synth = getattr(engine, "jupiter_x_synth", None)
            if jx_synth is not None:
                cm = getattr(jx_synth, "component_manager", None)
                if cm is not None:
                    return cm

        # Path 2: synthetic hardware dictionary
        hw = getattr(self.synth, "hardware", None)
        if hw is not None:
            jx = hw.get("jupiter_x") if isinstance(hw, dict) else None
            if jx is not None:
                cm = getattr(jx, "component_manager", None)
                if cm is not None:
                    return cm

        return None

    def _get_jupiter_x_synth(self) -> Any | None:
        """Get the raw JupiterXSynthesizer instance, if available."""
        engine = getattr(self.synth, "jupiter_x_engine", None)
        if engine is not None:
            return getattr(engine, "jupiter_x_synth", None)
        return None

    def _apply_jupiter_x_config(self, jx: JupiterXConfig) -> None:
        """Apply a complete Jupiter-X configuration to the synthesizer.

        Silently skips Jupiter-X subsystems when the hardware
        component manager is not available.
        """
        if jx.system is not None:
            self._apply_jupiter_x_system(jx.system)

        if jx.parts is not None:
            for part_num, part_cfg in jx.parts.items():
                self._apply_jupiter_x_part(part_num, part_cfg)

        if jx.effects is not None:
            self._apply_jupiter_x_vcm(jx.effects)

        if jx.arpeggiator is not None:
            self._apply_jupiter_x_arp(jx.arpeggiator)

    def _apply_jupiter_x_system(self, sys: JupiterXSystemConfig) -> None:
        """Apply Jupiter-X global system parameters."""
        manager = self._get_jupiter_x_manager()
        if manager is None:
            self.warnings.append("Jupiter-X not available; skipping system config")
            return

        sp = manager.system_params
        try:
            if sys.master_volume is not None:
                sp.master_volume = max(0, min(127, sys.master_volume))
            if sys.master_tune is not None:
                sp.master_tune = max(-64, min(63, sys.master_tune))
            if sys.master_transpose is not None:
                sp.master_transpose = max(-12, min(12, sys.master_transpose))
            if sys.master_pan is not None:
                sp.master_pan = max(-64, min(63, sys.master_pan))
        except Exception as e:
            self.warnings.append(f"Failed to set Jupiter-X system params: {e}")

    def _apply_jupiter_x_part(self, part_num: int, part: JupiterXPartConfig) -> None:
        """Apply a Jupiter-X part configuration (part-level + engines + LFO + envelope + mod)."""
        manager = self._get_jupiter_x_manager()
        if manager is None:
            self.warnings.append(f"Jupiter-X not available; skipping part {part_num}")
            return

        try:
            p = manager.parts[part_num]

            # --- Part-level parameters (via set_parameter param_id) ---
            # param_id 0x02 = Volume (0-127)
            vol = part.level if part.level is not None else part.volume
            if vol is not None:
                p.set_parameter(0x02, max(0, min(127, vol)))

            # param_id 0x03 = Pan (expects 0-127, 64=center)
            if part.pan is not None:
                p.set_parameter(0x03, max(0, min(127, part.pan + 64)))

            # param_id 0x04 = Coarse Tune (expects 0-127, 64=center → -24..24)
            if part.coarse_tune is not None:
                p.set_parameter(0x04, max(0, min(127, part.coarse_tune + 64)))

            # param_id 0x05 = Fine Tune (expects 0-127, 64=center → -50..50)
            if part.fine_tune is not None:
                p.set_parameter(0x05, max(0, min(127, part.fine_tune + 64)))

            # param_id 0x06 = Reverb Send (0-127)
            if part.reverb_send is not None:
                p.set_parameter(0x06, max(0, min(127, part.reverb_send)))

            # param_id 0x07 = Chorus Send (0-127)
            if part.chorus_send is not None:
                p.set_parameter(0x07, max(0, min(127, part.chorus_send)))

            # param_id 0x08 = Delay Send (0-127)
            if part.delay_send is not None:
                p.set_parameter(0x08, max(0, min(127, part.delay_send)))

            # param_id 0x0B = Key Range Low (0-127)
            if part.key_range_low is not None:
                p.set_parameter(0x0B, max(0, min(127, part.key_range_low)))

            # param_id 0x0C = Key Range High (0-127)
            if part.key_range_high is not None:
                p.set_parameter(0x0C, max(0, min(127, part.key_range_high)))

            # --- Engine selection (via engine mix levels) ---
            if part.active_engine is not None:
                engine_type = max(0, min(3, part.active_engine))
                for e_type in range(4):
                    level = 1.0 if e_type == engine_type else 0.0
                    manager.set_engine_level(part_num, e_type, level)

            # --- Per-engine configuration ---
            if part.engines is not None:
                for engine_name, engine_cfg in part.engines.items():
                    self._apply_jupiter_x_engine(part_num, engine_name, engine_cfg)

            # --- LFO ---
            if part.lfo is not None:
                self._apply_jupiter_x_lfo(part_num, part.lfo)

            # --- Envelope ---
            if part.envelope is not None:
                self._apply_jupiter_x_envelope(part_num, part.envelope)

            # --- Modulation routing ---
            if part.modulation is not None:
                self._apply_jupiter_x_modulation(part_num, part.modulation)

        except Exception as e:
            self.warnings.append(f"Failed to set Jupiter-X part {part_num}: {e}")

    def _apply_jupiter_x_engine(
        self, part_num: int, engine_name: str, engine: JupiterXEngineConfig
    ) -> None:
        """Apply engine-level parameters for a specific Jupiter-X engine.

        engine_name is one of: 'analog', 'digital', 'fm', 'external'.
        """
        manager = self._get_jupiter_x_manager()
        if manager is None:
            return

        engine_type = self._ENGINE_NAME_MAP.get(engine_name.lower().strip())
        if engine_type is None:
            self.warnings.append(
                f"Unknown Jupiter-X engine '{engine_name}' for part {part_num}"
            )
            return

        try:
            # Base parameters (common across all engines)
            if engine.enable is not None:
                manager.set_engine_parameter(part_num, engine_type, 0x00, 1 if engine.enable else 0)
            if engine.level is not None:
                manager.set_engine_parameter(part_num, engine_type, 0x01, max(0, min(127, engine.level)))
            if engine.pan is not None:
                manager.set_engine_parameter(part_num, engine_type, 0x02, max(0, min(127, engine.pan + 64)))
            if engine.coarse_tune is not None:
                manager.set_engine_parameter(part_num, engine_type, 0x03, max(0, min(127, engine.coarse_tune + 64)))
            if engine.fine_tune is not None:
                manager.set_engine_parameter(part_num, engine_type, 0x04, max(0, min(127, engine.fine_tune + 64)))

            # Engine-specific parameters (via set_parameter_by_name on the part)
            if engine.parameters:
                part = manager.parts[part_num]
                for param_name, value in engine.parameters.items():
                    try:
                        part.set_parameter_by_name(param_name, value)
                    except Exception:
                        self.warnings.append(
                            f"Failed to set engine param '{param_name}'={value} "
                            f"on part {part_num} {engine_name}"
                        )

        except Exception as e:
            self.warnings.append(
                f"Failed to apply {engine_name} engine config on part {part_num}: {e}"
            )

    def _apply_jupiter_x_lfo(self, part_num: int, lfo: JupiterXPartLFO) -> None:
        """Apply LFO parameters for a Jupiter-X part.

        Routes to the analog engine's LFO1 via set_parameter_by_name
        (the most common Jupiter-X LFO target).
        """
        manager = self._get_jupiter_x_manager()
        if manager is None:
            return

        try:
            part = manager.parts[part_num]

            # Map to LFO1
            if lfo.waveform is not None:
                part.set_parameter_by_name("lfo1_waveform", max(0, min(5, lfo.waveform)))
            if lfo.rate is not None:
                part.set_parameter_by_name("lfo1_rate", max(0, min(127, lfo.rate)))
            if lfo.depth is not None:
                part.set_parameter_by_name("lfo1_depth", max(0, min(127, lfo.depth)))

            # key_trigger -> lfo1_sync
            if lfo.key_trigger is not None:
                part.set_parameter_by_name("lfo1_sync", 1 if lfo.key_trigger else 0)

            # delay and fade are not exposed via set_parameter_by_name yet
            if lfo.delay is not None:
                logger.debug(
                    "Jupiter-X LFO delay not directly settable on part %d (value=%d)",
                    part_num,
                    lfo.delay,
                )
            if lfo.fade is not None:
                logger.debug(
                    "Jupiter-X LFO fade not directly settable on part %d (value=%d)",
                    part_num,
                    lfo.fade,
                )

        except Exception as e:
            self.warnings.append(f"Failed to set Jupiter-X LFO on part {part_num}: {e}")

    def _apply_jupiter_x_envelope(self, part_num: int, env: JupiterXPartEnvelope) -> None:
        """Apply envelope parameters for a Jupiter-X part.

        Routes to the analog engine's amp envelope via set_parameter_by_name.
        """
        manager = self._get_jupiter_x_manager()
        if manager is None:
            return

        try:
            part = manager.parts[part_num]

            if env.attack is not None:
                part.set_parameter_by_name("amp_attack", max(0, min(127, env.attack)))
            if env.decay is not None:
                part.set_parameter_by_name("amp_decay", max(0, min(127, env.decay)))
            if env.sustain is not None:
                part.set_parameter_by_name("amp_sustain", max(0, min(127, env.sustain)))
            if env.release is not None:
                part.set_parameter_by_name("amp_release", max(0, min(127, env.release)))
            if env.velocity_sensitivity is not None:
                part.set_parameter_by_name(
                    "amp_velocity_sensitivity", max(0, min(127, env.velocity_sensitivity))
                )

            # Curve types not currently exposed via set_parameter_by_name
            if env.attack_curve is not None:
                logger.debug(
                    "Jupiter-X envelope attack_curve not settable on part %d (value=%d)",
                    part_num,
                    env.attack_curve,
                )
            if env.decay_curve is not None:
                logger.debug(
                    "Jupiter-X envelope decay_curve not settable on part %d (value=%d)",
                    part_num,
                    env.decay_curve,
                )
            if env.release_curve is not None:
                logger.debug(
                    "Jupiter-X envelope release_curve not settable on part %d (value=%d)",
                    part_num,
                    env.release_curve,
                )

        except Exception as e:
            self.warnings.append(f"Failed to set Jupiter-X envelope on part {part_num}: {e}")

    def _apply_jupiter_x_modulation(self, part_num: int, mod: JupiterXPartModulation) -> None:
        """Apply modulation routing parameters for a Jupiter-X part.

        These are higher-level modulation parameters that may require
        the parameter system if direct part access is unavailable.
        """
        manager = self._get_jupiter_x_manager()
        if manager is None:
            return

        try:
            # Try applying via the parameter system if available
            jx_synth = self._get_jupiter_x_synth()
            if jx_synth is not None and hasattr(jx_synth, "parameter_system"):
                ps = jx_synth.parameter_system
                if mod.mod_wheel_depth is not None:
                    ps.set_parameter(f"part_{part_num}_mod_wheel", mod.mod_wheel_depth)
                if mod.aftertouch_depth is not None:
                    ps.set_parameter(f"part_{part_num}_aftertouch", mod.aftertouch_depth)
                if mod.velocity_depth is not None:
                    ps.set_parameter(f"part_{part_num}_velocity_depth", mod.velocity_depth)
                if mod.key_tracking_depth is not None:
                    ps.set_parameter(f"part_{part_num}_key_track", mod.key_tracking_depth)
                if mod.super_knob_depth is not None:
                    ps.set_parameter(f"part_{part_num}_super_knob", mod.super_knob_depth)
            else:
                # Fallback: log and skip — modulation routing not available
                if any(
                    x is not None
                    for x in [mod.mod_wheel_depth, mod.aftertouch_depth, mod.velocity_depth,
                              mod.key_tracking_depth, mod.super_knob_depth]
                ):
                    logger.debug(
                        "Jupiter-X modulation routing not available for part %d "
                        "(no parameter system)",
                        part_num,
                    )

        except Exception as e:
            self.warnings.append(f"Failed to set Jupiter-X modulation on part {part_num}: {e}")

    def _apply_jupiter_x_vcm(self, vcm: JupiterXVCMConfig) -> None:
        """Apply Jupiter-X VCM effects chain configuration.

        Maps to JupiterXEffectsParameters.set_parameter(addr_high, addr_mid, addr_low, value).
        """
        manager = self._get_jupiter_x_manager()
        if manager is None:
            self.warnings.append("Jupiter-X not available; skipping VCM effects")
            return

        ep = manager.effects_params
        try:
            # Distortion  (0x40, 0x03, XX)
            if vcm.distortion_type is not None:
                t = vcm.distortion_type if isinstance(vcm.distortion_type, int) else 1
                ep.set_parameter(0x40, 0x03, 0x00, max(0, min(7, t)))
            if vcm.distortion_drive is not None:
                ep.set_parameter(0x40, 0x03, 0x02, max(0, min(127, vcm.distortion_drive)))
            if vcm.distortion_level is not None:
                ep.set_parameter(0x40, 0x03, 0x01, max(0, min(127, vcm.distortion_level)))

            # Phaser — not directly supported by effects_params; log if set
            if any(
                x is not None
                for x in [vcm.phaser_polarity, vcm.phaser_rate, vcm.phaser_depth, vcm.phaser_level]
            ):
                logger.debug(
                    "Jupiter-X phaser params not directly supported by effects_params; skipped"
                )

            # Chorus  (0x40, 0x01, XX)
            if vcm.chorus_type is not None:
                t = vcm.chorus_type if isinstance(vcm.chorus_type, int) else 1
                ep.set_parameter(0x40, 0x01, 0x00, max(0, min(7, t)))
            if vcm.chorus_rate is not None:
                ep.set_parameter(0x40, 0x01, 0x02, max(0, min(127, vcm.chorus_rate)))
            if vcm.chorus_depth is not None:
                # Depth not directly exposed on effects_params; log
                logger.debug(
                    "Jupiter-X chorus depth not directly supported by effects_params (value=%d)",
                    vcm.chorus_depth,
                )
            if vcm.chorus_level is not None:
                ep.set_parameter(0x40, 0x01, 0x01, max(0, min(127, vcm.chorus_level)))

            # Delay  (0x40, 0x02, XX)
            if vcm.delay_type is not None:
                t = vcm.delay_type if isinstance(vcm.delay_type, int) else 1
                ep.set_parameter(0x40, 0x02, 0x00, max(0, min(7, t)))
            if vcm.delay_time is not None:
                ep.set_parameter(0x40, 0x02, 0x02, max(0, min(127, vcm.delay_time)))
            if vcm.delay_feedback is not None:
                # Feedback not directly on effects_params; log
                logger.debug(
                    "Jupiter-X delay feedback not directly supported (value=%d)",
                    vcm.delay_feedback,
                )
            if vcm.delay_level is not None:
                ep.set_parameter(0x40, 0x02, 0x01, max(0, min(127, vcm.delay_level)))

            # Reverb  (0x40, 0x00, XX)
            if vcm.reverb_type is not None:
                t = vcm.reverb_type if isinstance(vcm.reverb_type, int) else 1
                ep.set_parameter(0x40, 0x00, 0x00, max(0, min(7, t)))
            if vcm.reverb_time is not None:
                ep.set_parameter(0x40, 0x00, 0x02, max(0, min(127, vcm.reverb_time)))
            if vcm.reverb_level is not None:
                ep.set_parameter(0x40, 0x00, 0x01, max(0, min(127, vcm.reverb_level)))
            if vcm.reverb_density is not None:
                # Density not on effects_params; log
                logger.debug(
                    "Jupiter-X reverb density not directly supported (value=%d)",
                    vcm.reverb_density,
                )

        except Exception as e:
            self.warnings.append(f"Failed to set Jupiter-X VCM effects: {e}")

    def _apply_jupiter_x_arp(self, arp: JupiterXArpConfig) -> None:
        """Apply Jupiter-X arpeggiator configuration.

        Applies to part 0 by default (global arp config). For multi-part
        arp, call this method per part via the parts loop.
        """
        jx_synth = self._get_jupiter_x_synth()
        if jx_synth is None:
            self.warnings.append("Jupiter-X not available; skipping arpeggiator config")
            return

        try:
            arp_engine = getattr(jx_synth, "arpeggiator", None)
            if arp_engine is None:
                self.warnings.append("Jupiter-X arpeggiator engine not available")
                return

            # Apply to part 0 as default (global config)
            part_num = 0

            if arp.enable is not None:
                jx_synth.enable_arpeggiator(part_num, arp.enable)

            if arp.style is not None:
                jx_synth.set_arpeggiator_pattern(part_num, max(0, min(127, arp.style)))

            if arp.tempo is not None:
                jx_synth.set_arpeggiator_tempo(part_num, float(max(20, min(300, arp.tempo))))

            if arp.gate_time is not None:
                # Convert 0-127 to 0.0-1.0 for the arpeggiator API
                gate = max(0, min(127, arp.gate_time)) / 127.0
                jx_synth.set_arpeggiator_gate_time(part_num, gate)

            if arp.swing is not None:
                # Convert -50..50 to 0.0-1.0 (0.5 = no swing)
                swing = (max(-50, min(50, arp.swing)) + 50) / 100.0
                jx_synth.set_arpeggiator_swing(part_num, swing)

            # rate, latch, target, type, range, pattern_length are logged if present
            if arp.type is not None:
                logger.debug("Jupiter-X arp type=%d: not directly settable", arp.type)
            if arp.range is not None:
                logger.debug("Jupiter-X arp range=%d: not directly settable", arp.range)
            if arp.rate is not None:
                logger.debug("Jupiter-X arp rate=%d: not directly settable", arp.rate)
            if arp.latch is not None:
                logger.debug("Jupiter-X arp latch=%s: not directly settable", arp.latch)
            if arp.target is not None:
                logger.debug("Jupiter-X arp target=%d: not directly settable", arp.target)
            if arp.pattern_length is not None:
                logger.debug(
                    "Jupiter-X arp pattern_length=%d: not directly settable",
                    arp.pattern_length,
                )

        except Exception as e:
            self.warnings.append(f"Failed to set Jupiter-X arpeggiator: {e}")

    # ------------------------------------------------------------------
    # Scale Tuning
    # ------------------------------------------------------------------

    def _apply_scale_tuning(self, st: ScaleTuning) -> None:
        """Apply scale/micro-tuning to the synthesizer."""
        synth = self.synth
        if not hasattr(synth, "set_scale_tuning"):
            self.warnings.append("set_scale_tuning not available on synthesizer")
            return
        try:
            params: dict[str, int] = {}
            if st.c is not None:
                params["c"] = st.c
            if st.c_sharp is not None:
                params["c_sharp"] = st.c_sharp
            if st.d is not None:
                params["d"] = st.d
            if st.d_sharp is not None:
                params["d_sharp"] = st.d_sharp
            if st.e is not None:
                params["e"] = st.e
            if st.f is not None:
                params["f"] = st.f
            if st.f_sharp is not None:
                params["f_sharp"] = st.f_sharp
            if st.g is not None:
                params["g"] = st.g
            if st.g_sharp is not None:
                params["g_sharp"] = st.g_sharp
            if st.a is not None:
                params["a"] = st.a
            if st.a_sharp is not None:
                params["a_sharp"] = st.a_sharp
            if st.b is not None:
                params["b"] = st.b
            if st.master_tune is not None:
                params["master_tune"] = st.master_tune
            if st.transpose is not None:
                params["transpose"] = st.transpose
            if st.temperament is not None:
                t_val = st.temperament if isinstance(st.temperament, int) else 0
                params["temperament"] = t_val
            if st.octave_tune is not None:
                params["octave_tune"] = st.octave_tune
            synth.set_scale_tuning(params)
        except Exception as e:
            self.warnings.append(f"Failed to set scale tuning: {e}")

    # ------------------------------------------------------------------
    # System Exclusive
    # ------------------------------------------------------------------

    def _apply_system_exclusive(self, sysex: list[SystemExclusive]) -> None:
        """Apply system exclusive messages to the synthesizer."""
        synth = self.synth
        if not hasattr(synth, "send_sysex"):
            self.warnings.append("send_sysex not available on synthesizer")
            return
        for msg in sysex:
            try:
                data = [msg.manufacturer, msg.device] + msg.data
                synth.send_sysex(data)
            except Exception as e:
                self.warnings.append(f"Failed to send sysex: {e}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_program(self, program: str | int) -> int:
        if isinstance(program, int):
            return max(0, min(127, program))
        names = {
            "acoustic_grand_piano": 0, "bright_acoustic_piano": 1, "electric_grand_piano": 2,
            "honky_tonk_piano": 3, "electric_piano_1": 4, "electric_piano_2": 5,
            "harpsichord": 6, "clavinet": 7, "celesta": 8, "glockenspiel": 9,
            "music_box": 10, "vibraphone": 11, "marimba": 12, "xylophone": 13,
            "tubular_bells": 14, "dulcimer": 15, "drawbar_organ": 16, "percussive_organ": 17,
            "rock_organ": 18, "church_organ": 19, "reed_organ": 20, "accordion": 21,
            "harmonica": 22, "tango_accordion": 23,
        }
        return names.get(program.lower().strip(), 0)

    def _resolve_pan(self, pan: str | int) -> int | None:
        if isinstance(pan, int):
            return max(0, min(127, pan))
        p = pan.lower().strip()
        return {"center": 64, "left": 0, "right": 127, "left_center": 32, "right_center": 96}.get(p)

    def _resolve_filter_type(self, ft: str | int) -> int | None:
        if isinstance(ft, int):
            return max(0, min(3, ft))
        return {"through": 0, "lowpass": 1, "highpass": 2, "bandpass": 3}.get(ft.lower())

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        return len(self.warnings) > 0
