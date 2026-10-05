from __future__ import annotations

import argparse
from datetime import date, timedelta

import pandas as pd
from sqlalchemy import create_engine, text

from app.analysis.features import MLFeatureConfig, build_ml_feature_dataset
from app.analysis.indicators import calculate_stock_indicators
from app.analysis.scoring import calculate_stock_technical_score
from app.backtesting.engine import BacktestConfig, ExecutionCostConfig
from app.backtesting.strategy import run_signal_score_backtest
from app.core.settings import get_settings
from app.ml.risk_adjustment import calculate_stock_risk_adjustment
from app.ml.signal import calculate_signal_score
from app.ml.splitting import build_walk_forward_splits
from app.ml.tuning import TuningConfig, build_inner_splits, default_candidate_grid, TuningCandidate
from app.ml.xgboost_baseline import build_model, fit_baseline_model
from sklearn.metrics import average_precision_score, roc_auc_score


def _load_stock(symbol: str, days: int) -> tuple[pd.DataFrame, str]:
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
    if not rows:
        raise ValueError(f"no DB history found for {symbol}")
    return pd.DataFrame(rows), "PostgreSQL canonical history"


def _select_candidate(frame: pd.DataFrame, asset_type: str) -> TuningCandidate:
    columns = [
        c for c in frame.columns
        if c not in {"target", "forward_return_5d", "trading_date"}
    ]
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
    args = parser.parse_args()

    raw, source = _load_stock(args.symbol.strip().upper(), args.days)
    indicators = calculate_stock_indicators(raw)
    technical = calculate_stock_technical_score(indicators)
    dataset = build_ml_feature_dataset(
        indicators,
        asset_type="stock",
        config=MLFeatureConfig(horizon=5, positive_return_threshold=0.03),
    )
    if len(dataset) < 140:
        raise ValueError("not enough observations for backtest")

    folds = build_walk_forward_splits(
        len(dataset), n_splits=3, test_size=40, gap=args.gap
    )
    technical_lookup = technical.set_index("trading_date")
    rows: list[pd.DataFrame] = []
    feature_columns = [
        c for c in dataset.columns
        if c not in {"trading_date", "target", "forward_return_5d"}
    ]

    for fold_number, fold in enumerate(folds, start=1):
        train = dataset.iloc[fold.train_start : fold.train_end].copy()
        test = dataset.iloc[fold.test_start : fold.test_end].copy()

        candidate = _select_candidate(train, "stock")
        model = fit_baseline_model(
            train,
            asset_type="stock",
            config=candidate.config,
        )
        probability = model.predict_proba(test[feature_columns])[:, 1]

        fold_rows: list[dict[str, float | int | pd.Timestamp]] = []
        for idx, (_, test_row) in enumerate(test.iterrows()):
            latest = technical_lookup.loc[test_row["trading_date"]]
            risk = calculate_stock_risk_adjustment(latest)
            final_signal = calculate_signal_score(
                float(probability[idx]),
                float(latest["technical_score"]),
                float(risk.adjustment),
            )
            fold_rows.append(
                {
                    "fold": fold_number,
                    "date": pd.Timestamp(test_row["trading_date"]),
                    "open": float(test_row["open"]),
                    "close": float(test_row["close"]),
                    "signal_score": float(final_signal.signal_score),
                    "target": int(test_row["target"]),
                    "forward_return_5d": float(test_row["forward_return_5d"]),
                }
            )
        rows.append(pd.DataFrame(fold_rows))

        y = rows[-1]["target"]
        print(
            f"Fold {fold_number}: inner PR-AUC={candidate.score:.4f}, "
            f"signal ROC={_safe_auc(y, rows[-1]['signal_score']) if _safe_auc(y, rows[-1]['signal_score']) is not None else float('nan'):.4f}, "
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
    result = run_signal_score_backtest(
        oos,
        backtest_config=backtest_config,
        market="BIST",
        score_weight_config=None,
    )

    metrics = result.backtest.metrics
    print(f"Symbol: {args.symbol.strip().upper()}")
    print(f"Data source: {source}")
    print(f"Raw rows: {len(raw)}")
    print(f"Dataset rows: {len(dataset)}")
    print(f"OOS rows: {len(oos)}")
    print("Backtest strategy: continuous signal score -> linear target weight")
    print("Signal mapping: score 0..100 -> target weight 0..1")
    print(f"Initial capital: {backtest_config.initial_capital:.2f}")
    print(f"Total return: {metrics.total_return:.6f}")
    print(f"Annualized return: {metrics.annualized_return:.6f}")
    print(f"Annualized volatility: {metrics.annualized_volatility:.6f}")
    print(f"Sharpe ratio: {metrics.sharpe_ratio:.6f}")
    print(f"Maximum drawdown: {metrics.maximum_drawdown:.6f}")
    print(f"Win rate: {metrics.win_rate:.6f}")
    print(f"Profit factor: {metrics.profit_factor}")
    print(f"Transaction cost: {metrics.total_transaction_cost:.6f}")
    print(f"Slippage cost: {metrics.total_slippage_cost:.6f}")
    print(f"Turnover: {metrics.total_turnover:.6f}")

    assert len(oos) == 120
    assert metrics.total_transaction_cost >= 0.0
    assert metrics.total_slippage_cost >= 0.0
    assert (result.backtest.equity_curve["cash"] >= 0.0).all()
    print("REAL BACKTEST SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
