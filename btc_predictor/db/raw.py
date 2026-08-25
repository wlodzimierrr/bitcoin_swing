"""Raw database table definitions."""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Index,
    MetaData,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Table,
)

from btc_predictor.db.base import NAMING_CONVENTION


RAW_SCHEMA = "raw"
BTC_OHLCV_TABLE_NAME = "btc_ohlcv"
BTC_OHLCV_PRIMARY_KEY = (
    "timestamp",
    "exchange",
    "symbol",
    "timeframe",
    "provider",
)
FUNDING_RATES_PRIMARY_KEY = (
    "observation_time",
    "exchange",
    "symbol",
    "instrument",
    "provider",
)
OPEN_INTEREST_PRIMARY_KEY = (
    "observation_time",
    "exchange",
    "symbol",
    "instrument",
    "provider",
)
FUTURES_BASIS_PRIMARY_KEY = (
    "observation_time",
    "exchange",
    "symbol",
    "instrument",
    "expiry",
    "provider",
)
LIQUIDATIONS_PRIMARY_KEY = (
    "observation_time",
    "exchange",
    "symbol",
    "timeframe",
    "side",
    "provider",
)
PERP_VOLUME_PRIMARY_KEY = (
    "observation_time",
    "exchange",
    "symbol",
    "timeframe",
    "provider",
)

raw_metadata = MetaData(schema=RAW_SCHEMA, naming_convention=NAMING_CONVENTION)

