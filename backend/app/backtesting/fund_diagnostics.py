from __future__ import annotations

from typing import Final

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score


EXPOSURE_BANDS: Final[tuple[tuple[float, float | None, str], ...]] = (
    (0.0, 0.25, "<25%"),
    (0.25, 0.50, "25-50%"),
    (0.50, 0.75, "50-75%"),
    (0.75, None, ">=75%"),
)


def _validate_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "target_weight",
        "target",
        "forward_return_5d",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(
            "fund diagnostic frame is missing columns: " + ", ".join(missing)
        )

    result = frame.copy()
    numeric_columns = [
        "target_weight",
        "target",
        "forward_return_5d",
    ]
    for column in numeric_columns:
        result[column] = pd.to_numeric(result[column], errors="raise")

    values = result[numeric_columns].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("fund diagnostic numeric values must be finite")
    if not result["target_weight"].between(0.0, 1.0).all():
        raise ValueError("target_weight must be between 0 and 1")
    if not result["target"].isin([0, 1]).all():
        raise ValueError("target must contain only 0/1 values")

    return result.reset_index(drop=True)


def summarize_exposure(frame: pd.DataFrame) -> dict[str, float | int]:
    """Summarize realized continuous target weights without changing the frame."""
    data = _validate_frame(frame)
    weights = data["target_weight"].astype(float)

    return {
        "observations": int(len(data)),
        "mean_weight": float(weights.mean()),
        "median_weight": float(weights.median()),
        "min_weight": float(weights.min()),
        "max_weight": float(weights.max()),
        "pct_weight_gt_25": float((weights > 0.25).mean()),
        "pct_weight_gt_50": float((weights > 0.50).mean()),
        "pct_weight_gt_75": float((weights > 0.75).mean()),
        "pct_weight_eq_zero": float(np.isclose(weights, 0.0).mean()),
    }


def _safe_auc(
    target: pd.Series,
    score: pd.Series,
) -> float | None:
    if target.nunique() < 2:
        return None
    return float(
        roc_auc_score(
            target.astype(int),
            score.astype(float),
        )
    )


def _safe_pr(
    target: pd.Series,
    score: pd.Series,
) -> float | None:
    if target.nunique() < 2:
        return None
    return float(
        average_precision_score(
            target.astype(int),
            score.astype(float),
        )
    )


def _safe_spearman(
    left: pd.Series,
    right: pd.Series,
) -> float | None:
    if left.nunique() < 2 or right.nunique() < 2:
        return None
    value = left.corr(right, method="spearman")
    return float(value) if pd.notna(value) else None


def summarize_signal_relationships(
    frame: pd.DataFrame,
    *,
    score_columns: tuple[str, ...] = (
        "ml_probability",
        "technical_score",
        "signal_score",
        "pre_risk_signal",
        "risk_score",
        "risk_adjustment",
    ),
) -> pd.DataFrame:
    """Measure OOS score association with binary target and 5-day return."""
    data = _validate_frame(frame)
    rows: list[dict[str, float | str | None]] = []

    for column in score_columns:
        if column not in data.columns:
            raise ValueError(f"fund diagnostic frame is missing column: {column}")
        score = pd.to_numeric(data[column], errors="raise")
        if not np.isfinite(score.to_numpy(dtype=float)).all():
            raise ValueError(f"{column} must be finite")

        target_corr = _safe_spearman(score, data["target"])
        return_corr = _safe_spearman(score, data["forward_return_5d"])
        rows.append(
            {
                "score": column,
                "spearman_target": target_corr,
                "spearman_forward_return_5d": return_corr,
                "roc_auc": _safe_auc(data["target"], score),
                "pr_auc": _safe_pr(data["target"], score),
            }
        )

    return pd.DataFrame(rows)


def summarize_exposure_bands(frame: pd.DataFrame) -> pd.DataFrame:
    """Summarize realized forward outcomes inside fixed exposure bands."""
    data = _validate_frame(frame)
    weights = data["target_weight"]

    rows: list[dict[str, float | int | str]] = []
    for lower, upper, label in EXPOSURE_BANDS:
        mask = weights >= lower
        if upper is not None:
            mask &= weights < upper
        bucket = data.loc[mask]
        rows.append(
            {
                "band": label,
                "observations": int(len(bucket)),
                "share": float(len(bucket) / len(data)),
                "mean_weight": (
                    float(bucket["target_weight"].mean())
                    if not bucket.empty
                    else float("nan")
                ),
                "mean_forward_return_5d": (
                    float(bucket["forward_return_5d"].mean())
                    if not bucket.empty
                    else float("nan")
                ),
                "median_forward_return_5d": (
                    float(bucket["forward_return_5d"].median())
                    if not bucket.empty
                    else float("nan")
                ),
                "positive_target_rate": (
                    float(bucket["target"].mean())
                    if not bucket.empty
                    else float("nan")
                ),
                "positive_forward_return_rate": (
                    float((bucket["forward_return_5d"] > 0.0).mean())
                    if not bucket.empty
                    else float("nan")
                ),
            }
        )

    return pd.DataFrame(rows)


def summarize_score_quintiles(
    frame: pd.DataFrame,
    *,
    score_column: str,
    n_bins: int = 5,
) -> pd.DataFrame:
    """Summarize realized outcomes across equal-count OOS score quintiles."""
    data = _validate_frame(frame)
    if score_column not in data.columns:
        raise ValueError(f"fund diagnostic frame is missing column: {score_column}")
    if n_bins < 2:
        raise ValueError("n_bins must be at least 2")

    score = pd.to_numeric(data[score_column], errors="raise")
    if not np.isfinite(score.to_numpy(dtype=float)).all():
        raise ValueError(f"{score_column} must be finite")
    if len(data) < n_bins:
        raise ValueError("fund diagnostic frame is too small for requested bins")

    ranks = score.rank(method="first")
    buckets = pd.qcut(
        ranks,
        q=n_bins,
        labels=False,
    ).astype(int) + 1

    rows: list[dict[str, float | int | str]] = []
    for bucket_number in range(1, n_bins + 1):
        bucket = data.loc[buckets == bucket_number]
        rows.append(
            {
                "score": score_column,
                "quintile": f"Q{bucket_number}",
                "observations": int(len(bucket)),
                "mean_score": float(score.loc[bucket.index].mean()),
                "mean_forward_return_5d": float(bucket["forward_return_5d"].mean()),
                "median_forward_return_5d": float(
                    bucket["forward_return_5d"].median()
                ),
                "positive_target_rate": float(bucket["target"].mean()),
                "positive_forward_return_rate": float(
                    (bucket["forward_return_5d"] > 0.0).mean()
                ),
            }
        )

    return pd.DataFrame(rows)
