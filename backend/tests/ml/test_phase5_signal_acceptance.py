from __future__ import annotations

import pandas as pd

from app.ml.signal_rules import SignalRuleConfig, classify_signal
from app.ml.signal_validation import evaluate_signal_thresholds


def test_phase5_signal_rules_are_deterministic() -> None:
    config = SignalRuleConfig(sell_threshold=40.0, buy_threshold=60.0)
    scores = [0.0, 40.0, 40.1, 59.9, 60.0, 100.0]

    assert [classify_signal(score, config=config) for score in scores] == [
        "SELL",
        "SELL",
        "HOLD",
        "HOLD",
        "BUY",
        "BUY",
    ]


def test_phase5_threshold_validation_is_descriptive_not_leaky() -> None:
    frame = pd.DataFrame(
        {
            "signal_score": [20.0, 50.0, 80.0],
            "target": [0, 0, 1],
            "forward_return_5d": [-0.03, 0.01, 0.04],
        }
    )
    candidates = (
        SignalRuleConfig(sell_threshold=30.0, buy_threshold=70.0),
        SignalRuleConfig(sell_threshold=40.0, buy_threshold=60.0),
    )

    results = evaluate_signal_thresholds(frame, candidates)

    assert len(results) == len(candidates)
    assert [(row.sell_threshold, row.buy_threshold) for row in results] == [
        (30.0, 70.0),
        (40.0, 60.0),
    ]
