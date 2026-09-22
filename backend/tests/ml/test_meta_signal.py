from __future__ import annotations

import pandas as pd
import pytest

from app.ml.meta_signal import (
    META_FEATURE_COLUMNS,
    SignalMetaConfig,
    build_signal_meta_model,
    predict_signal_meta_probability,
)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "ml_probability": [0.05, 0.10, 0.30, 0.70, 0.90, 0.95],
            "technical_score": [20.0, 30.0, 40.0, 60.0, 80.0, 90.0],
            "risk_adjustment": [-15.0, -10.0, -8.0, -4.0, -2.0, 0.0],
            "target": [0, 0, 0, 1, 1, 1],
        }
    )


def test_meta_model_predicts_deterministically_in_probability_range() -> None:
    frame = _frame()
    model_1 = build_signal_meta_model(frame)
    model_2 = build_signal_meta_model(frame)

    prediction_1 = predict_signal_meta_probability(model_1, frame)
    prediction_2 = predict_signal_meta_probability(model_2, frame)

    assert prediction_1.shape == (len(frame),)
    assert (prediction_1 >= 0.0).all()
    assert (prediction_1 <= 1.0).all()
    assert prediction_1.tolist() == pytest.approx(prediction_2.tolist())


def test_meta_model_requires_both_target_classes() -> None:
    frame = _frame().assign(target=1)
    with pytest.raises(ValueError, match="both classes"):
        build_signal_meta_model(frame)


def test_meta_model_rejects_missing_features() -> None:
    frame = _frame().drop(columns=["technical_score"])
    with pytest.raises(ValueError, match="missing required meta-signal columns"):
        build_signal_meta_model(frame)


def test_meta_model_rejects_missing_prediction_features() -> None:
    model = build_signal_meta_model(_frame())
    frame = _frame().drop(columns=["risk_adjustment"])
    with pytest.raises(ValueError, match="missing required meta-signal features"):
        predict_signal_meta_probability(model, frame)


def test_meta_model_config_validates() -> None:
    with pytest.raises(ValueError, match="C must be positive"):
        SignalMetaConfig(C=0)

    with pytest.raises(ValueError, match="max_iter must be positive"):
        SignalMetaConfig(max_iter=0)


def test_meta_feature_contract_is_explicit() -> None:
    assert META_FEATURE_COLUMNS == (
        "ml_probability",
        "technical_score",
        "risk_adjustment",
    )
