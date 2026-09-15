from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AssetType(StrEnum):
    STOCK = "STOCK"
    FUND = "FUND"


class AssetStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Asset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assets"

    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, name="asset_type"), nullable=False
    )
    canonical_symbol: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    isin: Mapped[str | None] = mapped_column(String(32))
    exchange: Mapped[str | None] = mapped_column(String(32))
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="TRY")
    status: Mapped[AssetStatus] = mapped_column(
        Enum(AssetStatus, name="asset_status"),
        nullable=False,
        default=AssetStatus.ACTIVE,
    )


class AssetProviderMapping(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "asset_provider_mappings"

    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_symbol: Mapped[str] = mapped_column(String(128), nullable=False)
    is_primary: Mapped[bool] = mapped_column(nullable=False, default=False)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("provider", "provider_symbol", name="uq_provider_symbol"),
        Index("ix_asset_provider_mappings_asset_id", "asset_id"),
    )


class StockDailyBar(Base):
    __tablename__ = "stock_daily_bars"

    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True
    )
    trading_date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    adjusted_close: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    volume: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    turnover: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    source_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    source_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        Index("ix_stock_daily_bars_date", "trading_date"),
        Index("ix_stock_daily_bars_asset_date", "asset_id", "trading_date"),
    )


class FundDailyPrice(Base):
    __tablename__ = "fund_daily_prices"

    asset_id: Mapped[UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True
    )
    pricing_date: Mapped[date] = mapped_column(Date, primary_key=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    total_net_assets: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    source_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    source_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        Index("ix_fund_daily_prices_date", "pricing_date"),
        Index("ix_fund_daily_prices_asset_date", "asset_id", "pricing_date"),
    )
