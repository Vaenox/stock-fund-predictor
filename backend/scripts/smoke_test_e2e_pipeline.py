from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.data.ingestion import ingest_fund_history, ingest_stock_history
from app.data.quality import inspect_fund_prices, inspect_stock_bars
from app.data.providers.base import (
    MarketDataProvider,
    ProviderFundPrice,
    ProviderStockBar,
    ProviderSymbol,
)
from app.data.validator import DataValidationError
from app.models.market_data import (
    Asset,
    AssetProviderMapping,
    AssetStatus,
    AssetType,
    FundDailyPrice,
    StockDailyBar,
)


TEST_START = date(2026, 9, 14)
TEST_END = date(2026, 9, 15)
VALIDATION_TODAY = date(2026, 9, 16)


class ControlledProvider(MarketDataProvider):
    """Deterministic provider used to exercise the full DB-backed pipeline."""

    def __init__(self, name: str, *, invalid: bool = False) -> None:
        self._name = name
        self._invalid = invalid

    @property
    def name(self) -> str:
        return self._name

    def list_symbols(self) -> list[ProviderSymbol]:
        return []

    def get_symbol_metadata(self, provider_symbol: str) -> ProviderSymbol:
        raise NotImplementedError

    def get_daily_history(
        self,
        provider_symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[ProviderStockBar]:
        if self._invalid:
            return [
                ProviderStockBar(
                    provider_symbol=provider_symbol,
                    trading_date=VALIDATION_TODAY.replace(day=17),
                    open=Decimal("100"),
                    high=Decimal("105"),
                    low=Decimal("99"),
                    close=Decimal("104"),
                    volume=Decimal("1000"),
                    source_timestamp=datetime(2026, 9, 17, tzinfo=timezone.utc),
                )
            ]
        return [
            ProviderStockBar(
                provider_symbol=provider_symbol,
                trading_date=TEST_START,
                open=Decimal("100"),
                high=Decimal("105"),
                low=Decimal("99"),
                close=Decimal("104"),
                volume=Decimal("1000"),
                source_timestamp=datetime(2026, 9, 14, tzinfo=timezone.utc),
            ),
            ProviderStockBar(
                provider_symbol=provider_symbol,
                trading_date=TEST_END,
                open=Decimal("104"),
                high=Decimal("108"),
                low=Decimal("103"),
                close=Decimal("107"),
                volume=Decimal("1200"),
                source_timestamp=datetime(2026, 9, 15, tzinfo=timezone.utc),
            ),
        ]

    def get_latest_price(self, provider_symbol: str) -> ProviderStockBar:
        raise NotImplementedError

    def get_fund_history(
        self,
        provider_symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[ProviderFundPrice]:
        if self._invalid:
            return [
                ProviderFundPrice(
                    provider_symbol=provider_symbol,
                    pricing_date=VALIDATION_TODAY.replace(day=17),
                    unit_price=Decimal("12.34"),
                    total_net_assets=Decimal("1000000"),
                    source_timestamp=datetime(2026, 9, 17, tzinfo=timezone.utc),
                )
            ]
        return [
            ProviderFundPrice(
                provider_symbol=provider_symbol,
                pricing_date=TEST_START,
                unit_price=Decimal("12.345600"),
                total_net_assets=Decimal("1000000"),
                source_timestamp=datetime(2026, 9, 14, tzinfo=timezone.utc),
            ),
            ProviderFundPrice(
                provider_symbol=provider_symbol,
                pricing_date=TEST_END,
                unit_price=Decimal("12.612300"),
                total_net_assets=Decimal("1020000"),
                source_timestamp=datetime(2026, 9, 15, tzinfo=timezone.utc),
            ),
        ]

    def health_check(self) -> bool:
        return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a controlled PostgreSQL end-to-end market-data pipeline smoke test."
    )
    parser.add_argument(
        "--keep-data",
        action="store_true",
        help="Keep temporary E2E assets/rows instead of cleaning them up.",
    )
    return parser.parse_args()


def _ensure_schema(engine) -> None:
    required = {
        "assets",
        "asset_provider_mappings",
        "stock_daily_bars",
        "fund_daily_prices",
    }
    missing = sorted(required - set(inspect(engine).get_table_names()))
    if missing:
        raise RuntimeError(
            "Database schema is incomplete. Run 'alembic upgrade head' first. "
            f"Missing tables: {', '.join(missing)}"
        )


def _create_asset(
    session: Session,
    *,
    asset_type: AssetType,
    symbol: str,
    provider: str,
) -> Asset:
    asset = Asset(
        asset_type=asset_type,
        canonical_symbol=symbol,
        name=symbol,
        exchange="BIST" if asset_type == AssetType.STOCK else "TEFAS",
        currency="TRY",
        status=AssetStatus.ACTIVE,
    )
    session.add(asset)
    session.flush()
    session.add(
        AssetProviderMapping(
            asset_id=asset.id,
            provider=provider,
            provider_symbol=symbol,
            is_primary=True,
        )
    )
    session.commit()
    return asset


def _count(session: Session, table: str, asset_id) -> int:
    return int(
        session.scalar(
            text(f"SELECT COUNT(*) FROM {table} WHERE asset_id = :asset_id"),
            {"asset_id": asset_id},
        )
        or 0
    )


def _assert_stock_quality(session: Session, asset_id) -> None:
    rows = session.execute(
        select(
            StockDailyBar.trading_date,
            StockDailyBar.open,
            StockDailyBar.high,
            StockDailyBar.low,
            StockDailyBar.close,
            StockDailyBar.volume,
            StockDailyBar.source_provider,
        ).where(StockDailyBar.asset_id == asset_id).order_by(StockDailyBar.trading_date)
    ).mappings().all()
    report = inspect_stock_bars(rows, start_date=TEST_START, end_date=TEST_END)
    if not report.ok or report.missing_business_dates or report.extreme_return_dates:
        raise AssertionError(f"stock quality failed: {report}")
    sources = {str(row["source_provider"]) for row in rows}
    if sources != {"e2e-stock"}:
        raise AssertionError(f"unexpected stock sources: {sorted(sources)}")


def _assert_fund_quality(session: Session, asset_id) -> None:
    rows = session.execute(
        select(
            FundDailyPrice.pricing_date,
            FundDailyPrice.unit_price,
            FundDailyPrice.total_net_assets,
            FundDailyPrice.source_provider,
        ).where(FundDailyPrice.asset_id == asset_id).order_by(FundDailyPrice.pricing_date)
    ).mappings().all()
    report = inspect_fund_prices(rows, start_date=TEST_START, end_date=TEST_END)
    if not report.ok or report.missing_business_dates:
        raise AssertionError(f"fund quality failed: {report}")
    sources = {str(row["source_provider"]) for row in rows}
    if sources != {"e2e-fund"}:
        raise AssertionError(f"unexpected fund sources: {sorted(sources)}")


def _assert_invalid_data_is_not_persisted(
    session: Session,
    *,
    asset_type: AssetType,
    asset_id,
    provider: ControlledProvider,
    provider_symbol: str,
) -> None:
    table = "stock_daily_bars" if asset_type == AssetType.STOCK else "fund_daily_prices"
    before = _count(session, table, asset_id)
    try:
        if asset_type == AssetType.STOCK:
            ingest_stock_history(
                session,
                provider,
                asset_id=asset_id,
                provider_symbol=provider_symbol,
                start_date=TEST_START,
                end_date=TEST_END,
                today=VALIDATION_TODAY,
            )
        else:
            ingest_fund_history(
                session,
                provider,
                asset_id=asset_id,
                provider_symbol=provider_symbol,
                start_date=TEST_START,
                end_date=TEST_END,
                today=VALIDATION_TODAY,
            )
    except DataValidationError:
        pass
    else:
        raise AssertionError("expected DataValidationError")

    after = _count(session, table, asset_id)
    if after != before:
        raise AssertionError(
            f"invalid data changed DB row count: before={before} after={after}"
        )


def main() -> int:
    args = parse_args()
    engine = create_engine(get_settings().database_url, future=True)
    _ensure_schema(engine)

    stock_symbol = f"E2ESTK{uuid4().hex[:8].upper()}"
    fund_symbol = f"E2EFND{uuid4().hex[:8].upper()}"
    bad_stock_symbol = f"E2EBADSTK{uuid4().hex[:6].upper()}"
    bad_fund_symbol = f"E2EBADFND{uuid4().hex[:6].upper()}"

    stock_provider = ControlledProvider("e2e-stock")
    fund_provider = ControlledProvider("e2e-fund")
    invalid_stock_provider = ControlledProvider("e2e-bad-stock", invalid=True)
    invalid_fund_provider = ControlledProvider("e2e-bad-fund", invalid=True)
    created_asset_ids = []

    try:
        with Session(engine) as session:
            stock_asset = _create_asset(
                session,
                asset_type=AssetType.STOCK,
                symbol=stock_symbol,
                provider=stock_provider.name,
            )
            fund_asset = _create_asset(
                session,
                asset_type=AssetType.FUND,
                symbol=fund_symbol,
                provider=fund_provider.name,
            )
            bad_stock_asset = _create_asset(
                session,
                asset_type=AssetType.STOCK,
                symbol=bad_stock_symbol,
                provider=invalid_stock_provider.name,
            )
            bad_fund_asset = _create_asset(
                session,
                asset_type=AssetType.FUND,
                symbol=bad_fund_symbol,
                provider=invalid_fund_provider.name,
            )
            created_asset_ids = [
                stock_asset.id,
                fund_asset.id,
                bad_stock_asset.id,
                bad_fund_asset.id,
            ]

            stock_result = ingest_stock_history(
                session,
                stock_provider,
                asset_id=stock_asset.id,
                provider_symbol=stock_symbol,
                start_date=TEST_START,
                end_date=TEST_END,
                today=VALIDATION_TODAY,
            )
            fund_result = ingest_fund_history(
                session,
                fund_provider,
                asset_id=fund_asset.id,
                provider_symbol=fund_symbol,
                start_date=TEST_START,
                end_date=TEST_END,
                today=VALIDATION_TODAY,
            )

            if (stock_result.received, stock_result.written) != (2, 2):
                raise AssertionError(f"unexpected stock ingestion result: {stock_result}")
            if (fund_result.received, fund_result.written) != (2, 2):
                raise AssertionError(f"unexpected fund ingestion result: {fund_result}")

            stock_before = _count(session, "stock_daily_bars", stock_asset.id)
            fund_before = _count(session, "fund_daily_prices", fund_asset.id)
            if stock_before != 2 or fund_before != 2:
                raise AssertionError(
                    f"unexpected first-write counts: stock={stock_before}, fund={fund_before}"
                )

            stock_repeat = ingest_stock_history(
                session,
                stock_provider,
                asset_id=stock_asset.id,
                provider_symbol=stock_symbol,
                start_date=TEST_START,
                end_date=TEST_END,
                today=VALIDATION_TODAY,
            )
            fund_repeat = ingest_fund_history(
                session,
                fund_provider,
                asset_id=fund_asset.id,
                provider_symbol=fund_symbol,
                start_date=TEST_START,
                end_date=TEST_END,
                today=VALIDATION_TODAY,
            )
            stock_after = _count(session, "stock_daily_bars", stock_asset.id)
            fund_after = _count(session, "fund_daily_prices", fund_asset.id)
            if (stock_repeat.written, fund_repeat.written) != (2, 2):
                raise AssertionError("repeat ingestion did not process the expected rows")
            if stock_after != stock_before or fund_after != fund_before:
                raise AssertionError(
                    "upsert duplicated rows: "
                    f"stock {stock_before}->{stock_after}, fund {fund_before}->{fund_after}"
                )

            _assert_stock_quality(session, stock_asset.id)
            _assert_fund_quality(session, fund_asset.id)

            _assert_invalid_data_is_not_persisted(
                session,
                asset_type=AssetType.STOCK,
                asset_id=bad_stock_asset.id,
                provider=invalid_stock_provider,
                provider_symbol=bad_stock_symbol,
            )
            _assert_invalid_data_is_not_persisted(
                session,
                asset_type=AssetType.FUND,
                asset_id=bad_fund_asset.id,
                provider=invalid_fund_provider,
                provider_symbol=bad_fund_symbol,
            )

            print(
                "SUCCESS STOCK: provider -> normalize -> validate -> upsert -> quality "
                f"({stock_before} rows)"
            )
            print(
                "SUCCESS FUND: provider -> normalize -> validate -> upsert -> quality "
                f"({fund_before} rows)"
            )
            print("UPSERT: repeat ingestion preserved row counts")
            print("VALIDATION GUARD: invalid future records were rejected and not persisted")
            print("E2E DATA PIPELINE SMOKE TEST PASSED")

            if args.keep_data:
                return 0

            for asset_id in created_asset_ids:
                session.execute(
                    text("DELETE FROM assets WHERE id = :asset_id"),
                    {"asset_id": asset_id},
                )
            session.commit()

    except Exception as exc:
        print(f"E2E DATA PIPELINE SMOKE TEST FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
