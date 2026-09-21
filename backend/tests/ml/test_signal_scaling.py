from __future__ import annotations

import pytest

from app.ml.signal_scaling import (
    SignalScaleConfig,
    calculate_scaled_signal_base,
    derive_signal_scale_config,
    calculate_percentile_scaled_signal_base,
)


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
    assert ml_scaled == pytest.approx(37.5)
    assert tech_scaled == pytest.approx(37.5)
    assert base == pytest.approx(37.5)


def test_signal_scaling_rejects_invalid_bounds() -> None:
    with pytest.raises(ValueError, match="ml probability bounds"):
        SignalScaleConfig(ml_floor=0.5, ml_ceiling=0.5)


def test_signal_scaling_rejects_invalid_probability() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        calculate_scaled_signal_base(1.2, 50.0)


def test_signal_scaling_derives_bounds_from_quantiles() -> None:
    config = derive_signal_scale_config(
        [0.01, 0.02, 0.03, 0.04, 0.05],
        [40.0, 50.0, 60.0, 70.0, 80.0],
        lower_quantile=0.0,
        upper_quantile=1.0,
    )
    assert config.ml_floor == pytest.approx(0.01)
    assert config.ml_ceiling == pytest.approx(0.05)
    assert config.technical_floor == pytest.approx(40.0)
    assert config.technical_ceiling == pytest.approx(80.0)


def test_signal_scaling_derivation_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="quantile bounds"):
        derive_signal_scale_config([0.1, 0.2], [50.0, 60.0], lower_quantile=0.8, upper_quantile=0.2)

    with pytest.raises(ValueError, match="cannot be empty"):
        derive_signal_scale_config([], [])

    with pytest.raises(ValueError, match="equal length"):
        derive_signal_scale_config([0.1], [50.0, 60.0])


def test_signal_scaling_derivation_rejects_constant_component() -> None:
    with pytest.raises(ValueError, match="ml probability bounds"):
        derive_signal_scale_config(
            [0.1, 0.1, 0.1],
            [40.0, 50.0, 60.0],
            lower_quantile=0.0,
            upper_quantile=1.0,
        )



def test_percentile_scaling_maps_reference_extremes() -> None:
    ml_scaled, tech_scaled, base = calculate_percentile_scaled_signal_base(
        0.01,
        40.0,
        [0.01, 0.02, 0.03, 0.04, 0.05],
        [40.0, 50.0, 60.0, 70.0, 80.0],
    )
    assert ml_scaled == pytest.approx(0.0)
    assert tech_scaled == pytest.approx(0.0)
    assert base == pytest.approx(0.0)

    ml_scaled, tech_scaled, base = calculate_percentile_scaled_signal_base(
        0.05,
        80.0,
        [0.01, 0.02, 0.03, 0.04, 0.05],
        [40.0, 50.0, 60.0, 70.0, 80.0],
    )
    assert ml_scaled == pytest.approx(100.0)
    assert tech_scaled == pytest.approx(100.0)
    assert base == pytest.approx(100.0)


def test_percentile_scaling_handles_ties() -> None:
    ml_scaled, tech_scaled, base = calculate_percentile_scaled_signal_base(
        0.02,
        60.0,
        [0.01, 0.02, 0.02, 0.03],
        [40.0, 60.0, 60.0, 80.0],
    )
    assert ml_scaled == pytest.approx(50.0)
    assert tech_scaled == pytest.approx(50.0)
    assert base == pytest.approx(50.0)


def test_percentile_scaling_rejects_invalid_reference_inputs() -> None:
    with pytest.raises(ValueError, match="at least two observations"):
        calculate_percentile_scaled_signal_base(
            0.1, 50.0, [0.1], [50.0, 60.0]
        )

    with pytest.raises(ValueError, match="finite"):
        calculate_percentile_scaled_signal_base(
            0.1, 50.0, [0.1, float("nan")], [50.0, 60.0]
        )

    with pytest.raises(ValueError, match="one-dimensional"):
        calculate_percentile_scaled_signal_base(
            0.1, 50.0, [[0.1, 0.2]], [50.0, 60.0]
        )
