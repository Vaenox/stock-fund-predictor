from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas.assets import AssetResponse
from app.api.schemas.predictions import PredictionHistoryResponse
from app.data.prediction_history import get_latest_prediction, list_predictions
from app.db import get_db
from app.models.market_data import Asset


router = APIRouter(prefix="/assets", tags=["assets"])


def _load_asset(session: Session, symbol: str) -> Asset:
    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol:
        raise HTTPException(status_code=400, detail="symbol cannot be empty")

    statement = select(Asset).where(Asset.canonical_symbol == normalized_symbol)
    asset = session.scalar(statement)
    if asset is None:
        raise HTTPException(
            status_code=404,
            detail=f"asset not found: {normalized_symbol}",
        )
    return asset


def _asset_uuid(asset: Asset) -> UUID:
    return asset.id


@router.get(
    "/{symbol}",
    response_model=AssetResponse,
    summary="Get asset metadata",
)
def get_asset(
    symbol: str,
    session: Session = Depends(get_db),
) -> Asset:
    return _load_asset(session, symbol)


@router.get(
    "/{symbol}/predictions/latest",
    response_model=PredictionHistoryResponse,
    summary="Get the latest persisted prediction",
)
def get_latest_asset_prediction(
    symbol: str,
    session: Session = Depends(get_db),
) -> PredictionHistoryResponse:
    asset = _load_asset(session, symbol)
    prediction = get_latest_prediction(session, asset_id=_asset_uuid(asset))
    if prediction is None:
        raise HTTPException(
            status_code=404,
            detail=f"no prediction history for asset: {asset.canonical_symbol}",
        )
    return prediction


@router.get(
    "/{symbol}/predictions",
    response_model=list[PredictionHistoryResponse],
    summary="List persisted prediction history",
)
def get_asset_predictions(
    symbol: str,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
) -> list[PredictionHistoryResponse]:
    asset = _load_asset(session, symbol)

    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date cannot be after end_date",
        )

    return list_predictions(
        session,
        asset_id=_asset_uuid(asset),
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
