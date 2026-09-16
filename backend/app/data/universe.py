from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.data.providers.base import MarketDataProvider, ProviderSymbol
from app.models.market_data import Asset, AssetProviderMapping, AssetStatus, AssetType


@dataclass(frozen=True, slots=True)
class UniverseSyncResult:
    provider: str
    discovered: int
    assets_created: int
    mappings_created: int
    mappings_updated: int


def sync_provider_universe(
    session: Session,
    provider: MarketDataProvider,
    *,
    asset_type: AssetType,
) -> UniverseSyncResult:
    symbols = provider.list_symbols()
    symbols = [
        symbol
        for symbol in symbols
        if symbol.asset_type.upper() == asset_type.value
    ]

    discovered = len(symbols)
    assets_created = 0
    mappings_created = 0
    mappings_updated = 0
    now = datetime.now(timezone.utc)

    try:
        for symbol in symbols:
            canonical_symbol = symbol.canonical_symbol.strip().upper()
            provider_symbol = symbol.provider_symbol.strip().upper()
            if not canonical_symbol or not provider_symbol or not symbol.name.strip():
                raise ValueError("Provider universe contains an incomplete symbol record")

            asset = session.scalar(
                select(Asset).where(Asset.canonical_symbol == canonical_symbol)
            )
            if asset is None:
                asset = Asset(
                    asset_type=asset_type,
                    canonical_symbol=canonical_symbol,
                    name=symbol.name.strip(),
                    isin=symbol.isin,
                    exchange=symbol.exchange or "BIST",
                    currency=symbol.currency.upper(),
                    status=AssetStatus.ACTIVE,
                )
                session.add(asset)
                session.flush()
                assets_created += 1
            elif asset.asset_type != asset_type:
                raise ValueError(
                    f"Canonical symbol {canonical_symbol} already exists as {asset.asset_type}"
                )

            mapping = session.scalar(
                select(AssetProviderMapping).where(
                    AssetProviderMapping.provider == provider.name,
                    AssetProviderMapping.provider_symbol == provider_symbol,
                )
            )
            if mapping is None:
                session.add(
                    AssetProviderMapping(
                        asset_id=asset.id,
                        provider=provider.name,
                        provider_symbol=provider_symbol,
                        is_primary=True,
                        first_seen_at=now,
                        last_seen_at=now,
                    )
                )
                mappings_created += 1
            else:
                mapping.asset_id = asset.id
                mapping.last_seen_at = now
                mappings_updated += 1

        session.commit()
    except Exception:
        session.rollback()
        raise

    return UniverseSyncResult(
        provider=provider.name,
        discovered=discovered,
        assets_created=assets_created,
        mappings_created=mappings_created,
        mappings_updated=mappings_updated,
    )
