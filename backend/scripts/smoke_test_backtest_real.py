from __future__ import annotations

import argparse
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import create_engine, text

from app.analysis.features import MLFeatureConfig, build_ml_feature_dataset, feature_columns
from app.analysis.indicators import calculate_stock_indicators
from app.analysis.scoring import calculate_stock_technical_score
from app.backtesting.engine import BacktestConfig, ExecutionCostConfig, run_long_only_backtest
from app.backtesting.strategy import SignalScoreWeightConfig, run_signal_score_backtest
from app.core.settings import get_settings
from app.data.providers.borsapy import BorsapyProvider
from app.ml.risk_adjustment import calculate_stock_risk_adjustment
from app.ml.signal import calculate_signal_score
from app.ml.splitting import build_walk_forward_splits
from app.ml.tuning import TuningConfig, build_inner_splits, default_candidate_grid, TuningCandidate
from app.ml.xgboost_baseline import build_model, fit_baseline_model
from sklearn.metrics import average_precision_score, roc_auc_score


def _load_stock(symbol: str, days: int, min_db_rows: int) -> tuple[pd.DataFrame, str]:
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    engine = create_engine(get_settings().database_url, future=True)
    query = text(
        """
        SELECT b.trading_date, b.open, b.high, b.low, b.close, b.volume
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

    records = BorsapyProvider().get_daily_history(symbol, start_date, end_date)
    if not records:
        raise ValueError(f"no historical stock data found for {symbol}")
    return (
        pd.DataFrame(
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
        ),
        "Borsapy provider (DB history insufficient)",
    )


def _select_candidate(frame: pd.DataFrame, asset_type: str) -> TuningCandidate:
    columns = list(feature_columns(asset_type))
    scores: list[TuningCandidate] = []
    config = TuningConfig(n_inner_splits=2, inner_test_size=20, gap=5)
    for candidate in default_candidate_grid():
        fold_scores: list[float] = []
        for fold in build_inner_splits(len(frame), config=config):
            train = frame.iloc[fold.train_start : fold.train_end]
            validation = frame.iloc[fold.test_start : fold.test_end]
            if train["target"].nunique() < 2 or validation["target"].nunique() < 2:
                continue
            model = build_model(candidate)
            model.fit(train[columns], train["target"].astype(int))
            probability = model.predict_proba(validation[columns])[:, 1]
            fold_scores.append(
                float(
                    average_precision_score(
                        validation["target"].astype(int),
                        probability,
                    )
                )
            )
        if fold_scores:
            scores.append(
                TuningCandidate(
                    config=candidate,
                    score=sum(fold_scores) / len(fold_scores),
                )
            )
    if not scores:
        raise ValueError("no usable inner tuning candidate")
    return max(
        scores,
        key=lambda item: (
            item.score,
            -item.config.max_depth,
            -item.config.learning_rate,
            -item.config.min_child_weight,
        ),
    )


def _safe_auc(y: pd.Series, score: pd.Series) -> float | None:
    if y.nunique() < 2:
        return None
    return float(roc_auc_score(y.astype(int), score.astype(float)))


def _safe_pr(y: pd.Series, score: pd.Series) -> float:
    if y.nunique() < 2:
        return float("nan")
    return float(average_precision_score(y.astype(int), score.astype(float)))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--days", type=int, default=1000)
    parser.add_argument("--gap", type=int, default=5)
    parser.add_argument("--transaction-cost-bps", type=float, default=10.0)
    parser.add_argument("--slippage-bps", type=float, default=5.0)
    parser.add_argument("--max-weight", type=float, default=1.0)
    parser.add_argument("--min-db-rows", type=int, default=400)
    args = parser.parse_args()

    raw, source = _load_stock(args.symbol.strip().upper(), args.days, args.min_db_rows)
    raw["trading_date"] = pd.to_datetime(raw["trading_date"], errors="raise")
    if raw["trading_date"].duplicated().any():
        raise ValueError("historical stock data contains duplicate trading dates")
    raw = raw.sort_values("trading_date").reset_index(drop=True)
    indicators = calculate_stock_indicators(raw)
    technical = calculate_stock_technical_score(indicators)
    dataset = build_ml_feature_dataset(
        indicators,
        asset_type="stock",
        config=MLFeatureConfig(horizon=5, positive_return_threshold=0.03),
    )
    print(f"Loaded raw rows: {len(raw)}")
    print(f"Prepared dataset rows: {len(dataset)}")
    if len(dataset) <= 3 * 40 + args.gap:
        raise ValueError(
            f"not enough dataset observations for 3x40 outer OOS with gap={args.gap}: "
            f"got {len(dataset)}, need more than {3 * 40 + args.gap}"
        )

    folds = build_walk_forward_splits(
        len(dataset), n_splits=3, test_size=40, gap=args.gap
    )
    technical_lookup = technical.copy()
    technical_lookup["trading_date"] = pd.to_datetime(
        technical_lookup["trading_date"], errors="raise"
    )
    technical_lookup = technical_lookup.set_index("trading_date")
    if technical_lookup.index.has_duplicates:
        raise ValueError("technical score data contains duplicate trading dates")

    market_lookup = raw.copy()
    market_lookup["trading_date"] = pd.to_datetime(
        market_lookup["trading_date"], errors="raise"
    )
    market_lookup = market_lookup.set_index("trading_date").sort_index()
    if market_lookup.index.has_duplicates:
        raise ValueError("market OHLCV data contains duplicate trading dates")
    rows: list[pd.DataFrame] = []
    ml_columns = list(feature_columns("stock"))

    for fold_number, fold in enumerate(folds, start=1):
        train = dataset.iloc[fold.train_start : fold.train_end].copy()
        test = dataset.iloc[fold.test_start : fold.test_end].copy()

        try:
            candidate = _select_candidate(train, "stock")
        except ValueError as exc:
            raise ValueError(
                f"outer fold {fold_number} cannot produce a usable inner tuning candidate "
                f"(outer training rows={len(train)}, dataset rows={len(dataset)}): {exc}"
            ) from exc
        model = fit_baseline_model(
            train,
            asset_type="stock",
            config=candidate.config,
        )
        probability = model.predict_proba(test[ml_columns])[:, 1]

        fold_rows: list[dict[str, float | int | pd.Timestamp]] = []
        for idx, (_, test_row) in enumerate(test.iterrows()):
            signal_date = pd.Timestamp(test_row["trading_date"])
            if signal_date not in technical_lookup.index:
                raise ValueError(
                    f"missing technical score for OOS date {signal_date.date()}"
                )
            if signal_date not in market_lookup.index:
                raise ValueError(
                    f"missing market OHLCV for OOS date {signal_date.date()}"
                )

            latest = technical_lookup.loc[signal_date]
            market_row = market_lookup.loc[signal_date]
            risk = calculate_stock_risk_adjustment(latest)
            final_signal = calculate_signal_score(
                float(probability[idx]),
                float(latest["technical_score"]),
                float(risk.adjustment),
            )
            fold_rows.append(
                {
                    "fold": fold_number,
                    "date": signal_date,
                    "open": float(market_row["open"]),
                    "close": float(market_row["close"]),
                    "signal_score": float(final_signal.signal_score),
                    "target": int(test_row["target"]),
                    "forward_return_5d": float(test_row["forward_return_5d"]),
                }
            )
        rows.append(pd.DataFrame(fold_rows))

        y = rows[-1]["target"]
        auc = _safe_auc(y, rows[-1]["signal_score"])
        print(
            f"Fold {fold_number}: inner PR-AUC={candidate.score:.4f}, "
            f"signal ROC={auc if auc is not None else float('nan'):.4f}, "
            f"signal PR={_safe_pr(y, rows[-1]['signal_score']):.4f}"
        )

    oos = pd.concat(rows, ignore_index=True)
    backtest_config = BacktestConfig(
        transaction_cost_bps=args.transaction_cost_bps,
        slippage_bps=args.slippage_bps,
        market_costs={
            "BIST": ExecutionCostConfig(
                transaction_cost_bps=args.transaction_cost_bps,
                slippage_bps=args.slippage_bps,
            )
        },
    )
    fold_backtests = []
    for fold_number, fold_frame in enumerate(rows, start=1):
        # Keep each outer OOS window isolated so the gap between folds cannot
        # be mistaken for an executable next-open observation.
        fold_result = run_signal_score_backtest(
            fold_frame,
            backtest_config=backtest_config,
            market="BIST",
            score_weight_config=SignalScoreWeightConfig(
                maximum_weight=args.max_weight
            ),
        )
        fold_backtests.append(fold_result)

        benchmark_frame = fold_frame[["date", "open", "close"]].copy()
        benchmark_frame["target_weight"] = 1.0
        benchmark_result = run_long_only_backtest(
            benchmark_frame,
            config=backtest_config,
            market="BIST",
        )
        benchmark_no_cost_result = run_long_only_backtest(
            benchmark_frame,
            config=BacktestConfig(
                initial_capital=backtest_config.initial_capital,
                transaction_cost_bps=0.0,
                slippage_bps=0.0,
            ),
            market="BIST",
        )

        metrics = fold_result.backtest.metrics
        benchmark_metrics = benchmark_result.metrics
        benchmark_no_cost_metrics = benchmark_no_cost_result.metrics

        print(f"Backtest Fold {fold_number}:")
        print(
            f"  Window: {fold_frame['date'].min().date()} -> "
            f"{fold_frame['date'].max().date()}"
        )
        print(f"  Signal rows: {len(fold_frame)}")
        print(
            f"  Executed periods: {len(fold_result.backtest.equity_curve)} "
            "(last signal has no in-fold next-open execution)"
        )
        print(f"  Strategy total return: {metrics.total_return:.6f}")
        print(f"  Buy-and-hold total return: {benchmark_metrics.total_return:.6f}")
        print(
            f"  Strategy minus buy-and-hold: "
            f"{metrics.total_return - benchmark_metrics.total_return:.6f}"
        )
        print(
            f"  Costless buy-and-hold total return: "
            f"{benchmark_no_cost_metrics.total_return:.6f}"
        )
        print(f"  Annualized return: {metrics.annualized_return:.6f}")
        print(f"  Annualized volatility: {metrics.annualized_volatility:.6f}")
        print(f"  Sharpe ratio: {metrics.sharpe_ratio:.6f}")
        print(f"  Maximum drawdown: {metrics.maximum_drawdown:.6f}")
        print(f"  Win rate: {metrics.win_rate:.6f}")
        print(f"  Profit factor: {metrics.profit_factor}")
        print(f"  Transaction cost: {metrics.total_transaction_cost:.6f}")
        print(f"  Slippage cost: {metrics.total_slippage_cost:.6f}")
        print(f"  Turnover: {metrics.total_turnover:.6f}")

    print(f"Symbol: {args.symbol.strip().upper()}")
    print(f"Data source: {source}")
    print(f"Raw rows: {len(raw)}")
    print(f"Dataset rows: {len(dataset)}")
    print(f"OOS rows: {len(oos)}")
    print("Backtest strategy: continuous signal score -> linear target weight")
    print(
        f"Signal mapping: score 0..100 -> target weight 0..{args.max_weight:.2f}"
    )
    print(f"Initial capital per fold: {backtest_config.initial_capital:.2f}")
    print("Fold windows are evaluated independently; no cross-fold execution is used.")

    assert len(oos) == 120
    assert len(fold_backtests) == 3
    assert sum(len(item.backtest.equity_curve) for item in fold_backtests) == 117
    for fold_result in fold_backtests:
        metrics = fold_result.backtest.metrics
        assert metrics.total_transaction_cost >= 0.0
        assert metrics.total_slippage_cost >= 0.0
        assert benchmark_metrics.total_transaction_cost >= 0.0
        assert benchmark_metrics.total_slippage_cost >= 0.0
        assert benchmark_no_cost_metrics.total_transaction_cost == 0.0
        assert benchmark_no_cost_metrics.total_slippage_cost == 0.0
        assert (fold_result.backtest.equity_curve["cash"] >= 0.0).all()
        assert (benchmark_result.equity_curve["cash"] >= 0.0).all()
    print("REAL BACKTEST SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
