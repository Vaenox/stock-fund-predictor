from __future__ import annotations

import pandas as pd
import pytest

from app.ml.signal_rules import SignalRuleConfig
from app.ml.signal_validation import (
    evaluate_signal_score_association,
    evaluate_signal_score_bins,
    evaluate_signal_thresholds,
)


def test_threshold_validation_reports_each_class_without_selecting_winner() -> None:
    frame = pd.DataFrame(
        {
            "signal_score": [20.0, 35.0, 45.0, 55.0, 65.0, 80.0],
            "target": [0, 0, 0, 1, 1, 1],
            "forward_return_5d": [-0.02, 0.01, 0.00, 0.04, 0.05, 0.07],
        }
    )
    candidates = (
        SignalRuleConfig(sell_threshold=30.0, buy_threshold=70.0),
        SignalRuleConfig(sell_threshold=40.0, buy_threshold=60.0),
    )

    results = evaluate_signal_thresholds(frame, candidates)

    assert len(results) == 2
    assert results[0].sell_threshold == 30.0
    assert results[0].buy_threshold == 70.0
    assert results[0].buy_count == 1
    assert results[0].sell_count == 1
    assert results[0].hold_count == 4
    assert results[0].buy_target_rate == pytest.approx(1.0)
    assert results[0].sell_target_rate == pytest.approx(0.0)


def test_threshold_validation_preserves_candidate_order() -> None:
    frame = pd.DataFrame(
        {
            "signal_score": [10.0, 90.0],
            "target": [0, 1],
            "forward_return_5d": [-0.01, 0.05],
        }
    )
    first = SignalRuleConfig(sell_threshold=20.0, buy_threshold=80.0)
    second = SignalRuleConfig(sell_threshold=30.0, buy_threshold=70.0)

    results = evaluate_signal_thresholds(frame, (first, second))

    assert results[0].sell_threshold == first.sell_threshold
    assert results[0].buy_threshold == first.buy_threshold
    assert results[1].sell_threshold == second.sell_threshold
    assert results[1].buy_threshold == second.buy_threshold


def test_threshold_validation_rejects_missing_data() -> None:
    frame = pd.DataFrame({"signal_score": [50.0], "target": [1]})

    with pytest.raises(ValueError, match="missing required validation columns"):
        evaluate_signal_thresholds(frame, (SignalRuleConfig(),))



def test_signal_score_bins_are_ascending_and_descriptive() -> None:
    frame = pd.DataFrame(
        {
            "signal_score": [10.0, 20.0, 30.0, 40.0, 50.0],
            "target": [0, 0, 1, 1, 1],
            "forward_return_5d": [-0.02, 0.00, 0.01, 0.04, 0.06],
        }
    )
    results = evaluate_signal_score_bins(frame, n_bins=5)

    assert len(results) == 5
    assert results[0].upper_score <= results[1].lower_score
    assert results[0].target_rate == pytest.approx(0.0)
    assert results[-1].target_rate == pytest.approx(1.0)
    assert results[-1].mean_forward_return == pytest.approx(0.06)


def test_signal_score_bins_handle_repeated_scores() -> None:
    frame = pd.DataFrame(
        {
            "signal_score": [10.0, 10.0, 10.0, 20.0, 20.0, 30.0],
            "target": [0, 1, 0, 0, 1, 1],
            "forward_return_5d": [0.0, 0.01, -0.01, 0.02, 0.03, 0.05],
        }
    )
    results = evaluate_signal_score_bins(frame, n_bins=3)

    assert len(results) == 3
    assert sum(item.count for item in results) == len(frame)


def test_signal_score_association_reports_spearman_relationships() -> None:
    frame = pd.DataFrame(
        {
            "signal_score": [10.0, 20.0, 30.0, 40.0],
            "target": [0, 0, 1, 1],
            "forward_return_5d": [-0.02, 0.00, 0.03, 0.05],
        }
    )
    target_corr, return_corr = evaluate_signal_score_association(frame)

    assert target_corr == pytest.approx(1.0)
    assert return_corr == pytest.approx(1.0)


def test_signal_score_bins_reject_invalid_bin_count() -> None:
    frame = pd.DataFrame(
        {
            "signal_score": [10.0],
            "target": [0],
            "forward_return_5d": [0.01],
        }
    )
    with pytest.raises(ValueError, match="positive"):
        evaluate_signal_score_bins(frame, n_bins=0)
