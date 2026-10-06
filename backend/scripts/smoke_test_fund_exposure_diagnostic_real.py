from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from app.analysis.features import MLFeatureConfig, build_ml_feature_dataset, feature_columns
from app.analysis.indicators import calculate_fund_indicators
from app.analysis.scoring import calculate_fund_technical_score
from app.backtesting.fund_diagnostics import (
    summarize_exposure,
    summarize_exposure_bands,
    summarize_signal_relationships,
)
from app.backtesting.strategy import SignalScoreWeightConfig, map_signal_scores_to_target_weights
from app.ml.risk_adjustment import calculate_fund_risk_adjustment
from app.ml.signal import calculate_signal_score
from app.ml.splitting import build_walk_forward_splits
from app.ml.tuning import TuningConfig
from app.ml.xgboost_baseline import fit_baseline_model

from smoke_test_backtest_fund_real import _load_fund, _select_best_candidate_sparse


def _fmt(value: float | None, *, pct: bool = False) -> str:
    if value is None or not np.isfinite(value):
        return "nan"
    return f"{value:+.4%}" if pct else f"{value:+.4f}"


def _build_oos_frame(
    dataset: pd.DataFrame,
    technical: pd.DataFrame,
    raw: pd.DataFrame,
    *,
    fold,
    fold_number: int,
    gap: int,
    max_weight: float,
) -> pd.DataFrame:
    train = dataset.iloc[fold.train_start : fold.train_end].copy()
    test = dataset.iloc[fold.test_start : fold.test_end].copy()

    tuning = _select_best_candidate_sparse(
        train,
        asset_type="fund",
        tuning_config=TuningConfig(
            n_inner_splits=2,
            inner_test_size=20,
            gap=gap,
        ),
    )
    model = fit_baseline_model(
        train,
        asset_type="fund",
        config=tuning.config,
    )
    columns = list(feature_columns("fund"))
    probability = model.predict_proba(test[columns])[:, 1]

    technical_lookup = technical.copy()
    technical_lookup["pricing_date"] = pd.to_datetime(
        technical_lookup["pricing_date"],
        errors="raise",
    )
    technical_lookup = technical_lookup.set_index("pricing_date")
    if technical_lookup.index.has_duplicates:
        raise ValueError("technical score data contains duplicate pricing dates")

    price_lookup = raw.set_index("pricing_date").sort_index()
    if price_lookup.index.has_duplicates:
        raise ValueError("fund price data contains duplicate pricing dates")

    score_config = SignalScoreWeightConfig(maximum_weight=max_weight)
    rows: list[dict[str, float | int | pd.Timestamp]] = []

    for index, (_, test_row) in enumerate(test.iterrows()):
        signal_date = pd.Timestamp(test_row["pricing_date"])
        if signal_date not in technical_lookup.index:
            raise ValueError(
                f"missing technical score for OOS date {signal_date.date()}"
            )
        if signal_date not in price_lookup.index:
            raise ValueError(
                f"missing fund price for OOS date {signal_date.date()}"
            )

        latest = technical_lookup.loc[signal_date]
        risk = calculate_fund_risk_adjustment(latest)
        signal = calculate_signal_score(
            float(probability[index]),
            float(latest["technical_score"]),
            risk.adjustment,
        )
        weight = float(
            map_signal_scores_to_target_weights(
                pd.Series([signal.signal_score]),
                config=score_config,
                policy="linear",
            ).iloc[0]
        )

        rows.append(
            {
                "fold": fold_number,
                "date": signal_date,
                "unit_price": float(price_lookup.loc[signal_date]["unit_price"]),
                "ml_probability": float(probability[index]),
                "technical_score": float(latest["technical_score"]),
                "risk_score": float(risk.risk_score),
                "risk_adjustment": float(risk.adjustment),
                "signal_score": float(signal.signal_score),
                "target_weight": weight,
                "target": int(test_row["target"]),
                "forward_return_5d": float(test_row["forward_return_5d"]),
                "inner_pr_auc": float(tuning.score),
            }
        )

    return pd.DataFrame(rows)


