from __future__ import annotations

import argparse
import time
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sklearn.metrics import average_precision_score, roc_auc_score

from app.analysis.features import MLFeatureConfig, build_ml_feature_dataset, feature_columns
from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.analysis.scoring import calculate_fund_technical_score, calculate_stock_technical_score
from app.core.settings import get_settings
from app.data.providers.borsapy import BorsapyProvider
from app.data.providers.tefas import TefasProvider
from app.ml.risk_adjustment import calculate_fund_risk_adjustment, calculate_stock_risk_adjustment
from app.ml.signal import calculate_signal_score
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


def _load_stock_frame(
    symbol: str,
    days: int,
    min_db_rows: int,
) -> tuple[pd.DataFrame, str]:
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
            {
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date,
            },
        ).mappings().all()

    if rows and len(rows) >= min_db_rows:
        return pd.DataFrame(rows), "PostgreSQL canonical history"

    return (
        _load_stock_frame_provider(symbol, days),
        "Borsapy provider (DB history insufficient)",
    )


def _load_fund_frame_provider(
    symbol: str,
    days: int,
    chunk_delay: float,
) -> pd.DataFrame:
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
        records.extend(provider.get_fund_history(symbol, chunk_start, chunk_end))
        if index < len(chunks) - 1 and chunk_delay > 0:
            time.sleep(chunk_delay)

    frame = (
        pd.DataFrame(
            {
                "pricing_date": [record.pricing_date for record in records],
                "unit_price": [float(record.unit_price) for record in records],
            }
        )
        .drop_duplicates(subset=["pricing_date"])
        .sort_values("pricing_date")
        .reset_index(drop=True)
    )
    if frame.empty:
        raise ValueError(f"no TEFAS history found for {symbol}")
    return frame


def _load_fund_frame(
    symbol: str,
    days: int,
    min_db_rows: int,
    chunk_delay: float,
) -> tuple[pd.DataFrame, str]:
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
            {
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date,
            },
        ).mappings().all()

    if rows and len(rows) >= min_db_rows:
        return pd.DataFrame(rows), "PostgreSQL canonical history"

    return (
        _load_fund_frame_provider(symbol, days, chunk_delay),
        "TEFAS provider (DB history insufficient)",
    )


def _describe(series: pd.Series) -> str:
    values = series.astype(float)
    return (
        f"min={values.min():.3f}, p25={values.quantile(0.25):.3f}, "
        f"median={values.median():.3f}, mean={values.mean():.3f}, "
        f"p75={values.quantile(0.75):.3f}, max={values.max():.3f}"
    )


def _safe_metrics(
    y_true: np.ndarray,
    score: np.ndarray,
) -> tuple[float | None, float]:
    if np.unique(y_true).size < 2:
        return None, float("nan")
    return (
        float(roc_auc_score(y_true, score)),
        float(average_precision_score(y_true, score)),
    )


def _association(
    frame: pd.DataFrame,
    column: str,
) -> tuple[float, float]:
    scores = frame[column].astype(float)
    target = frame["target"].astype(float)
    forward_return = frame["forward_return_5d"].astype(float)
    return (
        float(scores.corr(target, method="spearman")),
        float(scores.corr(forward_return, method="spearman")),
    )


