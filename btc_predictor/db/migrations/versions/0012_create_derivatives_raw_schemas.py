"""create derivatives raw schemas

Revision ID: 0012_raw_derivatives
Revises: 0011_raw_btc_ohlcv
Create Date: 2026-08-25 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0012_raw_derivatives"
down_revision = "0011_raw_btc_ohlcv"
branch_labels = None
depends_on = None


DERIVATIVES_TABLES = (
    "funding_rates",
    "open_interest",
    "futures_basis",
    "liquidations",
    "perp_volume",
)


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    _create_funding_rates()
    _create_open_interest()
    _create_futures_basis()
    _create_liquidations()
    _create_perp_volume()


def downgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    for table_name in reversed(DERIVATIVES_TABLES):
        op.drop_table(table_name, schema="raw")


def _create_funding_rates() -> None:
    op.create_table(
        "funding_rates",
        sa.Column(
            "observation_time",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="UTC funding timestamp or period end reported by the exchange.",
        ),
        sa.Column("exchange", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("instrument", sa.String(length=64), nullable=False),
        sa.Column(
            "funding_rate",
            sa.Numeric(precision=38, scale=18),
            nullable=False,
            comment="Decimal funding rate for the funding interval, e.g. 0.0001 = 1 bp.",
        ),
        sa.Column("funding_interval_hours", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="UTC time this observation first became available to the system.",
        ),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "funding_interval_hours > 0",
            name="ck_funding_rates_funding_interval_hours_positive",
        ),
        sa.PrimaryKeyConstraint(
            "observation_time",
            "exchange",
            "symbol",
            "instrument",
            "provider",
            name="pk_raw_funding_rates",
        ),
        schema="raw",
        comment="Point-in-time raw perpetual funding observations.",
    )
    op.create_index(
        "ix_raw_funding_rates_available_at",
        "funding_rates",
        ["available_at"],
        schema="raw",
    )


def _create_open_interest() -> None:
    op.create_table(
        "open_interest",
        sa.Column(
            "observation_time",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="UTC market timestamp for the open-interest snapshot.",
        ),
        sa.Column("exchange", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("instrument", sa.String(length=64), nullable=False),
        sa.Column("open_interest", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column(
            "open_interest_unit",
            sa.String(length=32),
            nullable=False,
            comment="Provider-reported unit, for example contracts, coin, or USD.",
        ),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="UTC time this observation first became available to the system.",
        ),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "open_interest >= 0",
            name="ck_open_interest_open_interest_non_negative",
        ),
        sa.PrimaryKeyConstraint(
            "observation_time",
            "exchange",
            "symbol",
            "instrument",
            "provider",
            name="pk_raw_open_interest",
        ),
        schema="raw",
        comment="Point-in-time raw open-interest snapshots.",
    )
    op.create_index(
        "ix_raw_open_interest_available_at",
        "open_interest",
        ["available_at"],
        schema="raw",
    )


def _create_futures_basis() -> None:
    op.create_table(
        "futures_basis",
        sa.Column(
            "observation_time",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="UTC market timestamp for the basis observation.",
        ),
        sa.Column("exchange", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("instrument", sa.String(length=64), nullable=False),
        sa.Column(
            "expiry",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="UTC futures expiry timestamp.",
        ),
        sa.Column(
            "basis_rate",
            sa.Numeric(precision=38, scale=18),
            nullable=False,
            comment="Decimal futures basis versus spot, e.g. 0.05 = 5%.",
        ),
        sa.Column(
            "annualized_basis_rate",
            sa.Numeric(precision=38, scale=18),
            nullable=False,
            comment="Decimal annualized basis, e.g. 0.15 = 15%.",
        ),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="UTC time this observation first became available to the system.",
        ),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "observation_time",
            "exchange",
            "symbol",
            "instrument",
            "expiry",
            "provider",
            name="pk_raw_futures_basis",
        ),
        schema="raw",
        comment="Point-in-time raw futures basis observations.",
    )
    op.create_index(
        "ix_raw_futures_basis_available_at",
        "futures_basis",
        ["available_at"],
        schema="raw",
    )


def _create_liquidations() -> None:
    op.create_table(
        "liquidations",
        sa.Column(
            "observation_time",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="UTC bar timestamp or period end for liquidation aggregation.",
        ),
        sa.Column("exchange", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False, comment="Liquidated side: long or short."),
        sa.Column("quantity", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column(
            "quantity_unit",
            sa.String(length=32),
            nullable=False,
            comment="Provider-reported liquidation quantity unit.",
        ),
        sa.Column("notional_usd", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="UTC time this observation first became available to the system.",
        ),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("side in ('long', 'short')", name="ck_liquidations_side_valid"),
        sa.CheckConstraint("quantity >= 0", name="ck_liquidations_quantity_non_negative"),
        sa.CheckConstraint(
            "notional_usd is null or notional_usd >= 0",
            name="ck_liquidations_notional_usd_non_negative",
        ),
        sa.PrimaryKeyConstraint(
            "observation_time",
            "exchange",
            "symbol",
            "timeframe",
            "side",
            "provider",
            name="pk_raw_liquidations",
        ),
        schema="raw",
        comment="Point-in-time raw liquidation observations or aggregations.",
    )
    op.create_index(
        "ix_raw_liquidations_available_at",
        "liquidations",
        ["available_at"],
        schema="raw",
    )


def _create_perp_volume() -> None:
    op.create_table(
        "perp_volume",
        sa.Column(
            "observation_time",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="UTC bar timestamp or period end for perpetual volume aggregation.",
        ),
        sa.Column("exchange", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("volume", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column(
            "volume_unit",
            sa.String(length=32),
            nullable=False,
            comment="Provider-reported volume unit, for example contracts, BTC, or USD.",
        ),
        sa.Column("notional_usd", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="UTC time this observation first became available to the system.",
        ),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("volume >= 0", name="ck_perp_volume_volume_non_negative"),
        sa.CheckConstraint(
            "notional_usd is null or notional_usd >= 0",
            name="ck_perp_volume_notional_usd_non_negative",
        ),
        sa.PrimaryKeyConstraint(
            "observation_time",
            "exchange",
            "symbol",
            "timeframe",
            "provider",
            name="pk_raw_perp_volume",
        ),
        schema="raw",
        comment="Point-in-time raw perpetual futures volume observations.",
    )
    op.create_index(
        "ix_raw_perp_volume_available_at",
        "perp_volume",
        ["available_at"],
        schema="raw",
    )