def _run_symbol(
    symbol: str,
    *,
    days: int,
    gap: int,
    min_db_rows: int,
    threshold: float,
    max_weight: float,
    chunk_delay: float,
) -> pd.DataFrame:
    raw, source = _load_fund(
        symbol,
        days,
        min_db_rows,
        chunk_delay,
    )
    raw["pricing_date"] = pd.to_datetime(raw["pricing_date"], errors="raise")
    if raw["pricing_date"].duplicated().any():
        raise ValueError("historical fund data contains duplicate pricing dates")
    raw = raw.sort_values("pricing_date").reset_index(drop=True)

    indicators = calculate_fund_indicators(raw)
    technical = calculate_fund_technical_score(indicators)
    dataset = build_ml_feature_dataset(
        indicators,
        asset_type="fund",
        config=MLFeatureConfig(
            horizon=5,
            positive_return_threshold=threshold,
        ),
    )
    if len(dataset) <= 3 * 40 + gap:
        raise ValueError(
            f"not enough dataset observations for 3x40 outer OOS with gap={gap}: "
            f"got {len(dataset)}"
        )

    folds = build_walk_forward_splits(
        len(dataset),
        n_splits=3,
        test_size=40,
        gap=gap,
    )

    print("=" * 96)
    print(f"Fund: {symbol}")
    print(f"Data source: {source}")
    print(f"Raw rows: {len(raw)} | Dataset rows: {len(dataset)}")
    print(
        f"OOS protocol: 3 x 40 test observations | gap={gap} | "
        f"target=h5/{threshold:.2%}"
    )
    print("Exposure policy: production linear mapping | max weight=%.2f" % max_weight)
    print("-" * 96)

    fold_frames: list[pd.DataFrame] = []
    for fold_number, fold in enumerate(folds, start=1):
        fold_frame = _build_oos_frame(
            dataset,
            technical,
            raw,
            fold=fold,
            fold_number=fold_number,
            gap=gap,
            max_weight=max_weight,
        )
        fold_frames.append(fold_frame)

        exposure = summarize_exposure(fold_frame)
        relationships = summarize_signal_relationships(fold_frame)
        bands = summarize_exposure_bands(fold_frame)

        print(
            f"Fold {fold_number}: {len(fold_frame)} OOS rows | "
            f"Window {fold_frame['date'].min().date()} -> {fold_frame['date'].max().date()}"
        )
        print(
            f"  Inner PR-AUC={fold_frame['inner_pr_auc'].iloc[0]:.4f} | "
            f"mean weight={exposure['mean_weight']:.4f} | "
            f"median={exposure['median_weight']:.4f} | "
            f"max={exposure['max_weight']:.4f}"
        )
        print(
            f"  Weight >25%={exposure['pct_weight_gt_25']:.2%} | "
            f">50%={exposure['pct_weight_gt_50']:.2%} | "
            f">75%={exposure['pct_weight_gt_75']:.2%} | "
            f"zero={exposure['pct_weight_eq_zero']:.2%}"
        )

        for row in relationships.itertuples(index=False):
            print(
                f"  {row.score}: Spearman(target)={_fmt(row.spearman_target)}, "
                f"Spearman(fwd5d)={_fmt(row.spearman_forward_return_5d)}, "
                f"ROC={_fmt(row.roc_auc)}, PR={_fmt(row.pr_auc)}"
            )

        print("  Exposure bands:")
        for row in bands.itertuples(index=False):
            print(
                f"    {row.band}: n={row.observations}, share={row.share:.2%}, "
                f"mean_w={_fmt(row.mean_weight)}, "
                f"mean_fwd5d={_fmt(row.mean_forward_return_5d, pct=True)}, "
                f"median_fwd5d={_fmt(row.median_forward_return_5d, pct=True)}, "
                f"positive_target={row.positive_target_rate:.2%}"
            )

    combined = pd.concat(fold_frames, ignore_index=True)
    exposure = summarize_exposure(combined)
    relationships = summarize_signal_relationships(combined)
    bands = summarize_exposure_bands(combined)

    print("-" * 96)
    print(
        f"{symbol} aggregate: OOS rows={len(combined)}, "
        f"mean weight={exposure['mean_weight']:.4f}, "
        f"median weight={exposure['median_weight']:.4f}, "
        f"max weight={exposure['max_weight']:.4f}"
    )
    for row in relationships.itertuples(index=False):
        print(
            f"  {row.score}: Spearman(target)={_fmt(row.spearman_target)}, "
            f"Spearman(fwd5d)={_fmt(row.spearman_forward_return_5d)}, "
            f"ROC={_fmt(row.roc_auc)}, PR={_fmt(row.pr_auc)}"
        )

    high_bands = bands[bands["band"].isin(["50-75%", ">=75%"])]
    if not high_bands.empty:
        non_empty = high_bands[high_bands["observations"] > 0]
        if not non_empty.empty:
            print(
                "  High-exposure observations: "
                f"{int(non_empty['observations'].sum())}/{len(combined)}"
            )

    assert len(fold_frames) == 3
    assert all(len(frame) == 40 for frame in fold_frames)
    assert all(
        frame["target_weight"].between(0.0, 1.0).all()
        for frame in fold_frames
    )

    return combined


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a leakage-safe real fund OOS exposure/signal diagnostic."
    )
    parser.add_argument("--symbols", default="AFA,AFT")
    parser.add_argument("--days", type=int, default=1000)
    parser.add_argument("--gap", type=int, default=5)
    parser.add_argument("--min-db-rows", type=int, default=365)
    parser.add_argument("--threshold", type=float, default=0.03)
    parser.add_argument("--max-weight", type=float, default=1.0)
    parser.add_argument("--chunk-delay", type=float, default=3.0)
    args = parser.parse_args()

    if args.days < 260:
        raise SystemExit("days must be at least 260")
    if args.gap < 5:
        raise SystemExit("gap must be at least 5")
    if args.min_db_rows <= 0:
        raise SystemExit("min-db-rows must be positive")
    if args.threshold <= -1.0:
        raise SystemExit("threshold must be greater than -1")
    if not 0.0 < args.max_weight <= 1.0:
        raise SystemExit("max-weight must be between 0 and 1")
    if args.chunk_delay < 0:
        raise SystemExit("chunk-delay cannot be negative")

    symbols = tuple(
        symbol.strip().upper()
        for symbol in args.symbols.split(",")
        if symbol.strip()
    )
    if not symbols:
        raise SystemExit("symbols cannot be empty")

    all_frames: list[pd.DataFrame] = []
    failures: list[tuple[str, str]] = []

    for symbol in symbols:
        try:
            frame = _run_symbol(
                symbol,
                days=args.days,
                gap=args.gap,
                min_db_rows=args.min_db_rows,
                threshold=args.threshold,
                max_weight=args.max_weight,
                chunk_delay=args.chunk_delay,
            )
            frame["symbol"] = symbol
            all_frames.append(frame)
        except Exception as exc:
            failures.append((symbol, f"{type(exc).__name__}: {exc}"))
            print("=" * 96)
            print(f"FAILED {symbol}: {type(exc).__name__}: {exc}")

    if failures:
        print("=" * 96)
        print("FAILURES")
        for symbol, message in failures:
            print(f"{symbol}: {message}")
        return 1

    combined = pd.concat(all_frames, ignore_index=True)
    print("=" * 96)
    print("CROSS-FUND EXPOSURE DIAGNOSTIC SUMMARY")
    print(f"Symbols: {combined['symbol'].nunique()}")
    print(f"OOS observations: {len(combined)}")

    overall_exposure = summarize_exposure(combined)
    print(
        f"Mean target weight: {overall_exposure['mean_weight']:.4f} | "
        f"Median: {overall_exposure['median_weight']:.4f} | "
        f"Max: {overall_exposure['max_weight']:.4f}"
    )
    print(
        f"Weight >25%: {overall_exposure['pct_weight_gt_25']:.2%} | "
        f">50%: {overall_exposure['pct_weight_gt_50']:.2%} | "
        f">75%: {overall_exposure['pct_weight_gt_75']:.2%} | "
        f"zero: {overall_exposure['pct_weight_eq_zero']:.2%}"
    )

    relationships = summarize_signal_relationships(combined)
    print("Overall signal relationships:")
    for row in relationships.itertuples(index=False):
        print(
            f"  {row.score}: Spearman(target)={_fmt(row.spearman_target)}, "
            f"Spearman(fwd5d)={_fmt(row.spearman_forward_return_5d)}, "
            f"ROC={_fmt(row.roc_auc)}, PR={_fmt(row.pr_auc)}"
        )

    print("Overall exposure bands:")
    for row in summarize_exposure_bands(combined).itertuples(index=False):
        print(
            f"  {row.band}: n={row.observations}, share={row.share:.2%}, "
            f"mean_w={_fmt(row.mean_weight)}, "
            f"mean_fwd5d={_fmt(row.mean_forward_return_5d, pct=True)}, "
            f"median_fwd5d={_fmt(row.median_forward_return_5d, pct=True)}, "
            f"positive_target={row.positive_target_rate:.2%}"
        )

    assert len(all_frames) == len(symbols)
    assert len(combined) == len(symbols) * 3 * 40
    print("REAL FUND EXPOSURE DIAGNOSTIC PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
