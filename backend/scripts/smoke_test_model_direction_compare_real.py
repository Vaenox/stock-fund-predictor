from __future__ import annotations

import argparse
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sklearn.metrics import average_precision_score, roc_auc_score

from app.analysis.features import build_ml_feature_dataset, feature_columns
from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.core.settings import get_settings
from app.data.providers.borsapy import BorsapyProvider
from app.ml.splitting import build_walk_forward_splits
from app.ml.tuning import TuningConfig, select_best_candidate
from app.ml.xgboost_baseline import XGBoostBaselineConfig, build_model


def _load_stock_frame_provider(symbol: str, days: int) -> pd.DataFrame:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    records = BorsapyProvider().get_daily_history(symbol, start_date, end_date)
    if not records:
        raise ValueError(f"no Borsapy history found for {symbol}")
    return pd.DataFrame(
        {
            "trading_date": [record.trading_date for record in records],
            "open": [float(record.open) for record in records],
            "high": [float(record.high) for record in records],
            "low": [float(record.low) for record in records],
            "close": [float(record.close) for record in records],
            "volume": [
                float(record.volume) if record.volume is not None else float("nan")
                for record in records
            ],
        }
    )


def _load_stock_frame(symbol: str, days: int) -> pd.DataFrame:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    engine = create_engine(get_settings().database_url, future=True)

    query = text(
        """
        SELECT
            b.trading_date,
            b.open,
            b.high,
            b.low,
            b.close,
            b.volume
        FROM stock_daily_bars AS b
        JOIN assets AS a ON a.id = b.asset_id
        WHERE a.canonical_symbol = :symbol
          AND b.trading_date BETWEEN :start_date AND :end_date
        ORDER BY b.trading_date
        """
    )

    with engine.connect() as conn:
        rows = conn.execute(
            query,
            {"symbol": symbol, "start_date": start_date, "end_date": end_date},
        ).mappings().all()

    if not rows:
        raise ValueError(f"no DB stock history found for {symbol}")

    return pd.DataFrame(rows)


def _load_fund_frame(symbol: str, days: int) -> pd.DataFrame:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    engine = create_engine(get_settings().database_url, future=True)

    query = text(
        """
        SELECT
            p.pricing_date,
            p.unit_price
        FROM fund_daily_prices AS p
        JOIN assets AS a ON a.id = p.asset_id
        WHERE a.canonical_symbol = :symbol
          AND p.pricing_date BETWEEN :start_date AND :end_date
        ORDER BY p.pricing_date
        """
    )

    with engine.connect() as conn:
        rows = conn.execute(
            query,
            {"symbol": symbol, "start_date": start_date, "end_date": end_date},
        ).mappings().all()

    if not rows:
        raise ValueError(f"no DB fund history found for {symbol}")

    return pd.DataFrame(rows)


def _safe_metrics(
    y_true: np.ndarray, probability: np.ndarray
) -> tuple[float | None, float]:
    if np.unique(y_true).size < 2:
        return None, float("nan")
    return (
        float(roc_auc_score(y_true, probability)),
        float(average_precision_score(y_true, probability)),
    )


def _describe(name: str, y: np.ndarray, probability: np.ndarray) -> None:
    roc, pr = _safe_metrics(y, probability)
    spear = float(pd.Series(probability).corr(pd.Series(y), method="spearman"))
    inverse = 1.0 - probability
    inv_roc, inv_pr = _safe_metrics(y, inverse)
    inv_spear = float(pd.Series(inverse).corr(pd.Series(y), method="spearman"))
    print(
        f"  {name}: direct ROC={roc if roc is not None else float('nan'):.4f}, "
        f"PR={pr:.4f}, Spearman={spear:.4f} | "
        f"inverse ROC={inv_roc if inv_roc is not None else float('nan'):.4f}, "
        f"PR={inv_pr:.4f}, Spearman={inv_spear:.4f}"
    )


