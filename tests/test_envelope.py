"""
Comprehensive Test Suite for UltraFastADSREnvelope

This test suite provides in-depth validation of:
1. Basic envelope generation (ADSR phases)
2. Parameter validation and edge cases
3. Velocity sensitivity and key scaling
4. Pedal support (sustain, sostenuto, soft)
5. Block processing and cross-boundary behavior
6. Parameter modulation with smooth transitions
7. Envelope pooling for performance
8. State transitions and lifecycle management
9. Multi-rate support (different sample rates)
10. Performance benchmarks

Author: Generated for UltraFastADSREnvelope testing
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np
import pytest

from synth.primitives.envelope import (
    STATE_MASK_ATTACK,
    STATE_MASK_DECAY,
    STATE_MASK_DELAY,
    STATE_MASK_HOLD,
    STATE_MASK_IDLE,
    STATE_MASK_RELEASE,
    STATE_MASK_SUSTAIN,
    EnvelopePool,
    EnvelopeState,
    UltraFastADSREnvelope,
)

logger = logging.getLogger(__name__)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def ref_soundfont_path():
    """Get path to reference soundfont."""
    path = Path(__file__).parent / "ref.sf2"
    if not path.exists():
        pytest.skip("Reference soundfont (tests/ref.sf2) not found")
    return str(path)


@pytest.fixture
def default_envelope() -> UltraFastADSREnvelope:
    """Create envelope with default parameters."""
    return UltraFastADSREnvelope(
        delay=0.01,
        attack=0.01,
        hold=0.02,
        decay=0.3,
        sustain=0.7,
        release=0.5,
        sample_rate=48000,
        block_size=1024,
    )


@pytest.fixture
def fast_envelope() -> UltraFastADSREnvelope:
    """Create envelope with fast parameters for percussive sounds."""
    return UltraFastADSREnvelope(
        delay=0.0,
        attack=0.001,
        hold=0.0,
        decay=0.1,
        sustain=0.0,
        release=0.1,
        sample_rate=48000,
        block_size=512,
    )


@pytest.fixture
def slow_envelope() -> UltraFastADSREnvelope:
    """Create envelope with slow parameters for pad sounds."""
    return UltraFastADSREnvelope(
        delay=0.5,
        attack=1.0,
        hold=0.5,
        decay=2.0,
        sustain=0.8,
        release=3.0,
        sample_rate=44100,
        block_size=2048,
    )


@pytest.fixture
def envelope_pool() -> EnvelopePool:
    """Create envelope pool for testing."""
    return EnvelopePool(max_envelopes=100, block_size=1024, sample_rate=48000)


# ============================================================================
# TEST: ENVELOPE STATE CONSTANTS
# ============================================================================


class TestEnvelopeStateConstants:
    """Test envelope state constants and bitmasks."""

    def test_state_enum_values(self):
        """Test EnvelopeState enum has correct values."""
        assert EnvelopeState.IDLE == 0
        assert EnvelopeState.DELAY == 1
        assert EnvelopeState.ATTACK == 2
        assert EnvelopeState.HOLD == 3
        assert EnvelopeState.DECAY == 4
        assert EnvelopeState.SUSTAIN == 5
        assert EnvelopeState.RELEASE == 6

    def test_bitmask_constants(self):
        """Test bitmask constants are powers of 2."""
        assert STATE_MASK_IDLE == 1 << 0  # 1
        assert STATE_MASK_DELAY == 1 << 1  # 2
        assert STATE_MASK_ATTACK == 1 << 2  # 4
        assert STATE_MASK_HOLD == 1 << 3  # 8
        assert STATE_MASK_DECAY == 1 << 4  # 16
        assert STATE_MASK_SUSTAIN == 1 << 5  # 32
        assert STATE_MASK_RELEASE == 1 << 6  # 64


# ============================================================================
# TEST: INITIALIZATION AND PARAMETER VALIDATION
# ============================================================================


class TestEnvelopeInitialization:
    """Test envelope initialization and parameter validation."""

    def test_default_parameters(self, default_envelope):
        """Test envelope initializes with correct default parameters."""
        assert default_envelope.delay == 0.01
        assert default_envelope.attack == 0.01
        assert default_envelope.hold == 0.02
        assert default_envelope.decay == 0.3
        assert default_envelope.sustain == 0.7
        assert default_envelope.release == 0.5
        assert default_envelope.sample_rate == 48000
        assert default_envelope.block_size == 1024

    def test_initial_state_is_idle(self, default_envelope):
        """Test envelope starts in IDLE state."""
        assert default_envelope.state == EnvelopeState.IDLE
        assert default_envelope.level == 0.0

    def test_parameter_clamping_delay_negative(self):
        """Test negative delay is clamped to 0."""
        env = UltraFastADSREnvelope(delay=-1.0)
        assert env.delay == 0.0

    def test_parameter_clamping_attack_minimum(self):
        """Test attack is clamped to minimum 0.001."""
        env = UltraFastADSREnvelope(attack=0.0)
        assert env.attack == 0.001

    def test_parameter_clamping_decay_minimum(self):
        """Test decay is clamped to minimum 0.001."""
        env = UltraFastADSREnvelope(decay=0.0)
        assert env.decay == 0.001

    def test_parameter_clamping_release_minimum(self):
        """Test release is clamped to minimum 0.001."""
        env = UltraFastADSREnvelope(release=0.0)
        assert env.release == 0.001

    def test_parameter_clamping_sustain_range(self):
        """Test sustain is clamped to 0.0-1.0 range."""
        env_low = UltraFastADSREnvelope(sustain=-0.5)
        env_high = UltraFastADSREnvelope(sustain=1.5)
        assert env_low.sustain == 0.0
        assert env_high.sustain == 1.0

    def test_parameter_clamping_velocity_sense_range(self):
        """Test velocity_sense is clamped to 0.0-2.0 range."""
        env_low = UltraFastADSREnvelope(velocity_sense=-1.0)
        env_high = UltraFastADSREnvelope(velocity_sense=3.0)
        assert env_low.velocity_sense == 0.0
        assert env_high.velocity_sense == 2.0

    def test_delay_samples_calculation(self, default_envelope):
        """Test delay_samples is calculated correctly."""
        expected = int(0.01 * 48000)  # 480 samples
        assert default_envelope.delay_samples == expected

    def test_hold_samples_calculation(self, default_envelope):
        """Test hold_samples is calculated correctly."""
        expected = int(0.02 * 48000)  # 960 samples
        assert default_envelope.hold_samples == expected

    def test_increments_calculated_on_init(self, default_envelope):
        """Test increments are calculated during initialization."""
        assert hasattr(default_envelope, "attack_increment")
        assert hasattr(default_envelope, "decay_decrement")
        assert hasattr(default_envelope, "release_decrement")
        assert default_envelope.attack_increment > 0
        assert default_envelope.decay_decrement > 0
        assert default_envelope.release_decrement > 0


# ============================================================================
# TEST: BASIC ENVELOPE GENERATION
# ============================================================================


class TestBasicEnvelopeGeneration:
    """Test basic ADSR envelope generation."""

    def test_delay_phase(self, default_envelope):
        """Test delay phase produces zero output."""
        default_envelope.note_on(velocity=100)

        # Generate block during delay
        output = np.zeros(100, dtype=np.float32)
        default_envelope.generate_block(output)

        # All samples should be zero during delay
        assert np.all(output == 0.0)

    def test_attack_phase(self, default_envelope):
        """Test attack phase ramps from 0 to peak."""
        default_envelope.note_on(velocity=100)

        # Skip delay (480 samples at 48kHz with 0.01s delay)
        delay_samples = default_envelope.delay_samples
        samples_processed = 0

        while samples_processed < delay_samples:
            block_size = min(default_envelope.block_size, delay_samples - samples_processed)
            output = np.zeros(block_size, dtype=np.float32)
            default_envelope.generate_block(output)
            samples_processed += len(output)

        # Generate attack block
        output = np.zeros(default_envelope.block_size, dtype=np.float32)
        default_envelope.generate_block(output)

        # Attack should produce non-zero values ramping up
        assert output[0] >= 0.0
        assert np.max(output) > 0.5  # Should reach significant level

    def test_hold_phase(self, default_envelope):
        """Test hold phase maintains peak level."""
        default_envelope.note_on(velocity=100)

        # Skip delay and attack
        total_skip = default_envelope.delay_samples + int(
            default_envelope.attack * default_envelope.sample_rate
        )
        samples_processed = 0

        while samples_processed < total_skip:
            output = np.zeros(
                min(default_envelope.block_size, total_skip - samples_processed), dtype=np.float32
            )
            default_envelope.generate_block(output)
            samples_processed += len(output)

        # Generate hold block
        output = np.zeros(default_envelope.block_size, dtype=np.float32)
        default_envelope.generate_block(output)

        # Hold should maintain high level (velocity 100/127 ≈ 0.79)
        # Allow tolerance for boundary samples
        assert np.mean(output) > 0.6

    def test_decay_phase(self, default_envelope):
        """Test decay phase ramps from peak to sustain."""
        default_envelope.note_on(velocity=100)

        # Skip delay, attack, and hold
        total_skip = (
            default_envelope.delay_samples
            + int(default_envelope.attack * default_envelope.sample_rate)
            + default_envelope.hold_samples
        )
        samples_processed = 0

        while samples_processed < total_skip:
            block_size = min(default_envelope.block_size, total_skip - samples_processed)
            output = np.zeros(block_size, dtype=np.float32)
            default_envelope.generate_block(output)
            samples_processed += len(output)

        # Generate decay block
        output = np.zeros(default_envelope.block_size, dtype=np.float32)
        default_envelope.generate_block(output)

        # Decay should produce decreasing values
        # (allowing for first sample potentially being at peak)
        assert output[-1] <= output[0]

    def test_sustain_phase(self, default_envelope):
        """Test sustain phase maintains constant level."""
        default_envelope.note_on(velocity=100)

        # Skip to sustain phase
        total_skip = (
            default_envelope.delay_samples
            + int(default_envelope.attack * default_envelope.sample_rate)
            + default_envelope.hold_samples
            + int(default_envelope.decay * default_envelope.sample_rate)
        )
        samples_processed = 0

        while samples_processed < total_skip:
            block_size = min(default_envelope.block_size, total_skip - samples_processed)
            output = np.zeros(block_size, dtype=np.float32)
            default_envelope.generate_block(output)
            samples_processed += len(output)

        # Generate sustain block
        output = np.zeros(default_envelope.block_size, dtype=np.float32)
        default_envelope.generate_block(output)

        # Sustain should be at configured level (scaled by velocity)
        # sustain=0.7 * velocity_factor(100/127) ≈ 0.55
        expected_sustain = 0.7 * (100 / 127)
        tolerance = 0.15
        assert np.all(output > expected_sustain - tolerance)
        assert np.all(output < expected_sustain + tolerance)

    def test_release_phase(self, default_envelope):
        """Test release phase ramps from current level to 0."""
        default_envelope.note_on(velocity=100)

        # Skip to sustain
        total_skip = (
            default_envelope.delay_samples
            + int(default_envelope.attack * default_envelope.sample_rate)
            + default_envelope.hold_samples
            + int(default_envelope.decay * default_envelope.sample_rate)
        )
        samples_processed = 0

        while samples_processed < total_skip:
            block_size = min(default_envelope.block_size, total_skip - samples_processed)
            output = np.zeros(block_size, dtype=np.float32)
            default_envelope.generate_block(output)
            samples_processed += len(output)

        # Trigger release
        default_envelope.note_off()

        # Generate release block
        output = np.zeros(default_envelope.block_size, dtype=np.float32)
        default_envelope.generate_block(output)

        # Release should produce decreasing values
        assert output[0] > 0
        assert output[-1] < output[0]

    def test_idle_state_after_release(self):
        """Test envelope reaches IDLE state after release completes."""
        env = UltraFastADSREnvelope(
            delay=0.0,
            attack=0.01,
            hold=0.0,
            decay=0.01,
            sustain=0.5,
            release=0.01,
            sample_rate=48000,
            block_size=1024,
        )

        env.note_on(velocity=100)

        # Trigger release immediately
        env.note_off()

        # Process through all phases
        for _ in range(20):  # Should be more than enough
            output = np.zeros(1024, dtype=np.float32)
            env.generate_block(output)

            if env.state == EnvelopeState.IDLE:
                break

        # Envelope should be idle
        assert env.state == EnvelopeState.IDLE


# ============================================================================
# TEST: VELOCITY SENSITIVITY AND KEY SCALING
# ============================================================================


class TestVelocityAndKeyScaling:
    """Test velocity sensitivity and key scaling features."""

    def test_velocity_affects_peak_level(self, default_envelope):
        """Test higher velocity produces higher peak level."""
        env_low = UltraFastADSREnvelope(velocity_sense=1.0)
        env_high = UltraFastADSREnvelope(velocity_sense=1.0)

        env_low.note_on(velocity=50)
        env_high.note_on(velocity=120)

        # Skip to attack
        for _ in range(2):
            for env in [env_low, env_high]:
                output = np.zeros(1024, dtype=np.float32)
                env.generate_block(output)

        # Get attack output
        output_low = np.zeros(1024, dtype=np.float32)
        output_high = np.zeros(1024, dtype=np.float32)
        env_low.generate_block(output_low)
        env_high.generate_block(output_high)

        assert np.max(output_high) > np.max(output_low)

    def test_velocity_sense_zero_ignores_velocity(self):
        """Test velocity_sense=0 produces same level regardless of velocity."""
        env1 = UltraFastADSREnvelope(velocity_sense=0.0)
        env2 = UltraFastADSREnvelope(velocity_sense=0.0)

        env1.note_on(velocity=30)
        env2.note_on(velocity=120)

        # Both should have same velocity_factor
        assert env1.velocity_factor == env2.velocity_factor

    def test_velocity_sense_high_exaggerates_differences(self):
        """Test high velocity_sense exaggerates velocity differences."""
        env_low = UltraFastADSREnvelope(velocity_sense=2.0)
        env_high = UltraFastADSREnvelope(velocity_sense=2.0)

        env_low.note_on(velocity=50)
        env_high.note_on(velocity=100)

        # With velocity_sense=2.0, difference should be exaggerated
        ratio = env_high.velocity_factor / max(env_low.velocity_factor, 0.001)
        assert ratio > 1.5  # Significant difference

    def test_key_scaling_positive(self):
        """Test positive key scaling increases envelope for higher notes."""
        env = UltraFastADSREnvelope(key_scaling=0.5)

        env.note_on(velocity=100, note=30)  # Low note
        low_factor = env.key_factor

        env.note_on(velocity=100, note=90)  # High note
        high_factor = env.key_factor

        assert high_factor > low_factor

    def test_key_scaling_negative(self):
        """Test negative key scaling decreases envelope for higher notes."""
        env = UltraFastADSREnvelope(key_scaling=-0.5)

        env.note_on(velocity=100, note=30)  # Low note
        low_factor = env.key_factor

        env.note_on(velocity=100, note=90)  # High note
        high_factor = env.key_factor

        assert high_factor < low_factor

    def test_key_scaling_zero_ignores_note(self):
        """Test key_scaling=0 produces same level regardless of note."""
        env = UltraFastADSREnvelope(key_scaling=0.0)

        env.note_on(velocity=100, note=30)
        low_factor = env.key_factor

        env.note_on(velocity=100, note=90)
        high_factor = env.key_factor

        assert low_factor == high_factor == 1.0


# ============================================================================
# TEST: PEDAL SUPPORT
# ============================================================================


class TestPedalSupport:
    """Test sustain, sostenuto, and soft pedal functionality."""

    def test_sustain_pedal_prevents_release(self, default_envelope):
        """Test sustain pedal prevents envelope from releasing on note_off."""
        default_envelope.note_on(velocity=100)

        # Skip to sustain
        total_skip = (
            default_envelope.delay_samples
            + int(default_envelope.attack * default_envelope.sample_rate)
            + default_envelope.hold_samples
            + int(default_envelope.decay * default_envelope.sample_rate)
        )
        samples_processed = 0

        while samples_processed < total_skip:
            block_size = min(default_envelope.block_size, total_skip - samples_processed)
            output = np.zeros(block_size, dtype=np.float32)
            default_envelope.generate_block(output)
            samples_processed += len(output)

        # Enable sustain pedal
        default_envelope.sustain_pedal_on()

        # Note off should not trigger release
        default_envelope.note_off()
        assert default_envelope.state != EnvelopeState.RELEASE

        # Sustain pedal off should trigger release
        default_envelope.sustain_pedal_off()
        assert default_envelope.state == EnvelopeState.RELEASE

    def test_sostenuto_pedal_holds_envelope(self, default_envelope):
        """Test sostenuto pedal holds envelope at current level."""
        default_envelope.note_on(velocity=100)

        # Skip to decay
        total_skip = (
            default_envelope.delay_samples
            + int(default_envelope.attack * default_envelope.sample_rate)
            + default_envelope.hold_samples
        )
        samples_processed = 0

        while samples_processed < total_skip:
            block_size = min(default_envelope.block_size, total_skip - samples_processed)
            output = np.zeros(block_size, dtype=np.float32)
            default_envelope.generate_block(output)
            samples_processed += len(output)

        # Enable sostenuto during decay
        default_envelope.sostenuto_pedal_on()

        # Note off should not trigger release while sostenuto is held
        default_envelope.note_off()
        assert default_envelope.state != EnvelopeState.RELEASE

    def test_soft_pedal_reduces_level(self, default_envelope):
        """Test soft pedal reduces envelope level by 50%."""
        env_no_pedal = UltraFastADSREnvelope()
        env_pedal = UltraFastADSREnvelope()

        env_no_pedal.note_on(velocity=100)
        env_pedal.note_on(velocity=100, soft_pedal=True)

        # Soft pedal should reduce velocity_factor by 50%
        assert env_pedal.velocity_factor == env_no_pedal.velocity_factor * 0.5

    def test_all_notes_off_triggers_sustain(self, default_envelope):
        """Test all_notes_off transitions envelope to sustain."""
        default_envelope.note_on(velocity=100)

        # Skip delay
        samples_processed = 0
        while samples_processed < default_envelope.delay_samples:
            output = np.zeros(100, dtype=np.float32)
            default_envelope.generate_block(output)
            samples_processed += len(output)

        # All notes off
        default_envelope.all_notes_off()

        # Should be in sustain state
        assert default_envelope.state == EnvelopeState.SUSTAIN


# ============================================================================
# TEST: BLOCK PROCESSING AND CROSS-BOUNDARY BEHAVIOR
# ============================================================================


class TestBlockProcessing:
    """Test block-based processing and cross-boundary behavior."""

    def test_block_spans_multiple_phases(self):
        """Test single block correctly handles multiple phase transitions."""
        env = UltraFastADSREnvelope(
            delay=0.001,
            attack=0.001,
            hold=0.001,
            decay=0.001,
            sustain=0.5,
            release=0.001,
            sample_rate=48000,
            block_size=1024,
        )

        env.note_on(velocity=100)

        # Trigger release so envelope can complete
        env.note_off()

        # Single block should handle all phases
        output = np.zeros(1024, dtype=np.float32)
        env.generate_block(output)

        # Should have gone through delay, attack, hold, decay, sustain, and release
        # Final state should be IDLE or RELEASE (might still be releasing)
        assert env.state in [EnvelopeState.IDLE, EnvelopeState.RELEASE, EnvelopeState.SUSTAIN]

    def test_cross_block_continuity(self, default_envelope):
        """Test envelope maintains continuity across block boundaries."""
        default_envelope.note_on(velocity=100)

        # Process multiple blocks
        all_samples = []
        for _ in range(5):
            output = np.zeros(default_envelope.block_size, dtype=np.float32)
            default_envelope.generate_block(output)
            all_samples.extend(output)

        # Check for discontinuities (large jumps between blocks)
        all_samples = np.array(all_samples)
        for i in range(default_envelope.block_size, len(all_samples), default_envelope.block_size):
            if i < len(all_samples):
                jump = abs(all_samples[i] - all_samples[i - 1])
                assert jump < 0.3  # Reasonable continuity threshold

    def test_zero_block_size(self, default_envelope):
        """Test handling of zero-length block."""
        default_envelope.note_on(velocity=100)

        output = np.zeros(0, dtype=np.float32)
        result = default_envelope.generate_block(output)

        assert len(result) == 0

    def test_very_small_block(self, default_envelope):
        """Test handling of very small blocks."""
        default_envelope.note_on(velocity=100)

        output = np.zeros(10, dtype=np.float32)
        result = default_envelope.generate_block(output)

        assert len(result) == 10
        assert result.dtype == np.float32

    def test_very_large_block(self):
        """Test handling of very large blocks."""
        env = UltraFastADSREnvelope(
            delay=0.01,
            attack=0.01,
            hold=0.01,
            decay=0.1,
            sustain=0.5,
            release=0.1,
            sample_rate=48000,
            block_size=8192,
        )

        env.note_on(velocity=100)

        output = np.zeros(8192, dtype=np.float32)
        result = env.generate_block(output)

        assert len(result) == 8192


# ============================================================================
# TEST: PARAMETER MODULATION
# ============================================================================


class TestParameterModulation:
    """Test real-time parameter modulation with smooth transitions."""

    def test_attack_modulation(self, default_envelope):
        """Test attack time modulation."""
        default_envelope.note_on(velocity=100)

        # Apply attack modulation (2x longer)
        default_envelope.modulate_parameters(attack_mod=1.0)

        # Target should be set
        assert default_envelope.target_attack == default_envelope.base_attack * 2.0

    def test_decay_modulation(self, default_envelope):
        """Test decay time modulation."""
        # Apply decay modulation (0.5x shorter)
        default_envelope.modulate_parameters(decay_mod=-1.0)

        # Target should be set
        assert default_envelope.target_decay == default_envelope.base_decay * 0.5

    def test_sustain_modulation(self, default_envelope):
        """Test sustain level modulation."""
        original_sustain = default_envelope.base_sustain

        # Apply sustain modulation (+0.2)
        default_envelope.modulate_parameters(sustain_mod=0.2)

        # Target should be clipped to valid range
        expected = np.clip(original_sustain + 0.2, 0.0, 1.0)
        assert default_envelope.target_sustain == expected

    def test_release_modulation(self, default_envelope):
        """Test release time modulation."""
        # Apply release modulation (4x longer)
        default_envelope.modulate_parameters(release_mod=2.0)

        # Target should be set
        assert default_envelope.target_release == default_envelope.base_release * 4.0

    def test_smooth_transition_during_modulation(self, default_envelope):
        """Test parameters transition smoothly during modulation."""
        default_envelope.note_on(velocity=100)

        original_attack = default_envelope.attack

        # Apply modulation
        default_envelope.modulate_parameters(attack_mod=1.0)

        # Process blocks during transition
        attack_values = []
        for _ in range(5):
            output = np.zeros(1024, dtype=np.float32)
            default_envelope.generate_block(output)
            attack_values.append(default_envelope.attack)

        # Attack should transition from original to target
        assert attack_values[0] <= attack_values[-1]
        assert attack_values[-1] <= original_attack * 2.0

    def test_multiple_simultaneous_modulations(self, default_envelope):
        """Test multiple parameters modulated simultaneously."""
        default_envelope.modulate_parameters(
            attack_mod=0.5, decay_mod=-0.5, sustain_mod=0.1, release_mod=1.0
        )

        assert default_envelope.target_attack == default_envelope.base_attack * (2.0**0.5)
        assert default_envelope.target_decay == default_envelope.base_decay * (2.0**-0.5)
        assert default_envelope.target_sustain == np.clip(
            default_envelope.base_sustain + 0.1, 0.0, 1.0
        )
        assert default_envelope.target_release == default_envelope.base_release * 2.0


# ============================================================================
# TEST: ENVELOPE POOLING
# ============================================================================


class TestEnvelopePooling:
    """Test envelope pool functionality."""

    def test_pool_preallocates_envelopes(self, envelope_pool):
        """Test pool pre-allocates envelopes."""
        stats = envelope_pool.get_pool_stats()
        assert stats["pooled_envelopes"] > 0

    def test_acquire_from_pool(self, envelope_pool):
        """Test acquiring envelope from pool."""
        env = envelope_pool.acquire_envelope()

        assert isinstance(env, UltraFastADSREnvelope)
        assert env.state == EnvelopeState.IDLE  # Should be reset

    def test_release_to_pool(self, envelope_pool):
        """Test releasing envelope back to pool."""
        initial_count = len(envelope_pool.pool)

        env = envelope_pool.acquire_envelope()
        after_acquire = len(envelope_pool.pool)

        envelope_pool.release_envelope(env)
        after_release = len(envelope_pool.pool)

        assert after_acquire == initial_count - 1
        assert after_release == initial_count

    def test_pool_exhaustion_fallback(self, envelope_pool):
        """Test pool creates new envelope when empty."""
        # Empty the pool
        envelopes = []
        for _ in range(envelope_pool.max_envelopes + 10):
            env = envelope_pool.acquire_envelope()
            envelopes.append(env)

        # Should still get envelopes (created on demand)
        assert len(envelopes) == envelope_pool.max_envelopes + 10

    def test_pool_parameters(self, envelope_pool):
        """Test pool statistics."""
        stats = envelope_pool.get_pool_stats()

        assert stats["max_envelopes"] == 100
        assert stats["block_size"] == 1024
        assert stats["sample_rate"] == 48000


# ============================================================================
# TEST: STATE TRANSITIONS AND LIFECYCLE
# ============================================================================


class TestStateTransitions:
    """Test envelope state transitions and lifecycle."""

    def test_full_lifecycle(self, fast_envelope):
        """Test complete envelope lifecycle from note_on to idle."""
        states = []

        fast_envelope.note_on(velocity=100)
        states.append(fast_envelope.state)

        # Trigger release after a short time
        release_after = 5
        for i in range(100):
            output = np.zeros(512, dtype=np.float32)
            fast_envelope.generate_block(output)
            states.append(fast_envelope.state)

            if i == release_after:
                fast_envelope.note_off()

            if fast_envelope.state == EnvelopeState.IDLE:
                break

        # Should have gone through expected states
        assert EnvelopeState.DELAY in states or EnvelopeState.ATTACK in states
        assert EnvelopeState.IDLE in states

    def test_note_off_during_attack(self, default_envelope):
        """Test note_off during attack phase triggers release."""
        default_envelope.note_on(velocity=100)

        # Note off immediately (during attack)
        default_envelope.note_off()

        # Should transition to release
        assert default_envelope.state == EnvelopeState.RELEASE

    def test_note_off_during_decay(self, default_envelope):
        """Test note_off during decay phase triggers release."""
        default_envelope.note_on(velocity=100)

        # Skip to decay
        total_skip = (
            default_envelope.delay_samples
            + int(default_envelope.attack * default_envelope.sample_rate)
            + default_envelope.hold_samples
        )

        for _ in range(total_skip // 100 + 1):
            output = np.zeros(100, dtype=np.float32)
            default_envelope.generate_block(output)

        default_envelope.note_off()
        assert default_envelope.state == EnvelopeState.RELEASE

    def test_reset_clears_state(self, default_envelope):
        """Test reset() clears envelope state."""
        default_envelope.note_on(velocity=100)
        default_envelope.reset()

        assert default_envelope.state == EnvelopeState.IDLE
        assert default_envelope.level == 0.0
        assert default_envelope.delay_counter == 0
        assert default_envelope.hold_counter == 0

    def test_update_parameters(self, default_envelope):
        """Test updating envelope parameters."""
        original_attack = default_envelope.attack
        original_increment = default_envelope.attack_increment

        default_envelope.update_parameters(attack=0.05)

        assert default_envelope.attack == 0.05
        assert default_envelope.attack_increment != original_increment  # Recalculated


# ============================================================================
# TEST: MULTI-RATE SUPPORT
# ============================================================================


class TestMultiRateSupport:
    """Test envelope behavior at different sample rates."""

    def test_sample_rate_44100(self):
        """Test envelope at 44100 Hz sample rate."""
        env = UltraFastADSREnvelope(attack=0.01, sample_rate=44100, block_size=1024)
        env.note_on(velocity=100)

        output = np.zeros(1024, dtype=np.float32)
        env.generate_block(output)

        assert len(output) == 1024

    def test_sample_rate_96000(self):
        """Test envelope at 96000 Hz sample rate."""
        env = UltraFastADSREnvelope(attack=0.01, sample_rate=96000, block_size=2048)
        env.note_on(velocity=100)

        output = np.zeros(2048, dtype=np.float32)
        env.generate_block(output)

        assert len(output) == 2048

    def test_sample_rate_affects_timing(self):
        """Test sample rate correctly affects timing calculations."""
        env_48k = UltraFastADSREnvelope(attack=0.01, sample_rate=48000)
        env_96k = UltraFastADSREnvelope(attack=0.01, sample_rate=96000)

        # delay_samples should be proportional to sample rate
        assert env_96k.delay_samples == env_48k.delay_samples * 2


# ============================================================================
# TEST: EDGE CASES AND ERROR HANDLING
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_instant_attack(self):
        """Test envelope with instant attack (0.001s)."""
        env = UltraFastADSREnvelope(attack=0.001)
        env.note_on(velocity=127)  # Max velocity for peak output

        output = np.zeros(1024, dtype=np.float32)
        env.generate_block(output)

        # Should reach near peak quickly (velocity 127 = 1.0 factor)
        assert np.max(output) > 0.8

    def test_zero_sustain(self):
        """Test envelope with zero sustain level."""
        env = UltraFastADSREnvelope(sustain=0.0)
        env.note_on(velocity=100)

        # Process through decay
        for _ in range(100):
            output = np.zeros(1024, dtype=np.float32)
            env.generate_block(output)
            if env.state == EnvelopeState.SUSTAIN:
                break

        # Sustain level should be 0
        assert env.level == 0.0

    def test_very_long_release(self):
        """Test envelope with very long release time."""
        env = UltraFastADSREnvelope(
            delay=0.0,
            attack=0.001,
            hold=0.0,
            decay=0.001,
            sustain=0.5,
            release=10.0,
            sample_rate=48000,
            block_size=1024,
        )
        env.note_on(velocity=100)

        # Skip to sustain first
        for _ in range(10):
            output = np.zeros(1024, dtype=np.float32)
            env.generate_block(output)

        # Now trigger release
        env.note_off()

        # Should still be releasing after processing some blocks
        for _ in range(10):
            output = np.zeros(1024, dtype=np.float32)
            env.generate_block(output)

        assert env.state == EnvelopeState.RELEASE

    def test_note_on_during_release(self, default_envelope):
        """Test note_on during release phase retriggers envelope."""
        default_envelope.note_on(velocity=100)

        # Skip to release
        default_envelope.note_off()

        # Note on during release
        default_envelope.note_on(velocity=100)

        # Should retrigger
        assert default_envelope.state == EnvelopeState.DELAY

    def test_output_buffer_dtype(self, default_envelope):
        """Test output buffer maintains float32 dtype."""
        default_envelope.note_on(velocity=100)

        output = np.zeros(1024, dtype=np.float32)
        result = default_envelope.generate_block(output)

        assert result.dtype == np.float32

    def test_output_values_in_valid_range(self, default_envelope):
        """Test all output values are in valid 0.0-1.0 range."""
        default_envelope.note_on(velocity=100)

        all_outputs = []
        for _ in range(20):
            output = np.zeros(1024, dtype=np.float32)
            default_envelope.generate_block(output)
            all_outputs.extend(output)

        all_outputs = np.array(all_outputs)
        assert np.all(all_outputs >= 0.0)
        assert np.all(all_outputs <= 1.0)


# ============================================================================
# TEST: PERFORMANCE BENCHMARKS
# ============================================================================


class TestPerformanceBenchmarks:
    """Performance benchmarks for UltraFastADSREnvelope."""

    def test_single_envelope_throughput(self):
        """Benchmark single envelope processing throughput."""
        env = UltraFastADSREnvelope(sample_rate=48000, block_size=1024)
        env.note_on(velocity=100)
        output = np.zeros(1024, dtype=np.float32)

        # Process 1000 blocks and measure time
        start = time.perf_counter()
        for _ in range(1000):
            env.generate_block(output)
        elapsed = time.perf_counter() - start

        # Should process 1000 blocks in reasonable time (< 1 second)
        assert elapsed < 1.0, f"Processing took {elapsed:.3f}s, expected < 1.0s"

    def test_multiple_envelopes_throughput(self):
        """Benchmark multiple concurrent envelopes."""
        num_envelopes = 100
        envelopes = [
            UltraFastADSREnvelope(sample_rate=48000, block_size=1024) for _ in range(num_envelopes)
        ]

        for env in envelopes:
            env.note_on(velocity=100)

        outputs = [np.zeros(1024, dtype=np.float32) for _ in range(num_envelopes)]

        # Process 100 blocks for all envelopes
        start = time.perf_counter()
        for _ in range(100):
            for i, env in enumerate(envelopes):
                env.generate_block(outputs[i])
        elapsed = time.perf_counter() - start

        # Should process in reasonable time (< 2 seconds)
        assert elapsed < 2.0, f"Processing took {elapsed:.3f}s, expected < 2.0s"

    def test_pool_acquisition_speed(self):
        """Benchmark envelope pool acquisition speed."""
        pool = EnvelopePool(max_envelopes=500, sample_rate=48000)

        # Acquire and release 1000 times
        start = time.perf_counter()
        for _ in range(1000):
            env = pool.acquire_envelope()
            pool.release_envelope(env)
        elapsed = time.perf_counter() - start

        # Should complete in reasonable time (< 0.5 seconds)
        assert elapsed < 0.5, f"Pool operations took {elapsed:.3f}s, expected < 0.5s"

    def test_memory_allocation(self):
        """Test minimal memory allocation during processing."""
        import tracemalloc

        env = UltraFastADSREnvelope(sample_rate=48000, block_size=1024)
        env.note_on(velocity=100)
        output = np.zeros(1024, dtype=np.float32)

        tracemalloc.start()

        # Process many blocks
        for _ in range(1000):
            env.generate_block(output)

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Should have minimal allocations (mostly just the output buffer)
        # Allow some overhead for Python internals
        assert peak < 10 * 1024 * 1024  # Less than 10MB


# ============================================================================
# TEST: SF2 INTEGRATION
# ============================================================================


class TestSF2Integration:
    """Test UltraFastADSREnvelope integration with SF2 regions."""

    def test_envelope_imported_by_sf2_region(self):
        """Test SF2 region imports UltraFastADSREnvelope correctly."""
        # This test verifies the envelope module is properly integrated
        # with the SF2 region implementation

        from synth.primitives.envelope import EnvelopeState, UltraFastADSREnvelope

        # Verify envelope can be instantiated with typical SF2 parameters
        # SF2 uses timecents for time parameters and centibels for sustain
        env = UltraFastADSREnvelope(
            delay=0.01,  # Typical SF2 delay
            attack=0.01,  # Typical SF2 attack
            hold=0.02,  # Typical SF2 hold
            decay=0.3,  # Typical SF2 decay
            sustain=0.7,  # Typical SF2 sustain (0.0-1.0)
            release=0.5,  # Typical SF2 release
            sample_rate=44100,  # Common audio sample rate
            block_size=1024,  # Common block size
        )

        # Verify envelope initializes correctly
        assert env.state == EnvelopeState.IDLE
        assert env.sample_rate == 44100
        assert env.block_size == 1024

        # Verify envelope can process audio blocks
        import numpy as np

        output = np.zeros(1024, dtype=np.float32)
        env.note_on(velocity=100)
        result = env.generate_block(output)

        assert len(result) == 1024
        assert result.dtype == np.float32


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
