from __future__ import annotations

import pandas as pd
import pytest

from app.backtesting.engine import BacktestConfig
from app.backtesting.strategy import (
    SignalScoreWeightConfig,
    map_signal_scores_to_target_weights,
    prepare_signal_score_backtest_frame,
    run_signal_score_backtest,
)


def _frame(scores: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=len(scores), freq="D"),
            "open": [100.0, 100.0, 110.0, 121.0][: len(scores)],
            "close": [100.0, 110.0, 121.0, 121.0][: len(scores)],
            "signal_score": scores,
        }
    )


def test_continuous_scores_map_to_bounded_target_weights() -> None:
    weights = map_signal_scores_to_target_weights(
        pd.Series([-10.0, 0.0, 25.0, 50.0, 100.0, 120.0])
    )

    assert weights.tolist() == pytest.approx([0.0, 0.0, 0.25, 0.5, 1.0, 1.0])


def test_score_weight_config_supports_capped_exposure() -> None:
    weights = map_signal_scores_to_target_weights(
        pd.Series([20.0, 50.0, 80.0]),
        config=SignalScoreWeightConfig(
            score_floor=20.0,
            score_ceiling=80.0,
            maximum_weight=0.6,
        ),
    )

    assert weights.tolist() == pytest.approx([0.0, 0.3, 0.6])


def test_signal_backtest_executes_the_mapped_weight_at_next_open() -> None:
    result = run_signal_score_backtest(
        _frame([50.0, 50.0, 50.0, 50.0]),
        backtest_config=BacktestConfig(transaction_cost_bps=0.0, slippage_bps=0.0),
    )

    first_trade = result.backtest.trade_log.iloc[0]

    assert result.input_frame["target_weight"].tolist() == pytest.approx([0.5] * 4)
    assert first_trade["signal_date"] == pd.Timestamp("2026-01-01")
    assert first_trade["execution_date"] == pd.Timestamp("2026-01-02")
    assert first_trade["target_weight"] == pytest.approx(0.5)


def test_signal_backtest_accepts_source_specific_column_names() -> None:
    source_frame = _frame([0.0, 100.0, 0.0]).rename(
        columns={
            "date": "trading_date",
            "signal_score": "final_signal_score",
        }
    )

    prepared = prepare_signal_score_backtest_frame(
        source_frame,
        date_column="trading_date",
        signal_column="final_signal_score",
    )

    assert prepared.columns.tolist() == ["date", "open", "close", "target_weight"]
    assert prepared["target_weight"].tolist() == pytest.approx([0.0, 1.0, 0.0])


def test_signal_backtest_rejects_non_finite_scores() -> None:
    frame = _frame([0.0, float("nan"), 100.0])

    with pytest.raises(ValueError, match="signal scores must be finite"):
        prepare_signal_score_backtest_frame(frame)



def test_supported_exposure_mappings_are_predefined() -> None:
    from app.backtesting.strategy import SUPPORTED_EXPOSURE_MAPPINGS

    assert SUPPORTED_EXPOSURE_MAPPINGS == (
        "linear",
        "concave",
        "convex",
        "capped",
    )


@pytest.mark.parametrize(
    ("policy", "expected"),
    [
        ("linear", [0.0, 0.25, 0.50, 0.75, 1.0]),
        ("concave", [0.0, 0.5, 2**-0.5, 3**0.5 / 2.0, 1.0]),
        ("convex", [0.0, 0.0625, 0.25, 0.5625, 1.0]),
        ("capped", [0.0, 0.25, 0.50, 0.75, 0.75]),
    ],
)
def test_mapping_policies_are_bounded_and_monotone(
    policy: str,
    expected: list[float],
) -> None:
    weights = map_signal_scores_to_target_weights(
        pd.Series([0.0, 25.0, 50.0, 75.0, 100.0]),
        policy=policy,
    )

    assert weights.tolist() == pytest.approx(expected)
    assert (weights >= 0.0).all()
    assert (weights <= 1.0).all()
    assert weights.is_monotonic_increasing


def test_concave_mapping_respects_custom_maximum_weight() -> None:
    weights = map_signal_scores_to_target_weights(
        pd.Series([0.0, 50.0, 100.0]),
        config=SignalScoreWeightConfig(maximum_weight=0.8),
        policy="concave",
    )

    assert weights.tolist() == pytest.approx([0.0, 0.8 / 2**0.5, 0.8])


def test_capped_mapping_uses_explicit_cap() -> None:
    weights = map_signal_scores_to_target_weights(
        pd.Series([50.0, 75.0, 100.0]),
        policy="capped",
        capped_weight=0.6,
    )

    assert weights.tolist() == pytest.approx([0.5, 0.6, 0.6])


def test_mapping_rejects_unknown_policy() -> None:
    with pytest.raises(ValueError, match="unsupported exposure mapping policy"):
        map_signal_scores_to_target_weights(
            pd.Series([50.0]),
            policy="step",
        )


def test_mapping_rejects_invalid_capped_weight() -> None:
    with pytest.raises(ValueError, match="capped_weight"):
        map_signal_scores_to_target_weights(
            pd.Series([50.0]),
            policy="capped",
            capped_weight=1.1,
        )
