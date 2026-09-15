from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.market_data import AssetStatus, AssetType


class AssetCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    asset_type: AssetType
    canonical_symbol: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=255)
    isin: str | None = Field(default=None, max_length=32)
    exchange: str | None = Field(default=None, max_length=32)
    currency: str = Field(default="TRY", min_length=3, max_length=8)
    status: AssetStatus = AssetStatus.ACTIVE


class AssetProviderMappingCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    asset_id: UUID
    provider: str = Field(min_length=1, max_length=32)
    provider_symbol: str = Field(min_length=1, max_length=128)
    is_primary: bool = False


class StockDailyBarCreate(BaseModel):
    asset_id: UUID
    trading_date: date
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)
    adjusted_close: Decimal | None = Field(default=None, gt=0)
    volume: Decimal | None = Field(default=None, ge=0)
    turnover: Decimal | None = Field(default=None, ge=0)
    source_provider: str = Field(min_length=1, max_length=32)
    source_timestamp: datetime | None = None
    ingested_at: datetime

    @model_validator(mode="after")
    def validate_ohlc(self):
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be >= open, close and low")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be <= open, close and high")
        return self


class FundDailyPriceCreate(BaseModel):
    asset_id: UUID
    pricing_date: date
    unit_price: Decimal = Field(gt=0)
    total_net_assets: Decimal | None = Field(default=None, ge=0)
    source_provider: str = Field(min_length=1, max_length=32)
    source_timestamp: datetime | None = None
    ingested_at: datetime
