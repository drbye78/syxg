from __future__ import annotations

import numpy as np
import pytest

from synth.primitives.fast_approx import FastMath, fast_math


@pytest.mark.unit
class TestFastMath:
    def test_default_table_size(self):
        fm = FastMath()
        assert fm.table_size == 4096

    def test_custom_table_size(self):
        fm = FastMath(1024)
        assert fm.table_size == 1024

    def test_fast_exp_scalar(self):
        fm = FastMath()
        # fast_exp(0.0) should be very close to 1.0 (exp(-0) = 1.0)
        assert fm.fast_exp(0.0) == pytest.approx(1.0, abs=0.1)
        # fast_exp(10.0) should be very close to 0.0 (exp(-10) ≈ 4.5e-5)
        assert fm.fast_exp(10.0) == pytest.approx(0.0, abs=0.1)

    def test_fast_exp_array(self):
        fm = FastMath()
        arr = np.array([0.0, 5.0, 10.0], dtype=np.float32)
        result = fm.fast_exp(arr)
        assert isinstance(result, np.ndarray)
        assert result.shape == arr.shape

    def test_fast_log_scalar(self):
        fm = FastMath()
        # fast_log(1.0) should be close to 0.0 (ln(1) = 0)
        assert fm.fast_log(1.0) == pytest.approx(0.0, abs=0.1)
        # fast_log(10.0) should be close to ~2.3026 (ln(10) ≈ 2.3026)
        assert fm.fast_log(10.0) == pytest.approx(2.302585, abs=0.1)

    def test_fast_log_array(self):
        fm = FastMath()
        arr = np.array([0.5, 1.0, 5.0, 10.0], dtype=np.float32)
        result = fm.fast_log(arr)
        assert isinstance(result, np.ndarray)
        assert result.shape == arr.shape

    def test_fast_pow_scalar(self):
        fm = FastMath()
        # fast_pow(0.5, 0.5) should be close to sqrt(0.5) ≈ 0.7071
        assert fm.fast_pow(0.5, 0.5) == pytest.approx(0.7071068, abs=0.1)

    def test_fast_pow_array(self):
        fm = FastMath()
        arr = np.array([0.0, 0.25, 0.5, 0.75, 1.0], dtype=np.float32)
        result = fm.fast_pow(arr, 0.5)
        assert isinstance(result, np.ndarray)
        assert result.shape == arr.shape

    def test_fast_sin_scalar(self):
        fm = FastMath()
        # fast_sin(0) should be close to 0.0
        assert fm.fast_sin(0.0) == pytest.approx(0.0, abs=0.1)
        # fast_sin(pi/2) should be close to 1.0
        assert fm.fast_sin(np.pi / 2) == pytest.approx(1.0, abs=0.1)

    def test_fast_sin_array(self):
        fm = FastMath()
        arr = np.array([0.0, np.pi / 4, np.pi / 2, np.pi], dtype=np.float32)
        result = fm.fast_sin(arr)
        assert isinstance(result, np.ndarray)
        assert result.shape == arr.shape

    def test_fast_cos_scalar(self):
        fm = FastMath()
        # fast_cos(0) should be close to 1.0
        assert fm.fast_cos(0.0) == pytest.approx(1.0, abs=0.1)
        # fast_cos(pi/2) should be close to 0.0
        assert fm.fast_cos(np.pi / 2) == pytest.approx(0.0, abs=0.1)

    def test_cos_symmetry(self):
        fm = FastMath()
        x = np.array([0.0, 0.5, 1.0, 2.0, np.pi / 2, np.pi], dtype=np.float32)
        cos_vals = fm.fast_cos(x)
        sin_shifted = fm.fast_sin(x + np.pi / 2)
        assert cos_vals == pytest.approx(sin_shifted, abs=0.15)

    def test_global_instance(self):
        assert isinstance(fast_math, FastMath)

    def test_approximation_vs_numpy(self):
        fm = FastMath()
        points = [0.0, 0.5, 1.0, 2.0, 5.0, 8.0]
        for x in points:
            approx = fm.fast_exp(x)
            expected = np.exp(-x)
            assert approx == pytest.approx(expected, abs=0.15)
