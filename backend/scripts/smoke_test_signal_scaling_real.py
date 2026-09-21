from __future__ import annotations

import argparse
import time
from datetime import date, timedelta

import numpy as np
import pandas as pd

from app.analysis.features import build_ml_feature_dataset, feature_columns
from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.analysis.scoring import calculate_fund_technical_score, calculate_stock_technical_score
from app.data.providers.borsapy import BorsapyProvider
from app.data.providers.tefas import TefasProvider
from app.ml.risk_adjustment import calculate_fund_risk_adjustment, calculate_stock_risk_adjustment
from app.ml.signal import calculate_signal_score
from app.ml.signal_rules import SignalRuleConfig
from app.ml.signal_scaling import (
    calculate_percentile_scaled_signal_base,
    calculate_scaled_signal_base,
    derive_signal_scale_config,
    evaluate_signal_scaling_stability,
)
from app.ml.splitting import build_walk_forward_splits
from app.ml.tuning import TuningConfig, build_inner_splits, select_best_candidate
from app.ml.xgboost_baseline import XGBoostBaselineConfig, fit_baseline_model


CANDIDATES = (
    SignalRuleConfig(sell_threshold=30.0, buy_threshold=70.0),
    SignalRuleConfig(sell_threshold=35.0, buy_threshold=65.0),
    SignalRuleConfig(sell_threshold=40.0, buy_threshold=60.0),
    SignalRuleConfig(sell_threshold=45.0, buy_threshold=55.0),
)


def _stock_frame(symbol: str, days: int) -> pd.DataFrame:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    records = BorsapyProvider().get_daily_history(symbol, start_date, end_date)
    return pd.DataFrame(
        {
            "trading_date": [r.trading_date for r in records],
            "open": [float(r.open) for r in records],
            "high": [float(r.high) for r in records],
            "low": [float(r.low) for r in records],
            "close": [float(r.close) for r in records],
            "volume": [
                float(r.volume) if r.volume is not None else float("nan")
                for r in records
            ],
        }
    )


def _fund_frame(code: str, days: int, chunk_delay: float) -> pd.DataFrame:
    provider = TefasProvider()
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    records: list = []
    chunks = tuple(
        provider._chunks(
            start_date,
            end_date,
            provider._settings.max_days_per_request,
        )
    )
    for index, (chunk_start, chunk_end) in enumerate(chunks):
        records.extend(provider.get_fund_history(code, chunk_start, chunk_end))
        if index < len(chunks) - 1 and chunk_delay > 0:
            time.sleep(chunk_delay)

    return (
        pd.DataFrame(
            {
                "pricing_date": [r.pricing_date for r in records],
                "unit_price": [float(r.unit_price) for r in records],
            }
        )
        .drop_duplicates(subset=["pricing_date"])
        .sort_values("pricing_date")
        .reset_index(drop=True)
    )


def _describe(series: pd.Series) -> str:
    values = series.astype(float)
    return (
        f"min={values.min():.3f}, p25={values.quantile(.25):.3f}, "
        f"median={values.median():.3f}, mean={values.mean():.3f}, "
        f"p75={values.quantile(.75):.3f}, max={values.max():.3f}"
    )


def _inner_training_components(
    train: pd.DataFrame,
    *,
    asset_type: str,
    tuning_config: TuningConfig,
    model_config: XGBoostBaselineConfig,
    technical_lookup: pd.DataFrame,
    date_column: str,
    feature_list: list[str],
) -> tuple[np.ndarray, np.ndarray]:
    """Build chronological OOF components using only the outer training period."""
    inner_folds = build_inner_splits(len(train), config=tuning_config)
    ml_values: list[float] = []
    technical_values: list[float] = []

    for inner_fold in inner_folds:
        inner_train = train.iloc[
            inner_fold.train_start : inner_fold.train_end
        ].copy()
        inner_validation = train.iloc[
            inner_fold.test_start : inner_fold.test_end
        ].copy()

        if inner_train["target"].nunique() < 2:
            continue

        model = fit_baseline_model(
            inner_train,
            asset_type=asset_type,
            config=model_config,
        )
        probability = model.predict_proba(inner_validation[feature_list])[:, 1]

        for index, (_, validation_row) in enumerate(inner_validation.iterrows()):
            latest = technical_lookup.loc[validation_row[date_column]]
            ml_values.append(float(probability[index]))
            technical_values.append(float(latest["technical_score"]))

    if not ml_values:
        raise ValueError("outer training period has no two-class inner OOF folds")

    return np.asarray(ml_values, dtype=float), np.asarray(technical_values, dtype=float)


