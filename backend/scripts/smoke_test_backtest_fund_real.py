from __future__ import annotations

import argparse
import time
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import create_engine, text
from sklearn.metrics import average_precision_score, roc_auc_score

from app.analysis.features import MLFeatureConfig, build_ml_feature_dataset, feature_columns
from app.analysis.indicators import calculate_fund_indicators
from app.analysis.scoring import calculate_fund_technical_score
from app.backtesting.fund_engine import FundBacktestConfig, run_long_only_fund_backtest
from app.backtesting.strategy import SignalScoreWeightConfig, map_signal_scores_to_target_weights
from app.core.settings import get_settings
from app.data.providers.tefas import TefasProvider
from app.ml.risk_adjustment import calculate_fund_risk_adjustment
from app.ml.signal import calculate_signal_score
from app.ml.splitting import build_walk_forward_splits
from app.ml.tuning import TuningConfig
from app.ml.xgboost_baseline import fit_baseline_model

from smoke_test_signal_chain_real import _select_best_candidate_sparse


def _fund_frame_provider(
    symbol: str,
    days: int,
    chunk_delay: float,
) -> pd.DataFrame:
    provider = TefasProvider()
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    records = []
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


def _load_fund(
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
        SELECT p.pricing_date, p.unit_price
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
        _fund_frame_provider(symbol, days, chunk_delay),
        "TEFAS provider (DB history insufficient)",
    )


def _safe_auc(y: pd.Series, score: pd.Series) -> float | None:
    if y.nunique() < 2:
        return None
    return float(roc_auc_score(y.astype(int), score.astype(float)))


def _safe_pr(y: pd.Series, score: pd.Series) -> float:
    if y.nunique() < 2:
        return float("nan")
    return float(average_precision_score(y.astype(int), score.astype(float)))


def _buy_and_hold_total_return(
    frame: pd.DataFrame,
    *,
    config: FundBacktestConfig,
) -> tuple[float, float, float]:
    """True first-execution-next-day-price -> final-price buy-and-hold."""
    if len(frame) < 2:
        raise ValueError("fund buy-and-hold requires at least two observations")

    opening = float(frame.iloc[1]["unit_price"])
    final_price = float(frame.iloc[-1]["unit_price"])
    capital = float(config.initial_capital)
    fee_rate = config.transaction_cost_bps / 10_000.0

    units = capital / (opening * (1.0 + fee_rate))
    trade_notional = units * opening
    transaction_cost = trade_notional * fee_rate
    cash = capital - trade_notional - transaction_cost

    if abs(cash) < 1e-8:
        cash = 0.0
    if cash < -1e-8:
        raise AssertionError("fund buy-and-hold produced negative cash")

    final_equity = cash + units * final_price
    return (
        final_equity / capital - 1.0,
        transaction_cost,
        cash,
    )


