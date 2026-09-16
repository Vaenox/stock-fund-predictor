"""create initial market data schema

Revision ID: 0001_initial_market_data
Revises:
Create Date: 2026-09-15
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_market_data"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create PostgreSQL enum types explicitly once. ``create_type=False``
    # prevents SQLAlchemy from trying to CREATE TYPE again while creating
    # the table columns below.
    asset_type = postgresql.ENUM(
        "STOCK",
        "FUND",
        name="asset_type",
        create_type=False,
    )
    asset_status = postgresql.ENUM(
        "ACTIVE",
        "INACTIVE",
        name="asset_status",
        create_type=False,
    )
    asset_type.create(op.get_bind(), checkfirst=True)
    asset_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("asset_type", asset_type, nullable=False),
        sa.Column("canonical_symbol", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("isin", sa.String(length=32), nullable=True),
        sa.Column("exchange", sa.String(length=32), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="TRY"),
        sa.Column("status", asset_status, nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("canonical_symbol", name="uq_assets_canonical_symbol"),
    )

    op.create_table(
        "asset_provider_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_symbol", sa.String(length=128), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("provider", "provider_symbol", name="uq_provider_symbol"),
    )
    op.create_index("ix_asset_provider_mappings_asset_id", "asset_provider_mappings", ["asset_id"])

    op.create_table(
        "stock_daily_bars",
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trading_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(20, 8), nullable=False),
        sa.Column("high", sa.Numeric(20, 8), nullable=False),
        sa.Column("low", sa.Numeric(20, 8), nullable=False),
        sa.Column("close", sa.Numeric(20, 8), nullable=False),
        sa.Column("adjusted_close", sa.Numeric(20, 8), nullable=True),
        sa.Column("volume", sa.Numeric(24, 4), nullable=True),
        sa.Column("turnover", sa.Numeric(24, 4), nullable=True),
        sa.Column("source_provider", sa.String(length=32), nullable=False),
        sa.Column("source_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("asset_id", "trading_date"),
    )
    op.create_index("ix_stock_daily_bars_date", "stock_daily_bars", ["trading_date"])

    op.create_table(
        "fund_daily_prices",
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pricing_date", sa.Date(), nullable=False),
        sa.Column("unit_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("total_net_assets", sa.Numeric(24, 4), nullable=True),
        sa.Column("source_provider", sa.String(length=32), nullable=False),
        sa.Column("source_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("asset_id", "pricing_date"),
    )
    op.create_index("ix_fund_daily_prices_date", "fund_daily_prices", ["pricing_date"])

    # TimescaleDB hypertables are created conditionally so the migration
    # remains runnable on plain PostgreSQL during local development/CI.
    op.execute(
        "DO $$ BEGIN "
        "IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN "
        "PERFORM create_hypertable('stock_daily_bars', 'trading_date', if_not_exists => TRUE); "
        "PERFORM create_hypertable('fund_daily_prices', 'pricing_date', if_not_exists => TRUE); "
        "END IF; END $$;"
    )


def downgrade() -> None:
    op.drop_index("ix_fund_daily_prices_date", table_name="fund_daily_prices")
    op.drop_table("fund_daily_prices")
    op.drop_index("ix_stock_daily_bars_date", table_name="stock_daily_bars")
    op.drop_table("stock_daily_bars")
    op.drop_index("ix_asset_provider_mappings_asset_id", table_name="asset_provider_mappings")
    op.drop_table("asset_provider_mappings")
    op.drop_table("assets")
    op.execute("DROP TYPE IF EXISTS asset_status")
    op.execute("DROP TYPE IF EXISTS asset_type")
