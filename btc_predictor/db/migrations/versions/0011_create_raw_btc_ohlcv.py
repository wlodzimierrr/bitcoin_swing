"""create raw btc ohlcv

Revision ID: 0011_raw_btc_ohlcv
Revises: 0010_core_schemas
Create Date: 2026-08-25 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0011_raw_btc_ohlcv"
down_revision = "0010_core_schemas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    op.create_table(
        "btc_ohlcv",
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("exchange", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("open", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("high", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("low", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("close", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("volume", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("open > 0", name="ck_btc_ohlcv_open_positive"),
        sa.CheckConstraint("high > 0", name="ck_btc_ohlcv_high_positive"),
        sa.CheckConstraint("low > 0", name="ck_btc_ohlcv_low_positive"),
        sa.CheckConstraint("close > 0", name="ck_btc_ohlcv_close_positive"),
        sa.CheckConstraint("volume >= 0", name="ck_btc_ohlcv_volume_non_negative"),
        sa.PrimaryKeyConstraint(
            "timestamp",
            "exchange",
            "symbol",
            "timeframe",
            "provider",
            name="pk_raw_btc_ohlcv",
        ),
        schema="raw",
        comment="Immutable provider OHLCV observations for BTC market data.",
    )


def downgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    op.drop_table("btc_ohlcv", schema="raw")