def _run(asset_type: str, symbol: str, days: int, gap: int, min_db_rows: int) -> None:
    if asset_type == "stock":
        raw = _load_stock_frame(symbol, days)
        indicators = calculate_stock_indicators(raw)
    else:
        raw = _load_fund_frame(symbol, days)
        indicators = calculate_fund_indicators(raw)

    dataset = build_ml_feature_dataset(indicators, asset_type=asset_type)
    folds = build_walk_forward_splits(
        len(dataset),
        n_splits=3,
        test_size=40,
        gap=gap,
    )
    features = list(feature_columns(asset_type))
    tuning_config = TuningConfig(
        n_inner_splits=2,
        inner_test_size=20,
        gap=gap,
    )
    baseline_config = XGBoostBaselineConfig()

    rows: list[dict] = []
    for fold_number, fold in enumerate(folds, start=1):
        train = dataset.iloc[fold.train_start : fold.train_end].copy()
        test = dataset.iloc[fold.test_start : fold.test_end].copy()
        if train["target"].nunique() < 2:
            raise ValueError(f"fold {fold_number} training target contains one class")

        tuning = select_best_candidate(
            train,
            asset_type=asset_type,
            tuning_config=tuning_config,
        )
        baseline = build_model(baseline_config)
        tuned = build_model(tuning.config)

        baseline.fit(train[features], train["target"].astype(int))
        tuned.fit(train[features], train["target"].astype(int))

        baseline_p = baseline.predict_proba(test[features])[:, 1]
        tuned_p = tuned.predict_proba(test[features])[:, 1]
        y = test["target"].to_numpy(dtype=int)

        print(
            f"Fold {fold_number}: tuned depth={tuning.config.max_depth}, "
            f"lr={tuning.config.learning_rate:.2f}, "
            f"mcw={tuning.config.min_child_weight:.1f}, "
            f"inner PR-AUC={tuning.score:.4f}"
        )
        _describe("baseline", y, baseline_p)
        _describe("tuned", y, tuned_p)

        for index in range(len(test)):
            rows.append(
                {
                    "target": int(y[index]),
                    "baseline_probability": float(baseline_p[index]),
                    "tuned_probability": float(tuned_p[index]),
                    "forward_return_5d": float(
                        test.iloc[index]["forward_return_5d"]
                    ),
                }
            )

    oos = pd.DataFrame(rows)
    y = oos["target"].to_numpy(dtype=int)

    print(f"Asset type: {asset_type}")
    print(f"Symbol: {symbol.strip().upper()}")
    print(f"Data source: {source}")
    print(f"Raw rows: {len(raw)}")
    print(f"Raw range: {raw.iloc[0].iloc[0]} -> {raw.iloc[-1].iloc[0]}")
    print(f"Training rows: {len(dataset)}")
    print(f"OOS rows: {len(oos)}")
    print(f"Target distribution: {dataset['target'].value_counts().sort_index().to_dict()}")
    print(f"Target rate: {y.mean():.3f}")
    _describe(
        "baseline aggregate",
        y,
        oos["baseline_probability"].to_numpy(dtype=float),
    )
    _describe(
        "tuned aggregate",
        y,
        oos["tuned_probability"].to_numpy(dtype=float),
    )

    assert len(oos) > 0
    print("MODEL DIRECTION COMPARISON PASSED")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-type", choices=("stock", "fund"), required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--days", type=int, default=1000)
    parser.add_argument("--gap", type=int, default=5)
    parser.add_argument("--min-db-rows", type=int, default=365)
    args = parser.parse_args()

    if args.days < 260:
        raise SystemExit("days must be at least 260")
    if args.gap < 5:
        raise SystemExit("gap must be at least 5")
    if args.min_db_rows <= 0:
        raise SystemExit("min-db-rows must be positive")

    _run(
        args.asset_type,
        args.symbol.strip().upper(),
        args.days,
        args.gap,
        args.min_db_rows,
    )


if __name__ == "__main__":
    main()
