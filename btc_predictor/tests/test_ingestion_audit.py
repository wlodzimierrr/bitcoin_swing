from datetime import UTC, datetime

import pytest
from sqlalchemy.dialects import postgresql

from btc_predictor.data import IngestionAuditRecord, build_ingestion_audit_insert_ignore
from btc_predictor.db import (
    INGESTION_AUDIT_LOG_PRIMARY_KEY,
    INGESTION_AUDIT_STATUSES,
    ingestion_audit_log,
)


def audit_record(**overrides) -> IngestionAuditRecord:
    values = {
        "job_run_id": "ohlcv-20260826T000000Z",
        "job_name": "btc_ohlcv_collector",
        "feed_name": "btc_ohlcv",
        "provider": "coinbase",
        "source": "coinbase-api",
        "status": "partial",
        "started_at": datetime(2026, 8, 26, tzinfo=UTC),
        "ended_at": datetime(2026, 8, 26, 0, 1, tzinfo=UTC),
        "records_fetched": 24,
        "records_inserted": 23,
        "failures": ("timeout retry recovered",),
        "gaps": ("2026-08-25T05:00:00Z",),
        "provider_response_metadata": {"http_status": 200, "request_id": "abc"},
        "config_version": "dev",
        "reason_codes": ("MISSING_SOURCE_INTERVAL",),
    }
    values.update(overrides)
    return IngestionAuditRecord(**values)


def test_ingestion_audit_schema_tracks_required_job_fields() -> None:
    assert INGESTION_AUDIT_LOG_PRIMARY_KEY == ("ingestion_audit_id",)
    assert INGESTION_AUDIT_STATUSES == ("started", "succeeded", "failed", "partial")

    for column_name in (
        "job_run_id",
        "job_name",
        "feed_name",
        "provider",
        "source",
        "status",
        "started_at",
        "ended_at",
        "records_fetched",
        "records_inserted",
        "failure_count",
        "gap_count",
        "failures",
        "gaps",
        "provider_response_metadata",
        "config_version",
        "reason_codes",
        "created_at",
    ):
        assert column_name in ingestion_audit_log.c

    assert ingestion_audit_log.c.started_at.type.timezone is True
    assert ingestion_audit_log.c.ended_at.type.timezone is True
    assert ingestion_audit_log.c.created_at.type.timezone is True


def test_ingestion_audit_record_is_deterministic_and_counts_failures_and_gaps() -> None:
    record = audit_record().as_record()

    assert record["failure_count"] == 1
    assert record["gap_count"] == 1
    assert record["failures"] == ["timeout retry recovered"]
    assert record["gaps"] == ["2026-08-25T05:00:00Z"]
    assert record["provider_response_metadata"] == {"http_status": 200, "request_id": "abc"}
    assert record["reason_codes"] == ["MISSING_SOURCE_INTERVAL"]
    assert record["created_at"] == record["started_at"]


def test_ingestion_audit_insert_ignore_is_idempotent_on_job_run_id() -> None:
    statement = build_ingestion_audit_insert_ignore([audit_record()])
    compiled = str(statement.compile(dialect=postgresql.dialect()))

    assert "INSERT INTO system.ingestion_audit_log" in compiled
    assert "ON CONFLICT (job_run_id) DO NOTHING" in compiled
    assert "DO UPDATE SET" not in compiled


def test_ingestion_audit_record_rejects_invalid_status() -> None:
    with pytest.raises(ValueError, match="Unsupported ingestion audit status"):
        audit_record(status="done").as_record()


def test_ingestion_audit_record_rejects_negative_counts() -> None:
    with pytest.raises(ValueError, match="records_fetched"):
        audit_record(records_fetched=-1).as_record()


def test_ingestion_audit_record_rejects_non_utc_timestamps() -> None:
    with pytest.raises(ValueError, match="UTC"):
        audit_record(started_at=datetime(2026, 8, 26)).as_record()


def test_ingestion_audit_record_rejects_end_before_start() -> None:
    with pytest.raises(ValueError, match="ended_at"):
        audit_record(ended_at=datetime(2026, 8, 25, tzinfo=UTC)).as_record()