def _run(
    asset_type: str,
    symbol: str,
    days: int,
    gap: int,
    chunk_delay: float,
) -> None:
    if asset_type == "stock":
        raw = _stock_frame(symbol, days)
        indicators = calculate_stock_indicators(raw)
        scored = calculate_stock_technical_score(indicators)
        date_column = "trading_date"
        risk_fn = calculate_stock_risk_adjustment
    else:
        raw = _fund_frame(symbol, days, chunk_delay)
        indicators = calculate_fund_indicators(raw)
        scored = calculate_fund_technical_score(indicators)
        date_column = "pricing_date"
        risk_fn = calculate_fund_risk_adjustment

    dataset = build_ml_feature_dataset(indicators, asset_type=asset_type)
    folds = build_walk_forward_splits(
        len(dataset),
        n_splits=3,
        test_size=40,
        gap=gap,
    )

    feature_list = list(feature_columns(asset_type))
    scored_lookup = scored.set_index(date_column)
    tuning_config = TuningConfig(
        n_inner_splits=2,
        inner_test_size=20,
        gap=gap,
    )
    rows: list[pd.DataFrame] = []

    for fold_number, fold in enumerate(folds, start=1):
        train = dataset.iloc[fold.train_start : fold.train_end].copy()
        test = dataset.iloc[fold.test_start : fold.test_end].copy()

        tuning = select_best_candidate(
            train,
            asset_type=asset_type,
            tuning_config=tuning_config,
        )
        model = fit_baseline_model(
            train,
            asset_type=asset_type,
            config=tuning.config,
        )
        probability = model.predict_proba(test[feature_list])[:, 1]

        # Bounds are derived only from OOF observations strictly inside outer train.
        inner_ml, inner_technical = _inner_training_components(
            train,
            asset_type=asset_type,
            tuning_config=tuning_config,
            model_config=tuning.config,
            technical_lookup=scored_lookup,
            date_column=date_column,
            feature_list=feature_list,
        )
        scale_config = derive_signal_scale_config(
            inner_ml,
            inner_technical,
            lower_quantile=0.05,
            upper_quantile=0.95,
        )

        fold_rows: list[dict] = []
        for index, (_, test_row) in enumerate(test.iterrows()):
            latest = scored_lookup.loc[test_row[date_column]]
            risk = risk_fn(latest)

            raw_signal = calculate_signal_score(
                float(probability[index]),
                float(latest["technical_score"]),
                risk.adjustment,
            )
            ml_scaled, technical_scaled, scaled_base = calculate_scaled_signal_base(
                float(probability[index]),
                float(latest["technical_score"]),
                config=scale_config,
            )
            scaled_signal_score = float(
                np.clip(scaled_base + risk.adjustment, 0.0, 100.0)
            )
            percentile_ml, percentile_technical, percentile_base = (
                calculate_percentile_scaled_signal_base(
                    float(probability[index]),
                    float(latest["technical_score"]),
                    inner_ml,
                    inner_technical,
                )
            )
            percentile_signal_score = float(
                np.clip(percentile_base + risk.adjustment, 0.0, 100.0)
            )

            fold_rows.append(
                {
                    "fold": fold_number,
                    "raw_signal_score": raw_signal.signal_score,
                    "scaled_signal_score": scaled_signal_score,
                    "percentile_signal_score": percentile_signal_score,
                    "ml_probability": float(probability[index]),
                    "ml_scaled": ml_scaled,
                    "percentile_ml": percentile_ml,
                    "technical_score": float(latest["technical_score"]),
                    "technical_scaled": technical_scaled,
                    "percentile_technical": percentile_technical,
                    "risk_adjustment": float(risk.adjustment),
                    "target": int(test_row["target"]),
                    "forward_return_5d": float(test_row["forward_return_5d"]),
                }
            )

        fold_frame = pd.DataFrame(fold_rows)
        rows.append(fold_frame)

        print(
            f"Fold {fold_number}: "
            f"ML bounds={scale_config.ml_floor:.4f}..{scale_config.ml_ceiling:.4f} | "
            f"technical bounds={scale_config.technical_floor:.2f}..{scale_config.technical_ceiling:.2f} | "
            f"selected depth={tuning.config.max_depth}, "
            f"lr={tuning.config.learning_rate:.2f}, "
            f"mcw={tuning.config.min_child_weight:.1f} | "
            f"inner PR-AUC={tuning.score:.4f}"
        )
        print(f"  raw signal:         {_describe(fold_frame['raw_signal_score'])}")
        print(f"  quantile signal:    {_describe(fold_frame['scaled_signal_score'])}")
        print(f"  percentile signal:  {_describe(fold_frame['percentile_signal_score'])}")

    oos = pd.concat(rows, ignore_index=True)

    quantile_folds = tuple(
        group["scaled_signal_score"].to_numpy(dtype=float)
        for _, group in oos.groupby("fold", sort=True)
    )
    percentile_folds = tuple(
        group["percentile_signal_score"].to_numpy(dtype=float)
        for _, group in oos.groupby("fold", sort=True)
    )
    quantile_stability = evaluate_signal_scaling_stability(quantile_folds)
    percentile_stability = evaluate_signal_scaling_stability(percentile_folds)

    print(f"Asset type: {asset_type}")
    print(f"Symbol: {symbol.strip().upper()}")
    print(f"Raw rows: {len(raw)}")
    print(f"OOS rows: {len(oos)}")
    print(f"Raw signal distribution:             {_describe(oos['raw_signal_score'])}")
    print(f"Quantile signal distribution:        {_describe(oos['scaled_signal_score'])}")
    print(f"Percentile signal distribution:      {_describe(oos['percentile_signal_score'])}")
    print(f"Quantile ML distribution:            {_describe(oos['ml_scaled'])}")
    print(f"Percentile ML distribution:          {_describe(oos['percentile_ml'])}")
    print(f"Quantile technical distribution:     {_describe(oos['technical_scaled'])}")
    print(f"Percentile technical distribution:   {_describe(oos['percentile_technical'])}")
    print(f"Overall target rate: {oos['target'].mean():.3f}")
    print(
        "Quantile stability: "
        f"median_spread={quantile_stability.median_spread:.3f}, "
        f"median_std={quantile_stability.median_std:.3f}, "
        f"iqr_spread={quantile_stability.iqr_spread:.3f}, "
        f"saturation={quantile_stability.saturation_rate:.1%}"
    )
    print(
        "Percentile stability: "
        f"median_spread={percentile_stability.median_spread:.3f}, "
        f"median_std={percentile_stability.median_std:.3f}, "
        f"iqr_spread={percentile_stability.iqr_spread:.3f}, "
        f"saturation={percentile_stability.saturation_rate:.1%}"
    )

    print("Threshold coverage — quantile scaling (descriptive; no winner selected):")
    for config in CANDIDATES:
        buy = oos["scaled_signal_score"] >= config.buy_threshold
        sell = oos["scaled_signal_score"] <= config.sell_threshold
        hold = ~(buy | sell)
        print(
            f"  SELL<={config.sell_threshold:.0f} / BUY>={config.buy_threshold:.0f} | "
            f"BUY={int(buy.sum())} ({buy.mean():.1%}) | "
            f"HOLD={int(hold.sum())} ({hold.mean():.1%}) | "
            f"SELL={int(sell.sum())} ({sell.mean():.1%})"
        )

    print("Threshold coverage — percentile scaling (descriptive; no winner selected):")
    for config in CANDIDATES:
        buy = oos["percentile_signal_score"] >= config.buy_threshold
        sell = oos["percentile_signal_score"] <= config.sell_threshold
        hold = ~(buy | sell)
        print(
            f"  SELL<={config.sell_threshold:.0f} / BUY>={config.buy_threshold:.0f} | "
            f"BUY={int(buy.sum())} ({buy.mean():.1%}) | "
            f"HOLD={int(hold.sum())} ({hold.mean():.1%}) | "
            f"SELL={int(sell.sum())} ({sell.mean():.1%})"
        )

    assert len(oos) > 0
    assert oos["scaled_signal_score"].between(0.0, 100.0).all()
    assert oos["percentile_signal_score"].between(0.0, 100.0).all()
    assert oos["ml_scaled"].between(0.0, 100.0).all()
    assert oos["technical_scaled"].between(0.0, 100.0).all()
    print("REAL SIGNAL SCALING COMPARISON SMOKE TEST PASSED")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-type", choices=("stock", "fund"), required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--days", type=int, default=1000)
    parser.add_argument("--gap", type=int, default=5)
    parser.add_argument("--chunk-delay", type=float, default=3.0)
    args = parser.parse_args()

    if args.days < 260:
        raise SystemExit("days must be at least 260")
    if args.gap < 5:
        raise SystemExit("gap must be at least 5")
    if args.chunk_delay < 0:
        raise SystemExit("chunk-delay cannot be negative")

    _run(
        args.asset_type,
        args.symbol,
        args.days,
        args.gap,
        args.chunk_delay,
    )


if __name__ == "__main__":
    main()
