from __future__ import annotations

import pandas as pd
import pytest

from app.backtesting.fund_diagnostics import (
    summarize_exposure,
    summarize_exposure_bands,
    summarize_signal_relationships,
    summarize_score_quintiles,
)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "target_weight": [0.0, 0.20, 0.40, 0.60, 0.80, 1.0],
            "target": [0, 0, 1, 0, 1, 1],
            "forward_return_5d": [-0.01, 0.01, 0.03, -0.02, 0.05, 0.08],
            "ml_probability": [0.1, 0.2, 0.4, 0.3, 0.8, 0.9],
            "technical_score": [10, 20, 40, 30, 80, 90],
            "signal_score": [5, 15, 35, 25, 75, 95],
            "pre_risk_signal": [6, 16, 36, 26, 76, 96],
            "risk_score": [60, 50, 40, 30, 20, 10],
            "risk_adjustment": [-1, -1, -1, -1, -1, -1],
        }
    )


def test_summarize_exposure_returns_bounded_distribution() -> None:
    result = summarize_exposure(_frame())

    assert result["observations"] == 6
    assert result["mean_weight"] == pytest.approx(0.5)
    assert result["median_weight"] == pytest.approx(0.5)
    assert result["min_weight"] == pytest.approx(0.0)
    assert result["max_weight"] == pytest.approx(1.0)
    assert result["pct_weight_gt_25"] == pytest.approx(4 / 6)
    assert result["pct_weight_gt_50"] == pytest.approx(3 / 6)
    assert result["pct_weight_gt_75"] == pytest.approx(2 / 6)
    assert result["pct_weight_eq_zero"] == pytest.approx(1 / 6)


def test_summarize_exposure_bands_uses_fixed_non_overlapping_ranges() -> None:
    result = summarize_exposure_bands(_frame())

    assert result["observations"].tolist() == [2, 1, 1, 2]
    assert result["band"].tolist() == ["<25%", "25-50%", "50-75%", ">=75%"]
    assert result.loc[0, "mean_forward_return_5d"] == pytest.approx(0.0)
    assert result.loc[2, "positive_target_rate"] == pytest.approx(0.0)
    assert result.loc[3, "positive_target_rate"] == pytest.approx(1.0)
    assert result.loc[1, "positive_forward_return_rate"] == pytest.approx(1.0)


def test_summarize_signal_relationships_reports_oos_associations() -> None:
    result = summarize_signal_relationships(_frame())
    by_score = result.set_index("score")

    assert by_score.loc["ml_probability", "roc_auc"] > 0.5
    assert by_score.loc["technical_score", "pr_auc"] > 0.5
    assert by_score.loc["signal_score", "spearman_forward_return_5d"] > 0.5
    assert by_score.loc["pre_risk_signal", "spearman_forward_return_5d"] > 0.5
    assert by_score.loc["risk_score", "spearman_forward_return_5d"] < 0.0
    assert set(result.columns) == {
        "score",
        "spearman_target",
        "spearman_forward_return_5d",
        "roc_auc",
        "pr_auc",
    }


def test_diagnostics_reject_missing_columns() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        summarize_exposure(
            pd.DataFrame(
                {
                    "target_weight": [0.5],
                    "target": [1],
                }
            )
        )


def test_summarize_signal_relationships_handles_constant_scores() -> None:
    frame = _frame()
    frame["risk_score"] = 50.0
    frame["risk_adjustment"] = -10.0

    result = summarize_signal_relationships(frame)
    by_score = result.set_index("score")

    assert pd.isna(by_score.loc["risk_score", "spearman_target"])
    assert pd.isna(by_score.loc["risk_score", "spearman_forward_return_5d"])
    assert pd.isna(by_score.loc["risk_adjustment", "spearman_target"])


def test_summarize_score_quintiles_creates_equal_count_buckets() -> None:
    result = summarize_score_quintiles(_frame(), score_column="signal_score")

    assert result["quintile"].tolist() == ["Q1", "Q2", "Q3", "Q4", "Q5"]
    assert result["observations"].tolist() == [2, 1, 1, 1, 1]
    assert result.loc[0, "mean_score"] == pytest.approx(10.0)
    assert result.loc[4, "mean_score"] == pytest.approx(95.0)


def test_summarize_score_quintiles_rejects_small_frames() -> None:
    with pytest.raises(ValueError, match="too small"):
        summarize_score_quintiles(
            _frame().head(4),
            score_column="signal_score",
            n_bins=5,
        )
