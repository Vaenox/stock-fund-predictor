from __future__ import annotations

import numpy as np
import pytest

from app.ml.probability_calibration import (
    apply_probability_calibrator,
    evaluate_probability_calibration,
    expected_calibration_error,
    fit_probability_calibrator,
)


def test_raw_calibrator_preserves_probability() -> None:
    p = np.array([0.1, 0.5, 0.9])
    y = np.array([0, 0, 1])

    calibrator = fit_probability_calibrator("raw", p, y)
    result = apply_probability_calibrator(calibrator, p)

    assert np.allclose(result, p)


def test_sigmoid_calibrator_returns_valid_probabilities() -> None:
    p = np.array([0.01, 0.02, 0.08, 0.2, 0.5, 0.8, 0.95])
    y = np.array([0, 0, 0, 1, 0, 1, 1])

    calibrator = fit_probability_calibrator("sigmoid", p, y)
    result = apply_probability_calibrator(calibrator, p)

    assert np.all((result > 0.0) & (result < 1.0))


def test_isotonic_calibrator_returns_monotone_valid_probabilities() -> None:
    p = np.array([0.01, 0.02, 0.08, 0.2, 0.5, 0.8, 0.95])
    y = np.array([0, 0, 0, 1, 0, 1, 1])

    calibrator = fit_probability_calibrator("isotonic", p, y)
    result = apply_probability_calibrator(calibrator, p)

    assert np.all((result >= 0.0) & (result <= 1.0))
    assert np.all(np.diff(result) >= -1e-12)


def test_calibrator_rejects_one_class_target() -> None:
    with pytest.raises(ValueError, match="both classes"):
        fit_probability_calibrator(
            "sigmoid",
            np.array([0.1, 0.2, 0.3]),
            np.array([0, 0, 0]),
        )


def test_ece_is_zero_for_perfect_binary_probabilities() -> None:
    y = np.array([0, 0, 1, 1])
    p = np.array([0.0, 0.0, 1.0, 1.0])

    assert expected_calibration_error(y, p) == pytest.approx(0.0)


def test_evaluate_probability_calibration_metrics() -> None:
    y = np.array([0, 0, 1, 1])
    p = np.array([0.1, 0.2, 0.8, 0.9])

    result = evaluate_probability_calibration("raw", p, y)

    assert result.method == "raw"
    assert 0.0 <= result.brier <= 1.0
    assert result.log_loss > 0.0
    assert result.pr_auc is not None
