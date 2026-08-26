"""System database table definitions."""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Identity,
    Index,
    JSON,
    MetaData,
    PrimaryKeyConstraint,
    String,
    Table,
    UniqueConstraint,
)

from btc_predictor.db.base import NAMING_CONVENTION


SYSTEM_SCHEMA = "system"
INGESTION_AUDIT_STATUSES = ("started", "succeeded", "failed", "partial")
INGESTION_AUDIT_LOG_PRIMARY_KEY = ("ingestion_audit_id",)

system_metadata = MetaData(schema=SYSTEM_SCHEMA, naming_convention=NAMING_CONVENTION)

ingestion_audit_log = Table(
    "ingestion_audit_log",
    system_metadata,
    Column("ingestion_audit_id", BigInteger, Identity(always=True), nullable=False),
    Column("job_run_id", String(length=128), nullable=False),
    Column("job_name", String(length=128), nullable=False),
    Column("feed_name", String(length=64), nullable=False),
    Column("provider", String(length=64), nullable=False),
    Column("source", String(length=255), nullable=False),
    Column("status", String(length=16), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("ended_at", DateTime(timezone=True), nullable=True),
    Column("records_fetched", BigInteger, nullable=False),
    Column("records_inserted", BigInteger, nullable=False),
    Column("failure_count", BigInteger, nullable=False),
    Column("gap_count", BigInteger, nullable=False),
    Column("failures", JSON, nullable=False),
    Column("gaps", JSON, nullable=False),
    Column("provider_response_metadata", JSON, nullable=False),
    Column("config_version", String(length=64), nullable=True),
    Column("reason_codes", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint(*INGESTION_AUDIT_LOG_PRIMARY_KEY, name="pk_system_ingestion_audit_log"),
    UniqueConstraint("job_run_id", name="uq_system_ingestion_audit_log_job_run_id"),
    CheckConstraint(
        "status in ('started', 'succeeded', 'failed', 'partial')",
        name="ingestion_audit_log_status_valid",
    ),
    CheckConstraint("ended_at is null or ended_at >= started_at", name="ingestion_audit_log_time_order"),
    CheckConstraint("records_fetched >= 0", name="ingestion_audit_log_records_fetched_non_negative"),
    CheckConstraint("records_inserted >= 0", name="ingestion_audit_log_records_inserted_non_negative"),
    CheckConstraint("failure_count >= 0", name="ingestion_audit_log_failure_count_non_negative"),
    CheckConstraint("gap_count >= 0", name="ingestion_audit_log_gap_count_non_negative"),
    comment="Ingestion job audit log with counters, gaps, failures, and provider metadata.",
)
Index("ix_system_ingestion_audit_log_job_name_started", ingestion_audit_log.c.job_name, ingestion_audit_log.c.started_at)
Index("ix_system_ingestion_audit_log_status", ingestion_audit_log.c.status)
