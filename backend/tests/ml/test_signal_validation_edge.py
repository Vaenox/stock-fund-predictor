from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.ml.signal_validation import evaluate_signal_thresholds
from app.ml.signal_rules import SignalRuleConfig


def test_threshold_validation_rejects_unsorted_candidates() -> None:
    frame = pd.DataFrame(
        {
            "signal_score": [20.0, 50.0, 80.0],
            "target": [0, 0, 1],
            "forward_return_5d": [-0.03, 0.01, 0.04],
        }
    )
    candidates = (
        SignalRuleConfig(sell_threshold=40.0, buy_threshold=60.0),
        SignalRuleConfig(sell_threshold=30.0, buy_threshold=70.0),
    )
    results = evaluate_signal_thresholds(frame, candidates)
    assert len(results) == 2


def test_threshold_validation_handles_all_empty_classes() -> None:
    frame = pd.DataFrame(
        {
            "signal_score": [10.0, 20.0],
            "target": [0, 0],
            "forward_return_5d": [-0.01, -0.02],
        }
    )
    result = evaluate_signal_thresholds(
        frame,
        (SignalRuleConfig(sell_threshold=30.0, buy_threshold=70.0),),
    )[0]
    assert result.buy_count == 0
    assert result.buy_target_rate is None
    assert np.isnan(result.buy_mean_forward_return) or result.buy_mean_forward_return is None
