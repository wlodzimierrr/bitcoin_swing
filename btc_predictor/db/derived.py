"""Derived market-reference database table definitions."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Index,
    MetaData,
    Numeric,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    Table,
)
from sqlalchemy.dialects.postgresql import insert

from btc_predictor.db.base import NAMING_CONVENTION


DERIVED_SCHEMA = "derived"
BTC_REFERENCE_COMPOSITE_TABLE_NAME = "btc_reference_composite"
BTC_REFERENCE_COMPOSITE_PRIMARY_KEY = (
    "reference_policy_version",
    "observation_time",
    "composite_method_version",
)

derived_metadata = MetaData(schema=DERIVED_SCHEMA, naming_convention=NAMING_CONVENTION)

btc_reference_composite = Table(
    BTC_REFERENCE_COMPOSITE_TABLE_NAME,
    derived_metadata,
    Column("reference_policy_version", String(length=64), nullable=False),
    Column("observation_time", DateTime(timezone=True), nullable=False),
    Column(
        "available_at",
        DateTime(timezone=True),
        nullable=False,
        comment="Fixed composite decision time: one-hour bar close plus five minutes.",
    ),
    Column("input_providers_expected", JSON, nullable=False),
    Column("input_providers_available", JSON, nullable=False),
    Column("bitstamp_observation_id", String(length=64), nullable=True),
    Column("coinbase_observation_id", String(length=64), nullable=True),
    Column("bitfinex_observation_id", String(length=64), nullable=True),
    Column("input_count", SmallInteger, nullable=False),
    Column("composite_method", String(length=64), nullable=False),
    Column("composite_method_version", String(length=64), nullable=False),
    Column("open", Numeric(precision=38, scale=18), nullable=True),
    Column("high", Numeric(precision=38, scale=18), nullable=True),
    Column("low", Numeric(precision=38, scale=18), nullable=True),
    Column("close", Numeric(precision=38, scale=18), nullable=True),
    Column("quality_state", String(length=32), nullable=False),
    Column("confirmation_state", String(length=48), nullable=False),
    Column("fallback_used", Boolean, nullable=False),
    Column("diagnostics", JSON, nullable=False),
    Column("reason_codes", JSON, nullable=False),
    PrimaryKeyConstraint(
        *BTC_REFERENCE_COMPOSITE_PRIMARY_KEY,
        name="pk_derived_btc_reference_composite",
    ),
    CheckConstraint("input_count between 0 and 3", name="input_count_range"),
    CheckConstraint(
        "quality_state in ('REFERENCE_OK', 'REFERENCE_DEGRADED', "
        "'REFERENCE_UNAVAILABLE', 'VENUE_DISAGREEMENT')",
        name="quality_state_valid",
    ),
    CheckConstraint(
        "confirmation_state in ('SINGLE_PROVIDER_OBSERVATION', "
        "'TWO_PROVIDER_CONSENSUS', 'THREE_PROVIDER_CONSENSUS', "
        "'UNRESOLVED_PROVIDER_DISAGREEMENT')",
        name="confirmation_state_valid",
    ),
    CheckConstraint("fallback_used = false", name="fallback_splicing_prohibited"),
    CheckConstraint(
        "((open is null and high is null and low is null and close is null) or "
        "(open is not null and high is not null and low is not null and close is not null))",
        name="ohlc_all_present_or_absent",
    ),
    CheckConstraint(
        "high is null or (open > 0 and high >= open and high >= close and "
        "low > 0 and low <= open and low <= close and high >= low)",
        name="ohlc_valid",
    ),
    comment=(
        "Immutable point-in-time cross-venue BTC reference-composite research "
        "observations with full raw provenance."
    ),
)
Index(
    "ix_derived_btc_reference_composite_available_at",
    btc_reference_composite.c.available_at,
)
Index(
    "ix_derived_btc_reference_composite_quality_state",
    btc_reference_composite.c.quality_state,
)


def build_reference_composite_insert_ignore(rows: Sequence[Mapping[str, Any]]):
    """Build an immutable, idempotent PostgreSQL composite insert."""

    if not rows:
        raise ValueError("rows must contain at least one composite observation")
    statement = insert(btc_reference_composite).values(list(rows))
    return statement.on_conflict_do_nothing(
        index_elements=list(BTC_REFERENCE_COMPOSITE_PRIMARY_KEY),
    )
