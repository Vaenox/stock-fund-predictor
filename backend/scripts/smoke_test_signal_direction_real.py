from __future__ import annotations

import argparse
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sklearn.metrics import average_precision_score, roc_auc_score

from app.analysis.features import build_ml_feature_dataset, feature_columns
from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.analysis.scoring import calculate_fund_technical_score, calculate_stock_technical_score
from app.core.settings import get_settings
from app.data.providers.borsapy import BorsapyProvider
from app.ml.splitting import build_walk_forward_splits
from app.ml.tuning import TuningConfig, select_best_candidate
from app.ml.xgboost_baseline import fit_baseline_model


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


def _load_stock_frame(symbol: str, days: int, min_db_rows: int) -> tuple[pd.DataFrame, str]:
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
    if rows and len(rows) >= min_db_rows:
        return pd.DataFrame(rows), "PostgreSQL canonical history"
    return _load_stock_frame_provider(symbol, days), "Borsapy provider (DB history insufficient)"


def _load_fund_frame(symbol: str, days: int) -> tuple[pd.DataFrame, str]:
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
    return pd.DataFrame(rows), "PostgreSQL canonical history"


def _metrics(y: np.ndarray, score: np.ndarray) -> tuple[float | None, float]:
    if np.unique(y).size < 2:
        return None, float("nan")
    return float(roc_auc_score(y, score)), float(average_precision_score(y, score))


def _run(
    asset_type: str,
    symbol: str,
    days: int,
    gap: int,
    min_db_rows: int,
) -> None:
    if asset_type == "stock":
        raw, source = _load_stock_frame(symbol, days, min_db_rows)
        indicators = calculate_stock_indicators(raw)
        scored = calculate_stock_technical_score(indicators)
        date_column = "trading_date"
    else:
        raw, source = _load_fund_frame(symbol, days)
        indicators = calculate_fund_indicators(raw)
        scored = calculate_fund_technical_score(indicators)
        date_column = "pricing_date"

    dataset = build_ml_feature_dataset(indicators, asset_type=asset_type)
    folds = build_walk_forward_splits(len(dataset), n_splits=3, test_size=40, gap=gap)
    features = list(feature_columns(asset_type))
    scored_lookup = scored.set_index(date_column)
    tune_config = TuningConfig(n_inner_splits=2, inner_test_size=20, gap=gap)

    rows: list[dict] = []
    for fold_number, fold in enumerate(folds, start=1):
        train = dataset.iloc[fold.train_start:fold.train_end].copy()
        test = dataset.iloc[fold.test_start:fold.test_end].copy()
        tuning = select_best_candidate(train, asset_type=asset_type, tuning_config=tune_config)
        model = fit_baseline_model(train, asset_type=asset_type, config=tuning.config)
        probability = model.predict_proba(test[features])[:, 1]
        for i, (_, test_row) in enumerate(test.iterrows()):
            latest = scored_lookup.loc[test_row[date_column]]
            technical = float(latest["technical_score"])
            rows.append(
                {
                    "fold": fold_number,
                    "target": int(test_row["target"]),
                    "forward_return_5d": float(test_row["forward_return_5d"]),
                    "ml_probability": float(probability[i]),
                    "technical_score": technical,
                }
            )

    oos = pd.DataFrame(rows)
    y = oos["target"].to_numpy(dtype=int)
    print(f"Asset type: {asset_type}")
    print(f"Symbol: {symbol.strip().upper()}")
    print(f"Data source: {source}")
    print(f"Raw rows: {len(raw)}")
    print(f"OOS rows: {len(oos)}")
    print(f"Target rate: {y.mean():.3f}")

    for name, values, inverse in (
        ("ML probability", oos["ml_probability"].to_numpy(float), lambda x: 1.0 - x),
        ("Technical score", oos["technical_score"].to_numpy(float), lambda x: 100.0 - x),
    ):
        direct_roc, direct_pr = _metrics(y, values)
        inverse_values = inverse(values)
        inverse_roc, inverse_pr = _metrics(y, inverse_values)
        direct_spear = float(pd.Series(values).corr(pd.Series(y), method="spearman"))
        inverse_spear = float(pd.Series(inverse_values).corr(pd.Series(y), method="spearman"))
        print(
            f"{name} direct:   ROC-AUC={direct_roc if direct_roc is not None else float('nan'):.4f}, "
            f"PR-AUC={direct_pr:.4f}, Spearman={direct_spear:.4f}"
        )
        print(
            f"{name} inverse:  ROC-AUC={inverse_roc if inverse_roc is not None else float('nan'):.4f}, "
            f"PR-AUC={inverse_pr:.4f}, Spearman={inverse_spear:.4f}"
        )

    print("DIRECTION DIAGNOSTIC PASSED")


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
    _run(args.asset_type, args.symbol.strip().upper(), args.days, args.gap, args.min_db_rows)


if __name__ == "__main__":
    main()
