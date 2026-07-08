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
from .insertion import ProductionXGInsertionEffectsProcessor
from .system import XGSystemEffectsProcessor
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

        self.reverb_sends: np.ndarray = np.full(
            max_channels, 0.4, dtype=np.float32
        )
        self.chorus_sends: np.ndarray = np.full(
            max_channels, 0.0, dtype=np.float32
        )
        self.variation_sends: np.ndarray = np.full(
            max_channels, 0.0, dtype=np.float32
        )

        self.effect_units_active: np.ndarray = np.ones(10, dtype=bool)

        self.dry_signal_buffer: np.ndarray | None = None

        # Pre-allocated work buffers for hot-path processing (zero-allocation)
        self._filter_work_buffer: np.ndarray | None = None
        self._delay_tap_buffer: np.ndarray | None = None

        self.master_eq = XGMultiBandEqualizer(sample_rate)

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
            "distortion": {"type": "distortion", "algorithm": "jupiter_ds", "params": {"drive": 0.5, "tone": 0.5, "level": 0.8}},
            "phaser": {"type": "vcm_phaser", "algorithm": "jupiter_phaser", "params": {"rate": 0.5, "depth": 0.7, "manual": 0.5, "resonance": 0.3}},
            "enhancer": {"type": "stereo_enhancer", "algorithm": "jupiter_enhancer", "params": {"enhance": 0.5, "clarity": 0.3, "depth": 0.5}},
            "vcm_rotary": {"type": "rotary_speaker", "algorithm": "jupiter_rotary", "params": {"speed": 0.5, "drive": 0.3, "balance": 0.5}},
            "overdrive": {"type": "overdrive", "algorithm": "jupiter_od", "params": {"gain": 0.5, "tone": 0.5, "level": 0.8}},
        }

    def _initialize_processing(self):
        with self.lock:
            self.buffer_manager = XGBufferManager(self.buffer_pool)
        self.dry_signal_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self._preallocate_static_buffers()

    def _preallocate_static_buffers(self):
        self._channel_result_buffers = [self.memory_pool.get_stereo_buffer(self.block_size) for _ in range(self.max_channels)]
        self._main_mix_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self._reverb_accumulate_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self._chorus_accumulate_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self._variation_output_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self._system_output_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self._temp_working_buffers = [self.memory_pool.get_stereo_buffer(self.block_size) for _ in range(8)]
        self._reverb_temp_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self._chorus_temp_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self._eq_work_buffer = self.memory_pool.get_stereo_buffer(self.block_size)
        self._wet_dry_work_buffer = self.memory_pool.get_stereo_buffer(self.block_size)


    def process_channels_to_stereo_zero_alloc(self, input_channels: list[np.ndarray], output_stereo: np.ndarray, num_samples: int) -> None:
        if not self.processing_enabled or not self.buffer_manager:
            self._mix_channels_to_stereo_direct(input_channels, output_stereo, num_samples)
            return

        with self.lock:
            start_time = time.perf_counter()
            nch = len(input_channels)
            if nch == 0 or num_samples > self.block_size:
                return

            try:
                with self.buffer_manager as bm:
                    processed_channels = [bm.get_stereo(num_samples) for _ in range(nch)]
                    main_mix = bm.get_stereo(num_samples)
                    reverb_accumulate = bm.get_stereo(num_samples)
                    chorus_accumulate = bm.get_stereo(num_samples)
                    variation_output = bm.get_stereo(num_samples)
                    system_output = bm.get_stereo(num_samples)
                    temp_buffers = [bm.get_stereo(num_samples) for _ in range(4)]

                main_mix.fill(0.0)
                reverb_accumulate.fill(0.0)
                chorus_accumulate.fill(0.0)

                self._apply_insertion_effects_to_channels_optimized(
                    input_channels, processed_channels, temp_buffers, num_samples
                )
                self._mix_channels_with_effect_sends_optimized(
                    processed_channels, main_mix, reverb_accumulate, chorus_accumulate, num_samples
                )
                self._apply_variation_effects_to_mix_optimized(
                    main_mix, variation_output, temp_buffers, num_samples
                )
                self._apply_system_effects_with_sends_optimized(
                    variation_output, system_output, reverb_accumulate, chorus_accumulate, temp_buffers, num_samples
                )
                self._apply_master_processing_optimized(system_output, num_samples, output_stereo)
                self._update_performance_stats((time.perf_counter() - start_time) * 1000)

            except Exception as e:
                logger.error(f"XG Effects processing error: {e}")
                self._mix_channels_to_stereo_direct(input_channels, output_stereo, num_samples)


    def _apply_insertion_effects_to_channels_optimized(self, input_channels: list[np.ndarray], processed_channels: list[np.ndarray], temp_buffers: list[np.ndarray], num_samples: int) -> None:
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

            insertion_params = {"enabled": True}
            self.insertion_effects[ch_idx].apply_insertion_effect_to_channel_zero_alloc(
                working_buffer, channel_data, insertion_params, num_samples, ch_idx
            )

            np.copyto(processed_channels[ch_idx][:num_samples], working_buffer[:num_samples])

    def _mix_channels_with_effect_sends_optimized(self, processed_channels: list[np.ndarray], main_mix: np.ndarray, reverb_accumulate: np.ndarray, chorus_accumulate: np.ndarray, num_samples: int) -> None:
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
                left_data = channel_data[:num_samples, 0] * volume
                right_data = channel_data[:num_samples, 1] * volume

            dry_level = 1.0 - max(reverb_send, chorus_send, variation_send)
            if dry_level > 0:
                main_mix[:num_samples, 0] += left_data * dry_level
                main_mix[:num_samples, 1] += right_data * dry_level
            if reverb_send > 0:
                reverb_accumulate[:num_samples, 0] += left_data * reverb_send
                reverb_accumulate[:num_samples, 1] += right_data * reverb_send
            if chorus_send > 0:
                chorus_accumulate[:num_samples, 0] += left_data * chorus_send
                chorus_accumulate[:num_samples, 1] += right_data * chorus_send

    def _apply_variation_effects_to_mix_optimized(self, main_mix: np.ndarray, variation_output: np.ndarray, temp_buffers: list[np.ndarray], num_samples: int) -> None:
        if not self.effect_units_active[0]:
            np.copyto(variation_output[:num_samples], main_mix[:num_samples])
            return

        np.copyto(variation_output[:num_samples], main_mix[:num_samples])
        self.variation_effects.apply_variation_effect_zero_alloc(
            variation_output[:num_samples], num_samples
        )

    def _apply_system_effects_with_sends_optimized(self, variation_output: np.ndarray, system_output: np.ndarray, reverb_accumulate: np.ndarray, chorus_accumulate: np.ndarray, temp_buffers: list[np.ndarray], num_samples: int) -> None:
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
        return bool(self.synthesizer and hasattr(self.synthesizer, "parameter_priority") and self.synthesizer.parameter_priority.is_gs_active())

    def _apply_system_reverb_optimized(self, send: np.ndarray, buf: np.ndarray, n: int, gs: bool = False) -> np.ndarray | None:
        return self._apply_system_processor(send, buf, n, self.system_effects.reverb_processor, gs)

    def _apply_system_chorus_optimized(self, send: np.ndarray, buf: np.ndarray, n: int, gs: bool = False) -> np.ndarray | None:
        return self._apply_system_processor(send, buf, n, self.system_effects.chorus_processor, gs)

    def _apply_system_processor(self, send: np.ndarray, buf: np.ndarray, n: int, processor, use_gs: bool = False) -> np.ndarray | None:
        try:
            np.copyto(buf[:n], send[:n])
            if use_gs and self.synthesizer and hasattr(self.synthesizer, "gs_components"):
                gs_system = self.synthesizer.gs_components.get_component("system_params")
                if gs_system:
                    pass
            processor.apply_system_effects_to_mix_zero_alloc(buf, n)
            return buf
        except Exception:
            return None

    def _apply_master_processing_optimized(self, system_output: np.ndarray, num_samples: int, output_stereo: np.ndarray) -> None:
        np.copyto(output_stereo[:num_samples], system_output[:num_samples])
        if self.wet_dry_mix < 1.0 and self.dry_signal_buffer is not None:
            np.copyto(self.dry_signal_buffer[:num_samples], output_stereo[:num_samples])
        if self.master_level != 1.0:
            output_stereo[:num_samples] *= self.master_level
        if self.wet_dry_mix < 1.0 and self.dry_signal_buffer is not None:
            wl, dl = self.wet_dry_mix, 1.0 - self.wet_dry_mix
            self.dry_signal_buffer[:num_samples] *= dl
            output_stereo[:num_samples] = output_stereo[:num_samples] * wl + self.dry_signal_buffer[:num_samples]
        np.copyto(self._eq_work_buffer[:num_samples], output_stereo[:num_samples])
        eq = self.master_eq.process_buffer(self._eq_work_buffer[:num_samples])
        self._apply_stereo_enhancement(eq, num_samples)
        cs = min(num_samples, eq.shape[0], output_stereo.shape[0])
        if eq.ndim == 1 and output_stereo.ndim == 2:
            output_stereo[:cs, 0] = eq[:cs]
            output_stereo[:cs, 1] = eq[:cs]
        else:
            cc = min(output_stereo.shape[1] if output_stereo.ndim > 1 else 1, eq.shape[1] if eq.ndim > 1 else 1)
            output_stereo[:cs, :cc] = eq[:cs, :cc]
        np.clip(output_stereo[:num_samples], -0.99, 0.99, out=output_stereo[:num_samples])

    def _apply_stereo_enhancement(self, stereo_buffer: np.ndarray, num_samples: int) -> None:
        e = 0.1
        mono = (stereo_buffer[:num_samples, 0] + stereo_buffer[:num_samples, 1]) * 0.5
        stereo_buffer[:num_samples, 0] -= mono * e
        stereo_buffer[:num_samples, 1] -= mono * e

    def _mix_channels_to_stereo_direct(self, input_channels: list[np.ndarray], output_stereo: np.ndarray, num_samples: int) -> None:
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
            return 0 <= channel < len(self.insertion_effects) and self.insertion_effects[channel].set_insertion_effect_type(slot, effect_type)

    def set_channel_insertion_bypass(self, channel: int, slot: int, bypass: bool) -> bool:
        with self.lock:
            return 0 <= channel < len(self.insertion_effects) and self.insertion_effects[channel].set_insertion_effect_bypass(slot, bypass)

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
            sends = {"reverb": self.reverb_sends, "chorus": self.chorus_sends, "variation": self.variation_sends}
            t = sends.get(effect_type)
            if t is None:
                return False
            t[channel] = level
            return True

    def set_system_effect_parameter(self, effect: str, param: str, value: float) -> bool:
        with self.lock:
            return self.system_effects.set_system_effect_parameter(effect, param, value)

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
        "low": lambda eq, v: eq.set_low_gain(v), "low_mid": lambda eq, v: eq.set_low_mid_gain(v),
        "mid": lambda eq, v: eq.set_mid_gain(v), "high_mid": lambda eq, v: eq.set_high_mid_gain(v),
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

    def set_xg_effect_preset(self, preset_name: str) -> bool:
        return False

    def get_processing_status(self) -> dict[str, Any]:
        with self.lock:
            return {"processing_enabled": self.processing_enabled, "master_level": self.master_level, "wet_dry_mix": self.wet_dry_mix, "routing_mode": self.effect_routing_mode, "performance": self.processing_stats.copy(), "buffer_pool": self.buffer_pool.get_memory_stats(), "system_effects": self.system_effects.get_system_effects_status(), "variation_effects": self.variation_effects.get_variation_status(), "effect_units_active": self.effect_units_active.tolist()}

    def reset_all_effects(self) -> None:
        _delay = int(2.0 * self.sample_rate)
        with self.lock:
            self.system_effects = XGSystemEffectsProcessor(self.sample_rate, self.block_size, int(5.0 * self.sample_rate), int(0.05 * self.sample_rate))
            self.variation_effects = XGVariationEffectsProcessor(self.sample_rate, _delay)
            for i in range(len(self.insertion_effects)):
                self.insertion_effects[i] = ProductionXGInsertionEffectsProcessor(self.sample_rate, _delay)
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
            rp, cp = self.system_effects.reverb_processor.params, self.system_effects.chorus_processor.params
            return {"processing_enabled": self.processing_enabled, "master_level": self.master_level, "wet_dry_mix": self.wet_dry_mix, "reverb_params": {"type": rp.get("reverb_type", 1), "level": rp.get("level", 0.0), "time": rp.get("time", 0.5), "hf_damping": rp.get("hf_damping", 0.5), "density": rp.get("density", 0.8)}, "chorus_params": {"type": cp.get("chorus_type", 0), "level": cp.get("level", 0.0), "rate": cp.get("rate", 1.0), "depth": cp.get("depth", 0.5), "feedback": cp.get("feedback", 0.3)}, "variation_params": {"level": 0.0, "type": 0}, "equalizer_params": {"low_gain": 0.0, "mid_gain": 0.0, "high_gain": 0.0}, "effect_units_active": self.effect_units_active.tolist(), "channel_volumes": self.channel_volumes.tolist(), "channel_pans": self.channel_pans.tolist(), "reverb_sends": self.reverb_sends.tolist(), "chorus_sends": self.chorus_sends.tolist(), "variation_sends": self.variation_sends.tolist()}

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

    def _process_vcm_overdrive(self, audio: np.ndarray, params: dict[str, Any] | None = None) -> np.ndarray:
        p = params or {}
        d, t, l = p.get("drive", 0.5), p.get("tone", 0.5), p.get("level", 0.7)
        x = audio * (1.0 + d * 3.0)
        proc = np.where(x > 0, np.tanh(x * 0.7) * 1.2, np.tanh(x * 0.5) * 0.8)
        if t < 0.5:
            proc = self._apply_simple_filter(proc, 1.0 - (0.5 - t) * 2.0, "lowpass")
        return proc * l

    def _process_vcm_distortion(self, audio: np.ndarray, params: dict[str, Any] | None = None) -> np.ndarray:
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

    def _process_vcm_phaser(self, audio: np.ndarray, params: dict[str, Any] | None = None) -> np.ndarray:
        p = params or {}
        r, d, f, l = p.get("rate", 0.5), p.get("depth", 0.6), p.get("feedback", 0.3), p.get("level", 0.8)
        t = np.arange(len(audio)) / self.sample_rate
        ps = np.sin(2 * np.pi * (0.1 + r * 2.0) * t) * d * np.pi
        proc = audio * np.cos(ps) + audio * np.sin(ps) * 0.5
        proc += proc * f
        proc *= l
        m = p.get("mix", 1.0)
        return audio * (1.0 - m) + proc * m

    def _process_vcm_equalizer(self, audio: np.ndarray, params: dict[str, Any] | None = None) -> np.ndarray:
        p = params or {}
        lg, mg, hg, lvl = p.get("low_gain", 0.0), p.get("mid_gain", 0.0), p.get("high_gain", 0.0), p.get("level", 1.0)
        proc = audio.copy()
        if lg:
            proc = self._apply_simple_filter(proc, 0.1, "lowshelf", gain=10 ** (lg / 20.0))
        if hg:
            proc = self._apply_simple_filter(proc, 0.4, "highshelf", gain=10 ** (hg / 20.0))
        if mg:
            proc = self._apply_simple_filter(proc, 0.25, "peaking", gain=10 ** (mg / 20.0))
        return proc * lvl

    def _process_vcm_stereo_enhancer(self, audio: np.ndarray, params: dict[str, Any] | None = None) -> np.ndarray:
        p = params or {}
        w, lvl = p.get("width", 0.5), p.get("level", 1.0)
        if audio.ndim == 1:
            return audio * lvl
        left, right = audio[:, 0].copy(), audio[:, 1].copy()
        m = (left + right) * 0.5
        d = (left - right) * w
        return np.column_stack([m + d, m - d]) * lvl

    def _apply_simple_filter(self, audio: np.ndarray, freq: float, filter_type: str = "lowpass", gain: float = 1.0) -> np.ndarray:
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

    def process_multiband_compression(self, audio: np.ndarray, params: dict[str, Any] | None = None) -> np.ndarray:
        p = params or {}
        lt, mt, ht = p.get("low_threshold", -20.0), p.get("mid_threshold", -20.0), p.get("high_threshold", -20.0)
        lr, mr, hr = p.get("low_ratio", 4.0), p.get("mid_ratio", 4.0), p.get("high_ratio", 4.0)
        lo = self._apply_simple_filter(audio.copy(), 0.2, "lowpass")
        hi = self._apply_simple_filter(audio.copy(), 0.6, "highpass")
        mi = audio - lo - hi
        return self._apply_compression(lo, lt, lr) + self._apply_compression(mi, mt, mr) + self._apply_compression(hi, ht, hr)

    def _apply_compression(self, audio: np.ndarray, threshold_db: float, ratio: float) -> np.ndarray:
        amp = np.abs(audio)
        db = 20 * np.log10(amp + 1e-10)
        cdb = np.where(db > threshold_db, threshold_db + (db - threshold_db) / ratio, db)
        return np.sign(audio) * (10 ** (cdb / 20.0))

    def process_multitap_delay(self, audio: np.ndarray, params: dict[str, Any] | None = None) -> np.ndarray:
        p = params or {}
        tt, tl = p.get("tap_times", [100, 200, 300]), p.get("tap_levels", [0.5, 0.4, 0.3])
        fb, md, mr = p.get("feedback", 0.3), p.get("modulation_depth", 0.0), p.get("modulation_rate", 0.5)
        output = audio.copy()
        needed = len(audio) * 2
        if self._delay_tap_buffer is None or len(self._delay_tap_buffer) < needed:
            self._delay_tap_buffer = np.zeros(needed, dtype=np.float32)
        buf = self._delay_tap_buffer[:needed]
        buf[:len(audio)] = audio
        buf[len(audio):] = 0.0
        for t, l in zip(tt, tl, strict=False):
            s = int(t * self.sample_rate / 1000.0)
            if s < len(buf):
                output += buf[s:s + len(audio)] * l
        if fb:
            output += audio * fb
        if md:
            output *= 1.0 + np.sin(2 * np.pi * mr * np.arange(len(output)) / self.sample_rate) * md
        return output

    def process_spectral_effect(self, audio: np.ndarray, params: dict[str, Any] | None = None) -> np.ndarray:
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

    def process_parallel_chain(self, audio: np.ndarray, chain: list[tuple[str, dict[str, Any]]], mix: float = 0.5) -> np.ndarray:
        wet = audio.copy()
        for name, p in chain:
            wet = self.apply_effect(wet, name, p)
        return audio * (1.0 - mix) + wet * mix

    def get_effects_status(self) -> dict[str, Any]:
        return {
            "system_effects": {"reverb": self.system_effects.get("reverb", {}).get("type", "none"), "chorus": self.system_effects.get("chorus", {}).get("type", "none")},
            "variation_effects": self.variation_effects.get_variation_status(),
            "insertion_effects": len(self.insertion_effects) if hasattr(self, "insertion_effects") else 0,
        }
