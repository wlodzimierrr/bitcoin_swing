"""create raw generic series

Revision ID: 0014_create_raw_generic_series
Revises: 0013_create_raw_etf_flows
Create Date: 2026-08-25 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0014_create_raw_generic_series"
down_revision = "0013_create_raw_etf_flows"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    op.create_table(
        "generic_series",
        sa.Column(
            "series_id",
            sa.String(length=128),
            nullable=False,
            comment=(
                "Stable provider or application identifier, e.g. VIX, DXY, "
                "M2_GLOBAL, BTC_ACTIVE_ADDRESSES."
            ),
        ),
        sa.Column(
            "series_type",
            sa.String(length=32),
            nullable=False,
            comment="Series family: macro, liquidity, onchain, or market_proxy.",
        ),
        sa.Column(
            "observation_time",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="UTC timestamp for the economic, liquidity, or on-chain observation.",
        ),
        sa.Column("value", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column(
            "unit",
            sa.String(length=64),
            nullable=False,
            comment="Measurement unit, e.g. index_points, percent, usd, btc, count.",
        ),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column(
            "revision",
            sa.String(length=64),
            nullable=False,
            comment="Provider revision identifier; use initial when no explicit revision exists.",
        ),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="UTC time this specific revision first became available to the system.",
        ),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "series_type in ('macro', 'liquidity', 'onchain', 'market_proxy')",
            name="ck_generic_series_type_valid",
        ),
        sa.PrimaryKeyConstraint(
            "series_id",
            "observation_time",
            "provider",
            "revision",
            "available_at",
            name="pk_raw_generic_series",
        ),
        schema="raw",
        comment=(
            "Point-in-time generic macro, liquidity, market-proxy, and on-chain "
            "series observations with revisions preserved."
        ),
    )
    op.create_index(
        "ix_raw_generic_series_available_at",
        "generic_series",
        ["available_at"],
        schema="raw",
    )
    op.create_index(
        "ix_raw_generic_series_observation_time",
        "generic_series",
        ["observation_time"],
        schema="raw",
    )


def downgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    op.drop_table("generic_series", schema="raw")
