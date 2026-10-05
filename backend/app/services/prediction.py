from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal
from uuid import UUID

import pandas as pd

from app.analysis.features import MLFeatureConfig, build_inference_features, build_ml_feature_dataset, feature_columns
from app.analysis.indicators import calculate_fund_indicators, calculate_stock_indicators
from app.analysis.scoring import calculate_fund_technical_score, calculate_stock_technical_score
from app.backtesting.strategy import SignalScoreWeightConfig, map_signal_scores_to_target_weights
from app.ml.risk_adjustment import calculate_fund_risk_adjustment, calculate_stock_risk_adjustment
from app.ml.signal import calculate_signal_score
from app.ml.tuning import TuningConfig, select_best_candidate
from app.ml.xgboost_baseline import fit_baseline_model
from app.schemas.prediction_history import PredictionHistoryCreate


AssetKind = Literal["stock", "fund"]


@dataclass(frozen=True, slots=True)
class PredictionGenerationResult:
    payload: PredictionHistoryCreate
    raw_rows: int
    training_rows: int
    inner_pr_auc: float
    model_version: str


def _model_version(config) -> str:
    return (
        f"xgboost-n{config.n_estimators}"
        f"-d{config.max_depth}"
        f"-lr{config.learning_rate:.4f}"
        f"-mcw{config.min_child_weight:g}"
        f"-ss{config.subsample:.2f}"
        f"-cs{config.colsample_bytree:.2f}"
        f"-rl{config.reg_lambda:g}"
        f"-rs{config.random_state}"
    )


def _latest_date(scored: pd.DataFrame, asset_type: AssetKind) -> date:
    column = "trading_date" if asset_type == "stock" else "pricing_date"
    value = scored.iloc[-1][column]
    return pd.Timestamp(value).date()


def generate_latest_prediction(
    *,
    asset_id: UUID,
    asset_type: AssetKind,
    raw_frame: pd.DataFrame,
    source_provider: str,
    quality_ok: bool = True,
    stale_days: int = 0,
    generated_at: datetime | None = None,
    gap: int = 5,
    feature_config: MLFeatureConfig | None = None,
) -> PredictionGenerationResult:
    """Generate one current prediction using the existing production signal chain.

    This function intentionally does not write to the database. Callers decide
    whether the resulting validated payload should be persisted.
    """
    if gap < 5:
        raise ValueError("gap must be at least 5")
    if stale_days < 0:
        raise ValueError("stale_days cannot be negative")
    if not source_provider.strip():
        raise ValueError("source_provider must be non-empty")

    ml_config = feature_config or MLFeatureConfig(horizon=5, positive_return_threshold=0.03)

    if asset_type == "stock":
        indicators = calculate_stock_indicators(raw_frame)
        scored = calculate_stock_technical_score(indicators)
    elif asset_type == "fund":
        indicators = calculate_fund_indicators(raw_frame)
        scored = calculate_fund_technical_score(indicators)
    else:
        raise ValueError(f"unsupported asset_type: {asset_type}")

    dataset = build_ml_feature_dataset(
        indicators,
        asset_type=asset_type,
        config=ml_config,
    )
    inference = build_inference_features(indicators, asset_type=asset_type)
    if dataset.empty or inference.empty:
        raise ValueError("insufficient data for latest prediction")

    tuning = select_best_candidate(
        dataset,
        asset_type=asset_type,
        tuning_config=TuningConfig(
            n_inner_splits=2,
            inner_test_size=20,
            gap=gap,
        ),
    )
    model = fit_baseline_model(
        dataset,
        asset_type=asset_type,
        config=tuning.config,
    )

    feature_frame = inference.iloc[[-1]][list(feature_columns(asset_type))]
    ml_probability = float(model.predict_proba(feature_frame)[:, 1][0])
    latest_row = scored.iloc[-1]

    if asset_type == "stock":
        risk = calculate_stock_risk_adjustment(
            latest_row,
            quality_ok=quality_ok,
            stale_days=stale_days,
        )
    else:
        risk = calculate_fund_risk_adjustment(
            latest_row,
            quality_ok=quality_ok,
            stale_days=stale_days,
        )

    signal = calculate_signal_score(
        ml_probability,
        float(latest_row["technical_score"]),
        risk.adjustment,
    )

    weight = float(
        map_signal_scores_to_target_weights(
            pd.Series([signal.signal_score], dtype=float),
            config=SignalScoreWeightConfig(),
            policy="linear",
        ).iloc[0]
    )

    prediction_date = _latest_date(scored, asset_type)
    generation_time = generated_at or datetime.now(timezone.utc)
    if generation_time.tzinfo is None or generation_time.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware")

    technical_reason = str(latest_row.get("technical_score_reason", "")).strip()
    reasons = [*risk.reasons, *signal.reasons]
    if technical_reason:
        reasons.insert(0, technical_reason)

    payload = PredictionHistoryCreate(
        asset_id=asset_id,
        prediction_date=prediction_date,
        generated_at=generation_time,
        data_as_of=prediction_date,
        horizon_days=ml_config.horizon,
        target_return_threshold=Decimal(str(ml_config.positive_return_threshold)),
        model_family="xgboost",
        model_version=_model_version(tuning.config),
        feature_representation="raw_all",
        ml_probability=Decimal(str(signal.ml_probability)),
        technical_score=Decimal(str(signal.technical_score)),
        risk_score=Decimal(str(risk.risk_score)),
        risk_adjustment=Decimal(str(signal.risk_adjustment)),
        signal_score=Decimal(str(signal.signal_score)),
        target_weight=Decimal(str(weight)),
        quality_ok=quality_ok,
        stale_days=stale_days,
        source_provider=source_provider.strip().lower(),
        reasons=reasons,
    )

    return PredictionGenerationResult(
        payload=payload,
        raw_rows=len(raw_frame),
        training_rows=len(dataset),
        inner_pr_auc=float(tuning.score),
        model_version=payload.model_version or "",
    )
