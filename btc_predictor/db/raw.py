"""Raw database table definitions."""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
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
