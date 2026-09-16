from __future__ import annotations

import argparse

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.data.universe import sync_provider_universe
from app.data.providers.borsapy import BorsapyProvider
from app.models.market_data import AssetType


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync the complete BIST stock universe.")
    parser.parse_args()

    settings = get_settings()
    engine = create_engine(settings.database_url, future=True)
    provider = BorsapyProvider()

    with Session(engine) as session:
        result = sync_provider_universe(
            session,
            provider,
            asset_type=AssetType.STOCK,
        )

    print(
        f"provider={result.provider} discovered={result.discovered} "
        f"assets_created={result.assets_created} "
        f"mappings_created={result.mappings_created} "
        f"mappings_updated={result.mappings_updated}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