def _run_symbol(
    symbol: str,
    *,
    days: int,
    gap: int,
    min_db_rows: int,
    threshold: float,
    transaction_cost_bps: float,
    max_weight: float,
    chunk_delay: float,
) -> list[dict[str, float | int | str]]:
    raw, source = _load_fund(symbol, days, min_db_rows, chunk_delay)
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

    columns = list(feature_columns("fund"))
    tuning_config = TuningConfig(
        n_inner_splits=2,
        inner_test_size=20,
        gap=gap,
    )
    backtest_config = FundBacktestConfig(
        transaction_cost_bps=transaction_cost_bps,
    )
    score_config = SignalScoreWeightConfig(maximum_weight=max_weight)

    results: list[dict[str, float | int | str]] = []

    print("=" * 96)
    print(f"Fund: {symbol}")
    print(f"Data source: {source}")
    print(f"Raw rows: {len(raw)} | Dataset rows: {len(dataset)}")
    print(
        f"OOS protocol: 3 x 40 test observations | gap={gap} | "
        f"target=h5/{threshold:.2%}"
    )
    print(
        f"Execution: next-day unit_price | transaction_cost={transaction_cost_bps:.2f} bps | "
        "slippage=0 bps"
    )
    print("-" * 96)

    for fold_number, fold in enumerate(folds, start=1):
        train = dataset.iloc[fold.train_start : fold.train_end].copy()
        test = dataset.iloc[fold.test_start : fold.test_end].copy()

        tuning = _select_best_candidate_sparse(
            train,
            asset_type="fund",
            tuning_config=tuning_config,
        )
        model = fit_baseline_model(
            train,
            asset_type="fund",
            config=tuning.config,
        )
        probability = model.predict_proba(test[columns])[:, 1]

        fold_rows: list[dict[str, float | int | pd.Timestamp]] = []
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
            market_row = price_lookup.loc[signal_date]
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

            fold_rows.append(
                {
                    "fold": fold_number,
                    "date": signal_date,
                    "unit_price": float(market_row["unit_price"]),
                    "signal_score": float(signal.signal_score),
                    "target_weight": weight,
                    "target": int(test_row["target"]),
                    "forward_return_5d": float(test_row["forward_return_5d"]),
                }
            )

        fold_frame = pd.DataFrame(fold_rows)
        strategy = run_long_only_fund_backtest(
            fold_frame,
            config=backtest_config,
            date_column="date",
            price_column="unit_price",
            target_column="target_weight",
        )

        benchmark_return, benchmark_cost, benchmark_cash = _buy_and_hold_total_return(
            fold_frame,
            config=backtest_config,
        )
        costless_benchmark_return, costless_benchmark_cost, costless_benchmark_cash = (
            _buy_and_hold_total_return(
                fold_frame,
                config=FundBacktestConfig(
                    initial_capital=backtest_config.initial_capital,
                    transaction_cost_bps=0.0,
                    periods_per_year=backtest_config.periods_per_year,
                ),
            )
        )

        y = fold_frame["target"]
        signal_roc = _safe_auc(y, fold_frame["signal_score"])
        signal_pr = _safe_pr(y, fold_frame["signal_score"])
        metrics = strategy.metrics

        results.append(
            {
                "symbol": symbol,
                "fold": fold_number,
                "strategy_return": metrics.total_return,
                "benchmark_return": benchmark_return,
                "excess_return": metrics.total_return - benchmark_return,
                "sharpe": metrics.sharpe_ratio,
                "max_drawdown": metrics.maximum_drawdown,
                "turnover": metrics.total_turnover,
                "transaction_cost": metrics.total_transaction_cost,
                "signal_roc": signal_roc if signal_roc is not None else float("nan"),
                "signal_pr": signal_pr,
                "inner_pr": float(tuning.score),
            }
        )

        print(
            f"Fold {fold_number}: inner PR-AUC={tuning.score:.4f}, "
            f"signal ROC={signal_roc if signal_roc is not None else float('nan'):.4f}, "
            f"signal PR={signal_pr:.4f}"
        )
        print(
            f"  Window: {fold_frame['date'].min().date()} -> "
            f"{fold_frame['date'].max().date()}"
        )
        print(
            f"  Strategy return: {metrics.total_return:+.4%} | "
            f"B&H: {benchmark_return:+.4%} | "
            f"Excess: {metrics.total_return - benchmark_return:+.4%}"
        )
        print(
            f"  Costless B&H: {costless_benchmark_return:+.4%} | "
            f"Strategy Sharpe: {metrics.sharpe_ratio:+.3f} | "
            f"MaxDD: {metrics.maximum_drawdown:+.4%} | "
            f"Turnover: {metrics.total_turnover:.4f}"
        )
        print(
            f"  Strategy transaction cost: {metrics.total_transaction_cost:.6f} | "
            f"B&H transaction cost: {benchmark_cost:.6f} | "
            f"Executed periods: {len(strategy.equity_curve)}"
        )

        if benchmark_cash < -1e-8 or costless_benchmark_cash < -1e-8:
            raise AssertionError("benchmark cash must not be negative")
        if abs(costless_benchmark_cost) > 1e-12:
            raise AssertionError("costless benchmark must have zero transaction cost")
        if len(strategy.equity_curve) != 39:
            raise AssertionError("each 40-row OOS fold must produce 39 executed periods")

    results_frame = pd.DataFrame(results)
    print("-" * 96)
    print(
        f"{symbol} aggregate: mean strategy={results_frame['strategy_return'].mean():+.4%}, "
        f"mean B&H={results_frame['benchmark_return'].mean():+.4%}, "
        f"mean excess={results_frame['excess_return'].mean():+.4%}, "
        f"positive excess={(results_frame['excess_return'] > 0).mean():.2%}, "
        f"mean Sharpe={results_frame['sharpe'].mean():+.3f}"
    )

    assert len(results) == 3
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a leakage-safe real fund OOS backtest using daily unit-price execution."
    )
    parser.add_argument("--symbols", default="AFA,AFT")
    parser.add_argument("--days", type=int, default=1000)
    parser.add_argument("--gap", type=int, default=5)
    parser.add_argument("--min-db-rows", type=int, default=365)
    parser.add_argument("--threshold", type=float, default=0.03)
    parser.add_argument("--transaction-cost-bps", type=float, default=10.0)
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
    if args.transaction_cost_bps < 0:
        raise SystemExit("transaction-cost-bps cannot be negative")
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

    all_results: list[dict[str, float | int | str]] = []
    failures: list[tuple[str, str]] = []

    for symbol in symbols:
        try:
            all_results.extend(
                _run_symbol(
                    symbol,
                    days=args.days,
                    gap=args.gap,
                    min_db_rows=args.min_db_rows,
                    threshold=args.threshold,
                    transaction_cost_bps=args.transaction_cost_bps,
                    max_weight=args.max_weight,
                    chunk_delay=args.chunk_delay,
                )
            )
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

    frame = pd.DataFrame(all_results)
    print("=" * 96)
    print("CROSS-FUND SUMMARY")
    print(f"Successful funds: {frame['symbol'].nunique()}")
    print(f"Outer folds: {len(frame)}")
    print(f"Mean strategy return: {frame['strategy_return'].mean():+.4%}")
    print(f"Mean B&H return: {frame['benchmark_return'].mean():+.4%}")
    print(f"Mean excess return: {frame['excess_return'].mean():+.4%}")
    print(f"Median excess return: {frame['excess_return'].median():+.4%}")
    print(
        f"Positive excess fold rate: "
        f"{(frame['excess_return'] > 0).mean():.2%}"
    )
    print(f"Mean Sharpe: {frame['sharpe'].mean():+.3f}")
    print(f"Mean max drawdown: {frame['max_drawdown'].mean():+.4%}")
    print(f"Mean turnover: {frame['turnover'].mean():.4f}")
    print(f"Total transaction cost: {frame['transaction_cost'].sum():.6f}")
    print(f"Signal mean ROC-AUC: {frame['signal_roc'].mean():.4f}")
    print(f"Signal mean PR-AUC: {frame['signal_pr'].mean():.4f}")

    assert len(frame) == len(symbols) * 3
    assert (frame["transaction_cost"] >= 0.0).all()
    assert (frame["turnover"] >= 0.0).all()
    print("REAL FUND BACKTEST SMOKE TEST PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
