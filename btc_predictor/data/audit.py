"""Ingestion audit log helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert

from btc_predictor.data.ohlcv import require_utc_datetime
from btc_predictor.db.system import INGESTION_AUDIT_STATUSES, ingestion_audit_log


@dataclass(frozen=True)
class IngestionAuditRecord:
    job_run_id: str
    job_name: str
    feed_name: str
    provider: str
    source: str
    status: str
    started_at: datetime
    records_fetched: int
    records_inserted: int
    ended_at: datetime | None = None
    failures: tuple[str, ...] = ()
    gaps: tuple[str, ...] = ()
    provider_response_metadata: Mapping[str, Any] = field(default_factory=dict)
    config_version: str | None = None
    reason_codes: tuple[str, ...] = ()
    created_at: datetime | None = None

    def as_record(self) -> dict[str, Any]:
        self._validate()
        return {
            "job_run_id": self.job_run_id,
            "job_name": self.job_name,
            "feed_name": self.feed_name,
            "provider": self.provider,
            "source": self.source,
            "status": self.status,
            "started_at": require_utc_datetime(self.started_at, "started_at"),
            "ended_at": (
                require_utc_datetime(self.ended_at, "ended_at")
                if self.ended_at is not None
                else None
            ),
            "records_fetched": self.records_fetched,
            "records_inserted": self.records_inserted,
            "failure_count": len(self.failures),
            "gap_count": len(self.gaps),
            "failures": list(self.failures),
            "gaps": list(self.gaps),
            "provider_response_metadata": dict(self.provider_response_metadata),
            "config_version": self.config_version,
            "reason_codes": list(self.reason_codes),
            "created_at": require_utc_datetime(self.created_at or self.started_at, "created_at"),
        }

    def _validate(self) -> None:
        for field_name in ("job_run_id", "job_name", "feed_name", "provider", "source"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if self.status not in INGESTION_AUDIT_STATUSES:
            raise ValueError(f"Unsupported ingestion audit status: {self.status}")
        require_utc_datetime(self.started_at, "started_at")
        if self.ended_at is not None:
            ended_at = require_utc_datetime(self.ended_at, "ended_at")
            if ended_at < self.started_at:
                raise ValueError("ended_at must be >= started_at")
        for field_name in ("records_fetched", "records_inserted"):
            value = getattr(self, field_name)
            if value < 0:
                raise ValueError(f"{field_name} must be >= 0")


def build_ingestion_audit_insert_ignore(records: Sequence[IngestionAuditRecord]):
    """Build an idempotent insert for stable ingestion audit records."""

    if not records:
        raise ValueError("records must contain at least one ingestion audit record")

    statement = insert(ingestion_audit_log).values([record.as_record() for record in records])
    return statement.on_conflict_do_nothing(index_elements=["job_run_id"])
