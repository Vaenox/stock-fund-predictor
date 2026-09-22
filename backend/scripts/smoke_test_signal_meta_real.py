from __future__ import annotations

import argparse
import time
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from app.analysis.features import build_ml_feature_dataset, feature_columns
from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.analysis.scoring import calculate_fund_technical_score, calculate_stock_technical_score
from app.data.providers.borsapy import BorsapyProvider
from app.data.providers.tefas import TefasProvider
from app.ml.meta_signal import META_FEATURE_COLUMNS, SignalMetaConfig, build_signal_meta_model, predict_signal_meta_probability
from app.ml.risk_adjustment import calculate_fund_risk_adjustment, calculate_stock_risk_adjustment
from app.ml.signal import calculate_signal_score
from app.ml.signal_validation import evaluate_signal_score_association, evaluate_signal_score_bins
from app.ml.splitting import build_walk_forward_splits
from app.ml.tuning import TuningConfig, build_inner_splits, select_best_candidate
from app.ml.xgboost_baseline import XGBoostBaselineConfig, fit_baseline_model


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
        provider._chunks(start_date, end_date, provider._settings.max_days_per_request)
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


def _build_inner_meta_frame(
    train: pd.DataFrame,
    *,
    asset_type: str,
    model_config: XGBoostBaselineConfig,
    tuning_config: TuningConfig,
    scored_lookup: pd.DataFrame,
    date_column: str,
    feature_list: list[str],
    risk_fn,
) -> pd.DataFrame:
    rows: list[dict] = []
    for fold in build_inner_splits(len(train), config=tuning_config):
        inner_train = train.iloc[fold.train_start:fold.train_end].copy()
        inner_validation = train.iloc[fold.test_start:fold.test_end].copy()
        if inner_train["target"].nunique() < 2:
            continue

        model = fit_baseline_model(
            inner_train,
            asset_type=asset_type,
            config=model_config,
        )
        probability = model.predict_proba(inner_validation[feature_list])[:, 1]

        for index, (_, validation_row) in enumerate(inner_validation.iterrows()):
            latest = scored_lookup.loc[validation_row[date_column]]
            risk = risk_fn(latest)
            rows.append(
                {
                    "ml_probability": float(probability[index]),
                    "technical_score": float(latest["technical_score"]),
                    "risk_adjustment": float(risk.adjustment),
                    "target": int(validation_row["target"]),
                }
            )

    result = pd.DataFrame(rows)
    if result.empty:
        raise ValueError("no two-class inner OOF observations available")
    if result["target"].nunique() < 2:
        raise ValueError("inner meta training target must contain both classes")
    return result


def _safe_metrics(y_true: np.ndarray, probability: np.ndarray) -> tuple[float | None, float]:
    roc = float(roc_auc_score(y_true, probability)) if np.unique(y_true).size > 1 else None
    pr = float(average_precision_score(y_true, probability)) if np.unique(y_true).size > 1 else float("nan")
    return roc, pr


