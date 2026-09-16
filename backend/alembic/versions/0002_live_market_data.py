"""add live market time-series tables

Revision ID: 0002_live_market_data
Revises: 0001_initial_market_data
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_live_market_data"
down_revision = "0001_initial_market_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stock_live_ticks",
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price", sa.Numeric(20, 8), nullable=False),
        sa.Column("bid", sa.Numeric(20, 8), nullable=True),
        sa.Column("ask", sa.Numeric(20, 8), nullable=True),
        sa.Column("volume", sa.Numeric(24, 8), nullable=True),
        sa.Column("change_percent", sa.Numeric(12, 6), nullable=True),
        sa.Column("source_provider", sa.String(length=64), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("asset_id", "occurred_at"),
    )

    op.create_table(
        "stock_live_candles",
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("interval", sa.String(length=16), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(20, 8), nullable=False),
        sa.Column("high", sa.Numeric(20, 8), nullable=False),
        sa.Column("low", sa.Numeric(20, 8), nullable=False),
        sa.Column("close", sa.Numeric(20, 8), nullable=False),
        sa.Column("volume", sa.Numeric(24, 8), nullable=True),
        sa.Column("source_provider", sa.String(length=64), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("asset_id", "interval", "occurred_at"),
    )

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "pg_extension" in inspector.get_table_names():
        pass

    if bind.dialect.name == "postgresql":
        op.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
                    PERFORM create_hypertable('stock_live_ticks', 'occurred_at', if_not_exists => TRUE);
                    PERFORM create_hypertable('stock_live_candles', 'occurred_at', if_not_exists => TRUE);
                END IF;
            END $$;
            """
        )


def downgrade() -> None:
    op.drop_table("stock_live_candles")
    op.drop_table("stock_live_ticks")
