"""create ingestion audit log

Revision ID: 0018_ingestion_audit
Revises: 0017_manual_trade_journal
Create Date: 2026-08-26 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0018_ingestion_audit"
down_revision = "0017_manual_trade_journal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    op.create_table(
        "ingestion_audit_log",
        sa.Column("ingestion_audit_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("job_run_id", sa.String(length=128), nullable=False),
        sa.Column("job_name", sa.String(length=128), nullable=False),
        sa.Column("feed_name", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_fetched", sa.BigInteger(), nullable=False),
        sa.Column("records_inserted", sa.BigInteger(), nullable=False),
        sa.Column("failure_count", sa.BigInteger(), nullable=False),
        sa.Column("gap_count", sa.BigInteger(), nullable=False),
        sa.Column("failures", sa.JSON(), nullable=False),
        sa.Column("gaps", sa.JSON(), nullable=False),
        sa.Column("provider_response_metadata", sa.JSON(), nullable=False),
        sa.Column("config_version", sa.String(length=64), nullable=True),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status in ('started', 'succeeded', 'failed', 'partial')",
            name="ck_ingestion_audit_log_status_valid",
        ),
        sa.CheckConstraint(
            "ended_at is null or ended_at >= started_at",
            name="ck_ingestion_audit_log_time_order",
        ),
        sa.CheckConstraint(
            "records_fetched >= 0",
            name="ck_ingestion_audit_log_records_fetched_non_negative",
        ),
        sa.CheckConstraint(
            "records_inserted >= 0",
            name="ck_ingestion_audit_log_records_inserted_non_negative",
        ),
        sa.CheckConstraint(
            "failure_count >= 0",
            name="ck_ingestion_audit_log_failure_count_non_negative",
        ),
        sa.CheckConstraint(
            "gap_count >= 0",
            name="ck_ingestion_audit_log_gap_count_non_negative",
        ),
        sa.PrimaryKeyConstraint("ingestion_audit_id", name="pk_system_ingestion_audit_log"),
        sa.UniqueConstraint("job_run_id", name="uq_system_ingestion_audit_log_job_run_id"),
        schema="system",
        comment="Ingestion job audit log with counters, gaps, failures, and provider metadata.",
    )
    op.create_index(
        "ix_system_ingestion_audit_log_job_name_started",
        "ingestion_audit_log",
        ["job_name", "started_at"],
        schema="system",
    )
    op.create_index(
        "ix_system_ingestion_audit_log_status",
        "ingestion_audit_log",
        ["status"],
        schema="system",
    )


def downgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    op.drop_table("ingestion_audit_log", schema="system")
