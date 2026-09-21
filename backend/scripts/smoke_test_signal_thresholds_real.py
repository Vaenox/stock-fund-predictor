from __future__ import annotations

import argparse
import time
from datetime import date, timedelta

import pandas as pd

from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.analysis.scoring import calculate_fund_technical_score, calculate_stock_technical_score
from app.data.providers.borsapy import BorsapyProvider
from app.data.providers.tefas import TefasProvider
from app.ml.risk_adjustment import calculate_fund_risk_adjustment, calculate_stock_risk_adjustment
from app.ml.signal import calculate_signal_score
from app.ml.signal_rules import SignalRuleConfig
from app.ml.signal_validation import evaluate_signal_thresholds
from app.ml.splitting import build_walk_forward_splits
from app.ml.tuning import TuningConfig, select_best_candidate
from app.ml.xgboost_baseline import fit_baseline_model
from app.analysis.features import build_ml_feature_dataset, feature_columns


def _stock_frame(symbol: str, days: int) -> pd.DataFrame:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    records = BorsapyProvider().get_daily_history(symbol, start_date, end_date)
    return pd.DataFrame({
        "trading_date": [r.trading_date for r in records],
        "open": [float(r.open) for r in records],
        "high": [float(r.high) for r in records],
        "low": [float(r.low) for r in records],
        "close": [float(r.close) for r in records],
        "volume": [float(r.volume) if r.volume is not None else float("nan") for r in records],
    })


def _fund_frame(code: str, days: int, chunk_delay: float) -> pd.DataFrame:
    provider = TefasProvider()
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    records: list = []
    chunks = tuple(provider._chunks(start_date, end_date, provider._settings.max_days_per_request))
    for index, (chunk_start, chunk_end) in enumerate(chunks):
        records.extend(provider.get_fund_history(code, chunk_start, chunk_end))
        if index < len(chunks) - 1 and chunk_delay > 0:
            time.sleep(chunk_delay)
    return (
        pd.DataFrame({
            "pricing_date": [r.pricing_date for r in records],
            "unit_price": [float(r.unit_price) for r in records],
        })
        .drop_duplicates(subset=["pricing_date"])
        .sort_values("pricing_date")
        .reset_index(drop=True)
    )


CANDIDATES = (
    SignalRuleConfig(sell_threshold=30.0, buy_threshold=70.0),
    SignalRuleConfig(sell_threshold=35.0, buy_threshold=65.0),
    SignalRuleConfig(sell_threshold=40.0, buy_threshold=60.0),
    SignalRuleConfig(sell_threshold=45.0, buy_threshold=55.0),
)


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
    folds = build_walk_forward_splits(
        len(dataset),
        n_splits=3,
        test_size=40,
        gap=gap,
    )

    feature_list = list(feature_columns(asset_type))
    scored_lookup = scored.set_index(date_column)
    oos_parts: list[pd.DataFrame] = []

    for fold_number, fold in enumerate(folds, start=1):
        train = dataset.iloc[fold.train_start:fold.train_end].copy()
        test = dataset.iloc[fold.test_start:fold.test_end].copy()

        tuning = select_best_candidate(
            train,
            asset_type=asset_type,
            tuning_config=TuningConfig(
                n_inner_splits=2,
                inner_test_size=20,
                gap=gap,
            ),
        )
        model = fit_baseline_model(
            train,
            asset_type=asset_type,
            config=tuning.config,
        )
        probability = model.predict_proba(test[feature_list])[:, 1]

        rows: list[dict] = []
        for index, (_, test_row) in enumerate(test.iterrows()):
            latest = scored_lookup.loc[test_row[date_column]]
            risk = risk_fn(latest)
            signal = calculate_signal_score(
                float(probability[index]),
                float(latest["technical_score"]),
                risk.adjustment,
            )
            rows.append({
                "signal_score": signal.signal_score,
                "target": int(test_row["target"]),
                "forward_return_5d": float(test_row["forward_return_5d"]),
                "fold": fold_number,
            })
        oos_parts.append(pd.DataFrame(rows))

    oos = pd.concat(oos_parts, ignore_index=True)
    results = evaluate_signal_thresholds(oos, CANDIDATES)

    print(f"Asset type: {asset_type}")
    print(f"Symbol: {symbol.strip().upper()}")
    print(f"Raw rows: {len(raw)}")
    print(f"OOS rows: {len(oos)}")
    print("Candidate threshold validation (descriptive; no winner selected):")
    for row in results:
        print(
            f"  SELL<={row.sell_threshold:.0f} / BUY>={row.buy_threshold:.0f} | "
            f"BUY={row.buy_count} ({row.buy_coverage:.1%}) | "
            f"HOLD={row.hold_count} ({row.hold_coverage:.1%}) | "
            f"SELL={row.sell_count} ({row.sell_coverage:.1%}) | "
            f"BUY target={row.buy_target_rate if row.buy_target_rate is not None else float('nan'):.3f} | "
            f"SELL target={row.sell_target_rate if row.sell_target_rate is not None else float('nan'):.3f} | "
            f"BUY mean fwd={row.buy_mean_forward_return if row.buy_mean_forward_return is not None else float('nan'):.4f}"
        )
    assert len(results) == len(CANDIDATES)
    assert len(oos) > 0
    print("REAL SIGNAL THRESHOLD VALIDATION SMOKE TEST PASSED")


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