def _run(asset_type: str, symbol: str, days: int, gap: int, chunk_delay: float) -> None:
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
    folds = build_walk_forward_splits(len(dataset), n_splits=3, test_size=40, gap=gap)
    feature_list = list(feature_columns(asset_type))
    scored_lookup = scored.set_index(date_column)
    tuning_config = TuningConfig(n_inner_splits=2, inner_test_size=20, gap=gap)

    all_parts: list[pd.DataFrame] = []

    for fold_number, fold in enumerate(folds, start=1):
        train = dataset.iloc[fold.train_start:fold.train_end].copy()
        test = dataset.iloc[fold.test_start:fold.test_end].copy()

        tuning = select_best_candidate(
            train,
            asset_type=asset_type,
            tuning_config=tuning_config,
        )
        meta_train = _build_inner_meta_frame(
            train,
            asset_type=asset_type,
            model_config=tuning.config,
            tuning_config=tuning_config,
            scored_lookup=scored_lookup,
            date_column=date_column,
            feature_list=feature_list,
            risk_fn=risk_fn,
        )
        meta_model = build_signal_meta_model(meta_train, config=SignalMetaConfig())
        base_model = fit_baseline_model(
            train,
            asset_type=asset_type,
            config=tuning.config,
        )
        base_probability = base_model.predict_proba(test[feature_list])[:, 1]

        rows: list[dict] = []
        test_components: list[dict] = []
        for index, (_, test_row) in enumerate(test.iterrows()):
            latest = scored_lookup.loc[test_row[date_column]]
            risk = risk_fn(latest)
            raw_signal = calculate_signal_score(
                float(base_probability[index]),
                float(latest["technical_score"]),
                risk.adjustment,
            )
            test_components.append(
                {
                    "ml_probability": float(base_probability[index]),
                    "technical_score": float(latest["technical_score"]),
                    "risk_adjustment": float(risk.adjustment),
                }
            )
            rows.append(
                {
                    "fold": fold_number,
                    "target": int(test_row["target"]),
                    "forward_return_5d": float(test_row["forward_return_5d"]),
                    "raw_signal_score": raw_signal.signal_score,
                }
            )

        test_component_frame = pd.DataFrame(test_components)
        meta_probability = predict_signal_meta_probability(meta_model, test_component_frame)
        for index, value in enumerate(meta_probability):
            rows[index]["meta_probability"] = float(value)
            rows[index]["meta_signal_score"] = float(value * 100.0)

        logistic = meta_model.named_steps["logistic"]
        print(
            f"Fold {fold_number}: selected depth={tuning.config.max_depth}, "
            f"lr={tuning.config.learning_rate:.2f}, "
            f"mcw={tuning.config.min_child_weight:.1f}, "
            f"inner PR-AUC={tuning.score:.4f}, "
            f"meta_train_rows={len(meta_train)}"
        )
        print(
            "  meta standardized coefficients: "
            + ", ".join(
                f"{name}={coef:.4f}"
                for name, coef in zip(META_FEATURE_COLUMNS, logistic.coef_[0])
            )
        )
        all_parts.append(pd.DataFrame(rows))

    oos = pd.concat(all_parts, ignore_index=True)
    print(f"Asset type: {asset_type}")
    print(f"Symbol: {symbol.strip().upper()}")
    print(f"Raw rows: {len(raw)}")
    print(f"OOS rows: {len(oos)}")

    for column, label in (
        ("raw_signal_score", "fixed raw signal"),
        ("meta_signal_score", "meta signal"),
    ):
        diagnostic_frame = oos[
            [column, "target", "forward_return_5d"]
        ].rename(columns={column: "signal_score"})
        target_corr, return_corr = evaluate_signal_score_association(diagnostic_frame)
        print(
            f"{label}: spearman_target={target_corr:.4f}, "
            f"spearman_forward_return={return_corr:.4f}"
        )
        roc, pr = _safe_metrics(
            diagnostic_frame["target"].to_numpy(dtype=int),
            oos["meta_probability"].to_numpy(dtype=float)
            if label == "meta signal"
            else (
                oos["raw_signal_score"].to_numpy(dtype=float) / 100.0
            ),
        )
        print(f"{label}: ROC-AUC={roc if roc is not None else float('nan'):.4f}, PR-AUC={pr:.4f}")
        for item in evaluate_signal_score_bins(diagnostic_frame, n_bins=5):
            print(
                f"  Bin {item.bin_index}: score={item.lower_score:.2f}..{item.upper_score:.2f}, "
                f"n={item.count}, target={item.target_rate:.3f}, "
                f"fwd={item.mean_forward_return:.4f}"
            )

    assert len(oos) > 0
    assert oos["meta_probability"].between(0.0, 1.0).all()
    assert oos["meta_signal_score"].between(0.0, 100.0).all()
    print("REAL SIGNAL META-AGGREGATION SMOKE TEST PASSED")


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

    _run(args.asset_type, args.symbol, args.days, args.gap, args.chunk_delay)


if __name__ == "__main__":
    main()