def _run(
    asset_type: str,
    symbol: str,
    days: int,
    gap: int,
    min_db_rows: int,
    threshold: float,
    chunk_delay: float,
) -> None:
    if asset_type == "stock":
        raw, source = _load_stock_frame(symbol, days, min_db_rows)
        indicators = calculate_stock_indicators(raw)
        scored = calculate_stock_technical_score(indicators)
        date_column = "trading_date"
        risk_fn = calculate_stock_risk_adjustment
    else:
        raw, source = _load_fund_frame(
            symbol,
            days,
            min_db_rows,
            chunk_delay,
        )
        indicators = calculate_fund_indicators(raw)
        scored = calculate_fund_technical_score(indicators)
        date_column = "pricing_date"
        risk_fn = calculate_fund_risk_adjustment

    dataset = build_ml_feature_dataset(
        indicators,
        asset_type=asset_type,
        config=MLFeatureConfig(horizon=5, positive_return_threshold=threshold),
    )
    if dataset.empty:
        raise ValueError("signal-chain dataset is empty")

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

        fold_rows: list[dict] = []
        for index, (_, test_row) in enumerate(test.iterrows()):
            latest = scored_lookup.loc[test_row[date_column]]
            risk = risk_fn(latest)

            pre_risk = calculate_signal_score(
                float(probability[index]),
                float(latest["technical_score"]),
                0.0,
            )
            final_signal = calculate_signal_score(
                float(probability[index]),
                float(latest["technical_score"]),
                risk.adjustment,
            )

            fold_rows.append(
                {
                    "fold": fold_number,
                    "target": int(test_row["target"]),
                    "forward_return_5d": float(test_row["forward_return_5d"]),
                    "ml_probability": float(probability[index]),
                    "technical_score": float(latest["technical_score"]),
                    "risk_score": float(risk.risk_score),
                    "risk_adjustment": float(risk.adjustment),
                    "pre_risk_signal_score": float(pre_risk.signal_score),
                    "signal_score": float(final_signal.signal_score),
                }
            )

        fold_frame = pd.DataFrame(fold_rows)
        rows.append(fold_frame)

        y = fold_frame["target"].to_numpy(dtype=int)
        pre_roc, pre_pr = _safe_metrics(
            y,
            fold_frame["pre_risk_signal_score"].to_numpy(dtype=float),
        )
        final_roc, final_pr = _safe_metrics(
            y,
            fold_frame["signal_score"].to_numpy(dtype=float),
        )
        final_target_corr, final_return_corr = _association(
            fold_frame,
            "signal_score",
        )

        print(
            f"Fold {fold_number}: "
            f"selected depth={tuning.config.max_depth}, "
            f"lr={tuning.config.learning_rate:.2f}, "
            f"mcw={tuning.config.min_child_weight:.1f}, "
            f"inner PR-AUC={tuning.score:.4f}"
        )
        print(
            f"  pre-risk: ROC-AUC={pre_roc if pre_roc is not None else float('nan'):.4f}, "
            f"PR-AUC={pre_pr:.4f}"
        )
        print(
            f"  final:    ROC-AUC={final_roc if final_roc is not None else float('nan'):.4f}, "
            f"PR-AUC={final_pr:.4f}, "
            f"Spearman(target)={final_target_corr:.4f}, "
            f"Spearman(fwd)={final_return_corr:.4f}"
        )
        print(
            f"  signal={_describe(fold_frame['signal_score'])} | "
            f"risk={_describe(fold_frame['risk_adjustment'])} | "
            f"target={fold_frame['target'].mean():.3f}"
        )

    oos = pd.concat(rows, ignore_index=True)
    y = oos["target"].to_numpy(dtype=int)

    print(f"Asset type: {asset_type}")
    print(f"Symbol: {symbol.strip().upper()}")
    print(f"Data source: {source}")
    print(f"Raw rows: {len(raw)}")
    print(f"Dataset rows: {len(dataset)}")
    print(f"OOS rows: {len(oos)}")
    print(f"Production target: horizon=5, threshold={threshold:.3%}")
    print(f"ML probability distribution: {_describe(oos['ml_probability'])}")
    print(f"Technical score distribution: {_describe(oos['technical_score'])}")
    print(f"Risk score distribution: {_describe(oos['risk_score'])}")
    print(f"Risk adjustment distribution: {_describe(oos['risk_adjustment'])}")
    print(f"Pre-risk signal distribution: {_describe(oos['pre_risk_signal_score'])}")
    print(f"Final signal distribution: {_describe(oos['signal_score'])}")
    print(f"Overall target rate: {y.mean():.3f}")

    for column, label in (
        ("pre_risk_signal_score", "pre-risk signal"),
        ("signal_score", "final signal"),
    ):
        roc, pr = _safe_metrics(y, oos[column].to_numpy(dtype=float))
        target_corr, return_corr = _association(oos, column)
        print(
            f"{label}: ROC-AUC={roc if roc is not None else float('nan'):.4f}, "
            f"PR-AUC={pr:.4f}, "
            f"Spearman(target)={target_corr:.4f}, "
            f"Spearman(fwd)={return_corr:.4f}"
        )

    risk_corr_target, risk_corr_return = _association(oos, "risk_adjustment")
    score_change = (
        oos["signal_score"] - oos["pre_risk_signal_score"]
    )
    print(
        "Risk impact: "
        f"mean_adjustment={oos['risk_adjustment'].mean():.4f}, "
        f"mean_absolute_change={score_change.abs().mean():.4f}, "
        f"max_absolute_change={score_change.abs().max():.4f}, "
        f"target_spearman={risk_corr_target:.4f}, "
        f"forward_return_spearman={risk_corr_return:.4f}"
    )

    # Historical OOS cannot reconstruct production freshness from the past.
    # Keep quality_ok=True and stale_days=0 so this smoke validates the
    # deterministic risk composition without inventing historical stale data.
    print(
        "Historical risk-quality assumption: quality_ok=True, stale_days=0; "
        "freshness-specific runtime logic is not inferred from historical dates."
    )

    assert len(oos) == 120
    assert oos["ml_probability"].between(0.0, 1.0).all()
    assert oos["technical_score"].between(0.0, 100.0).all()
    assert oos["risk_score"].between(0.0, 100.0).all()
    assert oos["risk_adjustment"].between(-20.0, 0.0).all()
    assert oos["pre_risk_signal_score"].between(0.0, 100.0).all()
    assert oos["signal_score"].between(0.0, 100.0).all()
    print("REAL SIGNAL CHAIN SMOKE TEST PASSED")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asset-type", choices=("stock", "fund"), required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--days", type=int, default=1000)
    parser.add_argument("--gap", type=int, default=5)
    parser.add_argument("--min-db-rows", type=int, default=365)
    parser.add_argument("--threshold", type=float, default=0.03)
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
    if args.chunk_delay < 0:
        raise SystemExit("chunk-delay cannot be negative")

    _run(
        args.asset_type,
        args.symbol.strip().upper(),
        args.days,
        args.gap,
        args.min_db_rows,
        args.threshold,
        args.chunk_delay,
    )


if __name__ == "__main__":
    main()
