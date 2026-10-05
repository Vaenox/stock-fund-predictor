from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.prediction_history import PredictionHistory
from app.schemas.prediction_history import PredictionHistoryCreate


def record_prediction(
    session: Session,
    payload: PredictionHistoryCreate,
) -> PredictionHistory:
    """Append one prediction record and return the persisted entity.

    Prediction history is intentionally append-only. Re-running a prediction
    creates a new audit record instead of overwriting an earlier result.
    """
    record = PredictionHistory(**payload.model_dump())
    session.add(record)
    try:
        session.commit()
        session.refresh(record)
    except Exception:
        session.rollback()
        raise
    return record


def record_predictions(
    session: Session,
    payloads: list[PredictionHistoryCreate],
) -> list[PredictionHistory]:
    """Append a batch of prediction records atomically."""
    if not payloads:
        return []

    records = [PredictionHistory(**payload.model_dump()) for payload in payloads]
    session.add_all(records)
    try:
        session.commit()
        for record in records:
            session.refresh(record)
    except Exception:
        session.rollback()
        raise
    return records


def list_predictions(
    session: Session,
    *,
    asset_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[PredictionHistory]:
    """Return prediction history newest-first for one asset."""
    if limit <= 0 or limit > 500:
        raise ValueError("limit must be between 1 and 500")
    if offset < 0:
        raise ValueError("offset cannot be negative")
    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("start_date cannot be after end_date")

    stmt: Select[tuple[PredictionHistory]] = select(PredictionHistory).where(
        PredictionHistory.asset_id == asset_id
    )
    if start_date is not None:
        stmt = stmt.where(PredictionHistory.prediction_date >= start_date)
    if end_date is not None:
        stmt = stmt.where(PredictionHistory.prediction_date <= end_date)

    stmt = (
        stmt.order_by(
            PredictionHistory.prediction_date.desc(),
            PredictionHistory.generated_at.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(stmt).all())


def get_latest_prediction(
    session: Session,
    *,
    asset_id: UUID,
) -> PredictionHistory | None:
    """Return the latest generated prediction for one asset."""
    stmt = (
        select(PredictionHistory)
        .where(PredictionHistory.asset_id == asset_id)
        .order_by(
            PredictionHistory.prediction_date.desc(),
            PredictionHistory.generated_at.desc(),
        )
        .limit(1)
    )
    return session.scalar(stmt)
