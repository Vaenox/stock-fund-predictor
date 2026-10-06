from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.market_data import AssetStatus, AssetType


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_type: AssetType
    canonical_symbol: str
    name: str
    isin: str | None
    exchange: str | None
    currency: str
    status: AssetStatus
