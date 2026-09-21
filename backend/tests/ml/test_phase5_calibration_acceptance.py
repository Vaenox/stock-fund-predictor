from __future__ import annotations

import numpy as np

from app.ml.probability_calibration import (
    apply_probability_calibrator,
    fit_probability_calibrator,
)


def test_phase5_calibration_methods_are_deterministic() -> None:
    p = np.array([0.01, 0.03, 0.08, 0.15, 0.40, 0.70, 0.90])
    y = np.array([0, 0, 0, 1, 0, 1, 1])

    for method in ("raw", "sigmoid", "isotonic"):
        first = fit_probability_calibrator(method, p, y)
        second = fit_probability_calibrator(method, p, y)
        first_values = apply_probability_calibrator(first, p)
        second_values = apply_probability_calibrator(second, p)
        assert np.allclose(first_values, second_values)


def test_phase5_calibration_does_not_change_input_probability() -> None:
    p = np.array([0.05, 0.20, 0.80])
    y = np.array([0, 1, 1])
    original = p.copy()

    calibrator = fit_probability_calibrator("sigmoid", p, y)
    _ = apply_probability_calibrator(calibrator, p)

    assert np.array_equal(p, original)
