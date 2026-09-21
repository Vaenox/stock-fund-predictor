from __future__ import annotations

import pytest

from app.ml.signal_scaling import SignalScaleConfig, calculate_scaled_signal_base


def test_signal_scaling_maps_configured_bounds_to_zero_and_hundred() -> None:
    ml_scaled, tech_scaled, base = calculate_scaled_signal_base(
        0.02,
        30.0,
    )
    assert ml_scaled == pytest.approx(0.0)
    assert tech_scaled == pytest.approx(0.0)
    assert base == pytest.approx(0.0)

    ml_scaled, tech_scaled, base = calculate_scaled_signal_base(
        0.50,
        85.0,
    )
    assert ml_scaled == pytest.approx(100.0)
    assert tech_scaled == pytest.approx(100.0)
    assert base == pytest.approx(100.0)


def test_signal_scaling_preserves_weighted_combination() -> None:
    ml_scaled, tech_scaled, base = calculate_scaled_signal_base(
        0.26,
        57.5,
    )
    assert ml_scaled == pytest.approx(50.0)
    assert tech_scaled == pytest.approx(50.0)
    assert base == pytest.approx(50.0)


def test_signal_scaling_rejects_invalid_bounds() -> None:
    with pytest.raises(ValueError, match="ml probability bounds"):
        SignalScaleConfig(ml_floor=0.5, ml_ceiling=0.5)


def test_signal_scaling_rejects_invalid_probability() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        calculate_scaled_signal_base(1.2, 50.0)
