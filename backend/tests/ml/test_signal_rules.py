from __future__ import annotations

import pytest

from app.ml.signal_rules import SignalRuleConfig, classify_signal


def test_signal_rules_classify_boundaries() -> None:
    config = SignalRuleConfig(sell_threshold=40.0, buy_threshold=60.0)

    assert classify_signal(0.0, config=config) == "SELL"
    assert classify_signal(40.0, config=config) == "SELL"
    assert classify_signal(40.01, config=config) == "HOLD"
    assert classify_signal(59.99, config=config) == "HOLD"
    assert classify_signal(60.0, config=config) == "BUY"
    assert classify_signal(100.0, config=config) == "BUY"


def test_signal_rules_reject_invalid_threshold_order() -> None:
    with pytest.raises(ValueError, match="sell_threshold must be lower"):
        SignalRuleConfig(sell_threshold=60.0, buy_threshold=60.0)


def test_signal_rules_reject_invalid_score() -> None:
    with pytest.raises(ValueError, match="signal_score must be finite"):
        classify_signal(float("nan"))

    with pytest.raises(ValueError, match="signal_score must be between"):
        classify_signal(100.1)
