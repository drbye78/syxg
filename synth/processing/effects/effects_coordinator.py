"""XGEffectsCoordinator — central orchestrator for the XG effects pipeline.

Routes Insertion → Variation → System effects with zero-alloc processing.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Any

import numpy as np

from ...primitives.buffer_pool import XGBufferManager
from .eq_processor import XGMultiBandEqualizer
from .effect_slot import EffectSlot, EffectStageType
from .insertion import ProductionXGInsertionEffectsProcessor
from .output_bus_manager import OutputBusManager
from .pipeline_topology import PipelineTopology
from .system import XGSystemEffectsProcessor
from .system_delay import SystemDelayEffect
from .variation_effects import XGVariationEffectsProcessor

logger = logging.getLogger(__name__)


class XGEffectsCoordinator:
    """Orchestrates XG effects processing with channel routing and effect chaining.

    Processing Chain: insertion → mixing → variation → system → master.
    """

    def __init__(
        self,
        sample_rate: int,
        block_size: int = 1024,
        max_channels: int = 16,
        synthesizer=None,
        buffer_pool=None,
    ):
        self.synthesizer = synthesizer
        self.sample_rate = sample_rate
        self.block_size = block_size
        self.max_channels = max_channels

        if buffer_pool is not None:
            self.buffer_pool = buffer_pool
        else:
            from ...primitives.buffer_pool import XGBufferPool

            self.buffer_pool = XGBufferPool(sample_rate, block_size * 4)
        self.buffer_manager: XGBufferManager | None = None
        self.memory_pool = self.buffer_pool

        max_reverb_delay = int(5.0 * sample_rate)
        max_chorus_delay = int(0.05 * sample_rate)
        max_effect_delay = int(2.0 * sample_rate)

        self.system_effects = XGSystemEffectsProcessor(
            sample_rate, block_size, max_reverb_delay, max_chorus_delay
        )

        self.variation_effects = XGVariationEffectsProcessor(sample_rate, max_effect_delay)

        self.system_delay = SystemDelayEffect(sample_rate)

        self._delay_out_l = np.zeros(block_size, dtype=np.float32)
        self._delay_out_r = np.zeros(block_size, dtype=np.float32)

        self.insertion_effects: list[ProductionXGInsertionEffectsProcessor] = []
        for _ in range(max_channels):
            self.insertion_effects.append(
                ProductionXGInsertionEffectsProcessor(sample_rate, max_effect_delay)
            )

        self.processing_enabled = True
        self.wet_dry_mix = 1.0
        self.master_level = 1.0

        self.effect_routing_mode = "XG_STANDARD"

        self.channel_volumes: np.ndarray = np.ones(max_channels, dtype=np.float32)
        self.channel_pans: np.ndarray = np.zeros(max_channels, dtype=np.float32)

        self.reverb_sends: np.ndarray = np.full(max_channels, 0.25, dtype=np.float32)
        self.chorus_sends: np.ndarray = np.full(max_channels, 0.0, dtype=np.float32)
        self.variation_sends: np.ndarray = np.full(max_channels, 0.0, dtype=np.float32)

        self.delay_sends: np.ndarray = np.full(max_channels, 0.0, dtype=np.float32)

        self.effect_units_active: np.ndarray = np.ones(10, dtype=bool)

        self.dry_signal_buffer: np.ndarray | None = None

        # Pre-allocated work buffers for hot-path processing (zero-allocation)
        self._filter_work_buffer: np.ndarray | None = None
        self._delay_tap_buffer: np.ndarray | None = None

        self.master_eq = XGMultiBandEqualizer(sample_rate)

        # Per-channel EQ (GS per-part 2-band EQ support)
        self.per_channel_eq: list[XGMultiBandEqualizer] = [
            XGMultiBandEqualizer(sample_rate) for _ in range(max_channels)
        ]

        # Pipeline topology — configurable effect chain
        self.pipeline: PipelineTopology = PipelineTopology.xg_standard()

        # Output bus manager — multi-bus routing support
        self.bus_manager = OutputBusManager(num_buses=1, num_parts=max_channels)
        self.bus_manager.allocate_buffers(block_size)

        self.effects = []

        self.processing_stats = {
            "total_blocks_processed": 0,
            "average_processing_time_ms": 0.0,
            "peak_processing_time_ms": 0.0,
            "cpu_usage_percent": 0.0,
            "memory_usage_mb": 0.0,
            "zero_allocation_violations": 0,
            "buffer_pool_hits": 0,
            "buffer_pool_misses": 0,
        }

        self.lock = threading.RLock()

        # Jupiter-X integration
        self.jupiter_x_mode = False
        self.jupiter_x_effects = self._initialize_jupiter_x_effects()
        # Jupiter-X VCM effects chain — authentic analog circuit modeling (lazy import to avoid circular dep)
        from ...hardware.jupiter_x.jupiter_x_vcm_effects import JupiterXVCMEffects

        self.vcm_chain = JupiterXVCMEffects(sample_rate, block_size, self.buffer_pool)
        # All VCM effects disabled by default; enabled individually via set_vcm_effect_enabled

        self.jupiter_x_modulation = {
            "lfo1": {"rate": 5.0, "depth": 0.0, "waveform": "sine"},
            "lfo2": {"rate": 3.0, "depth": 0.0, "waveform": "triangle"},
            "envelope": {"attack": 0.01, "decay": 0.1, "amount": 0.0},
        }

        self.mpe_enabled = False
        self.mpe_channels = {}

        self._initialize_processing()

    def _initialize_jupiter_x_effects(self):
        return {
            "distortion": {
                "type": "distortion",
                "algorithm": "jupiter_ds",
                "params": {"drive": 0.5, "tone": 0.5, "level": 0.8},
            },
            "phaser": {
                "type": "vcm_phaser",
                "algorithm": "jupiter_phaser",
                "params": {"rate": 0.5, "depth": 0.7, "manual": 0.5, "resonance": 0.3},
            },
            "enhancer": {
                "type": "stereo_enhancer",
                "algorithm": "jupiter_enhancer",
                "params": {"enhance": 0.5, "clarity": 0.3, "depth": 0.5},
            },
            "vcm_rotary": {
                "type": "rotary_speaker",
                "algorithm": "jupiter_rotary",
                "params": {"speed": 0.5, "drive": 0.3, "balance": 0.5},
            },
            "overdrive": {
                "type": "overdrive",
                "algorithm": "jupiter_od",
                "params": {"gain": 0.5, "tone": 0.5, "level": 0.8},
            },
        }

    def _apply_jupiter_x_vcm_chain(self, main_mix: np.ndarray, num_samples: int) -> None:
        """Apply Jupiter-X VCM effects chain to the stereo mix (in-place).

        Processes left and right channels through the VCM chain when
        Jupiter-X mode is active and at least one VCM effect is enabled.
        Called after channel mixing, before variation effects.
        """
        if not self.jupiter_x_mode:
            return
        # Quick check: skip if no VCM effect is enabled
        vcm = self.vcm_chain
        if not (
            vcm.vcm_distortion.enabled
            or vcm.vcm_phaser.enabled
            or vcm.vcm_chorus.enabled
            or vcm.vcm_delay.enabled
            or vcm.vcm_reverb.enabled
        ):
            return
        # Process left channel
        left = main_mix[:num_samples, 0]
        processed_left = vcm.process_vcm_chain(left)
        left[:] = processed_left
        # Process right channel (shares delay buffers — musically acceptable)
        right = main_mix[:num_samples, 1]
        processed_right = vcm.process_vcm_chain(right)
        right[:] = processed_right

    def set_jupiter_x_mode(self, enabled: bool) -> None:
        """Enable or disable Jupiter-X mode (activates VCM effects chain)."""
        with self.lock:
            self.jupiter_x_mode = enabled

    def set_vcm_effect_enabled(self, effect_name: str, enabled: bool) -> bool:
        """Enable or disable a specific VCM effect.

        Args:
            effect_name: One of 'distortion', 'phaser', 'chorus', 'delay', 'reverb'
            enabled: Whether the effect should process audio

        Returns:
            True if the effect was found and set
        """
        effect_map = {
            "distortion": self.vcm_chain.vcm_distortion,
            "phaser": self.vcm_chain.vcm_phaser,
            "chorus": self.vcm_chain.vcm_chorus,
            "delay": self.vcm_chain.vcm_delay,
            "reverb": self.vcm_chain.vcm_reverb,
        }
        with self.lock:
            effect = effect_map.get(effect_name)
            if effect is None:
                return False
            effect.enabled = enabled
            return True

    def set_vcm_parameters(self, effect_name: str, params: dict) -> bool:
        """Set parameters for a specific VCM effect.

        Args:
            effect_name: Effect name ('distortion', 'phaser', 'chorus', 'delay', 'reverb')
            params: Dict of parameter name → value (0-1 normalized)

        Returns:
            True if the effect was found
        """
        vcm = self.vcm_chain
        effect_map = {
            "distortion": vcm.vcm_distortion,
            "phaser": vcm.vcm_phaser,
            "chorus": vcm.vcm_chorus,
            "delay": vcm.vcm_delay,
            "reverb": vcm.vcm_reverb,
        }
        with self.lock:
            effect = effect_map.get(effect_name)
            if effect is None:
                return False
            for key, value in params.items():
                if hasattr(effect, key):
                    setattr(effect, key, value)
            return True

    def _initialize_processing(self):
        with self.lock:
            self.buffer_manager = XGBufferManager(self.buffer_pool)
        self.dry_signal_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self._preallocate_static_buffers()

    def _preallocate_static_buffers(self):
        self._channel_result_buffers = [
            self.memory_pool.get_stereo_buffer(self.block_size) for _ in range(self.max_channels)
        ]
        self._main_mix_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self._reverb_accumulate_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self._chorus_accumulate_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self._variation_output_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self._system_output_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self._temp_working_buffers = [
            self.memory_pool.get_stereo_buffer(self.block_size) for _ in range(8)
        ]
        self._reverb_temp_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self._chorus_temp_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self._eq_work_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self._wet_dry_work_buffer = self.memory_pool.get_stereo_buffer(self.block_size)

    def process_channels_to_stereo_zero_alloc(
        self, input_channels: list[np.ndarray], output_stereo: np.ndarray, num_samples: int
    ) -> None:
        """Process channels through the single-bus pipeline.

        Compatibility shim that forwards to the multi-bus processing path
        using bus 0 (master bus). New code should use process_buses_zero_alloc.
        """
        self.process_buses_zero_alloc({0: input_channels}, num_samples, output_stereo)

    def process_buses_zero_alloc(
        self,
        bus_inputs: dict[int, list[np.ndarray]],
        num_samples: int,
        output_stereo: np.ndarray,
    ) -> None:
        """Process audio through multiple output buses.

        Each bus gets its own pipeline processing. Results are summed
        into the master output.

        Args:
            bus_inputs: Dict of {bus_id: [input_channels]} — which channels go to which bus
            num_samples: Number of samples to process
            output_stereo: Master output buffer (written to)
        """
        if not self.processing_enabled or not self.buffer_manager:
            # Fallback: mix all inputs directly
            for bus_id, channels in bus_inputs.items():
                if channels:
                    self._mix_channels_to_stereo_direct(channels, output_stereo, num_samples)
            return

        with self.lock:
            start_time = time.perf_counter()

            try:
                # Reset all bus outputs
                self.bus_manager.reset_all_buses()

                # Process each bus independently
                for bus_id, input_channels in bus_inputs.items():
                    if not input_channels:
                        continue

                    nch = len(input_channels)
                    if nch == 0 or num_samples > self.block_size:
                        continue

                    bus_output = self.bus_manager.get_bus_output(bus_id)
                    if bus_output is None:
                        continue

                    with self.buffer_manager as bm:
                        processed_channels = [bm.get_stereo(num_samples) for _ in range(nch)]
                        main_mix = bm.get_stereo(num_samples)
                        reverb_accumulate = bm.get_stereo(num_samples)
                        chorus_accumulate = bm.get_stereo(num_samples)
                        delay_accumulate = bm.get_stereo(num_samples)
                        variation_output = bm.get_stereo(num_samples)
                        system_output = bm.get_stereo(num_samples)
                        temp_buffers = [bm.get_stereo(num_samples) for _ in range(4)]
                        for tb in temp_buffers:
                            tb.fill(0.0)

                    # Zero recycled buffers to prevent stale data from the
                    # buffer pool leaking into the output when stages are
                    # skipped (e.g. insertion disabled).
                    for pc in processed_channels:
                        pc.fill(0.0)
                    main_mix.fill(0.0)
                    reverb_accumulate.fill(0.0)
                    chorus_accumulate.fill(0.0)
                    delay_accumulate.fill(0.0)

                    # Use the bus's topology
                    original_pipeline = self.pipeline
                    bus_topology = self.bus_manager.get_bus_topology(bus_id)
                    if bus_topology is not None:
                        self.pipeline = bus_topology

                    try:
                        self.process_pipeline(
                            input_channels,
                            bus_output,
                            num_samples,
                            processed_channels,
                            main_mix,
                            reverb_accumulate,
                            chorus_accumulate,
                            delay_accumulate,
                            variation_output,
                            system_output,
                            temp_buffers,
                        )
                    finally:
                        self.pipeline = original_pipeline

                # Sum all bus outputs to master
                self.bus_manager.master_sum(num_samples, output_stereo)

                self._update_performance_stats((time.perf_counter() - start_time) * 1000)

            except Exception as e:
                logger.error(f"Multi-bus processing error: {e}")
                # Fallback: direct mix of bus 0
                if 0 in bus_inputs:
                    self._mix_channels_to_stereo_direct(bus_inputs[0], output_stereo, num_samples)

    def process_pipeline(
        self,
        input_channels: list[np.ndarray],
        output_stereo: np.ndarray,
        num_samples: int,
        processed_channels: list[np.ndarray],
        main_mix: np.ndarray,
        reverb_accumulate: np.ndarray,
        chorus_accumulate: np.ndarray,
        delay_accumulate: np.ndarray,
        variation_output: np.ndarray,
        system_output: np.ndarray,
        temp_buffers: list[np.ndarray],
    ) -> None:
        """Execute the configured effects pipeline based on current topology.

        Dispatches each enabled stage in order, matching the existing
        zero-alloc processing methods exactly.

        When INSERTION is disabled, input channels are copied directly to
        processed_channels (passthrough).  When MASTER is disabled,
        system_output is copied directly to output_stereo (passthrough).
        This preserves the signal chain even with all effects off.
        """
        # --- Capture true dry signal for wet/dry mixing BEFORE any effects
        # processing touches the buffers. This must happen prior to any
        # stage so that the dry reference is the raw input, not the
        # fully-processed (wet) output.
        if self.wet_dry_mix < 1.0 and self.dry_signal_buffer is not None and input_channels:
            self.dry_signal_buffer[:num_samples, :].fill(0.0)
            nch = len(input_channels)
            inv_nch = 1.0 / max(nch, 1)
            for ch in input_channels:
                if ch.ndim == 1:
                    self.dry_signal_buffer[:num_samples, 0] += ch[:num_samples]
                    self.dry_signal_buffer[:num_samples, 1] += ch[:num_samples]
                else:
                    self.dry_signal_buffer[:num_samples, 0] += ch[:num_samples, 0]
                    self.dry_signal_buffer[:num_samples, 1] += ch[:num_samples, 1]
            if nch > 1:
                self.dry_signal_buffer[:num_samples] *= inv_nch

        # --- Passthrough: INSERTION stage copies input → processed_channels.
        # If the stage is skipped, do the copy here so MIX has data to work with.
        insertion_slot = self.pipeline.get_stage(EffectStageType.INSERTION)
        insertion_skipped = (
            insertion_slot is None or not insertion_slot.enabled or insertion_slot.bypass
        )
        if insertion_skipped:
            for i, ch in enumerate(input_channels):
                if i < len(processed_channels):
                    if ch.ndim == 1:
                        processed_channels[i][:num_samples, 0] = ch[:num_samples]
                        processed_channels[i][:num_samples, 1] = ch[:num_samples]
                    else:
                        np.copyto(processed_channels[i][:num_samples], ch[:num_samples])

        for slot in self.pipeline.stages:
            if not slot.enabled or slot.bypass:
                continue

            stage = slot.stage_type

            if stage == EffectStageType.INSERTION:
                self._apply_insertion_effects_to_channels_optimized(
                    input_channels, processed_channels, temp_buffers, num_samples
                )
            elif stage == EffectStageType.MIX:
                self._mix_channels_with_effect_sends_optimized(
                    processed_channels, main_mix, reverb_accumulate, chorus_accumulate, num_samples
                )
                # Also accumulate delay sends
                if (
                    self.pipeline.get_stage(EffectStageType.SYSTEM_DELAY)
                    and self.pipeline.get_stage(EffectStageType.SYSTEM_DELAY).enabled
                ):
                    self._accumulate_delay_sends_optimized(
                        processed_channels, delay_accumulate, num_samples
                    )
            elif stage == EffectStageType.VCM:
                self._apply_jupiter_x_vcm_chain(main_mix, num_samples)
            elif stage == EffectStageType.VARIATION:
                self._apply_variation_effects_to_mix_optimized(
                    main_mix, variation_output, temp_buffers, num_samples
                )
            elif stage == EffectStageType.SYSTEM_REVERB:
                self._apply_system_effects_with_sends_optimized(
                    variation_output if self._get_variation_enabled() else main_mix,
                    system_output,
                    reverb_accumulate,
                    chorus_accumulate,
                    temp_buffers,
                    num_samples,
                )
            elif stage == EffectStageType.SYSTEM_CHORUS:
                # Chorus is handled inside _apply_system_effects_with_sends_optimized
                # So this stage is a no-op when reverb is also present
                # When reverb is bypassed, apply chorus independently
                if (
                    not self.pipeline.get_stage(EffectStageType.SYSTEM_REVERB)
                    or not self.pipeline.get_stage(EffectStageType.SYSTEM_REVERB).enabled
                ):
                    self._apply_system_effects_with_sends_optimized(
                        variation_output if self._get_variation_enabled() else main_mix,
                        system_output,
                        reverb_accumulate,
                        chorus_accumulate,
                        temp_buffers,
                        num_samples,
                    )
            elif stage == EffectStageType.SYSTEM_DELAY:
                self._apply_system_delay_to_mix(
                    variation_output if self._get_variation_enabled() else main_mix,
                    system_output,
                    delay_accumulate,
                    num_samples,
                )
            elif stage == EffectStageType.MASTER:
                self._apply_master_processing_optimized(system_output, num_samples, output_stereo)

        # --- Passthrough: MASTER stage copies system_output → output_stereo.
        # If the stage is skipped, copy directly so the bus gets output.
        master_slot = self.pipeline.get_stage(EffectStageType.MASTER)
        master_skipped = master_slot is None or not master_slot.enabled or master_slot.bypass
        if master_skipped:
            np.copyto(output_stereo[:num_samples], system_output[:num_samples])

    def _get_variation_enabled(self) -> bool:
        """Check if variation effects are in the pipeline and enabled."""
        var_slot = self.pipeline.get_stage(EffectStageType.VARIATION)
        return var_slot is not None and var_slot.enabled and not var_slot.bypass

    def set_pipeline_topology(self, topology: PipelineTopology) -> None:
        """Set a new pipeline topology at runtime."""
        with self.lock:
            self.pipeline = topology

    def get_pipeline_topology(self) -> PipelineTopology:
        """Get the current pipeline topology."""
        with self.lock:
            return self.pipeline

    def set_num_buses(self, num_buses: int) -> None:
        """Set the number of output buses (1-4). Resets existing assignments."""
        with self.lock:
            self.bus_manager = OutputBusManager(
                num_buses=max(1, min(4, num_buses)),
                num_parts=self.max_channels,
            )
            self.bus_manager.allocate_buffers(self.block_size)

    def assign_part_to_bus(self, part_num: int, bus_id: int) -> bool:
        """Assign a part to an output bus."""
        return self.bus_manager.assign_part_to_bus(part_num, bus_id)

    def get_part_bus(self, part_num: int) -> int:
        """Get the bus for a part."""
        return self.bus_manager.get_part_bus(part_num)

    def set_bus_topology(self, bus_id: int, topology: PipelineTopology) -> bool:
        """Set pipeline topology for a bus."""
        return self.bus_manager.set_bus_topology(bus_id, topology)

    def _accumulate_delay_sends_optimized(
        self, processed_channels: list[np.ndarray], delay_accumulate: np.ndarray, num_samples: int
    ) -> None:
        """Accumulate per-channel delay sends into delay accumulate buffer."""
        for ch_idx, ch_buf in enumerate(processed_channels):
            if ch_idx < len(self.delay_sends):
                send = self.delay_sends[ch_idx]
                if send > 0.0:
                    for s in range(num_samples):
                        delay_accumulate[s, 0] += ch_buf[s, 0] * send
                        delay_accumulate[s, 1] += ch_buf[s, 1] * send

    def _apply_system_delay_to_mix(
        self,
        input_mix: np.ndarray,
        output_mix: np.ndarray,
        delay_accumulate: np.ndarray,
        num_samples: int,
    ) -> None:
        """Apply system delay effect to the mix."""
        # Ensure pre-allocated buffers are large enough
        if num_samples > len(self._delay_out_l):
            self._delay_out_l = np.zeros(int(num_samples * 1.5), dtype=np.float32)
            self._delay_out_r = np.zeros(int(num_samples * 1.5), dtype=np.float32)
        delay_out_l = self._delay_out_l[:num_samples]
        delay_out_r = self._delay_out_r[:num_samples]
        # Process delay sends through delay effect
        self.system_delay.process(
            delay_accumulate[:num_samples, 0],
            delay_accumulate[:num_samples, 1],
            delay_out_l,
            delay_out_r,
            num_samples,
        )
        # Mix delay output into the output
        for s in range(num_samples):
            output_mix[s, 0] += delay_out_l[s]
            output_mix[s, 1] += delay_out_r[s]

    def _apply_insertion_effects_to_channels_optimized(
        self,
        input_channels: list[np.ndarray],
        processed_channels: list[np.ndarray],
        temp_buffers: list[np.ndarray],
        num_samples: int,
    ) -> None:
        for ch_idx, channel_data in enumerate(input_channels):
            if ch_idx >= len(self.insertion_effects):
                if channel_data.ndim == 1:
                    processed_channels[ch_idx][:num_samples, 0] = channel_data[:num_samples]
                    processed_channels[ch_idx][:num_samples, 1] = channel_data[:num_samples]
                else:
                    np.copyto(processed_channels[ch_idx][:num_samples], channel_data[:num_samples])
                continue

            working_buffer = temp_buffers[ch_idx % len(temp_buffers)]

            if channel_data.ndim == 2:
                np.copyto(working_buffer[:num_samples], channel_data[:num_samples])
            else:
                # Mono channel: copy same data to both stereo channels
                working_buffer[:num_samples, 0] = channel_data[:num_samples]
                working_buffer[:num_samples, 1] = channel_data[:num_samples]

            insertion_params: dict[str, Any] = {}
            self.insertion_effects[ch_idx].apply_insertion_effect_to_channel_zero_alloc(
                working_buffer, channel_data, insertion_params, num_samples, ch_idx
            )

            np.copyto(processed_channels[ch_idx][:num_samples], working_buffer[:num_samples])

    def _mix_channels_with_effect_sends_optimized(
        self,
        processed_channels: list[np.ndarray],
        main_mix: np.ndarray,
        reverb_accumulate: np.ndarray,
        chorus_accumulate: np.ndarray,
        num_samples: int,
    ) -> None:
        for ch_idx, channel_data in enumerate(processed_channels):
            if ch_idx >= self.max_channels:
                continue

            volume = self.channel_volumes[ch_idx]
            pan = self.channel_pans[ch_idx]
            reverb_send = self.reverb_sends[ch_idx]
            chorus_send = self.chorus_sends[ch_idx]
            variation_send = self.variation_sends[ch_idx]

            if channel_data.ndim == 1:
                left_data = channel_data[:num_samples] * volume * (1.0 - pan) * 0.5
                right_data = channel_data[:num_samples] * volume * (1.0 + pan) * 0.5
            else:
                left_data = channel_data[:num_samples, 0] * volume * (1.0 - pan)
                right_data = channel_data[:num_samples, 1] * volume * (1.0 + pan)

            # Full dry signal at channel volume — sends are additive, not subtractive.
            # In XG send/return architecture, the effect sends are POST-fader copies,
            # not crossfade mix parameters. The send levels control how much of the
            # channel signal goes to each effect bus; the dry stays at full volume.
            dry_level = 1.0
            main_mix[:num_samples, 0] += left_data
            main_mix[:num_samples, 1] += right_data
            if reverb_send > 0:
                reverb_accumulate[:num_samples, 0] += left_data * reverb_send
                reverb_accumulate[:num_samples, 1] += right_data * reverb_send
            if chorus_send > 0:
                chorus_accumulate[:num_samples, 0] += left_data * chorus_send
                chorus_accumulate[:num_samples, 1] += right_data * chorus_send

    def _apply_variation_effects_to_mix_optimized(
        self,
        main_mix: np.ndarray,
        variation_output: np.ndarray,
        temp_buffers: list[np.ndarray],
        num_samples: int,
    ) -> None:
        if not self.effect_units_active[0]:
            np.copyto(variation_output[:num_samples], main_mix[:num_samples])
            return

        np.copyto(variation_output[:num_samples], main_mix[:num_samples])
        self.variation_effects.apply_variation_effect_zero_alloc(
            variation_output[:num_samples], num_samples
        )

    def _apply_system_effects_with_sends_optimized(
        self,
        variation_output: np.ndarray,
        system_output: np.ndarray,
        reverb_accumulate: np.ndarray,
        chorus_accumulate: np.ndarray,
        temp_buffers: list[np.ndarray],
        num_samples: int,
    ) -> None:
        np.copyto(system_output[:num_samples], variation_output[:num_samples])
        use_gs_effects = self._should_use_gs_system_effects()

        if self.effect_units_active[1] and np.max(np.abs(reverb_accumulate)) > 0:
            reverb_wet = self._apply_system_reverb_optimized(
                reverb_accumulate, temp_buffers[0], num_samples, use_gs_effects
            )
            if reverb_wet is not None:
                system_output[:num_samples] += reverb_wet[:num_samples]

        if self.effect_units_active[2] and np.max(np.abs(chorus_accumulate)) > 0:
            chorus_wet = self._apply_system_chorus_optimized(
                chorus_accumulate, temp_buffers[1], num_samples, use_gs_effects
            )
            if chorus_wet is not None:
                system_output[:num_samples] += chorus_wet[:num_samples]

    def _should_use_gs_system_effects(self) -> bool:
        return bool(
            self.synthesizer
            and hasattr(self.synthesizer, "parameter_priority")
            and self.synthesizer.parameter_priority.is_gs_active()
        )

    def _apply_system_reverb_optimized(
        self, send: np.ndarray, buf: np.ndarray, n: int, gs: bool = False
    ) -> np.ndarray | None:
        return self._apply_system_processor(send, buf, n, self.system_effects.reverb_processor, gs)

    def _apply_system_chorus_optimized(
        self, send: np.ndarray, buf: np.ndarray, n: int, gs: bool = False
    ) -> np.ndarray | None:
        return self._apply_system_processor(send, buf, n, self.system_effects.chorus_processor, gs)

    def _apply_system_processor(
        self, send: np.ndarray, buf: np.ndarray, n: int, processor, use_gs: bool = False
    ) -> np.ndarray | None:
        try:
            np.copyto(buf[:n], send[:n])
            if use_gs and self.synthesizer and hasattr(self.synthesizer, "gs_components"):
                gs_system = self.synthesizer.gs_components.get_component("system_params")
                if gs_system:
                    # Apply GS system-level master send as global wet trim.
                    # The GS sysex handler already forwards per-part send levels
                    # and per-effect parameters via set_system_effect_parameter().
                    # Here we apply the GS master return level as an overall wet gain.
                    if processor is self.system_effects.reverb_processor:
                        gs_level = getattr(gs_system, "reverb_send_level", 0)
                    elif processor is self.system_effects.chorus_processor:
                        gs_level = getattr(gs_system, "chorus_send_level", 0)
                    else:
                        gs_level = 0
                    if gs_level > 0:
                        buf[:n] *= gs_level / 127.0
            processor.apply_system_effects_to_mix_zero_alloc(buf, n)
            return buf
        except Exception:
            return None

    def _apply_master_processing_optimized(
        self, system_output: np.ndarray, num_samples: int, output_stereo: np.ndarray
    ) -> None:
        np.copyto(output_stereo[:num_samples], system_output[:num_samples])
        if self.master_level != 1.0:
            output_stereo[:num_samples] *= self.master_level
        if self.wet_dry_mix < 1.0 and self.dry_signal_buffer is not None:
            wl, dl = self.wet_dry_mix, 1.0 - self.wet_dry_mix
            output_stereo[:num_samples] = (
                output_stereo[:num_samples] * wl + self.dry_signal_buffer[:num_samples] * dl
            )
        np.copyto(self._eq_work_buffer[:num_samples], output_stereo[:num_samples])
        eq = self.master_eq.process_buffer(self._eq_work_buffer[:num_samples])
        self._apply_stereo_enhancement(eq, num_samples)
        cs = min(num_samples, eq.shape[0], output_stereo.shape[0])
        if eq.ndim == 1 and output_stereo.ndim == 2:
            output_stereo[:cs, 0] = eq[:cs]
            output_stereo[:cs, 1] = eq[:cs]
        else:
            cc = min(
                output_stereo.shape[1] if output_stereo.ndim > 1 else 1,
                eq.shape[1] if eq.ndim > 1 else 1,
            )
            output_stereo[:cs, :cc] = eq[:cs, :cc]
        np.clip(output_stereo[:num_samples], -0.99, 0.99, out=output_stereo[:num_samples])

    def _apply_stereo_enhancement(self, stereo_buffer: np.ndarray, num_samples: int) -> None:
        """Mid-side stereo enhancement — preserves mono compatibility.

        Widen the side (L-R) signal while keeping the mid (L+R) signal intact.
        e = 0 = no effect; e = 1.0 = maximum width.
        """
        e = 0.1  # enhancement amount
        mid = (stereo_buffer[:num_samples, 0] + stereo_buffer[:num_samples, 1]) * 0.5
        side = (stereo_buffer[:num_samples, 0] - stereo_buffer[:num_samples, 1]) * 0.5
        side *= 1.0 + e  # widen the side signal
        stereo_buffer[:num_samples, 0] = mid + side
        stereo_buffer[:num_samples, 1] = mid - side

    def _mix_channels_to_stereo_direct(
        self, input_channels: list[np.ndarray], output_stereo: np.ndarray, num_samples: int
    ) -> None:
        output_stereo[:num_samples, :].fill(0.0)
        num_active_channels = min(len(input_channels), self.max_channels)
        mix_level = 1.0 / max(num_active_channels, 1)

        for channel_data in input_channels:
            if channel_data.ndim == 1:
                output_stereo[:num_samples, 0] += channel_data[:num_samples] * mix_level
                output_stereo[:num_samples, 1] += channel_data[:num_samples] * mix_level
            else:
                output_stereo[:num_samples, 0] += channel_data[:num_samples, 0] * mix_level
                output_stereo[:num_samples, 1] += channel_data[:num_samples, 1] * mix_level

    def _update_performance_stats(self, t_ms: float) -> None:
        s = self.processing_stats
        s["total_blocks_processed"] += 1
        s["average_processing_time_ms"] = s["average_processing_time_ms"] * 0.99 + t_ms * 0.01
        if t_ms > s["peak_processing_time_ms"]:
            s["peak_processing_time_ms"] = t_ms

    def set_channel_insertion_effect(self, channel: int, slot: int, effect_type: int) -> bool:
        with self.lock:
            return 0 <= channel < len(self.insertion_effects) and self.insertion_effects[
                channel
            ].set_insertion_effect_type(slot, effect_type)

    def set_channel_insertion_bypass(self, channel: int, slot: int, bypass: bool) -> bool:
        with self.lock:
            return 0 <= channel < len(self.insertion_effects) and self.insertion_effects[
                channel
            ].set_insertion_effect_bypass(slot, bypass)

    def set_variation_effect_type(self, variation_type: int) -> bool:
        with self.lock:
            try:
                if hasattr(self.variation_effects, "set_variation_type"):
                    # Accept both int and XGVariationType
                    self.variation_effects.set_variation_type(variation_type)
                return True
            except (ValueError, TypeError):
                return False

    def set_effect_send_level(self, channel: int, effect_type: str, level: float) -> bool:
        with self.lock:
            if not (0 <= channel < self.max_channels):
                return False
            level = max(0.0, min(1.0, level))
            sends = {
                "reverb": self.reverb_sends,
                "chorus": self.chorus_sends,
                "variation": self.variation_sends,
            }
            t = sends.get(effect_type)
            if t is None:
                return False
            t[channel] = level
            return True

    def set_system_effect_parameter(self, effect: str, param: str, value: float) -> bool:
        with self.lock:
            return self.system_effects.set_system_effect_parameter(effect, param, value)

    def modulate_efx_parameter(
        self, part_num: int, parameter: str, depth: float, value: float
    ) -> None:
        """Modulate an EFX parameter from a control switch.

        Args:
            part_num: Target part number
            parameter: EFX parameter name
            depth: Modulation depth (0.0-1.0)
            value: CC normalized value (0.0-1.0)
        """
        if not (0 <= part_num < len(self.insertion_effects)):
            return
        try:
            efx = self.insertion_effects[part_num]
            if hasattr(efx, "set_parameter"):
                # Scale value by depth
                scaled = 0.5 + (value - 0.5) * depth
                efx.set_parameter(parameter, scaled)
        except Exception:
            logger.warning(f"EFX modulation failed for part {part_num}", exc_info=True)

    def set_effect_unit_activation(self, unit: int, active: bool) -> bool:
        with self.lock:
            if 0 <= unit < len(self.effect_units_active):
                self.effect_units_active[unit] = active
                return True
            return False

    def set_master_controls(self, level: float = None, wet_dry: float = None) -> bool:
        with self.lock:
            if level is not None:
                self.master_level = max(0.0, min(2.0, level))
            if wet_dry is not None:
                self.wet_dry_mix = max(0.0, min(1.0, wet_dry))
            return level is not None or wet_dry is not None

    def set_channel_volume(self, channel: int, volume: float) -> bool:
        with self.lock:
            if 0 <= channel < self.max_channels:
                self.channel_volumes[channel] = max(0.0, min(1.0, volume))
                return True
            return False

    def set_channel_pan(self, channel: int, pan: float) -> bool:
        with self.lock:
            if 0 <= channel < self.max_channels:
                self.channel_pans[channel] = max(-1.0, min(1.0, pan))
                return True
            return False

    def set_master_eq_type(self, eq_type: int) -> bool:
        with self.lock:
            try:
                self.master_eq.set_eq_type(eq_type)
                return True
            except Exception:
                return False

    _EQ_BAND_SETTERS = {
        "low": lambda eq, v: eq.set_low_gain(v),
        "low_mid": lambda eq, v: eq.set_low_mid_gain(v),
        "mid": lambda eq, v: eq.set_mid_gain(v),
        "high_mid": lambda eq, v: eq.set_high_mid_gain(v),
        "high": lambda eq, v: eq.set_high_gain(v),
    }

    def set_master_eq_gain(self, band: str, gain_db: float) -> bool:
        with self.lock:
            s = self._EQ_BAND_SETTERS.get(band)
            if s is None:
                return False
            try:
                s(self.master_eq, gain_db)
                return True
            except Exception:
                return False

    def set_master_eq_frequency(self, freq_hz: float) -> bool:
        with self.lock:
            try:
                self.master_eq.set_mid_frequency(freq_hz)
                return True
            except Exception:
                return False

    def set_master_eq_q_factor(self, q: float) -> bool:
        with self.lock:
            try:
                self.master_eq.set_q_factor(q)
                return True
            except Exception:
                return False

    def set_channel_eq_gain(self, channel: int, band: str, gain_db: float) -> bool:
        """Set per-channel EQ gain for GS per-part EQ support.

        Args:
            channel: Channel index (0 to max_channels-1)
            band: 'low' or 'high'
            gain_db: Gain in dB (range -12 to +12)

        Returns:
            True if set successfully
        """
        if not (0 <= channel < self.max_channels):
            return False
        eq = self.per_channel_eq[channel]
        if band == "low":
            eq.set_low_gain(gain_db)
        elif band == "high":
            eq.set_high_gain(gain_db)
        else:
            return False
        return True

    def reset_channel_eq(self, channel: int) -> None:
        """Reset per-channel EQ to flat."""
        if 0 <= channel < self.max_channels:
            self.per_channel_eq[channel].reset()

    def set_xg_effect_preset(self, preset_name: str) -> bool:
        return False

    def get_processing_status(self) -> dict[str, Any]:
        with self.lock:
            return {
                "processing_enabled": self.processing_enabled,
                "master_level": self.master_level,
                "wet_dry_mix": self.wet_dry_mix,
                "routing_mode": self.effect_routing_mode,
                "performance": self.processing_stats.copy(),
                "buffer_pool": self.buffer_pool.get_memory_stats(),
                "system_effects": self.system_effects.get_system_effects_status(),
                "variation_effects": self.variation_effects.get_variation_status(),
                "effect_units_active": self.effect_units_active.tolist(),
            }

    def reset_all_effects(self) -> None:
        _delay = int(2.0 * self.sample_rate)
        with self.lock:
            self.system_effects = XGSystemEffectsProcessor(
                self.sample_rate,
                self.block_size,
                int(5.0 * self.sample_rate),
                int(0.05 * self.sample_rate),
            )
            self.variation_effects = XGVariationEffectsProcessor(self.sample_rate, _delay)
            for i in range(len(self.insertion_effects)):
                self.insertion_effects[i] = ProductionXGInsertionEffectsProcessor(
                    self.sample_rate, _delay
                )
            self.channel_volumes.fill(1.0)
            self.channel_pans.fill(0.0)
            self.reverb_sends.fill(0.4)
            self.chorus_sends.fill(0.0)
            self.variation_sends.fill(0.0)
            self.effect_units_active.fill(True)
            self.master_level = 1.0
            self.wet_dry_mix = 1.0

    def get_current_state(self) -> dict[str, Any]:
        with self.lock:
            rp, cp = (
                self.system_effects.reverb_processor.params,
                self.system_effects.chorus_processor.params,
            )
            return {
                "processing_enabled": self.processing_enabled,
                "master_level": self.master_level,
                "wet_dry_mix": self.wet_dry_mix,
                "reverb_params": {
                    "type": rp.get("reverb_type", 1),
                    "level": rp.get("level", 0.0),
                    "time": rp.get("time", 0.5),
                    "hf_damping": rp.get("hf_damping", 0.5),
                    "density": rp.get("density", 0.8),
                },
                "chorus_params": {
                    "type": cp.get("chorus_type", 0),
                    "level": cp.get("level", 0.0),
                    "rate": cp.get("rate", 1.0),
                    "depth": cp.get("depth", 0.5),
                    "feedback": cp.get("feedback", 0.3),
                },
                "variation_params": {"level": 0.0, "type": 0},
                "equalizer_params": {"low_gain": 0.0, "mid_gain": 0.0, "high_gain": 0.0},
                "effect_units_active": self.effect_units_active.tolist(),
                "channel_volumes": self.channel_volumes.tolist(),
                "channel_pans": self.channel_pans.tolist(),
                "reverb_sends": self.reverb_sends.tolist(),
                "chorus_sends": self.chorus_sends.tolist(),
                "variation_sends": self.variation_sends.tolist(),
            }

    def shutdown(self) -> None:
        with self.lock:
            self.processing_enabled = False
            self.buffer_manager = None

    def register_effect(self, name: str, effect_func: Callable) -> bool:
        with self.lock:
            if not hasattr(self, "vcm_effects"):
                self.vcm_effects: dict[str, Callable] = {}
            self.vcm_effects[name] = effect_func
            return True

    def process_block(self, audio_block: np.ndarray) -> np.ndarray:
        with self.lock:
            if not hasattr(self, "vcm_effects") or not self.vcm_effects:
                return audio_block
            processed = audio_block.copy()
            for name, fn in self.vcm_effects.items():
                try:
                    processed = fn(processed)
                except Exception as e:
                    logger.error(f"VCM effect {name} failed: {e}")
            return processed

    def apply_effect(self, audio: np.ndarray, name: str, params: dict[str, float]) -> np.ndarray:
        with self.lock:
            if not hasattr(self, "vcm_effects") or name not in self.vcm_effects:
                return audio
            try:
                return self.vcm_effects[name](audio, params)
            except Exception as e:
                logger.error(f"VCM effect {name} failed: {e}")
                return audio

    def get_effect_info(self, name: str) -> dict[str, Any] | None:
        with self.lock:
            if hasattr(self, "vcm_effects") and name in self.vcm_effects:
                return {"name": name, "type": "vcm", "registered": True, "callable": True}
            return None

    def get_registered_vcm_effects(self) -> list[str]:
        with self.lock:
            return list(self.vcm_effects.keys()) if hasattr(self, "vcm_effects") else []

    def unregister_effect(self, name: str) -> bool:
        with self.lock:
            if hasattr(self, "vcm_effects") and name in self.vcm_effects:
                del self.vcm_effects[name]
                return True
            return False

    def clear_vcm_effects(self) -> None:
        with self.lock:
            if hasattr(self, "vcm_effects"):
                self.vcm_effects.clear()

    def _process_vcm_overdrive(
        self, audio: np.ndarray, params: dict[str, Any] | None = None
    ) -> np.ndarray:
        p = params or {}
        d, t, l = p.get("drive", 0.5), p.get("tone", 0.5), p.get("level", 0.7)
        x = audio * (1.0 + d * 3.0)
        proc = np.where(x > 0, np.tanh(x * 0.7) * 1.2, np.tanh(x * 0.5) * 0.8)
        if t < 0.5:
            proc = self._apply_simple_filter(proc, 1.0 - (0.5 - t) * 2.0, "lowpass")
        return proc * l

    def _process_vcm_distortion(
        self, audio: np.ndarray, params: dict[str, Any] | None = None
    ) -> np.ndarray:
        p = params or {}
        d, t, l = p.get("drive", 0.7), p.get("tone", 0.3), p.get("level", 0.6)
        x = audio * (1.0 + d * 5.0)
        proc = np.where(np.abs(x) < 0.8, x, np.sign(x) * (0.8 + (np.abs(x) - 0.8) * 0.3))
        proc += np.sign(proc) * 0.1
        if t < 0.5:
            proc = self._apply_simple_filter(proc, 0.3 + t, "lowpass")
        else:
            proc = self._apply_simple_filter(proc, 0.5 + t * 0.5, "highpass")
        return proc * l

    def _process_vcm_phaser(
        self, audio: np.ndarray, params: dict[str, Any] | None = None
    ) -> np.ndarray:
        p = params or {}
        r, d, f, l = (
            p.get("rate", 0.5),
            p.get("depth", 0.6),
            p.get("feedback", 0.3),
            p.get("level", 0.8),
        )
        t = np.arange(len(audio)) / self.sample_rate
        ps = np.sin(2 * np.pi * (0.1 + r * 2.0) * t) * d * np.pi
        ps = ps[:, np.newaxis]  # (N,) → (N, 1) for stereo broadcast
        proc = audio * np.cos(ps) + audio * np.sin(ps) * 0.5
        proc += proc * f
        proc *= l
        m = p.get("mix", 1.0)
        return audio * (1.0 - m) + proc * m

    def _process_vcm_equalizer(
        self, audio: np.ndarray, params: dict[str, Any] | None = None
    ) -> np.ndarray:
        p = params or {}
        lg, mg, hg, lvl = (
            p.get("low_gain", 0.0),
            p.get("mid_gain", 0.0),
            p.get("high_gain", 0.0),
            p.get("level", 1.0),
        )
        proc = audio.copy()
        if lg:
            proc = self._apply_simple_filter(proc, 0.1, "lowshelf", gain=10 ** (lg / 20.0))
        if hg:
            proc = self._apply_simple_filter(proc, 0.4, "highshelf", gain=10 ** (hg / 20.0))
        if mg:
            proc = self._apply_simple_filter(proc, 0.25, "peaking", gain=10 ** (mg / 20.0))
        return proc * lvl

    def _process_vcm_stereo_enhancer(
        self, audio: np.ndarray, params: dict[str, Any] | None = None
    ) -> np.ndarray:
        p = params or {}
        w, lvl = p.get("width", 0.5), p.get("level", 1.0)
        if audio.ndim == 1:
            return audio * lvl
        left, right = audio[:, 0].copy(), audio[:, 1].copy()
        m = (left + right) * 0.5
        d = (left - right) * w
        return np.column_stack([m + d, m - d]) * lvl

    def _apply_simple_filter(
        self, audio: np.ndarray, freq: float, filter_type: str = "lowpass", gain: float = 1.0
    ) -> np.ndarray:
        if filter_type in ("lowshelf", "highshelf", "peaking", "other"):
            return audio * gain
        alpha = freq
        if self._filter_work_buffer is None or self._filter_work_buffer.shape != audio.shape:
            self._filter_work_buffer = np.zeros_like(audio)
        filtered = self._filter_work_buffer
        filtered[0] = audio[0]
        if filter_type == "lowpass":
            for i in range(1, len(audio)):
                filtered[i] = alpha * audio[i] + (1 - alpha) * filtered[i - 1]
        elif filter_type == "highpass":
            for i in range(1, len(audio)):
                filtered[i] = alpha * (filtered[i - 1] + audio[i] - audio[i - 1])
        return filtered * gain

    def process_multiband_compression(
        self, audio: np.ndarray, params: dict[str, Any] | None = None
    ) -> np.ndarray:
        p = params or {}
        lt, mt, ht = (
            p.get("low_threshold", -20.0),
            p.get("mid_threshold", -20.0),
            p.get("high_threshold", -20.0),
        )
        lr, mr, hr = p.get("low_ratio", 4.0), p.get("mid_ratio", 4.0), p.get("high_ratio", 4.0)
        lo = self._apply_simple_filter(audio.copy(), 0.2, "lowpass")
        hi = self._apply_simple_filter(audio.copy(), 0.6, "highpass")
        mi = audio - lo - hi
        return (
            self._apply_compression(lo, lt, lr)
            + self._apply_compression(mi, mt, mr)
            + self._apply_compression(hi, ht, hr)
        )

    def _apply_compression(
        self, audio: np.ndarray, threshold_db: float, ratio: float
    ) -> np.ndarray:
        amp = np.abs(audio)
        db = 20 * np.log10(amp + 1e-10)
        cdb = np.where(db > threshold_db, threshold_db + (db - threshold_db) / ratio, db)
        return np.sign(audio) * (10 ** (cdb / 20.0))

    def process_multitap_delay(
        self, audio: np.ndarray, params: dict[str, Any] | None = None
    ) -> np.ndarray:
        p = params or {}
        tt, tl = p.get("tap_times", [100, 200, 300]), p.get("tap_levels", [0.5, 0.4, 0.3])
        fb, md, mr = (
            p.get("feedback", 0.3),
            p.get("modulation_depth", 0.0),
            p.get("modulation_rate", 0.5),
        )
        output = audio.copy()
        needed = len(audio) * 2
        if self._delay_tap_buffer is None or len(self._delay_tap_buffer) < needed:
            self._delay_tap_buffer = np.zeros(needed, dtype=np.float32)
        buf = self._delay_tap_buffer[:needed]
        buf[: len(audio)] = audio
        buf[len(audio) :] = 0.0
        for t, l in zip(tt, tl, strict=False):
            s = int(t * self.sample_rate / 1000.0)
            if s < len(buf):
                output += buf[s : s + len(audio)] * l
        if fb:
            output += audio * fb
        if md:
            output *= 1.0 + np.sin(2 * np.pi * mr * np.arange(len(output)) / self.sample_rate) * md
        return output

    def process_spectral_effect(
        self, audio: np.ndarray, params: dict[str, Any] | None = None
    ) -> np.ndarray:
        p = params or {}
        t = p.get("effect_type", "spectral_enhance")
        sp = np.fft.rfft(audio)
        mag, ph = np.abs(sp), np.angle(sp)
        if t == "spectral_enhance":
            mag *= 1.0 + p.get("enhancement", 0.5) * np.log10(mag + 1.0)
        elif t == "spectral_gate":
            mag = np.where(mag > p.get("threshold", 0.1), mag, 0.0)
        elif t == "spectral_compress":
            th, r = p.get("threshold", 0.5), p.get("ratio", 2.0)
            mag = np.where(mag > th, th + (mag - th) / r, mag)
        return np.fft.irfft(mag * np.exp(1j * ph), len(audio))

    def process_parallel_chain(
        self, audio: np.ndarray, chain: list[tuple[str, dict[str, Any]]], mix: float = 0.5
    ) -> np.ndarray:
        wet = audio.copy()
        for name, p in chain:
            wet = self.apply_effect(wet, name, p)
        return audio * (1.0 - mix) + wet * mix

    def get_effects_status(self) -> dict[str, Any]:
        return {
            "system_effects": {
                "reverb": self.system_effects.get("reverb", {}).get("type", "none"),
                "chorus": self.system_effects.get("chorus", {}).get("type", "none"),
            },
            "variation_effects": self.variation_effects.get_variation_status(),
            "insertion_effects": (
                len(self.insertion_effects) if hasattr(self, "insertion_effects") else 0
            ),
        }
