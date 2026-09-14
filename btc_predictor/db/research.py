"""Research-schema persistence contracts."""

from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    JSON,
    MetaData,
    PrimaryKeyConstraint,
    String,
    Table,
    UniqueConstraint,
)

from btc_predictor.db.base import NAMING_CONVENTION


RESEARCH_SCHEMA = "research"
TRUSTED_ACQUISITION_TABLE = "etf_calendar_trusted_acquisitions"
TRUSTED_ACQUISITION_PRIMARY_KEY = ("envelope_sha256",)

research_metadata = MetaData(schema=RESEARCH_SCHEMA, naming_convention=NAMING_CONVENTION)

etf_calendar_trusted_acquisitions = Table(
    TRUSTED_ACQUISITION_TABLE,
    research_metadata,
    Column("envelope_sha256", String(length=64), nullable=False),
    Column("signed_payload", JSON, nullable=False),
    Column("signed_payload_sha256", String(length=64), nullable=False),
    Column("signing_key_id", String(length=128), nullable=False),
    Column("signature_algorithm", String(length=16), nullable=False),
    Column("signature", String(length=88), nullable=False),
    Column("response_sha256", String(length=64), nullable=False),
    Column("response_received_at", DateTime(timezone=True), nullable=False),
    Column("acquired_at", DateTime(timezone=True), nullable=False),
    Column("available_at", DateTime(timezone=True), nullable=False),
    Column("source_profile_id", String(length=128), nullable=False),
    Column("venue_id", String(length=32), nullable=False),
    Column("source_authority_id", String(length=128), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint(
        *TRUSTED_ACQUISITION_PRIMARY_KEY,
        name="pk_research_etf_calendar_trusted_acquisitions",
    ),
    UniqueConstraint(
        "signed_payload_sha256",
        "signing_key_id",
        name="uq_etf_calendar_trusted_acquisitions_payload_key",
    ),
    comment="Append-only Ed25519-signed ETF-calendar HTTPS acquisitions.",
)
