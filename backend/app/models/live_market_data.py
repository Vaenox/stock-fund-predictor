from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class StockLiveTick(Base):
    __tablename__ = "stock_live_ticks"

    asset_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    price: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    bid: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    ask: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    volume: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    change_percent: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    source_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StockLiveCandle(Base):
    __tablename__ = "stock_live_candles"

    asset_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True
    )
    interval: Mapped[str] = mapped_column(String(16), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    open: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 8), nullable=False)
    volume: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    source_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