btc_ohlcv = Table(
    BTC_OHLCV_TABLE_NAME,
    raw_metadata,
    Column("timestamp", DateTime(timezone=True), nullable=False),
    Column("exchange", String(length=64), nullable=False),
    Column("symbol", String(length=32), nullable=False),
    Column("timeframe", String(length=16), nullable=False),
    Column("open", Numeric(precision=38, scale=18), nullable=False),
    Column("high", Numeric(precision=38, scale=18), nullable=False),
    Column("low", Numeric(precision=38, scale=18), nullable=False),
    Column("close", Numeric(precision=38, scale=18), nullable=False),
    Column("volume", Numeric(precision=38, scale=18), nullable=False),
    Column("provider", String(length=64), nullable=False),
    Column("ingested_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint(*BTC_OHLCV_PRIMARY_KEY, name="pk_raw_btc_ohlcv"),
    CheckConstraint("open > 0", name="open_positive"),
    CheckConstraint("high > 0", name="high_positive"),
    CheckConstraint("low > 0", name="low_positive"),
    CheckConstraint("close > 0", name="close_positive"),
    CheckConstraint("volume >= 0", name="volume_non_negative"),
)

funding_rates = Table(
    "funding_rates",
    raw_metadata,
    Column(
        "observation_time",
        DateTime(timezone=True),
        nullable=False,
        comment="UTC funding timestamp or period end reported by the exchange.",
    ),
    Column("exchange", String(length=64), nullable=False),
    Column("symbol", String(length=32), nullable=False),
    Column("instrument", String(length=64), nullable=False),
    Column(
        "funding_rate",
        Numeric(precision=38, scale=18),
        nullable=False,
        comment="Decimal funding rate for the funding interval, e.g. 0.0001 = 1 bp.",
    ),
    Column("funding_interval_hours", Numeric(precision=10, scale=4), nullable=False),
    Column("provider", String(length=64), nullable=False),
    Column("source", String(length=255), nullable=False),
    Column(
        "available_at",
        DateTime(timezone=True),
        nullable=False,
        comment="UTC time this observation first became available to the system.",
    ),
    Column("ingested_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint(*FUNDING_RATES_PRIMARY_KEY, name="pk_raw_funding_rates"),
    CheckConstraint("funding_interval_hours > 0", name="funding_interval_hours_positive"),
    comment="Point-in-time raw perpetual funding observations.",
)
Index("ix_raw_funding_rates_available_at", funding_rates.c.available_at)

open_interest = Table(
    "open_interest",
    raw_metadata,
    Column(
        "observation_time",
        DateTime(timezone=True),
        nullable=False,
        comment="UTC market timestamp for the open-interest snapshot.",
    ),
    Column("exchange", String(length=64), nullable=False),
    Column("symbol", String(length=32), nullable=False),
    Column("instrument", String(length=64), nullable=False),
    Column("open_interest", Numeric(precision=38, scale=18), nullable=False),
    Column(
        "open_interest_unit",
        String(length=32),
        nullable=False,
        comment="Provider-reported unit, for example contracts, coin, or USD.",
    ),
    Column("provider", String(length=64), nullable=False),
    Column("source", String(length=255), nullable=False),
    Column(
        "available_at",
        DateTime(timezone=True),
        nullable=False,
        comment="UTC time this observation first became available to the system.",
    ),
    Column("ingested_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint(*OPEN_INTEREST_PRIMARY_KEY, name="pk_raw_open_interest"),
    CheckConstraint("open_interest >= 0", name="open_interest_non_negative"),
    comment="Point-in-time raw open-interest snapshots.",
)
Index("ix_raw_open_interest_available_at", open_interest.c.available_at)

futures_basis = Table(
    "futures_basis",
    raw_metadata,
    Column(
        "observation_time",
        DateTime(timezone=True),
        nullable=False,
        comment="UTC market timestamp for the basis observation.",
    ),
    Column("exchange", String(length=64), nullable=False),
    Column("symbol", String(length=32), nullable=False),
    Column("instrument", String(length=64), nullable=False),
    Column(
        "expiry",
        DateTime(timezone=True),
        nullable=False,
        comment="UTC futures expiry timestamp.",
    ),
    Column(
        "basis_rate",
        Numeric(precision=38, scale=18),
        nullable=False,
        comment="Decimal futures basis versus spot, e.g. 0.05 = 5%.",
    ),
    Column(
        "annualized_basis_rate",
        Numeric(precision=38, scale=18),
        nullable=False,
        comment="Decimal annualized basis, e.g. 0.15 = 15%.",
    ),
    Column("provider", String(length=64), nullable=False),
    Column("source", String(length=255), nullable=False),
    Column(
        "available_at",
        DateTime(timezone=True),
        nullable=False,
        comment="UTC time this observation first became available to the system.",
    ),
    Column("ingested_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint(*FUTURES_BASIS_PRIMARY_KEY, name="pk_raw_futures_basis"),
    comment="Point-in-time raw futures basis observations.",
)
Index("ix_raw_futures_basis_available_at", futures_basis.c.available_at)

liquidations = Table(
    "liquidations",
    raw_metadata,
    Column(
        "observation_time",
        DateTime(timezone=True),
        nullable=False,
        comment="UTC bar timestamp or period end for liquidation aggregation.",
    ),
    Column("exchange", String(length=64), nullable=False),
    Column("symbol", String(length=32), nullable=False),
    Column("timeframe", String(length=16), nullable=False),
    Column("side", String(length=8), nullable=False, comment="Liquidated side: long or short."),
    Column("quantity", Numeric(precision=38, scale=18), nullable=False),
    Column(
        "quantity_unit",
        String(length=32),
        nullable=False,
        comment="Provider-reported liquidation quantity unit.",
    ),
    Column("notional_usd", Numeric(precision=38, scale=18), nullable=True),
    Column("provider", String(length=64), nullable=False),
    Column("source", String(length=255), nullable=False),
    Column(
        "available_at",
        DateTime(timezone=True),
        nullable=False,
        comment="UTC time this observation first became available to the system.",
    ),
    Column("ingested_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint(*LIQUIDATIONS_PRIMARY_KEY, name="pk_raw_liquidations"),
    CheckConstraint("side in ('long', 'short')", name="liquidations_side_valid"),
    CheckConstraint("quantity >= 0", name="liquidations_quantity_non_negative"),
    CheckConstraint(
        "notional_usd is null or notional_usd >= 0",
        name="liquidations_notional_usd_non_negative",
    ),
    comment="Point-in-time raw liquidation observations or aggregations.",
)
Index("ix_raw_liquidations_available_at", liquidations.c.available_at)

perp_volume = Table(
    "perp_volume",
    raw_metadata,
    Column(
        "observation_time",
        DateTime(timezone=True),
        nullable=False,
        comment="UTC bar timestamp or period end for perpetual volume aggregation.",
    ),
    Column("exchange", String(length=64), nullable=False),
    Column("symbol", String(length=32), nullable=False),
    Column("timeframe", String(length=16), nullable=False),
    Column("volume", Numeric(precision=38, scale=18), nullable=False),
    Column(
        "volume_unit",
        String(length=32),
        nullable=False,
        comment="Provider-reported volume unit, for example contracts, BTC, or USD.",
    ),
    Column("notional_usd", Numeric(precision=38, scale=18), nullable=True),
    Column("provider", String(length=64), nullable=False),
    Column("source", String(length=255), nullable=False),
    Column(
        "available_at",
        DateTime(timezone=True),
        nullable=False,
        comment="UTC time this observation first became available to the system.",
    ),
    Column("ingested_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint(*PERP_VOLUME_PRIMARY_KEY, name="pk_raw_perp_volume"),
    CheckConstraint("volume >= 0", name="perp_volume_non_negative"),
    CheckConstraint(
        "notional_usd is null or notional_usd >= 0",
        name="perp_volume_notional_usd_non_negative",
    ),
    comment="Point-in-time raw perpetual futures volume observations.",
)
Index("ix_raw_perp_volume_available_at", perp_volume.c.available_at)
