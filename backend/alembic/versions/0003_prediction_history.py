"""add append-only prediction history

Revision ID: 0003_prediction_history
Revises: 0002_live_market_data
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_prediction_history"
down_revision = "0002_live_market_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prediction_history",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "asset_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("prediction_date", sa.Date(), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("data_as_of", sa.Date(), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column(
            "target_return_threshold",
            sa.Numeric(10, 8),
            nullable=False,
        ),
        sa.Column("model_family", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=128), nullable=True),
        sa.Column(
            "feature_representation",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("ml_probability", sa.Numeric(12, 10), nullable=False),
        sa.Column("technical_score", sa.Numeric(8, 4), nullable=False),
        sa.Column("risk_score", sa.Numeric(8, 4), nullable=False),
        sa.Column("risk_adjustment", sa.Numeric(8, 4), nullable=False),
        sa.Column("signal_score", sa.Numeric(8, 4), nullable=False),
        sa.Column("target_weight", sa.Numeric(12, 10), nullable=False),
        sa.Column("quality_ok", sa.Boolean(), nullable=False),
        sa.Column("stale_days", sa.Integer(), nullable=False),
        sa.Column("source_provider", sa.String(length=32), nullable=False),
        sa.Column("reasons", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            ondelete="CASCADE",
        ),
    )

    op.create_index(
        "ix_prediction_history_asset_prediction_date",
        "prediction_history",
        ["asset_id", "prediction_date"],
    )
    op.create_index(
        "ix_prediction_history_prediction_date",
        "prediction_history",
        ["prediction_date"],
    )
    op.create_index(
        "ix_prediction_history_generated_at",
        "prediction_history",
        ["generated_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_prediction_history_generated_at",
        table_name="prediction_history",
    )
    op.drop_index(
        "ix_prediction_history_prediction_date",
        table_name="prediction_history",
    )
    op.drop_index(
        "ix_prediction_history_asset_prediction_date",
        table_name="prediction_history",
    )
    op.drop_table("prediction_history")
